## 1. Build Strategy

The Phase 3 frontend follows a shell-first approach. Navigation structure, AppShell layout, and empty page shells are built during M5–M8 so that M9 (December 2026) becomes data wiring and chart integration rather than UI creation from scratch. This is the single most important time-saving decision for Phase 3 — it decouples frontend progress from backend API readiness and allows the team to validate routing, authentication guards, and component reuse before any live data exists.

Every page shell consists of three things only: the correct route, the AppShell layout zones (header, sidebar, content area), and a placeholder content block. No API calls. No chart rendering. No data fetching. Shell build is complete when navigation works correctly across all eight pages and all RBAC access guards reject unauthorised roles.

---

## 2. Page Shell Build Schedule

| Page | URL | Shell Build | Data Wiring | Auth Guard |
|------|-----|-------------|-------------|-----------|
| Home / Overview | `/dashboard` | M5 | M5 | Viewer+ (all roles) |
| Pipeline Monitor | `/pipelines` | M5 | M5 | Engineer+ (Admin, Data Engineer, BI Analyst) |
| Data Quality Dashboard | `/quality` | M6 | M6 | Engineer+ (Admin, Data Engineer, BI Analyst) |
| Lineage Explorer | `/lineage` | M6 | M6 | Analyst+ (Admin, Data Engineer, BI Analyst) |
| Catalog Browser | `/catalog` | M7 | M7 | Viewer+ (all roles) |
| BI Report Builder | `/reports/builder` | M7 | M8 | Analyst only (Admin, BI Analyst) |
| Admin Panel | `/admin` | M8 | M8 | Admin only |
| User Management | `/admin/users` | M8 | M8 | Admin only |

Shell build = empty layout + routing + auth guard only.
Data wiring = live API connection + chart rendering + real data.

---

## 3. Component Build Schedule

Shared components (used across multiple pages) are built first in M5. Page-specific components follow in the milestone when their page shell is built.

| Order | Component | Build Milestone | Pages | Dependency |
|-------|-----------|----------------|-------|-----------|
| 1 | Navigation Sidebar | M5 | All pages | None — first component built |
| 2 | Top Navigation Bar | M5 | All pages | None — built alongside sidebar |
| 3 | Button | M5 | All interactive pages | None |
| 4 | Status Badge | M5 | Home, Pipeline Monitor, Data Quality, Catalog | None |
| 5 | KPI Summary Card | M5 | Home, Data Quality | Status Badge |
| 6 | Data Table | M5 | Home, Pipeline Monitor, Data Quality | Status Badge |
| 7 | Pipeline Row | M5 | Home, Pipeline Monitor | Status Badge, Data Table |
| 8 | Activity Feed | M5 | Home | None |
| 9 | Progress Bar | M6 | Pipeline Monitor | None |
| 10 | Filter Bar | M6 | Pipeline Monitor, Data Quality | Status Badge |
| 11 | Execution Log | M6 | Pipeline Monitor | None |
| 12 | Detail Panel | M6 | Pipeline Monitor, Lineage, Catalog | None |
| 13 | Quality Rule Row | M6 | Data Quality Dashboard | Status Badge |
| 14 | DAG Node Graph | M7 | Lineage Explorer | D3.js |
| 15 | Filter Sidebar | M7 | Data Catalog | None |
| 16 | Asset Card | M7 | Data Catalog | Status Badge |
| 17 | Input Field | M8 | BI Report Builder, Admin Panel | None |
| 18 | BI Chart Canvas | M8 | BI Report Builder, Home | Chart.js, ECharts |

---

## 4. Dependency Notes

The following page shells cannot be wired to live data until their backend API endpoint group is available. This table maps each page to its blocking dependency.

| Page | Blocking API Dependency | Available From |
|------|------------------------|---------------|
| Home / Overview | `GET /api/v1/pipelines`, WebSocket `/ws/v1/monitor` | M5 — ETL Engine |
| Pipeline Monitor | `GET /api/v1/pipelines`, `GET /api/v1/pipelines/{id}/logs` | M5 — ETL Engine |
| Data Quality Dashboard | `GET /api/v1/quality/scores` | M7 — Data Quality Engine |
| Lineage Explorer | `GET /api/v1/lineage/{asset_id}` | M8 — Data Lineage |
| Data Catalog | `GET /api/v1/catalog/search` | M8 — Data Catalog |
| BI Report Builder | `GET /api/v1/warehouse/query` | M9 — BI Dashboard Layer |
| Admin Panel | `GET /api/v1/auth/users`, `PUT /api/v1/auth/rbac` | M10 — Security |
| User Management | `GET /api/v1/auth/users`, `POST /api/v1/auth/users` | M10 — Security |

Shell builds proceed independently of these dependencies. Data wiring is blocked until the corresponding API endpoint group is live.

---

## 5. Delay Risk Mitigation

Three components carry the highest risk of implementation delay. Each has a documented fallback approach.

**Risk 1 — DAG Node Graph (Lineage Explorer)**
Primary approach: D3.js force-directed graph with custom node shapes per type (source, ETL, warehouse, dashboard).
Fallback: If D3.js force layout proves too complex to implement within the M7 timeline, replace with a static SVG diagram generated server-side from the lineage metadata. The detail panel and downstream impact list remain fully functional — only the interactive canvas is simplified. Acceptable for M7 delivery; full interactive DAG deferred to M8 polish sprint.

**Risk 2 — BI Report Builder Chart Canvas**
Primary approach: Integrated Chart.js and ECharts instances within a drag-and-drop builder canvas.
Fallback: If the drag-and-drop builder is not achievable in M8, deliver a form-based chart configurator — the user selects chart type, data source, and dimensions from dropdowns. The output renders the same chart. Visual parity is maintained; only the interaction model is simplified. Full drag-and-drop deferred to M9 or post-launch.

**Risk 3 — Data Catalog Live Search**
Primary approach: Debounced search input triggering `GET /api/v1/catalog/search` after 2 characters, with results filtering live as the user types.
Fallback: If the catalog API response time exceeds 300ms consistently, replace live search with a submit-on-enter pattern (user types, presses Enter or clicks Search, results load). The filter sidebar and detail panel remain unchanged. Live search restored once API performance is confirmed stable.
