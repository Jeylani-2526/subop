
# M8W28T10 — CDC Replication Slot Lifecycle Measurement

## 1. Task Overview

- **Owner:** Omer
- **Branch:** develop
- **Environment:** Local M7 stack (existing Docker volumes)
- **Original experiment date:** 19–20 November 2026
- **Review revision date:** 26 November 2026
- **Repeat experiment date:** 26 November 2026

### Objectives

- Measure retained WAL during connector pause and resume.
- Verify LSN advancement and CDC event completeness.
- Measure Kafka consumer topic discovery latency.
- Propose an improved metadata refresh configuration.
- Document commands, measurements, failures, and environment discrepancies.
- Improve experiment reproducibility by preserving execution commands and terminal outputs.

## 2. Test Environment

| Component | Value |
|---|---|
| PostgreSQL | 15 |
| Debezium | 3.6.3.Final |
| confluent-kafka | 2.16.2 |
| librdkafka | 2.16.0 |
| Connector | subop-postgres-cdc |
| Replication slot | subop_cdc_slot |
| Publication | subop_cdc_pub |
| Source table | cdc_demo.orders |
| Event log | cdc_meta.event_log |
| Kafka bootstrap server | localhost:9092 |
| Kafka Connect REST API | localhost:8083 |

The local PostgreSQL environment retained existing Docker volumes.

The environment discrepancy affecting the `cdc_demo.customers` table is documented in Finding 3.

## 3. Finding 1 — Replication Slot Lifecycle

### Measurement Script

Implemented:

`infrastructure/scripts/check_cdc_slot.sh`

The script reports:

- slot_name
- active
- restart_lsn
- confirmed_flush_lsn
- retained_wal_bytes
- retained_wal_mb

Retained WAL is calculated using:

```sql
pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn)
```

The script is read-only and does not modify database state or connector configuration.

Execution:

```bash
bash infrastructure/scripts/check_cdc_slot.sh
```

### Test Procedure

Start the CDC consumer:

```powershell
python -m services.cdc.kafka_consumer
```

Measure the initial event log count:

```powershell
docker compose exec -T postgres psql -U subop -d subop -c "SELECT COUNT(*) FROM cdc_meta.event_log;"
```

Pause the connector:

```powershell
curl.exe -sS -i -X PUT http://localhost:8083/connectors/subop-postgres-cdc/pause
```

Verify the connector status:

```powershell
curl.exe -sS http://localhost:8083/connectors/subop-postgres-cdc/status
```

Observed result: HTTP 202 Accepted.

The connector and its task entered the PAUSED state.

Generate three batches of source changes:

```powershell
python -m services.cdc.cdc_demo_changes --all --loop 10 --interval 0
python -m services.cdc.cdc_demo_changes --all --loop 20 --interval 0
python -m services.cdc.cdc_demo_changes --all --loop 30 --interval 0
```

The replication slot was measured after each batch using:

```bash
bash infrastructure/scripts/check_cdc_slot.sh
```

### Original Measurement Results

All timestamps are UTC (2026-11-20).

| Stage | Time | Changes | Retained WAL (bytes) |
|---|---|---:|---:|
| Paused baseline | 07:32:13 | 0 | 821480 |
| Batch 1 | 07:33:59 | 30 | 828032 |
| Batch 2 | 07:34:58 | 60 | 839952 |
| Batch 3 | 07:36:07 | 90 | 894960 |
| Resume — first measurement | 07:38:21 | — | 1359096 |
| Resume — second measurement | 07:39:43 | — | 1388120 |

During the pause:

- Total generated changes: 180.
- Retained WAL increase: 73480 bytes (+8.94%).
- restart_lsn remained at 0/1990D98.
- confirmed_flush_lsn remained at 0/19954E8.
- Event log count remained at 186.

Resume the connector:

```powershell
curl.exe -sS -i -X PUT http://localhost:8083/connectors/subop-postgres-cdc/resume
```

Verify the connector status:

```powershell
curl.exe -sS http://localhost:8083/connectors/subop-postgres-cdc/status
```

Observed result: HTTP 202 Accepted.

The connector and its task returned to the RUNNING state.

### Original LSN Verification

| Parameter | Before resume | After resume |
|---|---|---|
| restart_lsn | 0/1990D98 | 0/1995588 |
| confirmed_flush_lsn | 0/19954E8 | 0/1A6B4B0 |

Both LSN values advanced after resume.

The advancement was observed 125 seconds after the resume request.


#### WAL Retention and LSN Interpretation

After resuming the connector:

- `confirmed_flush_lsn` advanced by 876488 bytes (approximately 876 KB).
- `restart_lsn` advanced by only 18416 bytes (approximately 18 KB).

The relatively small advancement of `restart_lsn`, combined with continued WAL generation, explains why the measured retained WAL continued to increase despite progress in `confirmed_flush_lsn`.

PostgreSQL normally manages WAL in 16 MiB segments. WAL removal or recycling depends on checkpoints, replication slot requirements, and retention settings.

The approximately 1.4 MB of measured retained WAL does not necessarily indicate that a complete WAL segment can be removed or recycled.

No additional CHECKPOINT experiment was performed.

#### LSN Advancement vs. CDC Latency

The observed 125-second interval represents the time until replication slot progress was observed following the connector resume request.

It is related to replication position acknowledgement and Kafka Connect offset persistence, rather than a direct measurement of CDC event delivery latency.

Therefore, this interval must not be interpreted as an end-to-end CDC latency KPI. The same limitation applies to the LSN advancement observed in the repeat experiment.


### Original Event Completeness Verification

```powershell
docker compose exec -T postgres psql -U subop -d subop -c "SELECT COUNT(*) FROM cdc_meta.event_log;"
```

Recorded output:

```text
 count
-------
   366
(1 row)
```

Expected: 186 + 180 = 366 records.

Verify operation counts for test IDs 65–124:

```powershell
docker compose exec -T postgres psql -U subop -d subop -c "SELECT op, COUNT(*) FROM cdc_meta.event_log WHERE table_name = 'cdc_demo.orders' AND row_key::integer BETWEEN 65 AND 124 GROUP BY op ORDER BY op;"
```

Recorded output:

```text
   op   | count
--------+-------
 delete |    60
 insert |    60
 update |    60
(3 rows)
```

Verify missing or duplicate events:

```powershell
docker compose exec -T postgres psql -U subop -d subop -c "SELECT r.id, o.op, COUNT(e.id) AS actual_count FROM generate_series(65,124) AS r(id) CROSS JOIN (VALUES ('insert'), ('update'), ('delete')) AS o(op) LEFT JOIN cdc_meta.event_log e ON e.table_name = 'cdc_demo.orders' AND e.row_key = r.id::text AND e.op = o.op GROUP BY r.id, o.op HAVING COUNT(e.id) <> 1;"
```

Recorded output:

```text
 id | op | actual_count
----+----+--------------
(0 rows)
```

### Original Finding 1 Result

- WAL accumulated during the pause.
- LSN values advanced after resume.
- All 180 expected events reached the event log.
- Missing events: 0.
- Duplicate test events in the event log: 0.

Retained WAL did not decrease during the observed post-resume window.

Consumer writes to the same PostgreSQL environment may have contributed to additional WAL generation. This explanation was not independently verified.

Complete WAL reclamation was not demonstrated.

Finding 1 remains valid despite the environment discrepancy described in Finding 3 because the experiment used the `cdc_demo.orders` table exclusively.

### Execution Record Status

The original experiment was performed on 2026-11-20.

The PowerShell commands were recovered from command history on 2026-11-26.

The original measurement results are preserved in this report.

Complete verbatim terminal outputs for the original pause/resume requests, batch executions, and intermediate replication slot measurements were not fully recovered.

A separately dated repeat experiment was performed on 2026-11-26 to improve the execution record and independently verify the original findings.

### Repeat Experiment — 26 November 2026

The experiment was repeated in response to the task review feedback.

The existing database volumes were preserved.

No changes to the critical-path Kafka consumer implementation were made as part of this experiment.

#### Step 1 — Initial Connector Status

An initial attempt to execute curl in PowerShell failed because curl resolved to Invoke-WebRequest.

Command:

```powershell
curl -sS http://localhost:8083/connectors/subop-postgres-cdc/status
```

Recorded error:

```text
Invoke-WebRequest : A parameter cannot be found that matches parameter name 'sS'.
At line:1 char:6
+ curl -sS http://localhost:8083/connectors/subop-postgres-cdc/status
+      ~~~
    + CategoryInfo          : InvalidArgument: (:) [Invoke-WebRequest], ParameterBindingException
    + FullyQualifiedErrorId : NamedParameterNotFound,Microsoft.PowerShell.Commands.InvokeWebRequest 
   Command
```

The command was corrected by explicitly using curl.exe.

Command:

```powershell
curl.exe -sS http://localhost:8083/connectors/subop-postgres-cdc/status
```

Raw output:

```text
{"name":"subop-postgres-cdc","connector":{"state":"RUNNING","worker_id":"172.18.0.5:8083","version":"3.6.3.Final"},"tasks":[{"id":0,"state":"RUNNING","worker_id":"172.18.0.5:8083","version":"3.6.3.Final"}],"type":"source"}
```

Result:

- Connector state: RUNNING.
- Task 0 state: RUNNING.
- Debezium version: 3.6.3.Final.

The connector was operational before the pause/resume test.

#### Step 2 — Initial Replication Slot Measurement

Command:

```bash
bash infrastructure/scripts/check_cdc_slot.sh
```

Raw output:

```text
==============================================================
 SUBOP — CDC Replication Slot Measurement
 Task: M8W28T10
==============================================================

Timestamp (UTC): 2026-11-26T17:28:45Z
Database:        subop
PostgreSQL user: subop
Replication slot: subop_cdc_slot

--------------------------------------------------------------
 Replication Slot Status
--------------------------------------------------------------

   slot_name    | active | restart_lsn | confirmed_flush_lsn | retained_wal_bytes | retained_wal_mb
----------------+--------+-------------+---------------------+--------------------+-----------------
 subop_cdc_slot | t      | 0/1A5DF58   | 0/1A6B4B0           |             622808 |            0.59
(1 row)


--------------------------------------------------------------
 Measurement completed successfully
--------------------------------------------------------------
```

Result:

- Replication slot: subop_cdc_slot.
- Active: true.
- Initial restart_lsn: 0/1A5DF58.
- Initial confirmed_flush_lsn: 0/1A6B4B0.
- Initial retained WAL: 622808 bytes (0.59 MiB).
- Measurement completed successfully.

This measurement represents the initial replication slot state before pausing the Debezium connector.

#### Step 3 — Start CDC Consumer

The CDC consumer was started in a separate PowerShell terminal.

Command:

```powershell
python -m services.cdc.kafka_consumer
```

Recorded subscription log:

```text
2026-11-26 20:29:40,058 INFO subscribed to ^subop-postgres-cdc\.cdc_demo\..* as group subop-cdc-consumer
```

The timestamp above is preserved as displayed by the consumer.

The consumer subscribed to the CDC topic pattern and remained running throughout the experiment.

Successful subscription alone does not demonstrate CDC event delivery. Event delivery was verified separately through SQL queries in Step 13.

#### Step 4 — Initial Event Log Count

Command:

```powershell
docker compose exec -T postgres psql -U subop -d subop -c "SELECT COUNT(*) FROM cdc_meta.event_log;"
```

Raw output:

```text
 count 
-------
   366
(1 row)
```

Initial event log count: 366.

The planned experiment generates 180 additional source changes.

Expected final event log count:

```text
366 + 180 = 546
```

#### Step 5 — Pause Connector

Command:

```powershell
curl.exe -sS -i -X PUT http://localhost:8083/connectors/subop-postgres-cdc/pause
```

Raw output:

```text
HTTP/1.1 202 Accepted
Server: Jetty(12.0.34)
Date: Thu, 26 Nov 2026 17:32:47 GMT
Content-Length: 0
```

Verify connector status:

