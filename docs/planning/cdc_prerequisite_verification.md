# CDC Prerequisite Re-Verification Report

**Task ID:** M7W23T1
**Project:** SUBOP
**Date:** October 13, 2026
**Environment:** Local Development — Docker Compose (Windows, Git Bash / MINGW64)
**Status:** ✅ Verification completed — all checks PASS. Gate on M7W23T12 released.

## 1. Objective

Week 22's M7W22T7 verified the Kafka Connect side of the CDC infrastructure but never
verified the PostgreSQL side. It confirmed the `postgres` container was healthy without
running `SHOW wal_level`, querying `pg_publication`, or checking that the `subop_cdc` role
exists.

This mattered because `cdc_replication_setup.sql` is mounted into
`/docker-entrypoint-initdb.d/`, which PostgreSQL executes **only on a first-time volume
initialisation**. M7W22T7's own Issue 2 records that the `.env` CDC variables were added
*after* the stack had already started. If the volume initialised before `SUBOP_CDC_USER`
existed, then the role, schema, publication and seed table would be silently absent — and
M7W23T12's connector registration would fail at its first REST call with no obvious cause.

This task re-verifies every PostgreSQL-side prerequisite from a clean volume, and captures
the output verbatim.

A second objective: close M7W22T7's own open item by recording the full-stack
`docker compose ps` output after a clean restart.

## 2. Method

The stack was torn down including volumes, the stray `subop-network` was removed, and the
stack was restarted:

```bash
docker compose down -v --remove-orphans
docker network rm subop-network
docker compose up -d --quiet-pull
```

Each check was then issued through `docker compose exec -T postgres psql`.

**Clean-volume condition — independently confirmed.** Rather than relying on the teardown
command having worked, first-time initialisation is proven by the init script's own
execution in the container log (Section 4). PostgreSQL runs
`/docker-entrypoint-initdb.d/` scripts on a first-time volume initialisation and skips
them entirely otherwise, so the presence of that output is direct evidence of a clean
volume. This distinction matters: querying `pg_publication` alone answers *"is the state
correct"*, not *"was it created this time"*, and a pre-existing correct state is
indistinguishable from a freshly created one from the queries alone. Conflating those two
questions is what left Week 22's PostgreSQL side unverified.

## 3. Prerequisite Check Results

### 3.1 CHECK 1 — `wal_level`

```
$ SHOW wal_level;
 wal_level
-----------
 logical
(1 row)
```

**Result:** PASS — `logical`, as required for logical decoding. Supplied by the
`command:` override on the `postgres` service in `docker-compose.yml`.

### 3.2 CHECK 2 — Publication scope

```
$ SELECT pubname, puballtables FROM pg_publication;
    pubname    | puballtables
---------------+--------------
 subop_cdc_pub | f
(1 row)
```

**Result:** PASS — `subop_cdc_pub` exists and `puballtables = f`.

The `f` is the load-bearing value. A publication created `FOR ALL TABLES` would capture
warehouse writes as change events, feeding the pipeline's own output back into itself —
precisely the loop `cdc_replication_setup.sql` separates schemas to prevent. This also
confirms Debezium has not yet auto-created a publication of its own, which is the failure
mode `publication.autocreate.mode=disabled` exists to prevent in M7W23T12.

### 3.3 CHECK 3 — Published tables

```
$ SELECT * FROM pg_publication_tables;
    pubname    | schemaname | tablename |                       attnames                       | rowfilter
---------------+------------+-----------+------------------------------------------------------+-----------
 subop_cdc_pub | cdc_demo   | orders    | {id,customer_id,status,amount,created_at,updated_at} |
(1 row)
```

**Result:** PASS — exactly one published table, `cdc_demo.orders`, with all six columns
and no row filter.

The `attnames` list is a useful bonus: it is the column set M7W23T4's schema-drift
baseline snapshot will be derived from, so the two should agree.

### 3.4 CHECK 4 — CDC replication role

```
$ SELECT rolname, rolreplication FROM pg_roles WHERE rolname = 'subop_cdc';
  rolname  | rolreplication
-----------+----------------
 subop_cdc | t
(1 row)
```

**Result:** PASS — the role exists with `rolreplication = t`. Debezium cannot open a
replication slot without this attribute.

### 3.5 CHECK 5 — Replica identity

```
$ SELECT n.nspname, c.relname, c.relreplident
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
   WHERE c.relname = 'orders';
 nspname  | relname | relreplident
----------+---------+--------------
 cdc_demo | orders  | f
(1 row)
```

**Result:** PASS — `relreplident = f` (FULL).

