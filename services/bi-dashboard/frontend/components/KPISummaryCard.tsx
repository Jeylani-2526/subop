interface KPISummaryCardProps {
  label: string;
  value: string | number;
  unit?: string;
  trend: "up" | "down" | "neutral";
  trendValue: string;
  status: "healthy" | "warning" | "critical";
}

const STATUS_BORDER: Record<KPISummaryCardProps["status"], string> = {
  healthy: "var(--color-success)",
  warning: "var(--color-warning)",
  critical: "var(--color-danger)",
};

const STATUS_BG: Record<KPISummaryCardProps["status"], string> = {
  healthy: "rgba(46, 125, 50, 0.04)",
  warning: "rgba(230, 81, 0, 0.04)",
  critical: "rgba(198, 40, 40, 0.04)",
};

const TREND_COLOR: Record<KPISummaryCardProps["trend"], string> = {
  up: "var(--color-success)",
  down: "var(--color-danger)",
  neutral: "var(--color-neutral-500)",
};

const TREND_ARROW: Record<KPISummaryCardProps["trend"], string> = {
  up: "↑",
  down: "↓",
  neutral: "→",
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
        backgroundColor: "var(--color-surface)",
        borderRadius: "10px",
        border: "1px solid var(--color-border)",
        borderLeft: `4px solid ${STATUS_BORDER[status]}`,
        background: STATUS_BG[status],
        padding: "24px",
        display: "flex",
        flexDirection: "column",
        gap: "8px",
        minWidth: "160px",
      }}
    >
      <span
        style={{
          fontSize: "11px",
          fontWeight: 600,
          color: "var(--color-neutral-500)",
          textTransform: "uppercase",
          letterSpacing: "0.8px",
        }}
      >
        {label}
      </span>
      <span
        style={{
          fontSize: "32px",
          fontWeight: 700,
          color: "var(--color-primary)",
          lineHeight: 1,
        }}
      >
        {value}
        {unit && (
          <span
            style={{
              fontSize: "16px",
              fontWeight: 400,
              color: "var(--color-neutral-500)",
              marginLeft: "4px",
            }}
          >
            {unit}
          </span>
        )}
      </span>
      <span
        style={{
          fontSize: "12px",
          color: TREND_COLOR[trend],
          display: "flex",
          alignItems: "center",
          gap: "4px",
        }}
      >
        {TREND_ARROW[trend]} {trendValue}
      </span>
    </div>
  );
}
