# SUBOP 🗄️

**Database-Independent Enterprise Data Platform**
> A 12-month prototype connecting heterogeneous data sources, executing database-agnostic ETL,
> supporting near-real-time change capture, automating data warehouse management, and delivering
> self-service BI dashboards — validated through real pilot testing with enterprise data teams.

[![CI](https://github.com/jeylani-2526/subop/actions/workflows/ci.yml/badge.svg)](https://github.com/jeylani-2526/subop/actions/workflows/ci.yml) [![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://github.com/jeylani-2526/subop/blob/main/LICENSE) [![Milestone](https://img.shields.io/badge/Milestone-1%20%E2%80%94%20Requirements-blue)](https://github.com/jeylani-2526/subop/blob/main/docs/milestones) [![Platform](https://img.shields.io/badge/Platform-Enterprise%20Data-1E4D78)](https://github.com/jeylani-2526/subop)

---

## Table of Contents

- [What is SUBOP?](#what-is-subop)
- [The Problem](#the-problem)
- [Architecture](#architecture)
- [System Modules](#system-modules)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
- [Project Structure](#project-structure)
- [Team](#team)
- [Roadmap](#roadmap)
- [KPI Targets](#kpi-targets)
- [Contributing](#contributing)
- [License](#license)

---

## What is SUBOP?

SUBOP (Software United Business Operation Platform) is a database-independent, end-to-end enterprise data platform. It connects to any data source, moves and transforms data through a unified ETL engine, captures real-time database changes via CDC, automatically builds and manages a data warehouse, and delivers self-service BI dashboards — without being tied to any single database vendor.

**Pipeline summary:**

```
Any Data Source (Oracle · PostgreSQL · MySQL · MSSQL · MongoDB · CSV · REST API · Kafka · ...)
  → Connector Framework
  → Database Abstraction Layer
  → ETL Engine  ◄──── CDC / Real-Time Layer (Debezium + Kafka)
  → Metadata-Driven Data Warehouse  (PostgreSQL)
  → BI Dashboard & OLAP Layer

Cross-cutting modules (apply to all layers):
  Data Quality Engine ──  validates every pipeline execution
  Data Lineage ────────── tracks source → ETL → DW → dashboard
  Data Catalog ────────── indexes all data assets for search
  Security & Compliance ─ RBAC · column masking · audit logs
```

---

## The Problem

Enterprise organisations face five critical data challenges that no single existing tool fully addresses:

| # | Problem | Impact |
|---|---------|--------|
| P1 | **Database vendor lock-in** — ETL tools tightly coupled to specific DB engines | High |
| P2 | **Fragmented data silos** — no unified connector and integration layer | High |
| P3 | **No real-time data movement** — batch-only ETL, no CDC infrastructure | High |
| P4 | **Expensive BI tooling** — high licensing costs, no self-service analytics | Medium |
| P5 | **No data quality or governance** — no automated validation, lineage, or audit | Critical |

SUBOP is designed to solve all five within a single, open, database-independent platform.

---

## Architecture

[![SUBOP Architecture](docs/architecture/architecture_v1.png)](docs/architecture/)

Full architecture documentation and the editable draw.io source are in [`docs/architecture/`](docs/architecture/).

---

## System Modules

| # | Module | Description | Tech | Milestone |
|---|--------|-------------|------|-----------|
| 1 | **Connector Framework** | Standardised access to 12+ heterogeneous data sources | psycopg2 · PyMySQL · cx_Oracle · pyodbc · pymongo · pandas · requests · confluent-kafka-python | M4 |
| 2 | **Database Abstraction Layer** | Universal SQL/NoSQL interface — zero code change when switching DB engine | Custom Python abstraction | M4 |
| 3 | **ETL Engine** | Batch, incremental, and parallel extract/transform/load pipelines | Python (Pipeline DSL) | M5 |
| 4 | **CDC / Real-Time Layer** | Near-real-time change capture from database transaction logs | Debezium + Apache Kafka | M7 |
| 5 | **Metadata-Driven Data Warehouse** | Auto-generated fact/dimension tables, SCD, and schema versioning | PostgreSQL + Python | M8 |
| 6 | **BI Dashboard & OLAP Layer** | Self-service dashboard builder — no SQL knowledge required | React/Vue + Chart.js/ECharts + FastAPI | M9 |
| 7 | **Data Quality Engine** | Automated null/duplicate/format/range/anomaly checks with quality scoring | Python (custom rules engine) | M10 |
| 8 | **Data Lineage** | Source-to-dashboard tracing via directed acyclic graph | Python + graph library | M10 |
| 9 | **Data Catalog** | Searchable inventory of all data assets with metadata and quality scores | Python + search index | M10 |
| 10 | **Security & Compliance** | RBAC, server-side column masking, anonymisation, audit logs, KVKK/GDPR | FastAPI middleware + PostgreSQL | M11 |

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend API | FastAPI + Uvicorn (Python 3.10+) |
| Data Warehouse | PostgreSQL 15 |
| CDC & Streaming | Debezium + Apache Kafka 3.7 + Apache Zookeeper |
| Connector Drivers | psycopg2 · PyMySQL · cx_Oracle · pyodbc · pymongo · cassandra-driver · pandas · pyarrow · requests · gql · confluent-kafka-python |
| BI Frontend | React / Vue 3 + Chart.js / Apache ECharts |
| Infrastructure | Docker Compose |
| Testing | pytest + Locust (load testing) |
| Code Quality | Black · flake8 · Prettier · ESLint |
| Version Control | GitHub — `main` / `develop` branch policy |

---

## Getting Started

### Prerequisites

- Docker Desktop ≥ 4.x installed and running
- Git
- Python 3.10+
- Node.js 18+ *(required for BI dashboard — M9 onward)*

### 1. Clone the repo

```bash
git clone https://github.com/jeylani-2526/subop.git
cd subop
```

### 2. Copy environment config

```bash
cp .env.example .env
# Edit .env with your local settings if needed
```

### 3. Start the full stack

```bash
docker compose up -d
```

Services will be available at:

| Service | URL |
|---------|-----|
| SUBOP API (FastAPI) | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| pgAdmin | http://localhost:5050 |
| Kafka UI | http://localhost:8080 |
| PostgreSQL | localhost:5432 |

> **Note:** The `subop-api` service is commented out in `docker-compose.yml` until M3 (CI/CD setup).
> Run `docker compose up -d postgres pgadmin zookeeper kafka kafka-ui` for the M1–M2 dev environment.

### 4. Run tests

```bash
# Python services
cd services/
pip install -r requirements-dev.txt
pytest -v

# BI Dashboard frontend (M9+)
cd services/bi-dashboard/frontend
npm install && npm test
```

---

## Project Structure

```
subop/
├── .github/
│   ├── workflows/
│   │   ├── ci.yml                  # Run lint + tests on push to develop / main
│   │   └── lint.yml                # Black + flake8 check on every PR
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.md
│   │   ├── feature_request.md
│   │   └── milestone_task.md
│   └── pull_request_template.md
├── docs/
│   ├── architecture/               # Architecture diagram (v1.1) + draw.io source
│   ├── milestones/                 # M1–M12 milestone documents and week plans
│   └── api/                        # FastAPI OpenAPI contract specs (M3+)
├── services/
│   ├── connectors/                 # Module 1  — Connector Framework
│   ├── abstraction/                # Module 2  — Database Abstraction Layer
│   ├── etl-engine/                 # Module 3  — ETL Engine
│   ├── cdc/                        # Module 4  — CDC / Real-Time Layer
│   ├── warehouse/                  # Module 5  — Metadata-Driven Data Warehouse
│   ├── bi-dashboard/
│   │   ├── frontend/               # Module 6a — React/Vue dashboard frontend
│   │   └── backend/                # Module 6b — FastAPI BI backend
│   ├── data-quality/               # Module 7  — Data Quality Engine
│   ├── lineage/                    # Module 8  — Data Lineage
│   ├── catalog/                    # Module 9  — Data Catalog
│   └── security/                   # Module 10 — Security & Compliance
├── infrastructure/
│   ├── docker/                     # Dockerfiles per service (M3+)
│   └── scripts/                    # Setup, seed, and utility scripts
├── data/
│   └── samples/                    # Sample CSV/JSON data for connector testing
├── docker-compose.yml              # Full local development stack
├── .env.example                    # Environment variable template
├── .gitignore
├── CONTRIBUTING.md
├── LICENSE
└── README.md
```

---

## Team

| Member | Role | Key Areas |
|--------|------|-----------|
| **Abdullah** | Project Lead · Data Engineering | Architecture, ETL engine, CDC, data warehouse, data quality, documentation, pilot testing |
| **Beyza** | BI & UI/UX Lead | BI dashboard, chart components, data catalog UI, lineage visualisation, user guide |
| **Omer** | Backend & Infrastructure | DB abstraction layer, connectors, FastAPI backend, Kafka/Debezium, security module, CI/CD |

**Advisor:** Weekly written progress report every Sunday.

---

## Roadmap

| # | Milestone | Dates | Owner | Status |
|---|-----------|-------|-------|--------|
| M1 | Project Understanding & Requirements | 11 May – 7 Jun 2026 | All | 🔄 In Progress |
| M2 | Research, Feasibility & Competitor Analysis | 8 Jun – 28 Jun 2026 | All | ⏳ Upcoming |
| M3 | System Architecture & Infrastructure Setup | 29 Jun – 19 Jul 2026 | Abdullah + Omer | ⏳ Upcoming |
| M4 | Database-Agnostic Abstraction Layer | 20 Jul – 9 Aug 2026 | Omer | ⏳ Upcoming |
| M5 | ETL Engine Core | 10 Aug – 6 Sep 2026 | Abdullah + Omer | ⏳ Upcoming |
| M6 | Connector Ecosystem Expansion | 7 Sep – 4 Oct 2026 | Omer | ⏳ Upcoming |
| M7 | CDC & Real-Time Streaming Module | 5 Oct – 2 Nov 2026 | Abdullah + Omer | ⏳ Upcoming |
| M8 | Metadata-Driven Data Warehouse | 3 Nov – 30 Nov 2026 | Abdullah + Omer | ⏳ Upcoming |
| M9 | BI Dashboard & OLAP Layer | 1 Dec – 28 Dec 2026 | Beyza | ⏳ Upcoming |
| M10 | Data Quality, Profiling, Lineage & Catalog | 29 Dec 2026 – 2 Feb 2027 | Abdullah + Beyza | ⏳ Upcoming |
| M11 | Security, Compliance & Full Integration | 3 Feb – 23 Mar 2027 | All | ⏳ Upcoming |
| M12 | Pilot Testing, Documentation & Final Delivery | 24 Mar – 11 May 2027 | All | ⏳ Upcoming |

See the full [Milestone documents](docs/milestones/) for week-by-week breakdowns.

---

## KPI Targets

These targets are agreed by the team and validated at the milestones indicated.

| KPI | Target | Owner | Validate By |
|-----|--------|-------|-------------|
| ETL speed | 1 million rows processed in under 5 minutes | Abdullah + Omer | Sep 2026 |
| CDC latency | End-to-end change capture under 30 seconds | Abdullah + Omer | Nov 2026 |
| Abstraction performance | ≥85% of native database query performance retained | Omer | Aug 2026 |
| DB migration code change | Zero code change required when switching the database engine | Omer | Oct 2026 |
| DW schema automation | Warehouse schema generated 80% faster than manual | Abdullah | Nov 2026 |
| Dashboard creation time | Non-technical user creates a dashboard in under 15 minutes | Beyza | Dec 2026 |
| Load test | 5 million rows handled without system failure | Omer | Mar 2027 |
| System uptime | 99.5%+ during pilot period | Omer | May 2027 |
| Pilot satisfaction | Average score of 4.0 / 5.0 or higher | Abdullah | May 2027 |

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full branching strategy, commit message conventions, PR process, and weekly workflow.

**Quick summary:**
- Branch from `develop`, never commit directly to `main`
- Branch naming: `feature/short-description` or `milestone/m3-architecture`
- Commit format: `type(scope): message` — e.g. `feat(connectors): add PostgreSQL psycopg2 driver`
- All PRs require at least one review before merging to `develop`

---

## License

MIT License — see [LICENSE](LICENSE).

---

*SUBOP Platform · Team: Abdullah · Beyza · Omer · Start: 11 May 2026 · Target: 11 May 2027*
