# ETL Engine — Input/Output Contracts Outline (Draft v1)

**Owner:** Abdullah · **Status:** Superseded — deepened into the full contract draft in Week 12. See `etl_engine_contracts_v1.md` (docs/data-layer/) for the current, binding version, including the resolved Universal Type Mapping boundary question (Section 7 of that document).
**Source:** Architecture Document s2.2, s4 (Module 3), s5.1, s5.2, s6, s9.2 (Q1, Q3, Q5), s9.3.

---

## 1. Purpose of This Outline

Section 4 already defines ETL Engine's inputs/outputs at the module-table level. This outline goes one level deeper — enumerating each contract point explicitly, so that Week 12's full spec has a checklist to work from rather than starting blank. It does **not** attempt to specify transformation DSL syntax, retry timing values, or implementation code — those are Week 12+ decisions.

## 2. Inputs Consumed

| Source | What's consumed | Format | Mode |
|---|---|---|---|
| API (pipeline creation) | Pipeline definition — source, transformations, target, `processing_purpose` | JSON pipeline DSL | Batch (via `POST /api/pipelines/`) |
| Abstraction Layer (Module 2) | Row batches, already dialect-normalized | `List[Dict[str, Any]]` | Batch |
| CDC Layer (Module 4) | Normalized change events | JSON `{op, table, before, after, ts_ms}` via Kafka consumer | Streaming |
| Security & Compliance (Module 10) | *(pending T2 proposal landing)* — no current input path; if the VERBİS proposal is adopted, ETL Engine may need to read back a registration confirmation before a pipeline is allowed to run | TBD | Both |

## 3. Outputs Produced

| Destination | What's produced | Format | Mode |
|---|---|---|---|
| Warehouse Layer (Module 5) | Transformed row batches | `List[Dict[str, Any]]` | Batch — upsert against `dim_*`/`fact_*` tables, SCD Type 2 where tracked fields changed |
| Warehouse Layer (Module 5) | Transformed change events | Same shape as batch — idempotent upsert keyed by PK + operation timestamp | Streaming |
| Data Quality (Module 7) | Row batch, passed as an in-process hook *before* warehouse write | `List[Dict[str, Any]]` | Both — call is synchronous even in streaming mode per event |
| Data Lineage (Module 8) | Execution metadata: source table → transform step → target table | JSON (nodes/edges) | Both — recorded as part of the warehouse write step, not a separate afterthought pass |
| API (status) | Run status and logs | JSON via `GET /api/pipelines/{id}/runs/{run_id}` | Batch |
| API (status) | Latency/consumer-lag metrics (four measurement points from s5.2) | JSON via `GET /api/cdc/connectors/{id}/status` — technically CDC's endpoint, but sourced from ETL Engine's streaming consumer offset | Streaming |

## 4. Contract With the Abstraction Layer (Module 2) — the Load-Bearing Boundary

This is the interface ETL Engine depends on most directly, and the one Section 1's non-negotiable constraint #2 ("no direct cross-module calls") applies to most strictly:

- ETL Engine never issues SQL directly and never knows which dialect is underneath — it calls the Abstraction Layer's `execute_query`/`execute_write`, and receives back `List[Dict[str, Any]]` or a row-count `int`, per s9.2 Q5.
- Errors arrive as `ConnectorError` subclasses (`ConnectionError`, `QueryError`, `WriteError`) carrying `{error_code, message, connector_type, retryable: bool}`. ETL Engine's own failure classification (s5.1's recoverable/fatal table) is built directly on top of this `retryable` flag — it is not re-derived independently.
- Per s9.2 Q3, this contract is source-agnostic: whether the underlying connector is PostgreSQL, MySQL, MSSQL, or MongoDB (via `DocumentConnector`), ETL Engine receives the identical shape. The document/relational distinction is fully absorbed below this boundary.

## 5. Contract With the CDC Layer (Module 4) — Streaming Mode Only

- ETL Engine's streaming consumer reads from Kafka topics named `cdc.<source>.<table>`.
- Per s9.2 Q1, this path is asynchronous — a separate concern from the synchronous batch contract in Section 4. The two modes share the same downstream Warehouse contract (Section 5.2's core guarantee: no separate "streaming store" to reconcile) but are distinct on the input side.
- Idempotency is required, not optional: Kafka's at-least-once delivery means ETL Engine's streaming consumer will see duplicate events, and the upsert-by-PK-plus-timestamp pattern in s5.2 is what makes that safe rather than something ETL Engine needs to de-duplicate itself.

## 6. Contract With Governance Modules (Quality, Lineage) — Synchronous Hooks

- **Data Quality:** called as an in-process hook *before* the warehouse write, not after. A rule violation can halt the pipeline (fatal) or quarantine offending rows (recoverable) depending on configured rule severity — this branching happens inside ETL Engine's execution flow, not as a separate downstream check.
- **Lineage:** recorded as part of the same write step that lands data in the Warehouse — Section 5.1 is explicit that this is not an afterthought pass, which matters for the contract: Lineage's write call and the Warehouse write are not independently retriable steps; they succeed or fail together.

## 7. Open Boundary Question — Not Resolved in This Outline

**How ETL Engine consumes the Universal Type Mapping module.** Omer's type-mapping specification and abstraction-layer interface sketch (M4W11T8–T9) are still in progress. Until that sketch exists, this outline can't specify:
- Whether type coercion happens inside the Abstraction Layer (invisible to ETL Engine, consistent with the dialect-normalization pattern already used for `LIMIT`/`TOP`) or whether ETL Engine needs visibility into lossy-mapping flags to decide how to handle a transformation.
- Whether a lossy type mapping (flagged per Omer's spec) should be a `retryable: false` `ConnectorError`, a warning surfaced to Data Quality, or something else — this needs to be decided jointly, not assumed here.

This is flagged as the single largest open item for Week 12's full spec, to be resolved with Omer once his sketch is available — not guessed at in this outline.

## 8. What's Deliberately Out of Scope for This Outline

- Transformation DSL syntax (currency normalization, PII masking flag mechanics) — Week 12+.
- Retry/backoff timing values — Section 5.1 names *what's* recoverable, not the specific backoff schedule.
- The VERBİS registration interaction (Section 3 above) — depends on whether the M4W11T2 proposal is adopted as written.
- CDC schema-drift handling — explicitly carried forward as unresolved M4/M5 scope per s9.3; this outline doesn't attempt to pre-empt that decision.
