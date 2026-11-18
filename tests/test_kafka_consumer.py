"""tests/test_kafka_consumer.py — M7W26T3; latency points M8W28T4.

Drives KafkaCDCConnector with an in-memory stand-in for confluent-kafka's
Consumer, fed with the real captured envelopes. No broker is needed, for the
same reason test_cdc_normalizer.py needs none: CI cannot run logical decoding.
"""

from __future__ import annotations

import asyncio
import copy
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


from services.cdc.kafka_consumer import (
    HALTED,
    HANDLED,
    RETRY,
    SKIPPED,
    KafkaCDCConnector,
)
from services.connectors.errors import WriteError
from services.connectors.streaming_connector_base import StreamingConnectionConfig

FIXTURES = Path(__file__).parent / "fixtures" / "cdc"
ORDERS_TOPIC = "subop-postgres-cdc.cdc_demo.orders"
CUSTOMERS_TOPIC = "subop-postgres-cdc.cdc_demo.customers"
ORDERS = "cdc_demo.orders"
CUSTOMERS = "cdc_demo.customers"


def load(name: str) -> Dict[str, Any]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def as_table(envelope: Dict[str, Any], table: str) -> Dict[str, Any]:
    """The same envelope attributed to another table, standing in for a second
    published table with an identical shape."""
    moved = copy.deepcopy(envelope)
    moved["payload"]["source"]["table"] = table
    return moved


class FakeMsg:
    def __init__(self, topic, offset, value, partition=0, error=None):
        self._topic, self._offset, self._partition = topic, offset, partition
        self._value, self._error = value, error

    def topic(self):
        return self._topic

    def partition(self):
        return self._partition

    def offset(self):
        return self._offset

    def value(self):
        return self._value

    def error(self):
        return self._error


def msg(topic: str, offset: int, envelope: Optional[Dict[str, Any]]) -> FakeMsg:
    value = None if envelope is None else json.dumps(envelope).encode("utf-8")
    return FakeMsg(topic, offset, value)


class FakeConsumer:
    def __init__(self, messages: Optional[List[FakeMsg]] = None, on_empty=None):
        self.queue = list(messages or [])
        self.on_empty = on_empty
        self.committed: List[tuple] = []
        self.paused: List[tuple] = []
        self.seeks: List[tuple] = []
        self.subscribed_to: List[str] = []
        self.settings: Dict[str, Any] = {}
        self.closed = False

    def subscribe(self, topics):
        self.subscribed_to = list(topics)

    def poll(self, timeout):
        if self.queue:
            return self.queue.pop(0)
        if self.on_empty:
            self.on_empty()
        return None

    def commit(self, message, asynchronous):
        assert asynchronous is False, "commit must be synchronous"
        self.committed.append((message.topic(), message.offset()))

    def pause(self, partitions):
        self.paused.extend((p.topic, p.partition) for p in partitions)

    def seek(self, partition):
        self.seeks.append((partition.topic, partition.offset))

    def close(self):
        self.closed = True


class FakeStore:
    """In-memory CDCStateStore with the same method surface."""

    def __init__(self):
        self.rows: Dict[str, Dict[str, Any]] = {}
        self.baseline_saves = 0
        self.events: List[tuple] = []

    def _row(self, table):
        return self.rows.setdefault(
            table,
            {
                "baseline": None,
                "halted": False,
                "last_lsn": None,
            },
        )

    def load(self):
        # Like the real store, the count comes from the deduplicated event log.
        rows = copy.deepcopy(self.rows)
        for table, row in rows.items():
            row["events_processed"] = len(
                {e for e in self.events if e[0] == table and e[2] is not None}
            )
        return rows

    def save_baseline(self, table, snapshot):
        self.baseline_saves += 1
        self._row(table)["baseline"] = dict(snapshot)

    def record_event(self, table, ts_ms, lsn):
        row = self._row(table)
        row["last_event_ts_ms"] = ts_ms
        row["last_lsn"] = lsn

    def record_halt(self, table, error_code, reason):
        row = self._row(table)
        row.update(halted=True, halt_error_code=error_code, halt_reason=reason)

    def append_event(self, event, lsn):
        self.events.append((event["table"], event["op"], lsn))

    def clear_halt(self, table):
        self._row(table).update(halted=False, halt_error_code=None, halt_reason=None)


