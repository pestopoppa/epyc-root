"""Anytime-valid sequential verdict primitives for AutoPilot candidates.

The module is intentionally pure. W4 wiring can fold journal rows into these
states without changing the safety gate in the same patch that introduces the
math.
"""

from __future__ import annotations

import logging
import math
import random
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from typing import Any

from .measurement_guards import is_quality_admissible


log = logging.getLogger(__name__)

STATE_ACCUMULATING = "accumulating"
STATE_CONFIRMED = "confirmed"
STATE_REFUTED = "refuted"

# SEQ-3a: validity floor for a per-trial e-process statistic ``z``.
#
# The wealth process is a nonnegative supermartingale (the property Ville's
# inequality — hence the anytime-valid type-I guarantee — rests on) only while every
# applied factor ``1 + lambda_t * z`` stays >= 0. With ``lambda_t`` capped at
# ``policy.lambda_cap``, that is threatened ONLY on the negative side: it requires
# ``z >= -1/lambda_cap``. This is EXACTLY the condition under which
# ``EProcessState.update`` raises ValueError. A journal-derived z below that floor
# (an old-schema / mis-scaled / corrupt value) would crash the rebuild.
#
# We deliberately impose NO upper bound: a large-positive z keeps the factor >= 0 and
# is legitimate strong evidence — it does not threaten the nonnegative-supermartingale
# validity guarantee, and the statistics that produce z are already bounded by
# construction (quality in [-1, 1]; rate in ~[-0.9, 1.1]). Rejecting large-positive
# values would instead break legitimate accumulation. The public candidate-view rebuild
# entry point SKIPS (not clamps) non-finite / below-floor values and counts them.
_SEQ_Z_RANGE_EPS = 1e-9


@dataclass(frozen=True)
class SequentialPolicy:
    """Default seq-v1 e-process policy from the Fable 5 01c spec."""

    version: str = "seq-v1"
    alpha: float = 0.05
    confirm_e: float = 20.0
    futility_e: float = 0.05
    budget: int = 8
    budget_min_e: float = 2.0
    first_lambda: float = 0.1
    lambda_cap: float = 0.5
    rate_noninferiority_margin: float = 0.05
    # SEQ-A: is a stop decision final?
    #
    # `state_name()` is a pure function of CURRENT state, so a candidate whose
    # wealth later climbs back above `futility_e`/`budget_min_e` reads
    # `accumulating` again — the function does not remember having refuted. The
    # persisted labels, however, are never recomputed, so they stay `refuted`.
    # The two disagree for exactly 3 candidates in `core_v1` (70902e4b665474e7
    # k=40, dd793a6ee43ce718 k=24, 85c3dcf25823c537 k=15), which are excluded
    # from promotion and positive strategy distillation by a condition they no
    # longer meet.
    #
    # Which side gives is SEQ-A1, an OPERATOR decision and human-amendment-only
    # per MEASUREMENT.md: it changes which candidates are promotable. This flag
    # exists so that choice is a one-line, reviewable switch rather than a
    # rewrite under time pressure. It DEFAULTS TO THE CURRENT SEMANTICS
    # (non-sticky) so declaring it changes nothing until an operator sets it.
    sticky_refuted: bool = False

    def __post_init__(self) -> None:
        """SEQ-B: fail loudly if the policy can produce a negative wealth factor.

        ``rate_noninferiority_z`` bottoms out at ``(-1 + margin) / 0.5``. The wealth
        factor ``1 + lambda_t * z`` stays nonnegative — the property the anytime-valid
        guarantee rests on — only while that floor is ``>= -1/lambda_cap``. Checked here
        so a future policy edit cannot silently break Ville; ``replace()`` re-runs it.
        """
        if self.lambda_cap > 0.0:
            rate_z_floor = (-1.0 + self.rate_noninferiority_margin) / 0.5
            if rate_z_floor < -1.0 / self.lambda_cap - _SEQ_Z_RANGE_EPS:
                raise ValueError(
                    "SequentialPolicy would admit a negative wealth factor on the rate "
                    f"axis: rate z floor {rate_z_floor} < -1/lambda_cap "
                    f"{-1.0 / self.lambda_cap} (lambda_cap must be <= "
                    f"{0.5 / (1.0 - self.rate_noninferiority_margin)} for margin "
                    f"{self.rate_noninferiority_margin})"
                )


