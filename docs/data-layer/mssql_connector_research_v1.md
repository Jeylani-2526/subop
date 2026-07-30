# MSSQL Connector Research & Prototype Plan

## Table of Contents

- [1. Driver Setup](#1-driver-setup)
- [2. Connection String Format](#2-connection-string-format)
- [3. SQL Dialect Differences Compared to PostgreSQL](#3-sql-dialect-differences-compared-to-postgresql)
  - [3.1 Limiting Results: TOP vs LIMIT](#31-limiting-results-top-vs-limit)
  - [3.2 Auto-Increment Columns: IDENTITY vs SERIAL / SEQUENCE](#3.2-auto-increment-columns-identity-vs-serial--sequence)
  - [3.3 Unicode Text Types: NVARCHAR(MAX) vs TEXT](#3.3-unicode-text-types-nvarcharmax-vs-text)
- [4. Prototype Plan for MSSQL Connector](#4-prototype-plan-for-mssql-connector)
- [5. Implementation Complexity](#5-implementation-complexity)
- [6. Conclusion](#6-conclusion)

---

## 1. Driver Setup

The MSSQL connector requires an ODBC-based database driver stack. In Python, the most common option is `pyodbc`, which provides access to databases through ODBC drivers. For Microsoft SQL Server, this requires the Microsoft ODBC Driver for SQL Server to be installed in the runtime environment.

For Linux or Docker-based environments, the setup includes:

- Installing the Microsoft ODBC Driver for SQL Server
- Installing `unixODBC` and development headers
- Installing the Python package `pyodbc`

Example Python dependency:

```bash
pip install pyodbc
```

A typical Docker/Linux setup would need to install the Microsoft ODBC Driver before the Python application starts. This makes the MSSQL connector more complex than the PostgreSQL connector, because PostgreSQL can be accessed directly through Python drivers such as `psycopg2`, while MSSQL depends on an external ODBC driver layer.

A simplified Python import check can be used to verify that the dependency is available:

```python
import pyodbc

print(pyodbc.drivers())
```

This code lists the installed ODBC drivers. For the MSSQL connector, the expected driver should include an entry such as `ODBC Driver 18 for SQL Server`.

---

## 2. Connection String Format

A typical MSSQL ODBC connection string can look like this:

```text
DRIVER={ODBC Driver 18 for SQL Server};
SERVER=host,1433;
DATABASE=db;
UID=user;
PWD=password;
TrustServerCertificate=yes;
```

For local Docker-based development, the server value would usually point to the container host and SQL Server port `1433`.

Example:

```text
DRIVER={ODBC Driver 18 for SQL Server};
SERVER=localhost,1433;
DATABASE=testdb;
UID=sa;
PWD=YourStrongPassword;
TrustServerCertificate=yes;
```

A simple connection test with `pyodbc` could look like this:

```python
import pyodbc

connection_string = (
    "DRIVER={ODBC Driver 18 for SQL Server};"
    "SERVER=localhost,1433;"
    "DATABASE=testdb;"
    "UID=sa;"
    "PWD=YourStrongPassword;"
    "TrustServerCertificate=yes;"
)

connection = pyodbc.connect(connection_string)
cursor = connection.cursor()

cursor.execute("SELECT 1")
print(cursor.fetchone())

cursor.close()
connection.close()
```

`TrustServerCertificate=yes` can simplify local development, especially when no trusted certificate chain is configured. For production environments, certificate handling should be reviewed more carefully.

---

## 3. SQL Dialect Differences Compared to PostgreSQL

SQL Server uses the T-SQL dialect, which differs from PostgreSQL in several relevant areas. These differences are important for connector implementation because SQL statements cannot always be reused directly across database systems.

### 3.1 Limiting Results: TOP vs LIMIT

One of the primary SQL dialect differences between PostgreSQL and SQL Server concerns row limiting. PostgreSQL uses the `LIMIT` clause, whereas SQL Server uses the `TOP` keyword.

| PostgreSQL | SQL Server |
|------------|------------|
| `SELECT * FROM users LIMIT 10;` | `SELECT TOP 10 * FROM users;` |
| Uses `LIMIT` | Uses `TOP` |
| Limit expression appears at the end of the query | Limit expression appears immediately after `SELECT` |

PostgreSQL example:

```sql
SELECT * FROM users LIMIT 10;
```

SQL Server example:

```sql
SELECT TOP 10 * FROM users;
```

Although both statements return the same result set, the syntax differs significantly. PostgreSQL places the row limit at the end of the query using the `LIMIT` clause, while SQL Server specifies the number of rows immediately after the `SELECT` keyword by using `TOP`. Consequently, SQL queries cannot be converted between these database systems through simple string replacement.

This difference directly affects the connector implementation. If `execute_query()` supports automatic row limiting or if SQL statements are generated programmatically, the connector must generate database-specific SQL syntax rather than relying on a generic implementation.

A simple helper function for SQL Server-specific row limiting could look like this:

```python
def build_mssql_select_with_limit(table_name: str, limit: int) -> str:
    return f"SELECT TOP {limit} * FROM {table_name};"


query = build_mssql_select_with_limit("users", 10)
print(query)
# SELECT TOP 10 * FROM users;
```

Therefore, the abstraction layer should encapsulate these dialect-specific differences to provide a consistent connector interface while generating database-specific SQL internally.

---

### 3.2 Auto-Increment Columns: IDENTITY vs SERIAL / SEQUENCE

Another important SQL dialect difference concerns the implementation of auto-incrementing primary keys. Although PostgreSQL and Microsoft SQL Server both provide automatically generated identifiers, they use fundamentally different mechanisms to achieve this functionality.

| PostgreSQL | SQL Server |
|------------|------------|
| `SERIAL` / `BIGSERIAL` | `IDENTITY(1,1)` |
| Sequence-based value generation | Column property handles value generation |
| Commonly backed by a sequence object | Managed internally by SQL Server |

PostgreSQL example:

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL
);
```

SQL Server example:

```sql
CREATE TABLE users (
    id INT IDENTITY(1,1) PRIMARY KEY,
    name NVARCHAR(100) NOT NULL
);
```

PostgreSQL typically relies on sequence objects through the `SERIAL` or `BIGSERIAL` data types, whereas SQL Server manages value generation internally by using the `IDENTITY` column property.

This distinction affects schema creation, data insertion, and database abstraction. During schema translation, the connector must map PostgreSQL sequence-based columns to SQL Server identity columns while preserving the same logical behavior across different database systems.

Furthermore, write operations should not explicitly provide values for auto-generated columns unless this behavior is intentionally required. Instead, the database engine should remain responsible for generating primary key values automatically.

Example insert without explicitly setting the auto-generated ID:

```sql
INSERT INTO users (name)
VALUES ('Alice');
```

This insert pattern works conceptually for both systems because the database engine generates the primary key value automatically.

---

### 3.3 Unicode Text Types: NVARCHAR(MAX) vs TEXT

One important difference between PostgreSQL and SQL Server concerns the representation of large text data. Although both database systems support storing long text values, they use different data types and Unicode handling mechanisms, which should be considered when designing a database-independent connector.

| PostgreSQL | SQL Server |
|------------|------------|
| `TEXT` | `NVARCHAR(MAX)` |
| Variable-length text | Large Unicode text |
| Common general-purpose text type | Explicit Unicode-capable text type |

SQL Server example:

```sql
description NVARCHAR(MAX)
```

PostgreSQL example:

```sql
description TEXT
```

SQL Server commonly relies on `NVARCHAR(MAX)` for Unicode text, whereas PostgreSQL generally uses the `TEXT` data type for storing variable-length text.

This distinction is particularly important when translating database schemas between different database management systems. Although both data types provide similar functionality from an application perspective, their underlying implementations and Unicode handling differ.

A simplified mapping function could look like this:

```python
def map_text_type_to_mssql(source_type: str) -> str:
    if source_type.upper() == "TEXT":
        return "NVARCHAR(MAX)"
    return source_type


print(map_text_type_to_mssql("TEXT"))
# NVARCHAR(MAX)
```

Consequently, the connector abstraction layer should map these data types appropriately to ensure consistent behavior across supported database systems while preserving compatibility and data integrity.

---

## 4. Prototype Plan for MSSQL Connector

To ensure consistency across supported database systems, the proposed MSSQL connector should follow the same architectural interface as the existing PostgreSQL and MySQL connectors. While the internal implementation relies on `pyodbc` and SQL Server-specific behavior, the public connector interface should remain identical.

The planned connector should expose the following methods:

| Method | Responsibility |
|--------|----------------|
| `connect()` | Establish a database connection using `pyodbc.connect()` |
| `disconnect()` | Close the active database connection |
| `execute_query()` | Execute read-only SQL queries and return results |
| `execute_write()` | Execute write operations such as `INSERT`, `UPDATE`, and `DELETE` |
| `health_check()` | Verify whether the database connection is working |

The MSSQL connector follows the same high-level interface design as the existing PostgreSQL and MySQL connectors. The connector exposes five core methods: `connect()`, `disconnect()`, `execute_query()`, `execute_write()`, and `health_check()`. This provides a consistent API regardless of the underlying database system.

Each method is responsible for a specific aspect of database interaction. The `connect()` and `disconnect()` methods manage the database connection lifecycle, while `execute_query()` and `execute_write()` handle read and write operations, respectively. The `health_check()` method provides a lightweight mechanism for verifying database availability.

A simplified prototype could look like this:

```python
import pyodbc
from typing import Any


class MSSQLConnector:
    def __init__(self, connection_string: str) -> None:
        self.connection_string = connection_string
        self.connection = None

    def connect(self) -> None:
        self.connection = pyodbc.connect(self.connection_string)

    def disconnect(self) -> None:
        if self.connection is not None:
            self.connection.close()
            self.connection = None

    def execute_query(self, query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        if self.connection is None:
            raise RuntimeError("Database connection is not established.")

        cursor = self.connection.cursor()
        try:
            cursor.execute(query, params)
            columns = [column[0] for column in cursor.description]
            rows = cursor.fetchall()

            return [
                dict(zip(columns, row))
                for row in rows
            ]
        finally:
            cursor.close()

    def execute_write(self, query: str, params: tuple[Any, ...] = ()) -> int:
        if self.connection is None:
            raise RuntimeError("Database connection is not established.")

        cursor = self.connection.cursor()
        try:
            cursor.execute(query, params)
            self.connection.commit()
            return cursor.rowcount
        except Exception:
            self.connection.rollback()
            raise
        finally:
            cursor.close()

    def health_check(self) -> bool:
        try:
            result = self.execute_query("SELECT 1 AS status;")
            return bool(result)
        except Exception:
            return False
```

Example usage:

```python
connector = MSSQLConnector(
    "DRIVER={ODBC Driver 18 for SQL Server};"
    "SERVER=localhost,1433;"
    "DATABASE=testdb;"
    "UID=sa;"
    "PWD=YourStrongPassword;"
    "TrustServerCertificate=yes;"
)

connector.connect()

if connector.health_check():
    users = connector.execute_query("SELECT TOP 10 * FROM users;")
    print(users)

connector.disconnect()
```

Although the external interface remains consistent with the existing connectors, the internal implementation must account for SQL Server-specific requirements such as ODBC-based connectivity, connection string construction, transaction handling, and result normalization. This approach preserves a unified connector abstraction while allowing each database implementation to handle its own platform-specific behavior.

---

## 5. Implementation Complexity

The MSSQL connector is expected to be more complex than the PostgreSQL connector for three main reasons.

First, MSSQL access from Python usually requires an ODBC driver stack. This means that the runtime environment must include both the Python package `pyodbc` and the Microsoft ODBC Driver for SQL Server.

Second, SQL Server uses T-SQL, which differs from PostgreSQL SQL syntax in several areas. Important examples include `TOP` instead of `LIMIT`, `IDENTITY` columns instead of PostgreSQL-style serial or sequence-based identifiers, and `NVARCHAR(MAX)` instead of PostgreSQL `TEXT`.

Third, result handling may require extra normalization. PostgreSQL's current implementation can rely on dictionary-like cursor behavior, while `pyodbc` returns row objects that may need to be manually converted into dictionaries.

Example result normalization:

```python
def rows_to_dicts(cursor, rows):
    columns = [column[0] for column in cursor.description]
    return [dict(zip(columns, row)) for row in rows]
```

Overall, these differences increase the implementation effort compared to the existing PostgreSQL connector while maintaining the same connector interface for the SUBOP platform.

---

## 6. Conclusion

This research examined the main technical requirements for implementing an MSSQL connector within the SUBOP platform. The analysis showed that, despite several SQL Server-specific differences, the connector can follow the same high-level architecture and public interface as the existing PostgreSQL and MySQL connectors.

The primary implementation challenges arise from three areas: the dependency on the ODBC driver stack, differences in the SQL dialect, and additional result normalization required by `pyodbc`. These aspects should be addressed within the internal implementation while preserving a consistent connector interface across all supported database systems.

Overall, the proposed prototype plan provides a clear foundation for developing the MSSQL connector. By reusing the existing connector architecture and introducing SQL Server-specific adaptations where necessary, the connector can be integrated into the SUBOP platform without affecting the overall abstraction layer.

This research note therefore serves as a technical reference and implementation guideline for the upcoming M4 MSSQL connector development task.
