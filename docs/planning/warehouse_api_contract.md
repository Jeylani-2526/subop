# Warehouse API Contract

**Task:** M8W28T2 · **Owner:** Abdalla · **For:** Beyza (M8W28T6, M8W28T7, M8W29T7)
**Status:** Contract, written before the code. Implemented in M8W29T1 (API) on top of
M8W28T3 (generator) · **Date:** 18 November 2026

The two endpoints behind the new `WarehousePage.tsx`. They are served by `subop-api` on
the same base URL as the pipeline and CDC routes, so `warehouseClient.ts` follows
`pipelinesClient.ts`'s `BASE_URL` convention, as `cdcClient.ts` does since PR #33:

```
VITE_API_BASE_URL ?? "http://localhost:8000/api"
```

## 1. Endpoints

| Function in `warehouseClient.ts` | Endpoint | Used by the page |
|---|---|---|
| `getWarehouseSchemas()` | `GET /warehouse/schemas` | Yes: Zones 1 and 2 |
| `generateWarehouseSchema(definition)` | `POST /warehouse/schemas/generate` | No. Generation is API-only in M8; the page is read-only |

**Not added:** `GET /warehouse/schemas/{id}/versions` (Architecture Section 6). Schema
versioning is deferred to the M9 window (Part B item 1). There is no stub, because a
placeholder would report a capability that doesn't exist.

## 2. Types

```ts
export type LegalBasis =
  | "Consent"
  | "Contract"
  | "LegalObligation"
  | "VitalInterests"
  | "PublicTask"
  | "LegitimateInterest";

export type CanonicalType =
  | "INTEGER" | "BIGINT" | "DECIMAL" | "VARCHAR" | "TEXT"
  | "BOOLEAN" | "DATE" | "TIMESTAMP" | "JSON" | "BINARY";

export type ColumnRole =
  | "surrogate_key"      // generated primary key of a dimension
  | "business_key"       // the source's natural key
  | "attribute"          // ordinary column; in a Type 2 dimension, overwritten in place (Type 1)
  | "tracked_attribute"  // Type 2: a change closes the current row and adds a version
  | "measure"            // fact only: the numbers to aggregate
  | "dimension_ref"      // fact only: the source column used to look a dimension up
  | "foreign_key"        // fact only: generated, points to a dimension's surrogate key
  | "scd_metadata"       // valid_from, valid_to, is_current
  | "date_part";         // generated columns of a derived date dimension

export interface WarehouseColumn {
  name: string;
  role: ColumnRole;
  native_type: string | null;      // source type, e.g. "numeric(12,2)"; null for generated columns
  canonical_type: CanonicalType;   // through UniversalTypeMapper
  warehouse_type: string;          // PostgreSQL DDL type in the dw schema, e.g. "NUMERIC(12,2)"
  references: string | null;       // foreign_key only: "dw.dim_customer.customer_key"
}

export interface WarehouseTable {
  name: string;                    // "dim_customer"
  qualified_name: string;          // "dw.dim_customer"
  role: "fact" | "dimension";
  source_table: string | null;     // "cdc_demo.customers"; null for a derived dimension
  derived_from: { kind: "date"; column: string } | null;
  scd_type: 1 | 2 | null;          // null for the fact table
  tracked_attributes: string[];    // [] unless scd_type is 2
  business_key: string[];
  measures: string[];              // [] for dimensions
  personal_data: boolean;
  legal_basis: LegalBasis | null;  // never null when personal_data is true
  retention_policy_days: number | null; // never null when personal_data is true
  columns: WarehouseColumn[];
}

export interface WarehouseSchema {
  schema_id: string;               // the definition name, e.g. "demo_orders_star"
  name: string;
  version: number;                 // always 1 in M8 (versioning deferred)
  description: string | null;
  target_schema: "dw";
  source: { connector_type: string; connection_ref: string };
  generated_at: string;            // ISO 8601
  tables: WarehouseTable[];        // fact first, then dimensions in definition order
}
```

`GET /warehouse/schemas` returns `WarehouseSchema[]`, and `[]` when nothing has been
generated yet. `POST /warehouse/schemas/generate` returns one `WarehouseSchema`.

## 3. Example: `GET /api/warehouse/schemas` after generating the demo

Built from `services/warehouse/definitions/demo_orders_star.json`. Use it as the base
for `warehouseFixtures.ts`.