This is the single most consequential check in the task. The PostgreSQL default is `d`
(primary key only), which would put only an `id` into the WAL for UPDATE and DELETE. The
normaliser built in M7W23T3 would then receive an id-only `before` block, quietly breaking
the `{op, table, before, after, ts_ms}` neutral contract — and the error would not surface
until Week 24's consumer, where it is most expensive to find. `f` confirms
`ALTER TABLE orders REPLICA IDENTITY FULL` took effect, and that M7W23T13's `before`-block
check should pass.

**Deviation from the task plan, recorded.** The plan specified
`SELECT relreplident FROM pg_class WHERE relname='orders'`. That predicate is
schema-unqualified. It returns one row today, but once M8's warehouse layer creates its own
`orders` table in another schema it would return several rows with no indication of which
is which. The query was joined to `pg_namespace` and the schema reported explicitly. Same
check, same expected value, stable as the schema count grows.

### 3.6 CHECK 6 — Seed rows (supplementary)

```
$ SELECT count(*) AS seed_rows FROM cdc_demo.orders;
 seed_rows
-----------
         3
(1 row)
```

**Result:** PASS — 3 rows, matching the seed block in `cdc_replication_setup.sql`.

Not in the task plan. Added because `pg_publication_tables` naming a table does not prove
the table is populated, and Debezium's initial snapshot needs rows to read.

### 3.7 CHECK 7 — CDC role SELECT grant (supplementary)

```
$ SELECT has_table_privilege('subop_cdc', 'cdc_demo.orders', 'SELECT') AS can_select;
 can_select
------------
 t
(1 row)
```

**Result:** PASS — the CDC role can read the published table.

Not in the task plan. Added because the grant block is the one part of the init script
whose failure is completely invisible to the other six checks: the role, schema,
publication and table would all verify correctly while Debezium's snapshot phase failed on
permissions.

## 4. Init-Script Execution Evidence

```
$ docker compose logs postgres --no-color | grep -A 12 "10-cdc-replication.sql"
subop-postgres  | /usr/local/bin/docker-entrypoint.sh: running /docker-entrypoint-initdb.d/10-cdc-replication.sql
subop-postgres  | CREATE ROLE
subop-postgres  | CREATE SCHEMA
subop-postgres  | SET
subop-postgres  | CREATE TABLE
subop-postgres  | ALTER TABLE
subop-postgres  | INSERT 0 3
subop-postgres  | CREATE PUBLICATION
subop-postgres  | GRANT
subop-postgres  | GRANT
subop-postgres  | ALTER DEFAULT PRIVILEGES
```

**Result:** PASS — every statement in `cdc_replication_setup.sql` executed on this volume,
in order, with no errors. `INSERT 0 3` confirms the seed block ran rather than being
skipped by its `WHERE NOT EXISTS` guard.

This also confirms `psql`'s `\getenv` meta-command works on `postgres:15`. The init script
reads `SUBOP_CDC_USER` and three other variables through `\getenv`, which was added to
`psql` in PostgreSQL 15 (commit `33d3eea`, December 2021). Had it been a PostgreSQL 16
feature, the script would have failed on the pinned image. Verified rather than assumed,
because a failure here would have presented as a missing role with no obvious cause.

## 5. Full-Stack Container Status

Closes the item M7W22T7 left open.

```
$ docker compose ps
NAME              IMAGE                                        SERVICE     STATUS                        PORTS
subop-api         suboprepo-subop-api                          subop-api   Up About a minute (healthy)   0.0.0.0:8000->8000/tcp
subop-connect     quay.io/debezium/connect:3.6                 connect     Up About a minute (healthy)   0.0.0.0:8083->8083/tcp
subop-kafka       confluentinc/cp-kafka:7.6.0                  kafka       Up 2 minutes (healthy)        0.0.0.0:9092->9092/tcp
subop-kafka-ui    provectuslabs/kafka-ui:latest                kafka-ui    Up About a minute             0.0.0.0:8080->8080/tcp
subop-mssql       mcr.microsoft.com/mssql/server:2022-latest   mssql       Up 3 minutes (healthy)        0.0.0.0:1433->1433/tcp
subop-mysql       mysql:8                                      mysql       Up 2 minutes (healthy)        0.0.0.0:3306->3306/tcp
subop-oracle      gvenzl/oracle-free:23-slim                   oracle      Up 3 minutes (healthy)        0.0.0.0:1521->1521/tcp
subop-pgadmin     dpage/pgadmin4:8                             pgadmin     Up 2 minutes                  0.0.0.0:5050->80/tcp
subop-postgres    postgres:15                                  postgres    Up 3 minutes (healthy)        0.0.0.0:5433->5432/tcp
subop-zookeeper   confluentinc/cp-zookeeper:7.6.0              zookeeper   Up 3 minutes (healthy)        0.0.0.0:2181->2181/tcp
```

**Result:** PASS — all ten services running. `connect` reached `healthy`, which Week 22
could not confirm after its healthcheck was added.

