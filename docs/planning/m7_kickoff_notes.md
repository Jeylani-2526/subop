# SUBOP — M7 Kickoff Sync

---

## Part A — Agenda / Talking Points

**1. Omer capacity question — decide it here, don't carry it again (20 min)**
This question was first raised in Part A of `m6_kickoff_notes.md` ("is 5+ new connectors plus a test framework by end of October realistic at 20%?") and was never answered. It was carried as an open item in the Week 19, 20 and 21 plans, and moved here as the first agenda item so it is decided at the start of the milestone it affects most. M7's roadmap ownership is **Abdullah + Omer**, and Kafka/Debezium work is heavier than any M6 connector.
- Evidence from the four M6 weeks (as recorded in each week's plan and confirmed against `develop`):

  | Week | Planned for Omer | What happened |
  |---|---|---|
  | W18 | SQLite + CSV connectors | Both built and unit-tested, but not wired into the resolver or DSL validation — Abdullah wired them in W19 (M6W19T1). |
  | W19 | JSON + REST API connectors, conformance framework (first pass) | JSON reassigned to Abdullah (M6W19T2). REST API built but not wired — Abdullah wired it in W20 (M6W20T1). Conformance framework built by Abdullah in W20 (M6W20T2). |
  | W20 | Oracle connector only | Landed (M6W20T5). |
  | W21 | .env.example fix, 8+ KPI validation, clean-environment regression run | .env.example fix and KPI validation taken by Abdullah (M6W21T1, M6W21T3). Regression run assigned to Mert (M6W21T8). Omer owns the develop → main merge (M6W21T4). |

- Of the five M6 connectors, Omer built four (SQLite, CSV, REST API, Oracle). Two of those needed wiring by someone else before a pipeline could use them. The conformance framework and KPI validation, both named in his M6 charter scope, were done by Abdullah.
- **Mert** joins the team at **10%**, starting slowly with one task per week. Confirm whether his 10% adds to the team's capacity or shares the existing 20% line, and what kind of task suits his first M7 weeks (bounded, hands-on, well-scoped — same rule as Omer's).
- Decide one of three options. Part B records which one, with owners — not "carried again":
  - **(a) Keep 20%, bounded tasks.** Omer takes 1–2 bounded, hands-on tasks per week; Abdullah leads the CDC build.
  - **(b) Omer owns the infrastructure slice.** Omer owns the Debezium / Kafka Connect service and the Postgres replication config (item 4); Abdullah owns CDC event handling, delivery to the warehouse, and latency measurement.
  - **(c) Formally change M7 ownership.** Abdullah becomes primary owner, Omer supporting, and the change is stated in the Week 22 advisor report rather than handled as an unannounced workaround.

**2. Confirm M6 closure (10 min)**
- Walk through the ten M6 success criteria in `m6_completion_checklist.docx` one at a time. State plainly which are Done and which have a resolution plan. Don't round partial progress up to "done."
- Items expected to carry into M7 (**provisional** — to be reconciled with the final M6 checklist before the sync):
  - **Omer capacity question** — resolved in item 1 above, not re-carried.
  - **Data Quality hook** — still a stub; `/api/kpis` reports `average_quality_score: null`. Full implementation belongs to M10.
  - **Bilingual dashboard (TR/EN) remainder** — only if Beyza's Thursday 1 October fallback in M6W21T12 was triggered. Owner: Beyza.
  - **CI server-backed tests** — only if the postgresql/mysql/mssql/oracle legs of the conformance suite were not confirmed green by a CI run link.
  - **Anything the clean-environment regression run (M6W21T8) recorded as a failure** — including environment problems.
- Each carried item needs a named owner and a target week in Part B.

**3. M7 scope and the CDC latency KPI (20 min)**
Per `SUBOP_roadmap.docx`: **M7 — CDC & Real-Time Streaming Module, 5 Oct – 2 Nov 2026 (W22–W26), owned by Abdullah + Omer.** The Success Metrics table sets **CDC latency under 30 seconds, target end of November 2026**.
- **Date tension:** the KPI's end-of-November validation date sits after M7's 2 November end date — the same kind of gap the M6 kickoff flagged for the connector KPI. Decide explicitly: validate inside M7, or accept a validation window in early M8. Don't assume the dates line up.
- **First source database:** `.env.example` already names `DEBEZIUM_CONNECTOR_NAME=subop-postgres-cdc`, pointing to PostgreSQL. Confirm Postgres-first, and whether any other source is in M7 scope at all or deferred.
- **How latency is measured:** agree what "source change to warehouse delivery" means in practice — which timestamp starts the clock, which ends it, and where the number is recorded — before building, so the KPI is measured the same way every time.
- Confirm the headline M7 outputs, so each one is scoped as its own deliverable: the CDC capture pipeline, change-event handling into the warehouse, and a repeatable latency measurement.

