# CDC Design Note (v1)

**Owner:** Abdalla · **Status:** ✅ Finalized — Week 22 (Milestone 7). Resolves the one item Architecture Document Section 9.3 left explicitly unresolved.
**Source of the items:** Architecture Document Section 2.4 (metadata representation format), Section 5.2 (latency measurement points; schema drift as a fatal open risk), Section 9.3 (M4-readiness carry-forward).

---

## 1. Scope

Two items, both of which block clean work later if left vague, and both confirmed as M7 scope at the Week 22 kickoff:

1. **Latency measurement** — Architecture Section 5.2 already fixes the four measurement points. This note confirms them as binding, specifies **where each timestamp is actually read**, and specifies **where the result is recorded**, so the 30-second KPI is measured identically every run rather than drifting between sessions.
2. **Schema drift** — Architecture Section 5.2 classifies a source column being added or renamed as a **fatal** failure with no automatic handling designed, and Section 9.3 states it must be resolved before M7's CDC work begins in earnest. It has been open since Milestone 3. This note **resolves** it rather than deferring it a fourth time.

This note is a specification. No code is written in Week 22 — Week 23's normaliser and Week 24's consumer implement against it, the same boundary M7W22T3 drew for `StreamingConnector.subscribe()`.

---

## 2. Part A — Latency Measurement Points

### 2.1 The four points are binding, not re-derived

Architecture Section 5.2's worked example (`UPDATE orders SET status='shipped'`) fixes five timestamps and four intervals. Confirmed at the Week 22 kickoff as binding. Instrumenting all four intervals — not only the total — is a stated M7 requirement, because it is what identifies *which* hop is responsible when the KPI is missed.

| Point | Event | Interval it closes |
|---|---|---|
| t0 | Transaction commits, written to WAL | — (start of budget) |
| t1 | Debezium reads the WAL entry | t1 − t0 = capture latency |
| t2 | Event published to Kafka topic | t2 − t1 = publish latency |
| t3 | Streaming consumer picks up the event | t3 − t2 = consumer lag |
| t4 | Warehouse write (upsert) completes | **t4 − t0 = total, KPI target under 30 s** |

### 2.2 Where each timestamp is read

| Point | Source | Notes |
|---|---|---|
| **t0** | Debezium envelope, `payload.source.ts_ms` | The **source database commit time**, taken from the WAL record itself. |
| **t1** | Debezium envelope, `payload.ts_ms` (top level) | The time **Debezium processed** the record. Distinct from `payload.source.ts_ms` despite the near-identical name — this is the single most likely instrumentation mistake in M7, and reversing the two silently reports capture latency as zero. |
| **t2** | Kafka record timestamp (`Message.timestamp()` in `confluent-kafka`) | Broker-assigned at publish. |
| **t3** | Consumer host clock at the moment `poll()` returns the message | `datetime.now(timezone.utc)`. |
| **t4** | Consumer host clock after the warehouse upsert commits | Recorded **after** commit, not after statement issue — an uncommitted write has not completed. |

All values normalised to **integer milliseconds, UTC**. Intervals are computed, never stored pre-computed, so a correction to one point does not require recomputing persisted derived values.

### 2.3 Where the result is recorded

A `latency_store.py` module in `services/cdc/`, following the **in-memory, interface-first pattern** `lineage_store.py` and `run_store.py` already establish — one record per change event, keyed by event id, holding all five raw timestamps plus the source table and operation. Replaced by durable storage when M8's warehouse layer lands; the interface does not change.

Exposed through the API surface Architecture Section 6 already defines for Module 4: `GET /api/cdc/connectors/{id}/status`, documented there as returning snapshot/streaming status **plus current latency, specifically the measurement points from Section 5.2**. No new endpoint is invented — the contract already exists and this note fills it.

Consumed by the frontend through `cdc_latency_ms` on the `KPISummary` interface, the nullable field added in M7W22T10, so the HomePage CDC Latency card reads a live value with no further frontend change.

### 2.4 Known limitation — clock skew (recorded, not papered over)

t0 and t1 originate from the PostgreSQL/Debezium host clock, t2 from the Kafka broker clock, t3 and t4 from the consumer host clock. Under Docker Compose all containers share the host clock, so skew is effectively zero and all four intervals are trustworthy.

In a distributed deployment they would not be. Each individual interval crosses a clock boundary, and so does the t4 − t0 total. **This is a real limitation of the measurement, not of the system**, and it is recorded here rather than discovered during KPI validation. Revisit before any multi-host deployment; not actionable inside M7, whose target environment is single-host Compose.

---

## 3. Part B — Schema Drift Resolution

### 3.1 The gap, stated plainly

Architecture Section 2.4 and Section 9.3 pose the same question in two forms: **what format represents source metadata** (JSON Schema? annotated SQL DDL? YAML?), and **what happens when a source table's schema changes mid-stream**. Section 5.2 classifies drift as *fatal, no automatic handling designed*. Open since Milestone 3, carried through M4 and M5, and now blocking M7.

### 3.2 Decision A — metadata representation format

**`Dict[str, str]`, mapping column name to native source type.** Example: `{"id": "bigint", "status": "character varying", "amount": "numeric"}`.

