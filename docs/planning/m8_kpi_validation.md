# Milestone 8 KPI Validation Record

**Project:** SUBOP
**Milestone:** 8 — Metadata-Driven Data Warehouse
**Protocols:** `docs/planning/m8_kickoff_notes.md` Part B item 4 (decided 18 November 2026, before any measurement code existed)

| Section | KPI | Task | Status |
|---|---|---|---|
| 1 | DW schema automation, at least 80% faster than manual | M8W29T3 | Pending |
| 2 | CDC latency under 30 seconds, idle and active | M8W29T4 | **MET in both conditions** |

## 1. DW Schema Automation — M8W29T3

Pending. Recorded by M8W29T3 under Part B item 4b.

## 2. CDC Latency Under 30 Seconds — M8W29T4

**Date:** 23 November 2026, 14:47–14:52 UTC
**Branch:** `develop` at `51b7142`, plus `services/cdc/latency_kpi.py` (this commit)
**Environment:** Local Development — Docker Compose (Windows, Git Bash). The stack is the
one rebuilt from clean volumes for M8W29T11 at about 14:13 UTC the same day
(`docs/planning/cdc_e2e_reproduction.md`). The consumer runs on the host from `develop`,
so Omer's `topic.metadata.refresh.interval.ms = 5000` (M8W29T1) is in effect.
**Result:** MET in both conditions. p95 of t4 − t0 is **649.85 ms idle** and
**648.95 ms active**, against a 30 000 ms threshold. No event exceeded 30 s.

### 2.1 Protocol

As fixed in Part B item 4a. Nothing was changed after measuring.

| Item | Protocol | As run |
|---|---|---|
| Measure | t4 − t0 and the four hops, from `cdc_meta.event_latency` | same |
| Idle | no other writes; one change at a time; the next only after the previous event's t4 is recorded, plus 5 s | `latency_kpi.py idle`: waits for each latency row, then sleeps 5 s |
| Active | background load from `cdc_demo_changes.py` in a loop, one change every 2 s | `latency_kpi.py active` starts `cdc_demo_changes --insert --loop 0 --interval 2`, stops it after the window |
| Sample | 30 counted events per condition | 30 and 30 |
| Warm-up | one recorded, uncounted event | one per condition: the first event of each window (decided 23 November, so both conditions are treated alike) |
| Change type | not specified | INSERT only, both conditions (decided 23 November, so the two compare like for like) |
| Pass rule | p95 of t4 − t0 under 30 000 ms, per condition | same |
| Reported | min, median, p95, max, count over 30 s, unrounded | same; see 2.4 on decimals |
| Clock | single host, skew effectively zero (Design Note Section 2.4) | **amended:** measured before each condition (2.2) |

**Clock amendment.** On this machine the containers run inside Docker Desktop's virtual
machine and the consumer runs on Windows, so t0, t1 and t2 come from the VM's clock and
t3 and t4 from the Windows clock (M8W29T11 Finding 5). The skew was therefore measured
rather than assumed.

### 2.2 Clock Check

`latency_kpi.py` compares the Postgres container's `clock_timestamp()` with the host clock
at the midpoint of each round trip, five times, before each condition.

| Before | Samples: Postgres minus host (ms) | Worst case \|skew\| |
|---|---|---|
| Idle | −11 ±5, −11 ±1, −11 ±1, −11 ±1, −11 ±1 | ≤ 16 ms |
| Active | +3 ±2, +2 ±1, +2 ±1, +2 ±1, +2 ±1 | ≤ 5 ms |

The skew moved by about 13 ms in about three minutes, so the VM clock is adjusted as it runs.
Against a 30 000 ms threshold that is under 0.06%, so it cannot change either verdict.
It is, however, the same size as the **consumer** hop (t3 − t2, 7–21 ms), the one hop that
crosses from the VM clock to the host clock. That hop's figures are only good to about
±16 ms. The e2e figure crosses the clock boundary once and carries the same uncertainty.

