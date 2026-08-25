import os

import pytest

from services.connectors.errors import ConnectorError
from services.connectors.mssql_connector import (
    MSSQLConnector,
    ConnectionConfig,
)


# Create the MSSQL connection configuration used by all tests.
@pytest.fixture
def mssql_config():
    return ConnectionConfig(
        host=os.getenv("MSSQL_HOST", "localhost"),
        port=int(os.getenv("MSSQL_PORT", "1433")),
        database=os.getenv("MSSQL_DATABASE", "master"),
        username=os.getenv("MSSQL_USERNAME", "sa"),
        password=os.getenv("MSSQL_PASSWORD", "SubopDev123!"),
    )


# Create a connected MSSQL connector for each test
@pytest.fixture
def mssql_connector(mssql_config):
    connector = MSSQLConnector(mssql_config)

    # Open the database connection before the test runs.
    connector.connect()

    # Provide the connected connector to the test.
    yield connector

    # Always close the database connection after the test finishes.
    connector.disconnect()


# Verify that the connector can connect and disconnect successfully.
def test_connect_disconnect(mssql_config):
    connector = MSSQLConnector(mssql_config)

    # Establish the database connection.
    connector.connect()

    # Confirm that a connection object was created.
    assert connector.connection is not None

    # Close the active database connection.
    connector.disconnect()

    # Confirm that the connection reference was cleared.
    assert connector.connection is None


# Verify that the health check reports a working database connection.
def test_health_check(mssql_connector):
    # The health check should return True for an active connection.
    assert mssql_connector.health_check() is True


# Verify that SELECT queries return rows as dictionaries.
def test_execute_query(mssql_connector):
    # Execute a simple MSSQL SELECT query with named result columns.
    result = mssql_connector.execute_query("SELECT 1 AS id, 'SubOP' AS name")

    # Confirm that exactly one row was returned.
    assert len(result) == 1

    # Confirm that the row is represented as a dictionary.
    assert isinstance(result[0], dict)

    # Confirm that the returned values match the query result.
    assert result[0]["id"] == 1
    assert result[0]["name"] == "SubOP"


# Verify that INSERT, UPDATE and DELETE operations can be executed.
def test_execute_write(mssql_connector):
    # Remove the temporary test table if it already exists.
    mssql_connector.execute_write("""
        IF OBJECT_ID('dbo.subop_test', 'U') IS NOT NULL
            DROP TABLE dbo.subop_test
        """)

    # Create a temporary table for the write test.
    mssql_connector.execute_write("""
        CREATE TABLE dbo.subop_test (
            id INT PRIMARY KEY,
            name VARCHAR(100)
        )
        """)

    try:
        # Insert one test record into the table.
        affected_rows = mssql_connector.execute_write(
            "INSERT INTO dbo.subop_test (id, name) VALUES (?, ?)",
            (1, "SubOP"),
        )

        # Confirm that exactly one row was inserted.
        assert affected_rows == 1

        # Read the inserted record back from the database.
        result = mssql_connector.execute_query(
            "SELECT id, name FROM dbo.subop_test WHERE id = ?",
            (1,),
        )

        # Confirm that the inserted record exists.
        assert len(result) == 1

        # Confirm that the stored values are correct.
        assert result[0]["id"] == 1
        assert result[0]["name"] == "SubOP"

    finally:
        # Always remove the test table, even if an assertion fails.
        mssql_connector.execute_write("""
            IF OBJECT_ID('dbo.subop_test', 'U') IS NOT NULL
                DROP TABLE dbo.subop_test
            """)


# Verify that malformed SQL raises a non-retryable ConnectorError.
def test_malformed_query_raises_connector_error(mssql_connector):
    # Execute intentionally invalid SQL syntax.
    with pytest.raises(ConnectorError) as exc_info:
        mssql_connector.execute_query("SELECT FROM WHERE")

    # Confirm that the connector marks the error as non-retryable.
    assert exc_info.value.retryable is False
