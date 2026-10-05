"""Tests for NIB2-42 safety_gate + diversity metrics + VS recovery probe.

12 tests covering:
  - distinct-2, self-BLEU, TTR, entropy math
  - semantic-embedding-agreement with mock embedder (and NaN without)
  - SafetyGate PASS / WARN / REJECT paths
  - warn_only guard flag suppresses REJECT
  - VS recovery >= 0.50 suppresses REJECT even under multi-signal drop
  - parse_vs_completions tolerates minor formatting drift
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.diversity_gate import EvalResult, SafetyGate, Verdict
from src.tools.diversity import metrics, verbalized_sampling


# ── diversity metrics ───────────────────────────────────────────────

def test_distinct2_counts_unique_bigrams():
    # "a b c" and "a b d" share the bigram (a, b). Total 4 bigrams, 3 unique.
    assert metrics.distinct_n(["a b c", "a b d"], n=2) == pytest.approx(3 / 4)


def test_distinct2_identical_completions_score_low():
    same = "the quick brown fox jumps over the lazy dog"
    low = metrics.distinct_n([same, same, same], n=2)
    diverse = metrics.distinct_n([
        "alpha beta gamma delta",
        "epsilon zeta eta theta",
        "iota kappa lambda mu",
    ], n=2)
    assert low < diverse


def test_self_bleu_identical_scores_high_diverse_scores_low():
    same = ["the quick brown fox jumps over the lazy dog"] * 3
    diverse = [
        "The quick brown fox jumps over the lazy dog",
        "Photosynthesis converts carbon dioxide into glucose",
        "Neural networks learn via gradient descent backpropagation",
    ]
    assert metrics.self_bleu(same) > metrics.self_bleu(diverse)


def test_ttr_and_entropy_track_variety():
    narrow = ["word"] * 20
    wide = [
        "alpha beta gamma",
        "delta epsilon zeta",
        "eta theta iota",
    ]
    assert metrics.type_token_ratio(wide) > metrics.type_token_ratio(narrow)
    assert metrics.entropy(wide) > metrics.entropy(narrow)


def test_semantic_embedding_agreement_with_mock_embedder():
    class MockEmbedder:
        def encode(self, texts):
            # Return fixed vectors: first two are identical, third orthogonal.
            return np.array([
                [1.0, 0.0, 0.0],
                [1.0, 0.0, 0.0],
                [0.0, 1.0, 0.0],
            ], dtype=np.float32)

    # Mean pair cosine of (1,2,3): sim(1,2)=1, sim(1,3)=0, sim(2,3)=0 → 1/3.
    val = metrics.semantic_embedding_agreement(["a", "b", "c"], embedder=MockEmbedder())
    assert val == pytest.approx(1 / 3)


def test_semantic_embedding_agreement_without_embedder_returns_nan():
    val = metrics.semantic_embedding_agreement(["a", "b"], embedder=None)
    assert math.isnan(val)


# ── SafetyGate verdicts ─────────────────────────────────────────────

def _baseline():
    return EvalResult(
        quality=1.20, speed=20.0, cost=0.5, reliability=0.90,
        diversity_entropy=5.0,
        diversity_distinct2=0.60,
        diversity_self_bleu=0.30,
        diversity_ttr=0.40,
        diversity_semantic_embedding_agreement=0.50,
    )


def test_pass_verdict_when_no_drop():
    gate = SafetyGate(baseline=_baseline(), warn_only=False)
    result = EvalResult(
        quality=1.30, speed=22.0, cost=0.5, reliability=0.91,
        diversity_entropy=5.1,
        diversity_distinct2=0.62,  # slight up
        diversity_self_bleu=0.28,
        diversity_ttr=0.41,
        diversity_semantic_embedding_agreement=0.52,
    )
    v = gate.evaluate(result)
    assert v.verdict == Verdict.PASS
    assert v.reasons == []


def test_tier1_warn_when_distinct2_drops_and_quality_flat():
    gate = SafetyGate(baseline=_baseline(), warn_only=False)
    result = EvalResult(
        quality=1.18,  # slight drop
        speed=20.0, cost=0.5, reliability=0.90,
        diversity_entropy=4.8,
        diversity_distinct2=0.40,  # >20% drop from 0.60
        diversity_self_bleu=0.35,
        diversity_ttr=0.35,
        diversity_semantic_embedding_agreement=0.49,  # small drop, <10%
    )
    v = gate.evaluate(result)
    assert v.verdict == Verdict.WARN
    assert "tier 1 warn" in v.reasons[0]


def test_tier2_reject_requires_all_four_signals():
    gate = SafetyGate(baseline=_baseline(), warn_only=False)
    result = EvalResult(
        quality=1.10,  # down
        speed=20.0, cost=0.5, reliability=0.90,
        diversity_entropy=4.0,
        diversity_distinct2=0.40,  # >20% drop
        diversity_self_bleu=0.40,
        diversity_ttr=0.30,
        diversity_semantic_embedding_agreement=0.40,  # >10% drop from 0.50
        vs_recovery_ratio=0.30,  # < 0.50, probe couldn't recover
    )
    v = gate.evaluate(result)
    assert v.verdict == Verdict.REJECT
    joined = " ".join(v.reasons)
    assert "distinct-2 drop" in joined
    assert "semantic" in joined
    assert "VS recovery" in joined


def test_vs_recovery_above_threshold_prevents_reject():
    """Even with distinct-2 + semantic drops + quality flat, a VS recovery
    above 0.50 downgrades REJECT to WARN (amended multi-signal gate)."""
    gate = SafetyGate(baseline=_baseline(), warn_only=False)
    result = EvalResult(
        quality=1.10, speed=20.0, cost=0.5, reliability=0.90,
        diversity_entropy=4.0,
        diversity_distinct2=0.40,
        diversity_self_bleu=0.40,
        diversity_ttr=0.30,
        diversity_semantic_embedding_agreement=0.40,
        vs_recovery_ratio=0.80,  # recovered most of the gap
    )
    v = gate.evaluate(result)
    assert v.verdict == Verdict.WARN  # Tier 1 still fires, Tier 2 doesn't
    assert v.deltas["diversity_distinct2_delta"] < 0


def test_warn_only_mode_converts_reject_to_warn():
    gate = SafetyGate(baseline=_baseline(), warn_only=True)
    result = EvalResult(
        quality=1.10, speed=20.0, cost=0.5, reliability=0.90,
        diversity_distinct2=0.40,
        diversity_semantic_embedding_agreement=0.40,
        vs_recovery_ratio=0.30,
    )
    v = gate.evaluate(result)
    assert v.verdict == Verdict.WARN
    assert v.warn_only_active is True


def test_nan_baseline_signals_fall_through_to_pass():
    """When the baseline has NaN diversity (not populated yet), the
    diversity checks cannot fire — SafetyGate must not REJECT on
    missing signal."""
    baseline = EvalResult(
        quality=1.0, speed=20.0, cost=0.5, reliability=0.9,
        # all diversity fields NaN by default
    )
    gate = SafetyGate(baseline=baseline, warn_only=False)
    result = EvalResult(
        quality=0.9, speed=20.0, cost=0.5, reliability=0.9,
        diversity_distinct2=0.01,
        diversity_semantic_embedding_agreement=0.01,
        vs_recovery_ratio=0.0,
    )
    v = gate.evaluate(result)
    assert v.verdict == Verdict.PASS


# ── Verbalized Sampling recovery probe ──────────────────────────────

def test_vs_recovery_clamped_to_unit_interval():
    base = ["same same same"] * 4   # distinct-2 low
    vs = ["alpha beta", "gamma delta", "epsilon zeta", "eta theta"]  # high
    r = verbalized_sampling.recovery_ratio(base, vs, ceiling_distinct2=1.0)
    assert 0.0 <= r <= 1.0


def test_parse_vs_completions_tolerant_of_whitespace():
    raw = """
Some preamble.

Response 1 (probability 0.30):
Answer one line.

Response 2 (probability 0.25):
Answer two,
with multiple lines.

Response 3 (probability 0.45):
Answer three.
""".strip()
    segments = verbalized_sampling.parse_vs_completions(raw)
    assert len(segments) == 3
    assert segments[0].startswith("Answer one")
    assert "multiple lines" in segments[1]
    assert segments[2].startswith("Answer three")
