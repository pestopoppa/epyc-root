"""Clean-room, stdlib-only statistics for EPYC eval / calibration reports.

This module consolidates metric functions that had been copy-pasted (and had
begun to drift) across the orchestrator's analysis, graph-router, eval-tower,
and maintenance scripts. Everything here is pure ``math`` — **no numpy, no
sklearn, no pandas**, and (by rule) **no import from ``scripts/``**: this module
lives under ``src`` and is imported *by* scripts, never the other way around.

Consolidated prior copies (all now delegate here):

* ``wilson_interval`` replaces
  - ``scripts/analysis/reviewer_calibration_report.py::wilson_interval``
  - ``scripts/graph_router/extract_journal_soft_labels.py::_wilson_lower`` /
    ``_wilson_upper``
  (a third copy lives in the epyc-inference-research repo and is out of scope
  for this orchestrator-only consolidation).

* ``expected_calibration_error`` replaces
  - ``scripts/analysis/reviewer_calibration_report.py::ece``
  - ``orchestration/repl_memory/replay/engine.py::_expected_calibration_error``
  - ``scripts/maintenance/analyze_verifier_shadow.py::_ece``
  - ``scripts/graph_router/{train_verifier_head,mc_dropout_eval,
    train_frontdoor_verifier}.py::_ece``

* ``roc_auc`` replaces
  - ``scripts/analysis/reviewer_calibration_report.py::roc_auc``
  - ``scripts/maintenance/analyze_verifier_shadow.py::_roc_auc``
  - ``scripts/graph_router/{train_verifier_head,mc_dropout_eval,
    train_frontdoor_verifier}.py::_roc_auc``
  (``evaluate_offline_reward_verifier_model_families.py`` imports ``_roc_auc``
  from ``train_verifier_head`` and so inherits this consolidation transitively).

* ``compute_calibration_metrics`` replaces
  - ``scripts/autopilot/eval_tower.py::compute_calibration_metrics`` and its
    local rank/cohort helpers.

Deliberately **not** consolidated here:

* **McNemar** — the canonical exact paired-McNemar test already lives at
  ``scripts/autopilot/paired_stats.py::mcnemar_from_vectors``; it stays there.
* **Brier score** — each call site keeps its own one-line Brier; it was never
  the source of drift and is out of scope for this module.
* ``src/llm_primitives/stats.py::StatsMixin`` — that is an unrelated
  call-logging mixin; these are free functions and do not touch it.

External reference: ``roc_auc`` uses the tie-averaged Mann-Whitney U estimator,
which matches ``sklearn.metrics.roc_auc_score``. The intake-802 source
``llm_decode_bench.py`` was read for behavioral reference only — it is
UNLICENSED and no code was copied from it.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

# Two-sided 95% normal quantile. This is the value the intake-802 source and the
# paired-significance methodology note (research/deep-dives/
# 2026-07-11-paired-significance-eval-methodology.md) standardize on. The prior
# copies used the rounded 1.96; callers that must reproduce a historical number
# bit-for-bit pass ``z=1.96`` explicitly (the delegating wrappers do exactly
# that), so this sharper default only affects new call sites.
DEFAULT_WILSON_Z = 1.959964

# The six per-role EV-4 calibration metrics, in report order.
CALIBRATION_METRIC_KEYS = (
    "ece",
    "auroc",
    "top1_accuracy",
    "bottom1_accuracy",
    "spearman_rho",
    "mae",
)


def wilson_interval(
    correct: int,
    total: int,
    z: float = DEFAULT_WILSON_Z,
) -> tuple[float, float]:
    """Wilson score confidence interval for a binomial proportion.

    Args:
        correct: number of successes.
        total: number of trials.
        z: normal quantile (default two-sided 95%). Pass ``1.96`` to reproduce
            the rounded constant the pre-consolidation copies used.

    Returns:
        ``(lower, upper)`` bounds clamped to ``[0.0, 1.0]``. For
        ``total <= 0`` the maximally-uninformative ``(0.0, 1.0)`` is returned —
        this matches every prior copy's degenerate-input behavior (the
        reviewer-report interval and the soft-label ``_wilson_lower``/
        ``_wilson_upper`` both returned 0.0 / 1.0 on an empty denominator).
    """
    if total <= 0:
        return (0.0, 1.0)
    p = correct / total
    denom = 1.0 + z * z / total
    centre = p + z * z / (2.0 * total)
    margin = z * math.sqrt((p * (1.0 - p) + z * z / (4.0 * total)) / total)
    return (max(0.0, (centre - margin) / denom), min(1.0, (centre + margin) / denom))


def expected_calibration_error(
    probs: Sequence[float],
    labels: Sequence[float],
    n_bins: int = 10,
) -> float | None:
    """Expected Calibration Error over equal-width probability bins.

    ``ECE = sum_bins (bin_fraction * |mean_accuracy - mean_confidence|)``.

    Bins are the equal-width intervals ``[i/n_bins, (i+1)/n_bins)`` for
    ``i < n_bins - 1``; the final bin is closed on the right (``<=``) so a
    confidence of exactly ``1.0`` lands in it. This is the identical binning
    used by all prior copies (the reviewer report, the replay engine, and the
    numpy graph-router / shadow variants).

    Args:
        probs: predicted probabilities / confidences in ``[0, 1]``.
        labels: ground-truth outcomes (``0``/``1`` or float in ``[0, 1]``).
        n_bins: number of equal-width bins (default 10).

    Returns:
        The ECE as a float, or ``None`` when ``probs`` is empty (calibration
        undefined). Callers that need the historical "0.0 on empty" convention
        wrap this and coalesce ``None`` -> ``0.0``.
    """
    probs = [float(p) for p in probs]
    labels = [float(y) for y in labels]
    n = len(probs)
    if n == 0:
        return None
    if len(labels) != n:
        raise ValueError(f"probs/labels length mismatch: {n} != {len(labels)}")

    total = 0.0
    for i in range(n_bins):
        lo = i / n_bins
        hi = (i + 1) / n_bins
        if i < n_bins - 1:
            idx = [k for k in range(n) if lo <= probs[k] < hi]
        else:
            idx = [k for k in range(n) if lo <= probs[k] <= hi]
        m = len(idx)
        if m:
            bin_conf = sum(probs[k] for k in idx) / m
            bin_acc = sum(labels[k] for k in idx) / m
            total += (m / n) * abs(bin_acc - bin_conf)
    return total


def roc_auc(
    scores: Sequence[float],
    labels: Sequence[float],
) -> float | None:
    """Rank-based ROC-AUC (Mann-Whitney U) with tie averaging.

    The positive class is ``label >= 0.5``. Tied scores share the mean of the
    ranks they span, which makes this equal to ``sklearn.metrics.roc_auc_score``
    and to the reviewer-report ``roc_auc``. (The pre-consolidation numpy
    ``argsort(argsort(...))`` variants did **not** average ties; on the
    continuous score distributions those scripts feed this function the two
    agree exactly, and on genuine ties the tie-averaged value here is the
    order-independent, correct one.)

    Args:
        scores: predictor scores (higher = more likely positive).
        labels: ground-truth outcomes; positive iff ``>= 0.5``.

    Returns:
        The AUC as a float, or ``None`` when one class is absent (AUC
        undefined). Callers that need the historical ``float('nan')`` convention
        wrap this and coalesce ``None`` -> ``nan``.
    """
    scores = [float(s) for s in scores]
    labels = [float(y) for y in labels]
    n = len(scores)
    if len(labels) != n:
        raise ValueError(f"scores/labels length mismatch: {n} != {len(labels)}")

    pos = sum(1 for y in labels if y >= 0.5)
    neg = n - pos
    if pos == 0 or neg == 0:
        return None

    # Average ranks (1-based); tied scores share the mean rank of their block.
    order = sorted(range(n), key=lambda i: scores[i])
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and scores[order[j + 1]] == scores[order[i]]:
            j += 1
        avg_rank = (i + j) / 2.0 + 1.0  # 1-based mean rank for the tie block
        for k in range(i, j + 1):
            ranks[order[k]] = avg_rank
        i = j + 1

    rank_pos = sum(ranks[k] for k in range(n) if labels[k] >= 0.5)
    return (rank_pos - pos * (pos + 1) / 2.0) / (pos * neg)


def _average_ranks(values: Sequence[float]) -> list[float]:
    """1-based tie-averaged ranks (same convention as ``roc_auc``)."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def _pearson(xs: Sequence[float], ys: Sequence[float]) -> float | None:
    n = len(xs)
    if n < 2 or n != len(ys):
        return None
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    var_x = sum((x - mean_x) ** 2 for x in xs)
    var_y = sum((y - mean_y) ** 2 for y in ys)
    if var_x <= 0.0 or var_y <= 0.0:
        return None
    return cov / math.sqrt(var_x * var_y)


