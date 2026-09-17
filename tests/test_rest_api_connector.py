import httpx
import pytest

from services.connectors.errors import QueryError
from services.connectors.rest_api_connector import (
    ConnectionConfig,
    RESTAPIConnector,
)


def _create_connector(handler):
    """Create a connected REST API connector with a mock HTTP transport."""
    config = ConnectionConfig("https://example.com")
    connector = RESTAPIConnector(config)

    connector.client = httpx.Client(
        base_url=config.base_url,
        transport=httpx.MockTransport(handler),
    )

    return connector


def test_connect_and_disconnect():
    config = ConnectionConfig("https://example.com")
    connector = RESTAPIConnector(config)

    connector.connect()

    assert connector.client is not None

    connector.disconnect()

    assert connector.client is None


def test_execute_query_returns_rows_as_dicts():
    def handler(request):
        return httpx.Response(
            200,
            json=[
                {"id": 1, "name": "Ali", "age": 21},
                {"id": 2, "name": "Ayse", "age": 24},
            ],
        )

    connector = _create_connector(handler)

    rows = connector.execute_query()

    assert rows == [
        {"id": 1, "name": "Ali", "age": 21},
        {"id": 2, "name": "Ayse", "age": 24},
    ]

    connector.disconnect()


def test_execute_query_without_connection_raises_query_error():
    config = ConnectionConfig("https://example.com")
    connector = RESTAPIConnector(config)

    with pytest.raises(QueryError) as exc_info:
        connector.execute_query()

    assert exc_info.value.error_code == "REST_API_NOT_CONNECTED"
    assert exc_info.value.connector_type == "rest_api"
    assert exc_info.value.retryable is False


def test_non_2xx_response_raises_query_error():
    def handler(request):
        return httpx.Response(
            500,
            json={"error": "Internal Server Error"},
        )

    connector = _create_connector(handler)

    with pytest.raises(QueryError) as exc_info:
        connector.execute_query()

    assert exc_info.value.error_code == "REST_API_HTTP_ERROR"
    assert exc_info.value.connector_type == "rest_api"
    assert exc_info.value.retryable is False

    connector.disconnect()


def test_malformed_json_raises_query_error():
    def handler(request):
        return httpx.Response(
            200,
            content=b"{invalid json",
            headers={"Content-Type": "application/json"},
        )

    connector = _create_connector(handler)

    with pytest.raises(QueryError) as exc_info:
        connector.execute_query()

    assert exc_info.value.error_code == "REST_API_MALFORMED_JSON"
    assert exc_info.value.connector_type == "rest_api"
    assert exc_info.value.retryable is False

    connector.disconnect()


def test_non_array_top_level_raises_query_error():
    def handler(request):
        return httpx.Response(
            200,
            json={"records": [{"id": 1}]},
        )

    connector = _create_connector(handler)

    with pytest.raises(QueryError) as exc_info:
        connector.execute_query()

    assert exc_info.value.error_code == "REST_API_INVALID_SHAPE"
    assert exc_info.value.connector_type == "rest_api"
    assert exc_info.value.retryable is False

    connector.disconnect()


def test_array_of_non_objects_raises_query_error():
    def handler(request):
        return httpx.Response(
            200,
            json=[1, 2, 3],
        )

    connector = _create_connector(handler)

    with pytest.raises(QueryError) as exc_info:
        connector.execute_query()

    assert exc_info.value.error_code == "REST_API_INVALID_SHAPE"

    connector.disconnect()


def test_empty_array_returns_empty_list():
    def handler(request):
        return httpx.Response(
            200,
            json=[],
        )

    connector = _create_connector(handler)

    rows = connector.execute_query()

    assert rows == []

    connector.disconnect()


def test_request_failure_raises_query_error():
    def handler(request):
        raise httpx.ConnectError(
            "Connection failed",
            request=request,
        )

    connector = _create_connector(handler)

    with pytest.raises(QueryError) as exc_info:
        connector.execute_query()

    assert exc_info.value.error_code == "REST_API_REQUEST_FAILED"
    assert exc_info.value.connector_type == "rest_api"
    assert exc_info.value.retryable is True

    connector.disconnect()


def test_health_check():
    def handler(request):
        return httpx.Response(200, json=[])

    connector = _create_connector(handler)

    assert connector.health_check() is True

    connector.disconnect()

    assert connector.health_check() is False
