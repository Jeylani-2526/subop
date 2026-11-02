"""Generate reproducible CDC change events against cdc_demo.orders (M7W23T2)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import timezone
from typing import Any, Dict, Optional, Tuple

import psycopg2
from psycopg2 import sql

from services.connectors.errors import (
    ConnectionError as ConnectorConnectionError,
    WriteError,
)

_CONNECTOR_TYPE = "postgresql"
_CONNECTION_REF = "pg-main"
_DEFAULT_SCHEMA = "cdc_demo"
_TABLE = "orders"

_DEMO_CUSTOMER_ID = 9001
_DEMO_AMOUNT = "149.90"
_SHIPPED = "shipped"


def _env_var_name(connection_ref: str) -> str:
    """Mirror connection_resolver's SUBOP_CONN_<REF> convention."""
    slug = connection_ref.strip().replace("-", "_").upper()
    return f"SUBOP_CONN_{slug}"


def _load_credentials() -> Dict[str, Any]:
    env_var = _env_var_name(_CONNECTION_REF)
    raw = os.environ.get(env_var)

    if raw is None:
        raise ConnectorConnectionError(
            f"No connection registered for '{_CONNECTION_REF}' "
            f"(expected environment variable {env_var}).",
            error_code="CONNECTION_REF_NOT_FOUND",
            connector_type=_CONNECTOR_TYPE,
            retryable=False,
        )

    try:
        creds = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ConnectorConnectionError(
            f"Malformed credentials in {env_var}: {e}",
            error_code="CONNECTION_REF_MALFORMED",
            connector_type=_CONNECTOR_TYPE,
            retryable=False,
        )

    required = ("host", "port", "database", "username", "password")
    missing = [field for field in required if field not in creds]
    if missing:
        raise ConnectorConnectionError(
            f"Connection '{_CONNECTION_REF}' missing field(s): "
            f"{', '.join(missing)}",
            error_code="CONNECTION_REF_INCOMPLETE",
            connector_type=_CONNECTOR_TYPE,
            retryable=False,
        )

    return creds


def connect():
    """Open a psycopg2 connection resolved from SUBOP_CONN_PG_MAIN."""
    creds = _load_credentials()
    try:
        return psycopg2.connect(
            host=creds["host"],
            port=creds["port"],
            database=creds["database"],
            user=creds["username"],
            password=creds["password"],
        )
    except psycopg2.DatabaseError as e:
        raise ConnectorConnectionError(
            f"Connection failed: {e}",
            error_code="POSTGRES_CONNECTION_FAILED",
            connector_type=_CONNECTOR_TYPE,
            retryable=False,
        )


def _qualified_table(schema: str):
    return sql.SQL("{}.{}").format(sql.Identifier(schema), sql.Identifier(_TABLE))


def _schema() -> str:
    return os.environ.get("SUBOP_CDC_SCHEMA", _DEFAULT_SCHEMA)


def _commit_timestamps_available(conn) -> bool:
    with conn.cursor() as cur:
        cur.execute("SHOW track_commit_timestamp;")
        return cur.fetchone()[0] == "on"


def _format_ts(value) -> Tuple[Optional[str], Optional[int]]:
    """Return (ISO-8601 UTC, epoch milliseconds) for a timestamptz."""
    if value is None:
        return None, None
    utc = value.astimezone(timezone.utc)
    return utc.isoformat(), int(utc.timestamp() * 1000)


def _commit_ts_from_row(conn, schema: str, order_id: int):
    """Read the commit timestamp of the row's current version via xmin."""
    with conn.cursor() as cur:
        cur.execute(
            sql.SQL(
                "SELECT pg_xact_commit_timestamp(xmin) FROM {} WHERE id = %s"
            ).format(_qualified_table(schema)),
            (order_id,),
        )
        row = cur.fetchone()
        return row[0] if row else None