MySQL took 21.2s and Kafka 34.0s to report healthy on this clean start, consistent with
M7W22T7's observation that first-time MySQL initialisation needs a longer grace period.

## 6. Kafka Connect Readiness for M7W23T12

```
$ curl -s http://localhost:8083/
{"version":"4.3.0","commit":"a9ce3221537b8653","kafka_cluster_id":"I2wfjS0_RN6LdB7EdVX0QQ"}

$ curl -s http://localhost:8083/connectors
[]

$ curl -s http://localhost:8083/connector-plugins | grep -o "io.debezium.connector.postgresql.PostgresConnector"
io.debezium.connector.postgresql.PostgresConnector
```

**Result:** PASS — REST API responding, no connectors registered (correct state entering
M7W23T12), and the Debezium PostgreSQL connector plugin available.

**Clarification on the version numbers**, which read confusingly and did so in Week 22 too:
`"version": "4.3.0"` is the **Kafka Connect runtime** version, not the Debezium version.
The Debezium plugin reports `3.6.3.Final` separately via `/connector-plugins`, and the
image is `quay.io/debezium/connect:3.6`. These are three different version numbers for
three different things, not an inconsistency.

## 7. Findings

Four items, none of which block M7W23T12, all recorded rather than left for a later reader
to rediscover.

### Finding 1 — `.env` was missing all four `CONNECT_*` variables

A pre-flight `.env` completeness check, run before any teardown, found
`CONNECT_GROUP_ID`, `CONNECT_CONFIG_STORAGE_TOPIC`, `CONNECT_OFFSET_STORAGE_TOPIC` and
`CONNECT_STATUS_STORAGE_TOPIC` all absent. The `DEBEZIUM_*` and `SUBOP_CDC_*` blocks were
present and correct.

This contradicts `cdc_infra_verification.md`, which lists Group ID as
`subop-connect-cluster` and the three storage topics as `subop-connect-*`, and whose Issue
2 states the resolution was that `.env` "was updated with Kafka Connect, pgAdmin, and
PostgreSQL CDC configuration values."

The consequence is not cosmetic. `docker-compose.yml` passes these through as
`${CONNECT_GROUP_ID}` and so on, and Compose substitutes an **empty string** for an unset
variable rather than failing. Week 22's Connect container therefore came up on the
Debezium image's own defaults, not on SUBOP's intended group and topic names. Harmless in
Week 22, when nothing was registered. Not harmless from M7W23T12 onward: Kafka Connect
stores connector configurations and consumer offsets in those topics, so the name they are
written under is the name capture must resume from in Week 24.

**Resolution:** the four variables were added to `.env` from `.env.example` before the
verification run. The values in Section 6 were produced with them set.

### Finding 2 — First run failed to start the stack; Docker Desktop port proxy

An initial attempt aborted partway through `docker compose up -d`:

```
Error response from daemon: ports are not available: exposing port TCP 0.0.0.0:3306
-> 127.0.0.1:0: listen tcp 0.0.0.0:3306: bind: Only one usage of each socket address
(protocol/network address/port) is normally permitted.
```

Compose abandons the remaining services when one fails to start, so `kafka`, `connect`,
`kafka-ui`, `pgadmin` and `subop-api` were created but never started — leaving a stack in
which PostgreSQL verified green while the entire CDC path was down.

The Docker daemon itself was running throughout: the same run pulled
`quay.io/debezium/connect:3.6`, created five volumes and ten containers, and started four
of them healthy. The cause was Docker Desktop not being fully initialised — on Windows the
port-forwarding proxy comes up as a layer separate from the daemon, and a bind failure on a
free port is what a half-initialised proxy produces. No conflicting MySQL service or stray
container was ever found, and no configuration was changed between the failed and
successful runs.

**Resolution:** Docker Desktop started fully, then `docker compose up -d` completed with
exit code 0 and all ten services running (Section 5).

### Finding 3 — Compose project name is derived from the folder name

```
warning: a network with name subop-network exists but was not created for project
"suboprepo". Set `external: true` to use an existing network
```

`COMPOSE_PROJECT_NAME` was unset, so Compose derived the project name from the containing
directory (`Subop repo` → `suboprepo`), while `docker-compose.yml` hardcodes
`networks.default.name: subop-network`. Volume names therefore differ between team members
purely by checkout folder name: `suboprepo_postgres_data` here, `subop_postgres_data` for a
teammate who cloned into `subop`. Instructions of the form "remove the postgres volume" are
not portable across the team under this arrangement, and `docker compose down -v` run from
a differently-named folder silently targets different volumes.

