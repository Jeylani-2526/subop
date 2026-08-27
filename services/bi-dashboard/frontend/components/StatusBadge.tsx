interface StatusBadgeProps {
  status: 'running' | 'completed' | 'failed' | 'warning' | 'completed_with_quarantine';
  label?: string;
  size?: 'default' | 'compact';
}

const STATUS_CONFIG: Record<StatusBadgeProps['status'], { bg: string; color: string; defaultLabel: string }> = {
  running:                   { bg: 'var(--color-row-alt)',     color: 'var(--color-secondary)', defaultLabel: 'Running' },
  completed:                 { bg: 'var(--color-success-bg)',  color: 'var(--color-success)',   defaultLabel: 'Completed' },
  failed:                    { bg: 'var(--color-danger-bg)',   color: 'var(--color-danger)',     defaultLabel: 'Failed' },
  warning:                   { bg: 'var(--color-warning-bg)', color: 'var(--color-warning)',    defaultLabel: 'Warning' },
  completed_with_quarantine: { bg: 'rgba(230,81,0,0.1)',      color: 'var(--color-warning)',    defaultLabel: 'Completed ⚠' },
};

export default function StatusBadge({ status, label, size = 'default' }: StatusBadgeProps) {
  const { bg, color, defaultLabel } = STATUS_CONFIG[status];
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '4px',
        backgroundColor: bg,
        color,
        borderRadius: '9999px',
        fontSize: size === 'compact' ? '10px' : '11px',
        fontWeight: 500,
        padding: size === 'compact' ? '2px 8px' : '3px 10px',
        lineHeight: '16px',
        whiteSpace: 'nowrap',
      }}
    >
      {label ?? defaultLabel}
    </span>
  );
}