import httpx

from services.connectors.errors import (
    ConnectionError as ConnectorConnectionError,
    QueryError,
)

_CONNECTOR_TYPE = "rest_api"


class ConnectionConfig:
    """Stores the connection settings for a REST API."""

    def __init__(self, base_url):
        self.base_url = base_url


class RESTAPIConnector:
    """Connector for reading JSON data from a REST API."""

    def __init__(self, config):
        self.config = config
        self.client = None

    def connect(self):
        """Create an HTTP client for the configured REST API."""
        try:
            self.client = httpx.Client(base_url=self.config.base_url)
        except (httpx.HTTPError, ValueError) as e:
            raise ConnectorConnectionError(
                f"Connection setup failed: {e}",
                error_code="REST_API_CONNECTION_FAILED",
                connector_type=_CONNECTOR_TYPE,
                retryable=False,
            )

    def disconnect(self):
        """Close the current HTTP client."""
        if self.client is not None:
            self.client.close()
            self.client = None

    def execute_query(self, sql=None, params=None):
        """
        Send a GET request and return the JSON response as rows.

        Expects the response body to be a JSON array of objects and
        returns it as List[Dict], matching the row shape expected by
        the Abstraction Layer.

        The sql and params arguments are accepted to stay compatible
        with the connector interface used by database connectors.
        """
        if self.client is None:
            raise QueryError(
                "Not connected. Call connect() first.",
                error_code="REST_API_NOT_CONNECTED",
                connector_type=_CONNECTOR_TYPE,
                retryable=False,
            )

        try:
            response = self.client.get("")
            response.raise_for_status()

        except httpx.HTTPStatusError as e:
            raise QueryError(
                f"REST API returned HTTP {e.response.status_code}.",
                error_code="REST_API_HTTP_ERROR",
                connector_type=_CONNECTOR_TYPE,
                retryable=False,
            )

        except httpx.HTTPError as e:
            raise QueryError(
                f"REST API request failed: {e}",
                error_code="REST_API_REQUEST_FAILED",
                connector_type=_CONNECTOR_TYPE,
                retryable=True,
            )

        try:
            data = response.json()
        except ValueError as e:
            raise QueryError(
                f"Malformed JSON response: {e}",
                error_code="REST_API_MALFORMED_JSON",
                connector_type=_CONNECTOR_TYPE,
                retryable=False,
            )

        if not isinstance(data, list) or not all(isinstance(row, dict) for row in data):
            raise QueryError(
                "REST API response must contain a JSON array of objects.",
                error_code="REST_API_INVALID_SHAPE",
                connector_type=_CONNECTOR_TYPE,
                retryable=False,
            )

        return data

    def health_check(self):
        """Check whether the REST API is reachable."""
        if self.client is None:
            return False

        try:
            response = self.client.get("")
            return response.is_success
        except httpx.HTTPError:
            return False
