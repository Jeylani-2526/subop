import pytest

from services.connectors.csv_connector import CSVConnector
from services.connectors.errors import QueryError
from services.connectors.file_connector_base import FileConnectionConfig


def test_connect_and_disconnect(tmp_path):
    csv_path = tmp_path / "test.csv"
    csv_path.write_text("id,name\n1,Ali\n", encoding="utf-8")

    config = FileConnectionConfig(csv_path)
    connector = CSVConnector(config)

    connector.connect()

    assert connector.connected is True

    connector.disconnect()

    assert connector.connected is False


def test_execute_query_returns_rows_as_dicts(tmp_path):
    csv_path = tmp_path / "users.csv"
    csv_path.write_text(
        "id,name,age\n" "1,Ali,21\n" "2,Ayse,24\n",
        encoding="utf-8",
    )

    config = FileConnectionConfig(csv_path)
    connector = CSVConnector(config)
    connector.connect()

    rows = connector.execute_query()

    assert rows == [
        {"id": "1", "name": "Ali", "age": "21"},
        {"id": "2", "name": "Ayse", "age": "24"},
    ]

    connector.disconnect()


def test_execute_query_without_connection_raises_query_error(tmp_path):
    csv_path = tmp_path / "test.csv"
    csv_path.write_text("id,name\n1,Ali\n", encoding="utf-8")

    config = FileConnectionConfig(csv_path)
    connector = CSVConnector(config)

    with pytest.raises(QueryError) as exc_info:
        connector.execute_query()

    assert exc_info.value.error_code == "CSV_NOT_CONNECTED"
    assert exc_info.value.connector_type == "csv"
    assert exc_info.value.retryable is False


def test_connect_with_missing_file_raises_connection_error(tmp_path):
    from services.connectors.errors import (
        ConnectionError as ConnectorConnectionError,
    )

    csv_path = tmp_path / "missing.csv"

    config = FileConnectionConfig(csv_path)
    connector = CSVConnector(config)

    with pytest.raises(ConnectorConnectionError) as exc_info:
        connector.connect()

    assert exc_info.value.error_code == "FILE_NOT_FOUND"
    assert exc_info.value.connector_type == "file"
    assert exc_info.value.retryable is False


def test_empty_csv_returns_empty_list(tmp_path):
    csv_path = tmp_path / "empty.csv"
    csv_path.write_text("", encoding="utf-8")

    config = FileConnectionConfig(csv_path)
    connector = CSVConnector(config)
    connector.connect()

    rows = connector.execute_query()

    assert rows == []

    connector.disconnect()


def test_header_only_csv_returns_empty_list(tmp_path):
    csv_path = tmp_path / "header_only.csv"
    csv_path.write_text("id,name,age\n", encoding="utf-8")

    config = FileConnectionConfig(csv_path)
    connector = CSVConnector(config)
    connector.connect()

    rows = connector.execute_query()

    assert rows == []

    connector.disconnect()


def test_health_check(tmp_path):
    csv_path = tmp_path / "test.csv"
    csv_path.write_text("id,name\n1,Ali\n", encoding="utf-8")

    config = FileConnectionConfig(csv_path)
    connector = CSVConnector(config)

    assert connector.health_check() is False

    connector.connect()

    assert connector.health_check() is True

    connector.disconnect()

    assert connector.health_check() is False
