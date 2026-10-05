"""EV-11 / stats-consolidation contract tests for eval_tower (Wave-2 B1).

Covers:
  (i)  math_verify hard-fail — a missing ``math-verify`` library must RAISE, never
       silently degrade to exact_match (the 0/1,819-question EV-11 no-op bug); plus
       the math adapter now emits ``scoring_method="math_verify"`` for both suites.
  (iv) ROC-AUC consolidation — eval_tower computes AUROC via the stdlib clean-room
       ``src/llm_primitives/stat_tests.roc_auc`` and the value is behavior-preserving
       (identical to sklearn, which the inline code used before).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "autopilot"))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "benchmark"))
sys.path.insert(0, str(REPO_ROOT))

from eval_tower import EvalTower, QuestionResult, _require_math_verify  # type: ignore[import-not-found]
from src.llm_primitives.stat_tests import (
    expected_calibration_error,
    roc_auc as stat_roc_auc,
)


# ── (i) math_verify hard-fail ────────────────────────────────────────────────


def test_require_math_verify_present_does_not_raise() -> None:
    # math-verify is installed in the eval venv; the guard must be a no-op.
    assert _require_math_verify() is None


def test_require_math_verify_missing_hard_fails(monkeypatch) -> None:
    # sys.modules[name] = None makes `import name` raise ImportError, simulating an
    # environment where math-verify is not installed.
    monkeypatch.setitem(sys.modules, "math_verify", None)
    with pytest.raises(RuntimeError) as exc:
        _require_math_verify()
    msg = str(exc.value).lower()
    # It must be a loud refusal, and it must NOT silently fall back.
    assert "math_verify" in msg or "math-verify" in msg
    assert "exact_match" in msg  # names the fallback it is refusing to take


def test_eval_tower_roc_auc_is_the_consolidated_stat_tests_impl() -> None:
    # The AUROC swap must reference the shared clean-room implementation, not a
    # local/sklearn copy.
    import eval_tower

    assert eval_tower.roc_auc is stat_roc_auc


# ── (i) adapter flip ─────────────────────────────────────────────────────────


def test_math_adapter_flips_both_suites_to_math_verify() -> None:
    from dataset_adapter_modules.math_adapter import MathAdapter

    adapter = MathAdapter()
    gsm = adapter._gsm8k_prompt(7, {"question": "Q?", "answer": "#### 42"})
    m500 = adapter._math500_prompt(
        1, {"problem": "P?", "answer": "\\frac{1}{2}", "level": 2, "subject": "algebra"}
    )

    assert gsm["scoring_method"] == "math_verify"
    assert m500["scoring_method"] == "math_verify"
    # GSM8K must request a \boxed{} answer so math_verify can parse it natively
    # (the EV-11 path does not read the old <answer></answer> tags).
    assert "\\boxed{}" in gsm["prompt"]
    assert "<answer>" not in gsm["prompt"]


# ── (iv) AUROC behavior-preservation ─────────────────────────────────────────


def _qr(qid: str, correct: bool, confidence: float) -> QuestionResult:
    return QuestionResult(
        question_id=qid,
        suite="math",
        prompt="p",
        expected="e",
        qid=qid,
        answer="a",
        correct=correct,
        error=None,
        tokens_generated=10,
        elapsed_s=1.0,
        confidence=confidence,
    )


def test_aggregate_auroc_matches_stat_tests_and_sklearn() -> None:
    tower = EvalTower(url="http://127.0.0.1:1", timeout=1)
    # >2 distinct confidences and both correctness classes so the AUROC guard fires.
    confidences = [0.10, 0.25, 0.40, 0.55, 0.70, 0.85, 0.90]
    correctness = [False, False, True, False, True, True, True]
    results = [_qr(f"q{i}", c, conf) for i, (c, conf) in enumerate(zip(correctness, confidences))]

    agg = tower._aggregate(results, tier=1)

    expected = stat_roc_auc(confidences, [float(c) for c in correctness])
    assert expected is not None
    assert agg.auroc == pytest.approx(expected, abs=1e-12)

    # Cross-check the behavior-preserving claim against sklearn directly (the impl
    # the inline code used before consolidation).
    sklearn_metrics = pytest.importorskip("sklearn.metrics")
    sk = sklearn_metrics.roc_auc_score([float(c) for c in correctness], confidences)
    assert agg.auroc == pytest.approx(sk, abs=1e-9)


def test_aggregate_auroc_guard_degenerate_confidence_stays_zero() -> None:
    # Fewer than 3 distinct confidences -> guard skips AUROC, value stays 0.0.
    tower = EvalTower(url="http://127.0.0.1:1", timeout=1)
    results = [_qr("q0", True, 1.0), _qr("q1", False, 0.0), _qr("q2", True, 1.0)]
    agg = tower._aggregate(results, tier=1)
    assert agg.auroc == 0.0


def test_aggregate_ece_uses_ev11b_closed_top_bin_stat_tests() -> None:
    tower = EvalTower(url="http://127.0.0.1:1", timeout=1)
    results = [_qr("q0", False, 1.0)]

    agg = tower._aggregate(results, tier=1)

    expected = expected_calibration_error([1.0], [0.0], n_bins=10)
    assert expected == pytest.approx(1.0, abs=1e-12)
    assert agg.ece == pytest.approx(expected, abs=1e-12)
    assert agg.calibration_violations == 1
    assert agg.details["ece_binning"] == "closed_top_bin_stat_tests"
    assert agg.details["ece_instrument_era"] == "ev11b_closed_bin_2026_07_20"


# ── EV-11c placeholder-zero elimination (data-absent → None, not 0.0) ─────────


def _err_qr(qid: str) -> QuestionResult:
    return QuestionResult(
        question_id=qid,
        suite="math",
        prompt="p",
        expected="e",
        qid=qid,
        answer="",
        correct=False,
        error="boom",
        tokens_generated=0,
        elapsed_s=1.0,
    )


def test_aggregate_absent_confidence_emits_none_not_zero_placeholder() -> None:
    # EV-11c: an all-error batch has NO confidence data — ECE/AUROC must be None
    # (honest absence), NEVER a 0.0 placeholder that reads as a real measurement.
    tower = EvalTower(url="http://127.0.0.1:1", timeout=1)
    agg = tower._aggregate([_err_qr("q0"), _err_qr("q1")], tier=1)
    assert agg.ece is None
    assert agg.auroc is None
    assert agg.details["calibration_confidence_present"] is False
    assert agg.details["confidence_is_real"] is False


def test_aggregate_present_binary_proxy_keeps_computed_ece_but_flags_not_real() -> None:
    # Present data (even binary-proxy confidence) still computes ECE at the CORE
    # aggregate (pins preserved); provenance flags it not-real so decision-facing
    # per-role builders can gate. calibration_confidence_present is True here.
    tower = EvalTower(url="http://127.0.0.1:1", timeout=1)
    agg = tower._aggregate([_qr("q0", False, 1.0), _qr("q1", True, 0.0)], tier=1)
    assert agg.ece is not None
    assert agg.details["confidence_is_real"] is False
    assert agg.details["calibration_confidence_present"] is True
