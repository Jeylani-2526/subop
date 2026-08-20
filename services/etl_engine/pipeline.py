"""
Pipeline DSL parsing and validation.

Implements the wire schema fixed in etl_engine_api_spec_v1.md Section 2 —
field names, types, and required/optional status only. Per that spec's
Section 6, transformation `type`/`params` *execution* semantics are
explicitly out of scope here: this module fixes the wire shape
(step_id, type, params, ordered array) and nothing about what a given
`type` does at runtime. That's executor.py's concern, dispatched not
interpreted by this module.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class PipelineValidationError(ValueError):
    """
    Raised when a Pipeline DSL document fails schema validation
    (API spec Section 3.3: maps to a 400 response).

    Carries `errors`, the complete list of field-level problems found —
    not just the first one — so the API layer (M5W15T4) can return a
    single 400 response with the full problem list rather than making
    the caller fix and resubmit one field at a time.
    """

    def __init__(self, errors: List[str]):
        super().__init__("; ".join(errors))
        self.errors = errors


_VALID_CONNECTOR_TYPES = {"postgresql", "mysql", "mssql", "mongodb"}
_VALID_WRITE_MODES = {"upsert", "append"}


@dataclass(frozen=True)
class SourceSpec:
    connector_type: str
    connection_ref: str
    object: str
    query: Optional[str] = None


@dataclass(frozen=True)
class TargetSpec:
    connector_type: str
    connection_ref: str
    object: str
    write_mode: str


@dataclass(frozen=True)
class TransformationStep:
    step_id: str
    type: str
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PipelineDefinition:
    name: str
    source: SourceSpec
    transformations: List[TransformationStep]
    target: TargetSpec
    processing_purpose: str
    data_subject_categories: List[str]
    transfer_recipients: List[str]


def parse_pipeline(payload: Dict[str, Any]) -> PipelineDefinition:
    """
    Validate and parse a Pipeline DSL JSON document (API spec Section 2).

    Raises PipelineValidationError collecting *all* field errors found,
    rather than failing on the first one.
    """
    errors: List[str] = []

    if not isinstance(payload, dict):
        raise PipelineValidationError(["Request body must be a JSON object."])

    name = payload.get("name")
    if not isinstance(name, str) or not name.strip():
        errors.append("`name` is required and must be a non-empty string.")

    source = _parse_source(payload.get("source"), errors)
    transformations = _parse_transformations(payload.get("transformations"), errors)
    target = _parse_target(payload.get("target"), errors)

    processing_purpose = payload.get("processing_purpose")
    if not isinstance(processing_purpose, str) or not processing_purpose.strip():
        errors.append(
            "`processing_purpose` is required and must be a non-empty string."
        )

    data_subject_categories = payload.get("data_subject_categories")
    if not isinstance(data_subject_categories, list) or not all(
        isinstance(c, str) for c in data_subject_categories
    ):
        errors.append(
            "`data_subject_categories` is required and must be an array of strings."
        )

    transfer_recipients = payload.get("transfer_recipients")
    if not isinstance(transfer_recipients, list) or not all(
        isinstance(r, str) for r in transfer_recipients
    ):
        errors.append(
            "`transfer_recipients` is required and must be an array of strings (may be empty)."
        )

    if errors:
        raise PipelineValidationError(errors)

    return PipelineDefinition(
        name=name,
        source=source,
        transformations=transformations,
        target=target,
        processing_purpose=processing_purpose,
        data_subject_categories=data_subject_categories,
        transfer_recipients=transfer_recipients,
    )


def _parse_source(payload: Any, errors: List[str]) -> Optional[SourceSpec]:
    if not isinstance(payload, dict):
        errors.append("`source` is required and must be an object.")
        return None

    connector_type = payload.get("connector_type")
    if connector_type not in _VALID_CONNECTOR_TYPES:
        errors.append(
            f"`source.connector_type` must be one of {sorted(_VALID_CONNECTOR_TYPES)}."
        )

    connection_ref = payload.get("connection_ref")
    if not isinstance(connection_ref, str) or not connection_ref.strip():
        errors.append(
            "`source.connection_ref` is required and must be a non-empty string."
        )

    object_name = payload.get("object")
    if not isinstance(object_name, str) or not object_name.strip():
        errors.append("`source.object` is required and must be a non-empty string.")

    query = payload.get("query")
    if query is not None and not isinstance(query, str):
        errors.append("`source.query` must be a string or null.")

    if (
        connector_type not in _VALID_CONNECTOR_TYPES
        or not isinstance(connection_ref, str)
        or not connection_ref.strip()
        or not isinstance(object_name, str)
        or not object_name.strip()
    ):
        return None

    return SourceSpec(
        connector_type=connector_type,
        connection_ref=connection_ref,
        object=object_name,
        query=query,
    )


def _parse_target(payload: Any, errors: List[str]) -> Optional[TargetSpec]:
    if not isinstance(payload, dict):
        errors.append("`target` is required and must be an object.")
        return None

    connector_type = payload.get("connector_type")
    if connector_type not in _VALID_CONNECTOR_TYPES:
        errors.append(
            f"`target.connector_type` must be one of {sorted(_VALID_CONNECTOR_TYPES)}."
        )

    connection_ref = payload.get("connection_ref")
    if not isinstance(connection_ref, str) or not connection_ref.strip():
        errors.append(
            "`target.connection_ref` is required and must be a non-empty string."
        )

    object_name = payload.get("object")
    if not isinstance(object_name, str) or not object_name.strip():
        errors.append("`target.object` is required and must be a non-empty string.")

    write_mode = payload.get("write_mode")
    if write_mode not in _VALID_WRITE_MODES:
        errors.append(
            f"`target.write_mode` must be one of {sorted(_VALID_WRITE_MODES)}."
        )

    if (
        connector_type not in _VALID_CONNECTOR_TYPES
        or not isinstance(connection_ref, str)
        or not connection_ref.strip()
        or not isinstance(object_name, str)
        or not object_name.strip()
        or write_mode not in _VALID_WRITE_MODES
    ):
        return None

    return TargetSpec(
        connector_type=connector_type,
        connection_ref=connection_ref,
        object=object_name,
        write_mode=write_mode,
    )


def _parse_transformations(payload: Any, errors: List[str]) -> List[TransformationStep]:
    if payload is None:
        payload = []

    if not isinstance(payload, list):
        errors.append("`transformations` must be an array (may be empty).")
        return []

    steps: List[TransformationStep] = []
    seen_step_ids = set()

    for index, step_payload in enumerate(payload):
        if not isinstance(step_payload, dict):
            errors.append(f"`transformations[{index}]` must be an object.")
            continue

        step_id = step_payload.get("step_id")
        if not isinstance(step_id, str) or not step_id.strip():
            errors.append(
                f"`transformations[{index}].step_id` is required and must be a non-empty string."
            )
            continue

        if step_id in seen_step_ids:
            errors.append(
                f"`transformations[{index}].step_id` ('{step_id}') is not unique."
            )
            continue
        seen_step_ids.add(step_id)

        step_type = step_payload.get("type")
        if not isinstance(step_type, str) or not step_type.strip():
            errors.append(
                f"`transformations[{index}].type` is required and must be a non-empty string."
            )
            continue

        params = step_payload.get("params", {})
        if not isinstance(params, dict):
            errors.append(f"`transformations[{index}].params` must be an object.")
            continue

        steps.append(TransformationStep(step_id=step_id, type=step_type, params=params))

    return steps
