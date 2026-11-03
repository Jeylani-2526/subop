// services/bi-dashboard/frontend/api/cdcTypes.ts

export type CDCOperation = "insert" | "update" | "delete" | "snapshot";

export type ConnectorState =
  | "RUNNING"
  | "PAUSED"
  | "FAILED"
  | "UNASSIGNED"
  | "DESTROYED";

// CDC_SCHEMA_DRIFT_DETECTED: normalizer.py'nin table-scoped halting kararı
// (Design Note Section 3.4). "none" = drift yok; "CDC_SCHEMA_DRIFT_DETECTED"
// = en az bir tablo durduruldu. W27'de endpoint bu değeri döndürmeye başlar;
// o zamana kadar fixture null döndürür ve UI "none" gibi davranır.
export type DriftState = "none" | "CDC_SCHEMA_DRIFT_DETECTED" | null;

export interface CDCChangeEvent {
  op: CDCOperation;
  table: string;
  before: Record<string, unknown> | null;
  after: Record<string, unknown> | null;
  ts_ms: number;
  latency_ms?: number;
}

export interface CDCConnectorStatus {
  connector_id: string;
  connector_name: string;
  state: ConnectorState;
  last_event_ts_ms: number | null;
  lag_ms: number | null;
  // W26'da eklendi — M7W26T6 endpoint'i null döndürür, W27 live swap'tan sonra dolar.
  drift_state: DriftState;
  halted_tables: string[] | null;
}
