# Module 5 — Metadata-Driven Data Warehouse

**Status:** ⏳ Scheduled for M8 (3 Nov – 30 Nov 2026)
**Owner:** Abdullah + Omer

## Description

Automatically generates and manages fact tables, dimension tables, SCD logic,
and schema versioning from source metadata — without manual SQL writing.

## KPI Target

Warehouse schema generated 80% faster than a manually written equivalent.

## Storage

PostgreSQL 15 is the target database. No separate OLAP engine (e.g. ClickHouse)
is included — the BI layer queries PostgreSQL directly.