```powershell
curl.exe -sS http://localhost:8083/connectors/subop-postgres-cdc/status
```

Raw output:

```text
{"name":"subop-postgres-cdc","connector":{"state":"PAUSED","worker_id":"172.18.0.5:8083","version":"3.6.3.Final"},"tasks":[{"id":0,"state":"PAUSED","worker_id":"172.18.0.5:8083","version":"3.6.3.Final"}],"type":"source"}
```

Result:

- Pause request: HTTP 202 Accepted.
- Connector state: PAUSED.
- Task 0 state: PAUSED.

#### Step 6 — Paused Baseline Measurement

Command:

```bash
bash infrastructure/scripts/check_cdc_slot.sh
```

Recorded output:

```text
==============================================================
 SUBOP — CDC Replication Slot Measurement
 Task: M8W28T10
==============================================================

Timestamp (UTC): 2026-11-26T17:33:28Z
Database:        subop
PostgreSQL user: subop
Replication slot: subop_cdc_slot

--------------------------------------------------------------
 Replication Slot Status
--------------------------------------------------------------

   slot_name    | active | restart_lsn | confirmed_flush_lsn | retained_wal_bytes | retained_wal_mb
----------------+--------+-------------+---------------------+--------------------+-----------------
 subop_cdc_slot | t      | 0/1A5DF58   | 0/1A6B4B0           |             631264 |            0.60
(1 row)


--------------------------------------------------------------
 Measurement completed successfully
--------------------------------------------------------------
```

Paused baseline retained WAL: 631264 bytes.

Both LSN values remained unchanged compared with the initial measurement.

The replication slot remained active even though the connector and its task were paused.

The active flag alone does not establish that new CDC events are being processed.

This measurement was used as the baseline for calculating retained WAL accumulation during the pause.

#### Step 7 — Batch 1: 30 Source Changes

Command:

```powershell
python -m services.cdc.cdc_demo_changes --all --loop 10 --interval 0
```

Raw output:

```text
INSERT id=125 commit_ts=2026-11-26T17:34:00.579454+00:00 commit_ts_ms=1795714440579 customer_id=9001
UPDATE id=125 commit_ts=2026-11-26T17:34:00.594991+00:00 commit_ts_ms=1795714440594 status=shipped
DELETE id=125 commit_ts=2026-11-26T17:34:00.653121+00:00 commit_ts_ms=1795714440653
INSERT id=126 commit_ts=2026-11-26T17:34:00.657702+00:00 commit_ts_ms=1795714440657 customer_id=9001
UPDATE id=126 commit_ts=2026-11-26T17:34:00.663258+00:00 commit_ts_ms=1795714440663 status=shipped
DELETE id=126 commit_ts=2026-11-26T17:34:00.782069+00:00 commit_ts_ms=1795714440782
INSERT id=127 commit_ts=2026-11-26T17:34:00.941547+00:00 commit_ts_ms=1795714440941 customer_id=9001
UPDATE id=127 commit_ts=2026-11-26T17:34:00.954380+00:00 commit_ts_ms=1795714440954 status=shipped
DELETE id=127 commit_ts=2026-11-26T17:34:00.970577+00:00 commit_ts_ms=1795714440970
INSERT id=128 commit_ts=2026-11-26T17:34:00.986890+00:00 commit_ts_ms=1795714440986 customer_id=9001
UPDATE id=128 commit_ts=2026-11-26T17:34:00.991596+00:00 commit_ts_ms=1795714440991 status=shipped
DELETE id=128 commit_ts=2026-11-26T17:34:01.055389+00:00 commit_ts_ms=1795714441055
INSERT id=129 commit_ts=2026-11-26T17:34:01.117224+00:00 commit_ts_ms=1795714441117 customer_id=9001
UPDATE id=129 commit_ts=2026-11-26T17:34:01.123455+00:00 commit_ts_ms=1795714441123 status=shipped
DELETE id=129 commit_ts=2026-11-26T17:34:01.132712+00:00 commit_ts_ms=1795714441132
INSERT id=130 commit_ts=2026-11-26T17:34:01.145822+00:00 commit_ts_ms=1795714441145 customer_id=9001
UPDATE id=130 commit_ts=2026-11-26T17:34:01.151307+00:00 commit_ts_ms=1795714441151 status=shipped
DELETE id=130 commit_ts=2026-11-26T17:34:01.156407+00:00 commit_ts_ms=1795714441156
INSERT id=131 commit_ts=2026-11-26T17:34:01.162240+00:00 commit_ts_ms=1795714441162 customer_id=9001
UPDATE id=131 commit_ts=2026-11-26T17:34:01.172317+00:00 commit_ts_ms=1795714441172 status=shipped
DELETE id=131 commit_ts=2026-11-26T17:34:01.179982+00:00 commit_ts_ms=1795714441179
INSERT id=132 commit_ts=2026-11-26T17:34:01.183234+00:00 commit_ts_ms=1795714441183 customer_id=9001
UPDATE id=132 commit_ts=2026-11-26T17:34:01.187164+00:00 commit_ts_ms=1795714441187 status=shipped
DELETE id=132 commit_ts=2026-11-26T17:34:01.204565+00:00 commit_ts_ms=1795714441204
INSERT id=133 commit_ts=2026-11-26T17:34:01.210988+00:00 commit_ts_ms=1795714441210 customer_id=9001
UPDATE id=133 commit_ts=2026-11-26T17:34:01.214779+00:00 commit_ts_ms=1795714441214 status=shipped
DELETE id=133 commit_ts=2026-11-26T17:34:01.231454+00:00 commit_ts_ms=1795714441231
INSERT id=134 commit_ts=2026-11-26T17:34:01.285166+00:00 commit_ts_ms=1795714441285 customer_id=9001
UPDATE id=134 commit_ts=2026-11-26T17:34:01.291374+00:00 commit_ts_ms=1795714441291 status=shipped
DELETE id=134 commit_ts=2026-11-26T17:34:01.345226+00:00 commit_ts_ms=1795714441345
loop finished after 10 round(s)
```

Generated source changes:

- INSERT: 10.
- UPDATE: 10.
- DELETE: 10.
- Total: 30.
- ID range: 125–134.

Replication slot measurement:

```bash
bash infrastructure/scripts/check_cdc_slot.sh
```

Recorded output:

```text
==============================================================
 SUBOP — CDC Replication Slot Measurement
 Task: M8W28T10
==============================================================

Timestamp (UTC): 2026-11-26T17:34:12Z
Database:        subop
PostgreSQL user: subop
Replication slot: subop_cdc_slot

--------------------------------------------------------------
 Replication Slot Status
--------------------------------------------------------------

   slot_name    | active | restart_lsn | confirmed_flush_lsn | retained_wal_bytes | retained_wal_mb
----------------+--------+-------------+---------------------+--------------------+-----------------
 subop_cdc_slot | t      | 0/1A5DF58   | 0/1A6B4B0           |             637792 |            0.61
(1 row)


--------------------------------------------------------------
 Measurement completed successfully
--------------------------------------------------------------
```

Retained WAL increased by 6528 bytes compared with the paused baseline.

Both LSN values remained unchanged.

#### Step 8 — Batch 2: 60 Source Changes

Command:

```powershell
python -m services.cdc.cdc_demo_changes --all --loop 20 --interval 0
```

Recorded execution results:

- Completed rounds: 20.
- INSERT: 20.
- UPDATE: 20.
- DELETE: 20.
- Total: 60.
- ID range: 135–154.
- Cumulative source changes: 90.

Verified excerpts from the execution output:

```text
INSERT id=135 commit_ts=2026-11-26T17:37:02.740242+00:00
DELETE id=154 commit_ts=2026-11-26T17:37:03.026149+00:00 commit_ts_ms=1795714623026
loop finished after 20 round(s)
```

These are recorded excerpts from the pause/resume experiment. Complete terminal transcripts from separately executed supplementary batches are provided in the Supplementary Batch Execution Records section.

Replication slot measurement:

```bash
bash infrastructure/scripts/check_cdc_slot.sh
```

Recorded output:

```text
==============================================================
 SUBOP — CDC Replication Slot Measurement
 Task: M8W28T10
==============================================================

Timestamp (UTC): 2026-11-26T17:37:19Z
Database:        subop
PostgreSQL user: subop
Replication slot: subop_cdc_slot

--------------------------------------------------------------
 Replication Slot Status
--------------------------------------------------------------

   slot_name    | active | restart_lsn | confirmed_flush_lsn | retained_wal_bytes | retained_wal_mb
----------------+--------+-------------+---------------------+--------------------+-----------------
 subop_cdc_slot | t      | 0/1A5DF58   | 0/1A6B4B0           |             652296 |            0.62
(1 row)


--------------------------------------------------------------
 Measurement completed successfully
--------------------------------------------------------------
```

Retained WAL increased by 14504 bytes compared with the previous measurement.

Both LSN values remained unchanged.

#### Step 9 — Batch 3: 90 Source Changes

Command:

```powershell
python -m services.cdc.cdc_demo_changes --all --loop 30 --interval 0
```

Recorded execution results:

- Completed rounds: 30.
- INSERT: 30.
- UPDATE: 30.
- DELETE: 30.
- Total: 90.
- ID range: 155–184.
- Cumulative source changes: 180.

Verified excerpts from the execution output:

```text
INSERT id=155 commit_ts=2026-11-26T17:37:53.079822+00:00 commit_ts_ms=1795714673079 customer_id=9001
DELETE id=184 commit_ts=2026-11-26T17:37:53.561976+00:00 commit_ts_ms=1795714673561
loop finished after 30 round(s)
```

These are recorded excerpts from the pause/resume experiment. Complete terminal transcripts from separately executed supplementary batches are provided in the Supplementary Batch Execution Records section.

Replication slot measurement:

```bash
bash infrastructure/scripts/check_cdc_slot.sh
```

Recorded output:

```text
==============================================================
 SUBOP — CDC Replication Slot Measurement
 Task: M8W28T10
==============================================================

Timestamp (UTC): 2026-11-26T17:38:11Z
Database:        subop
PostgreSQL user: subop
Replication slot: subop_cdc_slot

--------------------------------------------------------------
 Replication Slot Status
--------------------------------------------------------------

   slot_name    | active | restart_lsn | confirmed_flush_lsn | retained_wal_bytes | retained_wal_mb
----------------+--------+-------------+---------------------+--------------------+-----------------
 subop_cdc_slot | t      | 0/1A5DF58   | 0/1A6B4B0           |             720136 |            0.69
(1 row)


--------------------------------------------------------------
 Measurement completed successfully
--------------------------------------------------------------
```

Retained WAL increased by 67840 bytes compared with the previous measurement.

Both LSN values remained unchanged.

Total generated source changes during the pause:

| Operation | Count |
|---|---:|
| INSERT | 60 |
| UPDATE | 60 |
| DELETE | 60 |
| Total | 180 |

The complete test ID range was 125–184.

#### Step 10 — Event Log Verification During Pause

Command:

```powershell
docker compose exec -T postgres psql -U subop -d subop -c "SELECT COUNT(*) FROM cdc_meta.event_log;"
```

Raw output:

```text
 count 
-------
   366
(1 row)
```

The event log count remained at 366 after all 180 source changes had been generated.

This confirms that there was no net increase in the event log count during the paused observation window.

#### Step 11 — Resume Connector

Command:

```powershell
curl.exe -sS -i -X PUT http://localhost:8083/connectors/subop-postgres-cdc/resume
```

Raw output:

```text
HTTP/1.1 202 Accepted
Server: Jetty(12.0.34)
Date: Thu, 26 Nov 2026 17:39:01 GMT
Content-Length: 0
```

Verify connector status:

```powershell
curl.exe -sS http://localhost:8083/connectors/subop-postgres-cdc/status
```

Raw output:

```text
{"name":"subop-postgres-cdc","connector":{"state":"RUNNING","worker_id":"172.18.0.5:8083","version":"3.6.3.Final"},"tasks":[{"id":0,"state":"RUNNING","worker_id":"172.18.0.5:8083","version":"3.6.3.Final"}],"type":"source"}
```

