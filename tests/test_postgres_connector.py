import pytest

from services.connectors.postgres_connector import (
    ConnectionConfig,
    ConnectorError,
    PostgresConnector,
)


def test_connect_success(test_db_connection):
    """Verify that a valid connection config connects without error."""
    assert test_db_connection.connection is not None


def test_connect_failure():
    """Verify that wrong credentials raise ConnectorError."""
    bad_config = ConnectionConfig(
        host="127.0.0.1",
        port=5432,
        database="subop",
        username="wrong_user",
        password="wrong_password",
    )
    connector = PostgresConnector(bad_config)
    with pytest.raises(ConnectorError):
        connector.connect()


def test_health_check_returns_true(test_db_connection):
    """Verify that the health check returns True for a live connection."""
    assert test_db_connection.health_check() is True


def test_execute_query_returns_list(test_db_connection):
    """Verify that a SELECT query returns a list of dictionaries."""
    result = test_db_connection.execute_query("SELECT 1 AS test")
    assert isinstance(result, list)
    assert result[0]["test"] == 1


def test_execute_write_insert(test_db_connection):
    """Test INSERT, UPDATE, and DELETE operations in sequence."""
    test_db_connection.execute_write(
        """
        CREATE TABLE IF NOT EXISTS test_users (
            id SERIAL PRIMARY KEY,
            name TEXT
        )
        """
    )

    inserted_rows = test_db_connection.execute_write(
        "INSERT INTO test_users (name) VALUES (%s)",
        ("Omer",),
    )
    assert inserted_rows == 1

    updated_rows = test_db_connection.execute_write(
        "UPDATE test_users SET name = %s WHERE name = %s",
        ("Omer Updated", "Omer"),
    )
    assert updated_rows >= 1

    deleted_rows = test_db_connection.execute_write(
        "DELETE FROM test_users WHERE name = %s",
        ("Omer Updated",),
    )
    assert deleted_rows >= 1
