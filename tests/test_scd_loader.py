"""tests/test_scd_loader.py — M8W29T2.

Runs against a real PostgreSQL. Each test gets throwaway source, warehouse and
registry schemas; the source tables mirror cdc_demo's (cdc_replication_setup.sql).
"""

from __future__ import annotations

import copy
import json
import uuid
from pathlib import Path

import pytest

from services.abstraction.abstraction_layer import AbstractionLayer
from services.warehouse.metadata import validate_definition
from services.warehouse.schema_generator import SchemaGenerator
from services.warehouse.scd_loader import LoaderError, WarehouseLoader, main

DEMO = (
    Path(__file__).resolve().parents[1]
    / "services"
    / "warehouse"
    / "definitions"
    / "demo_orders_star.json"
)


class _RecordingLayer:
    def __init__(self, layer):
        self._layer = layer
        self.writes, self.queries = [], []

    def execute_write(self, sql, params=None):
        self.writes.append(sql)
        return self._layer.execute_write(sql, params)

    def execute_query(self, sql, params=None):
        self.queries.append(sql)
        return self._layer.execute_query(sql, params)


@pytest.fixture
def layer(test_db_connection):
    return AbstractionLayer(connector=test_db_connection, database="postgresql")


@pytest.fixture
def names(layer):
    suffix = uuid.uuid4().hex[:8]
    out = {k: f"test_{k}_{suffix}" for k in ("src", "dw", "meta")}
    yield out
    for name in out.values():
        layer.execute_write(f"DROP SCHEMA IF EXISTS {name} CASCADE")


@pytest.fixture
def src(layer, names):
    s = names["src"]
    layer.execute_write(f"CREATE SCHEMA {s}")
    layer.execute_write(
        f"CREATE TABLE {s}.customers (id BIGINT PRIMARY KEY, name VARCHAR(64) NOT NULL, "
        f"city VARCHAR(64) NOT NULL)"
    )
    layer.execute_write(
        f"CREATE TABLE {s}.orders (id BIGINT PRIMARY KEY, customer_id BIGINT NOT NULL, "
        f"status VARCHAR(32) NOT NULL, amount NUMERIC(12,2) NOT NULL, "
        f"created_at TIMESTAMPTZ NOT NULL)"
    )
    layer.execute_write(
        f"INSERT INTO {s}.customers VALUES (1001, 'Ayse Yilmaz', 'Istanbul'), "
        f"(1002, 'Mehmet Kaya', 'Ankara')"
    )
    layer.execute_write(
        f"INSERT INTO {s}.orders VALUES "
        f"(1, 1001, 'pending', 149.90, '2026-11-20 10:00+00'), "
        f"(2, 1002, 'paid', 82.50, '2026-11-21 09:30+00')"
    )
    return s


@pytest.fixture
def defn(src):
    data = json.loads(DEMO.read_text(encoding="utf-8"))
    data["fact"]["source_table"] = f"{src}.orders"
    data["dimensions"][0]["source_table"] = f"{src}.customers"
    return validate_definition(data)


@pytest.fixture
def loader(layer, names, defn):
    SchemaGenerator(layer, schema=names["dw"], meta_schema=names["meta"]).generate(defn)
    return WarehouseLoader(
        defn, layer, layer, schema=names["dw"], meta_schema=names["meta"]
    )


def rows(layer, sql):
    return [dict(r) for r in layer.execute_query(sql)]


def customer_versions(layer, dw, customer_id):
    return rows(
        layer,
        f"SELECT customer_key, name, city, valid_from, valid_to, is_current "
        f"FROM {dw}.dim_customer WHERE id = {customer_id} ORDER BY customer_key",
    )


def by_table(reports):
    return {r.table: r for r in reports}


# -- first load ----------------------------------------------------------------


