# CDC API Contract

**Task:** M7W26T6 · **Owner:** Abdalla · **For:** Beyza (M7W26T7, M7W27T6, M7W27T7)
**Status:** Implemented on `abdullah/M7W26T1-6` · **Date:** 3 November 2026
**Updated:** 18 November 2026, M8W28T4: latency shape added in Section 9, which
replaces Section 6.
Updated again on 18 November 2026, M8W28T5: Section 10 says how the endpoints behave
while Kafka Connect is down.

The three endpoints behind `CDCPage.tsx`, served by `subop-api` on the same base
URL `pipelinesClient.ts` already uses:

```
VITE_API_BASE_URL ?? "http://localhost:8000/api"
```

No second client or base URL is needed.

## 1. What changes in `cdcClient.ts`

| Function | Today (fixture marker) | Live endpoint | Change |
|---|---|---|---|
| `getCDCConnectorStatus(id)` | `GET /cdc/connectors/{id}/status` | `GET /cdc/connectors/{id}/status` | none |
| `getAllCDCConnectorStatuses()` | `GET /cdc/connectors/status` | **`GET /cdc/connectors`** | **path** — follows Architecture Section 6 |
| `getCDCEvents()` | `GET /cdc/events` | `GET /cdc/events?limit=50` | none (`limit` optional) |

The connector id is the Kafka Connect connector name: **`subop-postgres-cdc`**.

## 2. Types — additions only

`CDCChangeEvent` is unchanged. `CDCConnectorStatus` keeps all five existing
fields with the same names and gains new ones. Nothing is renamed or removed.

```ts
export interface CDCTableStatus {
  table: string;                    // "cdc_demo.orders"
  events_processed: number;         // distinct change events; redeliveries not counted (M7W27T1 F4)
  last_event_ts_ms: number | null;
  last_lsn: number | null;
  halted: boolean;
  halt_error_code: string | null;   // "CDC_SCHEMA_DRIFT_DETECTED", ...
  halt_reason: string | null;       // human-readable, from the detector
  halted_at: string | null;         // ISO 8601, first time the table halted
}

export interface CDCConnectorStatus {
  connector_id: string;
  connector_name: string;
  state: ConnectorState;            // live from Kafka Connect
  last_event_ts_ms: number | null;  // latest across tables
  lag_ms: number | null;            // always null until M8

  // Added by M7W26T7 (Beyza, 3 Nov) — served exactly as declared
  drift_state: DriftState;          // "none" | "CDC_SCHEMA_DRIFT_DETECTED"; never null from the API
  halted_tables: string[] | null;   // every halted table, for ANY reason; [] when none

  // M7W26T6 additions
  task_state: ConnectorState | null; // null = connector RUNNING but no task: reads nothing
  events_processed: number;          // sum across tables
  halted: boolean;                   // true if any table is halted
  tables: CDCTableStatus[];          // every table the connector captures
  latency: null;                     // reserved for M8's five measurement points
}
```

**`halted_tables` and `drift_state` measure different things.** A table can halt
for a reason other than drift: a TRUNCATE (`CDC_UNSUPPORTED_OPERATION`) or a
warehouse write failure. Such a table **is** in `halted_tables`, but
`drift_state` stays `"none"`. For the reason, read
`tables[i].halt_error_code` / `halt_reason`.

`ConnectorState` may need widening: Kafka Connect can also report
`"RESTARTING"` and `"STOPPED"`, which the current union lacks.

## 3. Example responses

`GET /api/cdc/connectors/subop-postgres-cdc/status` with `orders` halted:

```json
{
  "connector_id": "subop-postgres-cdc",
  "connector_name": "subop-postgres-cdc",
  "state": "RUNNING",
  "task_state": "RUNNING",
  "last_event_ts_ms": 1793723713533,
  "events_processed": 1,
  "halted": true,
  "tables": [
    {
      "table": "cdc_demo.orders",
      "events_processed": 1,
      "last_event_ts_ms": 1793723713533,
      "last_lsn": 27052864,
      "halted": true,
      "halt_error_code": "CDC_SCHEMA_DRIFT_DETECTED",
      "halt_reason": "cdc_demo.orders: columns added ['discount']",
      "halted_at": "2026-11-03T19:44:30.642446+03:00"
    },
    {
      "table": "cdc_demo.customers",
      "events_processed": 0,
      "last_event_ts_ms": null,
      "last_lsn": null,
      "halted": false,
      "halt_error_code": null,
      "halt_reason": null,
      "halted_at": null
    }
  ],
  "halted_tables": ["cdc_demo.orders"],
  "drift_state": "CDC_SCHEMA_DRIFT_DETECTED",
  "lag_ms": null,
  "latency": null
}
```

