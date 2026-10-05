"""Observe-only AW-10 contract for tasks at hypothesis disagreement boundaries."""

from __future__ import annotations

import re
from dataclasses import dataclass
from types import MappingProxyType


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
VOCABULARY_AXES = ("regimes", "surfaces", "outcomes", "contradictions")
OWNER_LOOPS = frozenset({"autokernel", "autopilot"})


@dataclass(frozen=True)
class HypothesisBoundaryContract:
    """Controller-supplied evidence boundary; the task LLM cannot author it."""

    boundary_id: str
    parent_hypothesis_ids: tuple[str, str]
    owner_loop: str
    common_vocabulary: dict[str, list[str]]
    source_receipt_ids: tuple[str, ...]
    empirical_demand_receipt_id: str
    excluded_alternatives: tuple[str, ...]
    abstraction_construction_cost: float
    abstraction_cost_unit: str
    abstraction_cost_receipt_id: str
    matched_control_id: str
    verifier_source_receipt_id: str
    representation_frame_sha256: str
    falsifier_feedback_ref: str

    def __post_init__(self) -> None:
        for name in (
            "boundary_id",
            "empirical_demand_receipt_id",
            "abstraction_cost_unit",
            "abstraction_cost_receipt_id",
            "matched_control_id",
            "verifier_source_receipt_id",
            "falsifier_feedback_ref",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name}: required non-empty string")
        if self.owner_loop not in OWNER_LOOPS:
            raise ValueError(f"owner_loop: expected one of {sorted(OWNER_LOOPS)}")
        if (
            not isinstance(self.parent_hypothesis_ids, tuple)
            or len(self.parent_hypothesis_ids) != 2
            or len(set(self.parent_hypothesis_ids)) != 2
            or any(
                not isinstance(item, str) or not item.strip() for item in self.parent_hypothesis_ids
            )
        ):
            raise ValueError("parent_hypothesis_ids: expected two distinct non-empty ids")
        if set(self.common_vocabulary) != set(VOCABULARY_AXES):
            raise ValueError(f"common_vocabulary: expected exactly {list(VOCABULARY_AXES)}")
        for axis, values in self.common_vocabulary.items():
            if (
                not isinstance(values, (list, tuple))
                or not values
                or any(not isinstance(value, str) or not value.strip() for value in values)
            ):
                raise ValueError(f"common_vocabulary.{axis}: expected non-empty string list")
        if not self.source_receipt_ids or any(
            not isinstance(value, str) or not value.strip() for value in self.source_receipt_ids
        ):
            raise ValueError("source_receipt_ids: expected at least one receipt")
        if (
            isinstance(self.abstraction_construction_cost, bool)
            or not isinstance(self.abstraction_construction_cost, (int, float))
            or self.abstraction_construction_cost < 0
        ):
            raise ValueError("abstraction_construction_cost: expected non-negative number")
        if not _SHA256_RE.match(self.representation_frame_sha256):
            raise ValueError("representation_frame_sha256: expected lowercase sha256")
        object.__setattr__(
            self,
            "common_vocabulary",
            MappingProxyType(
                {axis: tuple(self.common_vocabulary[axis]) for axis in VOCABULARY_AXES}
            ),
        )

    def to_dict(self) -> dict:
        return {
            "boundary_id": self.boundary_id,
            "parent_hypothesis_ids": list(self.parent_hypothesis_ids),
            "owner_loop": self.owner_loop,
            "common_vocabulary": {
                axis: list(self.common_vocabulary[axis]) for axis in VOCABULARY_AXES
            },
            "source_receipt_ids": list(self.source_receipt_ids),
            "empirical_demand_receipt_id": self.empirical_demand_receipt_id,
            "excluded_alternatives": list(self.excluded_alternatives),
            "abstraction_construction_cost": self.abstraction_construction_cost,
            "abstraction_cost_unit": self.abstraction_cost_unit,
            "abstraction_cost_receipt_id": self.abstraction_cost_receipt_id,
            "matched_control_id": self.matched_control_id,
            "verifier_source_receipt_id": self.verifier_source_receipt_id,
            "representation_frame_sha256": self.representation_frame_sha256,
            "falsifier_feedback_ref": self.falsifier_feedback_ref,
            "evaluation_tier": "dynamic_t1",
            "t0_eligible": False,
        }


def boundary_evidence(
    contract: HypothesisBoundaryContract,
    *,
    task_id: str,
    evidence_receipt_id: str,
    hypothesis_results: dict[str, str],
) -> dict:
    """Build the typed feedback record routed to the boundary's owning loop."""
    if set(hypothesis_results) != set(contract.parent_hypothesis_ids):
        raise ValueError("hypothesis_results must resolve both parent hypotheses exactly")
    if not evidence_receipt_id.strip():
        raise ValueError("evidence_receipt_id: required")
    return {
        "schema": "epyc.env_synth.hypothesis_boundary_evidence.v1",
        "authority": "observe_only",
        "owner_loop": contract.owner_loop,
        "feedback_ref": contract.falsifier_feedback_ref,
        "boundary_id": contract.boundary_id,
        "task_id": task_id,
        "parent_hypothesis_ids": list(contract.parent_hypothesis_ids),
        "representation_frame_sha256": contract.representation_frame_sha256,
        "evidence_receipt_id": evidence_receipt_id,
        "hypothesis_results": dict(hypothesis_results),
    }
