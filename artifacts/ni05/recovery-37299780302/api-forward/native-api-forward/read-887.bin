"""Unit tests for the measured fan-out policy (src/typed_decisions/fanout_policy.py).

Every branch and both numeric boundaries (question_count 7/8,
stability_tolerance 0.12) are pinned, including the exactness-required
non-native fallback. The constants table is checked against the receipt
provenance strings so a policy number cannot drift from its receipt.
"""

from __future__ import annotations

from src.typed_decisions.fanout_policy import (
    BATCHED_MIN_QUESTIONS,
    MEASURED_CONSTANTS,
    STABILITY_TOLERANCE_FLOOR,
    FanoutMode,
    choose_fanout_mode,
    describe_policy,
)


def _choose(**overrides):
    args = {
        "question_count": 24,
        "exactness_required": False,
        "stability_tolerance": 0.5,
        "native_eligible": True,
    }
    args.update(overrides)
    return choose_fanout_mode(**args)


class TestModeValues:
    def test_modes_are_the_declared_string_values(self):
        assert FanoutMode.BATCHED.value == "batched"
        assert FanoutMode.NATIVE_PER_QUESTION.value == "native_per_question"
        assert FanoutMode.SEQUENTIAL_SINGLETON.value == "sequential_singleton"

    def test_modes_are_string_enum_members(self):
        assert isinstance(FanoutMode.BATCHED, str)
        assert FanoutMode("batched") is FanoutMode.BATCHED


class TestExactnessBranch:
    def test_exactness_with_native_eligibility_is_native_per_question(self):
        assert _choose(exactness_required=True, native_eligible=True) is (
            FanoutMode.NATIVE_PER_QUESTION
        )

    def test_exactness_wins_over_batched_conditions(self):
        mode = _choose(
            exactness_required=True,
            native_eligible=True,
            question_count=64,
            stability_tolerance=1.0,
        )
        assert mode is FanoutMode.NATIVE_PER_QUESTION

    def test_exactness_without_native_eligibility_falls_back_to_sequential(self):
        mode = _choose(exactness_required=True, native_eligible=False)
        assert mode is FanoutMode.SEQUENTIAL_SINGLETON

    def test_exactness_without_native_eligibility_never_batches(self):
        """The exactness+non-native case does not leak into the batched branch."""
        mode = _choose(
            exactness_required=True,
            native_eligible=False,
            question_count=64,
            stability_tolerance=1.0,
        )
        assert mode is FanoutMode.SEQUENTIAL_SINGLETON


class TestBatchedBranch:
    def test_batched_at_both_boundaries(self):
        mode = _choose(
            question_count=BATCHED_MIN_QUESTIONS,
            stability_tolerance=STABILITY_TOLERANCE_FLOOR,
        )
        assert mode is FanoutMode.BATCHED

    def test_one_below_the_question_floor_does_not_batch(self):
        mode = _choose(
            question_count=BATCHED_MIN_QUESTIONS - 1,
            stability_tolerance=1.0,
        )
        assert mode is FanoutMode.SEQUENTIAL_SINGLETON

    def test_one_below_the_tolerance_floor_does_not_batch(self):
        mode = _choose(
            question_count=24,
            stability_tolerance=STABILITY_TOLERANCE_FLOOR - 1e-9,
        )
        assert mode is FanoutMode.SEQUENTIAL_SINGLETON

    def test_batching_does_not_require_native_eligibility(self):
        mode = _choose(
            question_count=24,
            stability_tolerance=0.5,
            native_eligible=False,
        )
        assert mode is FanoutMode.BATCHED

    def test_small_catalogue_with_full_tolerance_is_sequential(self):
        mode = _choose(question_count=4, stability_tolerance=1.0)
        assert mode is FanoutMode.SEQUENTIAL_SINGLETON

    def test_high_tolerance_with_large_catalogue_is_batched(self):
        mode = _choose(question_count=100, stability_tolerance=0.12)
        assert mode is FanoutMode.BATCHED


class TestMeasuredConstants:
    def test_thresholds_match_the_table(self):
        by_name = {constant.name: constant for constant in MEASURED_CONSTANTS}
        assert by_name["batched_min_questions"].value == BATCHED_MIN_QUESTIONS
        assert by_name["stability_tolerance_floor"].value == STABILITY_TOLERANCE_FLOOR

    def test_speed_and_agreement_constants_are_the_measured_values(self):
        by_name = {constant.name: constant for constant in MEASURED_CONSTANTS}
        assert by_name["native_per_question_speedup"].value == 11.98
        assert by_name["native_per_question_agreement"].value == 0.9375
        assert by_name["batched_speedup"].value == 2.196
        assert by_name["batched_agreement"].value == 0.875

    def test_every_constant_names_its_receipt(self):
        for constant in MEASURED_CONSTANTS:
            assert constant.provenance, constant.name
            assert "2026-09-17" in constant.provenance
        by_name = {constant.name: constant for constant in MEASURED_CONSTANTS}
        assert "bench-cue-sweep-worker.json" in by_name["native_per_question_speedup"].provenance
        assert "fanout-provided-worker.json" in by_name["batched_speedup"].provenance
        assert "fanout-lfm.json" in by_name["batched_min_questions"].provenance

    def test_derived_floor_is_labelled_derived(self):
        by_name = {constant.name: constant for constant in MEASURED_CONSTANTS}
        provenance = by_name["batched_min_questions"].provenance
        assert "derived" in provenance
        assert "not a measured point" in provenance


class TestDescribePolicy:
    def test_describe_policy_names_every_mode_and_receipt(self):
        text = describe_policy()
        for mode in FanoutMode:
            assert mode.value in text
        assert "11.98" in text
        assert "2.2" in text
        assert "0.875" in text
        assert "bench-cue-sweep-worker.json" in text
        assert "fanout-provided-worker.json" in text

    def test_describe_policy_is_deterministic(self):
        assert describe_policy() == describe_policy()
