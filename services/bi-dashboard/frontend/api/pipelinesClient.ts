// ─────────────────────────────────────────────
// SUBOP — Frontend API Client
// services/bi-dashboard/frontend/api/pipelinesClient.ts
//
// Şimdilik mock response'larla çalışıyor.
// Week 15'te BASE_URL aktif edilip mock'lar kaldırılacak.
// ─────────────────────────────────────────────

const BASE_URL = "/api"; // Week 15'te aktif olacak

// ─── Tipler ───────────────────────────────────

export type PipelineStatus = "Running" | "Completed" | "Failed" | "Pending";

export interface Pipeline {
  id: string;
  pipelineName: string;
  source: string;
  target: string;
  status: PipelineStatus;
  lastRunTime: string;
  processingPurpose: string;
}

export interface RunLog {
  timestamp: string;
  level: "INFO" | "ERROR" | "SUCCESS";
  message: string;
}

export interface RunStatus {
  runId: string;
  pipelineId: string;
  status: PipelineStatus;
  rowsProcessed: number | null;
  startedAt: string;
  finishedAt: string | null;
  logs: RunLog[];
}

export interface CreatePipelinePayload {
  pipelineName: string;
  source: string;
  target: string;
  transformations: string[];
  processingPurpose: string;
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
    pipelineName: "Orders ETL",
    source: "PostgreSQL",
    target: "Data Warehouse",
    status: "Running",
    lastRunTime: "2 min ago",
    processingPurpose: "Sipariş verisi entegrasyonu",
  },
  {
    id: "2",
    pipelineName: "Customer Sync",
    source: "MySQL",
    target: "Data Warehouse",
    status: "Completed",
    lastRunTime: "1 hr ago",
    processingPurpose: "Müşteri verisi senkronizasyonu",
  },
  {
    id: "3",
    pipelineName: "Inventory Load",
    source: "MSSQL",
    target: "Data Warehouse",
    status: "Failed",
    lastRunTime: "3 hr ago",
    processingPurpose: "Envanter verisi yükleme",
  },
];

const MOCK_RUN_STATUS: Record<string, RunStatus> = {
  "1": {
    runId: "run-001",
    pipelineId: "1",
    status: "Running",
    rowsProcessed: null,
    startedAt: "2026-08-12T10:00:00Z",
    finishedAt: null,
    logs: [
      { timestamp: "10:00:01", level: "INFO", message: "Pipeline başlatıldı" },
      {
        timestamp: "10:00:02",
        level: "INFO",
        message: "Kaynak bağlantısı kuruldu: PostgreSQL",
      },
      {
        timestamp: "10:00:03",
        level: "INFO",
        message: "Veri çekme başladı...",
      },
    ],
  },
  "2": {
    runId: "run-002",
    pipelineId: "2",
    status: "Completed",
    rowsProcessed: 42381,
    startedAt: "2026-08-12T09:00:00Z",
    finishedAt: "2026-08-12T09:04:22Z",
    logs: [
      { timestamp: "09:00:01", level: "INFO", message: "Pipeline başlatıldı" },
      {
        timestamp: "09:00:02",
        level: "INFO",
        message: "Kaynak bağlantısı kuruldu: MySQL",
      },
      {
        timestamp: "09:04:22",
        level: "SUCCESS",
        message: "Pipeline tamamlandı — 42.381 satır",
      },
    ],
  },
  "3": {
    runId: "run-003",
    pipelineId: "3",
    status: "Failed",
    rowsProcessed: null,
    startedAt: "2026-08-12T07:00:00Z",
    finishedAt: "2026-08-12T07:01:10Z",
    logs: [
      { timestamp: "07:00:01", level: "INFO", message: "Pipeline başlatıldı" },
      {
        timestamp: "07:01:10",
        level: "ERROR",
        message: "Bağlantı zaman aşımına uğradı: MSSQL",
      },
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

// Tüm pipeline'ları getir
export async function getPipelines(): Promise<Pipeline[]> {
  // Week 15: return fetch(`${BASE_URL}/pipelines/`).then(r => r.json());
  return Promise.resolve(MOCK_PIPELINES);
}

// Yeni pipeline oluştur
export async function createPipeline(
  payload: CreatePipelinePayload,
): Promise<Pipeline> {
  // Week 15: return fetch(`${BASE_URL}/pipelines/`, { method: "POST", body: JSON.stringify(payload) }).then(r => r.json());
  const newPipeline: Pipeline = {
    id: String(Date.now()),
    pipelineName: payload.pipelineName,
    source: payload.source,
    target: payload.target,
    status: "Pending",
    lastRunTime: "Az önce",
    processingPurpose: payload.processingPurpose,
  };
  return Promise.resolve(newPipeline);
}

// Belirli bir pipeline'ın run durumunu getir
export async function getRunStatus(pipelineId: string): Promise<RunStatus> {
  // Week 15: return fetch(`${BASE_URL}/pipelines/${pipelineId}/runs/latest`).then(r => r.json());
  return Promise.resolve(MOCK_RUN_STATUS[pipelineId]);
}

// KPI özeti getir (HomePage için)
export async function getKPISummary(): Promise<KPISummary> {
  // Week 15: return fetch(`${BASE_URL}/kpi/summary`).then(r => r.json());
  return Promise.resolve(MOCK_KPI);
}

// Catalog asset listesi getir (CatalogBrowserPage için)
export async function getCatalogAssets(): Promise<CatalogAsset[]> {
  // Week 15: return fetch(`${BASE_URL}/catalog/assets/`).then(r => r.json());
  return Promise.resolve(MOCK_CATALOG);
}
