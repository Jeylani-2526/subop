"""Read column names and native types from the source database (G5: "from source metadata").

A sourced table in a definition may now give its columns three ways:
  - "columns": {"col": "native type", ...}  as before; the source is not read
  - "columns": ["col", ...]                  names only; types read from the source
  - no "columns" key                         every column, in source order
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from services.warehouse.metadata import (
    MetadataValidationError,
    WarehouseDefinition,
    validate_definition,
)

Catalog = Callable[[str], Optional[Dict[str, str]]]

_PG_COLUMNS = """
SELECT a.attname AS name, format_type(a.atttypid, a.atttypmod) AS native
FROM pg_attribute a
JOIN pg_class c ON c.oid = a.attrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = %s AND c.relname = %s AND c.relkind IN ('r', 'p', 'v', 'm', 'f')
  AND a.attnum > 0 AND NOT a.attisdropped
ORDER BY a.attnum
"""


def postgres_catalog(layer: Any) -> Catalog:
    def columns(source_table: str) -> Optional[Dict[str, str]]:
        schema, _, table = source_table.rpartition(".")
        rows = layer.execute_query(_PG_COLUMNS, (schema or "public", table))
        return {r["name"]: r["native"] for r in rows} or None

    return columns


# Only PostgreSQL is read today; other sources list their columns with types.
CATALOGS: Dict[str, Callable[[Any], Catalog]] = {"postgresql": postgres_catalog}


def _sourced_tables(data: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
    tables = []
    if isinstance(data.get("fact"), dict):
        tables.append(("fact", data["fact"]))
    dims = data.get("dimensions")
    for i, dim in enumerate(dims if isinstance(dims, list) else []):
        if isinstance(dim, dict) and dim.get("source_table"):
            tables.append((f"dimensions[{i}]", dim))
    return tables


def needs_source(data: Any) -> bool:
    if not isinstance(data, dict):
        return False
    return any(not isinstance(t.get("columns"), dict) for _, t in _sourced_tables(data))


def resolve_columns(data: Dict[str, Any], catalog: Catalog) -> Dict[str, Any]:
    """Fill in missing or names-only columns from the catalog. Returns a copy."""
    out = copy.deepcopy(data)
    errors: List[str] = []
    for path, table in _sourced_tables(out):
        given = table.get("columns")
        if isinstance(given, dict):
            continue
        source_table = table.get("source_table")
        if not isinstance(source_table, str):
            continue  # validation reports it
        found = catalog(source_table)
        if found is None:
            errors.append(
                f"{path}.source_table: '{source_table}' not found in the source database"
            )
            continue
        if given is None:
            table["columns"] = dict(found)
            continue
        if not isinstance(given, list):
            continue  # validation reports it
        picked: Dict[str, str] = {}
        for j, name in enumerate(given):
            if name not in found:
                errors.append(
                    f"{path}.columns[{j}]: '{name}' is not a column of {source_table}"
                )
            else:
                picked[name] = found[name]
        table["columns"] = picked
    if errors:
        raise MetadataValidationError(errors)
    return out


def definition_from_data(
    data: Any,
    connect: Callable[[str, str], Any],
    release: Callable[[Any], None],
) -> WarehouseDefinition:
    """Validate a parsed definition, reading the source only when it must.
    `connect` may raise ConnectorError; callers map it (exit code or 503)."""
    if not needs_source(data):
        return validate_definition(data)
    source = data.get("source") if isinstance(data.get("source"), dict) else {}
    kind, ref = source.get("connector_type"), source.get("connection_ref")
    if not isinstance(kind, str) or not isinstance(ref, str):
        return validate_definition(data)  # reports the missing source fields
    if kind not in CATALOGS:
        raise MetadataValidationError(
            [
                f"source.connector_type: columns can be read from "
                f"{', '.join(CATALOGS)} sources only; list each column with its "
                f"native type for '{kind}'"
            ]
        )
    layer = connect(kind, ref)
    try:
        resolved = resolve_columns(data, CATALOGS[kind](layer))
    finally:
        release(layer)
    return validate_definition(resolved)


def read_json(path: Union[str, Path]) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise MetadataValidationError([f"(root): invalid JSON: {exc}"]) from None


def load_with_source(path: Union[str, Path]) -> WarehouseDefinition:
    """CLI helper: read a definition file, reading the source if needed."""
    from services.etl_engine.connection_resolver import (
        release_connection,
        resolve_connection,
    )

    def connect(kind: str, ref: str) -> Any:
        layer, _ = resolve_connection(kind, ref)
        return layer

    return definition_from_data(read_json(path), connect, release_connection)
