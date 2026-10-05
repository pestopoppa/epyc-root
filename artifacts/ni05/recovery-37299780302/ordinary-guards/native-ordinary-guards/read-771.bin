"""SEQ-B: the sequential rate axis must be a PAIRED measurement that can actually confirm.

Why this file exists
--------------------
`E_rate_noninf` never left ~1.0 across the entire recorded history of the statistic —
396 sequenced trials, 141 candidates, 0 confirms — and every existing test passed the
whole time. They passed because none of them crossed the seam where the defect lived:

  * `test_safety_gate_sequential_verdict.py` proves the JOINT RULE (given E_rate >= 20
    the gate confirms) by HAND-FEEDING `prior_rate_obs=[(i, 1.2) ...]` and
    `task_rate=1.0, baseline_task_rate=0.5`. z = 1.2 is not even reachable —
    `rate_noninferiority_z` maxes at 1.1 — and a 100% throughput lift never occurs. The
    test proves the CONSUMER works; nothing tested whether the PRODUCER can ever emit
    such evidence.
  * `test_sequential_verdict.py::test_rate_noninferiority_z_has_zero_boundary_at_margin`
    tests the z transform on clean literals (95/100, 100/100, 110/100). It never asks
    where those two numbers come from.
  * Nothing asserted that the candidate's rate and the incumbent comparator are the SAME
    measurement. They were not: `task_rate_qph_from(result)` divided the DECISION
    partition question count by the FULL batch's wall clock, while the comparator in
    `autopilot._seq_inputs_for_trial` divided the FULL `question_results` count by the
    same wall clock. A candidate identical to the incumbent measured 55/65 = 0.846x its
    own throughput => z_rate = -0.208 on every trial => `next_lambda` clipped the
    negative running mean to 0 => the wealth factor became exactly 1.0 => frozen.

The missing assertion was never "confirmed is False" — that passed throughout. It is
"given evidence this strong, the gate MUST confirm", plus "an unchanged config is not a
regression". Both are asserted below.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "autopilot"))

import autopilot  # type: ignore[import-not-found]  # noqa: E402
from experiment_journal import ExperimentJournal, JournalEntry  # noqa: E402
from safety_gate import EvalResult, SafetyGate  # type: ignore[import-not-found]  # noqa: E402

from src.autopilot_core.sequential_verdict import (  # noqa: E402
    DEFAULT_POLICY,
    EProcessState,
    SequentialPolicy,
    journal_seq_block,
    rate_noninferiority_z,
    rebuild_candidate_view,
)
from src.autopilot_core.tier_specs import (  # noqa: E402
    SEQ_RATE_MIN_SECONDS_PER_QUESTION,
    seq_task_rate_qph,
    seq_task_rate_qph_from,
    seq_task_rate_qph_from_row,
    task_rate_qph_from,
    task_rate_qph_from_row,
)


# ---------------------------------------------------------------------------
# fixtures — the exact shape EvalTower._aggregate_decision_partitions produces
# ---------------------------------------------------------------------------
DECISION_N = 55  # core questions -> EvalResult.n_questions / details.total
FULL_N = 65      # core + audit-shadow -> question_results (copied from the full result)
WALL_S = 1200.0  # wall clock of the FULL batch (max(r.eval_wall_s) over all questions)


def _audit_shadow_result(
    *,
    decision_n: int = DECISION_N,
    full_n: int = FULL_N,
    eval_wall_s: float = WALL_S,
    quality: float = 2.5,
) -> EvalResult:
    """An EvalResult shaped like `EvalTower._aggregate_decision_partitions` returns it.

    `n_questions` / `details.total` count only the DECISION partition; `question_results`
    is the FULL per-question ledger the method explicitly copies over from the full
    result; `eval_wall_s` is the FULL batch's wall clock. That combination is the defect
    surface: numerator from one population, denominator from another.
    """
    qr = [
        {"qid": f"q{i}", "suite": "coder", "correct": i % 2 == 0}
        for i in range(full_n)
    ]
    return EvalResult(
        tier=2,
        quality=quality,
        speed=12.7,
        cost=0.1,
        reliability=0.99,
        per_suite_quality={"coder": quality},
        n_questions=decision_n,
        question_results=qr,
        eval_wall_s=eval_wall_s,
        details={
            "total": decision_n,
            "n_questions": decision_n,
            "eval_wall_s": eval_wall_s,
            "audit_shadow_excluded_partitions": ["audit"],
        },
    )


def _journal_row_for(result: EvalResult) -> dict:
    """The journal row the autopilot writes for that EvalResult."""
    return {
        "quality": result.quality,
        "eval_details": {
            "eval_wall_s": result.eval_wall_s,
            "question_results": list(result.question_results),
            "details": dict(result.details),
        },
    }


def _entry(trial_id: int, action: dict, *, eval_wall_s: float, n: int = 10) -> JournalEntry:
    return JournalEntry(
        trial_id=trial_id,
        timestamp="2026-06-18T00:00:00Z",
        species="test",
        action_type=str(action.get("type") or "seed_batch"),
        tier=1,
        quality=3.0,
        speed=10.0,
        cost=0.2,
        reliability=1.0,
        pareto_status="frontier",
        config_snapshot=dict(action),
        eval_details={
            "eval_wall_s": eval_wall_s,
            "question_results": [{"qid": f"q{i}", "correct": True} for i in range(n)],
        },
    )


# ---------------------------------------------------------------------------
# 1. THE ROOT-CAUSE TEST: a trial compared against ITSELF is not a regression
# ---------------------------------------------------------------------------
def test_a_trial_compared_against_itself_is_not_a_rate_regression() -> None:
    """The single assertion that would have caught SEQ-B on day one.

    Under the pre-fix pairing this scored a 15% throughput REGRESSION for a config that
    had not changed at all.
    """
    result = _audit_shadow_result()
    row = _journal_row_for(result)

    candidate_rate = seq_task_rate_qph_from(result)
    incumbent_rate = seq_task_rate_qph_from_row(row)

    assert candidate_rate is not None and incumbent_rate is not None
    # Same trial, same wall clock, same questions => IDENTICAL rate. Not "close".
    assert candidate_rate == pytest.approx(incumbent_rate, rel=0, abs=0)

    z = rate_noninferiority_z(candidate_rate, incumbent_rate)
    # An unchanged config sits at the equality point, which is strictly INSIDE H1 for a
    # non-inferiority test with margin > 0: it accrues positive evidence.
    assert z == pytest.approx(DEFAULT_POLICY.rate_noninferiority_margin / 0.5)
    assert z > 0.0


def test_the_pre_fix_pairing_scored_an_unchanged_config_as_a_regression() -> None:
    """Pins the DEFECT itself so a revert cannot pass silently.

    This reconstructs the exact pre-SEQ-B pairing — candidate through
    `task_rate_qph_from`, incumbent through `task_rate_qph_from_row` with
    `n_questions=len(question_results)` — and shows it is negative. If someone reroutes
    the rate axis back through these two functions, test #1 fails and this one explains
    why.
    """
    result = _audit_shadow_result()
    row = _journal_row_for(result)

    legacy_candidate = task_rate_qph_from(result)                 # 55 / wall
    legacy_incumbent = task_rate_qph_from_row(                    # 65 / wall
        {**row, "n_questions": len(result.question_results)}
    )

    assert legacy_candidate / legacy_incumbent == pytest.approx(DECISION_N / FULL_N)
    assert rate_noninferiority_z(legacy_candidate, legacy_incumbent) < 0.0


# ---------------------------------------------------------------------------
# 2. THE MISSING ASSERTION: evidence this strong MUST confirm
# ---------------------------------------------------------------------------
def test_equal_throughput_accumulates_and_reaches_confirm_e() -> None:
    """"Given evidence this strong, the gate MUST confirm."

    A candidate whose throughput exactly matches the incumbent is non-inferior, so the
    rate e-process must GROW and eventually cross `confirm_e`. Under the defect the
    wealth sat at 0.91 and multiplied by exactly 1.0 forever, so a test asserting only
    `confirmed is False` passed for the statistic's entire life.
    """
    rate = 200.0
    z = rate_noninferiority_z(rate, rate)
    assert z > 0.0

    state = EProcessState()
    wealth_at = {}
    for trial in range(1, 81):
        state, update = state.update(z, policy=DEFAULT_POLICY, trial_id=trial)
        wealth_at[trial] = update.wealth
        # the freeze signature: lambda == 0 => factor == 1.0 => no evidence ever again
        assert update.factor > 1.0, f"wealth froze at trial {trial}"

    # clears the budget kill bar long before the budget rule could refute it
    assert wealth_at[20] > DEFAULT_POLICY.budget_min_e
    # and reaches the confirm threshold on real, reachable evidence
    assert state.wealth >= DEFAULT_POLICY.confirm_e
    assert state.state_name(DEFAULT_POLICY) == "confirmed"


def test_a_faster_candidate_confirms_the_rate_axis_faster_than_an_equal_one() -> None:
    """Monotonicity: more throughput => fewer trials to confirm. A statistic that is
    genuinely measuring something must order these correctly."""

    def trials_to_confirm(lift: float) -> int:
        state = EProcessState()
        z = rate_noninferiority_z(200.0 * (1.0 + lift), 200.0)
        for trial in range(1, 500):
            state, _ = state.update(z, policy=DEFAULT_POLICY, trial_id=trial)
            if state.wealth >= DEFAULT_POLICY.confirm_e:
                return trial
        raise AssertionError(f"never confirmed at lift={lift}")

    assert trials_to_confirm(0.20) < trials_to_confirm(0.10) < trials_to_confirm(0.0)


def test_a_genuinely_slower_candidate_never_confirms_the_rate_axis() -> None:
    """The other half of the contract. A fix that confirms everything is as broken as one
    that confirms nothing."""
    state = EProcessState()
    z = rate_noninferiority_z(140.0, 200.0)  # 30% slower, well past the 5% margin
    assert z < 0.0
    for trial in range(1, 201):
        state, _ = state.update(z, policy=DEFAULT_POLICY, trial_id=trial)
        assert state.wealth < DEFAULT_POLICY.confirm_e
    assert state.state_name(DEFAULT_POLICY) == "refuted"


# ---------------------------------------------------------------------------
# 3. ANYTIME-VALIDITY: E[z] <= 0 under H0 must survive the clip
# ---------------------------------------------------------------------------
def test_rate_z_expectation_stays_nonpositive_under_a_heavy_lower_tail_null() -> None:
    """The clip must never RAISE E[z] above 0 under H0.

    Clipping is mean-decreasing only when it truncates the UPPER tail. The pre-fix
    two-sided clip at [-0.5, 0.5] also truncated the null-side lower tail, which pulls
    E[y] up toward 0 and can make E[z] strictly positive under H0 — the wealth is then a
    SUBmartingale and Ville's inequality does not apply.

    This null sits exactly at the H0 boundary (E[y] = -margin) with mass below -0.5,
    which is precisely where the old clip broke.
    """
    margin = DEFAULT_POLICY.rate_noninferiority_margin
    base = 100.0
    # E[y] = -margin exactly: a heavy but rare slow tail against frequent small gains.
    outcomes = [(-0.80, 0.25), (0.20, 0.75)]
    assert sum(y * p for y, p in outcomes) == pytest.approx(-margin)

    e_z = sum(rate_noninferiority_z(base * (1.0 + y), base) * p for y, p in outcomes)
    assert e_z <= 0.0 + 1e-12, f"E[z] = {e_z} > 0 under H0: wealth is not a supermartingale"

    # and the pre-fix two-sided clip is shown to fail the same null
    def _legacy_z(y: float) -> float:
        return (max(-0.5, min(0.5, y)) + margin) / 0.5

    legacy_e_z = sum(_legacy_z(y) * p for y, p in outcomes)
    assert legacy_e_z > 0.0


def test_rate_z_range_keeps_the_wealth_factor_nonnegative() -> None:
    """z must stay >= -1/lambda_cap or `EProcessState.update` raises and the rebuild
    would have to skip real evidence."""
    floor = -1.0 / DEFAULT_POLICY.lambda_cap
    # the worst physically possible observation: a candidate that produced nothing
    worst = rate_noninferiority_z(0.0, 100.0)
    assert worst >= floor
    state, update = EProcessState().update(worst, policy=DEFAULT_POLICY)
    assert update.factor >= 0.0

    # and it survives the rebuild's out-of-domain filter rather than being skipped
    view = rebuild_candidate_view(
        candidate="c", core_id="core_v1",
        observations=[(1, worst)], policy=DEFAULT_POLICY, expected_axis="rate",
    )
    assert view.out_of_range_skipped == 0


def test_policy_rejects_a_lambda_cap_that_would_break_factor_nonnegativity() -> None:
    with pytest.raises(ValueError, match="negative wealth factor"):
        SequentialPolicy(lambda_cap=0.9)


# ---------------------------------------------------------------------------
# 4. MISSING MEASUREMENT MUST SKIP, NEVER FABRICATE
# ---------------------------------------------------------------------------
def test_unmeasurable_rate_returns_none_not_a_zero_sentinel() -> None:
    """`task_rate_qph_from` returns 0.0 for "unavailable". Fed to
    `rate_noninferiority_z` that is a MEASURED throughput of zero => y = -1 => the worst
    observation the statistic can express, invented out of missing data."""
    no_wall = _audit_shadow_result(eval_wall_s=0.0)
    assert task_rate_qph_from(no_wall) == 0.0          # the sentinel that lied
    assert seq_task_rate_qph_from(no_wall) is None     # now distinguishable

    # an aborted batch is not a throughput measurement either
    aborted = _audit_shadow_result(eval_wall_s=FULL_N * SEQ_RATE_MIN_SECONDS_PER_QUESTION / 2)
    assert seq_task_rate_qph_from(aborted) is None
    assert seq_task_rate_qph_from_row(_journal_row_for(aborted)) is None


def test_gate_omits_the_rate_axis_when_the_rate_was_not_measured(tmp_path) -> None:
    gate = SafetyGate(baseline_path=tmp_path / "absent.yaml", use_sequential=True)
    result = _audit_shadow_result(eval_wall_s=0.0)
    verdict = gate.check(
        result,
        question_results=result.question_results,
        baseline_profile={f"q{i}": 0.5 for i in range(FULL_N)},
        task_rate=seq_task_rate_qph_from(result),
        baseline_task_rate=200.0,
        prior_quality_obs=[(i, 1.2) for i in range(10)],
        candidate="cand",
        core_id="core_v1",
    )

    assert verdict.seq is not None
    assert verdict.seq["rate_axis_available"] is False
    assert verdict.seq["rate_axis_skip_reason"] == "candidate_task_rate_not_measured"
    assert "E_rate_noninf" not in verdict.seq
    # strong quality alone still cannot ratchet the baseline
    assert verdict.seq["confirmed"] is False


def test_gate_omits_the_rate_axis_when_the_comparator_is_unavailable(tmp_path) -> None:
    gate = SafetyGate(baseline_path=tmp_path / "absent.yaml", use_sequential=True)
    result = _audit_shadow_result()
    verdict = gate.check(
        result,
        question_results=result.question_results,
        baseline_profile={f"q{i}": 0.5 for i in range(FULL_N)},
        task_rate=seq_task_rate_qph_from(result),
        baseline_task_rate=None,
        prior_quality_obs=[(i, 1.2) for i in range(10)],
        candidate="cand",
        core_id="core_v1",
    )
    assert verdict.seq["rate_axis_available"] is False
    assert verdict.seq["rate_axis_skip_reason"] == "incumbent_task_rate_comparator_unavailable"


# ---------------------------------------------------------------------------
# 5. THE COMPARATOR MUST BE ROBUST AND PREDICTABLE
# ---------------------------------------------------------------------------
def test_one_aborted_trial_cannot_move_the_incumbent_comparator(tmp_path) -> None:
    """Journal evidence: trial 1302 recorded 65 questions in 0.054 s = 4.3 MILLION
    questions/hour. Inside a 120-row arithmetic MEAN that single row moves the comparator
    by ~36,000 qph and pins every subsequent candidate at the clip floor forever."""
    action = {"type": "seed_batch", "n_questions": 10}
    journal = ExperimentJournal(journal_dir=tmp_path)
    # three honest incumbent rows: 10 questions in 1800 s => 20 qph
    for tid in (1, 2, 3):
        journal.record(_entry(tid, action, eval_wall_s=1800.0))

    clean = autopilot._seq_inputs_for_trial(journal=journal, action=action, tier=1)
    assert clean["baseline_task_rate"] == pytest.approx(20.0)

    # now add an aborted batch: 10 questions in 0.054 s
    journal.record(_entry(4, action, eval_wall_s=0.054))
    poisoned = autopilot._seq_inputs_for_trial(journal=journal, action=action, tier=1)

    assert poisoned["baseline_task_rate"] == pytest.approx(20.0), (
        "an aborted trial changed the incumbent comparator"
    )


def test_comparator_is_unavailable_below_the_minimum_trial_count(tmp_path) -> None:
    """A comparator built from one row is a guess, not a null. Journal evidence: trial
    836 ran the rate axis against a single prior row."""
    action = {"type": "seed_batch", "n_questions": 10}
    journal = ExperimentJournal(journal_dir=tmp_path)
    for tid in (1, 2, 3):
        journal.record(_entry(tid, action, eval_wall_s=1800.0))
    # quality profile needs 3 rows; make the rate pool thinner than the rate minimum by
    # stripping the wall clock from all but one of them
    thin = ExperimentJournal(journal_dir=tmp_path / "thin")
    for tid in (1, 2, 3):
        entry = _entry(tid, action, eval_wall_s=1800.0 if tid == 1 else 0.0)
        thin.record(entry)
    inputs = autopilot._seq_inputs_for_trial(journal=thin, action=action, tier=1)
    assert inputs["baseline_task_rate"] is None


# ---------------------------------------------------------------------------
# 6. THE AXIS MUST BE AUDITABLE FROM THE JOURNAL ALONE
# ---------------------------------------------------------------------------
def test_journal_block_records_the_rate_axis_own_k_and_lambda() -> None:
    """`k` and `lambda` in the seq block are the QUALITY axis's. Without the rate axis's
    own counters a frozen rate e-process (lambda == 0 => factor == 1.0) is
    indistinguishable in the journal from one that is accumulating normally — which is
    exactly why this survived undiagnosed."""
    q_state, q_update = EProcessState().update(0.5, policy=DEFAULT_POLICY, trial_id=1)
    r_state = EProcessState()
    for _ in range(4):
        r_state, r_update = r_state.update(0.1, policy=DEFAULT_POLICY, trial_id=1)

    block = journal_seq_block(
        candidate="c", core_id="core_v1",
        quality_update=q_update, quality_state=q_state,
        rate_noninf_update=r_update,
    )

    assert block["k"] == 1                 # quality axis
    assert block["k_rate"] == 4            # rate axis, independently tracked
    assert block["lambda_rate"] == pytest.approx(DEFAULT_POLICY.lambda_cap)
    assert block["E_rate_noninf"] == pytest.approx(r_state.wealth)


def test_rate_axis_rebuild_reads_z_rate_not_the_quality_z() -> None:
    """`rebuild_candidate_view` accepted `expected_axis` and never consulted it, so a
    rate rebuild fed JOURNAL ROWS folded QUALITY evidence into the rate wealth."""
    rows = [
        {"trial_id": i, "seq": {"candidate": "c", "core_id": "core_v1", "z": 1.0, "z_rate": -0.5}}
        for i in range(5)
    ]
    rate_view = rebuild_candidate_view(
        candidate="c", core_id="core_v1", observations=rows,
        policy=DEFAULT_POLICY, expected_axis="rate",
    )
    quality_view = rebuild_candidate_view(
        candidate="c", core_id="core_v1", observations=rows,
        policy=DEFAULT_POLICY, expected_axis="quality",
    )

    assert rate_view.quality_state.mean_z == pytest.approx(-0.5)
    assert quality_view.quality_state.mean_z == pytest.approx(1.0)
    assert rate_view.quality_state.wealth < 1.0 < quality_view.quality_state.wealth


# ---------------------------------------------------------------------------
# 7. END-TO-END: the gate's own producer must emit growing rate evidence
# ---------------------------------------------------------------------------
def test_gate_accrues_real_rate_wealth_for_a_candidate_that_matches_the_incumbent(
    tmp_path,
) -> None:
    """Drives `SafetyGate.check` the way the autopilot loop does — threading each trial's
    journaled z_rate into the next trial's `prior_rate_obs` — with a candidate whose
    measured throughput equals the incumbent comparator.

    Under the defect this produced E_rate_noninf = 0.91, frozen, forever.
    """
    gate = SafetyGate(baseline_path=tmp_path / "absent.yaml", use_sequential=True)
    incumbent_rate = seq_task_rate_qph_from_row(_journal_row_for(_audit_shadow_result()))
    baseline_profile = {f"q{i}": 0.5 for i in range(FULL_N)}

    prior_quality_obs: list[tuple[int, float]] = []
    prior_rate_obs: list[tuple[int, float]] = []
    seq = None
    for trial in range(30):
        result = _audit_shadow_result()
        verdict = gate.check(
            result,
            question_results=result.question_results,
            baseline_profile=baseline_profile,
            task_rate=seq_task_rate_qph_from(result),
            baseline_task_rate=incumbent_rate,
            prior_quality_obs=list(prior_quality_obs),
            prior_rate_obs=list(prior_rate_obs),
            candidate="cand",
            core_id="core_v1",
        )
        seq = verdict.seq
        assert seq is not None
        assert seq["rate_axis_available"] is True
        assert seq["z_rate"] > 0.0, "an unchanged config scored a rate regression"
        prior_quality_obs.append((trial, seq["z"]))
        prior_rate_obs.append((trial, seq["z_rate"]))

    assert seq["k_rate"] == 30
    assert seq["lambda_rate"] > 0.0, "the rate e-process froze (lambda == 0)"
    # 30 trials of genuine non-inferiority is real evidence: past the budget kill bar and
    # an order of magnitude above the frozen 0.91 the defect produced.
    assert seq["E_rate_noninf"] > DEFAULT_POLICY.budget_min_e
    assert seq["task_rate_qph"] == pytest.approx(seq["baseline_task_rate_qph"])


def test_seq_rate_question_count_is_symmetric_across_result_and_row() -> None:
    """Both sides count the questions the wall clock covers, deduplicated by qid, with the
    same fallback order. Any divergence here re-opens SEQ-B."""
    result = _audit_shadow_result()
    row = _journal_row_for(result)
    assert seq_task_rate_qph_from(result) == seq_task_rate_qph_from_row(row)

    # duplicate qids must not inflate either side
    dup = _audit_shadow_result()
    dup.question_results = list(dup.question_results) + list(dup.question_results)
    assert seq_task_rate_qph_from(dup) == pytest.approx(seq_task_rate_qph_from(result))

    # with no per-question ledger both sides fall back to the declared count identically
    bare = seq_task_rate_qph(question_results=None, n_questions=DECISION_N, eval_wall_s=WALL_S)
    assert bare == pytest.approx(DECISION_N / (WALL_S / 3600.0))
