import pymysql
from pymysql import Error

from services.connectors.errors import (
    ConnectionError as ConnectorConnectionError,
    QueryError,
    WriteError,
)

_CONNECTOR_TYPE = "mysql"


class ConnectionConfig:
    """Stores the connection settings for MySQL."""

    def __init__(self, host, port, database, username, password):
        self.host = host
        self.port = port
        self.database = database
        self.username = username
        self.password = password


class MySQLConnector:
    def __init__(self, config):
        self.config = config
        self.connection = None

    def connect(self):
        """Connect to the MySQL database."""
        try:
            self.connection = pymysql.connect(
                host=self.config.host,
                port=self.config.port,
                database=self.config.database,
                user=self.config.username,
                password=self.config.password,
            )
        except Error as e:
            raise ConnectorConnectionError(
                f"Connection failed: {e}",
                error_code="MYSQL_CONNECTION_FAILED",
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
                error_code="MYSQL_NOT_CONNECTED",
                connector_type=_CONNECTOR_TYPE,
                retryable=False,
            )
        cursor = None
        try:
            cursor = self.connection.cursor(pymysql.cursors.DictCursor)
            cursor.execute(sql, params)
            return cursor.fetchall()
        except Error as e:
            raise QueryError(
                f"Query failed: {e}",
                error_code="MYSQL_QUERY_FAILED",
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
                error_code="MYSQL_NOT_CONNECTED",
                connector_type=_CONNECTOR_TYPE,
                retryable=False,
            )
        try:
            cursor = self.connection.cursor()
            cursor.execute(sql, params)
            affected_rows = cursor.rowcount
            self.connection.commit()
            return affected_rows
        except Error as e:
            self.connection.rollback()
            raise WriteError(
                f"Write failed: {e}",
                error_code="MYSQL_WRITE_FAILED",
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
