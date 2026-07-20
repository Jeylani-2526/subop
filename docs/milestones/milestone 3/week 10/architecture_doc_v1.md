# SUBOP Architecture Document v1
**Final consolidated version — Sections 1–9 · Owner: Abdullah**
**Path:** `docs/milestones/milestone-3/week-10/architecture_doc_v1.md`



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
**Resolved in Section 4:** non-SQL sources (Kafka, REST, MongoDB) require interface extensions beyond this layer's base `connect/disconnect/execute_query/execute_write/health_check` contract — resolved via the optional-mixin pattern (Section 3.5, Question 2; Section 9.2).

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
**Open item — carried into M4/M5 (see Section 9.3):** the metadata representation format (JSON schema? annotated SQL DDL? YAML?) is not yet decided. This is the same gap Section 5.2 identifies as the CDC schema-drift risk, and it is *not* resolved by this document — see Section 9.3 for the explicit M4/M5 carry-forward statement.

### 2.5 Analytics Layer
**Purpose:** Self-service BI dashboard builder and OLAP-style views for non-technical users, querying the warehouse directly.
**Inputs:** PostgreSQL warehouse schema.
**Outputs:** Rendered dashboards, charts, and exported reports (PDF/Excel) to the end user.
**Confirmed technology:** React 18 + Tailwind CSS (frontend), Chart.js and Apache ECharts (charting) — rated **HIGH** feasibility. The shell-first build strategy (page shells built M5–M8, data wiring in M9) is already underway via the frontend project setup (M3W8T5–T7, extended through M3W9T5–T8 and M3W10T5–T7).
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
**Confirmed technology:** JWT + FastAPI middleware for RBAC — rated **MEDIUM-HIGH** feasibility. The main open item is not technical but documentary: mapping each KVKK article to a specific SUBOP module/process and confirming VERBİS registration requirements, using the 8–10 item compliance checklist from the Week 6 KVKK/GDPR research as direct input. (Full detail in Section 8.)

---

## Section 3 — Technology Stack Confirmation

Every entry below is traceable to a specific M2 document — this table is a *lock*, not a proposal. Any change after this point should be treated as a scope change requiring team sign-off, not a routine implementation detail.

