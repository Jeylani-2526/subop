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

  function validate(): boolean {
    const e: Record<string, string> = {};
    if (!form.name.trim()) e.name = "Pipeline adı zorunlu";
    if (!form.source_connector_type)
      e.source_connector_type = "Kaynak tipi zorunlu";
    if (!form.source_connection_ref.trim())
      e.source_connection_ref = "Kaynak bağlantı referansı zorunlu";
    if (!form.source_object.trim())
      e.source_object = "Kaynak tablo/koleksiyon zorunlu";
    if (!form.target_connector_type)
      e.target_connector_type = "Hedef tipi zorunlu";
    if (!form.target_connection_ref.trim())
      e.target_connection_ref = "Hedef bağlantı referansı zorunlu";
    if (!form.target_object.trim())
      e.target_object = "Hedef tablo/koleksiyon zorunlu";
    if (!form.processing_purpose.trim())
      e.processing_purpose = "İşleme amacı zorunlu";
    if (!form.data_subject_categories.trim())
      e.data_subject_categories = "Veri konusu kategorisi zorunlu";
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
      setTimeout(() => onSuccess(), 1500);
    } catch (err: unknown) {
      const envelope = err as ErrorEnvelope;
      if (envelope?.error_code === "DSL_VALIDATION_FAILED") {
        setApiError(`Validation hatası: ${envelope.message}`);
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
          padding: "32px",
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
        padding: "24px",
        display: "flex",
        flexDirection: "column",
        gap: "16px",
        maxWidth: "560px",
        width: "100%",
      }}
    >
      <div
        style={{
          fontSize: "16px",
          fontWeight: 700,
          color: "var(--color-neutral-dark)",
        }}
      >
        Yeni Pipeline Oluştur
      </div>

      {apiError && (
        <div
          style={{
            padding: "10px 14px",
            borderRadius: "7px",
            background: "rgba(198,40,40,0.08)",
            border: "1px solid var(--color-danger)",
            fontSize: "12px",
            color: "var(--color-danger)",
          }}
        >
          {apiError}
        </div>
      )}

      <Field label="Pipeline Adı" error={errors.name}>
        <input
          value={form.name}
          onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
          placeholder="Örn: Orders ETL"
          style={inputStyle(!!errors.name)}
        />
      </Field>

      <div
        style={{
          fontWeight: 600,
          fontSize: "11px",
          color: "var(--color-neutral-dark)",
        }}
      >
        Kaynak
      </div>

      <Field label="Connector Tipi" error={errors.source_connector_type}>
        <select
          value={form.source_connector_type}
          onChange={(e) =>
            setForm((f) => ({ ...f, source_connector_type: e.target.value }))
          }
          style={inputStyle(!!errors.source_connector_type)}
        >
          <option value="">Seçin</option>
          {CONNECTOR_TYPES.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
      </Field>

      <Field label="Bağlantı Referansı" error={errors.source_connection_ref}>
        <input
          value={form.source_connection_ref}
          onChange={(e) =>
            setForm((f) => ({ ...f, source_connection_ref: e.target.value }))
          }
          placeholder="Örn: pg-main"
          style={inputStyle(!!errors.source_connection_ref)}
        />
      </Field>

      <Field label="Tablo / Koleksiyon" error={errors.source_object}>
        <input
          value={form.source_object}
          onChange={(e) =>
            setForm((f) => ({ ...f, source_object: e.target.value }))
          }
          placeholder="Örn: orders"
          style={inputStyle(!!errors.source_object)}
        />
      </Field>

      <div
        style={{
          fontWeight: 600,
          fontSize: "11px",
          color: "var(--color-neutral-dark)",
        }}
      >
        Hedef
      </div>

      <Field label="Connector Tipi" error={errors.target_connector_type}>
        <select
          value={form.target_connector_type}
          onChange={(e) =>
            setForm((f) => ({ ...f, target_connector_type: e.target.value }))
          }
          style={inputStyle(!!errors.target_connector_type)}
        >
          <option value="">Seçin</option>
          {CONNECTOR_TYPES.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
      </Field>

      <Field label="Bağlantı Referansı" error={errors.target_connection_ref}>
        <input
          value={form.target_connection_ref}
          onChange={(e) =>
            setForm((f) => ({ ...f, target_connection_ref: e.target.value }))
          }
          placeholder="Örn: dw-main"
          style={inputStyle(!!errors.target_connection_ref)}
        />
      </Field>

      <Field label="Tablo / Koleksiyon" error={errors.target_object}>
        <input
          value={form.target_object}
          onChange={(e) =>
            setForm((f) => ({ ...f, target_object: e.target.value }))
          }
          placeholder="Örn: fact_orders"
          style={inputStyle(!!errors.target_object)}
        />
      </Field>

      <Field label="Write Mode" error={undefined}>
        <select
          value={form.target_write_mode}
          onChange={(e) =>
            setForm((f) => ({ ...f, target_write_mode: e.target.value }))
          }
          style={inputStyle(false)}
        >
          {WRITE_MODES.map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </select>
      </Field>

      <div
        style={{
          fontWeight: 600,
          fontSize: "11px",
          color: "var(--color-neutral-dark)",
        }}
      >
        Uyumluluk
      </div>

      <Field label="İşleme Amacı" error={errors.processing_purpose}>
        <textarea
          value={form.processing_purpose}
          onChange={(e) =>
            setForm((f) => ({ ...f, processing_purpose: e.target.value }))
          }
          placeholder="Bu pipeline verisi ne amaçla işliyor?"
          rows={2}
          style={{
            ...inputStyle(!!errors.processing_purpose),
            resize: "vertical",
            fontFamily: "inherit",
          }}
        />
      </Field>

      <Field
        label="Veri Konusu Kategorileri (virgülle ayırın)"
        error={errors.data_subject_categories}
      >
        <input
          value={form.data_subject_categories}
          onChange={(e) =>
            setForm((f) => ({ ...f, data_subject_categories: e.target.value }))
          }
          placeholder="Örn: customers, employees"
          style={inputStyle(!!errors.data_subject_categories)}
        />
      </Field>

      <Field
        label="Transfer Alıcıları (opsiyonel, virgülle ayırın)"
        error={undefined}
      >
        <input
          value={form.transfer_recipients}
          onChange={(e) =>
            setForm((f) => ({ ...f, transfer_recipients: e.target.value }))
          }
          placeholder="Boş bırakılabilir"
          style={inputStyle(false)}
        />
      </Field>

      <div style={{ display: "flex", gap: "10px", justifyContent: "flex-end" }}>
        <button
          onClick={onCancel}
          disabled={loading}
          style={{
            padding: "8px 18px",
            borderRadius: "7px",
            border: "1px solid var(--color-border)",
            background: "none",
            fontSize: "12px",
            cursor: "pointer",
          }}
        >
          İptal
        </button>
        <button
          onClick={handleSubmit}
          disabled={loading}
          style={{
            padding: "8px 18px",
            borderRadius: "7px",
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
  );
}

function Field({
  label,
  error,
  children,
}: {
  label: string;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
      <label
        style={{
          fontSize: "11px",
          fontWeight: 600,
          color: "var(--color-neutral-dark)",
        }}
      >
        {label}
      </label>
      {children}
      {error && (
        <span style={{ fontSize: "10px", color: "var(--color-danger)" }}>
          {error}
        </span>
      )}
    </div>
  );
}

function inputStyle(hasError: boolean): React.CSSProperties {
  return {
    padding: "8px 10px",
    borderRadius: "7px",
    border: `1px solid ${hasError ? "var(--color-danger)" : "var(--color-border)"}`,
    fontSize: "12px",
    color: "var(--color-neutral-dark)",
    background: "var(--color-surface)",
    width: "100%",
    outline: "none",
  };
}
