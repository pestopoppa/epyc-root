"""Unit tests for src/test_time/deepconf.py (P21.A, intake-603).

Pure scoring/filtering/voting logic — no inference. Traces and their per-token
top-k probabilities are canned. Verifies the confidence polarity (peaked > flat),
the sliding window, bottom-pct weakest-link aggregation, rank-based top-η% filtering,
confidence-weighted voting, the llama.cpp completion_probabilities adapter, and the
default-OFF feature flag.
"""

from __future__ import annotations

import math

import pytest

from src.features import Features, get_features
from src.test_time.deepconf import (
    DeepConfConfig,
    DeepConfResult,
    Trace,
    group_confidences,
    normalize_answer,
    run_offline,
    score_trace,
    select_top,
    token_confidence,
    trace_confidence,
    trace_from_completion_probabilities,
    weighted_vote,
)


# ── token confidence ───────────────────────────────────────────────────────
class TestTokenConfidence:
    def test_empty_is_zero(self):
        assert token_confidence([]) == 0.0

    def test_peaked_more_confident_than_flat(self):
        peaked = token_confidence([0.97, 0.02, 0.005, 0.005])
        flat = token_confidence([0.25, 0.25, 0.25, 0.25])
        assert peaked > flat  # higher = more confident

    def test_flat_equals_neg_log_uniform(self):
        # -mean(log p) for four equal 0.25 probs == -log(0.25)
        assert token_confidence([0.25, 0.25, 0.25, 0.25]) == pytest.approx(-math.log(0.25))

    def test_zero_prob_floored_not_inf(self):
        v = token_confidence([1.0, 0.0])
        assert math.isfinite(v)

    def test_top_k_truncates(self):
        # Only the first 2 candidates are considered.
        assert token_confidence([0.5, 0.5, 0.0, 0.0], top_k=2) == pytest.approx(
            -math.log(0.5)
        )


# ── group confidence (sliding window) ───────────────────────────────────────
class TestGroupConfidences:
    def test_empty(self):
        assert group_confidences([], 4) == []

    def test_short_trace_single_group(self):
        assert group_confidences([1.0, 2.0, 3.0], window=8) == [pytest.approx(2.0)]

    def test_sliding_window_means(self):
        # window=2 over [1,2,3,4] -> means of (1,2),(2,3),(3,4)
        got = group_confidences([1.0, 2.0, 3.0, 4.0], window=2)
        assert got == [pytest.approx(1.5), pytest.approx(2.5), pytest.approx(3.5)]


# ── trace confidence aggregation ─────────────────────────────────────────────
class TestTraceConfidence:
    def test_bottom_pct_is_weakest_link(self):
        # 10 groups 1..10; bottom 10% -> just the min (1.0)
        confs = [float(i) for i in range(1, 11)]
        score = trace_confidence(confs, window=1, metric="bottom_pct", bottom_fraction=0.10)
        assert score == pytest.approx(1.0)

    def test_mean_metric(self):
        confs = [1.0, 2.0, 3.0]
        assert trace_confidence(confs, window=1, metric="mean") == pytest.approx(2.0)

    def test_tail_metric_uses_last_group(self):
        confs = [1.0, 2.0, 3.0, 4.0]
        assert trace_confidence(confs, window=1, metric="tail") == pytest.approx(4.0)

    def test_bottom_pct_below_mean_when_one_bad_group(self):
        confs = [9.0, 9.0, 9.0, 1.0]  # one weak link
        bottom = trace_confidence(confs, window=1, metric="bottom_pct", bottom_fraction=0.25)
        mean = trace_confidence(confs, window=1, metric="mean")
        assert bottom < mean  # weakest-link penalises the trace


# ── select top-η% (rank based) ───────────────────────────────────────────────
class TestSelectTop:
    def test_empty(self):
        assert select_top([], 10.0) == []

    def test_keeps_at_least_one(self):
        assert select_top([0.1, 0.2, 0.3], keep_percent=1.0) == [2]

    def test_keeps_top_half(self):
        # 4 scores, keep 50% -> top 2 by score
        assert select_top([0.1, 0.9, 0.5, 0.7], keep_percent=50.0) == [1, 3]

    def test_returns_sorted_indices(self):
        out = select_top([0.9, 0.1, 0.8], keep_percent=100.0)
        assert out == [0, 1, 2]


# ── weighted voting ──────────────────────────────────────────────────────────
class TestWeightedVote:
    def test_empty(self):
        assert weighted_vote([], []) == (None, {})

    def test_confidence_weight_overrides_count(self):
        # "A" appears twice (low weight) but "B" once with high weight -> B wins
        winner, votes = weighted_vote(["A", "A", "B"], [0.4, 0.4, 1.0])
        assert winner == "B"
        assert votes["A"] == pytest.approx(0.8)
        assert votes["B"] == pytest.approx(1.0)

    def test_majority_when_equal_weights(self):
        winner, _ = weighted_vote(["A", "B", "A"], [1.0, 1.0, 1.0])
        assert winner == "A"


