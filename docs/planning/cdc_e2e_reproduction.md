# CDC Runbook Reproduction Record

**Task ID:** M8W29T11 (reassigned from Mert to Abdalla on 23 November 2026)
**Project:** SUBOP
**Date:** 23 November 2026
**Branch:** `develop` at `51b7142` (M8W29T1 and M8W29T2 merged)
**Environment:** Local Development — Docker Compose (Windows, Git Bash)
**Runbook reproduced:** `docs/planning/cdc_e2e_verification.md` (M7W27T1), Phases 1–5
**Status:** ✅ Phases 1–5 reproduce from a clean environment. INSERT, UPDATE and DELETE reach `warehouse.orders`; a full replay of 9 messages changes nothing; the new M8 latency rows are written once per change and not duplicated by redelivery. One runbook defect found (Finding 1).

## 1. Objective

Run the M7 end-to-end runbook as written, from a clean rebuild, and record
every command and its output verbatim. Any step that is ambiguous, or that
works only because of something not written in the runbook, is a finding.

**Scope.** Phases 1–5 only, as the Weeks 28–29 plan names them. Phase 6 (drift)
is skipped on purpose: it alters `cdc_demo.orders` and halts that table, which
would block the latency KPI runs (M8W29T4) that start from this stack.

**Limit of this run.** The plan intended a second person on a second machine.
It was reassigned to the runbook's author, on the machine the M7 run used. A
step that works only on this machine may therefore go unnoticed (Finding 4).

## 2. Method

Two terminals: **A** for commands, **B** for the consumer. Commands are the
runbook's Section 2, run in order. One check was added to Phases 4 and 5 that
the M7 runbook does not have, marked *(addition)*: it reads the M8 latency
table (`cdc_meta.event_latency`, M8W28T4), as a preflight for M8W29T4.

```bash
# (A) Use the merged code; Phase 1 builds subop-api from it
git checkout develop
git pull origin develop

# Phase 1 (A)
./infrastructure/scripts/verify_cdc_prerequisites.sh --rebuild

# Phase 2 (A)
curl -s -X POST http://localhost:8083/connectors -H "Content-Type: application/json" -d @services/cdc/debezium_postgres_connector.json
curl -s http://localhost:8083/connectors/subop-postgres-cdc/status
docker compose exec -T kafka kafka-topics --bootstrap-server localhost:29092 --list

# Phase 3 (B)
python -m services.cdc.kafka_consumer

# Phase 4 (A) — --insert, --update, --delete, each followed by:
docker compose exec -T postgres psql -U subop -d subop -c "SELECT id, status, _cdc_op, _cdc_deleted, _cdc_lsn FROM warehouse.orders ORDER BY id DESC LIMIT 1;"

# (addition) after Phase 4 and after Phase 5
docker compose exec -T postgres psql -U subop -d subop -c "SELECT op, t4_ms - t0_ms AS e2e_ms FROM cdc_meta.event_latency ORDER BY id;"

# Phase 5 — count (A), Ctrl+C (B), rewind (A), restart (B), count (A)
docker compose exec -T postgres psql -U subop -d subop -c "SELECT count(*), max(_cdc_lsn), sum(_cdc_deleted::int) FROM warehouse.orders;"
docker compose exec -T kafka kafka-consumer-groups --bootstrap-server localhost:29092 --group subop-cdc-consumer --reset-offsets --to-earliest --all-topics --execute
```

The run was done in two passes. **Pass 1** followed the runbook's Section 2
command block literally and so ran only the INSERT, the Phase 2 status check
once, and the Phase 5 "before" count (Finding 1). **Pass 2**, on the same
stack minutes later, completed the missing steps: the status re-check, UPDATE
and DELETE, and a full Phase 5 with counts before and after. Both passes are
recorded as they happened. Consumer timestamps are local time (UTC+3).

## 3. Phase 1 — Clean Rebuild and Prerequisite Checks

`docker compose down -v --remove-orphans` removed every container and all nine
volumes; `up -d --build --quiet-pull` rebuilt `subop-api` from `develop`.

