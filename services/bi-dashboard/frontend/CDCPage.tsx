import AppShell from "./components/AppShell";
import { useT } from "./src/i18n/LanguageProvider";

export default function CDCPage() {
  const { t } = useT();

  return (
    <AppShell pageTitle={t("page_title_cdc")} userRole="admin">
      <div
        style={{
          padding: "24px",
          display: "flex",
          flexDirection: "column",
          gap: "20px",
        }}
      >
        {/* Zone 1 — Latency Summary Strip */}
        <div
          style={{
            backgroundColor: "var(--color-primary)",
            borderRadius: "8px",
            padding: "20px 24px",
          }}
        >
          <div
            style={{
              color: "rgba(255,255,255,0.7)",
              fontSize: "11px",
              fontWeight: 600,
              textTransform: "uppercase",
              letterSpacing: "0.5px",
              marginBottom: "16px",
            }}
          >
            {t("cdc_latency_strip_title")}
          </div>
          <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
            {(
              [
                "cdc_hop_e2e",
                "cdc_hop_capture",
                "cdc_hop_publish",
                "cdc_hop_consumer",
                "cdc_hop_warehouse",
              ] as const
            ).map((key) => (
              <div
                key={key}
                style={{
                  flex: "1 1 140px",
                  backgroundColor: "rgba(255,255,255,0.07)",
                  borderRadius: "6px",
                  padding: "12px 16px",
                }}
              >
                <div
                  style={{
                    color: "rgba(255,255,255,0.6)",
                    fontSize: "11px",
                    marginBottom: "6px",
                  }}
                >
                  {t(key)}
                </div>
                <div
                  style={{ color: "#fff", fontSize: "22px", fontWeight: 700 }}
                >
                  —
                </div>
                <div
                  style={{
                    color: "rgba(255,255,255,0.4)",
                    fontSize: "10px",
                    marginTop: "4px",
                  }}
                >
                  {t("kpi_cdc_latency_unit")}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Zone 2 — Change Event Feed */}
        <div
          style={{
            backgroundColor: "var(--color-surface)",
            border: "1px solid var(--color-border)",
            borderRadius: "8px",
            padding: "20px 24px",
          }}
        >
          <div
            style={{
              fontSize: "13px",
              fontWeight: 600,
              color: "var(--color-primary)",
              marginBottom: "16px",
            }}
          >
            {t("cdc_event_feed_title")}
          </div>
          <div
            style={{
              fontSize: "12px",
              color: "var(--color-warning)",
              marginBottom: "12px",
            }}
          >
            {t("cdc_pending_notice")}
          </div>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr 1fr 1fr 80px",
              gap: "8px",
              fontSize: "11px",
              fontWeight: 600,
              color: "rgba(0,0,0,0.4)",
              borderBottom: "1px solid var(--color-border)",
              paddingBottom: "8px",
            }}
          >
            <span>{t("cdc_col_table")}</span>
            <span>{t("cdc_col_op")}</span>
            <span>{t("cdc_col_before")}</span>
            <span>{t("cdc_col_after")}</span>
            <span>{t("cdc_col_latency")}</span>
          </div>
        </div>

        {/* Zone 3 — Connector Status */}
        <div
          style={{
            backgroundColor: "var(--color-surface)",
            border: "1px solid var(--color-border)",
            borderRadius: "8px",
            padding: "20px 24px",
          }}
        >
          <div
            style={{
              fontSize: "13px",
              fontWeight: 600,
              color: "var(--color-primary)",
              marginBottom: "16px",
            }}
          >
            {t("cdc_connector_title")}
          </div>
          <div
            style={{
              fontSize: "12px",
              color: "var(--color-warning)",
              marginBottom: "12px",
            }}
          >
            {t("cdc_pending_notice")}
          </div>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr 1fr 1fr",
              gap: "8px",
              fontSize: "11px",
              fontWeight: 600,
              color: "rgba(0,0,0,0.4)",
              borderBottom: "1px solid var(--color-border)",
              paddingBottom: "8px",
            }}
          >
            <span>{t("cdc_col_connector")}</span>
            <span>{t("cdc_col_status")}</span>
            <span>{t("cdc_col_last_event")}</span>
            <span>{t("cdc_col_lag")}</span>
          </div>
        </div>
      </div>
    </AppShell>
  );
}