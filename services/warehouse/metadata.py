"""Warehouse metadata definitions: Pydantic models and validation (M8W28T2)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from services.abstraction.type_mapping import UniversalTypeMapper, UnsupportedTypeError

LegalBasis = Literal[
    "Consent",
    "Contract",
    "LegalObligation",
    "VitalInterests",
    "PublicTask",
    "LegitimateInterest",
]

IDENTIFIER = re.compile(r"^[a-z_][a-z0-9_]{0,62}$")
SOURCE_TABLE = re.compile(r"^[a-z_][a-z0-9_]{0,62}(\.[a-z_][a-z0-9_]{0,62})?$")

SCD2_COLUMNS = ("valid_from", "valid_to", "is_current")
DATE_COLUMNS = ("full_date", "year", "quarter", "month", "day", "day_of_week")
DATE_SOURCE_TYPES = ("DATE", "TIMESTAMP")


class MetadataValidationError(Exception):
    def __init__(self, errors: List[str]):
        super().__init__("; ".join(errors))
        self.errors = errors


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SourceRef(_Strict):
    # Limited to the databases UniversalTypeMapper can map.
    connector_type: Literal["postgresql", "mysql", "mssql", "sqlite"]
    connection_ref: str = Field(min_length=1)


class DerivedFrom(_Strict):
    kind: Literal["date"]
    column: str


class _Table(_Strict):
    name: str
    columns: Dict[str, str] = Field(default_factory=dict)
    business_key: List[str] = Field(default_factory=list)
    personal_data: bool
    legal_basis: Optional[LegalBasis] = None
    retention_policy_days: Optional[int] = Field(default=None, gt=0)


class Dimension(_Table):
    source_table: Optional[str] = None
    derived_from: Optional[DerivedFrom] = None
    scd_type: Literal[1, 2]
    tracked_attributes: List[str] = Field(default_factory=list)


class Fact(_Table):
    source_table: str
    measures: List[str] = Field(min_length=1)
    dimension_keys: Dict[str, str] = Field(min_length=1)


class WarehouseDefinition(_Strict):
    name: str
    version: int = Field(ge=1)
    description: Optional[str] = None
    source: SourceRef
    fact: Fact
    dimensions: List[Dimension] = Field(min_length=1)

    def dimension(self, name: str) -> Optional[Dimension]:
        return next((d for d in self.dimensions if d.name == name), None)


def surrogate_key(dimension_name: str) -> str:
    # dim_customer -> customer_key; also the fact's foreign-key column name.
    base = dimension_name[4:] if dimension_name.startswith("dim_") else dimension_name
    return f"{base}_key"


def _path(loc: Tuple[Union[str, int], ...]) -> str:
    out = ""
    for part in loc:
        if isinstance(part, int):
            out += f"[{part}]"
        else:
            out += f".{part}" if out else str(part)
    return out or "(root)"


def _check_table(
    defn: WarehouseDefinition, path: str, table: _Table, errors: List[str]
) -> None:
    if not IDENTIFIER.match(table.name):
        errors.append(
            f"{path}.name: must be a lowercase SQL identifier, got '{table.name}'"
        )
    for col, native in table.columns.items():
        if not IDENTIFIER.match(col):
            errors.append(f"{path}.columns.{col}: must be a lowercase SQL identifier")
            continue
        try:
            UniversalTypeMapper.map_type(defn.source.connector_type, native)
        except UnsupportedTypeError as exc:
            errors.append(f"{path}.columns.{col}: {exc}")
    for i, key in enumerate(table.business_key):
        if key not in table.columns:
            errors.append(
                f"{path}.business_key[{i}]: '{key}' is not a column of {table.name}"
            )
    if table.personal_data:
        if table.legal_basis is None:
            errors.append(
                f"{path}.legal_basis: required when personal_data is true (C03)"
            )
        if table.retention_policy_days is None:
            errors.append(
                f"{path}.retention_policy_days: required when personal_data is true (C09)"
            )


def _check_reserved(
    path: str, table: _Table, reserved: List[str], errors: List[str]
) -> None:
    for col in table.columns:
        if col in reserved:
            errors.append(f"{path}.columns.{col}: reserved for a generated column")


def _check_dimension(
    defn: WarehouseDefinition, i: int, dim: Dimension, errors: List[str]
) -> None:
    path = f"dimensions[{i}]"
    if dim.source_table and dim.derived_from:
        errors.append(f"{path}: set source_table or derived_from, not both")
        return
    if not dim.source_table and not dim.derived_from:
        errors.append(f"{path}.source_table: required unless derived_from is set")
        return

    for j, attr in enumerate(dim.tracked_attributes):
        if attr not in dim.columns:
            errors.append(
                f"{path}.tracked_attributes[{j}]: '{attr}' is not a column of {dim.name}"
            )
        elif attr in dim.business_key:
            errors.append(
                f"{path}.tracked_attributes[{j}]: '{attr}' is part of the business key"
            )
    if dim.scd_type == 2 and not dim.tracked_attributes:
        errors.append(
            f"{path}.tracked_attributes: a Type 2 dimension must track at least one"
        )
    if dim.scd_type == 1 and dim.tracked_attributes:
        errors.append(
            f"{path}.tracked_attributes: only Type 2 dimensions track attributes"
        )

    reserved = [surrogate_key(dim.name)]
    if dim.scd_type == 2:
        reserved += list(SCD2_COLUMNS)

    if dim.source_table:
        if not SOURCE_TABLE.match(dim.source_table):
            errors.append(
                f"{path}.source_table: expected 'schema.table', got '{dim.source_table}'"
            )
        if not dim.columns:
            errors.append(f"{path}.columns: must list at least one column")
        if len(dim.business_key) != 1:
            errors.append(f"{path}.business_key: must be exactly one column in M8")
        _check_reserved(path, dim, reserved, errors)
        return

    # Derived dimension: the generator defines its columns and key.
    if dim.columns:
        errors.append(f"{path}.columns: generated for a derived dimension, leave empty")
    if dim.business_key:
        errors.append(
            f"{path}.business_key: generated for a derived dimension, leave empty"
        )
    if dim.scd_type != 1:
        errors.append(f"{path}.scd_type: a derived dimension is Type 1")
    col = dim.derived_from.column
    native = defn.fact.columns.get(col)
    if native is None:
        errors.append(
            f"{path}.derived_from.column: '{col}' is not a column of {defn.fact.name}"
        )
        return
    if defn.fact.dimension_keys.get(col) != dim.name:
        errors.append(
            f"{path}.derived_from.column: fact.dimension_keys.{col} must point to {dim.name}"
        )
    try:
        canonical = UniversalTypeMapper.map_type(defn.source.connector_type, native)
    except UnsupportedTypeError:
        return  # already reported against the fact column
    if canonical.canonical_type not in DATE_SOURCE_TYPES:
        errors.append(
            f"{path}.derived_from.column: '{col}' is {canonical.canonical_type}, "
            "expected DATE or TIMESTAMP"
        )


def _check_fact(defn: WarehouseDefinition, errors: List[str]) -> None:
    fact = defn.fact
    if not SOURCE_TABLE.match(fact.source_table):
        errors.append(
            f"fact.source_table: expected 'schema.table', got '{fact.source_table}'"
        )
    if not fact.business_key:
        errors.append("fact.business_key: must list at least one column")

    for i, measure in enumerate(fact.measures):
        if measure not in fact.columns:
            errors.append(
                f"fact.measures[{i}]: '{measure}' is not a column of {fact.name}"
            )
        elif measure in fact.dimension_keys or measure in fact.business_key:
            errors.append(f"fact.measures[{i}]: '{measure}' is a key, not a measure")

    keyed_by: Dict[str, str] = {}
    for col, dim_name in fact.dimension_keys.items():
        path = f"fact.dimension_keys.{col}"
        if col not in fact.columns:
            errors.append(f"{path}: '{col}' is not a column of {fact.name}")
        if defn.dimension(dim_name) is None:
            errors.append(f"{path}: unknown dimension '{dim_name}'")
        elif dim_name in keyed_by:
            errors.append(
                f"{path}: {dim_name} is already keyed by '{keyed_by[dim_name]}'"
            )
        else:
            keyed_by[dim_name] = col

    for i, dim in enumerate(defn.dimensions):
        if dim.name not in keyed_by:
            errors.append(
                f"dimensions[{i}]: '{dim.name}' is not referenced by fact.dimension_keys"
            )

    _check_reserved("fact", fact, [surrogate_key(d) for d in keyed_by], errors)


def _check(defn: WarehouseDefinition) -> List[str]:
    errors: List[str] = []
    if not IDENTIFIER.match(defn.name):
        errors.append(f"name: must be a lowercase SQL identifier, got '{defn.name}'")

    tables = [("fact", defn.fact)] + [
        (f"dimensions[{i}]", d) for i, d in enumerate(defn.dimensions)
    ]
    seen: Dict[str, str] = {}
    for path, table in tables:
        _check_table(defn, path, table, errors)
        if table.name in seen:
            errors.append(
                f"{path}.name: '{table.name}' is already used by {seen[table.name]}"
            )
        seen.setdefault(table.name, path)

    _check_fact(defn, errors)
    for i, dim in enumerate(defn.dimensions):
        _check_dimension(defn, i, dim, errors)
    return errors


def validate_definition(data: Any) -> WarehouseDefinition:
    """Validate a parsed definition; raises MetadataValidationError with field paths."""
    try:
        defn = WarehouseDefinition.model_validate(data)
    except ValidationError as exc:
        raise MetadataValidationError(
            [f"{_path(e['loc'])}: {e['msg']}" for e in exc.errors()]
        ) from None
    errors = _check(defn)
    if errors:
        raise MetadataValidationError(errors)
    return defn


def load_definition(path: Union[str, Path]) -> WarehouseDefinition:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise MetadataValidationError([f"(root): invalid JSON: {exc}"]) from None
    return validate_definition(data)
