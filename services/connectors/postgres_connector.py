import psycopg2
from psycopg2.extras import RealDictCursor

from services.connectors.errors import (
    ConnectionError as ConnectorConnectionError,
    ConnectorError,
    QueryError,
    WriteError,
)

_CONNECTOR_TYPE = "postgresql"


class ConnectionConfig:
    """Stores the connection settings for PostgreSQL."""

    def __init__(self, host, port, database, username, password):
        self.host = host
        self.port = port
        self.database = database
        self.username = username
        self.password = password


class PostgresConnector:
    def __init__(self, config):
        self.config = config
        self.connection = None

    def connect(self):
        """Connect to the PostgreSQL database."""
        try:
            self.connection = psycopg2.connect(
                host=self.config.host,
                port=self.config.port,
                database=self.config.database,
                user=self.config.username,
                password=self.config.password,
            )
        except psycopg2.DatabaseError as e:
            raise ConnectorConnectionError(
                f"Connection failed: {e}",
                error_code="POSTGRES_CONNECTION_FAILED",
                connector_type=_CONNECTOR_TYPE,
                retryable=False,
            )

    def disconnect(self):
        """Close the current database connection."""
        if self.connection:
            self.connection.close()

    def execute_query(self, sql, params=None):
        """Run a SELECT query and return rows as dictionaries."""
        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(sql, params)
                return cursor.fetchall()
        except psycopg2.DatabaseError as e:
            raise QueryError(
                f"Query failed: {e}",
                error_code="POSTGRES_QUERY_FAILED",
                connector_type=_CONNECTOR_TYPE,
                retryable=False,
            )

    def execute_write(self, sql, params=None):
        """Run INSERT, UPDATE or DELETE and return affected row count."""
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(sql, params)
                affected_rows = cursor.rowcount
                self.connection.commit()
                return affected_rows
        except psycopg2.DatabaseError as e:
            self.connection.rollback()
            raise WriteError(
                f"Write failed: {e}",
                error_code="POSTGRES_WRITE_FAILED",
                connector_type=_CONNECTOR_TYPE,
                retryable=False,
            )

    def health_check(self):
        """Check whether the database connection works."""
        try:
            result = self.execute_query("SELECT 1 AS health")
            return len(result) > 0
        except Exception:
            return False
