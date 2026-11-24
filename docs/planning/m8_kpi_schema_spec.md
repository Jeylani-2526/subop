# M8 KPI Target Schema Specification — `kpi_shipments_star`

**Task:** M8W29T3 · **Owner:** Abdalla · **Date:** 23 November 2026
**Purpose:** The one written spec for the DW schema automation KPI (kickoff notes Part B
item 4b). Committed **before** either half starts. Both halves build exactly this schema:
the generated half by writing a metadata definition and running the generator, the manual
half by writing `CREATE TABLE` statements by hand.

It is deliberately **not** the demo schema: different source system, different tables,
three dimensions instead of two, and a Type 1 dimension that is not derived. The target
has 4 tables and 26 columns; Part B asks for about 20–25, and the derived date dimension
alone has 7 fixed columns. Kept at 26 (decided 23 November): the slightly larger schema
makes the manual half longer, not shorter, so it cannot flatter the result.

## 1. Business Need

A logistics company wants to analyse **shipment weight and freight cost** by **carrier**,
by **depot** and by **ship date**. Depots sometimes move to another city, and past
shipments must stay with the city the depot was in at the time, so the depot's city is
tracked with history. The depot manager's name is personal data.

## 2. Source System

PostgreSQL, connection `pg-main` (`connector_type: postgresql`). Three source tables in
schema `logistics`:

| Source table | Column | Native type | Note |
|---|---|---|---|
| `logistics.shipments` | `shipment_id` | `bigint` | primary key |
| | `carrier_code` | `varchar(8)` | refers to a carrier |
| | `depot_id` | `integer` | refers to a depot |
| | `shipped_at` | `timestamptz` | when the shipment left |
| | `weight_kg` | `numeric(10,3)` | |
| | `freight_cost` | `numeric(12,2)` | |
| `logistics.carriers` | `carrier_code` | `varchar(8)` | primary key |
| | `carrier_name` | `varchar(80)` | |
| `logistics.depots` | `depot_id` | `integer` | primary key |
| | `city` | `varchar(60)` | changes over time; history needed |
| | `manager_name` | `varchar(80)` | personal data; corrections only, no history |

The source tables do not need to exist for this KPI: generation reads only the definition.

## 3. Target Star Schema

Name `kpi_shipments_star`, version 1.

| Target table | Role | Built from | Business key | Detail |
|---|---|---|---|---|
| `fact_shipments` | fact | `logistics.shipments`, all six columns | `shipment_id` | measures `weight_kg`, `freight_cost`; dimension keys `carrier_code` → `dim_carrier`, `depot_id` → `dim_depot`, `shipped_at` → `dim_ship_date` |
| `dim_carrier` | dimension, SCD Type 1 | `logistics.carriers`, both columns | `carrier_code` | |
| `dim_depot` | dimension, SCD Type 2 | `logistics.depots`, all three columns | `depot_id` | `city` tracked (Type 2); `manager_name` overwritten (Type 1) |
| `dim_ship_date` | dimension, derived date | `fact_shipments.shipped_at` | (generated) | standard date columns |

**Compliance (KVKK/GDPR, C03 and C09):**

| Table | Personal data | Legal basis | Retention |
|---|---|---|---|
| `fact_shipments` | no | — | — |
| `dim_carrier` | no | — | — |
| `dim_depot` | **yes** (`manager_name`) | `LegitimateInterest` | 1825 days |
| `dim_ship_date` | no | — | — |

These values belong in the metadata definition. Plain DDL has no place for them, so they
are not part of the equality check.

## 4. Warehouse Conventions

These are SUBOP's existing warehouse rules (`docs/planning/warehouse_api_contract.md`
Section 4, as implemented in `schema_generator.py`). The generated half gets them
automatically; the manual half must apply them by hand.

| Rule | Detail |
|---|---|
| Schema | generated half → `dw`; manual half → `dw_manual` |
| Surrogate key name | `dim_<x>` → `<x>_key`, e.g. `dim_depot` → `depot_key` |
| Surrogate key, sourced dimension | `BIGINT GENERATED ALWAYS AS IDENTITY`, the primary key |
| Surrogate key, derived date dimension | `INTEGER` (the date as `YYYYMMDD`), the primary key, not identity |
| Source column types | `bigint` → `BIGINT`; `integer` → `INTEGER`; `varchar(n)` → `VARCHAR(n)`; `numeric(p,s)` → `NUMERIC(p,s)`; `timestamptz` → `TIMESTAMPTZ` |
| Nullability | business key columns `NOT NULL`; every other source column nullable |
| Type 2 columns | `valid_from TIMESTAMPTZ NOT NULL`, `valid_to TIMESTAMPTZ` (nullable), `is_current BOOLEAN NOT NULL`, after the source columns |
| Type 1 dimension | `UNIQUE` on its business key |
| Type 2 dimension | unique index on its business key `WHERE is_current` |
| Derived date dimension | `<x>_key INTEGER`, `full_date DATE`, `year`, `quarter`, `month`, `day`, `day_of_week` (all `INTEGER`); all `NOT NULL`; `UNIQUE (full_date)` |
| Fact table | primary key = its business key; no surrogate key; one foreign-key column per dimension, named like that dimension's surrogate key, same type, nullable, `REFERENCES` that key |

## 5. Equality Check

After both halves, `services/warehouse/schema_compare.py` compares the four tables in `dw`
and `dw_manual`:

```bash
python -m services.warehouse.schema_compare dw dw_manual fact_shipments dim_carrier dim_depot dim_ship_date
```

**Pass/fail** (Part B item 4b): tables, columns, types, nullability, primary keys and
foreign keys must be identical. Column order is not compared. Identity columns and unique
constraints or indexes are listed for information but do not decide the result.

## 6. Timing Rules

From Part B item 4b, plus rules 3, 4 and 5 made explicit on 23 November, before either half started.

1. This spec is read **once, untimed**, before the first half.
2. **Generated half first**, then manual. Abdalla does both.
3. Each half is timed from its **first keystroke** until **its four tables exist without
   errors**. Fixing errors counts. Start and end are UTC timestamps taken in the terminal
   with `date -u +%H:%M:%S.%3N`: just before the first keystroke, and right after the
   successful run. The record quotes those lines verbatim.
   - Generated: writing the JSON definition plus running the generator.
   - Manual: writing the DDL plus running it.
4. **Decided 23 November:** if the equality check then finds a difference, the half at
   fault is corrected and its clock **resumes** for the correction. Both figures are
   recorded: time to first error-free run, and time to an identical schema. The KPI uses
   the second, so each half is measured to a correct result.
5. **Decided 23 November:** both halves start from an **empty file**. No templates and no
   copying: not from `demo_orders_star.json`, the tests, earlier DDL, or the other half.
   This spec may stay open during both halves; consulting it is part of the timed work.
6. **Pass rule:** generated time ≤ 20% of manual time. The ratio is recorded unrounded.
