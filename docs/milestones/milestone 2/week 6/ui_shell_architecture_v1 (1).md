## 1. Framework Decision

**Selected stack: React 18 + Tailwind CSS**

React 18 is confirmed in the SUBOP technical requirements and system modules document — selecting it avoids introducing a second frontend framework and keeps the team aligned with Omer's FastAPI backend, which already targets a React-compatible JSON API contract. React's component model maps directly to the six priority components specified in `component_patterns_v1.md`, and the React ecosystem provides React Query for server state and Zustand for client state — both production-ready libraries with minimal learning curve. Tailwind CSS eliminates the need for a custom CSS design system by enforcing the colour tokens, spacing grid, and typography scale from `subop_color_typography_v1.md` at the configuration level.

---

## 2. Page Routing

All routes require authentication. No route is publicly accessible. Authentication guard levels follow the RBAC definitions in `user_role_notes.md`.

| Route | URL Path | Auth Guard | Page Shell Build |
|-------|----------|-----------|-----------------|
| Home / Overview | `/dashboard` | Viewer+ (all roles) | M5 |
| Pipeline Monitor | `/pipelines` | Engineer+ (Admin, Data Engineer, BI Analyst) | M5 |
| Data Quality Dashboard | `/quality` | Engineer+ (Admin, Data Engineer, BI Analyst) | M6 |
| Lineage Explorer | `/lineage` | Analyst+ (Admin, Data Engineer, BI Analyst) | M6 |
| Data Catalog | `/catalog` | Viewer+ (all roles) | M7 |
| BI Report Builder | `/reports/builder` | Analyst only (Admin, BI Analyst) | M7 |
| Admin Panel | `/admin` | Admin only | M8 |
| User Management | `/admin/users` | Admin only | M8 |

**Routing behaviour:**
- Unauthenticated requests redirect to `/login`.
- Authenticated users whose role does not satisfy the guard level receive a 403 page — not a redirect to login.
- `/` redirects to `/dashboard` for all authenticated users.

---

## 3. AppShell Layout

The AppShell is a persistent layout component that wraps all authenticated pages. It has three fixed zones.

**Zone 1 — Top Header (height: 56px, background: `color-primary` `#1B3A6B`)**

| Element | Position | Description |
|---------|----------|-------------|
| SUBOP logo + wordmark | Left | Links to `/dashboard` |
| Global search input | Centre | Searches across pipeline names, catalog assets, and dashboard names |
| Notification bell | Right | Shows unread count badge; opens notification drawer |
| User profile menu | Right | Shows user name and role; links to profile settings and logout |

**Zone 2 — Left Sidebar (width: 240px desktop, 64px tablet icon-only, hidden mobile)**

- Navigation links map 1:1 to the eight routes defined in Section 2.
- Active item: `color-primary` `#1B3A6B` background, white text, 4px left accent bar in `color-secondary` `#2E75B6`.
- Inactive item: transparent background, `color-neutral-dark` `#3A4A5A` text.
- Hover item: `color-neutral-light` `#F4F7FA` background, `color-primary` text.
- Admin section (Admin Panel, User Management) rendered only for `admin` role — not present in DOM for other roles.
- Section divider: 1px `color-border` line between main pages and admin section.

**Zone 3 — Main Content Area (fills remaining width)**

- Router outlet: page component renders here.
- Consistent padding: 24px all sides (`space-lg`).
- Background: `color-background` `#F9FAFB`.
- No max-width applied to the content area itself — max-widths are set per page component.

---

## 4. State Management

**Selected solution: React Query + Zustand**

React Query handles all server state — API data fetching, caching, background refresh intervals, and loading/error states for every REST endpoint and WebSocket subscription. Zustand manages the three pieces of global client state that multiple components read simultaneously without triggering unnecessary re-fetches.

**Global client state (Zustand store):**

| State key | Type | Description |
|-----------|------|-------------|
| `user` | `{ id, name, role }` | Authenticated user — set on login, cleared on logout |
| `pipelineStatusUpdates` | `Record<string, PipelineStatus>` | Live pipeline status from WebSocket — updates every 30 seconds |
| `notificationQueue` | `Notification[]` | Unread platform notifications — badge count and drawer content |

**Server state (React Query):**

All API data is fetched and cached through React Query. Key query keys:

| Query key | Endpoint | Stale time |
|-----------|----------|-----------|
| `['pipelines']` | `GET /api/v1/pipelines` | 30 seconds |
| `['quality-scores']` | `GET /api/v1/quality/scores` | 5 minutes |
| `['catalog-search', query]` | `GET /api/v1/catalog/search` | 2 minutes |
| `['lineage', assetId]` | `GET /api/v1/lineage/{asset_id}` | 5 minutes |

---

## 5. Phase 3 Shell Build Assignments

Shell build = empty page layout + routing only. No data fetching. No chart rendering. Confirms navigation, auth guards, and AppShell zones work correctly before API wiring begins.

Data wiring = connecting the page shell to live API endpoints. All pages wired in M9.

| Milestone | Pages — Shell Build | Pages — Data Wiring |
|-----------|--------------------|--------------------|
| M5 (Aug–Sep 2026) | Home / Overview, Pipeline Monitor | Home / Overview, Pipeline Monitor |
| M6 (Sep–Oct 2026) | Data Quality Dashboard, Lineage Explorer | Data Quality Dashboard, Lineage Explorer |
| M7 (Oct–Nov 2026) | Data Catalog, BI Report Builder | Data Catalog, BI Report Builder |
| M8 (Nov–Dec 2026) | Admin Panel, User Management, full navigation polish | Admin Panel, User Management |
| M9 (Dec 2026) | — | All remaining pages — final data wiring and chart integration |
