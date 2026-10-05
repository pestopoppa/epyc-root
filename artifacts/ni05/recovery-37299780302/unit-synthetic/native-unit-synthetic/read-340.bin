#!/usr/bin/env python3
"""Contract tests for eval_tower's paired-significance screening hook.

The screening hook (``eval_tower.screen_paired_arms``) is the additive A/B glue
that turns two arms' per-question correctness vectors into a statistically
grounded verdict: the exact paired McNemar sign-test over the discordant/flip
pairs plus a per-arm Wilson score interval. It must REUSE the landed clean-room
primitives verbatim — ``paired_stats.mcnemar_from_vectors`` and
``stat_tests.wilson_interval`` — and reimplement no statistic.

These tests feed synthetic paired-arm result sets (no inference, no server) and
assert the McNemar p and Wilson CIs are attached and equal to what the landed
primitives produce directly.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "autopilot"))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "benchmark"))
sys.path.insert(0, str(REPO_ROOT))

from eval_tower import screen_paired_arms  # type: ignore[import-not-found]
from paired_stats import (  # type: ignore[import-not-found]
    QuestionOutcome,
    mcnemar_from_vectors,
)
from src.llm_primitives.stat_tests import wilson_interval

MATCHED_PROFILE = {"dataset_sha256": "deadbeef", "test_profile": "ev11-math-rebaseline-v1"}


def _vector(outcomes: dict[str, bool]) -> dict[str, QuestionOutcome]:
    return {
        qid: QuestionOutcome(qid=qid, suite="math", correct=bool(c), trial_id=-1)
        for qid, c in outcomes.items()
    }


def _arm(label: str, outcomes: dict[str, bool], profile=MATCHED_PROFILE) -> dict:
    arm: dict = {"label": label, "outcomes": outcomes}
    if profile is not None:
        arm["profile"] = profile
    return arm


# ── the two synthetic paired-arm result sets used across the tests ───────────
# 12 shared questions. Arm A is correct on q1-q4; arm B is correct on q1-q12.
# So the discordant pairs are all one-directional: b (A right / B wrong) = 0 and
# c (A wrong / B right) = 8 — a clean, clearly-significant McNemar signal.
ARM_A = {f"q{i}": (i <= 4) for i in range(1, 13)}
ARM_B = {f"q{i}": True for i in range(1, 13)}


def test_screen_attaches_mcnemar_p_matching_landed_primitive() -> None:
    out = screen_paired_arms([_arm("A", ARM_A), _arm("B", ARM_B)])

    assert out["n_arms"] == 2
    assert len(out["pairs"]) == 1
    pair = out["pairs"][0]

    # Cross-check against the LANDED McNemar directly (same vectors, same labels).
    ref = mcnemar_from_vectors(_vector(ARM_A), _vector(ARM_B), "A", "B")
    assert pair["mcnemar_p_two_sided"] == ref.p_value_two_sided
    assert pair["a_correct_b_wrong"] == ref.a_correct_b_wrong == 0
    assert pair["a_wrong_b_correct"] == ref.a_wrong_b_correct == 8
    assert pair["same_correct"] == ref.same_correct == 4
    assert pair["delta_b_minus_a"] == ref.delta_b_minus_a

    # 8 one-directional discordant pairs => exact two-sided p = 2 * C(8,0)/2^8.
    assert pair["mcnemar_p_two_sided"] == pytest.approx(2.0 / 256.0)
    assert pair["significant"] is True


def test_screen_attaches_per_arm_wilson_cis_matching_landed_primitive() -> None:
    out = screen_paired_arms([_arm("A", ARM_A), _arm("B", ARM_B)])
    pair = out["pairs"][0]

    # Per-arm Wilson CI on the SHARED set (the McNemar denominator): A=4/12, B=12/12.
    exp_a = wilson_interval(4, 12)
    exp_b = wilson_interval(12, 12)
    assert pair["wilson_a"] == [round(exp_a[0], 6), round(exp_a[1], 6)]
    assert pair["wilson_b"] == [round(exp_b[0], 6), round(exp_b[1], 6)]

    # Per-arm summary Wilson CI (over each arm's own outcomes) is attached too.
    assert out["arms"]["A"]["wilson_lower"] == round(exp_a[0], 6)
    assert out["arms"]["A"]["wilson_upper"] == round(exp_a[1], 6)
    assert out["arms"]["A"]["correct"] == 4
    assert out["arms"]["B"]["correct"] == 12

    # Non-overlapping CIs here (A tops out well below B's floor) — the screen must
    # report that; combined with the significant McNemar p it is a grounded win.
    assert exp_a[1] < exp_b[0]
    assert pair["wilson_ci_overlap"] is False


def test_screen_noise_band_case_is_not_significant() -> None:
    # A balanced flip set: b == c, so McNemar cannot reject and the CIs overlap.
    arm_a = {f"q{i}": c for i, c in enumerate([1, 1, 1, 0, 0, 1], 1)}
    arm_b = {f"q{i}": c for i, c in enumerate([1, 0, 1, 1, 1, 1], 1)}
    out = screen_paired_arms([_arm("A", arm_a), _arm("B", arm_b)])
    pair = out["pairs"][0]

    assert pair["a_correct_b_wrong"] == 1
    assert pair["a_wrong_b_correct"] == 2
    assert pair["mcnemar_p_two_sided"] == 1.0
    assert pair["significant"] is False
    assert pair["wilson_ci_overlap"] is True


def test_screen_gates_on_matched_dataset_and_profile() -> None:
    # Different dataset_sha256 -> the provenance gate refuses to pair the arms.
    other = {"dataset_sha256": "cafef00d", "test_profile": "ev11-math-rebaseline-v1"}
    out = screen_paired_arms(
        [_arm("A", ARM_A), _arm("B", ARM_B, profile=other)]
    )
    assert out["pairs"] == []
    assert len(out["mismatched_pairs"]) == 1
    mism = out["mismatched_pairs"][0]
    assert {mism["arm_a"], mism["arm_b"]} == {"A", "B"}
    assert "dataset_sha256" in mism["reason"]


def test_screen_refuses_one_sided_provenance() -> None:
    out = screen_paired_arms([_arm("A", ARM_A), _arm("B", ARM_B, profile=None)])

    assert out["pairs"] == []
    assert len(out["mismatched_pairs"]) == 1
    mism = out["mismatched_pairs"][0]
    assert {mism["arm_a"], mism["arm_b"]} == {"A", "B"}
    assert "one-sided" in mism["reason"]


def test_screen_refuses_both_sided_missing_provenance() -> None:
    # PAIR-1: when BOTH arms lack a profile, McNemar must NOT run over unidentified
    # data — paired_stats' contract treats missing identity on either arm as a refusal.
    out = screen_paired_arms(
        [_arm("A", ARM_A, profile=None), _arm("B", ARM_B, profile=None)]
    )
    assert out["pairs"] == []
    assert len(out["mismatched_pairs"]) == 1
    mism = out["mismatched_pairs"][0]
    assert {mism["arm_a"], mism["arm_b"]} == {"A", "B"}
    assert mism["reason"] == "provenance_missing_both"


def test_screen_both_present_matching_still_screens() -> None:
    # Sanity: the both-None refusal must not disturb the happy path — two arms that
    # both carry the SAME matched profile still pair and produce a McNemar screen.
    out = screen_paired_arms([_arm("A", ARM_A), _arm("B", ARM_B)])
    assert out["mismatched_pairs"] == []
    assert len(out["pairs"]) == 1
    assert out["pairs"][0]["mcnemar_p_two_sided"] == pytest.approx(2.0 / 256.0)


def test_screen_single_arm_has_wilson_but_no_pairs() -> None:
    out = screen_paired_arms([_arm("A", ARM_A)])
    assert out["pairs"] == []
    assert out["mismatched_pairs"] == []
    assert out["arms"]["A"]["n"] == 12
    assert out["arms"]["A"]["correct"] == 4


def test_screen_accepts_questionresult_like_and_dict_outcomes() -> None:
    # The hook coerces bare bools, {"correct": ...} mappings, and objects with a
    # .correct attribute (QuestionResult) into the same paired vector.
    class _QRLike:
        def __init__(self, correct: bool) -> None:
            self.correct = correct
            self.suite = "math"

    arm_a = {"q1": True, "q2": {"correct": False}, "q3": _QRLike(True)}
    arm_b = {"q1": _QRLike(False), "q2": {"correct": True}, "q3": True}
    out = screen_paired_arms([_arm("A", arm_a), _arm("B", arm_b)])
    pair = out["pairs"][0]

    assert pair["shared_qids"] == 3
    assert out["arms"]["A"]["correct"] == 2  # q1, q3
    assert out["arms"]["B"]["correct"] == 2  # q2, q3
    # Cross-check p against the landed primitive on the coerced vectors.
    ref = mcnemar_from_vectors(
        _vector({"q1": True, "q2": False, "q3": True}),
        _vector({"q1": False, "q2": True, "q3": True}),
        "A",
        "B",
    )
    assert pair["mcnemar_p_two_sided"] == ref.p_value_two_sided


def test_screen_output_is_json_serializable() -> None:
    import json

    out = screen_paired_arms([_arm("A", ARM_A), _arm("B", ARM_B)])
    # The screen is attached verbatim to eval_math_rebaseline's returned dict, so
    # it must round-trip through JSON.
    assert json.loads(json.dumps(out)) == out


# ── promoted McNemar VERDICT surface + per-role threading ────────────────────
# The screen now attaches an explicit {verdict, method, p_value/z, n_discordant}
# block to every matched pair, and attach_role_paired_verdicts threads a
# role-oriented view into each per-role record so downstream consumers read a
# VERDICT rather than raw discordant counts.

from eval_tower import attach_role_paired_verdicts  # type: ignore[import-not-found]  # noqa: E402
from paired_stats import (  # type: ignore[import-not-found]  # noqa: E402
    MCNEMAR_EXACT_MAX_DISCORDANT,
    mcnemar_verdict,
)


def test_screen_pair_carries_verdict_block_matching_primitive() -> None:
    out = screen_paired_arms([_arm("A", ARM_A), _arm("B", ARM_B)])
    pair = out["pairs"][0]
    assert out["mcnemar_exact_max_discordant"] == MCNEMAR_EXACT_MAX_DISCORDANT

    verdict = pair["verdict"]
    # Cross-check against the landed primitive on the SAME discordant counts.
    ref = mcnemar_verdict(pair["a_correct_b_wrong"], pair["a_wrong_b_correct"])
    assert verdict == ref
    # 0 A-right/B-wrong, 8 A-wrong/B-right => clean, significant b_better verdict.
    assert verdict["verdict"] == "b_better"
    assert verdict["method"] == "mcnemar"
    assert verdict["approximation"] == "exact_binomial"
    assert verdict["n_discordant"] == 8
    assert verdict["z"] is None


def test_screen_noise_band_pair_verdict_is_indistinguishable() -> None:
    arm_a = {f"q{i}": c for i, c in enumerate([1, 1, 1, 0, 0, 1], 1)}
    arm_b = {f"q{i}": c for i, c in enumerate([1, 0, 1, 1, 1, 1], 1)}
    out = screen_paired_arms([_arm("A", arm_a), _arm("B", arm_b)])
    assert out["pairs"][0]["verdict"]["verdict"] == "indistinguishable"


def test_screen_threshold_override_forces_normal_branch() -> None:
    # With a large one-directional flip set, lowering the exact threshold routes
    # the verdict through the continuity-corrected normal approximation.
    arm_a = {f"q{i}": (i <= 4) for i in range(1, 41)}  # correct on q1-q4 only
    arm_b = {f"q{i}": True for i in range(1, 41)}  # correct on all -> 36 flips B-right
    out = screen_paired_arms(
        [_arm("A", arm_a), _arm("B", arm_b)], mcnemar_exact_max_discordant=8
    )
    verdict = out["pairs"][0]["verdict"]
    assert verdict["approximation"] == "normal_approx"
    assert verdict["n_discordant"] == 36
    assert verdict["z"] is not None and verdict["z"] > 0
    assert verdict["verdict"] == "b_better"


def test_attach_role_paired_verdicts_threads_normalized_view() -> None:
    out = screen_paired_arms(
        [_arm("armA-label", ARM_A), _arm("armB-label", ARM_B)]
    )
    # per_role records carry the arm label (as eval_math_rebaseline builds them).
    per_role = {
        "worker_general": {"role": "worker_general", "arm": "armA-label"},
        "worker_math": {"role": "worker_math", "arm": "armB-label"},
    }
    returned = attach_role_paired_verdicts(per_role, out)
    assert returned is per_role  # mutates in place

    gen = per_role["worker_general"]["paired_verdicts"]
    mat = per_role["worker_math"]["paired_verdicts"]
    assert len(gen) == 1 and len(mat) == 1

    # Arm B wins (b_better). From worker_general's (arm_a) perspective that is
    # "other_better"; from worker_math's (arm_b) perspective it is "this_better".
    assert gen[0]["verdict"] == "other_better"
    assert gen[0]["raw_verdict"] == "b_better"
    assert gen[0]["vs_role"] == "worker_math"
    assert gen[0]["vs_arm"] == "armB-label"
    assert gen[0]["significant"] is True
    assert gen[0]["method"] == "mcnemar"

    assert mat[0]["verdict"] == "this_better"
    assert mat[0]["vs_role"] == "worker_general"


def test_attach_role_paired_verdicts_empty_when_no_pairs() -> None:
    # Single arm -> no pairs -> every role gets an empty paired_verdicts list.
    out = screen_paired_arms([_arm("solo", ARM_A)])
    per_role = {"worker_general": {"role": "worker_general", "arm": "solo"}}
    attach_role_paired_verdicts(per_role, out)
    assert per_role["worker_general"]["paired_verdicts"] == []


def test_attach_role_paired_verdicts_indistinguishable_normalizes_both_sides() -> None:
    arm_a = {f"q{i}": c for i, c in enumerate([1, 1, 1, 0, 0, 1], 1)}
    arm_b = {f"q{i}": c for i, c in enumerate([1, 0, 1, 1, 1, 1], 1)}
    out = screen_paired_arms([_arm("a", arm_a), _arm("b", arm_b)])
    per_role = {
        "ra": {"role": "ra", "arm": "a"},
        "rb": {"role": "rb", "arm": "b"},
    }
    attach_role_paired_verdicts(per_role, out)
    assert per_role["ra"]["paired_verdicts"][0]["verdict"] == "indistinguishable"
    assert per_role["rb"]["paired_verdicts"][0]["verdict"] == "indistinguishable"


def test_screen_with_verdict_round_trips_through_json() -> None:
    import json

    out = screen_paired_arms([_arm("A", ARM_A), _arm("B", ARM_B)])
    assert json.loads(json.dumps(out)) == out
