import { useState } from 'react';
import AppShell from './components/AppShell';
import PipelineRow from './components/PipelineRow';

const PIPELINES = [
  {
    id: '1',
    pipelineName: 'Orders ETL',
    source: 'PostgreSQL',
    target: 'Data Warehouse',
    status: 'Running' as const,
    lastRunTime: '2 min ago',
  },
  {
    id: '2',
    pipelineName: 'Customer Sync',
    source: 'MySQL',
    target: 'Data Warehouse',
    status: 'Completed' as const,
    lastRunTime: '1 hr ago',
  },
  {
    id: '3',
    pipelineName: 'Inventory Load',
    source: 'MSSQL',
    target: 'Data Warehouse',
    status: 'Failed' as const,
    lastRunTime: '3 hr ago',
  },
];

export default function PipelinesPage() {
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const selected = PIPELINES.find((p) => p.id === selectedId) ?? null;

  return (
    <AppShell pageTitle="Pipeline Monitor" userRole="admin">
      <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: '0' }}>

        {/* Zone 1 — Filtre Bar */}
        <div style={{
          display: 'flex', gap: '12px', alignItems: 'center',
          padding: '12px 16px', borderBottom: '1px solid var(--color-neutral-200)',
          flexShrink: 0,
        }}>
          <input
            placeholder="Pipeline ara..."
            style={{
              fontSize: '12px', padding: '6px 10px',
              border: '1px solid var(--color-neutral-200)', borderRadius: '6px',
              width: '200px', color: 'var(--color-neutral-dark)',
            }}
          />
          <select style={{
            fontSize: '12px', padding: '6px 10px',
            border: '1px solid var(--color-neutral-200)', borderRadius: '6px',
            color: 'var(--color-neutral-dark)',
          }}>
            <option value="">Tüm Durumlar</option>
            <option value="running">Running</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
            <option value="pending">Pending</option>
          </select>
          <input
            type="date"
            style={{
              fontSize: '12px', padding: '6px 10px',
              border: '1px solid var(--color-neutral-200)', borderRadius: '6px',
              color: 'var(--color-neutral-dark)',
            }}
          />
        </div>

        {/* Zone 2 + Zone 3 */}
        <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>

          {/* Zone 2 — Sol Panel */}
          <div style={{
            width: '320px', minWidth: '320px',
            borderRight: '1px solid var(--color-neutral-200)',
            overflowY: 'auto', flexShrink: 0,
          }}>
            {PIPELINES.map((p) => (
              <PipelineRow
                key={p.id}
                {...p}
                selected={selectedId === p.id}
                onSelect={() => setSelectedId(p.id)}
              />
            ))}
          </div>

          {/* Zone 3 — Sağ Detay Panel */}
          <div style={{ flex: 1, padding: '20px', overflowY: 'auto' }}>
            {selected ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>

                {/* Metadata */}
                <div>
                  <div style={{ fontSize: '16px', fontWeight: 700, marginBottom: '8px' }}>
                    {selected.pipelineName}
                  </div>
                  <div style={{ display: 'flex', gap: '24px', fontSize: '12px', color: 'var(--color-neutral-500)' }}>
                    <span>Kaynak: <strong>{selected.source}</strong></span>
                    <span>Hedef: <strong>{selected.target}</strong></span>
                    <span>Son çalışma: <strong>{selected.lastRunTime}</strong></span>
                  </div>
                </div>

                {/* Row count — static placeholder */}
                <div style={{
                  padding: '10px 14px', borderRadius: '8px',
                  background: 'var(--color-row-alt)', fontSize: '12px',
                  color: 'var(--color-neutral-dark)',
                }}>
                  İşlenen satır sayısı: <strong>— (M5'te bağlanacak)</strong>
                </div>

                {/* Execution Log */}
                <div>
                  <div style={{ fontSize: '12px', fontWeight: 600, marginBottom: '8px' }}>
                    Execution Log
                  </div>
                  <div style={{
                    fontFamily: 'monospace', fontSize: '11px',
                    background: '#0f172a', color: '#94a3b8',
                    padding: '12px', borderRadius: '8px', lineHeight: '1.8',
                  }}>
                    <div>[INFO] Pipeline başlatıldı — {selected.lastRunTime}</div>
                    <div>[INFO] Kaynak bağlantısı kuruldu: {selected.source}</div>
                    <div>[INFO] Veri çekme başladı...</div>
                    {selected.status === 'Failed' && (
                      <div style={{ color: '#f87171' }}>[ERROR] Bağlantı zaman aşımına uğradı</div>
                    )}
                    {selected.status === 'Completed' && (
                      <div style={{ color: '#4ade80' }}>[SUCCESS] Pipeline tamamlandı</div>
                    )}
                    {selected.status === 'Running' && (
                      <div style={{ color: '#60a5fa' }}>[INFO] Çalışıyor...</div>
                    )}
                  </div>
                </div>

                {/* BI Analyst kısıtlı görünüm notu */}
                <div style={{
                  fontSize: '11px', color: 'var(--color-neutral-400)',
                  padding: '8px 12px', borderRadius: '6px',
                  border: '1px dashed var(--color-neutral-200)',
                }}>
                  BI Analyst rolünde execution log ve pipeline yönetimi görünümü kısıtlıdır.
                </div>

              </div>
            ) : (
              <div style={{
                height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: '13px', color: 'var(--color-neutral-400)',
              }}>
                Detayları görmek için bir pipeline seçin
              </div>
            )}
          </div>
        </div>
      </div>
    </AppShell>
  );
}