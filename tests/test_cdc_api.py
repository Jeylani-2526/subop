"""tests/test_cdc_api.py — M7W26T6.

The /api/cdc routes with Kafka Connect and the state store replaced through
FastAPI dependency overrides, so the response contract is checked without a
running Connect worker or database.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services" / "etl_engine"))
sys.path.insert(
    0, str(Path(__file__).resolve().parents[1] / "services" / "etl_engine" / "api")
)

from app import app  # noqa: E402
from services.cdc.api import (  # noqa: E402
    ConnectorNotFound,
    ConnectUnavailable,
    get_connect_client,
    get_state_store,
)

NAME = "subop-postgres-cdc"
ORDERS, CUSTOMERS = "cdc_demo.orders", "cdc_demo.customers"


class FakeConnect:
    def __init__(self, tasks=("RUNNING",), down=False):
        self.tasks, self.down = tasks, down

    def _check(self):
        if self.down:
            raise ConnectUnavailable("Kafka Connect unreachable at http://connect:8083")

    def connector_names(self):
        self._check()
        return [NAME]

    def status(self, name):
        self._check()
        if name != NAME:
            raise ConnectorNotFound(name)
        return {
            "connector": {"state": "RUNNING"},
            "tasks": [{"id": i, "state": s} for i, s in enumerate(self.tasks)],
        }

    def config(self, name):
        self._check()
        return {"table.include.list": f"{ORDERS},{CUSTOMERS}"}


class FakeStore:
    def __init__(self, state=None, events=None):
        self.state, self.events = state or {}, events or []

    def load(self):
        return self.state

    def recent_events(self, limit):
        return [dict(e) for e in self.events[:limit]]


HALT_TIME = datetime(2026, 11, 3, 16, 0, tzinfo=timezone.utc)
STATE = {
    ORDERS: {
        "events_processed": 21,
        "last_event_ts_ms": 1793723713533,
        "last_lsn": 27052864,
        "halted": True,
        "halt_error_code": "CDC_SCHEMA_DRIFT_DETECTED",
        "halt_reason": "cdc_demo.orders: columns added ['discount']",
        "halted_at": HALT_TIME,
    },
    CUSTOMERS: {
        "events_processed": 3,
        "last_event_ts_ms": 1793695208276,
        "last_lsn": 26622592,
    },
}


@pytest.fixture
def client():
    yield TestClient(app)
    app.dependency_overrides.clear()


def use(connect=None, store=None):
    app.dependency_overrides[get_connect_client] = lambda: connect or FakeConnect()
    app.dependency_overrides[get_state_store] = lambda: store or FakeStore()


def test_status_carries_the_fields_cdc_types_already_declare(client):
    """CDCConnectorStatus in cdcTypes.ts: nothing renamed, nothing dropped."""
    use(store=FakeStore(STATE))
    body = client.get(f"/api/cdc/connectors/{NAME}/status").json()
    for field in (
        "connector_id",
        "connector_name",
        "state",
        "last_event_ts_ms",
        "lag_ms",
    ):
        assert field in body
    assert (body["connector_id"], body["state"]) == (NAME, "RUNNING")


def test_latency_fields_are_present_and_null(client):
    """Reserved for M8, so the response shape does not change when it lands."""
    use(store=FakeStore(STATE))
    body = client.get(f"/api/cdc/connectors/{NAME}/status").json()
    assert body["lag_ms"] is None
    assert "latency" in body and body["latency"] is None


def test_status_reports_counts_and_a_table_scoped_halt(client):
    use(store=FakeStore(STATE))
    body = client.get(f"/api/cdc/connectors/{NAME}/status").json()
    assert body["events_processed"] == 24
    assert body["last_event_ts_ms"] == 1793723713533
    assert body["halted"] is True
    by_table = {t["table"]: t for t in body["tables"]}
    assert by_table[ORDERS]["halted"] is True
    assert by_table[ORDERS]["halt_error_code"] == "CDC_SCHEMA_DRIFT_DETECTED"
    assert by_table[ORDERS]["halted_at"] == HALT_TIME.isoformat()
    assert by_table[CUSTOMERS]["halted"] is False


def test_tables_follow_the_connector_include_list_even_before_any_event(client):
    use(store=FakeStore({}))
    body = client.get(f"/api/cdc/connectors/{NAME}/status").json()
    assert [t["table"] for t in body["tables"]] == [ORDERS, CUSTOMERS]
    assert body["events_processed"] == 0 and body["last_event_ts_ms"] is None


def test_a_running_connector_without_a_task_is_visible(client):
    use(connect=FakeConnect(tasks=()))
    body = client.get(f"/api/cdc/connectors/{NAME}/status").json()
    assert body["state"] == "RUNNING" and body["task_state"] is None


def test_list_uses_the_architecture_path(client):
    use(store=FakeStore(STATE))
    response = client.get("/api/cdc/connectors")
    assert response.status_code == 200
    assert [c["connector_id"] for c in response.json()] == [NAME]


def test_unknown_connector_is_404_in_the_error_envelope(client):
    use()
    response = client.get("/api/cdc/connectors/nope/status")
    assert response.status_code == 404
    assert response.json() == {
        "error_code": "CDC_CONNECTOR_NOT_FOUND",
        "message": "No such CDC connector.",
        "connector_type": "streaming",
        "retryable": False,
    }


def test_connect_down_is_503_not_a_guessed_state(client):
    use(connect=FakeConnect(down=True))
    for path in ("/api/cdc/connectors", f"/api/cdc/connectors/{NAME}/status"):
        response = client.get(path)
        assert response.status_code == 503
        body = response.json()
        assert (
            body["error_code"] == "CDC_CONNECT_UNAVAILABLE"
            and body["retryable"] is True
        )


def test_events_feed_matches_cdc_change_event(client):
    events = [
        {
            "op": "delete",
            "table": ORDERS,
            "before": {"id": 7},
            "after": None,
            "ts_ms": 3,
        },
        {
            "op": "update",
            "table": ORDERS,
            "before": {"id": 7},
            "after": {"id": 7},
            "ts_ms": 2,
        },
    ]
    use(store=FakeStore(events=events))
    body = client.get("/api/cdc/events").json()
    assert [e["op"] for e in body] == ["delete", "update"]
    for event in body:
        assert set(event) == {"op", "table", "before", "after", "ts_ms", "latency_ms"}
        assert event["latency_ms"] is None


def test_events_limit_is_bounded(client):
    use()
    assert client.get("/api/cdc/events?limit=0").status_code == 422
    assert client.get("/api/cdc/events?limit=501").status_code == 422


# ---------------------------------------------------------------------------
# Fields CDCPage.tsx already reads — M7W26T7 shipped before the contract
# ---------------------------------------------------------------------------


def test_beyza_fields_report_a_drift_halt(client):
    use(store=FakeStore(STATE))
    body = client.get(f"/api/cdc/connectors/{NAME}/status").json()
    assert body["halted_tables"] == [ORDERS]
    assert body["drift_state"] == "CDC_SCHEMA_DRIFT_DETECTED"


def test_beyza_fields_when_nothing_is_halted(client):
    use(store=FakeStore({}))
    body = client.get(f"/api/cdc/connectors/{NAME}/status").json()
    assert body["halted_tables"] == []
    assert body["drift_state"] == "none"


def test_a_non_drift_halt_is_listed_but_not_called_drift(client):
    truncated = {
        ORDERS: {"halted": True, "halt_error_code": "CDC_UNSUPPORTED_OPERATION"}
    }
    use(store=FakeStore(truncated))
    body = client.get(f"/api/cdc/connectors/{NAME}/status").json()
    assert body["halted_tables"] == [ORDERS]
    assert body["drift_state"] == "none"
