# SUBOP Frontend — M6 Handoff: Component & Page Status

---

## 1. API Client Layer

### `services/bi-dashboard/frontend/api/pipelinesClient.ts`

| Function                       | Status  | Endpoint                                     |
| ------------------------------ | ------- | -------------------------------------------- |
| `getPipelines(page, pageSize)` | ✅ Live | `GET /api/pipelines/?page={n}&page_size={n}` |
| `createPipeline(payload)`      | ✅ Live | `POST /api/pipelines/`                       |
| `getRunStatus(id, runId)`      | ✅ Live | `GET /api/pipelines/{id}/runs/{run_id}`      |
| `getKPISummary()`              | ✅ Live | `GET /api/kpis`                              |
| `getCatalogAssets()`           | ⏳ Mock | Catalog endpoint coming in M9/M10            |

**Types:**

- `ConnectorType` — 8 values: `postgresql | mysql | mssql | sqlite | csv | json | rest_api | oracle` (mongodb removed M6W18T3)
- `RunStatus` — 6 values: `pending | running | succeeded | completed_with_quarantine | failed | cancelled`
- `PaginatedPipelines` — `{ items, total, page, page_size }`
- `KPISummary` — `{ pipeline_count, rows_processed_today, average_quality_score, connector_count? }`

---

## 2. Component Status

### `components/StatusBadge.tsx`

**Status: ✅ Built — 5 Variants**

| Variant                     | Color    | Trigger                     |
| --------------------------- | -------- | --------------------------- |
| `running`                   | Blue     | `running`                   |
| `completed`                 | Green    | `succeeded`                 |
| `failed`                    | Red      | `failed`                    |
| `warning`                   | Orange   | `pending`, `cancelled`      |
| `completed_with_quarantine` | Orange ⚠ | `completed_with_quarantine` |

---

### `components/PipelineRow.tsx`

**Status: ✅ Built — Responsive Card-Stack**

- Card-stack layout below 900px (`useWindowWidth` hook)
- Default row layout at 900px and above
- `StatusBadge` reused for status display
- `selected` state with left border highlight

---

### `components/DataTable.tsx`

**Status: ✅ Built — Responsive Card-Stack**

- Card-stack layout below 900px
- Default table layout at 900px and above
- `useWindowWidth` hook — same pattern as PipelineRow
- Generic `DataTableColumn<T>` interface with optional `render` function

---

### `components/KPISummaryCard.tsx`

**Status: ✅ Built — Live Data**

- Props: `label`, `value`, `unit?`, `trend`, `trendValue`, `status`
- Status → left border color + background tint
- Trend → arrow + color (up=green, down=red, neutral=grey)
- i18n: labels passed as props from parent (already translated)

---

### `components/AppShell.tsx`

**Status: ✅ Built — Responsive + i18n**

- Mobile header (hamburger, ≤767px)
- Mobile nav overlay with click-outside close
- TR/EN language toggle in header (single button, toggles on click)
- `useT()` hook integrated
- Header box-shadow for depth

---

### `components/NavigationSidebar.tsx`

**Status: ✅ Built — Responsive + i18n**

- Icons on all nav items — visible in tablet icon-only mode
- `className="subop-sidebar"` for CSS responsive control
- Tablet (768–1279px): 56px wide, icons only, labels hidden
- Mobile (≤767px): hidden, shown via overlay
- `useT()` — all labels translated via `TranslationKey`
- Hover state via CSS (`.subop-sidebar a:hover`)

---

### `components/PipelineCreationForm.tsx`

**Status: ✅ Built — Live API + i18n**

- `POST /api/pipelines/` — live submit
- 8 connector types (mongodb removed)
- 400 → DSL validation error displayed
- 422 → VERBIS error on processing_purpose field
- 201 → success message, `onSuccess()` called after 1.2s
- Loading state — button disabled during submit
- `useT()` — all labels, placeholders, errors translated

---

## 3. Page Status

### `HomePage.tsx`

**Status: ✅ Live — 5 KPI Cards**

| KPI Card                | Source                                    | Status                                   |
| ----------------------- | ----------------------------------------- | ---------------------------------------- |
| Active Pipelines        | `GET /api/kpis` → `pipeline_count`        | ✅ Live                                  |
| Data Quality Score      | `GET /api/kpis` → `average_quality_score` | ✅ Live — null shows "Not available yet" |
| Records Processed Today | `GET /api/kpis` → `rows_processed_today`  | ✅ Live                                  |
| CDC Latency             | —                                         | ⏳ M7                                    |
| Connectors              | `GET /api/kpis` → `connector_count`       | ✅ Live — from registry                  |

