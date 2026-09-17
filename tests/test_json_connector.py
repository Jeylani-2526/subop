import pytest

from services.connectors.json_connector import JSONConnector
from services.connectors.errors import QueryError
from services.connectors.file_connector_base import FileConnectionConfig


def test_connect_and_disconnect(tmp_path):
    json_path = tmp_path / "test.json"
    json_path.write_text('[{"id": 1, "name": "Ali"}]', encoding="utf-8")

    config = FileConnectionConfig(json_path)
    connector = JSONConnector(config)

    connector.connect()

    assert connector.connected is True

    connector.disconnect()

    assert connector.connected is False


def test_execute_query_returns_rows_as_dicts(tmp_path):
    json_path = tmp_path / "users.json"
    json_path.write_text(
        '[{"id": 1, "name": "Ali", "age": 21}, '
        '{"id": 2, "name": "Ayse", "age": 24}]',
        encoding="utf-8",
    )

    config = FileConnectionConfig(json_path)
    connector = JSONConnector(config)
    connector.connect()

    rows = connector.execute_query()

    assert rows == [
        {"id": 1, "name": "Ali", "age": 21},
        {"id": 2, "name": "Ayse", "age": 24},
    ]

    connector.disconnect()


def test_execute_query_without_connection_raises_query_error(tmp_path):
    json_path = tmp_path / "test.json"
    json_path.write_text('[{"id": 1, "name": "Ali"}]', encoding="utf-8")

    config = FileConnectionConfig(json_path)
    connector = JSONConnector(config)

    with pytest.raises(QueryError) as exc_info:
        connector.execute_query()

    assert exc_info.value.error_code == "JSON_NOT_CONNECTED"
    assert exc_info.value.connector_type == "json"
    assert exc_info.value.retryable is False


def test_connect_with_missing_file_raises_connection_error(tmp_path):
    from services.connectors.errors import (
        ConnectionError as ConnectorConnectionError,
    )

    json_path = tmp_path / "missing.json"

    config = FileConnectionConfig(json_path)
    connector = JSONConnector(config)

    with pytest.raises(ConnectorConnectionError) as exc_info:
        connector.connect()

    assert exc_info.value.error_code == "FILE_NOT_FOUND"
    assert exc_info.value.connector_type == "file"
    assert exc_info.value.retryable is False


def test_empty_array_json_returns_empty_list(tmp_path):
    json_path = tmp_path / "empty.json"
    json_path.write_text("[]", encoding="utf-8")

    config = FileConnectionConfig(json_path)
    connector = JSONConnector(config)
    connector.connect()

    rows = connector.execute_query()

    assert rows == []

    connector.disconnect()


def test_malformed_json_raises_query_error(tmp_path):
    json_path = tmp_path / "broken.json"
    json_path.write_text('[{"id": 1, "name": "Ali"]', encoding="utf-8")

    config = FileConnectionConfig(json_path)
    connector = JSONConnector(config)
    connector.connect()

    with pytest.raises(QueryError) as exc_info:
        connector.execute_query()

    assert exc_info.value.error_code == "JSON_MALFORMED"
    assert exc_info.value.connector_type == "json"
    assert exc_info.value.retryable is False


def test_non_array_top_level_raises_query_error(tmp_path):
    """
    A top-level JSON object (e.g. a {"records": [...]} wrapper) is
    rejected rather than silently unwrapped — M6W19T2 scopes this
    connector to array-of-objects only, matching CSVConnector's single
    fixed shape rather than sniffing for variants.
    """
    json_path = tmp_path / "wrapped.json"
    json_path.write_text('{"records": [{"id": 1}]}', encoding="utf-8")

    config = FileConnectionConfig(json_path)
    connector = JSONConnector(config)
    connector.connect()

    with pytest.raises(QueryError) as exc_info:
        connector.execute_query()

    assert exc_info.value.error_code == "JSON_INVALID_SHAPE"
    assert exc_info.value.connector_type == "json"
    assert exc_info.value.retryable is False


def test_array_of_non_objects_raises_query_error(tmp_path):
    json_path = tmp_path / "flat_list.json"
    json_path.write_text("[1, 2, 3]", encoding="utf-8")

    config = FileConnectionConfig(json_path)
    connector = JSONConnector(config)
    connector.connect()

    with pytest.raises(QueryError) as exc_info:
        connector.execute_query()

    assert exc_info.value.error_code == "JSON_INVALID_SHAPE"

    connector.disconnect()


def test_health_check(tmp_path):
    json_path = tmp_path / "test.json"
    json_path.write_text('[{"id": 1, "name": "Ali"}]', encoding="utf-8")

    config = FileConnectionConfig(json_path)
    connector = JSONConnector(config)

    assert connector.health_check() is False

    connector.connect()

    assert connector.health_check() is True

    connector.disconnect()

    assert connector.health_check() is False
