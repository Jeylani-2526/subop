import { useEffect, useState } from "react";
import AppShell from "./components/AppShell";
import KPISummaryCard from "./components/KPISummaryCard";
import { getKPISummary, KPISummary } from "./api/pipelinesClient";
import { useT } from "./src/i18n/LanguageProvider";

export default function HomePage() {
  const { t } = useT();
  const [kpi, setKpi] = useState<KPISummary | null>(null);

  useEffect(() => {
    getKPISummary()
      .then(setKpi)
      .catch(() => {});
  }, []);

  return (
    <AppShell pageTitle={t("nav_overview")} userRole="admin">
      <div
        className="subop-kpi-grid"
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(5, 1fr)",
          gap: "20px",
          padding: "24px",
          alignItems: "start",
        }}
      >
        <KPISummaryCard
          label={t("kpi_active_pipelines")}
          value={kpi?.pipeline_count ?? "—"}
          trend="up"
          trendValue={t("kpi_active_pipelines_trend")}
          status="healthy"
        />
        <KPISummaryCard
          label={t("kpi_data_quality")}
          value={
            kpi?.average_quality_score != null
              ? `${(kpi.average_quality_score * 100).toFixed(0)}`
              : "—"
          }
          unit="%"
          trend="up"
          trendValue={
            kpi?.average_quality_score == null
              ? t("kpi_data_quality_null")
              : t("kpi_data_quality_trend")
          }
          status={kpi?.average_quality_score == null ? "warning" : "healthy"}
        />
        <KPISummaryCard
          label={t("kpi_records_today")}
          value={
            kpi ? `${(kpi.rows_processed_today / 1_000_000).toFixed(1)}M` : "—"
          }
          trend="neutral"
          trendValue={t("kpi_records_trend")}
          status="healthy"
        />
        <KPISummaryCard
          label={t("kpi_cdc_latency")}
          value="—"
          unit="ms"
          trend="down"
          trendValue={t("kpi_cdc_trend")}
          status="warning"
        />
        <KPISummaryCard
          label={t("kpi_connectors")}
          value={kpi?.connector_count ?? "—"}
          trend="neutral"
          trendValue={t("kpi_connectors_trend")}
          status="healthy"
        />
      </div>
    </AppShell>
  );
}
