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
- Ask directly: `services/cdc/README.md` lists "Omer to complete Kafka self-study during M5 (August)" as an M7 prerequisite. Did this happen? The answer affects which option below is realistic.
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

**Attendees:**

**Decisions confirmed:**

**Action items:**
