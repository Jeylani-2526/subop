# SUBOP Frontend — M6 Handoff: Component & Page Status

---

## 1. API Client Layer

### `services/bi-dashboard/frontend/api/pipelinesClient.ts`

| Alan | Durum |
|---|---|
| TypeScript tipleri | ✅ API spec v1'e göre güncel |
| `getPipelines()` | ✅ Canlı — `GET /api/pipelines/?page={n}&page_size={n}` |
| `createPipeline()` | ✅ Canlı — `POST /api/pipelines/` |
| `getRunStatus()` | ✅ Canlı — `GET /api/pipelines/{id}/runs/{run_id}` |
| `getKPISummary()` | ✅ Canlı — `GET /api/kpis` |
| `getCatalogAssets()` | ⏳ Mock — Catalog endpoint M9/M10'da gelecek |

**Notlar:**
- `BASE_URL` = `http://localhost:8000/api` (Docker container, port 8000)
- `PaginatedPipelines` interface mevcut — `items`, `total`, `page`, `page_size`
- `Pipeline` interface'inde `run_id?: string` alanı var — API'den otomatik geliyor
- `KPISummary` alanları: `pipeline_count`, `rows_processed_today`, `average_quality_score`
- `RunStatus` 6 değerli enum: `pending | running | succeeded | completed_with_quarantine | failed | cancelled`

---

## 2. Component Durumları

### `components/StatusBadge.tsx`
**Durum: ✅ Built — 5 Variant**

| Variant | Görünüm | Tetikleyici |
|---|---|---|
| `running` | Mavi | `running` |
| `completed` | Yeşil | `succeeded` |
| `failed` | Kırmızı | `failed` |
| `warning` | Turuncu | `pending`, `cancelled` |
| `completed_with_quarantine` | Turuncu ⚠ | `completed_with_quarantine` |

**M6 için notlar:** Variant listesi tamamdır. Data Quality hook gerçek mantığa kavuştuğunda (M10) `completed_with_quarantine` aktif olarak üretilecek.

---

### `components/PipelineRow.tsx`
**Durum: ✅ Built — 5 Status Desteği**

- `StatusBadge` reuse ediyor
- `statusMap` tüm API run status değerlerini karşılıyor
- `CompletedWithQuarantine` dahil 5 status destekleniyor
- `selected` state ile sol border vurgusu çalışıyor

**M6 için notlar:** Değişiklik gerekmez. Yeni status eklenirse sadece `statusMap`'e satır eklenir.

---

### `components/KPISummaryCard.tsx`
**Durum: ✅ Built — Canlı Veri Destekli**

- `status` prop'u: `healthy | warning | critical`
- Status'a göre sol border rengi ve arka plan tonu
- `trend` prop'u: `up | down | neutral` — ok ve renk gösterimi
- `value`, `unit`, `trendValue` prop'ları tam çalışıyor

**M6 için notlar:** CDC Latency kartı şu an `"—"` gösteriyor — M7'de endpoint gelince `cdcLatencyMs` alanı `KPISummary`'ye eklenecek, card'a prop olarak geçilecek.

---

### `components/AppShell.tsx`
**Durum: ✅ Built — Stabil**

- `height: 100vh`, `overflow: hidden` — layout bozulmuyor
- `pageTitle` ve `userRole` prop'ları çalışıyor
- Header: `var(--color-primary)` arka plan

**M6 için notlar:** Değişiklik gerekmez.

---

### `components/NavigationSidebar.tsx`
**Durum: ✅ Built — Stabil**

- SUBOP logosuna tıklayınca `navigate("/")` — ana sayfaya yönlendiriyor
- `userRole === "admin"` olmayan kullanıcılarda Admin ve User Management gizleniyor
- Aktif sayfa `var(--color-secondary)` vurgusu

**M6 için notlar:** M6'da yeni sayfa eklenirse `NAV_ITEMS` array'ine satır eklenir.

---

### `components/PipelineCreationForm.tsx`
**Durum: ✅ Built — Canlı API Bağlı**

- `POST /api/pipelines/` — canlı submit
- Client-side validation: tüm zorunlu alanlar kontrol ediliyor
- 400 hatası → DSL Validation mesajı forma yansıtılıyor
- 422 hatası → `processing_purpose` alanına VERBIS hatası yansıtılıyor
- 201 başarı → "Pipeline başarıyla oluşturuldu!" confirmation gösterimi
- Loading state — submit sırasında buton disabled
- Spec alanları: `name`, `source`, `transformations`, `target`, `processing_purpose`, `data_subject_categories`, `transfer_recipients`

