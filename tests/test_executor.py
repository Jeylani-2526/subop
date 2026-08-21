"""Tests for the ETL Engine executor (M5W15T3)."""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(
    0, str(Path(__file__).resolve().parents[1] / "services" / "etl_engine")
)

import run_store  # noqa: E402
from services.abstraction.abstraction_layer import (
    AbstractionLayer,
)  # noqa: E402
from services.connectors.errors import QueryError  # noqa: E402
from pipeline import parse_pipeline  # noqa: E402
import executor  # noqa: E402
import connection_resolver  # noqa: E402

# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakeConnector:
    """Minimal ConnectorBase-compatible fake, mirrors test_abstraction_layer.py."""

    def __init__(self, rows=None, fail_on_query=False, fail_on_write=False):
        self.rows = rows or []
        self.fail_on_query = fail_on_query
        self.fail_on_write = fail_on_write
        self.written_rows: List[Any] = []
        self.disconnected = False

    def execute_query(self, sql, params=None):
        if self.fail_on_query:
            raise QueryError(
                "simulated query failure",
                error_code="FAKE_QUERY_FAILED",
                connector_type="postgresql",
                retryable=False,
            )
        return self.rows

    def execute_write(self, sql, params=None):
        if self.fail_on_write:
            raise QueryError(
                "simulated write failure",
                error_code="FAKE_WRITE_FAILED",
                connector_type="postgresql",
                retryable=False,
            )
        self.written_rows.append(params)
        return 1

    def health_check(self):
        return True

    def disconnect(self):
        self.disconnected = True


def _valid_doc(transformations=None):
    return {
        "name": "customers-to-warehouse",
        "source": {
            "connector_type": "postgresql",
            "connection_ref": "app-db",
            "object": "customers",
            "query": None,
        },
        "transformations": transformations or [],
        "target": {
            "connector_type": "postgresql",
            "connection_ref": "warehouse",
            "object": "dim_customers",
            "write_mode": "append",
        },
        "processing_purpose": "customer analytics",
        "data_subject_categories": ["customer_pii"],
        "transfer_recipients": [],
    }


@pytest.fixture(autouse=True)
def reset_state():
    run_store.clear_runs()
    yield
    run_store.clear_runs()