Result:

- Resume request: HTTP 202 Accepted.
- Connector state: RUNNING.
- Task 0 state: RUNNING.

#### Step 12 — First Post-Resume Slot Measurement

Command:

```bash
bash infrastructure/scripts/check_cdc_slot.sh
```

Raw output:

```text
==============================================================
 SUBOP — CDC Replication Slot Measurement
 Task: M8W28T10
==============================================================

Timestamp (UTC): 2026-11-26T17:39:21Z
Database:        subop
PostgreSQL user: subop
Replication slot: subop_cdc_slot

--------------------------------------------------------------
 Replication Slot Status
--------------------------------------------------------------

   slot_name    | active | restart_lsn | confirmed_flush_lsn | retained_wal_bytes | retained_wal_mb 
----------------+--------+-------------+---------------------+--------------------+-----------------
 subop_cdc_slot | t      | 0/1A6B550   | 0/1B0DBC0           |            1053776 |            1.00
(1 row)


--------------------------------------------------------------
 Measurement completed successfully
--------------------------------------------------------------
```

LSN comparison:

| Parameter | Before resume | After resume |
|---|---|---|
| restart_lsn | 0/1A5DF58 | 0/1A6B550 |
| confirmed_flush_lsn | 0/1A6B4B0 | 0/1B0DBC0 |

Both LSN values advanced after resume.

The advancement was observed in the measurement performed 20 seconds after the resume request.

Retained WAL increased to 1053776 bytes.

The measurement demonstrates replication slot progress but does not demonstrate complete WAL reclamation.

#### Step 13 — Event Completeness Verification

##### Total Event Count

Command:

```powershell
docker compose exec -T postgres psql -U subop -d subop -c "SELECT COUNT(*) FROM cdc_meta.event_log;"
```

Raw output:

```text
 count 
-------
   546
(1 row)
```

Expected event log count:

```text
366 + 180 = 546
```

Actual event log count: 546.

Result: PASS.

##### Operation Count Verification

Command:

```powershell
docker compose exec -T postgres psql -U subop -d subop -c "SELECT op, COUNT(*) FROM cdc_meta.event_log WHERE table_name = 'cdc_demo.orders' AND row_key::integer BETWEEN 125 AND 184 GROUP BY op ORDER BY op;"
```

Raw output:

```text
   op   | count 
--------+-------
 delete |    60
 insert |    60
 update |    60
(3 rows)
```

| Operation | Expected | Actual |
|---|---:|---:|
| INSERT | 60 | 60 |
| UPDATE | 60 | 60 |
| DELETE | 60 | 60 |
| Total | 180 | 180 |

Result: PASS.

##### Missing and Duplicate Event Verification

Command:

```powershell
docker compose exec -T postgres psql -U subop -d subop -c "SELECT r.id, o.op, COUNT(e.id) AS actual_count FROM generate_series(125,184) AS r(id) CROSS JOIN (VALUES ('insert'), ('update'), ('delete')) AS o(op) LEFT JOIN cdc_meta.event_log e ON e.table_name = 'cdc_demo.orders' AND e.row_key = r.id::text AND e.op = o.op GROUP BY r.id, o.op HAVING COUNT(e.id) <> 1;"
```

Raw output:

```text
 id | op | actual_count 
----+----+--------------
(0 rows)
```

The query checks each expected combination of test row ID and operation type.

Returning zero rows means that each expected combination appeared exactly once in the event log.

Results:

- Expected events: 180.
- Observed events: 180.
- Event completeness: 100%.
- Missing events: 0.
- Duplicate test event log records: 0.

Result: PASS.

The result applies to the observed event log records and does not establish a general exactly-once Kafka delivery guarantee.

#### Step 14 — Final Post-Resume Slot Measurement

Command:

```bash
bash infrastructure/scripts/check_cdc_slot.sh
```

Raw output:

```text
==============================================================
 SUBOP — CDC Replication Slot Measurement
 Task: M8W28T10
==============================================================

Timestamp (UTC): 2026-11-26T17:40:25Z
Database:        subop
PostgreSQL user: subop
Replication slot: subop_cdc_slot

--------------------------------------------------------------
 Replication Slot Status
--------------------------------------------------------------

   slot_name    | active | restart_lsn | confirmed_flush_lsn | retained_wal_bytes | retained_wal_mb 
----------------+--------+-------------+---------------------+--------------------+-----------------
 subop_cdc_slot | t      | 0/1A6B550   | 0/1B0DBC0           |            1166512 |            1.11
(1 row)


--------------------------------------------------------------
 Measurement completed successfully
--------------------------------------------------------------
```

The final measurement was performed 84 seconds after the resume request.

Both LSN values remained unchanged compared with the first post-resume measurement.

Retained WAL increased by a further 112736 bytes.

Complete WAL reclamation was not observed.

### Repeat Experiment — Consolidated Measurement Results

All timestamps are UTC (2026-11-26).

| Stage | Time | Changes | Retained WAL (bytes) | Retained WAL (MiB) |
|---|---|---:|---:|---:|
| Initial measurement | 17:28:45 | 0 | 622808 | 0.59 |
| Paused baseline | 17:33:28 | 0 | 631264 | 0.60 |
| Batch 1 | 17:34:12 | 30 | 637792 | 0.61 |
| Batch 2 | 17:37:19 | 60 | 652296 | 0.62 |
| Batch 3 | 17:38:11 | 90 | 720136 | 0.69 |
| Resume — first measurement | 17:39:21 | — | 1053776 | 1.00 |
| Resume — second measurement | 17:40:25 | — | 1166512 | 1.11 |

### WAL Accumulation Analysis

| Measurement interval | Retained WAL increase (bytes) |
|---|---:|
| Initial measurement to paused baseline | 8456 |
| Paused baseline to Batch 1 | 6528 |
| Batch 1 to Batch 2 | 14504 |
| Batch 2 to Batch 3 | 67840 |
| Total increase during paused batch executions | 88872 |
| Final paused measurement to first post-resume measurement | 333640 |
| First to second post-resume measurement | 112736 |

Percentage increase during pause:

```text
(720136 - 631264) / 631264 * 100
= approximately 14.08%
```

Retained WAL increased by 88872 bytes during the paused batch execution window.

The measured increases reflect PostgreSQL WAL generation and retention between observations. They are not necessarily attributable exclusively to the generated test operations.

### LSN Lifecycle Summary

| Stage | restart_lsn | confirmed_flush_lsn |
|---|---|---|
| Initial | 0/1A5DF58 | 0/1A6B4B0 |
| Paused baseline | 0/1A5DF58 | 0/1A6B4B0 |
| Batch 1 | 0/1A5DF58 | 0/1A6B4B0 |
| Batch 2 | 0/1A5DF58 | 0/1A6B4B0 |
| Batch 3 | 0/1A5DF58 | 0/1A6B4B0 |
| Resume — first measurement | 0/1A6B550 | 0/1B0DBC0 |
| Resume — second measurement | 0/1A6B550 | 0/1B0DBC0 |

Both LSN values remained unchanged throughout the pause and advanced after resume.

### Event Completeness Summary

| Parameter | Result |
|---|---:|
| Initial event log count | 366 |
| Event log count during pause | 366 |
| Generated source changes | 180 |
| Expected final event log count | 546 |
| Actual final event log count | 546 |
| INSERT events | 60 |
| UPDATE events | 60 |
| DELETE events | 60 |
| Missing events | 0 |
| Duplicate test event log records | 0 |
| Event completeness | 100% |

### Comparison of Original and Repeat Experiments

| Metric | 20 November | 26 November |
|---|---:|---:|
| Generated source changes | 180 | 180 |
| Initial event log count | 186 | 366 |
| Final event log count | 366 | 546 |
| Paused retained WAL increase | 73480 bytes | 88872 bytes |
| Relative retained WAL increase | 8.94% | 14.08% |
| restart_lsn advancement | Yes | Yes |
| confirmed_flush_lsn advancement | Yes | Yes |
| Expected events received | 180/180 | 180/180 |
| Missing events | 0 | 0 |
| Duplicate test event log records | 0 | 0 |
| Complete WAL reclamation demonstrated | No | No |

Across the two experiments, 360 test events were generated and verified in the event log.

The initial conditions and database activity differed between the experiments. Therefore, differences in retained WAL magnitude should not be interpreted as a controlled performance comparison.

### Repeat Experiment Acceptance Results

| Acceptance criterion | Result |
|---|---|
| Initial connector status | PASS |
| Replication slot measurement | PASS |
| Connector pause | PASS |
| WAL accumulation during pause | PASS |
| Stable LSN values during pause | PASS |
| Unchanged event log count during pause | PASS |
| Connector resume | PASS |
| restart_lsn advancement | PASS |
| confirmed_flush_lsn advancement | PASS |
| Event completeness | PASS — 180/180 |
| Missing events | 0 |
| Duplicate test event log records | 0 |
| Complete WAL reclamation | Not demonstrated |

### Final Finding 1 Conclusion

The repeat experiment performed on 26 November 2026 confirmed the principal findings of the original 20 November experiment.

Retained WAL increased while the Debezium connector was paused.

The event log count remained unchanged during the pause.

After resuming the connector, both LSN values advanced and all 180 expected CDC events reached the event log.

No missing or duplicate test event log records were identified for IDs 125–184.

Retained WAL continued to increase during the observed post-resume measurement window.

Consumer writes to the same PostgreSQL instance may have contributed to additional WAL generation, but this explanation was not independently verified.

Complete WAL reclamation was not demonstrated.

The experiment was restricted to `cdc_demo.orders` because the local `cdc_demo.customers` table was missing, as documented in Finding 3.

The original and repeat experiments are documented separately.

The technical verification of Finding 1 is complete. Supplementary batch execution transcripts are included, while historical execution record limitations are documented in Section 9.


### Supplementary Batch Execution Records — 26 November 2026

The 20-round and 30-round source change generation commands were executed again to capture complete terminal transcripts.

These supplementary executions are separate from the earlier connector pause/resume experiment and must not be interpreted as its original terminal outputs.

#### Execution Results

| Batch | Rounds | INSERT | UPDATE | DELETE | Total | ID range |
|---|---:|---:|---:|---:|---:|---|
| Batch 2 | 20 | 20 | 20 | 20 | 60 | 185–204 |
| Batch 3 | 30 | 30 | 30 | 30 | 90 | 205–234 |
| Total | 50 | 50 | 50 | 50 | 150 | 185–234 |

Both commands completed successfully.