DEFAULT_POLICY = SequentialPolicy()

# SEQ-B2: axis names used by every refutation-attribution consumer. One spelling,
# shared by the live write side (`safety_gate._sequential_verdict`) and the post-hoc
# reader (`scripts/analysis/readjudicate_sequential_candidates.py`), so a live record
# and a reconstructed one are comparable without a translation table.
AXIS_QUALITY = "quality"
AXIS_RATE = "rate"
# Rule tokens naming WHICH clause of the refutation condition was the binding bar.
REFUTATION_RULE_FUTILITY = "futility_e"
REFUTATION_RULE_BUDGET = "budget_min_e"


@dataclass(frozen=True)
class AxisRefutation:
    """SEQ-B2: one evidence axis measured against the policy's refutation bar.

    Canonical definition, shared by the live stop-time writer and the post-hoc
    re-adjudicator so the two can never drift.

    ``refuted`` reproduces ``EProcessState._meets_refutation`` exactly: an axis
    refutes when ``wealth <= futility_e``, or when ``k >= budget`` and
    ``wealth < budget_min_e``.

    ``threshold`` is the BINDING bar for this ``k``. Because ``futility_e``
    (0.05) sits far below ``budget_min_e`` (2.0), once ``k >= budget`` the budget
    clause dominates the futility clause — anything at or below ``futility_e`` is
    also below ``budget_min_e`` — so the binding bar is ``budget_min_e`` for
    ``k >= budget`` and ``futility_e`` before it. ``rule`` names which one.

    ``margin = wealth - threshold``. SIGN CONVENTION: **negative means refuted**
    (the axis is below its bar), positive means surviving headroom, and the
    magnitude is the wealth distance to the bar. The one boundary asymmetry is
    inherited from the policy, not invented here: the futility clause is
    inclusive (``<=``) so ``margin == 0.0`` refutes under
    ``rule == "futility_e"``, while the budget clause is strict (``<``) so
    ``margin == 0.0`` does NOT refute under ``rule == "budget_min_e"``. Read
    ``refuted`` for the decision; ``margin`` is the distance, not the predicate.

    An axis that was never measured (``wealth is None`` — e.g. the rate axis was
    skipped) yields ``refuted=False`` with ``margin=None``: an absent measurement
    is not evidence against, the same skip-don't-fabricate doctrine
    ``rebuild_candidate_view`` applies to out-of-domain z.
    """

    axis: str
    wealth: float | None
    k: int
    refuted: bool
    margin: float | None
    threshold: float
    rule: str

    def as_journal_dict(self) -> dict[str, Any]:
        """Journal-shaped mapping (rounded margin, JSON-safe)."""
        return {
            "axis": self.axis,
            "wealth": None if self.wealth is None else round(float(self.wealth), 6),
            "k": self.k,
            "refuted": self.refuted,
            "margin": None if self.margin is None else round(float(self.margin), 6),
            "threshold": self.threshold,
            "rule": self.rule,
        }


def axis_refutation(
    axis: str,
    wealth: float | None,
    k: int,
    policy: SequentialPolicy = DEFAULT_POLICY,
) -> AxisRefutation:
    """Measure ONE evidence axis against the policy's refutation bar (SEQ-B2)."""
    k = int(k)
    if k >= policy.budget:
        threshold = float(policy.budget_min_e)
        rule = REFUTATION_RULE_BUDGET
    else:
        threshold = float(policy.futility_e)
        rule = REFUTATION_RULE_FUTILITY
    if wealth is None:
        return AxisRefutation(axis, None, k, False, None, threshold, rule)
    w = float(wealth)
    refuted = w <= policy.futility_e or (k >= policy.budget and w < policy.budget_min_e)
    return AxisRefutation(axis, w, k, refuted, w - threshold, threshold, rule)


SEQ_REFUTATION_SCHEMA = "seq-refutation-v1"