```json
[
  {
    "schema_id": "demo_orders_star",
    "name": "demo_orders_star",
    "version": 1,
    "description": "Orders star schema built from the M7 CDC demo tables.",
    "target_schema": "dw",
    "source": { "connector_type": "postgresql", "connection_ref": "pg-main" },
    "generated_at": "2026-11-20T14:05:12.481203+00:00",
    "tables": [
      {
        "name": "fact_orders",
        "qualified_name": "dw.fact_orders",
        "role": "fact",
        "source_table": "cdc_demo.orders",
        "derived_from": null,
        "scd_type": null,
        "tracked_attributes": [],
        "business_key": ["id"],
        "measures": ["amount"],
        "personal_data": true,
        "legal_basis": "Contract",
        "retention_policy_days": 3650,
        "columns": [
          { "name": "id", "role": "business_key", "native_type": "bigint", "canonical_type": "BIGINT", "warehouse_type": "BIGINT", "references": null },
          { "name": "customer_id", "role": "dimension_ref", "native_type": "bigint", "canonical_type": "BIGINT", "warehouse_type": "BIGINT", "references": null },
          { "name": "status", "role": "attribute", "native_type": "varchar(32)", "canonical_type": "VARCHAR", "warehouse_type": "VARCHAR(32)", "references": null },
          { "name": "amount", "role": "measure", "native_type": "numeric(12,2)", "canonical_type": "DECIMAL", "warehouse_type": "NUMERIC(12,2)", "references": null },
          { "name": "created_at", "role": "dimension_ref", "native_type": "timestamptz", "canonical_type": "TIMESTAMP", "warehouse_type": "TIMESTAMPTZ", "references": null },
          { "name": "customer_key", "role": "foreign_key", "native_type": null, "canonical_type": "BIGINT", "warehouse_type": "BIGINT", "references": "dw.dim_customer.customer_key" },
          { "name": "date_key", "role": "foreign_key", "native_type": null, "canonical_type": "INTEGER", "warehouse_type": "INTEGER", "references": "dw.dim_date.date_key" }
        ]
      },
      {
        "name": "dim_customer",
        "qualified_name": "dw.dim_customer",
        "role": "dimension",
        "source_table": "cdc_demo.customers",
        "derived_from": null,
        "scd_type": 2,
        "tracked_attributes": ["city"],
        "business_key": ["id"],
        "measures": [],
        "personal_data": true,
        "legal_basis": "Contract",
        "retention_policy_days": 3650,
        "columns": [
          { "name": "customer_key", "role": "surrogate_key", "native_type": null, "canonical_type": "BIGINT", "warehouse_type": "BIGINT", "references": null },
          { "name": "id", "role": "business_key", "native_type": "bigint", "canonical_type": "BIGINT", "warehouse_type": "BIGINT", "references": null },
          { "name": "name", "role": "attribute", "native_type": "varchar(64)", "canonical_type": "VARCHAR", "warehouse_type": "VARCHAR(64)", "references": null },
          { "name": "city", "role": "tracked_attribute", "native_type": "varchar(64)", "canonical_type": "VARCHAR", "warehouse_type": "VARCHAR(64)", "references": null },
          { "name": "valid_from", "role": "scd_metadata", "native_type": null, "canonical_type": "TIMESTAMP", "warehouse_type": "TIMESTAMPTZ", "references": null },
          { "name": "valid_to", "role": "scd_metadata", "native_type": null, "canonical_type": "TIMESTAMP", "warehouse_type": "TIMESTAMPTZ", "references": null },
          { "name": "is_current", "role": "scd_metadata", "native_type": null, "canonical_type": "BOOLEAN", "warehouse_type": "BOOLEAN", "references": null }
        ]
      },
      {
        "name": "dim_date",
        "qualified_name": "dw.dim_date",
        "role": "dimension",
        "source_table": null,
        "derived_from": { "kind": "date", "column": "created_at" },
        "scd_type": 1,
        "tracked_attributes": [],
        "business_key": ["full_date"],
        "measures": [],
        "personal_data": false,
        "legal_basis": null,
        "retention_policy_days": null,
        "columns": [
          { "name": "date_key", "role": "surrogate_key", "native_type": null, "canonical_type": "INTEGER", "warehouse_type": "INTEGER", "references": null },
          { "name": "full_date", "role": "date_part", "native_type": null, "canonical_type": "DATE", "warehouse_type": "DATE", "references": null },
          { "name": "year", "role": "date_part", "native_type": null, "canonical_type": "INTEGER", "warehouse_type": "INTEGER", "references": null },
          { "name": "quarter", "role": "date_part", "native_type": null, "canonical_type": "INTEGER", "warehouse_type": "INTEGER", "references": null },
          { "name": "month", "role": "date_part", "native_type": null, "canonical_type": "INTEGER", "warehouse_type": "INTEGER", "references": null },
          { "name": "day", "role": "date_part", "native_type": null, "canonical_type": "INTEGER", "warehouse_type": "INTEGER", "references": null },
          { "name": "day_of_week", "role": "date_part", "native_type": null, "canonical_type": "INTEGER", "warehouse_type": "INTEGER", "references": null }
        ]
      }
    ]
  }
]
```

## 4. Rules the response follows

These rules are what M8W28T3 builds and M8W29T1 serves. Fixtures can rely on them.

