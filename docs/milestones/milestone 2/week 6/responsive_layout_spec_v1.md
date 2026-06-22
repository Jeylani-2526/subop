# SUBOP Responsive Layout Grid & Component Minimum Widths

---

## 1. Breakpoint System

| Breakpoint | Range | Grid | Sidebar | Features |
|-----------|-------|------|---------|----------|
| Desktop | ≥ 1280px | 12 columns, 16px gutters | Fixed 240px | All features fully available |
| Tablet | 768px – 1279px | 8 columns | Icon-only 64px (hamburger to expand) | Dashboard view + building on wider tablets; data tables switch to card-stack below 900px |
| Mobile | ≤ 767px | 1 column | Hidden — hamburger overlay | Read-only access only |

**Desktop layout constraints:**
- Sidebar: fixed 240px left
- Main content max-width: 1440px
- Content area padding: 24px all sides (`space-lg`)

**Mobile access restrictions:**
- No pipeline configuration
- No report building
- No admin actions
- All data tables replaced with card-based list views
- Minimum tap target: 44×44px
- Minimum font size: 14px

---

## 2. Page Route Behaviour on Mobile

| Route | URL | Mobile Behaviour |
|-------|-----|-----------------|
| Home / Overview | `/dashboard` | Available — read-only; charts render, no drill-down actions |
| Pipeline Monitor | `/pipelines` | Available — read-only; pipeline list only, no detail panel, no actions |
| Data Quality Dashboard | `/quality` | Available — read-only; KPI cards and score list only |
| Lineage Explorer | `/lineage` | Available — read-only; simplified list view, no DAG canvas |
| Data Catalog | `/catalog` | Available — read-only; card list, detail panel, no metadata editing |
| BI Report Builder | `/reports/builder` | Hidden — redirects to `/dashboard` on mobile |
| Admin Panel | `/admin` | Hidden — redirects to `/dashboard` on mobile |
| User Management | `/admin/users` | Hidden — redirects to `/dashboard` on mobile |

---

## 3. Component Minimum Widths

| Component | Min Width Desktop (px) | Min Width Tablet (px) | Notes |
|-----------|----------------------|----------------------|-------|
| Navigation Sidebar | 240 | 64 (icon-only) | Collapses to icon-only on tablet; hidden on mobile |
| KPI Card | 200 | 160 | 4-column grid on desktop; 2-column on tablet; 1-column on mobile |
| Status Badge | 80 | 80 | Pill shape; never truncates label text |
| Pipeline Row | 600 | 480 | Switches to card layout below 900px on tablet |
| Asset Card | 280 | 240 | Grid: 3 columns desktop; 2 columns tablet; 1 column mobile |
| Data Table | 640 | 480 | Switches to card-stack list below 900px; horizontal scroll above 480px |
| BI Chart Panel | 320 | 280 | Full width on mobile where available |
| Filter Sidebar | 200 | 200 | Collapses to overlay drawer on mobile |
| Admin Form Panel | 480 | 400 | Hidden on mobile — admin routes not accessible |

---

## 4. Tailwind CSS Configuration

All breakpoints and spacing values map directly to the `tailwind.config.js` theme extension. No custom values outside this spec are permitted in Phase 3 component builds.

```js
// tailwind.config.js — theme extension
theme: {
  extend: {
    screens: {
      'sm': '640px',
      'md': '768px',   // tablet breakpoint
      'lg': '1280px',  // desktop breakpoint
      'xl': '1440px',
    },
    colors: {
      primary:        '#1B3A6B',
      secondary:      '#2E75B6',
      success:        '#2E7D32',
      warning:        '#E65100',
      danger:         '#C62828',
      'neutral-dark': '#3A4A5A',
      'neutral-light':'#F4F7FA',
      background:     '#F9FAFB',
      surface:        '#FFFFFF',
      border:         '#DDE4EE',
      'row-alt':      '#EBF3FB',
    },
    spacing: {
      'xs':  '4px',
      'sm':  '8px',
      'md':  '16px',
      'lg':  '24px',
      'xl':  '32px',
      '2xl': '48px',
    },
    fontSize: {
      'h1':      ['20px', { lineHeight: '28px', fontWeight: '700' }],
      'h2':      ['15px', { lineHeight: '22px', fontWeight: '600' }],
      'h3':      ['13px', { lineHeight: '18px', fontWeight: '600' }],
      'body':    ['12px', { lineHeight: '18px', fontWeight: '400' }],
      'caption': ['11px', { lineHeight: '16px', fontWeight: '500' }],
      'kpi':     ['26px', { lineHeight: '1',    fontWeight: '700' }],
    },
    borderRadius: {
      'sm':   '4px',
      'md':   '6px',
      'lg':   '8px',
      'full': '9999px',
    },
    boxShadow: {
      'sm': '0 1px 3px rgba(0,0,0,0.06)',
      'md': '0 4px 12px rgba(0,0,0,0.10)',
      'lg': '0 8px 24px rgba(0,0,0,0.14)',
    },
    maxWidth: {
      'content': '1440px',
    },
    width: {
      'sidebar':       '240px',
      'sidebar-icons': '64px',
    },
  },
},
```
