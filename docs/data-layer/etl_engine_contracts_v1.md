# ETL Engine — Input/Output Contracts (Full Draft v1)

**Owner:** Abdullah · **Status:** Full draft

---

## 1. Purpose of This Document

This is the binding input/output contract for the ETL Engine (Module 3), specified in enough detail for M5 implementation to begin without further architectural clarification. It supersedes the Week 11 outline: every contract point enumerated there is now specified to the level of concrete formats, failure modes, and module boundaries. It still does not specify transformation DSL grammar or retry/backoff timing values — those remain implementation-level decisions for M5 itself, not architecture.

## 2. Inputs Consumed

| Source | What's consumed | Format | Mode |
|---|---|---|---|
| API (pipeline creation) | Pipeline definition — source, transformations, target, `processing_purpose` | JSON pipeline DSL | Batch (via `POST /api/pipelines/`) |
| Abstraction Layer (Module 2) | Row batches, already dialect-normalized **and type-normalized** (Section 7) | `List[Dict[str, Any]]` | Batch |
| CDC Layer (Module 4) | Normalized change events | JSON `{op, table, before, after, ts_ms}` via Kafka consumer | Streaming |
| Security & Compliance (Module 10) | Registration confirmation for `processing_purpose`, `data_subject_categories`, `transfer_recipients` — read at pipeline-creation time, not per run | JSON via internal call | Batch (pipeline creation only, not part of the per-run hot path) |

**Resolved since the Week 11 outline:** the Security & Compliance input row above was previously marked "pending T2 proposal landing." The VERBİS interface-placement proposal was finalized in Week 12 (`verbis_interface_proposal_v1.md`), placing `data_subject_categories` and `transfer_recipients` in Module 10. ETL Engine's contract with Security & Compliance is a **read-once-at-creation** check, not a per-run dependency: a pipeline cannot be created without a completed VERBİS registration record, but running an already-created pipeline does not re-query Security & Compliance on every execution. This keeps the hot path (Section 5.1/5.2) free of a compliance round-trip per run while still guaranteeing no pipeline runs unregistered.

## 3. Outputs Produced

| Destination | What's produced | Format | Mode |
|---|---|---|---|
| Warehouse Layer (Module 5) | Transformed row batches | `List[Dict[str, Any]]` | Batch — upsert against `dim_*`/`fact_*` tables, SCD Type 2 where tracked fields changed |
| Warehouse Layer (Module 5) | Transformed change events | Same shape as batch — idempotent upsert keyed by PK + operation timestamp | Streaming |
| Data Quality (Module 7) | Row batch, passed as an in-process hook *before* warehouse write | `List[Dict[str, Any]]` | Both — call is synchronous even in streaming mode per event |
| Data Lineage (Module 8) | Execution metadata: source table → transform step → target table, **plus per-column type-mapping condition where non-`direct`** (Section 7) | JSON (nodes/edges, with mapping-condition annotations) | Both — recorded as part of the warehouse write step, not a separate afterthought pass |
| API (status) | Run status and logs | JSON via `GET /api/pipelines/{id}/runs/{run_id}` | Batch |
| API (status) | Latency/consumer-lag metrics (four measurement points from Section 5.2) | JSON via `GET /api/cdc/connectors/{id}/status` — technically CDC's endpoint, but sourced from ETL Engine's streaming consumer offset | Streaming |

**All writes are routed through the Abstraction Layer** — ETL Engine never opens a direct database connection for a Warehouse write, consistent with the "no direct cross-module calls" constraint. Writes handed to the CDC path (streaming mode) follow the same rule: the streaming consumer's resulting upserts against the Warehouse go through `execute_write()`, identically to the batch path. There is no separate write mechanism for streaming vs. batch — only the trigger differs (Kafka consumer vs. API-triggered run).

## 4. Contract With the Abstraction Layer (Module 2) — the Load-Bearing Boundary

This is the interface ETL Engine depends on most directly, and the one Section 1's non-negotiable constraint #2 ("no direct cross-module calls") applies to most strictly:

