import { useState } from "react";
import {
  createPipeline,
  CreatePipelinePayload,
  ErrorEnvelope,
} from "../api/pipelinesClient";
import { useT } from "../src/i18n/LanguageProvider";

interface PipelineCreationFormProps {
  onSuccess: () => void;
  onCancel: () => void;
}

const CONNECTOR_TYPES = [
  { value: "postgresql", label: "PostgreSQL" },
  { value: "mysql", label: "MySQL" },
  { value: "mssql", label: "MSSQL" },
  { value: "sqlite", label: "SQLite" },
  { value: "csv", label: "CSV" },
  { value: "json", label: "JSON" },
  { value: "rest_api", label: "REST API" },
  { value: "oracle", label: "Oracle" },
] as const;

const WRITE_MODES = ["upsert", "append"] as const;

function getInputStyle(hasError?: boolean): React.CSSProperties {
  return {
    width: "100%",
    padding: "4px 9px",
    fontSize: "11px",
    border: `1px solid ${hasError ? "var(--color-danger)" : "#e0e7ef"}`,
    borderRadius: "6px",
    background: "#f8fafc",
    color: "#1e293b",
    outline: "none",
    height: "28px",
    boxSizing: "border-box",
    transition: "border-color 0.15s, box-shadow 0.15s",
  };
}

interface FieldProps {
  label: string;
  error?: string;
  children: React.ReactNode;
}
function Field({ label, error, children }: FieldProps) {
  return (
    <div>
      <label
        style={{
          fontSize: "9px",
          fontWeight: 700,
          color: "#64748b",
          textTransform: "uppercase",
          letterSpacing: "0.6px",
          marginBottom: "2px",
          display: "block",
        }}
      >
        {label}
        {error && (
          <span style={{ color: "var(--color-danger)", marginLeft: 2 }}>*</span>
        )}
      </label>
      {children}
    </div>
  );
}

interface SectionProps {
  label: string;
  color?: string;
  children: React.ReactNode;
}
function Section({ label, children }: SectionProps) {
  return (
    <div
      style={{
        background: "#fff",
        border: "1px solid #e2e8f0",
        borderRadius: "8px",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          padding: "6px 12px",
          background: "var(--color-primary)",
          fontSize: "10px",
          fontWeight: 700,
          color: "#fff",
          letterSpacing: "0.8px",
          textTransform: "uppercase",
        }}
      >
        {label}
      </div>
      <div
        style={{
          padding: "10px 12px",
          display: "flex",
          flexDirection: "column",
          gap: "8px",
        }}
      >
        {children}
      </div>
    </div>
  );
}