class Recorder:
    def __init__(self, fail_with: Optional[Exception] = None):
        self.calls: List[tuple] = []
        self.fail_with = fail_with

    def __call__(self, event, meta):
        self.calls.append((event, meta))
        if self.fail_with is not None:
            raise self.fail_with


def connector(store=None) -> KafkaCDCConnector:
    config = StreamingConnectionConfig(
        "unused:9092", r"^subop-postgres-cdc\..*", "test"
    )
    return KafkaCDCConnector(config, state_store=store)


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_real_envelopes_are_handled_and_committed():
    conn, kafka, handler = connector(FakeStore()), FakeConsumer(), Recorder()
    for offset, name in enumerate(("insert.json", "update.json", "delete.json")):
        assert (
            conn.handle_message(kafka, msg(ORDERS_TOPIC, offset, load(name)), handler)
            == HANDLED
        )
    assert [e["op"] for e, _ in handler.calls] == ["insert", "update", "delete"]
    assert kafka.committed == [(ORDERS_TOPIC, 0), (ORDERS_TOPIC, 1), (ORDERS_TOPIC, 2)]


def test_handler_receives_the_lsn_for_ordering():
    """M7W26T4 orders upserts by LSN, which the neutral event does not carry."""
    conn, handler = connector(), Recorder()
    envelope = load("update.json")
    conn.handle_message(FakeConsumer(), msg(ORDERS_TOPIC, 7, envelope), handler)
    _, meta = handler.calls[0]
    assert meta["lsn"] == envelope["payload"]["source"]["lsn"]
    assert (meta["topic"], meta["offset"]) == (ORDERS_TOPIC, 7)


def test_snapshot_then_streaming_does_not_halt():
    """The live sequence — the false halt M7W26T2 fixed, now at consumer level."""
    conn, kafka, handler = connector(), FakeConsumer(), Recorder()
    assert (
        conn.handle_message(
            kafka, msg(ORDERS_TOPIC, 0, load("snapshot_event.json")), handler
        )
        == HANDLED
    )
    assert (
        conn.handle_message(kafka, msg(ORDERS_TOPIC, 1, load("insert.json")), handler)
        == HANDLED
    )
    assert not conn.halted


def test_baseline_is_persisted_once_per_table():
    store = FakeStore()
    conn, kafka = connector(store), FakeConsumer()
    for offset, name in enumerate(("insert.json", "update.json")):
        conn.handle_message(kafka, msg(ORDERS_TOPIC, offset, load(name)), Recorder())
    assert store.baseline_saves == 1
    assert store.load()[ORDERS]["events_processed"] == 2
    assert [op for _, op, _ in store.events] == ["insert", "update"]
    assert (
        store.rows[ORDERS]["last_lsn"]
        == load("update.json")["payload"]["source"]["lsn"]
    )


# ---------------------------------------------------------------------------
# Commit only after the handler succeeds
# ---------------------------------------------------------------------------


def test_retryable_handler_failure_seeks_back_without_committing():
    failure = WriteError(
        "db busy", error_code="X", connector_type="postgresql", retryable=True
    )
    conn, kafka = connector(), FakeConsumer()
    outcome = conn.handle_message(
        kafka, msg(ORDERS_TOPIC, 3, load("insert.json")), Recorder(failure)
    )
    assert outcome == RETRY
    assert kafka.committed == []
    assert kafka.seeks == [(ORDERS_TOPIC, 3)]
    assert not conn.halted


