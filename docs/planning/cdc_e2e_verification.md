# End-to-End CDC Verification Record

**Task ID:** M7W27T1
**Project:** SUBOP
**Date:** 10 November 2026
**Branch:** `develop` at `c09219a`, plus the Finding 4 fix (`fix/events-processed-distinct`)
**Environment:** Local Development — Docker Compose (Windows, Git Bash)
**Status:** ✅ Backend verified — INSERT, UPDATE and DELETE reach warehouse storage with no scheduled run; redelivery is idempotent; drift halts one table only. UI confirmation of the real halt (M7W27T7) pending Beyza's live swap (M7W27T6).

## 1. Objective

Substantiate Milestone 7's claim: a change committed in the source database
arrives in warehouse storage on its own, with no scheduled pipeline run.

From a clean environment (`docker compose down -v`, then `up -d`), this run
registers the Debezium connector, issues an INSERT, an UPDATE to
`status='shipped'` and a DELETE through `cdc_demo_changes.py`, and shows each
one arriving as a row in `warehouse.orders`. It then replays every message to
prove redelivery is harmless, and alters `cdc_demo.orders` to prove a drift
halts that table only while `cdc_demo.customers` keeps flowing.

Elapsed time per operation is recorded as an **observation, not a KPI
validation**. The formal latency measurement, with the Design Note's five
measurement points, belongs to the M8 window under the revised KPI decision.

The live run cannot happen in CI: `ci.yml`'s `postgres:15` service runs at
`wal_level=replica`. It is a local run recorded by hand, as M7W23T1 and
M7W26T1 were.

## 2. Method

Two terminals: **A** for commands, **B** for the consumer.

```bash
# Phase 1 (A) — clean rebuild and prerequisite checks
./infrastructure/scripts/verify_cdc_prerequisites.sh --rebuild

# Phase 2 (A) — register, then confirm connector, task and topics
curl -s -X POST http://localhost:8083/connectors -H "Content-Type: application/json" -d @services/cdc/debezium_postgres_connector.json
curl -s http://localhost:8083/connectors/subop-postgres-cdc/status
docker compose exec -T kafka kafka-topics --bootstrap-server localhost:29092 --list

# Phase 3 (B) — consumer, left running
python -m services.cdc.kafka_consumer

# Phase 4 (A) — one change at a time, warehouse checked after each
python -m services.cdc.cdc_demo_changes --insert   # then --update, then --delete
docker compose exec -T postgres psql -U subop -d subop -c "SELECT id, status, _cdc_op, _cdc_deleted, _cdc_lsn FROM warehouse.orders ORDER BY id DESC LIMIT 1;"

# Phase 5 — redelivery: count (A), stop consumer (B), rewind (A), restart (B), count (A)
docker compose exec -T postgres psql -U subop -d subop -c "SELECT count(*), max(_cdc_lsn), sum(_cdc_deleted::int) FROM warehouse.orders;"
docker compose exec -T kafka kafka-consumer-groups --bootstrap-server localhost:29092 --group subop-cdc-consumer --reset-offsets --to-earliest --all-topics --execute

# Phase 6 (A) — drift on orders, a change on customers, then status
docker compose exec -T postgres psql -U subop -d subop -c "ALTER TABLE cdc_demo.orders ADD COLUMN note TEXT;"
python -m services.cdc.cdc_demo_changes --insert
docker compose exec -T postgres psql -U subop -d subop -c "INSERT INTO cdc_demo.customers (id, name, city) VALUES (9001, 'E2E Test', 'Bandirma');"
curl -s http://localhost:8000/api/cdc/connectors/subop-postgres-cdc/status
```

The run was executed twice. **Run 1** (06:12 UTC) skipped Phase 2 and is
recorded as aborted in Section 3. **Run 2** (07:01 UTC onward) is the run of
record, Sections 4–9.

## 3. Run 1 — Aborted (Connector Not Registered)

