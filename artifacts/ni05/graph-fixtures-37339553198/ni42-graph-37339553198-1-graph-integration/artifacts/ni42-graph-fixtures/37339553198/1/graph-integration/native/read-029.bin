"""Classifier/verifier fast-path pure helpers for MemRL routing.

Extracted from retriever.py + hybrid_router.py during the 2026-05-22 Tranche-6
refactor. Holds pure-function helpers that don't depend on TwoPhaseRetriever /
HybridRouter `self` state — confidence aggregation across neighbor Q-values,
action-prior probability lookup, and effective-threshold resolution under
calibration + risk control.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List

import numpy as np

if TYPE_CHECKING:
    from .retrieval_config import RetrievalConfig, RetrievalResult


def compute_robust_confidence(
    q_values: List[float],
    estimator: str = "median",
    trim_ratio: float = 0.0,
) -> float:
    """Compute robust confidence from neighbor Q-values.

    Supports two estimators:
      - "median": uses np.median over the input values
      - "trimmed_mean": symmetric-trim mean (requires ≥3 values to engage trim)

    Returns 0.0 for empty input. Always returns a float.
    """
    if not q_values:
        return 0.0
    if estimator == "trimmed_mean" and len(q_values) >= 3:
        values = sorted(float(v) for v in q_values)
        trim_n = int(len(values) * trim_ratio)
        if trim_n > 0 and len(values) > 2 * trim_n:
            values = values[trim_n:-trim_n]
        return float(sum(values) / len(values)) if values else 0.0
    # Default: median
    return float(np.median(np.array(q_values, dtype=np.float32)))


def apply_confidence_to_results(
    results: "List[RetrievalResult]",
    config: "RetrievalConfig",
) -> float:
    """Assign a shared robust confidence estimate across top neighbors.

    Mutates each result's `q_confidence` to the shared value. Returns the
    confidence so callers can also use it directly.
    """
    if not results:
        return 0.0
    top = results[: max(config.confidence_min_neighbors, 1)]
    conf = compute_robust_confidence(
        [r.q_value for r in top],
        estimator=config.confidence_estimator,
        trim_ratio=config.confidence_trim_ratio,
    )
    for r in results:
        r.q_confidence = conf
    return conf


def effective_confidence_threshold(config: "RetrievalConfig") -> float:
    """Return the active routing threshold after calibration / risk controls.

    When `risk_control_enabled` and a `calibrated_confidence_threshold` are set,
    the calibrated value wins. `conformal_margin` is always added on top
    (TwoPhaseRetriever's original semantic), and the result is clamped to [0, 1].
    """
    base = config.confidence_threshold
    if (
        config.risk_control_enabled
        and config.calibrated_confidence_threshold is not None
    ):
        base = float(config.calibrated_confidence_threshold)
    return max(0.0, min(1.0, base + float(config.conformal_margin)))


def action_prior_prob(action: str, priors: Dict[str, float]) -> float:
    """Look up the prior probability for `action` in `priors`.

    Defaults to 0.0 (no prior contribution) when the action isn't in the dict.
    Always returns a float.
    """
    if not priors:
        return 0.0
    val = priors.get(action)
    if val is None:
        return 0.0
    return float(val)
