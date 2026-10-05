"""Decision-bearing staged evidence across EvalTower T1/T2/T3 lanes.

T1 remains the inexpensive sequential screening lane.  A T1-confirmed
candidate may promote only after matched, same-instrument T2 and T3 evidence
shows non-inferiority.  Raw quality is never compared across tiers.

This module is deliberately pure: runtime orchestration, offline collectors,
ratifiers, and dashboard reconstruction can all render the same verdict from
the same sealed evidence.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import math
from typing import Any, Iterable, Mapping


MULTITIER_POLICY_VERSION = "staged-multitier-v1"
REQUIRED_VALIDATION_TIERS: tuple[int, ...] = (2, 3)
DEFAULT_MAX_ATTEMPTS_PER_TIER = 3
DEFAULT_MIN_OVERLAP_RATIO = 0.80
DEFAULT_ONE_SIDED_Z = 1.6448536269514722
DEFAULT_RELATIVE_NONINFERIORITY_MARGIN = 0.05
DEFAULT_MIN_FLIPS = 2


@dataclass(frozen=True)
class TierValidationVerdict:
    policy_version: str
    tier: int
    status: str
    reason: str
    attempts: int
    baseline_n: int
    paired_n: int
    overlap_ratio: float
    baseline_quality: float | None
    candidate_quality: float | None
    delta_quality: float | None
    standard_error_quality: float | None
    lower_bound_quality: float | None
    upper_bound_quality: float | None
    noninferiority_margin_quality: float | None
    improvement: bool
    instrument_match: bool

    @property
    def passed(self) -> bool:
        return self.status == "pass"

    @property
    def terminal_regression(self) -> bool:
        return self.status == "regression"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _outcome_map(rows: Any) -> dict[str, bool]:
    if not isinstance(rows, (list, tuple)):
        return {}
    outcomes: dict[str, bool] = {}
    for item in rows:
        if not isinstance(item, Mapping):
            continue
        qid = str(item.get("qid") or item.get("question_id") or "").strip()
        if qid:
            outcomes[qid] = bool(item.get("correct"))
    return outcomes


def _text(value: Any) -> str:
    if isinstance(value, (Mapping, list, tuple)):
        return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return str(value or "").strip()


def build_tier_baseline_evidence(result: Any, *, tier: int | None = None) -> dict[str, Any]:
    """Build the compact, sealed baseline vector consumed by the policy."""
    details = getattr(result, "details", {}) or {}
    outcomes = _outcome_map(
        getattr(result, "question_results", None) or details.get("question_results")
    )
    resolved_tier = int(tier if tier is not None else getattr(result, "tier", 0))
    return {
        "schema_version": "multitier-tier-baseline.v1",
        "policy_version": MULTITIER_POLICY_VERSION,
        "tier": resolved_tier,
        "core_id": _text(getattr(result, "core_id", None) or details.get("core_id")),
        "dataset_content_sha256": _text(
            getattr(result, "dataset_content_sha256", None) or details.get("dataset_content_sha256")
        ),
        "test_profile": _text(getattr(result, "test_profile", None) or details.get("test_profile")),
        "quality": float(getattr(result, "quality", 0.0) or 0.0),
        "reliability": float(getattr(result, "reliability", 0.0) or 0.0),
        "n_questions": len(outcomes),
        "outcomes": outcomes,
    }


def build_tier_candidate_evidence(result: Any) -> dict[str, Any]:
    """Build one compact candidate attempt for durable runtime state."""
    return {
        "schema_version": "multitier-tier-candidate.v1",
        **_candidate_payload(result),
    }


def _candidate_payload(result: Any) -> dict[str, Any]:
    if isinstance(result, Mapping) and isinstance(result.get("outcomes"), Mapping):
        return {
            "tier": int(result.get("tier") or 0),
            "core_id": _text(result.get("core_id")),
            "dataset_content_sha256": _text(result.get("dataset_content_sha256")),
            "test_profile": _text(result.get("test_profile")),
            "quality": float(result.get("quality") or 0.0),
            "reliability": float(result.get("reliability") or 0.0),
            "outcomes": {
                str(key): bool(value) for key, value in result.get("outcomes", {}).items()
            },
        }
    details = getattr(result, "details", {}) or {}
    outcomes = _outcome_map(
        getattr(result, "question_results", None) or details.get("question_results")
    )
    return {
        "tier": int(getattr(result, "tier", 0) or 0),
        "core_id": _text(getattr(result, "core_id", None) or details.get("core_id")),
        "dataset_content_sha256": _text(
            getattr(result, "dataset_content_sha256", None) or details.get("dataset_content_sha256")
        ),
        "test_profile": _text(getattr(result, "test_profile", None) or details.get("test_profile")),
        "quality": float(getattr(result, "quality", 0.0) or 0.0),
        "reliability": float(getattr(result, "reliability", 0.0) or 0.0),
        "outcomes": outcomes,
    }


def _instrument_match(candidate: Mapping[str, Any], baseline: Mapping[str, Any]) -> bool:
    if int(candidate.get("tier") or 0) != int(baseline.get("tier") or 0):
        return False
    for key in ("core_id", "dataset_content_sha256", "test_profile"):
        expected = _text(baseline.get(key))
        observed = _text(candidate.get(key))
        if expected and observed != expected:
            return False
    return True


def _empty_verdict(
    *,
    tier: int,
    status: str,
    reason: str,
    attempts: int,
    baseline_n: int = 0,
    instrument_match: bool = False,
) -> TierValidationVerdict:
    return TierValidationVerdict(
        policy_version=MULTITIER_POLICY_VERSION,
        tier=tier,
        status=status,
        reason=reason,
        attempts=attempts,
        baseline_n=baseline_n,
        paired_n=0,
        overlap_ratio=0.0,
        baseline_quality=None,
        candidate_quality=None,
        delta_quality=None,
        standard_error_quality=None,
        lower_bound_quality=None,
        upper_bound_quality=None,
        noninferiority_margin_quality=None,
        improvement=False,
        instrument_match=instrument_match,
    )


def evaluate_tier_validation(
    candidate_results: Iterable[Any],
    baseline: Mapping[str, Any] | None,
    *,
    tier: int,
    min_overlap_ratio: float = DEFAULT_MIN_OVERLAP_RATIO,
    one_sided_z: float = DEFAULT_ONE_SIDED_Z,
    relative_margin: float = DEFAULT_RELATIVE_NONINFERIORITY_MARGIN,
    min_flips: int = DEFAULT_MIN_FLIPS,
) -> TierValidationVerdict:
    """Render a paired same-tier non-inferiority verdict.

    Candidate repeats are paired independently against the fixed incumbent
    outcome for each shared qid.  The bound is on the paired correctness
    difference, expressed on EvalTower's 0..3 quality scale.  A conclusive
    positive lower bound is also surfaced as the higher-tier tie-break signal.
    """
    candidates = [_candidate_payload(result) for result in candidate_results]
    attempts = len(candidates)
    if not isinstance(baseline, Mapping):
        return _empty_verdict(
            tier=tier,
            status="baseline_missing",
            reason=f"T{tier} matched incumbent baseline is missing",
            attempts=attempts,
        )

    baseline_outcomes_raw = baseline.get("outcomes")
    baseline_outcomes = (
        {str(key): bool(value) for key, value in baseline_outcomes_raw.items()}
        if isinstance(baseline_outcomes_raw, Mapping)
        else {}
    )
    baseline_n = len(baseline_outcomes)
    if baseline_n <= 0:
        return _empty_verdict(
            tier=tier,
            status="baseline_invalid",
            reason=f"T{tier} incumbent baseline has no per-question outcomes",
            attempts=attempts,
        )
    if not candidates:
        return _empty_verdict(
            tier=tier,
            status="pending",
            reason=f"T{tier} candidate evidence has not been collected",
            attempts=0,
            baseline_n=baseline_n,
            instrument_match=True,
        )
    if any(not _instrument_match(candidate, baseline) for candidate in candidates):
        return _empty_verdict(
            tier=tier,
            status="instrument_mismatch",
            reason=f"T{tier} candidate and incumbent instrument identities differ",
            attempts=attempts,
            baseline_n=baseline_n,
        )

    differences: list[float] = []
    candidate_correct = 0
    baseline_correct = 0
    unique_shared: set[str] = set()
    for candidate in candidates:
        outcomes = candidate["outcomes"]
        shared = set(outcomes) & set(baseline_outcomes)
        unique_shared.update(shared)
        for qid in shared:
            candidate_value = bool(outcomes[qid])
            baseline_value = bool(baseline_outcomes[qid])
            candidate_correct += int(candidate_value)
            baseline_correct += int(baseline_value)
            differences.append(float(candidate_value) - float(baseline_value))

    overlap_ratio = len(unique_shared) / baseline_n
    paired_n = len(differences)
    if overlap_ratio < min_overlap_ratio or paired_n <= 0:
        return TierValidationVerdict(
            policy_version=MULTITIER_POLICY_VERSION,
            tier=tier,
            status="insufficient_overlap",
            reason=(
                f"T{tier} shared-qid coverage {overlap_ratio:.1%} is below "
                f"the required {min_overlap_ratio:.1%}"
            ),
            attempts=attempts,
            baseline_n=baseline_n,
            paired_n=paired_n,
            overlap_ratio=overlap_ratio,
            baseline_quality=None,
            candidate_quality=None,
            delta_quality=None,
            standard_error_quality=None,
            lower_bound_quality=None,
            upper_bound_quality=None,
            noninferiority_margin_quality=None,
            improvement=False,
            instrument_match=True,
        )

    mean_difference = sum(differences) / paired_n
    if paired_n > 1:
        variance = sum((value - mean_difference) ** 2 for value in differences) / (paired_n - 1)
        standard_error = math.sqrt(max(0.0, variance) / paired_n)
    else:
        standard_error = 0.0
    baseline_quality = 3.0 * baseline_correct / paired_n
    candidate_quality = 3.0 * candidate_correct / paired_n
    delta_quality = 3.0 * mean_difference
    standard_error_quality = 3.0 * standard_error
    lower = delta_quality - one_sided_z * standard_error_quality
    upper = delta_quality + one_sided_z * standard_error_quality
    resolution_margin = 3.0 * max(0, int(min_flips)) / max(1, len(unique_shared))
    margin = max(abs(baseline_quality) * max(0.0, relative_margin), resolution_margin)

    if lower >= -margin:
        status = "pass"
        reason = f"T{tier} non-inferiority passed: LCB {lower:+.4f} >= margin {-margin:+.4f}"
    elif upper < -margin:
        status = "regression"
        reason = f"T{tier} regression: UCB {upper:+.4f} < margin {-margin:+.4f}"
    else:
        status = "inconclusive"
        reason = (
            f"T{tier} interval [{lower:+.4f}, {upper:+.4f}] crosses "
            f"the non-inferiority margin {-margin:+.4f}"
        )

    return TierValidationVerdict(
        policy_version=MULTITIER_POLICY_VERSION,
        tier=tier,
        status=status,
        reason=reason,
        attempts=attempts,
        baseline_n=baseline_n,
        paired_n=paired_n,
        overlap_ratio=overlap_ratio,
        baseline_quality=baseline_quality,
        candidate_quality=candidate_quality,
        delta_quality=delta_quality,
        standard_error_quality=standard_error_quality,
        lower_bound_quality=lower,
        upper_bound_quality=upper,
        noninferiority_margin_quality=margin,
        improvement=lower > 0.0,
        instrument_match=True,
    )
