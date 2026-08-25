"""
ETL Engine — pipeline executor.

Executes a parsed PipelineDefinition (pipeline.py) end to end:
resolve connections -> read source -> run the ordered transformations
array step by step -> write target -> record run status throughout via
run_store.py.

Per etl_engine_contracts_v1.md Section 4, this module never opens a
direct DB connection or knows the dialect underneath — every read and
write goes through AbstractionLayer.execute_query / execute_write.

Per etl_engine_api_spec_v1.md Section 6, transformation *execution*
semantics (what a given `type` actually does to a row) are explicitly
out of scope for M5 Week 15 — flagged as Week 16 hardening in the task
plan. This module therefore implements the dispatch mechanism only: an
ordered loop over `transformations`, tracking each step_id, calling out
to a pluggable registry. With zero transformation types registered
today, any pipeline whose `transformations` array is non-empty fails
clearly with UNKNOWN_TRANSFORMATION_TYPE rather than guessing at
semantics that haven't been decided yet. Week 16 registers real types
via `register_transformation()` without changing anything else here.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Tuple

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

import connection_resolver  # noqa: E402
import run_store  # noqa: E402

from pipeline import PipelineDefinition, TransformationStep  # noqa: E402
from services.connectors.errors import ConnectorError  # noqa: E402

# ---------------------------------------------------------------------------
# Transformation registry (dispatch mechanism only — see module docstring)
# ---------------------------------------------------------------------------

# A transformation handler takes (rows, params) and returns the
# transformed rows. Registered by `type` string from the DSL
# (etl_engine_api_spec_v1.md Section 2).
TransformationHandler = Callable[
    [List[Dict[str, Any]], Dict[str, Any]], List[Dict[str, Any]]
]

_TRANSFORMATION_REGISTRY: Dict[str, TransformationHandler] = {}


def register_transformation(type_name: str, handler: TransformationHandler) -> None:
    """
    Register a transformation handler for a DSL `type` string.

    Intentionally empty by default (see module docstring) — Week 16
    calls this to add real transformation types without touching the
    executor's control flow.
    """
    _TRANSFORMATION_REGISTRY[type_name] = handler


class PipelineExecutionError(Exception):
    """
    Raised when a pipeline run fails outright (fatal, not quarantine).

    Wraps the underlying ConnectorError-shaped envelope (or an
    UNKNOWN_TRANSFORMATION_TYPE envelope for an unregistered step type)
    so callers can go straight from this exception to the run-status
    `error` field (API spec Section 4.1) without re-deriving the shape.
    """

    def __init__(self, envelope: Dict[str, Any]):
        super().__init__(envelope.get("message", "Pipeline run failed."))
        self.envelope = envelope


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _unknown_transformation_envelope(
    step: TransformationStep,
) -> Dict[str, Any]:
    return {
        "error_code": "UNKNOWN_TRANSFORMATION_TYPE",
        "message": (
            f"No handler registered for transformation type '{step.type}' "
            f"(step_id '{step.step_id}')."
        ),
        "connector_type": None,
        "retryable": False,
    }


def execute_pipeline(pipeline: PipelineDefinition, pipeline_id: str) -> Dict[str, Any]:
    """
    Execute one run of `pipeline` and return the final run record
    (same shape as run_store.get_run() / API spec Section 4.1).

    Every run is recorded in run_store from creation to completion —
    a caller (T4's API routes) always has a run_id to hand back, even
    if resolving the source connection fails before a single row is
    read.
    """
    run = run_store.create_run(pipeline_id)
    run_id = run["run_id"]

    logs: List[str] = []
    source_layer = None
    target_layer = None

    try:
        run_store.update_run(run_id, status="running", started_at=_now())
        logs.append(f"Run started for pipeline '{pipeline.name}'.")

        # Resolve connections(contracts Section 4: only via AbstractionLayer)
        source_layer, _ = connection_resolver.resolve_connection(
            pipeline.source.connector_type, pipeline.source.connection_ref
        )
        logs.append(f"Resolved source connection '{pipeline.source.connection_ref}'.")

        target_layer, _ = connection_resolver.resolve_connection(
            pipeline.target.connector_type, pipeline.target.connection_ref
        )
        logs.append(f"Resolved target connection '{pipeline.target.connection_ref}'.")

        # --- Read source ---
        rows, lineage_records = _read_source(source_layer, pipeline)
        rows_read = len(rows)
        logs.append(f"Read {rows_read} row(s) from '{pipeline.source.object}'.")

        # Execute transformations in array order (Section 2.1: order matters)
        rows, step_logs = _run_transformations(rows, pipeline.transformations)
        logs.extend(step_logs)

        # --- Write target ---
        rows_written, write_logs = _write_target(target_layer, pipeline, rows)
        logs.extend(write_logs)
        logs.append(f"Wrote {rows_written} row(s) to '{pipeline.target.object}'.")

        run = run_store.update_run(
            run_id,
            status="succeeded",
            finished_at=_now(),
            rows_read=rows_read,
            rows_written=rows_written,
            rows_quarantined=0,
            logs=logs,
        )

        if lineage_records:
            logs.append(
                f"{len(lineage_records)} column value(s) had a non-direct type mapping "
                "— recorded for Lineage, not treated as errors (contracts Section 7.2)."
            )
            run = run_store.update_run(run_id, logs=logs)

        return run

    except ConnectorError as exc:
        logs.append(f"Run failed: {exc.message}")
        return run_store.update_run(
            run_id,
            status="failed",
            finished_at=_now(),
            logs=logs,
            error=exc.to_envelope(),
        )

    except PipelineExecutionError as exc:
        logs.append(f"Run failed: {exc.envelope['message']}")
        return run_store.update_run(
            run_id,
            status="failed",
            finished_at=_now(),
            logs=logs,
            error=exc.envelope,
        )

    finally:
        # Always release connections, even on failure.
        if source_layer is not None:
            connection_resolver.release_connection(source_layer)
        if target_layer is not None:
            connection_resolver.release_connection(target_layer)


def _read_source(
    source_layer: Any, pipeline: PipelineDefinition
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Read all rows from the pipeline's source object.

    `source.query` (API spec Section 2.1) is an optional raw
    filter/query; when absent, this reads the full object. Column-type
    metadata for lineage-aware normalization isn't available at this
    generic layer (no schema catalog integration yet — flagged as a
    gap, not invented here), so this call doesn't pass column_types
    and capture_lineage will be empty until that's wired up.
    """
    sql = pipeline.source.query or f"SELECT * FROM {pipeline.source.object}"
    rows, lineage_records = source_layer.execute_query(sql, capture_lineage=True)
    return rows, lineage_records


def _run_transformations(
    rows: List[Dict[str, Any]], steps: List[TransformationStep]
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Execute the ordered transformations array step by step against
    each step_id, per etl_engine_api_spec_v1.md Section 2.1 ("Executed
    in array order — order is semantically meaningful").
    """
    logs: List[str] = []

    for step in steps:
        handler = _TRANSFORMATION_REGISTRY.get(step.type)

        if handler is None:
            raise PipelineExecutionError(_unknown_transformation_envelope(step))

        rows = handler(rows, step.params)
        logs.append(
            f"Applied step '{step.step_id}' (type '{step.type}') to {len(rows)} row(s)."
        )

    return rows, logs


def _write_target(
    target_layer: Any, pipeline: PipelineDefinition, rows: List[Dict[str, Any]]
) -> Tuple[int, List[str]]:
    """
    Write the transformed rows to the pipeline's target object.

    write_mode (upsert/append) is a DSL-level field (Section 2.1); the
    actual upsert-vs-append SQL construction (conflict targets, key
    columns) is target-object-specific and out of scope for this pass
    — same explicitly-deferred boundary as transformation semantics
    (Section 6). Every row is written via a plain INSERT through
    execute_write today, regardless of write_mode, so control flow and
    run accounting are correct now; this is logged explicitly (rather
    than silently claiming upsert behavior it doesn't yet have) so a
    run's logs never overstate what happened. Week 16 swaps in real
    upsert/append SQL generation without changing anything above it.
    """
    logs: List[str] = []
    if pipeline.target.write_mode == "upsert":
        logs.append(
            "write_mode is 'upsert' but conflict-resolution SQL isn't implemented yet "
            "(Week 16 scope) — rows were written as plain inserts."
        )

    written = 0
    for row in rows:
        columns = ", ".join(row.keys())
        placeholders = ", ".join(["%s"] * len(row))
        sql = (
            f"INSERT INTO {pipeline.target.object} ({columns}) VALUES ({placeholders})"
        )
        target_layer.execute_write(sql, tuple(row.values()))
        written += 1

    return written, logs
