# SUBOP — M6 Kickoff Sync

---

## Part A — Agenda / Talking Points

**1. Confirm M5 closure (10 min)**
- Walk through the twelve M5 success criteria (`m5_completion_checklist.docx`) one at a time — state plainly which are Done and which are open. Don't let partial progress get rounded up to "we're done."
- Ten of twelve are Done as of the checklist's writing (Week 17). Two are carried forward, not silently closed:
  - **Lineage integration** — `lineage_store.py` itself is built and unit-tested, but the executor never actually populates it on a real run (`execute_query()` is called without `column_types`, so a run's lineage list is unconditionally empty today). This has a named resolution plan already — see item 2 below.
  - **Week 17 advisor report** — confirm with Abdullah it was sent by Sunday 6 September EOD before formally calling M5 closed.

**2. Two items deferred from M5 — first order of business, not background context (20 min)**
Both were surfaced during Week 16/17 audits and explicitly deferred to this kickoff rather than resolved quietly. Neither is "M6 must build this" by default — each needs an actual decision from the team:
- **Lineage `column_types` wiring:** the gap is that `executor.py`'s `_read_source()` never supplies `column_types` to `AbstractionLayer.execute_query()`, so lineage capture is a no-op regardless of what data flows through a pipeline. Decide: does this get fixed early in M6 (before real connector work compounds on top of it), or does it wait for M9's dedicated Lineage module? Owner if fixed now: Abdullah.
- **CatalogBrowserPage → AssetCard wiring:** never scoped into any M5 week despite being named in the original M5 kickoff's data-wiring surface list. Per Beyza's `component_status_m6_handoff_v1.md`, its actual content milestone is M9 (Catalog), not M6 — so the decision here isn't "build it in M6," it's confirming the team still agrees M9 is correct and this isn't a dropped commitment.
- **DSL's `mongodb` connector_type:** `pipeline.py`'s validation currently accepts `"mongodb"` as a valid `connector_type` even though no MongoDB connector exists anywhere in `services/connectors/`. Decide one of two ways: (a) build a MongoDB connector as part of M6's connector expansion, which would also directly serve item 3 below, or (b) remove `mongodb` from the validated set until a connector exists, so the DSL doesn't silently accept pipelines it can't run. Recommend deciding this in the same conversation as item 3, since building it may be the more efficient path.

**3. Review the roadmap's 8+ connector KPI (15 min)**
Per `SUBOP_roadmap.docx`'s Success Metrics table: **8+ working connectors, owned by Omer, target end of October 2026** — which is inside this milestone's window (M6: 7 Sep – 4 Oct 2026, per the roadmap's own milestone table — flag this date tension with the team; the KPI's end-of-Oct target sits after M6's stated end date and should be reconciled explicitly, not assumed to align).
- Current count: **3 connectors built** (PostgreSQL, MySQL, MSSQL), all confirmed live since M4.
- The roadmap's own "Key Differentiator" line names the target connector surface: PostgreSQL, MySQL, MSSQL, Oracle, files, and APIs — plus MongoDB if item 2's decision goes that way. Confirm with Omer which specific connectors he intends to build toward the 8+ target, since the roadmap doesn't enumerate all eight explicitly.
- The 12-month timeline also names a **connector test framework** as one of M6's two headline outputs (alongside the 8+ connectors themselves) — confirm this is scoped as its own deliverable, not assumed to fall out of individual connector test suites.
- Ask Omer directly: at 20% workload, is 5+ new connectors plus a test framework by end of October realistic, or does this need to be renegotiated now rather than discovered as a shortfall in Week 20 or 21?

**4. Confirm M6 scope and ownership split (10 min)**
- Per the roadmap, M6 (Connector Ecosystem Expansion) is the first milestone with **Omer as primary owner**, a shift from M4/M5 where Abdullah carried most hands-on technical work. Confirm out loud what this means for the team's workload split this milestone — does Abdullah's role shift toward architecture/review, or does he continue building alongside Omer as in Weeks 15–17?
- Confirm Beyza's M6 scope: per her M6 handoff doc's "Frontend Priorities" section, mounting `PipelineCreationForm` into `PipelinesPage`, adding the connection-ref env vars needed for pipelines to actually reach `succeeded`, and a responsive-design pass are already named as next steps — confirm these are M6 (not M7+) scope.
- Name what M6 explicitly does not cover, so it isn't assumed by default: CDC latency work (M7), dashboard/BI work (M9), data quality rule engine (M10) — all out of scope here even though this milestone's connector work touches the same codebase.

**5. Close (5 min)**
- Confirm the M5 Completion Checklist is the team's shared reference for what's Done vs. deferred going into M6 — no re-litigating settled items without new evidence.
- Confirm who owns writing up Part B live during the sync — recommend Abdullah captures during the sync, shares same day, consistent with M4→M5 and M5's own retroactive Part B practice.
- Confirm the Week 18 advisor report's due date and who's presenting the connector-count progress to Emrah given Omer's primary ownership this milestone.

---

## Part B — Kickoff Notes (fill in during/after the sync)

*To be completed live at the M6 kickoff sync.*
