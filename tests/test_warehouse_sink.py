"""tests/test_warehouse_sink.py — M7W26T4.

The idempotency claim lives in SQL, so it is tested against a real PostgreSQL
through the Abstraction Layer, not a mock. Each test gets its own schema.
"""

from __future__ import annotations

import copy
import json
import uuid
from pathlib import Path

import pytest

from services.abstraction.abstraction_layer import AbstractionLayer
from services.cdc.kafka_consumer import HANDLED, KafkaCDCConnector
from services.cdc.normalizer import normalize
from services.cdc.warehouse_sink import WarehouseSink
from services.connectors.errors import WriteError
from services.connectors.streaming_connector_base import StreamingConnectionConfig

FIXTURES = Path(__file__).parent / "fixtures" / "cdc"


def envelope(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def event_and_meta(name):
    env = envelope(name)
    return normalize(env), {"lsn": env["payload"]["source"]["lsn"]}


@pytest.fixture
def layer(test_db_connection):
    return AbstractionLayer(connector=test_db_connection, database="postgresql")


@pytest.fixture
def sink(layer):
    schema = f"test_wh_{uuid.uuid4().hex[:8]}"
    warehouse = WarehouseSink(layer, schema=schema)
    warehouse.ensure_schema()
    yield warehouse
    layer.execute_write(f"DROP SCHEMA {schema} CASCADE")


def rows(layer, sink, table="orders"):
    return layer.execute_query(
        f"SELECT id, status, amount, _cdc_lsn, _cdc_op, _cdc_deleted "
        f"FROM {sink.schema}.{table} ORDER BY id"
    )


def test_ensure_schema_is_idempotent(sink):
    sink.ensure_schema()


def test_insert_lands_as_a_warehouse_row(layer, sink):
    event, meta = event_and_meta("insert.json")
    assert sink.apply(event, meta) == 1
    (row,) = rows(layer, sink)
    assert row["id"] == event["after"]["id"]
    assert str(row["amount"]) == event["after"]["amount"]
    assert (row["_cdc_lsn"], row["_cdc_op"], row["_cdc_deleted"]) == (
        meta["lsn"],
        "insert",
        False,
    )


def test_redelivery_changes_nothing(layer, sink):
    """At-least-once delivery: the same event twice must not corrupt the row."""
    event, meta = event_and_meta("update.json")
    assert sink.apply(event, meta) == 1
    before = rows(layer, sink)
    assert sink.apply(event, meta) == 0
    assert rows(layer, sink) == before


def test_full_sequence_applies_in_order(layer, sink):
    for name in ("insert.json", "update.json"):
        sink.apply(*event_and_meta(name))
    (row,) = rows(layer, sink)
    assert row["status"] == "shipped"
    assert row["_cdc_op"] == "update"


def test_stale_change_is_ignored(layer, sink):
    """An older LSN arriving after a newer one — e.g. a rewound offset."""
    sink.apply(*event_and_meta("update.json"))
    assert sink.apply(*event_and_meta("insert.json")) == 0
    assert rows(layer, sink)[0]["status"] == "shipped"


def test_delete_is_soft(layer, sink):
    for name in ("insert.json", "update.json", "delete.json"):
        sink.apply(*event_and_meta(name))
    (row,) = rows(layer, sink)
    assert row["_cdc_deleted"] is True
    assert row["_cdc_op"] == "delete"
    assert row["status"] == "shipped", "keeps the last known values from before"


def test_replay_after_delete_does_not_resurrect(layer, sink):
    """The reason deletes are soft: the delete's LSN stays on the row."""
    for name in ("insert.json", "update.json", "delete.json"):
        sink.apply(*event_and_meta(name))
    assert sink.apply(*event_and_meta("update.json")) == 0
    assert rows(layer, sink)[0]["_cdc_deleted"] is True


def test_reinsert_after_delete_undeletes(layer, sink):
    sink.apply(*event_and_meta("delete.json"))
    event, meta = event_and_meta("insert.json")
    meta = {"lsn": meta["lsn"] + 10_000_000}
    assert sink.apply(event, meta) == 1
    assert rows(layer, sink)[0]["_cdc_deleted"] is False


def test_snapshot_rows_are_applied(layer, sink):
    event, meta = event_and_meta("snapshot_event.json")
    assert event["op"] == "snapshot"
    assert sink.apply(event, meta) == 1
    assert rows(layer, sink)[0]["_cdc_op"] == "snapshot"


def test_second_table_lands_in_its_own_warehouse_table(layer, sink):
    event = {
        "op": "insert",
        "table": "cdc_demo.customers",
        "before": None,
        "after": {
            "id": 1001,
            "name": "Ayse Yilmaz",
            "city": "Istanbul",
            "created_at": "2026-11-03T08:00:00Z",
            "updated_at": "2026-11-03T08:00:00Z",
        },
        "ts_ms": 1_793_691_261_547,
    }
    assert sink.apply(event, {"lsn": 1}) == 1
    (row,) = layer.execute_query(f"SELECT name, city FROM {sink.schema}.customers")
    assert (row["name"], row["city"]) == ("Ayse Yilmaz", "Istanbul")


@pytest.mark.parametrize(
    "mutate, code",
    [
        (lambda e, m: e.update(table="cdc_demo.unmapped"), "CDC_TABLE_NOT_MAPPED"),
        (lambda e, m: m.update(lsn=None), "CDC_LSN_MISSING"),
        (lambda e, m: e.update(after=None), "CDC_ROW_MISSING"),
        (lambda e, m: e["after"].pop("status"), "CDC_ROW_INCOMPLETE"),
    ],
)
def test_unsafe_events_are_rejected_not_guessed(sink, mutate, code):
    event, meta = event_and_meta("insert.json")
    event = copy.deepcopy(event)
    mutate(event, meta)
    with pytest.raises(WriteError) as excinfo:
        sink.apply(event, meta)
    assert excinfo.value.error_code == code
    assert excinfo.value.retryable is False


# ---------------------------------------------------------------------------
# Through the consumer — the path the Week 27 end-to-end run exercises live
# ---------------------------------------------------------------------------


class _Msg:
    def __init__(self, topic, offset, env):
        self._t, self._o, self._v = topic, offset, json.dumps(env).encode()

    def topic(self):
        return self._t

    def partition(self):
        return 0

    def offset(self):
        return self._o

    def value(self):
        return self._v

    def error(self):
        return None


class _Kafka:
    def __init__(self):
        self.committed = []

    def commit(self, message, asynchronous):
        self.committed.append(message.offset())

    def pause(self, partitions):
        pass


def test_consumer_delivers_real_envelopes_into_the_warehouse(layer, sink):
    config = StreamingConnectionConfig("unused:9092", "^t", "grp")
    conn, kafka = KafkaCDCConnector(config), _Kafka()
    topic = "subop-postgres-cdc.cdc_demo.orders"
    names = ("snapshot_event.json", "insert.json", "update.json", "delete.json")
    for offset, name in enumerate(names):
        assert (
            conn.handle_message(kafka, _Msg(topic, offset, envelope(name)), sink)
            == HANDLED
        )
    assert kafka.committed == [0, 1, 2, 3]

    by_id = {row["id"]: row for row in rows(layer, sink)}
    assert by_id[1]["_cdc_op"] == "snapshot"
    assert by_id[4]["_cdc_deleted"] is True
