import csv

from services.connectors.errors import QueryError
from services.connectors.file_connector_base import FileConnectorBase

_CONNECTOR_TYPE = "csv"

_CONNECTOR_TYPE = "csv"


class CSVConnector(FileConnectorBase):
    """Connector for reading CSV files."""

    def __init__(self, config):
        super().__init__(config)

    def execute_query(self, sql=None, params=None):
        """
        Read the CSV file and return rows as dictionaries.

        The sql and params arguments are accepted to stay compatible with
        the connector interface used by database connectors.
        """
        if not self.connected:
            raise QueryError(
                "Not connected. Call connect() first.",
                error_code="CSV_NOT_CONNECTED",
                connector_type=_CONNECTOR_TYPE,
                retryable=False,
            )

        try:
            with self.config.file_path.open(
                mode="r",
                encoding="utf-8",
                newline="",
            ) as csv_file:
                reader = csv.DictReader(csv_file)
                return [dict(row) for row in reader]

        except (OSError, csv.Error) as e:
            raise QueryError(
                f"CSV read failed: {e}",
                error_code="CSV_READ_FAILED",
                connector_type=_CONNECTOR_TYPE,
                retryable=False,
            )
