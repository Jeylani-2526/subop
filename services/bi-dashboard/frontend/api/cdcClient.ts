// services/bi-dashboard/frontend/api/cdcClient.ts

import type { CDCChangeEvent, CDCConnectorStatus } from "./cdcTypes";
import { CDC_CHANGE_EVENTS, CDC_CONNECTOR_STATUSES } from "./cdcFixtures";

export type { CDCChangeEvent, CDCConnectorStatus };
export type { CDCOperation, ConnectorState } from "./cdcTypes";

// ─── API Fonksiyonları ────────────────────────────────

export async function getCDCEvents(): Promise<CDCChangeEvent[]> {
  // W24'te: GET ${_BASE_URL}/cdc/events
  return Promise.resolve(CDC_CHANGE_EVENTS);
}

export async function getCDCConnectorStatus(
  connectorId: string,
): Promise<CDCConnectorStatus> {
  // W24'te: GET ${_BASE_URL}/cdc/connectors/${connectorId}/status
  const found = CDC_CONNECTOR_STATUSES.find(
    (c) => c.connector_id === connectorId,
  );
  if (!found) throw new Error(`Connector not found: ${connectorId}`);
  return Promise.resolve(found);
}

export async function getAllCDCConnectorStatuses(): Promise<
  CDCConnectorStatus[]
> {
  // W24'te: GET ${_BASE_URL}/cdc/connectors/status
  return Promise.resolve(CDC_CONNECTOR_STATUSES);
}
