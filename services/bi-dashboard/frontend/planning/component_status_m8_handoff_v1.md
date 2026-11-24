# Component & Page Status — M8 Handoff (v1)

**Sprint:** M8 W28  
**Last updated:** 24 November 2026 — Beyza Ülkümen  
**Branch:** `feat/m8w28-warehouse-page`  
**Purpose:** M9 başlangıç noktası — tüm bileşenlerin canlı/fixture durumu, bilinen eksikler, i18n durumu.

---

## 1. API Clients

| Client | Dosya | Durum | Notlar |
|--------|-------|-------|--------|
| `pipelinesClient` | `api/pipelinesClient.ts` | ✅ Canlı | FastAPI `/pipelines` endpoint'e bağlı |
| `cdcClient` | `api/cdcClient.ts` | ✅ Canlı | FastAPI `/cdc` endpoint'e bağlı; `CDCConnectUnavailableError` (503) handle edildi |
| `warehouseClient` | `api/warehouseClient.ts` | ✅ Canlı | FastAPI `/warehouse` endpoint'e bağlı; M8W28'de eklendi |

---

## 2. Shared Components

| Bileşen | Dosya | Durum | Notlar |
|---------|-------|-------|--------|
| `AppShell` | `components/AppShell.tsx` | ✅ Canlı | NavigationSidebar, header, userRole prop |
| `NavigationSidebar` | `components/NavigationSidebar.tsx` | ✅ Canlı | CDC + Warehouse nav linkleri M8'de eklendi |
| `StatusBadge` | `components/StatusBadge.tsx` | ✅ Canlı | `op` (CDC event) + `state` (connector) + pipeline statuses |
| `KPISummaryCard` | `components/KPISummaryCard.tsx` | ✅ Canlı | `status: "healthy"\|"warning"\|"critical"` border rengi |
| `DataTable` | `components/DataTable.tsx` | ✅ Canlı | Sıralama, arama, pagination |
| `PipelineRow` | (HomePage inline) | ✅ Canlı | Expandable row |

---

## 3. Sayfa Durumu

| Sayfa | Dosya | API | Durum | Sprint |
|-------|-------|-----|-------|--------|
| `HomePage` | `HomePage.tsx` | `pipelinesClient` + `cdcClient` | ✅ Canlı | M6 |
| `PipelinesPage` | `PipelinesPage.tsx` | `pipelinesClient` | ✅ Canlı | M6 |
| `CDCPage` | `CDCPage.tsx` | `cdcClient` | ✅ Canlı | M7 |
| `WarehousePage` | `WarehousePage.tsx` | `warehouseClient` | ✅ Canlı | M8 W28 |
| `DataQualityPage` | `DataQualityPage.tsx` | — | 🔲 Shell | — |
| `LineagePage` | `LineagePage.tsx` | — | 🔲 Shell | — |
| `CatalogPage` | `CatalogPage.tsx` | — | 🔲 Shell | — |
| `BIReportsPage` | `BIReportsPage.tsx` | — | 🔲 Shell | — |
| `AdminPage` | `AdminPage.tsx` | — | 🔲 Shell | — |
| `UserManagementPage` | `UserManagementPage.tsx` | — | 🔲 Shell | — |

Shell sayfalar `shell_coming_soon` i18n key'ini gösterir.

---

## 4. M8 T8 — CDC Latency KPI

- `kpi_cdc_latency_pending` key'i `en.ts` ve `tr.ts`'den kaldırıldı
- `kpi_cdc_latency_target: "< 30 s"` eklendi (her iki dil)
- `HomePage.tsx` KPISummaryCard:
  - `trendValue={t("kpi_cdc_latency_target")}`
  - `status` dinamik: `null → "warning"`, `< 30_000 ms → "healthy"`, `≥ 30_000 ms → "critical"`
- `CDCPage.tsx` latency strip tile: veri yokken `t("kpi_cdc_latency_target")` gösterir
- KPI validation (M8W28): p95 649.85 ms idle / 648.95 ms active → eşik 30 000 ms

