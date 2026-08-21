import { useEffect, useState } from "react";
import AppShell from "./components/AppShell";
import KPISummaryCard from "./components/KPISummaryCard";
import { getKPISummary, KPISummary } from "./api/pipelinesClient";

export default function HomePage() {
  const [kpi, setKpi] = useState<KPISummary | null>(null);

  useEffect(() => {
    getKPISummary().then(setKpi);
  }, []);

  return (
    <AppShell pageTitle="Home / Overview" userRole="admin">
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(4, 1fr)",
          gap: "16px",
        }}
      >
        <KPISummaryCard
          label="Active Pipelines"
          value={kpi?.activePipelines ?? "—"}
          trend="up"
          trendValue="+3 from yesterday"
          status="healthy"
        />
        <KPISummaryCard
          label="Data Quality Score"
          value={kpi?.dataQualityScore ?? "—"}
          unit="%"
          trend="up"
          trendValue="+2 from last week"
          status="healthy"
        />
        <KPISummaryCard
          label="Records Processed Today"
          value={
            kpi ? `${(kpi.recordsProcessedToday / 1_000_000).toFixed(1)}M` : "—"
          }
          trend="neutral"
          trendValue="Updated 5 min ago"
          status="healthy"
        />
        <KPISummaryCard
          label="CDC Latency"
          value={kpi?.cdcLatencyMs ?? "—"}
          unit="ms"
          trend="down"
          trendValue="Above threshold"
          status="warning"
        />
      </div>
    </AppShell>
  );
}
