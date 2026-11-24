"""Warehouse schema generator: metadata definition -> star schema (M8W28T3)."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from services.abstraction.type_mapping import UniversalTypeMapper
from services.warehouse.metadata import (
    DATE_COLUMNS,
    IDENTIFIER,
    Dimension,
    MetadataValidationError,
    WarehouseDefinition,
    surrogate_key,
)
from services.warehouse.pg_types import formatted, pg_type

TARGET_SCHEMA = "dw"
META_SCHEMA = "dw_meta"
DEFAULT_TARGET_REF = "dw-main"


class SchemaConflictError(Exception):
    error_code = "WAREHOUSE_SCHEMA_CONFLICT"


@dataclass(frozen=True)
class ColumnPlan:
    name: str
    role: str
    native_type: Optional[str]
    canonical_type: str
    warehouse_type: str
    nullable: bool = True
    identity: bool = False
    references: Optional[str] = None


@dataclass(frozen=True)
class TablePlan:
    name: str
    role: str
    columns: Tuple[ColumnPlan, ...]
    primary_key: Tuple[str, ...]
    business_key: Tuple[str, ...]
    unique: Tuple[str, ...] = ()
    current_unique: Tuple[str, ...] = ()
    foreign_keys: Tuple[Tuple[str, str, str], ...] = ()  # (column, table, column)
    info: Optional[Dict[str, Any]] = None


# -- plan: pure, no database ------------------------------------------------


def _canonical(defn: WarehouseDefinition, native: str) -> str:
    return UniversalTypeMapper.map_type(
        defn.source.connector_type, native
    ).canonical_type


def _declared(
    defn: WarehouseDefinition, name: str, native: str, role: str, nullable: bool
):
    canonical = _canonical(defn, native)
    return ColumnPlan(
        name, role, native, canonical, pg_type(canonical, native), nullable
    )


def _generated(name: str, role: str, canonical: str, nullable: bool = False, **kw):
    return ColumnPlan(name, role, None, canonical, pg_type(canonical), nullable, **kw)


def _compliance(table: Any) -> Dict[str, Any]:
    return {
        "personal_data": table.personal_data,
        "legal_basis": table.legal_basis,
        "retention_policy_days": table.retention_policy_days,
    }


def _date_dimension(dim: Dimension) -> TablePlan:
    key = surrogate_key(dim.name)
    columns = (_generated(key, "surrogate_key", "INTEGER"),) + tuple(
        _generated(c, "date_part", "DATE" if c == "full_date" else "INTEGER")
        for c in DATE_COLUMNS
    )
    info = {
        "source_table": None,
        "derived_from": dim.derived_from.model_dump(),
        "scd_type": dim.scd_type,
        "tracked_attributes": [],
        "measures": [],
        **_compliance(dim),
    }
    return TablePlan(
        dim.name,
        "dimension",
        columns,
        (key,),
        ("full_date",),
        unique=("full_date",),
        info=info,
    )


def _sourced_dimension(defn: WarehouseDefinition, dim: Dimension) -> TablePlan:
    key = surrogate_key(dim.name)
    columns = [_generated(key, "surrogate_key", "BIGINT", identity=True)]
    for name, native in dim.columns.items():
        if name in dim.business_key:
            role = "business_key"
        elif name in dim.tracked_attributes:
            role = "tracked_attribute"
        else:
            role = "attribute"
        columns.append(
            _declared(defn, name, native, role, nullable=role != "business_key")
        )
    if dim.scd_type == 2:
        columns += [
            _generated("valid_from", "scd_metadata", "TIMESTAMP"),
            _generated("valid_to", "scd_metadata", "TIMESTAMP", nullable=True),
            _generated("is_current", "scd_metadata", "BOOLEAN"),
        ]
    bk = tuple(dim.business_key)
    info = {
        "source_table": dim.source_table,
        "derived_from": None,
        "scd_type": dim.scd_type,
        "tracked_attributes": list(dim.tracked_attributes),
        "measures": [],
        **_compliance(dim),
    }
    return TablePlan(
        dim.name,
        "dimension",
        tuple(columns),
        (key,),
        bk,
        # Type 2 keeps one row per version, so only the current one is unique.
        unique=bk if dim.scd_type == 1 else (),
        current_unique=bk if dim.scd_type == 2 else (),
        info=info,
    )


def _fact(
    defn: WarehouseDefinition, schema: str, dims: Dict[str, TablePlan]
) -> TablePlan:
    fact = defn.fact
    columns = []
    for name, native in fact.columns.items():
        if name in fact.business_key:
            role = "business_key"
        elif name in fact.dimension_keys:
            role = "dimension_ref"
        elif name in fact.measures:
            role = "measure"
        else:
            role = "attribute"
        columns.append(
            _declared(defn, name, native, role, nullable=role != "business_key")
        )

    foreign_keys = []
    for dim_name in fact.dimension_keys.values():
        key = surrogate_key(dim_name)
        target = next(c for c in dims[dim_name].columns if c.name == key)
        columns.append(
            _generated(
                key,
                "foreign_key",
                target.canonical_type,
                nullable=True,
                references=f"{schema}.{dim_name}.{key}",
            )
        )
        foreign_keys.append((key, dim_name, key))

    info = {
        "source_table": fact.source_table,
        "derived_from": None,
        "scd_type": None,
        "tracked_attributes": [],
        "measures": list(fact.measures),
        **_compliance(fact),
    }
    bk = tuple(fact.business_key)
    return TablePlan(
        fact.name,
        "fact",
        tuple(columns),
        bk,
        bk,
        foreign_keys=tuple(foreign_keys),
        info=info,
    )


def plan_schema(
    defn: WarehouseDefinition, schema: str = TARGET_SCHEMA
) -> List[TablePlan]:
    """Dimensions first (foreign-key targets), then the fact."""
    dims = {
        d.name: _date_dimension(d) if d.derived_from else _sourced_dimension(defn, d)
        for d in defn.dimensions
    }
    return list(dims.values()) + [_fact(defn, schema, dims)]


# -- DDL --------------------------------------------------------------------


def _column_ddl(col: ColumnPlan) -> str:
    parts = [col.name, col.warehouse_type]
    if col.identity:
        parts.append("GENERATED ALWAYS AS IDENTITY")
    if not col.nullable:
        parts.append("NOT NULL")
    return " ".join(parts)


def table_ddl(schema: str, table: TablePlan) -> List[str]:
    lines = [_column_ddl(c) for c in table.columns]
    lines.append(f"PRIMARY KEY ({', '.join(table.primary_key)})")
    if table.unique:
        lines.append(f"UNIQUE ({', '.join(table.unique)})")
    for col, ref_table, ref_col in table.foreign_keys:
        lines.append(f"FOREIGN KEY ({col}) REFERENCES {schema}.{ref_table} ({ref_col})")
    body = ",\n    ".join(lines)
    statements = [f"CREATE TABLE IF NOT EXISTS {schema}.{table.name} (\n    {body}\n)"]
    if table.current_unique:
        statements.append(
            f"CREATE UNIQUE INDEX IF NOT EXISTS {table.name}_current_uq "
            f"ON {schema}.{table.name} ({', '.join(table.current_unique)}) "
            f"WHERE is_current"
        )
    return statements


def schema_ddl(schema: str, plan: List[TablePlan]) -> List[str]:
    statements = [f"CREATE SCHEMA IF NOT EXISTS {schema}"]
    for table in plan:
        statements += table_ddl(schema, table)
    return statements


# -- contract shape ---------------------------------------------------------


def describe_tables(schema: str, plan: List[TablePlan]) -> List[Dict[str, Any]]:
    """Tables as warehouse_api_contract.md Section 2 shows them: fact first."""
    ordered = [t for t in plan if t.role == "fact"] + [
        t for t in plan if t.role != "fact"
    ]
    return [
        {
            "name": t.name,
            "qualified_name": f"{schema}.{t.name}",
            "role": t.role,
            "source_table": t.info["source_table"],
            "derived_from": t.info["derived_from"],
            "scd_type": t.info["scd_type"],
            "tracked_attributes": t.info["tracked_attributes"],
            "business_key": list(t.business_key),
            "measures": t.info["measures"],
            "personal_data": t.info["personal_data"],
            "legal_basis": t.info["legal_basis"],
            "retention_policy_days": t.info["retention_policy_days"],
            "columns": [
                {
                    "name": c.name,
                    "role": c.role,
                    "native_type": c.native_type,
                    "canonical_type": c.canonical_type,
                    "warehouse_type": c.warehouse_type,
                    "references": c.references,
                }
                for c in t.columns
            ],
        }
        for t in ordered
    ]


def fingerprint(defn: WarehouseDefinition) -> str:
    canonical = json.dumps(
        defn.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# -- database ---------------------------------------------------------------


def _json(value: Any) -> Any:
    return json.loads(value) if isinstance(value, str) else value


class SchemaGenerator:
    """Creates a validated definition's star schema and records it in the
    registry. Every statement is one execute_write: the Postgres connector
    commits after each, so a re-run picks up wherever a failed run stopped."""

    def __init__(
        self, layer: Any, schema: str = TARGET_SCHEMA, meta_schema: str = META_SCHEMA
    ) -> None:
        for name in (schema, meta_schema):
            if not IDENTIFIER.match(name):
                raise ValueError(f"not a valid schema name: '{name}'")
        self._layer = layer
        self.schema = schema
        self.registry = f"{meta_schema}.schema_registry"
        self._meta_schema = meta_schema

    def ensure_registry(self) -> None:
        self._layer.execute_write(f"CREATE SCHEMA IF NOT EXISTS {self._meta_schema}")
        self._layer.execute_write(f"""
            CREATE TABLE IF NOT EXISTS {self.registry} (
                schema_id      TEXT        PRIMARY KEY,
                name           TEXT        NOT NULL,
                version        INTEGER     NOT NULL,
                description    TEXT,
                target_schema  TEXT        NOT NULL,
                source         JSONB       NOT NULL,
                fingerprint    TEXT        NOT NULL,
                definition     JSONB       NOT NULL,
                tables         JSONB       NOT NULL,
                generated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """)

    def generate(self, defn: WarehouseDefinition) -> Tuple[Dict[str, Any], bool]:
        """Returns (schema, created). created is False when the same
        definition was already generated; nothing changes then."""
        self.ensure_registry()
        plan = plan_schema(defn, self.schema)
        fp = fingerprint(defn)
        self._check_registry(defn, plan, fp)
        # Before: a table already there with another shape stops the run with
        # nothing created. After: every table must now match the plan exactly.
        self._verify(plan, allow_missing=True)

        for statement in schema_ddl(self.schema, plan):
            self._layer.execute_write(statement)
        self._verify(plan)

        created = self._register(defn, plan, fp) == 1
        return self.get_schema(defn.name), created

    def list_schemas(self) -> List[Dict[str, Any]]:
        self.ensure_registry()
        rows = self._layer.execute_query(
            f"SELECT schema_id, name, version, description, target_schema, source, "
            f"generated_at, tables FROM {self.registry} ORDER BY generated_at, schema_id"
        )
        return [self._row_to_schema(r) for r in rows]

    def get_schema(self, schema_id: str) -> Optional[Dict[str, Any]]:
        return next(
            (s for s in self.list_schemas() if s["schema_id"] == schema_id), None
        )

    def _check_registry(
        self, defn: WarehouseDefinition, plan: List[TablePlan], fp: str
    ):
        rows = self._layer.execute_query(
            f"SELECT schema_id, version, fingerprint, target_schema, tables FROM {self.registry}"
        )
        wanted = {t.name for t in plan}
        for row in rows:
            if row["schema_id"] == defn.name:
                if row["fingerprint"] != fp:
                    raise SchemaConflictError(
                        f"'{defn.name}' version {row['version']} was already generated from "
                        "a different definition; changing a schema needs versioning, "
                        "which is deferred"
                    )
                continue
            if row["target_schema"] != self.schema:
                continue
            taken = wanted & {t["name"] for t in _json(row["tables"])}
            if taken:
                raise SchemaConflictError(
                    f"{', '.join(sorted(taken))} already belong to '{row['schema_id']}' "
                    f"in schema {self.schema}"
                )

    def _verify(self, plan: List[TablePlan], allow_missing: bool = False) -> None:
        # CREATE TABLE IF NOT EXISTS skips a table that already exists, so a
        # table left with another shape would pass silently without this.
        rows = self._layer.execute_query(
            "SELECT c.relname AS table_name, a.attname AS column_name, "
            "format_type(a.atttypid, a.atttypmod) AS data_type "
            "FROM pg_attribute a "
            "JOIN pg_class c ON c.oid = a.attrelid "
            "JOIN pg_namespace n ON n.oid = c.relnamespace "
            "WHERE n.nspname = %s AND c.relname = ANY(%s) "
            "AND a.attnum > 0 AND NOT a.attisdropped "
            "ORDER BY c.relname, a.attnum",
            (self.schema, [t.name for t in plan]),
        )
        actual: Dict[str, List[Tuple[str, str]]] = {}
        for row in rows:
            actual.setdefault(row["table_name"], []).append(
                (row["column_name"], row["data_type"])
            )
        for table in plan:
            if allow_missing and table.name not in actual:
                continue
            expected = [(c.name, formatted(c.warehouse_type)) for c in table.columns]
            if actual.get(table.name) != expected:
                raise SchemaConflictError(
                    f"{self.schema}.{table.name} already exists with different columns: "
                    f"expected {expected}, found {actual.get(table.name)}"
                )

    def _register(
        self, defn: WarehouseDefinition, plan: List[TablePlan], fp: str
    ) -> int:
        return self._layer.execute_write(
            f"INSERT INTO {self.registry} (schema_id, name, version, description, "
            f"target_schema, source, fingerprint, definition, tables) "
            f"VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s, %s::jsonb, %s::jsonb) "
            f"ON CONFLICT (schema_id) DO NOTHING",
            (
                defn.name,
                defn.name,
                defn.version,
                defn.description,
                self.schema,
                json.dumps(defn.source.model_dump()),
                fp,
                json.dumps(defn.model_dump(mode="json")),
                json.dumps(describe_tables(self.schema, plan)),
            ),
        )

    @staticmethod
    def _row_to_schema(row: Dict[str, Any]) -> Dict[str, Any]:
        generated_at = row["generated_at"]
        return {
            "schema_id": row["schema_id"],
            "name": row["name"],
            "version": row["version"],
            "description": row["description"],
            "target_schema": row["target_schema"],
            "source": _json(row["source"]),
            "generated_at": (
                generated_at.isoformat()
                if hasattr(generated_at, "isoformat")
                else generated_at
            ),
            "tables": _json(row["tables"]),
        }


# -- command line -----------------------------------------------------------


def _load_dotenv() -> None:
    # As in cdc_demo_changes.py (M7W26T1 Finding 6): host-run scripts need .env.
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    from pathlib import Path

    load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate a warehouse star schema from a metadata definition."
    )
    parser.add_argument("definition", help="path to a definition JSON file")
    parser.add_argument(
        "--target-ref",
        default=DEFAULT_TARGET_REF,
        help=f"warehouse connection ref (default: {DEFAULT_TARGET_REF})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the DDL without touching a database",
    )
    args = parser.parse_args(argv)

    from services.connectors.errors import ConnectorError
    from services.warehouse.source_catalog import load_with_source

    _load_dotenv()
    try:
        defn = load_with_source(args.definition)
    except MetadataValidationError as exc:
        print("Definition is invalid:", file=sys.stderr)
        for error in exc.errors:
            print(f"  - {error}", file=sys.stderr)
        return 2
    except ConnectorError as exc:
        print(f"Source unreachable: {exc.error_code}: {exc.message}", file=sys.stderr)
        return 4

    if args.dry_run:
        for statement in schema_ddl(TARGET_SCHEMA, plan_schema(defn)):
            print(statement + ";\n")
        return 0

    from services.etl_engine.connection_resolver import resolve_connection

    try:
        layer, _ = resolve_connection("postgresql", args.target_ref)
    except ConnectorError as exc:
        print(
            f"Warehouse unreachable: {exc.error_code}: {exc.message}", file=sys.stderr
        )
        return 4
    try:
        schema, created = SchemaGenerator(layer).generate(defn)
    except SchemaConflictError as exc:
        print(f"Conflict: {exc}", file=sys.stderr)
        return 3

    state = "created" if created else "unchanged (already generated)"
    print(f"{schema['schema_id']} v{schema['version']}: {state}")
    for table in schema["tables"]:
        print(f"  {table['qualified_name']}: {len(table['columns'])} columns")
    return 0


if __name__ == "__main__":
    sys.exit(main())