Recorded because this project records failures as well as passes.

### 3.1 Clean rebuild and prerequisite checks — all values as expected

| Check | Expected | Actual | Result |
|---|---|---|---|
| 1 — `wal_level` | `logical` | `logical` | PASS |
| 2 — publication not FOR ALL TABLES | `subop_cdc_pub`, `puballtables = f` | `subop_cdc_pub`, `f` | PASS |
| 3 — published tables | exactly `cdc_demo.orders` (6 columns) and `cdc_demo.customers` (5 columns) | as expected | PASS |
| 4 — CDC role | `subop_cdc`, `rolreplication = t` | `subop_cdc`, `t` | PASS |
| 5 — replica identity | `f` for both tables | `f`, `f` | PASS |
| 6 — seed rows | 3 in each table | 3, 3 | PASS |
| 7 — CDC role SELECT grant | `t` for both tables | `t`, `t` | PASS |

```
--- CHECK 3 — published tables (expect: exactly cdc_demo.orders and cdc_demo.customers) ---
$ SELECT * FROM pg_publication_tables;
    pubname    | schemaname | tablename |                       attnames           | rowfilter
---------------+------------+-----------+------------------------------------------------------+-----------
 subop_cdc_pub | cdc_demo   | orders    | {id,customer_id,status,amount,created_at,updated_at} |
 subop_cdc_pub | cdc_demo   | customers | {id,name,city,created_at,updated_at}           |
(2 rows)

--- CHECK 6 — seed rows (expect: 3 in each table) ---
    tbl    | seed_rows
-----------+-----------
 orders    |         3
 customers |         3
(2 rows)

$ curl -s http://localhost:8083/
{"version":"4.3.0","commit":"a9ce3221537b8653","kafka_cluster_id":"HEHUBbZySryDuc-mYTYW3Q"}

$ curl -s http://localhost:8083/connectors
[]
```

### 3.2 What failed

Phase 2 was not run. With no connector registered, no topics existed:

```
$ python -m services.cdc.kafka_consumer
2026-11-10 09:19:59,571 INFO subscribed to ^subop-postgres-cdc\.cdc_demo\..* as group subop-cdc-consumer
2026-11-10 09:19:59,709 WARNING kafka error on ^subop-postgres-cdc\.cdc_demo\..*: KafkaError{code=UNKNOWN_TOPIC_OR_PART,val=3,str="Subscribed topic not available: ^subop-postgres-cdc\.cdc_demo\..*: Broker: Unknown topic or partition"}
```

Every warehouse check returned `(0 rows)`, the offset reset listed no
topics, and the Phase 6 status call returned:

```
{"error_code":"CDC_CONNECTOR_NOT_FOUND","message":"No such CDC connector.","connector_type":"streaming","retryable":false}
```

Run 1 also left the source altered — the `note` column, plus order 5 and
customer 9001. Registering the connector at that point would have taken the
`note` column into the first snapshot, so the drift test would have proved
nothing. Run 2 therefore started again from `--rebuild`.

## 4. Run 2 — Clean Environment

Run 2's own Phase 1 terminal output was not retained. The prerequisite
script was re-run, without `--rebuild`, after Phase 6. Its output is below.
That Run 2 started from fresh volumes is established by three independent
pieces of evidence:

| Evidence | Value | Shows |
|---|---|---|
| Init script re-executed | Postgres log: `10-cdc-replication.sql` ran, server restart at `07:01:28 UTC` | fresh `postgres_data` volume, before the snapshot at 07:10:05 UTC |
| Kafka cluster ID changed | Run 1 `HEHUBbZySryDuc-mYTYW3Q` → Run 2 `K5anUOlIToK72V2gKhmSAQ` | fresh `kafka_data` volume |
| Order IDs restarted | Run 2's first INSERT is `id=4` again, after seeds 1–3 | Run 1's rows 4 and 5 are gone |

