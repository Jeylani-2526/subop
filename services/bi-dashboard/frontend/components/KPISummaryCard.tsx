interface KPISummaryCardProps {
  label: string;
  value: string | number;
  unit?: string;
  trend: 'up' | 'down' | 'neutral';
  trendValue: string;
  status: 'healthy' | 'warning' | 'critical';
}

const STATUS_BORDER: Record<KPISummaryCardProps['status'], string> = {
  healthy:  'var(--color-success)',
  warning:  'var(--color-warning)',
  critical: 'var(--color-danger)',
};

const TREND_COLOR: Record<KPISummaryCardProps['trend'], string> = {
  up:      'var(--color-success)',
  down:    'var(--color-danger)',
  neutral: 'var(--color-neutral-dark)',
};

const TREND_ARROW: Record<KPISummaryCardProps['trend'], string> = {
  up:      '↑',
  down:    '↓',
  neutral: '→',
};

export default function KPISummaryCard({
  label,
  value,
  unit,
  trend,
  trendValue,
  status,
}: KPISummaryCardProps) {
  return (
    <div
      style={{
        backgroundColor: 'var(--color-surface)',
        borderRadius: '6px',
        boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
        borderLeft: `3px solid ${STATUS_BORDER[status]}`,
        padding: '8px 16px',
        display: 'flex',
        flexDirection: 'column',
        gap: '4px',
        minWidth: '160px',
      }}
    >
      <span
        style={{
          fontSize: '11px',
          fontWeight: 500,
          color: 'var(--color-neutral-dark)',
          textTransform: 'uppercase',
          letterSpacing: '0.6px',
          lineHeight: '16px',
        }}
      >
        {label}
      </span>

      <span
        style={{
          fontSize: '26px',
          fontWeight: 700,
          color: 'var(--color-primary)',
          lineHeight: 1,
        }}
      >
        {value}
        {unit && (
          <span
            style={{
              fontSize: '14px',
              fontWeight: 400,
              color: 'var(--color-neutral-dark)',
              marginLeft: '4px',
            }}
          >
            {unit}
          </span>
        )}
      </span>

      <span
        style={{
          fontSize: '12px',
          fontWeight: 400,
          color: TREND_COLOR[trend],
          lineHeight: '18px',
        }}
      >
        {TREND_ARROW[trend]} {trendValue}
      </span>
    </div>
  );
}
