import pyodbc


# Custom exception used for all connector-related errors.
class ConnectorError(Exception):
    """Custom error for connector failures."""

    def __init__(self, message, retryable=False):
        super().__init__(message)
        self.retryable = retryable


# Stores all database connection parameters.
class ConnectionConfig:
    """Stores the connection settings for MSSQL."""

    def __init__(self, host, port, database, username, password):
        self.host = host
        self.port = port
        self.database = database
        self.username = username
        self.password = password


class MSSQLConnector:
    # Initialize the connector with a configuration object.
    def __init__(self, config):
        self.config = config
        self.connection = None

    # Establish a connection to the Microsoft SQL Server.
    def connect(self):
        # Connect to the MSSQL database.
        try:
            available_drivers = pyodbc.drivers()

            if "ODBC Driver 18 for SQL Server" in available_drivers:
                driver = "ODBC Driver 18 for SQL Server"
            elif "ODBC Driver 17 for SQL Server" in available_drivers:
                driver = "ODBC Driver 17 for SQL Server"
            else:
                raise ConnectorError(
                    "No supported SQL Server ODBC driver found.",
                    retryable=False,
                )

            connection_string = (
                f"DRIVER={{{driver}}};"
                f"SERVER={self.config.host},{self.config.port};"
                f"DATABASE={self.config.database};"
                f"UID={self.config.username};"
                f"PWD={self.config.password};"
                "TrustServerCertificate=yes;"
            )

            self.connection = pyodbc.connect(connection_string)

        except pyodbc.Error as e:
            raise ConnectorError(f"Connection failed: {e}", retryable=False)

    # Close the active database connection.
    def disconnect(self):
        """Close the current database connection."""
        if self.connection:
            self.connection.close()
            self.connection = None

    # Execute a SELECT query and return the results as dictionaries.
    def execute_query(self, sql, params=None):
        """Run a SELECT query and return rows as dictionaries."""
        if self.connection is None:
            raise ConnectorError(
                "Not connected. Call connect() first.", retryable=False
            )

        cursor = None
        try:
            cursor = self.connection.cursor()
            cursor.execute(sql, params or ())

            # Retrieve column names from the query result.
            columns = [column[0] for column in cursor.description]

            # Fetch all rows returned by the query.
            rows = cursor.fetchall()

            # Convert each row into a dictionary.
            return [dict(zip(columns, row)) for row in rows]
        except pyodbc.Error as e:
            raise ConnectorError(f"Query failed: {e}", retryable=False)

        finally:
            if cursor is not None:
                cursor.close()

    # Execute INSERT, UPDATE or DELETE statements.
    def execute_write(self, sql, params=None):
        """Run INSERT, UPDATE or DELETE and return affected row count."""

        if self.connection is None:
            raise ConnectorError(
                "Not connected. Call connect() first.", retryable=False
            )

        cursor = None
        try:
            cursor = self.connection.cursor()
            cursor.execute(sql, params or ())

            # Store the number of affected rows.
            affected_rows = cursor.rowcount

            # Save changes to the database.
            self.connection.commit()

            return affected_rows
        except pyodbc.Error as e:
            # Undo changes if an error occurs.
            self.connection.rollback()
            raise ConnectorError(f"Write failed: {e}", retryable=False)

        finally:
            if cursor is not None:
                cursor.close()

    # Verify that the database connection is still working.
    def health_check(self):
        """Check whether the database connection works."""
        try:
            result = self.execute_query("SELECT 1 AS health")
            return len(result) > 0
        except Exception:
            return False