#### Complete Raw Terminal Output
```
python -m services.cdc.cdc_demo_changes --all --loop 20 --interval 0
INSERT id=185 commit_ts=2026-11-26T18:06:59.872291+00:00 commit_ts_ms=1795716419872 customer_id=9001
UPDATE id=185 commit_ts=2026-11-26T18:06:59.877895+00:00 commit_ts_ms=1795716419877 status=shipped
DELETE id=185 commit_ts=2026-11-26T18:06:59.884392+00:00 commit_ts_ms=1795716419884
INSERT id=186 commit_ts=2026-11-26T18:06:59.888720+00:00 commit_ts_ms=1795716419888 customer_id=9001
UPDATE id=186 commit_ts=2026-11-26T18:06:59.894362+00:00 commit_ts_ms=1795716419894 status=shipped
DELETE id=186 commit_ts=2026-11-26T18:06:59.899839+00:00 commit_ts_ms=1795716419899
INSERT id=187 commit_ts=2026-11-26T18:06:59.904337+00:00 commit_ts_ms=1795716419904 customer_id=9001
UPDATE id=187 commit_ts=2026-11-26T18:06:59.910414+00:00 commit_ts_ms=1795716419910 status=shipped
DELETE id=187 commit_ts=2026-11-26T18:06:59.916334+00:00 commit_ts_ms=1795716419916
INSERT id=188 commit_ts=2026-11-26T18:06:59.920176+00:00 commit_ts_ms=1795716419920 customer_id=9001
UPDATE id=188 commit_ts=2026-11-26T18:06:59.926693+00:00 commit_ts_ms=1795716419926 status=shipped
DELETE id=188 commit_ts=2026-11-26T18:06:59.932773+00:00 commit_ts_ms=1795716419932
INSERT id=189 commit_ts=2026-11-26T18:06:59.937099+00:00 commit_ts_ms=1795716419937 customer_id=9001
UPDATE id=189 commit_ts=2026-11-26T18:06:59.945209+00:00 commit_ts_ms=1795716419945 status=shipped
DELETE id=189 commit_ts=2026-11-26T18:06:59.952927+00:00 commit_ts_ms=1795716419952
INSERT id=190 commit_ts=2026-11-26T18:06:59.959914+00:00 commit_ts_ms=1795716419959 customer_id=9001
UPDATE id=190 commit_ts=2026-11-26T18:06:59.966343+00:00 commit_ts_ms=1795716419966 status=shipped
DELETE id=190 commit_ts=2026-11-26T18:06:59.975055+00:00 commit_ts_ms=1795716419975
INSERT id=191 commit_ts=2026-11-26T18:06:59.980440+00:00 commit_ts_ms=1795716419980 customer_id=9001
UPDATE id=191 commit_ts=2026-11-26T18:06:59.988775+00:00 commit_ts_ms=1795716419988 status=shipped
DELETE id=191 commit_ts=2026-11-26T18:06:59.995424+00:00 commit_ts_ms=1795716419995
INSERT id=192 commit_ts=2026-11-26T18:07:00.000134+00:00 commit_ts_ms=1795716420000 customer_id=9001
UPDATE id=192 commit_ts=2026-11-26T18:07:00.011468+00:00 commit_ts_ms=1795716420011 status=shipped
DELETE id=192 commit_ts=2026-11-26T18:07:00.023199+00:00 commit_ts_ms=1795716420023
INSERT id=193 commit_ts=2026-11-26T18:07:00.027920+00:00 commit_ts_ms=1795716420027 customer_id=9001
UPDATE id=193 commit_ts=2026-11-26T18:07:00.033175+00:00 commit_ts_ms=1795716420033 status=shipped
DELETE id=193 commit_ts=2026-11-26T18:07:00.040183+00:00 commit_ts_ms=1795716420040
INSERT id=194 commit_ts=2026-11-26T18:07:00.044032+00:00 commit_ts_ms=1795716420044 customer_id=9001
UPDATE id=194 commit_ts=2026-11-26T18:07:00.051081+00:00 commit_ts_ms=1795716420051 status=shipped
DELETE id=194 commit_ts=2026-11-26T18:07:00.058635+00:00 commit_ts_ms=1795716420058
INSERT id=195 commit_ts=2026-11-26T18:07:00.063411+00:00 commit_ts_ms=1795716420063 customer_id=9001
UPDATE id=195 commit_ts=2026-11-26T18:07:00.071636+00:00 commit_ts_ms=1795716420071 status=shipped
DELETE id=195 commit_ts=2026-11-26T18:07:00.080148+00:00 commit_ts_ms=1795716420080
INSERT id=196 commit_ts=2026-11-26T18:07:00.085711+00:00 commit_ts_ms=1795716420085 customer_id=9001
UPDATE id=196 commit_ts=2026-11-26T18:07:00.089412+00:00 commit_ts_ms=1795716420089 status=shipped
DELETE id=196 commit_ts=2026-11-26T18:07:00.094374+00:00 commit_ts_ms=1795716420094
INSERT id=197 commit_ts=2026-11-26T18:07:00.098830+00:00 commit_ts_ms=1795716420098 customer_id=9001
UPDATE id=197 commit_ts=2026-11-26T18:07:00.104040+00:00 commit_ts_ms=1795716420104 status=shipped
DELETE id=197 commit_ts=2026-11-26T18:07:00.108326+00:00 commit_ts_ms=1795716420108
INSERT id=198 commit_ts=2026-11-26T18:07:00.111641+00:00 commit_ts_ms=1795716420111 customer_id=9001
UPDATE id=198 commit_ts=2026-11-26T18:07:00.116341+00:00 commit_ts_ms=1795716420116 status=shipped
DELETE id=198 commit_ts=2026-11-26T18:07:00.121738+00:00 commit_ts_ms=1795716420121
INSERT id=199 commit_ts=2026-11-26T18:07:00.124631+00:00 commit_ts_ms=1795716420124 customer_id=9001
UPDATE id=199 commit_ts=2026-11-26T18:07:00.128953+00:00 commit_ts_ms=1795716420128 status=shipped
DELETE id=199 commit_ts=2026-11-26T18:07:00.136263+00:00 commit_ts_ms=1795716420136
INSERT id=200 commit_ts=2026-11-26T18:07:00.139699+00:00 commit_ts_ms=1795716420139 customer_id=9001
UPDATE id=200 commit_ts=2026-11-26T18:07:00.143707+00:00 commit_ts_ms=1795716420143 status=shipped
DELETE id=200 commit_ts=2026-11-26T18:07:00.149008+00:00 commit_ts_ms=1795716420149
INSERT id=201 commit_ts=2026-11-26T18:07:00.153244+00:00 commit_ts_ms=1795716420153 customer_id=9001
UPDATE id=201 commit_ts=2026-11-26T18:07:00.156945+00:00 commit_ts_ms=1795716420156 status=shipped
DELETE id=201 commit_ts=2026-11-26T18:07:00.161484+00:00 commit_ts_ms=1795716420161
INSERT id=202 commit_ts=2026-11-26T18:07:00.164837+00:00 commit_ts_ms=1795716420164 customer_id=9001
UPDATE id=202 commit_ts=2026-11-26T18:07:00.170516+00:00 commit_ts_ms=1795716420170 status=shipped
DELETE id=202 commit_ts=2026-11-26T18:07:00.175521+00:00 commit_ts_ms=1795716420175
INSERT id=203 commit_ts=2026-11-26T18:07:00.178447+00:00 commit_ts_ms=1795716420178 customer_id=9001
UPDATE id=203 commit_ts=2026-11-26T18:07:00.183065+00:00 commit_ts_ms=1795716420183 status=shipped
DELETE id=203 commit_ts=2026-11-26T18:07:00.189027+00:00 commit_ts_ms=1795716420189
INSERT id=204 commit_ts=2026-11-26T18:07:00.192456+00:00 commit_ts_ms=1795716420192 customer_id=9001
UPDATE id=204 commit_ts=2026-11-26T18:07:00.196033+00:00 commit_ts_ms=1795716420196 status=shipped
DELETE id=204 commit_ts=2026-11-26T18:07:00.204320+00:00 commit_ts_ms=1795716420204
loop finished after 20 round(s)
PS C:\Users\asus\subop> python -m services.cdc.cdc_demo_changes --all --loop 30 --interval 0
INSERT id=205 commit_ts=2026-11-26T18:07:04.278806+00:00 commit_ts_ms=1795716424278 customer_id=9001
UPDATE id=205 commit_ts=2026-11-26T18:07:04.286771+00:00 commit_ts_ms=1795716424286 status=shipped
DELETE id=205 commit_ts=2026-11-26T18:07:04.293678+00:00 commit_ts_ms=1795716424293
INSERT id=206 commit_ts=2026-11-26T18:07:04.298925+00:00 commit_ts_ms=1795716424298 customer_id=9001
UPDATE id=206 commit_ts=2026-11-26T18:07:04.304266+00:00 commit_ts_ms=1795716424304 status=shipped
DELETE id=206 commit_ts=2026-11-26T18:07:04.312899+00:00 commit_ts_ms=1795716424312
INSERT id=207 commit_ts=2026-11-26T18:07:04.317626+00:00 commit_ts_ms=1795716424317 customer_id=9001
UPDATE id=207 commit_ts=2026-11-26T18:07:04.326192+00:00 commit_ts_ms=1795716424326 status=shipped
DELETE id=207 commit_ts=2026-11-26T18:07:04.333131+00:00 commit_ts_ms=1795716424333
INSERT id=208 commit_ts=2026-11-26T18:07:04.337526+00:00 commit_ts_ms=1795716424337 customer_id=9001
UPDATE id=208 commit_ts=2026-11-26T18:07:04.343729+00:00 commit_ts_ms=1795716424343 status=shipped
DELETE id=208 commit_ts=2026-11-26T18:07:04.349121+00:00 commit_ts_ms=1795716424349
INSERT id=209 commit_ts=2026-11-26T18:07:04.352813+00:00 commit_ts_ms=1795716424352 customer_id=9001
UPDATE id=209 commit_ts=2026-11-26T18:07:04.358364+00:00 commit_ts_ms=1795716424358 status=shipped
DELETE id=209 commit_ts=2026-11-26T18:07:04.362782+00:00 commit_ts_ms=1795716424362
INSERT id=210 commit_ts=2026-11-26T18:07:04.366528+00:00 commit_ts_ms=1795716424366 customer_id=9001
UPDATE id=210 commit_ts=2026-11-26T18:07:04.371387+00:00 commit_ts_ms=1795716424371 status=shipped
DELETE id=210 commit_ts=2026-11-26T18:07:04.375981+00:00 commit_ts_ms=1795716424375
INSERT id=211 commit_ts=2026-11-26T18:07:04.379038+00:00 commit_ts_ms=1795716424379 customer_id=9001
UPDATE id=211 commit_ts=2026-11-26T18:07:04.383944+00:00 commit_ts_ms=1795716424383 status=shipped
DELETE id=211 commit_ts=2026-11-26T18:07:04.390086+00:00 commit_ts_ms=1795716424390
INSERT id=212 commit_ts=2026-11-26T18:07:04.393049+00:00 commit_ts_ms=1795716424393 customer_id=9001
UPDATE id=212 commit_ts=2026-11-26T18:07:04.396839+00:00 commit_ts_ms=1795716424396 status=shipped
DELETE id=212 commit_ts=2026-11-26T18:07:04.403536+00:00 commit_ts_ms=1795716424403
INSERT id=213 commit_ts=2026-11-26T18:07:04.406790+00:00 commit_ts_ms=1795716424406 customer_id=9001
UPDATE id=213 commit_ts=2026-11-26T18:07:04.410459+00:00 commit_ts_ms=1795716424410 status=shipped
DELETE id=213 commit_ts=2026-11-26T18:07:04.415824+00:00 commit_ts_ms=1795716424415
INSERT id=214 commit_ts=2026-11-26T18:07:04.420806+00:00 commit_ts_ms=1795716424420 customer_id=9001
UPDATE id=214 commit_ts=2026-11-26T18:07:04.424468+00:00 commit_ts_ms=1795716424424 status=shipped
DELETE id=214 commit_ts=2026-11-26T18:07:04.428641+00:00 commit_ts_ms=1795716424428
INSERT id=215 commit_ts=2026-11-26T18:07:04.433449+00:00 commit_ts_ms=1795716424433 customer_id=9001
UPDATE id=215 commit_ts=2026-11-26T18:07:04.438703+00:00 commit_ts_ms=1795716424438 status=shipped
DELETE id=215 commit_ts=2026-11-26T18:07:04.443768+00:00 commit_ts_ms=1795716424443
INSERT id=216 commit_ts=2026-11-26T18:07:04.447656+00:00 commit_ts_ms=1795716424447 customer_id=9001
UPDATE id=216 commit_ts=2026-11-26T18:07:04.452949+00:00 commit_ts_ms=1795716424452 status=shipped
DELETE id=216 commit_ts=2026-11-26T18:07:04.457657+00:00 commit_ts_ms=1795716424457
INSERT id=217 commit_ts=2026-11-26T18:07:04.460419+00:00 commit_ts_ms=1795716424460 customer_id=9001
UPDATE id=217 commit_ts=2026-11-26T18:07:04.463983+00:00 commit_ts_ms=1795716424463 status=shipped
DELETE id=217 commit_ts=2026-11-26T18:07:04.470392+00:00 commit_ts_ms=1795716424470
INSERT id=218 commit_ts=2026-11-26T18:07:04.473342+00:00 commit_ts_ms=1795716424473 customer_id=9001
UPDATE id=218 commit_ts=2026-11-26T18:07:04.478691+00:00 commit_ts_ms=1795716424478 status=shipped
DELETE id=218 commit_ts=2026-11-26T18:07:04.487171+00:00 commit_ts_ms=1795716424487
INSERT id=219 commit_ts=2026-11-26T18:07:04.491081+00:00 commit_ts_ms=1795716424491 customer_id=9001
UPDATE id=219 commit_ts=2026-11-26T18:07:04.494855+00:00 commit_ts_ms=1795716424494 status=shipped
DELETE id=219 commit_ts=2026-11-26T18:07:04.500331+00:00 commit_ts_ms=1795716424500
INSERT id=220 commit_ts=2026-11-26T18:07:04.504554+00:00 commit_ts_ms=1795716424504 customer_id=9001
UPDATE id=220 commit_ts=2026-11-26T18:07:04.508716+00:00 commit_ts_ms=1795716424508 status=shipped
DELETE id=220 commit_ts=2026-11-26T18:07:04.514443+00:00 commit_ts_ms=1795716424514
INSERT id=221 commit_ts=2026-11-26T18:07:04.519766+00:00 commit_ts_ms=1795716424519 customer_id=9001
UPDATE id=221 commit_ts=2026-11-26T18:07:04.523531+00:00 commit_ts_ms=1795716424523 status=shipped
DELETE id=221 commit_ts=2026-11-26T18:07:04.528037+00:00 commit_ts_ms=1795716424528
INSERT id=222 commit_ts=2026-11-26T18:07:04.531609+00:00 commit_ts_ms=1795716424531 customer_id=9001
UPDATE id=222 commit_ts=2026-11-26T18:07:04.538089+00:00 commit_ts_ms=1795716424538 status=shipped
DELETE id=222 commit_ts=2026-11-26T18:07:04.543120+00:00 commit_ts_ms=1795716424543
INSERT id=223 commit_ts=2026-11-26T18:07:04.546768+00:00 commit_ts_ms=1795716424546 customer_id=9001
UPDATE id=223 commit_ts=2026-11-26T18:07:04.554035+00:00 commit_ts_ms=1795716424554 status=shipped
DELETE id=223 commit_ts=2026-11-26T18:07:04.558465+00:00 commit_ts_ms=1795716424558
INSERT id=224 commit_ts=2026-11-26T18:07:04.561939+00:00 commit_ts_ms=1795716424561 customer_id=9001
UPDATE id=224 commit_ts=2026-11-26T18:07:04.566012+00:00 commit_ts_ms=1795716424566 status=shipped
DELETE id=224 commit_ts=2026-11-26T18:07:04.571956+00:00 commit_ts_ms=1795716424571
INSERT id=225 commit_ts=2026-11-26T18:07:04.575019+00:00 commit_ts_ms=1795716424575 customer_id=9001
UPDATE id=225 commit_ts=2026-11-26T18:07:04.579112+00:00 commit_ts_ms=1795716424579 status=shipped
DELETE id=225 commit_ts=2026-11-26T18:07:04.585720+00:00 commit_ts_ms=1795716424585
INSERT id=226 commit_ts=2026-11-26T18:07:04.589110+00:00 commit_ts_ms=1795716424589 customer_id=9001
UPDATE id=226 commit_ts=2026-11-26T18:07:04.592719+00:00 commit_ts_ms=1795716424592 status=shipped
DELETE id=226 commit_ts=2026-11-26T18:07:04.598637+00:00 commit_ts_ms=1795716424598
INSERT id=227 commit_ts=2026-11-26T18:07:04.603891+00:00 commit_ts_ms=1795716424603 customer_id=9001
UPDATE id=227 commit_ts=2026-11-26T18:07:04.609203+00:00 commit_ts_ms=1795716424609 status=shipped
DELETE id=227 commit_ts=2026-11-26T18:07:04.617019+00:00 commit_ts_ms=1795716424617
INSERT id=228 commit_ts=2026-11-26T18:07:04.622436+00:00 commit_ts_ms=1795716424622 customer_id=9001
UPDATE id=228 commit_ts=2026-11-26T18:07:04.626688+00:00 commit_ts_ms=1795716424626 status=shipped
DELETE id=228 commit_ts=2026-11-26T18:07:04.633060+00:00 commit_ts_ms=1795716424633
INSERT id=229 commit_ts=2026-11-26T18:07:04.638841+00:00 commit_ts_ms=1795716424638 customer_id=9001
UPDATE id=229 commit_ts=2026-11-26T18:07:04.644261+00:00 commit_ts_ms=1795716424644 status=shipped
DELETE id=229 commit_ts=2026-11-26T18:07:04.654084+00:00 commit_ts_ms=1795716424654
INSERT id=230 commit_ts=2026-11-26T18:07:04.658742+00:00 commit_ts_ms=1795716424658 customer_id=9001
UPDATE id=230 commit_ts=2026-11-26T18:07:04.664711+00:00 commit_ts_ms=1795716424664 status=shipped
DELETE id=230 commit_ts=2026-11-26T18:07:04.672516+00:00 commit_ts_ms=1795716424672
INSERT id=231 commit_ts=2026-11-26T18:07:04.676786+00:00 commit_ts_ms=1795716424676 customer_id=9001
UPDATE id=231 commit_ts=2026-11-26T18:07:04.681420+00:00 commit_ts_ms=1795716424681 status=shipped
DELETE id=231 commit_ts=2026-11-26T18:07:04.689433+00:00 commit_ts_ms=1795716424689
INSERT id=232 commit_ts=2026-11-26T18:07:04.692667+00:00 commit_ts_ms=1795716424692 customer_id=9001
UPDATE id=232 commit_ts=2026-11-26T18:07:04.696356+00:00 commit_ts_ms=1795716424696 status=shipped
DELETE id=232 commit_ts=2026-11-26T18:07:04.703197+00:00 commit_ts_ms=1795716424703
INSERT id=233 commit_ts=2026-11-26T18:07:04.706526+00:00 commit_ts_ms=1795716424706 customer_id=9001
UPDATE id=233 commit_ts=2026-11-26T18:07:04.710209+00:00 commit_ts_ms=1795716424710 status=shipped
DELETE id=233 commit_ts=2026-11-26T18:07:04.715034+00:00 commit_ts_ms=1795716424715
INSERT id=234 commit_ts=2026-11-26T18:07:04.719571+00:00 commit_ts_ms=1795716424719 customer_id=9001
UPDATE id=234 commit_ts=2026-11-26T18:07:04.723299+00:00 commit_ts_ms=1795716424723 status=shipped
DELETE id=234 commit_ts=2026-11-26T18:07:04.728095+00:00 commit_ts_ms=1795716424728
loop finished after 30 round(s)
PS C:\Users\asus\subop> 

```