### 4.1 Prerequisite checks, taken after the run

| Check | Expected | Actual | Result |
|---|---|---|---|
| 1 — `wal_level` | `logical` | `logical` | PASS |
| 2 — publication not FOR ALL TABLES | `subop_cdc_pub`, `f` | `subop_cdc_pub`, `f` | PASS |
| 3 — published tables | `orders` (6 columns), `customers` (5 columns) | `orders` has **7** — `note`, added in Phase 6 | expected difference |
| 4 — CDC role | `subop_cdc`, `t` | `subop_cdc`, `t` | PASS |
| 5 — replica identity | `f`, `f` | `f`, `f` | PASS |
| 6 — seed rows | 3, 3 | **4, 4** — order 5 and customer 9001, from Phase 6 | expected difference |
| 7 — CDC role SELECT grant | `t`, `t` | `t`, `t` | PASS |

Both differences come from the run itself. The script still printed
"All checks PASS" with Check 6 at 4 against an expected 3 — see Finding 6.

```
--- CHECK 3 — published tables (expect: exactly cdc_demo.orders and cdc_demo.customers) ---
$ SELECT * FROM pg_publication_tables;
    pubname    | schemaname | tablename |                         attnames           | rowfilter
---------------+------------+-----------+-----------------------------------------------------------+-----------
 subop_cdc_pub | cdc_demo   | orders    | {id,customer_id,status,amount,created_at,updated_at,note} |
 subop_cdc_pub | cdc_demo   | customers | {id,name,city,created_at,updated_at}           |
(2 rows)

--- CHECK 6 — seed rows (expect: 3 in each table) ---
$ SELECT 'orders' AS tbl, count(*) AS seed_rows FROM cdc_demo.orders UNION ALL SELECT 'customers', count(*) FROM cdc_demo.customers;
    tbl    | seed_rows
-----------+-----------
 orders    |         4
 customers |         4
(2 rows)

==============================================================
SECTION 4 — INIT-SCRIPT EXECUTION EVIDENCE
==============================================================
$ docker compose logs postgres --no-color | grep -A 16 '10-cdc-replication.sql'
subop-postgres  | /usr/local/bin/docker-entrypoint.sh: running /docker-entrypoint-initdb.d/10-cdc-replication.sql
subop-postgres  | CREATE ROLE
subop-postgres  | CREATE SCHEMA
subop-postgres  | SET
subop-postgres  | CREATE TABLE
subop-postgres  | ALTER TABLE
subop-postgres  | INSERT 0 3
subop-postgres  | CREATE TABLE
subop-postgres  | ALTER TABLE
subop-postgres  | INSERT 0 3
subop-postgres  | CREATE PUBLICATION
subop-postgres  | GRANT
subop-postgres  | GRANT
subop-postgres  | ALTER DEFAULT PRIVILEGES
subop-postgres  |
subop-postgres  |
subop-postgres  | 2026-11-10 07:01:28.124 UTC [48] LOG:  received fast shutdown request

$ curl -s http://localhost:8083/
{"version":"4.3.0","commit":"a9ce3221537b8653","kafka_cluster_id":"K5anUOlIToK72V2gKhmSAQ"}
```

## 5. Connector Registration

