export type LegalBasis =
  | "Consent"
  | "Contract"
  | "LegalObligation"
  | "VitalInterests"
  | "PublicTask"
  | "LegitimateInterest";

export type CanonicalType =
  | "INTEGER"
  | "BIGINT"
  | "DECIMAL"
  | "VARCHAR"
  | "TEXT"
  | "BOOLEAN"
  | "DATE"
  | "TIMESTAMP"
  | "JSON"
  | "BINARY";

export type ColumnRole =
  | "surrogate_key" // generated primary key of a dimension
  | "business_key" // the source's natural key
  | "attribute" // ordinary column; in a Type 2 dimension, overwritten in place (Type 1)
  | "tracked_attribute" // Type 2: a change closes the current row and adds a version
  | "measure" // fact only: the numbers to aggregate
  | "dimension_ref" // fact only: the source column used to look a dimension up
  | "foreign_key" // fact only: generated, points to a dimension's surrogate key
  | "scd_metadata" // valid_from, valid_to, is_current
  | "date_part"; // generated columns of a derived date dimension

export interface WarehouseColumn {
  name: string;
  role: ColumnRole;
  native_type: string | null; // source type, e.g. "numeric(12,2)"; null for generated columns
  canonical_type: CanonicalType; // through UniversalTypeMapper
  warehouse_type: string; // PostgreSQL DDL type in the dw schema, e.g. "NUMERIC(12,2)"
  references: string | null; // foreign_key only: "dw.dim_customer.customer_key"
}

export interface WarehouseTable {
  name: string; // "dim_customer"
  qualified_name: string; // "dw.dim_customer"
  role: "fact" | "dimension";
  source_table: string | null; // "cdc_demo.customers"; null for a derived dimension
  derived_from: { kind: "date"; column: string } | null;
  scd_type: 1 | 2 | null; // null for the fact table
  tracked_attributes: string[]; // [] unless scd_type is 2
  business_key: string[];
  measures: string[]; // [] for dimensions
  personal_data: boolean;
  legal_basis: LegalBasis | null; // never null when personal_data is true
  retention_policy_days: number | null; // never null when personal_data is true
  columns: WarehouseColumn[];
}

export interface WarehouseSchema {
  schema_id: string; // the definition name, e.g. "demo_orders_star"
  name: string;
  version: number; // always 1 in M8 (versioning deferred)
  description: string | null;
  target_schema: "dw";
  source: { connector_type: string; connection_ref: string };
  generated_at: string; // ISO 8601
  tables: WarehouseTable[]; // fact first, then dimensions in definition order
}
