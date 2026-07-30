# SUBOP Architecture Document v1
**Section 9 of 9 · Owner: Abdullah · Draft date: 9 July 2026**


---

## Section 9 — M3 Conclusion & Open-Question Resolution

### 9.1 Part 1 — Four Architecture Decisions Formally Locked in M3

These four decisions were identified as needing to be locked during M3 (per the M3 scope note, Week 8) and have now been confirmed and threaded consistently through every section of this document since Section 2. Restating them here as the closing lock, not a new proposal:

| # | Decision | What Was Locked | Supporting Section |
|---|---|---|---|
| 1 | **Database abstraction pattern** | **Adapter pattern**, via `ConnectorBase` as the mandatory 5-method interface (`connect`, `disconnect`, `execute_query`, `execute_write`, `health_check`), with optional mixins (`StreamingConnector`, `PaginatedConnector`, `DocumentConnector`) layered on top for connector-specific capability. SQLAlchemy ORM and a custom DSL were formally evaluated and rejected during M2. | §2.2, §3, §4, §3.5 (Q1–Q5) |
| 2 | **Frontend stack** | **React 18 + Tailwind CSS** (Vite + TypeScript), matching Design System v1 tokens. Already scaffolded and in active use since M3W8T5 — this is a confirmation of a decision already being built against, not a still-open choice. | §2.5, §3, Beyza's Week 8–9 component work (M3W8T5–T8, M3W9T5–T8) |
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
**Supporting detail:** §4 (Module 1 and Module 2's interface definitions are written against exactly this contract), §7.2 (the service dependency table treats every SQL connector identically — Connector Framework depends on whichever of postgres/mysql/mssql is configured — precisely because the shared base makes them interchangeable at that level).

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

**One item is explicitly not resolved by this document** and should not be mistaken for an oversight: §8.4 flagged that two of the five VERBİS registration fields (data subject categories, transfer recipients) have no current home in the Section 4 module interface contracts. This is carried forward as real, unresolved scope for M4/M5 — not a Milestone 3 closure item — and should be addressed explicitly rather than silently assumed away when connector and pipeline metadata schemas are implemented.

With that one flagged exception, Milestone 3 delivers what it set out to: a locked architecture (§9.1), a closed set of open questions (§9.2), a verified deployment topology (§7), and a security/compliance model (§8) — the stable foundation Milestone 4 needs to build against.

---

