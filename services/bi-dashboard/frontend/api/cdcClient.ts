// services/bi-dashboard/frontend/api/cdcClient.ts

import type { CDCChangeEvent, CDCConnectorStatus } from "./cdcTypes";

export type { CDCChangeEvent, CDCConnectorStatus };
export type { CDCOperation, ConnectorState } from "./cdcTypes";

const BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";

// ─── Hata tipleri ─────────────────────────────────────

export class CDCConnectUnavailableError extends Error {
  constructor() {
    super("CDC_CONNECT_UNAVAILABLE");
    this.name = "CDCConnectUnavailableError";
  }
}

// ─── Yardımcı ─────────────────────────────────────────

async function cdcFetch<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`);
  if (res.status === 503) {
    throw new CDCConnectUnavailableError();
  }
  if (!res.ok) {
    throw new Error(`CDC API error: ${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

// ─── API Fonksiyonları ────────────────────────────────

export async function getCDCEvents(): Promise<CDCChangeEvent[]> {
  return cdcFetch<CDCChangeEvent[]>("/cdc/events");
}

export async function getCDCConnectorStatus(
  connectorId: string,
): Promise<CDCConnectorStatus> {
  return cdcFetch<CDCConnectorStatus>(`/cdc/connectors/${connectorId}/status`);
}

export async function getAllCDCConnectorStatuses(): Promise<
  CDCConnectorStatus[]
> {
  return cdcFetch<CDCConnectorStatus[]>("/cdc/connectors");
}