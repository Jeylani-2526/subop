# Architecture

## SUBOP System Architecture v1

Full documentation of all 10 SUBOP modules, their data flow, and cross-cutting concerns.

| File | Description |
|------|-------------|
| `architecture_doc_v1.md` | Full architecture document (module design, data flow, deployment topology) |

| `diagrams/deployment_topology_diagram.png` | Deployment topology diagram (editable source: `deployment_topology_diagram.drawio`) |

## Layer Summary

| Layer | Modules |
|-------|---------|
| Data Sources | Oracle · PostgreSQL · MySQL · MSSQL · MongoDB · Cassandra · CSV/Parquet · REST API · GraphQL · Kafka |
| Ingestion | Module 1 — Connector Framework |
| Abstraction | Module 2 — Database Abstraction Layer |
| Processing | Module 3 — ETL Engine · Module 4 — CDC/Real-Time Layer |
| Storage | Module 5 — Metadata-Driven Data Warehouse (PostgreSQL) |
| Analytics | Module 6 — BI Dashboard & Analytics |
| Governance | Module 7 — Data Quality · Module 8 — Lineage · Module 9 — Catalog |
| Security | Module 10 — Security & Compliance (cross-cutting) |

Full architecture documentation will be expanded in **M3 (29 Jun – 19 Jul 2026)**.

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend API | FastAPI + Uvicorn (Python 3.10+) |
| Data Warehouse | PostgreSQL 15 |
| CDC & Streaming | Debezium + Apache Kafka 3.7 + Apache Zookeeper |
| Connector Drivers | psycopg2 · PyMySQL · cx_Oracle · pyodbc · pymongo · cassandra-driver · pandas · pyarrow · requests · gql · confluent-kafka-python |
| BI Frontend | React + TypeScript (Vite) |
| Infrastructure | Docker Compose |
| Testing | pytest + Locust (load testing) |
| Code Quality | Black · flake8 · Prettier · ESLint |
| Version Control | GitHub — `main` / `develop` branch policy |
