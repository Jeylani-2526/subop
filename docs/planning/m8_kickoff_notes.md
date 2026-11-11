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

*To be captured during the sync on 16 November 2026.*