- ETL Engine never issues SQL directly and never knows which dialect is underneath — it calls the Abstraction Layer's `execute_query`/`execute_write`, and receives back `List[Dict[str, Any]]` or a row-count `int`, per Section 9.2 Q5.
- As of Week 12's Abstraction Layer sketch, `execute_query()` also performs type normalization internally before returning — ETL Engine receives already type-normalized rows, exactly as it already received already dialect-normalized rows. This is the same invisibility guarantee, extended to cover value types as well as SQL syntax (Section 7).
- Errors arrive as `ConnectorError` subclasses (`ConnectionError`, `QueryError`, `WriteError`) carrying `{error_code, message, connector_type, retryable: bool}`. ETL Engine's own failure classification (Section 5.1's recoverable/fatal table) is built directly on top of this `retryable` flag — it is not re-derived independently. As of Week 12, normalization failures (Section 7) use this same `ConnectorError` shape, so ETL Engine's existing classification logic requires zero new code to handle them.
- Per Section 9.2 Q3, this contract is source-agnostic: whether the underlying connector is PostgreSQL, MySQL, MSSQL, or MongoDB (via `DocumentConnector`), ETL Engine receives the identical shape. The document/relational distinction is fully absorbed below this boundary — and now the type-system distinction (native `NVARCHAR(MAX)` vs. `TEXT` vs. MongoDB's dynamic typing) is absorbed at the same boundary, for the same reason.

## 5. Contract With the CDC Layer (Module 4) — Streaming Mode Only

- ETL Engine's streaming consumer reads from Kafka topics named `cdc.<source>.<table>`.
- Per Section 9.2 Q1, this path is asynchronous — a separate concern from the synchronous batch contract in Section 2. The two modes share the same downstream Warehouse contract (Section 5.2's core guarantee: no separate "streaming store" to reconcile) but are distinct on the input side.
- Idempotency is required, not optional: Kafka's at-least-once delivery means ETL Engine's streaming consumer will see duplicate events, and the upsert-by-PK-plus-timestamp pattern in Section 5.2 is what makes that safe rather than something ETL Engine needs to de-duplicate itself.
- Type normalization for CDC events is out of scope for the Abstraction Layer (Debezium emits its own typed JSON payload, not a connector-driven `execute_query()` result) — this is flagged explicitly as a Milestone 7 concern in Section 9.3's carried-forward CDC schema-drift gap, not something this contract resolves.

## 6. Contract With Governance Modules (Quality, Lineage) — Synchronous Hooks

- **Data Quality:** called as an in-process hook *before* the warehouse write, not after. A rule violation can halt the pipeline (fatal) or quarantine offending rows (recoverable) depending on configured rule severity — this branching happens inside ETL Engine's execution flow, not as a separate downstream check. **Type-mapping conditions (`inexact`, `ambiguous`, `conditional`, `fallback`) are explicitly not routed to Data Quality** (Section 7) — Data Quality validates business rules against already-normalized values, not the type system's own confidence in how it produced them. Keeping this boundary clean means Data Quality rule authors never need type-system awareness to write a rule.
- **Lineage:** recorded as part of the same write step that lands data in the Warehouse — Section 5.1 is explicit that this is not an afterthought pass, which matters for the contract: Lineage's write call and the Warehouse write are not independently retriable steps; they succeed or fail together. As of Week 12, Lineage's execution-metadata payload gains one addition (Section 7): where a column's type-mapping condition was non-`direct`, that condition is recorded alongside the transform step it passed through, giving M12's data lineage / audit surface visibility into representational caveats without requiring Data Quality to model them as rule violations.

## 7. Boundary Question, Resolved — Universal Type Mapping Consumption

The Week 11 outline left this open pending Omer's Abstraction Layer sketch. That sketch now exists (`abstraction_layer_interface_sketch_v1.md`), and combined with the Type Mapping specification's six mapping conditions (`direct`, `inexact`, `ambiguous`, `conditional`, `fallback`, `unsupported`), the question splits cleanly into two cases rather than one:

**7.1 — Where type coercion happens.** Inside the Abstraction Layer, invisible to ETL Engine — confirmed by the sketch's `execute_query()` flow, which resolves column metadata and normalizes rows internally before returning the same `List[Dict[str, Any]]` shape ETL Engine already expects. This is consistent with the existing dialect-normalization pattern (`LIMIT` vs. `TOP`): ETL Engine's contract with the Abstraction Layer does not change shape when type mapping is added, only what happens beneath it.

**7.2 — How a lossy mapping surfaces.** The Type Mapping spec's six conditions are not equally severe, and the outline's original framing ("non-retryable `ConnectorError` vs. a Data Quality warning") assumed a single answer where two are actually needed:

| Condition | Is it a failure? | How it surfaces to ETL Engine |
|---|---|---|
| `direct` | No | Nothing — standard normalized value, no annotation |
| `inexact`, `ambiguous`, `conditional`, `fallback` | No — these are successful mappings with a caveat, not errors | **Not surfaced as an error, and not routed to Data Quality.** Recorded as column-level metadata in the Lineage execution record for that transform step (Section 6), so the caveat is auditable without being treated as a business-rule violation. |
| `unsupported` | Yes — the Type Mapping spec's own Rule 8 requires an explicit error for unknown native types | Raised as a **non-retryable `ConnectorError`**, using the exact same shape ETL Engine already handles for connection/query/write errors (Section 4). No new error-handling code path is needed in ETL Engine — its existing recoverable/fatal classification (Section 5.1) already treats `retryable: false` as fatal. |

**Rationale for the split:** Data Quality's rules validate business meaning (is this value plausible, complete, consistent with other fields) — it has no natural vocabulary for "this value came from a `FLOAT` column and may have lost binary-floating-point precision." Routing type-system caveats there would force every Data Quality rule author to also reason about source-database type systems. Lineage, by contrast, already exists to answer "where did this value come from and what happened to it on the way" — a type-mapping condition is exactly that kind of provenance fact, not a validation outcome. This keeps each governance module's contract doing one job.

**What this resolves for M5:** ETL Engine's transformation logic can be written against a single assumption — every row it receives from the Abstraction Layer is either already-normalized data (silently, for `direct`/`inexact`/`ambiguous`/`conditional`/`fallback`, with Lineage recording any caveat as a side effect it doesn't need to branch on) or the call raised a `ConnectorError` it already knows how to classify (for `unsupported`). No new conditional branching is required in ETL Engine's core execution path.

## 8. Data Quality — Full Contract

Unchanged from the outline in structure, now stated as the binding contract:

- Data Quality is called synchronously, in-process, immediately before the Warehouse write — for both batch and streaming (per-event) modes.
- Input: the transformed row batch (`List[Dict[str, Any]]`) and the active rule set for the pipeline/dataset (JSON rule definitions).
- Output: a quality score (JSON) plus zero or more violations, each carrying a configured severity.
- **Fatal severity** halts the pipeline run before the Warehouse write occurs; the run status (Section 3) reflects this as a failed run, not a partial one.
- **Recoverable severity** quarantines the offending rows (they are not written to the Warehouse) while the remainder of the batch proceeds; the run status reflects a completed run with a quarantine count.
- Data Quality never receives type-mapping condition metadata (Section 7.2) — its rule inputs are exclusively already-normalized business values.

## 9. What's Deliberately Out of Scope for This Contract

- Transformation DSL syntax (currency normalization, PII masking flag mechanics) — M5 implementation-level decision, not architecture.
- Retry/backoff timing values — Section 5.1 names *what's* recoverable, not the specific backoff schedule; that schedule is an M5 configuration decision.
- CDC schema-drift handling — explicitly carried forward as unresolved M4/M5 scope per Section 9.3; this document doesn't attempt to pre-empt that decision, and Section 5 above notes CDC's type-handling is a separate, later concern from the Abstraction Layer's synchronous-query type mapping resolved in Section 7.
- Type-mapping value tables themselves (which native type maps to which canonical type) — fully owned by `universal_type_mapping_v1.md`; this document only specifies how ETL Engine consumes the *outcome* of that mapping, not the mapping rules themselves.

## 10. Readiness Statement

With Sections 2–9 above, ETL Engine's full input/output contract is specified against a stable Abstraction Layer interface and a resolved type-mapping boundary. M5 can begin implementation against this contract without further architectural clarification, subject only to the two items explicitly carried forward as out-of-scope (Section 9): transformation DSL syntax and CDC schema-drift handling, both flagged as M5/M7 implementation-level or cross-milestone decisions rather than gaps in this contract.
