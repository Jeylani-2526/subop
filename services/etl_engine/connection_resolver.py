"""
Resolves a Pipeline DSL (connector_type, connection_ref) pair into a
live AbstractionLayer the executor can call execute_query/execute_write
on — ETL Engine never opens a direct DB connection or holds credentials
itself (contracts Section 4).

Per etl_engine_api_spec_v1.md Section 2.1: "connection_ref: Reference to
a pre-registered connection (credentials never live in the DSL)." This
module implements that pre-registration as environment variables,
confirmed for M5 (Week 15 task discussion) as the simplest approach that
satisfies the constraint without adding new infrastructure. A future
secrets-manager-backed resolver can replace the body of
resolve_connection() without changing its signature, so nothing above
this module needs to change if that happens later.

Convention:
    connection_ref -> env var named
    SUBOP_CONN_<UPPERCASED_REF_WITH_NON_ALNUM_CHARS_AS_UNDERSCORE>,
    holding a JSON object: {"host", "port", "database", "username",
    "password"}.

    Example:
        connection_ref "prod-warehouse" -> SUBOP_CONN_PROD_WAREHOUSE
        SUBOP_CONN_PROD_WAREHOUSE='{"host":"db.internal","port":5432,
            "database":"warehouse","username":"etl_svc","password":"..."}'
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, Tuple

from services.abstraction.abstraction_layer import AbstractionLayer
from services.connectors.errors import ConnectionError as ConnConnectionError

_ENV_PREFIX = "SUBOP_CONN_"

# Populated lazily so importing this module never hard-requires a driver
# (e.g. pyodbc/unixODBC) that may not be installed in every environment —
# a pipeline that never touches MSSQL shouldn't fail to import over it.
_CONNECTOR_CLASSES: Dict[str, Tuple[Any, Any]] = {}


def _connector_classes() -> Dict[str, Tuple[Any, Any]]:
    global _CONNECTOR_CLASSES
    if _CONNECTOR_CLASSES:
        return _CONNECTOR_CLASSES

    from services.connectors.postgres_connector import (
        ConnectionConfig as PgConfig,
        PostgresConnector,
    )
    from services.connectors.mysql_connector import (
        ConnectionConfig as MyConfig,
        MySQLConnector,
    )

    classes: Dict[str, Tuple[Any, Any]] = {
        "postgresql": (PgConfig, PostgresConnector),
        "mysql": (MyConfig, MySQLConnector),
    }

    try:
        from services.connectors.mssql_connector import (
            ConnectionConfig as MsConfig,
            MSSQLConnector,
        )

        classes["mssql"] = (MsConfig, MSSQLConnector)
    except ImportError:
        # ODBC driver not available in this environment. An MSSQL
        # pipeline will fail clearly at resolve_connection() time with
        # UNSUPPORTED_CONNECTOR_TYPE rather than at import time.
        pass

    # mongodb intentionally omitted: no MongoDB connector exists in the
    # repo yet on either branch (confirmed during Week 15 repo audit).
    # A pipeline naming it fails the same clear way as MSSQL without a
    # driver, not a crash.

    _CONNECTOR_CLASSES = classes
    return classes


def _env_var_name(connection_ref: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]", "_", connection_ref.strip()).upper()
    return f"{_ENV_PREFIX}{slug}"


def resolve_connection(
    connector_type: str, connection_ref: str
) -> Tuple[AbstractionLayer, str]:
    """
    Resolve a DSL (connector_type, connection_ref) pair into
    (AbstractionLayer, database) the executor calls execute_query /
    execute_write on.

    Always raises a typed ConnectorError (non-retryable) rather than a
    raw KeyError/JSONDecodeError — consistent with the rest of the
    connector layer's error contract, and directly usable by T4's API
    routes to build the shared error envelope (API spec Section 5).
    """
    normalized_type = connector_type.strip().lower()
    classes = _connector_classes()

    if normalized_type not in classes:
        raise ConnConnectionError(
            f"Unsupported or unavailable connector_type: {connector_type}",
            error_code="UNSUPPORTED_CONNECTOR_TYPE",
            connector_type=connector_type,
            retryable=False,
        )

    env_var = _env_var_name(connection_ref)
    raw = os.environ.get(env_var)

    if raw is None:
        raise ConnConnectionError(
            f"No connection registered for connection_ref '{connection_ref}' "
            f"(expected environment variable {env_var}).",
            error_code="CONNECTION_REF_NOT_FOUND",
            connector_type=connector_type,
            retryable=False,
        )

    try:
        creds: Dict[str, Any] = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ConnConnectionError(
            f"Malformed connection credentials for '{connection_ref}' in {env_var}: {e}",
            error_code="CONNECTION_REF_MALFORMED",
            connector_type=connector_type,
            retryable=False,
        )

    required_fields = ("host", "port", "database", "username", "password")
    missing = [field for field in required_fields if field not in creds]
    if missing:
        raise ConnConnectionError(
            f"Connection '{connection_ref}' missing required field(s): {', '.join(missing)}",
            error_code="CONNECTION_REF_INCOMPLETE",
            connector_type=connector_type,
            retryable=False,
        )

    config_cls, connector_cls = classes[normalized_type]
    config = config_cls(
        host=creds["host"],
        port=creds["port"],
        database=creds["database"],
        username=creds["username"],
        password=creds["password"],
    )

    connector = connector_cls(config)
    connector.connect()  # raises a typed ConnectionError on failure

    return (
        AbstractionLayer(connector=connector, database=normalized_type),
        normalized_type,
    )


def release_connection(layer: AbstractionLayer) -> None:
    """Disconnect the underlying connector held by an AbstractionLayer."""
    disconnect = getattr(layer.connector, "disconnect", None)
    if callable(disconnect):
        disconnect()