@pytest.fixture
def patch_resolver(monkeypatch):
    """
    Patch connection_resolver.resolve_connection so tests never touch
    real env vars or real drivers — returns a FakeConnector-backed
    AbstractionLayer per connection_ref instead.
    """

    layers: Dict[str, Any] = {}

    def _fake_resolve(connector_type, connection_ref):
        if connection_ref not in layers:
            raise AssertionError(
                f"Test didn't register a fake layer for '{connection_ref}'"
            )
        return layers[connection_ref], connector_type

    monkeypatch.setattr(
        connection_resolver, "resolve_connection", _fake_resolve
    )

    def _register(
        connection_ref: str, connector: FakeConnector, database="postgresql"
    ):
        layers[connection_ref] = AbstractionLayer(
            connector=connector, database=database
        )

    return _register


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_execute_pipeline_succeeds_with_no_transformations(patch_resolver):
    source_connector = FakeConnector(
        rows=[{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
    )
    target_connector = FakeConnector()

    patch_resolver("app-db", source_connector)
    patch_resolver("warehouse", target_connector)

    pipeline = parse_pipeline(_valid_doc())
    run = executor.execute_pipeline(pipeline, pipeline_id="pipe-1")

    assert run["status"] == "succeeded"
    assert run["rows_read"] == 2
    assert run["rows_written"] == 2
    assert run["started_at"] is not None
    assert run["finished_at"] is not None
    assert len(target_connector.written_rows) == 2
    assert source_connector.disconnected is True
    assert target_connector.disconnected is True


def test_execute_pipeline_persists_run_in_run_store(patch_resolver):
    patch_resolver("app-db", FakeConnector(rows=[]))
    patch_resolver("warehouse", FakeConnector())

    pipeline = parse_pipeline(_valid_doc())
    run = executor.execute_pipeline(pipeline, pipeline_id="pipe-2")

    stored = run_store.get_run(run["run_id"])
    assert stored["status"] == "succeeded"


def test_upsert_write_mode_logs_fallback_to_insert(patch_resolver):
    patch_resolver("app-db", FakeConnector(rows=[{"id": 1}]))
    patch_resolver("warehouse", FakeConnector())

    doc = _valid_doc()
    doc["target"]["write_mode"] = "upsert"
    pipeline = parse_pipeline(doc)

    run = executor.execute_pipeline(pipeline, pipeline_id="pipe-3")

    assert run["status"] == "succeeded"
    assert any("upsert" in line and "Week 16" in line for line in run["logs"])


# ---------------------------------------------------------------------------
# Transformation dispatch
# ---------------------------------------------------------------------------


def test_unregistered_transformation_type_fails_the_run(patch_resolver):
    patch_resolver("app-db", FakeConnector(rows=[{"id": 1}]))
    patch_resolver("warehouse", FakeConnector())

    doc = _valid_doc(
        transformations=[
            {"step_id": "s1", "type": "does_not_exist", "params": {}}
        ]
    )
    pipeline = parse_pipeline(doc)

    run = executor.execute_pipeline(pipeline, pipeline_id="pipe-4")

    assert run["status"] == "failed"
    assert run["error"]["error_code"] == "UNKNOWN_TRANSFORMATION_TYPE"
    assert run["error"]["retryable"] is False
    assert "s1" in run["error"]["message"]


def test_registered_transformation_is_applied_in_order(patch_resolver):
    patch_resolver("app-db", FakeConnector(rows=[{"id": 1, "flag": False}]))
    target_connector = FakeConnector()
    patch_resolver("warehouse", target_connector)

    calls = []

    def mark_step_a(rows, params):
        calls.append("a")
        return rows

    def mark_step_b(rows, params):
        calls.append("b")
        return rows

    executor.register_transformation("step_a", mark_step_a)
    executor.register_transformation("step_b", mark_step_b)
    try:
        doc = _valid_doc(
            transformations=[
                {"step_id": "s1", "type": "step_a", "params": {}},
                {"step_id": "s2", "type": "step_b", "params": {}},
            ]
        )
        pipeline = parse_pipeline(doc)
        run = executor.execute_pipeline(pipeline, pipeline_id="pipe-5")

        assert run["status"] == "succeeded"
        assert calls == ["a", "b"]
    finally:
        executor._TRANSFORMATION_REGISTRY.pop("step_a", None)
        executor._TRANSFORMATION_REGISTRY.pop("step_b", None)


# ---------------------------------------------------------------------------
# Connector failure paths
# ---------------------------------------------------------------------------


def test_source_query_failure_marks_run_failed_with_connector_error(
    patch_resolver,
):
    patch_resolver("app-db", FakeConnector(fail_on_query=True))
    patch_resolver("warehouse", FakeConnector())

    pipeline = parse_pipeline(_valid_doc())
    run = executor.execute_pipeline(pipeline, pipeline_id="pipe-6")

    assert run["status"] == "failed"
    assert run["error"]["error_code"] == "FAKE_QUERY_FAILED"
    assert run["error"]["connector_type"] == "postgresql"
    assert run["error"]["retryable"] is False


def test_target_write_failure_marks_run_failed(patch_resolver):
    patch_resolver("app-db", FakeConnector(rows=[{"id": 1}]))
    patch_resolver("warehouse", FakeConnector(fail_on_write=True))

    pipeline = parse_pipeline(_valid_doc())
    run = executor.execute_pipeline(pipeline, pipeline_id="pipe-7")

    assert run["status"] == "failed"
    assert run["error"]["error_code"] == "FAKE_WRITE_FAILED"


def test_connection_resolution_failure_still_creates_a_run_record(monkeypatch):
    def _raise(connector_type, connection_ref):
        raise QueryError(
            "no such connection",
            error_code="CONNECTION_REF_NOT_FOUND",
            connector_type=connector_type,
            retryable=False,
        )

    monkeypatch.setattr(connection_resolver, "resolve_connection", _raise)

    pipeline = parse_pipeline(_valid_doc())
    run = executor.execute_pipeline(pipeline, pipeline_id="pipe-8")

    assert run["status"] == "failed"
    assert run["error"]["error_code"] == "CONNECTION_REF_NOT_FOUND"
    # A run_id exists and is retrievable even though nothing was read.
    assert run_store.get_run(run["run_id"])["run_id"] == run["run_id"]


# ---------------------------------------------------------------------------
# connection_resolver unit tests (env-var based connection_ref resolution)
# ---------------------------------------------------------------------------


def test_resolve_connection_missing_env_var_raises_connector_error(
    monkeypatch,
):
    monkeypatch.delenv("SUBOP_CONN_MISSING_REF", raising=False)

    from services.connectors.errors import ConnectorError

    with pytest.raises(ConnectorError) as exc_info:
        connection_resolver.resolve_connection("postgresql", "missing-ref")

    assert exc_info.value.error_code == "CONNECTION_REF_NOT_FOUND"


def test_resolve_connection_malformed_json_raises_connector_error(monkeypatch):
    monkeypatch.setenv("SUBOP_CONN_BAD_REF", "not-json")

    from services.connectors.errors import ConnectorError

    with pytest.raises(ConnectorError) as exc_info:
        connection_resolver.resolve_connection("postgresql", "bad-ref")

    assert exc_info.value.error_code == "CONNECTION_REF_MALFORMED"


def test_resolve_connection_incomplete_credentials_raises_connector_error(
    monkeypatch,
):
    monkeypatch.setenv(
        "SUBOP_CONN_PARTIAL_REF", json.dumps({"host": "localhost"})
    )

    from services.connectors.errors import ConnectorError

    with pytest.raises(ConnectorError) as exc_info:
        connection_resolver.resolve_connection("postgresql", "partial-ref")

    assert exc_info.value.error_code == "CONNECTION_REF_INCOMPLETE"


def test_resolve_connection_unsupported_connector_type_raises_connector_error():
    from services.connectors.errors import ConnectorError

    with pytest.raises(ConnectorError) as exc_info:
        connection_resolver.resolve_connection("mongodb", "some-ref")

    assert exc_info.value.error_code == "UNSUPPORTED_CONNECTOR_TYPE"


def test_env_var_naming_convention():
    assert (
        connection_resolver._env_var_name("prod-warehouse")
        == "SUBOP_CONN_PROD_WAREHOUSE"
    )
    assert connection_resolver._env_var_name("app_db") == "SUBOP_CONN_APP_DB"
    assert connection_resolver._env_var_name("Ref 1") == "SUBOP_CONN_REF_1"