`GET /api/cdc/connectors` returns an array of the same object.

`GET /api/cdc/events?limit=3`, newest first:

```json
[
  { "op": "delete", "table": "cdc_demo.orders", "before": { "id": 7, "status": "shipped" }, "after": null, "ts_ms": 1793723713533, "latency_ms": null },
  { "op": "update", "table": "cdc_demo.orders", "before": { "id": 7, "status": "pending" }, "after": { "id": 7, "status": "shipped" }, "ts_ms": 1793723713520, "latency_ms": null },
  { "op": "insert", "table": "cdc_demo.orders", "before": null, "after": { "id": 7, "status": "pending" }, "ts_ms": 1793723713507, "latency_ms": null }
]
```

`limit` is 1–500, default 50. A redelivered event appears once.

## 4. Building the halted state (M7W26T7)

A halt is **per table**, not per connector. The connector stays `RUNNING` and
the other tables keep flowing, so the page must read `tables[].halted` and not
infer anything from `state`.

The merged `HaltedTablesBanner` reads `halted_tables`, which works as served.
One gap: the banner always shows the drift reason (`cdc_drift_reason`), which
is wrong for a TRUNCATE or write-failure halt. Show the drift text only when
`drift_state === "CDC_SCHEMA_DRIFT_DETECTED"`. Otherwise show the table's
`halt_error_code`.

| What the UI should show | Condition |
|---|---|
| Table halted, needs manual resolution | `tables[i].halted === true` (or the name is in `halted_tables`) — show `table`, `halt_error_code`, `halt_reason`, `halted_at` |
| Connector registered, no events yet | `events_processed === 0` and nothing halted |
| Connector running but capturing nothing | `state === "RUNNING"` and `task_state === null` |

Manual resolution is an operator action on the consumer, not something the UI
triggers: `python -m services.cdc.kafka_consumer --reset-table cdc_demo.orders`.

M7W27T1 produces a real halt with `ALTER TABLE` on `orders`, which is when
M7W27T7 confirms this state against live data.

## 5. Errors

Same four-field envelope as the pipeline routes:

| Status | `error_code` | When | `retryable` |
|---|---|---|---|
| 404 | `CDC_CONNECTOR_NOT_FOUND` | unknown connector id | false |
| 503 | `CDC_CONNECT_UNAVAILABLE` | Kafka Connect not reachable | true |
| 503 | connector `error_code` | state database not reachable | as reported |
| 422 | FastAPI validation | `limit` outside 1–500 | — |

A 503 means the state is unknown. Show it as unknown; don't fall back to a
cached or fixture value.

## 6. Latency — null on purpose (M7; replaced by Section 9)

`lag_ms`, `latency` and every event's `latency_ms` are `null` until M8's
instrumentation (`latency_store.py`, the five points t0–t4 of CDC Design Note
Section 2). They are present now so the response shape doesn't change when
they fill in. Keep the existing `!= null` checks and the "—" fallback. The
HomePage CDC Latency card stays on its dash, per M7W27T7.

## 7. Reconciliation with the M7W26T7 commit (`98812b7`, 3 Nov 10:17)

Beyza's T7/T8 commit predates this contract, so it declared its own fields.
Reconciled on 4 November:

- **Kept as declared:** the endpoint serves `drift_state` and `halted_tables`,
  so the merged UI needs no rework.
- **Build is broken on `develop`.** `cdcTypes.ts` made both fields required, but
  `cdcFixtures.ts` wasn't updated, so `tsc -b` (and so `npm run build`) fails
  with TS2739. It passed at `a200c0a`. Verified fix, two lines in the fixture:
  ```ts
  drift_state: "none",
  halted_tables: [],
  ```
  CI didn't catch it because no workflow builds the frontend.
- **Banner reason:** see Section 4. Not every halt is drift.

## 8. Deviations recorded

- **Location.** The plan named `services/bi-dashboard/` for this task. That
  directory holds only an M9 README, and the dashboard already calls `subop-api`
  on port 8000. The routes live in `services/cdc/api.py`, mounted into
  `services/etl_engine/api/app.py`. Decided 3 November.
