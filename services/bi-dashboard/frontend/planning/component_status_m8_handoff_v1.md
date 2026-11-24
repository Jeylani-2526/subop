# SUBOP Frontend — M8 Handoff: Component & Page Status (v1)

**Milestone:** M8, Weeks 28–29 · **Last updated:** 24 November 2026 — Beyza Ülkümen
**Branch:** `feat/m8w28-warehouse-page` · **Follows:** `component_status_m6_handoff_v1.md`
**Purpose:** the starting point for M9: what is live, what is still a shell, known gaps,
and the state of i18n.

---

## 1. API Clients

| Client | File | Status | Notes |
|---|---|---|---|
| `pipelinesClient` | `api/pipelinesClient.ts` | ✅ Live | `/api/pipelines` |
| `cdcClient` | `api/cdcClient.ts` | ✅ Live | `/api/cdc`; `CDCConnectUnavailableError` (503) handled |
| `warehouseClient` | `api/warehouseClient.ts` | ✅ Live | `/api/warehouse`; added in M8W28, live since M8W29 (fixtures removed) |

---

## 2. Shared Components

| Component | File | Status | Notes |
|---|---|---|---|
| `AppShell` | `components/AppShell.tsx` | ✅ Live | NavigationSidebar, header, `userRole` prop |
| `NavigationSidebar` | `components/NavigationSidebar.tsx` | ✅ Live | CDC and Warehouse links added in M8 |
| `StatusBadge` | `components/StatusBadge.tsx` | ✅ Live | CDC `op`, connector `state`, pipeline statuses |
| `KPISummaryCard` | `components/KPISummaryCard.tsx` | ✅ Live | `status: "healthy" \| "warning" \| "critical"` sets the border colour |
| `DataTable` | `components/DataTable.tsx` | ✅ Live | sorting, search, pagination |
| `PipelineRow` | inline in `HomePage.tsx` | ✅ Live | expandable row |

---

## 3. Pages

| Page | File | API | Status | Since |
|---|---|---|---|---|
| `HomePage` | `HomePage.tsx` | `pipelinesClient`, `cdcClient` | ✅ Live | M6 |
| `PipelinesPage` | `PipelinesPage.tsx` | `pipelinesClient` | ✅ Live | M6 |
| `CDCPage` | `CDCPage.tsx` | `cdcClient` | ✅ Live | M7 |
| `WarehousePage` | `WarehousePage.tsx` | `warehouseClient` | ✅ Live | M8 (shell W28, live W29) |
| `QualityPage` | `QualityPage.tsx` | — | 🔲 Shell | — |
| `LineagePage` | `LineagePage.tsx` | — | 🔲 Shell | — |
| `CatalogPage` | `CatalogPage.tsx` | — | 🔲 Shell | — |
| `ReportsPage` | `ReportsPage.tsx` | — | 🔲 Shell | — |
| `AdminPage` | `AdminPage.tsx` | — | 🔲 Shell | — |
| `UsersPage` | `UsersPage.tsx` | — | 🔲 Shell | — |

Shell pages show the `shell_coming_soon` key.

---

## 4. M8W29T8 — CDC Latency, Live

- `kpi_cdc_latency_pending` ("Goes live in M8") removed from `en.ts` and `tr.ts`.
- `kpi_cdc_latency_target: "< 30 s"` added, in both languages.
- `HomePage.tsx`, CDC Latency `KPISummaryCard`:
  - `trendValue={t("kpi_cdc_latency_target")}`
  - `status` follows the value: no value → `warning`; under 30 000 ms → `healthy`;
    30 000 ms or more → `critical`.
  - The value is `cdc_latency_ms` from `/api/kpis`: p95 of end-to-end latency over the
    newest 100 CDC events.
- `CDCPage.tsx` latency strip: each hop tile shows the real p95; with no data it shows the
  new `cdc_latency_no_data` key ("No data yet" / "Henüz veri yok").
- KPI validation (M8W29T4, `docs/planning/m8_kpi_validation.md` Section 2): p95
  649.85 ms idle and 648.95 ms active, against the 30 000 ms target.

