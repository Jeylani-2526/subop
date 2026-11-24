import { useState, useEffect } from "react";
import AppShell from "./components/AppShell";
import { useT } from "./src/i18n/LanguageProvider";
import type { TranslationKey } from "./src/i18n/tr";
import type { WarehouseSchema, WarehouseTable } from "./api/warehouseTypes";
import { getWarehouseSchemas } from "./api/warehouseClient";

// ─── Legal basis key map ───────────────────────────────────

const LEGAL_BASIS_KEY: Record<string, TranslationKey> = {
  Consent: "warehouse_legal_consent",
  Contract: "warehouse_legal_contract",
  LegalObligation: "warehouse_legal_legal_obligation",
  VitalInterests: "warehouse_legal_vital_interests",
  PublicTask: "warehouse_legal_public_task",
  LegitimateInterest: "warehouse_legal_legitimate_interest",
};

// ─── Helpers ──────────────────────────────────────────────

function useWindowWidth() {
  const [width, setWidth] = useState(window.innerWidth);
  useEffect(() => {
    const handler = () => setWidth(window.innerWidth);
    window.addEventListener("resize", handler);
    return () => window.removeEventListener("resize", handler);
  }, []);
  return width;
}

// ─── SchemaCard (Zone 1) ──────────────────────────────────

function SchemaCard({
  schema,
  selected,
  onClick,
}: {
  schema: WarehouseSchema;
  selected: boolean;
  onClick: () => void;
}) {
  const { t } = useT();
  const factCount = schema.tables.filter((tb) => tb.role === "fact").length;
  const dimCount = schema.tables.filter((tb) => tb.role === "dimension").length;

  return (
    <div
      onClick={onClick}
      style={{
        padding: "12px 14px",
        marginBottom: "8px",
        borderRadius: "8px",
        border: selected
          ? "1.5px solid var(--color-secondary)"
          : "1px solid var(--color-border)",
        backgroundColor: selected
          ? "var(--color-row-alt)"
          : "var(--color-surface)",
        cursor: "pointer",
        display: "flex",
        flexDirection: "column",
        gap: "4px",
        boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
        transition: "border-color 0.15s, background-color 0.15s",
      }}
    >
      <div
        style={{
          fontSize: "13px",
          fontWeight: 600,
          color: "var(--color-primary)",
          fontFamily: "monospace",
        }}
      >
        {schema.name}
      </div>
      <div style={{ fontSize: "11px", color: "var(--color-text-muted)" }}>
        v{schema.version} · {schema.source.connection_ref}
      </div>
      <div
        style={{
          display: "flex",
          gap: "6px",
          marginTop: "4px",
          flexWrap: "wrap",
        }}
      >
        <span
          style={{
            fontSize: "10px",
            fontWeight: 600,
            backgroundColor: "var(--color-secondary)",
            color: "#fff",
            borderRadius: "3px",
            padding: "1px 6px",
          }}
        >
          {t("warehouse_fact_label")} ×{factCount}
        </span>
        <span
          style={{
            fontSize: "10px",
            fontWeight: 600,
            backgroundColor: "var(--color-neutral-dark)",
            color: "#fff",
            borderRadius: "3px",
            padding: "1px 6px",
          }}
        >
          {t("warehouse_dim_label")} ×{dimCount}
        </span>
      </div>
    </div>
  );
}

// ─── ComplianceChips ──────────────────────────────────────

function ComplianceChips({
  table,
  t,
}: {
  table: WarehouseTable;
  t: (k: TranslationKey) => string;
}) {
  if (
    !table.personal_data &&
    !table.legal_basis &&
    table.retention_policy_days == null
  ) {
    return null;
  }
  return (
    <div
      style={{
        display: "flex",
        gap: "6px",
        flexWrap: "wrap",
        marginBottom: "10px",
      }}
    >
      {table.personal_data && (
        <span
          style={{
            fontSize: "10px",
            fontWeight: 600,
            backgroundColor: "var(--color-warning-bg)",
            color: "var(--color-warning)",
            border: "1px solid var(--color-warning)",
            borderRadius: "3px",
            padding: "2px 7px",
          }}
        >
          {t("warehouse_badge_personal_data")}
        </span>
      )}
      {table.legal_basis && (
        <span
          style={{
            fontSize: "10px",
            fontWeight: 600,
            backgroundColor: "var(--color-success-bg)",
            color: "var(--color-success)",
            border: "1px solid var(--color-success)",
            borderRadius: "3px",
            padding: "2px 7px",
          }}
        >
          {t("warehouse_badge_legal_basis")}:{" "}
          {t(
            LEGAL_BASIS_KEY[table.legal_basis] ?? "warehouse_badge_legal_basis",
          )}
        </span>
      )}
      {table.retention_policy_days != null && (
        <span
          style={{
            fontSize: "10px",
            fontWeight: 600,
            backgroundColor: "var(--color-row-alt)",
            color: "var(--color-text-muted)",
            border: "1px solid var(--color-border)",
            borderRadius: "3px",
            padding: "2px 7px",
          }}
        >
          {t("warehouse_badge_retention")}: {table.retention_policy_days}d
        </span>
      )}
    </div>
  );
}

