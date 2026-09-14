import { useState } from "react";
import {
  createPipeline,
  CreatePipelinePayload,
  ErrorEnvelope,
} from "../api/pipelinesClient";

interface PipelineCreationFormProps {
  onSuccess: () => void;
  onCancel: () => void;
}

const CONNECTOR_TYPES = ["postgresql", "mysql", "mssql", "mongodb"] as const;
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
    if (!form.name.trim()) e.name = "Zorunlu";
    if (!form.source_connector_type) e.source_connector_type = "Zorunlu";
    if (!form.source_connection_ref.trim()) e.source_connection_ref = "Zorunlu";
    if (!form.source_object.trim()) e.source_object = "Zorunlu";
    if (!form.target_connector_type) e.target_connector_type = "Zorunlu";
    if (!form.target_connection_ref.trim()) e.target_connection_ref = "Zorunlu";
    if (!form.target_object.trim()) e.target_object = "Zorunlu";
    if (!form.processing_purpose.trim()) e.processing_purpose = "Zorunlu";
    if (!form.data_subject_categories.trim())
      e.data_subject_categories = "Zorunlu";
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
          processing_purpose: "VERBIS kaydı tamamlanmamış",
        }));
      } else {
        setApiError("Bir hata oluştu, tekrar deneyin.");
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
        ✓ Pipeline başarıyla oluşturuldu!
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
      {/* Header */}
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
          Yeni Pipeline
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

        {/* Pipeline Adı */}
        <Field label="Pipeline Adı" error={errors.name}>
          <input
            value={form.name}
            onChange={set("name")}
            placeholder="Örn: Orders ETL"
            style={getInputStyle(!!errors.name)}
          />
        </Field>

        {/* Kaynak + Hedef — 2 sütun */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: "12px",
          }}
        >
          {/* Kaynak */}
          <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
            <SectionTitle text="Kaynak" color="var(--color-secondary)" />
            <Field label="Connector" error={errors.source_connector_type}>
              <select
                value={form.source_connector_type}
                onChange={set("source_connector_type")}
                style={getInputStyle(!!errors.source_connector_type)}
              >
                <option value="">Seçin</option>
                {CONNECTOR_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Connection Ref" error={errors.source_connection_ref}>
              <input
                value={form.source_connection_ref}
                onChange={set("source_connection_ref")}
                placeholder="pg-main"
                style={getInputStyle(!!errors.source_connection_ref)}
              />
            </Field>
            <Field label="Tablo / Koleksiyon" error={errors.source_object}>
              <input
                value={form.source_object}
                onChange={set("source_object")}
                placeholder="orders"
                style={getInputStyle(!!errors.source_object)}
              />
            </Field>
          </div>

          {/* Hedef */}
          <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
            <SectionTitle text="Hedef" color="var(--color-success)" />
            <Field label="Connector" error={errors.target_connector_type}>
              <select
                value={form.target_connector_type}
                onChange={set("target_connector_type")}
                style={getInputStyle(!!errors.target_connector_type)}
              >
                <option value="">Seçin</option>
                {CONNECTOR_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Connection Ref" error={errors.target_connection_ref}>
              <input
                value={form.target_connection_ref}
                onChange={set("target_connection_ref")}
                placeholder="dw-main"
                style={getInputStyle(!!errors.target_connection_ref)}
              />
            </Field>
            <Field label="Tablo / Koleksiyon" error={errors.target_object}>
              <input
                value={form.target_object}
                onChange={set("target_object")}
                placeholder="fact_orders"
                style={getInputStyle(!!errors.target_object)}
              />
            </Field>
            <Field label="Write Mode" error={undefined}>
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

        {/* Uyumluluk */}
        <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
          <SectionTitle text="Uyumluluk" color="var(--color-warning)" />
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: "12px",
            }}
          >
            <Field label="İşleme Amacı" error={errors.processing_purpose}>
              <input
                value={form.processing_purpose}
                onChange={set("processing_purpose")}
                placeholder="Sipariş entegrasyonu"
                style={getInputStyle(!!errors.processing_purpose)}
              />
            </Field>
            <Field
              label="Veri Konusu Kategorileri"
              error={errors.data_subject_categories}
            >
              <input
                value={form.data_subject_categories}
                onChange={set("data_subject_categories")}
                placeholder="customers, employees"
                style={getInputStyle(!!errors.data_subject_categories)}
              />
            </Field>
          </div>
          <Field label="Transfer Alıcıları (opsiyonel)" error={undefined}>
            <input
              value={form.transfer_recipients}
              onChange={set("transfer_recipients")}
              placeholder="Boş bırakılabilir"
              style={getInputStyle()}
            />
          </Field>
        </div>

        {/* Butonlar */}
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
            İptal
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
            {loading ? "Oluşturuluyor..." : "Oluştur"}
          </button>
        </div>
      </div>
    </div>
  );
}
