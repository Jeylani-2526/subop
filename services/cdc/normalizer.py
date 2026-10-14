"""Normalise Debezium envelopes and detect source schema drift (M7W23T3, M7W23T4)."""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from services.connectors.errors import QueryError

_CONNECTOR_TYPE = "streaming"

# Debezium op codes. 't' (truncate) and 'm' (logical decoding message) are
# deliberately absent: a default PostgreSQL publication does publish TRUNCATE
# (pubtruncate = t), so 't' can arrive and must halt rather than be dropped —
# the warehouse cannot represent a truncate, and silently skipping it lets the
# target diverge from the source.
_OP_MAP = {
    "c": "insert",
    "u": "update",
    "d": "delete",
    "r": "snapshot",
}

NEUTRAL_FIELDS = ("op", "table", "before", "after", "ts_ms")

# Set by Debezium's column.propagate.source.type. Without that option the
# schema block carries only Connect types, under which varchar(32) ->
# varchar(64) and numeric(12,2) -> numeric(14,4) are both invisible: each stays
# "string". schema_type_mode() reports which vocabulary a message actually
# carried, so a mistyped regex surfaces as a test failure rather than as
# drift detection that quietly stopped covering type changes.
_PARAM_TYPE = "__debezium.source.column.type"
_PARAM_LENGTH = "__debezium.source.column.length"
_PARAM_SCALE = "__debezium.source.column.scale"

TYPE_MODE_NATIVE = "native"
TYPE_MODE_CONNECT = "connect"
TYPE_MODE_MIXED = "mixed"


def _malformed(message: str) -> QueryError:
    return QueryError(
        message,
        error_code="CDC_ENVELOPE_MALFORMED",
        connector_type=_CONNECTOR_TYPE,
        retryable=False,
    )


def _unsupported(message: str) -> QueryError:
    return QueryError(
        message,
        error_code="CDC_UNSUPPORTED_OPERATION",
        connector_type=_CONNECTOR_TYPE,
        retryable=False,
    )


def _drift(message: str) -> QueryError:
    return QueryError(
        message,
        error_code="CDC_SCHEMA_DRIFT_DETECTED",
        connector_type=_CONNECTOR_TYPE,
        retryable=False,
    )


def extract_payload(message: Any) -> Dict[str, Any]:
    """Return the payload, accepting either a full {schema, payload}
    message or a bare payload dict."""
    if not isinstance(message, dict):
        raise _malformed(f"Envelope must be a dict, got {type(message).__name__}.")

    payload = message["payload"] if "payload" in message else message

    if payload is None:
        raise _malformed(
            "Envelope payload is null. A null message value is a Kafka "
            "tombstone, which callers skip rather than normalise."
        )
    if not isinstance(payload, dict):
        raise _malformed(
            f"Envelope payload must be a dict, got {type(payload).__name__}."
        )
    return payload


def _normalize_op(payload: Dict[str, Any]) -> str:
    raw = payload.get("op")
    if raw is None:
        raise _malformed("Envelope payload has no 'op' field.")
    if not isinstance(raw, str):
        raise _malformed(f"Envelope 'op' must be a string, got {type(raw).__name__}.")
    if raw not in _OP_MAP:
        raise _unsupported(
            f"Unsupported Debezium op '{raw}'. SUBOP's neutral contract covers "
            f"{' | '.join(sorted(set(_OP_MAP.values())))}."
        )
    return _OP_MAP[raw]


def _source_block(payload: Dict[str, Any]) -> Dict[str, Any]:
    source = payload.get("source")
    if source is None:
        raise _malformed("Envelope payload has no 'source' block.")
    if not isinstance(source, dict):
        raise _malformed(
            f"Envelope 'source' must be a dict, got {type(source).__name__}."
        )
    return source


def _qualified_table(source: Dict[str, Any]) -> str:
    schema = source.get("schema")
    table = source.get("table")
    for name, value in (("schema", schema), ("table", table)):
        if not isinstance(value, str) or not value:
            raise _malformed(
                f"Envelope source.{name} must be a non-empty string, got {value!r}."
            )
    return f"{schema}.{table}"


