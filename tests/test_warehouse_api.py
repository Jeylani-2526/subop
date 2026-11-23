"""tests/test_warehouse_api.py — M8W29T1.

The /api/warehouse routes through TestClient. Success paths generate into a
real PostgreSQL (each test in its own throwaway schemas); failure paths that
need a broken database use small fakes through dependency overrides.
"""

from __future__ import annotations

import copy
import json
import sys
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "etl_engine"))
sys.path.insert(0, str(ROOT / "services" / "etl_engine" / "api"))

from app import app  # noqa: E402
from services.abstraction.abstraction_layer import AbstractionLayer  # noqa: E402
from services.connectors.errors import ConnectionError, WriteError  # noqa: E402
from services.warehouse.api import get_session  # noqa: E402
from services.warehouse.schema_generator import SchemaGenerator  # noqa: E402

DEMO = ROOT / "services" / "warehouse" / "definitions" / "demo_orders_star.json"
SCHEMAS = "/api/warehouse/schemas"
GENERATE = "/api/warehouse/schemas/generate"


@pytest.fixture
def demo_dict():
    return json.loads(DEMO.read_text(encoding="utf-8"))


@pytest.fixture
def client():
    yield TestClient(app)
    app.dependency_overrides.pop(get_session, None)


class _Session:
    def __init__(self, generator=None, error=None):
        self._generator, self._error = generator, error

    def generator(self):
        if self._error:
            raise self._error
        return self._generator


def _use(session):
    app.dependency_overrides[get_session] = lambda: session


# -- against a real PostgreSQL ---------------------------------------------


@pytest.fixture
def layer(test_db_connection):
    return AbstractionLayer(connector=test_db_connection, database="postgresql")


@pytest.fixture
def generator(layer):
    suffix = uuid.uuid4().hex[:8]
    names = (f"test_dw_{suffix}", f"test_dwmeta_{suffix}")
    yield SchemaGenerator(layer, schema=names[0], meta_schema=names[1])
    for name in names:
        layer.execute_write(f"DROP SCHEMA IF EXISTS {name} CASCADE")


@pytest.fixture
def live(client, generator):
    _use(_Session(generator))
    return client


def test_list_is_empty_before_generation(live):
    response = live.get(SCHEMAS)
    assert response.status_code == 200
    assert response.json() == []


def test_generate_returns_201_and_the_contract_shape(live, generator, demo_dict):
    response = live.post(GENERATE, json=demo_dict)
    assert response.status_code == 201
    body = response.json()
    assert body["schema_id"] == "demo_orders_star"
    assert body["version"] == 1
    assert body["target_schema"] == generator.schema
    assert body["source"] == {
        "connector_type": "postgresql",
        "connection_ref": "pg-main",
    }
    assert [t["name"] for t in body["tables"]] == [
        "fact_orders",
        "dim_customer",
        "dim_date",
    ]
    customer = body["tables"][1]
    assert customer["scd_type"] == 2
    assert customer["tracked_attributes"] == ["city"]
    assert customer["legal_basis"] == "Contract"
    assert customer["retention_policy_days"] == 3650
    assert customer["columns"][0] == {
        "name": "customer_key",
        "role": "surrogate_key",
        "native_type": None,
        "canonical_type": "BIGINT",
        "warehouse_type": "BIGINT",
        "references": None,
    }


def test_generated_schema_is_listed(live, demo_dict):
    created = live.post(GENERATE, json=demo_dict).json()
    response = live.get(SCHEMAS)
    assert response.status_code == 200
    assert response.json() == [created]


def test_same_definition_again_returns_200_and_changes_nothing(live, demo_dict):
    first = live.post(GENERATE, json=demo_dict).json()
    second = live.post(GENERATE, json=demo_dict)
    assert second.status_code == 200
    assert second.json() == first
    assert len(live.get(SCHEMAS).json()) == 1


def test_changed_definition_with_the_same_name_is_409(live, demo_dict):
    live.post(GENERATE, json=demo_dict)
    changed = copy.deepcopy(demo_dict)
    changed["fact"]["columns"]["status"] = "varchar(64)"
    response = live.post(GENERATE, json=changed)
    assert response.status_code == 409
    body = response.json()
    assert body["error_code"] == "WAREHOUSE_SCHEMA_CONFLICT"
    assert body["connector_type"] is None
    assert body["retryable"] is False


def test_invalid_definition_lists_every_problem_and_writes_nothing(live, demo_dict):
    bad = copy.deepcopy(demo_dict)
    del bad["dimensions"][0]["legal_basis"]
    bad["dimensions"][0]["tracked_attributes"] = ["country"]
    response = live.post(GENERATE, json=bad)
    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "WAREHOUSE_METADATA_INVALID"
    assert body["connector_type"] is None
    assert body["retryable"] is False
    problems = body["message"].split("; ")
    assert any(p.startswith("dimensions[0].legal_basis:") for p in problems)
    assert any(p.startswith("dimensions[0].tracked_attributes[0]:") for p in problems)
    assert live.get(SCHEMAS).json() == []


# -- validation needs no database --------------------------------------------


def test_shape_error_names_its_field(client, demo_dict):
    _use(_Session(error=AssertionError("validation must run before the database")))
    bad = copy.deepcopy(demo_dict)
    bad["dimensions"][0]["scd_type"] = 3
    response = client.post(GENERATE, json=bad)
    assert response.status_code == 422
    assert response.json()["message"].startswith("dimensions[0].scd_type:")


def test_malformed_json_gets_the_error_envelope(client):
    _use(_Session(error=AssertionError("validation must run before the database")))
    response = client.post(
        GENERATE, content=b"{not json", headers={"content-type": "application/json"}
    )
    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "WAREHOUSE_METADATA_INVALID"
    assert body["message"].startswith("(root): invalid JSON:")


# -- database failures ---------------------------------------------------------


def _unreachable():
    return ConnectionError(
        "could not connect to server",
        error_code="POSTGRES_CONNECTION_FAILED",
        connector_type="postgresql",
        retryable=True,
    )


@pytest.mark.parametrize("method, path", [("get", SCHEMAS), ("post", GENERATE)])
def test_unreachable_database_is_503(client, demo_dict, method, path):
    _use(_Session(error=_unreachable()))
    kwargs = {"json": demo_dict} if method == "post" else {}
    response = getattr(client, method)(path, **kwargs)
    assert response.status_code == 503
    assert response.json() == {
        "error_code": "POSTGRES_CONNECTION_FAILED",
        "message": "could not connect to server",
        "connector_type": None,
        "retryable": True,
    }


def test_failed_ddl_is_500(client, demo_dict):
    class FailingGenerator:
        def generate(self, defn):
            raise WriteError("Write failed: permission denied for database subop")

    _use(_Session(FailingGenerator()))
    response = client.post(GENERATE, json=demo_dict)
    assert response.status_code == 500
    body = response.json()
    assert body["error_code"] == "WAREHOUSE_GENERATION_FAILED"
    assert "permission denied" in body["message"]
    assert body["retryable"] is False


def test_unknown_connection_ref_is_503_not_a_crash(client, monkeypatch):
    monkeypatch.setenv("WAREHOUSE_REF", "no-such-ref")
    monkeypatch.delenv("SUBOP_CONN_NO_SUCH_REF", raising=False)
    response = client.get(SCHEMAS)
    assert response.status_code == 503
    assert response.json()["error_code"] == "CONNECTION_REF_NOT_FOUND"


def test_versions_route_is_not_added(client):
    _use(_Session(error=AssertionError("no route should reach the database")))
    assert client.get(f"{SCHEMAS}/demo_orders_star/versions").status_code == 404
