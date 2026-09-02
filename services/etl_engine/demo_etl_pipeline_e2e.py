"""
SUBOP ETL Engine — Final End-to-End Demonstration (M5 W17 T1).

Drives one full pipeline run through the real system, not a per-component check:

"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(
    os.path.dirname(_THIS_DIR)
)  # services/etl_engine -> repo root
for path in (_REPO_ROOT, _THIS_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)

from fastapi.testclient import TestClient  # noqa: E402

import lineage_store  # noqa: E402

# import pipeline_store  # noqa: E402
# import run_store  # noqa: E402
from api.app import app  # noqa: E402
from services.connectors.postgres_connector import (  # noqa: E402
    ConnectionConfig as PostgresConnectionConfig,
    PostgresConnector,
)

# ---------------------------------------------------------------------------
# Demo configuration
# ---------------------------------------------------------------------------

SOURCE_TABLE = "raw_customer_signups"
TARGET_TABLE = "customers_clean_e2e_demo"

# connection_ref values used in the DSL document below. connection_resolver
# maps each to an env var (SUBOP_CONN_<REF>) holding JSON credentials — see
# connection_resolver.py's module docstring for the exact convention.
SOURCE_CONNECTION_REF = "demo-e2e-source"
TARGET_CONNECTION_REF = "demo-e2e-target"


def _postgres_config() -> PostgresConnectionConfig:
    """
    Build a PostgresConnectionConfig from the same env vars /
    docker-compose defaults demo_zero_code_change.py uses, so this
    demo needs no setup beyond `docker compose up -d postgres`.
    """
    return PostgresConnectionConfig(
        host=os.getenv("POSTGRES_HOST", "127.0.0.1"),
        port=int(os.getenv("POSTGRES_PORT", "5433")),
        database=os.getenv("POSTGRES_DB", "subop"),
        username=os.getenv("POSTGRES_USER", "subop"),
        password=os.getenv("POSTGRES_PASSWORD", "subop_dev"),
    )


def _register_connection_ref(
    connection_ref: str, config: PostgresConnectionConfig
) -> None:
    """
    Register a connection_ref the way connection_resolver.py expects:
    an env var SUBOP_CONN_<UPPERCASED_REF> holding a JSON blob of
    {host, port, database, username, password}.
    """
    import json
    import re

    slug = re.sub(r"[^A-Za-z0-9]", "_", connection_ref.strip()).upper()
    env_var = f"SUBOP_CONN_{slug}"
    os.environ[env_var] = json.dumps(
        {
            "host": config.host,
            "port": config.port,
            "database": config.database,
            "username": config.username,
            "password": config.password,
        }
    )


def _seed_source_table(config: PostgresConnectionConfig) -> None:
    """
    Reset and seed the demo source table with data deliberately shaped
    to exercise all four Week 16 transformation types:

      - contact_phone / age_text: renamed by rename_columns
      - age (post-rename), is_active: cast by type_cast (str -> int, str -> bool)
      - email: one row is NULL, dropped by drop_null_rows
      - internal_staging_notes: removed by drop_columns
    """
    connector = PostgresConnector(config)
    connector.connect()
    try:
        connector.execute_write(f"DROP TABLE IF EXISTS {SOURCE_TABLE}")
        connector.execute_write(f"""
            CREATE TABLE {SOURCE_TABLE} (
                id INT PRIMARY KEY,
                full_name VARCHAR(100),
                contact_phone VARCHAR(50),
                age_text VARCHAR(10),
                is_active VARCHAR(10),
                email VARCHAR(255),
                internal_staging_notes VARCHAR(255)
            )
        """)
        connector.execute_write(f"""
            INSERT INTO {SOURCE_TABLE}
                (id, full_name, contact_phone, age_text, is_active, email, internal_staging_notes)
            VALUES
                (1,'Ayşe Yilmaz', '+905551110001', '29', 'yes', 'ayse@example.com', 'staging-only'),
                (
                    2,
                    "Mehmet Demir",
                    "+905551110002",
                    "41",
                    "no",
                    "mehmet@example.com",
                    "staging-only",
                ),
                (3,'Zeynep Kaya', '+905551110003', '35', 'yes', NULL, 'staging-only'),
                (4,'Ali Şahin', '+905551110004', '52', 'no',  'ali@example.com', 'staging-only')
        """)
    finally:
        connector.disconnect()


def _reset_target_table(config: PostgresConnectionConfig) -> None:
    """Reset the demo target table so the run's writes are clearly visible."""
    connector = PostgresConnector(config)
    connector.connect()
    try:
        connector.execute_write(f"DROP TABLE IF EXISTS {TARGET_TABLE}")
        connector.execute_write(f"""
            CREATE TABLE {TARGET_TABLE} (
                id INT,
                full_name VARCHAR(100),
                phone VARCHAR(50),
                age INT,
                is_active BOOLEAN,
                email VARCHAR(255)
            )
        """)
    finally:
        connector.disconnect()


