from pathlib import Path

from services.connectors.errors import (
    ConnectionError as ConnectorConnectionError,
)

_CONNECTOR_TYPE = "file"


class FileConnectionConfig:
    """Stores the connection settings for file-based connectors."""

    def __init__(self, file_path):
        self.file_path = Path(file_path)


class FileConnectorBase:
    """Base class for file-based connectors."""

    def __init__(self, config):
        self.config = config
        self.connected = False

    def connect(self):
        """Validate that the configured file exists."""
        if not self.config.file_path.exists():
            raise ConnectorConnectionError(
                f"File not found: {self.config.file_path}",
                error_code="FILE_NOT_FOUND",
                connector_type=_CONNECTOR_TYPE,
                retryable=False,
            )

        if not self.config.file_path.is_file():
            raise ConnectorConnectionError(
                f"Path is not a file: {self.config.file_path}",
                error_code="INVALID_FILE_PATH",
                connector_type=_CONNECTOR_TYPE,
                retryable=False,
            )

        self.connected = True

    def disconnect(self):
        """Mark the file connector as disconnected."""
        self.connected = False

    def health_check(self):
        """Check whether the configured file is accessible."""
        return (
            self.connected
            and self.config.file_path.exists()
            and self.config.file_path.is_file()
        )