---

## 5. M8 T9 — i18n Audit

| Key | Dosya | Kullanım | Durum |
|-----|-------|----------|-------|
| `app_name` | `en.ts`, `tr.ts` | `AppShell` header | ✅ Kullanımda |
| `form_data_subjects_placeholder` | `en.ts`, `tr.ts` | `PipelineCreationForm` | ✅ Kullanımda |
| `form_recipients_placeholder` | `en.ts`, `tr.ts` | `PipelineCreationForm` | ✅ Kullanımda |
| `cdc_status_healthy` | `en.ts`, `tr.ts` | `StatusBadge` | ✅ Kullanımda |
| `cdc_status_warning` | `en.ts`, `tr.ts` | `StatusBadge` | ✅ Kullanımda |
| `cdc_status_error` | `en.ts`, `tr.ts` | `StatusBadge` | ✅ Kullanımda |
| `cdc_status_unknown` | `en.ts`, `tr.ts` | `StatusBadge` | ✅ Kullanımda |
| `warehouse_scd_type1` | `en.ts`, `tr.ts` | `ScdBadge` (WarehousePage) | ✅ M8W28'de wire edildi |
| `warehouse_scd_type2` | `en.ts`, `tr.ts` | `ScdBadge` (WarehousePage) | ✅ M8W28'de wire edildi |
| `kpi_cdc_latency_pending` | — | — | ✅ Kaldırıldı (T8) |

Doğrulama yöntemi: `dist/assets/index-*.js` bundle grep (PowerShell) — tüm key'ler build output'ta mevcut.

---

## 6. WarehousePage — M8W28

### Özellikler
- Warehouse schema listesi (sol panel) + tablo detayı (sağ panel)
- Responsive: `< 900px` → stacked layout
- `ScdBadge`: `warehouse_scd_type1` / `warehouse_scd_type2` i18n key'leri ile (`t` prop)
- Compliance badge'leri: `warehouse_badge_personal_data`, `warehouse_badge_legal_basis`, `warehouse_badge_retention`
- Legal basis: 6 key (consent, contract, legal_obligation, vital_interests, public_task, legitimate_interest)
- Fact/Dim etiketi: `warehouse_fact_label` / `warehouse_dim_label`

### Bilinen Eksikler (M9 için)
- Column-level lineage linki yok
- Schema versiyonlama / diff görünümü yok
- Retention süresi hesaplama yok (sadece etiket gösteriliyor)

---

## 7. Design System Token'ları

```css
--color-primary
--color-surface
--color-border
--color-text
--color-text-muted
--color-row-alt
--color-error / --color-error-bg
--color-warning / --color-warning-bg
```

Dark mode: CSS `prefers-color-scheme: dark` ile otomatik.

---

## 8. M9 Başlangıç Noktası

### Yüksek Öncelik
- [ ] `WarehousePage` column-level lineage linki
- [ ] `DataQualityPage` — API + UI tasarımı
- [ ] CDC latency alert eşiği yapılandırılabilir hale getirme

### Orta Öncelik
- [ ] Shell sayfalar için iskelet UI (DataQuality, Lineage, Catalog)
- [ ] `KPISummaryCard` sparkline desteği
- [ ] i18n: `⚠️ unverified` olarak işaretlenen key'lerin kaynak koda izlenmesi

### Düşük Öncelik
- [ ] `WarehousePage` schema versiyonlama
- [ ] Pipeline form: multi-step wizard
- [ ] Mobil: `CDCPage` event feed card görünümü iyileştirme

---

## 9. M8 Özeti

| Sprint | Tamamlanan |
|--------|-----------|
| M8 W27 | CDC latency strip (Zone 1), connector status (Zone 3), halt banner |
| M8 W28 | WarehousePage (canlı), CDC `connect_reachable: false` handling (Section 10), T8 KPI target, T9 i18n |
