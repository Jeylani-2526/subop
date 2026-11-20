
#!/usr/bin/env bash
# =============================================================================
# SUBOP — CDC Replication Slot Lifecycle Measurement
# Task: M8W28T10
#
# Reads PostgreSQL replication slot information and retained WAL size.
# Read-only: does not modify database state or connector configuration.
#
# Usage:
#   bash infrastructure/scripts/check_cdc_slot.sh
#
# Run from any directory inside the repository.
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# 1. Locate repository root
# ---------------------------------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$REPO_ROOT"

# ---------------------------------------------------------------------------
# 2. Validate prerequisites
# ---------------------------------------------------------------------------

if ! command -v docker >/dev/null 2>&1; then
    echo "ERROR: Docker is not installed or not in PATH." >&2
    exit 1
fi

if ! docker info >/dev/null 2>&1; then
    echo "ERROR: Docker daemon is not reachable." >&2
    exit 1
fi

if [[ ! -f .env ]]; then
    echo "ERROR: .env file not found in repository root." >&2
    exit 1
fi

# Load environment variables using the same approach as
# verify_cdc_prerequisites.sh.
set -a
source .env
set +a

: "${POSTGRES_USER:?POSTGRES_USER is not set}"
: "${POSTGRES_DB:?POSTGRES_DB is not set}"

CDC_SLOT="${SUBOP_CDC_SLOT:-subop_cdc_slot}"

# PostgreSQL replication slot names must be safe identifiers.
if [[ ! "$CDC_SLOT" =~ ^[a-z0-9_]+$ ]]; then
    echo "ERROR: Invalid replication slot name: $CDC_SLOT" >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# 3. Verify PostgreSQL container
# ---------------------------------------------------------------------------

if ! docker compose ps --services --filter status=running \
    | grep -qx "postgres"; then

    echo "ERROR: PostgreSQL service is not running." >&2
    echo "Start it with: docker compose up -d postgres" >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# 4. Print measurement header
# ---------------------------------------------------------------------------

echo "=============================================================="
echo " SUBOP — CDC Replication Slot Measurement"
echo " Task: M8W28T10"
echo "=============================================================="
echo

echo "Timestamp (UTC): $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
echo "Database:        $POSTGRES_DB"
echo "PostgreSQL user: $POSTGRES_USER"
echo "Replication slot: $CDC_SLOT"
echo

# ---------------------------------------------------------------------------
# 5. Query PostgreSQL replication slot
# ---------------------------------------------------------------------------

SQL="
SELECT
    slot_name,
    active,
    restart_lsn,
    confirmed_flush_lsn,
    pg_wal_lsn_diff(
        pg_current_wal_lsn(),
        restart_lsn
    )::bigint AS retained_wal_bytes,
    ROUND(
        pg_wal_lsn_diff(
            pg_current_wal_lsn(),
            restart_lsn
        ) / 1024 / 1024,
        2
    ) AS retained_wal_mb
FROM pg_replication_slots
WHERE slot_name = '$CDC_SLOT';
"

echo "--------------------------------------------------------------"
echo " Replication Slot Status"
echo "--------------------------------------------------------------"
echo

docker compose exec -T postgres \
    psql \
    -X \
    -v ON_ERROR_STOP=1 \
    -U "$POSTGRES_USER" \
    -d "$POSTGRES_DB" \
    -c "$SQL"

echo

# ---------------------------------------------------------------------------
# 6. Verify that the replication slot exists
# ---------------------------------------------------------------------------

SLOT_COUNT="$(
    docker compose exec -T postgres \
        psql \
        -X \
        -v ON_ERROR_STOP=1 \
        -U "$POSTGRES_USER" \
        -d "$POSTGRES_DB" \
        -Atc "
            SELECT COUNT(*)
            FROM pg_replication_slots
            WHERE slot_name = '$CDC_SLOT';
        " | tr -d '\r'
)"

if [[ "$SLOT_COUNT" != "1" ]]; then
    echo "ERROR: Replication slot '$CDC_SLOT' was not found." >&2
    echo "Check whether the Debezium connector is registered." >&2
    exit 1
fi

echo "--------------------------------------------------------------"
echo " Measurement completed successfully"
echo "--------------------------------------------------------------"
echo
