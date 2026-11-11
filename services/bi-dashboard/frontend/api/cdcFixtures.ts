// services/bi-dashboard/frontend/api/cdcFixtures.ts
// W27 live swap'a kadar bu fixture'lar kullanılır.
// cdcClient.ts'teki "// W24'te:" markerları W27T6'da kaldırılacak.

import type { CDCChangeEvent, CDCConnectorStatus } from "./cdcTypes";

const DELETE_MS = Date.now() - 95_000; // ~95 s önce

export const CDC_CHANGE_EVENTS: CDCChangeEvent[] = [
  {
    op: "insert",
    table: "cdc_demo.orders",
    before: null,
    after: { id: 7, status: "pending" },
    ts_ms: DELETE_MS - 26_000,
    latency_ms: null,
  },
  {
    op: "update",
    table: "cdc_demo.orders",
    before: { id: 7, status: "pending" },
    after: { id: 7, status: "shipped" },
    ts_ms: DELETE_MS - 13_000,
    latency_ms: null,
  },
  {
    op: "delete",
    table: "cdc_demo.orders",
    before: { id: 7, status: "shipped" },
    after: null,
    ts_ms: DELETE_MS,
    latency_ms: null,
  },
];

export const CDC_CONNECTOR_STATUSES: CDCConnectorStatus[] = [
  {
    connector_id: "subop-postgres-cdc",
    connector_name: "subop-postgres-cdc",
    state: "RUNNING",
    task_state: "RUNNING",
    last_event_ts_ms: DELETE_MS,
    lag_ms: null,
    drift_state: "none",
    halted_tables: [],
    events_processed: 3,
    halted: false,
    tables: [
      {
        table: "cdc_demo.orders",
        events_processed: 3,
        last_event_ts_ms: DELETE_MS,
        last_lsn: null,
        halted: false,
        halt_error_code: null,
        halt_reason: null,
        halted_at: null,
      },
      {
        table: "cdc_demo.customers",
        events_processed: 0,
        last_event_ts_ms: null,
        last_lsn: null,
        halted: false,
        halt_error_code: null,
        halt_reason: null,
        halted_at: null,
      },
    ],
    latency: null,
  },
];
