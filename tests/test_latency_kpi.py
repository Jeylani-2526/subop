"""tests/test_latency_kpi.py — M8W29T4.

Run drivers are tested with fakes; the report runs against a real PostgreSQL
in a throwaway schema, so the committed SQL is the SQL that is tested.
"""

from __future__ import annotations

import uuid

import pytest

from services.abstraction.abstraction_layer import AbstractionLayer
from services.cdc.latency_kpi import (
    Window,
    clock_samples,
    main,
    report,
    run_active,
    run_idle,
)
from services.cdc.latency_store import LatencyStore

# -- clock --------------------------------------------------------------------


def test_clock_skew_is_taken_at_the_midpoint():
    host = iter([1000, 1010, 2000, 2004])
    db = iter([1105, 2052])
    samples = clock_samples(lambda: next(db), lambda: next(host), n=2)
    assert samples == [(100, 5), (50, 2)]


# -- drivers ---------------------------------------------------------------------


class FakeFeed:
    """Latency rows that appear `delay` polls after each change."""

    def __init__(self, delay=2, start_id=10):
        self.next_id, self.delay = start_id, delay
        self.pending, self.rows, self.log = [], [], []

    def change(self):
        self.log.append("change")
        self.next_id += 1
        self.pending.append([self.next_id, self.delay])

    def latest(self, after_id):
        for item in self.pending:
            item[1] -= 1
        while self.pending and self.pending[0][1] <= 0:
            self.rows.append(self.pending.pop(0)[0])
        found = [r for r in self.rows if r > after_id]
        return min(found) if found else None

    def current_max(self):
        return 10


class FakeTime:
    def __init__(self, log):
        self.t, self.log = 0.0, log

    def sleep(self, s):
        if s >= 1:
            self.log.append(f"pause {s:g}")
        self.t += s

    def now(self):
        return self.t


def test_idle_waits_for_each_event_then_pauses():
    feed = FakeFeed()
    clock = FakeTime(feed.log)
    window = run_idle(
        feed.change,
        feed.latest,
        feed.current_max,
        count=3,
        pause_s=5,
        timeout_s=60,
        sleep=clock.sleep,
        now=clock.now,
    )
    assert window == Window(11, 13)
    assert feed.log == ["change", "pause 5", "change", "pause 5", "change"]


def test_idle_stops_when_an_event_never_arrives():
    feed = FakeFeed(delay=10_000)
    clock = FakeTime(feed.log)
    with pytest.raises(TimeoutError, match="event 1 of 31"):
        run_idle(
            feed.change,
            feed.latest,
            feed.current_max,
            count=31,
            pause_s=5,
            timeout_s=30,
            sleep=clock.sleep,
            now=clock.now,
        )


def test_active_collects_events_and_always_stops_the_load():
    feed = FakeFeed(delay=1)
    clock = FakeTime(feed.log)
    stopped = []

    def latest(after_id):
        feed.change()  # the background load keeps producing
        return feed.latest(after_id)

    window = run_active(
        lambda: "proc",
        stopped.append,
        latest,
        feed.current_max,
        count=4,
        timeout_s=60,
        sleep=clock.sleep,
        now=clock.now,
    )
    assert (window.first_id, window.last_id) == (11, 14)
    assert stopped == ["proc"]

    stopped.clear()
    with pytest.raises(TimeoutError):
        run_active(
            lambda: "proc",
            stopped.append,
            lambda after_id: None,
            feed.current_max,
            count=4,
            timeout_s=5,
            sleep=clock.sleep,
            now=clock.now,
        )
    assert stopped == ["proc"]


# -- report against a real PostgreSQL -------------------------------------------


@pytest.fixture
def layer(test_db_connection):
    return AbstractionLayer(connector=test_db_connection, database="postgresql")


@pytest.fixture
def table(layer):
    schema = f"test_kpi_{uuid.uuid4().hex[:8]}"
    name = f"{schema}.event_latency"
    LatencyStore(layer, table=name).ensure_schema()
    yield name
    layer.execute_write(f"DROP SCHEMA IF EXISTS {schema} CASCADE")


def add(layer, table, e2e_ms, lsn, op="insert", name="cdc_demo.orders"):
    t0 = 1_800_000_000_000
    # hops: capture 100, publish 50, consumer = rest - 20, warehouse 20
    points = (t0, t0 + 100, t0 + 150, t0 + e2e_ms - 20, t0 + e2e_ms)
    layer.execute_write(
        f"INSERT INTO {table} (table_name, op, row_key, lsn, t0_ms, t1_ms, t2_ms, "
        f"t3_ms, t4_ms) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (name, op, str(lsn), lsn, *points),
    )
    return layer.execute_query(f"SELECT max(id) AS id FROM {table}")[0]["id"]


def test_report_excludes_the_warm_up_and_computes_unrounded_stats(layer, table):
    first = add(layer, table, 290_000, 1)  # warm-up: slow first-topic pickup
    for i in range(30):
        last = add(layer, table, 1000 + 10 * i, 100 + i)
    result = report(layer, Window(first, last), table)

    assert result["warm_up"] == [{"id": first, "e2e_ms": 290_000}]
    e2e = result["hops"][0]
    assert e2e["hop"] == "e2e"
    assert (e2e["n"], e2e["min_ms"], e2e["max_ms"]) == (30, 1000, 1290)
    assert e2e["median_ms"] == pytest.approx(1145.0)
    assert e2e["p95_ms"] == pytest.approx(1275.5)
    assert e2e["over_30s"] == 0
    assert [h["hop"] for h in result["hops"]] == [
        "e2e",
        "capture",
        "publish",
        "consumer",
        "warehouse",
    ]
    assert result["hops"][1]["max_ms"] == 100
    assert result["verdict"] == "MET"


def test_report_not_met_when_p95_reaches_30_seconds(layer, table):
    first = add(layer, table, 500, 1)
    for i in range(30):
        last = add(layer, table, 56_000 if i >= 27 else 800, 100 + i)
    result = report(layer, Window(first, last), table)
    assert result["hops"][0]["over_30s"] == 3
    assert result["verdict"] == "NOT MET"


def test_report_counts_only_order_inserts_in_the_window(layer, table):
    first = add(layer, table, 500, 1)
    for i in range(29):
        last = add(layer, table, 800, 100 + i)
    add(layer, table, 800, 900, op="update")
    last = add(layer, table, 800, 901, name="cdc_demo.customers")
    result = report(layer, Window(first, last), table)
    assert result["verdict"] == "INCOMPLETE (29 of 30 counted)"


def test_sql_command_prints_the_committed_query(capsys):
    assert main(["sql"]) == 0
    out = capsys.readouterr().out
    assert "percentile_cont(0.95)" in out and "OFFSET %(skip)s" in out


def test_printed_columns_never_run_together(capsys):
    from services.cdc.latency_kpi import print_report

    hop = {
        "hop": "capture",
        "n": 30,
        "min_ms": 11,
        "median_ms": 234.0,
        "p95_ms": 476.54999999999995,
        "max_ms": 490,
        "over_30s": 0,
    }
    print_report(
        "idle",
        {"window": Window(8, 38), "warm_up": [], "hops": [hop], "verdict": "MET"},
    )
    line = capsys.readouterr().out.splitlines()[3]
    assert line.split() == ["capture", "30", "11", "234.00", "476.55", "490", "0"]
