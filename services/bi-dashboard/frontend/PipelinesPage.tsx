import { useEffect, useState, useMemo, useCallback } from "react";
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

function useDebounce<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return debounced;
}

export default function PipelinesPage() {
  const [pipelines, setPipelines] = useState<Pipeline[]>([]);
  const [paginationInfo, setPaginationInfo] = useState({
    total: 0,
    page: 1,
    page_size: 20,
  });
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [runs, setRuns] = useState<Record<string, PipelineRun>>({});
  const [selectedRun, setSelectedRun] = useState<PipelineRun | null>(null);
  const [loadingRun, setLoadingRun] = useState(false);
  const [loadingList, setLoadingList] = useState(true);
  const [listError, setListError] = useState<string | null>(null);

  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [timeFilter, setTimeFilter] = useState("");

  const debouncedSearch = useDebounce(searchTerm, 300);

  const fetchPipelines = useCallback(() => {
    setLoadingList(true);
    setListError(null);
    getPipelines()
      .then((data) => {
        setPipelines(data.items);
        setPaginationInfo({
          total: data.total,
          page: data.page,
          page_size: data.page_size,
        });
        data.items.forEach((p) => {
          if (!p.run_id) return;
          getRunStatus(p.id, p.run_id)
            .then((run) => setRuns((prev) => ({ ...prev, [p.id]: run })))
            .catch(() => {});
        });
      })
      .catch(() =>
        setListError("Pipeline listesi yüklenemedi. API çalışıyor mu?"),
      )
      .finally(() => setLoadingList(false));
  }, []);

  useEffect(() => {
    fetchPipelines();
  }, [fetchPipelines]);

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
  }, [selectedId]);

  const filteredPipelines = useMemo(() => {
    return pipelines.filter((p) => {
      if (
        debouncedSearch &&
        !p.name.toLowerCase().includes(debouncedSearch.toLowerCase())
      )
        return false;
      if (statusFilter) {
        const run = runs[p.id];
        if ((run?.status ?? "pending") !== statusFilter) return false;
      }
      if (timeFilter) {
        const created = new Date(p.created_at).getTime();
        if (Date.now() - created > parseInt(timeFilter) * 60 * 60 * 1000)
          return false;
      }
      return true;
    });
  }, [pipelines, runs, debouncedSearch, statusFilter, timeFilter]);

  const hasFilter = searchTerm || statusFilter || timeFilter;
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
            gap: "10px",
            alignItems: "center",
            padding: "12px 16px",
            borderBottom: "1px solid var(--color-neutral-200)",
            flexShrink: 0,
          }}
        >
          <input
            placeholder="Pipeline ara..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{
              fontSize: "12px",
              padding: "6px 10px",
              border: "1px solid var(--color-neutral-200)",
              borderRadius: "6px",
              width: "180px",
            }}
          />
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
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
          <select
            value={timeFilter}
            onChange={(e) => setTimeFilter(e.target.value)}
            style={{
              fontSize: "12px",
              padding: "6px 10px",
              border: "1px solid var(--color-neutral-200)",
              borderRadius: "6px",
            }}
          >
            <option value="">Tüm Zamanlar</option>
            <option value="1">Son 1 Saat</option>
            <option value="24">Son 24 Saat</option>
            <option value="168">Son 7 Gün</option>
          </select>
          {hasFilter && (
            <button
              onClick={() => {
                setSearchTerm("");
                setStatusFilter("");
                setTimeFilter("");
              }}
              style={{
                fontSize: "11px",
                padding: "5px 10px",
                border: "1px solid var(--color-neutral-200)",
                borderRadius: "6px",
                cursor: "pointer",
                background: "none",
                color: "var(--color-neutral-500)",
              }}
            >
              Filtreleri Temizle ✕
            </button>
          )}
          <button
            onClick={fetchPipelines}
            style={{
              fontSize: "11px",
              padding: "5px 10px",
              border: "1px solid var(--color-neutral-200)",
              borderRadius: "6px",
              cursor: "pointer",
              background: "none",
              color: "var(--color-neutral-500)",
            }}
          >
            ↻ Yenile
          </button>
          <span
            style={{
              fontSize: "11px",
              color: "var(--color-neutral-400)",
              marginLeft: "auto",
            }}
          >
            {hasFilter ? `${filteredPipelines.length} / ` : ""}
            {paginationInfo.total} pipeline
          </span>
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
            {loadingList ? (
              <div
                style={{
                  padding: "24px 16px",
                  textAlign: "center",
                  fontSize: "12px",
                  color: "var(--color-neutral-400)",
                }}
              >
                Yükleniyor...
              </div>
            ) : listError ? (
              <div
                style={{
                  padding: "16px",
                  fontSize: "12px",
                  color: "var(--color-danger)",
                }}
              >
                {listError}
              </div>
            ) : filteredPipelines.length === 0 ? (
              <div
                style={{
                  padding: "24px 16px",
                  textAlign: "center",
                  fontSize: "12px",
                  color: "var(--color-neutral-400)",
                }}
              >
                {hasFilter ? "Filtre sonucu bulunamadı" : "Henüz pipeline yok"}
              </div>
            ) : (
              filteredPipelines.map((p) => {
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
              })
            )}
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
