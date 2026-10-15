import { useEffect, useState } from "react";
import AppShell from "./components/AppShell";
import StatusBadge from "./components/StatusBadge";
import { useT } from "./src/i18n/LanguageProvider";
import type { TranslationKey } from "./src/i18n/tr";
import { getCDCEvents, getAllCDCConnectorStatuses } from "./api/cdcClient";
import type { CDCChangeEvent, CDCConnectorStatus } from "./api/cdcClient";

// ─── Yardımcı ─────────────────────────────────────────

function formatTs(ts_ms: number): string {
  const diff = Date.now() - ts_ms;
  if (diff < 60_000) return `${Math.round(diff / 1000)}s ago`;
  if (diff < 3_600_000) return `${Math.round(diff / 60_000)}m ago`;
  return `${Math.round(diff / 3_600_000)}h ago`;
}

function jsonSummary(obj: Record<string, unknown> | null): string {
  if (!obj) return "—";
  const keys = Object.keys(obj);
  if (keys.length === 0) return "{}";
  if (keys.length <= 2) return JSON.stringify(obj);
  return `{ ${keys.slice(0, 2).join(", ")}, … }`;
}

function useWindowWidth() {
  const [width, setWidth] = useState(window.innerWidth);
  useEffect(() => {
    const handler = () => setWidth(window.innerWidth);
    window.addEventListener("resize", handler);
    return () => window.removeEventListener("resize", handler);
  }, []);
  return width;
}

// ─── Expandable Row ────────────────────────────────────

function EventRow({
  event,
  t,
  isCard,
}: {
  event: CDCChangeEvent;
  t: (k: TranslationKey) => string;
  isCard: boolean;
}) {
  const [expanded, setExpanded] = useState(false);

  if (isCard) {
    return (
      <div
        onClick={() => setExpanded((v) => !v)}
        style={{
          padding: "12px 14px",
          marginBottom: "8px",
          borderRadius: "8px",
          border: "1px solid var(--color-border)",
          backgroundColor: "var(--color-surface)",
          cursor: "pointer",
          display: "flex",
          flexDirection: "column",
          gap: "6px",
          boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <span
            style={{
              fontSize: "12px",
              fontWeight: 600,
              color: "var(--color-text)",
              fontFamily: "monospace",
            }}
          >
            {event.table}
          </span>
          <StatusBadge status={event.op} size="compact" />
        </div>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <span style={{ fontSize: "11px", color: "var(--color-text-muted)" }}>
            {t("cdc_col_latency")}:{" "}
            {event.latency_ms != null ? `${event.latency_ms} ms` : "—"}
          </span>
          <span style={{ fontSize: "11px", color: "var(--color-text-muted)" }}>
            {formatTs(event.ts_ms)}
          </span>
          <span style={{ fontSize: "11px", color: "var(--color-text-muted)" }}>
            {expanded ? "▲" : "▼"}
          </span>
        </div>
        {expanded && (
          <div
            style={{
              backgroundColor: "var(--color-row-alt)",
              borderRadius: "6px",
              padding: "10px 12px",
              display: "flex",
              flexDirection: "column",
              gap: "10px",
              fontSize: "11px",
              fontFamily: "monospace",
            }}
          >
            <div>
              <div
                style={{
                  fontWeight: 600,
                  marginBottom: "4px",
                  color: "var(--color-text-muted)",
                }}
              >
                {t("cdc_col_before")}
              </div>
              <pre
                style={{
                  margin: 0,
                  whiteSpace: "pre-wrap",
                  wordBreak: "break-all",
                }}
              >
                {event.before ? JSON.stringify(event.before, null, 2) : "null"}
              </pre>
            </div>
            <div>
              <div
                style={{
                  fontWeight: 600,
                  marginBottom: "4px",
                  color: "var(--color-text-muted)",
                }}
              >
                {t("cdc_col_after")}
              </div>
              <pre
                style={{
                  margin: 0,
                  whiteSpace: "pre-wrap",
                  wordBreak: "break-all",
                }}
              >
                {event.after ? JSON.stringify(event.after, null, 2) : "null"}
              </pre>
            </div>
          </div>
        )}
      </div>
    );
  }

  return (
    <>
      <div
        onClick={() => setExpanded((v) => !v)}
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 100px 90px 1fr 1fr 80px 32px",
          gap: "8px",
          alignItems: "center",
          fontSize: "12px",
          padding: "10px 0",
          borderBottom: "1px solid var(--color-border)",
          cursor: "pointer",
        }}
      >
        <span
          style={{
            color: "var(--color-text)",
            fontFamily: "monospace",
            fontSize: "11px",
          }}
        >
          {event.table}
        </span>
        <StatusBadge status={event.op} size="compact" />
        <span style={{ color: "var(--color-text-muted)", fontSize: "11px" }}>
          {formatTs(event.ts_ms)}
        </span>
        <span
          style={{
            color: "var(--color-text-muted)",
            fontSize: "11px",
            fontFamily: "monospace",
          }}
        >
          {jsonSummary(event.before)}
        </span>
        <span
          style={{
            color: "var(--color-text-muted)",
            fontSize: "11px",
            fontFamily: "monospace",
          }}
        >
          {jsonSummary(event.after)}
        </span>
        <span style={{ color: "var(--color-text)", fontSize: "11px" }}>
          {event.latency_ms != null ? `${event.latency_ms} ms` : "—"}
        </span>
        <span
          style={{
            color: "var(--color-text-muted)",
            fontSize: "14px",
            textAlign: "center",
          }}
        >
          {expanded ? "▲" : "▼"}
        </span>
      </div>

      {expanded && (
        <div
          style={{
            backgroundColor: "var(--color-row-alt)",
            borderRadius: "6px",
            padding: "12px 16px",
            marginBottom: "4px",
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: "16px",
            fontSize: "11px",
            fontFamily: "monospace",
          }}
        >
          <div>
            <div
              style={{
                fontWeight: 600,
                marginBottom: "6px",
                color: "var(--color-text-muted)",
              }}
            >
              {t("cdc_col_before")}
            </div>
            <pre
              style={{
                margin: 0,
                whiteSpace: "pre-wrap",
                wordBreak: "break-all",
              }}
            >
              {event.before ? JSON.stringify(event.before, null, 2) : "null"}
            </pre>
          </div>
          <div>
            <div
              style={{
                fontWeight: 600,
                marginBottom: "6px",
                color: "var(--color-text-muted)",
              }}
            >
              {t("cdc_col_after")}
            </div>
            <pre
              style={{
                margin: 0,
                whiteSpace: "pre-wrap",
                wordBreak: "break-all",
              }}
            >
              {event.after ? JSON.stringify(event.after, null, 2) : "null"}
            </pre>
          </div>
        </div>
      )}
    </>
  );
}

