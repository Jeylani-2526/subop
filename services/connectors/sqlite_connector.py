import sqlite3

from services.connectors.errors import (
    ConnectionError as ConnectorConnectionError,
    QueryError,
    WriteError,
)

_CONNECTOR_TYPE = "sqlite"


class ConnectionConfig:
    """Stores the connection settings for SQLite."""

    def __init__(self, database):
        self.database = database


class SQLiteConnector:
    def __init__(self, config):
        self.config = config
        self.connection = None

    def connect(self):
        """Connect to the SQLite database."""
        try:
            self.connection = sqlite3.connect(self.config.database)
            self.connection.row_factory = sqlite3.Row
        except sqlite3.Error as e:
            raise ConnectorConnectionError(
                f"Connection failed: {e}",
                error_code="SQLITE_CONNECTION_FAILED",
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
                error_code="SQLITE_NOT_CONNECTED",
                connector_type=_CONNECTOR_TYPE,
                retryable=False,
            )

        cursor = None
        try:
            cursor = self.connection.cursor()
            cursor.execute(sql, params or ())
            rows = cursor.fetchall()

            return [dict(row) for row in rows]

        except sqlite3.Error as e:
            raise QueryError(
                f"Query failed: {e}",
                error_code="SQLITE_QUERY_FAILED",
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
                error_code="SQLITE_NOT_CONNECTED",
                connector_type=_CONNECTOR_TYPE,
                retryable=False,
            )

        cursor = None
        try:
            cursor = self.connection.cursor()
            cursor.execute(sql, params or ())

            affected_rows = cursor.rowcount
            self.connection.commit()

            return affected_rows

        except sqlite3.Error as e:
            self.connection.rollback()
            raise WriteError(
                f"Write failed: {e}",
                error_code="SQLITE_WRITE_FAILED",
                connector_type=_CONNECTOR_TYPE,
                retryable=False,
            )

        finally:
            if cursor is not None:
                cursor.close()

    def health_check(self):
        """Check whether the database connection works."""
        try:
            result = self.execute_query("SELECT 1 AS health")
            return len(result) > 0
        except Exception:
            return False
