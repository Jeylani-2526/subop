// services/bi-dashboard/frontend/api/cdcTypes.ts

export type CDCOperation = "insert" | "update" | "delete" | "snapshot";

export type ConnectorState =
  | "RUNNING"
  | "PAUSED"
  | "FAILED"
  | "UNASSIGNED"
  | "DESTROYED";

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
}
