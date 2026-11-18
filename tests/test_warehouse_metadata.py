"""tests/test_warehouse_metadata.py — M8W28T2.

Pure validation tests: no database needed.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from services.warehouse.metadata import (
    MetadataValidationError,
    load_definition,
    surrogate_key,
    validate_definition,
)

DEMO = (
    Path(__file__).resolve().parents[1]
    / "services"
    / "warehouse"
    / "definitions"
    / "demo_orders_star.json"
)


@pytest.fixture
def demo():
    return json.loads(DEMO.read_text(encoding="utf-8"))


def errors_for(data):
    with pytest.raises(MetadataValidationError) as info:
        validate_definition(data)
    return info.value.errors


def has_error(errors, path):
    return any(e.startswith(f"{path}:") for e in errors)


def test_demo_definition_validates():
    defn = load_definition(DEMO)
    assert defn.name == "demo_orders_star"
    assert defn.fact.name == "fact_orders"
    assert [d.name for d in defn.dimensions] == ["dim_customer", "dim_date"]
    customer = defn.dimension("dim_customer")
    assert customer.scd_type == 2
    assert customer.tracked_attributes == ["city"]
    assert customer.legal_basis == "Contract"
    assert customer.retention_policy_days == 3650
    assert defn.dimension("dim_date").derived_from.column == "created_at"


def test_surrogate_key_names():
    assert surrogate_key("dim_customer") == "customer_key"
    assert surrogate_key("dim_date") == "date_key"
    assert surrogate_key("region") == "region_key"


@pytest.mark.parametrize("field", ["legal_basis", "retention_policy_days"])
def test_personal_dimension_without_compliance_field_is_rejected(demo, field):
    del demo["dimensions"][0][field]
    assert has_error(errors_for(demo), f"dimensions[0].{field}")


@pytest.mark.parametrize("field", ["legal_basis", "retention_policy_days"])
def test_personal_fact_without_compliance_field_is_rejected(demo, field):
    demo["fact"][field] = None
    assert has_error(errors_for(demo), f"fact.{field}")


def test_non_personal_table_needs_no_compliance_fields(demo):
    for field in ("personal_data", "legal_basis", "retention_policy_days"):
        demo["fact"].pop(field)
    demo["fact"]["personal_data"] = False
    validate_definition(demo)


def test_unknown_legal_basis_is_rejected(demo):
    demo["fact"]["legal_basis"] = "BecauseWeCan"
    assert has_error(errors_for(demo), "fact.legal_basis")


def test_retention_must_be_positive(demo):
    demo["dimensions"][0]["retention_policy_days"] = 0
    assert has_error(errors_for(demo), "dimensions[0].retention_policy_days")


def test_tracked_attribute_must_be_a_column(demo):
    demo["dimensions"][0]["tracked_attributes"] = ["country"]
    assert has_error(errors_for(demo), "dimensions[0].tracked_attributes[0]")


@pytest.mark.parametrize("scd_type", [0, 3, "two"])
def test_unknown_scd_type_is_rejected(demo, scd_type):
    demo["dimensions"][0]["scd_type"] = scd_type
    assert has_error(errors_for(demo), "dimensions[0].scd_type")


def test_type_2_without_tracked_attributes_is_rejected(demo):
    demo["dimensions"][0]["tracked_attributes"] = []
    assert has_error(errors_for(demo), "dimensions[0].tracked_attributes")


def test_type_1_with_tracked_attributes_is_rejected(demo):
    demo["dimensions"][0]["scd_type"] = 1
    assert has_error(errors_for(demo), "dimensions[0].tracked_attributes")


def test_unsupported_native_type_is_rejected(demo):
    demo["fact"]["columns"]["amount"] = "money_but_fancy"
    assert has_error(errors_for(demo), "fact.columns.amount")


def test_unsafe_identifier_is_rejected(demo):
    demo["fact"]["name"] = "fact_orders; DROP TABLE x"
    assert has_error(errors_for(demo), "fact.name")


def test_reserved_column_name_is_rejected(demo):
    demo["dimensions"][0]["columns"]["is_current"] = "boolean"
    assert has_error(errors_for(demo), "dimensions[0].columns.is_current")


def test_dimension_key_to_unknown_dimension_is_rejected(demo):
    demo["fact"]["dimension_keys"]["customer_id"] = "dim_client"
    errors = errors_for(demo)
    assert has_error(errors, "fact.dimension_keys.customer_id")
    assert has_error(errors, "dimensions[0]")


def test_measure_must_be_a_column(demo):
    demo["fact"]["measures"] = ["total"]
    assert has_error(errors_for(demo), "fact.measures[0]")


def test_dimension_needs_a_source(demo):
    del demo["dimensions"][0]["source_table"]
    assert has_error(errors_for(demo), "dimensions[0].source_table")


def test_derived_dimension_cannot_declare_columns(demo):
    demo["dimensions"][1]["columns"] = {"full_date": "date"}
    assert has_error(errors_for(demo), "dimensions[1].columns")


def test_derived_date_needs_a_date_column(demo):
    demo["fact"]["dimension_keys"] = {
        "customer_id": "dim_customer",
        "status": "dim_date",
    }
    demo["dimensions"][1]["derived_from"]["column"] = "status"
    assert has_error(errors_for(demo), "dimensions[1].derived_from.column")


def test_unknown_field_is_rejected(demo):
    demo["fact"]["partition_by"] = "created_at"
    assert has_error(errors_for(demo), "fact.partition_by")


def test_every_error_is_reported_at_once(demo):
    del demo["dimensions"][0]["legal_basis"]
    demo["dimensions"][0]["tracked_attributes"] = ["country"]
    demo["fact"]["measures"] = ["total"]
    errors = errors_for(demo)
    assert len(errors) == 3
    assert all(": " in e for e in errors)


def test_validation_does_not_mutate_input(demo):
    before = copy.deepcopy(demo)
    validate_definition(demo)
    assert demo == before


def test_invalid_json_file_is_reported(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(MetadataValidationError) as info:
        load_definition(bad)
    assert info.value.errors[0].startswith("(root): invalid JSON")
