"""tests/test_schema_generator.py — M8W28T3.

pg_types and the plan are tested without a database. Generation runs against
a real PostgreSQL through the Abstraction Layer (CI's postgres:15; no logical
replication needed), each test in its own throwaway schemas.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest

from services.abstraction.abstraction_layer import AbstractionLayer
from services.connectors.errors import WriteError
from services.warehouse.metadata import load_definition, validate_definition
from services.warehouse.pg_types import PgTypeError, formatted, pg_type
from services.warehouse.schema_generator import (
    SchemaConflictError,
    SchemaGenerator,
    main,
    plan_schema,
    schema_ddl,
)

DEMO = (
    Path(__file__).resolve().parents[1]
    / "services"
    / "warehouse"
    / "definitions"
    / "demo_orders_star.json"
)

EXPECTED = {
    "dim_customer": [
        ("customer_key", "surrogate_key", "BIGINT"),
        ("id", "business_key", "BIGINT"),
        ("name", "attribute", "VARCHAR(64)"),
        ("city", "tracked_attribute", "VARCHAR(64)"),
        ("valid_from", "scd_metadata", "TIMESTAMPTZ"),
        ("valid_to", "scd_metadata", "TIMESTAMPTZ"),
        ("is_current", "scd_metadata", "BOOLEAN"),
    ],
    "dim_date": [
        ("date_key", "surrogate_key", "INTEGER"),
        ("full_date", "date_part", "DATE"),
        ("year", "date_part", "INTEGER"),
        ("quarter", "date_part", "INTEGER"),
        ("month", "date_part", "INTEGER"),
        ("day", "date_part", "INTEGER"),
        ("day_of_week", "date_part", "INTEGER"),
    ],
    "fact_orders": [
        ("id", "business_key", "BIGINT"),
        ("customer_id", "dimension_ref", "BIGINT"),
        ("status", "attribute", "VARCHAR(32)"),
        ("amount", "measure", "NUMERIC(12,2)"),
        ("created_at", "dimension_ref", "TIMESTAMPTZ"),
        ("customer_key", "foreign_key", "BIGINT"),
        ("date_key", "foreign_key", "INTEGER"),
    ],
}


@pytest.fixture
def demo_dict():
    return json.loads(DEMO.read_text(encoding="utf-8"))


@pytest.fixture
def demo():
    return load_definition(DEMO)


# -- pg_types ---------------------------------------------------------------


@pytest.mark.parametrize(
    "canonical, native, expected",
    [
        ("BIGINT", "bigint", "BIGINT"),
        ("INTEGER", "int(11)", "INTEGER"),
        ("VARCHAR", "varchar(32)", "VARCHAR(32)"),
        ("VARCHAR", "character varying", "VARCHAR"),
        ("DECIMAL", "numeric(12,2)", "NUMERIC(12,2)"),
        ("DECIMAL", "decimal(10)", "NUMERIC(10)"),
        ("DECIMAL", "numeric", "NUMERIC"),
        ("TIMESTAMP", "timestamp without time zone", "TIMESTAMPTZ"),
        ("TIMESTAMP", "timestamptz", "TIMESTAMPTZ"),
        ("JSON", "jsonb", "JSONB"),
        ("BINARY", "bytea", "BYTEA"),
        ("BOOLEAN", None, "BOOLEAN"),
    ],
)
def test_pg_type(canonical, native, expected):
    assert pg_type(canonical, native) == expected


@pytest.mark.parametrize(
    "canonical, native",
    [("UUID", None), ("VARCHAR", "varchar(0)"), ("DECIMAL", "numeric(5,7)")],
)
def test_pg_type_rejects_what_postgres_cannot_create(canonical, native):
    with pytest.raises(PgTypeError):
        pg_type(canonical, native)


@pytest.mark.parametrize(
    "ddl, expected",
    [
        ("NUMERIC(12,2)", "numeric(12,2)"),
        ("VARCHAR(64)", "character varying(64)"),
        ("TIMESTAMPTZ", "timestamp with time zone"),
        ("BIGINT", "bigint"),
    ],
)
def test_formatted_matches_format_type(ddl, expected):
    assert formatted(ddl) == expected


# -- plan and DDL (no database) ---------------------------------------------


def test_plan_matches_the_contract(demo):
    plan = {t.name: t for t in plan_schema(demo)}
    assert [t.name for t in plan_schema(demo)] == [
        "dim_customer",
        "dim_date",
        "fact_orders",
    ]
    for name, columns in EXPECTED.items():
        got = [(c.name, c.role, c.warehouse_type) for c in plan[name].columns]
        assert got == columns, name
    assert plan["fact_orders"].columns[5].references == "dw.dim_customer.customer_key"


def test_every_statement_is_create_if_not_exists(demo):
    statements = schema_ddl("dw", plan_schema(demo))
    assert statements[0] == "CREATE SCHEMA IF NOT EXISTS dw"
    for statement in statements[1:]:
        assert statement.startswith(
            ("CREATE TABLE IF NOT EXISTS", "CREATE UNIQUE INDEX IF NOT")
        )


def test_type_1_dimension_is_unique_on_its_business_key(demo_dict):
    demo_dict["dimensions"][0]["scd_type"] = 1
    demo_dict["dimensions"][0]["tracked_attributes"] = []
    plan = plan_schema(validate_definition(demo_dict))
    customer = plan[0]
    assert customer.unique == ("id",) and customer.current_unique == ()
    assert "valid_from" not in [c.name for c in customer.columns]


def test_cli_dry_run_prints_ddl(capsys):
    assert main([str(DEMO), "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "CREATE TABLE IF NOT EXISTS dw.fact_orders" in out


def test_cli_reports_an_invalid_definition(tmp_path, demo_dict, capsys):
    del demo_dict["fact"]["legal_basis"]
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(demo_dict), encoding="utf-8")
    assert main([str(bad), "--dry-run"]) == 2
    assert "fact.legal_basis" in capsys.readouterr().err


# -- generation against a real PostgreSQL -----------------------------------


class _RecordingLayer:
    def __init__(self, layer):
        self._layer = layer
        self.writes = []

    def execute_write(self, sql, params=None):
        self.writes.append(sql)
        return self._layer.execute_write(sql, params)

    def execute_query(self, sql, params=None):
        return self._layer.execute_query(sql, params)


@pytest.fixture
def layer(test_db_connection):
    return AbstractionLayer(connector=test_db_connection, database="postgresql")


@pytest.fixture
def schemas(layer):
    suffix = uuid.uuid4().hex[:8]
    names = (f"test_dw_{suffix}", f"test_dwmeta_{suffix}")
    yield names
    for name in names:
        layer.execute_write(f"DROP SCHEMA IF EXISTS {name} CASCADE")


@pytest.fixture
def generator(layer, schemas):
    return SchemaGenerator(layer, schema=schemas[0], meta_schema=schemas[1])


def snapshot(layer, schema):
    """Everything a second run could change, read from information_schema."""
    columns = layer.execute_query(
        "SELECT table_name, column_name, ordinal_position, data_type, is_nullable, "
        "character_maximum_length, numeric_precision, numeric_scale, is_identity "
        "FROM information_schema.columns WHERE table_schema = %s "
        "ORDER BY table_name, ordinal_position",
        (schema,),
    )
    constraints = layer.execute_query(
        "SELECT table_name, constraint_name, constraint_type "
        "FROM information_schema.table_constraints WHERE table_schema = %s "
        "ORDER BY table_name, constraint_name",
        (schema,),
    )
    indexes = layer.execute_query(
        "SELECT indexname, indexdef FROM pg_indexes WHERE schemaname = %s "
        "ORDER BY indexname",
        (schema,),
    )
    return (
        [dict(r) for r in columns],
        [dict(r) for r in constraints],
        [dict(r) for r in indexes],
    )


def test_generate_creates_the_star_schema(generator, layer, demo):
    schema, created = generator.generate(demo)
    assert created is True
    columns, constraints, _ = snapshot(layer, generator.schema)
    tables = {}
    for row in columns:
        tables.setdefault(row["table_name"], []).append(row["column_name"])
    assert tables == {name: [c[0] for c in cols] for name, cols in EXPECTED.items()}
    kinds = {(r["table_name"], r["constraint_type"]) for r in constraints}
    assert ("fact_orders", "FOREIGN KEY") in kinds
    assert ("dim_date", "UNIQUE") in kinds
    assert [t["name"] for t in schema["tables"]] == [
        "fact_orders",
        "dim_customer",
        "dim_date",
    ]


def test_second_run_changes_nothing(generator, layer, demo):
    first, created = generator.generate(demo)
    before = snapshot(layer, generator.schema)
    second, created_again = generator.generate(demo)
    assert created is True and created_again is False
    assert snapshot(layer, generator.schema) == before
    assert second == first


def test_every_write_goes_through_execute_write(layer, schemas, demo):
    recording = _RecordingLayer(layer)
    SchemaGenerator(recording, schema=schemas[0], meta_schema=schemas[1]).generate(demo)
    ddl = schema_ddl(schemas[0], plan_schema(demo, schemas[0]))
    assert all(statement in recording.writes for statement in ddl)
    assert any("INSERT INTO" in sql for sql in recording.writes)


def test_registry_keeps_the_compliance_fields(generator, demo):
    generator.generate(demo)
    [schema] = generator.list_schemas()
    assert schema["schema_id"] == "demo_orders_star"
    assert schema["target_schema"] == generator.schema
    assert isinstance(schema["generated_at"], str)
    fact = schema["tables"][0]
    assert (
        fact["personal_data"],
        fact["legal_basis"],
        fact["retention_policy_days"],
    ) == (
        True,
        "Contract",
        3650,
    )
    assert generator.get_schema("nope") is None


def test_list_is_empty_before_generation(generator):
    assert generator.list_schemas() == []


def test_changed_definition_with_the_same_name_conflicts(
    generator, layer, demo, demo_dict
):
    generator.generate(demo)
    before = snapshot(layer, generator.schema)
    demo_dict["fact"]["columns"]["discount"] = "numeric(5,2)"
    with pytest.raises(SchemaConflictError):
        generator.generate(validate_definition(demo_dict))
    assert snapshot(layer, generator.schema) == before


def test_tables_owned_by_another_schema_conflict(generator, demo, demo_dict):
    generator.generate(demo)
    demo_dict["name"] = "other_star"
    with pytest.raises(SchemaConflictError, match="demo_orders_star"):
        generator.generate(validate_definition(demo_dict))


def test_existing_table_with_another_shape_conflicts(generator, layer, demo):
    layer.execute_write(f"CREATE SCHEMA {generator.schema}")
    layer.execute_write(f"CREATE TABLE {generator.schema}.dim_date (date_key INTEGER)")
    with pytest.raises(SchemaConflictError, match="dim_date"):
        generator.generate(demo)
    assert generator.list_schemas() == []
    columns, _, _ = snapshot(layer, generator.schema)
    assert {r["table_name"] for r in columns} == {"dim_date"}  # nothing else was built


def test_only_one_current_row_per_customer(generator, layer, demo):
    generator.generate(demo)
    insert = (
        f"INSERT INTO {generator.schema}.dim_customer (id, name, city, valid_from, is_current) "
        "VALUES (1, 'Ayse', %s, now(), %s)"
    )
    layer.execute_write(insert, ("Ankara", False))
    layer.execute_write(insert, ("Izmir", True))
    with pytest.raises(WriteError):
        layer.execute_write(insert, ("Bursa", True))


def test_fact_foreign_key_is_enforced(generator, layer, demo):
    generator.generate(demo)
    with pytest.raises(WriteError):
        layer.execute_write(
            f"INSERT INTO {generator.schema}.fact_orders (id, customer_key) VALUES (1, 999)"
        )