## 4. Finding 2 — Kafka Topic Discovery Latency

### Test Method

The initial CDC consumer test targeted the non-existent `subop-postgres-cdc.cdc_demo.customers` topic.

The following command was recovered from PowerShell history:

```powershell
python -m services.cdc.kafka_consumer --pattern "^subop-postgres-cdc\.cdc_demo\.customers$" --group m8w28t10-discovery-test
```

The experiment returned an UNKNOWN_TOPIC_OR_PART warning.

The complete original warning output was not recovered.

The corresponding PostgreSQL source table was also missing.

To avoid database schema changes, the comparison was performed using isolated Kafka consumers with the same client library and equivalent basic subscription settings.

For each experiment:

1. Start a consumer with a unique regex subscription and group.
2. Poll for approximately 10 seconds before topic creation.
3. Create the topic and publish one test message.
4. Measure the time from successful topic creation to first message reception.

Python code was executed directly through PowerShell.

No additional source file was created during the original experiment.

Both original Python commands were recovered from PowerShell command history on 2026-11-26 and are documented below.

### Experiment 1 — Default Configuration

Metadata refresh interval: default (300000 ms reference).

#### Executed Command and Python Code

The original experiment was executed in PowerShell using the following inline Python command.

PowerShell history formatting artifacts were removed without changing the Python program logic.

```powershell
@'
import time
import uuid
from confluent_kafka import Consumer, Producer
from confluent_kafka.admin import AdminClient, NewTopic

topic = "discovery-test-" + uuid.uuid4().hex[:8]
consumer = Consumer({
    "bootstrap.servers": "localhost:9092",
    "group.id": topic,
    "auto.offset.reset": "earliest",
    "enable.auto.commit": False,
    "enable.auto.offset.store": False
})
admin = AdminClient({"bootstrap.servers": "localhost:9092"})
producer = Producer({"bootstrap.servers": "localhost:9092"})

consumer.subscribe(["^" + topic + "$"])
start = time.monotonic()
print("Consumer subscribed:", topic, flush=True)

while time.monotonic() - start < 10:
    consumer.poll(1)

admin.create_topics([NewTopic(topic, 1, 1)])[topic].result()
created = time.monotonic()
producer.produce(topic, value="test")
producer.flush()
print("Topic created and message sent.", flush=True)

try:
    while time.monotonic() - created < 360:
        msg = consumer.poll(1)
        if msg is not None and not msg.error():
            print("First message:", msg.value().decode())
            print("Discovery latency:", round(time.monotonic() - created, 3), "seconds")
            print("Total elapsed:", round(time.monotonic() - start, 3), "seconds")
            break
    else:
        print("TIMEOUT: 360 seconds")
finally:
    consumer.close()
'@ | python -
```

#### Recorded Output

```text
Consumer subscribed: discovery-test-2dddd72e
Topic created and message sent.
First message: test
Discovery latency: 292.482 seconds
Total elapsed: 303.142 seconds
```



#### Repeat Experiment 1 — Default Configuration (26 November 2026)

The default metadata refresh experiment was repeated on 2026-11-26 to verify the original measurement and capture the complete execution record.

The same Python code and consumer configuration were used without explicitly overriding the default metadata refresh interval.

##### Executed Command and Raw Terminal Output

```text
PS C:\Users\asus\subop> @'
>> import time
>> import uuid
>> from confluent_kafka import Consumer, Producer
>> from confluent_kafka.admin import AdminClient, NewTopic
>>
>> topic = "discovery-test-" + uuid.uuid4().hex[:8]
>> consumer = Consumer({
>>     "bootstrap.servers": "localhost:9092",
>>     "group.id": topic,
>>     "auto.offset.reset": "earliest",
>>     "enable.auto.commit": False,
>>     "enable.auto.offset.store": False
>> })
>> admin = AdminClient({"bootstrap.servers": "localhost:9092"})
>> producer = Producer({"bootstrap.servers": "localhost:9092"})
>>
>> consumer.subscribe(["^" + topic + "$"])
>> start = time.monotonic()
>> print("Consumer subscribed:", topic, flush=True)
>>
>> while time.monotonic() - start < 10:
>>     consumer.poll(1)
>>
>> admin.create_topics([NewTopic(topic, 1, 1)])[topic].result()
>> created = time.monotonic()
>> producer.produce(topic, value="test")
>> producer.flush()
>> print("Topic created and message sent.", flush=True)
>>
>> try:
>>     while time.monotonic() - created < 360:
>>         msg = consumer.poll(1)
>>         if msg is not None and not msg.error():
>>             print("First message:", msg.value().decode())
>>             print("Discovery latency:", round(time.monotonic() - created, 3), "seconds")
>>             print("Total elapsed:", round(time.monotonic() - start, 3), "seconds")
>>             break
>>     else:
>>         print("TIMEOUT: 360 seconds")
>> finally:
>>     consumer.close()
>> '@ | python -
Consumer subscribed: discovery-test-152559fe
Topic created and message sent.
First message: test
Discovery latency: 292.463 seconds
Total elapsed: 303.144 seconds
```

##### Measurement Results

