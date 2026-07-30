# Universal Type Mapping Specification v1

## 1. Purpose

This document defines the canonical type system used to normalize query results from the PostgreSQL (`psycopg2`), MySQL (`PyMySQL`), and Microsoft SQL Server (`pyodbc`) connectors.

The mapping standardizes database-specific types while preserving the existing query-result format:

```python
List[Dict[str, Any]]
```

This document defines the mapping contract only. Implementation of the abstraction layer is planned separately.

## 2. Canonical Type Set

| Canonical type | Python representation | Meaning |
|---|---|---|
| `INTEGER` | `int` | Integral value within conventional 32-bit semantics |
| `BIGINT` | `int` | Integral value requiring 64-bit semantics |
| `DECIMAL` | `decimal.Decimal` | Exact or normalized numeric value |
| `VARCHAR` | `str` | Character data with a declared finite length |
| `TEXT` | `str` | Large or effectively unbounded character data |
| `BOOLEAN` | `bool` | Logical true-or-false value |
| `DATE` | `datetime.date` | Date without a time component |
| `TIMESTAMP` | `datetime.datetime` | Date and time, optionally time-zone-aware |
| `JSON` | JSON-compatible Python value | Structured JSON data |
| `BINARY` | `bytes` | Raw binary data |

SQL `NULL` always remains Python `None`. Length, precision, scale, signedness, and time-zone information should be retained as metadata where available.

## 3. PostgreSQL Mapping

| PostgreSQL native type | Canonical type | Notes |
|---|---|---|
| `SMALLINT`, `INTEGER`, `SERIAL` | `INTEGER` | Smaller integer types are widened |
| `BIGINT`, `BIGSERIAL` | `BIGINT` | Sequence behavior is outside value mapping |
| `NUMERIC`, `DECIMAL` | `DECIMAL` | `psycopg2` normally returns `Decimal` |
| `REAL`, `DOUBLE PRECISION` | `DECIMAL` | **Inexact:** source uses binary floating point |
| `CHAR(n)`, `VARCHAR(n)` | `VARCHAR` | Declared length remains metadata |
| `TEXT` | `TEXT` | Direct mapping |
| `BOOLEAN` | `BOOLEAN` | Direct mapping |
| `DATE` | `DATE` | Direct mapping |
| `TIMESTAMP`, `TIMESTAMPTZ` | `TIMESTAMP` | Preserve time-zone awareness |
| `JSON`, `JSONB` | `JSON` | Both share one canonical type |
| `BYTEA` | `BINARY` | Convert `memoryview` or buffer values to `bytes` |
| `UUID` | `VARCHAR` | **Fallback:** canonical v1 has no UUID type |
| `XML` | `TEXT` | **Fallback:** XML semantics remain metadata |
| `ARRAY` | `JSON` | **Conditional:** elements must be recursively normalizable |
| `TIME`, `INTERVAL` | `VARCHAR` | **Fallback:** use a deterministic textual form |

## 4. MySQL Mapping

| MySQL native type | Canonical type | Notes |
|---|---|---|
| `TINYINT`, `SMALLINT`, `MEDIUMINT`, `INT` | `INTEGER` | `TINYINT(1)` follows the ambiguity rule below |
| `INT UNSIGNED` | `BIGINT` | Its maximum exceeds signed 32-bit range |
| `BIGINT` | `BIGINT` | Preserve unsigned status as metadata |
| `DECIMAL`, `NUMERIC` | `DECIMAL` | Preserve precision and scale |
| `FLOAT`, `DOUBLE` | `DECIMAL` | **Inexact:** source uses binary floating point |
| `CHAR(n)`, `VARCHAR(n)` | `VARCHAR` | Direct mapping |
| `TINYTEXT`, `TEXT`, `MEDIUMTEXT`, `LONGTEXT` | `TEXT` | Native capacity remains metadata |
| `BOOLEAN`, `BOOL` | `BOOLEAN` | MySQL aliases for `TINYINT(1)` |
| `TINYINT(1)` | `INTEGER` | **Ambiguous:** Boolean only with explicit schema intent |
| `DATE` | `DATE` | Zero dates require an error or configured fallback |
| `DATETIME`, `TIMESTAMP` | `TIMESTAMP` | Session time-zone context may be required |
| `JSON` | `JSON` | Parse if `PyMySQL` returns JSON as text |
| `BINARY`, `VARBINARY`, BLOB types | `BINARY` | Do not decode automatically |
| `ENUM` | `VARCHAR` | **Fallback:** enum definition remains metadata |
| `TIME` | `VARCHAR` | **Fallback:** preserve duration semantics |

## 5. Microsoft SQL Server Mapping

| SQL Server native type | Canonical type | Notes |
|---|---|---|
| `TINYINT`, `SMALLINT`, `INT` | `INTEGER` | Direct mapping |
| `BIGINT` | `BIGINT` | Direct mapping |
| `DECIMAL`, `NUMERIC`, `MONEY`, `SMALLMONEY` | `DECIMAL` | Currency identity is not encoded |
| `FLOAT`, `REAL` | `DECIMAL` | **Inexact:** source uses binary floating point |
| `CHAR(n)`, `NCHAR(n)`, `VARCHAR(n)`, `NVARCHAR(n)` | `VARCHAR` | Preserve Unicode and length metadata |
| `VARCHAR(MAX)`, `NVARCHAR(MAX)`, `TEXT`, `NTEXT` | `TEXT` | `TEXT` and `NTEXT` are deprecated native types |
| `BIT` | `BOOLEAN` | Direct mapping |
| `DATE` | `DATE` | Direct mapping |
| `DATETIME`, `SMALLDATETIME`, `DATETIME2` | `TIMESTAMP` | Preserve available precision |
| `DATETIMEOFFSET` | `TIMESTAMP` | Preserve UTC offset |
| `BINARY`, `VARBINARY`, `IMAGE` | `BINARY` | `IMAGE` is deprecated |
| `ROWVERSION`, `TIMESTAMP` | `BINARY` | Not a temporal value |
| `UNIQUEIDENTIFIER` | `VARCHAR` | **Fallback:** normalize to canonical UUID text |
| `XML` | `TEXT` | **Fallback:** preserve the complete XML document |
| `SQL_VARIANT` | Resolve per value | **Ambiguous:** rows may contain different native types |
| JSON stored in `NVARCHAR(MAX)` | `TEXT` | Map to `JSON` only with explicit schema intent |

## 6. Normalization and Ambiguity Rules

1. Native schema metadata takes priority over the returned Python runtime type.
2. SQL `NULL` must remain Python `None`.
3. Exact numeric values must use `decimal.Decimal`; they must not be silently converted to `float`.
4. Approximate floating-point values map to `DECIMAL` but must be marked as inexact.
5. Time-zone-aware timestamps must not lose their UTC offset.
6. Binary-compatible values must normalize to immutable Python `bytes`.
7. Text must not be parsed as JSON unless its native type or explicit configuration establishes JSON intent.
8. Unknown native types must produce an explicit unsupported-type error or use a registered override.
9. Mapping must not change column names, row order, or the `List[Dict[str, Any]]` result structure.
10. Mapping metadata or ambiguity flags must not be inserted as additional columns into user query results.

The recognized mapping conditions are:

- `direct`
- `inexact`
- `ambiguous`
- `conditional`
- `fallback`
- `unsupported`

## 7. Implementation Note

The current connectors already return dictionary-based rows but do not apply shared type normalization. The future abstraction layer will use these tables to normalize values while keeping the public connector result format unchanged.

Connector error handling, retry behavior, and connection lifecycle are outside the scope of this specification.