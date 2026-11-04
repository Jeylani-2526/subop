"""tests/test_cdc_state_store.py — M7W26T3.

Runs CDCStateStore's SQL against a real PostgreSQL through the Abstraction
Layer. Needs only an ordinary database, not logical replication, so it runs
against CI's postgres:15 service like the other connector tests.
"""

from __future__ import annotations

import uuid

import pytest

from services.abstraction.abstraction_layer import AbstractionLayer
from services.cdc.state_store import EVENT_LOG, TABLE, CDCStateStore

SNAPSHOT = {"id": "INT8", "status": "VARCHAR(32)"}


@pytest.fixture
def store(test_db_connection):
    layer = AbstractionLayer(connector=test_db_connection, database="postgresql")
    state = CDCStateStore(layer)
    state.ensure_schema()
    yield state
    layer.execute_write(f"DELETE FROM {TABLE} WHERE table_name LIKE 'test_%%'")
    layer.execute_write(f"DELETE FROM {EVENT_LOG} WHERE table_name LIKE 'test_%%'")


@pytest.fixture
def table():
    return f"test_{uuid.uuid4().hex[:8]}.orders"


def test_ensure_schema_is_idempotent(store):
    store.ensure_schema()
    store.ensure_schema()


def test_baseline_round_trips_as_a_dict(store, table):
    store.save_baseline(table, SNAPSHOT)
    assert store.load()[table]["baseline"] == SNAPSHOT


def test_events_accumulate_and_keep_the_latest_position(store, table):
    store.record_event(table, 1_000, 26642408)
    store.record_event(table, 2_000, 26643072)
    row = store.load()[table]
    assert row["events_processed"] == 2
    assert (row["last_event_ts_ms"], row["last_lsn"]) == (2_000, 26643072)


def test_event_without_lsn_keeps_the_previous_one(store, table):
    store.record_event(table, 1_000, 26642408)
    store.record_event(table, 2_000, None)
    assert store.load()[table]["last_lsn"] == 26642408


def test_halt_keeps_the_first_halt_time(store, table):
    """A restart redelivers the halting message and halts again; that is the
    same incident, so halted_at must not move."""
    store.record_halt(table, "CDC_SCHEMA_DRIFT_DETECTED", "columns added ['discount']")
    first = store.load()[table]["halted_at"]
    store.record_halt(table, "CDC_SCHEMA_DRIFT_DETECTED", "columns added ['discount']")
    row = store.load()[table]
    assert row["halted"] is True and row["halted_at"] == first


def test_halt_does_not_disturb_the_baseline(store, table):
    store.save_baseline(table, SNAPSHOT)
    store.record_halt(table, "CDC_SCHEMA_DRIFT_DETECTED", "x")
    assert store.load()[table]["baseline"] == SNAPSHOT


def test_clear_halt_keeps_the_baseline(store, table):
    store.save_baseline(table, SNAPSHOT)
    store.record_halt(table, "POSTGRES_WRITE_FAILED", "x")
    store.clear_halt(table)
    row = store.load()[table]
    assert row["halted"] is False and row["halted_at"] is None
    assert row["baseline"] == SNAPSHOT


def test_reset_clears_both_halt_and_baseline(store, table):
    store.save_baseline(table, SNAPSHOT)
    store.record_halt(table, "CDC_SCHEMA_DRIFT_DETECTED", "x")
    store.reset(table)
    row = store.load()[table]
    assert row["halted"] is False and row["baseline"] is None


# ---------------------------------------------------------------------------
# Event log — M7W26T6, the history behind GET /api/cdc/events
# ---------------------------------------------------------------------------


def _event(table, op, row_id, ts_ms):
    row = {"id": row_id, "status": "shipped"}
    return {
        "table": table,
        "op": op,
        "before": None if op in ("insert", "snapshot") else row,
        "after": None if op == "delete" else row,
        "ts_ms": ts_ms,
    }


def _mine(store, table):
    return [e for e in store.recent_events(500) if e["table"] == table]


def test_events_come_back_newest_first(store, table):
    store.append_event(_event(table, "insert", 7, 1), 100)
    store.append_event(_event(table, "update", 7, 2), 200)
    store.append_event(_event(table, "delete", 7, 3), 300)
    assert [e["op"] for e in _mine(store, table)] == ["delete", "update", "insert"]


def test_redelivered_event_is_logged_once(store, table):
    store.append_event(_event(table, "update", 7, 2), 200)
    store.append_event(_event(table, "update", 7, 2), 200)
    assert len(_mine(store, table)) == 1


def test_snapshot_rows_sharing_one_lsn_are_all_kept(store, table):
    """Every row of Debezium's initial snapshot carries the same LSN."""
    for row_id in (1, 2, 3):
        store.append_event(_event(table, "snapshot", row_id, 1), 100)
    assert len(_mine(store, table)) == 3


def test_row_images_round_trip_as_dicts(store, table):
    store.append_event(_event(table, "update", 7, 2), 200)
    (event,) = _mine(store, table)
    assert event["after"] == {"id": 7, "status": "shipped"}
    assert set(event) == {"op", "table", "before", "after", "ts_ms"}


def test_event_without_lsn_is_not_logged(store, table):
    store.append_event(_event(table, "insert", 7, 1), None)
    assert _mine(store, table) == []
