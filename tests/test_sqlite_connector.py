import pytest

from services.connectors.sqlite_connector import (
    ConnectionConfig,
    SQLiteConnector,
)
from services.connectors.errors import QueryError, WriteError


def test_connect_and_disconnect(tmp_path):
    db_path = tmp_path / "test.db"

    config = ConnectionConfig(str(db_path))
    connector = SQLiteConnector(config)

    connector.connect()

    assert connector.connection is not None

    connector.disconnect()

    assert connector.connection is None


def test_execute_write_and_query(tmp_path):
    db_path = tmp_path / "test.db"

    config = ConnectionConfig(str(db_path))
    connector = SQLiteConnector(config)
    connector.connect()

    connector.execute_write("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)")

    affected_rows = connector.execute_write(
        "INSERT INTO users (name) VALUES (?)",
        ("Omer",),
    )

    rows = connector.execute_query("SELECT id, name FROM users")

    assert affected_rows == 1
    assert rows == [{"id": 1, "name": "Omer"}]

    connector.disconnect()


def test_execute_query_without_connection_raises_query_error(tmp_path):
    db_path = tmp_path / "test.db"

    config = ConnectionConfig(str(db_path))
    connector = SQLiteConnector(config)

    with pytest.raises(QueryError) as exc_info:
        connector.execute_query("SELECT 1")

    assert exc_info.value.error_code == "SQLITE_NOT_CONNECTED"
    assert exc_info.value.connector_type == "sqlite"
    assert exc_info.value.retryable is False


def test_execute_write_without_connection_raises_write_error(tmp_path):
    db_path = tmp_path / "test.db"

    config = ConnectionConfig(str(db_path))
    connector = SQLiteConnector(config)

    with pytest.raises(WriteError) as exc_info:
        connector.execute_write("CREATE TABLE test (id INTEGER)")

    assert exc_info.value.error_code == "SQLITE_NOT_CONNECTED"
    assert exc_info.value.connector_type == "sqlite"
    assert exc_info.value.retryable is False


def test_invalid_query_raises_query_error(tmp_path):
    db_path = tmp_path / "test.db"

    config = ConnectionConfig(str(db_path))
    connector = SQLiteConnector(config)
    connector.connect()

    with pytest.raises(QueryError) as exc_info:
        connector.execute_query("SELECT * FROM missing_table")

    assert exc_info.value.error_code == "SQLITE_QUERY_FAILED"
    assert exc_info.value.connector_type == "sqlite"

    connector.disconnect()


def test_health_check(tmp_path):
    db_path = tmp_path / "test.db"

    config = ConnectionConfig(str(db_path))
    connector = SQLiteConnector(config)

    assert connector.health_check() is False

    connector.connect()

    assert connector.health_check() is True

    connector.disconnect()
