# SUBOP UI Component Pattern Library — First Draft

---

## 1. KPI Summary Card

**Screens:** Home / Overview, Data Quality Dashboard

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `label` | string | Yes | Metric name displayed above the value |
| `value` | string \| number | Yes | Primary display value |
| `trend` | `up` \| `down` \| `neutral` | No | Direction arrow next to trend text |
| `trend_text` | string | No | Short trend description (e.g. "+3 from yesterday") |
| `sub_text` | string | No | Secondary line below trend (e.g. "Updated 5 min ago") |
| `border_color` | token | Yes | Top border colour — one of: `color-primary`, `color-secondary`, `color-success`, `color-warning`, `color-danger` |
| `clickable` | boolean | No | If true, entire card is a link to the detail page |
| `href` | string | No | Target route when `clickable` is true |

**States:**

| State | Description |
|-------|-------------|
| Default | White surface, coloured top border, value and label visible |
| Hover | Border intensifies; cursor pointer (only when `clickable: true`) |
| Loading | Value replaced by skeleton bar; trend hidden |
| No data | Value shows `—`; trend hidden |

**Data (API fields consumed):**

| Field | Source endpoint |
|-------|----------------|
| Active pipeline count | `GET /api/v1/pipelines` |
| Rows processed today | `GET /api/v1/pipelines` |
| Average quality score | `GET /api/v1/quality/scores` |
| Active CDC stream count | `GET /api/v1/pipelines` |

**Notes:**
- `border_color` passed as token — never hardcoded per instance.
- KPI value font: `type-kpi-value` — 26px, weight 700.
- Trend arrow: ↑ for `up`, ↓ for `down`, no arrow for `neutral`.

---

## 2. Status Badge

**Screens:** Home / Overview, Pipeline Monitor, Data Quality Dashboard, Data Catalog

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `status` | `running` \| `completed` \| `failed` \| `pending` | Yes | Determines colour and label |
| `size` | `sm` \| `md` | No | `sm` = tables; `md` = detail headers. Default: `sm` |
| `show_icon` | boolean | No | If true, prepends status icon. Default: false |

**States:**

| Status | Label | Background | Text | Icon |
|--------|-------|------------|------|------|
| `running` | Running | `#EBF3FB` | `#1565A0` | ▶ |
| `completed` | Completed | `#E8F5E9` | `#2E7D32` | ✓ |
| `failed` | Failed | `#FFEBEE` | `#C62828` | ✗ |
| `pending` | Pending | `#F4F7FA` | `#3A4A5A` | ● |
| Disabled | — | 50% opacity | — | — |

**Data (API fields consumed):**

| Field | Source endpoint |
|-------|----------------|
| `status` | `GET /api/v1/pipelines` |

**Notes:**
- Display-only — never triggers an action.
- Border radius: `radius-full` always.

---

## 3. Pipeline Row

**Screens:** Home / Overview, Pipeline Monitor

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `pipeline_name` | string | Yes | Pipeline identifier |
| `source` | string | Yes | Source system name |
| `target` | string | Yes | Target system name |
| `status` | `running` \| `completed` \| `failed` \| `pending` | Yes | Passed to Status Badge |
| `rows_loaded` | number | No | Shown in Home table; hidden in Pipeline Monitor list |
| `duration` | string | No | Elapsed time string |
| `last_run` | string | No | Relative time string |
| `selected` | boolean | No | If true, applies selected state |
| `on_click` | function | Yes | Handler called on row click |

**States:**

| State | Description |
|-------|-------------|
| Default | White background; `color-border` bottom border |
| Hover | Background `color-neutral-light`; cursor pointer |
| Selected | Background `color-row-alt`; left border 3px solid `color-primary` |
| Loading | All fields replaced by skeleton bars |

**Data (API fields consumed):**

| Field | Source endpoint |
|-------|----------------|
| `id`, `name`, `source`, `target`, `status`, `rows_loaded`, `duration`, `last_run` | `GET /api/v1/pipelines` |

**Notes:**
- Pipeline Monitor: clicking a row updates the detail panel — no page navigation.
- Home table: clicking a row navigates to Pipeline Monitor with that pipeline pre-selected.

---

## 4. Data Table with Sort & Filter