def test_first_load_fills_every_table(layer, names, loader):
    reports = by_table(loader.load())
    dw = names["dw"]
    assert reports["dim_customer"].inserted == 2
    assert reports["dim_date"].inserted == 2
    assert reports["fact_orders"].inserted == 2

    ayse = customer_versions(layer, dw, 1001)
    assert len(ayse) == 1
    assert ayse[0]["is_current"] is True and ayse[0]["valid_to"] is None

    facts = rows(
        layer, f"SELECT id, customer_key, date_key FROM {dw}.fact_orders ORDER BY id"
    )
    assert facts[0]["customer_key"] == ayse[0]["customer_key"]
    assert [f["date_key"] for f in facts] == [20261120, 20261121]


def test_date_dimension_parts(layer, names, loader):
    loader.load()
    day = rows(
        layer, f"SELECT * FROM {names['dw']}.dim_date WHERE date_key = 20261120"
    )[0]
    assert (day["year"], day["quarter"], day["month"], day["day"]) == (2026, 4, 11, 20)
    assert day["day_of_week"] == 5  # ISO: Friday


def test_dates_are_taken_in_utc(layer, names, src, loader):
    # 23:30 in UTC on 21 Nov is already 22 Nov in Istanbul; the date stays 21 Nov.
    layer.execute_write(
        f"INSERT INTO {src}.orders VALUES (3, 1001, 'paid', 10, '2026-11-21 23:30+00')"
    )
    layer.execute_write("SET TIME ZONE 'Europe/Istanbul'")
    try:
        loader.load()
    finally:
        layer.execute_write("SET TIME ZONE 'UTC'")
    key = rows(layer, f"SELECT date_key FROM {names['dw']}.fact_orders WHERE id = 3")
    assert key[0]["date_key"] == 20261121


# -- SCD behaviour ---------------------------------------------------------------


def test_tracked_change_adds_a_version(layer, names, src, loader):
    loader.load()
    layer.execute_write(f"UPDATE {src}.customers SET city = 'Bandirma' WHERE id = 1001")
    reports = by_table(loader.load())
    assert reports["dim_customer"].new_versions == 1
    assert reports["dim_customer"].inserted == 0

    old, new = customer_versions(layer, names["dw"], 1001)
    assert (old["city"], old["is_current"]) == ("Istanbul", False)
    assert (new["city"], new["is_current"], new["valid_to"]) == ("Bandirma", True, None)
    assert old["valid_to"] == new["valid_from"]


def test_untracked_change_overwrites_without_a_version(layer, names, src, loader):
    loader.load()
    layer.execute_write(f"UPDATE {src}.customers SET city = 'Bandirma' WHERE id = 1001")
    loader.load()
    layer.execute_write(
        f"UPDATE {src}.customers SET name = 'Ayse Kaya' WHERE id = 1001"
    )
    reports = by_table(loader.load())
    assert reports["dim_customer"].new_versions == 0
    versions = customer_versions(layer, names["dw"], 1001)
    assert len(versions) == 2
    assert {v["name"] for v in versions} == {"Ayse Kaya"}  # every version corrected


def test_rerun_adds_nothing(layer, names, loader):
    loader.load()
    reports = loader.load()
    assert all(r.inserted == r.updated == r.new_versions == 0 for r in reports)
    counts = rows(
        layer,
        f"SELECT (SELECT count(*) FROM {names['dw']}.dim_customer) AS c, "
        f"(SELECT count(*) FROM {names['dw']}.fact_orders) AS f",
    )[0]
    assert (counts["c"], counts["f"]) == (2, 2)


