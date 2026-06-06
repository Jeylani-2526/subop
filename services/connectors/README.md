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
