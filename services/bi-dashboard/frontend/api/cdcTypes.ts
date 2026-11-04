// services/bi-dashboard/frontend/api/cdcTypes.ts

export type CDCOperation = "insert" | "update" | "delete" | "snapshot";

export type ConnectorState =
  | "RUNNING"
  | "PAUSED"
  | "FAILED"
  | "UNASSIGNED"
  | "DESTROYED"
  // M7W26T6: Kafka Connect bu iki durumu da dönebilir (contract Section 2)
  | "RESTARTING"
  | "STOPPED";

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
  latency_ms?: number | null;
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

export interface CDCConnectorStatus {
  connector_id: string;
  connector_name: string;
  state: ConnectorState;
  last_event_ts_ms: number | null;
  lag_ms: number | null; // M8'e kadar daima null

  // W26'da eklendi (M7W26T7) — endpoint tam olarak bu isimlerle dönüyor
  drift_state: DriftState; // "none" | "CDC_SCHEMA_DRIFT_DETECTED"; API'den asla null gelmiyor
  halted_tables: string[] | null; // HERHANGİ bir nedenle durdurulan tablolar; [] = yok

  // M7W26T6 eklemeleri (contract Section 2)
  task_state: ConnectorState | null; // null = connector RUNNING ama task yok → hiçbir şey okunmuyor
  events_processed: number; // tablolar toplamı
  halted: boolean; // herhangi bir tablo durduysa true
  tables: CDCTableStatus[]; // connector'ın yakaladığı her tablo
  latency: null; // M8'in beş ölçüm noktası için rezerve
}