def _commit_ts_ms(source: Dict[str, Any]) -> int:
    # Design Note v1 Section 2.2: t0 is source.ts_ms, the source commit time.
    # Top-level payload.ts_ms is Debezium's own processing time (t1), and
    # reversing the two reports capture latency as zero. Read here once so no
    # caller has to make the distinction.
    value = source.get("ts_ms")
    if value is None:
        raise _malformed(
            "Envelope source.ts_ms is missing — the source commit time (t0) "
            "cannot be recovered from top-level payload.ts_ms, which is "
            "Debezium's processing time (t1)."
        )
    if isinstance(value, bool) or not isinstance(value, int):
        raise _malformed(
            f"Envelope source.ts_ms must be an integer in milliseconds, "
            f"got {type(value).__name__} ({value!r})."
        )
    return value


def _row(payload: Dict[str, Any], key: str) -> Optional[Dict[str, Any]]:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, dict):
        raise _malformed(
            f"Envelope '{key}' must be a dict or null, got {type(value).__name__}."
        )
    return value


def normalize(message: Any) -> Dict[str, Any]:
    """Map one Debezium envelope onto {op, table, before, after, ts_ms}.

    Takes an already-decoded dict, not bytes from Kafka, so this is callable
    from recorded fixtures without a broker (M7W23T5).
    """
    payload = extract_payload(message)
    source = _source_block(payload)

    return {
        "op": _normalize_op(payload),
        "table": _qualified_table(source),
        "before": _row(payload, "before"),
        "after": _row(payload, "after"),
        "ts_ms": _commit_ts_ms(source),
    }


# ---------------------------------------------------------------------------
# Schema snapshot and drift detection (M7W23T4) — CDC Design Note v1 Section 3
# ---------------------------------------------------------------------------


def _row_fields(message: Any) -> list:
    """Return the column field list from the envelope's schema block.

    Taken from the message's own schema rather than an introspection query
    (Design Note 3.3): it costs no round trip, cannot drift from the payload
    it describes, and needs no privilege the subop_cdc role lacks.
    """
    if not isinstance(message, dict) or "schema" not in message:
        raise _malformed(
            "Drift detection needs the envelope's 'schema' block, which this "
            "message does not carry. A bare payload can be normalised but not "
            "schema-checked."
        )

    schema = message["schema"]
    if not isinstance(schema, dict):
        raise _malformed(
            f"Envelope 'schema' must be a dict, got {type(schema).__name__}."
        )

    envelope_fields = schema.get("fields")
    if not isinstance(envelope_fields, list):
        raise _malformed("Envelope schema has no 'fields' list.")

    # before and after share one Value schema. after is preferred only because
    # it is populated more often; either describes the same table version.
    by_name = {
        field.get("field"): field
        for field in envelope_fields
        if isinstance(field, dict)
    }
    for key in ("after", "before"):
        block = by_name.get(key)
        if isinstance(block, dict) and isinstance(block.get("fields"), list):
            return block["fields"]

    raise _malformed(
        "Envelope schema has neither an 'after' nor a 'before' struct with "
        "a field list — the table's column types cannot be derived."
    )


def _column_type(field: Dict[str, Any]) -> Tuple[str, bool]:
    """Return (type string, whether it came from a propagated native type)."""
    params = field.get("parameters")
    native = params.get(_PARAM_TYPE) if isinstance(params, dict) else None

    if isinstance(native, str) and native:
        length = params.get(_PARAM_LENGTH)
        scale = params.get(_PARAM_SCALE)
        if length is not None and scale is not None:
            return f"{native}({length},{scale})", True
        if length is not None:
            return f"{native}({length})", True
        return native, True

    # Connect vocabulary. The semantic name is preferred over the base type
    # where present, since io.debezium.time.ZonedTimestamp says more than
    # "string" — still Debezium's vocabulary, not PostgreSQL's.
    semantic = field.get("name")
    if isinstance(semantic, str) and semantic:
        return semantic, False

    base = field.get("type")
    if not isinstance(base, str) or not base:
        raise _malformed(f"Schema field {field.get('field')!r} has no usable type.")
    return base, False


