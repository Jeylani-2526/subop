"""Compare two warehouse schemas table by table (M8W29T3 equality check).

Pass/fail covers what kickoff notes Part B item 4b names: tables, columns,
types, nullability, primary keys and foreign keys. Identity columns and unique
constraints or indexes are listed as well, but do not decide the result.
"""

from __future__ import annotations

import argparse
import sys
from typing import Any, Dict, List, Optional, Tuple

_COLUMNS = """
SELECT a.attname AS name, format_type(a.atttypid, a.atttypmod) AS type,
       a.attnotnull AS not_null, a.attidentity <> '' AS identity
FROM pg_attribute a
JOIN pg_class c ON c.oid = a.attrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = %s AND c.relname = %s AND c.relkind = 'r'
  AND a.attnum > 0 AND NOT a.attisdropped
"""

_CONSTRAINTS = """
SELECT con.contype AS kind,
       ARRAY(SELECT a.attname FROM unnest(con.conkey) WITH ORDINALITY k(num, ord)
             JOIN pg_attribute a ON a.attrelid = con.conrelid AND a.attnum = k.num
             ORDER BY k.ord) AS cols,
       ref.relname AS ref_table,
       ARRAY(SELECT a.attname FROM unnest(con.confkey) WITH ORDINALITY k(num, ord)
             JOIN pg_attribute a ON a.attrelid = con.confrelid AND a.attnum = k.num
             ORDER BY k.ord) AS ref_cols
FROM pg_constraint con
JOIN pg_class c ON c.oid = con.conrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
LEFT JOIN pg_class ref ON ref.oid = con.confrelid
WHERE n.nspname = %s AND c.relname = %s AND con.contype IN ('p', 'f', 'u')
"""

# Unique indexes that no constraint owns, such as a Type 2 "current row" index.
_UNIQUE_INDEXES = """
SELECT ARRAY(SELECT a.attname FROM unnest(i.indkey::int2[]) WITH ORDINALITY k(num, ord)
             JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = k.num
             ORDER BY k.ord) AS cols,
       pg_get_expr(i.indpred, i.indrelid) AS predicate
FROM pg_index i
JOIN pg_class c ON c.oid = i.indrelid
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = %s AND c.relname = %s AND i.indisunique AND NOT i.indisprimary
  AND NOT EXISTS (SELECT 1 FROM pg_constraint con WHERE con.conindid = i.indexrelid)
"""


def describe(layer: Any, schema: str, table: str) -> Optional[Dict[str, Any]]:
    columns = layer.execute_query(_COLUMNS, (schema, table))
    if not columns:
        return None
    constraints = layer.execute_query(_CONSTRAINTS, (schema, table))
    indexes = layer.execute_query(_UNIQUE_INDEXES, (schema, table))
    pk = [tuple(c["cols"]) for c in constraints if c["kind"] == "p"]
    return {
        "columns": {c["name"]: (c["type"], c["not_null"]) for c in columns},
        "primary_key": pk[0] if pk else None,
        # The referenced schema is left out on purpose: dw.x and dw_manual.x
        # are the same target.
        "foreign_keys": sorted(
            (tuple(c["cols"]), c["ref_table"], tuple(c["ref_cols"]))
            for c in constraints
            if c["kind"] == "f"
        ),
        "identity": sorted(c["name"] for c in columns if c["identity"]),
        "unique": sorted(
            [(tuple(c["cols"]), None) for c in constraints if c["kind"] == "u"]
            + [(tuple(i["cols"]), i["predicate"]) for i in indexes]
        ),
    }


def compare_table(
    table: str, a: Optional[Dict[str, Any]], b: Optional[Dict[str, Any]]
) -> Tuple[List[str], List[str]]:
    """(differences that fail the check, differences listed for information)"""
    if a is None or b is None:
        side = "first" if a is None else "second"
        return [f"{table}: missing in the {side} schema"], []
    diffs: List[str] = []
    for name in sorted(set(a["columns"]) | set(b["columns"])):
        left, right = a["columns"].get(name), b["columns"].get(name)
        if left is None or right is None:
            side = "first" if left is None else "second"
            diffs.append(f"{table}.{name}: missing in the {side} schema")
            continue
        if left[0] != right[0]:
            diffs.append(f"{table}.{name}: type {left[0]} vs {right[0]}")
        if left[1] != right[1]:
            nulls = {True: "NOT NULL", False: "NULL"}
            diffs.append(f"{table}.{name}: {nulls[left[1]]} vs {nulls[right[1]]}")
    for key in ("primary_key", "foreign_keys"):
        if a[key] != b[key]:
            diffs.append(f"{table}: {key} {a[key]} vs {b[key]}")
    info = [
        f"{table}: {key} {a[key]} vs {b[key]}"
        for key in ("identity", "unique")
        if a[key] != b[key]
    ]
    return diffs, info


def compare(
    layer: Any, first: str, second: str, tables: List[str]
) -> Tuple[List[str], List[str]]:
    diffs: List[str] = []
    info: List[str] = []
    for table in tables:
        d, i = compare_table(
            table, describe(layer, first, table), describe(layer, second, table)
        )
        diffs += d
        info += i
    return diffs, info


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compare the same tables in two warehouse schemas."
    )
    parser.add_argument("first", help="first schema, e.g. dw")
    parser.add_argument("second", help="second schema, e.g. dw_manual")
    parser.add_argument("tables", nargs="+", help="table names to compare")
    parser.add_argument("--target-ref", default="dw-main")
    args = parser.parse_args(argv)

    from services.connectors.errors import ConnectorError
    from services.etl_engine.connection_resolver import (
        release_connection,
        resolve_connection,
    )
    from services.warehouse.schema_generator import _load_dotenv

    _load_dotenv()
    try:
        layer, _ = resolve_connection("postgresql", args.target_ref)
    except ConnectorError as exc:
        print(f"Compare failed: {exc.error_code}: {exc.message}", file=sys.stderr)
        return 4
    try:
        diffs, info = compare(layer, args.first, args.second, args.tables)
    finally:
        release_connection(layer)

    checked = "tables, columns, types, nullability, primary keys, foreign keys"
    print(f"Compared {args.first} with {args.second}: {', '.join(args.tables)}")
    print(f"Checked: {checked}")
    if diffs:
        print(f"RESULT: DIFFERENT ({len(diffs)})")
        for d in diffs:
            print(f"  - {d}")
    else:
        print("RESULT: IDENTICAL")
    if info:
        print("For information (not part of the check):")
        for i in info:
            print(f"  - {i}")
    return 0 if not diffs else 1


if __name__ == "__main__":
    sys.exit(main())