**Screens:** Home / Overview, Pipeline Monitor, Data Quality Dashboard

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `columns` | Column[] | Yes | Each column has `key`, `label`, `width`, `sortable` |
| `rows` | object[] | Yes | Row data keyed to column `key` values |
| `row_component` | component | No | If provided, renders rows using that component |
| `empty_message` | string | No | Text shown when rows is empty |
| `loading` | boolean | No | Renders skeleton rows when true |
| `sortable` | boolean | No | Enables column header click sorting |

**States:**

| State | Description |
|-------|-------------|
| Default | `color-neutral-light` header; alternating rows with `color-row-alt` |
| Row hover | Background `color-neutral-light` |
| Sorted | Column header shows ↑ or ↓; text shifts to `color-primary` |
| Loading | Animated skeleton bars |
| Empty | Single row showing `empty_message` in `type-caption` centred |

**Data:** Column definitions and row data passed as props from parent page component.

**Notes:**
- Table does not fetch its own data.
- Sorting is client-side only for initial implementation.
- Maximum 10 visible rows; overflow scrolls vertically.

---

## 5. Asset Card

**Screens:** Data Catalog

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `asset_name` | string | Yes | Table or asset name |
| `source_system` | `oracle` \| `postgresql` \| `mysql` \| `csv` \| `mongodb` \| `cassandra` \| `kafka` \| `rest_api` | Yes | Determines source badge colour |
| `schema` | string | Yes | Database schema path |
| `owner` | string | Yes | Owner name or team |
| `quality_score` | number | Yes | Integer 0–100 |
| `last_updated` | string | Yes | Relative timestamp |
| `description` | string | No | Truncated at 120 characters |
| `selected` | boolean | No | Applies selected state |
| `on_click` | function | Yes | Opens detail panel |

**Quality score rules:**

| Score | Colour | Icon |
|-------|--------|------|
| 80–100 | `color-success` | ✓ |
| 50–79 | `color-warning` | ⚠ |
| 0–49 | `color-danger` | ✗ |

**Source badge colours:**

| Source | Background | Text |
|--------|------------|------|
| Oracle | `#FFEBEE` | `#C62828` |
| PostgreSQL | `#EBF3FB` | `#1565A0` |
| MySQL | `#FFF8E1` | `#E65100` |
| CSV | `#F3E5F5` | `#6A1B9A` |
| MongoDB | `#E8F5E9` | `#2E7D32` |
| Cassandra | `#FFF3E0` | `#E65100` |
| Kafka | `#E0F2F1` | `#00695C` |
| REST API | `#F4F7FA` | `#3A4A5A` |

**States:**

| State | Description |
|-------|-------------|
| Default | White surface, `shadow-sm`, `radius-md`, `color-border` border |
| Hover | Border `color-primary`; `shadow-md` |
| Selected | Border 2px solid `color-primary`; background `color-row-alt` |
| Loading | All fields replaced by skeleton bars |

**Data (API fields consumed):**

| Field | Source endpoint |
|-------|----------------|
| `name`, `source`, `schema`, `owner`, `quality_score`, `last_updated`, `description` | `GET /api/v1/catalog/search` |

---

## 6. Navigation Sidebar

**Screens:** All pages (persistent)

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `active_route` | string | Yes | Current page route — determines active item |
| `user_role` | `admin` \| `data_engineer` \| `bi_analyst` \| `viewer` | Yes | Controls admin section visibility |

**Navigation items:**

| Item | Route | Visible to |
|------|-------|-----------|
| Home | `/` | All roles |
| Pipeline Monitor | `/pipeline-monitor` | Admin, Data Engineer, BI Analyst |
| Data Quality | `/data-quality` | Admin, Data Engineer, BI Analyst |
| Lineage Explorer | `/lineage` | Admin, Data Engineer, BI Analyst |
| Data Catalog | `/catalog` | All roles |
| BI Report Builder | `/bi-builder` | Admin, BI Analyst |
| Admin Panel | `/admin` | Admin only |
| User Management | `/users` | Admin only |

**States:**

| State | Description |
|-------|-------------|
| Default item | 12px, `color-neutral-dark`, transparent background |
| Active item | `color-primary` background, white text, weight 600, left edge flush, `radius-sm` right edge |
| Hover item | `color-neutral-light` background, `color-primary` text |
| Collapsed (mobile) | Sidebar hidden; hamburger toggle in top nav bar |
| Section divider | 1px `color-border` between main pages and admin section |
| Admin label | 11px, uppercase, `color-neutral-light` background strip |

**Notes:**
- Admin items not rendered in DOM for non-admin roles — not just hidden.
- Sidebar width: 180px desktop; hidden on mobile (< 768px).
