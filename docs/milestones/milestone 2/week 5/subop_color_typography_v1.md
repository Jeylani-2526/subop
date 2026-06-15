# SUBOP Colour System, Typography & Spacing Grid
**Task:** M2W5T6 · Owner: Beyza · Single source of truth for all Phase 3 components

---

## 1. Colour Palette

Seven colours define the SUBOP visual language. Every component in Phase 3 must use only these values — no ad hoc hex codes.

| Token | Hex | Usage Rule |
|-------|-----|------------|
| `color-primary` | `#1B3A6B` | Navigation bar, active sidebar item, primary buttons, page headings, source node in Lineage |
| `color-secondary` | `#2E75B6` | Nav icon background, avatar border, accent links, hover states on primary elements |
| `color-success` | `#2E7D32` | Completed status badge, rule PASS, upward trend indicator, progress bar fill (healthy) |
| `color-warning` | `#E65100` | ETL transformation node, WARN log entry, amber KPI border, degraded state |
| `color-danger` | `#C62828` | Failed status badge, rule FAIL, downward trend indicator, error state |
| `color-neutral-dark` | `#3A4A5A` | Body text, table cell text, secondary headings |
| `color-neutral-light` | `#F4F7FA` | Sidebar background, filter panel background, input field background |

**Supporting tokens derived from the palette above — not independent colours:**

| Token | Hex | Derived From | Usage Rule |
|-------|-----|-------------|------------|
| `color-background` | `#F9FAFB` | Neutral light | Main content area background |
| `color-surface` | `#FFFFFF` | — | Card surface, panel surface, table surface |
| `color-border` | `#DDE4EE` | Neutral light + secondary | Card borders, table dividers, input borders |
| `color-row-alt` | `#EBF3FB` | Secondary tint | Table alternate rows, selected card background |
| `color-success-bg` | `#E8F5E9` | Success tint | Success badge background, pass indicator background |
| `color-warning-bg` | `#FFF8E1` | Warning tint | Warning badge background, alert banner background |
| `color-danger-bg` | `#FFEBEE` | Danger tint | Danger badge background, error banner background |

**Resolved inconsistencies from audit:**
- `#00838F` (teal — used once on CDC KPI card) → replaced by `color-secondary` `#2E75B6`. CDC stream is a secondary metric, not a separate semantic category.
- Log entry colours (`#4CAF50`, `#42A5F5`, `#FFA726`) → replaced by `color-success`, `color-secondary`, `color-warning` respectively.
- Bottom bar background (`#F0F4F8`) → replaced by `color-neutral-light` `#F4F7FA`. One neutral background value only.

---

## 2. Typography

**Font family:** Inter (Google Fonts — free, open-source)
- Fallback stack: `Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif`
- Rationale: designed for screen readability at small sizes; used by Linear, Vercel, and Notion; excellent rendering at 10–12px label sizes critical for data tables and status badges.

**Type scale — five levels:**

| Level | Token | Size | Weight | Line Height | Usage |
|-------|-------|------|--------|-------------|-------|
| H1 — Display | `type-h1` | 20px | 700 | 28px | Page title (one per page) |
| H2 — Section | `type-h2` | 15px | 600 | 22px | Panel header, detail panel title, card group heading |
| H3 — Card title | `type-h3` | 13px | 600 | 18px | Selected asset name, pipeline name in detail view |
| Body | `type-body` | 12px | 400 | 18px | Table cells, activity feed items, sidebar items, form labels |
| Caption / Label | `type-caption` | 11px | 500 | 16px | Section labels (uppercase + letter-spacing 0.6px), badge text, meta text, timestamp |

**Special case — monospace log:**

| Token | Family | Size | Weight | Usage |
|-------|--------|------|--------|-------|
| `type-mono` | `'Courier New', monospace` | 11px | 400 | Execution log lines in Pipeline Monitor only |

**Resolved inconsistencies from audit:**
- Section labels standardised to `type-caption` at 11px — the 10px variant is retired.
- Panel header font sizes standardised to `type-h2` at 15px across all screens.
- KPI value display (26px bold) is not a type scale level — it is a one-off numeric display style applied only to KPI Card component values. Token: `type-kpi-value` — 26px, weight 700.

---

## 3. Spacing Grid

**Base unit: 8px**

All padding, margin, and gap values must be multiples of 8px (or the 4px half-unit for tight contexts only).

| Token | Value | Usage |
|-------|-------|-------|
| `space-xs` | 4px | Icon-to-text gap inside badges and buttons; tight internal padding |
| `space-sm` | 8px | Sidebar item padding (vertical); table cell padding (vertical); gap between badge and label |
| `space-md` | 16px | Card internal padding (horizontal); sidebar item padding (horizontal); gap between inline elements |
| `space-lg` | 24px | Main content area padding (horizontal); gap between page sections |
| `space-xl` | 32px | Page header bottom margin; gap between major layout regions |
| `space-2xl` | 48px | Top-level page vertical padding |

**Applied spacing rules by context:**

| Context | Rule |
|---------|------|
| Card internal padding | `space-sm` vertical (8px) · `space-md` horizontal (16px) |
| Panel header padding | `space-sm` vertical (8px) · `space-md` horizontal (16px) |
| Table cell padding | `space-sm` vertical (8px) · `space-md` horizontal (16px) |
| Gap between KPI cards | `space-md` (16px) — previously inconsistent at 12px/14px |
| Gap between panels (mid-row) | `space-md` (16px) — previously inconsistent at 12px/14px |
| Main content area padding | `space-md` vertical (16px) · `space-lg` horizontal (24px) |
| Sidebar item padding | `space-sm` vertical (8px) · `space-md` horizontal (16px) |

**Resolved inconsistencies from audit:**
- Card and panel gaps unified to `space-md` (16px). The 12px and 14px values found in M1 wireframes are retired.
- Table cell padding unified to `space-sm` / `space-md`. The 10px vertical / 12px horizontal variants are retired.

---

## 4. Border Radius & Shadow

**Border radius:**

| Token | Value | Usage |
|-------|-------|-------|
| `radius-sm` | 4px | Badges, tags, small buttons, input fields |
| `radius-md` | 6px | Cards, panels, table containers |
| `radius-lg` | 8px | Page-level containers, modal dialogs |
| `radius-full` | 9999px | Pill badges (status badges), avatar circles |

**Shadow — three elevation levels:**

| Token | Value | Usage |
|-------|-------|-------|
| `shadow-sm` | `0 1px 3px rgba(0,0,0,0.06)` | Cards at rest, filter sidebar |
| `shadow-md` | `0 4px 12px rgba(0,0,0,0.10)` | Page wrapper, active/focused card |
| `shadow-lg` | `0 8px 24px rgba(0,0,0,0.14)` | Modal dialogs, dropdown menus, detail panels |

No gradients. No decorative shadows. Shadows communicate elevation only.