export default function PipelineCreationForm({
  onSuccess,
  onCancel,
}: PipelineCreationFormProps) {
  const { t } = useT();
  const [form, setForm] = useState({
    name: "",
    source_connector_type: "",
    source_connection_ref: "",
    source_object: "",
    target_connector_type: "",
    target_connection_ref: "",
    target_object: "",
    target_write_mode: "upsert",
    processing_purpose: "",
    data_subject_categories: "",
    transfer_recipients: "",
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [apiError, setApiError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  function set(key: string) {
    return (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
      setForm((f) => ({ ...f, [key]: e.target.value }));
  }

  function validate(): boolean {
    const e: Record<string, string> = {};
    const req = t("form_error_required");
    if (!form.name.trim()) e.name = req;
    if (!form.source_connector_type) e.source_connector_type = req;
    if (!form.source_connection_ref.trim()) e.source_connection_ref = req;
    if (!form.source_object.trim()) e.source_object = req;
    if (!form.target_connector_type) e.target_connector_type = req;
    if (!form.target_connection_ref.trim()) e.target_connection_ref = req;
    if (!form.target_object.trim()) e.target_object = req;
    if (!form.processing_purpose.trim()) e.processing_purpose = req;
    if (!form.data_subject_categories.trim()) e.data_subject_categories = req;
    setErrors(e);
    return Object.keys(e).length === 0;
  }

  async function handleSubmit() {
    if (!validate()) return;
    setLoading(true);
    setApiError(null);
    const payload: CreatePipelinePayload = {
      name: form.name,
      source: {
        connector_type:
          form.source_connector_type as CreatePipelinePayload["source"]["connector_type"],
        connection_ref: form.source_connection_ref,
        object: form.source_object,
        query: null,
      },
      transformations: [],
      target: {
        connector_type:
          form.target_connector_type as CreatePipelinePayload["target"]["connector_type"],
        connection_ref: form.target_connection_ref,
        object: form.target_object,
        write_mode: form.target_write_mode as "upsert" | "append",
      },
      processing_purpose: form.processing_purpose,
      data_subject_categories: form.data_subject_categories
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean),
      transfer_recipients: form.transfer_recipients
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean),
    };
    try {
      await createPipeline(payload);
      setSuccess(true);
      setTimeout(() => onSuccess(), 1200);
    } catch (err: unknown) {
      const envelope = err as ErrorEnvelope;
      if (envelope?.error_code === "DSL_VALIDATION_FAILED") {
        setApiError(`Validation: ${envelope.message}`);
      } else if (envelope?.error_code === "VERBIS_REGISTRATION_INCOMPLETE") {
        setErrors((e) => ({
          ...e,
          processing_purpose: t("form_error_verbis"),
        }));
      } else {
        setApiError(t("form_error_generic"));
      }
    } finally {
      setLoading(false);
    }
  }

  if (success) {
    return (
      <div style={{ padding: "24px", textAlign: "center" }}>
        <div style={{ fontSize: "28px", marginBottom: "8px" }}>✓</div>
        <div
          style={{
            fontSize: "14px",
            fontWeight: 600,
            color: "var(--color-success)",
          }}
        >
          {t("form_success")}
        </div>
      </div>
    );
  }

  return (
    <div
      style={{
        background: "#f8fafc",
        borderRadius: "12px",
        overflow: "hidden",
        width: "100%",
        border: "1px solid #e2e8f0",
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: "8px 14px",
          background: "var(--color-primary)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <span
          style={{
            fontSize: "13px",
            fontWeight: 700,
            color: "#fff",
            letterSpacing: "0.3px",
          }}
        >
          {t("form_title")}
        </span>
        <button
          onClick={onCancel}
          style={{
            background: "rgba(255,255,255,0.12)",
            border: "1px solid rgba(255,255,255,0.2)",
            color: "#fff",
            cursor: "pointer",
            fontSize: "12px",
            padding: "3px 10px",
            borderRadius: "5px",
          }}
        >
          ✕
        </button>
      </div>

      <div
        style={{
          padding: "10px",
          display: "flex",
          flexDirection: "column",
          gap: "7px",
        }}
      >
        {apiError && (
          <div
            style={{
              padding: "6px 10px",
              borderRadius: "6px",
              background: "#ffebee",
              border: "1px solid var(--color-danger)",
              fontSize: "11px",
              color: "var(--color-danger)",
            }}
          >
            {apiError}
          </div>
        )}

        {/* Pipeline Name */}
        <Field label={t("form_pipeline_name")} error={errors.name}>
          <input
            value={form.name}
            onChange={set("name")}
            placeholder={t("form_pipeline_name_placeholder")}
            style={{
              ...getInputStyle(!!errors.name),
              height: "28px",
              fontSize: "12px",
              background: "#fff",
              borderColor: errors.name ? "var(--color-danger)" : "#cbd5e1",
            }}
          />
        </Field>

        {/* Source + Target */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: "8px",
          }}
        >
          <Section label={t("form_source")} color="var(--color-secondary)">
            <Field
              label={t("form_connector")}
              error={errors.source_connector_type}
            >
              <select
                value={form.source_connector_type}
                onChange={set("source_connector_type")}
                style={getInputStyle(!!errors.source_connector_type)}
              >
                <option value="">{t("form_select")}</option>
                {CONNECTOR_TYPES.map((c) => (
                  <option key={c.value} value={c.value}>
                    {c.label}
                  </option>
                ))}
              </select>
            </Field>
            <Field
              label={t("form_connection_ref")}
              error={errors.source_connection_ref}
            >
              <input
                value={form.source_connection_ref}
                onChange={set("source_connection_ref")}
                placeholder="pg-main"
                style={getInputStyle(!!errors.source_connection_ref)}
              />
            </Field>
            <Field label={t("form_table")} error={errors.source_object}>
              <input
                value={form.source_object}
                onChange={set("source_object")}
                placeholder="orders"
                style={getInputStyle(!!errors.source_object)}
              />
            </Field>
          </Section>

          <Section label={t("form_target")} color="var(--color-success)">
            <Field
              label={t("form_connector")}
              error={errors.target_connector_type}
            >
              <select
                value={form.target_connector_type}
                onChange={set("target_connector_type")}
                style={getInputStyle(!!errors.target_connector_type)}
              >
                <option value="">{t("form_select")}</option>
                {CONNECTOR_TYPES.map((c) => (
                  <option key={c.value} value={c.value}>
                    {c.label}
                  </option>
                ))}
              </select>
            </Field>
            <Field
              label={t("form_connection_ref")}
              error={errors.target_connection_ref}
            >
              <input
                value={form.target_connection_ref}
                onChange={set("target_connection_ref")}
                placeholder="dw-main"
                style={getInputStyle(!!errors.target_connection_ref)}
              />
            </Field>
            <Field label={t("form_table")} error={errors.target_object}>
              <input
                value={form.target_object}
                onChange={set("target_object")}
                placeholder="fact_orders"
                style={getInputStyle(!!errors.target_object)}
              />
            </Field>
            <Field label={t("form_write_mode")} error={undefined}>
              <select
                value={form.target_write_mode}
                onChange={set("target_write_mode")}
                style={getInputStyle()}
              >
                {WRITE_MODES.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
            </Field>
          </Section>
        </div>

        {/* Compliance */}
        <Section label={t("form_compliance")} color="var(--color-warning)">
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr 1fr",
              gap: "8px",
            }}
          >
            <Field
              label={t("form_processing_purpose")}
              error={errors.processing_purpose}
            >
              <input
                value={form.processing_purpose}
                onChange={set("processing_purpose")}
                placeholder={t("form_processing_purpose_placeholder")}
                style={getInputStyle(!!errors.processing_purpose)}
              />
            </Field>
            <Field
              label={t("form_data_subjects")}
              error={errors.data_subject_categories}
            >
              <input
                value={form.data_subject_categories}
                onChange={set("data_subject_categories")}
                placeholder="customers"
                style={getInputStyle(!!errors.data_subject_categories)}
              />
            </Field>
            <Field label={t("form_recipients")} error={undefined}>
              <input
                value={form.transfer_recipients}
                onChange={set("transfer_recipients")}
                placeholder="-"
                style={getInputStyle()}
              />
            </Field>
          </div>
        </Section>

        {/* Buttons */}
        <div
          style={{ display: "flex", gap: "8px", justifyContent: "flex-end" }}
        >
          <button
            onClick={onCancel}
            disabled={loading}
            style={{
              padding: "5px 14px",
              borderRadius: "6px",
              border: "1px solid #cbd5e1",
              background: "#fff",
              fontSize: "12px",
              cursor: "pointer",
              color: "#64748b",
              fontWeight: 500,
            }}
          >
            {t("form_cancel")}
          </button>
          <button
            onClick={handleSubmit}
            disabled={loading}
            style={{
              padding: "5px 14px",
              borderRadius: "6px",
              border: "none",
              background: "var(--color-primary)",
              color: "#fff",
              fontSize: "12px",
              fontWeight: 700,
              cursor: loading ? "not-allowed" : "pointer",
              opacity: loading ? 0.7 : 1,
              letterSpacing: "0.3px",
            }}
          >
            {loading ? t("form_creating") : t("form_create")}
          </button>
        </div>
      </div>
    </div>
  );
}
