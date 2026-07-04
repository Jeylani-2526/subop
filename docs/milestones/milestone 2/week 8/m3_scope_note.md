# SUBOP · Milestone 3 · Week 8 Scope Note

**Task:** M3W8T1 · Owner: Abdullah · 29 June 2026
**Path (updated convention — see Section 1 note):** `docs/milestones/milestone 3/week 8/m3_scope_note.md`

---

## 1. M2 GitHub Closure Status

A live audit was run against the `subop` repository (both `main` and `develop` branches, probed directly via `raw.githubusercontent.com` and a full repo tree pull) rather than relying on the Week 7 checklist assumption. Two findings changed the picture from "M2 backlog is empty" to "M2 is substantially closed, with three real gaps":

**Path convention correction — no action required, convention updated:**
The repo's actual folder structure uses spaces (`docs/milestones/milestone 2/week 5/`), not the hyphenated convention written into our planning docs (`milestone-2/week-5`). The working branch is also named `develop`, not `dev`. These are not backlog failures — every W5–W7 document that appeared "missing" under the old path assumption is in fact present under the real path. **Effective immediately, all future GitHub path references (starting with Milestone 3) should use the real convention: spaces in folder names, `develop` as the branch.** This note itself is filed under the corrected path above.

**Filename drift — accepted as-is, logged for awareness:**
Five Week 5/6 deliverables are committed under different filenames than originally specified in the task plan (e.g. `m2_scope_note.md` → `M2W5T1_Scope_Note.docx`; `db_abstraction_research_notes.md` → `abstraction_layer_research_v1.docx`). Content-wise these are treated as the same deliverables under different names — no rework needed. Going forward, task plans should reference actual committed filenames once known, rather than the filename specified before the work began.

**Genuine outstanding items (confirmed missing on both `main` and `develop`):**

| Item | Status | Owner | Resolution Deadline |
|---|---|---|---|
| `tests/test_mysql_connector.py` | Missing (404) — flagged blocking since Week 7, still unresolved | Omer | Before M3W8T9 sign-off (5 July) |
| `docs/milestones/milestone 2/MILESTONE2_COMPLETE.md` | Never created | Omer | 5 July |
| Week 5 advisor report | Not committed anywhere in repo | Abdullah | Retroactive — attach note in Week 8 advisor report; not blocking M3 |

**Confirmed good news:** `.github/workflows/ci.yml` and `lint.yml` already exist on `main` (lint + pytest against a Postgres service container). This resolves the open CI/CD scope question from the Week 7 advisor report — a pipeline did exist before Week 8, and it is a reasonable baseline for Omer to extend rather than a from-scratch build.

**M2 closure verdict:** Substantively closed. The two remaining Omer items (test file, completion registry) do not block M3 architecture writing and will close alongside this week's CI/CD and MSSQL work.

---

## 2. Five Open Architecture Questions M3 Must Resolve

Pulled directly from `connector_summary_m4_prep_v1.md` (Section 4):

1. Should the connector framework support only synchronous execution, or should asynchronous execution also be supported for connectors such as Kafka and REST APIs?
2. Should all connectors expose the same public interface, or should connector-specific methods (e.g. `subscribe()` for Kafka) be introduced through interface extensions?
3. How should non-relational data sources such as MongoDB be integrated while preserving a consistent abstraction layer designed primarily for SQL-based connectors?
4. Should connector-specific features (REST pagination, Kafka subscriptions, MongoDB document operations) be implemented within individual connectors, or standardized through shared abstraction components?
5. What common result format and error-handling strategy should be adopted to ensure consistent behavior across all supported connectors regardless of underlying technology?

These are the direct agenda for Architecture Document Sections 4–6 (M3W8T3 — module interfaces, data flow, API contracts).

---

## 3. M3 Week-by-Week Plan

| Week | Focus |
|---|---|
| **W8 (29 Jun–5 Jul)** | Architecture Document foundation: system layers, tech stack lock, module interfaces, data flow, API contract sketches (Sections 1–6). Frontend project setup + 2 shared components. CI/CD clarification + MSSQL foundation. |
| **W9 (6–12 Jul)** | Architecture Document Sections 7–9: deployment topology, security architecture (RBAC/audit/KVKK boundary), M3 conclusion. Three more frontend components. MSSQL connector completion (execute_query/execute_write + 5 tests). |
| **W10 (13–19 Jul)** | M3 finalization: architecture document review and sign-off, M3 completion checklist, M4 kickoff readiness confirmation across all three connector foundations. |

---

## 4. Four Architecture Decisions to Formally Lock This Week

Each is already supported by M2 research; this section makes the lock official and citable for the advisor and the architecture document.

| Decision | Locked Choice | Basis |
|---|---|---|
| **Database abstraction pattern** | Adapter pattern (`ConnectorBase` abstract class) | Feasibility Report Final v1, Section 2.2 — SQLAlchemy ORM and custom DSL formally rejected; Adapter pattern already proven in the PostgreSQL and MySQL prototypes |
| **Frontend stack** | React 18 + Tailwind CSS (+ Vite, TypeScript) | Confirmed in UI Shell Architecture Plan (M2 Week 6); consistent with Design System v1 |
| **API framework** | FastAPI | Carried from M1 technical requirements; confirmed as the target for all module API contract sketches (M3W8T3) |
| **Warehouse target** | PostgreSQL 15 | ClickHouse formally removed; BI layer queries PostgreSQL directly (Architecture Doc Section 2, Warehouse Layer) |

---

## 5. Reference: M2 Module Feasibility Ratings (from Feasibility Report Final v1)

For traceability into the architecture document's design-principle sections:

| Module | Milestone | Rating |
|---|---|---|
| Connector Framework | M4/M6 | HIGH |
| Database Abstraction Layer | M4 | MEDIUM-HIGH |
| ETL Engine | M5 | HIGH |
| CDC / Real-Time Streaming | M7 | HIGH WITH RISK (highest-risk module — Kafka/Debezium skill gap) |
| Metadata-Driven Data Warehouse | M8 | MEDIUM (most novel, least externally precedented) |
| BI Dashboard & OLAP | M9 | HIGH |
| Data Quality | M10 | HIGH |
| Lineage & Catalog | M10 | MEDIUM (graph rendering complexity) |
| Security & Compliance / RBAC | M11 | MEDIUM-HIGH |

---

*Share this note in the team task board before any architecture writing begins (M3W8T2).*
