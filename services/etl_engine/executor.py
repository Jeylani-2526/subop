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
to a pluggable registry.

Week 16 registers a first set of real transformation types via
`register_transformation()` — rename_columns, type_cast,
drop_null_rows, drop_columns — without changing the dispatch mechanism
itself. Each type's `params` shape is deliberately minimal and
documented inline on its handler; it is provisional Week-16 scope, not
a finalized DSL spec (transformation DSL syntax is still explicitly
flagged out of scope project-wide per the M5 kickoff notes).

Week 16 also wires a synchronous Data Quality pre-write hook
(data_quality_hook.py) into execute_pipeline(), ahead of the target
write (contracts Section 6). It follows the same interface-first stub
pattern as compliance_check.py: fixed signature, always-pass logic for
now, since the full Data Quality engine isn't built until M10.

Week 16 additionally persists non-direct type-mapping conditions
(contracts Section 7.2) as structured Lineage records via
lineage_store.py, alongside the existing summary log line — see that
module's docstring for why every entry today carries
lineage_store.SOURCE_READ_STEP_ID rather than a transformation
step_id.
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
import data_quality_hook  # noqa: E402
import lineage_store  # noqa: E402
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

        # --- Data Quality pre-write hook (contracts Section 6) ---
        # Stub today (M10 builds the real engine) — always passes, so
        # dq_result.rows_quarantined is 0 and quality_score is None for
        # every run right now. Called through a real function rather than
        # hardcoded here so nothing above this call has to change once
        # M10 lands.
        dq_result = data_quality_hook.run_data_quality_check(rows, pipeline.name)
        logs.append(
            f"Data Quality pre-write check: {dq_result.rows_quarantined} row(s) "
            "quarantined (stub check — always passes today; real rule "
            "evaluation is M10 scope)."
        )

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
            rows_quarantined=dq_result.rows_quarantined,
            quality_score=dq_result.quality_score,
            logs=logs,
        )

        if lineage_records:
            logs.append(
                f"{len(lineage_records)} column value(s) had a non-direct type mapping "
                "— recorded for Lineage, not treated as errors (contracts Section 7.2)."
            )
            run = run_store.update_run(run_id, logs=logs)

            # Persist each one as a structured Lineage record (contracts
            # Section 6) — see lineage_store.py module docstring for why
            # step_id is SOURCE_READ_STEP_ID today rather than one of
            # the pipeline's own transformation step_ids.
            for record in lineage_records:
                lineage_store.record_lineage_entry(
                    run_id=run_id,
                    step_id=lineage_store.SOURCE_READ_STEP_ID,
                    column=record["column"],
                    condition=record["condition"],
                    canonical_type=record.get("canonical_type"),
                    source_type=record.get("source_type"),
                )

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
    columns) is target-object-specific and remains out of scope —
    Week 16 hardens transformation execution and the Data Quality hook
    (see module docstring), not write_mode SQL generation, which stays
    an open item. Every row is written via a plain INSERT through
    execute_write today, regardless of write_mode, so control flow and
    run accounting are correct now; this is logged explicitly (rather
    than silently claiming upsert behavior it doesn't yet have) so a
    run's logs never overstate what happened.
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


# ---------------------------------------------------------------------------
# Week 16 transformation types
#
# Params shapes below are provisional Week-16 scope, not a finalized DSL
# spec — transformation DSL syntax is still explicitly flagged out of
# scope project-wide (M5 kickoff notes, contracts Section 9). Each
# handler follows the TransformationHandler signature: (rows, params)
# -> rows.
# ---------------------------------------------------------------------------

_TYPE_CASTERS: Dict[str, Callable[[Any], Any]] = {
    "int": int,
    "float": float,
    "str": str,
    "bool": lambda v: str(v).strip().lower() in ("true", "1", "yes"),
}


def _rename_columns(
    rows: List[Dict[str, Any]], params: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    params: {"mapping": {"old_name": "new_name", ...}}

    Renames each row's matching keys. A row missing an old_name is left
    untouched for that key (no error) — the row may simply not have
    that column.
    """
    mapping = params.get("mapping", {})
    new_rows = []
    for row in rows:
        new_row = dict(row)
        for old_name, new_name in mapping.items():
            if old_name in new_row:
                new_row[new_name] = new_row.pop(old_name)
        new_rows.append(new_row)
    return new_rows


def _type_cast(
    rows: List[Dict[str, Any]], params: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    params: {"casts": {"column_name": "int" | "float" | "str" | "bool"}}

    Casts each listed column's value to the target type. A cast that
    fails (e.g. casting "abc" to int) leaves the original value in
    place rather than raising — real validation/quarantine of bad
    values is the Data Quality engine's job (M10), not this stub-era
    transformation step's. A null value is left as null, uncast.
    """
    casts = params.get("casts", {})
    new_rows = []
    for row in rows:
        new_row = dict(row)
        for column, target_type in casts.items():
            if column not in new_row or new_row[column] is None:
                continue
            caster = _TYPE_CASTERS.get(target_type)
            if caster is None:
                continue
            try:
                new_row[column] = caster(new_row[column])
            except (ValueError, TypeError):
                pass
        new_rows.append(new_row)
    return new_rows


def _drop_null_rows(
    rows: List[Dict[str, Any]], params: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    params: {"required_columns": ["col1", "col2", ...]}

    Drops a row entirely if ANY of required_columns is null or missing
    on it. A column not listed in required_columns is never checked,
    even if it happens to be null.
    """
    required_columns = params.get("required_columns", [])
    return [
        row for row in rows if all(row.get(col) is not None for col in required_columns)
    ]


def _drop_columns(
    rows: List[Dict[str, Any]], params: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    params: {"columns": ["col1", "col2", ...]}

    Removes the listed columns from every row. A row missing a listed
    column is left untouched for that key (no error).
    """
    columns_to_drop = set(params.get("columns", []))
    return [{k: v for k, v in row.items() if k not in columns_to_drop} for row in rows]


register_transformation("rename_columns", _rename_columns)
register_transformation("type_cast", _type_cast)
register_transformation("drop_null_rows", _drop_null_rows)
register_transformation("drop_columns", _drop_columns)
