"""Unit tests for scripts/autopilot/diversity_metrics.py (EV-8 / NIB2-42).

Tests cover the four deterministic metrics (distinct_2, type_token_ratio,
self_bleu, entropy) plus the inference-gated semantic_embedding_agreement
path. The embedding path is exercised only with a mock embedder — no real
model or inference call is made.

Also covers:
  - EvalResult diversity fields present and defaulting to NaN
  - to_grep_lines() emits diversity keys when fields are populated,
    and silently omits them when NaN.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

# Add autopilot dir so diversity_metrics can resolve its own imports
_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / "scripts" / "autopilot"))

import diversity_metrics as dm  # noqa: E402
from scripts.autopilot.safety_gate import EvalResult  # noqa: E402


# ── fixtures ─────────────────────────────────────────────────────────────────

IDENTICAL = ["the quick brown fox"] * 4
DIVERSE = [
    "alpha beta gamma delta epsilon",
    "photosynthesis converts sunlight into glucose",
    "neural networks learn via gradient descent",
    "the roman empire spanned centuries of history",
]


# ── distinct_2 ────────────────────────────────────────────────────────────────

class TestDistinct2:
    def test_identical_texts_score_low(self):
        score = dm.distinct_2(IDENTICAL)
        assert score < 0.5

    def test_diverse_texts_score_high(self):
        score = dm.distinct_2(DIVERSE)
        assert score > 0.5

    def test_identical_lower_than_diverse(self):
        assert dm.distinct_2(IDENTICAL) < dm.distinct_2(DIVERSE)

    def test_known_value(self):
        # "a b c" + "a b d": bigrams = (a,b),(b,c),(a,b),(b,d) → 4 total, 3 unique
        assert dm.distinct_2(["a b c", "a b d"]) == pytest.approx(3 / 4)

    def test_single_token_texts_return_zero(self):
        # No bigrams can be formed from single-token strings
        assert dm.distinct_2(["word", "word", "word"]) == 0.0


# ── type_token_ratio ──────────────────────────────────────────────────────────

class TestTypeTokenRatio:
    def test_all_same_token_returns_low_ttr(self):
        score = dm.type_token_ratio(["word word word"] * 5)
        assert score == pytest.approx(1 / 15)  # 1 unique / 15 total

    def test_all_unique_tokens_returns_one(self):
        score = dm.type_token_ratio(["alpha", "beta", "gamma"])
        assert score == pytest.approx(1.0)

    def test_diverse_higher_than_identical(self):
        assert dm.type_token_ratio(DIVERSE) > dm.type_token_ratio(IDENTICAL)

    def test_empty_list_returns_zero(self):
        assert dm.type_token_ratio([]) == 0.0


# ── self_bleu ─────────────────────────────────────────────────────────────────

class TestSelfBleu:
    def test_identical_texts_score_high(self):
        score = dm.self_bleu(IDENTICAL)
        assert not math.isnan(score)
        assert score > 0.5

    def test_diverse_texts_score_lower_than_identical(self):
        identical_score = dm.self_bleu(IDENTICAL)
        diverse_score = dm.self_bleu(DIVERSE)
        assert identical_score > diverse_score

    def test_single_text_returns_nan(self):
        score = dm.self_bleu(["only one text"])
        assert math.isnan(score)

    def test_two_identical_texts_is_not_nan(self):
        score = dm.self_bleu(["the cat sat on the mat", "the cat sat on the mat"])
        assert not math.isnan(score)


# ── entropy ───────────────────────────────────────────────────────────────────

class TestEntropy:
    def test_single_repeated_token_has_zero_entropy(self):
        score = dm.entropy(["word word word"] * 5)
        assert score == pytest.approx(0.0)

    def test_diverse_texts_have_higher_entropy_than_identical(self):
        assert dm.entropy(DIVERSE) > dm.entropy(IDENTICAL)

    def test_empty_list_returns_zero(self):
        assert dm.entropy([]) == 0.0

    def test_entropy_is_nonnegative(self):
        assert dm.entropy(DIVERSE) >= 0.0
        assert dm.entropy(IDENTICAL) >= 0.0


# ── semantic_embedding_agreement ─────────────────────────────────────────────

class TestSemanticEmbeddingAgreement:
    def test_no_embedder_returns_nan(self):
        """Inference-gated: without an embedder the metric is unavailable."""
        val = dm.semantic_embedding_agreement(IDENTICAL, embed_fn=None)
        assert math.isnan(val)

    def test_mock_embedder_identical_vectors(self):
        """When all embeddings are identical, mean pairwise cosine = 1.0."""
        import numpy as np

        class ConstantEmbedder:
            def encode(self, texts):
                return np.tile(np.array([1.0, 0.0, 0.0], dtype=np.float32),
                               (len(texts), 1))

        val = dm.semantic_embedding_agreement(IDENTICAL, embed_fn=ConstantEmbedder())
        assert val == pytest.approx(1.0)

    def test_mock_embedder_orthogonal_pair(self):
        """Two orthogonal vectors → cosine similarity = 0."""
        import numpy as np

        class OrthogonalEmbedder:
            def encode(self, texts):
                return np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32)

        val = dm.semantic_embedding_agreement(["a", "b"], embed_fn=OrthogonalEmbedder())
        assert val == pytest.approx(0.0, abs=1e-6)

    def test_single_text_returns_nan(self):
        val = dm.semantic_embedding_agreement(["one"], embed_fn=None)
        assert math.isnan(val)


# ── compute_diversity ─────────────────────────────────────────────────────────

class TestComputeDiversity:
    def test_returns_all_five_keys(self):
        result = dm.compute_diversity(DIVERSE)
        expected_keys = {
            "diversity_entropy",
            "diversity_distinct2",
            "diversity_self_bleu",
            "diversity_ttr",
            "diversity_semantic_embedding_agreement",
        }
        assert set(result.keys()) == expected_keys

    def test_without_embedder_semantic_is_nan(self):
        result = dm.compute_diversity(DIVERSE)
        assert math.isnan(result["diversity_semantic_embedding_agreement"])

    def test_deterministic_metrics_are_finite(self):
        result = dm.compute_diversity(DIVERSE)
        for key in ("diversity_entropy", "diversity_distinct2", "diversity_ttr"):
            assert math.isfinite(result[key]), f"{key} should be finite"

    def test_identical_vs_diverse(self):
        r_identical = dm.compute_diversity(IDENTICAL)
        r_diverse = dm.compute_diversity(DIVERSE)
        # More diverse corpus should have higher distinct-2, TTR, entropy
        assert r_diverse["diversity_distinct2"] > r_identical["diversity_distinct2"]
        assert r_diverse["diversity_ttr"] > r_identical["diversity_ttr"]
        assert r_diverse["diversity_entropy"] > r_identical["diversity_entropy"]
        # self-BLEU: identical should score higher (lower diversity)
        assert r_identical["diversity_self_bleu"] > r_diverse["diversity_self_bleu"]


# ── EvalResult integration ────────────────────────────────────────────────────

class TestEvalResultDiversityFields:
    def _base(self, **overrides) -> EvalResult:
        defaults = dict(
            tier=1,
            quality=1.5,
            speed=20.0,
            cost=0.4,
            reliability=0.92,
        )
        defaults.update(overrides)
        return EvalResult(**defaults)

    def test_diversity_fields_default_to_nan(self):
        r = self._base()
        assert math.isnan(r.diversity_entropy)
        assert math.isnan(r.diversity_distinct2)
        assert math.isnan(r.diversity_self_bleu)
        assert math.isnan(r.diversity_ttr)
        assert math.isnan(r.diversity_semantic_embedding_agreement)

    def test_to_grep_lines_emits_null_for_nan_diversity(self):
        # D4 (audit FIELD-1): NaN diversity fields now emit the literal `null`
        # UNCONDITIONALLY (kills absence-vs-zero ambiguity) — never the string `nan`,
        # never a silently dropped line.
        r = self._base()
        output = r.to_grep_lines(trial_id=99, species="test")
        for key in (
            "diversity_entropy",
            "diversity_distinct2",
            "diversity_self_bleu",
            "diversity_ttr",
            "diversity_semantic_embedding_agreement",
        ):
            assert f"METRIC {key}: null" in output
        assert ": nan" not in output

    def test_to_grep_lines_emits_populated_diversity(self):
        r = self._base(
            diversity_entropy=3.14,
            diversity_distinct2=0.72,
            diversity_self_bleu=0.21,
            diversity_ttr=0.55,
            # leave semantic NaN (inference-gated)
        )
        output = r.to_grep_lines(trial_id=1, species="s1")
        assert "METRIC diversity_entropy: 3.1400" in output
        assert "METRIC diversity_distinct2: 0.7200" in output
        assert "METRIC diversity_self_bleu: 0.2100" in output
        assert "METRIC diversity_ttr: 0.5500" in output
        # Semantic still NaN → emitted as the explicit `null` sentinel (D4 always-emit).
        assert "METRIC diversity_semantic_embedding_agreement: null" in output

    def test_to_grep_lines_emits_all_five_when_fully_populated(self):
        r = self._base(
            diversity_entropy=4.0,
            diversity_distinct2=0.80,
            diversity_self_bleu=0.15,
            diversity_ttr=0.60,
            diversity_semantic_embedding_agreement=0.35,
        )
        output = r.to_grep_lines()
        for key in (
            "diversity_entropy",
            "diversity_distinct2",
            "diversity_self_bleu",
            "diversity_ttr",
            "diversity_semantic_embedding_agreement",
        ):
            assert f"METRIC {key}:" in output, f"Missing key: {key}"

    def test_existing_construction_sites_not_broken(self):
        """Keyword-only construction with just required fields still works."""
        r = EvalResult(tier=0, quality=0, speed=0, cost=0, reliability=0)
        assert math.isnan(r.diversity_distinct2)
        output = r.to_grep_lines()
        assert "METRIC quality: 0.0000" in output