| Parameter | Value |
|---|---|
| Execution date | 2026-11-26 |
| Test topic | discovery-test-152559fe |
| Consumer group | discovery-test-152559fe |
| Metadata refresh interval | Default (300000 ms reference) |
| Discovery latency | 292.463 seconds |
| Total elapsed | 303.144 seconds |
| Expected message | test |
| Received message | test |
| Timeout | No |
| Result | PASS |

##### Comparison with Original Experiment

| Metric | Original Experiment | Repeat Experiment | Absolute Difference |
|---|---:|---:|---:|
| Discovery latency | 292.482 s | 292.463 s | 0.019 s |
| Total elapsed | 303.142 s | 303.144 s | 0.002 s |

The repeated discovery latency measurement differed from the original measurement by only 0.019 seconds, approximately 0.0065%.

The repeat experiment confirms that the original discovery latency was reproducible under the tested local conditions.

Both default-configuration experiments successfully received the expected test message.

No modifications were made to the existing CDC consumer implementation.

The repeat experiment execution command and terminal output are now documented.

**Repeat Experiment 1 Result: PASS.**

### Experiment 2 — Proposed Configuration

The consumer configuration included:

```python
"topic.metadata.refresh.interval.ms": 5000
```

#### Executed Command and Python Code

The second experiment used the same measurement procedure with an explicit metadata refresh interval of 5000 ms.

The original command was recovered from PowerShell command history on 2026-11-26.

```powershell
@'
import time
import uuid
from confluent_kafka import Consumer, Producer
from confluent_kafka.admin import AdminClient, NewTopic

topic = "discovery-test-" + uuid.uuid4().hex[:8]
consumer = Consumer({
    "bootstrap.servers": "localhost:9092",
    "group.id": topic,
    "auto.offset.reset": "earliest",
    "enable.auto.commit": False,
    "enable.auto.offset.store": False,
    "topic.metadata.refresh.interval.ms": 5000
})
admin = AdminClient({"bootstrap.servers": "localhost:9092"})
producer = Producer({"bootstrap.servers": "localhost:9092"})

consumer.subscribe(["^" + topic + "$"])
start = time.monotonic()
print("Consumer subscribed:", topic, flush=True)

while time.monotonic() - start < 10:
    consumer.poll(1)

admin.create_topics([NewTopic(topic, 1, 1)])[topic].result()
created = time.monotonic()
producer.produce(topic, value="test")
producer.flush()
print("Topic created and message sent.", flush=True)

try:
    while time.monotonic() - created < 360:
        msg = consumer.poll(1)
        if msg is not None and not msg.error():
            print("First message:", msg.value().decode())
            print("Discovery latency:", round(time.monotonic() - created, 3), "seconds")
            print("Total elapsed:", round(time.monotonic() - start, 3), "seconds")
            break
    else:
        print("TIMEOUT: 360 seconds")
finally:
    consumer.close()
'@ | python -
```

#### Recorded Output

```text
Consumer subscribed: discovery-test-107559a0
Topic created and message sent.
First message: test
Discovery latency: 7.676 seconds
Total elapsed: 18.148 seconds
```

#### Repeat Experiment 2 — Proposed Configuration (26 November 2026)

The proposed metadata refresh configuration was tested again on 2026-11-26 to verify the original measurement and capture the complete execution record.

The same Python code and consumer configuration were used with an explicit metadata refresh interval of 5000 ms.

##### Executed Command and Raw Terminal Output

```text
PS C:\Users\asus\subop> @'
>> import time
>> import uuid
>> from confluent_kafka import Consumer, Producer
>> from confluent_kafka.admin import AdminClient, NewTopic
>> 
>> topic = "discovery-test-" + uuid.uuid4().hex[:8]
>> consumer = Consumer({
>>     "bootstrap.servers": "localhost:9092",
>>     "group.id": topic,
>>     "auto.offset.reset": "earliest",
>>     "enable.auto.commit": False,
>>     "enable.auto.offset.store": False,
>>     "topic.metadata.refresh.interval.ms": 5000
>> })
>> admin = AdminClient({"bootstrap.servers": "localhost:9092"})
>> producer = Producer({"bootstrap.servers": "localhost:9092"})
>> 
>> consumer.subscribe(["^" + topic + "$"])
>> start = time.monotonic()
>> print("Consumer subscribed:", topic, flush=True)
>> 
>> while time.monotonic() - start < 10:
>>     consumer.poll(1)
>> 
>> admin.create_topics([NewTopic(topic, 1, 1)])[topic].result()
>> created = time.monotonic()
>> producer.produce(topic, value="test")
>> producer.flush()
>> print("Topic created and message sent.", flush=True)
>> 
>> try:
>>     while time.monotonic() - created < 360:
>>         msg = consumer.poll(1)
>>         if msg is not None and not msg.error():
>>             print("First message:", msg.value().decode())
>>             print("Discovery latency:", round(time.monotonic() - created, 3), "seconds")
>>             print("Total elapsed:", round(time.monotonic() - start, 3), "seconds")
>>             break
>>     else:
>>         print("TIMEOUT: 360 seconds")
>> finally:
>>     consumer.close()
>> '@ | python -
Consumer subscribed: discovery-test-86b28cbf
Topic created and message sent.
First message: test
Discovery latency: 7.724 seconds
Total elapsed: 18.141 seconds
```

##### Measurement Results

| Parameter | Value |
|---|---|
| Execution date | 2026-11-26 |
| Test topic | discovery-test-86b28cbf |
| Consumer group | discovery-test-86b28cbf |
| Metadata refresh interval | 5000 ms |
| Discovery latency | 7.724 seconds |
| Total elapsed | 18.141 seconds |
| Expected message | test |
| Received message | test |
| Timeout | No |
| Result | PASS |

##### Comparison with Original Experiment

| Metric | Original Experiment | Repeat Experiment | Absolute Difference |
|---|---:|---:|---:|
| Discovery latency | 7.676 s | 7.724 s | 0.048 s |
| Total elapsed | 18.148 s | 18.141 s | 0.007 s |

The repeated discovery latency measurement differed from the original measurement by only 0.048 seconds, approximately 0.63%.

Both proposed-configuration experiments successfully received the expected test message.

The repeat experiment confirms that the significant reduction in discovery latency was reproducible under the tested local conditions.

No modifications were made to the existing CDC consumer implementation.

The repeat experiment execution command and terminal output are now documented.

**Repeat Experiment 2 Result: PASS.**




### Comparison

#### Original Experiment Results

| Metric | Default | Proposed |
|---|---:|---:|
| Metadata refresh interval | 300000 ms | 5000 ms |
| Discovery latency | 292.482 s | 7.676 s |
| Total elapsed | 303.142 s | 18.148 s |
| Message received | Yes | Yes |

- Latency reduction: 284.806 seconds.
- Percentage reduction: 97.38%.
- Observed improvement: approximately 38.10x.

#### Repeat Experiment Results — 26 November 2026

| Metric | Default | Proposed |
|---|---:|---:|
| Metadata refresh interval | 300000 ms | 5000 ms |
| Discovery latency | 292.463 s | 7.724 s |
| Total elapsed | 303.144 s | 18.141 s |
| Message received | Yes | Yes |

Latency reduction:

```text
292.463 - 7.724 = 284.739 seconds
```

Percentage reduction:

```text
(292.463 - 7.724) / 292.463 * 100
= approximately 97.36%
```

Observed improvement:

```text
292.463 / 7.724
= approximately 37.86x
```

#### Consolidated Experiment Results

| Metric | Original Experiments | Repeat Experiments |
|---|---:|---:|
| Default discovery latency | 292.482 s | 292.463 s |
| Proposed discovery latency | 7.676 s | 7.724 s |
| Latency reduction | 284.806 s | 284.739 s |
| Percentage reduction | 97.38% | 97.36% |
| Observed improvement | 38.10x | 37.86x |
| Successful message reception | 2/2 | 2/2 |

#### Reproducibility Assessment

| Configuration | Original Latency | Repeat Latency | Absolute Difference |
|---|---:|---:|---:|
| Default | 292.482 s | 292.463 s | 0.019 s |
| Proposed | 7.676 s | 7.724 s | 0.048 s |

Both configurations were tested twice.

All four experiments successfully received the expected test message.

The proposed metadata refresh interval consistently reduced the observed topic discovery latency by approximately 97%.

The repeat experiments independently reproduced the principal findings of the original experiments.

Complete execution commands and terminal outputs for both repeat experiments are documented.

These results describe isolated Kafka consumer topic discovery behavior under the tested local conditions. They do not establish end-to-end CDC latency or quantify additional broker overhead.


### Recommendation

Add the following configuration to the existing consumer:

```python
"topic.metadata.refresh.interval.ms": 5000,
```

Target file: `services/cdc/kafka_consumer.py`

Implementation owner: Abdalla.

The proposed configuration significantly reduced the observed topic discovery latency in the isolated experiment.

However, more frequent metadata requests may increase broker overhead.

### Limitations

- Two runs per configuration were performed: one original run and one repeat run on 26 November 2026.
- The experiment measured isolated Kafka client behavior, not end-to-end CDC latency.
- Broker overhead was not measured.
- Test topic cleanup was not verified.
- The latency measurement also includes message production and first-message reception after successful topic creation.
- The default metadata refresh interval was not explicitly overridden in Experiment 1.
- The recorded outputs are preserved from the original report.
- Complete original terminal transcripts have not been recovered.

### Finding 2 Result

Measurement completed and configuration proposed.

Both original Python commands are now documented, allowing the experiments to be reproduced.

No changes were made to `kafka_consumer.py` as part of this task because it is on the critical path.


### Repeat Experiment Status

Both topic discovery experiments were successfully repeated on 2026-11-26.

| Verification item | Status |
|---|---|
| Original default configuration Python code | Recovered and documented |
| Original proposed configuration Python code | Recovered and documented |
| Default configuration repeat experiment | PASS |
| Proposed configuration repeat experiment | PASS |
| Default repeat experiment terminal output | Documented |
| Proposed repeat experiment terminal output | Documented |
| Reproducibility of original measurements | Confirmed under tested conditions |
| Comparative latency analysis | Completed |
| Configuration recommendation | Documented |
| Existing CDC consumer modifications | None |

The original measurements have been preserved separately from the repeat measurements.

Although the complete original terminal transcripts were not recovered, both original experiments were reproduced using the documented Python commands, and the complete repeat experiment execution records are now included.

The proposed 5000 ms metadata refresh interval reduced discovery latency by approximately 97% in both comparisons.

**Finding 2 technical verification and repeat experiment documentation: COMPLETE.**


## 5. Finding 3 — Local Environment Discrepancy

**Date:** 2026-11-26

### Description

The local PostgreSQL environment was inspected using:

```bash
bash infrastructure/scripts/verify_cdc_prerequisites.sh
```

The verification script reported four failed prerequisite checks:

- CHECK 3 — Published tables
- CHECK 5 — Replica identity
- CHECK 6 — Seed rows
- CHECK 7 — CDC role SELECT grant

All four failures are related to the missing `cdc_demo.customers` table.

According to the task review feedback, the local environment retained Docker volumes initialized before the updated M7 database setup, which introduced the customers table into `cdc_replication_setup.sql` on November 3.

Existing Docker volumes were preserved.

### Impact on Finding 1

Finding 1 remains valid because the replication-slot lifecycle experiments performed on 20 November and 26 November used the `cdc_demo.orders` table exclusively.

The missing customers table limits the scope of the experiments but does not invalidate the measured orders replication results.

Both experiments demonstrated successful delivery of all 180 expected test events.

### Impact on Finding 2

The missing source table prevented the intended CDC customers topic discovery test from being completed.

Therefore, the comparison was performed using isolated Kafka topics and consumers instead.

The results demonstrate isolated Kafka topic discovery behavior rather than end-to-end customers CDC behavior.

### Additional Environment Warning

The verification script also reported that `COMPOSE_PROJECT_NAME` was unset.

This corresponds to the previously documented M7W23T1 Finding 3.

The recommended configuration is:

```dotenv
COMPOSE_PROJECT_NAME=subop
```

No environment configuration changes were performed as part of this verification.

### Infrastructure Status

All four required CDC infrastructure services were running and healthy:

- PostgreSQL
- Kafka
- ZooKeeper
- Debezium Kafka Connect

The Debezium connector and its task were also in the RUNNING state.

The `subop-api` service was not running, but it was not required for the CDC capture experiment.

### Recorded Terminal Output — Prerequisite Verification

The following command and output were recorded on 2026-11-26.

The output below is preserved from the existing report. Exact transcript completeness and formatting remain subject to verification.

```bash
bash infrastructure/scripts/verify_cdc_prerequisites.sh
```

```text
WARNING: COMPOSE_PROJECT_NAME is unset — volume names derive from the
         checkout folder name and differ between team members.
         M7W23T1 Finding 3, open item. Set COMPOSE_PROJECT_NAME=subop.

==============================================================
SECTION 3 — PREREQUISITE CHECKS
==============================================================

--- CHECK 1 — wal_level (expect: logical) ---
$ SHOW wal_level;
 wal_level
-----------
 logical
(1 row)

OK: logical

--- CHECK 2 — publication scope (expect: subop_cdc_pub, puballtables = f) ---
$ SELECT pubname, puballtables FROM pg_publication;
    pubname    | puballtables
---------------+--------------
 subop_cdc_pub | f
(1 row)

OK: subop_cdc_pub:false

--- CHECK 3 — published tables (expect: exactly cdc_demo.customers with 5 columns and cdc_demo.orders with 6) ---
$ SELECT * FROM pg_publication_tables;
    pubname    | schemaname | tablename |                       attnames                       | rowfilter
---------------+------------+-----------+------------------------------------------------------+-----------
 subop_cdc_pub | cdc_demo   | orders    | {id,customer_id,status,amount,created_at,updated_at} |
(1 row)

FAIL: expected 'cdc_demo.customers(5),cdc_demo.orders(6)', got 'cdc_demo.orders(6)'

--- CHECK 4 — CDC role (expect: subop_cdc, rolreplication = t) ---
$ SELECT rolname, rolreplication FROM pg_roles WHERE rolname = 'subop_cdc';
  rolname  | rolreplication
-----------+----------------
 subop_cdc | t
(1 row)

OK: subop_cdc:true

--- CHECK 5 — replica identity (expect: f for both orders and customers) ---
$ SELECT n.nspname, c.relname, c.relreplident FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 'cdc_demo' AND c.relkind = 'r' ORDER BY c.relname;
 nspname  | relname | relreplident
----------+---------+--------------
 cdc_demo | orders  | f
(1 row)

FAIL: expected 'customers:f,orders:f', got 'orders:f'

--- CHECK 6 — seed rows (expect: 3 in each table) ---
$ SELECT 'orders' AS tbl, count(*) AS seed_rows FROM cdc_demo.orders UNION ALL SELECT 'customers', count(*) FROM cdc_demo.customers;
ERROR:  relation "cdc_demo.customers" does not exist
LINE 1: ...rders UNION ALL SELECT 'customers', count(*) FROM cdc_demo.c...
                                                             ^

What's next:
    Debug this Compose error with Gordon → docker ai "help me fix this compose error"
FAIL: psql exited 1

--- CHECK 7 — CDC role SELECT grant (expect: t for both tables) ---
$ SELECT has_table_privilege('subop_cdc', 'cdc_demo.orders', 'SELECT') AS orders, has_table_privilege('subop_cdc', 'cdc_demo.customers', 'SELECT') AS customers;
ERROR:  relation "cdc_demo.customers" does not exist

What's next:
    Debug this Compose error with Gordon → docker ai "help me fix this compose error"
FAIL: psql exited 1

==============================================================
SECTION 4 — INIT-SCRIPT EXECUTION EVIDENCE
==============================================================
$ docker compose logs postgres --no-color | grep -A 16 '10-cdc-replication.sql'

==============================================================
SECTION 5 — FULL-STACK CONTAINER STATUS
==============================================================
$ docker compose ps
NAME              IMAGE                             COMMAND                  SERVICE     CREATED      STATUS                    PORTS
subop-connect     quay.io/debezium/connect:3.6       "/docker-entrypoint.…"   connect     7 days ago   Up 2 minutes (healthy)    0.0.0.0:8083->8083/tcp, [::]:8083->8083/tcp
subop-kafka       confluentinc/cp-kafka:7.6.0         "/etc/confluent/dock…"   kafka       7 days ago   Up 2 minutes (healthy)    0.0.0.0:9092->9092/tcp, [::]:9092->9092/tcp
subop-postgres    postgres:15                       "docker-entrypoint.s…"   postgres    7 days ago   Up 2 minutes (healthy)    0.0.0.0:5433->5432/tcp, [::]:5433->5432/tcp
subop-zookeeper   confluentinc/cp-zookeeper:7.6.0    "/etc/confluent/dock…"   zookeeper   7 days ago   Up 2 minutes (healthy)    0.0.0.0:2181->2181/tcp, [::]:2181->2181/tcp

==============================================================
SECTION 6 — KAFKA CONNECT READINESS
==============================================================

$ curl -s http://localhost:8083/
{"version":"4.3.0","commit":"a9ce3221537b8653","kafka_cluster_id":"PlmhK3b9RN-altmr_TTe8g"}

$ curl -s http://localhost:8083/connectors
["subop-postgres-cdc"]

$ curl -s http://localhost:8083/connector-plugins | grep -o PostgresConnector
io.debezium.connector.postgresql.PostgresConnector

NOTE: subop-api is not running. It depends on mysql, mssql and
      oracle reporting healthy, so a slow first-time init leaves it
      Created but never Started. Capture does not need it.

==============================================================
SUMMARY
==============================================================
4 check(s) reported a problem. Record them as findings; do not
proceed to capture until they are resolved or explained.
```

### Prerequisite Check Summary

| Check | Result | Explanation |
|---|---|---|
| WAL level | PASS | logical |
| Publication scope | PASS | subop_cdc_pub:false |
| Published tables | FAIL | customers missing |
| CDC role | PASS | subop_cdc:true |
| Replica identity | FAIL | customers missing |
| Seed rows | FAIL | customers relation does not exist |
| CDC role SELECT grant | FAIL | customers relation does not exist |

Total checks: 7.

Passed checks: 3.

Failed checks: 4.

No matching init-script execution evidence was returned in Section 4 of the verification output.




### Repeat Prerequisite Verification — 26 November 2026

**Verification date:** 2026-11-26

The prerequisite verification script was executed again during the review revision to capture the complete terminal output and verify the previously documented local environment discrepancy.

Command:

```bash
bash infrastructure/scripts/verify_cdc_prerequisites.sh
```

Raw terminal output:

```text
WARNING: COMPOSE_PROJECT_NAME is unset — volume names derive from the
         checkout folder name and differ between team members.
         M7W23T1 Finding 3, open item. Set COMPOSE_PROJECT_NAME=subop.

==============================================================
SECTION 3 — PREREQUISITE CHECKS
==============================================================

--- CHECK 1 — wal_level (expect: logical) ---
$ SHOW wal_level;
 wal_level 
-----------
 logical
(1 row)

OK: logical

--- CHECK 2 — publication scope (expect: subop_cdc_pub, puballtables = f) ---
$ SELECT pubname, puballtables FROM pg_publication;
    pubname    | puballtables 
---------------+--------------
 subop_cdc_pub | f
(1 row)

OK: subop_cdc_pub:false

--- CHECK 3 — published tables (expect: exactly cdc_demo.customers with 5 columns and cdc_demo.orders with 6) ---
$ SELECT * FROM pg_publication_tables;
    pubname    | schemaname | tablename |                       attnames                       | rowfilter 
---------------+------------+-----------+------------------------------------------------------+-----------
 subop_cdc_pub | cdc_demo   | orders    | {id,customer_id,status,amount,created_at,updated_at} | 
(1 row)

FAIL: expected 'cdc_demo.customers(5),cdc_demo.orders(6)', got 'cdc_demo.orders(6)'

--- CHECK 4 — CDC role (expect: subop_cdc, rolreplication = t) ---
$ SELECT rolname, rolreplication FROM pg_roles WHERE rolname = 'subop_cdc';
  rolname  | rolreplication 
-----------+----------------
 subop_cdc | t
(1 row)

OK: subop_cdc:true

--- CHECK 5 — replica identity (expect: f for both orders and customers) ---
$ SELECT n.nspname, c.relname, c.relreplident FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = 'cdc_demo' AND c.relkind = 'r' ORDER BY c.relname;
 nspname  | relname | relreplident 
----------+---------+--------------
 cdc_demo | orders  | f
(1 row)

FAIL: expected 'customers:f,orders:f', got 'orders:f'

--- CHECK 6 — seed rows (expect: 3 in each table) ---
$ SELECT 'orders' AS tbl, count(*) AS seed_rows FROM cdc_demo.orders UNION ALL SELECT 'customers', count(*) FROM cdc_demo.customers;
ERROR:  relation "cdc_demo.customers" does not exist
LINE 1: ...rders UNION ALL SELECT 'customers', count(*) FROM cdc_demo.c...
                                                             ^

What's next:
    Debug this Compose error with Gordon → docker ai "help me fix this compose error"
FAIL: psql exited 1

--- CHECK 7 — CDC role SELECT grant (expect: t for both tables) ---
$ SELECT has_table_privilege('subop_cdc', 'cdc_demo.orders', 'SELECT') AS orders, has_table_privilege('subop_cdc', 'cdc_demo.customers', 'SELECT') AS customers;
ERROR:  relation "cdc_demo.customers" does not exist

What's next:
    Debug this Compose error with Gordon → docker ai "help me fix this compose error"
FAIL: psql exited 1

==============================================================
SECTION 4 — INIT-SCRIPT EXECUTION EVIDENCE
==============================================================
$ docker compose logs postgres --no-color | grep -A 16 '10-cdc-replication.sql'

==============================================================
SECTION 5 — FULL-STACK CONTAINER STATUS
==============================================================
$ docker compose ps
NAME              IMAGE                             COMMAND                  SERVICE     CREATED      STATUS                    PORTS
subop-connect     quay.io/debezium/connect:3.6      "/docker-entrypoint.…"   connect     7 days ago   Up 46 minutes (healthy)   0.0.0.0:8083->8083/tcp, [::]:8083->8083/tcp
subop-kafka       confluentinc/cp-kafka:7.6.0       "/etc/confluent/dock…"   kafka       7 days ago   Up 47 minutes (healthy)   0.0.0.0:9092->9092/tcp, [::]:9092->9092/tcp
subop-postgres    postgres:15                       "docker-entrypoint.s…"   postgres    7 days ago   Up 47 minutes (healthy)   0.0.0.0:5433->5432/tcp, [::]:5433->5432/tcp
subop-zookeeper   confluentinc/cp-zookeeper:7.6.0   "/etc/confluent/dock…"   zookeeper   7 days ago   Up 47 minutes (healthy)   0.0.0.0:2181->2181/tcp, [::]:2181->2181/tcp

==============================================================
SECTION 6 — KAFKA CONNECT READINESS
==============================================================

$ curl -s http://localhost:8083/
{"version":"4.3.0","commit":"a9ce3221537b8653","kafka_cluster_id":"PlmhK3b9RN-altmr_TTe8g"}

$ curl -s http://localhost:8083/connectors
["subop-postgres-cdc"]

$ curl -s http://localhost:8083/connector-plugins | grep -o PostgresConnector
io.debezium.connector.postgresql.PostgresConnector

NOTE: subop-api is not running. It depends on mysql, mssql and
      oracle reporting healthy, so a slow first-time init leaves it
      Created but never Started. Capture does not need it.

==============================================================
SUMMARY
==============================================================
4 check(s) reported a problem. Record them as findings; do not
proceed to capture until they are resolved or explained.

asus@LAPTOP-18VI7S6I MINGW64 ~/subop (develop)
$
```

