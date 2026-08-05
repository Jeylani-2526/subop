# Naming-Ambiguity Resolution Note (v1)

**Owner:** Abdullah · **Status:** ✅ Finalized — applied to `docs/architecture/architecture_doc_v1.md` and all other current-facing docs. Originally shared for team review Wednesday 22 July; formally closed out in Week 12 (Milestone 4).
**Source of the ambiguity:** Architecture Document s9.1 (Decision 4), s2.5, s4 (Module 6), s6 (API), s7.2, s8.

---

## 1. The Ambiguity

SUBOP's architecture uses the term **"OLAP"** in several places even though ClickHouse — the one piece of infrastructure that would have made "OLAP" a literally accurate label — was formally excluded from the architecture:

| Location | Current wording |
|---|---|
| s2.5 (layer name) | "**Analytics Layer**" — purpose: "Self-service BI dashboard builder and **OLAP-style views**" |
| s4 (Module 6 name) | "**BI Dashboard & OLAP**" |
| s6 (API base path) | `/api/bi` — endpoint `POST /api/bi/query — run an ad-hoc **OLAP query**` |
| s7.2 (service dependency table) | "**BI Dashboard & OLAP**" |
| s8 (RBAC matrix, masking table) | "**BI Dashboard & OLAP**" (repeated in two tables) |
| s9.1 (Decision 4, the closing statement) | "'OLAP Layer' naming is retained in Section 2 to describe analytical *query behavior*, not a claim that a dedicated OLAP engine exists" |

s9.1 already acknowledges the tension directly — the term is kept deliberately, but flagged as needing a caveat every time it's read, which is itself the sign it should be resolved rather than re-explained indefinitely. There's also a second-order inconsistency worth naming: s2.5 calls the layer "**Analytics Layer**," while s4, s7.2, and s8 all call the same thing "**BI Dashboard & OLAP**" — two different names for what is, per the module table, one module (Module 6). The "OLAP" question and the "which name is canonical" question are really the same fix.

## 2. Proposed Resolution

**Retire "OLAP" from module/section naming; standardize on "Analytics."**

- **Module 6** renamed from "BI Dashboard & OLAP" → **"BI Dashboard & Analytics"** — this also resolves the s2.5/s4 naming mismatch, since s2.5's layer is already called "Analytics Layer."
- s2.5's "OLAP-style views" → **"analytical views"**
- s6's "run an ad-hoc OLAP query" → **"run an ad-hoc analytical query"**
- s7.2 and s8's table references to "BI Dashboard & OLAP" → **"BI Dashboard & Analytics"**, matching the renamed module everywhere it's referenced.

The API base path itself (`/api/bi`) doesn't need to change — "bi" was never OLAP-specific, so it's already accurate and requires no correction.

## 3. Rationale

- **Accuracy without losing meaning.** "Analytics" describes the same query behavior s9.1 was protecting — dashboards, self-service views, aggregate queries against PostgreSQL — without implying a dedicated OLAP engine that was explicitly rejected in the same decision record.
- **Removes a caveat that would otherwise recur indefinitely.** As written, every future reference to "OLAP" in this document (or in downstream artifacts that cite it) needs the same explanatory footnote s9.1 already had to add. A rename removes the need for the caveat rather than repeating it.
- **One name per module.** Standardizing on "Analytics" also fixes the s2.5-vs-s4 naming split — Module 6 has one canonical name everywhere it's referenced, matching the layer name already in use in s2.5.

## 4. Conflict Check

Confirmed no conflict with:
- **`ConnectorBase`/mixin naming** (`StreamingConnector`, `PaginatedConnector`, `DocumentConnector`) — unrelated namespace, no overlap.
- **Other module names** (Connector Framework, Database Abstraction Layer, ETL Engine, CDC/Real-Time Streaming, Metadata-Driven Data Warehouse, Data Quality, Data Lineage, Data Catalog, Security & Compliance) — "Analytics" doesn't collide with or shadow any of these.
- **s9.1's own Decision 4 wording** — the underlying decision (PostgreSQL 15, ClickHouse excluded) is unchanged; only the naming used to describe the BI/Analytics module and its query behavior is affected.

## 5. Status & Close-Out

This resolution was shared for team review at the Wednesday 22 July sync; no conflicts were raised. The renames described above (Module 6, section 2.5, section 6, section 7.2, section 8) were applied to `architecture_doc_v1.md` and verified as part of Week 12 close-out: the current document uses "Analytics" consistently throughout, with exactly one intentional, explanatory "OLAP" mention remaining in Decision 4 (section 9.1), which correctly cites this addendum. No residual unexplained "OLAP" references remain anywhere in the current-facing architecture document.

This addendum is formally **Finalized** as of Week 12. Separately: the mislabeled cross-reference found in section 9.2 (Question 3 answer cites "Module 3" for the Abstraction Layer, which is actually Module 2 per section 4) is a plain correction rather than a naming decision, and was called out separately in the Week 11 advisor report rather than bundled into this note.
