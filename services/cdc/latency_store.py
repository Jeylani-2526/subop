"""CDC latency store: five raw timestamps per change event (M8W28T4).

CDC Design Note Section 2. Persistent rather than in-memory: the consumer and
subop-api are separate processes (Design Note amendment, 18 November 2026).
"""

from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

SCHEMA = "cdc_meta"
TABLE = f"{SCHEMA}.event_latency"
WINDOW_SIZE = 100
POINTS = ("t0_ms", "t1_ms", "t2_ms", "t3_ms", "t4_ms")

# Contract Section 9.1: key -> (later point, earlier point).
HOPS = {
    "e2e": ("t4_ms", "t0_ms"),
    "capture": ("t1_ms", "t0_ms"),
    "publish": ("t2_ms", "t1_ms"),
    "consumer": ("t3_ms", "t2_ms"),
    "warehouse": ("t4_ms", "t3_ms"),
}


def _ddl(table: str) -> Tuple[str, ...]:
    schema, name = table.split(".")
    return (
        f"CREATE SCHEMA IF NOT EXISTS {schema}",
        # Keyed like event_log, so a redelivered event is a no-op. Intervals
        # are computed on read, never stored.
        f"""
    CREATE TABLE IF NOT EXISTS {table} (
        id           BIGSERIAL   PRIMARY KEY,
        table_name   TEXT        NOT NULL,
        op           TEXT        NOT NULL,
        row_key      TEXT        NOT NULL,
        lsn          BIGINT      NOT NULL,
        t0_ms        BIGINT      NOT NULL,
        t1_ms        BIGINT      NOT NULL,
        t2_ms        BIGINT      NOT NULL,
        t3_ms        BIGINT      NOT NULL,
        t4_ms        BIGINT      NOT NULL,
        recorded_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
        UNIQUE (table_name, lsn, op, row_key)
    )
    """,
        f"CREATE INDEX IF NOT EXISTS {name}_t4_idx ON {table} (t4_ms DESC)",
    )


Key = Tuple[str, int, str, str]


def row_key(event: Dict[str, Any]) -> str:
    # Same derivation as CDCStateStore.append_event, so the keys line up.
    row = event.get("after") or event.get("before") or {}
    return str(row["id"]) if "id" in row else json.dumps(row, sort_keys=True)


def _stat(value: Any) -> Any:
    # percentile_cont over integers at positions that are multiples of 0.01
    # (window <= 100) is exact to two decimals; this strips float noise only.
    return round(float(value), 2) if isinstance(value, float) else value


class LatencyStore:
    """Every method is one statement, as in CDCStateStore: the Postgres
    connector commits after each execute_write."""

    def __init__(
        self, layer: Any, window_size: int = WINDOW_SIZE, table: str = TABLE
    ) -> None:
        self._layer = layer
        self.window_size = window_size
        self.table = table

    def ensure_schema(self) -> None:
        for statement in _ddl(self.table):
            self._layer.execute_write(statement)

    def record(
        self, event: Dict[str, Any], lsn: Optional[int], points: Sequence[int]
    ) -> int:
        """Returns 1 when stored, 0 for a redelivery."""
        if lsn is None:
            return 0  # cannot be keyed, as in event_log
        return self._layer.execute_write(
            f"INSERT INTO {self.table} (table_name, op, row_key, lsn, "
            f"t0_ms, t1_ms, t2_ms, t3_ms, t4_ms) "
            f"VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) "
            f"ON CONFLICT (table_name, lsn, op, row_key) DO NOTHING",
            (event["table"], event["op"], row_key(event), lsn, *points),
        )

    def summary(self, tables: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        """Contract Section 9.2 CDCLatency over the newest window, plus lag_ms.
        None when no instrumented event exists."""
        where, params = "", [self.window_size]
        if tables is not None:
            where, params = "WHERE table_name = ANY(%s) ", [
                list(tables),
                self.window_size,
            ]
        stats = []
        for key, (later, earlier) in HOPS.items():
            d = f"({later} - {earlier})"
            stats.append(
                f"percentile_cont(0.5) WITHIN GROUP (ORDER BY {d}) AS {key}_median, "
                f"percentile_cont(0.95) WITHIN GROUP (ORDER BY {d}) AS {key}_p95, "
                f"max({d}) AS {key}_max"
            )
        rows = self._layer.execute_query(
            f"WITH w AS (SELECT * FROM {self.table} {where}"
            f"ORDER BY t4_ms DESC, id DESC LIMIT %s) "
            f"SELECT count(*) AS sample_size, "
            f"(SELECT t4_ms - t0_ms FROM w ORDER BY t4_ms DESC, id DESC LIMIT 1) AS lag_ms, "
            f"{', '.join(stats)} FROM w",
            tuple(params),
        )
        row = dict(rows[0]) if rows else {}
        if not row.get("sample_size"):
            return None
        result: Dict[str, Any] = {
            "window_size": self.window_size,
            "sample_size": row["sample_size"],
            "lag_ms": row["lag_ms"],
        }
        for key in HOPS:
            result[key] = {
                "median_ms": _stat(row[f"{key}_median"]),
                "p95_ms": _stat(row[f"{key}_p95"]),
                "max_ms": row[f"{key}_max"],
            }
        return result

    def e2e_by_key(self, keys: Iterable[Key]) -> Dict[Key, int]:
        """t4 - t0 for each (table_name, lsn, op, row_key) that has a row."""
        keys = list(keys)
        if not keys:
            return {}
        tables, lsns, ops, rks = (list(col) for col in zip(*keys))
        rows = self._layer.execute_query(
            f"SELECT l.table_name, l.lsn, l.op, l.row_key, l.t4_ms - l.t0_ms AS e2e "
            f"FROM {self.table} l JOIN unnest(%s::text[], %s::bigint[], %s::text[], %s::text[]) "
            f"AS k(table_name, lsn, op, row_key) USING (table_name, lsn, op, row_key)",
            (tables, lsns, ops, rks),
        )
        return {
            (r["table_name"], r["lsn"], r["op"], r["row_key"]): r["e2e"] for r in rows
        }
