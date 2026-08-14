# SUBOP — M5 Kickoff Sync

---

## Part A — Agenda / Talking Points

**1. Confirm M4 closure (10 min)**
- Walk through the nine M4 success criteria (Milestone 4 doc) one at a time — state plainly which are Done and which are open. Don't let partial progress get rounded up to "we're done."
- Repo audit ahead of this sync (main and develop, both current) shows real progress beyond what Week 13's opening audit found:
  - `type_mapping.py` and `abstraction_layer.py` are now both present in `services/abstraction/` on both branches.
  - The `retryable` attribute is now present on `ConnectorError` for all three connectors (PostgreSQL, MySQL, MSSQL) — confirmed directly in `postgres_connector.py`.
- **One criteria are still open as of this sync — say so explicitly:**
  - **Zero-code-change demonstration:** no `demo_zero_code_change.py` exists in the repo yet. Ask Omer to confirm today's/this week's date for presenting it live — do not treat this criterion as Done until the live run happens.
 

**2. Review the ETL Engine input/output contracts and module boundaries (15 min)**
Walk through `etl_engine_contracts_v1.md` (docs/data-layer/) section by section — this is the full draft, not the Week 11 outline (which is now marked Superseded and points here):
- **Inputs (Section 2):** pipeline definitions via API, dialect-and-type-normalized row batches from the Abstraction Layer, CDC change events via Kafka, and — newly resolved since the outline — a read-once-at-creation compliance check against Security & Compliance for `processing_purpose`, `data_subject_categories`, `transfer_recipients`. Flag for the team: this is a creation-time check only, not a per-run dependency, so it doesn't sit in the hot path.
- **Outputs (Section 3):** transformed batches to the Warehouse, a synchronous Data Quality hook before every write, Lineage metadata (now including per-column type-mapping conditions), and run-status/metrics via the API.
- **Abstraction Layer boundary (Section 4):** ETL Engine never opens a direct DB connection or knows the dialect underneath — confirm the team is aligned that this constraint is non-negotiable for M5 implementation.
- **CDC boundary (Section 5):** streaming is a separate input path from batch; idempotency (upsert by PK + timestamp) is required, not optional, because Kafka delivery is at-least-once.
- **Governance hooks (Section 6):** Data Quality runs synchronously pre-write; Lineage is recorded as part of the same write step, not an afterthought pass.

**3. Confirm the Universal Type Mapping boundary question is resolved (10 min)**
This was the Week 11 outline's open item (Section 7 of the outline) — confirm out loud that it's now closed, not just documented:
- **7.1 — Where coercion happens:** inside the Abstraction Layer, invisible to ETL Engine, per the interface sketch's `execute_query()` flow. Same invisibility guarantee as dialect normalization, just extended to value types.
- **7.2 — How a lossy mapping surfaces:** the six mapping conditions split into two behaviors, not one:
  - `direct` / `inexact` / `ambiguous` / `conditional` / `fallback` → not errors, not routed to Data Quality — recorded as Lineage metadata on the transform step.
  - `unsupported` → a non-retryable `ConnectorError`, using the exact same shape ETL Engine already handles for connection/query/write errors. No new error-handling code path required.
- Ask the team directly: does anyone see a gap in this split, or does M5 implementation start clean against it?

**4. Confirm M5 scope readiness (10 min)**
- Confirm with Omer: the Abstraction Layer's public contract (`execute_query`/`execute_write`, `ConnectorError` shape) is stable enough that M5 can build against it without expecting breaking changes.
- Confirm with Beyza: per `component_status_m5_handoff_v1.md`, the concrete M5 data-wiring surface is —
  - `PipelinesPage` Zone 3 (execution log, row counts) → API
  - `HomePage` KPISummaryCard (pipeline count, quality score) → API
  - `DataTable` → server-side pagination
  - `CatalogBrowserPage` → AssetCard catalog API
  - Ask if this list is complete or if anything changed since that document was written.
