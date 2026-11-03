#!/usr/bin/env python3
"""Capture one real Debezium envelope per operation into tests/fixtures/cdc/.

M7W26T1. Replaces the hand-reconstructed insert.json, update.json and
delete.json in place, keeping the filenames, and validates each capture against
the two conditions tests/fixtures/cdc/README.md documents.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from confluent_kafka import Consumer, KafkaError
except ImportError:
    sys.exit(
        "confluent-kafka not installed. pip install -r services/requirements-dev.txt"
    )

REPO = Path(__file__).resolve().parents[2]
FIXTURES = REPO / "tests" / "fixtures" / "cdc"

# topic.prefix from services/cdc/debezium_postgres_connector.json, plus the
# schema and table from table.include.list.
DEFAULT_TOPIC = "subop-postgres-cdc.cdc_demo.orders"

PARAM_TYPE = "__debezium.source.column.type"
OP_TO_FILE = {"c": "insert.json", "u": "update.json", "d": "delete.json"}
EXPECTED_COLUMNS = 6


def row_fields(message: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return the after/before struct's field list from the envelope schema."""
    by_name = {f.get("field"): f for f in message["schema"]["fields"]}
    for key in ("after", "before"):
        block = by_name.get(key)
        if isinstance(block, dict) and isinstance(block.get("fields"), list):
            return block["fields"]
    raise ValueError("Envelope schema has neither an 'after' nor 'before' struct.")


def native_type(field: Dict[str, Any]) -> Optional[str]:
    params = field.get("parameters")
    if not isinstance(params, dict):
        return None
    value = params.get(PARAM_TYPE)
    return value if isinstance(value, str) and value else None


def validate(message: Dict[str, Any], op: str) -> List[str]:
    """Return a list of problems; empty means the capture is usable."""
    problems: List[str] = []

    if "schema" not in message or "payload" not in message:
        problems.append(
            "Message has no 'schema'/'payload' split — Connect is running with "
            "schemas disabled. The drift tests cannot run on a payload-only capture."
        )
        return problems

    fields = row_fields(message)
    missing_native = [f.get("field") for f in fields if native_type(f) is None]
    if missing_native:
        problems.append(
            f"Columns without {PARAM_TYPE}: {missing_native}. "
            "column.propagate.source.type did not match — widenings would be invisible."
        )

    if op in ("u", "d"):
        before = message["payload"].get("before")
        if before is None:
            problems.append(
                "payload.before is null — REPLICA IDENTITY FULL did not apply."
            )
        elif len(before) < EXPECTED_COLUMNS:
            problems.append(
                f"payload.before has {len(before)} of {EXPECTED_COLUMNS} columns — "
                "looks id-only, contradicting relreplident = f."
            )

    return problems


def report_types(captured: Dict[str, Dict[str, Any]]) -> None:
    """Print observed native types beside the real snapshot — T2's evidence."""
    snapshot_path = FIXTURES / "snapshot_event.json"
    if not snapshot_path.exists():
        return
    snapshot = json.loads(snapshot_path.read_text())

    def types_of(message: Dict[str, Any]) -> Dict[str, str]:
        out = {}
        for f in row_fields(message):
            params = f.get("parameters") or {}
            native = params.get(PARAM_TYPE, "?")
            length = params.get("__debezium.source.column.length")
            scale = params.get("__debezium.source.column.scale")
            suffix = (
                f"({length},{scale})"
                if length and scale
                else f"({length})" if length else ""
            )
            out[f.get("field")] = f"{native}{suffix}"
        return out

    snap_types = types_of(snapshot)
    print("\n--- Observed native types: snapshot (baseline) vs streaming ---")
    print(f"{'column':<14}{'snapshot_event.json':<26}{'streaming capture':<26}")
    for op, message in captured.items():
        stream_types = types_of(message)
        print(f"\n[{OP_TO_FILE[op]}]")
        for column, snap in snap_types.items():
            stream = stream_types.get(column, "<absent>")
            flag = "" if snap == stream else "   <-- differs"
            print(f"{column:<14}{snap:<26}{stream:<26}{flag}")
        break  # all three streaming envelopes share one Value schema


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Capture real Debezium envelopes.")
    parser.add_argument("--topic", default=DEFAULT_TOPIC)
    parser.add_argument("--bootstrap", default="localhost:9092")
    parser.add_argument("--timeout", type=float, default=90.0, help="Seconds to wait")
    parser.add_argument(
        "--dry-run", action="store_true", help="Validate without writing"
    )
    args = parser.parse_args(argv)

    consumer = Consumer(
        {
            "bootstrap.servers": args.bootstrap,
            # A fresh group id each run, so capture always reads the topic from the
            # beginning rather than resuming from a previous run's committed offset.
            "group.id": f"subop-capture-{int(time.time())}",
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
        }
    )
    consumer.subscribe([args.topic])

    captured: Dict[str, Dict[str, Any]] = {}
    snapshot_reads = 0
    deadline = time.time() + args.timeout
    print(f"Consuming {args.topic} from {args.bootstrap} (timeout {args.timeout}s)...")

    while time.time() < deadline and len(captured) < len(OP_TO_FILE):
        msg = consumer.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            if msg.error().code() == KafkaError._PARTITION_EOF:
                continue
            print(f"Kafka error: {msg.error()}", file=sys.stderr)
            continue
        if msg.value() is None:
            continue  # tombstone; tombstones.on.delete is false, so unexpected

        envelope = json.loads(msg.value().decode("utf-8"))
        payload = envelope.get("payload") or {}
        op = payload.get("op")
        if op == "r":
            snapshot_reads += 1
            continue
        if op in OP_TO_FILE and op not in captured:
            captured[op] = envelope
            print(f"  captured op={op} -> {OP_TO_FILE[op]}")

    consumer.close()

    print(f"\nSnapshot reads seen (op=r, skipped): {snapshot_reads}")
    missing = [OP_TO_FILE[o] for o in OP_TO_FILE if o not in captured]
    if missing:
        print(
            f"MISSING: {missing} — run cdc_demo_changes.py --all, then re-run.",
            file=sys.stderr,
        )

    failed = False
    for op, envelope in captured.items():
        problems = validate(envelope, op)
        if problems:
            failed = True
            print(f"\nFAIL {OP_TO_FILE[op]}:", file=sys.stderr)
            for p in problems:
                print(f"  - {p}", file=sys.stderr)
        else:
            print(f"OK   {OP_TO_FILE[op]}")

    if captured:
        report_types(captured)

    if failed:
        print(
            "\nValidation failed — fixtures NOT written. Record this as a finding.",
            file=sys.stderr,
        )
        return 1
    if missing:
        return 1
    if args.dry_run:
        print("\n--dry-run: nothing written.")
        return 0

    for op, envelope in captured.items():
        path = FIXTURES / OP_TO_FILE[op]
        path.write_text(json.dumps(envelope, indent=2) + "\n")
        print(f"wrote {path.relative_to(REPO)}")

    print("\nAll three envelopes captured and validated. T1 gate released.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
