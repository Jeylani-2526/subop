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

function getScoreStyle(score: number): {
  bg: string;
  color: string;
  label: string;
} {
  if (score >= 80)
    return {
      bg: "rgba(46,125,50,0.1)",
      color: "var(--color-success)",
      label: "Good",
    };
  if (score >= 50)
    return {
      bg: "rgba(230,81,0,0.1)",
      color: "var(--color-warning)",
      label: "Fair",
    };
  return {
    bg: "rgba(198,40,40,0.1)",
    color: "var(--color-danger)",
    label: "Poor",
  };
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
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "12px",
        padding: "16px",
        borderRadius: "8px",
        border: selected
          ? "1px solid var(--color-primary)"
          : "1px solid var(--color-border)",
        backgroundColor: selected
          ? "var(--color-row-alt)"
          : "var(--color-surface)",
        cursor: "pointer",
        transition: "background-color 0.15s",
      }}
      onMouseEnter={(e) => {
        if (!selected)
          (e.currentTarget as HTMLDivElement).style.backgroundColor =
            "var(--color-neutral-light)";
      }}
      onMouseLeave={(e) => {
        if (!selected)
          (e.currentTarget as HTMLDivElement).style.backgroundColor =
            "var(--color-surface)";
      }}
    >
      {/* Üst satır — tablo adı + kalite skoru */}
      <div
        style={{
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
          gap: "8px",
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
            {tableName}
          </span>
          <span style={{ fontSize: "11px", color: "#6b7280" }}>
            {schemaName} · {sourceSystem}
          </span>
        </div>
        <span
          style={{
            backgroundColor: score.bg,
            color: score.color,
            fontSize: "11px",
            fontWeight: 500,
            padding: "2px 8px",
            borderRadius: "9999px",
            flexShrink: 0,
            whiteSpace: "nowrap",
          }}
        >
          {qualityScore} — {score.label}
        </span>
      </div>

      {/* Alt satır — owner + tarih */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <span style={{ fontSize: "11px", color: "#9ca3af" }}>
          Owner: {owner}
        </span>
        <span style={{ fontSize: "11px", color: "#9ca3af" }}>
          {lastUpdated}
        </span>
      </div>

      {/* Lineage butonu */}
      <button
        onClick={(e) => {
          e.stopPropagation();
          onViewLineage();
        }}
        style={{
          background: "none",
          border: "none",
          padding: 0,
          fontSize: "11px",
          color: "var(--color-secondary)",
          cursor: "pointer",
          textAlign: "left",
          textDecoration: "none",
        }}
        onMouseEnter={(e) =>
          (e.currentTarget.style.textDecoration = "underline")
        }
        onMouseLeave={(e) => (e.currentTarget.style.textDecoration = "none")}
      >
        Lineage'i Gör &rarr;
      </button>
    </div>
  );
}