**Resolution:** `COMPOSE_PROJECT_NAME=subop` was added to `.env` after this verification
run. The verification above was therefore performed under project `suboprepo` — visible in
the `subop-api` image name in Section 5. Switching project names orphans the running stack
and creates a second one, so the cutover is scheduled as a deliberate step rather than
applied mid-week. **Open item, owner Abdalla:** perform the cutover at a clean boundary
(`docker compose -p suboprepo down -v`, then `docker compose up -d`) and re-run Section 3's
checks against the renamed project. Recommend `.env.example` carry the variable too, so
the team inherits a stable name.

### Finding 4 — Verification tooling masked a non-zero exit (self-inflicted)

The first version of `infrastructure/scripts/verify_cdc_prerequisites.sh` echoed each
command through `tee`, so `$?` reported `tee`'s status rather than the command's. The
aborted `docker compose up -d` of Finding 2 returned non-zero and the script continued
regardless, reporting a clean PostgreSQL verification while five services were down. The
failure only became visible in the final `docker compose ps`.

A verification script that can pass while the thing it verifies is broken is the same class
of defect this task exists to catch.

**Resolution:** the script now returns `${PIPESTATUS[0]}`, warns explicitly on a non-zero
`up -d`, and ends with a service-presence check naming the `connect` and `kafka-ui`
dependencies of M7W23T12 and M7W23T13. It also passes `--quiet-pull`, image pull progress
having produced 5,700 of the original log's 5,875 lines.

## 8. Risk Recorded for Week 24 — Kafka Has No Volume

Noted here because this verification is what exposed it, and because Week 24 assigns the
offset and replication-slot lifecycle to Omer.

Neither the `kafka` nor the `zookeeper` service in `docker-compose.yml` declares a volume.
All Kafka data — including the `subop-connect-offsets`, `subop-connect-configs` and
`subop-connect-status` topics — lives in the container filesystem and is destroyed by
`docker compose down`. The changed `kafka_cluster_id` between Week 22
(`0iuMnjd6TwKPqdNSZzUybw`) and this run (`I2wfjS0_RN6LdB7EdVX0QQ`) is direct evidence of
this.

The asymmetry is the risk: the PostgreSQL **replication slot** persists in
`postgres_data`, while Debezium's **committed offsets** do not. After a `down -v` of Kafka
but not PostgreSQL — or any `down` at all — Debezium restarts with no memory of its
position against a slot that has one. Depending on the slot's state this produces either a
re-snapshot or a gap, and neither is obvious from the connector status endpoint.

Not actionable in Week 23: no offsets exist yet, and M7W23T12 registers the connector from
scratch. It bears directly on Week 24's "whether capture resumes from the right LSN" and
"whether a stale slot accumulates WAL" questions, and on whether Kafka should be given a
named volume before that work begins. **Owner: Abdalla, to raise in Week 24 planning.**

## 9. Verification Summary

| Check | Expected | Actual | Result |
|---|---|---|---|
| 1 — `wal_level` | `logical` | `logical` | PASS |
| 2 — publication exists, not FOR ALL TABLES | `subop_cdc_pub`, `puballtables = f` | `subop_cdc_pub`, `f` | PASS |
| 3 — published table | exactly `cdc_demo.orders` | `cdc_demo.orders`, 6 columns | PASS |
| 4 — CDC role | `subop_cdc`, `rolreplication = t` | `subop_cdc`, `t` | PASS |
| 5 — replica identity | `relreplident = f` (FULL) | `cdc_demo`/`orders`/`f` | PASS |
| 6 — seed rows (supplementary) | 3 | 3 | PASS |
| 7 — CDC role SELECT grant (supplementary) | `t` | `t` | PASS |
| Init script executed on clean volume | all statements, no errors | 10 statements, no errors | PASS |
| Full-stack container status | all services up | 10 of 10 running | PASS |
| Connect REST API | responding | `4.3.0` | PASS |
| Debezium PostgreSQL plugin | present | `3.6.3.Final` | PASS |
| Registered connectors | `[]` before T12 | `[]` | PASS |

## 10. Conclusion

Every PostgreSQL-side CDC prerequisite is verified from a clean volume with verbatim
output. The blocker this task was written to investigate did not materialise:
`cdc_replication_setup.sql` executed correctly and the role, schema, publication, seed
table and replica identity all exist as specified.

`relreplident = f` is the result that matters most downstream. It confirms UPDATE and
DELETE events will carry a fully populated `before` block, so M7W23T3's neutral contract
holds and M7W23T13's fixture check has a reasonable expectation of passing.

The gate on **M7W23T12 is released.** Kafka Connect is healthy on port 8083, the Debezium
PostgreSQL plugin is available, the connector list is empty, and the publication Debezium
must attach to exists with the correct per-table scope.

Four findings are recorded in Section 7 and one Week 24 risk in Section 8. None blocks
Week 23. Two carry named owners: the Compose project-name cutover (Finding 3) and the
Kafka volume question (Section 8).
