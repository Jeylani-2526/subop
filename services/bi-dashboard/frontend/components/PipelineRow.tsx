import { useEffect, useState } from "react";
import StatusBadge from "./StatusBadge";

interface PipelineRowProps {
  pipelineName: string;
  source: string;
  target: string;
  status:
    | "Running"
    | "Completed"
    | "Failed"
    | "Pending"
    | "CompletedWithQuarantine";
  lastRunTime: string;
  onSelect: () => void;
  selected?: boolean;
}

const statusMap = {
  Running: "running",
  Completed: "completed",
  Failed: "failed",
  Pending: "warning",
  CompletedWithQuarantine: "completed_with_quarantine",
} as const;

function useWindowWidth() {
  const [width, setWidth] = useState(window.innerWidth);
  useEffect(() => {
    const handler = () => setWidth(window.innerWidth);
    window.addEventListener("resize", handler);
    return () => window.removeEventListener("resize", handler);
  }, []);
  return width;
}

export default function PipelineRow({
  pipelineName,
  source,
  target,
  status,
  lastRunTime,
  onSelect,
  selected = false,
}: PipelineRowProps) {
  const width = useWindowWidth();
  const isCard = width < 900;

  if (isCard) {
    // Card-stack layout — mobile/tablet
    return (
      <div
        onClick={onSelect}
        style={{
          padding: "12px 14px",
          margin: "6px 8px",
          borderRadius: "8px",
          border: `1px solid ${selected ? "var(--color-primary)" : "var(--color-border)"}`,
          backgroundColor: selected
            ? "var(--color-row-alt)"
            : "var(--color-surface)",
          cursor: "pointer",
          display: "flex",
          flexDirection: "column",
          gap: "6px",
          boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
          }}
        >
          <span
            style={{
              fontSize: "13px",
              fontWeight: 600,
              color: "var(--color-neutral-dark)",
              flex: 1,
              marginRight: "8px",
            }}
          >
            {pipelineName}
          </span>
          <StatusBadge status={statusMap[status]} size="compact" />
        </div>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <span style={{ fontSize: "11px", color: "#6b7280" }}>
            {source} → {target}
          </span>
          <span style={{ fontSize: "10px", color: "#9ca3af" }}>
            {lastRunTime}
          </span>
        </div>
      </div>
    );
  }

  // Default row layout — desktop
  return (
    <div
      onClick={onSelect}
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "12px 16px",
        cursor: "pointer",
        borderLeft: selected
          ? "3px solid var(--color-primary)"
          : "3px solid transparent",
        backgroundColor: selected ? "var(--color-row-alt)" : "transparent",
        transition: "background-color 0.15s",
        borderBottom: "1px solid var(--color-border)",
      }}
      onMouseEnter={(e) => {
        if (!selected)
          (e.currentTarget as HTMLDivElement).style.backgroundColor =
            "var(--color-neutral-light)";
      }}
      onMouseLeave={(e) => {
        if (!selected)
          (e.currentTarget as HTMLDivElement).style.backgroundColor =
            "transparent";
      }}
    >
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: "4px",
          minWidth: 0,
        }}
      >
        <span
          style={{
            fontSize: "13px",
            fontWeight: 600,
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
            color: "var(--color-neutral-dark)",
          }}
        >
          {pipelineName}
        </span>
        <span
          style={{
            fontSize: "11px",
            color: "#6b7280",
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
        >
          {source} {"->"} {target}
        </span>
      </div>
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "flex-end",
          gap: "4px",
          flexShrink: 0,
          marginLeft: "12px",
        }}
      >
        <StatusBadge status={statusMap[status]} />
        <span style={{ fontSize: "11px", color: "#9ca3af" }}>
          {lastRunTime}
        </span>
      </div>
    </div>
  );
}