### 2.3 Results

| Condition | Hop | n | min | median | p95 | max | over 30 s |
|---|---|---|---|---|---|---|---|
| **Idle** | **e2e (t4 − t0)** | **30** | **94** | **608.50** | **649.85** | **670** | **0** |
| | capture (t1 − t0) | 30 | 11 | 234.00 | 476.55 | 490 | 0 |
| | publish (t2 − t1) | 30 | 35 | 233.50 | 486.20 | 489 | 0 |
| | consumer (t3 − t2) | 30 | 7 | 10.00 | 12.55 | 21 | 0 |
| | warehouse (t4 − t3) | 30 | 6 | 7.00 | 8.00 | 9 | 0 |
| **Active** | **e2e (t4 − t0)** | **30** | **74** | **565.50** | **648.95** | **657** | **0** |
| | capture (t1 − t0) | 30 | 11 | 310.00 | 477.35 | 504 | 0 |
| | publish (t2 − t1) | 30 | 12 | 234.50 | 456.85 | 490 | 0 |
| | consumer (t3 − t2) | 30 | 7 | 10.00 | 12.00 | 13 | 0 |
| | warehouse (t4 − t3) | 30 | 3 | 7.00 | 9.00 | 9 | 0 |

All values in milliseconds.

| Condition | Latency rows | Source orders | Warm-up (not counted) | Verdict |
|---|---|---|---|---|
| Idle | ids 8–38 | 5–35 | id 8, e2e **688 ms** | **MET** (p95 649.85 < 30 000) |
| Active | ids 39–69 | 36–66 | id 39, e2e **666 ms** | **MET** (p95 648.95 < 30 000) |

Latency ids start at 8, not 4: `BIGSERIAL` takes a value even when `ON CONFLICT DO
NOTHING` skips the row, and M8W29T11's two replays tried four rows that already existed.

**Cross-check against the logs.** For the idle warm-up, order 5 was committed at
14:47:48.151 UTC (`cdc_demo_changes`) and the consumer logged it at 17:47:48,839 local
(UTC+3): 688 ms, the value the table holds.

### 2.4 Observations

**Where the time goes.** In both conditions most of the time is on the Debezium side: capture (commit → Debezium processing) and publish (Debezium → Kafka) each
sit near 230–310 ms, with maxima just under 500 ms. That pattern fits Debezium's own
polling and batching intervals rather than load. SUBOP's own part, consumer plus
warehouse write, has medians of about 17 ms together; no single event took more than
21 ms (consumer) or 9 ms (warehouse).