| Rule | Detail |
|---|---|
| Column order | Surrogate key first, then the definition's columns in order, then foreign keys, then SCD metadata |
| Surrogate key name | `dim_customer` → `customer_key`. The fact's foreign key uses the same name |
| Type 2 dimensions | Add `valid_from`, `valid_to` (null on the current row) and `is_current` |
| Type 1 dimensions | Get a surrogate key but no SCD metadata |
| Derived date dimension | `date_key` is `YYYYMMDD` as an integer (20 November 2026 → `20261120`). `day_of_week` is ISO: 1 = Monday, 7 = Sunday. `business_key` is `["full_date"]` |
| Fact table | Keeps its source columns. Each dimension gets one `foreign_key` column. The fact's primary key is its `business_key`; it has no surrogate key |
| `warehouse_type` | Length and precision come from the native type (`VARCHAR(32)`, `NUMERIC(12,2)`). Every timestamp is stored as `TIMESTAMPTZ` |
| Compliance fields | When `personal_data` is true, `legal_basis` and `retention_policy_days` are never null. Validation guarantees it |

## 5. What the page should show

| What the UI shows | Condition |
|---|---|
| Empty state ("no schema generated yet") | The response is `[]` |
| Fact or dimension label | `tables[i].role` |
| SCD Type 1 / Type 2 badge | `scd_type`; no badge on the fact (`null`) |
| "Derived" marker | `derived_from !== null` (for `dim_date`) |
| Compliance chips | `personal_data`; `legal_basis` through a label key (six values, Section 6); `retention_policy_days` as "3650 days" |
| Column table | `name`, `native_type` (show "—" when null), `canonical_type`, and `role` if useful |

## 6. Labels needed in `tr.ts` and `en.ts`

One key per `LegalBasis` value (six in total), plus the two SCD badges, the derived marker,
the personal-data chip and the retention label. Turkish is the default. These are the
KVKK article 5(2) grounds. Suggested Turkish labels, which you may adjust:

| Value | en | tr |
|---|---|---|
| `Consent` | Consent | Açık rıza |
| `Contract` | Contract | Sözleşmenin ifası |
| `LegalObligation` | Legal obligation | Hukuki yükümlülük |
| `VitalInterests` | Vital interests | Hayati menfaat |
| `PublicTask` | Public task | Kamu görevi |
| `LegitimateInterest` | Legitimate interest | Meşru menfaat |

## 7. `POST /api/warehouse/schemas/generate`

**Body:** a metadata definition, exactly the shape of `demo_orders_star.json`. Validated
by the Pydantic models in `services/warehouse/metadata.py`.

| Status | Body | When |
|---|---|---|
| 201 | `WarehouseSchema` | Generated now |
| 200 | `WarehouseSchema` | Already generated from an identical definition. Nothing changes |
| 409 | error, `WAREHOUSE_SCHEMA_CONFLICT` | A schema with this name and version exists with a different definition. Changing a schema is versioning, which is deferred |
| 422 | error, `WAREHOUSE_METADATA_INVALID` | The definition fails validation |

A 422 lists **every** problem in `message`, as `path: reason` pairs joined by `"; "`,
for example:

```json
{
  "error_code": "WAREHOUSE_METADATA_INVALID",
  "message": "dimensions[0].legal_basis: required when personal_data is true (C03); dimensions[0].tracked_attributes[0]: 'country' is not a column of dim_customer",
  "connector_type": null,
  "retryable": false
}
```

Shape problems (a wrong type, an unknown field, an `scd_type` other than 1 or 2) are
reported first. The cross-field checks run once the shape is valid.

## 8. Errors

Same four-field envelope as the pipeline and CDC routes: `error_code`, `message`,
`connector_type` (always `null` here) and `retryable`.

| Status | `error_code` | When | `retryable` |
|---|---|---|---|
| 422 | `WAREHOUSE_METADATA_INVALID` | POST: the definition fails validation | false |
| 409 | `WAREHOUSE_SCHEMA_CONFLICT` | POST: same name and version, different definition | false |
| 500 | `WAREHOUSE_GENERATION_FAILED` | POST: DDL failed in the database | false |
| 503 | connector `error_code` | Warehouse database not reachable | as reported |

For the page, only `GET` matters. On any error, show one generic error line. Don't fall
back to fixtures once the live swap (M8W29T7) has happened.

## 9. Decisions recorded

- **`schema_id` is the definition name.** With versioning deferred there is one version
  per name, so a separate numeric id would add nothing.
- **A derived dimension declares no columns.** `dim_date` has `derived_from` instead of
  `columns`, and the generator defines its columns (decided 18 November).
- **`fact_orders` is personal data** (`Contract`, 3650 days), because `customer_id` links
  each order to a person. `dim_customer` uses the same values (decided 18 November).
- **Source types** are limited to the databases `UniversalTypeMapper` can map:
  `postgresql`, `mysql`, `mssql`, `sqlite`.
