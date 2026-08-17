# ETL Engine API & Pipeline DSL Specification (v1)

**Owner:** Abdullah · **Status:** Draft — Week 14 (M5W14T1)

**Builds on:** `etl_engine_contracts_v1.md` 

---

## 1. Purpose & Scope

This document specifies the two API endpoints named in `etl_engine_contracts_v1.md` Section 2 (`POST /api/pipelines/`) and Section 3 (`GET /api/pipelines/{id}/runs/{run_id}`), plus the JSON Pipeline DSL schema those endpoints carry. It is deliberately concrete enough to build against without further clarification — field names, types, and required/optional status are fixed here.

Per `etl_engine_contracts_v1.md` Section 9, this document does **not** specify:
- Transformation *execution* semantics (what each transformation type actually does at runtime) — only its wire shape.
- Retry/backoff timing values.
- CDC schema-drift handling.

Those remain later M5 implementation decisions.

---

## 2. Pipeline DSL Schema

The DSL is the JSON body of `POST /api/pipelines/`, matching `etl_engine_contracts_v1.md` Section 2's "Pipeline definition — source, transformations, target, `processing_purpose`."

```json
{
  "name": "string",
  "source": {
    "connector_type": "postgresql | mysql | mssql | mongodb",
    "connection_ref": "string",
    "object": "string",
    "query": "string | null"
  },
  "transformations": [
    {
      "step_id": "string",
      "type": "string",
      "params": { }
    }
  ],
  "target": {
    "connector_type": "postgresql | mysql | mssql | mongodb",
    "connection_ref": "string",
    "object": "string",
    "write_mode": "upsert | append"
  },
  "processing_purpose": "string",
  "data_subject_categories": ["string"],
  "transfer_recipients": ["string"]
}
```

### 2.1 Field reference

| Field | Type | Required | Notes |
|---|---|---|---|
| `name` | string | Yes | Human-readable pipeline name, unique per workspace. |
| `source.connector_type` | enum | Yes | Matches Abstraction Layer's supported connector types (Section 4: source-agnostic — PostgreSQL, MySQL, MSSQL, MongoDB). |
| `source.connection_ref` | string | Yes | Reference to a pre-registered connection (credentials never live in the DSL). |
| `source.object` | string | Yes | Table name (relational) or collection name (MongoDB). |
| `source.query` | string \| null | No | Optional raw filter/query passed through to the Abstraction Layer; `null` means "full object read." |
| `transformations` | **ordered array** | Yes (may be empty `[]`) | Executed in array order — order is semantically meaningful, not just presentational. Each step's `type` and `params` shape is transformation-specific and out of scope for this document (Section 9). `step_id` is required on every step so Lineage (Section 6 of the contracts doc) can reference a specific step per-column. |
| `target.connector_type` | enum | Yes | Same enum as `source.connector_type`. |
| `target.connection_ref` | string | Yes | Same pattern as source. |
| `target.object` | string | Yes | Destination table/collection. |
| `target.write_mode` | enum | Yes | `upsert` (default for `dim_*`/`fact_*` per contracts Section 3) or `append`. |
| `processing_purpose` | string | Yes | Read once at creation against Security & Compliance (Module 10) — contracts Section 2. Pipeline creation fails if this doesn't resolve to a completed VERBİS registration. |
| `data_subject_categories` | array\<string\> | Yes | Same read-once-at-creation compliance check. |
| `transfer_recipients` | array\<string\> | Yes (may be empty `[]`) | Same compliance check; empty array is valid if there are no transfers. |

**Assumption flagged for your review:** `source.object` / `target.object` as a single string covers the common relational-table / Mongo-collection case, but doesn't cover a source defined by an arbitrary join across objects. I've left `source.query` as the escape hatch for that (raw filter, not full custom SQL) rather than adding join structure to the DSL — flag if you want join support at this stage instead.

---

## 3. `POST /api/pipelines/`

Creates a pipeline. Triggers the read-once-at-creation compliance check (contracts Section 2) — this is the only point at which Security & Compliance is queried; runs never re-check it.

### 3.1 Request

- **Body:** the Pipeline DSL (Section 2 above).

### 3.2 Response — `201 Created`

