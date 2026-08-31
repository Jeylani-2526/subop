"""
Stub Data Quality pre-write hook (M5 Week 16 placeholder).

Per etl_engine_contracts_v1.md Section 6, Data Quality runs
synchronously pre-write, ahead of every write to the target — not an
afterthought pass. The full Data Quality engine (rule definitions,
scoring, quarantine routing) isn't built until M10; this is a stub
that always passes, following the same interface-first pattern as
compliance_check.py: the signature is fixed to match what a real check
would need, so nothing above this module (executor.py) has to change
when the real engine lands.

TODO (M10 owner): replace run_data_quality_check()'s body with real
rule evaluation. Until then this always returns a passing result with
quality_score=None — an honest "not yet available" rather than a
fabricated number — and rows_quarantined=0.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class DataQualityResult:
    rows_quarantined: int
    quality_score: Optional[float]


def run_data_quality_check(
    rows: List[Dict[str, Any]],
    pipeline_name: str,
) -> DataQualityResult:
    """
    Run the pre-write Data Quality check against `rows` ahead of the
    target write (contracts Section 6).

    STUB: always passes — no rule evaluation, no quarantining, no
    scoring. Returns rows_quarantined=0 and quality_score=None so
    downstream consumers (T4's KPI endpoint, run records) reflect an
    honest "not yet available" state rather than a value that looks
    complete but isn't.

    TODO(M10): replace with real rule evaluation against `rows`.
    `pipeline_name` is accepted now (not yet used) so the signature
    doesn't need to change when rules become pipeline-specific.
    """
    return DataQualityResult(rows_quarantined=0, quality_score=None)