def _spearman_rho(xs: Sequence[float], ys: Sequence[float]) -> float | None:
    """Spearman rank correlation (tie-averaged).

    None when undefined: fewer than 2 paired points, a length mismatch, or a
    constant vector on either axis (rank variance is 0).
    """
    if len(xs) < 2 or len(xs) != len(ys):
        return None
    return _pearson(_average_ranks(xs), _average_ranks(ys))


def _cohort_accuracy(
    confidences: Sequence[float],
    labels: Sequence[float],
    *,
    pick_max: bool,
) -> float | None:
    """Accuracy of the max- (or min-) confidence cohort.

    Ties are averaged: when several items share the extreme confidence the
    metric is the mean label over that whole cohort, so with distinct
    confidences this reduces to exactly the single top-1 / bottom-1 item.
    """
    if not confidences:
        return None
    target = max(confidences) if pick_max else min(confidences)
    cohort = [lab for conf, lab in zip(confidences, labels) if conf == target]
    if not cohort:
        return None
    return sum(cohort) / len(cohort)


def compute_calibration_metrics(
    confidences: Sequence[float],
    labels: Sequence[float],
) -> dict[str, float | None]:
    """EV-4 calibration metrics from paired confidence/correctness vectors.

    Returns every key in ``CALIBRATION_METRIC_KEYS`` plus ``n``. Metrics return
    ``None`` where undefined: empty input, single-class / too few distinct
    confidences for AUROC, or a constant vector for Spearman.
    """
    conf = [float(c) for c in confidences]
    lab = [float(y) for y in labels]
    if len(conf) != len(lab):
        raise ValueError(
            f"confidences/labels length mismatch: {len(conf)} != {len(lab)}"
        )
    n = len(conf)
    ece = expected_calibration_error(conf, lab, n_bins=10) if n else None
    # AUROC is only meaningful with both classes present and enough distinct
    # confidences for the confidence signal to rank examples.
    auroc: float | None = None
    if n and len({round(c, 6) for c in conf}) > 2 and len({round(y) for y in lab}) > 1:
        auroc = roc_auc(conf, lab)
    mae = (sum(abs(c - y) for c, y in zip(conf, lab)) / n) if n else None
    return {
        "n": n,
        "ece": ece,
        "auroc": auroc,
        "top1_accuracy": _cohort_accuracy(conf, lab, pick_max=True),
        "bottom1_accuracy": _cohort_accuracy(conf, lab, pick_max=False),
        "spearman_rho": _spearman_rho(conf, lab),
        "mae": mae,
    }
