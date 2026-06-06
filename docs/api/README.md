# API Specification

The SUBOP FastAPI backend exposes REST endpoints for all platform modules.

**Status:** ⏳ API design begins in M3 (29 Jun – 19 Jul 2026).

Once the API is live, Swagger UI is available at `http://localhost:8000/docs`.

## Planned Endpoint Groups

| Group | Prefix | Module |
|-------|--------|--------|
| Connectors | `/api/v1/connectors` | Module 1 |
| Pipelines (ETL) | `/api/v1/pipelines` | Module 3 |
| CDC Streams | `/api/v1/cdc` | Module 4 |
| Warehouse | `/api/v1/warehouse` | Module 5 |
| Dashboards | `/api/v1/dashboards` | Module 6 |
| Data Quality | `/api/v1/quality` | Module 7 |
| Lineage | `/api/v1/lineage` | Module 8 |
| Catalog | `/api/v1/catalog` | Module 9 |
| Auth / Users | `/api/v1/auth` | Module 10 |
| Health | `/health` | Infrastructure |
