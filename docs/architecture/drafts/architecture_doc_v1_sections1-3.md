# SUBOP Architecture Document v1
**Sections 1–3 of 9 · Task: M3W8T2 · Owner: Abdullah · Draft date: 30 June 2026**
**Path (updated convention):** `docs/milestones/milestone 3/week 8/architecture_doc_v1.md`

*Status: Sections 1–3 complete (this document). Sections 4–6 to follow in M3W8T3. Sections 7–9 (deployment topology, security architecture, M3 conclusion) scheduled for Week 9.*

---

## Section 1 — Architecture Overview & Design Principles

SUBOP's architecture is built around one central bet: that the differences between database engines can be fully absorbed by a single abstraction layer, so that every other module — ETL, CDC, warehousing, BI, governance, security — can be written once and never know or care which database engine sits underneath it. This is not a simplification for the prototype; it is the platform's core value proposition, confirmed as the correct approach in the Feasibility Report (Section 2.2): the Adapter pattern was selected over SQLAlchemy ORM and a custom DSL specifically because it achieves zero-code-change database switching without introducing an ORM's session-management overhead or a DSL's compiler complexity that would be unrealistic for a 12-month, three-person team to build. Every other architectural decision in this document — the layer boundaries, the module interface contracts, the shared warehouse target for both batch and streaming paths — exists to protect that one bet.

The architecture is organized as seven layers with strict separation of concerns, wrapped end-to-end by a security layer rather than having security bolted on per-module. This reflects a lesson visible in the M2 competitor analysis: every evaluated tool (Talend, Informatica, NiFi, dbt, Power BI) treats security and compliance as a partial, tool-specific add-on rather than a platform-wide guarantee — SUBOP's differentiation depends on not repeating that pattern. Four constraints are treated as non-negotiable for the remainder of the project; any future design decision that would violate one of these must be escalated and reconsidered rather than quietly worked around:

1. **Zero code change when switching the underlying database engine.** A pipeline written against PostgreSQL must run against MySQL or MSSQL without modification. This is SUBOP's primary KPI (validated Oct 2026 and Mar 2027 per the roadmap) and the direct justification for the Adapter pattern.
2. **All modules communicate through defined interfaces — no direct cross-module calls.** The ETL engine never reaches into the warehouse module's internals; the BI layer never queries a connector directly. This is what makes the module interface contracts in Section 4 binding rather than advisory.
3. **CDC and batch ETL share the same warehouse target.** Real-time change events and scheduled batch loads both land in the same PostgreSQL 15 warehouse through the same schema — there is no separate "streaming store" to reconcile later.
4. **The security layer wraps the entire platform.** RBAC, column masking, and audit logging apply uniformly across every layer rather than being implemented per-module, so that KVKK/GDPR compliance (M11) is a platform property, not a patchwork of module-level exceptions.

---

## Section 2 — System Layer Definitions

Seven layers, ordered from data ingress to user-facing output, with two cross-cutting layers (Governance, Security) that apply horizontally across the other five.

### 2.1 Data Source Layer
**Purpose:** Provide standardized access points for every supported connector type feeding the platform.
**Inputs:** Raw connections to Oracle, PostgreSQL, MySQL, MSSQL, MongoDB, Cassandra, CSV/Excel, Parquet, REST APIs, GraphQL, Kafka (per `supported_sources_v1.md`).
**Outputs:** A normalized connection object handed to the Abstraction & ETL Layer.
**Confirmed technology:** psycopg2 (PostgreSQL), PyMySQL (MySQL), pyodbc (MSSQL) — all three already implemented as working prototypes per the M2 Feasibility Report (Module 1: Connector Framework, rated **HIGH**).
**Open item:** Per the five open architecture questions (Section 1 of the M3 scope note), non-SQL sources (Kafka, REST, MongoDB) will require interface extensions beyond this layer's current `connect/disconnect/execute_query/execute_write/health_check` contract — to be resolved in Section 4.