- Name what M5 deliberately does **not** cover yet (Section 9 of the contracts doc): transformation DSL syntax, retry/backoff timing values, and CDC schema-drift handling (carried forward, flagged as M5/M7 concern). Confirm the team agrees these stay out of scope for the kickoff.

**5. Close (5 min)**
- Confirm the M4 Completion Checklist finalization date (should land after this week's demonstration).
- Confirm the M4 final advisor report is still on track for Sunday 9 August EOD.
- Confirm who owns writing up Part B below live — recommend Abdullah captures during the sync, shares same day.

---

## Part B — Kickoff Notes (fill in during/after the sync)

**Attendees:** ☐ Abdullah ☐ Beyza ☐ Omer
*(To be checked off live — not assumed here.)*

### M4 Closure — Confirmed Status

- **Abstraction layer implementation (Omer): ☑ Landed in repo, pending live demonstration.**
  Evidence: `type_mapping.py` and `abstraction_layer.py` present in `services/abstraction/` on both `main` and `develop`; `retryable` attribute present on `ConnectorError` for all three connectors. Verified directly against the live repo ahead of this sync, not assumed from the plan.

- **Zero-code-change demonstration (Omer): ☐ NOT yet confirmed — open.**
  Evidence: no `demo_zero_code_change.py` found in the repo as of this sync. Per Abdullah's check ahead of the meeting, the demo is scheduled to be presented live at the next team sync — do not mark this M4 success criterion Done until that happens.

- **CI status (Omer): _to be confirmed live_ — clean-environment run against the full suite, independent of the demo.**

- **VERBİS / naming-ambiguity closure (Abdullah): ☑ Confirmed Finalized.**
  Both `verbis_interface_proposal_v1.md` and `naming_ambiguity_resolution_v1.md` are Status: Finalized on `main`.

- **ETL Engine contracts (Abdullah): ☑ Confirmed full draft, ready for M5.**
  `etl_engine_contracts_v1.md` exists on `main` as a full draft; the Week 11 outline is correctly marked Superseded and points to it.

- **Frontend components / shell (Beyza): ☑ Confirmed built and wired**, per repo audit and `component_status_m5_handoff_v1.md`.

- **M4 Completion Checklist (Abdullah): ☐ Not yet written — correctly scheduled for after the demonstration, not before.**

- Any other M4 loose end raised in the sync: _to be filled live_

### ETL Engine Contracts — Team Alignment Check
- Any conflict or concern raised against Sections 2–6 (inputs, outputs, Abstraction Layer / CDC / Governance boundaries)? ☐ *To be confirmed live — no record of this discussion exists yet.*

### Universal Type Mapping Boundary — Resolution Confirmed
- Team agrees the Section 7 split (Lineage metadata for `inexact`/`ambiguous`/`conditional`/`fallback`; non-retryable `ConnectorError` for `unsupported`) is final and requires no new ETL Engine error-handling code: ☐ *To be confirmed live.*

### M5 Scope — Readiness Check
- Abstraction Layer contract confirmed stable for M5 to build against (Omer): ☐ *To be confirmed live.*
- Frontend data-wiring surface confirmed complete per `component_status_m5_handoff_v1.md` (Beyza): ☐ *To be confirmed live.*
- Out-of-scope items for M5 (transformation DSL syntax, retry/backoff timing, CDC schema-drift) — team agrees these stay out: ☐ *To be confirmed live.*
- Any new dependency or risk raised in discussion: _to be filled live_

### Action Items
| Owner | Action | Due |
|---|---|---|
| Omer | Present zero-code-change demonstration live in team sync | Next sync |
| Omer | Confirm clean-environment CI run (full suite) independent of demo | Next sync |
| Abdullah | Write M4 Completion Checklist once demonstration is confirmed | This week, after demo |
| Abdullah | Send M4 final advisor report & M5 readiness summary | Sun 9 Aug EOD |
| Beyza | Confirm data-wiring surface list is current, flag any changes | This sync |
| _team_ | Confirm no objections to ETL Engine contracts Sections 2–7 as binding for M5 | This sync |


