# Module 1 — Connector Framework

**Status:** ⏳ Scheduled for M4 (20 Jul – 9 Aug 2026)
**Owner:** Omer

## Description

Provides standardised, configurable access to all 12 supported data sources.
A connection to any supported source is configured without writing custom code,
and each connector passes an automated validation test.

## Supported Sources

| Source | Type | Library |
|--------|------|---------|
| PostgreSQL | Relational | psycopg2 |
| MySQL | Relational | PyMySQL |
| MS SQL Server | Relational | pyodbc |
| Oracle | Relational | cx_Oracle |
| MongoDB | NoSQL | pymongo |
| Cassandra | NoSQL | cassandra-driver |
| CSV / Excel | File | pandas |
| Parquet | File | pyarrow |
| REST API | API | requests |
| GraphQL | API | gql |
| Apache Kafka | Streaming | confluent-kafka-python |
| Debezium / Kafka Connect | CDC | Kafka Connect |

## Local Setup — MS SQL Server

`pyodbc` requires the **Microsoft ODBC Driver 18 for SQL Server** to be installed
as a system driver — `pip install pyodbc` alone is not enough. Without it,
`tests/test_mssql_connector.py` fails immediately with an
`[IM002] Data source name not found` error, before ever reaching the database.

Install it:
- Windows: `winget install Microsoft.msodbcsql.18`, or download from
  https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server
- Verify install (PowerShell): `Get-OdbcDriver | Where-Object Name -like "*SQL Server*"`
  should list "ODBC Driver 18 for SQL Server".

PostgreSQL (`psycopg2`) and MySQL (`PyMySQL`) don't need an equivalent OS-level
driver, so this step is MSSQL-specific.
