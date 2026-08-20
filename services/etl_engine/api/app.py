"""
ETL Engine API routes (M5W15T4).

Implements the two endpoints named in etl_engine_contracts_v1.md
Section 2/3 and specified field-for-field in
etl_engine_api_spec_v1.md:

    POST /api/pipelines/                        (Section 3)
    GET  /api/pipelines/{id}/runs/{run_id}       (Section 4)

Endpoints are plain `def`, not `async def` — every connector call
underneath (psycopg2, PyMySQL, pyodbc) is synchronous, so running them
as sync routes lets Starlette dispatch them to its thread pool instead
of blocking FastAPI's event loop.

Run-triggering gap: the spec names no endpoint that creates a run —
only "create a pipeline" and "get a run's status" exist. Per team
decision (Week 15), POST /api/pipelines/ auto-triggers one synchronous
run immediately after creation, so the run_id returned by that trigger
is reachable via the GET endpoint today. This is a deliberate stand-in
until a real run-trigger/scheduling design exists (flagged for a later
milestone) — noted here so it isn't mistaken for something the spec
itself defined.
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict

from fastapi import Body, FastAPI
from fastapi.responses import JSONResponse

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_ETL_ENGINE_DIR = os.path.dirname(_THIS_DIR)
if _ETL_ENGINE_DIR not in sys.path:
    sys.path.insert(0, _ETL_ENGINE_DIR)

import executor  # noqa: E402
import pipeline_store  # noqa: E402
import run_store  # noqa: E402
from compliance_check import (  # noqa: E402
    ComplianceCheckFailed,
    check_verbis_registration,
)
from pipeline import PipelineValidationError, parse_pipeline  # noqa: E402

app = FastAPI(title="SUBOP ETL Engine API")


def _error_envelope(
    error_code: str,
    message: str,
    *,
    connector_type: Any = None,
    retryable: bool = False,
) -> Dict[str, Any]:
    """
    Shared error envelope (API spec Section 5), matching ConnectorError's
    to_envelope() shape so API-layer and connector-layer errors look
    identical to a consumer. connector_type is null here since these
    are API/ETL-Engine-layer errors, not connector failures.
    """
    return {
        "error_code": error_code,
        "message": message,
        "connector_type": connector_type,
        "retryable": retryable,
    }


@app.post("/api/pipelines/", status_code=201)
def create_pipeline_route(payload: Dict[str, Any] = Body(...)):
    """
    POST /api/pipelines/ — API spec Section 3.

    400 on DSL schema validation failure, 422 on failed VERBİS
    compliance check (pipeline is not created), 201 on success.

    Note: a request body that isn't valid JSON at all is rejected by
    FastAPI's own request parsing before this function runs, using
    FastAPI's default error shape rather than the envelope below —
    the spec doesn't distinguish "not JSON" from "JSON but fails
    schema validation," so this is a known, low-risk edge case rather
    than a spec violation.
    """
    try:
        parsed = parse_pipeline(payload)
    except PipelineValidationError as exc:
        return JSONResponse(
            status_code=400,
            content=_error_envelope("DSL_VALIDATION_FAILED", "; ".join(exc.errors)),
        )

    try:
        check_verbis_registration(
            parsed.processing_purpose,
            parsed.data_subject_categories,
            parsed.transfer_recipients,
        )
    except ComplianceCheckFailed as exc:
        return JSONResponse(
            status_code=422,
            content=_error_envelope("VERBIS_REGISTRATION_INCOMPLETE", exc.message),
        )

    record = pipeline_store.create_pipeline(
        name=parsed.name,
        source=payload["source"],
        transformations=payload.get("transformations") or [],
        target=payload["target"],
    )

    # Auto-trigger one synchronous run (see module docstring). Failures
    # during the run itself are captured inside run_store by
    # execute_pipeline and don't affect this 201 — pipeline creation
    # already succeeded independent of whether its first run does.
    executor.execute_pipeline(parsed, pipeline_id=record["id"])

    return JSONResponse(status_code=201, content=record)


@app.get("/api/pipelines/{pipeline_id}/runs/{run_id}")
def get_run_status_route(pipeline_id: str, run_id: str):
    """GET /api/pipelines/{id}/runs/{run_id} — API spec Section 4."""
    if not pipeline_store.pipeline_exists(pipeline_id):
        return JSONResponse(
            status_code=404,
            content=_error_envelope(
                "PIPELINE_NOT_FOUND", f"Pipeline '{pipeline_id}' not found."
            ),
        )

    try:
        run = run_store.get_run(run_id)
    except KeyError:
        return JSONResponse(
            status_code=404,
            content=_error_envelope("RUN_NOT_FOUND", f"Run '{run_id}' not found."),
        )

    if run["pipeline_id"] != pipeline_id:
        return JSONResponse(
            status_code=404,
            content=_error_envelope(
                "RUN_NOT_FOUND",
                f"Run '{run_id}' not found for pipeline '{pipeline_id}'.",
            ),
        )

    return JSONResponse(status_code=200, content=run)
