import { useState } from "react";
import { CreatePipelinePayload } from "../api/pipelinesClient";

interface PipelineCreationFormProps {
  onSubmit: (payload: CreatePipelinePayload) => void;
  onCancel: () => void;
}

const SOURCES = ["PostgreSQL", "MySQL", "MSSQL", "MongoDB", "Kafka", "CSV", "REST API"];
const TARGETS = ["Data Warehouse", "PostgreSQL", "MySQL", "MSSQL"];

export default function PipelineCreationForm({ onSubmit, onCancel }: PipelineCreationFormProps) {
  const [form, setForm] = useState<CreatePipelinePayload>({
    pipelineName: "",
    source: "",
    target: "",
    transformations: [],
    processingPurpose: "",
  });

  const [errors, setErrors] = useState<Partial<Record<keyof CreatePipelinePayload, string>>>({});

  function validate(): boolean {
    const e: typeof errors = {};
    if (!form.pipelineName.trim()) e.pipelineName = "Pipeline adı zorunlu";
    if (!form.source) e.source = "Kaynak seçimi zorunlu";
    if (!form.target) e.target = "Hedef seçimi zorunlu";
    if (form.source && form.target && form.source === form.target) e.target = "Kaynak ve hedef aynı olamaz";
    if (!form.processingPurpose.trim()) e.processingPurpose = "İşleme amacı zorunlu";
    setErrors(e);
    return Object.keys(e).length === 0;
  }

  return (
    <div style={{ background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: "10px", padding: "24px", display: "flex", flexDirection: "column", gap: "18px", maxWidth: "520px", width: "100%" }}>
      
      <div style={{ fontSize: "16px", fontWeight: 700, color: "var(--color-neutral-dark)" }}>
        Yeni Pipeline Oluştur
      </div>

      <Field label="Pipeline Adı" error={errors.pipelineName}>
        <input
          value={form.pipelineName}
          onChange={e => setForm(f => ({ ...f, pipelineName: e.target.value }))}
          placeholder="Örn: Orders ETL"
          style={inputStyle(!!errors.pipelineName)}
        />
      </Field>

      <Field label="Kaynak" error={errors.source}>
        <select value={form.source} onChange={e => setForm(f => ({ ...f, source: e.target.value }))} style={inputStyle(!!errors.source)}>
          <option value="">Seçin</option>
          {SOURCES.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
      </Field>

      <Field label="Hedef" error={errors.target}>
        <select value={form.target} onChange={e => setForm(f => ({ ...f, target: e.target.value }))} style={inputStyle(!!errors.target)}>
          <option value="">Seçin</option>
          {TARGETS.map(t => <option key={t} value={t}>{t}</option>)}
        </select>
      </Field>

      <Field label="Dönüşümler (opsiyonel)" error={undefined}>
        <input
          placeholder="filter_nulls, normalize_dates (virgülle ayırın)"
          onChange={e => setForm(f => ({ ...f, transformations: e.target.value ? e.target.value.split(",").map(t => t.trim()) : [] }))}
          style={inputStyle(false)}
        />
      </Field>

      <Field label="İşleme Amacı" error={errors.processingPurpose}>
        <textarea
          value={form.processingPurpose}
          onChange={e => setForm(f => ({ ...f, processingPurpose: e.target.value }))}
          placeholder="Bu pipeline verisi ne amaçla işliyor?"
          rows={3}
          style={{ ...inputStyle(!!errors.processingPurpose), resize: "vertical", fontFamily: "inherit" }}
        />
      </Field>

      <div style={{ display: "flex", gap: "10px", justifyContent: "flex-end" }}>
        <button onClick={onCancel} style={{ padding: "8px 18px", borderRadius: "7px", border: "1px solid var(--color-border)", background: "none", fontSize: "12px", cursor: "pointer" }}>
          İptal
        </button>
        <button onClick={() => { if (validate()) onSubmit(form); }} style={{ padding: "8px 18px", borderRadius: "7px", border: "none", background: "var(--color-primary)", color: "#fff", fontSize: "12px", fontWeight: 600, cursor: "pointer" }}>
          Oluştur
        </button>
      </div>
    </div>
  );
}

function Field({ label, error, children }: { label: string; error?: string; children: React.ReactNode }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "5px" }}>
      <label style={{ fontSize: "11px", fontWeight: 600, color: "var(--color-neutral-dark)" }}>{label}</label>
      {children}
      {error && <span style={{ fontSize: "10px", color: "var(--color-danger)" }}>{error}</span>}
    </div>
  );
}

function inputStyle(hasError: boolean): React.CSSProperties {
  return {
    padding: "8px 10px", borderRadius: "7px",
    border: `1px solid ${hasError ? "var(--color-danger)" : "var(--color-border)"}`,
    fontSize: "12px", color: "var(--color-neutral-dark)",
    background: "var(--color-surface)", width: "100%", outline: "none",
  };
}