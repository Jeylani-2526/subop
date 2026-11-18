"""tests/test_cdc_latency_store.py — M8W28T4.

LatencyStore's SQL against a real PostgreSQL through the Abstraction Layer,
in a throwaway schema so a developer's real latency rows are never touched.
"""

from __future__ import annotations

import uuid

import pytest

from services.abstraction.abstraction_layer import AbstractionLayer
from services.cdc.latency_store import LatencyStore

ORDERS, CUSTOMERS = "cdc_demo.orders", "cdc_demo.customers"


def event(table=ORDERS, op="update", row_id=7):
    return {"op": op, "table": table, "before": None, "after": {"id": row_id}}


def points(t0, capture=0, publish=0, consumer=0, warehouse=0):
    t1 = t0 + capture
    t2 = t1 + publish
    t3 = t2 + consumer
    return (t0, t1, t2, t3, t3 + warehouse)


@pytest.fixture
def layer(test_db_connection):
    return AbstractionLayer(connector=test_db_connection, database="postgresql")


@pytest.fixture
def store(layer):
    schema = f"test_lat_{uuid.uuid4().hex[:8]}"
    latency = LatencyStore(layer, table=f"{schema}.event_latency")
    latency.ensure_schema()
    yield latency
    layer.execute_write(f"DROP SCHEMA IF EXISTS {schema} CASCADE")


def test_ensure_schema_is_idempotent(store):
    store.ensure_schema()
    store.ensure_schema()


def test_redelivery_is_a_no_op(store):
    assert store.record(event(), 500, points(1_000, 100)) == 1
    assert store.record(event(), 500, points(1_000, 999)) == 0
    assert store.summary()["sample_size"] == 1
    assert store.summary()["capture"]["max_ms"] == 100  # the first write stands


def test_event_without_lsn_is_not_recorded(store):
    assert store.record(event(), None, points(1_000)) == 0
    assert store.summary() is None


def test_summary_is_none_before_any_event(store):
    assert store.summary() is None
    assert store.summary([ORDERS]) is None


def test_hops_are_computed_from_the_raw_points(store):
    store.record(event(row_id=1), 501, points(1_000, 400, 12, 288, 9))
    stats = store.summary()
    assert stats["e2e"] == {"median_ms": 709, "p95_ms": 709, "max_ms": 709}
    assert stats["capture"]["max_ms"] == 400
    assert stats["publish"]["max_ms"] == 12
    assert stats["consumer"]["max_ms"] == 288
    assert stats["warehouse"]["max_ms"] == 9
    assert stats["lag_ms"] == 709


def test_median_p95_and_max_are_unrounded(store):
    # e2e of 100, 200, 300, 400: median 250, p95 = 385 (percentile_cont).
    for i, e2e in enumerate((100, 200, 300, 400)):
        store.record(event(row_id=i), 600 + i, points(10_000 * (i + 1), warehouse=e2e))
    stats = store.summary()
    assert stats["sample_size"] == 4
    assert stats["e2e"] == {"median_ms": 250.0, "p95_ms": 385.0, "max_ms": 400}


def test_fractional_values_keep_their_decimals(store):
    store.record(event(row_id=1), 700, points(1_000, warehouse=1))
    store.record(event(row_id=2), 701, points(2_000, warehouse=2))
    assert store.summary()["e2e"]["median_ms"] == 1.5


def test_window_keeps_only_the_newest_events_by_t4(layer, store):
    small = LatencyStore(layer, window_size=3, table=store.table)
    for i, e2e in enumerate((5_000, 10, 20, 30)):
        small.record(event(row_id=i), 800 + i, points(100_000 * i, warehouse=e2e))
    stats = small.summary()
    assert (stats["window_size"], stats["sample_size"]) == (3, 3)
    assert stats["e2e"]["max_ms"] == 30  # the oldest, slow event fell out


def test_lag_is_the_newest_event_not_the_slowest(store):
    store.record(event(row_id=1), 901, points(1_000, warehouse=9_000))
    store.record(event(row_id=2), 902, points(20_000, warehouse=50))
    assert store.summary()["lag_ms"] == 50


def test_summary_can_be_limited_to_tables(store):
    store.record(event(ORDERS, row_id=1), 1001, points(1_000, warehouse=100))
    store.record(event(CUSTOMERS, row_id=1), 1002, points(2_000, warehouse=900))
    assert store.summary([ORDERS])["e2e"]["max_ms"] == 100
    assert store.summary([CUSTOMERS])["e2e"]["max_ms"] == 900
    assert store.summary()["sample_size"] == 2
    assert store.summary(["cdc_demo.nothing"]) is None


def test_e2e_by_key_matches_event_log_keys(store):
    store.record(event(op="insert", row_id=7), 1100, points(1_000, warehouse=812))
    found = store.e2e_by_key(
        [(ORDERS, 1100, "insert", "7"), (ORDERS, 1101, "update", "7")]
    )
    assert found == {(ORDERS, 1100, "insert", "7"): 812}
    assert store.e2e_by_key([]) == {}
