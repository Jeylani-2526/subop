"""CDC status endpoints, base /api/cdc (M7W26T6).

Paths follow Architecture Section 6, Module 4. GET /events is an addition the
dashboard's event feed needs; see docs/planning/cdc_api_contract.md.

Connector state is read live from Kafka Connect's REST API; per-table counts,
halts and the event feed come from cdc_meta, written by the consumer.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Callable, Dict, Iterator, List, Optional

import httpx
from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from services.cdc.state_store import CDCStateStore
from services.connectors.errors import ConnectorError

router = APIRouter(prefix="/api/cdc", tags=["cdc"])

_CONNECT_TIMEOUT_SECONDS = 3.0
_DRIFT = "CDC_SCHEMA_DRIFT_DETECTED"


def _error(
    status: int, code: str, message: str, retryable: bool = False
) -> JSONResponse:
    # Same four-field envelope as the pipeline routes (API spec Section 5).
    return JSONResponse(
        status_code=status,
        content={
            "error_code": code,
            "message": message,
            "connector_type": "streaming",
            "retryable": retryable,
        },
    )


class ConnectUnavailable(Exception):
    pass


class ConnectorNotFound(Exception):
    pass


class ConnectClient:
    """Thin read-only client for the Kafka Connect REST API."""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def _get(self, path: str) -> Any:
        try:
            response = httpx.get(
                f"{self.base_url}{path}", timeout=_CONNECT_TIMEOUT_SECONDS
            )
        except httpx.HTTPError as exc:
            raise ConnectUnavailable(
                f"Kafka Connect unreachable at {self.base_url}: {exc}"
            )
        if response.status_code == 404:
            raise ConnectorNotFound(path)
        if response.status_code >= 400:
            raise ConnectUnavailable(
                f"Kafka Connect returned {response.status_code} for {path}"
            )
        return response.json()

    def connector_names(self) -> List[str]:
        return list(self._get("/connectors"))

    def status(self, name: str) -> Dict[str, Any]:
        return self._get(f"/connectors/{name}/status")

    def config(self, name: str) -> Dict[str, Any]:
        return self._get(f"/connectors/{name}/config")


def get_connect_client() -> ConnectClient:
    return ConnectClient(os.environ.get("KAFKA_CONNECT_URL", "http://localhost:8083"))


def get_state_store() -> Iterator[CDCStateStore]:
    from services.etl_engine.connection_resolver import (
        release_connection,
        resolve_connection,
    )

    layer, _ = resolve_connection(
        "postgresql", os.environ.get("CDC_STATE_REF", "dw-main")
    )
    try:
        store = CDCStateStore(layer)
        # Idempotent; lets the endpoints answer before the consumer's first run.
        store.ensure_schema()
        yield store
    finally:
        release_connection(layer)


# -- response building ------------------------------------------------------


def _iso(value: Any) -> Optional[str]:
    return value.isoformat() if isinstance(value, datetime) else value


def _table_entry(table: str, row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "table": table,
        "events_processed": row.get("events_processed", 0),
        "last_event_ts_ms": row.get("last_event_ts_ms"),
        "last_lsn": row.get("last_lsn"),
        "halted": bool(row.get("halted")),
        "halt_error_code": row.get("halt_error_code"),
        "halt_reason": row.get("halt_reason"),
        "halted_at": _iso(row.get("halted_at")),
    }


def _connector_status(
    name: str, connect: ConnectClient, state: Dict[str, Dict[str, Any]]
) -> Dict[str, Any]:
    status = connect.status(name)
    config = connect.config(name)
    include = [
        t.strip() for t in config.get("table.include.list", "").split(",") if t.strip()
    ]
    tables = [_table_entry(t, state.get(t, {})) for t in include]
    task_states = [task.get("state") for task in status.get("tasks", [])]
    timestamps = [
        t["last_event_ts_ms"] for t in tables if t["last_event_ts_ms"] is not None
    ]
    return {
        "connector_id": name,
        "connector_name": name,
        "state": status.get("connector", {}).get("state"),
        # A RUNNING connector with no task reads nothing (M7W26T1 Finding 5).
        "task_state": task_states[0] if task_states else None,
        "last_event_ts_ms": max(timestamps) if timestamps else None,
        "events_processed": sum(t["events_processed"] for t in tables),
        "halted": any(t["halted"] for t in tables),
        "tables": tables,
        # The two fields CDCPage.tsx already reads (M7W26T7, committed before
        # this contract existed), derived so its merged UI works unchanged.
        # halted_tables lists every halt; drift_state reports drift only, so a
        # TRUNCATE or write-failure halt is not labelled as drift.
        "halted_tables": [t["table"] for t in tables if t["halted"]],
        "drift_state": (
            _DRIFT
            if any(t["halt_error_code"] == _DRIFT for t in tables if t["halted"])
            else "none"
        ),
        # Reserved for the M8 latency instrumentation (CDC Design Note
        # Section 2). Present and null, so the shape does not change then.
        "lag_ms": None,
        "latency": None,
    }


def _guarded(build: Callable[[], Any]) -> Any:
    try:
        return build()
    except ConnectUnavailable as exc:
        return _error(503, "CDC_CONNECT_UNAVAILABLE", str(exc), retryable=True)
    except ConnectorNotFound:
        return _error(404, "CDC_CONNECTOR_NOT_FOUND", "No such CDC connector.")
    except ConnectorError as exc:
        return _error(503, exc.error_code, exc.message, retryable=exc.retryable)


# -- routes -----------------------------------------------------------------


@router.get("/connectors")
def list_connectors(
    connect: ConnectClient = Depends(get_connect_client),
    store: CDCStateStore = Depends(get_state_store),
):
    def build():
        state = store.load()
        return [_connector_status(n, connect, state) for n in connect.connector_names()]

    return _guarded(build)


@router.get("/connectors/{connector_id}/status")
def connector_status(
    connector_id: str,
    connect: ConnectClient = Depends(get_connect_client),
    store: CDCStateStore = Depends(get_state_store),
):
    return _guarded(lambda: _connector_status(connector_id, connect, store.load()))


@router.get("/events")
def recent_events(
    limit: int = Query(50, ge=1, le=500),
    store: CDCStateStore = Depends(get_state_store),
):
    def build():
        events = store.recent_events(limit)
        for event in events:
            event["latency_ms"] = None  # M8, as above
        return events

    return _guarded(build)
