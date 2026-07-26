# Next-Batch Component Selection & Build Order

## Already Built (M3)

| Component | Status |
|-----------|--------|
| Navigation Sidebar | Built |
| Data Table | Built |
| KPI Summary Card | Built |
| Status Badge | Built |
| AppShell | Built |

## Next Batch — M4 (Week 12 Build)

| Component | Status | Build Order | Reason |
|-----------|--------|-------------|--------|
| Pipeline Row | Specified → To Build | 1 | Directly unblocks Pipeline Monitor shell. Reuses Status Badge. Used on Home and Pipeline Monitor. |
| Asset Card | Specified → To Build | 2 | Required for Catalog Browser shell. Reuses quality-score badge styling. |

## Build Order Rationale

Pipeline Row is built first because the Pipeline Monitor page-shell plan (M4W11T6) depends on it. Asset Card follows once Pipeline Row is confirmed working — it has no dependency on Pipeline Row and can be built in parallel if needed.

Both components map cleanly onto existing Design System v1 tokens. No new tokens required.