def test_old_order_keeps_its_version_new_order_gets_the_new_one(
    layer, names, src, loader
):
    loader.load()
    layer.execute_write(f"UPDATE {src}.customers SET city = 'Bandirma' WHERE id = 1001")
    layer.execute_write(
        f"INSERT INTO {src}.orders VALUES (3, 1001, 'pending', 20, '2026-11-22 08:00+00')"
    )
    layer.execute_write(f"UPDATE {src}.orders SET status = 'shipped' WHERE id = 1")
    reports = by_table(loader.load())
    assert reports["fact_orders"].updated == 1
    assert reports["fact_orders"].inserted == 1

    dw = names["dw"]
    city = rows(
        layer,
        f"SELECT f.id, f.status, c.city FROM {dw}.fact_orders f "
        f"JOIN {dw}.dim_customer c USING (customer_key) WHERE f.customer_id = 1001 "
        f"ORDER BY f.id",
    )
    assert city == [
        {"id": 1, "status": "shipped", "city": "Istanbul"},
        {"id": 3, "status": "pending", "city": "Bandirma"},
    ]


def test_changed_reference_is_looked_up_again(layer, names, src, loader):
    loader.load()
    layer.execute_write(f"UPDATE {src}.orders SET customer_id = 1002 WHERE id = 1")
    loader.load()
    fact = rows(
        layer,
        f"SELECT c.id FROM {names['dw']}.fact_orders f "
        f"JOIN {names['dw']}.dim_customer c USING (customer_key) WHERE f.id = 1",
    )
    assert fact == [{"id": 1002}]


# -- unmatched references --------------------------------------------------------


def test_order_without_customer_loads_with_null_key_and_is_reported(
    layer, names, src, loader
):
    layer.execute_write(
        f"INSERT INTO {src}.orders VALUES (3, 9001, 'pending', 20, '2026-11-22 08:00+00')"
    )
    reports = by_table(loader.load())
    assert reports["fact_orders"].inserted == 3
    assert reports["fact_orders"].unmatched == {"dim_customer": 1, "dim_date": 0}
    key = rows(
        layer, f"SELECT customer_key FROM {names['dw']}.fact_orders WHERE id = 3"
    )
    assert key == [{"customer_key": None}]


def test_late_arriving_customer_fills_the_key(layer, names, src, loader):
    layer.execute_write(
        f"INSERT INTO {src}.orders VALUES (3, 9001, 'pending', 20, '2026-11-22 08:00+00')"
    )
    loader.load()
    layer.execute_write(
        f"INSERT INTO {src}.customers VALUES (9001, 'E2E Test', 'Bandirma')"
    )
    reports = by_table(loader.load())
    assert reports["fact_orders"].updated == 1
    assert reports["fact_orders"].unmatched["dim_customer"] == 0


# -- safety ------------------------------------------------------------------------


def test_every_write_goes_through_execute_write(layer, names, defn):
    SchemaGenerator(layer, schema=names["dw"], meta_schema=names["meta"]).generate(defn)
    recording = _RecordingLayer(layer)
    WarehouseLoader(
        defn, recording, recording, schema=names["dw"], meta_schema=names["meta"]
    ).load()
    assert all(q.lstrip().upper().startswith("SELECT") for q in recording.queries)
    close_and_insert = [w for w in recording.writes if w.startswith("WITH closed AS")]
    assert len(close_and_insert) == 1  # one statement, never two


def test_load_before_generation_fails_clearly(layer, names, defn):
    loader = WarehouseLoader(
        defn, layer, layer, schema=names["dw"], meta_schema=names["meta"]
    )
    with pytest.raises(LoaderError, match="has not been generated"):
        loader.load()


def test_load_with_a_changed_definition_fails(layer, names, defn):
    SchemaGenerator(layer, schema=names["dw"], meta_schema=names["meta"]).generate(defn)
    changed = copy.deepcopy(defn.model_dump(mode="json"))
    changed["description"] = "edited after generation"
    loader = WarehouseLoader(
        validate_definition(changed),
        layer,
        layer,
        schema=names["dw"],
        meta_schema=names["meta"],
    )
    with pytest.raises(LoaderError, match="different definition"):
        loader.load()


def test_duplicate_source_keys_stop_the_load(layer, names, src, loader):
    layer.execute_write(f"ALTER TABLE {src}.customers DROP CONSTRAINT customers_pkey")
    layer.execute_write(f"INSERT INTO {src}.customers VALUES (1001, 'Copy', 'Izmir')")
    with pytest.raises(LoaderError, match="duplicate business keys"):
        loader.load()


