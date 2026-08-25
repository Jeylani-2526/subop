"""
In-memory persistence layer for ETL pipeline Lineage metadata.

Per etl_engine_contracts_v1.md Section 6, Lineage is recorded as part
of the same write step as the run itself, not an afterthought pass.
This module records one structured entry per non-direct type-mapping
condition (contracts Section 7.2: inexact / ambiguous / conditional /
fallback), keyed by run_id so a run's full lineage trail can be
retrieved as a whole — replacing the single summary sentence that used
to be appended to the run's logs array as unstructured text.

Same in-memory, interface-first pattern as run_store.py /
pipeline_store.py, ahead of M10's dedicated Lineage module.

Where entries come from today: the only source of lineage-worthy
conditions right now is the source read (_read_source() in
executor.py, via AbstractionLayer.execute_query(capture_lineage=True))
— this happens before any transformation step runs. Every entry
recorded today therefore carries step_id=SOURCE_READ_STEP_ID rather
than one of the pipeline's own transformation step_ids, since none of
Week 16's transformation types (rename_columns, type_cast,
drop_null_rows, drop_columns) produce lineage-worthy conditions of
their own. If a transformation type does so in the future, it can
pass its own real step_id through record_lineage_entry() — the schema
below doesn't need to change.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

# Sentinel step_id for lineage entries that originate from the source
# read rather than from a named transformation step (see module
# docstring). Not one of the pipeline's own transformations[].step_id
# values — deliberately distinct so it can never collide with one.
SOURCE_READ_STEP_ID = "source_read"

_lineage_entries: Dict[str, Dict[str, Any]] = {}


def _current_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def record_lineage_entry(
    *,
    run_id: str,
    step_id: str,
    column: str,
    condition: str,
    canonical_type: Optional[str] = None,
    source_type: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Persist one Lineage entry — one non-direct type-mapping condition
    on one column, tied to the run and step it occurred in.

    canonical_type / source_type are carried through from the
    Abstraction Layer's lineage_records (contracts Section 7.2) when
    available; optional here so a future transformation-originated
    entry isn't forced to supply type metadata that doesn't apply to
    it.
    """
    entry_id = str(uuid4())
    entry = {
        "entry_id": entry_id,
        "run_id": run_id,
        "step_id": step_id,
        "column": column,
        "condition": condition,
        "canonical_type": canonical_type,
        "source_type": source_type,
        "recorded_at": _current_timestamp(),
    }

    _lineage_entries[entry_id] = entry

    return deepcopy(entry)


def get_lineage_for_run(run_id: str) -> List[Dict[str, Any]]:
    """
    Return every Lineage entry recorded for a run, oldest first.
    """
    return [deepcopy(e) for e in _lineage_entries.values() if e["run_id"] == run_id]


def clear_lineage() -> None:
    """Remove all stored lineage entries (test support)."""
    _lineage_entries.clear()
