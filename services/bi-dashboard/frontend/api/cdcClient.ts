// services/bi-dashboard/frontend/api/cdcClient.ts

import { CDC_CHANGE_EVENTS, CDC_CONNECTOR_STATUSES } from "./cdcFixtures";

const BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";

// ─── Tipler ───────────────────────────────────────────

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

// ─── API Fonksiyonları ────────────────────────────────

export async function getCDCEvents(): Promise<CDCChangeEvent[]> {
  // W24'te canlı API'ye geçilecek — şimdilik fixture
  return Promise.resolve(CDC_CHANGE_EVENTS);
}

export async function getCDCConnectorStatus(
  connectorId: string,
): Promise<CDCConnectorStatus> {
  // W24'te: GET /api/cdc/connectors/{id}/status
  const found = CDC_CONNECTOR_STATUSES.find(
    (c) => c.connector_id === connectorId,
  );
  if (!found) throw new Error(`Connector not found: ${connectorId}`);
  return Promise.resolve(found);
}

export async function getAllCDCConnectorStatuses(): Promise<
  CDCConnectorStatus[]
> {
  // W24'te: GET /api/cdc/connectors/status (toplu)
  return Promise.resolve(CDC_CONNECTOR_STATUSES);
}