```
$ curl -s -X POST http://localhost:8083/connectors -H "Content-Type: application/json" -d @services/cdc/debezium_postgres_connector.json
{"name":"subop-postgres-cdc","config":{"connector.class":"io.debezium.connector.postgresql.PostgresConnector","topic.prefix":"subop-postgres-cdc","database.hostname":"postgres","database.port":"5432","database.dbname":"subop","database.user":"subop_cdc","database.password":"cdc_dev","plugin.name":"pgoutput","slot.name":"subop_cdc_slot","publication.name":"subop_cdc_pub","publication.autocreate.mode":"disabled","table.include.list":"cdc_demo.orders,cdc_demo.customers","decimal.handling.mode":"string","tombstones.on.delete":"false","column.propagate.source.type":".*cdc_demo\\.(orders|customers)\\..*","tasks.max":"1","name":"subop-postgres-cdc"},"tasks":[],"type":"source"}
$ curl -s http://localhost:8083/connectors/subop-postgres-cdc/status
{"name":"subop-postgres-cdc","connector":{"state":"RUNNING","worker_id":"172.19.0.9:8083","version":"3.6.3.Final"},"tasks":[],"type":"source"}
$ docker compose exec -T kafka kafka-topics --bootstrap-server localhost:29092 --list
__consumer_offsets
subop-connect-configs
subop-connect-offsets
subop-connect-status
subop-postgres-cdc.cdc_demo.customers
subop-postgres-cdc.cdc_demo.orders
```

Immediately after registration the connector is `RUNNING` with no task (see
Finding 3). Re-polled after the run, Connect reports both:

```
$ curl -s http://localhost:8083/connectors/subop-postgres-cdc/status
{"name":"subop-postgres-cdc","connector":{"state":"RUNNING","worker_id":"172.19.0.9:8083","version":"3.6.3.Final"},"tasks":[{"id":0,"state":"RUNNING","worker_id":"172.19.0.9:8083","version":"3.6.3.Final"}],"type":"source"}
```

| Check | Expected | Actual | Result |
|---|---|---|---|
| Connector state | `RUNNING` | `RUNNING` | PASS |
| Task 0 state | `RUNNING` | `RUNNING` | PASS |
| One topic per published table | `…cdc_demo.orders`, `…cdc_demo.customers` | both present | PASS |

## 6. Change Events Reach the Warehouse

### 6.1 Initial snapshot (consumer, terminal B)

```
$ python -m services.cdc.kafka_consumer
2026-11-10 10:11:38,916 INFO subscribed to ^subop-postgres-cdc\.cdc_demo\..* as group subop-cdc-consumer
2026-11-10 10:11:42,268 INFO snapshot cdc_demo.orders id=1 ts_ms=1794294605441 lsn=26657808 -> warehouse
2026-11-10 10:11:42,325 INFO snapshot cdc_demo.orders id=2 ts_ms=1794294605441 lsn=26657808 -> warehouse
2026-11-10 10:11:42,351 INFO snapshot cdc_demo.orders id=3 ts_ms=1794294605441 lsn=26657808 -> warehouse
2026-11-10 10:11:42,383 INFO snapshot cdc_demo.customers id=1001 ts_ms=1794294605441 lsn=26657808 -> warehouse
2026-11-10 10:11:42,413 INFO snapshot cdc_demo.customers id=1002 ts_ms=1794294605441 lsn=26657808 -> warehouse
2026-11-10 10:11:42,439 INFO snapshot cdc_demo.customers id=1003 ts_ms=1794294605441 lsn=26657808 -> warehouse
```

### 6.2 INSERT, UPDATE, DELETE (terminal A)

