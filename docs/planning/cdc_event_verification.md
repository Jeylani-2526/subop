# Change Event Verification Record

**Task ID:** M7W26T1 (absorbs Mert's unfinished M7W23T13)
**Project:** SUBOP
**Date:** 3 November 2026
**Branch:** `abdullah/M7W26T1-6`
**Environment:** Local Development — Docker Compose (Windows, Git Bash)
**Status:** ✅ Capture complete — three real envelopes committed. Gate on M7W26T2 released.

## 1. Objective

Milestone 7 had been built on three change-event fixtures that were never
captured. `tests/fixtures/cdc/README.md` stated that `insert.json`,
`update.json` and `delete.json` were **hand-reconstructed, not captured** —
placeholders committed under M7W23T5 so the suite would run before M7W23T13
landed. M7W23T13 never landed.

This task captures one real envelope per operation, replaces the three files
in place, and re-runs M7W23T1's prerequisite checks against a clean volume,
since a fresh volume re-executes `cdc_replication_setup.sql` and the previous
verification does not survive the rebuild.

It gates M7W26T2. The only genuine capture in the repository,
`snapshot_event.json`, false-drifted against the placeholders on every column,
and which side was wrong could not be known until a real streaming envelope
existed.

## 2. Method

```bash
./infrastructure/scripts/verify_cdc_prerequisites.sh --rebuild
curl -s -X POST http://localhost:8083/connectors -H "Content-Type: application/json" \
     -d @services/cdc/debezium_postgres_connector.json
curl -s http://localhost:8083/connectors/subop-postgres-cdc/status
set -a; source .env; set +a            # see Finding 6
python -m services.cdc.cdc_demo_changes --all
python infrastructure/scripts/capture_cdc_envelopes.py
python -m pytest tests/test_cdc_normalizer.py -q
```

Two runs were made. **Run 1** surfaced a defect in the verification script
itself (Finding 3) and is not the run of record. **Run 2** is recorded below.
The capture in Sections 7–8 ran against Run 2's stack without a further
rebuild.

The clean-volume condition is proven by the init script's output in the
container log (Section 4), not by the teardown returning zero — the
distinction M7W23T1 Section 2 drew.

## 3. Prerequisite Check Results

| Check | Expected | Actual | Result |
|---|---|---|---|
| 1 — `wal_level` | `logical` | `logical` | PASS |
| 2 — publication not FOR ALL TABLES | `subop_cdc_pub`, `puballtables = f` | `subop_cdc_pub`, `f` | PASS |
| 3 — published table | exactly `cdc_demo.orders`, 6 columns | `cdc_demo.orders`, 6 columns | PASS |
| 4 — CDC role | `subop_cdc`, `rolreplication = t` | `subop_cdc`, `t` | PASS |
| 5 — replica identity | `cdc_demo`/`orders`/`f` | `cdc_demo`/`orders`/`f` | PASS |
| 6 — seed rows (supplementary) | 3 | 3 | PASS |
| 7 — CDC role SELECT grant (supplementary) | `t` | `t` | PASS |

```
--- CHECK 1 — wal_level (expect: logical) ---
$ SHOW wal_level;
 wal_level
-----------
 logical
(1 row)

--- CHECK 2 — publication scope (expect: subop_cdc_pub, puballtables = f) ---
$ SELECT pubname, puballtables FROM pg_publication;
    pubname    | puballtables
---------------+--------------
 subop_cdc_pub | f
(1 row)

--- CHECK 3 — published tables (expect: exactly cdc_demo.orders) ---
$ SELECT * FROM pg_publication_tables;
    pubname    | schemaname | tablename |                       attnames                       | rowfilter
---------------+------------+-----------+------------------------------------------------------+-----------
 subop_cdc_pub | cdc_demo   | orders    | {id,customer_id,status,amount,created_at,updated_at} |
(1 row)

--- CHECK 4 — CDC role (expect: subop_cdc, rolreplication = t) ---
$ SELECT rolname, rolreplication FROM pg_roles WHERE rolname = 'subop_cdc';
  rolname  | rolreplication
-----------+----------------
 subop_cdc | t
(1 row)

--- CHECK 5 — replica identity (expect: cdc_demo | orders | f) ---
$ SELECT n.nspname, c.relname, c.relreplident FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE c.relname = 'orders';
 nspname  | relname | relreplident
----------+---------+--------------
 cdc_demo | orders  | f
(1 row)

--- CHECK 6 — seed rows (expect: 3) ---
$ SELECT count(*) AS seed_rows FROM cdc_demo.orders;
 seed_rows
-----------
         3
(1 row)

--- CHECK 7 — CDC role SELECT grant (expect: t) ---
$ SELECT has_table_privilege('subop_cdc', 'cdc_demo.orders', 'SELECT') AS can_select;
 can_select
------------
 t
(1 row)
```

Check 5 is the one that matters downstream: `relreplident = f` is what puts a
fully populated `before` into the WAL for UPDATE and DELETE. Section 8
confirms it took effect.

## 4. Init-Script Execution Evidence

```
$ docker compose logs postgres --no-color | grep -A 12 '10-cdc-replication.sql'
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

**Result:** PASS — all statements executed on this volume in order. `INSERT 0 3`
confirms the seed block ran rather than being skipped by its guard.

## 5. Full-Stack Container Status

`docker compose up -d` exited 1 on this run (Finding 4). Three minutes later:

```
$ docker compose ps
NAME              IMAGE                                        SERVICE     STATUS
subop-api         suboprepo-subop-api                          subop-api   Up 2 minutes (healthy)
subop-connect     quay.io/debezium/connect:3.6                 connect     Up 2 minutes (healthy)
subop-kafka       confluentinc/cp-kafka:7.6.0                  kafka       Up 2 minutes (health: starting)
subop-kafka-ui    provectuslabs/kafka-ui:latest                kafka-ui    Up 2 minutes
subop-mssql       mcr.microsoft.com/mssql/server:2022-latest   mssql       Up 3 minutes (healthy)
subop-mysql       mysql:8                                      mysql       Up 3 minutes (healthy)
subop-oracle      gvenzl/oracle-free:23-slim                   oracle      Up 3 minutes (healthy)
subop-pgadmin     dpage/pgadmin4:8                             pgadmin     Up 3 minutes
subop-postgres    postgres:15                                  postgres    Up 3 minutes (healthy)
subop-zookeeper   confluentinc/cp-zookeeper:7.6.0              zookeeper   Up 3 minutes (healthy)
```

**Result:** PASS — all ten services running. Kafka was still `health: starting`
when this was taken, which bears on Section 6.

Connect REST responded after ~110s of polling:

```
$ curl -s http://localhost:8083/
{"version":"4.3.0","commit":"a9ce3221537b8653","kafka_cluster_id":"jscEC4wOT7GlYvjzH0UQpA"}

$ curl -s http://localhost:8083/connectors
[]

$ curl -s http://localhost:8083/connector-plugins | grep -o PostgresConnector
io.debezium.connector.postgresql.PostgresConnector
```

## 6. Connector Registration

Registered from `services/cdc/debezium_postgres_connector.json` unchanged.

```
$ curl -s -X POST http://localhost:8083/connectors -H "Content-Type: application/json" \
       -d @services/cdc/debezium_postgres_connector.json
{"name":"subop-postgres-cdc","config":{"connector.class":"io.debezium.connector.postgresql.PostgresConnector","topic.prefix":"subop-postgres-cdc","database.hostname":"postgres","database.port":"5432","database.dbname":"subop","database.user":"subop_cdc","database.password":"cdc_dev","plugin.name":"pgoutput","slot.name":"subop_cdc_slot","publication.name":"subop_cdc_pub","publication.autocreate.mode":"disabled","table.include.list":"cdc_demo.orders","decimal.handling.mode":"string","tombstones.on.delete":"false","column.propagate.source.type":".*cdc_demo\\.orders\\..*","tasks.max":"1","name":"subop-postgres-cdc"},"tasks":[],"type":"source"}
```

Status immediately after registration:

```
$ curl -s http://localhost:8083/connectors/subop-postgres-cdc/status
{"name":"subop-postgres-cdc","connector":{"state":"RUNNING","worker_id":"172.19.0.11:8083","version":"3.6.3.Final"},"tasks":[],"type":"source"}
```

**Connector RUNNING, `tasks: []`.** No task means nothing reads the WAL. This
is the state the plan warned a 201 can conceal (Finding 5).

Status on re-check, several minutes later, with no restart issued:

```
$ curl -s http://localhost:8083/connectors/subop-postgres-cdc/status
{"name":"subop-postgres-cdc","connector":{"state":"RUNNING","worker_id":"172.19.0.11:8083","version":"3.6.3.Final"},"tasks":[{"id":0,"state":"RUNNING","worker_id":"172.19.0.11:8083","version":"3.6.3.Final"}],"type":"source"}
```

**Result:** PASS — RUNNING for both connector and task, `3.6.3.Final`. This
closes the gap M7W23T12 left: whether the connector ever reached RUNNING is
now recorded.

## 7. Change Events Produced

```
$ docker compose exec -T kafka kafka-topics --bootstrap-server localhost:29092 --list
__consumer_offsets
subop-connect-configs
subop-connect-offsets
subop-connect-status
subop-postgres-cdc.cdc_demo.orders
```

The topic exists and the Connect storage topics carry SUBOP's names, so the
`CONNECT_*` variables were set (M7W23T1 Finding 1 did not recur).

```
$ python -m services.cdc.cdc_demo_changes --all
INSERT id=4 commit_ts=2026-11-03T07:34:21.547106+00:00 commit_ts_ms=1793691261547 customer_id=9001
UPDATE id=4 commit_ts=2026-11-03T07:34:21.562562+00:00 commit_ts_ms=1793691261562 status=shipped
DELETE id=4 commit_ts=2026-11-03T07:34:21.576166+00:00 commit_ts_ms=1793691261576
```

## 8. Envelope Capture & Validation

```
$ python infrastructure/scripts/capture_cdc_envelopes.py
Consuming subop-postgres-cdc.cdc_demo.orders from localhost:9092 (timeout 90.0s)...
  captured op=c -> insert.json
  captured op=u -> update.json
  captured op=d -> delete.json

Snapshot reads seen (op=r, skipped): 3
OK   insert.json
OK   update.json
OK   delete.json

--- Observed native types: snapshot (baseline) vs streaming ---
column        snapshot_event.json       streaming capture

[insert.json]
id            BIGSERIAL(19,0)           INT8(19,0)                   <-- differs
customer_id   INT8(19,0)                INT8(19,0)
status        VARCHAR(32,0)             VARCHAR(32,0)
amount        NUMERIC(12,2)             NUMERIC(12,2)
created_at    TIMESTAMPTZ(35,6)         TIMESTAMPTZ(35,6)
updated_at    TIMESTAMPTZ(35,6)         TIMESTAMPTZ(35,6)
wrote tests\fixtures\cdc\insert.json
wrote tests\fixtures\cdc\update.json
wrote tests\fixtures\cdc\delete.json

All three envelopes captured and validated. T1 gate released.
```

| Condition | Result |
|---|---|
| Both `schema` and `payload` blocks present | PASS |
| `payload.before` fully populated on UPDATE and DELETE (6 of 6 columns) | PASS |
| Every column carries `__debezium.source.column.type` | PASS |

The three snapshot reads are the seed rows Debezium read on first attach,
correctly skipped. The three changes committed as separate transactions, in
order: `txId` 744, 745, 746 at LSNs 26642408, 26643072, 26643288.

### 8.1 What the capture showed — and what it overturned

The Week 26–27 plan diagnosed three stacked defects by comparing the real
snapshot against the **hand-written** fixtures. Against **real** streaming
envelopes, only one survives:

| Plan's claimed defect | Real evidence | Verdict |
|---|---|---|
| **Case** — `NUMERIC` vs `numeric` | Debezium emits uppercase in both phases | **Not a defect.** The lowercase came from the hand-written placeholders. |
| **Identity** — `BIGSERIAL` vs `int8` | Snapshot `BIGSERIAL`, streaming `INT8`, same column | **Real.** The only cause of a false halt. |
| **Spurious precision** — `TIMESTAMPTZ(35,6)` | Present identically on both sides | **Cosmetic.** Never causes drift; display widths are noise. |

The likely mechanism: Debezium's snapshot phase reads column metadata through
JDBC, which reports the serial pseudo-type for a column with a `nextval()`
default, while the streaming phase reads the type OID from the replication
stream. Same column, two vocabularies.

**Scope restated for M7W26T2**, per the plan's own clause, before any code was
written: map serial aliases to their stored types (the evidenced defect);
suppress display-width modifiers per type (decided in review, though cosmetic);
**no** case-folding, since no case variation was observed.

## 9. Test Suite

| State | Result |
|---|---|
| Before this task, hand-reconstructed fixtures | 91 passed |
| After capture, real fixtures, before M7W26T2 | **91 passed** — see Finding 9 |
| After M7W26T2 | 105 passed |

```
$ python -m pytest tests/test_cdc_normalizer.py -q
91 passed in 1.01s
```

The suite stayed green against the real captures. That was not reassurance:
it was the third defect this task uncovered (Finding 9).

## 10. Findings

### Finding 1 — `verify_cdc_prerequisites.sh` was never committed

`cdc_prerequisite_verification.md` Finding 4 describes this script in detail,
including a bug fix applied to it. It did not exist on `develop` or `main`, and
`git log --all` showed it was never committed on any branch. Week 23's
verification ran on tooling nobody else could re-run.

**Resolution:** written and committed under this task at
`infrastructure/scripts/verify_cdc_prerequisites.sh`.

### Finding 2 — Compose project-name cutover still not done

Carried from M7W23T1 Finding 3. This task's `down -v` was the clean boundary
the cutover was scheduled for. `COMPOSE_PROJECT_NAME` was still unset, and the
volumes were recreated under the folder-derived name:

```
 ✔ Volume suboprepo_postgres_data Created
 ✔ Volume suboprepo_mysql_data    Created
```

**Status:** open. **Owner:** Abdalla. **Resolution path:** add
`COMPOSE_PROJECT_NAME=subop` to `.env` and `.env.example` under M7W26T5, which
already edits the Compose configuration, and apply it at that task's rebuild.

### Finding 3 — Verification script read an unready Connect as a pass (self-inflicted)

Run 1's version of the script waited a fixed 45 seconds after `up -d`. Kafka
took 129 seconds to report healthy on that cold start, so Connect was still
`health: starting` when Section 6 ran. All three `curl` calls returned an empty
body, and the script printed blank lines and continued.

This is the same class of defect as M7W23T1 Finding 4: a verification that can
pass while the thing it verifies is down. It recurred in the script written to
prevent it.

**Resolution:** the script now polls Connect's REST API for up to 300 seconds
and fails explicitly on an empty response. It also gained `--start` for
day-to-day use without a rebuild.

### Finding 4 — MySQL healthcheck has no `start_period`

Both runs' `docker compose up -d` exited 1 with
`dependency failed to start: container subop-mysql is unhealthy`, and Compose
abandoned the services after it. In Run 1, `subop-api` was never started. Three
minutes later MySQL, MSSQL and Oracle were all healthy: no real failure, only
a first-time initialisation that outlasted MySQL's healthcheck budget
(`interval: 10s`, `retries: 5`, no `start_period`, about 50 seconds).

It matters beyond noise: `subop-api` depends on all four databases with
`condition: service_healthy`, and M7W26T6's status endpoint must be reachable
on a cold start.

**Status:** open. **Owner:** Abdalla. **Resolution path:** add a
`start_period` to the MySQL healthcheck under M7W26T5.

### Finding 5 — Connector RUNNING with no task

Immediately after registration the connector reported `RUNNING` with
`tasks: []`. Kafka was still `health: starting` at the time. On re-check the
task was `RUNNING` with no restart issued, so the assignment completed once the
broker settled.

A RUNNING connector with an empty task list produces no events. Any automated
check, including M7W27T1's end-to-end run, must require a task in `RUNNING`, not
only the connector.

**Resolution:** recorded. M7W27T1 checks both.

### Finding 6 — Host-run Python scripts do not load `.env`

`cdc_demo_changes.py` failed twice with `CONNECTION_REF_NOT_FOUND`. Two causes
stacked: `SUBOP_CONN_PG_MAIN` was absent from the local `.env`, and nothing in
the repository loads `.env` into a host Python process — no `load_dotenv`
appears anywhere in `services/` or `tests/`. Compose reads `.env` for
containers; a script run on the host sees only the shell's environment.

**Resolution for this run:** both connection refs added to `.env`, then
`set -a; source .env; set +a` in the shell.

**Status:** open. **Owner:** Abdalla. A script that silently depends on the
developer having sourced `.env` by hand will fail the same way in M7W27T1 and
for every teammate. `python-dotenv` is already installed as a uvicorn
dependency, so loading it in the CLI entry points is a small change. Decide at
M7W26T3, which adds the next host-run entry point.

### Finding 7 — The CDC topic is named three different ways

The topic is `subop-postgres-cdc.cdc_demo.orders` (Section 7), derived from
`topic.prefix` in the connector config. The Week 26–27 plan calls it
`cdc.postgres.*`, and `.env.example` carries
`KAFKA_TOPIC_CDC_EVENTS=subop-cdc-events`. The connector config is
authoritative because it is what runs.

**Status:** open. **Owner:** Abdalla. **Resolution path:** correct
`.env.example` under M7W26T5. M7W26T3 consumes the real name.

### Finding 8 — The plan's three-defect diagnosis was two-thirds wrong

See Section 8.1. The plan built its diagnosis by comparing a real capture
against fabricated fixtures, then read the fabrication's choices (lowercase
types) as code defects. Only the serial alias is real. The plan anticipated
this risk and wrote T2 to restate scope rather than absorb it, which is what
happened.

### Finding 9 — The suite could not detect that every drift fixture was wrong

With the real captures installed, the suite still passed 91 of 91. The real
`insert.json` uses uppercase types; all eleven hand-authored fixtures used
lowercase. Every drift fixture therefore differed from the real baseline on all
six columns, not "in exactly one way" as the fixtures README promised.

The drift tests assert only `pytest.raises(QueryError)`, which passes whenever
*any* drift is raised. A fixture meant to show "a column was added" in fact
showed an added column plus six type changes, and nothing could tell the two
apart.

**Resolution:** under M7W26T2, the drift fixtures are now generated from the
real `insert.json` by `infrastructure/scripts/derive_cdc_fixtures.py`, and
`EXPECTED_DRIFT` asserts the exact difference each one must produce.

### Finding 10 — Three further fixture defects

Found while regenerating under M7W26T2:

- `connect_types_only.json` and `connect_types_only_widened.json` were
  **byte-identical**. The test proving that a widening is invisible without
  propagation compared a file with itself and could not fail.
- `drift_column_renamed.json` renamed `status` in the schema but not in the
  payload, so the envelope contradicted itself.
- `snapshot_read.json` was a hand-built `op: "r"` with `"snapshot": "true"`.
  The real capture says `"snapshot": "first"`. It is removed; the test now uses
  the real `snapshot_event.json`, which until this task no test referenced.

**Resolution:** all three corrected under M7W26T2.

## 11. Conclusion

Three real envelopes — INSERT, UPDATE and DELETE — are captured from a running
connector and committed under `tests/fixtures/cdc/`. Each carries schema and
payload blocks, native types on every column, and a fully populated `before`
on UPDATE and DELETE. Every PostgreSQL prerequisite re-verified on a clean
volume, and the connector reached RUNNING for both connector and task.

The capture reversed the plan's diagnosis. The normaliser had one real defect,
not three, and the green suite was hiding a fixture set that no longer
described reality. Both were corrected in M7W26T2, designed against the
captures above.

Four findings remain open with a named owner: the Compose project name (2), the
MySQL `start_period` (4), `.env` loading for host scripts (6), and the topic
name in `.env.example` (7). Three of them fold into M7W26T5.

**Gate on M7W26T2:** ✅ released.