**4. Infrastructure — what exists and what's missing (10 min)**
Confirmed on `develop`:
- **Present:** Zookeeper, Kafka and Kafka UI (`http://localhost:8080`) are defined in `docker-compose.yml`. The `KAFKA_*` and `DEBEZIUM_*` variables are already in `.env.example`.
- **Missing:** there is no Kafka Connect / Debezium service in `docker-compose.yml`. The Postgres service is not configured for logical replication (`wal_level=logical`), which Debezium needs to read changes. `services/cdc/` contains only a README.
- Decide: who adds the Debezium service and the Postgres replication config, and in which week. These block all other CDC work, so the default is Week 22. Owner depends on item 1's decision.
- Confirm the clean-environment and CI setup extends to these new services, so M7 doesn't repeat M6's pattern of code that works locally but isn't reachable in a fresh environment.

**5. Beyza's M7 scope and what M7 does not cover (10 min)**
- Confirm Beyza's M7 frontend scope, based on her `component_status_m6_handoff_v1.md`. Starting points:
  - The **CDC Latency** KPI card on `HomePage.tsx` currently shows "—" with "Coming in M7" — wiring it to a live value is the natural M7 frontend item, once the backend exposes one.
  - New screens built in M7 use the `src/i18n/` structure (Turkish default, TR/EN switch) from the start, with no hardcoded text.
- Name what M7 explicitly does not cover, so it isn't assumed by default: data warehouse schema automation (M8), BI dashboards (M9), data quality rule engine (M10).

**6. Close (5 min)**
- Confirm the M6 Completion Checklist is the shared reference for what's Done vs. deferred going into M7 — no re-opening settled items without new evidence.
- Confirm who writes Part B live during the sync — recommend Abdullah captures during the sync and shares the same day, as in M5 and M6.
- Confirm the Week 22 advisor report's due date (Sunday 11 October EOD), and that it states item 1's decision plainly.

---

## Part B — Kickoff Notes

