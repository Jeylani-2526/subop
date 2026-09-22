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

Convention — two shapes, chosen per connector_type's "kind"
(_CONNECTOR_CLASSES below):

    connection_ref -> env var named
    SUBOP_CONN_<UPPERCASED_REF_WITH_NON_ALNUM_CHARS_AS_UNDERSCORE>

    - "db"-kind (postgresql, mysql, mssql): env var holds a JSON object
      {"host", "port", "database", "username", "password"}.

        Example:
            connection_ref "prod-warehouse" -> SUBOP_CONN_PROD_WAREHOUSE
            SUBOP_CONN_PROD_WAREHOUSE='{"host":"db.internal","port":5432,
                "database":"warehouse","username":"etl_svc","password":"..."}'

    - "file"-kind (sqlite, csv — M6W19T1): env var holds a JSON object
      with a single field, {"file_path"}, rather than the five-field
      credential blob — sqlite/csv connectors take one path, not
      host/port/user/pass, and forcing them through the db-kind shape
      is what left them unreachable from a real pipeline through
      Week 18 despite being built and unit-tested.

        Example:
            connection_ref "demo-sqlite" -> SUBOP_CONN_DEMO_SQLITE
            SUBOP_CONN_DEMO_SQLITE='{"file_path":"/data/demo.db"}'

    - "url"-kind (rest_api — M6W20T1): env var holds {"base_url"}.
      Passthrough, no format validation (same as "db"/"file").

        Example:
            SUBOP_CONN_ORDERS_API='{"base_url":"https://api.example.com"}'
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
#
# Each entry is (kind, config_cls, connector_cls):
#   kind = "db"   -> config_cls built from the 5-field credential blob
#                    (host, port, database, username, password), as
#                    kwargs (field names vary slightly per connector's
#                    own ConnectionConfig, so kwargs are used, not a
#                    single positional value).
#   kind = "file" -> config_cls built from a single resolved file path,
#                    passed positionally: config_cls(path). This works
#                    unchanged for both sqlite_connector.ConnectionConfig
#                    (param named `database`) and file_connector_base's
#                    FileConnectionConfig (param named `file_path`) —
#                    both take that one value as their first positional
#                    argument, so the resolver doesn't need to know
#                    which kwarg name a given file-kind connector uses.
#   kind = "url"  -> config_cls(base_url), positional, same pattern as
#                    "file" (M6W20T1).
_CONNECTOR_CLASSES: Dict[str, Tuple[str, Any, Any]] = {}


def _connector_classes() -> Dict[str, Tuple[str, Any, Any]]:
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
    from services.connectors.sqlite_connector import (
        ConnectionConfig as SqliteConfig,
        SQLiteConnector,
    )
    from services.connectors.csv_connector import CSVConnector
    from services.connectors.json_connector import JSONConnector
    from services.connectors.file_connector_base import FileConnectionConfig
    from services.connectors.rest_api_connector import (
        ConnectionConfig as RestApiConfig,
        RESTAPIConnector,
    )

    classes: Dict[str, Tuple[str, Any, Any]] = {
        "postgresql": ("db", PgConfig, PostgresConnector),
        "mysql": ("db", MyConfig, MySQLConnector),
        # sqlite / csv (M6W19T1), json (M6W19T2): all "file"-kind —
        # they take a single file path, not host/port/user/pass.
        "sqlite": ("file", SqliteConfig, SQLiteConnector),
        "csv": ("file", FileConnectionConfig, CSVConnector),
        "json": ("file", FileConnectionConfig, JSONConnector),
        "rest_api": ("url", RestApiConfig, RESTAPIConnector),  # M6W20T1
    }

    try:
        from services.connectors.mssql_connector import (
            ConnectionConfig as MsConfig,
            MSSQLConnector,
        )

        classes["mssql"] = ("db", MsConfig, MSSQLConnector)
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

    kind, config_cls, connector_cls = classes[normalized_type]

    if kind == "file":
        # file-kind (sqlite, csv — M6W19T1): a single file_path field,
        # not the five-field db credential blob.
        required_fields = ("file_path",)
    elif kind == "url":
        # url-kind (rest_api — M6W20T1): a single base_url field.
        required_fields = ("base_url",)
    else:
        required_fields = ("host", "port", "database", "username", "password")

    missing = [field for field in required_fields if field not in creds]
    if missing:
        raise ConnConnectionError(
            f"Connection '{connection_ref}' missing required field(s): {', '.join(missing)}",
            error_code="CONNECTION_REF_INCOMPLETE",
            connector_type=connector_type,
            retryable=False,
        )

    if kind == "file":
        # Passed positionally: works unchanged for both
        # sqlite_connector.ConnectionConfig(database=...) and
        # file_connector_base.FileConnectionConfig(file_path=...) since
        # both take their path as the first positional argument — see
        # the _CONNECTOR_CLASSES comment above.
        config = config_cls(creds["file_path"])
    elif kind == "url":
        config = config_cls(creds["base_url"])  # M6W20T1
    else:
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