### 2.2 Abstraction & ETL Layer
**Purpose:** Hide database-specific SQL dialects and connection semantics behind the `ConnectorBase` interface; execute extract-transform-load pipelines against that interface.
**Inputs:** Normalized connections from the Data Source Layer; pipeline definitions (source, transformations, target).
**Outputs:** Transformed row batches delivered to the Warehouse Layer.
**Confirmed technology:** Adapter pattern (`ConnectorBase` abstract class with concrete `PostgreSQLConnector`, `MySQLConnector`, `MSSQLConnector` implementations). Rated **MEDIUM-HIGH** feasibility — the only module rated below HIGH among the SQL-based components, because dialect normalization (TOP N vs. LIMIT N, IDENTITY vs. SERIAL, NVARCHAR vs. TEXT) has no external template to copy; SUBOP must design it from first principles.
**Performance target:** 1M rows processed in under 5 minutes (KPI, validated Sep 2026).

### 2.3 CDC & Streaming Layer
**Purpose:** Capture INSERT/UPDATE/DELETE changes from source databases in near-real-time and deliver them to the same warehouse target used by batch ETL.
**Inputs:** PostgreSQL WAL, MySQL binlog.
**Outputs:** Normalized change events on Kafka topics, consumed by the ETL Engine in streaming mode.
**Confirmed technology:** Debezium + Kafka. Rated **HIGH WITH RISK** — the technical pattern is externally validated (the competitor analysis found NiFi's own documentation recommends this exact Debezium+Kafka combination, and Informatica's PowerExchange CDC uses the same underlying WAL/binlog read mechanism), but the risk is internal: Omer's Kafka/Debezium knowledge gap is the single highest-risk item in the project's risk register, requiring a structured 4–6 week study plan starting this week.
**Performance target:** End-to-end latency under 30 seconds (KPI, validated Nov 2026).

### 2.4 Warehouse Layer
**Purpose:** Metadata-driven storage that automatically generates and versions fact/dimension tables and SCD logic from source metadata, without manual SQL authorship.
**Inputs:** Transformed batches (from ETL) and streamed change events (from CDC) — same target for both.
**Outputs:** Queryable star/snowflake schema consumed directly by the Analytics Layer.
**Confirmed technology:** PostgreSQL 15. **ClickHouse has been formally removed from the architecture** — the BI layer queries PostgreSQL directly rather than through a separate OLAP store. This is rated **MEDIUM** feasibility, the most novel module in the platform: no evaluated competitor performs automatic metadata-to-schema generation, so this is a genuine design problem rather than a known pattern to adapt.
**Open item for Section 4/Week 9:** the metadata representation format (JSON schema? annotated SQL DDL? YAML?) is not yet decided and must be resolved before M8 (November 2026) begins.

### 2.5 Analytics Layer
**Purpose:** Self-service BI dashboard builder and OLAP-style views for non-technical users, querying the warehouse directly.
**Inputs:** PostgreSQL warehouse schema.
**Outputs:** Rendered dashboards, charts, and exported reports (PDF/Excel) to the end user.
**Confirmed technology:** React 18 + Tailwind CSS (frontend), Chart.js and Apache ECharts (charting) — rated **HIGH** feasibility. The shell-first build strategy (page shells built M5–M8, data wiring in M9) is already underway this week via the frontend project setup (M3W8T5–T7).
**Performance target:** Dashboard creation in under 15 minutes by a user with no SQL knowledge (KPI, validated Dec 2026).

### 2.6 Governance Layer *(cross-cutting)*
**Purpose:** Data Quality, Lineage, and Catalog services that apply across every other layer rather than living inside any single one.
**Inputs:** Execution metadata and row-level data from every pipeline run (ETL and CDC).
**Outputs:** Quality scores per dataset, lineage graphs (source → transform → warehouse → dashboard), and a searchable asset catalog.
**Confirmed technology:** pandas + scikit-learn Isolation Forest (quality/anomaly detection, Data Quality rated **HIGH**), D3.js or vis-network for the Lineage Explorer graph rendering (Lineage & Catalog rated **MEDIUM** — the graph rendering complexity is the main open risk), PostgreSQL full-text search for the Catalog.