// ─── CDCPage ───────────────────────────────────────────

export default function CDCPage() {
  const { t } = useT();
  const width = useWindowWidth();
  const isCard = width < 900;
  const isMobile = width < 768;

  const [events, setEvents] = useState<CDCChangeEvent[]>([]);
  const [connectors, setConnectors] = useState<CDCConnectorStatus[]>([]);

  useEffect(() => {
    getCDCEvents().then(setEvents).catch(console.error);
    getAllCDCConnectorStatuses().then(setConnectors).catch(console.error);
  }, []);

  return (
    <AppShell pageTitle={t("page_title_cdc")} userRole="admin">
      <div
        style={{
          padding: isCard ? "16px" : "24px",
          display: "flex",
          flexDirection: "column",
          gap: "20px",
        }}
      >
        {/* Mobile read-only banner */}
        {isMobile && (
          <div
            style={{
              backgroundColor: "var(--color-warning-bg)",
              color: "var(--color-warning)",
              borderRadius: "6px",
              padding: "10px 14px",
              fontSize: "12px",
              fontWeight: 500,
            }}
          >
            {t("pipeline_mobile_readonly")}
          </div>
        )}

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
              marginBottom: "8px",
            }}
          >
            {t("cdc_event_feed_title")}
          </div>

          {/* Fix ② — pending notice banner */}
          <div
            style={{
              fontSize: "12px",
              color: "var(--color-warning)",
              marginBottom: "12px",
            }}
          >
            {t("cdc_pending_notice")}
          </div>

          {events.length === 0 ? (
            <div
              style={{
                textAlign: "center",
                padding: "40px 0",
                color: "var(--color-text-muted)",
                fontSize: "13px",
              }}
            >
              {t("cdc_events_empty")}
            </div>
          ) : isCard ? (
            <div>
              {events.map((event, i) => (
                <EventRow key={i} event={event} t={t} isCard={true} />
              ))}
            </div>
          ) : (
            <>
              {/* Fix ③ — time column in header */}
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 100px 90px 1fr 1fr 80px 32px",
                  gap: "8px",
                  fontSize: "11px",
                  fontWeight: 600,
                  color: "var(--color-text-muted)",
                  borderBottom: "1px solid var(--color-border)",
                  paddingBottom: "8px",
                  marginBottom: "4px",
                }}
              >
                <span>{t("cdc_col_table")}</span>
                <span>{t("cdc_col_op")}</span>
                <span>{t("cdc_col_time")}</span>
                <span>{t("cdc_col_before")}</span>
                <span>{t("cdc_col_after")}</span>
                <span>{t("cdc_col_latency")}</span>
                <span />
              </div>
              {events.map((event, i) => (
                <EventRow key={i} event={event} t={t} isCard={false} />
              ))}
            </>
          )}
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
              marginBottom: "8px",
            }}
          >
            {t("cdc_connector_title")}
          </div>

          {/* Fix ② — pending notice banner */}
          <div
            style={{
              fontSize: "12px",
              color: "var(--color-warning)",
              marginBottom: "12px",
            }}
          >
            {t("cdc_pending_notice")}
          </div>

          {connectors.length === 0 ? (
            <div
              style={{
                textAlign: "center",
                padding: "40px 0",
                color: "var(--color-text-muted)",
                fontSize: "13px",
              }}
            >
              {t("cdc_connectors_empty")}
            </div>
          ) : isCard ? (
            <div>
              {connectors.map((c) => (
                <div
                  key={c.connector_id}
                  style={{
                    padding: "12px 14px",
                    marginBottom: "8px",
                    borderRadius: "8px",
                    border: "1px solid var(--color-border)",
                    backgroundColor: "var(--color-surface)",
                    display: "flex",
                    flexDirection: "column",
                    gap: "6px",
                    boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                    }}
                  >
                    <span
                      style={{
                        fontSize: "12px",
                        fontWeight: 600,
                        color: "var(--color-text)",
                      }}
                    >
                      {c.connector_name}
                    </span>
                    <StatusBadge status={c.state} size="compact" />
                  </div>
                  <div
                    style={{ display: "flex", justifyContent: "space-between" }}
                  >
                    <span
                      style={{
                        fontSize: "11px",
                        color: "var(--color-text-muted)",
                      }}
                    >
                      {t("cdc_col_last_event")}:{" "}
                      {c.last_event_ts_ms ? formatTs(c.last_event_ts_ms) : "—"}
                    </span>
                    <span
                      style={{
                        fontSize: "11px",
                        color: "var(--color-text-muted)",
                      }}
                    >
                      {t("cdc_col_lag")}:{" "}
                      {c.lag_ms != null ? `${c.lag_ms} ms` : "—"}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 100px 1fr 80px",
                  gap: "8px",
                  fontSize: "11px",
                  fontWeight: 600,
                  color: "var(--color-text-muted)",
                  borderBottom: "1px solid var(--color-border)",
                  paddingBottom: "8px",
                  marginBottom: "4px",
                }}
              >
                <span>{t("cdc_col_connector")}</span>
                <span>{t("cdc_col_status")}</span>
                <span>{t("cdc_col_last_event")}</span>
                <span>{t("cdc_col_lag")}</span>
              </div>
              {connectors.map((c) => (
                <div
                  key={c.connector_id}
                  style={{
                    display: "grid",
                    gridTemplateColumns: "1fr 100px 1fr 80px",
                    gap: "8px",
                    alignItems: "center",
                    fontSize: "12px",
                    padding: "10px 0",
                    borderBottom: "1px solid var(--color-border)",
                  }}
                >
                  <span style={{ color: "var(--color-text)", fontWeight: 500 }}>
                    {c.connector_name}
                  </span>
                  <StatusBadge status={c.state} size="compact" />
                  <span
                    style={{
                      color: "var(--color-text-muted)",
                      fontSize: "11px",
                    }}
                  >
                    {c.last_event_ts_ms ? formatTs(c.last_event_ts_ms) : "—"}
                  </span>
                  <span
                    style={{ color: "var(--color-text)", fontSize: "11px" }}
                  >
                    {c.lag_ms != null ? `${c.lag_ms} ms` : "—"}
                  </span>
                </div>
              ))}
            </>
          )}
        </div>
      </div>
    </AppShell>
  );
}
