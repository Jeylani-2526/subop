"""tests/test_source_catalog.py — column types read from the source (G5).

The decisive test: a definition that leaves column types out generates a schema
identical, by the M8W29T3 equality check, to one that spells every type.
"""

from __future__ import annotations

import copy
import json
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from services.abstraction.abstraction_layer import AbstractionLayer
from services.connectors.errors import ConnectionError
from services.warehouse.metadata import MetadataValidationError
from services.warehouse.schema_compare import compare
from services.warehouse.schema_generator import SchemaGenerator
from services.warehouse.source_catalog import (
    definition_from_data,
    needs_source,
    postgres_catalog,
    resolve_columns,
)

DEMO = (
    Path(__file__).resolve().parents[1]
    / "services"
    / "warehouse"
    / "definitions"
    / "demo_orders_star.json"
)

CATALOG = {
    "shop.orders": {
        "id": "bigint",
        "customer_id": "bigint",
        "status": "character varying(32)",
        "amount": "numeric(12,2)",
        "created_at": "timestamp with time zone",
        "updated_at": "timestamp with time zone",
    },
    "shop.customers": {
        "id": "bigint",
        "name": "character varying(64)",
        "city": "character varying(64)",
    },
}


def demo(**overrides):
    data = json.loads(DEMO.read_text(encoding="utf-8"))
    data["fact"]["source_table"] = "shop.orders"
    data["dimensions"][0]["source_table"] = "shop.customers"
    for path, value in overrides.items():
        target, key = data, path.split(".")
        for part in key[:-1]:
            target = target[int(part)] if part.isdigit() else target[part]
        if value is None:
            del target[key[-1]]
        else:
            target[key[-1]] = value
    return data


# -- resolving, with a fake catalog -----------------------------------------------


def test_explicit_types_never_need_the_source():
    data = demo()
    assert not needs_source(data)
    assert resolve_columns(data, CATALOG.get) == data


def test_missing_columns_take_every_source_column_in_order():
    data = demo(**{"dimensions.0.columns": None})
    assert needs_source(data)
    out = resolve_columns(data, CATALOG.get)
    assert out["dimensions"][0]["columns"] == CATALOG["shop.customers"]
    assert "columns" not in data["dimensions"][0]  # the input is not changed


def test_names_only_take_their_types_from_the_source():
    data = demo(**{"fact.columns": ["id", "customer_id", "amount", "created_at"]})
    out = resolve_columns(data, CATALOG.get)
    assert out["fact"]["columns"] == {
        "id": "bigint",
        "customer_id": "bigint",
        "amount": "numeric(12,2)",
        "created_at": "timestamp with time zone",
    }


def test_unknown_table_and_column_name_their_paths():
    data = demo(**{"fact.columns": ["id", "colour"], "dimensions.0.columns": None})
    data["dimensions"][0]["source_table"] = "shop.clients"
    with pytest.raises(MetadataValidationError) as exc:
        resolve_columns(data, CATALOG.get)
    assert exc.value.errors == [
        "fact.columns[1]: 'colour' is not a column of shop.orders",
        "dimensions[0].source_table: 'shop.clients' not found in the source database",
    ]


def test_source_is_opened_only_when_needed_and_always_released():
    opened, released = [], []

    def connect(kind, ref):
        opened.append((kind, ref))
        return "layer"

    definition_from_data(demo(), connect, released.append)
    assert opened == [] and released == []

    def failing_catalog_connect(kind, ref):
        opened.append((kind, ref))
        return None  # postgres_catalog(None) fails on first use

    with pytest.raises(AttributeError):
        definition_from_data(
            demo(**{"dimensions.0.columns": None}),
            failing_catalog_connect,
            released.append,
        )
    assert opened == [("postgresql", "pg-main")]
    assert released == [None]


def test_other_sources_must_list_their_types():
    data = demo(**{"dimensions.0.columns": None})
    data["source"]["connector_type"] = "mysql"
    with pytest.raises(MetadataValidationError) as exc:
        definition_from_data(data, lambda k, r: pytest.fail("must not connect"), print)
    assert exc.value.errors[0].startswith("source.connector_type:")


# -- against a real PostgreSQL ---------------------------------------------------


@pytest.fixture
def layer(test_db_connection):
    return AbstractionLayer(connector=test_db_connection, database="postgresql")


