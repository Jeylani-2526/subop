from __future__ import annotations

from typing import Any, Dict, List, Optional

from services.abstraction.type_mapping import (
    UniversalTypeMapper,
    normalize_value,
)


class AbstractionLayer:
    """
    Provides a unified interface over ConnectorBase-compatible
    database connectors.

    The abstraction layer delegates database operations to the
    configured connector while preserving the existing public
    query result structure:

        List[Dict[str, Any]]

    Query values can optionally be normalized through the
    Universal Type Mapping module when native schema metadata
    is available.
    """

    def __init__(
        self,
        connector: Any,
        database: str,
    ):
        """
        Initialize the abstraction layer.

        Args:
            connector:
                A ConnectorBase-compatible connector instance.

            database:
                Database identifier such as "postgresql",
                "mysql", or "mssql".
        """

        self.connector = connector
        self.database = database

    def execute_query(
        self,
        sql: str,
        params: Optional[Any] = None,
        *,
        column_types: Optional[Dict[str, str]] = None,
        schema_intents: Optional[Dict[str, str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Execute a SELECT query through the configured connector.

        When native column type metadata is supplied, each value
        is normalized through the Universal Type Mapping module.

        Args:
            sql:
                SQL SELECT statement.

            params:
                Optional query parameters passed unchanged to
                the underlying connector.

            column_types:
                Optional mapping of column name to native SQL type.

                Example:
                    {
                        "id": "BIGINT",
                        "name": "VARCHAR(255)",
                        "payload": "JSON"
                    }

            schema_intents:
                Optional explicit semantic intent for ambiguous
                columns, such as BOOLEAN or JSON.

        Returns:
            Query rows using the existing List[Dict[str, Any]]
            public result structure.
        """

        # Delegate the actual database query to the connector.
        rows = self.connector.execute_query(sql, params)

        # If no native schema information is available, preserve
        # the connector result unchanged.
        if not column_types:
            return rows

        # Normalize each returned row without changing column names,
        # row ordering, or the dictionary-based result structure.
        return self._normalize_rows(
            rows,
            column_types,
            schema_intents=schema_intents,
        )

    def execute_write(
        self,
        sql: str,
        params: Optional[Any] = None,
    ) -> Any:
        """
        Execute INSERT, UPDATE, or DELETE through the connector.

        The affected-row result is returned unchanged.
        ConnectorError exceptions are intentionally not wrapped
        so the connector's retryable flag remains preserved.
        """

        return self.connector.execute_write(sql, params)

    def health_check(self) -> bool:
        """
        Delegate the health check to the configured connector.
        """

        return self.connector.health_check()

    def _normalize_rows(
        self,
        rows: List[Dict[str, Any]],
        column_types: Dict[str, str],
        *,
        schema_intents: Optional[Dict[str, str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Normalize database result values using native column types.

        Metadata is used internally and is never inserted as
        additional columns into the user-visible query result.
        """

        normalized_rows: List[Dict[str, Any]] = []

        for row in rows:
            normalized_row: Dict[str, Any] = {}

            for column_name, value in row.items():
                # If no schema type is known for this column,
                # preserve its original value.
                source_type = column_types.get(column_name)

                if source_type is None:
                    normalized_row[column_name] = value
                    continue

                # Resolve optional explicit semantic intent for
                # ambiguous database-native types.
                schema_intent = None

                if schema_intents:
                    schema_intent = schema_intents.get(column_name)

                # Map the database-native SQL type to the canonical
                # type system.
                mapping = UniversalTypeMapper.map_type(
                    self.database,
                    source_type,
                    schema_intent=schema_intent,
                )

                # Normalize the runtime value according to the
                # resolved canonical type.
                normalized_row[column_name] = normalize_value(
                    value,
                    canonical_type=mapping.canonical_type,
                    source_type=source_type,
                )

            normalized_rows.append(normalized_row)

        return normalized_rows
