"""Persisted per-table CDC state: drift baselines, halts and event counts (M7W26T3)."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

# Separate schema from cdc_demo, so these writes are never published: the
# publication lists its tables explicitly (cdc_replication_setup.sql).
SCHEMA = "cdc_meta"
TABLE = f"{SCHEMA}.table_state"
EVENT_LOG = f"{SCHEMA}.event_log"

_DDL = (
    f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}",
    f"""
    CREATE TABLE IF NOT EXISTS {TABLE} (
        table_name        TEXT        PRIMARY KEY,
        baseline          JSONB,
        halted            BOOLEAN     NOT NULL DEFAULT FALSE,
        halt_error_code   TEXT,
        halt_reason       TEXT,
        halted_at         TIMESTAMPTZ,
        last_event_ts_ms  BIGINT,
        last_lsn          BIGINT,
        updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    # M7W26T6 — the history behind GET /api/cdc/events. The warehouse keeps
    # only each row's latest state, so it cannot show an insert-update-delete
    # sequence. The unique key makes a redelivered event a no-op; row_key is
    # part of it because every snapshot row shares one LSN.
    f"""
    CREATE TABLE IF NOT EXISTS {EVENT_LOG} (
        id          BIGSERIAL   PRIMARY KEY,
        table_name  TEXT        NOT NULL,
        op          TEXT        NOT NULL,
        row_key     TEXT        NOT NULL,
        lsn         BIGINT      NOT NULL,
        ts_ms       BIGINT      NOT NULL,
        before      JSONB,
        after       JSONB,
        logged_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
        UNIQUE (table_name, lsn, op, row_key)
    )
    """,
    # M7W27T1 Finding 4 — a running counter counted redeliveries too; the count
    # now comes from event_log, which keeps each event once. Drops the column
    # from databases created before this change.
    f"ALTER TABLE {TABLE} DROP COLUMN IF EXISTS events_processed",
)


class CDCStateStore:
    """Reads and writes cdc_meta.table_state through the Abstraction Layer.

    Every method is one statement, because the Postgres connector commits
    after each execute_write: a multi-statement method could leave the row
    half-updated if the process stopped between two of them.
    """

    def __init__(self, layer: Any) -> None:
        self._layer = layer

    def ensure_schema(self) -> None:
        for statement in _DDL:
            self._layer.execute_write(statement)

    def load(self) -> Dict[str, Dict[str, Any]]:
        rows = self._layer.execute_query(
            f"SELECT s.table_name, s.baseline, s.halted, s.halt_error_code, "
            f"s.halt_reason, s.halted_at, s.last_event_ts_ms, s.last_lsn, "
            f"(SELECT count(*) FROM {EVENT_LOG} e "
            f"WHERE e.table_name = s.table_name) AS events_processed "
            f"FROM {TABLE} s ORDER BY s.table_name"
        )
        state = {}
        for row in rows:
            entry = dict(row)
            baseline = entry.get("baseline")
            if isinstance(baseline, str):
                entry["baseline"] = json.loads(baseline)
            state[entry["table_name"]] = entry
        return state

    def save_baseline(self, table: str, snapshot: Dict[str, str]) -> None:
        self._layer.execute_write(
            f"INSERT INTO {TABLE} (table_name, baseline) VALUES (%s, %s::jsonb) "
            f"ON CONFLICT (table_name) DO UPDATE "
            f"SET baseline = EXCLUDED.baseline, updated_at = now()",
            (table, json.dumps(snapshot, sort_keys=True)),
        )

    def record_event(self, table: str, ts_ms: int, lsn: Optional[int]) -> None:
        self._layer.execute_write(
            f"INSERT INTO {TABLE} (table_name, last_event_ts_ms, last_lsn) "
            f"VALUES (%s, %s, %s) "
            f"ON CONFLICT (table_name) DO UPDATE SET "
            f"last_event_ts_ms = EXCLUDED.last_event_ts_ms, "
            f"last_lsn = COALESCE(EXCLUDED.last_lsn, {TABLE}.last_lsn), "
            f"updated_at = now()",
            (table, ts_ms, lsn),
        )

    def record_halt(self, table: str, error_code: str, reason: str) -> None:
        # halted_at keeps the first halt time: a restart redelivers the same
        # message and halts again, which is not a new incident.
        self._layer.execute_write(
            f"INSERT INTO {TABLE} (table_name, halted, halt_error_code, halt_reason, halted_at) "
            f"VALUES (%s, TRUE, %s, %s, now()) "
            f"ON CONFLICT (table_name) DO UPDATE SET halted = TRUE, "
            f"halt_error_code = EXCLUDED.halt_error_code, "
            f"halt_reason = EXCLUDED.halt_reason, "
            f"halted_at = COALESCE({TABLE}.halted_at, EXCLUDED.halted_at), "
            f"updated_at = now()",
            (table, error_code, reason),
        )

    def append_event(self, event: Dict[str, Any], lsn: Optional[int]) -> None:
        if lsn is None:
            return  # cannot be deduplicated, so not logged
        row = event.get("after") or event.get("before") or {}
        row_key = str(row["id"]) if "id" in row else json.dumps(row, sort_keys=True)
        self._layer.execute_write(
            f"INSERT INTO {EVENT_LOG} (table_name, op, row_key, lsn, ts_ms, before, after) "
            f"VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s::jsonb) "
            f"ON CONFLICT (table_name, lsn, op, row_key) DO NOTHING",
            (
                event["table"],
                event["op"],
                row_key,
                lsn,
                event["ts_ms"],
                _json_or_none(event.get("before")),
                _json_or_none(event.get("after")),
            ),
        )

    def recent_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        rows = self._layer.execute_query(
            f"SELECT op, table_name, before, after, ts_ms FROM {EVENT_LOG} "
            f"ORDER BY lsn DESC, id DESC LIMIT %s",
            (limit,),
        )
        events = []
        for row in rows:
            entry = dict(row)
            events.append(
                {
                    "op": entry["op"],
                    "table": entry["table_name"],
                    "before": _parsed(entry["before"]),
                    "after": _parsed(entry["after"]),
                    "ts_ms": entry["ts_ms"],
                }
            )
        return events

    def clear_halt(self, table: str) -> None:
        """A message for a restored halted table was handled successfully, so
        the halt no longer reproduces. The baseline is kept."""
        self._layer.execute_write(
            f"UPDATE {TABLE} SET halted = FALSE, halt_error_code = NULL, "
            f"halt_reason = NULL, halted_at = NULL, updated_at = now() "
            f"WHERE table_name = %s",
            (table,),
        )

    def reset(self, table: str) -> None:
        """Manual resolution path: clear the halt and the baseline, so the
        next message for this table establishes a new one."""
        self._layer.execute_write(
            f"UPDATE {TABLE} SET baseline = NULL, halted = FALSE, "
            f"halt_error_code = NULL, halt_reason = NULL, halted_at = NULL, "
            f"updated_at = now() WHERE table_name = %s",
            (table,),
        )


def _json_or_none(value: Any) -> Optional[str]:
    return None if value is None else json.dumps(value, default=str)


def _parsed(value: Any) -> Any:
    return json.loads(value) if isinstance(value, str) else value
