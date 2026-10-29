"""Experimental observed-outcome scorer for task/role pairs.

This module does not load a model or change serving configuration. Callers must
provide a disjoint group split and an explicitly chosen quality floor. The
first 1031 columns retain the classifier order (1024 embedding, five task-type
indicators, context length, image flag); semantic role indicators are appended.
Historical suite-derived proxies are inputs only to historical experiments and
are not substituted for absent decision-time TaskIR fields.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import log, sqrt
from numbers import Number
from typing import Sequence

import numpy as np

FEATURE_DIM = 1031


@dataclass(frozen=True)
class CandidateScore:
    rate: float | None
    supported: bool
    reason: str = ""


class ActionOutcomeScorer:
    """Train on observed cells only; role support is fixed by held-out groups."""

    def __init__(self, roles: Sequence[str], quality_floor: float, *, alpha: float = 0.05):
        self.roles = tuple(roles)
        if not self.roles or len(set(self.roles)) != len(self.roles):
            raise ValueError("roles must be nonempty and unique")
        if not 0 <= quality_floor <= 1 or not 0 < alpha < 1:
            raise ValueError("invalid quality floor or confidence budget")
        self.quality_floor = float(quality_floor)
        self.alpha = float(alpha)
        self.model = None
        self.support: dict[str, bool] = {}
        self.calibration_lower_bounds: dict[str, float] = {}

    def _features(self, features: np.ndarray) -> np.ndarray:
        x = np.asarray(features, dtype=np.float64)
        if x.ndim != 2 or x.shape[1] != FEATURE_DIM or np.isinf(x).any():
            raise ValueError("expected finite-or-missing 1031-column feature rows")
        return x

    def _cells(self, x, outcomes, seen):
        y = np.asarray(outcomes, dtype=float)
        mask = np.asarray(seen)
        shape = (len(x), len(self.roles))
        if y.shape != shape or mask.shape != shape or mask.dtype != np.bool_:
            raise ValueError("outcomes and boolean observation mask must match rows and roles")
        if not np.isfinite(y[mask]).all() or ((y[mask] < 0) | (y[mask] > 1)).any():
            raise ValueError("observed correctness must be in [0, 1]")
        row, role = np.nonzero(mask)
        identity = np.eye(len(self.roles), dtype=float)[role]
        expanded = np.concatenate((x[row], identity), axis=1)
        weights = 1.0 / mask.sum(axis=1)[row]
        return row, role, expanded, y[row, role], weights

    def fit(
        self,
        train_x,
        train_outcomes,
        train_seen,
        train_groups,
        calibration_x,
        calibration_outcomes,
        calibration_seen,
        calibration_groups,
    ):
        """Fit fixed CPU recipe and establish conservative per-role evidence bounds.

        Group means prevent repeated questions in a group from inflating evidence.
        Hoeffding bounds use a Bonferroni allocation over roles; they describe
        calibration outcomes, not a conditional guarantee for each prediction.
        """
        from sklearn.ensemble import HistGradientBoostingRegressor

        tx, cx = self._features(train_x), self._features(calibration_x)
        tg, cg = (
            np.asarray(train_groups, dtype=object),
            np.asarray(calibration_groups, dtype=object),
        )
        if tg.shape != (len(tx),) or cg.shape != (len(cx),):
            raise ValueError("one group id per question is required")
        for group in [*tg.tolist(), *cg.tolist()]:
            if group is None or (isinstance(group, (str, bytes)) and not group.strip()):
                raise ValueError("group ids must be nonempty and finite")
            if isinstance(group, Number) and not np.isfinite(group):
                raise ValueError("group ids must be nonempty and finite")
            try:
                hash(group)
            except TypeError as exc:
                raise ValueError("group ids must be hashable") from exc
        if set(tg.tolist()) & set(cg.tolist()):
            raise ValueError("train and calibration groups must be disjoint")
        tr, ti, expanded, target, weights = self._cells(tx, train_outcomes, train_seen)
        cr, ci, _, values, _ = self._cells(cx, calibration_outcomes, calibration_seen)
        if not len(tr):
            raise ValueError("no observed training outcomes")
        model = HistGradientBoostingRegressor(
            loss="squared_error",
            max_iter=100,
            max_leaf_nodes=7,
            min_samples_leaf=20,
            l2_regularization=1,
            early_stopping=False,
            random_state=0,
        )
        model.fit(expanded, target, sample_weight=weights)
        support, bounds = {}, {}
        for i, role in enumerate(self.roles):
            train_count = len(set(tg[tr[ti == i]].tolist()))
            indices = np.flatnonzero(ci == i)
            group_values = {}
            for j in indices:
                group_values.setdefault(cg[cr[j]], []).append(values[j])
            means = np.array([np.mean(v) for v in group_values.values()])
            n = len(means)
            bound = (
                max(0.0, float(means.mean()) - sqrt(log(len(self.roles) / self.alpha) / (2 * n)))
                if n
                else 0.0
            )
            bounds[role] = bound
            support[role] = train_count >= 20 and n >= 10 and bound >= self.quality_floor
        self.model, self.support, self.calibration_lower_bounds = model, support, bounds
        return self

    def score_candidates(
        self, features, admissible_roles: Sequence[str]
    ) -> dict[str, CandidateScore]:
        roles = list(dict.fromkeys(admissible_roles))
        scores = {role: CandidateScore(None, False, "unknown_or_unsupported") for role in roles}
        if self.model is None:
            return {role: CandidateScore(None, False, "unfitted") for role in roles}
        try:
            x = self._features(np.asarray(features).reshape(1, -1))
            selected = [r for r in roles if r in self.support and self.support[r]]
            if not selected:
                return scores
            identity = np.eye(len(self.roles))[[self.roles.index(r) for r in selected]]
            expanded = np.concatenate((np.repeat(x, len(selected), axis=0), identity), axis=1)
            predictions = self.model.predict(expanded)
            for role, prediction in zip(selected, predictions):
                rate = float(prediction)
                scores[role] = (
                    CandidateScore(rate, True)
                    if np.isfinite(rate) and 0 <= rate <= 1
                    else CandidateScore(None, False, "invalid_rate")
                )
        except Exception:
            return {role: CandidateScore(None, False, "prediction_error") for role in roles}
        return scores
