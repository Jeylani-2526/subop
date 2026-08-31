import { useEffect, useState } from "react";
import AppShell from "./components/AppShell";
import KPISummaryCard from "./components/KPISummaryCard";
import { getKPISummary, KPISummary } from "./api/pipelinesClient";

export default function HomePage() {
  const [kpi, setKpi] = useState<KPISummary | null>(null);

  useEffect(() => {
    getKPISummary()
      .then(setKpi)
      .catch(() => {});
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
          value={kpi?.pipeline_count ?? "—"}
          trend="up"
          trendValue="+3 from yesterday"
          status="healthy"
        />
        <KPISummaryCard
          label="Data Quality Score"
          value={
            kpi?.average_quality_score != null
              ? `${(kpi.average_quality_score * 100).toFixed(0)}`
              : "—"
          }
          unit="%"
          trend="up"
          trendValue={
            kpi?.average_quality_score == null
              ? "Henüz mevcut değil"
              : "+2 from last week"
          }
          status={kpi?.average_quality_score == null ? "warning" : "healthy"}
        />
        <KPISummaryCard
          label="Records Processed Today"
          value={
            kpi ? `${(kpi.rows_processed_today / 1_000_000).toFixed(1)}M` : "—"
          }
          trend="neutral"
          trendValue="Updated 5 min ago"
          status="healthy"
        />
        <KPISummaryCard
          label="CDC Latency"
          value="—"
          unit="ms"
          trend="down"
          trendValue="M7'de gelecek"
          status="warning"
        />
      </div>
    </AppShell>
  );
}