**i18n:** All KPI labels and trend values translated via `useT()`.

---

### `PipelinesPage.tsx`

**Status: ✅ Live — Full API + i18n + Responsive**

| Zone                  | Content                                                   | Status                                            |
| --------------------- | --------------------------------------------------------- | ------------------------------------------------- |
| Zone 1 — Filter Bar   | Search, time filter, status filter, refresh, new pipeline | ✅ Functional                                     |
| Zone 2 — Left Panel   | Pipeline list (paginated)                                 | ✅ Live — `GET /api/pipelines/`                   |
| Zone 3 — Detail Panel | Metadata, row count, execution log                        | ✅ Live — `GET /api/pipelines/{id}/runs/{run_id}` |

**Mobile (≤767px):**

- "New Pipeline" button hidden
- Read-only banner shown
- Zone 2 stacks above Zone 3

**i18n:** All labels, placeholders, messages translated via `useT()`.

---

### Other Pages — Shell Only ⏳

| Page                | File                      | Status     | Milestone |
| ------------------- | ------------------------- | ---------- | --------- |
| DataQualityPage     | `DataQualityPage.tsx`     | Shell Only | M10       |
| LineageExplorerPage | `LineageExplorerPage.tsx` | Shell Only | M9        |
| CatalogBrowserPage  | `CatalogBrowserPage.tsx`  | Shell Only | M9        |
| BIReportsPage       | `BIReportsPage.tsx`       | Shell Only | M11       |
| AdminPage           | `AdminPage.tsx`           | Shell Only | M8        |
| UsersPage           | `UsersPage.tsx`           | Shell Only | M8        |

---

## 4. i18n System

**Location:** `services/bi-dashboard/frontend/src/i18n/`

| File                   | Purpose                        |
| ---------------------- | ------------------------------ |
| `tr.ts`                | Turkish translations (default) |
| `en.ts`                | English translations           |
| `LanguageProvider.tsx` | Context + `useT()` hook        |

**Behaviour:**

- Turkish is default
- Language saved to `localStorage` (`subop_language`)
- Missing TR key falls back to EN
- Missing EN key falls back to key string
- `localStorage` reads/writes wrapped in try/catch

**How to add a new translated text:**

1. Add key to `tr.ts` and `en.ts` with same key name
2. Import `useT` in the component: `const { t } = useT();`
3. Use: `t("your_key")`

---

## 5. Design System Tokens

**File:** `services/bi-dashboard/frontend/src/index.css`

| Token                | Value                 | Usage                        |
| -------------------- | --------------------- | ---------------------------- |
| `--color-primary`    | `#1b3a6b`             | Header, Sidebar, Filter Bar  |
| `--color-secondary`  | `#2e75b6`             | Active nav, buttons          |
| `--color-success`    | `#2e7d32`             | Completed badge, healthy KPI |
| `--color-warning`    | `#e65100`             | Warning badge, quarantine    |
| `--color-danger`     | `#c62828`             | Failed badge, critical KPI   |
| `--color-success-bg` | `rgba(46,125,50,0.1)` | Added M5                     |
| `--color-warning-bg` | `rgba(230,81,0,0.1)`  | Added M5                     |
| `--color-danger-bg`  | `rgba(198,40,40,0.1)` | Added M5                     |
| `--color-background` | `#f9fafb`             | Page background              |
| `--color-surface`    | `#ffffff`             | Card background              |
| `--color-border`     | `#dde4ee`             | General borders              |
| `--color-row-alt`    | `#ebf3fb`             | Alternate rows, info boxes   |

**Responsive Breakpoints:**

- Desktop ≥1280px — sidebar 240px, 5-column KPI grid
- Tablet 768–1279px — sidebar 56px icon-only, 3-column KPI grid
- Mobile ≤767px — sidebar hidden, hamburger overlay, read-only, 1-column KPI grid

---

## 6. M7 Frontend Priorities

1. **CDC Latency KPI** — `cdc_latency_ms` field coming in M7; add to `KPISummary` type and HomePage
2. **Catalog endpoint** — `getCatalogAssets()` mock → live (M9)
3. **Shell pages** — DataQuality (M10), Lineage (M9), Catalog (M9), BI Reports (M11), Admin (M8)
4. **PipelineCreationForm mount check** — currently in PipelinesPage Zone 3 on desktop only
5. **i18n remaining** — shell page labels not yet translated (listed as M7 item)

---

_Last updated: 29 September 2026 — Beyza Ülkümen_
