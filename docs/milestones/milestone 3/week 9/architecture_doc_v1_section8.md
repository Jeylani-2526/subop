# SUBOP Architecture Document v1
**Section 8 of 9 · Owner: Abdullah · Draft date: 9 July 2026**


---

## Section 8 — Security Architecture

### 8.1 RBAC Model — Permission Matrix

The four SUBOP user roles were established in Milestone 1 (`user_requirements_v1.docx`, M1W2T4; `user_role_matrix.md`, M1W2T11): **Data Engineer**, **BI Analyst**, **Platform Admin**, **Viewer**. The matrix below extends that page-level access matrix down to module-level permissions, since Section 8 needs to bind roles to the 10 SUBOP modules defined in Section 4, not just to UI pages.

**Permission levels:** `Admin` (full control — create, edit, delete, configure) · `Write` (create/edit within the module, no delete/configure) · `Read` (view only) · `None` (no access; requests rejected by RBAC middleware with a 403)

| Module | Data Engineer | BI Analyst | Platform Admin | Viewer |
|---|---|---|---|---|
| 1. Connector Framework | Write | None | Admin | None |
| 2. Database Abstraction Layer | Write | None | Admin | None |
| 3. ETL Engine | Write | None | Admin | None |
| 4. CDC / Real-Time Streaming | Write | None | Admin | None |
| 5. Metadata-Driven Data Warehouse | Write | Read | Admin | None |
| 6. BI Dashboard & OLAP | Read | Write | Admin | Read *(published dashboards only)* |
| 7. Data Quality | Write | Read | Admin | Read *(score summaries only)* |
| 8. Data Lineage | Read | Read | Admin | None |
| 9. Data Catalog | Read | Read | Admin | Read |
| 10. Security & Compliance | None | None | Admin | None |

**Rationale for the notable rows:**
- **BI Analyst gets `None` on Connector Framework, Abstraction Layer, ETL Engine, and CDC** — directly enforces the Milestone 1 constraint that the BI Analyst "cannot configure ETL pipelines" (M1W2T11). This is a hard boundary, not a UI-level hint: the RBAC middleware rejects these calls at the API layer regardless of what the frontend shows.
- **Data Engineer gets `Write`, not `Admin`, everywhere in the pipeline path** — Data Engineers configure and run their own pipelines and connectors but cannot delete another engineer's connector configuration or reassign RBAC roles; that escalation path belongs to Platform Admin only.
- **Viewer's `Read` on BI Dashboard and Data Quality is explicitly scoped** ("published dashboards" / "score summaries") per the Milestone 1 definition — a Viewer cannot open the BI Report Builder itself (that surface is gated to BI Analyst `Write` and above) or see per-rule quality violation detail, only the aggregate score.
- **Data Catalog is `Read` for every non-admin role** — consistent with the Week 2 dashboard pages list marking Data Catalog as accessible to all roles; it is deliberately the most open module short of Admin, since browsing metadata (not the underlying data) carries low risk.
- **Security & Compliance is `None` for every role except Platform Admin** — user management, RBAC configuration, and audit log visibility are Platform Admin's defining responsibility (M1W2T4) and are not partially delegated to any other role.

### 8.2 Authentication Flow

**Login and JWT issuance:**
1. User submits credentials to `POST /api/auth/login` (Section 6, Module 10).
2. On success, the Security & Compliance module issues two tokens: a short-lived **access token** (JWT, 15-minute expiry) carrying the user's `role` claim, and a longer-lived **refresh token** (7-day expiry), following the sync/threadpool execution model locked in Section 3.5 (Question 1).
3. The access token is the sole artifact RBAC middleware inspects on every subsequent request — the `role` claim inside it is what the permission matrix in §8.1 is checked against.

**Token refresh:**
- The refresh token is stored in an `httpOnly`, `Secure` cookie — never in `localStorage` or JavaScript-accessible storage, to limit exposure if the frontend is compromised by XSS.
- When an access token expires, the frontend calls `POST /api/auth/refresh`; the server validates the refresh token, issues a new access token, and **rotates** the refresh token (invalidating the old one) to limit the damage window if a refresh token is ever intercepted.
- If the refresh token itself is expired or invalid, the user is redirected to `/login` — this is the same `PrivateRoute` guard already scaffolded in Beyza's Week 8 routing setup (M3W8T5), not a new component.

**How AppShell attaches bearer tokens:**
- The access token is held in memory inside a React auth context that wraps `AppShell` (not in `localStorage`, for the same XSS-exposure reason as the refresh token).
- A shared API client (a single configured `fetch`/`axios` instance used by every page component) attaches `Authorization: Bearer <token>` to every outgoing request via a request interceptor — individual pages never handle token attachment themselves, which keeps this concern in one place as the remaining seven pages get wired in future milestones.
- On a `401 Unauthorized` response, the client interceptor attempts one silent token refresh and retries the original request once; a second `401` after that triggers the redirect-to-`/login` path described above, rather than looping indefinitely.

### 8.3 Audit Log Design

**Logged actions** (union of the task's baseline list and the KVKK/GDPR checklist's audit requirements, C08/C10):
- Login attempts (success and failure)
- Connector configuration changes (create, update, delete)
- Dashboard exports
- Permission changes (role assignment or modification by Platform Admin)
- Data subject rights requests (access, rectification, erasure, restriction, objection, portability export — C05–C07)
- Bulk or anomalous data access on any table flagged `personal_data: true` (the breach-detection trigger for C08)

**Log schema:**

