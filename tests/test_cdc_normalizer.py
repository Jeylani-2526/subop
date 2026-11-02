"""
tests/test_cdc_normalizer.py — M7W23T5.

Covers services/cdc/normalizer.py: envelope normalisation (M7W23T3) and
schema drift detection (M7W23T4).

Runs entirely from recorded JSON under tests/fixtures/cdc/. No live Kafka,
Debezium or PostgreSQL connection — deliberate, because ci.yml's postgres:15
service has no command: override and so runs at wal_level=replica, which
cannot support logical decoding. Any test needing a real CDC connection
would turn develop red on the first push.

Expected values are read out of the fixtures rather than hardcoded, so
M7W23T13's captured envelopes replace insert.json / update.json /
delete.json without a single edit here.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

import pytest

from services.cdc.normalizer import (
    NEUTRAL_FIELDS,
    TYPE_MODE_CONNECT,
    TYPE_MODE_NATIVE,
    SchemaDriftDetector,
    describe_drift,
    extract_schema_snapshot,
    normalize,
    schema_type_mode,
)
from services.connectors.errors import QueryError

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "cdc"

# Captured from a live connector by M7W23T13. Placeholders of the same shape
# are committed so this suite is runnable before that task lands.
CAPTURED = {
    "insert": ("insert.json", "insert"),
    "update": ("update.json", "update"),
    "delete": ("delete.json", "delete"),
}

# Hand-authored. Each changes the schema block one way against insert.json.
DRIFT_FIXTURES = {
    "column_added": "drift_column_added.json",
    "column_dropped": "drift_column_dropped.json",
    "column_renamed": "drift_column_renamed.json",
    "type_changed": "drift_type_changed.json",
    "column_widened": "drift_column_widened.json",
    "numeric_rescaled": "drift_numeric_rescaled.json",
}

OTHER_FIXTURES = (
    "snapshot_read.json",
    "truncate.json",
    "ts_ms_source_vs_processing.json",
    "connect_types_only.json",
    "connect_types_only_widened.json",
)

TABLE = "cdc_demo.orders"
ROW_COLUMNS = 6


def load(name: str) -> Dict[str, Any]:
    with (FIXTURE_DIR / name).open(encoding="utf-8") as handle:
        return json.load(handle)


@dataclass
class CapturedCase:
    label: str
    message: Dict[str, Any]
    expected_op: str


@pytest.fixture(params=sorted(CAPTURED))
def captured(request) -> CapturedCase:
    filename, expected_op = CAPTURED[request.param]
    return CapturedCase(request.param, load(filename), expected_op)


@pytest.fixture
def detector() -> SchemaDriftDetector:
    return SchemaDriftDetector()


# ---------------------------------------------------------------------------
# Fixture integrity — a missing file must fail loudly, not silently reduce
# coverage to the cases that happen to still be present.
# ---------------------------------------------------------------------------


def test_fixture_directory_exists():
    assert FIXTURE_DIR.is_dir(), f"missing fixture directory {FIXTURE_DIR}"


@pytest.mark.parametrize(
    "filename",
    sorted(
        [name for name, _ in CAPTURED.values()]
        + list(DRIFT_FIXTURES.values())
        + list(OTHER_FIXTURES)
    ),
)
def test_expected_fixture_present(filename):
    assert (FIXTURE_DIR / filename).is_file(), f"missing fixture {filename}"


# ---------------------------------------------------------------------------
# Neutral contract — M7W23T3
# ---------------------------------------------------------------------------


def test_op_mapped_to_neutral_vocabulary(captured: CapturedCase):
    assert normalize(captured.message)["op"] == captured.expected_op


def test_event_carries_exactly_the_neutral_fields(captured: CapturedCase):
    assert sorted(normalize(captured.message)) == sorted(NEUTRAL_FIELDS)


def test_table_is_schema_qualified(captured: CapturedCase):
    assert normalize(captured.message)["table"] == TABLE


def test_snapshot_op_is_recognised():
    assert normalize(load("snapshot_read.json"))["op"] == "snapshot"


def test_before_is_null_on_insert():
    assert normalize(load("insert.json"))["before"] is None


def test_after_is_null_on_delete():
    assert normalize(load("delete.json"))["after"] is None


@pytest.mark.parametrize("filename", ["update.json", "delete.json"])
def test_before_is_fully_populated(filename):
    """REPLICA IDENTITY FULL payoff — asserted rather than assumed.

    An id-only `before` means the ALTER TABLE did not take effect, which
    M7W23T1 verified (relreplident = f) and M7W23T13 re-checks on capture.
    """
    before = normalize(load(filename))["before"]
    assert before is not None
    assert len(before) == ROW_COLUMNS, f"before has {len(before)} of {ROW_COLUMNS}"
    assert "id" in before and len(before) > 1, "before looks id-only"


def test_update_after_reflects_the_change():
    event = normalize(load("update.json"))
    assert "status" in event["before"], "before carries no status column"
    assert event["before"]["status"] != event["after"]["status"]
    assert event["after"]["status"] == "shipped"


def test_numeric_column_is_a_lossless_string():
    """decimal.handling.mode=string in the T12 connector config.

    Left at its default (precise) the value arrives base64-encoded and this
    assertion fails, which is the intended signal.
    """
    amount = normalize(load("insert.json"))["after"]["amount"]
    assert isinstance(amount, str)
    assert amount == str(float(amount)) or "." in amount


# ---------------------------------------------------------------------------
# The t0 / t1 distinction — CDC Design Note v1 Section 2.2 names reversing
# these as the single most likely instrumentation mistake in M7.
# ---------------------------------------------------------------------------


def test_ts_ms_is_the_source_commit_time(captured: CapturedCase):
    expected = captured.message["payload"]["source"]["ts_ms"]
    assert normalize(captured.message)["ts_ms"] == expected


def test_ts_ms_is_not_the_top_level_processing_time():
    """Explicit negative assertion, on a fixture whose two timestamps are
    deliberately far apart so it cannot pass by coincidence — real envelopes
    committed inside the same millisecond would make this vacuous."""
    message = load("ts_ms_source_vs_processing.json")
    source_ts = message["payload"]["source"]["ts_ms"]
    processing_ts = message["payload"]["ts_ms"]
    assert source_ts != processing_ts, "fixture must hold two distinct values"

    event = normalize(message)
    assert event["ts_ms"] == source_ts
    assert event["ts_ms"] != processing_ts


def test_captured_ts_ms_is_not_processing_time(captured: CapturedCase):
    payload = captured.message["payload"]
    if payload["source"]["ts_ms"] == payload["ts_ms"]:
        pytest.skip("fixture's commit and processing times fall in the same ms")
    assert normalize(captured.message)["ts_ms"] != payload["ts_ms"]


def test_ts_ms_is_integer_milliseconds(captured: CapturedCase):
    ts_ms = normalize(captured.message)["ts_ms"]
    assert isinstance(ts_ms, int) and not isinstance(ts_ms, bool)
    assert ts_ms > 1_000_000_000_000, "looks like seconds, not milliseconds"


# ---------------------------------------------------------------------------
# Unsupported operations
# ---------------------------------------------------------------------------


def test_truncate_halts_rather_than_being_dropped():
    """A default publication publishes TRUNCATE (pubtruncate = t), so op='t'
    can arrive. The warehouse cannot represent it; silently skipping would
    let the target diverge from the source."""
    with pytest.raises(QueryError) as excinfo:
        normalize(load("truncate.json"))
    error = excinfo.value
    assert error.error_code == "CDC_UNSUPPORTED_OPERATION"
    assert error.connector_type == "streaming"
    assert error.retryable is False


# ---------------------------------------------------------------------------
# Malformed envelopes — inline rather than committed, being one-line shapes
# ---------------------------------------------------------------------------


def _source(**overrides):
    base = {"schema": "cdc_demo", "table": "orders", "ts_ms": 1791971779551}
    base.update(overrides)
    return base


MALFORMED = {
    "not_a_dict": None,
    "list_message": [1, 2],
    "string_message": "nope",
    "null_payload_tombstone": {"schema": {}, "payload": None},
    "payload_not_a_dict": {"payload": "x"},
    "no_op": {"source": _source(), "after": {"id": 1}},
    "op_not_a_string": {"op": 3, "source": _source()},
    "unknown_op_code": {"op": "z", "source": _source()},
    "no_source_block": {"op": "c", "after": {"id": 1}},
    "source_not_a_dict": {"op": "c", "source": "x"},
    "no_source_schema": {"op": "c", "source": {"table": "orders", "ts_ms": 1}},
    "no_source_table": {"op": "c", "source": {"schema": "cdc_demo", "ts_ms": 1}},
    "empty_source_table": {"op": "c", "source": _source(table="")},
    "no_source_ts_ms": {"op": "c", "source": {"schema": "cdc_demo", "table": "o"}},
    "ts_ms_as_string": {"op": "c", "source": _source(ts_ms="1791971779551")},
    "ts_ms_as_float": {"op": "c", "source": _source(ts_ms=1.5)},
    "ts_ms_as_bool": {"op": "c", "source": _source(ts_ms=True)},
    "before_not_a_dict": {"op": "u", "before": [1], "source": _source()},
    "after_not_a_dict": {"op": "c", "after": "row", "source": _source()},
}


@pytest.mark.parametrize("label", sorted(MALFORMED))
def test_malformed_envelope_is_rejected(label):
    with pytest.raises(QueryError) as excinfo:
        normalize(MALFORMED[label])
    error = excinfo.value
    assert error.connector_type == "streaming"
    assert error.retryable is False
    expected = (
        "CDC_UNSUPPORTED_OPERATION"
        if label == "unknown_op_code"
        else "CDC_ENVELOPE_MALFORMED"
    )
    assert error.error_code == expected


def test_bare_payload_is_accepted():
    """schemas.enable=false, or a hand-authored fixture, yields a bare
    payload. Normalisation works; drift detection cannot and says so."""
    event = normalize(load("insert.json")["payload"])
    assert event["op"] == "insert"
    assert event["table"] == TABLE


# ---------------------------------------------------------------------------
# Schema snapshot — M7W23T4
# ---------------------------------------------------------------------------


def test_snapshot_covers_every_column(captured: CapturedCase):
    snapshot = extract_schema_snapshot(captured.message)
    assert len(snapshot) == ROW_COLUMNS
    assert set(snapshot) == {
        "id",
        "customer_id",
        "status",
        "amount",
        "created_at",
        "updated_at",
    }


def test_snapshot_values_are_type_strings(captured: CapturedCase):
    snapshot = extract_schema_snapshot(captured.message)
    assert all(isinstance(value, str) and value for value in snapshot.values())


def test_captured_fixtures_carry_native_types(captured: CapturedCase):
    """Gates the column.propagate.source.type line in T12's connector config.

    Without it the schema block carries only Connect types, under which
    varchar(32) -> varchar(64) and numeric(12,2) -> numeric(14,4) are both
    invisible. A red test here means the connector was registered without
    that option and Week 24 would inherit weaker drift detection than the
    CDC Design Note describes.
    """
    assert schema_type_mode(captured.message) == TYPE_MODE_NATIVE


def test_native_snapshot_records_length_and_scale():
    snapshot = extract_schema_snapshot(load("insert.json"))
    assert "(" in snapshot["status"], snapshot["status"]
    assert "," in snapshot["amount"], snapshot["amount"]


def test_snapshot_needs_the_schema_block():
    with pytest.raises(QueryError) as excinfo:
        extract_schema_snapshot(load("insert.json")["payload"])
    assert excinfo.value.error_code == "CDC_ENVELOPE_MALFORMED"


# ---------------------------------------------------------------------------
# Drift detection — M7W23T4
# ---------------------------------------------------------------------------


def test_first_message_establishes_the_baseline(detector: SchemaDriftDetector):
    assert detector.baseline(TABLE) is None
    returned = detector.check(load("insert.json"))
    assert detector.baseline(TABLE) == returned


def test_identical_schema_does_not_drift(detector: SchemaDriftDetector):
    detector.check(load("insert.json"))
    detector.check(load("insert.json"))
    detector.check(load("update.json"))


def test_baseline_is_returned_as_a_copy(detector: SchemaDriftDetector):
    detector.check(load("insert.json"))
    stolen = detector.baseline(TABLE)
    stolen["injected"] = "value"
    assert "injected" not in detector.baseline(TABLE)


@pytest.mark.parametrize("label", sorted(DRIFT_FIXTURES))
def test_drift_raises_the_design_note_error(label, detector: SchemaDriftDetector):
    detector.check(load("insert.json"))
    with pytest.raises(QueryError) as excinfo:
        detector.check(load(DRIFT_FIXTURES[label]))
    error = excinfo.value
    assert error.error_code == "CDC_SCHEMA_DRIFT_DETECTED"
    assert error.connector_type == "streaming"
    assert error.retryable is False
    assert TABLE in error.message


def test_renamed_column_is_explained_as_drop_plus_add(
    detector: SchemaDriftDetector,
):
    """The schema block carries no column identity beyond the name, so a
    rename cannot be distinguished from a drop plus an add. The table halts
    either way; the message does not overclaim."""
    detector.check(load("insert.json"))
    with pytest.raises(QueryError) as excinfo:
        detector.check(load("drift_column_renamed.json"))
    assert "rename" in excinfo.value.message.lower()


def test_type_change_reports_old_and_new(detector: SchemaDriftDetector):
    detector.check(load("insert.json"))
    with pytest.raises(QueryError) as excinfo:
        detector.check(load("drift_type_changed.json"))
    assert "->" in excinfo.value.message


def test_drift_halts_only_the_affected_table(detector: SchemaDriftDetector):
    """Table-scoped per Design Note 3.4: one rename on orders must not stop
    capture on every other published table."""
    detector.check(load("insert.json"))

    other = load("insert.json")
    other["payload"]["source"]["table"] = "customers"
    detector.check(other)

    drifted = load("drift_column_added.json")
    drifted["payload"]["source"]["table"] = "customers"
    with pytest.raises(QueryError):
        detector.check(drifted)

    detector.check(load("update.json"))
    assert len(detector.baseline(TABLE)) == ROW_COLUMNS


def test_drift_persists_across_retries(detector: SchemaDriftDetector):
    """retryable=False is deliberate: a retry delivers the same drifted
    message again, so the baseline is left untouched on drift."""
    detector.check(load("insert.json"))
    for _ in range(3):
        with pytest.raises(QueryError):
            detector.check(load("drift_column_added.json"))


def test_reset_is_the_manual_resolution_path(detector: SchemaDriftDetector):
    detector.check(load("insert.json"))
    with pytest.raises(QueryError):
        detector.check(load("drift_column_added.json"))

    detector.reset(TABLE)
    assert detector.baseline(TABLE) is None
    detector.check(load("drift_column_added.json"))
    assert len(detector.baseline(TABLE)) == ROW_COLUMNS + 1


def test_process_returns_an_event_and_drift_checks(
    detector: SchemaDriftDetector,
):
    event = detector.process(load("insert.json"))
    assert sorted(event) == sorted(NEUTRAL_FIELDS)
    with pytest.raises(QueryError):
        detector.process(load("drift_column_added.json"))


def test_describe_drift_is_empty_for_identical_snapshots():
    snapshot = extract_schema_snapshot(load("insert.json"))
    assert describe_drift(snapshot, dict(snapshot)) == {}


# ---------------------------------------------------------------------------
# The documented limitation, proven rather than asserted in prose
# ---------------------------------------------------------------------------


def test_connect_only_fixture_reports_connect_mode():
    assert schema_type_mode(load("connect_types_only.json")) == TYPE_MODE_CONNECT


def test_without_propagation_a_widening_is_invisible(
    detector: SchemaDriftDetector,
):
    """Both fixtures describe status as Connect type "string" — one at
    varchar(32), one at varchar(64). No drift is detectable, which is why
    T12 sets column.propagate.source.type."""
    detector.check(load("connect_types_only.json"))
    detector.check(load("connect_types_only_widened.json"))

    native = SchemaDriftDetector()
    native.check(load("insert.json"))
    with pytest.raises(QueryError):
        native.check(load("drift_column_widened.json"))
