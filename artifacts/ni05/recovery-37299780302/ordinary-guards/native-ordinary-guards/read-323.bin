"""D6 / FIELD-1: journal eval_details field-family parity + completeness guard.

The documented EvalResult metric families (diversity_* / rubric_* / reviewer_* /
branching_density / instruction_token_* / avg_prompt_tokens / compaction_events) were
being silently dropped from the journal's eval_details payload — they only reached the
METRIC grep-lines. These tests pin them into the payload via the extracted
`autopilot._eval_details_from_result` journal-assembly helper, and add a completeness
guard so a NEW prefixed field added to EvalResult fails until it is wired.
"""

from __future__ import annotations

import json
import sys
from dataclasses import fields
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "autopilot"))

import autopilot  # type: ignore[import-not-found]  # noqa: E402
from experiment_journal import ExperimentJournal, JournalEntry  # noqa: E402
from safety_gate import EvalResult  # noqa: E402


FAMILY_PREFIXES = ("diversity_", "rubric_", "reviewer_")

_EXPECTED_FAMILY_VALUES = {
    # EV-8 diversity (5)
    "diversity_entropy": 0.11,
    "diversity_distinct2": 0.22,
    "diversity_self_bleu": 0.33,
    "diversity_ttr": 0.44,
    "diversity_semantic_embedding_agreement": 0.55,
    # EV-9 / MindDR rubric (4)
    "rubric_reasoning_trajectory": 0.6,
    "rubric_tool_calls": 0.7,
    "rubric_outline": 0.8,
    "rubric_content_stage": 0.9,
    # AP-4 reviewer axes (4)
    "reviewer_fa_rate": 0.01,
    "reviewer_fr_rate": 0.02,
    "reviewer_fa_fr_ratio": 0.5,
    "review_decision_latency_ms": 123.0,
    # branching + instruction/compaction
    "branching_density": 0.15,
    "instruction_token_ratio": 0.05,
    "avg_prompt_tokens": 1024.0,
    "instruction_token_count": 42,
    "compaction_events": 3,
}


def _fully_populated_result() -> EvalResult:
    return EvalResult(
        tier=1,
        quality=2.0,
        speed=10.0,
        cost=0.2,
        reliability=1.0,
        diversity_entropy=0.11,
        diversity_distinct2=0.22,
        diversity_self_bleu=0.33,
        diversity_ttr=0.44,
        diversity_semantic_embedding_agreement=0.55,
        rubric_reasoning_trajectory=0.6,
        rubric_tool_calls=0.7,
        rubric_outline=0.8,
        rubric_content_stage=0.9,
        reviewer_fa_rate=0.01,
        reviewer_fr_rate=0.02,
        reviewer_fa_fr_ratio=0.5,
        review_decision_latency_ms=123.0,
        branching_density=0.15,
        instruction_token_count=42,
        instruction_token_ratio=0.05,
        avg_prompt_tokens=1024.0,
        compaction_events=3,
    )


def test_every_family_lands_in_payload() -> None:
    payload = autopilot._eval_details_from_result(_fully_populated_result())
    for key, value in _EXPECTED_FAMILY_VALUES.items():
        assert key in payload, f"family field {key} missing from journal payload"
        assert payload[key] == value


def test_nan_defaults_are_null_gated_to_none() -> None:
    # The diversity_*/rubric_*/reviewer_* float families default to NaN
    # ("unavailable this trial"); the helper null-gates them to None.
    payload = autopilot._eval_details_from_result(
        EvalResult(tier=1, quality=2.0, speed=10.0, cost=0.2, reliability=1.0)
    )
    for name in (
        "diversity_entropy",
        "diversity_semantic_embedding_agreement",
        "rubric_outline",
        "reviewer_fa_rate",
        "review_decision_latency_ms",
    ):
        assert payload[name] is None, f"{name} should be null-gated to None"
    # int families default to a REAL 0 (not "unavailable").
    assert payload["compaction_events"] == 0
    assert payload["instruction_token_count"] == 0


def test_non_finite_float_is_null_gated() -> None:
    payload = autopilot._eval_details_from_result(
        EvalResult(
            tier=1,
            quality=2.0,
            speed=10.0,
            cost=0.2,
            reliability=1.0,
            branching_density=float("inf"),
        )
    )
    assert payload["branching_density"] is None


def test_completeness_guard_covers_all_prefixed_dataclass_fields() -> None:
    # A NEW diversity_/rubric_/reviewer_ field added to EvalResult must be wired into
    # _eval_details_from_result — this guard fails until it is, so the journal schema
    # can never silently drop a freshly-added family axis.
    payload = autopilot._eval_details_from_result(_fully_populated_result())
    wired = set(autopilot._EVAL_DETAILS_FLOAT_FIELDS) | set(autopilot._EVAL_DETAILS_INT_FIELDS)
    prefixed = [f.name for f in fields(EvalResult) if f.name.startswith(FAMILY_PREFIXES)]
    assert prefixed, "expected diversity_/rubric_/reviewer_ fields on EvalResult"
    for name in prefixed:
        assert name in payload, f"EvalResult.{name} not wired into journal eval_details"
        assert name in wired, f"EvalResult.{name} not in _EVAL_DETAILS_*_FIELDS"


def test_families_round_trip_through_strict_json_journal(tmp_path: Path) -> None:
    # End-to-end: the merged payload survives the journal serializer (strict-JSON
    # json_sanitize with allow_nan=False). NaN defaults are already None here.
    result = EvalResult(tier=1, quality=2.0, speed=10.0, cost=0.2, reliability=1.0)
    eval_details = {"per_suite_quality": {}}
    eval_details.update(autopilot._eval_details_from_result(result))

    journal = ExperimentJournal(journal_dir=tmp_path)
    journal.record(
        JournalEntry(
            trial_id=1,
            timestamp="2026-07-20T00:00:00Z",
            species="test",
            action_type="seed_batch",
            tier=1,
            quality=2.0,
            speed=10.0,
            cost=0.2,
            reliability=1.0,
            pareto_status="candidate",
            eval_details=eval_details,
        )
    )

    raw = json.loads((tmp_path / "autopilot_journal.jsonl").read_text().splitlines()[0])
    persisted = raw["eval_details"]
    for name in _EXPECTED_FAMILY_VALUES:
        assert name in persisted
    # NaN-defaulted float families serialized as JSON null.
    assert persisted["diversity_entropy"] is None
    assert persisted["reviewer_fa_rate"] is None