### 2.7 Security Layer *(cross-cutting, wraps all layers)*
**Purpose:** RBAC, column-level masking, anonymization, and audit logging applied uniformly across the entire platform — not per-module.
**Inputs:** Every user and system action across all six other layers.
**Outputs:** Access decisions (allow/deny/mask), audit log entries, KVKK/GDPR compliance evidence.
**Confirmed technology:** JWT + FastAPI middleware for RBAC — rated **MEDIUM-HIGH** feasibility. The main open item is not technical but documentary: mapping each KVKK article to a specific SUBOP module/process and confirming VERBİS registration requirements, using the 8–10 item compliance checklist from the Week 6 KVKK/GDPR research as direct input.

---

## Section 3 — Technology Stack Confirmation

Every entry below is traceable to a specific M2 document — this table is a *lock*, not a proposal. Any change after this point should be treated as a scope change requiring team sign-off, not a routine implementation detail.

| Component | Selected Technology | Rationale | Confirming M2 Document |
|---|---|---|---|
| **Language runtime** | Python 3.11 | Matches connector prototypes already built (psycopg2/PyMySQL); mature ecosystem for ETL, ML (Isolation Forest), and API development | `backend_infrastructure_notes_v1.md` (M1), carried forward through M2 connector work |
| **API framework** | FastAPI | Async-capable (relevant to Open Question #1 — sync vs. async connector execution), strong typing via Pydantic, natural fit for the module interface contracts in Section 4 | M1 technical requirements; confirmed as target in `connector_summary_m4_prep_v1.md` |
| **DB abstraction pattern** | Adapter pattern (`ConnectorBase`) | SQLAlchemy ORM and custom DSL formally evaluated and rejected | Feasibility Report Final v1, §2.2 (Omer's recommendation) |
| **Connector drivers** | psycopg2 (PostgreSQL), PyMySQL (MySQL), pyodbc (MSSQL) | Already implemented and tested (10 passing pytest tests across Postgres + MySQL; MSSQL foundation in progress this week) | `postgres_connector.py`, `mysql_connector.py` (committed); `mssql_connector_research_v1.md` |
| **CDC / streaming** | Debezium + Kafka | Externally validated pattern — confirmed independently by NiFi's own architecture recommendations and Informatica's PowerExchange CDC mechanism | Feasibility Report Final v1, Module 4 discussion; Competitor Analysis Report |
| **Frontend stack** | React 18 + Tailwind CSS (Vite + TypeScript) | Confirmed in UI Shell Architecture Plan; matches Design System v1 tokens; already scaffolded this week (M3W8T5) | `ui_shell_architecture_v1.md` (Week 6), `design_system_v1.docx` (Week 7) |
| **Warehouse target** | PostgreSQL 15 | ClickHouse formally removed — BI layer queries PostgreSQL directly, avoiding a second store to keep in sync with CDC writes | Architecture decision, Section 2.4 above; consistent with locked project decisions |
| **Testing framework** | pytest | Already in use — 10 passing connector tests across two suites sharing one fixture set | `conftest.py`, `test_postgres_connector.py`, `test_mysql_connector.py` (in progress) |
| **Containerization** | Docker + Docker Compose | Shared dev environment established since M1 (postgres, pgadmin, zookeeper, kafka services); MSSQL service added this week | `docker-compose.yml` (M1, updated M3W8T9) |
| **CI/CD** | GitHub Actions | Pipeline already exists (`ci.yml`, `lint.yml` on `main`) — lint (Black + flake8) and pytest against a Postgres service container; being extended this week to cover MySQL and MSSQL | Verified directly on GitHub during M3W8T1 audit |

---

**Next:** Sections 4–6 (Module Interface Definitions, Inter-Module Data Flow, API Contract Sketches) — M3W8T3.
