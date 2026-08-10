from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, Optional


# Represents the result of mapping a database-native type
# to the canonical type system defined in Mapping Specification v1.
@dataclass(frozen=True)
class TypeMappingResult:
    canonical_type: str
    source_type: str
    condition: str = "direct"
    metadata: Optional[Dict[str, Any]] = None


class UnsupportedTypeError(ValueError):
    """
    Raised when a database-native type has no supported mapping
    and no registered override exists.
    """


class UniversalTypeMapper:
    """
    Maps PostgreSQL, MySQL, and Microsoft SQL Server native types
    to the canonical type set defined in Universal Type Mapping
    Specification v1.

    Canonical types:
    - INTEGER
    - BIGINT
    - DECIMAL
    - VARCHAR
    - TEXT
    - BOOLEAN
    - DATE
    - TIMESTAMP
    - JSON
    - BINARY
    """

    # PostgreSQL native types mapped to the canonical type set.
    POSTGRESQL_MAPPING = {
        # Integer types
        "smallint": ("INTEGER", "direct"),
        "integer": ("INTEGER", "direct"),
        "serial": ("INTEGER", "direct"),
        "bigint": ("BIGINT", "direct"),
        "bigserial": ("BIGINT", "direct"),

        # Exact numeric types
        "numeric": ("DECIMAL", "direct"),
        "decimal": ("DECIMAL", "direct"),

        # Approximate floating-point types.
        # These map to DECIMAL but must be flagged as inexact.
        "real": ("DECIMAL", "inexact"),
        "double precision": ("DECIMAL", "inexact"),

        # Character types
        "char": ("VARCHAR", "direct"),
        "character": ("VARCHAR", "direct"),
        "varchar": ("VARCHAR", "direct"),
        "character varying": ("VARCHAR", "direct"),
        "text": ("TEXT", "direct"),

        # Boolean type
        "boolean": ("BOOLEAN", "direct"),

        # Date and timestamp types
        "date": ("DATE", "direct"),
        "timestamp": ("TIMESTAMP", "direct"),
        "timestamp without time zone": ("TIMESTAMP", "direct"),
        "timestamp with time zone": ("TIMESTAMP", "direct"),
        "timestamptz": ("TIMESTAMP", "direct"),

        # Structured data
        "json": ("JSON", "direct"),
        "jsonb": ("JSON", "direct"),

        # Binary data
        "bytea": ("BINARY", "direct"),

        # Canonical v1 has no UUID type.
        "uuid": ("VARCHAR", "fallback"),

        # XML is represented as canonical text.
        "xml": ("TEXT", "fallback"),

        # Arrays require recursive element normalization.
        "array": ("JSON", "conditional"),

        # Canonical v1 has no TIME or INTERVAL type.
        "time": ("VARCHAR", "fallback"),
        "time without time zone": ("VARCHAR", "fallback"),
        "time with time zone": ("VARCHAR", "fallback"),
        "interval": ("VARCHAR", "fallback"),
    }

    # MySQL native types mapped to the canonical type set.
    MYSQL_MAPPING = {
        # Signed integer types
        "tinyint": ("INTEGER", "direct"),
        "smallint": ("INTEGER", "direct"),
        "mediumint": ("INTEGER", "direct"),
        "int": ("INTEGER", "direct"),
        "integer": ("INTEGER", "direct"),

        # BIGINT requires 64-bit semantics.
        "bigint": ("BIGINT", "direct"),

        # Exact numeric types
        "decimal": ("DECIMAL", "direct"),
        "numeric": ("DECIMAL", "direct"),

        # Approximate numeric types
        "float": ("DECIMAL", "inexact"),
        "double": ("DECIMAL", "inexact"),

        # Character types with declared finite length
        "char": ("VARCHAR", "direct"),
        "varchar": ("VARCHAR", "direct"),

        # Large text types
        "tinytext": ("TEXT", "direct"),
        "text": ("TEXT", "direct"),
        "mediumtext": ("TEXT", "direct"),
        "longtext": ("TEXT", "direct"),

        # Explicit Boolean aliases
        "boolean": ("BOOLEAN", "direct"),
        "bool": ("BOOLEAN", "direct"),

        # Date and timestamp types
        "date": ("DATE", "direct"),
        "datetime": ("TIMESTAMP", "direct"),
        "timestamp": ("TIMESTAMP", "direct"),

        # Structured JSON data
        "json": ("JSON", "direct"),

        # Binary data
        "binary": ("BINARY", "direct"),
        "varbinary": ("BINARY", "direct"),
        "tinyblob": ("BINARY", "direct"),
        "blob": ("BINARY", "direct"),
        "mediumblob": ("BINARY", "direct"),
        "longblob": ("BINARY", "direct"),

        # ENUM is represented as text while retaining schema metadata.
        "enum": ("VARCHAR", "fallback"),

        # MySQL TIME can represent durations, so canonical v1
        # preserves it as deterministic text.
        "time": ("VARCHAR", "fallback"),
    }

    # SQL Server native types mapped to the canonical type set.
    MSSQL_MAPPING = {
        # Integer types
        "tinyint": ("INTEGER", "direct"),
        "smallint": ("INTEGER", "direct"),
        "int": ("INTEGER", "direct"),
        "bigint": ("BIGINT", "direct"),

        # Exact and monetary numeric types
        "decimal": ("DECIMAL", "direct"),
        "numeric": ("DECIMAL", "direct"),
        "money": ("DECIMAL", "direct"),
        "smallmoney": ("DECIMAL", "direct"),

        # Approximate numeric types
        "float": ("DECIMAL", "inexact"),
        "real": ("DECIMAL", "inexact"),

        # Character types with finite declared length
        "char": ("VARCHAR", "direct"),
        "nchar": ("VARCHAR", "direct"),
        "varchar": ("VARCHAR", "direct"),
        "nvarchar": ("VARCHAR", "direct"),

        # Legacy large-text types
        "text": ("TEXT", "direct"),
        "ntext": ("TEXT", "direct"),

        # Boolean representation
        "bit": ("BOOLEAN", "direct"),

        # Temporal types
        "date": ("DATE", "direct"),
        "datetime": ("TIMESTAMP", "direct"),
        "smalldatetime": ("TIMESTAMP", "direct"),
        "datetime2": ("TIMESTAMP", "direct"),
        "datetimeoffset": ("TIMESTAMP", "direct"),

        # Binary types
        "binary": ("BINARY", "direct"),
        "varbinary": ("BINARY", "direct"),
        "image": ("BINARY", "direct"),
        "rowversion": ("BINARY", "direct"),

        # SQL Server TIMESTAMP is a binary row-version value,
        # not a temporal timestamp.
        "timestamp": ("BINARY", "direct"),

        # Canonical v1 has no UUID type.
        "uniqueidentifier": ("VARCHAR", "fallback"),

        # XML remains complete textual content.
        "xml": ("TEXT", "fallback"),

        # SQL_VARIANT must be resolved using the native type
        # of each individual value.
        "sql_variant": (None, "ambiguous"),
    }

    @classmethod
    def map_type(
        cls,
        database: str,
        source_type: str,
        *,
        schema_intent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TypeMappingResult:
        """
        Map a database-native type declaration to a canonical type.

        Native schema metadata takes precedence over the Python runtime type.

        Args:
            database:
                Database identifier such as "postgresql", "mysql", or "mssql".

            source_type:
                Native database type declaration such as VARCHAR(255),
                NUMERIC(10, 2), or NVARCHAR(MAX).

            schema_intent:
                Optional explicit intent used to resolve ambiguous types,
                such as JSON or BOOLEAN.

            metadata:
                Optional schema metadata such as precision, scale,
                unsigned status, Unicode status, or time-zone awareness.
        """

        normalized_database = database.strip().lower()
        normalized_type = cls._normalize_type_name(source_type)

        mapping_metadata: Dict[str, Any] = dict(metadata or {})

        # Preserve the original declaration so length, precision,
        # scale, MAX, signedness, and similar information can be retained.
        mapping_metadata["native_type"] = source_type

        if normalized_database in {"postgresql", "postgres", "psycopg2"}:
            return cls._map_postgresql(
                source_type,
                normalized_type,
                mapping_metadata,
            )

        if normalized_database in {"mysql", "pymysql"}:
            return cls._map_mysql(
                source_type,
                normalized_type,
                schema_intent,
                mapping_metadata,
            )

        if normalized_database in {
            "mssql",
            "sqlserver",
            "sql_server",
            "pyodbc",
        }:
            return cls._map_mssql(
                source_type,
                normalized_type,
                schema_intent,
                mapping_metadata,
            )

        raise UnsupportedTypeError(
            f"Unsupported database: {database}"
        )

    @staticmethod
    def _normalize_type_name(source_type: str) -> str:
        """
        Normalize a SQL type declaration while preserving special
        multi-word native type names.
        """

        if not source_type or not source_type.strip():
            raise ValueError("source_type must not be empty")

        normalized = " ".join(source_type.strip().lower().split())

        # Parameterized declarations are reduced to their base type.
        # VARCHAR(255) -> varchar
        # DECIMAL(10, 2) -> decimal
        # NVARCHAR(MAX) -> nvarchar
        if "(" in normalized:
            normalized = normalized.split("(", 1)[0].strip()

        return normalized

    @classmethod
    def _map_postgresql(
        cls,
        original_type: str,
        normalized_type: str,
        metadata: Dict[str, Any],
    ) -> TypeMappingResult:
        """
        Apply PostgreSQL-specific mapping rules.
        """

        mapping = cls.POSTGRESQL_MAPPING.get(normalized_type)

        if mapping is None:
            raise UnsupportedTypeError(
                f"Unsupported PostgreSQL type: {original_type}"
            )

        canonical_type, condition = mapping

        # Preserve TEXT identity explicitly because the Week 13
        # zero-code-change demonstration depends on this metadata.
        if normalized_type == "text":
            metadata["postgresql_text"] = True

        # Approximate floating-point values must be marked as inexact.
        if condition == "inexact":
            metadata["inexact"] = True
            metadata["reason"] = (
                "PostgreSQL source type uses binary floating-point semantics."
            )

        # UUID has no dedicated canonical v1 type.
        if normalized_type == "uuid":
            metadata["fallback_reason"] = (
                "Canonical type system v1 has no UUID type."
            )

        # XML semantics are retained as metadata even though the
        # canonical representation is TEXT.
        if normalized_type == "xml":
            metadata["xml_semantics"] = True

        # ARRAY is only valid if element values can also be normalized.
        if normalized_type == "array":
            metadata["requires_recursive_normalization"] = True

        return TypeMappingResult(
            canonical_type=canonical_type,
            source_type=original_type,
            condition=condition,
            metadata=metadata,
        )

    @classmethod
    def _map_mysql(
        cls,
        original_type: str,
        normalized_type: str,
        schema_intent: Optional[str],
        metadata: Dict[str, Any],
    ) -> TypeMappingResult:
        """
        Apply MySQL-specific mapping and ambiguity rules.
        """

        # Keep the complete original declaration for modifier checks
        # such as UNSIGNED and TINYINT(1).
        original_lower = original_type.strip().lower()

        # MySQL declarations may include modifiers such as UNSIGNED
        # or ZEROFILL. Canonical lookup is based on the native base type,
        # while modifiers remain available through metadata.
        base_type = normalized_type.split()[0]

        # INT UNSIGNED can exceed signed 32-bit integer semantics,
        # therefore the v1 specification maps it to BIGINT.
        if base_type in {"int", "integer"} and "unsigned" in original_lower:
            metadata["unsigned"] = True

            return TypeMappingResult(
                canonical_type="BIGINT",
                source_type=original_type,
                condition="direct",
                metadata=metadata,
            )

        # BIGINT remains BIGINT, while unsigned status is preserved
        # as metadata for callers that need the original range semantics.
        if base_type == "bigint" and "unsigned" in original_lower:
            metadata["unsigned"] = True

        # TINYINT(1) is ambiguous in MySQL. It remains INTEGER unless
        # explicit schema intent identifies the column as Boolean.
        if base_type == "tinyint" and "(1" in original_lower:
            metadata["ambiguous_boolean"] = True

            if schema_intent and schema_intent.lower() == "boolean":
                return TypeMappingResult(
                    canonical_type="BOOLEAN",
                    source_type=original_type,
                    condition="ambiguous",
                    metadata=metadata,
                )

            return TypeMappingResult(
                canonical_type="INTEGER",
                source_type=original_type,
                condition="ambiguous",
                metadata=metadata,
            )

        # Resolve the canonical type from the normalized MySQL base type.
        mapping = cls.MYSQL_MAPPING.get(base_type)

        # Unknown types must fail explicitly instead of being silently
        # coerced into an unrelated canonical representation.
        if mapping is None:
            raise UnsupportedTypeError(
                f"Unsupported MySQL type: {original_type}"
            )

        canonical_type, condition = mapping

        # FLOAT and DOUBLE originate from binary floating-point semantics.
        # They map to DECIMAL but are marked as inexact as required by v1.
        if condition == "inexact":
            metadata["inexact"] = True
            metadata["reason"] = (
                "MySQL source type uses binary floating-point semantics."
            )

        # ENUM falls back to VARCHAR while retaining its schema identity
        # through metadata when the abstraction layer needs it.
        if base_type == "enum":
            metadata["enum_semantics"] = True

        return TypeMappingResult(
            canonical_type=canonical_type,
            source_type=original_type,
            condition=condition,
            metadata=metadata,
        )

    @classmethod
    def _map_mssql(
        cls,
        original_type: str,
        normalized_type: str,
        schema_intent: Optional[str],
        metadata: Dict[str, Any],
    ) -> TypeMappingResult:
        """
        Apply SQL Server-specific mapping and ambiguity rules.
        """

        # Preserve the full native declaration for checks that depend
        # on MAX or other declaration-specific details.
        original_lower = original_type.strip().lower()

        # VARCHAR(MAX) and NVARCHAR(MAX) represent large text values.
        # Finite VARCHAR/NVARCHAR declarations remain canonical VARCHAR.
        if normalized_type in {"varchar", "nvarchar"} and "(max" in original_lower:
            if normalized_type == "nvarchar":
                metadata["unicode"] = True

            metadata["max_length"] = True

            # NVARCHAR(MAX) is JSON only when explicit schema intent
            # establishes JSON semantics. Text is never parsed as JSON
            # solely because its contents happen to look like JSON.
            if (
                normalized_type == "nvarchar"
                and schema_intent
                and schema_intent.lower() == "json"
            ):
                metadata["explicit_json_intent"] = True

                return TypeMappingResult(
                    canonical_type="JSON",
                    source_type=original_type,
                    condition="conditional",
                    metadata=metadata,
                )

            return TypeMappingResult(
                canonical_type="TEXT",
                source_type=original_type,
                condition="direct",
                metadata=metadata,
            )

        # Resolve the remaining SQL Server types through the v1 mapping table.
        mapping = cls.MSSQL_MAPPING.get(normalized_type)

        if mapping is None:
            raise UnsupportedTypeError(
                f"Unsupported MSSQL type: {original_type}"
            )

        canonical_type, condition = mapping

        # SQL_VARIANT cannot be normalized from the declared column type
        # alone because individual rows can contain different native types.
        if normalized_type == "sql_variant":
            raise UnsupportedTypeError(
                "SQL_VARIANT requires per-value native type resolution."
            )

        # Preserve Unicode semantics for SQL Server N-types.
        if normalized_type in {"nchar", "nvarchar", "ntext"}:
            metadata["unicode"] = True

        # FLOAT and REAL map to DECIMAL but must remain visibly inexact.
        if condition == "inexact":
            metadata["inexact"] = True
            metadata["reason"] = (
                "SQL Server source type uses binary floating-point semantics."
            )

        # Keep deprecated native-type information for compatibility and
        # migration diagnostics without adding columns to query results.
        if normalized_type in {"text", "ntext", "image"}:
            metadata["deprecated_native_type"] = True

        # SQL Server TIMESTAMP is a row-version binary value, not a date/time.
        if normalized_type == "timestamp":
            metadata["rowversion_semantics"] = True

        # UNIQUEIDENTIFIER falls back to VARCHAR in canonical v1.
        if normalized_type == "uniqueidentifier":
            metadata["uuid_semantics"] = True

        # XML falls back to TEXT while retaining XML identity in metadata.
        if normalized_type == "xml":
            metadata["xml_semantics"] = True

        return TypeMappingResult(
            canonical_type=canonical_type,
            source_type=original_type,
            condition=condition,
            metadata=metadata,
        )


def normalize_value(
    value: Any,
    canonical_type: Optional[str] = None,
    *,
    source_type: Optional[str] = None,
) -> Any:
    """
    Normalize a returned database value without changing the public
    List[Dict[str, Any]] result structure.
    """

    # SQL NULL must always remain Python None.
    if value is None:
        return None

    # Binary-compatible values should become immutable bytes.
    if canonical_type == "BINARY":
        if isinstance(value, memoryview):
            return value.tobytes()

        if isinstance(value, bytearray):
            return bytes(value)

        if isinstance(value, bytes):
            return value

    # Exact numeric values must remain Decimal.
    # Existing Decimal objects are therefore returned unchanged.
    if canonical_type == "DECIMAL" and isinstance(value, Decimal):
        return value

    # JSON text is parsed only when the canonical/native schema
    # explicitly establishes JSON intent.
    if canonical_type == "JSON" and isinstance(value, str):
        return json.loads(value)

    # All other values are preserved unless a future normalization
    # rule explicitly defines a deterministic conversion.
    return value