"""tests/test_schema_compare.py — M8W29T3 equality check.

The demo star is generated into one throwaway schema and written by hand into
another; the check must find them identical, then catch each kind of drift.
"""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from services.abstraction.abstraction_layer import AbstractionLayer
from services.warehouse.metadata import load_definition
from services.warehouse.schema_compare import compare
from services.warehouse.schema_generator import SchemaGenerator

DEMO = (
    Path(__file__).resolve().parents[1]
    / "services"
    / "warehouse"
    / "definitions"
    / "demo_orders_star.json"
)
TABLES = ["fact_orders", "dim_customer", "dim_date"]

HAND_DDL = """
CREATE TABLE {s}.dim_customer (
    customer_key BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id BIGINT NOT NULL, name VARCHAR(64), city VARCHAR(64),
    valid_from TIMESTAMPTZ NOT NULL, valid_to TIMESTAMPTZ, is_current BOOLEAN NOT NULL);
CREATE UNIQUE INDEX dim_customer_current_uq ON {s}.dim_customer (id) WHERE is_current;
CREATE TABLE {s}.dim_date (
    date_key INTEGER PRIMARY KEY, full_date DATE NOT NULL UNIQUE, year INTEGER NOT NULL,
    quarter INTEGER NOT NULL, month INTEGER NOT NULL, day INTEGER NOT NULL,
    day_of_week INTEGER NOT NULL);
CREATE TABLE {s}.fact_orders (
    id BIGINT PRIMARY KEY, customer_id BIGINT, status VARCHAR(32), amount NUMERIC(12,2),
    created_at TIMESTAMPTZ,
    customer_key BIGINT REFERENCES {s}.dim_customer (customer_key),
    date_key INTEGER REFERENCES {s}.dim_date (date_key));
"""


@pytest.fixture
def layer(test_db_connection):
    return AbstractionLayer(connector=test_db_connection, database="postgresql")


@pytest.fixture
def schemas(layer):
    suffix = uuid.uuid4().hex[:8]
    gen, hand, meta = (f"test_{k}_{suffix}" for k in ("gen", "hand", "meta"))
    SchemaGenerator(layer, schema=gen, meta_schema=meta).generate(load_definition(DEMO))
    layer.execute_write(f"CREATE SCHEMA {hand}")
    for statement in HAND_DDL.format(s=hand).split(";"):
        if statement.strip():
            layer.execute_write(statement)
    yield gen, hand
    for name in (gen, hand, meta):
        layer.execute_write(f"DROP SCHEMA IF EXISTS {name} CASCADE")


def test_generated_and_hand_written_demo_are_identical(layer, schemas):
    diffs, info = compare(layer, *schemas, TABLES)
    assert diffs == []
    assert info == []


def test_a_type_difference_fails(layer, schemas):
    layer.execute_write(
        f"ALTER TABLE {schemas[1]}.fact_orders ALTER COLUMN status TYPE VARCHAR(40)"
    )
    diffs, _ = compare(layer, *schemas, TABLES)
    assert diffs == [
        "fact_orders.status: type character varying(32) vs character varying(40)"
    ]


def test_a_nullability_difference_fails(layer, schemas):
    layer.execute_write(
        f"ALTER TABLE {schemas[1]}.dim_customer ALTER COLUMN name SET NOT NULL"
    )
    diffs, _ = compare(layer, *schemas, TABLES)
    assert diffs == ["dim_customer.name: NULL vs NOT NULL"]


def test_missing_column_and_table_fail(layer, schemas):
    layer.execute_write(f"ALTER TABLE {schemas[1]}.dim_date DROP COLUMN quarter")
    diffs, _ = compare(layer, *schemas, TABLES + ["dim_store"])
    assert "dim_date.quarter: missing in the second schema" in diffs
    assert "dim_store: missing in the first schema" in diffs


def test_a_missing_foreign_key_fails(layer, schemas):
    layer.execute_write(
        f"ALTER TABLE {schemas[1]}.fact_orders DROP CONSTRAINT fact_orders_date_key_fkey"
    )
    diffs, _ = compare(layer, *schemas, TABLES)
    assert len(diffs) == 1 and diffs[0].startswith("fact_orders: foreign_keys")


def test_identity_and_unique_are_listed_but_do_not_fail(layer, schemas):
    layer.execute_write(f"DROP INDEX {schemas[1]}.dim_customer_current_uq")
    layer.execute_write(
        f"ALTER TABLE {schemas[1]}.dim_customer ALTER COLUMN customer_key DROP IDENTITY"
    )
    diffs, info = compare(layer, *schemas, TABLES)
    assert diffs == []
    assert any(i.startswith("dim_customer: identity") for i in info)
    assert any(i.startswith("dim_customer: unique") for i in info)
