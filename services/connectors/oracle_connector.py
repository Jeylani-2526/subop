import oracledb

from services.connectors.errors import (
    ConnectionError as ConnectorConnectionError,
    QueryError,
    WriteError,
)

_CONNECTOR_TYPE = "oracle"


class ConnectionConfig:
    """Stores the connection settings for Oracle."""

    def __init__(self, host, port, database, username, password):
        self.host = host
        self.port = port
        self.database = database
        self.username = username
        self.password = password


class OracleConnector:
    def __init__(self, config):
        self.config = config
        self.connection = None

    def connect(self):
        """Connect to the Oracle database using python-oracledb thin mode."""
        try:
            dsn = oracledb.makedsn(
                self.config.host,
                self.config.port,
                service_name=self.config.database,
            )

            self.connection = oracledb.connect(
                user=self.config.username,
                password=self.config.password,
                dsn=dsn,
            )

        except oracledb.Error as e:
            raise ConnectorConnectionError(
                f"Connection failed: {e}",
                error_code="ORACLE_CONNECTION_FAILED",
                connector_type=_CONNECTOR_TYPE,
                retryable=False,
            )

    def disconnect(self):
        """Close the current database connection."""
        if self.connection:
            self.connection.close()
            self.connection = None

    def execute_query(self, sql, params=None):
        """Run a SELECT query and return rows as dictionaries."""
        if self.connection is None:
            raise QueryError(
                "Not connected. Call connect() first.",
                error_code="ORACLE_NOT_CONNECTED",
                connector_type=_CONNECTOR_TYPE,
                retryable=False,
            )

        cursor = None

        try:
            cursor = self.connection.cursor()
            cursor.execute(sql, params or {})

            columns = [column[0] for column in cursor.description]
            rows = cursor.fetchall()

            return [dict(zip(columns, row)) for row in rows]

        except oracledb.Error as e:
            raise QueryError(
                f"Query failed: {e}",
                error_code="ORACLE_QUERY_FAILED",
                connector_type=_CONNECTOR_TYPE,
                retryable=False,
            )

        finally:
            if cursor is not None:
                cursor.close()

    def execute_write(self, sql, params=None):
        """Run INSERT, UPDATE or DELETE and return affected row count."""
        if self.connection is None:
            raise WriteError(
                "Not connected. Call connect() first.",
                error_code="ORACLE_NOT_CONNECTED",
                connector_type=_CONNECTOR_TYPE,
                retryable=False,
            )

        cursor = None

        try:
            cursor = self.connection.cursor()
            cursor.execute(sql, params or {})

            affected_rows = cursor.rowcount

            self.connection.commit()

            return affected_rows

        except oracledb.Error as e:
            self.connection.rollback()

            raise WriteError(
                f"Write failed: {e}",
                error_code="ORACLE_WRITE_FAILED",
                connector_type=_CONNECTOR_TYPE,
                retryable=False,
            )

        finally:
            if cursor is not None:
                cursor.close()

    def health_check(self):
        """Check whether the database connection works."""
        try:
            result = self.execute_query("SELECT 1 AS health FROM DUAL")
            return len(result) > 0
        except Exception:
            return False