**Idle versus Week 23's 56 seconds.** The protocol's idle condition spaces changes about
6 s apart, a much shorter quiet period than the one behind Week 23's single 56-second
observation. This run does not test a database that has been quiet for many minutes.
It does contain one such data point: the idle warm-up came after about 16.5 minutes with
no writes (the last change was M8W29T11's DELETE at 14:31:15 UTC) and took **688 ms**.
That is one observation, not counted and not a KPI result. It suggests the 56-second case
does not reproduce on this stack, but it does not prove it. Not needed for the KPI;
recorded for M9 as an optional long-idle check.

**Decimals.** Every input is a whole number of milliseconds, and `percentile_cont` at 0.5
and 0.95 over 30 values lands on exact hundredths. The raw output showed float noise such
as `476.54999999999995`; the tables show `476.55`, which is the exact value, not a rounding.

**Report formatting fixed in this commit.** The first run's printed table let wide float
values run into the next column (raw output in 2.6). The values were unaffected; the
printer now formats each column separately, with a test.

### 2.5 Commands and SQL

```bash
# terminal B, left running
python -m services.cdc.kafka_consumer

# terminal A
python -m services.cdc.latency_kpi idle
python -m services.cdc.latency_kpi active

# re-print either window at any time
python -m services.cdc.latency_kpi report 8 38
python -m services.cdc.latency_kpi report 39 69
```

The report query (`python -m services.cdc.latency_kpi sql`), run with
`table_name = 'cdc_demo.orders'`, `op = 'insert'` and `skip = 1`:

```sql
WITH w AS (
    SELECT id, t0_ms, t1_ms, t2_ms, t3_ms, t4_ms
    FROM cdc_meta.event_latency
    WHERE id BETWEEN %(first)s AND %(last)s
      AND table_name = %(table_name)s AND op = %(op)s
    ORDER BY id
    OFFSET %(skip)s
), h AS (
    SELECT 'e2e' AS hop, t4_ms - t0_ms AS ms FROM w
    UNION ALL SELECT 'capture',   t1_ms - t0_ms FROM w
    UNION ALL SELECT 'publish',   t2_ms - t1_ms FROM w
    UNION ALL SELECT 'consumer',  t3_ms - t2_ms FROM w
    UNION ALL SELECT 'warehouse', t4_ms - t3_ms FROM w
)
SELECT hop,
       count(*) AS n,
       min(ms) AS min_ms,
       percentile_cont(0.5)  WITHIN GROUP (ORDER BY ms) AS median_ms,
       percentile_cont(0.95) WITHIN GROUP (ORDER BY ms) AS p95_ms,
       max(ms) AS max_ms,
       count(*) FILTER (WHERE ms > 30000) AS over_30s
FROM h
GROUP BY hop
```

### 2.6 Raw Output

Report blocks as printed by the first run, verbatim (before the formatting fix):

```
idle: ids 8..38
  warm-up (not counted): id 8, e2e 688 ms
  hop          n       min      median         p95       max  >30s
  e2e         30        94       608.5      649.85       670     0
  capture     30        11       234.0476.54999999999995       490     0
  publish     30        35       233.5       486.2       489     0
  consumer    30         7        10.012.549999999999997        21     0
  warehouse   30         6         7.0         8.0         9     0
  KPI (p95 of e2e < 30000 ms): MET

active: ids 39..69
  warm-up (not counted): id 39, e2e 666 ms
  hop          n       min      median         p95       max  >30s
  e2e         30        74       565.5648.9499999999999       657     0
  capture     30        11       310.0477.34999999999997       504     0
  publish     30        12       234.5456.8499999999999       490     0
  consumer    30         7        10.0        12.0        13     0
  warehouse   30         3         7.0         9.0         9     0
  KPI (p95 of e2e < 30000 ms): MET
```

Consumer log (terminal B), first and last lines of each condition:

```
2026-11-23 17:47:29,132 INFO subscribed to ^subop-postgres-cdc\.cdc_demo\..* as group subop-cdc-consumer
2026-11-23 17:47:48,839 INFO insert cdc_demo.orders id=5 ts_ms=1795445268151 lsn=27307232 -> warehouse
...
2026-11-23 17:50:46,231 INFO insert cdc_demo.orders id=35 ts_ms=1795445445643 lsn=27441952 -> warehouse
2026-11-23 17:50:49,738 INFO insert cdc_demo.orders id=36 ts_ms=1795445449073 lsn=27456072 -> warehouse
...
2026-11-23 17:51:49,896 INFO insert cdc_demo.orders id=66 ts_ms=1795445509378 lsn=27580112 -> warehouse
```

All 62 orders (5–66) reached the warehouse, one log line each, with no `latency not
recorded` warning. The active load produced exactly 31 orders and stopped with the window:
the log ends at order 66.

### 2.7 Conclusion

Under the protocol fixed on 18 November, CDC latency from source commit to warehouse
commit is **MET with a wide margin in both conditions**: p95 649.85 ms idle and
648.95 ms active, about 46 times under the 30-second target, with no event over 30 s.
Goal G4's latency criterion is met for PostgreSQL. MySQL CDC, the other half of G4,
remains carried to M11.
