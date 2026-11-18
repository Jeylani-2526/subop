import { useState, useEffect } from "react";
import AppShell from "./components/AppShell";
import { useT } from "./src/i18n/LanguageProvider";
import type { TranslationKey } from "./src/i18n/tr";

interface WarehouseColumn {
  name: string;
  native_type: string;
  canonical_type: string;
  tracked?: boolean; // SCD Type 2 tracked attribute
}

interface WarehouseTable {
  name: string;
  table_type: "fact" | "dim";
  scd_type?: 1 | 2;
  personal_data: boolean;
  legal_basis?: string;
  retention_policy_days?: number;
  columns: WarehouseColumn[];
}

interface WarehouseSchema {
  id: string;
  name: string;
  version: string;
  source_connection_ref: string;
  tables: WarehouseTable[];
}

const FIXTURE_SCHEMAS: WarehouseSchema[] = [
  {
    id: "demo_orders_star",
    name: "demo_orders_star",
    version: "1.0.0",
    source_connection_ref: "postgres-demo",
    tables: [
      {
        name: "fact_orders",
        table_type: "fact",
        personal_data: false,
        columns: [
          { name: "order_id", native_type: "int4", canonical_type: "integer" },
          {
            name: "customer_id",
            native_type: "int4",
            canonical_type: "integer",
          },
          { name: "date_id", native_type: "int4", canonical_type: "integer" },
          { name: "amount", native_type: "numeric", canonical_type: "decimal" },
          { name: "status", native_type: "varchar", canonical_type: "string" },
        ],
      },
      {
        name: "dim_customer",
        table_type: "dim",
        scd_type: 2,
        personal_data: true,
        legal_basis: "Contract",
        retention_policy_days: 1095,
        columns: [
          {
            name: "customer_id",
            native_type: "int4",
            canonical_type: "integer",
          },
          {
            name: "name",
            native_type: "varchar",
            canonical_type: "string",
            tracked: false,
          },
          {
            name: "city",
            native_type: "varchar",
            canonical_type: "string",
            tracked: true,
          },
          {
            name: "valid_from",
            native_type: "timestamptz",
            canonical_type: "timestamp",
          },
          {
            name: "valid_to",
            native_type: "timestamptz",
            canonical_type: "timestamp",
          },
          {
            name: "is_current",
            native_type: "bool",
            canonical_type: "boolean",
          },
        ],
      },
      {
        name: "dim_date",
        table_type: "dim",
        scd_type: 1,
        personal_data: false,
        columns: [
          { name: "date_id", native_type: "int4", canonical_type: "integer" },
          { name: "date", native_type: "date", canonical_type: "date" },
          { name: "year", native_type: "int4", canonical_type: "integer" },
          { name: "month", native_type: "int4", canonical_type: "integer" },
          { name: "day", native_type: "int4", canonical_type: "integer" },
        ],
      },
    ],
  },
];

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
  const factCount = schema.tables.filter(
    (tb) => tb.table_type === "fact",
  ).length;
  const dimCount = schema.tables.filter((tb) => tb.table_type === "dim").length;

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
        v{schema.version} · {schema.source_connection_ref}
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
    table.table_type === "fact"
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
              table.table_type === "fact"
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
                {col.tracked === true && (
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
                {col.native_type} → {col.canonical_type}
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
                {col.native_type}
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
                {col.tracked === true && (
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
                {col.tracked === false && table.scd_type === 2 && (
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
  const [selectedId, setSelectedId] = useState<string | null>(
    FIXTURE_SCHEMAS.length > 0 ? FIXTURE_SCHEMAS[0].id : null,
  );

  const isCard = width < 900;
  const isMobile = width < 768;

  const schemas = FIXTURE_SCHEMAS; // W29'da: replace with live data
  const selectedSchema = schemas.find((s) => s.id === selectedId) ?? null;

  return (
    <AppShell pageTitle={t("page_title_warehouse")} userRole="admin">
      <div style={{ padding: isCard ? "16px" : "24px" }}>
        {/* Pending notice — W29'da kaldırılacak */}
        <div
          style={{
            backgroundColor: "var(--color-warning-bg)",
            border: "1px solid var(--color-warning)",
            borderRadius: "6px",
            padding: "10px 14px",
            fontSize: "12px",
            fontWeight: 500,
            color: "var(--color-warning)",
            marginBottom: "20px",
          }}
        >
          {t("warehouse_pending_notice")}
        </div>

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

        {schemas.length === 0 ? (
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
                key={s.id}
                schema={s}
                selected={s.id === selectedId}
                onClick={() => setSelectedId(s.id)}
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
                  key={s.id}
                  schema={s}
                  selected={s.id === selectedId}
                  onClick={() => setSelectedId(s.id)}
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
