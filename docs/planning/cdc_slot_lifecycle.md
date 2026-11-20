
# M8W28T10 — CDC Replication Slot Lifecycle Measurement

## 1. Task Overview

- **Owner:** Omer
- **Branch:** develop
- **Environment:** Local M7 stack
- **Date:** 19–20 November 2026

### Objectives

- Measure retained WAL during connector pause and resume.
- Verify LSN advancement and CDC event completeness.
- Measure Kafka consumer topic discovery latency.
- Propose an improved metadata refresh configuration.

## 2. Test Environment

| Component | Value |
|---|---|
| PostgreSQL | 15 |
| Debezium | 3.6.3.Final |
| confluent-kafka | 2.16.2 |
| librdkafka | 2.16.0 |
| Connector | subop-postgres-cdc |
| Replication slot | subop_cdc_slot |
| Source table | cdc_demo.orders |
| Event log | cdc_meta.event_log |

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

Execution:

```bash
bash infrastructure/scripts/check_cdc_slot.sh
```

### Test Procedure

Start the CDC consumer:

```powershell
python -m services.cdc.kafka_consumer
```

Pause the connector:

```powershell
curl.exe -sS -i -X PUT http://localhost:8083/connectors/subop-postgres-cdc/pause
```

Result: HTTP 202 Accepted. Connector and task PAUSED.

Generate three batches of source changes:

```powershell
python -m services.cdc.cdc_demo_changes --all --loop 10 --interval 0
python -m services.cdc.cdc_demo_changes --all --loop 20 --interval 0
python -m services.cdc.cdc_demo_changes --all --loop 30 --interval 0
```

The replication slot was measured after each batch.

### Measurement Results

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

- Total generated changes: 180
- Retained WAL increase: 73,480 bytes (+8.94%)
- restart_lsn remained at 0/1990D98.
- confirmed_flush_lsn remained at 0/19954E8.
- Event log count remained at 186.

Resume the connector:

```powershell
curl.exe -sS -i -X PUT http://localhost:8083/connectors/subop-postgres-cdc/resume
```

Result: HTTP 202 Accepted. Connector and task RUNNING.

### LSN Verification

| Parameter | Before resume | After resume |
|---|---|---|
| restart_lsn | 0/1990D98 | 0/1995588 |
| confirmed_flush_lsn | 0/19954E8 | 0/1A6B4B0 |

Both LSN values advanced after resume.

The advancement was observed 125 seconds after the resume request.

### Event Completeness Verification

```powershell
docker compose exec -T postgres psql -U subop -d subop -c "SELECT COUNT(*) FROM cdc_meta.event_log;"
```

Output:

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

Output:

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

Output:

```text
 id | op | actual_count
----+----+--------------
(0 rows)
```

### Finding 1 Result: PASS

- WAL accumulated during the pause.
- LSN values advanced after resume.
- All 180 expected events reached the event log.
- Missing events: 0.
- Duplicate test events in the event log: 0.

Retained WAL did not decrease during the observed post-resume
window. Consumer writes to the same PostgreSQL environment may
have contributed to additional WAL generation.

Complete WAL reclamation was not demonstrated.

## 4. Finding 2 — Kafka Topic Discovery Latency

### Test Method

The initial CDC consumer test targeted the non-existent
`subop-postgres-cdc.cdc_demo.customers` topic and returned
an UNKNOWN_TOPIC_OR_PART warning.

The corresponding PostgreSQL source table was also missing.

To avoid database schema changes, the comparison was performed
using isolated Kafka consumers with the same client library
and equivalent basic subscription settings.

For each experiment:

1. Start a consumer with a unique regex subscription and group.
2. Poll for approximately 10 seconds before topic creation.
3. Create the topic and publish one test message.
4. Measure the time from topic creation to first message reception.

Python code was executed directly through PowerShell.
No additional source file was created.

### Experiment 1 — Default Configuration

Metadata refresh interval: default (300000 ms reference).

Output:

```text
Consumer subscribed: discovery-test-2dddd72e
Topic created and message sent.
First message: test
Discovery latency: 292.482 seconds
Total elapsed: 303.142 seconds
```

### Experiment 2 — Proposed Configuration

Consumer configuration:

```python
"topic.metadata.refresh.interval.ms": 5000
```

Output:

```text
Consumer subscribed: discovery-test-107559a0
Topic created and message sent.
First message: test
Discovery latency: 7.676 seconds
Total elapsed: 18.148 seconds
```

### Comparison

| Metric | Default | Proposed |
|---|---:|---:|
| Metadata refresh interval | 300000 ms | 5000 ms |
| Discovery latency | 292.482 s | 7.676 s |
| Total elapsed | 303.142 s | 18.148 s |
| Message received | Yes | Yes |

- Latency reduction: 284.806 seconds.
- Percentage reduction: 97.38%.
- Observed improvement: approximately 38.1x.

### Recommendation

Add the following configuration to the existing consumer:

```python
"topic.metadata.refresh.interval.ms": 5000,
```

Target file: `services/cdc/kafka_consumer.py`

Implementation owner: Abdalla.

The proposed configuration significantly reduced the observed
topic discovery latency. However, more frequent metadata
requests may increase broker overhead.

Only one run per configuration was performed. The experiment
measured isolated Kafka client behavior, not end-to-end CDC
latency. Broker overhead was not measured, and test topic
cleanup was not verified.

### Finding 2 Result

Measurement completed and configuration proposed.

No changes were made to `kafka_consumer.py` because it is
on the critical path.

## 5. Issues and Resolutions

| Issue | Resolution |
|---|---|
| PowerShell Bash/WSL issue | Used Git Bash |
| PowerShell curl alias issue | Used curl.exe |
| Missing replication slot | Registered Debezium connector |
| Missing connection references | Configured local .env |
| Kafka Connect empty reply | Waited for initialization |
| Missing event_log table | Started CDC consumer |
| Missing confluent_kafka | Installed Python dependency |
| Delayed LSN advancement | Repeated slot measurement |
| Missing customers table | Used isolated Kafka tests |

Existing Docker volumes were preserved.

The preliminary experiment on 2026-11-19 was repeated
on 2026-11-20 to complete event log verification.

## 6. Final Results

| Acceptance Criterion | Result |
|---|---|
| Replication slot measurement script | PASS |
| WAL accumulation during pause | PASS |
| LSN advancement after resume | PASS |
| CDC event completeness | 180/180 |
| Missing or duplicate test events | 0 |
| Topic discovery comparison | Completed |
| Metadata refresh recommendation | 5000 ms |
| Critical-path consumer modification | None |

## 7. Deliverables

- `infrastructure/scripts/check_cdc_slot.sh`
- `docs/planning/cdc_slot_lifecycle.md`

Both technical findings were measured successfully.

This report summarizes the execution results. Complete
verbatim terminal transcripts, including both discovery
test commands and detailed batch outputs, are not included
and must be appended to satisfy the full execution-record
requirement.
