# CDC Test Fixtures

Recorded Debezium change event envelopes for `tests/test_cdc_normalizer.py`
(M7W23T5).

The suite runs entirely from these files. No live Kafka, Debezium or
PostgreSQL connection is used — deliberate, because `ci.yml`'s `postgres:15`
service has no `command:` override and so runs at `wal_level=replica`, which
cannot support logical decoding. A test needing a real CDC connection would
turn `develop` red on the first push.

## Captured from a live connector — M7W23T13

| File | Operation |
|---|---|
| `insert.json` | one INSERT against `cdc_demo.orders` |
| `update.json` | one UPDATE setting `status='shipped'` |
| `delete.json` | one DELETE |

**Placeholders of the correct shape are committed now** so the suite is
runnable before M7W23T13 lands. They are hand-reconstructed, not captured.
Replace each file with a real envelope, keeping the filename — the tests read
their expected values out of the fixture itself (ids, timestamps, LSNs,
transaction ids), so no test needs editing when they are replaced.

Capture the **full message**, both `schema` and `payload` blocks. The
`schema` block is what drift detection reads; a payload-only capture leaves
the drift tests unable to run.

### What the real envelopes must show

Two things are checked on capture, and both trace back to earlier tasks:

- `payload.before` **fully populated** on `update.json` and `delete.json`,
  not an `id` only. An id-only `before` means `REPLICA IDENTITY FULL` did not
  take effect, contradicting M7W23T1's verified `relreplident = f`.
- Column schemas carrying `__debezium.source.column.type`. This comes from
  `column.propagate.source.type` in the M7W23T12 connector config. Without
  it the schema block holds only Connect types, under which
  `varchar(32)` → `varchar(64)` and `numeric(12,2)` → `numeric(14,4)` are
  both invisible to drift detection.

`test_captured_fixtures_carry_native_types` and
`test_before_is_fully_populated` fail loudly if either is missing, which is
the intended signal rather than a nuisance.

## Hand-authored

Each drift fixture differs from `insert.json` in exactly one way, so a
failure names the change responsible.

| File | What it represents |
|---|---|
| `snapshot_read.json` | `op: "r"` — Debezium's initial snapshot read |
| `truncate.json` | `op: "t"` — TRUNCATE, which a default publication does publish (`pubtruncate = t`) |
| `ts_ms_source_vs_processing.json` | commit and processing timestamps set deliberately far apart |
| `drift_column_added.json` | a `discount` column appears |
| `drift_column_dropped.json` | `updated_at` disappears |
| `drift_column_renamed.json` | `status` becomes `order_status` |
| `drift_type_changed.json` | `status` becomes `text` |
| `drift_column_widened.json` | `status` becomes `varchar(64)` |
| `drift_numeric_rescaled.json` | `amount` becomes `numeric(14,4)` |
| `connect_types_only.json` | no propagated native types |
| `connect_types_only_widened.json` | same, widened — proves the widening is undetectable |

`ts_ms_source_vs_processing.json` exists because the negative assertion
"`ts_ms` is not the top-level processing time" is vacuous when the two values
land in the same millisecond, which real envelopes often do. Its two
timestamps are years apart so the assertion always means something.

The last two files prove the documented limitation rather than only
describing it: `test_without_propagation_a_widening_is_invisible` passes
*because* no drift is detected between them.

Malformed envelopes are parametrised inline in the test module rather than
committed here — they are one-line shapes (a null payload, a string where a
dict belongs) and a file each would obscure more than it documents.