**M6 için notlar:** Form şu an herhangi bir sayfaya mount edilmemiş — PipelinesPage'e "Yeni Pipeline" butonu ile entegre edilmesi önerilir.

---

## 3. Sayfa Durumları

### `HomePage.tsx`
**Durum: ✅ Shell Wired — Canlı KPI Verisi**

| KPI Kartı | Kaynak | Durum |
|---|---|---|
| Active Pipelines | `GET /api/kpis` → `pipeline_count` | ✅ Canlı |
| Data Quality Score | `GET /api/kpis` → `average_quality_score` | ✅ Canlı — null ise "Henüz mevcut değil" |
| Records Processed Today | `GET /api/kpis` → `rows_processed_today` | ✅ Canlı |
| CDC Latency | — | ⏳ Mock — M7'de gelecek |

**M6 için notlar:** CDC Latency endpoint'i M7'de gelince `getKPISummary()` response'una `cdc_latency_ms` eklenmeli, `KPISummary` tipi güncellenmeli.

---

### `PipelinesPage.tsx`
**Durum: ✅ Full Wired — Canlı API**

| Zone | İçerik | Durum |
|---|---|---|
| Zone 1 — Filtre Bar | Pipeline ara, Tüm Zamanlar, Tüm Durumlar, Yenile | ✅ Fonksiyonel |
| Zone 2 — Sol Panel | Pipeline listesi (paginated) | ✅ Canlı — `GET /api/pipelines/` |
| Zone 3 — Detay Panel | Metadata, satır sayısı, execution log | ✅ Canlı — `GET /api/pipelines/{id}/runs/{run_id}` |

**Filtre özellikleri:**
- Arama (debounce 300ms), durum filtresi (running/succeeded/failed/pending), zaman filtresi (Son 1 Saat / 24 Saat / 7 Gün)
- Loading state ve error state mevcut

---

### Diğer Sayfalar — Shell Only ⏳

| Sayfa | Dosya | Durum | İçerik Milestone |
|---|---|---|---|
| DataQualityPage | `DataQualityPage.tsx` | Shell Only | M10 |
| LineageExplorerPage | `LineageExplorerPage.tsx` | Shell Only | M9 |
| CatalogBrowserPage | `CatalogBrowserPage.tsx` | Shell Only | M9 |
| BIReportsPage | `BIReportsPage.tsx` | Shell Only | M11 |
| AdminPage | `AdminPage.tsx` | Shell Only | M8 |
| UsersPage | `UsersPage.tsx` | Shell Only | M8 |

---

## 4. Design System Token Durumu

**Dosya:** `services/bi-dashboard/frontend/src/index.css`

| Token | Değer | Kullanım |
|---|---|---|
| `--color-primary` | `#1b3a6b` | Header, Sidebar, Filtre Bar arka plan |
| `--color-secondary` | `#2e75b6` | Aktif nav item |
| `--color-success` | `#2e7d32` | Completed badge, healthy KPI |
| `--color-warning` | `#e65100` | Warning badge, quarantine |
| `--color-danger` | `#c62828` | Failed badge, critical KPI |
| `--color-success-bg` | `rgba(46,125,50,0.1)` | ✅ M5'te eklendi |
| `--color-warning-bg` | `rgba(230,81,0,0.1)` | ✅ M5'te eklendi |
| `--color-danger-bg` | `rgba(198,40,40,0.1)` | ✅ M5'te eklendi |
| `--color-neutral-200/400/500` | — | Border, muted text |
| `--color-background` | `#f9fafb` | Sayfa arka planı |
| `--color-surface` | `#ffffff` | Kart arka planı |
| `--color-border` | `#dde4ee` | Genel border |
| `--color-row-alt` | `#ebf3fb` | Alternatif satır, info box |

---

## 5. M6 Frontend Öncelikleri

1. **`PipelineCreationForm` mount** — PipelinesPage'e "Yeni Pipeline" butonu ekle
2. **Connection ref'leri** — `.env`'e `SUBOP_CONN_PG_MAIN` ve `SUBOP_CONN_DW_MAIN` eklenince pipeline `succeeded` olacak
3. **Responsive tasarım** — Abdalla ile M6 başında kararlaştırıldı
4. **CORS güncellemesi** — Production URL'i için `allow_origins` güncellenmeli
5. **Catalog endpoint** — `getCatalogAssets()` mock'tan canlıya geçecek (M9)
6. **CDC Latency** — `getKPISummary()` response'una M7'de eklenecek
