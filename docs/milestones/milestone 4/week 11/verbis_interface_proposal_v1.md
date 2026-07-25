# VERBİS Interface-Placement Proposal (Draft v1)

**Owner:** Abdullah · **Status:** Draft — shared for team review Wednesday 22 July; finalized as a formal Architecture Document addendum in Week 12.
**Source of the open item:** Architecture Document s8.4, s9.3 (item 2) — carried forward from Milestone 3.

---

## 1. The Gap

VERBİS requires a controller to register five fields per processing activity: purpose, data subject categories, data categories, retention period, and recipients of transferred data. Three of the five already have a structured home in SUBOP's module contracts:

| VERBİS Field | Current Source | Module |
|---|---|---|
| Processing purpose | `processing_purpose` pipeline field | ETL Engine (Module 3) |
| Data categories | `declared_fields`, mapped to KVKK taxonomy | Connector Framework (Module 1) |
| Retention period | `retention_policy_days` | Warehouse (Module 5) |
| **Data subject categories** | **No structured home** | — |
| **Transfer recipients** | **No structured home** | — |

The two missing fields aren't a gap in *data availability* — they're a gap in *where the contract lives*. Without a designated home, M12's VERBİS template export would have to reconstruct these from unstructured documentation after the fact, which is exactly the failure mode s8.4 flags as worth avoiding now rather than in M11/M12.

## 2. Proposed Home: Security & Compliance (Module 10)

**Recommendation:** add both fields to the Security & Compliance module's interface contract, as part of the same compliance-metadata surface that already produces audit log entries and RBAC access decisions.

**Why this module and not the others:**

- **Consistency with Section 1's core constraint #4** — "the security layer wraps the entire platform... KVKK/GDPR compliance is a platform property, not a patchwork of module-level exceptions." VERBİS registration is compliance metadata, and Security & Compliance is the one module already designed to aggregate compliance concerns across every other module rather than owning a single pipeline stage. Putting these two fields anywhere else would recreate the per-module patchwork the architecture was explicitly built to avoid.
- **It's the natural aggregation point.** Purpose, data categories, and retention period are each produced as a side effect of a different module doing its normal job (ETL, Connector Framework, Warehouse). Data subject categories and transfer recipients don't have an equivalent "normal job" that produces them as a side effect — they need to be explicitly registered. Security & Compliance is the only module whose stated purpose is to collect exactly this kind of cross-cutting metadata (it already does this for audit log entries).
- **Avoids a second source of truth.** Section 4 states module contracts are binding — "no module may depend on another module's internal implementation beyond what's listed here." If these fields lived in, say, the Data Catalog (which *searches* metadata rather than originating it), we'd need a separate mechanism to keep Catalog's copy in sync with wherever the authoritative registration actually happens. Housing both fields where compliance data already converges avoids that duplication.

**Alternatives considered and rejected:**

| Alternative | Why rejected |
|---|---|
| ETL Engine's `processing_purpose` field (extend it) | Conflates two different concerns — `processing_purpose` describes *why* a pipeline runs; data subject categories and transfer recipients describe *who's affected* and *where data goes*. These are properties of the processing activity as a whole, not of a single pipeline execution, and pipelines can be rerun/rescheduled independently of registration status. |
| Data Catalog | Catalog is a downstream, read-oriented index (search over already-known metadata) — it's a consumer of compliance metadata, not the module that should originate it. |
| Connector Framework's `declared_fields` (C01) | `declared_fields` answers "what data leaves the source" (minimization) — a different question from "who are the data subjects" or "who receives transferred data." Overloading it would blur a control that's currently doing one job cleanly. |

## 3. Proposed Contract Addition (Module 10 — Security & Compliance)

Two new fields, populated at the point a processing activity is registered (pipeline creation/config time, alongside where `processing_purpose` is already captured):

```
data_subject_categories: List[str]
  # e.g. ["customers", "employees", "vendors"]
  # Tagged per processing activity at registration time.

transfer_recipients: List[str]
  # e.g. ["BI Dashboard export", "external-analytics-partner"]
  # Captured wherever a processing activity crosses a boundary
  # (BI export, external API integration, third-party handoff).
```

Both fields join the existing audit-log/compliance record Security & Compliance already produces per processing activity, alongside `processing_purpose`, `declared_fields`, and `retention_policy_days` sourced from their respective modules. This keeps VERBİS export (M12) a matter of reading one consolidated record rather than joining across five modules after the fact.

## 4. Status & Next Step

This is a **draft placement proposal**, not a finalized interface change — shared for team review at Wednesday's sync. If no conflicts are raised, this becomes a formal addendum to Architecture Document s4/s8 in Week 12, alongside the parallel Week 12 work already scoped for these fields.
