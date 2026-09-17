import json

from services.connectors.errors import QueryError
from services.connectors.file_connector_base import FileConnectorBase

_CONNECTOR_TYPE = "json"


class JSONConnector(FileConnectorBase):
    """Connector for reading a JSON array-of-objects file."""

    def __init__(self, config):
        super().__init__(config)

    def execute_query(self, sql=None, params=None):
        """
        Read the JSON file and return rows as dictionaries.

        Expects the file's top-level JSON value to be an array of flat
        objects — the shape named in M6W19T2 — and returns it as-is
        (List[Dict]), the same row shape every other connector's
        execute_query() returns to the Abstraction Layer (contracts
        Section 4). No wrapper-key ("records", "data", ...) unwrapping:
        mirrors CSVConnector, which likewise assumes one fixed shape
        rather than sniffing for variants.

        The sql and params arguments are accepted to stay compatible
        with the connector interface used by database connectors.
        """
        if not self.connected:
            raise QueryError(
                "Not connected. Call connect() first.",
                error_code="JSON_NOT_CONNECTED",
                connector_type=_CONNECTOR_TYPE,
                retryable=False,
            )

        try:
            with self.config.file_path.open(mode="r", encoding="utf-8") as json_file:
                data = json.load(json_file)

        except OSError as e:
            raise QueryError(
                f"JSON read failed: {e}",
                error_code="JSON_READ_FAILED",
                connector_type=_CONNECTOR_TYPE,
                retryable=False,
            )

        except json.JSONDecodeError as e:
            raise QueryError(
                f"Malformed JSON in {self.config.file_path}: {e}",
                error_code="JSON_MALFORMED",
                connector_type=_CONNECTOR_TYPE,
                retryable=False,
            )

        if not isinstance(data, list) or not all(isinstance(row, dict) for row in data):
            raise QueryError(
                f"{self.config.file_path} must contain a JSON array of "
                "objects at the top level.",
                error_code="JSON_INVALID_SHAPE",
                connector_type=_CONNECTOR_TYPE,
                retryable=False,
            )

        return data