def test_non_retryable_handler_failure_halts_without_committing():
    failure = WriteError(
        "bad row", error_code="POSTGRES_WRITE_FAILED", connector_type="postgresql"
    )
    store = FakeStore()
    conn, kafka = connector(store), FakeConsumer()
    outcome = conn.handle_message(
        kafka, msg(ORDERS_TOPIC, 3, load("insert.json")), Recorder(failure)
    )
    assert outcome == HALTED
    assert kafka.committed == []
    assert store.rows[ORDERS]["halt_error_code"] == "POSTGRES_WRITE_FAILED"


def test_unclassified_handler_failure_halts_rather_than_skipping():
    conn, kafka = connector(), FakeConsumer()
    outcome = conn.handle_message(
        kafka, msg(ORDERS_TOPIC, 0, load("insert.json")), Recorder(RuntimeError("boom"))
    )
    assert outcome == HALTED
    assert conn.halted[ORDERS]["error_code"] == "CDC_HANDLER_FAILED"


# ---------------------------------------------------------------------------
# Table-scoped halt — Design Note Section 3.4
# ---------------------------------------------------------------------------


def test_drift_halts_that_table_and_the_other_keeps_flowing():
    store = FakeStore()
    conn, kafka, handler = connector(store), FakeConsumer(), Recorder()
    conn.handle_message(kafka, msg(ORDERS_TOPIC, 0, load("insert.json")), handler)
    customers = as_table(load("insert.json"), "customers")
    conn.handle_message(kafka, msg(CUSTOMERS_TOPIC, 0, customers), handler)

    outcome = conn.handle_message(
        kafka, msg(ORDERS_TOPIC, 1, load("drift_column_added.json")), handler
    )
    assert outcome == HALTED
    assert kafka.paused == [(ORDERS_TOPIC, 0)]
    assert conn.halted[ORDERS]["error_code"] == "CDC_SCHEMA_DRIFT_DETECTED"
    assert store.rows[ORDERS]["halted"] is True

    assert (
        conn.handle_message(kafka, msg(CUSTOMERS_TOPIC, 1, customers), handler)
        == HANDLED
    )
    assert (CUSTOMERS_TOPIC, 1) in kafka.committed
    assert CUSTOMERS not in conn.halted


def test_nothing_is_committed_past_the_halting_message():
    """Committing a later offset on the partition would implicitly commit the
    halted message too, and a restart would never see it again."""
    conn, kafka = connector(), FakeConsumer()
    conn.handle_message(kafka, msg(ORDERS_TOPIC, 0, load("insert.json")), Recorder())
    conn.handle_message(
        kafka, msg(ORDERS_TOPIC, 1, load("drift_column_added.json")), Recorder()
    )
    assert (
        conn.handle_message(
            kafka, msg(ORDERS_TOPIC, 2, load("insert.json")), Recorder()
        )
        == SKIPPED
    )
    assert kafka.committed == [(ORDERS_TOPIC, 0)]


def test_truncate_halts_the_table():
    conn = connector()
    outcome = conn.handle_message(
        FakeConsumer(), msg(ORDERS_TOPIC, 0, load("truncate.json")), Recorder()
    )
    assert outcome == HALTED
    assert conn.halted[ORDERS]["error_code"] == "CDC_UNSUPPORTED_OPERATION"


def test_undecodable_message_halts_its_topic():
    conn = connector()
    bad = FakeMsg(ORDERS_TOPIC, 0, b"{not json")
    assert conn.handle_message(FakeConsumer(), bad, Recorder()) == HALTED
    assert conn.halted[ORDERS_TOPIC]["error_code"] == "CDC_ENVELOPE_MALFORMED"


def test_tombstone_is_committed_and_skipped():
    conn, kafka, handler = connector(), FakeConsumer(), Recorder()
    assert conn.handle_message(kafka, msg(ORDERS_TOPIC, 4, None), handler) == SKIPPED
    assert kafka.committed == [(ORDERS_TOPIC, 4)]
    assert handler.calls == []


# ---------------------------------------------------------------------------
# Restart — the gap M7W26T3 closes by persisting state
# ---------------------------------------------------------------------------


