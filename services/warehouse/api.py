"""Warehouse schema endpoints, base /api/warehouse (M8W29T1).

Shapes and status codes follow docs/planning/warehouse_api_contract.md.
GET /schemas/{id}/versions is deliberately absent: versioning is deferred.
"""

from __future__ import annotations

import json
import os
from typing import Any, Callable, Iterator, Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from services.connectors.errors import ConnectorError, WriteError
from services.warehouse.metadata import MetadataValidationError
from services.warehouse.schema_generator import (
    DEFAULT_TARGET_REF,
    SchemaConflictError,
    SchemaGenerator,
)
from services.warehouse.source_catalog import definition_from_data

router = APIRouter(prefix="/api/warehouse", tags=["warehouse"])


def _error(
    status: int, code: str, message: str, retryable: bool = False
) -> JSONResponse:
    # Same four-field envelope as the pipeline and CDC routes (contract Section 8).
    return JSONResponse(
        status_code=status,
        content={
            "error_code": code,
            "message": message,
            "connector_type": None,
            "retryable": retryable,
        },
    )


class WarehouseSession:
    """Opens the warehouse connection on first use, so an unreachable
    database becomes a 503 inside the route rather than an unhandled
    error while FastAPI resolves the dependency."""

    def __init__(self, connection_ref: str) -> None:
        self._ref = connection_ref
        self._layer: Optional[Any] = None

    def generator(self) -> SchemaGenerator:
        if self._layer is None:
            from services.etl_engine.connection_resolver import resolve_connection

            self._layer, _ = resolve_connection("postgresql", self._ref)
        return SchemaGenerator(self._layer)

    def close(self) -> None:
        if self._layer is not None:
            from services.etl_engine.connection_resolver import release_connection

            release_connection(self._layer)
            self._layer = None


def _connect_source(kind: str, ref: str) -> Any:
    from services.etl_engine.connection_resolver import resolve_connection

    layer, _ = resolve_connection(kind, ref)
    return layer


def _release_source(layer: Any) -> None:
    from services.etl_engine.connection_resolver import release_connection

    release_connection(layer)


def get_session() -> Iterator[WarehouseSession]:
    session = WarehouseSession(os.environ.get("WAREHOUSE_REF", DEFAULT_TARGET_REF))
    try:
        yield session
    finally:
        session.close()


def _guarded(build: Callable[[], Any], *, writing: bool = False) -> Any:
    try:
        return build()
    except SchemaConflictError as exc:
        return _error(409, SchemaConflictError.error_code, str(exc))
    except WriteError as exc:
        if writing:
            return _error(500, "WAREHOUSE_GENERATION_FAILED", exc.message)
        return _error(503, exc.error_code, exc.message, retryable=exc.retryable)
    except ConnectorError as exc:
        return _error(503, exc.error_code, exc.message, retryable=exc.retryable)


@router.get("/schemas")
def list_schemas(session: WarehouseSession = Depends(get_session)):
    return _guarded(lambda: session.generator().list_schemas())


@router.post("/schemas/generate")
async def generate_schema(
    request: Request, session: WarehouseSession = Depends(get_session)
):
    # The body is read here, not by FastAPI, so a malformed body still gets
    # the contract's error envelope and "path: reason" message.
    try:
        data = json.loads(await request.body())
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return _error(422, "WAREHOUSE_METADATA_INVALID", f"(root): invalid JSON: {exc}")
    try:
        # Reads the source only when a table leaves its column types out.
        defn = await run_in_threadpool(
            definition_from_data, data, _connect_source, _release_source
        )
    except MetadataValidationError as exc:
        return _error(422, "WAREHOUSE_METADATA_INVALID", "; ".join(exc.errors))
    except ConnectorError as exc:
        return _error(503, exc.error_code, exc.message, retryable=exc.retryable)

    def build() -> JSONResponse:
        schema, created = session.generator().generate(defn)
        return JSONResponse(status_code=201 if created else 200, content=schema)

    # Generation is blocking database work; keep it off the event loop.
    return await run_in_threadpool(_guarded, build, writing=True)
