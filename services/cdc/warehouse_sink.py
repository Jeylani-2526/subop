"""Apply CDC events to warehouse tables, idempotently (M7W26T4).

A source change reaches warehouse storage with no scheduled pipeline run:
the consumer hands each event to WarehouseSink, which writes it through the
Abstraction Layer's execute_write, never a direct connection.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from services.connectors.errors import WriteError

log = logging.getLogger("subop.cdc.warehouse")

DEFAULT_SCHEMA = "warehouse"
_CONNECTOR_TYPE = "streaming"


@dataclass(frozen=True)
class TableSpec:
    target: str
    key: str
    columns: Tuple[Tuple[str, str], ...]


# Hand-written on purpose. Generating these from source metadata is M8's
# metadata-driven warehouse; M7 must not depend on the milestone after it.
TABLES: Dict[str, TableSpec] = {
    "cdc_demo.orders": TableSpec(
        target="orders",
        key="id",
        columns=(
            ("id", "BIGINT"),
            ("customer_id", "BIGINT"),
            ("status", "VARCHAR(32)"),
            ("amount", "NUMERIC(12, 2)"),
            ("created_at", "TIMESTAMPTZ"),
            ("updated_at", "TIMESTAMPTZ"),
        ),
    ),
    "cdc_demo.customers": TableSpec(
        target="customers",
        key="id",
        columns=(
            ("id", "BIGINT"),
            ("name", "VARCHAR(64)"),
            ("city", "VARCHAR(64)"),
            ("created_at", "TIMESTAMPTZ"),
            ("updated_at", "TIMESTAMPTZ"),
        ),
    ),
}

# _cdc_lsn orders changes: it increases with every WAL record, whereas ts_ms
# is the transaction's commit time and repeats for two changes to one row in
# the same transaction. _cdc_ts_ms is kept as data for M8's latency work.
_CDC_COLUMNS = (
    ("_cdc_lsn", "BIGINT NOT NULL"),
    ("_cdc_ts_ms", "BIGINT NOT NULL"),
    ("_cdc_op", "TEXT NOT NULL"),
    ("_cdc_deleted", "BOOLEAN NOT NULL DEFAULT FALSE"),
    ("_cdc_applied_at", "TIMESTAMPTZ NOT NULL DEFAULT now()"),
)


def _write_error(message: str, code: str) -> WriteError:
    return WriteError(
        message, error_code=code, connector_type=_CONNECTOR_TYPE, retryable=False
    )


class WarehouseSink:
    """Handler for KafkaCDCConnector: one upsert statement per event.

    Idempotent by construction. The upsert only overwrites a row whose stored
    LSN is lower than the incoming one, so a redelivered event (same LSN) and
    a stale one (lower LSN) both change nothing.

    Deletes are soft: the row is kept with _cdc_deleted = TRUE and the delete's
    LSN. A hard delete would discard that LSN, and a replayed older change
    could then bring the row back. Readers filter on _cdc_deleted.
    """

    def __init__(self, layer: Any, schema: str = DEFAULT_SCHEMA) -> None:
        self._layer = layer
        self.schema = schema
        self._sql = {source: self._upsert_sql(spec) for source, spec in TABLES.items()}

    def ensure_schema(self) -> None:
        self._layer.execute_write(f"CREATE SCHEMA IF NOT EXISTS {self.schema}")
        for spec in TABLES.values():
            columns = ",\n    ".join(
                f"{name} {sqltype}" for name, sqltype in spec.columns
            )
            cdc = ",\n    ".join(f"{name} {sqltype}" for name, sqltype in _CDC_COLUMNS)
            self._layer.execute_write(
                f"CREATE TABLE IF NOT EXISTS {self.schema}.{spec.target} (\n"
                f"    {columns},\n    {cdc},\n    PRIMARY KEY ({spec.key})\n)"
            )

    def __call__(self, event: Dict[str, Any], meta: Dict[str, Any]) -> int:
        return self.apply(event, meta)

    def apply(self, event: Dict[str, Any], meta: Dict[str, Any]) -> int:
        """Write one event. Returns rows affected: 0 means it was a duplicate
        or older than what the warehouse already holds."""
        table = event["table"]
        spec = TABLES.get(table)
        if spec is None:
            raise _write_error(
                f"No warehouse table is mapped for {table}.", "CDC_TABLE_NOT_MAPPED"
            )

        lsn = meta.get("lsn")
        if not isinstance(lsn, int):
            raise _write_error(
                f"Event for {table} carries no LSN; it cannot be ordered safely.",
                "CDC_LSN_MISSING",
            )

        deleted = event["op"] == "delete"
        row = event["before"] if deleted else event["after"]
        if not isinstance(row, dict):
            raise _write_error(
                f"{event['op']} on {table} has no row image to apply.",
                "CDC_ROW_MISSING",
            )

        missing = [name for name, _ in spec.columns if name not in row]
        if missing:
            raise _write_error(
                f"{event['op']} on {table} is missing column(s) {missing}.",
                "CDC_ROW_INCOMPLETE",
            )

        params = [row[name] for name, _ in spec.columns]
        params += [lsn, event["ts_ms"], event["op"], deleted]
        affected = self._layer.execute_write(self._sql[table], params)
        if not affected:
            log.debug(
                "skipped %s %s: lsn %s not newer than stored", event["op"], table, lsn
            )
        return affected

    def _upsert_sql(self, spec: TableSpec) -> str:
        names: List[str] = [name for name, _ in spec.columns]
        names += ["_cdc_lsn", "_cdc_ts_ms", "_cdc_op", "_cdc_deleted"]
        target = f"{self.schema}.{spec.target}"
        updates = ", ".join(
            f"{name} = EXCLUDED.{name}" for name in names if name != spec.key
        )
        return (
            f"INSERT INTO {target} ({', '.join(names)}) "
            f"VALUES ({', '.join(['%s'] * len(names))}) "
            f"ON CONFLICT ({spec.key}) DO UPDATE SET {updates}, _cdc_applied_at = now() "
            f"WHERE {target}._cdc_lsn < EXCLUDED._cdc_lsn"
        )