- **`GET /api/cdc/events` is an addition to Architecture Section 6**, which
  lists the connector routes but no event feed. It's needed because the
  warehouse keeps only each row's latest state, so the history comes from
  `cdc_meta.event_log`, written by the consumer. Architecture Section 6 needs a
  one-line amendment.
- The list path follows the architecture (`/cdc/connectors`), not the fixture
  marker (`/cdc/connectors/status`).

## 9. Latency — M8 (M8W28T4)

**For:** Beyza (M8W28T8, M8W29T8) · **Date:** 18 November 2026 · Written before the code.

From M8W28T4 on, the latency fields carry real values. Field names don't change: only
their types widen from `null` to `T | null`.

### 9.1 Where the numbers come from

The consumer records the five raw timestamps of CDC Design Note Section 2 for every
change event whose warehouse write commits. They are stored as integer milliseconds (UTC)
in `cdc_meta.event_latency`:

| Point | Read from | Meaning |
|---|---|---|
| t0 | `payload.source.ts_ms` | Source commit |
| t1 | top-level `payload.ts_ms` | Debezium processed it |
| t2 | Kafka message timestamp | Published to the topic |
| t3 | consumer clock when `poll()` returns | Consumer picked it up |
| t4 | consumer clock after the upsert commits | In the warehouse |

The row's unique key matches `cdc_meta.event_log`, so a redelivered event adds nothing. An
event that halts, or whose write fails, never reaches t4 and has no latency row.

**Persistent, not in-memory.** The consumer and `subop-api` are separate processes, so an
in-memory store could never reach the endpoints. This is the same reason the 3 November
decision moved CDC state into Postgres. It is recorded as an amendment in the Design Note.

Intervals are computed when read, never stored:

| Key | Interval | UI tile (`CDCPage.tsx`) |
|---|---|---|
| `e2e` | t4 − t0 | `cdc_hop_e2e`. **The KPI interval** |
| `capture` | t1 − t0 | `cdc_hop_capture` |
| `publish` | t2 − t1 | `cdc_hop_publish` |
| `consumer` | t3 − t2 | `cdc_hop_consumer` |
| `warehouse` | t4 − t3 | `cdc_hop_warehouse` |

### 9.2 Types — what changes in `cdcTypes.ts`

```ts
export interface CDCLatencyStat {
  median_ms: number;   // unrounded: may end in .5
  p95_ms: number;      // unrounded; PostgreSQL percentile_cont(0.95)
  max_ms: number;
}

export interface CDCLatency {
  window_size: number;        // 100: the window is the last 100 events, newest by t4
  sample_size: number;        // events actually in the window, 1–100
  e2e: CDCLatencyStat;
  capture: CDCLatencyStat;
  publish: CDCLatencyStat;
  consumer: CDCLatencyStat;
  warehouse: CDCLatencyStat;
}

// CDCConnectorStatus — two fields widen, nothing else changes
lag_ms: number | null;        // e2e (t4 − t0) of the connector's most recent event
latency: CDCLatency | null;   // null until the connector has one instrumented event

// CDCChangeEvent
latency_ms: number | null;    // this event's t4 − t0; null for events from before M8
```

And in `pipelinesClient.ts`, where `cdc_latency_ms` is already declared:

```ts
cdc_latency_ms?: number | null;  // e2e p95 over the last 100 events, every connector
```

### 9.3 Rules

| Rule | Detail |
|---|---|
| Window | The last 100 instrumented events, newest by t4. For a connector, only its own tables (`table.include.list`). For `/api/kpis`, every table |
| Why a count, not a time window | The value stays meaningful when the database is idle (decided 18 November). A 15-minute window would go null whenever nothing changed |
| `lag_ms` | t4 − t0 of the most recent event: "how long did the latest change take?" It doesn't grow while the database is idle (decided 18 November) |
| `null` | `latency` is null and `lag_ms` is null when no instrumented event exists yet. When `latency` is not null, every stat inside it is a number |
| Unrounded | Values are passed through as computed. Medians and p95 can be fractional |
| Small or negative hops | All five clocks share one host under Compose (Design Note Section 2.4), but millisecond timestamps from different processes can make a hop 0 or slightly negative. These values are reported as they are, never clamped |
| Same headline as the KPI | The KPI pass rule is p95 of t4 − t0 (Part B item 4a). So `cdc_latency_ms` is that p95, and the strip's headline per hop is its `p95_ms` |

### 9.4 Example responses

`GET /api/cdc/connectors/subop-postgres-cdc/status` (only the changed fields):

