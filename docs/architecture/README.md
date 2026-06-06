# Architecture

## SUBOP System Architecture v1.1

The architecture diagram shows all 10 SUBOP modules, their data flow, and cross-cutting concerns.

| File | Description |
|------|-------------|
| `architecture_v1_1.drawio` | Editable draw.io source — open at app.diagrams.net |
| `architecture_v1.png` | PNG export for README display |

## Layer Summary

| Layer | Modules |
|-------|---------|
| Data Sources | Oracle · PostgreSQL · MySQL · MSSQL · MongoDB · Cassandra · CSV/Parquet · REST API · GraphQL · Kafka |
| Ingestion | Module 1 — Connector Framework |
| Abstraction | Module 2 — Database Abstraction Layer |
| Processing | Module 3 — ETL Engine · Module 4 — CDC/Real-Time Layer |
| Storage | Module 5 — Metadata-Driven Data Warehouse (PostgreSQL) |
| Analytics | Module 6 — BI Dashboard & OLAP Layer |
| Governance | Module 7 — Data Quality · Module 8 — Lineage · Module 9 — Catalog |
| Security | Module 10 — Security & Compliance (cross-cutting) |

Full architecture documentation will be expanded in **M3 (29 Jun – 19 Jul 2026)**.