| Field | Type | Notes |
|---|---|---|
| `timestamp` | ISO 8601 datetime | Event time, not log-write time, if they ever diverge |
| `user_id` | string | The authenticated principal; `system` for automated jobs (e.g., the nightly retention enforcement job in §8.4) |
| `action_type` | enum | e.g., `login_success`, `login_failure`, `connector_create`, `connector_update`, `connector_delete`, `dashboard_export`, `permission_change`, `subject_access_request`, `subject_erasure_request`, `bulk_access_anomaly` |
| `target_resource` | string | The specific connector ID, dashboard ID, user ID, or table name affected |
| `record_count` | integer, nullable | Populated for data-access events (per KVKK/GDPR C10); null for events like login or permission changes |
| `ip_address` | string | Required by C10's audit log specification |
| `result` | enum | `success` \| `failure` |

**Immutability:** the audit log is append-only — no `UPDATE` or `DELETE` operations are exposed on it through any API, including to Platform Admin. This is a direct implementation of the KVKK/GDPR checklist's requirement (C06) that audit trail records be *anonymised, not deleted*, even when the erasure right (C06) is exercised on the underlying subject data itself: the fact that an erasure happened stays in the audit trail; the personal data it references does not.

**Retention policy:** Proposed at **24 months**, after which entries are anonymised (user_id and IP address stripped, action metadata retained) rather than deleted outright — this preserves long-horizon accountability evidence (relevant to both KVKK Art. 12 and GDPR Art. 5(2) accountability principle) without indefinitely retaining identifiable access records. This is a proposed figure for team/advisor sign-off, not yet a locked decision — flagging it as such rather than presenting it as settled.

### 8.4 KVKK/GDPR Compliance Boundary

This section maps the unified compliance checklist (C01–C10, `kvkk_gdpr_compliance_notes.md`) onto the architecture already defined in Sections 1–7, rather than restating the checklist itself.

**Which modules touch personal data:**

| Module | Personal Data Touchpoint | Checklist Item(s) |
|---|---|---|
| Connector Framework | Point of extraction — the only place data minimisation can happen *before* personal data enters the platform at all | C01 |
| ETL Engine | Carries the declared `processing_purpose` on every pipeline run; the point where purpose-limitation is enforced in-flight | C02 |
| Metadata-Driven Data Warehouse | Stores `legal_basis` and `retention_policy_days` per table; runs the nightly retention enforcement job | C03, C06 (retention side), C09 |
| BI Dashboard & OLAP | Never receives personal data — only masked/aggregated output, per the RBAC + masking boundary below | C10 (masking enforcement point) |
| Data Catalog | Documents retention periods and last-erasure-run dates for personal-data tables, human-readable | C09 |
| CDC / Real-Time Streaming | Touches personal data if the replicated source table contains it (e.g., a `customers` table streamed via Debezium) — inherits the same minimisation and masking obligations as batch, not a separate regime | C01, C10 |
| Security & Compliance | The implementation home for the data subject rights API, consent tracking, and breach detection | C04, C05, C06 (API side), C07, C08 |

**Masking and anonymisation — connector layer vs. warehouse layer:**

These are two different mechanisms solving two different problems, and Section 8 needs to keep them distinct rather than treating "masking" as one undifferentiated control:

- **Connector layer (data minimisation, not masking):** `ConnectionConfig` carries a `declared_fields` list (C01); the connector raises `ComplianceError` if a table flagged `personal_data: true` has no declared fields. This is the strongest possible control — a field never extracted can never leak downstream — and it is enforced once, at ingestion, rather than repeatedly at every read.
- **Warehouse/query layer (role-based masking):** For fields that *are* legitimately stored (because some role needs them — e.g., a Data Engineer needs a customer's raw email for pipeline debugging, but a Viewer should never see it), masking is applied server-side at query execution time, keyed to the RBAC role in the requester's JWT (§8.1's permission matrix, combined with a column-level policy). The BI Dashboard module in particular must never receive unmasked PII in its query results unless the requesting role is explicitly entitled to it — this is what makes `BI Dashboard: Write` for BI Analyst in §8.1 safe despite BI Analysts having no direct connector/warehouse admin rights: the masking happens beneath the module they do have access to, not as something they configure themselves.

The practical distinction: connector-layer minimisation decides *what enters the warehouse at all*; warehouse-layer masking decides *what a given role sees of what's already there*. Both are required — minimisation alone doesn't help once a field is legitimately needed by at least one role, and masking alone doesn't reduce what's stored (and therefore doesn't reduce breach exposure, C08).

**VERBİS registration mapping:**

VERBİS requires a controller to register, per processing activity: purpose, data subject categories, data categories, retention period, and recipients. SUBOP's architecture already produces three of these five as structured metadata rather than free-text documentation, which is the direct payoff of locking C02/C03/C09 into the ETL Engine and Warehouse schemas now rather than deferring them to M11/M12:

| VERBİS Required Field | SUBOP Source |
|---|---|
| Processing purpose | ETL Engine's `processing_purpose` pipeline field (C02) |
| Data categories | Connector Framework's `declared_fields` (C01), mapped to the KVKK data category taxonomy (M12 documentation task) |
| Retention period | Warehouse's `retention_policy_days` field (C09) |
| Data subject categories | Not yet captured as structured metadata — **open item**, see below |
| Recipients of transferred data | Not yet captured as structured metadata — **open item**, see below |

**Open item flagged for M4/M5 scope, not resolved here:** two of the five VERBİS fields (data subject categories, transfer recipients) have no current home in the module interface contracts from Section 4. Rather than force a placeholder answer into this section, this is being carried forward explicitly as something the M4 connector work and M5 pipeline DSL should account for, so the M12 VERBİS template export isn't attempting to reconstruct this information after the fact from unstructured sources.

---
