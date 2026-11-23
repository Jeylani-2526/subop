# SUBOP — M8 Kickoff Sync

**Sync date:** Monday 16 November 2026
**Milestone:** M8 — Metadata-Driven Data Warehouse
**Prepared under:** M7W27T4, against `develop` at `5518e29`

---

## Part A — Agenda / Talking Points

**1. Scope — four weeks of work in two weeks (25 min)**
Per `SUBOP_roadmap.docx`, **M8 runs 3 – 30 November 2026 (W27–W30)**, owned by **Abdalla + Omer**. Its main output is fact/dimension automation, SCD and schema versioning. The Weeks 26–27 catch-up plan moved M8's start to **16 November** and kept the **30 November** end. That leaves two working weeks (W28: 16–22 Nov, W29: 23–29 Nov), with 30 November as a formal close only.

The starting point, confirmed on `develop`:

| What | State |
|---|---|
| `services/warehouse/` | **README only — no code.** M8 starts from zero. |
| Metadata format | **Not decided.** Architecture Section 2.4 says it must be decided before M8 begins. See item 2. |
| Universal type mapping | Present: `services/abstraction/type_mapping.py` (M4). Schema generation can build on it. |
| Write path into the warehouse | Present: the Abstraction Layer's `execute_write`, used by the M7 CDC sink. |
| KPIs due **end of November** | Two: **DW schema automation 80% faster than manual** (roadmap), and **CDC latency under 30 s** (carried from M7). |

Decide one of two options. Part B records which one:

- **(A) Hold 30 November, reduce scope — recommended.**
- **(B) Keep the full scope, move M8's end to Sunday 13 December.** M9 (1–28 Dec) and every later milestone would shift by two weeks. M12's 11 May 2027 end is fixed, so M11 and M12 would absorb the loss.

**Why (A).** Holding the roadmap timeline is the project's stated top priority. Goal G5 in `SUBOP_Final_Goal_Statement.docx` measures "done" by the 80% KPI, which a working generator can meet without schema versioning. M9 is Beyza-led, so Abdalla's backend time in December can take the deferred items without delaying M9.

Recommended scope under (A):

| Item | Under (A) | Where it goes |
|---|---|---|
| Metadata definition format and a demo star schema definition | **In M8** | W28 |
| Schema generator: metadata → fact and dimension tables, through `execute_write` and `type_mapping.py`, re-runnable | **In M8** | W28 |
| SCD Type 1 and Type 2 for dimensions flagged in the metadata, on the batch load path | **In M8** | W29 |
| `GET /api/warehouse/schemas`, `POST /api/warehouse/schemas/generate` (Architecture Section 6) | **In M8** | W29 |
| DW schema automation KPI (80% faster than manual) | **In M8** | W29 |
| CDC latency instrumentation (t0–t4) and KPI validation | **In M8** (carried from M7) | W28–W29 |
| Schema versioning: `GET /api/warehouse/schemas/{id}/versions`, changing a generated schema when its metadata changes | Deferred | M9 window, Abdalla |
| Snowflake schemas (star only in M8) | Deferred | To be placed at the M9 kickoff |
| CDC change events written into SCD dimensions (CDC keeps writing its M7 mirror tables) | Deferred | To be placed at the M9 kickoff |

Even under (A), the critical path sits on one person: the generator, SCD, the API, both KPIs and the latency instrumentation are all Abdalla's (see item 4). Part B should say plainly what is cut first if Week 29 slips.

**2. Metadata format — decide before any generator code (10 min)**
Open since Architecture Section 2.4: JSON schema, annotated SQL DDL, or YAML.
- **Recommended: JSON files validated by Pydantic models.** Pydantic already comes with FastAPI, so this adds no dependency. PyYAML is not in `requirements-dev.txt`. Pydantic also reports each validation error with its field path.
- Annotated SQL DDL is not recommended: it needs a SQL parser, and it puts hand-written SQL back into a module whose goal is "without manual SQL writing".
- The decision gates W28's generator work, so it is made in the sync, not after.

