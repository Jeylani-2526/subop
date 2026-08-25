"""
In-memory persistence layer for created ETL pipelines.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Dict, List
from uuid import uuid4

_pipelines: Dict[str, Dict[str, Any]] = {}


def _current_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_pipeline(
    *,
    name: str,
    source: Dict[str, Any],
    transformations: List[Dict[str, Any]],
    target: Dict[str, Any],
) -> Dict[str, Any]:
    """Create and persist a new pipeline record."""
    pipeline_id = str(uuid4())

    record = {
        "id": pipeline_id,
        "name": name,
        "status": "created",
        "created_at": _current_timestamp(),
        "source": deepcopy(source),
        "transformations": deepcopy(transformations),
        "target": deepcopy(target),
    }

    _pipelines[pipeline_id] = record

    return deepcopy(record)


def get_pipeline(pipeline_id: str) -> Dict[str, Any]:
    """Return a stored pipeline record by id. Raises KeyError if unknown."""
    if pipeline_id not in _pipelines:
        raise KeyError(f"Pipeline '{pipeline_id}' not found.")

    return deepcopy(_pipelines[pipeline_id])


def pipeline_exists(pipeline_id: str) -> bool:
    return pipeline_id in _pipelines


def clear_pipelines() -> None:
    """Remove all stored pipelines (test support)."""
    _pipelines.clear()


def list_pipelines() -> List[Dict[str, Any]]:
    """Return all stored pipelines as a list."""
    return [deepcopy(p) for p in _pipelines.values()]


def set_latest_run_id(pipeline_id: str, run_id: str) -> Dict[str, Any]:
    """
    Attach the id of a pipeline's most recent run to its record.
    """
    if pipeline_id not in _pipelines:
        raise KeyError(f"Pipeline '{pipeline_id}' not found.")

    _pipelines[pipeline_id]["run_id"] = run_id
    return deepcopy(_pipelines[pipeline_id])