```
 ✔ Container subop-mssql       Healthy                                     126.4s
 ✔ Container subop-mysql       Healthy                                      66.7s
 ✔ Container subop-oracle      Healthy                                     253.3s
 ✔ Container subop-postgres    Healthy                                      28.2s
 ✔ Container subop-zookeeper   Healthy                                      60.2s
 ✔ Container subop-kafka       Healthy                                     176.3s
 ✔ Container subop-api         Started                                     256.0s
 ✔ Container subop-connect     Started                                     177.6s

Waiting for Kafka Connect's REST API (up to 300s)...
Connect REST responded after ~55s.
```

| Check | Expected | Actual | Result |
|---|---|---|---|
| 1 — `wal_level` | `logical` | `logical` | PASS |
| 2 — publication scope | `subop_cdc_pub`, `puballtables = f` | `subop_cdc_pub`, `f` | PASS |
| 3 — published tables | `customers` (5 columns), `orders` (6) | `customers(5)`, `orders(6)` | PASS |
| 4 — CDC role | `subop_cdc`, `rolreplication = t` | `subop_cdc`, `t` | PASS |
| 5 — replica identity | `f` for both | `customers:f`, `orders:f` | PASS |
| 6 — seed rows | 3 in each table | `3, 3` | PASS |
| 7 — SELECT grant | `t` for both | `t, t` | PASS |
| Init script ran | `10-cdc-replication.sql` in the Postgres log | present: `CREATE ROLE` … `ALTER DEFAULT PRIVILEGES` | PASS |
| Containers | all up, health-checked ones healthy | all 10 up; 8 healthy | PASS |
| Connect readiness | REST answers, no connectors, Postgres plugin present | `[]`, `PostgresConnector` | PASS |

Script summary: `All checks PASS. Proceed to connector registration.`

## 4. Phase 2 — Connector Registration

Pass 1, immediately after registration:

```
$ curl -s -X POST http://localhost:8083/connectors -H "Content-Type: application/json" -d @services/cdc/debezium_postgres_connector.json
{"name":"subop-postgres-cdc","config":{...,"slot.name":"subop_cdc_slot","publication.name":"subop_cdc_pub",...,"table.include.list":"cdc_demo.orders,cdc_demo.customers",...},"tasks":[],"type":"source"}
$ curl -s http://localhost:8083/connectors/subop-postgres-cdc/status
{"name":"subop-postgres-cdc","connector":{"state":"RUNNING","worker_id":"172.19.0.10:8083","version":"3.6.3.Final"},"tasks":[],"type":"source"}
$ docker compose exec -T kafka kafka-topics --bootstrap-server localhost:29092 --list
__consumer_offsets
subop-connect-configs
subop-connect-offsets
subop-connect-status
subop-postgres-cdc.cdc_demo.customers
subop-postgres-cdc.cdc_demo.orders
```

Pass 2, re-polled:

```
$ curl -s http://localhost:8083/connectors/subop-postgres-cdc/status
{"name":"subop-postgres-cdc","connector":{"state":"RUNNING","worker_id":"172.19.0.10:8083","version":"3.6.3.Final"},"tasks":[{"id":0,"state":"RUNNING","worker_id":"172.19.0.10:8083","version":"3.6.3.Final"}],"type":"source"}
```

| Check | Expected | Actual | Result |
|---|---|---|---|
| Connector state | `RUNNING` | `RUNNING` | PASS |
| Task 0 state | `RUNNING` | none at first; `RUNNING` on re-poll | PASS (M7 Finding 3 reproduces) |
| One topic per published table | both present | both present | PASS |

## 5. Phases 3 and 4 — Change Events Reach the Warehouse

Consumer (B), initial snapshot:

```
$ python -m services.cdc.kafka_consumer
2026-11-23 17:23:33,817 INFO subscribed to ^subop-postgres-cdc\.cdc_demo\..* as group subop-cdc-consumer
2026-11-23 17:23:37,163 INFO snapshot cdc_demo.orders id=1 ts_ms=1795443732211 lsn=26451928 -> warehouse
2026-11-23 17:23:37,240 INFO snapshot cdc_demo.orders id=2 ts_ms=1795443732211 lsn=26451928 -> warehouse
2026-11-23 17:23:37,276 INFO snapshot cdc_demo.orders id=3 ts_ms=1795443732211 lsn=26451928 -> warehouse
2026-11-23 17:23:37,327 INFO snapshot cdc_demo.customers id=1001 ts_ms=1795443732211 lsn=26451928 -> warehouse
2026-11-23 17:23:37,358 INFO snapshot cdc_demo.customers id=1002 ts_ms=1795443732211 lsn=26451928 -> warehouse
2026-11-23 17:23:37,386 INFO snapshot cdc_demo.customers id=1003 ts_ms=1795443732211 lsn=26451928 -> warehouse
```