This is not a new format. The codebase converged on it independently across three modules and this decision formalises what is already load-bearing:

- `AbstractionLayer.execute_query(column_types: Optional[Dict[str, str]])`
- `executor._column_types_from_casts() -> Dict[str, str]`
- `lineage_store.record_lineage_entry(canonical_type=..., source_type=...)` — both plain type strings, same vocabulary

JSON Schema and annotated DDL were the alternatives named in Section 2.4. Both are rejected for v1: neither is used anywhere in the system today, so adopting either would introduce a fourth representation and a translation layer between it and the three call sites above, for no capability M7 requires.

### 3.3 Decision B — where the schema snapshot comes from

**From the Debezium change event itself.** Every Debezium message carries a `schema` block alongside `payload`, listing field names and types for that record. The normaliser derives a `Dict[str, str]` from it per message.

No introspection query is issued against the source database. This matters for three reasons: it costs nothing, it cannot drift from the event it describes (the schema block and payload are produced together, atomically), and it requires no additional privilege beyond what the `subop_cdc` role already holds.

The first message received for a table establishes the **baseline snapshot**. Each subsequent message is compared against it.

### 3.4 Decision C — handling

**A detected drift halts consumption for the affected table only — not the whole CDC connector.**

| Drift type | v1 handling |
|---|---|
| Column added | Halt table |
| Column renamed | Halt table |
| Column dropped | Halt table |
| Column type changed | Halt table |

Raised as the existing **`QueryError`** from `services/connectors/errors.py` — semantically the closest match, a failure to process an incoming record — carrying:

```
error_code    = "CDC_SCHEMA_DRIFT_DETECTED"
connector_type = "streaming"
retryable      = False
```

No new exception class is introduced. `errors.py` is the single source of truth for the error shape, and the four-field envelope (`error_code`, `message`, `connector_type`, `retryable`) already propagates through ETL Engine failure classification and the API error envelope unchanged.

`retryable=False` is correct and deliberate: retrying delivers the same drifted message again. Resolution is manual, exactly as Section 5.2 anticipated.

**Table-scoped rather than connector-scoped** because the blast radius of a connector-wide halt is disproportionate — one column rename on `orders` would stop capture on every other published table, including tables whose data remains perfectly valid. This also matches the error hierarchy's own granularity: `ConnectorError` carries a `connector_type` and describes one failing operation, not a global kill switch.

### 3.5 Why "column added" is fatal in v1, and when that should be revisited

Treating a purely additive change as fatal is conservative, and is correct **only for as long as the warehouse schema is fixed**. Until M8's metadata-driven schema generation exists, there is no mechanism to absorb a new column — the upsert target simply has no place to put it, so continuing would silently drop data, which is worse than halting.

**Named revisit:** once M8 delivers metadata-driven schema generation, column-added should be reclassified as non-fatal with automatic schema evolution. Owner: Abdalla. Target: M8. Recorded here so the conservative choice is a deliberate v1 position rather than a permanent assumption.

### 3.6 Implementation boundary

| What | Where | When | Owner |
|---|---|---|---|
| Snapshot extraction + comparison + raise | Week 23 normaliser | Week 23 | Abdalla |
| `latency_store.py` | `services/cdc/` | Week 24–25 | Abdalla |
| Drift surfaced in CDC Monitor connector status panel | Frontend, M7W22T9 shell | Week 24+ | Beyza |

---

## 4. Conflict Check

Confirmed no conflict with:

- **`StreamingConnector` mixin (M7W22T3)** — drift detection sits in the normaliser, *above* `subscribe()`. The mixin's contract is unchanged, and `subscribe()` stays free of schema concerns.
- **`services/connectors/errors.py`** — no new class, no new field. One docstring correction is required, raised separately: the `connector_type` argument description lists `"postgresql" | "mysql" | "mssql" | "mongodb"`, which omits the seven types M6 actually shipped (`sqlite`, `oracle`, `csv`, `json`, `rest_api`, `file`) plus `streaming`, and still names `mongodb`, removed from DSL validation in M6. A docstring inaccuracy, not a defect.
- **`lineage_store.py`** — same `Dict[str, str]` / plain-type-string vocabulary. Lineage and drift detection describe the same column types in the same terms.
- **M8 metadata-driven warehouse schema generation** — `Dict[str, str]` is an input shape, not a ceiling. A richer representation can be adopted in M8 if schema generation requires one; nothing in this note forecloses it.
- **M7W22T2's publication scope** — drift is evaluated per table, matching the publication's explicit per-table list (`cdc_demo.orders`). A table outside the publication cannot drift into scope.

---

## 5. Status & Close-Out

Both items are **resolved**, not deferred. With this note, the single item Architecture Document Section 9.3 carried forward as explicitly unresolved — the CDC schema-drift / metadata-representation-format gap — is closed, and Section 2.4's open item closes with it.

One item is **deliberately scoped forward with a named owner and target**, which is a different thing from a deferral: reclassifying column-added as non-fatal once M8's metadata-driven schema generation makes automatic evolution possible (Section 3.5 above).

Section 2.4, Section 5.2 and Section 9.3 of `architecture_doc_v1.md` should be updated to cite this addendum, following the precedent `verbis_interface_proposal_v1.md` set in Week 12.
