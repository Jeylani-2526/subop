import mysql.connector
from mysql.connector import Error


class ConnectorError(Exception):
    """Custom error for connector failures."""

    pass


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
            self.connection = mysql.connector.connect(
                host=self.config.host,
                port=self.config.port,
                database=self.config.database,
                user=self.config.username,
                password=self.config.password,
            )
        except Error as e:
            raise ConnectorError(f"Connection failed: {e}")

    def disconnect(self):
        """Close the current database connection."""
        if self.connection:
            self.connection.close()
            self.connection = None

    def execute_query(self, sql, params=None):
        """Run a SELECT query and return rows as dictionaries."""
        try:
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute(sql, params)
            result = cursor.fetchall()
            cursor.close()
            return result
        except Error as e:
            raise ConnectorError(f"Query failed: {e}")

    def execute_write(self, sql, params=None):
        """Run INSERT, UPDATE or DELETE and return affected row count."""
        try:
            cursor = self.connection.cursor()
            cursor.execute(sql, params)
            affected_rows = cursor.rowcount
            self.connection.commit()
            cursor.close()
            return affected_rows
        except Error as e:
            self.connection.rollback()
            raise ConnectorError(f"Write failed: {e}")

    def health_check(self):
        """Check whether the database connection works."""
        try:
            result = self.execute_query("SELECT 1 AS health")
            return len(result) > 0
        except Exception:
            return False