def test_drift_halt_survives_a_restart():
    """Before M7W26T3 the baseline lived in memory: after a restart the first
    post-ALTER message became the new baseline and the table un-halted."""
    store = FakeStore()
    first = connector(store)
    first.handle_message(
        FakeConsumer(), msg(ORDERS_TOPIC, 0, load("insert.json")), Recorder()
    )
    first.handle_message(
        FakeConsumer(),
        msg(ORDERS_TOPIC, 1, load("drift_column_added.json")),
        Recorder(),
    )

    restarted = connector(store)
    restarted.restore_state()
    assert ORDERS in restarted.halted
    kafka = FakeConsumer()
    outcome = restarted.handle_message(
        kafka, msg(ORDERS_TOPIC, 1, load("drift_column_added.json")), Recorder()
    )
    assert outcome == HALTED
    assert kafka.committed == []


def test_restored_handler_halt_clears_once_it_no_longer_reproduces():
    store = FakeStore()
    store.record_halt(ORDERS, "POSTGRES_WRITE_FAILED", "warehouse was down")

    conn = connector(store)
    conn.restore_state()
    assert ORDERS in conn.halted
    assert (
        conn.handle_message(
            FakeConsumer(), msg(ORDERS_TOPIC, 0, load("insert.json")), Recorder()
        )
        == HANDLED
    )
    assert ORDERS not in conn.halted
    assert store.rows[ORDERS]["halted"] is False


# ---------------------------------------------------------------------------
# The run loop and the async subscribe() contract
# ---------------------------------------------------------------------------


def test_subscribe_consumes_until_unsubscribed():
    kafka = FakeConsumer(
        [
            msg(ORDERS_TOPIC, i, load(n))
            for i, n in enumerate(("insert.json", "update.json"))
        ]
    )
    config = StreamingConnectionConfig("unused:9092", r"^subop-postgres-cdc\..*", "grp")
    conn = KafkaCDCConnector(config, consumer_factory=lambda settings: kafka)
    kafka.on_empty = conn.stop
    handler = Recorder()

    asyncio.run(conn.subscribe(handler))

    assert kafka.subscribed_to == [r"^subop-postgres-cdc\..*"]
    assert len(handler.calls) == 2
    assert kafka.closed and conn.subscribed is False


def test_consumer_is_configured_for_manual_commits():
    captured = {}

    def factory(settings):
        captured.update(settings)
        return FakeConsumer(on_empty=conn.stop)

    config = StreamingConnectionConfig("broker:9092", "^t", "grp")
    conn = KafkaCDCConnector(config, consumer_factory=factory)
    conn.run(Recorder())
    assert captured["enable.auto.commit"] is False
    assert captured["enable.auto.offset.store"] is False
    assert captured["group.id"] == "grp"


# ---------------------------------------------------------------------------
# Latency points t0-t4 (M8W28T4, CDC Design Note Section 2)
# ---------------------------------------------------------------------------

KAFKA_TS = 1793691261830


def timed(topic, offset, envelope, kafka_ts=(1, KAFKA_TS)):
    """A message carrying a Kafka timestamp, as confluent-kafka's does."""
    message = msg(topic, offset, envelope)
    message.timestamp = lambda: kafka_ts
    return message


class FakeLatency:
    def __init__(self, fail_with: Optional[Exception] = None):
        self.records: List[tuple] = []
        self.fail_with = fail_with

    def record(self, event, lsn, points):
        if self.fail_with is not None:
            raise self.fail_with
        self.records.append((event["table"], event["op"], lsn, tuple(points)))
        return 1


class Clock:
    def __init__(self, *values):
        self.values = list(values)

    def __call__(self):
        return self.values.pop(0)


def timed_connector(latency, *clock_values, consumer_factory=None):
    config = StreamingConnectionConfig("unused:9092", r"^subop-postgres-cdc\..*", "t")
    return KafkaCDCConnector(
        config,
        latency_store=latency,
        clock=Clock(*clock_values),
        consumer_factory=consumer_factory,
    )


