import type { CDCChangeEvent, CDCConnectorStatus } from "./cdcTypes";

const DELETE_MS = Date.now() - 95_000; // ~95 s önce

export const CDC_CHANGE_EVENTS: CDCChangeEvent[] = [
  {
    op: "insert",
    table: "cdc_demo.orders",
    before: null,
    after: { id: 7, status: "pending" },
    ts_ms: DELETE_MS - 26_000,
    latency_ms: null, // pre-M8 event
  },
  {
    op: "update",
    table: "cdc_demo.orders",
    before: { id: 7, status: "pending" },
    after: { id: 7, status: "shipped" },
    ts_ms: DELETE_MS - 13_000,
    latency_ms: 812,
  },
  {
    op: "delete",
    table: "cdc_demo.orders",
    before: { id: 7, status: "shipped" },
    after: null,
    ts_ms: DELETE_MS,
    latency_ms: null, // pre-M8 event
  },
];

export const CDC_CONNECTOR_STATUSES: CDCConnectorStatus[] = [
  // Connector 1: latency populated, connect_reachable true
  {
    connector_id: "subop-postgres-cdc",
    connector_name: "subop-postgres-cdc",
    state: "RUNNING",
    task_state: "RUNNING",
    last_event_ts_ms: DELETE_MS,
    lag_ms: 812,
    drift_state: "none",
    halted_tables: ["cdc_demo.orders"],
    events_processed: 3,
    halted: false,
    connect_reachable: true,
    tables: [
      {
        table: "cdc_demo.orders",
        events_processed: 3,
        last_event_ts_ms: DELETE_MS,
        last_lsn: null,
        halted: true,
        halt_error_code: "CDC_UNSUPPORTED_OPERATION",
        halt_reason: "TRUNCATE operation is not supported in CDC mode",
        halted_at: new Date(DELETE_MS - 5_000).toISOString(),
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
    // M8W28T8: populated latency örneği (contract Section 9.4)
    latency: {
      window_size: 100,
      sample_size: 42,
      e2e: { median_ms: 812, p95_ms: 1904.85 },
      capture: { median_ms: 210, p95_ms: 480.5 },
      publish: { median_ms: 95, p95_ms: 201.0 },
      consumer: { median_ms: 310, p95_ms: 720.3 },
      warehouse: { median_ms: 197, p95_ms: 503.0 },
    },
  },
  // Connector 2: latency null, connect_reachable false — her iki durum test edilebilir
  {
    connector_id: "subop-postgres-cdc-secondary",
    connector_name: "subop-postgres-cdc-secondary",
    state: "UNKNOWN",
    task_state: null,
    last_event_ts_ms: null,
    lag_ms: null,
    drift_state: null,
    halted_tables: null,
    events_processed: 0,
    halted: false,
    connect_reachable: false,
    tables: [],
    latency: null,
  },
];
