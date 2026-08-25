"""Tests for the ETL pipeline run persistence layer."""

import importlib.util
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Load run_store.py from the kebab-case etl-engine directory
# ---------------------------------------------------------------------------

RUN_STORE_PATH = (
    Path(__file__).resolve().parents[1]
    / "services"
    / "etl_engine"
    / "run_store.py"
)

spec = importlib.util.spec_from_file_location("run_store", RUN_STORE_PATH)

if spec is None or spec.loader is None:
    raise ImportError(f"Could not load run_store module from {RUN_STORE_PATH}")

run_store = importlib.util.module_from_spec(spec)
spec.loader.exec_module(run_store)

clear_runs = run_store.clear_runs
create_run = run_store.create_run
get_run = run_store.get_run
update_run = run_store.update_run


# ---------------------------------------------------------------------------
# Test setup
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_run_store():
    """Clear the in-memory run store before and after each test."""

    clear_runs()
    yield
    clear_runs()


# ---------------------------------------------------------------------------
# Run creation tests
# ---------------------------------------------------------------------------


def test_create_run_creates_pending_run():
    """A newly created run should use the API contract defaults."""

    run = create_run("pipeline-123")

    assert run["pipeline_id"] == "pipeline-123"
    assert run["status"] == "pending"
    assert run["started_at"] is None
    assert run["finished_at"] is None
    assert run["rows_read"] == 0
    assert run["rows_written"] == 0
    assert run["rows_quarantined"] == 0
    assert run["quality_score"] is None
    assert run["logs"] == []
    assert "error" not in run


def test_create_run_generates_unique_run_ids():
    """Each new pipeline run should receive a unique run ID."""

    first_run = create_run("pipeline-123")
    second_run = create_run("pipeline-123")

    assert first_run["run_id"] != second_run["run_id"]


# ---------------------------------------------------------------------------
# Run retrieval tests
# ---------------------------------------------------------------------------


def test_get_run_returns_stored_run():
    """A stored run should be retrievable by its run ID."""

    created_run = create_run("pipeline-123")

    retrieved_run = get_run(created_run["run_id"])

    assert retrieved_run == created_run


def test_get_run_raises_for_unknown_run():
    """Retrieving an unknown run ID should raise KeyError."""

    with pytest.raises(KeyError):
        get_run("missing-run")


# ---------------------------------------------------------------------------
# Run update tests
# ---------------------------------------------------------------------------


def test_update_run_updates_status_and_metrics():
    """Run status and processing metrics should be updateable."""

    run = create_run("pipeline-123")

    updated_run = update_run(
        run["run_id"],
        status="running",
        rows_read=100,
        rows_written=80,
        rows_quarantined=20,
        quality_score=0.8,
    )

    assert updated_run["status"] == "running"
    assert updated_run["rows_read"] == 100
    assert updated_run["rows_written"] == 80
    assert updated_run["rows_quarantined"] == 20
    assert updated_run["quality_score"] == 0.8


def test_update_run_updates_timestamps():
    """Run start and finish timestamps should be updateable."""

    run = create_run("pipeline-123")

    updated_run = update_run(
        run["run_id"],
        started_at="2026-08-18T08:00:00+00:00",
        finished_at="2026-08-18T08:05:00+00:00",
    )

    assert updated_run["started_at"] == "2026-08-18T08:00:00+00:00"
    assert updated_run["finished_at"] == "2026-08-18T08:05:00+00:00"


def test_update_run_replaces_logs():
    """Providing logs should replace the current log list."""

    run = create_run("pipeline-123")

    updated_run = update_run(
        run["run_id"],
        logs=["Extraction started", "100 rows processed"],
    )

    assert updated_run["logs"] == [
        "Extraction started",
        "100 rows processed",
    ]


def test_update_run_adds_error_for_failed_run():
    """A failed run should be able to store the shared error envelope."""

    run = create_run("pipeline-123")

    error = {
        "error_code": "CONNECTOR_FAILURE",
        "message": "Database connection failed.",
        "connector_type": "postgresql",
        "retryable": False,
    }

    updated_run = update_run(
        run["run_id"],
        status="failed",
        error=error,
    )

    assert updated_run["status"] == "failed"
    assert updated_run["error"] == error


def test_update_run_removes_error_when_status_changes_from_failed():
    """The error field should be removed when a run is no longer failed."""

    run = create_run("pipeline-123")

    update_run(
        run["run_id"],
        status="failed",
        error={
            "error_code": "TEST_ERROR",
            "message": "Test failure.",
            "connector_type": None,
            "retryable": False,
        },
    )

    updated_run = update_run(
        run["run_id"],
        status="running",
    )

    assert updated_run["status"] == "running"
    assert "error" not in updated_run


# ---------------------------------------------------------------------------
# Validation tests
# ---------------------------------------------------------------------------


def test_update_run_rejects_invalid_status():
    """Statuses outside the API contract should be rejected."""

    run = create_run("pipeline-123")

    with pytest.raises(ValueError):
        update_run(
            run["run_id"],
            status="success",
        )


def test_update_run_raises_for_unknown_run():
    """Updating an unknown run ID should raise KeyError."""

    with pytest.raises(KeyError):
        update_run(
            "missing-run",
            status="running",
        )


# ---------------------------------------------------------------------------
# Defensive copy tests
# ---------------------------------------------------------------------------


def test_create_run_returns_defensive_copy():
    """Mutating a returned run should not mutate the stored record."""

    run = create_run("pipeline-123")
    run["status"] = "failed"

    stored_run = get_run(run["run_id"])

    assert stored_run["status"] == "pending"


def test_get_run_returns_defensive_copy():
    """Mutating a retrieved run should not change the stored record."""

    created_run = create_run("pipeline-123")

    retrieved_run = get_run(created_run["run_id"])
    retrieved_run["logs"].append("External mutation")

    stored_run = get_run(created_run["run_id"])

    assert stored_run["logs"] == []
