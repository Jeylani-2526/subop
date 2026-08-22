// services/bi-dashboard/frontend/api/pipelinesClient.ts

const BASE_URL = "http://localhost:5433/api";

// ─── Tipler ───────────────────────────────────

export type ConnectorType = "postgresql" | "mysql" | "mssql" | "mongodb";
export type WriteMode = "upsert" | "append";
export type RunStatus =
  | "pending"
  | "running"
  | "succeeded"
  | "completed_with_quarantine"
  | "failed"
  | "cancelled";

export interface PipelineSource {
  connector_type: ConnectorType;
  connection_ref: string;
  object: string;
  query: string | null;
}

export interface PipelineTarget {
  connector_type: ConnectorType;
  connection_ref: string;
  object: string;
  write_mode: WriteMode;
}

export interface TransformationStep {
  step_id: string;
  type: string;
  params: Record<string, unknown>;
}

export interface CreatePipelinePayload {
  name: string;
  source: PipelineSource;
  transformations: TransformationStep[];
  target: PipelineTarget;
  processing_purpose: string;
  data_subject_categories: string[];
  transfer_recipients: string[];
}

export interface Pipeline {
  id: string;
  name: string;
  status: "created";
  created_at: string;
  source: PipelineSource;
  transformations: TransformationStep[];
  target: PipelineTarget;
}

export interface ErrorEnvelope {
  error_code: string;
  message: string;
  connector_type: ConnectorType | null;
  retryable: boolean;
}

export interface PipelineRun {
  run_id: string;
  pipeline_id: string;
  status: RunStatus;
  started_at: string | null;
  finished_at: string | null;
  rows_read: number;
  rows_written: number;
  rows_quarantined: number;
  quality_score: number | null;
  logs: string[];
  error?: ErrorEnvelope;
}

export interface KPISummary {
  activePipelines: number;
  dataQualityScore: number;
  recordsProcessedToday: number;
  cdcLatencyMs: number;
}

export interface CatalogAsset {
  id: string;
  tableName: string;
  sourceSystem: string;
  schemaName: string;
  owner: string;
  qualityScore: number;
  lastUpdated: string;
}

// ─── Mock Data ────────────────────────────────

const MOCK_PIPELINES: Pipeline[] = [
  {
    id: "1",
    name: "Orders ETL",
    status: "created",
    created_at: "2026-08-12T10:00:00Z",
    source: {
      connector_type: "postgresql",
      connection_ref: "pg-main",
      object: "orders",
      query: null,
    },
    transformations: [],
    target: {
      connector_type: "postgresql",
      connection_ref: "dw-main",
      object: "fact_orders",
      write_mode: "upsert",
    },
  },
  {
    id: "2",
    name: "Customer Sync",
    status: "created",
    created_at: "2026-08-12T09:00:00Z",
    source: {
      connector_type: "mysql",
      connection_ref: "mysql-main",
      object: "customers",
      query: null,
    },
    transformations: [],
    target: {
      connector_type: "postgresql",
      connection_ref: "dw-main",
      object: "dim_customers",
      write_mode: "upsert",
    },
  },
  {
    id: "3",
    name: "Inventory Load",
    status: "created",
    created_at: "2026-08-12T07:00:00Z",
    source: {
      connector_type: "mssql",
      connection_ref: "mssql-main",
      object: "inventory",
      query: null,
    },
    transformations: [],
    target: {
      connector_type: "postgresql",
      connection_ref: "dw-main",
      object: "fact_inventory",
      write_mode: "append",
    },
  },
];

const MOCK_RUNS: Record<string, PipelineRun> = {
  "1": {
    run_id: "run-001",
    pipeline_id: "1",
    status: "running",
    started_at: "2026-08-12T10:00:00Z",
    finished_at: null,
    rows_read: 0,
    rows_written: 0,
    rows_quarantined: 0,
    quality_score: null,
    logs: [
      "Pipeline başlatıldı",
      "Kaynak bağlantısı kuruldu: postgresql",
      "Veri çekme başladı...",
    ],
  },
  "2": {
    run_id: "run-002",
    pipeline_id: "2",
    status: "succeeded",
    started_at: "2026-08-12T09:00:00Z",
    finished_at: "2026-08-12T09:04:22Z",
    rows_read: 42381,
    rows_written: 42381,
    rows_quarantined: 0,
    quality_score: 0.97,
    logs: [
      "Pipeline başlatıldı",
      "42.381 satır işlendi",
      "Pipeline tamamlandı",
    ],
  },
  "3": {
    run_id: "run-003",
    pipeline_id: "3",
    status: "failed",
    started_at: "2026-08-12T07:00:00Z",
    finished_at: "2026-08-12T07:01:10Z",
    rows_read: 0,
    rows_written: 0,
    rows_quarantined: 0,
    quality_score: null,
    logs: [
      "Pipeline başlatıldı",
      "ERROR: Bağlantı zaman aşımına uğradı: mssql",
    ],
  },
};

const MOCK_KPI: KPISummary = {
  activePipelines: 24,
  dataQualityScore: 87,
  recordsProcessedToday: 4800000,
  cdcLatencyMs: 12,
};

const MOCK_CATALOG: CatalogAsset[] = [
  {
    id: "1",
    tableName: "dim_customers",
    sourceSystem: "MySQL",
    schemaName: "public",
    owner: "Data Team",
    qualityScore: 92,
    lastUpdated: "2026-08-12",
  },
  {
    id: "2",
    tableName: "fact_orders",
    sourceSystem: "PostgreSQL",
    schemaName: "sales",
    owner: "BI Team",
    qualityScore: 67,
    lastUpdated: "2026-08-11",
  },
  {
    id: "3",
    tableName: "inventory_snapshot",
    sourceSystem: "MSSQL",
    schemaName: "warehouse",
    owner: "Ops Team",
    qualityScore: 41,
    lastUpdated: "2026-08-10",
  },
];

// ─── API Fonksiyonları ────────────────────────

// GET endpoint henüz yok — mock
export async function getPipelines(): Promise<Pipeline[]> {
  return Promise.resolve(MOCK_PIPELINES);
}

// Canlı API
export async function createPipeline(
  payload: CreatePipelinePayload,
): Promise<Pipeline> {
  const res = await fetch(`${BASE_URL}/pipelines/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw await res.json();
  return res.json();
}

// Canlı API
export async function getRunStatus(
  pipelineId: string,
  runId: string,
): Promise<PipelineRun> {
  if (runId === "latest") return Promise.resolve(MOCK_RUNS[pipelineId]);
  const res = await fetch(`${BASE_URL}/pipelines/${pipelineId}/runs/${runId}`);
  if (!res.ok) throw await res.json();
  return res.json();
}

// Mock — KPI endpoint henüz yok
export async function getKPISummary(): Promise<KPISummary> {
  return Promise.resolve(MOCK_KPI);
}

// Mock — Catalog endpoint henüz yok
export async function getCatalogAssets(): Promise<CatalogAsset[]> {
  return Promise.resolve(MOCK_CATALOG);
}