def _commit_ts_from_txid(conn, txid: int):
    """Resolve a committed transaction's timestamp. Used for DELETE, whose
    row no longer exists to read xmin from."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT pg_xact_commit_timestamp(%s::text::xid)",
            (txid,),
        )
        return cur.fetchone()[0]


def _report(operation: str, order_id: int, commit_ts, extra: str = "") -> None:
    iso, epoch_ms = _format_ts(commit_ts)
    if iso is None:
        stamp = "commit_ts=unavailable"
    else:
        stamp = f"commit_ts={iso} commit_ts_ms={epoch_ms}"
    suffix = f" {extra}" if extra else ""
    print(f"{operation:<6} id={order_id} {stamp}{suffix}")


def _latest_id(conn, schema: str) -> int:
    with conn.cursor() as cur:
        cur.execute(sql.SQL("SELECT max(id) FROM {}").format(_qualified_table(schema)))
        order_id = cur.fetchone()[0]
    if order_id is None:
        raise WriteError(
            f"{schema}.{_TABLE} is empty — nothing to update or delete.",
            error_code="CDC_DEMO_TABLE_EMPTY",
            connector_type=_CONNECTOR_TYPE,
            retryable=False,
        )
    return order_id


def insert_order(conn, customer_id: int = _DEMO_CUSTOMER_ID) -> int:
    """INSERT one row. Returns the new id."""
    schema = _schema()
    try:
        with conn.cursor() as cur:
            cur.execute(
                sql.SQL(
                    "INSERT INTO {} (customer_id, status, amount) "
                    "VALUES (%s, 'pending', %s) RETURNING id"
                ).format(_qualified_table(schema)),
                (customer_id, _DEMO_AMOUNT),
            )
            order_id = cur.fetchone()[0]
        conn.commit()
    except psycopg2.DatabaseError as e:
        conn.rollback()
        raise WriteError(
            f"INSERT failed: {e}",
            error_code="CDC_DEMO_INSERT_FAILED",
            connector_type=_CONNECTOR_TYPE,
            retryable=False,
        )

    commit_ts = (
        _commit_ts_from_row(conn, schema, order_id)
        if _commit_timestamps_available(conn)
        else None
    )
    _report("INSERT", order_id, commit_ts, f"customer_id={customer_id}")
    return order_id


def update_order(conn, order_id: Optional[int] = None) -> int:
    """UPDATE one row to status='shipped' — Architecture Section 5.2's
    worked example, so Week 25 instruments the specified scenario."""
    schema = _schema()
    target = order_id if order_id is not None else _latest_id(conn, schema)

    try:
        with conn.cursor() as cur:
            cur.execute(
                sql.SQL(
                    "UPDATE {} SET status = %s, updated_at = now() "
                    "WHERE id = %s RETURNING id"
                ).format(_qualified_table(schema)),
                (_SHIPPED, target),
            )
            row = cur.fetchone()
            if row is None:
                conn.rollback()
                raise WriteError(
                    f"No row with id={target} in {schema}.{_TABLE}.",
                    error_code="CDC_DEMO_ROW_NOT_FOUND",
                    connector_type=_CONNECTOR_TYPE,
                    retryable=False,
                )
        conn.commit()
    except psycopg2.DatabaseError as e:
        conn.rollback()
        raise WriteError(
            f"UPDATE failed: {e}",
            error_code="CDC_DEMO_UPDATE_FAILED",
            connector_type=_CONNECTOR_TYPE,
            retryable=False,
        )

    commit_ts = (
        _commit_ts_from_row(conn, schema, target)
        if _commit_timestamps_available(conn)
        else None
    )
    _report("UPDATE", target, commit_ts, f"status={_SHIPPED}")
    return target


def delete_order(conn, order_id: Optional[int] = None) -> int:
    """DELETE one row. The commit timestamp comes from the transaction id
    rather than xmin, the row being gone by the time it is read."""
    schema = _schema()
    target = order_id if order_id is not None else _latest_id(conn, schema)
    track = _commit_timestamps_available(conn)

    try:
        with conn.cursor() as cur:
            cur.execute(
                sql.SQL("DELETE FROM {} WHERE id = %s RETURNING id").format(
                    _qualified_table(schema)
                ),
                (target,),
            )
            row = cur.fetchone()
            if row is None:
                conn.rollback()
                raise WriteError(
                    f"No row with id={target} in {schema}.{_TABLE}.",
                    error_code="CDC_DEMO_ROW_NOT_FOUND",
                    connector_type=_CONNECTOR_TYPE,
                    retryable=False,
                )
            txid = None
            if track:
                cur.execute("SELECT txid_current()")
                txid = cur.fetchone()[0]
        conn.commit()
    except psycopg2.DatabaseError as e:
        conn.rollback()
        raise WriteError(
            f"DELETE failed: {e}",
            error_code="CDC_DEMO_DELETE_FAILED",
            connector_type=_CONNECTOR_TYPE,
            retryable=False,
        )

    commit_ts = _commit_ts_from_txid(conn, txid) if txid is not None else None
    _report("DELETE", target, commit_ts)
    return target


def run_all(conn) -> int:
    """INSERT, then UPDATE and DELETE that same row, so the table is left
    exactly as it was found — Week 25's repeated latency runs each start
    from identical state."""
    order_id = insert_order(conn)
    update_order(conn, order_id)
    delete_order(conn, order_id)
    return order_id


def _parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description=(
            "Issue INSERT / UPDATE / DELETE against the CDC demo table "
            "to produce change events on demand."
        )
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--insert", action="store_true", help="INSERT one row")
    group.add_argument(
        "--update", action="store_true", help="UPDATE one row to status='shipped'"
    )
    group.add_argument("--delete", action="store_true", help="DELETE one row")
    group.add_argument(
        "--all",
        action="store_true",
        help="INSERT, then UPDATE and DELETE that same row",
    )
    parser.add_argument(
        "--id",
        type=int,
        default=None,
        help="Target row for --update/--delete (default: highest id)",
    )
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = _parse_args(argv)
    conn = None
    try:
        conn = connect()
        if not _commit_timestamps_available(conn):
            print(
                "NOTE track_commit_timestamp is off — commit_ts unavailable. "
                "Enable it on the postgres service to record commit times.",
                file=sys.stderr,
            )
        if args.all:
            run_all(conn)
        elif args.insert:
            insert_order(conn)
        elif args.update:
            update_order(conn, args.id)
        else:
            delete_order(conn, args.id)
    except (ConnectorConnectionError, WriteError) as e:
        print(json.dumps(e.to_envelope()), file=sys.stderr)
        return 1
    finally:
        if conn is not None:
            conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
