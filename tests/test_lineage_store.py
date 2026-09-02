import importlib.util
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Load lineage_store.py from the etl_engine directory
# ---------------------------------------------------------------------------

LINEAGE_STORE_PATH = (
    Path(__file__).resolve().parents[1] / "services" / "etl_engine" / "lineage_store.py"
)

spec = importlib.util.spec_from_file_location("lineage_store", LINEAGE_STORE_PATH)

if spec is None or spec.loader is None:
    raise ImportError(f"Could not load lineage_store module from {LINEAGE_STORE_PATH}")

lineage_store = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lineage_store)

SOURCE_READ_STEP_ID = lineage_store.SOURCE_READ_STEP_ID
clear_lineage = lineage_store.clear_lineage
get_lineage_for_run = lineage_store.get_lineage_for_run
record_lineage_entry = lineage_store.record_lineage_entry


@pytest.fixture(autouse=True)
def reset_lineage_store():
    clear_lineage()
    yield
    clear_lineage()


def test_record_lineage_entry():
    entry = record_lineage_entry(
        run_id="run-1",
        step_id=SOURCE_READ_STEP_ID,
        column="age",
        condition="inexact",
        canonical_type="integer",
        source_type="BIGINT",
    )

    assert entry["run_id"] == "run-1"
    assert entry["step_id"] == SOURCE_READ_STEP_ID
    assert entry["column"] == "age"
    assert entry["condition"] == "inexact"
    assert entry["canonical_type"] == "integer"
    assert entry["source_type"] == "BIGINT"

    assert "entry_id" in entry
    assert "recorded_at" in entry


def test_get_lineage_for_run_returns_only_matching_run():
    record_lineage_entry(
        run_id="run-1",
        step_id=SOURCE_READ_STEP_ID,
        column="age",
        condition="inexact",
    )

    record_lineage_entry(
        run_id="run-2",
        step_id=SOURCE_READ_STEP_ID,
        column="name",
        condition="ambiguous",
    )

    entries = get_lineage_for_run("run-1")

    assert len(entries) == 1
    assert entries[0]["run_id"] == "run-1"
    assert entries[0]["column"] == "age"


def test_source_read_step_id_sentinel():
    entry = record_lineage_entry(
        run_id="run-1",
        step_id=SOURCE_READ_STEP_ID,
        column="created_at",
        condition="fallback",
    )

    assert SOURCE_READ_STEP_ID == "source_read"
    assert entry["step_id"] == "source_read"
