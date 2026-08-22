"""
ETL Engine API routes (M5W15T4).
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, List

from fastapi import Body, FastAPI
from fastapi.middleware.cors import CORSMiddleware
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _error_envelope(
    error_code: str,
    message: str,
    *,
    connector_type: Any = None,
    retryable: bool = False,
) -> Dict[str, Any]:
    return {
        "error_code": error_code,
        "message": message,
        "connector_type": connector_type,
        "retryable": retryable,
    }


@app.get("/api/pipelines/")
def list_pipelines_route():
    """GET /api/pipelines/ — tüm pipeline'ları listele."""
    return JSONResponse(status_code=200, content=pipeline_store.list_pipelines())


@app.post("/api/pipelines/", status_code=201)
def create_pipeline_route(payload: Dict[str, Any] = Body(...)):
    """POST /api/pipelines/ — API spec Section 3."""
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

    executor.execute_pipeline(parsed, pipeline_id=record["id"])

    # run_id'yi response'a ve pipeline_store'a ekle
    all_runs = [
        run_store.get_run(rid)
        for rid in run_store._runs
        if run_store._runs[rid]["pipeline_id"] == record["id"]
    ]
    if all_runs:
        record["run_id"] = all_runs[0]["run_id"]
        pipeline_store._pipelines[record["id"]]["run_id"] = all_runs[0]["run_id"]

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