# SUBOP — M4 Kickoff Sync


---

## Part A — Agenda / Talking Points

**1. Confirm M3 closure (5 min)**
- State plainly: all 6 M3 success criteria are met per this week's Completion Checklist.
- Two items were flagged rather than fully closed — say so out loud, don't let them get lost in the "we're done" framing:
  - CI/CD lint fix on `mssql_connector.py` — confirm with Omer it landed.
  - `develop` → `main` merge for the frontend (5 components, 8 pages) — confirm with Beyza it's merged, or agree on a date.

**2. Walk through the four locked architecture decisions (10 min)**
Read these out from Architecture Document s9.1 — the point is alignment, not re-litigation:
1. Adapter pattern (`ConnectorBase` + optional mixins) for database abstraction.
2. React 18 + Tailwind CSS for the frontend.
3. FastAPI for the backend API.
4. PostgreSQL 15 as the sole warehouse target (ClickHouse excluded).

Ask each teammate: *"Does anything in your planned M4 work conflict with these, or assume something different?"* — this is the moment to catch a mismatch before Week 11 code gets written against a wrong assumption.

**3. Name the open items M4 needs to carry (5 min)**
- **CDC schema-drift / metadata-format gap** (Architecture Doc s2.4, s5.2, s9.3) — no design yet for handling source schema changes mid-stream. Ask Omer: does M4's connector schema-introspection work need to leave room for this, even before it's designed?
- **VERBİS fields** (s8.4, s9.3) — two compliance metadata fields with no interface home yet. Lower urgency; note it and move on unless someone flags a conflict.

**4. Align on Week 11 scope (10 min)**
- M4 = connector abstraction layer build-out, against the interfaces confirmed this week.
- Ask Omer: what's the first concrete connector task for Week 11 — extending the three existing connectors to the full mixin pattern, or starting a new connector type?
- Ask Beyza: does Week 11 involve any frontend work, or is this a backend-heavy milestone for her (per the 40/40/20 split, confirm workload allocation hasn't silently shifted)?
- Confirm: any dependency between Beyza's/Omer's Week 11 work and Abdullah's M4 documentation tasks?

**5. Close (2 min)**
- Confirm next advisor report date (following Friday/Sunday cadence).
- Confirm who owns writing up the filled kickoff notes (Part B below) — recommend Abdullah captures live, shares in team chat same day.

---

## Part B — Kickoff Notes (fill in during/after the sync)

**Attendees:** ☐ Abdullah ☐ Beyza ☐ Omer
*(To be checked off live — not assumed here.)*

### M3 Closure — Confirmed Status

- **CI/CD lint fix (Omer): ☑ Confirmed landed.**
  Evidence: Black formatting check run directly against `services/connectors/mssql_connector.py` on `main` — clean, no violations. Verified against the live repo, not just the checklist entry.

- **develop → main merge (Beyza): ☐ Partially confirmed — NOT fully closed.**
  Evidence:
  - Components: 5/5 present on `main` (AppShell, DataTable, KPISummaryCard, NavigationSidebar, StatusBadge). ✅
  - Page files: 8/8 present on `main` (Home, Admin, Catalog, Lineage, Pipelines, Quality, Reports, Users). ✅
  - **Routing table: only 1 of 8 routes is wired.** `App.tsx` registers only `/` → `HomePage`; the other 7 pages exist as files but are unreachable — everything else falls through to a catch-all redirect back to Home.
  - **Decision: this is carried forward as an open, small fix-forward item for Week 11 — not closed at this sync**, matching what the M3 checklist itself already flagged as unresolved ("confirm full routing table before M3 sign-off").

- Any other M3 loose end raised in the sync: _to be filled live_

### Architecture Decisions — Team Alignment Check
- Any conflict or concern raised against the 4 locked decisions? ☐ *To be confirmed live at the sync — no record of this discussion exists yet, so this is intentionally left open rather than assumed clean.*

### Open Items Carried Forward
- CDC schema-drift gap — any M4 scope implication raised in discussion: _to be filled live (ask Omer per Part A, item 3)_
- VERBİS fields — any concern raised: _to be filled live; Abdullah's VERBİS interface-placement proposal (M4W11T2) is already scoped to open this regardless of what's raised here_

### Week 11 Scope — Agreed
*(Sourced from the Week 11 task plan's confirmed per-person assignments — not live-discussion-dependent.)*

- **Omer's first M4 task:** Write the Universal Type Mapping specification (canonical type set + per-connector mapping tables for PostgreSQL/psycopg2, MySQL/PyMySQL, MSSQL/pyodbc, with lossy mappings flagged) and sketch the unified abstraction-layer interface wrapping `ConnectorBase` + mixins (M4W11T8–T9).
- **Beyza's Week 11 involvement:** Frontend-facing, not backend-heavy — component catalog review and next-batch selection (Pipeline Row, Asset Card), their props interface drafts, and the Pipeline Monitor page-shell layout plan (M4W11T5–T7). 40/40/20 split holds; no silent shift.
- **Cross-dependencies flagged:**
  - Abdullah's ETL Engine contracts outline (M4W11T3) references the `List[Dict[str, Any]]` abstraction-layer format that Omer's interface sketch (M4W11T9) formalizes — explicitly noted as a boundary question to resolve jointly once the abstraction-layer prototype exists, not resolved this week.
  - Beyza's Pipeline Monitor shell plan (M4W11T6) reuses Navigation Sidebar and Data Table as already built in M3 — no dependency on Abdullah's or Omer's Week 11 outputs.
  - **New dependency from this sync:** the routing-table gap above means Beyza's Week 11 work should include wiring the remaining 7 routes — not previously in the Week 11 task list, added as a fix-forward item.

### Action Items
| Owner | Action | Due |
|---|---|---|
| Beyza | Wire remaining 7 routes (Admin, Catalog, Lineage, Pipelines, Quality, Reports, Users) into `App.tsx` routing table | Week 11 |
| Abdullah | Draft VERBİS interface-placement proposal + naming-ambiguity resolution note | Wed 22 July (share for team review) |
| Abdullah | Outline ETL Engine input/output contracts | This week (Week 11) |
| Omer | Present Universal Type Mapping spec draft | Wed 22 July |
| Beyza | Confirm next-batch component selection + share Pipeline Monitor shell plan | Wed 22 July |
| Abdullah | Send Week 11 advisor progress report | Fri 24 July EOD |

### Next Advisor Report Due
Date: **Friday 24 July 2026** (Week 11 report — M4W11T4)
