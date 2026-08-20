"""Tests for Pipeline DSL parsing/validation (M5W15T3)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services" / "etl_engine"))

from pipeline import (  # noqa: E402
    PipelineValidationError,
    parse_pipeline,
)


def _valid_doc(**overrides):
    doc = {
        "name": "customers-to-warehouse",
        "source": {
            "connector_type": "postgresql",
            "connection_ref": "app-db",
            "object": "customers",
            "query": None,
        },
        "transformations": [
            {
                "step_id": "s1",
                "type": "rename_columns",
                "params": {"from": "a", "to": "b"},
            },
        ],
        "target": {
            "connector_type": "postgresql",
            "connection_ref": "warehouse",
            "object": "dim_customers",
            "write_mode": "upsert",
        },
        "processing_purpose": "customer analytics",
        "data_subject_categories": ["customer_pii"],
        "transfer_recipients": [],
    }
    doc.update(overrides)
    return doc


def test_valid_pipeline_parses():
    p = parse_pipeline(_valid_doc())
    assert p.name == "customers-to-warehouse"
    assert p.source.connector_type == "postgresql"
    assert p.source.query is None
    assert len(p.transformations) == 1
    assert p.transformations[0].step_id == "s1"
    assert p.target.write_mode == "upsert"
    assert p.transfer_recipients == []


def test_empty_transformations_array_is_valid():
    p = parse_pipeline(_valid_doc(transformations=[]))
    assert p.transformations == []


def test_missing_name_raises():
    doc = _valid_doc()
    del doc["name"]
    with pytest.raises(PipelineValidationError) as exc_info:
        parse_pipeline(doc)
    assert any("`name`" in e for e in exc_info.value.errors)


def test_invalid_connector_type_raises():
    doc = _valid_doc()
    doc["source"]["connector_type"] = "oracle"
    with pytest.raises(PipelineValidationError) as exc_info:
        parse_pipeline(doc)
    assert any("source.connector_type" in e for e in exc_info.value.errors)


def test_invalid_write_mode_raises():
    doc = _valid_doc()
    doc["target"]["write_mode"] = "replace"
    with pytest.raises(PipelineValidationError) as exc_info:
        parse_pipeline(doc)
    assert any("write_mode" in e for e in exc_info.value.errors)


def test_duplicate_step_id_raises():
    doc = _valid_doc()
    doc["transformations"] = [
        {"step_id": "dup", "type": "t1", "params": {}},
        {"step_id": "dup", "type": "t2", "params": {}},
    ]
    with pytest.raises(PipelineValidationError) as exc_info:
        parse_pipeline(doc)
    assert any("not unique" in e for e in exc_info.value.errors)


def test_missing_step_id_raises():
    doc = _valid_doc()
    doc["transformations"] = [{"type": "t1", "params": {}}]
    with pytest.raises(PipelineValidationError) as exc_info:
        parse_pipeline(doc)
    assert any("step_id" in e for e in exc_info.value.errors)


def test_data_subject_categories_must_be_string_array():
    doc = _valid_doc()
    doc["data_subject_categories"] = "not-a-list"
    with pytest.raises(PipelineValidationError) as exc_info:
        parse_pipeline(doc)
    assert any("data_subject_categories" in e for e in exc_info.value.errors)


def test_empty_transfer_recipients_is_valid():
    doc = _valid_doc(transfer_recipients=[])
    p = parse_pipeline(doc)
    assert p.transfer_recipients == []


def test_all_errors_collected_not_just_first():
    doc = {
        "name": "",
        "source": {},
        "transformations": "not-a-list",
        "target": {},
        "processing_purpose": "",
        "data_subject_categories": None,
        "transfer_recipients": None,
    }
    with pytest.raises(PipelineValidationError) as exc_info:
        parse_pipeline(doc)
    assert len(exc_info.value.errors) >= 5


def test_query_must_be_string_or_null():
    doc = _valid_doc()
    doc["source"]["query"] = 123
    with pytest.raises(PipelineValidationError) as exc_info:
        parse_pipeline(doc)
    assert any("source.query" in e for e in exc_info.value.errors)


def test_source_query_overrides_default_read():
    doc = _valid_doc()
    doc["source"]["query"] = "SELECT id FROM customers WHERE active = true"
    p = parse_pipeline(doc)
    assert p.source.query == "SELECT id FROM customers WHERE active = true"
