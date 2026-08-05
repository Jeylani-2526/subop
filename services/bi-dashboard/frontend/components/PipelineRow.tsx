import StatusBadge from "./StatusBadge";

interface PipelineRowProps {
  pipelineName: string;
  source: string;
  target: string;
  status: "Running" | "Completed" | "Failed" | "Pending";
  lastRunTime: string;
  onSelect: () => void;
  selected?: boolean;
}

const statusMap = {
  Running: "running",
  Completed: "completed",
  Failed: "failed",
  Pending: "warning",
} as const;

export default function PipelineRow({
  pipelineName,
  source,
  target,
  status,
  lastRunTime,
  onSelect,
  selected = false,
}: PipelineRowProps) {
  return (
    <div
      onClick={onSelect}
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "12px 16px",
        cursor: "pointer",
        borderLeft: selected ? "3px solid var(--color-primary)" : "3px solid transparent",
        backgroundColor: selected ? "var(--color-row-alt)" : "transparent",
        transition: "background-color 0.15s",
        borderBottom: "1px solid var(--color-border)",
      }}
      onMouseEnter={e => {
        if (!selected) (e.currentTarget as HTMLDivElement).style.backgroundColor = "var(--color-neutral-light)";
      }}
      onMouseLeave={e => {
        if (!selected) (e.currentTarget as HTMLDivElement).style.backgroundColor = "transparent";
      }}
    >
      <div style={{ display: "flex", flexDirection: "column", gap: "4px", minWidth: 0 }}>
        <span style={{ fontSize: "13px", fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", color: "var(--color-neutral-dark)" }}>
          {pipelineName}
        </span>
        <span style={{ fontSize: "11px", color: "#6b7280", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          {source} {"->"} {target}
        </span>
      </div>

      <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: "4px", flexShrink: 0, marginLeft: "12px" }}>
        <StatusBadge status={statusMap[status]} />
        <span style={{ fontSize: "11px", color: "#9ca3af" }}>{lastRunTime}</span>
      </div>
    </div>
  );
}