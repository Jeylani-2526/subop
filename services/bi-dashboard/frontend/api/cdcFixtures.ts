// services/bi-dashboard/frontend/api/cdcFixtures.ts
// W23 fixture modülü — W24'te kaldırılır, cdcClient.ts live API'ye geçer.
//
// Buradaki üç olay, M7W23T13'te Mert'in gerçekten yakalayıp
// tests/fixtures/cdc/ altına commit edeceği üç envelope'un birebir karşılığı:
//   • tek publication, tek tablo: cdc_demo.orders
//   • tek connector: subop-postgres-cdc
//   • insert → update → delete, hepsi AYNI satır üstünde
//     (services/cdc/cdc_demo_changes.py --all tam olarak bunu üretiyor)
//
// Not — snapshot (op: "r") olayları gerçek ve topic'te ilk onlar geliyor:
// Debezium'un snapshot.mode varsayılanı "initial", yani connector ilk
// kurulduğunda üç seed satırını READ olayı olarak yayınlıyor. Burada yoklar
// çünkü bu dosya T13'ün yakaladığı üç olayı yansıtıyor. StatusBadge'deki
// snapshot rengi ölü kod değil — W24'te canlı veriye geçince görünecek.

import type { CDCChangeEvent, CDCConnectorStatus } from "./cdcTypes";

// --- Zaman çizgisi ---------------------------------------------------------
// Gerçek çalıştırmada insert/update/delete arası ~30 ms
// (Abdalla'nın makinesinde ölçüldü: 551 → 582 → 599 ms).

const INSERT_MS = Date.now() - 42_000;
const UPDATE_MS = INSERT_MS + 31;
const DELETE_MS = INSERT_MS + 48;

const iso = (ms: number): string => new Date(ms).toISOString();

// --- Satır şekli -----------------------------------------------------------
// cdc_demo.orders'ın altı kolonu. REPLICA IDENTITY FULL sayesinde UPDATE ve
// DELETE olaylarında `before` bloğu da altı kolonun hepsini taşır — sadece id
// değil. (id-only before, M7W23T1 ve M7W23T13'ün elemeye çalıştığı hatadır.)
//
// amount string geliyor çünkü connector config'inde
// decimal.handling.mode=string var; precise modda base64 gelirdi.

const DEMO_ROW_PENDING = {
  id: 4,
  customer_id: 9001,
  status: "pending",
  amount: "149.90",
  created_at: iso(INSERT_MS),
  updated_at: iso(INSERT_MS),
};

const DEMO_ROW_SHIPPED = {
  ...DEMO_ROW_PENDING,
  status: "shipped",
  updated_at: iso(UPDATE_MS),
};

// --- Değişiklik olayları ---------------------------------------------------
// Yeniden eskiye sıralı. latency_ms BİLEREK yok: latency_store.py W24-25'te
// geliyor (CDC Design Note Section 2.3), yani bu hafta ölçülmüş bir gecikme
// değeri yok. CDCPage zaten `latency_ms != null` kontrolü yaptığı için kolon
// kendiliğinden "—" gösteriyor ve üstteki Gecikme Özeti kartlarıyla tutarlı
// oluyor.

export const CDC_CHANGE_EVENTS: CDCChangeEvent[] = [
  {
    op: "delete",
    table: "cdc_demo.orders",
    before: DEMO_ROW_SHIPPED,
    after: null,
    ts_ms: DELETE_MS,
  },
  {
    op: "update",
    table: "cdc_demo.orders",
    before: DEMO_ROW_PENDING,
    after: DEMO_ROW_SHIPPED,
    ts_ms: UPDATE_MS,
  },
  {
    op: "insert",
    table: "cdc_demo.orders",
    before: null,
    after: DEMO_ROW_PENDING,
    ts_ms: INSERT_MS,
  },
];

// --- Connector durumu ------------------------------------------------------
// M7'de tek connector var. MySQL / MSSQL / Oracle için CDC connector'ı ne
// kuruldu ne de planlandı — M7W23T1 doğruladı ki Debezium'da yalnızca
// io.debezium.connector.postgresql.PostgresConnector yüklü.
//
// connector_id, .env'deki DEBEZIUM_CONNECTOR_NAME ile birebir aynı; W24'te
// endpoint Kafka Connect'ten bu ismi döndürecek.
//
// lag_ms null: ölçüm altyapısı henüz yok, uydurma bir sayı yazmıyoruz.

export const CDC_CONNECTOR_STATUSES: CDCConnectorStatus[] = [
  {
    connector_id: "subop-postgres-cdc",
    connector_name: "subop-postgres-cdc",
    state: "RUNNING",
    last_event_ts_ms: DELETE_MS,
    lag_ms: null,
  },
];
