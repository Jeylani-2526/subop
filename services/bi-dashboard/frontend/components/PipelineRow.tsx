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
      className={`
        flex items-center justify-between px-4 py-3 cursor-pointer border-l-[3px] transition-colors
        ${
          selected
            ? "bg-row-alt border-l-primary"
            : "border-l-transparent hover:bg-neutral-light"
        }
      `}
    >
      <div className="flex flex-col gap-1 min-w-0">
        <span className="text-sm font-semibold truncate">{pipelineName}</span>
        <span className="text-xs text-neutral-500 truncate">
          {source} → {target}
        </span>
      </div>

      <div className="flex flex-col items-end gap-1 shrink-0 ml-3">
        <StatusBadge status={status} />
        <span className="text-xs text-neutral-400">{lastRunTime}</span>
      </div>
    </div>
  );
}