def extract_schema_snapshot(message: Any) -> Dict[str, str]:
    """Derive the column-name-to-type snapshot for one message's table."""
    snapshot: Dict[str, str] = {}
    for field in _row_fields(message):
        if not isinstance(field, dict):
            raise _malformed("Schema field entries must be dicts.")
        name = field.get("field")
        if not isinstance(name, str) or not name:
            raise _malformed("Schema field entry has no 'field' name.")
        snapshot[name] = _column_type(field)[0]

    if not snapshot:
        raise _malformed("Schema block describes no columns.")
    return snapshot


def schema_type_mode(message: Any) -> str:
    """Report which type vocabulary a message carried: native, connect or
    mixed. 'mixed' means column.propagate.source.type matched only some
    columns, which is what a mistyped regex looks like."""
    flags = {_column_type(field)[1] for field in _row_fields(message)}
    if flags == {True}:
        return TYPE_MODE_NATIVE
    if flags == {False}:
        return TYPE_MODE_CONNECT
    return TYPE_MODE_MIXED


def describe_drift(baseline: Dict[str, str], current: Dict[str, str]) -> Dict[str, Any]:
    """Compare two snapshots. Returns the differences, empty when identical."""
    added = sorted(set(current) - set(baseline))
    dropped = sorted(set(baseline) - set(current))
    changed = {
        name: (baseline[name], current[name])
        for name in sorted(set(baseline) & set(current))
        if baseline[name] != current[name]
    }
    result: Dict[str, Any] = {}
    if added:
        result["added"] = added
    if dropped:
        result["dropped"] = dropped
    if changed:
        result["changed"] = changed
    return result


class SchemaDriftDetector:
    """Holds one baseline snapshot per table and halts that table on drift.

    Table-scoped by design (Design Note 3.4): one rename on orders must not
    stop capture on every other published table, and ConnectorError already
    describes one failing operation rather than a global kill switch.
    """

    def __init__(self) -> None:
        self._baselines: Dict[str, Dict[str, str]] = {}

    def baseline(self, table: str) -> Optional[Dict[str, str]]:
        snapshot = self._baselines.get(table)
        return dict(snapshot) if snapshot is not None else None

    def reset(self, table: Optional[str] = None) -> None:
        """Drop a stored baseline, re-establishing it from the next message.

        retryable=False means a drifted table stays halted on retry, exactly
        as Design Note 3.4 intends. This is the manual resolution path for an
        operator who has reconciled the warehouse with the new shape.
        """
        if table is None:
            self._baselines.clear()
        else:
            self._baselines.pop(table, None)

    def check(self, message: Any) -> Dict[str, str]:
        """Establish or verify the baseline for this message's table.

        Returns the current snapshot. Raises QueryError with
        error_code="CDC_SCHEMA_DRIFT_DETECTED" when it differs from the
        baseline. The baseline is left untouched on drift so every
        subsequent message for that table halts the same way.
        """
        payload = extract_payload(message)
        table = _qualified_table(_source_block(payload))
        current = extract_schema_snapshot(message)

        baseline = self._baselines.get(table)
        if baseline is None:
            self._baselines[table] = current
            return dict(current)

        differences = describe_drift(baseline, current)
        if differences:
            raise _drift(
                f"Schema drift detected on {table}: "
                f"{_format_drift(differences)}. Consumption of this table is "
                f"halted; other tables are unaffected. Resolution is manual."
            )
        return dict(current)

    def process(self, message: Any) -> Dict[str, Any]:
        """Drift-check, then normalise. A drifted message yields no event."""
        self.check(message)
        return normalize(message)


def _format_drift(differences: Dict[str, Any]) -> str:
    parts = []
    if "added" in differences:
        parts.append(f"columns added {differences['added']}")
    if "dropped" in differences:
        parts.append(f"columns dropped {differences['dropped']}")
    if "changed" in differences:
        changes = ", ".join(
            f"{name} {was} -> {now}"
            for name, (was, now) in differences["changed"].items()
        )
        parts.append(f"types changed ({changes})")
    # A rename arrives as one dropped plus one added column: the schema block
    # carries no identity beyond the name, so the two cannot be distinguished.
    # Either way the table halts, which is what Design Note 3.4 requires.
    if "added" in differences and "dropped" in differences:
        parts.append("(a rename appears as one dropped and one added column)")
    return "; ".join(parts)