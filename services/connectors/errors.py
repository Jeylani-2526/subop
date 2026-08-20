"""
Shared connector error hierarchy.

Per etl_engine_contracts_v1.md Section 4, every connector error carries
{error_code, message, connector_type, retryable} and arrives as a
ConnectorError subclass (ConnectionError, QueryError, WriteError).
ETL Engine's failure classification (contracts Section 5.1) is built
directly on the `retryable` flag here, and the API's shared error
envelope (etl_engine_api_spec_v1.md Section 5) mirrors this shape
field-for-field.

This module is the single source of truth for the error shape so
services/connectors/*.py and services/abstraction/type_mapping.py
raise exactly the same thing rather than three divergent local classes.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


class ConnectorError(Exception):
    """
    Base error for all connector/abstraction-layer failures.

    Args:
        message:
            Human-readable failure description.
        error_code:
            Short machine-readable code (e.g. "POSTGRES_CONNECTION_FAILED").
            Defaults to a generic code so existing call sites that only
            pass (message, retryable=...) keep working unchanged.
        connector_type:
            One of "postgresql" | "mysql" | "mssql" | "mongodb", or None
            when the error originates above any specific connector
            (contracts/API spec: null connector_type for API/ETL-Engine
            layer errors that never reached a connector).
        retryable:
            Whether the caller may safely retry the operation.
    """

    def __init__(
        self,
        message: str,
        *,
        error_code: str = "CONNECTOR_ERROR",
        connector_type: Optional[str] = None,
        retryable: bool = False,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.connector_type = connector_type
        self.retryable = retryable

    def to_envelope(self) -> Dict[str, Any]:
        """Return the shared error envelope shape (API spec Section 5)."""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "connector_type": self.connector_type,
            "retryable": self.retryable,
        }


class ConnectionError(ConnectorError):
    """Raised when establishing a database connection fails."""


class QueryError(ConnectorError):
    """Raised when a SELECT query fails."""


class WriteError(ConnectorError):
    """Raised when an INSERT/UPDATE/DELETE fails."""