INSERT (pass 1, A):

```
$ python -m services.cdc.cdc_demo_changes --insert
INSERT id=4 commit_ts=2026-11-23T14:24:11.138622+00:00 commit_ts_ms=1795443851138 customer_id=9001
$ docker compose exec -T postgres psql -U subop -d subop -c "SELECT id, status, _cdc_op, _cdc_deleted, _cdc_lsn FROM warehouse.orders ORDER BY id DESC LIMIT 1;"
 id | status  | _cdc_op | _cdc_deleted | _cdc_lsn
----+---------+---------+--------------+----------
  4 | pending | insert  | f            | 26781008
(1 row)
```

UPDATE and DELETE (pass 2, A):

```
$ python -m services.cdc.cdc_demo_changes --update
UPDATE id=4 commit_ts=2026-11-23T14:31:12.538901+00:00 commit_ts_ms=1795444272538 status=shipped
$ docker compose exec -T postgres psql ... (same query)
 id | status  | _cdc_op | _cdc_deleted | _cdc_lsn
----+---------+---------+--------------+----------
  4 | shipped | update  | f            | 26793168
(1 row)

$ python -m services.cdc.cdc_demo_changes --delete
DELETE id=4 commit_ts=2026-11-23T14:31:15.359107+00:00 commit_ts_ms=1795444275359
$ docker compose exec -T postgres psql ... (same query)
 id | status  | _cdc_op | _cdc_deleted | _cdc_lsn
----+---------+---------+--------------+----------
  4 | shipped | delete  | t            | 26803816
(1 row)
```

Consumer (B):

```
2026-11-23 17:24:11,628 INFO insert cdc_demo.orders id=4 ts_ms=1795443851138 lsn=26781008 -> warehouse
2026-11-23 17:31:13,134 INFO update cdc_demo.orders id=4 ts_ms=1795444272538 lsn=26793168 -> warehouse
2026-11-23 17:31:15,583 INFO delete cdc_demo.orders id=4 ts_ms=1795444275359 lsn=26803816 -> warehouse
```

The UPDATE and DELETE lines come from the consumer restarted at the end of
pass 1 (Section 6.1), which was still running when pass 2 began.

| Operation | Expected in `warehouse.orders` | Actual | Result |
|---|---|---|---|
| INSERT | new row, `pending`, `_cdc_deleted = f` | id 4, `pending`, `insert`, `f` | PASS |
| UPDATE | same row, `shipped`, higher LSN | id 4, `shipped`, `update`, LSN 26781008 → 26793168 | PASS |
| DELETE | row kept, `_cdc_deleted = t` | id 4, `delete`, `t`, LSN 26803816 | PASS |

*(addition)* Latency rows after Phase 4:

```
$ docker compose exec -T postgres psql -U subop -d subop -c "SELECT op, t4_ms - t0_ms AS e2e_ms FROM cdc_meta.event_latency ORDER BY id;"
   op   | e2e_ms
--------+--------
 insert |    490
 update |    596
 delete |    224
(3 rows)
```

One row per change, none for the six snapshot rows, as M8W28T4 intends. These
three values are a preflight, **not** the KPI: the KPI run is M8W29T4, with its
own protocol. The INSERT's 490 ms agrees with the two logs: source commit
14:24:11.138 UTC, consumer line 17:24:11,628 (UTC+3).

## 6. Phase 5 — Redelivery Is Idempotent

### 6.1 Pass 1 (after the INSERT only)

```
$ docker compose exec -T postgres psql -U subop -d subop -c "SELECT count(*), max(_cdc_lsn), sum(_cdc_deleted::int) FROM warehouse.orders;"
 count |   max    | sum
-------+----------+-----
     4 | 26781008 |   0
(1 row)
```

Consumer stopped (Ctrl+C in B), group rewound (A):