# -- not tied to the demo ----------------------------------------------------------


def test_a_second_definition_loads_the_same_way(layer, names):
    s, dw, meta = names["src"], names["dw"], names["meta"]
    layer.execute_write(f"CREATE SCHEMA {s}")
    layer.execute_write(
        f"CREATE TABLE {s}.products (sku VARCHAR(16) PRIMARY KEY, "
        f"title VARCHAR(80), category VARCHAR(32), supplier VARCHAR(40))"
    )
    layer.execute_write(
        f"CREATE TABLE {s}.sales (sale_no INTEGER, line_no INTEGER, sku VARCHAR(16), "
        f"qty INTEGER, sold_on DATE, PRIMARY KEY (sale_no, line_no))"
    )
    layer.execute_write(
        f"INSERT INTO {s}.products VALUES ('A1', 'Kettle', 'kitchen', 'Arcelik'), "
        f"('B2', 'Lamp', 'home', 'Vestel')"
    )
    layer.execute_write(
        f"INSERT INTO {s}.sales VALUES (1, 1, 'A1', 2, '2026-11-02'), "
        f"(1, 2, 'B2', 1, '2026-11-02'), (2, 1, 'A1', 5, '2026-11-03')"
    )
    defn = validate_definition(
        {
            "name": "sales_star",
            "version": 1,
            "source": {"connector_type": "postgresql", "connection_ref": "pg-main"},
            "fact": {
                "name": "fact_sales",
                "source_table": f"{s}.sales",
                "columns": {
                    "sale_no": "integer",
                    "line_no": "integer",
                    "sku": "varchar(16)",
                    "qty": "integer",
                    "sold_on": "date",
                },
                "business_key": ["sale_no", "line_no"],
                "measures": ["qty"],
                "dimension_keys": {"sku": "dim_product", "sold_on": "dim_day"},
                "personal_data": False,
            },
            "dimensions": [
                {
                    "name": "dim_product",
                    "source_table": f"{s}.products",
                    "columns": {
                        "sku": "varchar(16)",
                        "title": "varchar(80)",
                        "category": "varchar(32)",
                        "supplier": "varchar(40)",
                    },
                    "business_key": ["sku"],
                    "scd_type": 2,
                    "tracked_attributes": ["category", "supplier"],
                    "personal_data": False,
                },
                {
                    "name": "dim_day",
                    "derived_from": {"kind": "date", "column": "sold_on"},
                    "scd_type": 1,
                    "personal_data": False,
                },
            ],
        }
    )
    SchemaGenerator(layer, schema=dw, meta_schema=meta).generate(defn)
    loader = WarehouseLoader(defn, layer, layer, schema=dw, meta_schema=meta)
    reports = by_table(loader.load())
    assert reports["fact_sales"].inserted == 3
    assert reports["dim_day"].inserted == 2

    layer.execute_write(f"UPDATE {s}.products SET supplier = 'Beko' WHERE sku = 'A1'")
    assert by_table(loader.load())["dim_product"].new_versions == 1
    current = rows(
        layer,
        f"SELECT supplier FROM {dw}.dim_product WHERE sku = 'A1' AND is_current",
    )
    assert current == [{"supplier": "Beko"}]


def test_cli_reports_an_invalid_definition(tmp_path, capsys):
    bad = json.loads(DEMO.read_text(encoding="utf-8"))
    del bad["dimensions"][0]["legal_basis"]
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(bad), encoding="utf-8")
    assert main([str(path)]) == 2
    assert "dimensions[0].legal_basis" in capsys.readouterr().err


def test_cli_reports_a_connection_problem(monkeypatch, capsys):
    monkeypatch.setenv("SUBOP_CONN_PG_MAIN", "not json")
    assert main([str(DEMO)]) == 4
    assert "CONNECTION_REF_MALFORMED" in capsys.readouterr().err