// ─── ScdBadge (inline — StatusBadge SCD türlerini bilmez) ─

function ScdBadge({ type }: { type: 1 | 2 }) {
  const isType2 = type === 2;
  return (
    <span
      style={{
        fontSize: "10px",
        fontWeight: 700,
        backgroundColor: isType2
          ? "var(--color-secondary)"
          : "var(--color-neutral-light)",
        color: isType2 ? "#fff" : "var(--color-neutral-dark)",
        border: isType2 ? "none" : "1px solid var(--color-border)",
        borderRadius: "3px",
        padding: "1px 7px",
        letterSpacing: "0.3px",
      }}
    >
      {isType2 ? "SCD 2" : "SCD 1"}
    </span>
  );
}

// ─── TableDetail (Zone 2) ─────────────────────────────────

function TableDetail({
  table,
  t,
  isCard,
}: {
  table: WarehouseTable;
  t: (k: TranslationKey) => string;
  isCard: boolean;
}) {
  const tableTypeBadge =
    table.role === "fact"
      ? t("warehouse_fact_label")
      : t("warehouse_dim_label");

  return (
    <div
      style={{
        marginBottom: "20px",
        border: "1px solid var(--color-border)",
        borderRadius: "8px",
        overflow: "hidden",
      }}
    >
      {/* Table header */}
      <div
        style={{
          backgroundColor: "var(--color-row-alt)",
          padding: "10px 14px",
          display: "flex",
          alignItems: "center",
          gap: "8px",
          flexWrap: "wrap",
        }}
      >
        <span
          style={{
            fontSize: "12px",
            fontWeight: 700,
            fontFamily: "monospace",
            color: "var(--color-primary)",
          }}
        >
          {table.name}
        </span>
        <span
          style={{
            fontSize: "10px",
            fontWeight: 600,
            backgroundColor:
              table.role === "fact"
                ? "var(--color-secondary)"
                : "var(--color-neutral-dark)",
            color: "#fff",
            borderRadius: "3px",
            padding: "1px 6px",
          }}
        >
          {tableTypeBadge}
        </span>
        {table.scd_type != null && <ScdBadge type={table.scd_type} />}
      </div>

      {/* Compliance chips */}
      <div style={{ padding: "8px 14px 0" }}>
        <ComplianceChips table={table} t={t} />
      </div>

      {/* Columns — card vs desktop */}
      {isCard ? (
        <div style={{ padding: "0 14px 12px" }}>
          {table.columns.map((col) => (
            <div
              key={col.name}
              style={{
                padding: "8px 0",
                borderBottom: "1px solid var(--color-border)",
                display: "flex",
                flexDirection: "column",
                gap: "2px",
              }}
            >
              <div
                style={{ display: "flex", alignItems: "center", gap: "6px" }}
              >
                <span
                  style={{
                    fontSize: "12px",
                    fontWeight: 600,
                    fontFamily: "monospace",
                    color: "var(--color-text)",
                  }}
                >
                  {col.name}
                </span>
                {col.role === "tracked_attribute" && (
                  <span
                    style={{
                      fontSize: "9px",
                      fontWeight: 700,
                      backgroundColor: "var(--color-secondary)",
                      color: "#fff",
                      borderRadius: "3px",
                      padding: "1px 5px",
                    }}
                  >
                    T2
                  </span>
                )}
              </div>
              <div
                style={{ fontSize: "11px", color: "var(--color-text-muted)" }}
              >
                {col.native_type ?? "—"} → {col.canonical_type}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div style={{ padding: "0 14px 12px" }}>
          {/* Header row */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "2fr 1fr 1fr 60px",
              gap: "8px",
              fontSize: "11px",
              fontWeight: 600,
              color: "var(--color-text-muted)",
              borderBottom: "1px solid var(--color-border)",
              paddingBottom: "6px",
              marginTop: "6px",
              marginBottom: "2px",
            }}
          >
            <span>{t("warehouse_col_column")}</span>
            <span>{t("warehouse_col_native_type")}</span>
            <span>{t("warehouse_col_canonical_type")}</span>
            <span>{t("warehouse_col_scd")}</span>
          </div>
          {table.columns.map((col) => (
            <div
              key={col.name}
              style={{
                display: "grid",
                gridTemplateColumns: "2fr 1fr 1fr 60px",
                gap: "8px",
                alignItems: "center",
                padding: "7px 0",
                borderBottom: "1px solid var(--color-border)",
              }}
            >
              <span
                style={{
                  color: "var(--color-text)",
                  fontFamily: "monospace",
                  fontSize: "11px",
                  fontWeight: 500,
                }}
              >
                {col.name}
              </span>
              <span
                style={{
                  color: "var(--color-text-muted)",
                  fontFamily: "monospace",
                  fontSize: "11px",
                }}
              >
                {col.native_type ?? "—"}
              </span>
              <span
                style={{
                  color: "var(--color-text-muted)",
                  fontFamily: "monospace",
                  fontSize: "11px",
                }}
              >
                {col.canonical_type}
              </span>
              <span>
                {col.role === "tracked_attribute" && (
                  <span
                    style={{
                      fontSize: "9px",
                      fontWeight: 700,
                      backgroundColor: "var(--color-secondary)",
                      color: "#fff",
                      borderRadius: "3px",
                      padding: "1px 5px",
                    }}
                  >
                    T2
                  </span>
                )}
                {col.role === "attribute" && table.scd_type === 2 && (
                  <span
                    style={{
                      fontSize: "9px",
                      fontWeight: 600,
                      backgroundColor: "var(--color-neutral-light)",
                      color: "var(--color-neutral-dark)",
                      border: "1px solid var(--color-border)",
                      borderRadius: "3px",
                      padding: "1px 5px",
                    }}
                  >
                    T1
                  </span>
                )}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── WarehousePage ────────────────────────────────────────

export default function WarehousePage() {
  const { t } = useT();
  const width = useWindowWidth();
  const isCard = width < 900;
  const isMobile = width < 768;

  const [schemas, setSchemas] = useState<WarehouseSchema[]>([]);
  const [loadError, setLoadError] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    getWarehouseSchemas()
      .then((data) => {
        setSchemas(data);
        if (data.length > 0) setSelectedId(data[0].schema_id);
      })
      .catch(() => setLoadError(true));
  }, []);

  const selectedSchema =
    schemas.find((s) => s.schema_id === selectedId) ?? null;

  return (
    <AppShell pageTitle={t("page_title_warehouse")} userRole="admin">
      <div style={{ padding: isCard ? "16px" : "24px" }}>
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
              marginBottom: "12px",
            }}
          >
            {t("pipeline_mobile_readonly")}
          </div>
        )}

        {/* Load error */}
        {loadError && (
          <div
            style={{
              backgroundColor: "var(--color-error-bg, rgba(220,38,38,0.08))",
              border: "1px solid var(--color-error, #dc2626)",
              borderRadius: "6px",
              padding: "10px 14px",
              fontSize: "12px",
              fontWeight: 500,
              color: "var(--color-error, #dc2626)",
              marginBottom: "12px",
            }}
          >
            {t("warehouse_api_error")}
          </div>
        )}

        {schemas.length === 0 && !loadError ? (
          <div
            style={{
              textAlign: "center",
              padding: "60px 0",
              color: "var(--color-text-muted)",
              fontSize: "13px",
            }}
          >
            {t("warehouse_empty")}
          </div>
        ) : isCard ? (
          /* ── Card layout (< 900px) ── */
          <div>
            {schemas.map((s) => (
              <SchemaCard
                key={s.schema_id}
                schema={s}
                selected={s.schema_id === selectedId}
                onClick={() => setSelectedId(s.schema_id)}
              />
            ))}
            {selectedSchema && (
              <div style={{ marginTop: "16px" }}>
                {selectedSchema.tables.map((tbl) => (
                  <TableDetail key={tbl.name} table={tbl} t={t} isCard={true} />
                ))}
              </div>
            )}
          </div>
        ) : (
          /* ── Desktop layout (≥ 900px) ── */
          <div
            style={{ display: "flex", gap: "20px", alignItems: "flex-start" }}
          >
            {/* Zone 1 — Schema list */}
            <div
              style={{
                width: "260px",
                flexShrink: 0,
                backgroundColor: "var(--color-surface)",
                border: "1px solid var(--color-border)",
                borderRadius: "8px",
                padding: "16px",
              }}
            >
              <div
                style={{
                  fontSize: "11px",
                  fontWeight: 600,
                  color: "var(--color-text-muted)",
                  textTransform: "uppercase",
                  letterSpacing: "0.5px",
                  marginBottom: "12px",
                }}
              >
                {t("page_title_warehouse")}
              </div>
              {schemas.map((s) => (
                <SchemaCard
                  key={s.schema_id}
                  schema={s}
                  selected={s.schema_id === selectedId}
                  onClick={() => setSelectedId(s.schema_id)}
                />
              ))}
            </div>

            {/* Zone 2 — Table detail */}
            <div style={{ flex: 1, minWidth: 0 }}>
              {selectedSchema ? (
                <>
                  <div
                    style={{
                      fontSize: "13px",
                      fontWeight: 600,
                      color: "var(--color-primary)",
                      marginBottom: "16px",
                      fontFamily: "monospace",
                    }}
                  >
                    {selectedSchema.name}{" "}
                    <span
                      style={{
                        fontSize: "11px",
                        color: "var(--color-text-muted)",
                        fontFamily: "inherit",
                      }}
                    >
                      v{selectedSchema.version}
                    </span>
                  </div>
                  {selectedSchema.tables.map((tbl) => (
                    <TableDetail
                      key={tbl.name}
                      table={tbl}
                      t={t}
                      isCard={false}
                    />
                  ))}
                </>
              ) : (
                <div
                  style={{
                    textAlign: "center",
                    padding: "60px 0",
                    color: "var(--color-text-muted)",
                    fontSize: "13px",
                  }}
                >
                  {t("warehouse_select_schema")}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
