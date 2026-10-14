// services/bi-dashboard/frontend/api/cdcFixtures.ts
// W23 fixture modülü — W24'te kaldırılır, cdcClient.ts live API'ye geçer

import type { CDCChangeEvent, CDCConnectorStatus } from "./cdcTypes";

export const CDC_CHANGE_EVENTS: CDCChangeEvent[] = [
  {
    op: "insert",
    table: "public.orders",
    before: null,
    after: { id: 1042, customer_id: 77, total: 249.9, status: "pending" },
    ts_ms: Date.now() - 4000,
    latency_ms: 312,
  },
  {
    op: "update",
    table: "public.orders",
    before: { id: 1041, status: "pending" },
    after: { id: 1041, status: "confirmed" },
    ts_ms: Date.now() - 18000,
    latency_ms: 540,
  },
  {
    op: "delete",
    table: "public.customers",
    before: { id: 55, email: "test@example.com" },
    after: null,
    ts_ms: Date.now() - 45000,
    latency_ms: 890,
  },
  {
    op: "snapshot",
    table: "public.products",
    before: null,
    after: { id: 9, name: "Widget A", price: 19.99, stock: 200 },
    ts_ms: Date.now() - 120000,
    latency_ms: 1100,
  },
  {
    op: "update",
    table: "sales.invoices",
    before: { id: 3301, paid: false },
    after: { id: 3301, paid: true },
    ts_ms: Date.now() - 300000,
    latency_ms: 420,
  },
];

export const CDC_CONNECTOR_STATUSES: CDCConnectorStatus[] = [
  {
    connector_id: "postgres-source-1",
    connector_name: "PostgreSQL Orders",
    state: "RUNNING",
    last_event_ts_ms: Date.now() - 4000,
    lag_ms: 312,
  },
  {
    connector_id: "mysql-source-1",
    connector_name: "MySQL Inventory",
    state: "RUNNING",
    last_event_ts_ms: Date.now() - 45000,
    lag_ms: 890,
  },
  {
    connector_id: "mssql-source-1",
    connector_name: "MSSQL Sales",
    state: "PAUSED",
    last_event_ts_ms: Date.now() - 3600000,
    lag_ms: null,
  },
  {
    connector_id: "oracle-source-1",
    connector_name: "Oracle ERP",
    state: "FAILED",
    last_event_ts_ms: null,
    lag_ms: null,
  },
];
