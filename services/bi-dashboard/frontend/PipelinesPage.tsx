import { useEffect, useState } from "react";
import AppShell from "./components/AppShell";
import PipelineRow from "./components/PipelineRow";
import {
  getPipelines,
  getRunStatus,
  Pipeline,
  PipelineRun,
} from "./api/pipelinesClient";

const statusMap: Record<
  string,
  "Running" | "Completed" | "Failed" | "Pending" | "CompletedWithQuarantine"
> = {
  running: "Running",
  succeeded: "Completed",
  completed_with_quarantine: "CompletedWithQuarantine",
  failed: "Failed",
  pending: "Pending",
  cancelled: "Pending",
};

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString("tr-TR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}

export default function PipelinesPage() {
  const [pipelines, setPipelines] = useState<Pipeline[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [runs, setRuns] = useState<Record<string, PipelineRun>>({});
  const [selectedRun, setSelectedRun] = useState<PipelineRun | null>(null);
  const [loadingRun, setLoadingRun] = useState(false);

  useEffect(() => {
    getPipelines().then(setPipelines);
  }, []);

  // Her pipeline için run_id varsa status çek
  useEffect(() => {
    pipelines.forEach((p) => {
      if (!p.run_id) return;
      getRunStatus(p.id, p.run_id)
        .then((run) => setRuns((prev) => ({ ...prev, [p.id]: run })))
        .catch(() => {});
    });
  }, [pipelines]);

  // Seçili pipeline'ın run'ını göster
  useEffect(() => {
    if (!selectedId) return;
    const pipeline = pipelines.find((p) => p.id === selectedId);
    if (!pipeline?.run_id) return;
    setLoadingRun(true);
    getRunStatus(selectedId, pipeline.run_id)
      .then((run) => {
        setSelectedRun(run);
        setRuns((prev) => ({ ...prev, [selectedId]: run }));
      })
      .catch(() => setSelectedRun(null))
      .finally(() => setLoadingRun(false));
  }, [selectedId, pipelines]);

  const selected = pipelines.find((p) => p.id === selectedId) ?? null;

  return (
    <AppShell pageTitle="Pipeline Monitor" userRole="admin">
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          height: "100%",
          minHeight: 0,
        }}
      >
        {/* Zone 1 */}
        <div
          style={{
            display: "flex",
            gap: "12px",
            alignItems: "center",
            padding: "12px 16px",
            borderBottom: "1px solid var(--color-neutral-200)",
            flexShrink: 0,
          }}
        >
          <input
            placeholder="Pipeline ara..."
            style={{
              fontSize: "12px",
              padding: "6px 10px",
              border: "1px solid var(--color-neutral-200)",
              borderRadius: "6px",
              width: "200px",
            }}
          />
          <select
            style={{
              fontSize: "12px",
              padding: "6px 10px",
              border: "1px solid var(--color-neutral-200)",
              borderRadius: "6px",
            }}
          >
            <option value="">Tüm Durumlar</option>
            <option value="running">Running</option>
            <option value="succeeded">Completed</option>
            <option value="failed">Failed</option>
            <option value="pending">Pending</option>
          </select>
          <input
            type="date"
            style={{
              fontSize: "12px",
              padding: "6px 10px",
              border: "1px solid var(--color-neutral-200)",
              borderRadius: "6px",
            }}
          />
        </div>

        {/* Zone 2 + 3 */}
        <div
          style={{ display: "flex", flex: 1, minHeight: 0, overflow: "hidden" }}
        >
          {/* Zone 2 */}
          <div
            style={{
              width: "320px",
              minWidth: "320px",
              flexShrink: 0,
              borderRight: "1px solid var(--color-neutral-200)",
              overflowY: "auto",
            }}
          >
            {pipelines.map((p) => {
              const run = runs[p.id];
              const status = run
                ? (statusMap[run.status] ?? "Pending")
                : "Pending";
              return (
                <PipelineRow
                  key={p.id}
                  pipelineName={p.name}
                  source={p.source.connector_type}
                  target={p.target.object}
                  status={status}
                  lastRunTime={formatDate(p.created_at)}
                  selected={selectedId === p.id}
                  onSelect={() => setSelectedId(p.id)}
                />
              );
            })}
          </div>

          {/* Zone 3 */}
          <div style={{ flex: 1, padding: "20px", overflowY: "auto" }}>
            {selected ? (
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: "16px",
                }}
              >
                <div>
                  <div
                    style={{
                      fontSize: "16px",
                      fontWeight: 700,
                      marginBottom: "8px",
                    }}
                  >
                    {selected.name}
                  </div>
                  <div
                    style={{
                      display: "flex",
                      gap: "24px",
                      fontSize: "12px",
                      color: "var(--color-neutral-500)",
                    }}
                  >
                    <span>
                      Kaynak: <strong>{selected.source.connector_type}</strong>
                    </span>
                    <span>
                      Hedef: <strong>{selected.target.object}</strong>
                    </span>
                    <span>
                      Oluşturulma:{" "}
                      <strong>{formatDate(selected.created_at)}</strong>
                    </span>
                  </div>
                </div>

                <div
                  style={{
                    padding: "10px 14px",
                    borderRadius: "8px",
                    background: "var(--color-row-alt)",
                    fontSize: "12px",
                  }}
                >
                  İşlenen satır:{" "}
                  <strong>
                    {selectedRun
                      ? selectedRun.rows_written.toLocaleString("tr-TR")
                      : "—"}
                  </strong>
                  {selectedRun?.rows_quarantined ? (
                    <span
                      style={{
                        color: "var(--color-warning)",
                        marginLeft: "12px",
                      }}
                    >
                      Karantina: {selectedRun.rows_quarantined}
                    </span>
                  ) : null}
                </div>

                <div>
                  <div
                    style={{
                      fontSize: "12px",
                      fontWeight: 600,
                      marginBottom: "8px",
                    }}
                  >
                    Execution Log
                  </div>
                  <div
                    style={{
                      fontFamily: "monospace",
                      fontSize: "11px",
                      background: "#0f172a",
                      color: "#94a3b8",
                      padding: "12px",
                      borderRadius: "8px",
                      lineHeight: "1.8",
                    }}
                  >
                    {loadingRun ? (
                      <div>Yükleniyor...</div>
                    ) : selectedRun ? (
                      selectedRun.logs.map((log, i) => (
                        <div
                          key={i}
                          style={{
                            color:
                              log.includes("ERROR") || log.includes("failed")
                                ? "#f87171"
                                : log.includes("succeeded") ||
                                    log.includes("Wrote")
                                  ? "#4ade80"
                                  : "#94a3b8",
                          }}
                        >
                          {log}
                        </div>
                      ))
                    ) : (
                      <div>
                        {selected.run_id
                          ? "Log bulunamadı"
                          : "Bu pipeline için henüz run yok"}
                      </div>
                    )}
                  </div>
                </div>

                <div
                  style={{
                    fontSize: "11px",
                    color: "var(--color-neutral-400)",
                    padding: "8px 12px",
                    borderRadius: "6px",
                    border: "1px dashed var(--color-neutral-200)",
                  }}
                >
                  BI Analyst rolünde execution log ve pipeline yönetimi görünümü
                  kısıtlıdır.
                </div>
              </div>
            ) : (
              <div
                style={{
                  height: "100%",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: "13px",
                  color: "var(--color-neutral-400)",
                }}
              >
                Detayları görmek için bir pipeline seçin
              </div>
            )}
          </div>
        </div>
      </div>
    </AppShell>
  );
}