def test_t1_is_the_top_level_ts_ms_never_the_source_one():
    """The Design Note's named trap: source.ts_ms is t0, payload.ts_ms is t1.
    This fixture sets them 100 billion ms apart, so a swap cannot hide."""
    latency = FakeLatency()
    conn = timed_connector(latency, 1_800_000_000_200)
    envelope = load("ts_ms_source_vs_processing.json")
    message = timed(ORDERS_TOPIC, 0, envelope, (1, 1_800_000_000_004))
    result = conn.handle_message(FakeConsumer(), message, Recorder(), 1_800_000_000_100)
    assert result == HANDLED
    [(table, op, lsn, points)] = latency.records
    assert points == (
        1_700_000_000_000,  # t0 payload.source.ts_ms
        1_799_999_999_999,  # t1 payload.ts_ms
        1_800_000_000_004,  # t2 Kafka message timestamp
        1_800_000_000_100,  # t3 poll() returned
        1_800_000_000_200,  # t4 after the handler committed
    )
    assert (table, op, lsn) == (ORDERS, "insert", 26642408)


def test_t3_falls_back_to_now_when_called_directly():
    latency = FakeLatency()
    conn = timed_connector(latency, 10, 20)
    conn.handle_message(
        FakeConsumer(), timed(ORDERS_TOPIC, 0, load("insert.json")), Recorder()
    )
    assert latency.records[0][3][3:] == (10, 20)


def test_run_stamps_t3_when_poll_returns():
    latency = FakeLatency()
    kafka = FakeConsumer([timed(ORDERS_TOPIC, 0, load("update.json"))])
    conn = timed_connector(latency, 111, 222, consumer_factory=lambda settings: kafka)
    kafka.on_empty = conn.stop
    conn.run(Recorder())
    assert latency.records[0][3][3:] == (111, 222)


def test_snapshot_rows_are_not_timed():
    """Their t0 is the snapshot time, not a change's commit time."""
    latency = FakeLatency()
    conn = timed_connector(latency, 1, 2)
    result = conn.handle_message(
        FakeConsumer(), timed(ORDERS_TOPIC, 0, load("snapshot_event.json")), Recorder()
    )
    assert result == HANDLED and latency.records == []


def test_missing_kafka_timestamp_skips_the_row_but_not_the_data():
    latency = FakeLatency()
    conn, kafka = timed_connector(latency, 1, 2, 3, 4), FakeConsumer()
    plain = msg(ORDERS_TOPIC, 0, load("insert.json"))
    unavailable = timed(ORDERS_TOPIC, 1, load("update.json"), (0, -1))
    assert conn.handle_message(kafka, plain, Recorder()) == HANDLED
    assert conn.handle_message(kafka, unavailable, Recorder()) == HANDLED
    assert latency.records == []
    assert kafka.committed == [(ORDERS_TOPIC, 0), (ORDERS_TOPIC, 1)]


def test_a_failed_latency_write_never_halts_the_table():
    failure = WriteError("db busy", error_code="X", connector_type="postgresql")
    conn, kafka = timed_connector(FakeLatency(fail_with=failure), 1, 2), FakeConsumer()
    result = conn.handle_message(
        kafka, timed(ORDERS_TOPIC, 0, load("insert.json")), Recorder()
    )
    assert result == HANDLED
    assert kafka.committed == [(ORDERS_TOPIC, 0)] and conn.halted == {}


def test_an_event_that_halts_or_retries_is_not_timed():
    latency = FakeLatency()
    conn = timed_connector(latency, 1, 2)
    retry = WriteError(
        "busy", error_code="X", connector_type="postgresql", retryable=True
    )
    halt = WriteError(
        "bad row", error_code="POSTGRES_WRITE_FAILED", connector_type="postgresql"
    )
    envelope = load("insert.json")
    assert (
        conn.handle_message(
            FakeConsumer(), timed(ORDERS_TOPIC, 0, envelope), Recorder(retry)
        )
        == RETRY
    )
    assert (
        conn.handle_message(
            FakeConsumer(), timed(ORDERS_TOPIC, 0, envelope), Recorder(halt)
        )
        == HALTED
    )
    assert latency.records == []