# ── answer extraction ────────────────────────────────────────────────────────
class TestNormalizeAnswer:
    def test_empty(self):
        assert normalize_answer("") == ""

    def test_boxed_preferred(self):
        assert normalize_answer(r"work... \boxed{42} done") == "42"

    def test_last_number(self):
        assert normalize_answer("step 1 then 2 so the answer is 7") == "7"

    def test_last_line_fallback(self):
        assert normalize_answer("reasoning\nFinal Answer: Yes") == "final answer: yes"


# ── end-to-end offline pass ──────────────────────────────────────────────────
class TestRunOffline:
    def _peaked(self, n: int) -> list[list[float]]:
        return [[0.98, 0.01, 0.01]] * n

    def _flat(self, n: int) -> list[list[float]]:
        return [[0.34, 0.33, 0.33]] * n

    def test_empty_traces(self):
        res = run_offline([])
        assert isinstance(res, DeepConfResult)
        assert res.answer is None and res.votes == {}

    def test_confident_correct_trace_beats_unconfident_majority(self):
        # Two low-confidence traces say "wrong"; one high-confidence says "right".
        traces = [
            Trace(text="answer is wrong", token_top_probs=self._flat(20)),
            Trace(text="answer is wrong", token_top_probs=self._flat(20)),
            Trace(text="answer is right", token_top_probs=self._peaked(20)),
        ]
        # keep top 40% -> 1 trace (the confident one). normalize_answer has no
        # number/boxed span to pull, so it falls back to the whole last line.
        res = run_offline(traces, DeepConfConfig(keep_percent=40.0, window=4))
        assert res.kept_indices == [2]
        assert res.answer == "answer is right"

    def test_keep_all_then_weighted_vote(self):
        traces = [
            Trace(text="cat", token_top_probs=self._flat(10)),
            Trace(text="dog", token_top_probs=self._peaked(10)),
        ]
        res = run_offline(traces, DeepConfConfig(keep_percent=100.0, window=4))
        assert set(res.kept_indices) == {0, 1}
        # dog's trace is more confident -> higher weight -> wins
        assert res.answer == "dog"

    def test_custom_answer_extractor(self):
        traces = [Trace(text="ignored", token_top_probs=self._peaked(5))]
        res = run_offline(traces, DeepConfConfig(keep_percent=100.0, window=4),
                          answer_extractor=lambda _t: "FIXED")
        assert res.answer == "FIXED"

    def test_trace_scores_parallel_to_input(self):
        traces = [
            Trace(text="a", token_top_probs=self._flat(6)),
            Trace(text="b", token_top_probs=self._peaked(6)),
        ]
        res = run_offline(traces, DeepConfConfig(window=3))
        assert len(res.trace_scores) == 2
        assert res.trace_scores[1] > res.trace_scores[0]  # peaked scores higher


# ── config validation ────────────────────────────────────────────────────────
class TestConfig:
    def test_bad_metric(self):
        with pytest.raises(ValueError):
            DeepConfConfig(group_metric="nope")

    def test_bad_keep_percent(self):
        with pytest.raises(ValueError):
            DeepConfConfig(keep_percent=0.0)
        with pytest.raises(ValueError):
            DeepConfConfig(keep_percent=150.0)


# ── completion_probabilities adapter ─────────────────────────────────────────
class TestCompletionProbabilitiesAdapter:
    def test_parses_llama_cpp_shape(self):
        comp = [
            {"content": "4", "probs": [{"tok_str": "4", "prob": 0.9}, {"tok_str": "5", "prob": 0.1}]},
            {"content": "2", "probs": [{"tok_str": "2", "prob": 0.8}, {"tok_str": "3", "prob": 0.2}]},
        ]
        tr = trace_from_completion_probabilities("42", comp)
        assert tr.text == "42"
        assert tr.token_top_probs == [[0.9, 0.1], [0.8, 0.2]]

    def test_empty_probabilities(self):
        tr = trace_from_completion_probabilities("x", [])
        assert tr.token_top_probs == []
        assert score_trace(tr, DeepConfConfig()) == 0.0


# ── feature flag wiring ──────────────────────────────────────────────────────
class TestFeatureFlag:
    def test_deepconf_default_off(self):
        assert Features().deepconf is False

    def test_deepconf_off_in_production_defaults(self):
        # DeepConf must NOT auto-enable in production until A2 sanity check passes.
        assert get_features(production=True).deepconf is False