```
$ docker compose exec -T kafka kafka-consumer-groups --bootstrap-server localhost:29092 --group subop-cdc-consumer --reset-offsets --to-earliest --all-topics --execute

GROUP                          TOPIC                          PARTITION  NEW-OFFSET
subop-cdc-consumer             subop-postgres-cdc.cdc_demo.customers 0          0
subop-cdc-consumer             subop-postgres-cdc.cdc_demo.orders 0          0
```

Consumer restarted (B):

```
$ python -m services.cdc.kafka_consumer
2026-11-23 17:27:33,279 INFO subscribed to ^subop-postgres-cdc\.cdc_demo\..* as group subop-cdc-consumer
2026-11-23 17:27:36,544 INFO snapshot cdc_demo.customers id=1001 ts_ms=1795443732211 lsn=26451928 -> unchanged (not newer)
2026-11-23 17:27:36,568 INFO snapshot cdc_demo.customers id=1002 ts_ms=1795443732211 lsn=26451928 -> unchanged (not newer)
2026-11-23 17:27:36,595 INFO snapshot cdc_demo.customers id=1003 ts_ms=1795443732211 lsn=26451928 -> unchanged (not newer)
2026-11-23 17:27:36,621 INFO snapshot cdc_demo.orders id=1 ts_ms=1795443732211 lsn=26451928 -> unchanged (not newer)
2026-11-23 17:27:36,646 INFO snapshot cdc_demo.orders id=2 ts_ms=1795443732211 lsn=26451928 -> unchanged (not newer)
2026-11-23 17:27:36,669 INFO snapshot cdc_demo.orders id=3 ts_ms=1795443732211 lsn=26451928 -> unchanged (not newer)
2026-11-23 17:27:36,692 INFO insert cdc_demo.orders id=4 ts_ms=1795443851138 lsn=26781008 -> unchanged (not newer)
```

*(addition)* `cdc_meta.event_latency` still held one row (`insert | 490`).
The "after" count was not run in pass 1 (Finding 1), so pass 1 shows the
replay but does not prove the table unchanged. Pass 2 does.

### 6.2 Pass 2 (after INSERT, UPDATE and DELETE)

Before:

```
$ docker compose exec -T postgres psql -U subop -d subop -c "SELECT count(*), max(_cdc_lsn), sum(_cdc_deleted::int) FROM warehouse.orders;"
 count |   max    | sum
-------+----------+-----
     4 | 26803816 |   1
(1 row)
```

Consumer stopped (Ctrl+C in B), group rewound (A) — same output as 6.1, both
partitions to offset 0. Consumer restarted (B):

```
$ python -m services.cdc.kafka_consumer
2026-11-23 17:32:17,108 INFO subscribed to ^subop-postgres-cdc\.cdc_demo\..* as group subop-cdc-consumer
2026-11-23 17:32:20,254 INFO snapshot cdc_demo.customers id=1001 ts_ms=1795443732211 lsn=26451928 -> unchanged (not newer)
2026-11-23 17:32:20,276 INFO snapshot cdc_demo.customers id=1002 ts_ms=1795443732211 lsn=26451928 -> unchanged (not newer)
2026-11-23 17:32:20,296 INFO snapshot cdc_demo.customers id=1003 ts_ms=1795443732211 lsn=26451928 -> unchanged (not newer)
2026-11-23 17:32:20,318 INFO snapshot cdc_demo.orders id=1 ts_ms=1795443732211 lsn=26451928 -> unchanged (not newer)
2026-11-23 17:32:20,341 INFO snapshot cdc_demo.orders id=2 ts_ms=1795443732211 lsn=26451928 -> unchanged (not newer)
2026-11-23 17:32:20,365 INFO snapshot cdc_demo.orders id=3 ts_ms=1795443732211 lsn=26451928 -> unchanged (not newer)
2026-11-23 17:32:20,388 INFO insert cdc_demo.orders id=4 ts_ms=1795443851138 lsn=26781008 -> unchanged (not newer)
2026-11-23 17:32:20,417 INFO update cdc_demo.orders id=4 ts_ms=1795444272538 lsn=26793168 -> unchanged (not newer)
2026-11-23 17:32:20,444 INFO delete cdc_demo.orders id=4 ts_ms=1795444275359 lsn=26803816 -> unchanged (not newer)
```

After:

```
$ docker compose exec -T postgres psql -U subop -d subop -c "SELECT count(*), max(_cdc_lsn), sum(_cdc_deleted::int) FROM warehouse.orders;"
 count |   max    | sum
-------+----------+-----
     4 | 26803816 |   1
(1 row)

$ docker compose exec -T postgres psql -U subop -d subop -c "SELECT op, t4_ms - t0_ms AS e2e_ms FROM cdc_meta.event_latency ORDER BY id;"
   op   | e2e_ms
--------+--------
 insert |    490
 update |    596
 delete |    224
(3 rows)
```

| Check | Expected | Actual | Result |
|---|---|---|---|
| All 9 replayed messages leave the warehouse unchanged | `unchanged (not newer)` × 9 | × 9 | PASS |
| Row count, max LSN, deleted count | identical before and after | `4 / 26803816 / 1` both | PASS |
| *(addition)* Latency rows after replay | still 3; a redelivery is a no-op | 3 | PASS |

The consumer was left running after this pass: M8W29T4 starts from this state.

## 7. Findings

### Finding 1 — Three runbook steps exist only as comments

**Observed.** Pass 1 followed Section 2's command block line by line and ran
only the INSERT, one status check and one count. Three steps are written only
as comments or prose, not as commands:

| Step | Where the runbook keeps it |
|---|---|
| `--update` and `--delete`, each followed by the warehouse query | comment: `# then --update, then --delete` |
| Phase 5's "after" count | comment: `count (A), stop consumer (B), rewind (A), restart (B), count (A)` — the count query appears once |
| Re-poll the connector status after registration | Section 5 prose and Finding 3, not Section 2 |

**Impact.** A literal run skips two of the three operations and the very count
that proves redelivery is idempotent, yet nothing fails, so it looks complete.

**Resolution.** Rewrite Section 2 so every step is its own command line,
including both counts and a `sleep 10` before the status re-poll.
Owner: Abdalla, carried to M9 Week 1 (small, bounded; suitable for Mert).

### Finding 2 — M7 Finding 3 reproduces

The connector reported `RUNNING` with `"tasks":[]` right after registration;
task 0 was `RUNNING` on the re-poll. Harmless, but a reader who stops at the
first check could conclude the connector has no task. Covered by Finding 1's
resolution (a scripted re-poll).

### Finding 3 — Demo orders point to a customer that a clean stack does not have

`cdc_demo_changes.py --insert` creates orders for `customer_id=9001`
(`_DEMO_CUSTOMER_ID`). The seed has customers 1001–1003 only; 9001 is created
in Phase 6, which this run skipped. On a clean stack, every demo order is
therefore an order without a customer. CDC does not care, but the warehouse
loader (M8W29T2) loads such orders with `customer_key = NULL` and reports them.

**Resolution.** Either seed customer 9001 in `cdc_replication_setup.sql`, or
point the demo script at 1001. Owner: Abdalla, M9 kickoff (affects M9's
dashboard demo data).

### Finding 4 — Not a second-person reproduction

Run by the runbook's author on the machine the M7 run used, after the task was
reassigned on 23 November. A step that depends on this machine (for example a
local `.env`, Git Bash on Windows, or Python packages installed on the host)
would not be caught. A run by another team member on another machine remains
worth doing; carried to M9 as an optional verification task for Mert.

### Finding 5 — Two clocks, not one

The consumer runs on Windows; the containers run inside Docker Desktop's
virtual machine. t0 comes from the Postgres container clock and t4 from the
Windows clock, so the latency figures span two clocks. The CDC Design Note
(Section 2.4) and kickoff notes Part B item 4a assume a single host with zero
skew. Not a fault in this run, where the 490 ms figure agrees with both logs,
but M8W29T4 measures the skew before each condition instead of assuming it.

## 8. Conclusion

From a clean environment, the M7 runbook's Phases 1–5 reproduce on `develop`
at `51b7142`: every prerequisite check passes; INSERT, UPDATE and DELETE reach
`warehouse.orders` with no scheduled run; a full replay of 9 messages changes
nothing; and the M8 latency instrumentation writes exactly one row per change,
untouched by redelivery. The runbook itself needs one fix (Finding 1) so that
a literal reading runs every step. The stack was left running for M8W29T4.