@pytest.fixture
def names(layer):
    suffix = uuid.uuid4().hex[:8]
    out = {k: f"test_{k}_{suffix}" for k in ("src", "a", "b", "meta_a", "meta_b")}
    s = out["src"]
    layer.execute_write(f"CREATE SCHEMA {s}")
    layer.execute_write(
        f"CREATE TABLE {s}.orders (id BIGINT PRIMARY KEY, customer_id BIGINT NOT NULL, "
        f"status VARCHAR(32) NOT NULL, amount NUMERIC(12,2) NOT NULL, "
        f"created_at TIMESTAMPTZ NOT NULL, updated_at TIMESTAMPTZ NOT NULL)"
    )
    layer.execute_write(
        f"CREATE TABLE {s}.customers (id BIGINT PRIMARY KEY, name VARCHAR(64), "
        f"city VARCHAR(64))"
    )
    yield out
    for name in out.values():
        layer.execute_write(f"DROP SCHEMA IF EXISTS {name} CASCADE")


def test_postgres_catalog_reads_names_and_types_in_order(layer, names):
    catalog = postgres_catalog(layer)
    assert catalog(f"{names['src']}.customers") == {
        "id": "bigint",
        "name": "character varying(64)",
        "city": "character varying(64)",
    }
    assert catalog(f"{names['src']}.missing") is None


def test_introspected_definition_generates_an_identical_schema(layer, names):
    s = names["src"]
    explicit = demo()
    explicit["fact"]["source_table"] = f"{s}.orders"
    explicit["dimensions"][0]["source_table"] = f"{s}.customers"
    lean = copy.deepcopy(explicit)
    lean["fact"]["columns"] = ["id", "customer_id", "status", "amount", "created_at"]
    del lean["dimensions"][0]["columns"]

    defn = definition_from_data(lean, lambda k, r: layer, lambda layer_: None)
    SchemaGenerator(layer, schema=names["a"], meta_schema=names["meta_a"]).generate(
        definition_from_data(explicit, lambda k, r: pytest.fail(), print)
    )
    SchemaGenerator(layer, schema=names["b"], meta_schema=names["meta_b"]).generate(
        defn
    )
    diffs, info = compare(
        layer, names["a"], names["b"], ["fact_orders", "dim_customer", "dim_date"]
    )
    assert diffs == [] and info == []


# -- through the API ---------------------------------------------------------------


def test_api_generates_from_a_lean_definition(layer, names, monkeypatch):
    import sys

    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "services" / "etl_engine"))
    sys.path.insert(0, str(root / "services" / "etl_engine" / "api"))
    from app import app

    from services.warehouse import api

    class Session:
        def generator(self):
            return SchemaGenerator(
                layer, schema=names["a"], meta_schema=names["meta_a"]
            )

    monkeypatch.setattr(api, "_connect_source", lambda kind, ref: layer)
    monkeypatch.setattr(api, "_release_source", lambda layer_: None)
    app.dependency_overrides[api.get_session] = lambda: Session()
    try:
        client = TestClient(app)
        s = names["src"]
        lean = demo(**{"dimensions.0.columns": None, "fact.columns": None})
        lean["fact"]["source_table"] = f"{s}.orders"
        lean["dimensions"][0]["source_table"] = f"{s}.customers"
        # updated_at is not in the demo; the whole table is taken, so it is kept.
        response = client.post("/api/warehouse/schemas/generate", json=lean)
        assert response.status_code == 201
        fact = response.json()["tables"][0]
        assert "updated_at" in [c["name"] for c in fact["columns"]]

        lean["dimensions"][0]["source_table"] = f"{s}.clients"
        response = client.post("/api/warehouse/schemas/generate", json=lean)
        assert response.status_code == 422
        assert "not found in the source database" in response.json()["message"]

        def unreachable(kind, ref):
            raise ConnectionError(
                "could not connect",
                error_code="POSTGRES_CONNECTION_FAILED",
                retryable=True,
            )

        monkeypatch.setattr(api, "_connect_source", unreachable)
        response = client.post("/api/warehouse/schemas/generate", json=lean)
        assert response.status_code == 503
        assert response.json()["error_code"] == "POSTGRES_CONNECTION_FAILED"
    finally:
        app.dependency_overrides.pop(api.get_session, None)
