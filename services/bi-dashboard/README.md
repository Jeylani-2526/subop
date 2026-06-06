# Module 6 — BI Dashboard & OLAP Layer

**Status:** ⏳ Scheduled for M9 (1 Dec – 28 Dec 2026)
**Owner:** Beyza

## Description

Self-service dashboard builder that non-technical users can operate to create
charts, reports, and OLAP-style views from warehouse data.

## Sub-modules

| Sub-module | Path | Description |
|-----------|------|-------------|
| Frontend | `frontend/` | React/Vue dashboard UI + chart components |
| Backend | `backend/` | FastAPI BI endpoints, PostgreSQL queries |

## KPI Target

A user with no SQL knowledge creates a working dashboard in under 15 minutes.

## Important Note

The BI layer queries PostgreSQL directly — no separate OLAP engine.
Beyza builds the UI shell (routing, layout, empty chart containers) during M5–M8
so M9 is data-wiring only, not full UI development from scratch.