```
$ python -m services.cdc.cdc_demo_changes --insert
INSERT id=4 commit_ts=2026-11-10T07:11:51.194490+00:00 commit_ts_ms=1794294711194 customer_id=9001
$ docker compose exec -T postgres psql -U subop -d subop -c "SELECT id, status, _cdc_op, _cdc_deleted, _cdc_lsn FROM warehouse.orders ORDER BY id DESC LIMIT 1;"
 id | status  | _cdc_op | _cdc_deleted | _cdc_lsn
----+---------+---------+--------------+----------
  4 | pending | insert  | f            | 26946312
(1 row)

$ python -m services.cdc.cdc_demo_changes --update
UPDATE id=4 commit_ts=2026-11-10T07:12:10.918173+00:00 commit_ts_ms=1794294730918 status=shipped
$ docker compose exec -T postgres psql -U subop -d subop -c "SELECT id, status, _cdc_op, _cdc_deleted, _cdc_lsn FROM warehouse.orders ORDER BY id DESC LIMIT 1;"
 id | status  | _cdc_op | _cdc_deleted | _cdc_lsn
----+---------+---------+--------------+----------
  4 | shipped | update  | f            | 26948304
(1 row)

$ python -m services.cdc.cdc_demo_changes --delete
DELETE id=4 commit_ts=2026-11-10T07:12:25.867901+00:00 commit_ts_ms=1794294745867
$ docker compose exec -T postgres psql -U subop -d subop -c "SELECT id, status, _cdc_op, _cdc_deleted, _cdc_lsn FROM warehouse.orders ORDER BY id DESC LIMIT 1;"
 id | status  | _cdc_op | _cdc_deleted | _cdc_lsn
----+---------+---------+--------------+----------
  4 | shipped | delete  | t            | 26949984
(1 row)
```

Consumer, terminal B:

```
2026-11-10 10:11:51,689 INFO insert cdc_demo.orders id=4 ts_ms=1794294711194 lsn=26946312 -> warehouse
2026-11-10 10:12:11,237 INFO update cdc_demo.orders id=4 ts_ms=1794294730918 lsn=26948304 -> warehouse
2026-11-10 10:12:26,780 INFO delete cdc_demo.orders id=4 ts_ms=1794294745867 lsn=26949984 -> warehouse
```

| Operation | Expected in `warehouse.orders` | Actual | Result |
|---|---|---|---|
| INSERT | new row, `pending`, `_cdc_deleted = f` | id 4, `pending`, `insert`, `f` | PASS |
| UPDATE | same row, `shipped`, higher LSN | id 4, `shipped`, `update`, LSN 26946312 → 26948304 | PASS |
| DELETE | row kept, `_cdc_deleted = t` | id 4, `delete`, `t`, LSN 26949984 | PASS |

No scheduled pipeline run was involved: the consumer wrote each row through
`WarehouseSink`, which uses the Abstraction Layer's `execute_write`.

**Delete handling — decision recorded.** Deletes are **soft**: the row is kept
with `_cdc_deleted = TRUE` and the delete's LSN, rather than removed. A hard
delete would leave nothing for the LSN guard to compare against, so a
redelivered older INSERT or UPDATE could bring the row back. Readers filter on
`_cdc_deleted`. This is the M7W26T4 implementation, now exercised live.

### 6.3 Elapsed time — observation, not a KPI validation

Source commit time (`commit_ts`, Postgres container clock) against the
consumer's log line (host clock). The two clocks are not synchronised, so
these figures are indicative only.

| Change | Source commit (UTC) | Consumer handled (UTC) | Elapsed |
|---|---|---|---|
| INSERT order 4 | 07:11:51.194 | 07:11:51.689 | 0.495 s |
| UPDATE order 4 | 07:12:10.918 | 07:12:11.237 | 0.319 s |
| DELETE order 4 | 07:12:25.868 | 07:12:26.780 | 0.912 s |
| INSERT customer 9001 | 07:14:09.839 | 07:14:10.512 | 0.673 s |

Week 23 observed **56 seconds** for a single change against an idle database,
traced to WAL flush behaviour rather than processing cost. These sub-second
figures come from a database with recent activity. They do not overturn the
Week 23 finding. They are not a measurement against the 30-second KPI either:
neither run used the Design Note's five measurement points. Formal
measurement remains in the M8 window.

## 7. Redelivery Is Idempotent

Before, with the consumer running:

```
$ docker compose exec -T postgres psql -U subop -d subop -c "SELECT count(*), max(_cdc_lsn), sum(_cdc_deleted::int) FROM warehouse.orders;"
 count |   max    | sum
-------+----------+-----
     4 | 26949984 |   1
(1 row)
```

Consumer stopped (Ctrl+C in B), group rewound to the start of both topics:

```
$ docker compose exec -T kafka kafka-consumer-groups --bootstrap-server localhost:29092 --group subop-cdc-consumer --reset-offsets --to-earliest --all-topics --execute

GROUP                          TOPIC                          PARTITION  NEW-OFFSET
subop-cdc-consumer             subop-postgres-cdc.cdc_demo.customers 0          0
subop-cdc-consumer             subop-postgres-cdc.cdc_demo.orders 0          0
```

Consumer restarted (B) — every message delivered a second time:

```
$ python -m services.cdc.kafka_consumer
2026-11-10 10:13:52,856 INFO subscribed to ^subop-postgres-cdc\.cdc_demo\..* as group subop-cdc-consumer
2026-11-10 10:13:55,979 INFO snapshot cdc_demo.customers id=1001 ts_ms=1794294605441 lsn=26657808 -> unchanged (not newer)
2026-11-10 10:13:56,005 INFO snapshot cdc_demo.customers id=1002 ts_ms=1794294605441 lsn=26657808 -> unchanged (not newer)
2026-11-10 10:13:56,043 INFO snapshot cdc_demo.customers id=1003 ts_ms=1794294605441 lsn=26657808 -> unchanged (not newer)
2026-11-10 10:13:56,071 INFO snapshot cdc_demo.orders id=1 ts_ms=1794294605441 lsn=26657808 -> unchanged (not newer)
2026-11-10 10:13:56,096 INFO snapshot cdc_demo.orders id=2 ts_ms=1794294605441 lsn=26657808 -> unchanged (not newer)
2026-11-10 10:13:56,122 INFO snapshot cdc_demo.orders id=3 ts_ms=1794294605441 lsn=26657808 -> unchanged (not newer)
2026-11-10 10:13:56,151 INFO insert cdc_demo.orders id=4 ts_ms=1794294711194 lsn=26946312 -> unchanged (not newer)
2026-11-10 10:13:56,175 INFO update cdc_demo.orders id=4 ts_ms=1794294730918 lsn=26948304 -> unchanged (not newer)
2026-11-10 10:13:56,202 INFO delete cdc_demo.orders id=4 ts_ms=1794294745867 lsn=26949984 -> unchanged (not newer)
```

After:

```
$ docker compose exec -T postgres psql -U subop -d subop -c "SELECT count(*), max(_cdc_lsn), sum(_cdc_deleted::int) FROM warehouse.orders;"
 count |   max    | sum
-------+----------+-----
     4 | 26949984 |   1
(1 row)
```

The "after" query was run once Phase 6 had finished. `warehouse.orders` had
received nothing in between, because the table was halted from 07:14:08 UTC
(Section 8). The figures therefore still describe the state after replay.

| Check | Expected | Actual | Result |
|---|---|---|---|
| All 9 replayed messages leave the warehouse unchanged | `unchanged (not newer)` × 9 | × 9 | PASS |
| Row count, max LSN, deleted count | identical before and after | `4 / 26949984 / 1` both | PASS |

## 8. Drift Halts One Table Only

```
$ docker compose exec -T postgres psql -U subop -d subop -c "ALTER TABLE cdc_demo.orders ADD COLUMN note TEXT;"
ALTER TABLE
$ python -m services.cdc.cdc_demo_changes --insert
INSERT id=5 commit_ts=2026-11-10T07:14:08.058051+00:00 commit_ts_ms=1794294848058 customer_id=9001
$ docker compose exec -T postgres psql -U subop -d subop -c "INSERT INTO cdc_demo.customers (id, name, city) VALUES (9001, 'E2E Test', 'Bandirma');"
INSERT 0 1
```

Consumer, terminal B:

```
2026-11-10 10:14:08,509 ERROR halted cdc_demo.orders (CDC_SCHEMA_DRIFT_DETECTED): Schema drift detected on cdc_demo.orders: columns added ['note']. Consumption of this table is halted; other tables are unaffected. Resolution is manual.
2026-11-10 10:14:10,512 INFO insert cdc_demo.customers id=9001 ts_ms=1794294849839 lsn=26972240 -> warehouse
```

