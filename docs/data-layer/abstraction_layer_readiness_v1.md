# M5 Abstraction-Layer Readiness Confirmation

## Status

The M4 abstraction layer is stable and ready to serve as the data-access boundary for the M5 ETL Engine.

The current implementation provides a database-independent interface over the validated PostgreSQL, MySQL, and Microsoft SQL Server connectors. M5 components can perform read and write operations through `AbstractionLayer` without depending directly on connector-specific implementations.

## Stable API Surface

The supported abstraction-layer operations are:

* `execute_query(sql, params=None, *, column_types=None, schema_intents=None)`
* `execute_write(sql, params=None)`
* `health_check()`

`execute_query()` preserves the existing `List[Dict[str, Any]]` public result structure. When native column metadata is supplied, returned values can be normalized through the Universal Type Mapping module without changing column names or row ordering.

`execute_write()` delegates write operations to the configured connector and returns the connector result unchanged.

Connection lifecycle operations remain the responsibility of the underlying connector.

## Error-Handling Contract

The abstraction layer intentionally does not wrap connector exceptions.

Connector failures therefore retain their existing exception type and error information, including the `retryable` attribute where provided by the connector.

Unsupported or unresolved type mappings fail explicitly rather than being silently converted to unrelated canonical types.

This behavior allows the M5 ETL Engine to distinguish database-operation failures from mapping failures without introducing connector-specific handling into ETL pipeline code.

## Known Mapping Limitations

Universal Type Mapping v1 provides a common canonical representation across PostgreSQL, MySQL, and MSSQL, but several native types require fallback, conditional, ambiguous, or inexact mappings.

Known cases include:

* PostgreSQL `REAL` and `DOUBLE PRECISION` map to `DECIMAL` with an `inexact` condition.
* PostgreSQL `UUID` falls back to `VARCHAR`.
* PostgreSQL `XML` falls back to `TEXT`.
* PostgreSQL `TIME` and `INTERVAL` fall back to `VARCHAR`.
* PostgreSQL arrays require recursive normalization.
* MySQL `FLOAT` and `DOUBLE` map to `DECIMAL` with an `inexact` condition.
* MySQL `ENUM` falls back to `VARCHAR`.
* MySQL `TIME` falls back to `VARCHAR`.
* MySQL `TINYINT(1)` is ambiguous and remains `INTEGER` unless explicit Boolean schema intent is supplied.
* MSSQL `FLOAT` and `REAL` map to `DECIMAL` with an `inexact` condition.
* MSSQL `UNIQUEIDENTIFIER` falls back to `VARCHAR`.
* MSSQL `XML` falls back to `TEXT`.
* MSSQL `NVARCHAR(MAX)` maps to `JSON` only when explicit JSON schema intent is supplied; otherwise it remains `TEXT`.
* MSSQL `SQL_VARIANT` requires per-value native type resolution and is not normalized from the declared column type alone.
* MSSQL `TIMESTAMP` is treated as binary row-version data rather than a temporal timestamp.

Mapping metadata preserves relevant native semantics where the canonical v1 type system cannot represent them directly.

## Validation

The abstraction-layer implementation has been validated through its unit-test suite and the M4 zero-code-change demonstration.

The abstraction-layer unit-test suite passes all 13 tests.

The zero-code-change demonstration successfully executed the same read/write logic through `AbstractionLayer` against:

* PostgreSQL
* MySQL
* Microsoft SQL Server

The full M4 verification suite also passes all 43 connector, type-mapping, and abstraction-layer tests in the validated local environment.

## M6 Connector Follow-Up

The five additional connectors planned for M6 should conform to the same abstraction boundary.

Each new connector should provide compatible:

* `connect()` and `disconnect()` lifecycle operations;
* `execute_query()` behavior;
* `execute_write()` behavior where applicable;
* `health_check()` behavior;
* dictionary-based query results;
* connector error semantics.

Each additional database or data source must also define its native-to-canonical type mappings and explicitly document unsupported, ambiguous, conditional, inexact, or fallback cases.

Connector-specific behavior should remain outside `AbstractionLayer` so that M5 ETL Engine code can continue using the same stable interface.

## Conclusion

The M4 abstraction layer is considered ready for M5 ETL Engine integration.

M5 may build against the current `execute_query()`, `execute_write()`, and `health_check()` interface without introducing database-specific logic into the ETL layer.

The known type-mapping limitations above are documented constraints rather than blockers. M6 connector expansion should preserve the same interface and error-handling contract.