```json
{
  "lag_ms": 812,
  "latency": {
    "window_size": 100,
    "sample_size": 42,
    "e2e": { "median_ms": 734.5, "p95_ms": 1904.85, "max_ms": 2311 },
    "capture": { "median_ms": 401, "p95_ms": 1450.2, "max_ms": 1702 },
    "publish": { "median_ms": 12, "p95_ms": 31.95, "max_ms": 44 },
    "consumer": { "median_ms": 288.5, "p95_ms": 402.9, "max_ms": 517 },
    "warehouse": { "median_ms": 9, "p95_ms": 21, "max_ms": 38 }
  }
}
```

`GET /api/cdc/events?limit=2`:

```json
[
  { "op": "update", "table": "cdc_demo.orders", "before": { "id": 7, "status": "pending" }, "after": { "id": 7, "status": "shipped" }, "ts_ms": 1795001010520, "latency_ms": 812 },
  { "op": "insert", "table": "cdc_demo.orders", "before": null, "after": { "id": 7, "status": "pending" }, "ts_ms": 1795001003507, "latency_ms": null }
]
```

The second event is from before instrumentation, so its `latency_ms` is null.

`GET /api/kpis` (only the new field):

```json
{ "cdc_latency_ms": 1904.85 }
```

### 9.5 What the UI should show

| Where | What | Fallback |
|---|---|---|
| Latency strip, five tiles | `latency[key].p95_ms`, labelled as p95. `median_ms` can be a secondary line | "—" while `latency` is null |
| Feed column | `latency_ms` | "—" when null |
| Connector row, Lag | `lag_ms` | "—" when null |
| HomePage CDC Latency card | `cdc_latency_ms`. Success colour under 30 000 ms, danger at 30 000 ms or above (M8W29T8) | "—" when null |

Fixtures: one connector with a populated `latency` (as in 9.4) and one with `latency: null`
and `lag_ms: null`, so both states stay testable (M8W28T8).

## 10. While Kafka Connect is down — M8W28T5

**For:** Beyza (M8W28T8) · **Date:** 18 November 2026 · Closes the M7 checklist's
"halt hidden while Connect is down" item.

Until now, an unreachable Connect turned the **whole** response into a 503, and the
page lost the halt states `cdc_meta.table_state` still holds. Now the connector
endpoints fall back to that stored state.

### 10.1 What changes in the response

```ts
// CDCConnectorStatus
state: "RUNNING" | "PAUSED" | "FAILED" | "UNASSIGNED" | "UNKNOWN";  // UNKNOWN is new
task_state: string | null;      // always null when state is UNKNOWN
connect_reachable: boolean;     // new, always present: true on the live path
```

With `connect_reachable: false`:

| Field | Value |
|---|---|
| `state` | `"UNKNOWN"`, because Connect could not be asked |
| `task_state` | `null` |
| `tables` | Every table in `cdc_meta.table_state`, sorted by name. The live path uses the connector's `table.include.list`, which only Connect knows |
| `halted`, `halted_tables`, `drift_state`, each table's halt fields | From `cdc_meta`, exactly as stored: **the last known state** |
| `events_processed`, `last_event_ts_ms`, `latency`, `lag_ms` | From `cdc_meta`, as on the live path |

### 10.2 Which connectors the list returns

`GET /api/cdc/connectors` normally asks Connect for the names. While Connect is down it
uses the `CDC_CONNECTOR_NAMES` setting (comma-separated, default `subop-postgres-cdc`;
decided 18 November).

### 10.3 When it is still a 503

| Case | Response |
|---|---|
| Connect down and `cdc_meta` holds no table state (the consumer has never run) | 503 `CDC_CONNECT_UNAVAILABLE`, `retryable: true`, as before |
| Connect down and the requested connector is not in `CDC_CONNECTOR_NAMES` | 503 `CDC_CONNECT_UNAVAILABLE`: without Connect, it cannot be confirmed to exist |
| Connect up, connector unknown | 404 `CDC_CONNECTOR_NOT_FOUND`, unchanged |

`GET /api/cdc/events` never depended on Connect, so it is unchanged.

### 10.4 What the UI should show

| Condition | Show |
|---|---|
| `connect_reachable === false` | The existing Connect-unavailable warning, **and** the halt banner if `halted_tables` is not empty, labelled as the last known state |
| `state === "UNKNOWN"` | A neutral status label: neither healthy nor failed |

Fixtures: one connector with `connect_reachable: false`, `state: "UNKNOWN"` and a halted
table, so the banner can be checked without stopping Connect (M8W28T8).
