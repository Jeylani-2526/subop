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
  "Running" | "Completed" | "Failed" | "Pending"
> = {
  running: "Running",
  succeeded: "Completed",
  completed_with_quarantine: "Completed",
  failed: "Failed",
  pending: "Pending",
  cancelled: "Pending",
};

export default function PipelinesPage() {
  const [pipelines, setPipelines] = useState<Pipeline[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [run, setRun] = useState<PipelineRun | null>(null);

  useEffect(() => {
    getPipelines().then(setPipelines);
  }, []);

  useEffect(() => {
    if (!selectedId) return;
    setRun(null);
    getRunStatus(selectedId, "latest")
      .then(setRun)
      .catch(() => setRun(null));
  }, [selectedId]);

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
        {/* Zone 1 — Filtre Bar */}
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

        {/* Zone 2 + Zone 3 */}
        <div
          style={{ display: "flex", flex: 1, minHeight: 0, overflow: "hidden" }}
        >
          {/* Zone 2 — Sol Panel */}
          <div
            style={{
              width: "320px",
              minWidth: "320px",
              flexShrink: 0,
              borderRight: "1px solid var(--color-neutral-200)",
              overflowY: "auto",
            }}
          >
            {pipelines.map((p) => (
              <PipelineRow
                key={p.id}
                pipelineName={p.name}
                source={p.source.connector_type}
                target={p.target.object}
                status={statusMap[run?.status ?? "pending"] ?? "Pending"}
                lastRunTime={p.created_at}
                selected={selectedId === p.id}
                onSelect={() => setSelectedId(p.id)}
              />
            ))}
          </div>

          {/* Zone 3 — Sağ Detay Panel */}
          <div style={{ flex: 1, padding: "20px", overflowY: "auto" }}>
            {selected ? (
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: "16px",
                }}
              >
                {/* Metadata */}
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
                  </div>
                </div>

                {/* Row count */}
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
                    {run ? run.rows_written.toLocaleString() : "—"}
                  </strong>
                  {run?.rows_quarantined ? (
                    <span
                      style={{
                        color: "var(--color-warning)",
                        marginLeft: "12px",
                      }}
                    >
                      Karantina: {run.rows_quarantined}
                    </span>
                  ) : null}
                </div>

                {/* Execution Log */}
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
                    {run ? (
                      run.logs.map((log, i) => (
                        <div
                          key={i}
                          style={{
                            color: log.includes("ERROR")
                              ? "#f87171"
                              : log.includes("SUCCESS")
                                ? "#4ade80"
                                : "#94a3b8",
                          }}
                        >
                          {log}
                        </div>
                      ))
                    ) : (
                      <div>Yükleniyor...</div>
                    )}
                  </div>
                </div>

                {/* BI Analyst kısıtlı görünüm notu */}
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