def refutation_record(
    *,
    e_quality: float | None,
    e_rate: float | None,
    k: int,
    policy: SequentialPolicy = DEFAULT_POLICY,
    captured_at: str | None = None,
    source: str = "live",
) -> dict[str, Any]:
    """SEQ-B2: the stop-time refutation counterfactual, as a journal record.

    WHY THIS EXISTS AT STOP TIME. The joint rule stamps ``state="refuted"`` when
    EITHER axis refutes, and a refuted candidate STOPS accumulating trials. A
    future objective can rescore every trial that exists; it cannot recover trials
    never run. So *which* axis refuted, and the surviving margin on the OTHER axis
    at the moment of the stop, must be captured live or not at all — post hoc
    reconstruction can only work where the journal happens to still carry both
    wealths, and only under today's policy constants.

    ATTRIBUTION PRECEDENCE (deterministic, and the both-axes answer). Axes are
    tested QUALITY FIRST, then RATE, mirroring the ``if/elif`` chain in
    ``scripts/analysis/readjudicate_sequential_candidates.py`` so a live record and
    a reconstructed one name the same axis for the same evidence. When BOTH axes
    refute, ``refuting_axis`` is therefore ``"quality"`` — and ``both_axes_refuted``
    is True, so the case is distinguishable rather than collapsed. Every axis's own
    verdict and margin is in ``axes`` regardless, so no attribution choice loses
    information.

    ``refuting_axis`` is None exactly when the joint verdict is refuted but NEITHER
    axis meets the current-state bar — the residual bucket the re-adjudicator
    reports as UNEXPLAINED (reachable today only via ``policy.sticky_refuted``).

    Margins follow ``AxisRefutation``: negative = below the bar. ``source`` records
    whether the record was written live at stop time or reconstructed after the
    fact by a reader.
    """
    q = axis_refutation(AXIS_QUALITY, e_quality, k, policy)
    r = axis_refutation(AXIS_RATE, e_rate, k, policy)
    if q.refuted:
        refuting, other = q, r
    elif r.refuted:
        refuting, other = r, q
    else:
        refuting, other = None, None
    def _margin(a: AxisRefutation | None) -> float | None:
        if a is None or a.margin is None:
            return None
        return round(float(a.margin), 6)

    return {
        "schema": SEQ_REFUTATION_SCHEMA,
        "source": source,
        "refuting_axis": refuting.axis if refuting is not None else None,
        "refuting_margin": _margin(refuting),
        "other_axis": other.axis if other is not None else None,
        "other_axis_margin": _margin(other),
        "both_axes_refuted": bool(q.refuted and r.refuted),
        "n_trials_at_stop": int(k),
        "axes": {AXIS_QUALITY: q.as_journal_dict(), AXIS_RATE: r.as_journal_dict()},
        "thresholds": {
            "policy_version": policy.version,
            "confirm_e": policy.confirm_e,
            "futility_e": policy.futility_e,
            "budget": policy.budget,
            "budget_min_e": policy.budget_min_e,
            "sticky_refuted": policy.sticky_refuted,
        },
        "captured_at": captured_at
        or datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


@dataclass(frozen=True)
class TrialStatistic:
    """A single trial-level observation used for one e-process update."""

    s: float
    r_eff: int
    z: float
    qids: tuple[str, ...]


@dataclass(frozen=True)
class EProcessUpdate:
    """Audit record for one wealth update."""

    k: int
    z: float
    lambda_t: float
    factor: float
    wealth: float
    state: str


@dataclass(frozen=True)
class CandidateSequentialView:
    """Rebuildable per-candidate view derived by folding trial observations."""

    fingerprint: str
    core_id: str
    trials: tuple[int, ...]
    quality_state: EProcessState
    quality_updates: tuple[EProcessUpdate, ...]
    state: str
    policy_version: str
    expected_axis: str = "quality"
    # SEQ-3a: count of journal-derived z observations rejected as non-finite /
    # out-of-domain during this rebuild (0 for clean evidence).
    out_of_range_skipped: int = 0


@dataclass(frozen=True)
class EProcessState:
    """Foldable e-process state for one candidate and one evidence axis."""

    wealth: float = 1.0
    k: int = 0
    sum_z: float = 0.0
    sum_z2: float = 0.0
    wealth_history: tuple[tuple[int | None, float], ...] = ()
    # SEQ-A: k at which this e-process FIRST met a refutation condition, or None.
    # Recorded unconditionally — observing that a stop happened is free and is
    # not the same as deciding it is permanent. Only `sticky_refuted` acts on it.
    # Defaults to None so a state reconstructed from an older persisted record
    # (which cannot carry this field) behaves exactly as it does today.
    first_refuted_k: int | None = None

    @property
    def mean_z(self) -> float:
        return self.sum_z / self.k if self.k else 0.0

    @property
    def var_z(self) -> float:
        if not self.k:
            return 0.0
        return max(0.0, self.sum_z2 / self.k - self.mean_z * self.mean_z)

    def next_lambda(self, policy: SequentialPolicy = DEFAULT_POLICY) -> float:
        """Predictable capped-Kelly bet using only past observations."""
        if self.k == 0:
            return _clip(policy.first_lambda, 0.0, policy.lambda_cap)
        mu = self.mean_z
        denom = self.var_z + mu * mu
        if denom <= 0.0:
            return 0.0
        return _clip(mu / denom, 0.0, policy.lambda_cap)

    def _meets_refutation(self, policy: SequentialPolicy) -> bool:
        """Refutation as a function of CURRENT state only (seq-v1 semantics)."""
        if self.wealth <= policy.futility_e:
            return True
        return self.k >= policy.budget and self.wealth < policy.budget_min_e

    def state_name(self, policy: SequentialPolicy = DEFAULT_POLICY) -> str:
        if self.wealth >= policy.confirm_e:
            return STATE_CONFIRMED
        if self._meets_refutation(policy):
            return STATE_REFUTED
        # SEQ-A / SEQ-A1. Under `sticky_refuted`, a stop decision is final: an
        # e-process that ever met the kill condition stays refuted even if later
        # evidence lifts it back over the line. Default False preserves seq-v1's
        # pure-function semantics exactly, so this branch is inert until an
        # operator ratifies the change.
        if policy.sticky_refuted and self.first_refuted_k is not None:
            return STATE_REFUTED
        return STATE_ACCUMULATING

    def update(
        self,
        z: float,
        *,
        policy: SequentialPolicy = DEFAULT_POLICY,
        trial_id: int | None = None,
    ) -> tuple["EProcessState", EProcessUpdate]:
        """Return the next e-process state and an audit update row."""
        z = float(z)
        lambda_t = self.next_lambda(policy)
        factor = 1.0 + lambda_t * z
        if factor < 0.0:
            raise ValueError(
                f"e-process update must stay nonnegative; lambda={lambda_t}, z={z}"
            )
        wealth = self.wealth * factor
        next_k = self.k + 1
        next_state = replace(
            self,
            wealth=wealth,
            k=next_k,
            sum_z=self.sum_z + z,
            sum_z2=self.sum_z2 + z * z,
            wealth_history=self.wealth_history + ((trial_id, wealth),),
            # First stop wins; a later recovery must not erase the record of it.
            first_refuted_k=self.first_refuted_k,
        )
        if next_state.first_refuted_k is None and next_state._meets_refutation(policy):
            next_state = replace(next_state, first_refuted_k=next_k)
        update = EProcessUpdate(
            k=next_state.k,
            z=z,
            lambda_t=lambda_t,
            factor=factor,
            wealth=wealth,
            state=next_state.state_name(policy),
        )
        return next_state, update


def baseline_profile_from_trials(
    trials: Iterable[Mapping[str, bool | int | float]],
) -> dict[str, float]:
    """Mean correctness per qid from baseline trial outcome maps."""
    values: dict[str, list[float]] = defaultdict(list)
    for trial in trials:
        for qid, correct in trial.items():
            values[str(qid)].append(_clip(float(correct), 0.0, 1.0))
    return {
        qid: sum(outcomes) / len(outcomes)
        for qid, outcomes in values.items()
        if outcomes
    }


def quality_trial_statistic(
    question_results: Mapping[str, bool | int | float] | Sequence[Mapping[str, Any]],
    baseline_profile: Mapping[str, float],
) -> TrialStatistic:
    """Compute the trial-level centered quality statistic from qid outcomes."""
    outcomes = _coerce_question_results(question_results)
    s = 0.0
    qids: list[str] = []
    for qid, observed in outcomes.items():
        if qid not in baseline_profile:
            continue
        p_base = _clip(float(baseline_profile[qid]), 0.0, 1.0)
        x = float(bool(observed))
        delta = x - p_base
        if 0.0 < p_base < 1.0 or x != round(p_base):
            qids.append(qid)
            s += delta

    r_eff = len(qids)
    z = s / r_eff if r_eff else 0.0
    return TrialStatistic(s=s, r_eff=r_eff, z=z, qids=tuple(sorted(qids)))


def rate_noninferiority_z(
    task_rate: float,
    baseline_task_rate: float,
    *,
    margin: float = DEFAULT_POLICY.rate_noninferiority_margin,
) -> float:
    """Task-rate non-inferiority statistic from 01c §3.

    H0 is ``E[y] <= -margin`` where ``y`` is relative task-rate lift. The
    returned value has nonpositive expectation under that null.

    SEQ-B validity fix — the lower clip was at ``-0.5`` and that docstring promise did
    not hold. Clipping is only mean-decreasing when it truncates the UPPER tail; a
    two-sided clip centered on 0 truncates the null-side (lower) tail too, which pulls
    ``E[y]`` UP toward 0 and can drive ``E[z]`` strictly POSITIVE under H0. The wealth
    process is then a SUBmartingale and Ville's inequality does not apply. Measured by
    simulating the exact code path at the null boundary (``true lift = -margin``) with
    Gaussian per-trial noise at the dispersion actually observed in the journal:
    ``P(sup E >= 20)`` was 0.066 at horizon 120 and 0.146 at horizon 400, against an
    alpha = 0.05 bound. This was latent only because the axis had never accumulated.

    The fix moves the LOWER clip to ``-1.0``, which is not a truncation at all: both
    rates are questions-per-hour and therefore nonnegative, so ``y = (r - b)/b >= -1``
    identically and the lower bound is an unreachable numerical guard. What remains is
    the UPPER clip at ``+0.5``, and ``E[clip_upper(y)] <= E[y] <= -margin`` under H0, so
    ``E[z] <= 0`` and the wealth is a genuine nonnegative supermartingale.

    The change is strictly CONSERVATIVE: ``z`` is unchanged for every ``y >= -0.5`` and
    strictly lower (more negative) below it, so a genuinely slow candidate is now
    penalized instead of having its penalty capped at the old floor.

    Factor nonnegativity is preserved. ``z`` now ranges over ``[-2 + 2*margin, 1.1]``;
    ``EProcessState.update`` requires ``z >= -1/lambda_cap``, which holds iff
    ``lambda_cap <= 0.5 / (1 - margin)`` (0.526 for margin=0.05, vs the policy's 0.5).
    The assertion below fails loudly rather than letting a future policy edit silently
    produce a negative wealth factor.
    """
    if baseline_task_rate <= 0.0:
        raise ValueError("baseline_task_rate must be positive")
    y = _clip((task_rate - baseline_task_rate) / baseline_task_rate, -1.0, 0.5)
    return (y + margin) / 0.5


def journal_seq_block(
    *,
    candidate: str,
    core_id: str,
    quality_update: EProcessUpdate,
    quality_state: EProcessState,
    policy: SequentialPolicy = DEFAULT_POLICY,
    rate_noninf_update: EProcessUpdate | None = None,
) -> dict[str, Any]:
    """Small JSON-serializable ``seq`` block for an evaluated trial row."""
    block: dict[str, Any] = {
        "candidate": candidate,
        "core_id": core_id,
        "k": quality_update.k,
        "z": round(quality_update.z, 6),
        "lambda": round(quality_update.lambda_t, 6),
        "E_quality": round(quality_state.wealth, 6),
        "state": quality_update.state,
        "policy_version": policy.version,
    }
    if rate_noninf_update is not None:
        block["E_rate_noninf"] = round(rate_noninf_update.wealth, 6)
        block["z_rate"] = round(rate_noninf_update.z, 6)
        # SEQ-B: the rate axis previously journaled only its wealth and its z. ``k`` and
        # ``lambda`` in this block are the QUALITY axis's, so a rate e-process stuck at
        # k=1, or frozen by lambda_rate=0 (which multiplies wealth by exactly 1.0 forever),
        # was indistinguishable in the journal from one that was accumulating normally.
        # That is why "E_rate_noninf never leaves ~1.0" survived undiagnosed for the
        # statistic's entire life. Journal the rate axis's own k and lambda.
        block["k_rate"] = rate_noninf_update.k
        block["lambda_rate"] = round(rate_noninf_update.lambda_t, 6)
    return block


def _z_lower_bound(policy: SequentialPolicy) -> float:
    """SEQ-3a factor-nonnegativity floor for ``z``: ``-1/lambda_cap`` (or -inf if uncapped)."""
    if policy.lambda_cap <= 0.0:
        return float("-inf")
    return -1.0 / policy.lambda_cap


def rebuild_candidate_view(
    *,
    candidate: str,
    core_id: str,
    observations: Iterable[Mapping[str, Any] | tuple[int | None, float]],
    policy: SequentialPolicy = DEFAULT_POLICY,
    expected_axis: str = "quality",
) -> CandidateSequentialView:
    """Fold journal rows or ``(trial_id, z)`` pairs into a candidate view.

    SEQ-3a: this is the PUBLIC entry point that accepts journal-derived z sequences.
    Each observed z is validated against the factor-nonnegativity floor
    (``_z_lower_bound`` = ``-1/lambda_cap``) BEFORE it reaches
    ``EProcessState.update`` — a non-finite or below-floor value (corrupt / mis-scaled
    journal evidence that would drive ``1 + lambda*z`` negative and raise) is SKIPPED
    and counted, never fed to the wealth update. Skipping (rather than clamping) is
    what preserves the anytime-valid guarantee: a skipped observation multiplies wealth
    by exactly 1.0, which cannot inflate the Ville false-confirm bound, whereas clamping
    would fabricate an observation that was never actually measured. No upper bound is
    imposed — a large-positive z keeps the factor nonnegative and is legitimate evidence.
    """
    state = EProcessState()
    updates: list[EProcessUpdate] = []
    trials: list[int] = []
    z_floor = _z_lower_bound(policy)
    skipped_out_of_range = 0
    for observation in observations:
        parsed = _coerce_seq_observation(
            observation,
            candidate=candidate,
            core_id=core_id,
            expected_axis=expected_axis,
        )
        if parsed is None:
            continue
        trial_id, z = parsed
        if not math.isfinite(z) or z < z_floor - _SEQ_Z_RANGE_EPS:
            skipped_out_of_range += 1
            continue
        state, update = state.update(z, policy=policy, trial_id=trial_id)
        updates.append(update)
        if trial_id is not None:
            trials.append(trial_id)
    if skipped_out_of_range:
        log.warning(
            "rebuild_candidate_view skipped %d non-finite / below-floor z value(s) for "
            "candidate=%s core_id=%s axis=%s (z floor=%.4f = -1/lambda_cap); corrupt "
            "journal evidence excluded to preserve e-process validity (SEQ-3a)",
            skipped_out_of_range,
            candidate,
            core_id,
            expected_axis,
            z_floor,
        )
    return CandidateSequentialView(
        fingerprint=candidate,
        core_id=core_id,
        trials=tuple(trials),
        quality_state=state,
        quality_updates=tuple(updates),
        state=state.state_name(policy),
        policy_version=policy.version,
        expected_axis=expected_axis,
        out_of_range_skipped=skipped_out_of_range,
    )


def empirical_ville_false_positive_rate(
    *,
    runs: int = 100_000,
    horizon: int = 12,
    policy: SequentialPolicy = DEFAULT_POLICY,
    seed: int = 20260612,
) -> float:
    """Simulate a mean-zero Rademacher null and return ``P(max E >= threshold)``."""
    rng = random.Random(seed)
    hits = 0
    for _ in range(runs):
        state = EProcessState()
        hit = False
        for _trial_idx in range(horizon):
            z = 1.0 if rng.random() < 0.5 else -1.0
            state, update = state.update(z, policy=policy)
            if update.state == STATE_CONFIRMED:
                hit = True
                break
        hits += int(hit)
    return hits / runs


def _coerce_question_results(
    question_results: Mapping[str, bool | int | float] | Sequence[Mapping[str, Any]],
) -> dict[str, bool]:
    """Read qid -> correctness, EXCLUDING rows that carry no quality signal.

    CJ-8. The compact journal rows already carry ``disposition`` (eval_tower
    stamps it at ``_compact_question_result``), and this coercer read only
    ``correct``. So an ``infra_failed`` row — a backend blip, a dropped
    response — arrived as ``correct=False`` and became ``x = 0.0`` in
    ``quality_trial_statistic``: a FABRICATED negative observation in an
    anytime-valid e-process, which then accumulates toward a refutation the
    candidate never earned.

    Excluded rows shrink ``r_eff`` rather than dragging ``z`` down, which is the
    same treatment ``rebuild_candidate_view`` already gives an out-of-domain
    observation: skip and count, never clamp.

    A row with NO disposition is admissible — the pre-taxonomy default is
    ``scored``, and flipping it would empty every historical denominator.
    """
    if isinstance(question_results, Mapping):
        # A bare {qid: correct} map carries no dispositions to filter on. Its
        # producer must filter before calling (autopilot._question_outcome_map).
        return {str(qid): bool(correct) for qid, correct in question_results.items()}
    outcomes: dict[str, bool] = {}
    for item in question_results:
        qid = str(item.get("qid") or item.get("question_id") or "").strip()
        if not qid:
            continue
        if not is_quality_admissible(item.get("disposition")):
            continue
        outcomes[qid] = bool(item.get("correct"))
    return outcomes


def excluded_question_results(
    question_results: Mapping[str, bool | int | float] | Sequence[Mapping[str, Any]],
) -> dict[str, int]:
    """Count, by disposition, the rows :func:`_coerce_question_results` dropped.

    Exported so a caller can REPORT the exclusion. A row that vanishes silently
    from a denominator is indistinguishable from one that was never asserted.
    """
    counts: dict[str, int] = {}
    if isinstance(question_results, Mapping):
        return counts
    for item in question_results:
        disposition = item.get("disposition")
        if not is_quality_admissible(disposition):
            key = str(disposition)
            counts[key] = counts.get(key, 0) + 1
    return counts


# SEQ-B: which journal field carries each axis's per-trial statistic. `journal_seq_block`
# writes the quality statistic as ``z`` and the rate statistic as ``z_rate``, so a
# rate-axis rebuild fed journal ROWS must read ``z_rate``. It previously always read
# ``z`` — `expected_axis` was accepted, stored on the view, and never consulted — so a
# rate rebuild from journal rows would have silently folded QUALITY evidence into the
# rate wealth. The live gate happens to pass ``(trial_id, z)`` tuples, so this was latent
# rather than firing; it is fixed here because `rebuild_candidate_view` is the documented
# public entry point for journal-derived evidence.
_SEQ_AXIS_Z_FIELDS: dict[str, tuple[str, ...]] = {
    "quality": ("z",),
    "rate": ("z_rate",),
}


def _coerce_seq_observation(
    observation: Mapping[str, Any] | tuple[int | None, float],
    *,
    candidate: str,
    core_id: str,
    expected_axis: str = "quality",
) -> tuple[int | None, float] | None:
    if isinstance(observation, tuple):
        trial_id, z = observation
        return trial_id, float(z)
    seq = observation.get("seq")
    block = seq if isinstance(seq, Mapping) else observation
    block_candidate = block.get("candidate")
    if block_candidate is not None and str(block_candidate) != candidate:
        return None
    block_core = block.get("core_id")
    if block_core is not None and str(block_core) != core_id:
        return None
    z_fields = _SEQ_AXIS_Z_FIELDS.get(expected_axis, _SEQ_AXIS_Z_FIELDS["quality"])
    z_field = next((name for name in z_fields if name in block), None)
    if z_field is None:
        return None
    raw_trial_id = observation.get("trial_id", block.get("trial_id"))
    trial_id = int(raw_trial_id) if raw_trial_id is not None else None
    return trial_id, float(block[z_field])


def _clip(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))
