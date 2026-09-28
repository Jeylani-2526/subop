import os

import pytest

from services.connectors.errors import ConnectorError
from services.connectors.oracle_connector import (
    OracleConnector,
    ConnectionConfig,
)


# Create the Oracle connection configuration used by all tests.
@pytest.fixture
def oracle_config():
    return ConnectionConfig(
        host=os.getenv("ORACLE_HOST", "localhost"),
        port=int(os.getenv("ORACLE_PORT", "1521")),
        database=os.getenv("ORACLE_DATABASE", "FREEPDB1"),
        username=os.getenv("ORACLE_USERNAME", "subop_app"),
        password=os.getenv("ORACLE_PASSWORD", "oracle_dev"),
    )


# Create a connected Oracle connector for each test.
@pytest.fixture
def oracle_connector(oracle_config):
    connector = OracleConnector(oracle_config)

    # Open the database connection before the test runs.
    connector.connect()

    # Provide the connected connector to the test.
    yield connector

    # Always close the database connection after the test finishes.
    connector.disconnect()


# Verify that the connector can connect and disconnect successfully.
def test_connect_disconnect(oracle_config):
    connector = OracleConnector(oracle_config)

    # Establish the database connection.
    connector.connect()

    # Confirm that a connection object was created.
    assert connector.connection is not None

    # Close the active database connection.
    connector.disconnect()

    # Confirm that the connection reference was cleared.
    assert connector.connection is None


# Verify that the health check reports a working database connection.
def test_health_check(oracle_connector):
    assert oracle_connector.health_check() is True


# Verify that SELECT queries return rows as dictionaries.
def test_execute_query(oracle_connector):
    result = oracle_connector.execute_query("SELECT 1 AS id, 'SubOP' AS name FROM DUAL")

    # Confirm that exactly one row was returned.
    assert len(result) == 1

    # Confirm that the row is represented as a dictionary.
    assert isinstance(result[0], dict)

    # Oracle normally returns unquoted column names in uppercase.
    assert result[0]["ID"] == 1
    assert result[0]["NAME"] == "SubOP"


# Verify that INSERT, UPDATE and DELETE operations can be executed.
def test_execute_write(oracle_connector):
    # Oracle does not support CREATE TABLE IF NOT EXISTS.
    # Try to remove the test table before creating it.
    try:
        oracle_connector.execute_write("DROP TABLE subop_test")
    except ConnectorError:
        pass

    oracle_connector.execute_write("""
        CREATE TABLE subop_test (
            id NUMBER PRIMARY KEY,
            name VARCHAR2(100)
        )
    """)

    try:
        # Insert one test record.
        affected_rows = oracle_connector.execute_write(
            "INSERT INTO subop_test (id, name) VALUES (:1, :2)",
            (1, "SubOP"),
        )

        assert affected_rows == 1

        # Read the inserted record back.
        result = oracle_connector.execute_query(
            "SELECT id, name FROM subop_test WHERE id = :1",
            (1,),
        )

        assert len(result) == 1
        assert result[0]["ID"] == 1
        assert result[0]["NAME"] == "SubOP"

        # Update the record.
        updated_rows = oracle_connector.execute_write(
            "UPDATE subop_test SET name = :1 WHERE id = :2",
            ("SubOP Updated", 1),
        )

        assert updated_rows == 1

        # Delete the record.
        deleted_rows = oracle_connector.execute_write(
            "DELETE FROM subop_test WHERE id = :1",
            (1,),
        )

        assert deleted_rows == 1

    finally:
        # Always remove the test table, even if an assertion fails.
        oracle_connector.execute_write("DROP TABLE subop_test")


# Verify that malformed SQL raises a non-retryable ConnectorError.
def test_malformed_query_raises_connector_error(oracle_connector):
    with pytest.raises(ConnectorError) as exc_info:
        oracle_connector.execute_query("SELECT FROM WHERE")

    assert exc_info.value.retryable is False
