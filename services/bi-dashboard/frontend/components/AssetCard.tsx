interface AssetCardProps {
  tableName: string;
  sourceSystem: string;
  schemaName: string;
  owner: string;
  qualityScore: number;
  lastUpdated: string;
  onViewLineage: () => void;
  selected?: boolean;
}

function getScoreStyle(score: number): { bg: string; color: string; label: string } {
  if (score >= 80) return { bg: 'var(--color-success-bg)', color: 'var(--color-success)', label: 'Good' };
  if (score >= 50) return { bg: 'var(--color-warning-bg)', color: 'var(--color-warning)', label: 'Fair' };
  return { bg: 'var(--color-danger-bg)', color: 'var(--color-danger)', label: 'Poor' };
}

export default function AssetCard({
  tableName,
  sourceSystem,
  schemaName,
  owner,
  qualityScore,
  lastUpdated,
  onViewLineage,
  selected = false,
}: AssetCardProps) {
  const score = getScoreStyle(qualityScore);

  return (
    <div
      className={`
        flex flex-col gap-3 p-4 rounded-lg border transition-colors cursor-pointer
        ${selected ? 'border-primary bg-row-alt' : 'border-neutral-200 hover:bg-neutral-light'}
      `}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex flex-col gap-1 min-w-0">
          <span className="text-sm font-semibold truncate">{tableName}</span>
          <span className="text-xs text-neutral-500">{schemaName} · {sourceSystem}</span>
        </div>
        <span
          style={{ backgroundColor: score.bg, color: score.color }}
          className="text-xs font-medium px-2 py-1 rounded-full shrink-0"
        >
          {qualityScore} — {score.label}
        </span>
      </div>

      <div className="flex items-center justify-between">
        <span className="text-xs text-neutral-400">Owner: {owner}</span>
        <span className="text-xs text-neutral-400">{lastUpdated}</span>
      </div>

      <button
        onClick={(e) => { e.stopPropagation(); onViewLineage(); }}
        className="text-xs text-secondary hover:underline self-start"
      >
        Lineage'ı Gör →
      </button>
    </div>
  );
}
