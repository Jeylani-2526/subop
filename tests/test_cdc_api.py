"""tests/test_cdc_api.py — M7W26T6; latency fields M8W28T4.

The /api/cdc routes with Kafka Connect and the state store replaced through
FastAPI dependency overrides, so the response contract is checked without a
running Connect worker or database.
"""

from __future__ import annotations

import copy
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
    get_latency_store,
    get_state_store,
)
from services.cdc.latency_store import row_key  # noqa: E402

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

    def recent_events(self, limit, with_keys=False):
        events = []
        for i, e in enumerate(self.events[:limit]):
            event = {k: v for k, v in e.items() if k != "lsn"}
            if with_keys:
                event["lsn"], event["row_key"] = e.get("lsn", 100 + i), row_key(e)
            events.append(event)
        return events


class FakeLatency:
    def __init__(self, summary=None, e2e=None):
        self._summary, self._e2e = summary, e2e or {}
        self.asked_for = []

    def summary(self, tables=None):
        self.asked_for.append(tables)
        return copy.deepcopy(self._summary)

    def e2e_by_key(self, keys):
        return {k: self._e2e[k] for k in keys if k in self._e2e}


def _stat(median, p95, maximum):
    return {"median_ms": median, "p95_ms": p95, "max_ms": maximum}


LATENCY = {
    "window_size": 100,
    "sample_size": 42,
    "lag_ms": 812,
    "e2e": _stat(734.5, 1904.85, 2311),
    "capture": _stat(401, 1450.2, 1702),
    "publish": _stat(12, 31.95, 44),
    "consumer": _stat(288.5, 402.9, 517),
    "warehouse": _stat(9, 21, 38),
}


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


def use(connect=None, store=None, latency=None):
    app.dependency_overrides[get_connect_client] = lambda: connect or FakeConnect()
    app.dependency_overrides[get_state_store] = lambda: store or FakeStore()
    app.dependency_overrides[get_latency_store] = lambda: latency or FakeLatency()


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


def test_latency_is_null_until_an_event_is_measured(client):
    """Contract Section 9.3: null, not zero, while nothing has been measured."""
    use(store=FakeStore(STATE))
    body = client.get(f"/api/cdc/connectors/{NAME}/status").json()
    assert body["lag_ms"] is None
    assert "latency" in body and body["latency"] is None


def test_latency_follows_the_contract_shape(client):
    """Contract Section 9.2: five hops, lag_ms beside them, not inside."""
    latency = FakeLatency(LATENCY)
    use(store=FakeStore(STATE), latency=latency)
    body = client.get(f"/api/cdc/connectors/{NAME}/status").json()
    expected = {k: v for k, v in LATENCY.items() if k != "lag_ms"}
    assert body["latency"] == expected
    assert body["lag_ms"] == 812
    assert set(body["latency"]) == {
        "window_size",
        "sample_size",
        "e2e",
        "capture",
        "publish",
        "consumer",
        "warehouse",
    }


def test_latency_covers_only_the_connector_tables(client):
    latency = FakeLatency(LATENCY)
    use(store=FakeStore(STATE), latency=latency)
    client.get(f"/api/cdc/connectors/{NAME}/status")
    assert latency.asked_for == [[ORDERS, CUSTOMERS]]


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


def test_connect_down_with_nothing_stored_is_still_503(client):
    """M8W28T5 keeps the 503 when there is no stored state to fall back on."""
    use(connect=FakeConnect(down=True))
    for path in ("/api/cdc/connectors", f"/api/cdc/connectors/{NAME}/status"):
        response = client.get(path)
        assert response.status_code == 503
        body = response.json()
        assert (
            body["error_code"] == "CDC_CONNECT_UNAVAILABLE"
            and body["retryable"] is True
        )


def test_connect_down_keeps_the_last_known_halt_visible(client):
    """M8W28T5: the halt in cdc_meta outlives a Connect outage."""
    use(connect=FakeConnect(down=True), store=FakeStore(STATE))
    response = client.get(f"/api/cdc/connectors/{NAME}/status")
    assert response.status_code == 200
    body = response.json()
    assert (body["state"], body["task_state"], body["connect_reachable"]) == (
        "UNKNOWN",
        None,
        False,
    )
    assert body["halted"] is True
    assert body["halted_tables"] == [ORDERS]
    assert body["drift_state"] == "CDC_SCHEMA_DRIFT_DETECTED"
    orders = next(t for t in body["tables"] if t["table"] == ORDERS)
    assert orders["halted_at"] == HALT_TIME.isoformat()
    assert {t["table"] for t in body["tables"]} == {ORDERS, CUSTOMERS}


def test_connect_down_list_uses_the_configured_connector_names(client, monkeypatch):
    monkeypatch.setenv("CDC_CONNECTOR_NAMES", f"{NAME}, other-cdc")
    use(connect=FakeConnect(down=True), store=FakeStore(STATE))
    body = client.get("/api/cdc/connectors").json()
    assert [c["connector_id"] for c in body] == [NAME, "other-cdc"]
    assert all(c["state"] == "UNKNOWN" and not c["connect_reachable"] for c in body)


def test_connect_down_list_defaults_to_the_demo_connector(client, monkeypatch):
    monkeypatch.delenv("CDC_CONNECTOR_NAMES", raising=False)
    use(connect=FakeConnect(down=True), store=FakeStore(STATE))
    body = client.get("/api/cdc/connectors").json()
    assert [c["connector_id"] for c in body] == [NAME]


def test_connect_down_cannot_confirm_an_unknown_connector(client):
    use(connect=FakeConnect(down=True), store=FakeStore(STATE))
    response = client.get("/api/cdc/connectors/nobody/status")
    assert response.status_code == 503
    assert response.json()["error_code"] == "CDC_CONNECT_UNAVAILABLE"


def test_connect_down_still_reports_latency(client):
    latency = FakeLatency(LATENCY)
    use(connect=FakeConnect(down=True), store=FakeStore(STATE), latency=latency)
    body = client.get(f"/api/cdc/connectors/{NAME}/status").json()
    assert body["lag_ms"] == 812 and body["latency"]["sample_size"] == 42
    assert latency.asked_for == [sorted([ORDERS, CUSTOMERS])]


def test_live_status_says_connect_is_reachable(client):
    use(store=FakeStore(STATE))
    body = client.get(f"/api/cdc/connectors/{NAME}/status").json()
    assert body["connect_reachable"] is True and body["state"] == "RUNNING"


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


def test_events_carry_their_own_latency(client):
    """latency_ms is that event's t4 - t0; an event from before M8 stays null."""
    events = [
        {
            "op": "update",
            "table": ORDERS,
            "before": None,
            "after": {"id": 7},
            "ts_ms": 2,
            "lsn": 501,
        },
        {
            "op": "insert",
            "table": ORDERS,
            "before": None,
            "after": {"id": 7},
            "ts_ms": 1,
            "lsn": 500,
        },
    ]
    latency = FakeLatency(e2e={(ORDERS, 501, "update", "7"): 812})
    use(store=FakeStore(events=events), latency=latency)
    body = client.get("/api/cdc/events").json()
    assert [e["latency_ms"] for e in body] == [812, None]
    assert all("lsn" not in e and "row_key" not in e for e in body)


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
