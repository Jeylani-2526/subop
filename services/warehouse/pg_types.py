"""Canonical type -> PostgreSQL DDL type for the warehouse (M8W28T3).

type_mapping.py maps native types to canonical ones only. This is the
missing second step the generator needs.
"""

from __future__ import annotations

import re
from typing import Optional

_DDL = {
    "INTEGER": "INTEGER",
    "BIGINT": "BIGINT",
    "DECIMAL": "NUMERIC",
    "VARCHAR": "VARCHAR",
    "TEXT": "TEXT",
    "BOOLEAN": "BOOLEAN",
    "DATE": "DATE",
    # Every warehouse timestamp is stored with its time zone (contract Section 4).
    "TIMESTAMP": "TIMESTAMPTZ",
    "JSON": "JSONB",
    "BINARY": "BYTEA",
}

# How PostgreSQL's format_type() reports each DDL type, used to verify tables.
_FORMATTED = {
    "INTEGER": "integer",
    "BIGINT": "bigint",
    "NUMERIC": "numeric",
    "VARCHAR": "character varying",
    "TEXT": "text",
    "BOOLEAN": "boolean",
    "DATE": "date",
    "TIMESTAMPTZ": "timestamp with time zone",
    "JSONB": "jsonb",
    "BYTEA": "bytea",
}

_PARAMS = re.compile(r"\(\s*(\d+)\s*(?:,\s*(\d+)\s*)?\)")
_MAX_VARCHAR = 10485760
_MAX_NUMERIC_PRECISION = 1000


class PgTypeError(ValueError):
    pass


def pg_type(canonical: str, native: Optional[str] = None) -> str:
    """DDL type for a canonical type; VARCHAR length and NUMERIC precision
    come from the native type when it carries them."""
    base = _DDL.get(canonical)
    if base is None:
        raise PgTypeError(f"no PostgreSQL type for canonical type '{canonical}'")
    if base not in ("VARCHAR", "NUMERIC") or not native:
        return base

    match = _PARAMS.search(native)
    if not match:
        return base
    first = int(match.group(1))
    second = match.group(2)

    if base == "VARCHAR":
        if not 1 <= first <= _MAX_VARCHAR:
            raise PgTypeError(f"VARCHAR length {first} out of range in '{native}'")
        return f"VARCHAR({first})"

    if not 1 <= first <= _MAX_NUMERIC_PRECISION:
        raise PgTypeError(f"NUMERIC precision {first} out of range in '{native}'")
    if second is None:
        return f"NUMERIC({first})"
    scale = int(second)
    if scale > first:
        raise PgTypeError(
            f"NUMERIC scale {scale} exceeds precision {first} in '{native}'"
        )
    return f"NUMERIC({first},{scale})"


def formatted(ddl_type: str) -> str:
    """The string format_type() returns for a DDL type from pg_type()."""
    base, _, params = ddl_type.partition("(")
    name = _FORMATTED[base]
    return f"{name}({params}" if params else name
