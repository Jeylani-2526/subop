#!/usr/bin/env bash
set -uo pipefail

REBUILD=0
START=0
case "${1:-}" in
    --rebuild) REBUILD=1 ;;   # down -v + up -d --build. Only needed when the init script
                            # must re-run; see the header note.
  --start)   START=1 ;;     # docker compose start — preserves container state
  "")        ;;             # checks only, against whatever is already running
  *) echo "Usage: $0 [--rebuild|--start]" >&2; exit 2 ;;
esac

FAILURES=0
cd "$(dirname "${BASH_SOURCE[0]}")/../.." || exit 1

# Preflight: an unreachable daemon makes every check below fail for one reason.
# Reporting that reason 13 times obscures it rather than recording it.
if ! docker info >/dev/null 2>&1; then
  echo "ERROR: the Docker daemon is not reachable." >&2
  echo "       Docker Desktop may be paused, stopped, or still starting." >&2
  echo "       Start it, wait for the whale icon to settle, then re-run." >&2
  echo >&2
  docker info 2>&1 | head -5 >&2
  exit 1
fi

# .env is required: docker compose substitutes an EMPTY STRING for an unset
# variable rather than failing (M7W23T1 Finding 1), so a missing .env produces
# a Connect container on the wrong group and topic names, silently.
if [[ ! -f .env ]]; then
  echo "ERROR: .env not found. Copy .env.example to .env before running." >&2
  exit 1
fi
set -a; source .env; set +a

: "${POSTGRES_USER:?POSTGRES_USER not set in .env}"
: "${POSTGRES_DB:?POSTGRES_DB not set in .env}"

for v in CONNECT_GROUP_ID CONNECT_CONFIG_STORAGE_TOPIC \
         CONNECT_OFFSET_STORAGE_TOPIC CONNECT_STATUS_STORAGE_TOPIC; do
  if [[ -z "${!v:-}" ]]; then
    echo "WARNING: $v is empty or unset — Connect will fall back to the" >&2
    echo "         Debezium image defaults, not SUBOP's topic names." >&2
    echo "         This is M7W23T1 Finding 1 recurring." >&2
    FAILURES=$((FAILURES + 1))
  fi
done

if [[ -z "${COMPOSE_PROJECT_NAME:-}" ]]; then
  echo "WARNING: COMPOSE_PROJECT_NAME is unset — volume names derive from the" >&2
  echo "         checkout folder name and differ between team members." >&2
  echo "         M7W23T1 Finding 3, open item. Set COMPOSE_PROJECT_NAME=subop." >&2
fi

banner() { echo; echo "=============================================================="; echo "$1"; echo "=============================================================="; }

# Runs one psql check: prints the full result for the record, then compares a
# compact form of it with the expected value. Reports psql's exit status, not
# the pipeline's — the M7W23T1 Finding 4 defect was a `tee` masking a non-zero
# status. M7W27T1 Finding 6: exit status alone let a wrong value read as PASS.
check() {
  local label="$1" sql="$2" assert_sql="$3" expected="$4" actual
  echo; echo "--- $label ---"; echo "\$ $sql"
  docker compose exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "$sql"
  local status=${PIPESTATUS[0]}
  if [[ $status -ne 0 ]]; then
    echo "FAIL: psql exited $status" >&2
    FAILURES=$((FAILURES + 1))
    return $status
  fi
  actual=$(docker compose exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
    -Atc "$assert_sql" | tr -d '\r')
  if [[ "$actual" == "$expected" ]]; then
    echo "OK: $actual"
  else
    echo "FAIL: expected '$expected', got '$actual'" >&2
    FAILURES=$((FAILURES + 1))
    return 1
  fi
}

