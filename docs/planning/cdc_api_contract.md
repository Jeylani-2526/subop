# CDC API Contract

**Task:** M7W26T6 · **Owner:** Abdalla · **For:** Beyza (M7W26T7, M7W27T6, M7W27T7)
**Status:** Implemented on `abdullah/M7W26T1-6` · **Date:** 3 November 2026

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
  events_processed: number;
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

  // M7W26T6 additions
  task_state: ConnectorState | null; // null = connector RUNNING but no task: reads nothing
  events_processed: number;          // sum across tables
  halted: boolean;                   // true if any table is halted
  tables: CDCTableStatus[];          // every table the connector captures
  latency: null;                     // reserved for M8's five measurement points
}
```

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

| What the UI should show | Condition |
|---|---|
| Table halted, needs manual resolution | `tables[i].halted === true` — show `table`, `halt_error_code`, `halt_reason`, `halted_at` |
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

## 6. Latency — null on purpose

`lag_ms`, `latency` and every event's `latency_ms` are `null` until M8's
instrumentation (`latency_store.py`, the five points t0–t4 of CDC Design Note
Section 2). They are present now so the response shape doesn't change when
they fill in. Keep the existing `!= null` checks and the "—" fallback. The
HomePage CDC Latency card stays on its dash, per M7W27T7.

## 7. Deviations recorded

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