```json
{
  "id": "string",
  "name": "string",
  "status": "created",
  "created_at": "ISO 8601 string",
  "source": { "...": "echoed from request" },
  "transformations": [ "...": "echoed from request" ],
  "target": { "...": "echoed from request" }
}
```

### 3.3 Error responses

| Status | Condition |
|---|---|
| `400` | DSL fails schema validation (missing required field, invalid enum value, malformed `transformations` array). |
| `422` | Compliance check fails — `processing_purpose` / `data_subject_categories` / `transfer_recipients` do not resolve to a completed VERBİS registration record (Module 10). Pipeline is **not** created. |
| `500` | Unhandled server error. |

All error bodies use the shared error envelope in Section 5.

---

## 4. `GET /api/pipelines/{id}/runs/{run_id}`

Returns run status and logs (contracts Section 3: "Run status and logs").

### 4.1 Response — `200 OK`

```json
{
  "run_id": "string",
  "pipeline_id": "string",
  "status": "pending | running | succeeded | completed_with_quarantine | failed | cancelled",
  "started_at": "ISO 8601 string | null",
  "finished_at": "ISO 8601 string | null",
  "rows_read": "integer",
  "rows_written": "integer",
  "rows_quarantined": "integer",
  "quality_score": "number | null",
  "logs": ["string"],
  "error": { "...": "error envelope, present only when status is failed" }
}
```

### 4.2 Proposed run status enum

You asked me to propose this set — derived directly from the Data Quality contract (contracts Section 8) and Section 3's output shapes, so every status has a concrete source condition rather than being invented:

| Status | When it applies |
|---|---|
| `pending` | Run accepted, not yet started (queued). |
| `running` | In progress. |
| `succeeded` | Completed, Data Quality raised no fatal or recoverable violations. |
| `completed_with_quarantine` | Completed, but Data Quality's **recoverable** severity quarantined some rows (contracts Section 8: "quarantines the offending rows... remainder of the batch proceeds; run status reflects a completed run with a quarantine count"). `rows_quarantined` will be > 0. |
| `failed` | Data Quality's **fatal** severity halted the run before the Warehouse write (contracts Section 8), or an unrecoverable `ConnectorError` (`retryable: false`) occurred. `error` field is populated. |
| `cancelled` | Run was cancelled before completion (e.g. manually, or system shutdown). Not directly named in the contracts doc — flagging this as my addition in case you'd rather omit it for v1 and add it later. |

**Assumption flagged for your review:** `cancelled` isn't derived from the contracts doc — I added it because run-status enums generally need a non-terminal-failure exit state, but if you want to keep v1 strictly to what Section 8 specifies, I can drop it and Omer's scaffold can add it later without a breaking change (it's purely additive to the enum).

### 4.3 Error responses

| Status | Condition |
|---|---|
| `404` | `pipeline_id` or `run_id` not found. |

---

## 5. Error Envelope (shared across both endpoints)

Per your decision, this mirrors the `ConnectorError` shape from `etl_engine_contracts_v1.md` Section 4 (`{error_code, message, connector_type, retryable}`) for consistency across the whole system — an API consumer handles ETL Engine API errors and Abstraction Layer errors the same way.

```json
{
  "error_code": "string",
  "message": "string",
  "connector_type": "postgresql | mysql | mssql | mongodb | null",
  "retryable": "boolean"
}
```

- `connector_type` is `null` when the error originates in the API/ETL Engine layer itself rather than from a specific connector (e.g. a `400` schema validation error on `POST /api/pipelines/` — there's no connector involved yet at that point).
- `retryable` follows the same semantics as the Abstraction Layer contract: `false` for anything ETL Engine's existing recoverable/fatal classification (contracts Section 5.1) treats as fatal, including `unsupported` type-mapping errors (contracts Section 7.2) surfaced unchanged through this envelope.

---

## 6. Explicitly Out of Scope (per contracts Section 9)

- Transformation `type`/`params` execution semantics — this document fixes the *wire shape* (`step_id`, `type`, `params`, ordered array) but not what any given `type` does at runtime.
- Retry/backoff timing for `retryable: true` errors.
- CDC-triggered pipeline runs — this spec covers the API-triggered batch path only; the CDC/Kafka streaming path (contracts Section 5) does not go through `POST /api/pipelines/`.

---

