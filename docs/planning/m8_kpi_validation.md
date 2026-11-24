# Milestone 8 KPI Validation Record

**Project:** SUBOP
**Milestone:** 8 — Metadata-Driven Data Warehouse
**Protocols:** `docs/planning/m8_kickoff_notes.md` Part B item 4 (decided 18 November 2026, before any measurement code existed)

| Section | KPI | Task | Status |
|---|---|---|---|
| 1 | DW schema automation, at least 80% faster than manual | M8W29T3 | **NOT MET** (re-measurement carried to M9) |
| 2 | CDC latency under 30 seconds, idle and active | M8W29T4 | **MET in both conditions** |

## 1. DW Schema Automation — M8W29T3

**Date:** 23–24 November 2026
**Branch:** `M8W29T3`; target spec `docs/planning/m8_kpi_schema_spec.md`, committed in
`40ca1ad` on 23 November at 16:10 UTC, before any attempt
**Environment:** Local Development — Docker Compose (Windows, Git Bash)
**Result:** **NOT MET.** Both halves built the same schema (equality check **IDENTICAL**),
but the generated half took at least **0.327** of the manual half's time, against a pass
rule of 0.20. The timing record has gaps (1.3); the verdict holds under every reading
the evidence allows.

### 1.1 Protocol and What Changed

| Item | Part B item 4b and spec | As run |
|---|---|---|
| Spec | one written target spec, committed first | `kpi_shipments_star`: 4 tables, 26 columns; committed before any attempt |
| Who | Abdalla does both halves | same |
| Order | generated half first | same |
| Start point | rule 5 (decided 23 Nov): both halves start from an empty file | **changed 24 Nov, about 08:23 UTC**, after attempt 2 showed the definition format was unknown: **both halves start from the demo template**, the generated half from `demo_orders_star.json`, the manual half from the demo DDL (`HAND_DDL` in `tests/test_schema_compare.py`) |
| Timing | `date -u` immediately before the first keystroke and after the successful run | **gaps:** no `date` at the start of the final generated half, none at the end of the manual half (1.3) |
| Equality check | tables, columns, types, nullability, primary and foreign keys | **IDENTICAL** (1.4) |
| Corrections | rule 4: clock resumes for fixes found by the check | none needed; the JSON was also reviewed against the spec's compliance fields after the clock stopped: correct |
| Pass rule | generated ≤ 20% of manual | not met |

### 1.2 Timeline (UTC)

| When | What | Evidence |
|---|---|---|
| 23 Nov, about 16:20 | **Attempt 1:** the spec's text pasted into the JSON file; the generator refused it twice (`(root): invalid JSON`). Abandoned. | terminal screenshot; no `date` line kept |
| 24 Nov, 07:14:33.196 → 07:23:03.779 | **Attempt 2:** from an empty file, 8 min 30.583 s. Abandoned: the definition format was not known. | `date` lines |
| 07:23 → about 08:25 | Untimed: the format explained and the demo definition read; the demo copied into the file and partly edited before the rule change (a half-edited file is visible at 08:14). | chat record, screenshot |
| about 08:23 | Rule 5 changed (1.1). | chat record |
| about 08:25 → 08:48:14.482 | **Generated half:** the definition edited from the template; generator run at 08:47:31.160 printed `kpi_shipments_star v1: created`. **About 23 min 14 s.** The start is Abdalla's account, not a `date` line. | `date` lines at 08:47:31.160 and 08:48:14.482; generator output |
| by 09:11 | The manual DDL file holds the demo template, not yet edited. | file shared at 09:11 |
| 10:17:28.493 → by 10:21 | `date` taken; the manual DDL run without errors; the equality check run. No `date` after the run; the result was reported at 10:21. | `date` line, psql and check output |

### 1.3 Timing Gaps and the Verdict

Two `date` lines are missing, so the ratio cannot be computed to the millisecond. The
evidence still bounds it:

