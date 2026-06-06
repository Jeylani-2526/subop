# Docker

Service-specific Dockerfiles are stored here and activated in M3.

| File | Service | Milestone |
|------|---------|-----------|
| `Dockerfile.api` | SUBOP FastAPI backend | M3 |
| `Dockerfile.etl` | ETL Engine worker | M5 |
| `Dockerfile.cdc` | Debezium CDC connector | M7 |

The shared development environment is defined in [`docker-compose.yml`](../../docker-compose.yml).
See [`infrastructure/scripts/setup.sh`](../scripts/setup.sh) for first-time setup instructions.
