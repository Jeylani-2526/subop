// services/bi-dashboard/frontend/api/pipelinesClient.ts

const BASE_URL = "http://localhost:8000/api";

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
  run_id?: string;
}

export interface PaginatedPipelines {
  items: Pipeline[];
  total: number;
  page: number;
  page_size: number;
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
  pipeline_count: number;
  rows_processed_today: number;
  average_quality_score: number | null;
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

export async function getPipelines(
  page = 1,
  pageSize = 20,
): Promise<PaginatedPipelines> {
  const res = await fetch(
    `${BASE_URL}/pipelines/?page=${page}&page_size=${pageSize}`,
  );
  if (!res.ok) throw await res.json();
  return res.json();
}

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

export async function getRunStatus(
  pipelineId: string,
  runId: string,
): Promise<PipelineRun> {
  const res = await fetch(`${BASE_URL}/pipelines/${pipelineId}/runs/${runId}`);
  if (!res.ok) throw await res.json();
  return res.json();
}

export async function getKPISummary(): Promise<KPISummary> {
  const res = await fetch(`${BASE_URL}/kpis`);
  if (!res.ok) throw await res.json();
  return res.json();
}

export async function getCatalogAssets(): Promise<CatalogAsset[]> {
  return Promise.resolve(MOCK_CATALOG);
}
