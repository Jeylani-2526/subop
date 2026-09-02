"""Tests for the ETL Engine API routes (M5W15T4)."""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services" / "etl_engine"))
sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "services" / "etl_engine" / "api"),
)

import run_store  # noqa: E402
import pipeline_store  # noqa: E402
import connection_resolver  # noqa: E402
from app import app  # noqa: E402

client = TestClient(app)


def _valid_doc(**overrides):
    doc = {
        "name": "customers-to-warehouse",
        "source": {
            "connector_type": "postgresql",
            "connection_ref": "app-db",
            "object": "customers",
            "query": None,
        },
        "transformations": [],
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
    doc.update(overrides)
    return doc


@pytest.fixture(autouse=True)
def reset_state(monkeypatch):
    run_store.clear_runs()
    pipeline_store.clear_pipelines()

    # Route the executor's auto-triggered run at connection resolution
    # that always fails cleanly (no live DB in tests) rather than
    # touching real env vars/drivers — proves the run is reachable via
    # GET without needing a real database.
    def _fail_resolve(connector_type, connection_ref):
        from services.connectors.errors import ConnectionError as ConnErr

        raise ConnErr(
            "no test database configured",
            error_code="TEST_NO_DB",
            connector_type=connector_type,
            retryable=False,
        )

    monkeypatch.setattr(connection_resolver, "resolve_connection", _fail_resolve)
    yield
    run_store.clear_runs()
    pipeline_store.clear_pipelines()


# ---------------------------------------------------------------------------
# POST /api/pipelines/
# ---------------------------------------------------------------------------


def test_create_pipeline_returns_201_with_expected_shape():
    response = client.post("/api/pipelines/", json=_valid_doc())

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "created"
    assert body["name"] == "customers-to-warehouse"
    assert "id" in body and body["id"]
    assert "created_at" in body
    assert body["source"]["connector_type"] == "postgresql"
    assert body["target"]["write_mode"] == "append"


def test_create_pipeline_persists_and_is_fetchable_by_id():
    response = client.post("/api/pipelines/", json=_valid_doc())
    pipeline_id = response.json()["id"]

    assert pipeline_store.pipeline_exists(pipeline_id)


def test_create_pipeline_invalid_dsl_returns_400_with_envelope():
    doc = _valid_doc()
    doc["source"]["connector_type"] = "oracle"

    response = client.post("/api/pipelines/", json=doc)

    assert response.status_code == 400
    body = response.json()
    assert body["error_code"] == "DSL_VALIDATION_FAILED"
    assert body["connector_type"] is None
    assert body["retryable"] is False
    assert "source.connector_type" in body["message"]


def test_create_pipeline_missing_required_field_returns_400():
    doc = _valid_doc()
    del doc["processing_purpose"]

    response = client.post("/api/pipelines/", json=doc)

    assert response.status_code == 400
    assert response.json()["error_code"] == "DSL_VALIDATION_FAILED"


def test_create_pipeline_compliance_failure_returns_422(monkeypatch):
    import compliance_check

    def _fail_check(purpose, categories, recipients):
        raise compliance_check.ComplianceCheckFailed(
            "No completed VERBİS registration found."
        )

    monkeypatch.setattr(compliance_check, "check_verbis_registration", _fail_check)
    # app.py imported the function by name, so patch it there too.
    import app as app_module

    monkeypatch.setattr(app_module, "check_verbis_registration", _fail_check)

    response = client.post("/api/pipelines/", json=_valid_doc())

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "VERBIS_REGISTRATION_INCOMPLETE"
    assert body["retryable"] is False


def test_create_pipeline_does_not_persist_on_compliance_failure(monkeypatch):
    import app as app_module

    def _fail_check(purpose, categories, recipients):
        from compliance_check import ComplianceCheckFailed

        raise ComplianceCheckFailed("blocked")

    monkeypatch.setattr(app_module, "check_verbis_registration", _fail_check)

    before = len(pipeline_store._pipelines)
    client.post("/api/pipelines/", json=_valid_doc())
    after = len(pipeline_store._pipelines)

    assert after == before


# ---------------------------------------------------------------------------
# GET /api/pipelines/{id}/runs/{run_id}
# ---------------------------------------------------------------------------


def test_get_run_status_reachable_after_creation():
    create_response = client.post("/api/pipelines/", json=_valid_doc())
    pipeline_id = create_response.json()["id"]

    # The auto-triggered run failed (no test DB), but it must still
    # have created a real, fetchable run record.
    runs_for_pipeline = [
        r for r in run_store._runs.values() if r["pipeline_id"] == pipeline_id
    ]
    assert len(runs_for_pipeline) == 1
    run_id = runs_for_pipeline[0]["run_id"]

    response = client.get(f"/api/pipelines/{pipeline_id}/runs/{run_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["run_id"] == run_id
    assert body["pipeline_id"] == pipeline_id
    assert body["status"] == "failed"  # no test DB configured
    assert body["error"]["error_code"] == "TEST_NO_DB"


def test_get_run_status_unknown_pipeline_returns_404():
    response = client.get("/api/pipelines/does-not-exist/runs/does-not-exist-either")

    assert response.status_code == 404
    assert response.json()["error_code"] == "PIPELINE_NOT_FOUND"


def test_get_run_status_unknown_run_returns_404():
    create_response = client.post("/api/pipelines/", json=_valid_doc())
    pipeline_id = create_response.json()["id"]

    response = client.get(f"/api/pipelines/{pipeline_id}/runs/not-a-real-run")

    assert response.status_code == 404
    assert response.json()["error_code"] == "RUN_NOT_FOUND"


def test_get_run_status_run_belongs_to_different_pipeline_returns_404():
    create_response_1 = client.post(
        "/api/pipelines/", json=_valid_doc(name="pipeline-one")
    )
    create_response_2 = client.post(
        "/api/pipelines/", json=_valid_doc(name="pipeline-two")
    )

    pipeline_id_2 = create_response_2.json()["id"]

    runs_for_pipeline_1 = [
        r
        for r in run_store._runs.values()
        if r["pipeline_id"] == create_response_1.json()["id"]
    ]
    run_id_from_pipeline_1 = runs_for_pipeline_1[0]["run_id"]

    # Ask for pipeline 2's run using pipeline 1's run_id.
    response = client.get(
        f"/api/pipelines/{pipeline_id_2}/runs/{run_id_from_pipeline_1}"
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "RUN_NOT_FOUND"


# ---------------------------------------------------------------------------
# GET /api/pipelines/ pagination
# ---------------------------------------------------------------------------


def test_list_pipelines_paginates_results():
    for i in range(5):
        pipeline_store.create_pipeline(
            name=f"pipeline-{i}",
            source=_valid_doc()["source"],
            transformations=[],
            target=_valid_doc()["target"],
        )

    response = client.get("/api/pipelines/?page=2&page_size=2")

    assert response.status_code == 200
    body = response.json()

    assert body["total"] == 5
    assert body["page"] == 2
    assert body["page_size"] == 2
    assert len(body["items"]) == 2


def test_list_pipelines_last_page_can_be_partial():
    for i in range(5):
        pipeline_store.create_pipeline(
            name=f"pipeline-{i}",
            source=_valid_doc()["source"],
            transformations=[],
            target=_valid_doc()["target"],
        )

    response = client.get("/api/pipelines/?page=3&page_size=2")

    assert response.status_code == 200
    body = response.json()

    assert body["total"] == 5
    assert body["page"] == 3
    assert body["page_size"] == 2
    assert len(body["items"]) == 1


# ---------------------------------------------------------------------------
# GET /api/kpis
# ---------------------------------------------------------------------------


def test_get_kpis_returns_expected_shape():
    pipeline = pipeline_store.create_pipeline(
        name="pipeline-one",
        source=_valid_doc()["source"],
        transformations=[],
        target=_valid_doc()["target"],
    )

    run_store.create_run(pipeline["id"])

    response = client.get("/api/kpis")

    assert response.status_code == 200
    body = response.json()

    assert body["pipeline_count"] == 1
    assert "rows_processed_today" in body
    assert "average_quality_score" in body


def test_get_kpis_average_quality_score_is_null_when_no_scores_exist():
    pipeline = pipeline_store.create_pipeline(
        name="pipeline-one",
        source=_valid_doc()["source"],
        transformations=[],
        target=_valid_doc()["target"],
    )

    run_store.create_run(pipeline["id"])

    response = client.get("/api/kpis")

    assert response.status_code == 200
    body = response.json()

    assert body["average_quality_score"] is None
