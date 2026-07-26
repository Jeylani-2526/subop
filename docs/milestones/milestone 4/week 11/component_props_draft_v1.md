# Pipeline Row & Asset Card — Props Interface Draft

## 1. Pipeline Row

**Screens:** Home / Overview, Pipeline Monitor

```typescript
interface PipelineRowProps {
  /** Pipeline identifier displayed as primary text */
  pipelineName: string;
  /** Source system name (e.g. Oracle, PostgreSQL, MySQL) */
  source: string;
  /** Target system name (always DW in current scope) */
  target: string;
  /** Pipeline status — passed to StatusBadge component */
  status: 'Running' | 'Completed' | 'Failed' | 'Pending';
  /** Relative time string (e.g. "2 min ago", "In progress") */
  lastRunTime: string;
  /** Called when row is clicked — updates detail panel */
  onSelect: (pipelineName: string) => void;
  /** If true, applies selected state styling */
  selected?: boolean;
}
```

**Design System v1 token usage:**
- `status` prop → passed directly to `StatusBadge` component (already built)
- Selected state → `color-row-alt` background, 3px `color-primary` left border
- Hover state → `color-neutral-light` background
- `pipelineName` → `type-body` weight 600, `color-primary`

---

## 2. Asset Card

**Screens:** Catalog Browser

```typescript
interface AssetCardProps {
  /** Table or asset name */
  tableName: string;
  /** Source system — determines source badge colour */
  sourceSystem: 'oracle' | 'postgresql' | 'mysql' | 'csv' | 'mongodb' | 'cassandra' | 'kafka' | 'rest_api';
  /** Database schema path (e.g. warehouse.public) */
  schemaName: string;
  /** Owner name or team */
  owner: string;
  /** Quality score 0–100 — determines badge colour */
  qualityScore: number;
  /** Relative timestamp string (e.g. "Updated 2 hours ago") */
  lastUpdated: string;
  /** Called when View Lineage button is clicked */
  onViewLineage: (tableName: string) => void;
  /** If true, applies selected state styling */
  selected?: boolean;
}
```

**Design System v1 token usage:**
- `qualityScore` → 80–100: `color-success`, 50–79: `color-warning`, 0–49: `color-danger` (same quality-score badge styling as component_patterns_v1.md)
- Selected state → 2px `color-primary` border, `color-row-alt` background
- Hover state → `color-primary` border, `shadow-md`
- Card surface → `color-surface`, `shadow-sm`, `radius-md`
