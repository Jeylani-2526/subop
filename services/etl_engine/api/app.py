"""
ETL Engine API routes (M5W15T4).

Week 16 (M5W16T4) adds pagination to GET /api/pipelines/ and a new
GET /api/kpis route aggregating real figures from pipeline_store and
run_store. average_quality_score is null whenever no run has a real
quality_score yet (T2's Data Quality hook is still a stub) — an
honest null rather than a fabricated number.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import Body, FastAPI, Query
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
def list_pipelines_route(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """
    GET /api/pipelines/ - paginated pipeline list (M5W16T4).

    Returns {items, total, page, page_size} — DataTable.tsx's
    pagination props already expect this shape. `total` is the full
    unpaginated count so the client can compute page count and the
    "Showing X-Y of Z" label without a separate request.
    """
    all_pipelines = pipeline_store.list_pipelines()
    total = len(all_pipelines)
    start = (page - 1) * page_size
    end = start + page_size
    items = all_pipelines[start:end]

    return JSONResponse(
        status_code=200,
        content={
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        },
    )


@app.post("/api/pipelines/", status_code=201)
def create_pipeline_route(payload: Dict[str, Any] = Body(...)):
    """POST /api/pipelines/ - API spec Section 3."""
    try:
        parsed = parse_pipeline(payload)
    except PipelineValidationError as exc:
        return JSONResponse(
            status_code=400,
            content=_error_envelope(
                "DSL_VALIDATION_FAILED",
                "; ".join(exc.errors),
            ),
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
            content=_error_envelope(
                "VERBIS_REGISTRATION_INCOMPLETE",
                exc.message,
            ),
        )

    record = pipeline_store.create_pipeline(
        name=parsed.name,
        source=payload["source"],
        transformations=payload.get("transformations") or [],
        target=payload["target"],
    )

    executor.execute_pipeline(parsed, pipeline_id=record["id"])

    # Attach the latest run's id to the response, through each
    # store's own functions — never touching _runs or _pipelines
    # directly.
    runs = run_store.get_runs_for_pipeline(record["id"])
    if runs:
        record = pipeline_store.set_latest_run_id(record["id"], runs[-1]["run_id"])

    return JSONResponse(status_code=201, content=record)


@app.get("/api/pipelines/{pipeline_id}/runs/{run_id}")
def get_run_status_route(pipeline_id: str, run_id: str):
    """GET /api/pipelines/{id}/runs/{run_id} - API spec Section 4."""
    if not pipeline_store.pipeline_exists(pipeline_id):
        return JSONResponse(
            status_code=404,
            content=_error_envelope(
                "PIPELINE_NOT_FOUND",
                f"Pipeline '{pipeline_id}' not found.",
            ),
        )

    try:
        run = run_store.get_run(run_id)
    except KeyError:
        return JSONResponse(
            status_code=404,
            content=_error_envelope(
                "RUN_NOT_FOUND",
                f"Run '{run_id}' not found.",
            ),
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


def _kpi_aggregates() -> Dict[str, Any]:
    """
    Aggregate live KPI figures from pipeline_store and run_store —
    no separate KPI store; computed fresh on each request (M5W16T4).

    - pipeline_count: total pipelines, live count.
    - rows_processed_today: sum of rows_written across every run whose
      finished_at falls on today's UTC calendar date, regardless of
      status (a failed run's rows_written is 0 by construction, so
      including it changes nothing).
    - average_quality_score: mean of quality_score across only the
      runs that actually have one. None (not 0, not a guess) when no
      run has one yet — honest status while T2's Data Quality hook is
      still a stub returning quality_score=None for every run.
    """
    pipelines = pipeline_store.list_pipelines()
    pipeline_count = len(pipelines)

    today = datetime.now(timezone.utc).date()
    rows_processed_today = 0
    quality_scores: List[float] = []

    for p in pipelines:
        for run in run_store.get_runs_for_pipeline(p["id"]):
            finished_at = run.get("finished_at")
            if finished_at:
                try:
                    finished_date = datetime.fromisoformat(finished_at).date()
                except ValueError:
                    finished_date = None
                if finished_date == today:
                    rows_processed_today += run.get("rows_written") or 0

            quality_score = run.get("quality_score")
            if quality_score is not None:
                quality_scores.append(quality_score)

    average_quality_score: Optional[float] = (
        sum(quality_scores) / len(quality_scores) if quality_scores else None
    )

    return {
        "pipeline_count": pipeline_count,
        "rows_processed_today": rows_processed_today,
        "average_quality_score": average_quality_score,
    }


@app.get("/api/kpis")
def get_kpis_route():
    """
    GET /api/kpis - live KPI aggregation (M5W16T4).

    Unblocks Beyza's T8 (HomePage KPISummaryCard live wiring),
    replacing the frontend's MOCK_KPI.
    """
    return JSONResponse(status_code=200, content=_kpi_aggregates())
