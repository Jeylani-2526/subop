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
        capture_lineage: bool = False,
    ) -> Any:
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

            capture_lineage:
                When True, also return per-column type-mapping
                condition metadata for any column whose mapping
                condition was not "direct" (contracts Section 7.2:
                inexact/ambiguous/conditional/fallback are recorded
                as Lineage metadata, not surfaced as errors). Default
                False keeps the public result shape exactly as it was
                before this parameter existed.

        Returns:
            By default: query rows using the existing
            List[Dict[str, Any]] public result structure.

            When capture_lineage=True: a tuple
            (rows, lineage_records), where lineage_records is a
            List[Dict[str, Any]] — one entry per (row_index, column)
            pair whose mapping condition was non-"direct", each
            shaped as {row_index, column, condition, canonical_type,
            source_type}. This is additive metadata for the caller
            to hand to the Lineage module (contracts Section 6); it
            is never merged into the row dicts themselves.
        """

        # Delegate the actual database query to the connector.
        rows = self.connector.execute_query(sql, params)

        # If no native schema information is available, preserve
        # the connector result unchanged.
        if not column_types:
            return (rows, []) if capture_lineage else rows

        # Normalize each returned row without changing column names,
        # row ordering, or the dictionary-based result structure.
        normalized_rows, lineage_records = self._normalize_rows(
            rows,
            column_types,
            schema_intents=schema_intents,
        )

        if capture_lineage:
            return normalized_rows, lineage_records

        return normalized_rows

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
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Normalize database result values using native column types.

        Metadata is used internally and is never inserted as
        additional columns into the user-visible query result.

        Returns (normalized_rows, lineage_records). lineage_records
        is populated only for columns whose mapping condition was
        not "direct" (contracts Section 7.2) and is kept separate
        from the row data itself.
        """

        normalized_rows: List[Dict[str, Any]] = []
        lineage_records: List[Dict[str, Any]] = []

        for row_index, row in enumerate(rows):
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
                # type system. An "unsupported" type raises
                # UnsupportedTypeError (a ConnectorError) here and
                # propagates unchanged, per contracts Section 7.2.
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

                # Non-direct conditions are provenance facts for
                # Lineage (Section 6/7.2) — never routed to Data
                # Quality, never added to the row itself.
                if mapping.condition != "direct":
                    lineage_records.append(
                        {
                            "row_index": row_index,
                            "column": column_name,
                            "condition": mapping.condition,
                            "canonical_type": mapping.canonical_type,
                            "source_type": source_type,
                        }
                    )

            normalized_rows.append(normalized_row)

        return normalized_rows, lineage_records