if [[ $REBUILD -eq 1 ]]; then
  banner "CLEAN-VOLUME REBUILD"
  echo "\$ docker compose down -v --remove-orphans"
  docker compose down -v --remove-orphans
  docker network rm "${COMPOSE_NETWORK_NAME:-subop-network}" 2>/dev/null || true

  echo "\$ docker compose up -d --build --quiet-pull"
  docker compose up -d --build --quiet-pull
  up_status=${PIPESTATUS[0]}
  if [[ $up_status -ne 0 ]]; then
    echo >&2
    echo "WARNING: 'docker compose up -d' exited $up_status." >&2
    echo "         Compose abandons remaining services when one fails to start," >&2
    echo "         so PostgreSQL can verify green while the whole CDC path is" >&2
    echo "         down (M7W23T1 Finding 2). Check 'docker compose ps' before" >&2
    echo "         trusting anything below." >&2
    echo "         NOTE: a slow first-time MySQL/MSSQL/Oracle init can trip the" >&2
    echo "         dependency wait while those services still come up healthy a" >&2
    echo "         minute later. Re-check below before treating this as fatal." >&2
    FAILURES=$((FAILURES + 1))
  fi
fi

if [[ $START -eq 1 ]]; then
  banner "START (preserving container state)"
  echo "\$ docker compose start"
  docker compose start
fi

# Poll rather than sleep a fixed interval. The previous fixed 45s wait expired
# while Connect was still at "health: starting" on a cold start — every curl in
# Section 6 then returned empty and the run read as green.
if [[ $REBUILD -eq 1 || $START -eq 1 ]]; then
  echo
  echo "Waiting for Kafka Connect's REST API (up to 300s)..."
  connect_ready=0
  for i in $(seq 1 60); do
    if curl -fsS http://localhost:8083/ >/dev/null 2>&1; then
      connect_ready=1
      echo "Connect REST responded after ~$((i * 5))s."
      break
    fi
    sleep 5
  done
  if [[ $connect_ready -eq 0 ]]; then
    echo "FAIL: Connect REST API never responded on :8083." >&2
    echo "      Capture cannot proceed. Check 'docker compose logs connect'." >&2
    FAILURES=$((FAILURES + 1))
  fi
fi

banner "SECTION 3 — PREREQUISITE CHECKS"

S="${SUBOP_CDC_SCHEMA:-cdc_demo}"
U="${SUBOP_CDC_USER:-subop_cdc}"
P="${SUBOP_CDC_PUBLICATION:-subop_cdc_pub}"

check "CHECK 1 — wal_level (expect: logical)" \
  "SHOW wal_level;" \
  "SHOW wal_level;" \
  "logical"

check "CHECK 2 — publication scope (expect: $P, puballtables = f)" \
  "SELECT pubname, puballtables FROM pg_publication;" \
  "SELECT string_agg(pubname || ':' || puballtables, ',' ORDER BY pubname) FROM pg_publication;" \
  "$P:false"

check "CHECK 3 — published tables (expect: exactly $S.customers with 5 columns and $S.orders with 6)" \
  "SELECT * FROM pg_publication_tables;" \
  "SELECT string_agg(schemaname || '.' || tablename || '(' || array_length(attnames, 1) || ')', ',' ORDER BY tablename) FROM pg_publication_tables;" \
  "$S.customers(5),$S.orders(6)"

check "CHECK 4 — CDC role (expect: $U, rolreplication = t)" \
  "SELECT rolname, rolreplication FROM pg_roles WHERE rolname = '$U';" \
  "SELECT string_agg(rolname || ':' || rolreplication, ',') FROM pg_roles WHERE rolname = '$U';" \
  "$U:true"

# Schema-qualified deliberately: M8's warehouse layer will create its own
# `orders`, and an unqualified predicate would then return several rows with no
# way to tell which is which (M7W23T1 Section 3.5).
check "CHECK 5 — replica identity (expect: f for both orders and customers)" \
  "SELECT n.nspname, c.relname, c.relreplident FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = '$S' AND c.relkind = 'r' ORDER BY c.relname;" \
  "SELECT string_agg(c.relname || ':' || c.relreplident::text, ',' ORDER BY c.relname) FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = '$S' AND c.relkind = 'r';" \
  "customers:f,orders:f"

