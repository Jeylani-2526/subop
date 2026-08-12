# Component Status — M5 Handoff

## Component Durumları

| Component | Dosya | Durum | Notlar |
|-----------|-------|-------|--------|
| AppShell | components/AppShell.tsx | ✅ Built | 8 sayfada aktif |
| NavigationSidebar | components/NavigationSidebar.tsx | ✅ Built | userRole guard + aktif route takibi |
| KPISummaryCard | components/KPISummaryCard.tsx | ✅ Built | M5'te API'ye bağlanacak |
| StatusBadge | components/StatusBadge.tsx | ✅ Built | Design System v1 token'ları aktif |
| DataTable | components/DataTable.tsx | ✅ Built | M5'te server-side pagination eklenecek |
| PipelineRow | components/PipelineRow.tsx | ✅ Built | StatusBadge reuse ediyor |
| AssetCard | components/AssetCard.tsx | ✅ Built | qualityScore renk logic aktif |

## Sayfa Durumları

| Sayfa | Durum | Notlar |
|-------|-------|--------|
| HomePage | ✅ Shell + Static Data | M5'te ETL Engine'e bağlanacak |
| PipelinesPage | ✅ Shell Wired | 3 zone aktif, M5'te API'ye bağlanacak |
| DataQualityPage | ⏳ Shell Only | M9'da gelecek |
| LineageExplorerPage | ⏳ Shell Only | M10'da gelecek |
| CatalogBrowserPage | ⏳ Shell Only | AssetCard M5'te burada kullanılacak |
| BIReportsPage | ⏳ Shell Only | M9'da gelecek |
| AdminPage | ⏳ Shell Only | M11'de gelecek |
| UsersPage | ⏳ Shell Only | M11'de gelecek |

## M5 Data Wiring Yüzeyi

- PipelinesPage Zone 3 — execution log ve satır sayısı API'ye bağlanacak
- HomePage KPISummaryCard — pipeline sayısı ve kalite skoru API'den çekilecek
- DataTable — server-side pagination eklenecek
- CatalogBrowserPage — AssetCard catalog API'sine bağlanacak