| Half | Known | Duration used |
|---|---|---|
| Generated | start about 08:25 (Abdalla's account); end 08:48:14.482 | **1 394.482 s** (about 23 min 14 s) |
| Manual | the template was still unedited at 09:11; the check had passed by 10:21:59 | **at most 4 259 s** (70 min 59 s); Abdalla's recollection of editing "between 10:30 and 12:00" local time does not fit the unedited file at 12:11 local, so the evidence bound is used |

The **lowest possible ratio** is 1 394.482 / 4 259 = **0.327**, reached only if the
manual half used the whole window. Taken at face value (editing after the 10:17:28 line,
about 3.5 minutes), the ratio is above 6. **Every reading is above 0.20: NOT MET.**

The two gaps are a process lesson for the re-measurement: a second person checks that
both `date` lines exist for each half before the run counts (1.7).

### 1.4 Equality Check

```
$ python -m services.warehouse.schema_compare dw dw_manual fact_shipments dim_carrier dim_depot dim_ship_date
Compared dw with dw_manual: fact_shipments, dim_carrier, dim_depot, dim_ship_date
Checked: tables, columns, types, nullability, primary keys, foreign keys
RESULT: IDENTICAL
```

Generator output (generated half):

```
kpi_shipments_star v1: created
  dw.fact_shipments: 9 columns
  dw.dim_carrier: 3 columns
  dw.dim_depot: 7 columns
  dw.dim_ship_date: 7 columns
```

The manual DDL ran inside `psql -1`; its own `BEGIN`/`COMMIT` produced two harmless
warnings (`there is already a transaction in progress`, `there is no transaction in
progress`). Both halves are committed as evidence:
`services/warehouse/definitions/kpi_shipments_star.json` and
`docs/planning/m8_kpi_manual_ddl.sql`.

### 1.5 Why It Was Not Met

1. **The definition still had to spell every column and type.** For this small star the
   definition (66 lines) was longer than the DDL (46 lines). The generator applied the
   conventions (keys, SCD columns, date columns, foreign keys) but saved little typing.
2. **The format was not documented.** Learning it fell inside the measurement: two
   attempts were abandoned before the format was known.
3. **The schema is narrow.** At about 25 columns, the DDL a person types is short, so
   there is little for automation to save (1.6).

### 1.6 What Was Built in Response (this branch)

- **Columns read from the source** (`services/warehouse/source_catalog.py`): a
  definition may leave `"columns"` out, or list names only, and the generator reads
  names and native types from the source database, as Goal G5 states ("generated from
  source metadata"). PostgreSQL sources today. A test proves a definition without types
  generates a schema identical to one with every type.
- **The definition format is documented** (`docs/planning/warehouse_definition_guide.md`).

Measured on a draft second schema of the same size (not a KPI run), the typing this saves
is about 21% (786 against 996 characters, spaces excluded). That is far from the 80%
target at this width. The saving grows with table width: each further source column adds
about 25 characters of DDL and none to a definition that reads its columns from the
source. A fair re-measurement therefore needs a realistic-width schema, agreed before it
is run, not a spec resized after a failed run.

### 1.7 Resolution Plan

| Item | Owner | Target |
|---|---|---|
| DW schema automation KPI carried to M9, recorded here as not met in M8 | Abdalla | M9 window (by 28 December 2026) |
| Propose the re-measurement to Emrah in the M8 report, before any re-run: a realistic-width spec (source tables as wide as a real source system), both halves from empty files, the definition guide read beforehand | Abdalla | M8 report, 30 November |
| A second person (Mert, verification and control) checks the `date` lines for each half during the re-run | Mert | the re-run |
| Read columns from MySQL and MSSQL sources too (PostgreSQL only today) | Abdalla | M9 |

### 1.8 Conclusion

Under the protocol fixed on 18 November, with the start-point rule changed openly on
24 November, the DW schema automation KPI is **NOT MET** in M8: generated time was at
least 0.327 of manual time. The generator's correctness is proven (identical schemas),
and the change Goal G5 calls for, generation from source metadata, is now built. Whether
it meets the 80% target is left to a re-measurement agreed in advance for M9.

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