**3. Confirm M7 closure (10 min)**
- Walk through `m7_completion_checklist.docx` one criterion at a time: 12 Done, 3 Pending (develop → main merge, M8 kickoff documents, M7 report to Emrah), 1 Deferred (latency KPI, item 5). Don't re-open settled items without new evidence.
- Items carried into M8 or later, each needing an owner and target in Part B (from the checklist's Section 3):

  | Item | Owner | Target |
  |---|---|---|
  | Latency instrumentation and KPI validation | Abdalla | M8, by 30 Nov |
  | CDC Latency KPI card live wiring | Beyza | M8 |
  | Offset and replication-slot lifecycle, including M7W27T1 Finding 2 (slow topic pickup) | Omer | M8, non-critical (item 4) |
  | Restart and resume verification | Mert | M8, non-critical (item 4) |
  | Halt hidden while Connect is down | Abdalla | M8 |
  | CI live-CDC capability | Omer | M8 or later |
  | Overview trend lines are fixed text | Beyza | M9 |
  | Production CORS origin (M6 Criterion 7) | Omer | When a deployment target exists |
  | Data Quality rule engine | Team | M10 |

- **Not yet planned anywhere — MySQL CDC.** Goal G4 defines CDC as done when events from **PostgreSQL and MySQL** arrive under 30 seconds. M7 delivered PostgreSQL only, by its kickoff decision. Decided 10 Nov: not added to M8. **Recommended: M11 (Security, Compliance & Full Integration, 3 Feb – 23 Mar 2027)**, owners Abdalla + Omer. Part B names the milestone so G4 isn't left half-met by default.

**4. Team and weekly tasks (10 min)**
- **Omer and Mert return on 16 November**, decided 10 Nov: **one task each per week**, never on the critical path, and no other task may depend on theirs. Team split **40 / 40 / 10 / 10** (Abdalla / Beyza / Omer / Mert).
- Proposed tasks. Each one stands alone; if one slips, nothing else moves:

  | Week | Omer | Mert |
  |---|---|---|
  | W28 | Replication-slot lifecycle: measure WAL retained by `subop_cdc_slot` while the connector is stopped, document how capture resumes, and propose a `topic.metadata.refresh.interval.ms` value for Finding 2. Output: a findings note. | Restart and resume verification on the existing M7 stack: stop and restart the consumer and the connector, confirm no event is lost or duplicated, commands and output verbatim. |
  | W29 | CI live-CDC capability: a **separate, non-required** CI job with `postgres:15` at `wal_level=logical`. It must not touch the required Lint and Tests jobs. | Second-person reproduction of the M7 runbook: `verify_cdc_prerequisites.sh --rebuild`, then Phases 2–5 of `cdc_e2e_verification.md`, recorded verbatim. |

- Abdalla carries every critical item. Under option (A) that is the generator, SCD, the warehouse API, both KPIs and the latency instrumentation. Confirm this load is accepted, and what is cut first if Week 29 slips.

**5. The two end-of-November KPIs — agree how each is measured before building (15 min)**
- **CDC latency under 30 s.** The five points t0–t4 from the CDC Design Note are binding. Two earlier observations disagree by two orders of magnitude: **56 s** on an idle database (Week 23, WAL flush behaviour) and **0.3–0.9 s** on an active one (10 Nov). Decide the conditions the KPI is measured under, recommended **both, reported separately**. The idle case is the one that can fail, and reporting only the active case would round the result up. Results are recorded unrounded.
- **DW schema automation 80% faster than manual.** Agree the protocol before the generator exists:
  - Same target star schema both ways.
  - Manual: hand-written DDL, timed from a written spec.
  - Generated: writing the metadata definition **plus** running the generator, timed from the same spec.
  - The KPI is met when generated time ≤ 20% of manual time.
  - Whoever designed the schema is faster at both, so the record states who did each half.

**6. Beyza's M8 scope and what M8 does not cover (10 min)**
- Proposed, using the shell-first pattern that worked in M7:
  - **W28:** a read-only **Warehouse Schemas** page, built against an agreed response shape for `GET /api/warehouse/schemas`, with a pending notice while it reads fixtures.
  - **W29:** swap that page to the live endpoint; wire the **CDC Latency** KPI card and the CDC page's latency strip once the endpoint returns values.
  - New strings in `tr.ts` and `en.ts` from the first commit. Use the colour tokens defined in `index.css`; the undefined-variable bug from 10 Nov must not recur.
- **What M8 does not cover**, so it isn't assumed by default: BI dashboards (M9), the data quality rule engine (M10), MySQL CDC (item 3), and the items deferred under item 1.

**7. Close (5 min)**
- Abdalla captures Part B during the sync and shares it the same day.
- `SUBOP_Milestone_8.docx` (the charter) is drafted for option (A). It is finalised with the option Part B records, so M8 closes against a committed criteria list rather than one rebuilt afterwards, which is what happened in M7.
- Advisor reporting, decided 10 Nov: **one report at the close of each milestone**, not weekly. The M8 report is due at M8's close.

---

## Part B — Kickoff Notes


**Attendees:** ☑ Abdalla ☑ Beyza ☑ Omer ☑ Mert
**Held:** Monday 16 November 2026. Part B was committed on Wednesday 18 November, two days
late. Items 1–3 record the sync. Items 4 and 5 were left open at the sync and decided on
18 November by Abdalla, as noted under each.

### 1. Scope — Decided: Option (A)

**Decision: hold 30 November with reduced scope.** M8 keeps its end date. Monday 30
November is a formal close only. Option (B), moving the end to 13 December, was not taken.

In M8: the metadata format and demo star definition, the schema generator, SCD Type 1 and
Type 2 on the batch path, `GET /api/warehouse/schemas` and
`POST /api/warehouse/schemas/generate`, both KPIs, CDC latency instrumentation, and the
compliance fields (item 2).

Deferred, each carried by name:

| Item | Owner | Target |
|---|---|---|
| Schema versioning (`GET /api/warehouse/schemas/{id}/versions`), with column-added drift reclassified non-fatal | Abdalla | M9 window |
| Snowflake schemas (M8 generates star schemas only) | Abdalla | Placed at the M9 kickoff |
| CDC change events into SCD dimensions (CDC keeps writing its M7 mirror tables) | Abdalla | Placed at the M9 kickoff |
| Nightly retention enforcement job (C06 retention side, C09) | Abdalla + Omer | M11 |
| MySQL CDC (Goal G4) | Abdalla + Omer | **M11 — decided** |

**MySQL CDC — decided: M11** (Security, Compliance & Full Integration, 3 Feb – 23 Mar
2027). Goal G4 names PostgreSQL and MySQL. M7 delivered PostgreSQL, so G4 stays half-met
until M11, and that is recorded here rather than left open by default.

### 2. Metadata Format — Decided: JSON Validated by Pydantic

**Decision: JSON definition files, validated by Pydantic models** in
`services/warehouse/metadata.py`. Pydantic ships with FastAPI, so this adds no dependency,
and every validation error carries its field path. YAML (PyYAML is not a dependency) and
annotated SQL DDL (needs a parser and brings back hand-written SQL) were not taken.

**Compliance fields are part of the format in M8 (C03, C09).** Every table carries
`personal_data`, `legal_basis` (the six-value C03 enum) and `retention_policy_days`.
Validation rejects a personal-data table without either field. The nightly job that acts on
them is deferred to M11 (item 1).

**One design point carried into M8W28T2:** `dim_date` is derived from
`orders.created_at`, not read from a source table, so it has no native column types for the
`Dict[str, str]` shape. M8W28T2 defines how a derived dimension is declared and records it
in the contract.

### 3. M7 Closure — Confirmed Closed

- **Criteria 13–15: ☑ Done.** Criterion 13: PR #35 merged `develop` into `main` on 11
  November, and on 18 November both branches were confirmed identical at `dba7b47`.
  Criterion 14: the M8 kickoff documents, this file and `SUBOP_Milestone_8.docx`.
  Criterion 15: the M7 report was sent to Emrah. Reports are emailed, not committed, so
  this one was confirmed verbally, the same treatment as earlier milestones.
  `m7_completion_checklist.docx` is updated to match under M8W28T1.
- **Latency KPI: deferred into M8**, as recorded in the checklist. It is validated under
  M8W29T4 by the protocol in item 4.
- Carried items, each with an owner:

  | Item | Owner | Target |
  |---|---|---|
  | Latency instrumentation and KPI validation | Abdalla | M8W28T4, M8W29T4 |
  | CDC Latency KPI card live wiring | Beyza | M8W29T8 |
  | Replication-slot lifecycle, incl. M7W27T1 Finding 2 | Omer | M8W28T10 |
  | Restart and resume verification | Mert | M8W28T11 |
  | Halt hidden while Connect is down | Abdalla | M8W28T5 (backend), M8W28T8 (UI, Beyza) |
  | CI live-CDC capability | Omer | M8W29T10 |
  | Overview trend lines are fixed text | Beyza | M9 |
  | Production CORS origin (M6 Criterion 7) | Omer | When a deployment target exists |
  | Data Quality rule engine | Team | M10 |

### 4. KPI Protocols — Decided 18 November

Not discussed at the sync. Decided by Abdalla on 18 November, before any measurement code
exists, so the conditions are fixed before the runs and are not changed afterwards.

**4a. CDC latency under 30 seconds (M8W29T4).**

- **Measure:** t4 − t0, plus the four hops, from `cdc_meta.event_latency`. The five points
  are the CDC Design Note's: t0 `payload.source.ts_ms`, t1 top-level `payload.ts_ms`, t2
  the Kafka message timestamp, t3 when `poll()` returns, t4 after the upsert commits.
- **Two conditions, reported separately.** The active result never stands in for the idle
  one.
  - **Idle:** no other writes. One change at a time. The next change is made only after the
    previous event's t4 is recorded, plus a 5-second pause.
  - **Active:** a fixed background load from `cdc_demo_changes.py` running in a loop, one
    change every 2 seconds. The script makes a single change and exits today, so a
    `--loop` / `--interval` option is added under M8W28T4.
- **Sample size: 30 counted events per condition.**
- **Warm-up:** after the stack starts, one warm-up event is sent and recorded, but not
  counted. This keeps the first-topic delay (M7W27T1 Finding 2, up to about five minutes)
  out of the sample. It is reported next to the results, not hidden. Its fix is Omer's
  M8W28T10 proposal (item 5).
- **Pass rule: p95 of t4 − t0 under 30 000 ms**, set per condition. Min, median, p95, max
  and the count over 30 s are always reported, unrounded, with the SQL committed alongside.
- **Clock:** single-host Compose, so skew is effectively zero (Design Note Section 2.4).
  The record states this assumption.
- **If idle misses,** it is recorded as not met, with its cause and a resolution plan.

**4b. DW schema automation 80% faster than manual (M8W29T3).**

- **One written spec, committed before either half starts.** It is a target star schema
  different from the demo: one fact table and three dimensions, about 20–25 columns, with
  one SCD Type 2 dimension.
- **Abdalla does both halves, generated half first.** One person removes the skill gap two
  people would bring. Doing the generated half first gives any "already learned the schema"
  advantage to the manual half, so a pass is never inflated.
- **Timing:** the spec is read once, untimed. Then each half is timed from its first
  keystroke until its tables exist without errors. Fixing errors counts in both halves.
  Start and end timestamps are recorded.
  - Generated: writing the JSON definition plus running the generator, into `dw`.
  - Manual: hand-written `CREATE TABLE` DDL, into a separate `dw_manual` schema.
- **Equality check:** both schemas are compared through `information_schema`: tables,
  columns, types, nullability, primary and foreign keys. They must match, or the timing
  comparison means nothing.
- **Pass rule:** generated time ≤ 20% of manual time. The ratio is recorded unrounded, with
  who did each half and in which order.

### 5. Team, Critical Path and Cut Order

- **Split confirmed: 40 / 40 / 10 / 10** (Abdalla / Beyza / Omer / Mert). Omer and Mert
  have one task each per week, off the critical path, and nothing depends on either.
- **Abdalla carries the whole critical path:** the generator, SCD, the warehouse API, both
  KPIs, the latency instrumentation and the closure. Accepted.
- **Cut order if Week 29 slips (decided 18 November):**
  1. `m9_kickoff_notes.md` Part A moves to Tuesday 1 December, M9's first day.
  2. The SCD Type 2 loader is carried to the M9 window by name. Its charter criterion then
     closes as not met, with an owner and target, not as Done.
  - **Trigger:** if the SCD loader is not green in CI by **Friday 27 November**, the cut
    order starts.
  - **Never cut:** the generator, the API, either KPI run, the checklist, the merge or the
    report.
- **Two Abdalla steps made explicit (decided 18 November):**
  - Omer's `topic.metadata.refresh.interval.ms` proposal (M8W28T10) is applied to
    `kafka_consumer.py` by Abdalla in **M8W29T1**, alongside that task's image rebuild.
    `kafka_consumer.py` is on the critical path, so only Abdalla edits it.
  - Omer's `cdc-live.yml` PR (M8W29T10) is reviewed by Abdalla in Week 29, before the
    develop → main merge (M8W29T6).

### 6. Beyza's M8 Scope

Not discussed at the sync. Taken from Part A item 6 and the Week 28–29 plan (M8W28T6–T9,
M8W29T7–T9): the Warehouse Schemas page, shell-first against fixtures in Week 28 and live
in Week 29; the CDC latency types, strip and KPI card; the Connect-down
state; i18n in `tr.ts` and `en.ts` from the first commit; and the M8 frontend handoff that
M9 starts from. Only colour tokens defined in `index.css` are used.

**What M8 does not cover:** BI dashboards (M9), the Data Quality rule engine (M10), MySQL
CDC (M11), and the items deferred in item 1.

### 7. Close and Schedule

- **Part B is late.** It is committed 18 November, not 16 November. So the two contracts
  that gate Beyza's week are re-dated: `warehouse_api_contract.md` by **Wednesday 18
  November EOD** (was Tuesday 17), and the latency shape in `cdc_api_contract.md` by
  **Thursday 19 November** (was Wednesday 18). Both are written before the code they
  describe.
- `SUBOP_Milestone_8.docx` is final for option (A) and the decisions above.
- Advisor reporting: one report at M8's close, emailed to Emrah by Monday 30 November.

### Action Items

| Owner | Action | Due |
|---|---|---|
| Abdalla | Part B, final charter, M7 checklist Criteria 13–15 (M8W28T1) | Wed 18 Nov |
| Abdalla | Metadata models, demo star definition, `warehouse_api_contract.md` (M8W28T2) | Contract Wed 18 Nov EOD |
| Abdalla | Latency shape in `cdc_api_contract.md` (M8W28T4) | Thu 19 Nov |
| Abdalla | Schema generator + `pg_types.py` (M8W28T3) | Fri 20 Nov |
| Abdalla | Latency instrumentation incl. `cdc_demo_changes.py --loop` (M8W28T4) | Week 28 |
| Abdalla | Halt visibility while Connect is down (M8W28T5) | Week 28, after T4 |
| Abdalla | Warehouse API + apply Omer's refresh-interval value (M8W29T1) | Tue 24 Nov |
| Abdalla | SCD Type 1 & 2 loader (M8W29T2); cut-order trigger | Thu 26 Nov; trigger Fri 27 Nov |
| Abdalla | Both KPI runs by item 4's protocols (M8W29T3, T4) | Week 29 |
| Abdalla | Review Omer's `cdc-live.yml` PR | Week 29, before the merge |
| Abdalla | M8 checklist, M9 notes, merge, M8 report (M8W29T5, T6) | Mon 30 Nov |
| Beyza | Warehouse page, client, latency types, Connect-down state, i18n (M8W28T6–T9) | Week 28 |
| Beyza | Live swap, latency wiring, i18n parity, M8 handoff (M8W29T7–T9) | Week 29 |
| Omer | Slot lifecycle script + record (M8W28T10) | Week 28 |
| Omer | CI live-CDC workflow as a PR (M8W29T10) | Week 29 |
| Mert | Restart and resume verification (M8W28T11) | Week 28 |
| Mert | Second-person runbook reproduction (M8W29T11) | Week 29 |
