# Pipeline Monitor Page-Shell Layout Plan

## Reference

M1 wireframe: `wireframe_pipeline_monitor.pdf` (Milestone 1, Week 2)

## Layout — Three Zones

**Zone 1 — Top Filter Bar**
Reuses the same filter bar pattern from Home/Overview. Static placeholder content for Week 12 shell:
- Status filter: All / Running / Completed / Failed / Pending
- Date range picker: placeholder input
- Search input: pipeline name

**Zone 2 — Left Panel: Pipeline List**
Width: 320px fixed. Built from Pipeline Row component (Week 12 build).
Each row shows: pipeline name, source, target, status badge, last run time.
Clicking a row updates the right detail panel — no page navigation.
Static placeholder: three Pipeline Row instances with hardcoded data.

**Zone 3 — Right Panel: Pipeline Detail**
Fills remaining width. Shown when a pipeline row is selected.
Four sections stacked vertically:
- Pipeline metadata: source, target, start time, estimated completion
- Row-count progress bar (reuses Progress Bar component)
- Execution log (monospace, dark background, type-mono token)
- BI Analyst restricted view note

## Component Reuse

| Component | Zone | Source |
|-----------|------|--------|
| AppShell | Wrapper | Built M3 |
| Navigation Sidebar | AppShell | Built M3 |
| Data Table | Pipeline list fallback | Built M3 |
| Status Badge | Pipeline Row | Built M3 |
| Pipeline Row | Zone 2 | Build Week 12 |
| Progress Bar | Zone 3 | Build Week 12 |

## Shell Approach

Same shell-first, static-placeholder approach used for Home/Overview in M3. No API calls. No live data. Shell is complete when all three zones render inside AppShell with correct layout and static content. Data wiring deferred to M5.