| Component | Selected Technology | Rationale | Confirming M2 Document |
|---|---|---|---|
| **Language runtime** | Python 3.11 | Matches connector prototypes already built (psycopg2/PyMySQL); mature ecosystem for ETL, ML (Isolation Forest), and API development | `backend_infrastructure_notes_v1.md` (M1), carried forward through M2 connector work |
| **API framework** | FastAPI | Async-capable (relevant to Open Question #1 — sync vs. async connector execution), strong typing via Pydantic, natural fit for the module interface contracts in Section 4 | M1 technical requirements; confirmed as target in `connector_summary_m4_prep_v1.md` |
| **DB abstraction pattern** | Adapter pattern (`ConnectorBase`) | SQLAlchemy ORM and custom DSL formally evaluated and rejected | Feasibility Report Final v1, §2.2 (Omer's recommendation) |
| **Connector drivers** | psycopg2 (PostgreSQL), PyMySQL (MySQL), pyodbc (MSSQL) | Implemented and tested (15 passing pytest tests across Postgres + MySQL + MSSQL as of Week 9) | `postgres_connector.py`, `mysql_connector.py`, `mssql_connector.py` (all committed) |
| **CDC / streaming** | Debezium + Kafka | Externally validated pattern — confirmed independently by NiFi's own architecture recommendations and Informatica's PowerExchange CDC mechanism | Feasibility Report Final v1, Module 4 discussion; Competitor Analysis Report |
| **Frontend stack** | React 18 + Tailwind CSS (Vite + TypeScript) | Confirmed in UI Shell Architecture Plan; matches Design System v1 tokens; scaffolded M3W8T5, extended through M3W10T5–T7 | `ui_shell_architecture_v1.md` (Week 6), `design_system_v1.docx` (Week 7) |
| **Warehouse target** | PostgreSQL 15 | ClickHouse formally removed — BI layer queries PostgreSQL directly, avoiding a second store to keep in sync with CDC writes | Architecture decision, Section 2.4 above; consistent with locked project decisions |
| **Testing framework** | pytest | 15 passing connector tests (5 Postgres + 5 MySQL + 5 MSSQL) sharing one fixture set | `conftest.py`, `test_postgres_connector.py`, `test_mysql_connector.py`, `test_mssql_connector.py` |
| **Containerization** | Docker + Docker Compose | Shared dev environment established since M1 (postgres, pgadmin, zookeeper, kafka services); MSSQL service added M3W8T9 | `docker-compose.yml` (M1, updated M3W8T9) |
| **CI/CD** | GitHub Actions | `ci.yml` / `lint.yml` on `main` — lint (Black + flake8) and pytest against all three service containers | Verified directly on GitHub during M3W8T1 audit; extended M3W9T10 |

---

## 3.5 — Resolutions to the Five Open Architecture Questions

*(Placed here, ahead of Section 4, because the module interface table below depends on these decisions. Proposed at the Wednesday 2 July sync; formally locked in Section 9.2.)*

| # | Open Question (from `connector_summary_m4_prep_v1.md`) | Resolution |
|---|---|---|
| 1 | Synchronous vs. asynchronous connector execution | `ConnectorBase` (SQL connectors) stays **synchronous**. A separate `StreamingConnectorBase` interface handles Kafka/REST asynchronously. FastAPI wraps sync connector calls in a threadpool executor. |
| 2 | Shared interface vs. connector-specific extensions | **Interface segregation.** `ConnectorBase`'s 5 methods (`connect`, `disconnect`, `execute_query`, `execute_write`, `health_check`) remain mandatory for all connectors. Optional mixins add capability only where needed: `StreamingConnector.subscribe()`, `PaginatedConnector.fetch_page()`, `DocumentConnector.find_documents()`. |
| 3 | Non-relational sources (MongoDB) vs. a SQL-oriented abstraction | MongoDB implements `DocumentConnector`, but its query method still returns the same `List[Dict[str, Any]]` shape as every SQL connector — the document/relational difference is absorbed internally and never leaks to the ETL Engine. |
| 4 | Connector-specific features: individual implementation vs. shared components | **Shared abstraction components** (the mixins above), not per-connector reinvention. Pagination, subscription, and document-query logic are each implemented once and reused. |
| 5 | Common result format and error-handling strategy | All connectors return `List[Dict[str, Any]]` from reads and a row-count `int` from writes. All errors are raised as `ConnectorError` subclasses — `ConnectionError`, `QueryError`, `WriteError` — carrying `{error_code, message, connector_type, retryable: bool}`. The `retryable` flag is the direct input to the recoverable-vs-fatal classification in Section 5. |

---

## Section 4 — Module Interface Definitions

For all 10 SUBOP modules. This table is the binding contract: no module may depend on another module's internal implementation beyond what's listed here.

| Module | Inputs Consumed | Outputs Produced | Primary Protocol |
|---|---|---|---|
| **1. Connector Framework** | Connection config (JSON: host/port/credentials) from Admin API; encrypted credentials from Security Layer | Normalized connection handle; row batches (`List[Dict]`) to Abstraction Layer | Python function call (in-process); Kafka subscription for streaming-capable connectors |
| **2. Database Abstraction Layer** | Query/write requests (`execute_query(sql, params)`) from ETL Engine | Normalized result sets (`List[Dict]`) or write confirmation (row count) | Python function call (in-process, wraps Connector Framework) |
| **3. ETL Engine** | Pipeline definitions (JSON pipeline DSL) via API; batches from Abstraction Layer; streaming events from CDC Layer | Transformed row batches to Warehouse Layer; execution metadata to Governance modules (Quality, Lineage) | REST API (trigger/status), Kafka consumer (streaming mode), Python function call (batch mode, internal) |
| **4. CDC / Real-Time Streaming** | PostgreSQL WAL / MySQL binlog via Debezium | Normalized change events (JSON: `{op, table, before, after, ts_ms}`) | Kafka topic: `cdc.<source>.<table>` |
| **5. Metadata-Driven Data Warehouse** | Transformed batches (batch) and change events (streaming) from ETL Engine; source metadata definitions from Connector Framework schema introspection | Star/snowflake schema tables in PostgreSQL 15 | SQL write (direct PostgreSQL connection); Python function call for schema generation |
| **6. BI Dashboard & OLAP** | Warehouse schema + data (read-only SQL); dashboard config (JSON) from frontend | Rendered chart data (JSON); exported reports (PDF/Excel) | REST API |
| **7. Data Quality** | Row batches from ETL Engine at execution checkpoints; rule definitions (JSON) | Quality score per dataset (JSON); anomaly alerts | Python function call (in-process pipeline hook) + REST API (score/violation queries) |
| **8. Data Lineage** | Pipeline execution metadata (source table, transform steps, target table) from ETL Engine | Lineage graph (nodes/edges JSON) | Python function call (metadata write, in-process) + REST API (graph queries) |
| **9. Data Catalog** | Table/column metadata from Warehouse; quality scores from Data Quality; lineage links from Lineage module | Searchable asset index (PostgreSQL full-text search) | SQL query (internal) + REST API (search) |
| **10. Security & Compliance** | Every incoming API request (JWT) across all modules; audit-relevant actions from any module | Access decision (allow/deny/mask) returned inline; audit log entries | FastAPI middleware (wraps every REST endpoint) + Python function call (e.g. masking inside BI query execution) |

---

## Section 5 — Inter-Module Data Flow

### 5.1 Batch ETL Path

**Connector Framework → Abstraction Layer → ETL Engine → Warehouse → BI Dashboard**, with Governance checkpoints at each stage.

**Worked example — nightly sync of a `customers` table from PostgreSQL:**
1. **Connector Framework** opens a connection using `PostgreSQLConnector`, confirms health via `health_check()`.
2. **Abstraction Layer** issues `execute_query("SELECT * FROM customers WHERE updated_at > :last_sync")` — dialect-specific syntax (e.g., `LIMIT` vs `TOP`) is resolved here, invisibly to the ETL Engine.
3. **ETL Engine** receives the row batch, applies configured transformations (e.g., PII masking flag, currency normalization), and calls **Data Quality** as an in-process hook before proceeding — a null/duplicate/format violation here can halt the pipeline (fatal) or quarantine the offending rows (recoverable), depending on rule severity.
4. **Warehouse Layer** receives the transformed batch and performs an upsert against the `dim_customer` table, applying SCD Type 2 logic if tracked fields changed.
5. **Lineage** records the run (`customers` table → transform step → `dim_customer`) as part of step 4, not as an afterthought.
6. **BI Dashboard** queries `dim_customer` directly on next dashboard load — no separate sync step required, since the warehouse is the single source both batch and CDC write to.

**Stateless vs. stateful:**
- **Stateless:** Abstraction Layer, BI Dashboard (queries on demand, no session state held between requests)
- **Stateful:** ETL Engine (holds execution state and checkpoint offsets *during* a run, stateless between runs), Warehouse (persistent by definition), Connector Framework (maintains a connection pool, though each query is independent)

**Recoverable vs. fatal failures:**
| Failure | Classification | Handling |
|---|---|---|
| Connector timeout | Recoverable | Retry with exponential backoff (uses the `retryable` flag from `ConnectorError`) |
| SQL dialect translation error | Fatal (for that pipeline run only) | Halt the run, do not corrupt other pipelines |
| Row-level transformation error | Recoverable | Quarantine the row, continue the batch |
| Warehouse constraint violation | Recoverable | Retry via upsert logic |
| Warehouse disk full | Fatal | Escalate — no automatic recovery path |

### 5.2 CDC Streaming Path

**Source DB WAL/binlog → Debezium → Kafka Topic → ETL Engine (streaming mode) → Warehouse**

**Worked example — an `UPDATE orders SET status='shipped'` in PostgreSQL:**
| Step | Time | Latency Measurement Point |
|---|---|---|
| t0 | Transaction commits, written to WAL | Start of latency budget |
| t1 | Debezium reads the WAL entry | t1 − t0 = capture latency |
| t2 | Event published to Kafka topic `cdc.postgres.orders` | t2 − t1 = publish latency |
| t3 | ETL Engine's streaming consumer picks up the event | t3 − t2 = consumer lag |
| t4 | Warehouse write (upsert) completes | t4 − t0 = **total end-to-end latency — must be under 30 seconds (KPI)** |

Instrumenting all four intervals (not just the total) is what lets us diagnose *which* hop is responsible if the 30-second target is missed — this is a concrete instrumentation requirement for M7, not just a monitoring nice-to-have.

**Stateless vs. stateful:**
- **Stateful throughout:** Debezium (tracks WAL/binlog offset position), Kafka (durable log with consumer group offsets), ETL Engine's streaming consumer (tracks its own consumption offset)
- **Idempotent by design:** Warehouse writes use upsert keyed by primary key + operation timestamp, because Kafka's at-least-once delivery guarantee means duplicate events are expected, not exceptional

**Recoverable vs. fatal failures:**
| Failure | Classification | Handling |
|---|---|---|
| Debezium connector crash | Recoverable | Resumes from last committed WAL/binlog offset |
| Kafka broker unavailable | Recoverable (if replicated) | Consumer retries; no data loss if replication factor ≥ 2 |
| Duplicate event delivery | Not a failure | Absorbed by idempotent upsert |
| Source table schema drift (e.g., column added/renamed) | **Fatal — flagged open risk** | No automatic schema evolution handling designed yet; requires manual intervention. This connects to the still-open metadata-format decision in Section 2.4 and is carried forward explicitly in Section 9.3 as unresolved M4/M5 scope — not silently deferred. |

---

## Section 6 — API Contract Sketches

FastAPI endpoint groups for all 10 modules. These are specific enough to unblock M5 planning without over-specifying implementation (request/response bodies are deferred to M5).

**1. Connector Framework** — base `/api/connectors`
- `GET /api/connectors/` — list configured connectors
- `POST /api/connectors/` — register a new connector
- `GET /api/connectors/{id}/health` — run health check
- `DELETE /api/connectors/{id}` — remove connector

**2. Database Abstraction Layer** — base `/api/query`
- `POST /api/query/execute` — execute a query through the abstraction layer (admin/debug use, RBAC-gated)
- `GET /api/query/dialects` — list supported SQL dialect mappings
- `GET /api/query/{connector_id}/schema` — introspect source schema

**3. ETL Engine** — base `/api/pipelines`
- `GET /api/pipelines/` — list pipeline definitions
- `POST /api/pipelines/` — create a new pipeline
- `POST /api/pipelines/{id}/run` — trigger a batch run
- `GET /api/pipelines/{id}/runs/{run_id}` — get run status and logs

**4. CDC / Real-Time Streaming** — base `/api/cdc`
- `GET /api/cdc/connectors` — list active Debezium connectors
- `POST /api/cdc/connectors` — register a new CDC source
- `GET /api/cdc/connectors/{id}/status` — snapshot/streaming status + current latency (the four measurement points from Section 5.2)
- `DELETE /api/cdc/connectors/{id}` — stop CDC capture

**5. Metadata-Driven Data Warehouse** — base `/api/warehouse`
- `GET /api/warehouse/schemas` — list generated fact/dimension schemas
- `POST /api/warehouse/schemas/generate` — generate a schema from a metadata definition
- `GET /api/warehouse/schemas/{id}/versions` — schema version history (SCD tracking)

**6. BI Dashboard & OLAP** — base `/api/bi`
- `GET /api/bi/dashboards` — list dashboards
- `POST /api/bi/dashboards` — create a dashboard
- `POST /api/bi/query` — run an ad-hoc OLAP query against the warehouse
- `GET /api/bi/dashboards/{id}/export` — export as PDF/Excel

**7. Data Quality** — base `/api/quality`
- `GET /api/quality/{dataset_id}/score` — current quality score
- `POST /api/quality/rules` — define a new quality rule
- `GET /api/quality/{dataset_id}/violations` — list rule violations

**8. Data Lineage** — base `/api/lineage`
- `GET /api/lineage/{asset_id}` — full upstream/downstream lineage graph
- `GET /api/lineage/{asset_id}/impact` — impact analysis (what breaks if this asset changes)

**9. Data Catalog** — base `/api/catalog`
- `GET /api/catalog/search?q=` — search assets
- `GET /api/catalog/{asset_id}` — asset detail (columns, sample values, quality score, owner)

**10. Security & Compliance** — base `/api/auth`, `/api/audit`
- `POST /api/auth/login` — authenticate, issue JWT
- `GET /api/auth/roles` — list RBAC roles/permissions
- `GET /api/audit/logs` — query the audit log (admin only)
- `POST /api/admin/masking-rules` — define a column-level masking rule

---

## Section 7 — Deployment Topology

### 7.1 Docker Container Network Diagram

The full SUBOP development environment runs as a single Docker Compose stack, all services attached to one bridge network (`subop_network`). The network diagram below shows every service currently defined in `docker-compose.yml`, drawn and exported per Omer's confirmed port mappings.

**Diagram files (embedded/attached):**
- `deployment_topology_diagram.drawio` — editable source (open in diagrams.net / draw.io)

![Deployment Topology Diagram](deployment_topology_diagram.png)

**Reachability boundaries:**

| Service | Port Mapping | Reachability | Notes |
|---|---|---|---|
| `postgres` (15) | 5432:5432 | Application-layer reachable (internal) | Warehouse target; also the BI Dashboard's only dependency |
| `mysql` (8) | 3306:3306 | Application-layer reachable (internal) | Source connector target |
| `mssql` (2022-latest) | 1433:1433 | Application-layer reachable (internal) | Source connector target; heaviest single-container memory footprint of the three databases |
| `kafka` | 9092:9092 | Application-layer reachable (internal) | CDC event bus; depends on `zookeeper` at startup |
| `zookeeper` | 2181:2181 | Internal-only — not reachable by application code directly | Exists solely to coordinate Kafka; no SUBOP module calls it directly |
| `pgadmin` | 8080:80 (mapped to host) | Host/dev-machine reachable only | Developer GUI tooling; not a runtime dependency of any SUBOP module and is not part of the application-layer trust boundary |

This distinction is noted here as a deployment-level trust-boundary observation rather than an application-security one: `pgadmin` sits outside the application trust boundary and is a candidate for exclusion from any pilot/production deployment entirely, since it exists for local developer convenience rather than a platform function. (Section 8's RBAC and audit model governs application-level access, not infrastructure tooling exclusions — pgadmin's removal is tracked as an M4 infrastructure decision rather than a Section 8 topic.)

### 7.2 Service Dependency Table

| Consuming Module | Depends On | Failure Impact if Dependency Is Unavailable |
|---|---|---|
| ETL Engine | `postgres`, `mysql`, `mssql`, `kafka` | Batch runs against the affected source fail (recoverable — retried per Section 5.1's connector-timeout classification); CDC-fed runs stall if `kafka` is down |
| Connector Framework | Whichever of `postgres` / `mysql` / `mssql` is configured for that connector instance | Connection attempts fail `health_check()`; classified per `ConnectorError.retryable` (Section 3.5, Question 5) |
| CDC / Real-Time Streaming | `kafka` (which itself depends on `zookeeper`) + the source database's WAL/binlog | If `zookeeper` is down, `kafka` cannot accept broker connections, which stalls the entire CDC path — this is the single most fragile dependency chain in the stack |
| BI Dashboard & OLAP | `postgres` only | Dashboards fail to load; no dependency on `mysql`, `mssql`, or `kafka` since the warehouse is the sole read target (Section 2.4/2.5) |
| Governance Layer (Quality, Lineage, Catalog) | `postgres` only | Same isolation as BI Dashboard — governance metadata lives in the same warehouse |
| Security & Compliance | None of the above directly; wraps every module as middleware (Section 2.7) | Not affected by any single service outage; addressed fully in Section 8 |

**Observation for M4 planning:** every module except CDC has exactly one direct-dependency failure mode. CDC is the outlier — its two-hop dependency (`kafka` → `zookeeper`) is the only place in this topology where a single container failure (`zookeeper`) can silently stall a module (`kafka`) that three other things depend on. This is worth carrying into M7 as an explicit monitoring requirement (alert on `zookeeper` health specifically, not just `kafka`'s).

### 7.3 Estimated Container Resource Requirements

Estimates below are planning figures confirmed against Omer's Week 8 setup and standard image guidance (e.g., Microsoft's documented minimum for MSSQL Developer edition); they are not yet backed by measured `docker stats` output under production-representative load, and should be revisited once M4 connector work generates realistic traffic.

| Service | Single-Node Dev (per container) | Multi-Node Pilot (per container) | Rationale |
|---|---|---|---|
| `postgres` | 1 vCPU / 1 GB RAM | 2 vCPU / 4 GB RAM | Warehouse target carries the heaviest read load in pilot (BI + Governance both query it exclusively) |
| `mysql` | 1 vCPU / 1 GB RAM | 2 vCPU / 4 GB RAM | Source-side only; scales with connector test/pilot traffic |
| `mssql` | 2 vCPU / 2 GB RAM | 2 vCPU / 4 GB RAM | Microsoft's documented minimum for Developer edition is 2 GB RAM; this is a floor, not a target |
| `kafka` | 1 vCPU / 1 GB RAM | 2 vCPU / 2 GB RAM | JVM heap needs headroom beyond the container floor once CDC throughput increases in M7 |
| `zookeeper` | 0.5 vCPU / 256 MB RAM | 1 vCPU / 512 MB RAM | Lightweight coordination role only |
| `pgadmin` | 0.25 vCPU / 256 MB RAM | 0.25 vCPU / 256 MB RAM | Dev tooling only — intentionally not scaled for pilot; candidate for exclusion per 7.1 |
| **Total (dev host)** | **~5.75 vCPU / ~5.5 GB RAM** | — | Comfortably runs on a standard developer laptop (8 vCPU / 16 GB class machine) |
| **Total (pilot, excl. pgadmin)** | — | **~9.25 vCPU / ~14.5 GB RAM** | Recommended split across at least two nodes: databases (postgres/mysql/mssql) on one node, Kafka/Zookeeper + application layer on a second, to isolate the CDC path's failure domain from the connector-heavy database node |

**Single-node dev vs. multi-node pilot — the key difference isn't just headroom.** The dev topology co-locates everything deliberately, since local development doesn't need failure isolation. The pilot split above exists specifically so that a database-side issue (e.g., an MSSQL connector under heavy load) doesn't compete for CPU with the CDC path, which has a hard 30-second end-to-end latency KPI (Section 5.2) that a resource-starved `kafka`/`zookeeper` pair would jeopardize first.

---

## Section 8 — Security Architecture

### 8.1 RBAC Model — Permission Matrix

The four SUBOP user roles were established in Milestone 1 (`user_requirements_v1.docx`, M1W2T4; `user_role_matrix.md`, M1W2T11): **Data Engineer**, **BI Analyst**, **Platform Admin**, **Viewer**. The matrix below extends that page-level access matrix down to module-level permissions, since Section 8 needs to bind roles to the 10 SUBOP modules defined in Section 4, not just to UI pages.

**Permission levels:** `Admin` (full control — create, edit, delete, configure) · `Write` (create/edit within the module, no delete/configure) · `Read` (view only) · `None` (no access; requests rejected by RBAC middleware with a 403)

| Module | Data Engineer | BI Analyst | Platform Admin | Viewer |
|---|---|---|---|---|
| 1. Connector Framework | Write | None | Admin | None |
| 2. Database Abstraction Layer | Write | None | Admin | None |
| 3. ETL Engine | Write | None | Admin | None |
| 4. CDC / Real-Time Streaming | Write | None | Admin | None |
| 5. Metadata-Driven Data Warehouse | Write | Read | Admin | None |
| 6. BI Dashboard & OLAP | Read | Write | Admin | Read *(published dashboards only)* |
| 7. Data Quality | Write | Read | Admin | Read *(score summaries only)* |
| 8. Data Lineage | Read | Read | Admin | None |
| 9. Data Catalog | Read | Read | Admin | Read |
| 10. Security & Compliance | None | None | Admin | None |

**Rationale for the notable rows:**
- **BI Analyst gets `None` on Connector Framework, Abstraction Layer, ETL Engine, and CDC** — directly enforces the Milestone 1 constraint that the BI Analyst "cannot configure ETL pipelines" (M1W2T11). This is a hard boundary, not a UI-level hint: the RBAC middleware rejects these calls at the API layer regardless of what the frontend shows.
- **Data Engineer gets `Write`, not `Admin`, everywhere in the pipeline path** — Data Engineers configure and run their own pipelines and connectors but cannot delete another engineer's connector configuration or reassign RBAC roles; that escalation path belongs to Platform Admin only.
- **Viewer's `Read` on BI Dashboard and Data Quality is explicitly scoped** ("published dashboards" / "score summaries") per the Milestone 1 definition — a Viewer cannot open the BI Report Builder itself (that surface is gated to BI Analyst `Write` and above) or see per-rule quality violation detail, only the aggregate score.
- **Data Catalog is `Read` for every non-admin role** — consistent with the Week 2 dashboard pages list marking Data Catalog as accessible to all roles; it is deliberately the most open module short of Admin, since browsing metadata (not the underlying data) carries low risk.
- **Security & Compliance is `None` for every role except Platform Admin** — user management, RBAC configuration, and audit log visibility are Platform Admin's defining responsibility (M1W2T4) and are not partially delegated to any other role.

### 8.2 Authentication Flow

**Login and JWT issuance:**
1. User submits credentials to `POST /api/auth/login` (Section 6, Module 10).
2. On success, the Security & Compliance module issues two tokens: a short-lived **access token** (JWT, 15-minute expiry) carrying the user's `role` claim, and a longer-lived **refresh token** (7-day expiry), following the sync/threadpool execution model locked in Section 3.5 (Question 1).
3. The access token is the sole artifact RBAC middleware inspects on every subsequent request — the `role` claim inside it is what the permission matrix in §8.1 is checked against.

**Token refresh:**
- The refresh token is stored in an `httpOnly`, `Secure` cookie — never in `localStorage` or JavaScript-accessible storage, to limit exposure if the frontend is compromised by XSS.
- When an access token expires, the frontend calls `POST /api/auth/refresh`; the server validates the refresh token, issues a new access token, and **rotates** the refresh token (invalidating the old one) to limit the damage window if a refresh token is ever intercepted.
- If the refresh token itself is expired or invalid, the user is redirected to `/login` — this is the same `PrivateRoute` guard already scaffolded in Beyza's Week 8 routing setup (M3W8T5), not a new component.

**How AppShell attaches bearer tokens:**
- The access token is held in memory inside a React auth context that wraps `AppShell` (not in `localStorage`, for the same XSS-exposure reason as the refresh token).
- A shared API client (a single configured `fetch`/`axios` instance used by every page component) attaches `Authorization: Bearer <token>` to every outgoing request via a request interceptor — individual pages never handle token attachment themselves, which keeps this concern in one place now that all eight page shells are in place (M3W10T5–T6).
- On a `401 Unauthorized` response, the client interceptor attempts one silent token refresh and retries the original request once; a second `401` after that triggers the redirect-to-`/login` path described above, rather than looping indefinitely.

### 8.3 Audit Log Design

**Logged actions** (union of the task's baseline list and the KVKK/GDPR checklist's audit requirements, C08/C10):
- Login attempts (success and failure)
- Connector configuration changes (create, update, delete)
- Dashboard exports
- Permission changes (role assignment or modification by Platform Admin)
- Data subject rights requests (access, rectification, erasure, restriction, objection, portability export — C05–C07)
- Bulk or anomalous data access on any table flagged `personal_data: true` (the breach-detection trigger for C08)

**Log schema:**

| Field | Type | Notes |
|---|---|---|
| `timestamp` | ISO 8601 datetime | Event time, not log-write time, if they ever diverge |
| `user_id` | string | The authenticated principal; `system` for automated jobs (e.g., the nightly retention enforcement job in §8.4) |
| `action_type` | enum | e.g., `login_success`, `login_failure`, `connector_create`, `connector_update`, `connector_delete`, `dashboard_export`, `permission_change`, `subject_access_request`, `subject_erasure_request`, `bulk_access_anomaly` |
| `target_resource` | string | The specific connector ID, dashboard ID, user ID, or table name affected |
| `record_count` | integer, nullable | Populated for data-access events (per KVKK/GDPR C10); null for events like login or permission changes |
| `ip_address` | string | Required by C10's audit log specification |
| `result` | enum | `success` \| `failure` |

**Immutability:** the audit log is append-only — no `UPDATE` or `DELETE` operations are exposed on it through any API, including to Platform Admin. This is a direct implementation of the KVKK/GDPR checklist's requirement (C06) that audit trail records be *anonymized, not deleted*, even when the erasure right (C06) is exercised on the underlying subject data itself: the fact that an erasure happened stays in the audit trail; the personal data it references does not.

**Retention policy:** Proposed at **24 months**, after which entries are anonymized (user_id and IP address stripped, action metadata retained) rather than deleted outright — this preserves long-horizon accountability evidence (relevant to both KVKK Art. 12 and GDPR Art. 5(2) accountability principle) without indefinitely retaining identifiable access records. This is a proposed figure for team/advisor sign-off, not yet a locked decision — flagging it as such rather than presenting it as settled.

### 8.4 KVKK/GDPR Compliance Boundary

This section maps the unified compliance checklist (C01–C10, `kvkk_gdpr_compliance_notes.md`) onto the architecture already defined in Sections 1–7, rather than restating the checklist itself.

**Which modules touch personal data:**

| Module | Personal Data Touchpoint | Checklist Item(s) |
|---|---|---|
| Connector Framework | Point of extraction — the only place data minimization can happen *before* personal data enters the platform at all | C01 |
| ETL Engine | Carries the declared `processing_purpose` on every pipeline run; the point where purpose-limitation is enforced in-flight | C02 |
| Metadata-Driven Data Warehouse | Stores `legal_basis` and `retention_policy_days` per table; runs the nightly retention enforcement job | C03, C06 (retention side), C09 |
| BI Dashboard & OLAP | Never receives personal data — only masked/aggregated output, per the RBAC + masking boundary below | C10 (masking enforcement point) |
| Data Catalog | Documents retention periods and last-erasure-run dates for personal-data tables, human-readable | C09 |
| CDC / Real-Time Streaming | Touches personal data if the replicated source table contains it (e.g., a `customers` table streamed via Debezium) — inherits the same minimization and masking obligations as batch, not a separate regime | C01, C10 |
| Security & Compliance | The implementation home for the data subject rights API, consent tracking, and breach detection | C04, C05, C06 (API side), C07, C08 |

**Masking and anonymization — connector layer vs. warehouse layer:**

These are two different mechanisms solving two different problems, and Section 8 needs to keep them distinct rather than treating "masking" as one undifferentiated control:

- **Connector layer (data minimization, not masking):** `ConnectionConfig` carries a `declared_fields` list (C01); the connector raises `ComplianceError` if a table flagged `personal_data: true` has no declared fields. This is the strongest possible control — a field never extracted can never leak downstream — and it is enforced once, at ingestion, rather than repeatedly at every read.
- **Warehouse/query layer (role-based masking):** For fields that *are* legitimately stored (because some role needs them — e.g., a Data Engineer needs a customer's raw email for pipeline debugging, but a Viewer should never see it), masking is applied server-side at query execution time, keyed to the RBAC role in the requester's JWT (§8.1's permission matrix, combined with a column-level policy). The BI Dashboard module in particular must never receive unmasked PII in its query results unless the requesting role is explicitly entitled to it — this is what makes `BI Dashboard: Write` for BI Analyst in §8.1 safe despite BI Analysts having no direct connector/warehouse admin rights: the masking happens beneath the module they do have access to, not as something they configure themselves.

The practical distinction: connector-layer minimization decides *what enters the warehouse at all*; warehouse-layer masking decides *what a given role sees of what's already there*. Both are required — minimization alone doesn't help once a field is legitimately needed by at least one role, and masking alone doesn't reduce what's stored (and therefore doesn't reduce breach exposure, C08).

**VERBİS registration mapping:**

VERBİS requires a controller to register, per processing activity: purpose, data subject categories, data categories, retention period, and recipients. SUBOP's architecture already produces three of these five as structured metadata rather than free-text documentation, which is the direct payoff of locking C02/C03/C09 into the ETL Engine and Warehouse schemas now rather than deferring them to M11/M12:

| VERBİS Required Field | SUBOP Source |
|---|---|
| Processing purpose | ETL Engine's `processing_purpose` pipeline field (C02) |
| Data categories | Connector Framework's `declared_fields` (C01), mapped to the KVKK data category taxonomy (M12 documentation task) |
| Retention period | Warehouse's `retention_policy_days` field (C09) |
| Data subject categories | Not yet captured as structured metadata — **open item**, see below |
| Recipients of transferred data | Not yet captured as structured metadata — **open item**, see below |

**Open item flagged for M4/M5 scope, not resolved here:** two of the five VERBİS fields (data subject categories, transfer recipients) have no current home in the module interface contracts from Section 4. Rather than force a placeholder answer into this section, this is being carried forward explicitly as something the M4 connector work and M5 pipeline DSL should account for, so the M12 VERBİS template export isn't attempting to reconstruct this information after the fact from unstructured sources. (This is one of *two* items Section 9.3 carries forward — see Section 9.3 for the other, the CDC schema-drift/metadata-format gap from Section 2.4/5.2.)

---

## Section 9 — M3 Conclusion & Open-Question Resolution

### 9.1 Part 1 — Four Architecture Decisions Formally Locked in M3

These four decisions were identified as needing to be locked during M3 (per the M3 scope note, Week 8) and have now been confirmed and threaded consistently through every section of this document since Section 2. Restating them here as the closing lock, not a new proposal:

| # | Decision | What Was Locked | Supporting Section |
|---|---|---|---|
| 1 | **Database abstraction pattern** | **Adapter pattern**, via `ConnectorBase` as the mandatory 5-method interface (`connect`, `disconnect`, `execute_query`, `execute_write`, `health_check`), with optional mixins (`StreamingConnector`, `PaginatedConnector`, `DocumentConnector`) layered on top for connector-specific capability. SQLAlchemy ORM and a custom DSL were formally evaluated and rejected during M2. | §2.2, §3, §4, §3.5 (Q1–Q5) |
| 2 | **Frontend stack** | **React 18 + Tailwind CSS** (Vite + TypeScript), matching Design System v1 tokens. Scaffolded since M3W8T5, with all five shared components and eight page shells completed by M3W10T5–T6. | §2.5, §3, Beyza's Week 8–10 component work (M3W8T5–T8, M3W9T5–T8, M3W10T5–T7) |
| 3 | **API framework** | **FastAPI**, chosen specifically because its async capability resolves Open Question #1 below (sync/async connector execution) rather than being a generic "modern Python framework" choice. | §3, §6, §3.5 (Q1) |
| 4 | **Warehouse target** | **PostgreSQL 15**, with **ClickHouse formally excluded**. The BI layer queries PostgreSQL directly; "OLAP Layer" naming is retained in Section 2 to describe analytical *query behavior*, not a claim that a dedicated OLAP engine exists. This avoids maintaining a second store that CDC writes would otherwise need to keep in sync. | §2.4, §2.5, §3, §5.1 |

None of these four are being revisited in this section — they are stated here as the formal closing record that Milestone 4 is built against, consistent with how they've already been used throughout Sections 2–8.

### 9.2 Part 2 — Resolution of the Five Open Architecture Questions

These five questions originated in `connector_summary_m4_prep_v1.md` (M2, Week 7) as the direct handoff from Milestone 2 to Milestone 3. They were first proposed for resolution in Section 3.5 (Week 8, pending team sign-off at the Wednesday 2 July sync); this section confirms each as formally answered, restates the question, and cross-references every section of this document that carries supporting detail — not just where the answer was first proposed.

---

**Question 1 — Synchronous vs. asynchronous connector execution.**
*Does the connector framework use synchronous or asynchronous execution? The Kafka connector requires async handling the current psycopg2 implementation does not demonstrate.*

**Answer:** `ConnectorBase` — the interface used by all SQL connectors (PostgreSQL, MySQL, MSSQL) — stays **synchronous**. A separate `StreamingConnectorBase` interface handles Kafka and REST sources **asynchronously**. FastAPI (locked in §9.1) wraps synchronous connector calls in a threadpool executor so the API layer itself remains non-blocking regardless of which connector type is underneath.
**Supporting detail:** §3 (FastAPI's async capability is the stated rationale for the framework choice), §4 (Module 1's interface table lists both the in-process Python call for SQL connectors and the Kafka subscription path for streaming-capable ones), §7.1 (the deployment diagram's application layer sits above both synchronous database connections and the asynchronous Kafka path, reflecting this same split).

**Question 2 — Shared interface vs. connector-specific extensions.**
*Should every connector implement one shared interface, or should connectors with unusual capabilities get their own extended interface?*

**Answer:** **Interface segregation.** The 5-method `ConnectorBase` contract remains mandatory for every connector — no connector may skip or partially implement it. Capability that doesn't apply to every connector is added only through optional mixins: `StreamingConnector.subscribe()`, `PaginatedConnector.fetch_page()`, `DocumentConnector.find_documents()`. A connector composes only the mixins it needs.
**Supporting detail:** §4 (Module 1 and 2's interface definitions are written against exactly this contract), §7.2 (the service dependency table treats every SQL connector identically — Connector Framework depends on whichever of postgres/mysql/mssql is configured — precisely because the shared base makes them interchangeable at that level).

**Question 3 — Non-relational sources (MongoDB) vs. a SQL-oriented abstraction.**
*Does a document-model source like MongoDB force a redesign of the SQL-shaped abstraction layer, or can it fit inside it?*

**Answer:** MongoDB implements `DocumentConnector` (the mixin from Question 2), but its query method still returns the same `List[Dict[str, Any]]` shape every SQL connector returns. The document/relational difference is absorbed **inside** the connector implementation and never leaks out to the ETL Engine — the ETL Engine's contract with the Abstraction Layer (§4, Module 3) is unaffected by which underlying source produced the batch.
**Supporting detail:** §2.1 (Data Source Layer's confirmed technology list already anticipates non-SQL sources as a stated open item, now closed by this answer), §4 (Module 2's "normalized result sets" output is what makes this possible).

**Question 4 — Connector-specific features: individual implementation vs. shared components.**
*When multiple connectors need similar-but-not-identical capability (e.g., pagination for REST, subscription for Kafka), should each connector implement its own version?*

**Answer:** **Shared abstraction components**, not per-connector reinvention. Pagination, subscription, and document-query logic are each implemented once (as the mixins from Question 2) and reused across every connector that needs that capability, rather than each connector solving the same problem independently.
**Supporting detail:** §4 (the mixin pattern itself is the direct answer, documented once and referenced rather than restated per module).

**Question 5 — Common result format and error-handling strategy.**
*Should every connector return data and raise errors the same way, or can each connector define its own conventions?*

**Answer:** Every connector returns `List[Dict[str, Any]]` from reads and a row-count `int` from writes — no exceptions per connector type. All errors are raised as `ConnectorError` subclasses (`ConnectionError`, `QueryError`, `WriteError`) carrying `{error_code, message, connector_type, retryable: bool}`. The `retryable` flag is not decorative — it is the direct input to the recoverable-vs-fatal classification used elsewhere in this document.
**Supporting detail:** §4 (Module 1 and 2 interface tables specify this exact shape), §5.1 (the batch ETL failure table classifies "connector timeout" as recoverable specifically *because* it uses this `retryable` flag), §5.2 (the CDC failure table applies the same recoverable/fatal logic to Debezium and Kafka failures), §8.3 (the audit log's `result` field — success/failure — is the same success/failure distinction this error model produces, now surfaced at the compliance layer as well as the pipeline layer).

---

### 9.3 M4-Readiness Statement

With all nine sections of this Architecture Document complete and the five open questions above formally closed, Milestone 4's connector, ETL, and CDC work can proceed against a stable interface contract without further architectural clarification on any of the following:

- **Connector implementation** (M4): every connector — the three already built (PostgreSQL, MySQL, MSSQL) and the remaining sources on the Milestone 1 supported-sources list — has an unambiguous contract to implement against: the mandatory `ConnectorBase` methods, the applicable optional mixins, the `List[Dict[str, Any]]` / `ConnectorError` result and error shape, and the sync-vs-async execution model per Question 1.
- **ETL Engine work** (M5): the pipeline DSL's required `processing_purpose` field (§8.4, KVKK/GDPR checklist item C02) and the batch/streaming data flow paths (§5.1, §5.2) are both specified in enough detail to begin implementation without waiting on further architecture decisions.
- **CDC work** (M7): the streaming path's latency instrumentation points (§5.2) and the deployment-level dependency chain risk already flagged in §7.2 (Kafka's dependency on Zookeeper as the single most fragile link in the topology) give M7 a concrete starting point for both feature work and monitoring design.

**Two items are explicitly not resolved by this document** and should not be mistaken for oversights — both are real, carried-forward scope rather than silently assumed away:

1. **CDC schema-drift / metadata-representation-format gap** (§2.4, §5.2): the format used to represent source metadata (JSON schema? annotated SQL DDL? YAML?) is undecided, and source-table schema drift (column added/renamed) has no automatic handling designed yet — flagged in §5.2 as a fatal, open risk. This must be resolved before M7's CDC work begins in earnest, and directly affects how M4's connector schema-introspection output should be shaped.
2. **VERBİS registration fields** (§8.4): two of the five VERBİS fields (data subject categories, transfer recipients) have no current home in the Section 4 module interface contracts. Carried forward as unresolved scope for M4/M5.

With those two flagged exceptions, Milestone 3 delivers what it set out to: a locked architecture (§9.1), a closed set of open questions (§9.2), a verified deployment topology (§7), and a security/compliance model (§8) — the stable foundation Milestone 4 needs to build against.

---