---

## 5. M8W29T9 — i18n Audit

| Key | Files | Used by | Status |
|---|---|---|---|
| `app_name` | — | not used in source | ✅ Removed |
| `form_data_subjects_placeholder` | — | not used in source | ✅ Removed |
| `form_recipients_placeholder` | — | not used in source | ✅ Removed |
| `cdc_status_healthy` | — | not used in source | ✅ Removed |
| `cdc_status_warning` | — | not used in source | ✅ Removed |
| `cdc_status_error` | — | not used in source | ✅ Removed |
| `cdc_status_unknown` | — | not used in source | ✅ Removed |
| `warehouse_pending_notice` | — | banner retired with the live swap | ✅ Removed |
| `kpi_cdc_latency_pending` | — | replaced (Section 4) | ✅ Removed |
| `kpi_cdc_latency_target` | `en.ts`, `tr.ts` | `HomePage` CDC Latency card | ✅ Added |
| `cdc_latency_no_data` | `en.ts`, `tr.ts` | `CDCPage` latency strip, empty state | ✅ Added |
| `warehouse_scd_type1`, `warehouse_scd_type2` | `en.ts`, `tr.ts` | `ScdBadge` in `WarehousePage` | ✅ Now used (were hard-coded) |

**Method:** each key is searched in the `.ts`/`.tsx` sources, excluding `src/i18n/`. A
search of the built bundle cannot find unused keys, because the bundle contains the
dictionaries themselves.

**Result:** 128 keys; `tr.ts` and `en.ts` hold the same set; no unused keys.

---

## 6. WarehousePage

### Features
- Schema list (left panel) and table detail (right panel)
- Responsive: stacked layout below 900 px
- `ScdBadge` uses `warehouse_scd_type1` / `warehouse_scd_type2` (passed `t`)
- Compliance chips: `warehouse_badge_personal_data`, `warehouse_badge_legal_basis`,
  `warehouse_badge_retention`, with the six legal-basis labels
- Fact/dimension labels: `warehouse_fact_label` / `warehouse_dim_label`
- Read-only: generation is API-only in M8

### Known Gaps (for M9)
- Overview (`HomePage`) KPI trend lines are fixed text (carried from the M7 checklist)
- No schema versioning or diff view (the backend is deferred to the M9 window)
- No link from a column to lineage
- Retention is shown as a label only; nothing is computed from it

---

## 7. Design System Tokens

```css
--color-primary          /* #1B3A6B */
--color-surface
--color-border
--color-text
--color-text-muted
--color-row-alt          /* #EBF3FB */
--color-error / --color-error-bg
--color-warning / --color-warning-bg
```

Theme follows the operating system through `prefers-color-scheme` (dark by default, a
light override in `index.css`).

---

## 8. M9 Starting Point

M9 (1–28 December) is the **BI Dashboard & OLAP Layer** milestone (Goal G6): a
self-service dashboard builder that a user without SQL can operate in under 15 minutes.

### High priority (M9's goal)
- [ ] Dashboard builder: choose warehouse data, chart type and layout, then save
- [ ] Chart components (no chart library is installed yet)
- [ ] BI API client for the new backend endpoints
- [ ] Replace the fixed Overview trend lines with real values

### Medium priority
- [ ] `KPISummaryCard` sparkline support
- [ ] Configurable CDC latency alert threshold

### Low priority / later milestones
- [ ] `WarehousePage` schema versioning view (after the backend lands)
- [ ] `QualityPage`, `LineagePage`, `CatalogPage` (M10)
- [ ] Pipeline form as a multi-step wizard
- [ ] Mobile: card view for the `CDCPage` event feed

---

## 9. M8 Summary

| Week | Delivered |
|---|---|
| W28 | `WarehousePage` shell on fixtures; warehouse client and types; CDC latency types, `UNKNOWN` state and Connect-down halt banner; latency strip on live data; i18n keys for all new strings |
| W29 | `WarehousePage` live; HomePage CDC Latency card live with value-driven status; i18n audit (128 keys, none unused); this handoff |