### Repeat Verification Results

| Verification item | Result |
|---|---|
| Total prerequisite checks | 7 |
| Passed checks | 3 |
| Failed checks | 4 |
| Missing table | cdc_demo.customers |
| PostgreSQL container | Healthy |
| Kafka container | Healthy |
| ZooKeeper container | Healthy |
| Kafka Connect container | Healthy |
| Existing connector registration | Confirmed |
| COMPOSE_PROJECT_NAME | Unset |
| Complete terminal output | Captured and documented |

The repeat verification reproduced the same four prerequisite failures associated with the missing cdc_demo.customers table.

The result is consistent with the outdated local database schema described in the review feedback.

The existing Docker volumes were preserved. No database schema changes or environment configuration changes were performed.

The discrepancy does not invalidate the replication slot lifecycle measurements because Finding 1 exclusively used cdc_demo.orders.

The prerequisite verification command and its complete repeat execution output are now documented, addressing the corresponding review requirement.

**Finding 3 documentation: COMPLETE.**

**Local environment discrepancy: Confirmed and documented, not remediated.**


### Finding 3 Result

The local environment discrepancy was confirmed and documented with the prerequisite verification output.

The four failed checks share the same missing-table issue.

The existing database volumes were preserved, and no schema modifications were made during this verification.

The local environment discrepancy remains unresolved but is explicitly documented.

## 6. Additional Verification — 26 November 2026

The following commands were executed during the review revision to verify the existing connector and replication slot.

These measurements are separate from both the original 20 November experiment and the subsequent 26 November pause/resume repeat experiment.

### Connector Registration Attempt

Command:

```bash
curl -sS -i -X POST \
-H "Content-Type: application/json" \
--data-binary @services/cdc/debezium_postgres_connector.json \
http://localhost:8083/connectors
```

Raw output:

```text
HTTP/1.1 409 Conflict
Server: Jetty(12.0.34)
Date: Thu, 26 Nov 2026 17:18:11 GMT
Content-Type: application/json
Content-Length: 74

{"error_code":409,"message":"Connector subop-postgres-cdc already exists"}
```

The registration request returned HTTP 409 because the connector was already registered.

No duplicate connector was created.

### Connector List

Command:

```bash
curl -sS http://localhost:8083/connectors
```

Raw output:

```text
["subop-postgres-cdc"]
```

### Connector Status

Command:

```bash
curl -sS http://localhost:8083/connectors/subop-postgres-cdc/status
```

Raw output:

```text
{"name":"subop-postgres-cdc","connector":{"state":"RUNNING","worker_id":"172.18.0.5:8083","version":"3.6.3.Final"},"tasks":[{"id":0,"state":"RUNNING","worker_id":"172.18.0.5:8083","version":"3.6.3.Final"}],"type":"source"}
```

Both the connector and its task were in the RUNNING state.

### Replication Slot Measurement

Command:

```bash
bash infrastructure/scripts/check_cdc_slot.sh
```

Recorded output:

```text
==============================================================
 SUBOP — CDC Replication Slot Measurement
 Task: M8W28T10
==============================================================

Timestamp (UTC): 2026-11-26T17:18:49Z
Database:        subop
PostgreSQL user: subop
Replication slot: subop_cdc_slot

--------------------------------------------------------------
 Replication Slot Status
--------------------------------------------------------------

   slot_name    | active | restart_lsn | confirmed_flush_lsn | retained_wal_bytes | retained_wal_mb
----------------+--------+-------------+---------------------+--------------------+-----------------
 subop_cdc_slot | t      | 0/1A5DF58   | 0/1A6B4B0           |             622552 |            0.59
(1 row)


--------------------------------------------------------------
 Measurement completed successfully
--------------------------------------------------------------
```

### Verification Summary

| Parameter | Value |
|---|---|
| Replication slot | subop_cdc_slot |
| Active | true |
| restart_lsn | 0/1A5DF58 |
| confirmed_flush_lsn | 0/1A6B4B0 |
| Retained WAL | 622552 bytes |
| Retained WAL | 0.59 MiB |
| Measurement status | Successful |

This verification confirms that the replication slot and measurement script were operational on 2026-11-26.

The complete pause/resume repeat experiment performed later on the same day is documented separately in Finding 1.

## 7. Issues and Resolutions

| Issue | Resolution or status |
|---|---|
| PowerShell Bash/WSL issue | Used Git Bash |
| PowerShell curl alias issue | Used curl.exe |
| Missing replication slot | Registered Debezium connector |
| Missing connection references | Configured local .env |
| Kafka Connect empty reply | Waited for initialization |
| Missing event_log table | Started CDC consumer |
| Missing confluent_kafka | Installed Python dependency |
| Delayed LSN advancement | Repeated slot measurement |
| Missing customers table | Documented in Finding 3; used isolated Kafka tests |
| Outdated local database schema | Documented; existing volumes preserved |
| COMPOSE_PROJECT_NAME unset | Documented as existing M7W23T1 open item |
| Connector registration HTTP 409 | Existing connector verified as RUNNING |
| Missing discovery test Python code | Recovered from PowerShell history and documented |
| Missing prerequisite verification output | Original and repeat verification outputs included |
| Missing original lifecycle experiment output | Performed separately dated repeat experiment |
| Incomplete Batch 2 and Batch 3 transcripts | Supplementary executions performed; complete new transcripts included |
| Incomplete Kafka discovery experiment records | Both configurations repeated; commands, Python code, and new outputs included |
| Retained WAL continued increasing after resume | Explained and documented as an experimental limitation |
| LSN advancement interpretation | Distinguished from end-to-end CDC delivery latency |
| Complete WAL reclamation | Not demonstrated |

Existing Docker volumes were preserved.

The preliminary experiment on 2026-11-19 was repeated on 2026-11-20 to complete event log verification.

A further repeat experiment was conducted on 2026-11-26 to address the execution evidence requirements raised during task review.

Both completed pause/resume experiments produced consistent technical results.

Supplementary batch executions generated another 150 source changes and provided complete terminal transcripts for the 20-round and 30-round commands.

These supplementary executions are documented separately and are not presented as historical outputs from the pause/resume experiments.

Both Kafka topic discovery configurations were also repeated on 2026-11-26.

No changes to the critical-path Kafka consumer implementation were made.

## 8. Final Results

| Acceptance Criterion | Result |
|---|---|
| Replication slot measurement script | PASS |
| WAL accumulation during pause | PASS |
| Stable LSN values during pause | PASS |
| LSN advancement after resume | PASS |
| Original CDC event completeness | 180/180 |
| Repeat CDC event completeness | 180/180 |
| Combined verified test events | 360/360 |
| Missing test events | 0 |
| Duplicate test event log records | 0 |
| Original retained WAL increase during pause | 73480 bytes (8.94%) |
| Repeat retained WAL increase during pause | 88872 bytes (14.08%) |
| Complete WAL reclamation | Not demonstrated |
| Original default topic discovery latency | 292.482 seconds |
| Original proposed topic discovery latency | 7.676 seconds |
| Repeat default topic discovery latency | 292.463 seconds |
| Repeat proposed topic discovery latency | 7.724 seconds |
| Original discovery latency reduction | Approximately 97.38% |
| Repeat discovery latency reduction | Approximately 97.36% |
| Kafka discovery experiments | 4/4 successful |
| Metadata refresh recommendation | 5000 ms |
| Discovery test Python code | Documented |
| Supplementary batch executions | 150 source changes; complete new transcripts included |
| Local environment discrepancy | Confirmed and documented |
| Prerequisite verification output | Original and repeat outputs included |
| Critical-path consumer modification by this task | None |
| Finding 1 repeat experiment | Technically completed |
| Historical verbatim execution record | Partially recovered; limitations documented |

### Key Conclusions

1. Retained WAL increased while the Debezium connector was paused in both experiments.

2. Both restart_lsn and confirmed_flush_lsn advanced after the connector resumed.

3. All 180 expected orders CDC events reached the event log during each experiment without missing or duplicate test event log records.

4. Across the two pause/resume experiments, 360 expected events were successfully verified.

5. The repeat experiment demonstrated a retained WAL increase of 88872 bytes, approximately 14.08%, during the paused batch execution window.

6. Complete WAL reclamation was not demonstrated in either experiment.

7. WAL retention depends on restart_lsn advancement, continued WAL generation, checkpoint behavior, and PostgreSQL retention requirements.

8. The observed LSN advancement intervals must not be interpreted as end-to-end CDC delivery latency measurements.

9. Reducing the Kafka metadata refresh interval to 5000 ms reduced observed topic discovery latency by approximately 97.38% in the original experiment and 97.36% in the repeat experiment.

10. The isolated Kafka discovery experiments produced consistent results across both execution dates.

11. The original and repeated Python discovery test commands are documented to support reproducibility.

12. Supplementary batch executions produced 150 additional source changes and complete new terminal transcripts. These changes are not included in the 360 verified pause/resume events.

13. The local database schema discrepancy was confirmed through prerequisite verification.

14. The existing Kafka consumer implementation was not modified as part of this task.

15. Existing PostgreSQL Docker volumes were preserved.

16. The technical scope of the replication slot lifecycle experiment is limited to the orders source table.

## 9. Deliverables

- `infrastructure/scripts/check_cdc_slot.sh`
- `docs/planning/cdc_slot_lifecycle.md`

### Review Revision Status

The following review findings have been addressed:

- Both original Python discovery experiment commands are included.
- Both Kafka topic discovery configurations were repeated on 2026-11-26.
- The repeated Python commands and their terminal outputs are included.
- Original and repeat discovery measurements are compared.
- The missing customers table is documented as a separate finding.
- Original and repeat prerequisite verification outputs are included.
- Additional connector and replication slot verification outputs are included.
- The original experiment results are preserved.
- A separately dated replication slot lifecycle repeat experiment was completed on 2026-11-26.
- Connector pause and resume requests and statuses are documented.
- All seven repeat-experiment WAL measurements are documented.
- LSN advancement was independently verified.
- All 180 expected repeat-experiment CDC events were verified.
- Missing and duplicate event log record checks returned zero rows.
- The original and repeat lifecycle experiment results are compared.
- Supplementary 20-round and 30-round commands were executed successfully.
- Complete supplementary terminal transcripts covering 150 source changes are included.
- WAL retention and checkpoint-related limitations are documented.
- LSN advancement is explicitly distinguished from end-to-end CDC delivery latency.
- The outdated local database schema is documented without modifying existing Docker volumes.

### Execution Record Limitations

Complete verbatim terminal transcripts from the original 19–20 November experiments have not been fully recovered.

The 26 November repeat lifecycle experiment provides new, separately dated technical evidence rather than reconstructed historical outputs.

The complete original operation transcripts for Batches 2 and 3 of the repeat pause/resume experiment are not available in this report.

To improve reproducibility, both batch commands were executed again and their complete supplementary terminal transcripts were recorded.

These supplementary transcripts contain different row IDs and timestamps and must not be treated as outputs from the earlier pause/resume experiment.

The repeated Kafka discovery experiments provide newly recorded execution evidence for both configurations.

Historical terminal outputs have not been reconstructed or fabricated.

Complete WAL reclamation remains unverified.

The local database schema discrepancy remains unresolved. Existing Docker volumes were intentionally preserved.

### Current Task Status

**Finding 1:** Technical verification completed. Original and repeat pause/resume experiments produced consistent results. Supplementary batch execution transcripts are included.

**Finding 2:** Original and repeat topic discovery experiments completed. Python code, recorded outputs, comparative analysis, and configuration recommendation are documented.

**Finding 3:** Local environment discrepancy confirmed and documented. Original and repeat prerequisite verification outputs are included.

**Implementation scope:** The read-only replication slot measurement script is implemented. No critical-path Kafka consumer modifications were made.

**Documentation status:** Updated with the additional execution evidence and explicitly documented limitations.

**Review status:** Ready for renewed review, subject to acceptance of the remaining historical execution record limitations.