Status endpoint, after the Finding 4 fix and the Finding 5 image rebuild:

```
$ curl -s http://localhost:8000/api/cdc/connectors/subop-postgres-cdc/status
{"connector_id":"subop-postgres-cdc","connector_name":"subop-postgres-cdc","state":"RUNNING","task_state":"RUNNING","last_event_ts_ms":1794294849839,"events_processed":10,"halted":true,"tables":[{"table":"cdc_demo.orders","events_processed":6,"last_event_ts_ms":1794294745867,"last_lsn":26949984,"halted":true,"halt_error_code":"CDC_SCHEMA_DRIFT_DETECTED","halt_reason":"Schema drift detected on cdc_demo.orders: columns added ['note']. Consumption of this table is halted; other tables are unaffected. Resolution is manual.","halted_at":"2026-11-10T07:14:08.503297+00:00"},{"table":"cdc_demo.customers","events_processed":4,"last_event_ts_ms":1794294849839,"last_lsn":26972240,"halted":false,"halt_error_code":null,"halt_reason":null,"halted_at":null}],"halted_tables":["cdc_demo.orders"],"drift_state":"CDC_SCHEMA_DRIFT_DETECTED","lag_ms":null,"latency":null}
```

| Check | Expected | Actual | Result |
|---|---|---|---|
| `orders` halts on the added column | `CDC_SCHEMA_DRIFT_DETECTED`, `['note']` | as expected | PASS |
| Order 5 does not reach the warehouse | `orders` last LSN unchanged | 26949984 (the DELETE's) | PASS |
| `customers` keeps flowing | customer 9001 reaches the warehouse | `-> warehouse`, LSN 26972240 | PASS |
| Consumer stays up | process continues after the halt | customer 9001 handled 2 s later | PASS |
| Endpoint reports the halt | `halted_tables`, `drift_state` | `["cdc_demo.orders"]`, `CDC_SCHEMA_DRIFT_DETECTED` | PASS |
| Latency fields present and null | `lag_ms`, `latency` = `null` | `null`, `null` | PASS |
| Event counts | distinct events: `orders` 6, `customers` 4 | 6, 4, total 10 | PASS |

The halt is left in place for the UI check in M7W27T7.

## 9. Test Suite

With the Finding 4 change, against a local PostgreSQL that started from the
**pre-change** `cdc_meta.table_state` schema, so the migration was exercised:

```
$ python -m pytest tests/test_cdc_state_store.py tests/test_warehouse_sink.py tests/test_kafka_consumer.py tests/test_cdc_api.py tests/test_cdc_normalizer.py -q
165 passed in 0.84s
```

Black and flake8 both pass against `.flake8`'s `max-line-length = 100`.

## 10. Findings

### Finding 1 — Run 1 aborted: connector not registered

Phase 2 was skipped, so no topics existed and nothing was captured
(Section 3). Run 1 also altered the source, which would have invalidated the
drift test.

**Resolution:** Run 2 started again from `--rebuild`.

**Status:** ✅ resolved.

### Finding 2 — A consumer started before its topics exist is slow to see them

The consumer subscribes by pattern. Its settings do not override librdkafka's
`topic.metadata.refresh.interval.ms` (default 300000 ms), so a topic created
after the consumer starts can take up to about five minutes to be noticed.

**Resolution for this run:** topics confirmed with `kafka-topics --list`
before the consumer started.

**Status:** recorded. Starting order is now part of the procedure. A shorter
refresh interval is a candidate for Omer's offset and slot lifecycle work in
M8.

### Finding 3 — Connector `RUNNING` with no task, immediately after registration

The status call directly after the POST returned `"tasks":[]`. Re-polled, task
0 was `RUNNING`. This repeats M7W26T1 Finding 5.

**Resolution:** the endpoint exposes `task_state` separately, and the record
shows a re-poll with both states.

**Status:** ✅ resolved by procedure.

### Finding 4 — `events_processed` counted redeliveries

After the Phase 5 replay, the endpoint reported `orders` at **12** and
`customers` at **7**. The real figures are 6 and 4: every message had been
counted on each delivery. `record_event()` added 1 per handled message,
including redeliveries that left the warehouse unchanged. A consumer restart
would therefore have doubled the count shown in the UI.

**Resolution:** `events_processed` is now derived from `cdc_meta.event_log`.
Its unique key `(table_name, lsn, op, row_key)` already stores each event
once. The `table_state.events_processed` column is dropped with
`DROP COLUMN IF EXISTS`, so existing databases migrate on the next
`ensure_schema()`. The response shape is unchanged. Three tests were added,
including one that a redelivery does not raise the count.

**Status:** ✅ resolved — verified live: `orders` 12 → 6, `customers` 7 → 4.

### Finding 5 — `subop-api` served code older than `develop`

The first live status response had no `halted_tables` and no `drift_state`.
Both fields have been in `services/cdc/api.py` since `b54e296`, and
`CDCPage.tsx` reads both. `docker compose down -v` removes volumes but not
images, and `up -d` reuses an existing `subop-subop-api` image.

**Resolution:** `docker compose up -d --build subop-api`. The build reported
its `COPY services` step as `CACHED`, so the container's content was checked
directly:

```
$ docker compose exec -T subop-api grep -c "DROP COLUMN IF EXISTS events_processed" services/cdc/state_store.py
1
```

**Status:** ✅ resolved for this run. Recommended: `verify_cdc_prerequisites.sh
--rebuild` should use `up -d --build`, so every clean rebuild also rebuilds
the API image.

### Finding 6 — "All checks PASS" means the queries ran, not that values matched

In the post-run checks, Check 6 returned 4 and 4 against "expect: 3", and the
script still printed "All checks PASS". `check()` counts a failure only when
`psql` exits non-zero. The expected values exist only in the check titles.

**Resolution for this run:** every check's actual value is compared by hand
against its expectation, in the tables of Sections 3.1 and 4.1. All of Run 1's
values matched.

**Fix:** each check still prints its full result, then runs a compact
assertion query and compares the result with the expected value. A mismatch,
or an assertion query that errors, counts as a failure. Check 3 now also
asserts column counts: 5 for `customers`, 6 for `orders`.

**Tested** against a local PostgreSQL 16 at `wal_level=logical`, loaded from
`cdc_replication_setup.sql`:

- **Correct database:** all 7 checks report `OK`.
- **Database left as Run 2 left it**, plus `customers` reset to replica
  identity `d`: Checks 3, 5 and 6 fail with the actual value, e.g.
  `FAIL: expected '3,3', got '4,4'`.

**Status:** ✅ resolved under this task.

## 11. Conclusion

From a clean environment, a committed INSERT, UPDATE and DELETE each arrived
as a row in `warehouse.orders` with no scheduled pipeline run. Each was
written through the Abstraction Layer. Every message replayed from the start
of both topics left the warehouse unchanged. An `ALTER TABLE` on
`cdc_demo.orders` halted that table only. `cdc_demo.customers` kept flowing,
and the consumer stayed up. The status endpoint reported the halt, the
distinct event counts and null latency fields.

This substantiates Milestone 7's claim for the backend. Two items remain
outside this record:

- **M7W27T7 — UI against the real halt.** Pending Beyza's live swap
  (M7W27T6). The halt is left in place for it. If the stack is rebuilt
  first, Section 8 is repeatable on its own.
- **Latency.** The sub-second figures in Section 6.3 are observations.
  Formal measurement against the 30-second KPI is in the M8 window.