**Attendees:** ☑ Abdullah ☑ Beyza ☑ Omer ☑ Mert (full team, including Mert's first kickoff)
**Held:** Week 22, w/c 5 October 2026. Captured live and shared the same day, per M5 and M6 practice.

### 1. Omer Capacity Question — Decided

**Decision: option (a).** Omer stays at 20%, working as Abdullah's hands-on partner on the
CDC build with one to two bounded, well-scoped tasks per week; Abdullah leads. Open since the
M6 kickoff and carried in the Week 19, 20 and 21 plans — closed here as a decision, not
carried a fifth time.

**What option (a) means in practice:** M7's roadmap ownership is Abdullah + Omer, and that
holds. Omer builds the CDC infrastructure layer directly — the Kafka Connect / Debezium
service and its verification this week, Debezium connector registration in Week 23 — which
is the infrastructure role the roadmap gives him. Abdullah owns the design decisions, the
replication configuration and the event-handling path, and sequences the work so each of
Omer's tasks lands against a dependency that is already in place.

**Evidence considered:** the four-week M6 reassignment table in Part A. Of the five M6
connectors Omer built four; the pattern the table shows is not capacity but sequencing —
work landed, then waited on wiring by someone else. Option (a) addresses that directly by
bounding each task and ordering the dependencies, rather than by reducing his share.

**Mert:** joins at 10%. Not assigned in Week 22, with no scope reason recorded — his first
M7 task is assigned in Week 23. **Open:** whether his 10% adds to team capacity or shares
the existing 20% line was not answered at this sync, and is carried to the Week 23 plan
with Abdullah as owner.

### 2. M6 Closure — Confirmed Status

- **Eight of ten criteria: ☑ Done.** `m6_completion_checklist.docx` confirmed present on
  `develop`. The 8 x 5 connector KPI matrix in Section 2 closes the roadmap's 8+ connector
  KPI inside M6, ahead of its end-of-October validation date.
- **Criterion 7 — production CORS origin: ☐ Pending, correctly.** No deployment target
  exists; `SUBOP_CORS_ORIGINS` lists only `localhost:5173` and `localhost:5174`. Owner:
  Omer. Target: Week 25, or whenever a deployment target appears. Not actionable in Week 22.
- **Criterion 9 — Week 21 / M6-closing advisor report: ☑ Confirmed sent.** Sent to Emrah on
  Sunday 4 October. Reports are emailed rather than committed, so this cannot be verified
  from the repository — confirmed verbally here, the same treatment Week 18 gave M5's
  Criterion 11. Criterion 9 closes.
- **Clean-environment regression run (M6W21T8): ☑ No failures recorded.** No environment
  problems, no carried findings.
- No other M6 loose end raised. The M6 Completion Checklist stands as the shared reference
  for Done vs. deferred — no re-opening settled items without new evidence.

### 3. M7 Scope and the CDC Latency KPI

- **First source database: PostgreSQL.** Confirmed, consistent with
  `DEBEZIUM_CONNECTOR_NAME=subop-postgres-cdc` already in `.env.example`. No second source
  is in M7 scope.
- **KPI date tension — decided: validate inside M7.** The roadmap's CDC-latency KPI carries
  an end-of-November validation date, after M7's 2 November end. Rather than accept a
  validation window in early M8, latency measurement is **pulled into Week 25**, so the KPI
  is validated inside the milestone that owns it.
- **How latency is measured: Architecture Section 5.2's four points are binding** — t0 WAL
  commit, t1 Debezium read, t2 Kafka publish, t3 consumer pickup, t4 warehouse write. Not
  re-derived here. Where each timestamp is read, and where the result is recorded, is fixed
  in the CDC Design Note v1 (M7W22T4).
- **Schema drift** stays Section 5.2's open fatal risk. M7W22T4 either defines handling or
  defers it with a named owner and target milestone.
- **Headline M7 outputs,** each scoped as its own deliverable: the CDC capture pipeline,
  change-event handling into the warehouse, and a repeatable latency measurement.
- **Week 26 boundary recorded:** M7 ends Monday 2 November while the project's Week 26 runs
  2–8 November. Accepted rather than renegotiated — Week 25 carries the substantive closure
  work, 2 November is a formal close only, and M8 still opens on 3 November.

### 4. Infrastructure — What Exists and What's Missing

Confirmed by direct audit of `develop` ahead of this sync, not assumed from Part A.

- **Present:** Zookeeper, Kafka 3.7 and Kafka UI (`http://localhost:8080`) in
  `docker-compose.yml` since M1; `KAFKA_*` and `DEBEZIUM_*` blocks in `.env.example`.
- **Missing — the two hard blockers:** no Kafka Connect / Debezium service in
  `docker-compose.yml`, and the `postgres` service runs at the default `wal_level=replica`,
  which carries no row-level change data for Debezium to decode. `services/cdc/` holds a
  README and no code.
- **Owners, per item 1's decision:** Postgres logical replication → Abdullah (M7W22T2),
  ahead of Connect so it starts against a WAL-ready Postgres. Kafka Connect / Debezium
  service → Omer (M7W22T6). Smoke verification → Omer (M7W22T7). Abdullah and Omer build
  the CDC layer together across M7; the split is by dependency order, not by seniority.
- **Clean-environment rule extends to the new services:** verification runs from
  `docker compose down -v` then `up -d`, not from an already-running developer machine —
  the gap M6W21T8 was created to catch.

### 5. Beyza's M7 Scope

Confirmed as scoped, with no additions: the six-page i18n pass (M7W22T8), the CDC Monitor
page shell (M7W22T9), the CDC Latency KPI card wiring prep (M7W22T10), and the corrected M6
component status handoff (M7W22T11). New screens use `src/i18n/` from the first commit, with
no hardcoded text, per the Week 21 bilingual decision.

**What M7 explicitly does not cover,** so it isn't assumed by default: data warehouse schema
automation (M8), BI dashboards (M9), data quality rule engine (M10).

### 6. Close

- Abdullah captures Part B during the sync and shares the same day. ☑ Done.
- Week 22 advisor report due **Sunday 11 October EOD**, stating item 1's decision plainly.

### Action Items

| Owner | Action | Due |
|---|---|---|
| Abdullah | Postgres logical replication config + `cdc_replication_setup.sql` (M7W22T2) | Week 22 |
| Abdullah | `StreamingConnectorBase` + `confluent-kafka` dependency (M7W22T3) | Week 22 |
| Abdullah | CDC Design Note v1 — latency points + schema-drift decision (M7W22T4) | Week 22 |
| Abdullah | Week 22 advisor progress report (M7W22T5) | Sun 11 Oct EOD |
| Abdullah | Resolve whether Mert's 10% adds to or shares the 20% line | Week 23 plan |
| Omer | Kafka Connect / Debezium service in `docker-compose.yml` (M7W22T6) | Week 22 |
| Omer | Connect smoke verification, commands and output verbatim (M7W22T7) | Week 22 |
| Omer | Production CORS origin (M6 Criterion 7) | Week 25 / on deployment target |
| Beyza | Six-page i18n pass, CDC Monitor shell, KPI card prep, handoff correction (M7W22T8–T11) | Week 22 |
| Mert | First M7 task — scope to be set | Week 23 |
| Abdullah + Omer | CDC build runs as a pair across M7 — Abdullah sequences, Omer builds infrastructure | M7 (W22–W26) |