check "CHECK 6 — seed rows (expect: 3 in each table)" \
  "SELECT 'orders' AS tbl, count(*) AS seed_rows FROM $S.orders UNION ALL SELECT 'customers', count(*) FROM $S.customers;" \
  "SELECT (SELECT count(*) FROM $S.customers) || ',' || (SELECT count(*) FROM $S.orders);" \
  "3,3"

check "CHECK 7 — CDC role SELECT grant (expect: t for both tables)" \
  "SELECT has_table_privilege('$U', '$S.orders', 'SELECT') AS orders, has_table_privilege('$U', '$S.customers', 'SELECT') AS customers;" \
  "SELECT has_table_privilege('$U', '$S.orders', 'SELECT') || ',' || has_table_privilege('$U', '$S.customers', 'SELECT');" \
  "true,true"

banner "SECTION 4 — INIT-SCRIPT EXECUTION EVIDENCE"
# Proves a FIRST-TIME volume initialisation. Querying pg_publication answers
# "is the state correct", not "was it created this time" — and a pre-existing
# correct state is indistinguishable from a fresh one from the queries alone.
echo "\$ docker compose logs postgres --no-color | grep -A 16 '10-cdc-replication.sql'"
docker compose logs postgres --no-color | grep -A 16 "10-cdc-replication.sql"
if [[ ${PIPESTATUS[0]} -ne 0 ]]; then
  echo "WARNING: init script output not found in the postgres log." >&2
  echo "         The volume was NOT freshly initialised — run with --rebuild." >&2
  FAILURES=$((FAILURES + 1))
fi

banner "SECTION 5 — FULL-STACK CONTAINER STATUS"
echo "\$ docker compose ps"
docker compose ps

for svc in postgres zookeeper kafka connect; do
  if ! docker compose ps --services --filter "status=running" | grep -qx "$svc"; then
    echo "FAIL: service '$svc' is not running — T1 capture cannot proceed." >&2
    FAILURES=$((FAILURES + 1))
  fi
done

banner "SECTION 6 — KAFKA CONNECT READINESS"
# Each response is asserted non-empty. An empty body here previously printed as
# a blank line and read as a pass, which is the same defect class as M7W23T1
# Finding 4: a verification that can pass while the thing it verifies is down.
probe() {
  local label="$1" url="$2" body
  echo; echo "\$ curl -s $url"
  body=$(curl -fsS "$url" 2>&1)
  if [[ -z "$body" ]]; then
    echo "FAIL: $label returned an empty body — Connect is not serving." >&2
    FAILURES=$((FAILURES + 1))
    return 1
  fi
  echo "$body"
}

probe "Connect root" "http://localhost:8083/"
probe "Connector list" "http://localhost:8083/connectors"

echo; echo "\$ curl -s http://localhost:8083/connector-plugins | grep -o PostgresConnector"
plugin=$(curl -fsS http://localhost:8083/connector-plugins 2>/dev/null \
  | grep -o "io.debezium.connector.postgresql.PostgresConnector" | head -1)
if [[ -z "$plugin" ]]; then
  echo "FAIL: Debezium PostgreSQL connector plugin not found." >&2
  FAILURES=$((FAILURES + 1))
else
  echo "$plugin"
fi

# Needed by M7W26T6 and the Week 27 run, not by capture. Reported, not fatal.
if ! docker compose ps --services --filter "status=running" | grep -qx "subop-api"; then
  echo; echo "NOTE: subop-api is not running. It depends on mysql, mssql and"
  echo "      oracle reporting healthy, so a slow first-time init leaves it"
  echo "      Created but never Started. Capture does not need it."
fi

banner "SUMMARY"
if [[ $FAILURES -eq 0 ]]; then
  echo "All checks PASS. Proceed to connector registration."
  exit 0
fi
echo "$FAILURES check(s) reported a problem. Record them as findings; do not"
echo "proceed to capture until they are resolved or explained."
exit 1