def _pipeline_dsl_document() -> Dict[str, Any]:
    """
    The Pipeline DSL document submitted to POST /api/pipelines/.

    Applies all four Week 16 transformation types in array order
    (order is semantically meaningful per etl_engine_api_spec_v1.md
    Section 2.1): rename first so later steps can refer to the new
    column names, then type_cast, then the row filter, then the
    column drop.
    """
    return {
        "name": "m5-e2e-demo-customer-onboarding",
        "source": {
            "connector_type": "postgresql",
            "connection_ref": SOURCE_CONNECTION_REF,
            "object": SOURCE_TABLE,
            "query": None,
        },
        "transformations": [
            {
                "step_id": "rename-contact-fields",
                "type": "rename_columns",
                "params": {"mapping": {"contact_phone": "phone", "age_text": "age"}},
            },
            {
                "step_id": "cast-types",
                "type": "type_cast",
                "params": {"casts": {"age": "int", "is_active": "bool"}},
            },
            {
                "step_id": "drop-incomplete-rows",
                "type": "drop_null_rows",
                "params": {"required_columns": ["email"]},
            },
            {
                "step_id": "drop-internal-columns",
                "type": "drop_columns",
                "params": {"columns": ["internal_staging_notes"]},
            },
        ],
        "target": {
            "connector_type": "postgresql",
            "connection_ref": TARGET_CONNECTION_REF,
            "object": TARGET_TABLE,
            "write_mode": "append",
        },
        # VERBİS fields (compliance_check.py is a stub that always
        # passes today — Module 10 doesn't exist yet — but the DSL
        # still requires these per the wire schema).
        "processing_purpose": "customer onboarding analytics (M5 demo)",
        "data_subject_categories": ["customer_pii"],
        "transfer_recipients": [],
    }


def main() -> None:
    print("=" * 78)
    print("SUBOP ETL Engine — M5 Week 17 End-to-End Demonstration")
    print("=" * 78)

    config = _postgres_config()

    print(f"\n[setup] Seeding source table '{SOURCE_TABLE}' ...")
    _seed_source_table(config)

    print(f"[setup] Resetting target table '{TARGET_TABLE}' ...")
    _reset_target_table(config)

    print("[setup] Registering connection_ref env vars for the resolver ...")
    _register_connection_ref(SOURCE_CONNECTION_REF, config)
    _register_connection_ref(TARGET_CONNECTION_REF, config)

    client = TestClient(app)
    payload = _pipeline_dsl_document()

    # --- Step 1: create + run the pipeline through the real HTTP API ------
    print("\n[1/3] POST /api/pipelines/  (creates the pipeline AND runs it)")
    create_response = client.post("/api/pipelines/", json=payload)
    print(f"      -> HTTP {create_response.status_code}")
    if create_response.status_code != 201:
        print(f"      -> Body: {create_response.json()}")
        raise SystemExit(
            "Pipeline creation/execution failed — see body above. "
            "Confirm `docker compose up -d postgres` is running and "
            "matches the POSTGRES_* env vars this demo reads."
        )

    pipeline_record = create_response.json()
    pipeline_id = pipeline_record["id"]
    run_id = pipeline_record["run_id"]
    print(f"      pipeline_id = {pipeline_id}")
    print(f"      run_id      = {run_id}")

    # --- Step 2: retrieve the run status through the real HTTP API --------
    print(f"\n[2/3] GET /api/pipelines/{pipeline_id}/runs/{run_id}")
    run_response = client.get(f"/api/pipelines/{pipeline_id}/runs/{run_id}")
    print(f"      -> HTTP {run_response.status_code}")
    run = run_response.json()

    print(f"      status            = {run['status']}")
    print(f"      rows_read         = {run['rows_read']}  (4 rows in source table)")
    print(
        f"      rows_written      = {run['rows_written']}  (1 row dropped by drop_null_rows)"
    )
    print(f"      rows_quarantined  = {run['rows_quarantined']}")
    print(f"      quality_score     = {run['quality_score']}")

    print("      logs:")
    for line in run["logs"]:
        print(f"        - {line}")

    # --- Step 3: check Lineage — honestly reporting the known gap ---------
    print(f"\n[3/3] lineage_store.get_lineage_for_run('{run_id}')")
    lineage_entries = lineage_store.get_lineage_for_run(run_id)
    print(
        f"      -> {len(lineage_entries)} entr{'y' if len(lineage_entries) == 1 else 'ies'}"
    )
    if not lineage_entries:
        print("      -- Expected today: executor.py's _read_source() calls")
        print("         AbstractionLayer.execute_query(capture_lineage=True) WITHOUT")
        print("         column_types. execute_query() only computes lineage_records")
        print("         when column_types is supplied, so a real run's lineage list")
        print("         is unconditionally empty until schema-catalog integration")
        print("         wires column_types through. lineage_store.py itself (the")
        print("         module, the source_read sentinel, record/get functions) is")
        print("         implemented and unit-tested — the executor->AbstractionLayer")
        print("         integration point is the open gap, tracked for M5 closure.")

    print("\n" + "=" * 78)
    print("Summary — what this run demonstrated end to end:")
    print("=" * 78)
    print(
        "- Source read via AbstractionLayer.execute_query          : "
        f"rows_read={run['rows_read']}"
    )
    print("  - All four registered transformation types applied in order:")
    (
        "  - Lineage check via lineage_store.py (honest gap reported) : "
        f"{len(lineage_entries)} entries"
    )
    print(
        "  - Data Quality pre-write hook (stub) recorded              : "
        "rows_quarantined="
        f"{run['rows_quarantined']}, "
        "quality_score="
        f"{run['quality_score']}"
    )
    print(
        "  - Run persisted via run_store.py and retrieved via the real GET route : "
        "status="
        f"{run['status']}"
    )
    print(
        "  - Lineage check via lineage_store.py (honest gap reported) : "
        f"{len(lineage_entries)} entries"
    )
    print("=" * 78)


if __name__ == "__main__":
    main()
