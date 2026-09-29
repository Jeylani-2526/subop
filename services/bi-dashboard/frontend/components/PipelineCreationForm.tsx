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
    padding: "7px 10px",
    fontSize: "12px",
    border: `1px solid ${hasError ? "var(--color-danger)" : "var(--color-border)"}`,
    borderRadius: "6px",
    background: "var(--color-surface)",
    color: "var(--color-neutral-dark)",
    outline: "none",
  };
}

const labelStyle: React.CSSProperties = {
  fontSize: "10px",
  fontWeight: 600,
  color: "var(--color-neutral-500)",
  textTransform: "uppercase",
  letterSpacing: "0.5px",
  marginBottom: "4px",
  display: "block",
};

interface FieldProps {
  label: string;
  error?: string;
  children: React.ReactNode;
}
function Field({ label, error, children }: FieldProps) {
  return (
    <div>
      <label style={labelStyle}>
        {label}
        {error && (
          <span style={{ color: "var(--color-danger)", marginLeft: 4 }}>
            — {error}
          </span>
        )}
      </label>
      {children}
    </div>
  );
}

interface SectionTitleProps {
  text: string;
  color: string;
}
function SectionTitle({ text, color }: SectionTitleProps) {
  return (
    <div
      style={{
        fontSize: "11px",
        fontWeight: 700,
        color,
        padding: "6px 10px",
        background: color + "18",
        borderRadius: "6px",
        marginBottom: "10px",
        borderLeft: `3px solid ${color}`,
      }}
    >
      {text}
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
    return (
      e: React.ChangeEvent<
        HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement
      >,
    ) => setForm((f) => ({ ...f, [key]: e.target.value }));
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
      <div
        style={{
          padding: "24px",
          textAlign: "center",
          color: "var(--color-success)",
          fontSize: "14px",
          fontWeight: 600,
        }}
      >
        {t("form_success")}
      </div>
    );
  }

  return (
    <div
      style={{
        background: "var(--color-surface)",
        border: "1px solid var(--color-border)",
        borderRadius: "10px",
        overflow: "hidden",
        width: "100%",
        maxWidth: "560px",
      }}
    >
      <div
        style={{
          padding: "12px 16px",
          borderBottom: "1px solid var(--color-border)",
          background: "var(--color-primary)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <span style={{ fontSize: "13px", fontWeight: 700, color: "#fff" }}>
          {t("form_title")}
        </span>
        <button
          onClick={onCancel}
          style={{
            background: "none",
            border: "none",
            color: "rgba(255,255,255,0.7)",
            cursor: "pointer",
            fontSize: "16px",
            padding: 0,
          }}
        >
          ✕
        </button>
      </div>

      <div
        style={{
          padding: "16px",
          display: "flex",
          flexDirection: "column",
          gap: "14px",
        }}
      >
        {apiError && (
          <div
            style={{
              padding: "8px 12px",
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

        <Field label={t("form_pipeline_name")} error={errors.name}>
          <input
            value={form.name}
            onChange={set("name")}
            placeholder={t("form_pipeline_name_placeholder")}
            style={getInputStyle(!!errors.name)}
          />
        </Field>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: "12px",
          }}
        >
          <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
            <SectionTitle
              text={t("form_source")}
              color="var(--color-secondary)"
            />
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
                {CONNECTOR_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
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
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
            <SectionTitle
              text={t("form_target")}
              color="var(--color-success)"
            />
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
                {CONNECTOR_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
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
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
          <SectionTitle
            text={t("form_compliance")}
            color="var(--color-warning)"
          />
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: "12px",
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
                placeholder={t("form_data_subjects_placeholder")}
                style={getInputStyle(!!errors.data_subject_categories)}
              />
            </Field>
          </div>
          <Field label={t("form_recipients")} error={undefined}>
            <input
              value={form.transfer_recipients}
              onChange={set("transfer_recipients")}
              placeholder={t("form_recipients_placeholder")}
              style={getInputStyle()}
            />
          </Field>
        </div>

        <div
          style={{
            display: "flex",
            gap: "8px",
            justifyContent: "flex-end",
            paddingTop: "4px",
          }}
        >
          <button
            onClick={onCancel}
            disabled={loading}
            style={{
              padding: "7px 16px",
              borderRadius: "6px",
              border: "1px solid var(--color-border)",
              background: "none",
              fontSize: "12px",
              cursor: "pointer",
              color: "var(--color-neutral-dark)",
            }}
          >
            {t("form_cancel")}
          </button>
          <button
            onClick={handleSubmit}
            disabled={loading}
            style={{
              padding: "7px 16px",
              borderRadius: "6px",
              border: "none",
              background: "var(--color-primary)",
              color: "#fff",
              fontSize: "12px",
              fontWeight: 600,
              cursor: loading ? "not-allowed" : "pointer",
              opacity: loading ? 0.7 : 1,
            }}
          >
            {loading ? t("form_creating") : t("form_create")}
          </button>
        </div>
      </div>
    </div>
  );
}
