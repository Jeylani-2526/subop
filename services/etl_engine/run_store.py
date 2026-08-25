"""In-memory persistence layer for ETL pipeline run records."""

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

# ---------------------------------------------------------------------------
# Run status configuration
# ---------------------------------------------------------------------------

VALID_STATUSES = {
    "pending",
    "running",
    "succeeded",
    "completed_with_quarantine",
    "failed",
    "cancelled",
}


# ---------------------------------------------------------------------------
# In-memory run storage
# ---------------------------------------------------------------------------

_runs: dict[str, dict[str, Any]] = {}


# ---------------------------------------------------------------------------
# Internal helper functions
# ---------------------------------------------------------------------------


def _current_timestamp() -> str:
    """Return the current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Run creation
# ---------------------------------------------------------------------------


def create_run(pipeline_id: str) -> dict[str, Any]:
    """Create and persist a new pipeline run with pending status."""

    run_id = str(uuid4())

    run = {
        "run_id": run_id,
        "pipeline_id": pipeline_id,
        "status": "pending",
        "started_at": None,
        "finished_at": None,
        "rows_read": 0,
        "rows_written": 0,
        "rows_quarantined": 0,
        "quality_score": None,
        "logs": [],
    }

    _runs[run_id] = run

    return deepcopy(run)


# ---------------------------------------------------------------------------
# Run update
# ---------------------------------------------------------------------------


def update_run(
    run_id: str,
    *,
    status: str | None = None,
    started_at: str | None = None,
    finished_at: str | None = None,
    rows_read: int | None = None,
    rows_written: int | None = None,
    rows_quarantined: int | None = None,
    quality_score: float | None = None,
    logs: list[str] | None = None,
    error: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Update an existing pipeline run and return the updated record."""

    if run_id not in _runs:
        raise KeyError(f"Run '{run_id}' not found.")

    run = _runs[run_id]

    # Validate the run status before storing it.
    if status is not None:
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid run status: '{status}'.")
        run["status"] = status

    # Update run timestamps when provided.
    if started_at is not None:
        run["started_at"] = started_at

    if finished_at is not None:
        run["finished_at"] = finished_at

    # Update row processing counters when provided.
    if rows_read is not None:
        run["rows_read"] = rows_read

    if rows_written is not None:
        run["rows_written"] = rows_written

    if rows_quarantined is not None:
        run["rows_quarantined"] = rows_quarantined

    # Update the data-quality score when provided.
    if quality_score is not None:
        run["quality_score"] = quality_score

    # Replace the current run logs when a new log list is provided.
    if logs is not None:
        run["logs"] = list(logs)

    # The error field is present only when an error is provided.
    if error is not None:
        run["error"] = deepcopy(error)
    elif status is not None and status != "failed":
        run.pop("error", None)

    return deepcopy(run)


# ---------------------------------------------------------------------------
# Run retrieval
# ---------------------------------------------------------------------------


def get_run(run_id: str) -> dict[str, Any]:
    """Return a stored pipeline run by its run ID."""

    if run_id not in _runs:
        raise KeyError(f"Run '{run_id}' not found.")

    return deepcopy(_runs[run_id])


def get_runs_for_pipeline(pipeline_id: str) -> list[dict[str, Any]]:
    """
    Return every run recorded for a pipeline, oldest first.

    A pipeline can have more than one run over time — this returns all
    of them so a caller can pick the latest one explicitly.
    """
    return [deepcopy(r) for r in _runs.values() if r["pipeline_id"] == pipeline_id]


# ---------------------------------------------------------------------------
# Store maintenance
# ---------------------------------------------------------------------------


def clear_runs() -> None:
    """Remove all stored runs from the in-memory store."""

    _runs.clear()
