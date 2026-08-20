"""
Stub VERBİS compliance check (M5 placeholder).

Per etl_engine_contracts_v1.md Section 2 and etl_engine_api_spec_v1.md
Section 3.3, pipeline creation must fail 422 if processing_purpose /
data_subject_categories / transfer_recipients don't resolve to a
completed VERBİS registration in Security & Compliance (Module 10).

Module 10 doesn't exist yet anywhere in the repo (README.md only, both
main and develop, confirmed by the Week 15 repo audit) — this is a
stub that always passes, so T4 can be built and tested against the
contract shape now.

TODO (Module 10 owner): replace check_verbis_registration()'s body
with a real call once Security & Compliance exists. The signature is
deliberately fixed to match what a real call would need, so nothing
above this module (the API route) has to change when that happens.
"""

from __future__ import annotations

from typing import List


class ComplianceCheckFailed(Exception):
    """Raised when a processing activity has no completed VERBİS registration."""

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def check_verbis_registration(
    processing_purpose: str,
    data_subject_categories: List[str],
    transfer_recipients: List[str],
) -> None:
    """
    Verify that processing_purpose / data_subject_categories /
    transfer_recipients resolve to a completed VERBİS registration
    (Module 10). Raises ComplianceCheckFailed if not.

    STUB: always passes — logs nothing to the run/pipeline record,
    just returns. TODO(Module 10): call the real Security & Compliance
    service here once it exists.
    """
    return None
