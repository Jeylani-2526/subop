# SUBOP Architecture Document v1
**Sections 4–6 of 9 · Task: M3W8T3 · Owner: Abdullah · Draft date: 30 June–2 July 2026**
**Path (updated convention):** `docs/milestones/milestone 3/week 8/architecture_doc_v1.md` (continuation of Sections 1–3)

*Status: Sections 4–6 complete (this document). Sections 7–9 scheduled for Week 9.*

---

## 3.5 — Resolutions to the Five Open Architecture Questions

*(Placed here, ahead of Section 4, because the module interface table below depends on these decisions. These are proposed resolutions for team sign-off at the Wednesday 2 July sync — not unilaterally locked.)*

| # | Open Question (from `connector_summary_m4_prep_v1.md`) | Proposed Resolution |
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
| Source table schema drift (e.g., column added/renamed) | **Fatal — flagged open risk** | No automatic schema evolution handling designed yet; requires manual intervention. This connects to the still-open metadata-format decision in Section 2.4 and should be resolved before M7 begins. |

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

**Next:** Sections 7–9 (Deployment Topology, Security Architecture, M3 Conclusion) — Week 9, per the M3 scope note plan.
