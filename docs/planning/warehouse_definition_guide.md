# Warehouse Definition Guide

**Module:** Metadata-Driven Data Warehouse (Goal G5) · **Since:** M8, 24 November 2026
**Files:** `services/warehouse/definitions/*.json` · **Rules in code:** `services/warehouse/metadata.py`

A definition describes one star schema. The generator turns it into warehouse tables,
and the loader fills them, without hand-written SQL. This guide is the reference for
writing one; it was added after the M8W29T3 KPI run showed the format could only be
learned from the code.

## 1. The Shape in One Look

```json
{
  "name": "demo_orders_star",
  "version": 1,
  "description": "optional free text",
  "source": { "connector_type": "postgresql", "connection_ref": "pg-main" },
  "fact": { ... one fact table ... },
  "dimensions": [ { ... }, { ... } ]
}
```

| Key | Meaning |
|---|---|
| `name` | lowercase identifier; also the `schema_id` in the registry and the API |
| `version` | `1` in M8 (schema versioning is deferred) |
| `source` | where the source tables live: a connector type and a connection ref (`SUBOP_CONN_<REF>`) |

## 2. Columns: Three Ways to Give Them

Every sourced table (the fact, and each dimension with a `source_table`) needs its
columns. Since 24 November the generator can read them from the source database.

| You write | What happens | When to use |
|---|---|---|
| nothing (no `"columns"` key) | every column of the source table, with its source type, in source order | the warehouse table keeps all source columns |
| `"columns": ["a", "b"]` | only these columns; types read from the source | the warehouse table keeps some columns |
| `"columns": {"a": "bigint", "b": "varchar(32)"}` | exactly these columns and types; the source is not read | the source is not reachable, or is not PostgreSQL |

Reading from the source works for **PostgreSQL** sources today. For other sources, give
each column with its native type.

## 3. The Fact Table

```json
"fact": {
  "name": "fact_orders",
  "source_table": "cdc_demo.orders",
  "columns": ["id", "customer_id", "status", "amount", "created_at"],
  "business_key": ["id"],
  "measures": ["amount"],
  "dimension_keys": { "customer_id": "dim_customer", "created_at": "dim_date" },
  "personal_data": true,
  "legal_basis": "Contract",
  "retention_policy_days": 3650
}
```

| Key | Meaning |
|---|---|
| `source_table` | `schema.table` in the source |
| `business_key` | the column(s) that identify a row; becomes the fact's primary key |
| `measures` | the numbers to add up; each must be a column |
| `dimension_keys` | fact column → dimension name; each becomes a foreign key to that dimension |
| `personal_data`, `legal_basis`, `retention_policy_days` | see Section 5 |

## 4. Dimensions

**A sourced dimension**, SCD Type 1 (changes overwrite) or Type 2 (changes keep history):

```json
{
  "name": "dim_customer",
  "source_table": "cdc_demo.customers",
  "business_key": ["id"],
  "scd_type": 2,
  "tracked_attributes": ["city"],
  "personal_data": true,
  "legal_basis": "Contract",
  "retention_policy_days": 3650
}
```

| Key | Meaning |
|---|---|
| `business_key` | exactly one column in M8 |
| `scd_type` | `1` or `2` |
| `tracked_attributes` | Type 2 only: the columns whose change creates a new version; other columns are overwritten |

**A derived date dimension**, built from a date or timestamp column of the fact:

```json
{
  "name": "dim_date",
  "derived_from": { "kind": "date", "column": "created_at" },
  "scd_type": 1,
  "personal_data": false
}
```

No `columns` and no `business_key`: the generator defines them.

## 5. Compliance Fields (KVKK/GDPR)

Every table says whether it holds personal data. If `personal_data` is `true`, both of
these are required:

| Key | Values |
|---|---|
| `legal_basis` | `Consent`, `Contract`, `LegalObligation`, `VitalInterests`, `PublicTask`, `LegitimateInterest` (C03) |
| `retention_policy_days` | a whole number of days, above 0 (C09) |

## 6. What the Generator Adds for You

| For | Added |
|---|---|
| A sourced dimension | surrogate key `<name without dim_>_key`, `BIGINT` identity, primary key |
| A Type 1 dimension | `UNIQUE` on the business key |
| A Type 2 dimension | `valid_from`, `valid_to`, `is_current`, and a unique index on the business key for current rows |
| A derived date dimension | `<x>_key` (`YYYYMMDD`), `full_date`, `year`, `quarter`, `month`, `day`, `day_of_week` |
| The fact | one foreign-key column per dimension, named like its surrogate key |

Source types become warehouse types through the Universal Type Mapper, for example
`varchar(32)` → `VARCHAR(32)`, `numeric(12,2)` → `NUMERIC(12,2)`, any timestamp →
`TIMESTAMPTZ`.

## 7. Running It

```bash
# check and print the SQL, no database changes (needs the source only for read columns)
python -m services.warehouse.schema_generator <definition.json> --dry-run
# generate into dw
python -m services.warehouse.schema_generator <definition.json>
# load from the source
python -m services.warehouse.scd_loader <definition.json>
```

Or `POST /api/warehouse/schemas/generate` with the definition as the body.

Every mistake is reported with its place in the file, for example
`dimensions[1].legal_basis: required when personal_data is true (C03)`. Fix the
named field and run it again.
