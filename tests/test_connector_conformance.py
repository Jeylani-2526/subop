"""
tests/test_connector_conformance.py — M6W20T2.

Shared-interface conformance suite: connect() / execute_query() /
health_check() / disconnect(), plus the shared ConnectorError
hierarchy on an induced failure, run against all 7 connectors wired
via M6W20T1. Oracle (8th) is added in M6W20T3.

Doesn't replace the per-connector suites (test_postgres_connector.py
etc.), which still own connector-specific behavior.

postgresql/mysql/mssql need a live server (`docker compose up -d
postgres mysql mssql`) — no graceful skip if unreachable.

Known gap (not fixed here, confirmed with Abdullah): postgres_
connector.py's execute_query() has no "not connected" guard, unlike
every other connector — raises a bare AttributeError instead of
ConnectorError. test_execute_query_before_connect_raises_connector_
error is expected to fail for postgresql; left red deliberately.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Callable, Dict

import httpx
import pytest

from services.connectors.errors import ConnectorError
from services.connectors.postgres_connector import (
    ConnectionConfig as PostgresConfig,
    PostgresConnector,
)
from services.connectors.mysql_connector import (
    ConnectionConfig as MySQLConfig,
    MySQLConnector,
)
from services.connectors.mssql_connector import (
    ConnectionConfig as MSSQLConfig,
    MSSQLConnector,
)
from services.connectors.sqlite_connector import (
    ConnectionConfig as SQLiteConfig,
    SQLiteConnector,
)
from services.connectors.csv_connector import CSVConnector
from services.connectors.json_connector import JSONConnector
from services.connectors.file_connector_base import FileConnectionConfig
from services.connectors.rest_api_connector import (
    ConnectionConfig as RestApiConfig,
    RESTAPIConnector,
)

# Each builder returns (connector, query_kwargs, configure).
# query_kwargs: db-kind connectors need a real `sql` string; file/url-kind
# don't. configure: post-connect hook (only rest_api uses it, to swap in
# a mock HTTP transport).


def _noop(_connector: Any) -> None:
    pass


def _mock_rest_transport(connector: Any) -> None:
    """Swap in a mock HTTP transport so tests don't hit the network."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[{"id": 1, "name": "Ali"}])

    connector.client = httpx.Client(
        base_url=connector.config.base_url,
        transport=httpx.MockTransport(handler),
    )


def _build_postgresql(tmp_path):
    config = PostgresConfig(
        host=os.getenv("POSTGRES_HOST", "127.0.0.1"),
        port=int(os.getenv("POSTGRES_PORT", 5433)),
        database=os.getenv("POSTGRES_DB", "subop"),
        username=os.getenv("POSTGRES_USER", "subop"),
        password=os.getenv("POSTGRES_PASSWORD", "subop_dev"),
    )
    return PostgresConnector(config), {"sql": "SELECT 1 AS health"}, _noop


def _build_mysql(tmp_path):
    config = MySQLConfig(
        host=os.getenv("MYSQL_HOST", "localhost"),
        port=int(os.getenv("MYSQL_PORT", 3306)),
        database=os.getenv("MYSQL_DATABASE", "subop"),
        username=os.getenv("MYSQL_USER", "subop_app"),
        password=os.getenv("MYSQL_PASSWORD", "mysql_dev"),
    )
    return MySQLConnector(config), {"sql": "SELECT 1 AS health"}, _noop


def _build_mssql(tmp_path):
    config = MSSQLConfig(
        host=os.getenv("MSSQL_HOST", "localhost"),
        port=int(os.getenv("MSSQL_PORT", 1433)),
        database=os.getenv("MSSQL_DATABASE", "master"),
        username=os.getenv("MSSQL_USERNAME", "sa"),
        password=os.getenv("MSSQL_SA_PASSWORD", "SubopDev123!"),
    )
    return MSSQLConnector(config), {"sql": "SELECT 1 AS health"}, _noop


def _build_sqlite(tmp_path):
    db_path = tmp_path / "conformance.db"
    config = SQLiteConfig(str(db_path))
    return SQLiteConnector(config), {"sql": "SELECT 1 AS health"}, _noop


def _build_csv(tmp_path):
    csv_path = tmp_path / "conformance.csv"
    csv_path.write_text("id,name\n1,Ali\n", encoding="utf-8")
    config = FileConnectionConfig(csv_path)
    return CSVConnector(config), {}, _noop


def _build_json(tmp_path):
    json_path = tmp_path / "conformance.json"
    json_path.write_text('[{"id": 1, "name": "Ali"}]', encoding="utf-8")
    config = FileConnectionConfig(json_path)
    return JSONConnector(config), {}, _noop


def _build_rest_api(tmp_path):
    config = RestApiConfig("https://example.com")
    return RESTAPIConnector(config), {}, _mock_rest_transport


_BUILDERS: Dict[str, Callable[[Any], Any]] = {
    "postgresql": _build_postgresql,
    "mysql": _build_mysql,
    "mssql": _build_mssql,
    "sqlite": _build_sqlite,
    "csv": _build_csv,
    "json": _build_json,
    "rest_api": _build_rest_api,
}

CONNECTOR_TYPES = list(_BUILDERS)  # 7 for T2, Oracle added in T3


@dataclass
class ConformanceCase:
    connector_type: str
    connector: Any
    query_kwargs: Dict[str, Any]
    configure: Callable[[Any], None]


@pytest.fixture(params=CONNECTOR_TYPES)
def case(request, tmp_path) -> ConformanceCase:
    connector_type = request.param
    connector, query_kwargs, configure = _BUILDERS[connector_type](tmp_path)
    yield ConformanceCase(connector_type, connector, query_kwargs, configure)
    connector.disconnect()  # safe even if never connected


# ---------------------------------------------------------------------------
# Shared contract — happy path
# ---------------------------------------------------------------------------


def test_connect_succeeds(case: ConformanceCase):
    """connect() completes without raising for a valid configuration."""
    case.connector.connect()
    case.configure(case.connector)


def test_execute_query_returns_list_of_dicts(case: ConformanceCase):
    """execute_query() returns List[Dict] for every connector."""
    case.connector.connect()
    case.configure(case.connector)
    rows = case.connector.execute_query(**case.query_kwargs)
    assert isinstance(rows, list)
    assert len(rows) >= 1
    assert all(isinstance(row, dict) for row in rows)


def test_health_check_true_when_connected(case: ConformanceCase):
    case.connector.connect()
    case.configure(case.connector)
    assert case.connector.health_check() is True


def test_disconnect_does_not_raise(case: ConformanceCase):
    case.connector.connect()
    case.configure(case.connector)
    case.connector.disconnect()  # must not raise


# ---------------------------------------------------------------------------
# Shared contract — deliberately induced failure
# ---------------------------------------------------------------------------


def test_execute_query_before_connect_raises_connector_error(case: ConformanceCase):
    """Induced failure: execute_query() before connect() must raise
    ConnectorError, not a raw exception. Expected to fail for postgresql."""
    with pytest.raises(ConnectorError) as exc_info:
        case.connector.execute_query(**case.query_kwargs)

    err = exc_info.value
    envelope = err.to_envelope()
    assert isinstance(envelope["error_code"], str) and envelope["error_code"]
    assert isinstance(envelope["message"], str) and envelope["message"]
    assert isinstance(envelope["retryable"], bool)
    assert envelope["connector_type"] == case.connector_type
