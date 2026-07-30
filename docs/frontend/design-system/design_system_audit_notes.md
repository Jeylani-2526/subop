# Design System Audit Notes
**Task:** M2W5T5 · Owner: Beyza · Feeds: M2W5T6, M2W5T7

---

## 1. Colour Audit — M1 Wireframes

Colours observed across all five M1 wireframes (Home, Pipeline Monitor, Data Quality Dashboard, Lineage Explorer, Catalog Browser):

| Role | Hex | Used In |
|------|-----|---------|
| Primary brand | `#1B3A6B` | Navigation bar, active sidebar item, headings, primary buttons, node (source) |
| Secondary / accent | `#2E75B6` | Nav icon background, avatar border, link colour, KPI card top border |
| Success green | `#2E7D32` | Completed status badge, quality pass, upward trend, progress indicators |
| Warning amber | `#E65100` | ETL transformation node, warn log entry, orange KPI border |
| Danger red | `#C62828` | Failed status badge, rule FAIL, downward trend |
| Neutral dark | `#3A4A5A` | Body text, table cell text |
| Neutral light | `#F4F7FA` | Sidebar background, card background, filter panel |
| Background | `#F9FAFB` | Main content area background |
| Surface white | `#FFFFFF` | Card surfaces, panels, tables |
| Border | `#DDE4EE` | Card borders, table dividers, sidebar divider |
| Alternate row | `#EBF3FB` | Table alternate rows, selected state background |

**Inconsistencies identified:**
- KPI card top borders use four different colours (`#1B3A6B`, `#2E75B6`, `#2E7D32`, `#00838F`) — the teal `#00838F` is used only once and has no semantic role defined
- Log entry colours in Pipeline Monitor use different hex values (`#4CAF50`, `#42A5F5`, `#FFA726`) than the established success/warning/danger palette — these need to be unified
- Bottom bar background (`#F0F4F8`) differs from sidebar background (`#F4F7FA`) with no visual purpose for the difference

---

## 2. Typography Audit — M1 Wireframes

| Element | Observed Size | Weight | Used In |
|---------|--------------|--------|---------|
| Page title | 20px | Bold | All pages |
| Section heading | 13–15px | Bold | Panel headers, detail panel titles |
| KPI value | 26px | Bold | Home, Data Quality KPI cards |
| Body text | 12px | Regular | Table cells, feed items, sidebar items |
| Label / caption | 10–11px | Regular or Bold | Section labels, meta text, badge text |
| Monospace log | 11px | Regular | Execution log in Pipeline Monitor |

**Inconsistencies identified:**
- Section labels alternate between 10px and 11px with no rule governing which is correct
- Panel header font sizes vary between 11px, 12px, and 13px across screens
- No defined H1 / H2 / H3 hierarchy — headings are sized ad hoc per screen

---

## 3. Spacing Audit — M1 Wireframes

| Context | Observed Value |
|---------|---------------|
| Card internal padding | 14px vertical, 16px horizontal |
| Panel header padding | 10px vertical, 14px horizontal |
| Gap between KPI cards | 12px |
| Gap between mid-row panels | 14px |
| Main content area padding | 20px vertical, 24px horizontal |
| Sidebar item padding | 8px vertical, 16px horizontal |
| Table cell padding | 8–10px vertical, 10–12px horizontal |

**Inconsistencies identified:**
- Card gaps vary between 12px, 14px, and 16px across screens with no governing rule
- Table cell padding is inconsistent between screens (8px in some, 10px in others)
- No explicit base unit applied — spacing values are arbitrary per component

---

## 4. Design Direction Note

**Reference systems reviewed:** Ant Design (data-heavy apps), Atlassian Design System (product tools), Material Design 3 (information density)

**Chosen direction for SUBOP:**

**Colour personality:** Professional and trustworthy — dark navy primary (`#1B3A6B`) communicates reliability for an enterprise data platform. Accent blues provide hierarchy without reducing readability. Status colours (green/amber/red) must be immediately readable at a glance — these carry operational meaning, not decoration.

**Target font family:** Inter — clean sans-serif, excellent readability at small sizes (10–12px labels and table cells), designed for screen, free and open-source, widely used in data dashboards (Linear, Vercel, Notion).

**Visual hierarchy principle:** Information density over decoration. SUBOP dashboards are operational tools — every pixel must carry meaning. No gradients, no shadows beyond one elevation level, no animations beyond status transitions. Tables, badges, and numbers are the primary visual language.
