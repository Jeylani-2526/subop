#!/usr/bin/env python3
"""Derive the hand-authored CDC fixtures from the real captured insert.json.

M7W26T2. Each derived fixture is the real envelope with exactly one documented
change applied, so a drift test failure names the change responsible. Re-run
after any recapture of insert.json.
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List

REPO = Path(__file__).resolve().parents[2]
FIXTURES = REPO / "tests" / "fixtures" / "cdc"
PARAM_PREFIX = "__debezium.source.column."
TS_SHIFT_MS = 10_000

Envelope = Dict[str, Any]


def row_structs(env: Envelope) -> List[Dict[str, Any]]:
    """The before and after Value structs — both carry the column list."""
    return [
        f
        for f in env["schema"]["fields"]
        if f.get("field") in ("before", "after") and isinstance(f.get("fields"), list)
    ]


def column(struct: Dict[str, Any], name: str) -> Dict[str, Any]:
    for f in struct["fields"]:
        if f.get("field") == name:
            return f
    raise KeyError(f"column {name!r} not in struct")


def shift_timestamps(env: Envelope, ms: int = TS_SHIFT_MS) -> None:
    """Move commit and processing time later, as a later change would be."""
    payload = env["payload"]
    for block in (payload, payload["source"]):
        block["ts_ms"] += ms
        if block.get("ts_us") is not None:
            block["ts_us"] += ms * 1_000
        if block.get("ts_ns") is not None:
            block["ts_ns"] += ms * 1_000_000


def set_params(env: Envelope, name: str, **params: str) -> None:
    for struct in row_structs(env):
        target = column(struct, name)["parameters"]
        for key, value in params.items():
            target[PARAM_PREFIX + key] = value


def column_added(env: Envelope) -> None:
    for struct in row_structs(env):
        struct["fields"].append(
            {
                "type": "string",
                "optional": True,
                "parameters": {
                    PARAM_PREFIX + "type": "NUMERIC",
                    PARAM_PREFIX + "length": "5",
                    PARAM_PREFIX + "scale": "2",
                    PARAM_PREFIX + "name": "discount",
                },
                "field": "discount",
            }
        )
    env["payload"]["after"]["discount"] = "5.00"
    shift_timestamps(env)


def column_dropped(env: Envelope) -> None:
    for struct in row_structs(env):
        struct["fields"] = [
            f for f in struct["fields"] if f.get("field") != "updated_at"
        ]
    env["payload"]["after"].pop("updated_at")
    shift_timestamps(env)


def column_renamed(env: Envelope) -> None:
    for struct in row_structs(env):
        target = column(struct, "status")
        target["field"] = "order_status"
        target["parameters"][PARAM_PREFIX + "name"] = "order_status"
    after = env["payload"]["after"]
    env["payload"]["after"] = {
        ("order_status" if k == "status" else k): v for k, v in after.items()
    }
    shift_timestamps(env)


def type_changed(env: Envelope) -> None:
    # The length/scale Debezium emits for TEXT has not been captured. Both are
    # removed rather than invented; the normaliser drops them for TEXT anyway.
    for struct in row_structs(env):
        params = column(struct, "status")["parameters"]
        params[PARAM_PREFIX + "type"] = "TEXT"
        params.pop(PARAM_PREFIX + "length", None)
        params.pop(PARAM_PREFIX + "scale", None)
    shift_timestamps(env)


def column_widened(env: Envelope) -> None:
    set_params(env, "status", length="64")
    shift_timestamps(env)


def numeric_rescaled(env: Envelope) -> None:
    set_params(env, "amount", length="14", scale="4")
    shift_timestamps(env)


def truncate(env: Envelope) -> None:
    env["payload"]["op"] = "t"
    env["payload"]["before"] = None
    env["payload"]["after"] = None
    shift_timestamps(env, 150)


def ts_ms_source_vs_processing(env: Envelope) -> None:
    # Years apart, so "ts_ms is not processing time" can never pass by
    # coincidence. Real envelopes often land in the same millisecond.
    env["payload"]["source"]["ts_ms"] = 1_700_000_000_000
    env["payload"]["ts_ms"] = 1_799_999_999_999


def strip_native_types(env: Envelope) -> None:
    """What the connector emits without column.propagate.source.type."""
    for struct in row_structs(env):
        for f in struct["fields"]:
            params = f.get("parameters")
            if not isinstance(params, dict):
                continue
            for key in [k for k in params if k.startswith(PARAM_PREFIX)]:
                params.pop(key)
            if not params:
                f.pop("parameters")


def connect_types_only_widened(env: Envelope) -> None:
    # A genuinely widened envelope with propagation off. Previously a byte
    # copy of connect_types_only.json, which made the invisibility test
    # compare a file with itself.
    column_widened(env)
    strip_native_types(env)


DERIVED: Dict[str, Callable[[Envelope], None]] = {
    "drift_column_added.json": column_added,
    "drift_column_dropped.json": column_dropped,
    "drift_column_renamed.json": column_renamed,
    "drift_type_changed.json": type_changed,
    "drift_column_widened.json": column_widened,
    "drift_numeric_rescaled.json": numeric_rescaled,
    "truncate.json": truncate,
    "ts_ms_source_vs_processing.json": ts_ms_source_vs_processing,
    "connect_types_only.json": strip_native_types,
    "connect_types_only_widened.json": connect_types_only_widened,
}


def main() -> int:
    base_path = FIXTURES / "insert.json"
    base = json.loads(base_path.read_text(encoding="utf-8"))
    if base.get("payload", {}).get("op") != "c":
        print(
            "insert.json is not an op=c envelope; refusing to derive.", file=sys.stderr
        )
        return 1

    for filename, mutate in DERIVED.items():
        env = copy.deepcopy(base)
        mutate(env)
        (FIXTURES / filename).write_text(
            json.dumps(env, indent=2) + "\n", encoding="utf-8"
        )
        print(f"derived {filename}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
