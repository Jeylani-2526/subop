export type CDCOperation = "insert" | "update" | "delete" | "snapshot";

export type ConnectorState =
  | "RUNNING"
  | "PAUSED"
  | "FAILED"
  | "UNASSIGNED"
  | "DESTROYED"
  // M7W26T6: Kafka Connect bu iki durumu da dönebilir (contract Section 2)
  | "RESTARTING"
  | "STOPPED"
  // M8W28T8: Connect erişilemez durumdayken son bilinen state (contract Section 9 + T5)
  | "UNKNOWN";

export type DriftState = "none" | "CDC_SCHEMA_DRIFT_DETECTED" | null;

export interface CDCChangeEvent {
  op: CDCOperation;
  table: string;
  before: Record<string, unknown> | null;
  after: Record<string, unknown> | null;
  ts_ms: number;
  latency_ms: number | null; // M8W28T8: null → number | null (t4 − t0); null for pre-M8 events
}

// M7W26T6: Tablo başına durum — halt nedenini içerir (contract Section 2)
export interface CDCTableStatus {
  table: string; // "cdc_demo.orders"
  events_processed: number;
  last_event_ts_ms: number | null;
  last_lsn: number | null;
  halted: boolean;
  halt_error_code: string | null; // "CDC_SCHEMA_DRIFT_DETECTED", "CDC_UNSUPPORTED_OPERATION", …
  halt_reason: string | null; // human-readable, detector'dan
  halted_at: string | null; // ISO 8601, ilk halt zamanı
}

// M8W28T8: Latency istatistikleri — contract Section 9.2
export interface CDCLatencyStat {
  median_ms: number; // unrounded: may end in .5
  p95_ms: number; // unrounded; PostgreSQL percentile_cont(0.95)
  max_ms: number; // unrounded; max observed in window
}

// M8W28T8: Beş hop latency özeti — contract Section 9.2
export interface CDCLatency {
  window_size: number; // 100: the window is the last 100 events, newest by t4
  sample_size: number; // events actually in the window, 1–100
  e2e: CDCLatencyStat;
  capture: CDCLatencyStat;
  publish: CDCLatencyStat;
  consumer: CDCLatencyStat;
  warehouse: CDCLatencyStat;
}

export interface CDCConnectorStatus {
  connector_id: string;
  connector_name: string;
  state: ConnectorState;
  last_event_ts_ms: number | null;
  lag_ms: number | null;

  // W26'da eklendi (M7W26T7)
  drift_state: DriftState;
  halted_tables: string[] | null;

  // M7W26T6 eklemeleri (contract Section 2)
  task_state: ConnectorState | null;
  events_processed: number;
  halted: boolean;
  tables: CDCTableStatus[];

  // M8W28T8: null → CDCLatency | null (contract Section 9)
  latency: CDCLatency | null;

  // M8W28T8: Connect erişilemez olduğunda false; sayfada son bilinen halt
  // durumu görünmeye devam eder (contract Section 9, T5)
  connect_reachable: boolean;
}
