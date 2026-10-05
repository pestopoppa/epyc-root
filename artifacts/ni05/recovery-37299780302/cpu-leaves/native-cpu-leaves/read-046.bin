"""AP-55 (b) same-regime seed re-run + (c) candidate-batch homogeneity.

Pins: a declared-only kernel (server PIDs invisible) never compares COMPARABLE;
the chi-square is exact against reference values; unfingerprinted / unpinned
legacy rows are excluded, never back-filled; shadow mode never holds; enforce
holds only on definitive negatives; the autopilot forces a re-run on a regime
change (with a churn guard) and the paired diagnostic skips foreign-regime draws.
"""

from __future__ import annotations

import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

# ── clock pinning ────────────────────────────────────────────────────────────
# `_seq_baseline_reference_state` defaults `now_ts` to `time.time()` and marks a
# reference draw stale after SEQ_BASELINE_REFERENCE_STALE_AFTER_S (48h), so a
# journal fixture dated with a hard-coded wall-clock timestamp silently flips the
# seq-cadence assertions 48h after it was written (it did: the fixtures were
# pinned to 2026-09-16T00:00:00Z in 0e6e2288 and rotted two days later).
# Fixtures are therefore dated RELATIVE to a pinned clock, and `_pinned_clock`
# freezes `time.time()` at that same instant for every test in this file, so the
# reference age is a property of the fixture and never of the calendar.
# Move the pin to prove the file is clock-independent, e.g.
#   AP55_TEST_PINNED_NOW_S=1852675200 python -m pytest tests/unit/test_ap55_promotion_gate.py
_PINNED_NOW_S = float(os.environ.get("AP55_TEST_PINNED_NOW_S", "1789516800"))  # 2026-09-16Z
_FIXTURE_AGE_S = 3600.0  # fresh w.r.t. the 48h staleness threshold


def _fixture_ts(age_s: float = _FIXTURE_AGE_S) -> str:
    """An ISO timestamp `age_s` seconds before the pinned clock."""
    return datetime.fromtimestamp(_PINNED_NOW_S - age_s, tz=timezone.utc).isoformat()


@pytest.fixture(autouse=True)
def _pinned_clock(monkeypatch):
    monkeypatch.setattr(time, "time", lambda: _PINNED_NOW_S)


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "autopilot"))

from src.autopilot_core import ap55_promotion_gate as g  # noqa: E402
from src.autopilot_core import infra_fingerprint as inf  # noqa: E402
from src.autopilot_core.infra_fingerprint import (  # noqa: E402
    COMPARABLE,
    NON_COMPARABLE,
    UNVERIFIED,
    compare_infra_fingerprints,
)


def _fp(evidence: str = "live", declared: str = "bin-a", **digests):
    full = {name: f"d-{name}" for name in inf.COMPONENTS}
    full.update(digests)
    kernel = {"declared_binaries": {"/b/llama-server": declared},
              "live_binaries": {"/b/llama-server": declared} if evidence == "live" else {},
              "live_libraries": {}}
    return {"digest": inf._digest(full), "component_digests": full,
            "components": {"kernel": kernel}}


# ── kernel evidence / declared-only fallback ─────────────────────────────────


def test_declared_only_kernel_never_comparable():
    a, b = _fp("declared_only"), _fp("declared_only")
    assert inf.kernel_evidence(a) == "declared_only"
    verdict = compare_infra_fingerprints(a, b)
    assert verdict["status"] == UNVERIFIED
    assert verdict["unverified_components"] == ["kernel"]
    assert verdict["kernel_basis"] == "declared_only"


def test_declared_only_binary_change_is_non_comparable():
    a = _fp("declared_only", declared="bin-a", kernel="k1")
    b = _fp("declared_only", declared="bin-b", kernel="k2")
    verdict = compare_infra_fingerprints(a, b)
    assert verdict["status"] == NON_COMPARABLE
    assert verdict["differing_components"] == ["kernel"]


def test_live_vs_declared_is_not_a_false_regime_change():
    live = _fp("live", kernel="k-live")
    declared = _fp("declared_only", kernel="k-declared")
    assert compare_infra_fingerprints(live, declared)["status"] == UNVERIFIED


def test_both_live_matching_is_comparable_and_explicit_field_wins():
    assert compare_infra_fingerprints(_fp(), _fp())["status"] == COMPARABLE
    fp = _fp("declared_only")
    fp["kernel_evidence"] = "live"
    assert inf.kernel_evidence(fp) == "live"


def test_fingerprint_without_kernel_detail_is_unknown_not_comparable():
    full = {name: "x" for name in inf.COMPONENTS}
    bare = {"digest": "d", "component_digests": full}
    assert inf.kernel_evidence(bare) == "unknown"
    assert compare_infra_fingerprints(bare, dict(bare))["status"] == UNVERIFIED


def test_collector_records_declared_only_when_pids_invisible(tmp_path):
    binary = tmp_path / "llama-server"
    binary.write_bytes(b"elf")
    (tmp_path / "proc").mkdir()
    fp = inf.collect_infra_fingerprint(
        orchestrator_root=tmp_path, stack_state={"r": {"pid": 99999999}},
        fallback_binary=binary, proc_root=tmp_path / "proc", sys_root=tmp_path / "sys",
    )
    assert fp["kernel_evidence"] == "declared_only"
    assert compare_infra_fingerprints(fp, fp)["status"] == UNVERIFIED


# ── chi-square ───────────────────────────────────────────────────────────────


@pytest.mark.parametrize("x,df,expected", [
    (3.841458820694124, 1, 0.05),
    (5.991464547107979, 2, 0.05),
    (7.814727903251178, 3, 0.05),
    (11.070497693516351, 5, 0.05),
    (2.0, 4, 0.7357588823428847),
    (0.0, 3, 1.0),
])
def test_chi2_sf_matches_reference(x, df, expected):
    assert g.chi2_sf(x, df) == pytest.approx(expected, rel=1e-9)


def test_chi2_homogeneity_known_table():
    # 2x2: 30/50 vs 20/50 -> chi2 = 4.0, p = 0.0455
    out = g.chi2_homogeneity([(30, 50), (20, 50)])
    assert out["statistic"] == pytest.approx(4.0)
    assert out["p_value"] == pytest.approx(0.04550026, rel=1e-6)
    assert out["df"] == 1 and out["low_expected_counts"] is False


def test_chi2_homogeneity_degenerate():
    assert g.chi2_homogeneity([(3, 5)])["p_value"] is None
    assert g.chi2_homogeneity([(5, 5), (7, 7)])["p_value"] == 1.0


# ── batch + seed legs ────────────────────────────────────────────────────────


def _row(tid, *, fp=None, rev=7, correct=5, scored=10, key="cfgA", seed=False, tier=1, **over):
    row = {
        "trial_id": tid, "tier": tier, "outcome_status": "ok", "bug_corrupted_by": "",
        "baseline_pin": {"baseline_revision": rev} if rev is not None else {},
        "infra_fingerprint": fp if fp is not None else {},
        "eval_details": {"seq_baseline_reference_draw": seed, "counts": (correct, scored)},
        "config_snapshot": {"key": key},
    }
    row.update(over)
    return row


def _gate(rows, cand_fp, *, counts=(9, 10), key="cfgC", rev=7, mode="enforce"):
    return g.promotion_gate(
        rows, tier=1, baseline_revision=rev, candidate_key=key, candidate_counts=counts,
        candidate_fingerprint=cand_fp,
        counts_fn=lambda r: r["eval_details"]["counts"],
        key_fn=lambda r: r["config_snapshot"]["key"],
        mode=mode, alpha=0.05,
    )


def test_seed_rerun_missing_when_only_legacy_rows():
    rows = [_row(1, seed=True)]  # unfingerprinted legacy re-run
    seed = g.seed_rerun_verdict(rows, tier=1, candidate_fingerprint=_fp())
    assert seed["status"] == g.MISSING
    assert seed["unfingerprinted_reruns"] == 1


def test_seed_rerun_prefers_newest_same_regime_draw():
    rows = [_row(1, fp=_fp(), seed=True), _row(2, fp=_fp(orchestrator="new"), seed=True)]
    seed = g.seed_rerun_verdict(rows, tier=1, candidate_fingerprint=_fp())
    assert seed["status"] == COMPARABLE and seed["trial_id"] == 1
    assert seed["non_comparable_reruns"] == 1


def test_seed_rerun_non_comparable_names_component():
    rows = [_row(1, fp=_fp(models="old"), seed=True)]
    seed = g.seed_rerun_verdict(rows, tier=1, candidate_fingerprint=_fp())
    assert seed["status"] == NON_COMPARABLE
    assert seed["differing_components"] == ["models"]


def test_seed_rerun_ignores_other_tier_and_corrupted():
    rows = [_row(1, fp=_fp(), seed=True, tier=2),
            _row(2, fp=_fp(), seed=True, bug_corrupted_by="reload"),
            _row(3, fp=_fp(), seed=True, outcome_status="skipped")]
    assert g.seed_rerun_verdict(rows, tier=1, candidate_fingerprint=_fp())["status"] == g.MISSING


def test_homogeneous_batch_holds_in_enforce_not_in_shadow():
    rows = [_row(1, fp=_fp(), seed=True, correct=5), _row(2, fp=_fp(), correct=5, key="cfgA")]
    enforced = _gate(rows, _fp(), counts=(6, 10))
    assert enforced["batch_homogeneity"]["status"] == g.HOMOGENEOUS
    assert enforced["seed_rerun"]["status"] == COMPARABLE
    assert enforced["hold"] and enforced["hold_reasons"] == ["batch:HOMOGENEOUS"]
    shadow = _gate(rows, _fp(), counts=(6, 10), mode="shadow")
    assert shadow["hold"] is False and shadow["batch_homogeneity"]["status"] == g.HOMOGENEOUS


def test_heterogeneous_batch_with_same_regime_seed_passes_enforce():
    rows = [_row(1, fp=_fp(), seed=True, correct=10, scored=50),
            _row(2, fp=_fp(), correct=12, scored=50)]
    out = _gate(rows, _fp(), counts=(40, 50))
    batch = out["batch_homogeneity"]
    assert batch["status"] == g.HETEROGENEOUS
    assert batch["leader"] == "cfgC" and batch["candidate_rank"] == 1
    assert out["hold"] is False


def test_batch_pools_replays_and_excludes_foreign_legacy_and_other_revision():
    rows = [
        _row(1, fp=_fp(), correct=5, key="cfgA"),
        _row(2, fp=_fp(), correct=7, key="cfgA"),        # pooled with 1
        _row(3, fp=_fp(host="other"), key="cfgB"),       # cross-regime
        _row(4, key="cfgB"),                             # unfingerprinted legacy
        _row(5, fp=_fp(), rev=6, key="cfgB"),            # other incumbent
        _row(6, fp=_fp(), rev=None, key="cfgB"),         # no pin (pre EV-14e)
    ]
    batch = _gate(rows, _fp())["batch_homogeneity"]
    assert batch["members"]["cfgA"]["scored"] == 20
    assert batch["members"]["cfgA"]["trials"] == [1, 2]
    assert "cfgB" not in batch["members"]
    assert batch["cross_regime_excluded"] == 1
    assert batch["unfingerprinted_excluded"] == 1


def test_single_member_is_insufficient_and_missing_seed_holds():
    out = _gate([], _fp())
    assert out["batch_homogeneity"]["status"] == g.INSUFFICIENT
    assert out["hold_reasons"] == ["seed_rerun:MISSING"]


def test_candidate_without_fingerprint_is_unverified_and_holds():
    out = _gate([_row(1, fp=_fp(), seed=True)], {})
    assert out["seed_rerun"]["status"] == UNVERIFIED
    assert out["batch_homogeneity"]["status"] == UNVERIFIED
    assert out["hold"]


def test_declared_only_regime_passes_enforce_but_not_strict():
    fp = _fp("declared_only")
    rows = [_row(1, fp=fp, seed=True, correct=10, scored=50), _row(2, fp=fp, correct=10, scored=50)]
    enforce = _gate(rows, fp, counts=(40, 50))
    assert enforce["seed_rerun"]["status"] == UNVERIFIED
    assert enforce["batch_homogeneity"]["batch_regime"] == UNVERIFIED
    assert enforce["hold"] is False
    strict = _gate(rows, fp, counts=(40, 50), mode="strict")
    assert strict["hold"]
    assert "seed_rerun:UNVERIFIED" in strict["hold_reasons"]
    assert "batch_regime:UNVERIFIED" in strict["hold_reasons"]


def test_gate_error_fails_closed_only_when_binding():
    def boom(_row):
        raise RuntimeError("x")
    rows = [_row(1, fp=_fp())]
    kw = dict(tier=1, baseline_revision=7, candidate_key="c", candidate_counts=(1, 2),
              candidate_fingerprint=_fp(), counts_fn=boom, key_fn=lambda r: "k", alpha=0.05)
    assert g.promotion_gate(rows, mode="shadow", **kw)["hold"] is False
    assert g.promotion_gate(rows, mode="enforce", **kw)["hold_reasons"] == ["gate_error"]


def test_mode_and_alpha_env_parsing():
    assert g.gate_mode({}) == "shadow"
    assert g.gate_mode({"AUTOPILOT_AP55_PROMOTION_GATE": "ENFORCE"}) == "enforce"
    assert g.gate_mode({"AUTOPILOT_AP55_PROMOTION_GATE": "bogus"}) == "shadow"
    assert g.gate_alpha({"AUTOPILOT_AP55_HOMOGENEITY_ALPHA": "0.1"}) == 0.1
    assert g.gate_alpha({"AUTOPILOT_AP55_HOMOGENEITY_ALPHA": "2"}) == g.DEFAULT_ALPHA


def test_gate_summary_is_compact():
    summary = g.gate_summary(_gate([], _fp()))
    assert summary["seed_rerun"] == g.MISSING
    assert summary["batch_homogeneity"] == g.INSUFFICIENT
    assert summary["hold"] is True
    assert g.gate_summary({}) == {}


# ── autopilot wiring ─────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def autopilot():
    import autopilot as module  # noqa: E402

    return module


def _entry(tid, *, fp=None, seed=False, qr=None, pin_rev=None, snap=None,
           age_s=_FIXTURE_AGE_S):
    from experiment_journal import JournalEntry

    details = {"question_results": qr or [{"qid": f"q{i}", "correct": i % 2 == 0} for i in range(4)]}
    if seed:
        details["seq_baseline_reference_draw"] = True
    return JournalEntry(
        trial_id=tid, timestamp=_fixture_ts(age_s), species="s",
        action_type="seed_batch", tier=1, quality=1.0, speed=1.0, cost=1.0,
        reliability=1.0, pareto_status="candidate", eval_details=details,
        infra_fingerprint=fp or {},
        baseline_pin={"baseline_revision": pin_rev} if pin_rev is not None else {},
        config_snapshot=snap or {"type": "seed_batch", "n_questions": 4},
    )


class _Journal:
    def __init__(self, entries):
        self._entries = entries

    def entries_with_supersessions(self):
        return list(self._entries)


def test_reference_state_regime_due_on_change_with_churn_guard(autopilot, monkeypatch):
    monkeypatch.setattr(autopilot, "SEQ_BASELINE_REFRESH_CADENCE", 100)
    monkeypatch.setattr(autopilot, "AP55_REGIME_REFRESH_MIN_TRIALS", 2)
    old = _fp(orchestrator="old")
    journal = _Journal([_entry(1, fp=old, seed=True), _entry(2, fp=old)])
    state = autopilot._seq_baseline_reference_state(
        journal, tier=1, now_ts=0, current_fingerprint=_fp(), regime_forcing=True)
    assert state["regime_status"] == NON_COMPARABLE
    assert state["regime_due"] is False  # only one trial since the draw
    journal._entries.append(_entry(3, fp=_fp()))
    state = autopilot._seq_baseline_reference_state(
        journal, tier=1, now_ts=0, current_fingerprint=_fp(), regime_forcing=True)
    assert state["regime_due"] and state["due"]
    assert "orchestrator" in state["reason"]
    # same regime -> not due; no fingerprint passed -> legacy behaviour
    same = autopilot._seq_baseline_reference_state(
        _Journal([_entry(1, fp=_fp(), seed=True), _entry(2), _entry(3)]),
        tier=1, now_ts=0, current_fingerprint=_fp(), regime_forcing=True)
    assert same["regime_status"] == COMPARABLE and not same["due"]
    legacy = autopilot._seq_baseline_reference_state(journal, tier=1, now_ts=0)
    assert legacy["regime_status"] == "" and not legacy["regime_due"]
    # knob off: the regime is reported but never schedules a re-run
    off = autopilot._seq_baseline_reference_state(
        journal, tier=1, now_ts=0, current_fingerprint=_fp())
    assert off["regime_status"] == NON_COMPARABLE and not off["regime_due"] and not off["due"]


def test_reference_state_legacy_draw_triggers_one_refresh(autopilot, monkeypatch):
    monkeypatch.setattr(autopilot, "SEQ_BASELINE_REFRESH_CADENCE", 100)
    monkeypatch.setattr(autopilot, "AP55_REGIME_REFRESH_MIN_TRIALS", 1)
    journal = _Journal([_entry(1, seed=True), _entry(2)])
    state = autopilot._seq_baseline_reference_state(
        journal, tier=1, now_ts=0, current_fingerprint=_fp(), regime_forcing=True)
    assert state["regime_status"] == "UNFINGERPRINTED" and state["regime_due"]


def test_declared_only_regime_does_not_force_reruns(autopilot, monkeypatch):
    monkeypatch.setattr(autopilot, "SEQ_BASELINE_REFRESH_CADENCE", 100)
    monkeypatch.setattr(autopilot, "AP55_REGIME_REFRESH_MIN_TRIALS", 0)
    fp = _fp("declared_only")
    journal = _Journal([_entry(1, fp=fp, seed=True), _entry(2, fp=fp)])
    state = autopilot._seq_baseline_reference_state(
        journal, tier=1, now_ts=0, current_fingerprint=fp, regime_forcing=True)
    assert state["regime_status"] == UNVERIFIED and not state["regime_due"]


def test_force_draw_with_seq_off_only_on_regime_knob(autopilot, monkeypatch):
    monkeypatch.setattr(autopilot, "SEQ_BASELINE_REFRESH_CADENCE", 1)
    monkeypatch.setattr(autopilot, "AP55_REGIME_REFRESH_MIN_TRIALS", 0)
    monkeypatch.setattr(autopilot, "_infra_fingerprint_for_trial", lambda: _fp())
    kw = dict(state={}, blacklist=[], rationale={}, trial_counter=5, enabled=False)
    same = _Journal([_entry(1, fp=_fp(), seed=True), _entry(2, fp=_fp())])
    moved = _Journal([_entry(1, fp=_fp(recipe="old"), seed=True), _entry(2)])
    monkeypatch.delenv("AUTOPILOT_AP55_SEED_RERUN", raising=False)
    action = {"type": "numeric_trial"}
    assert autopilot._maybe_force_seq_baseline_draw(action, journal=moved, tier=1, **kw)[2] is None
    monkeypatch.setenv("AUTOPILOT_AP55_SEED_RERUN", "1")
    # cadence alone is seq-only
    assert autopilot._maybe_force_seq_baseline_draw(action, journal=same, tier=1, **kw)[2] is None
    forced, rationale, reference = autopilot._maybe_force_seq_baseline_draw(
        action, journal=moved, tier=1, **kw)
    assert reference is not None and reference["regime_due"]
    assert forced["type"] == "seed_batch" and rationale["seq_baseline_reference_draw"]


def test_paired_reference_skips_foreign_regime(autopilot):
    journal = _Journal([
        _entry(1, fp=_fp(), seed=True),
        _entry(2, fp=_fp(kernel="k2"), seed=True),
    ])
    ref = autopilot._latest_seq_baseline_reference_vector(journal, tier=1, candidate_fingerprint=_fp())
    assert ref["trial_id"] == 1 and ref["regime"] == COMPARABLE
    assert autopilot._latest_seq_baseline_reference_vector(journal, tier=1)["trial_id"] == 2
    payload = autopilot._seq_paired_baseline_diagnostics(
        journal=journal, tier=1, candidate="c", candidate_trial_id=3,
        question_results=[{"qid": "q0", "correct": True}], candidate_fingerprint=_fp())
    assert payload["baseline_reference_trial_id"] == 1
    assert payload["baseline_reference_regime"] == COMPARABLE
    assert payload["used_for_gating"] is False


def test_autopilot_gate_helper_reads_journal_rows(autopilot, monkeypatch):
    monkeypatch.setenv("AUTOPILOT_AP55_PROMOTION_GATE", "enforce")
    snap_a = {"type": "numeric_trial", "x": 1}
    all_right = [{"qid": f"q{i}", "correct": True} for i in range(20)]
    all_wrong = [{"qid": f"q{i}", "correct": False} for i in range(20)]
    journal = _Journal([
        _entry(1, fp=_fp(), seed=True, qr=all_wrong, pin_rev=3),
        _entry(2, fp=_fp(), qr=all_wrong, pin_rev=3, snap=snap_a),
    ])
    out = autopilot._ap55_promotion_gate_for_trial(
        journal, tier=1, baseline_pin={"baseline_revision": 3},
        candidate_action={"type": "numeric_trial", "x": 2},
        question_results=all_right, trial_fingerprint=_fp())
    assert out["mode"] == "enforce"
    assert out["seed_rerun"]["status"] == COMPARABLE
    batch = out["batch_homogeneity"]
    assert batch["status"] == g.HETEROGENEOUS
    assert set(batch["members"]) == {"seed", autopilot._config_fingerprint(snap_a),
                                     autopilot._config_fingerprint({"type": "numeric_trial", "x": 2})}
    assert out["hold"] is False


def test_autopilot_gate_helper_never_raises(autopilot, monkeypatch):
    monkeypatch.setenv("AUTOPILOT_AP55_PROMOTION_GATE", "enforce")
    out = autopilot._ap55_promotion_gate_for_trial(
        object(), tier=1, baseline_pin=None, candidate_action={}, question_results=None,
        trial_fingerprint=_fp())
    assert out["hold"] and out["hold_reasons"] == ["gate_error"]
    monkeypatch.setenv("AUTOPILOT_AP55_PROMOTION_GATE", "shadow")
    out = autopilot._ap55_promotion_gate_for_trial(
        object(), tier=1, baseline_pin=None, candidate_action={}, question_results=None,
        trial_fingerprint=_fp())
    assert out["hold"] is False


def test_measurement_tuple_carries_gate_legs_and_legacy_carries_none(tmp_path):
    from experiment_journal import ExperimentJournal, JournalEntry

    base = dict(timestamp="2026-09-16T00:00:00+00:00", species="s", action_type="t", tier=1,
                quality=1.0, speed=1.0, cost=1.0, reliability=1.0, pareto_status="candidate")
    gate = _gate([], _fp())
    journal = ExperimentJournal(journal_dir=tmp_path)
    journal.record(JournalEntry(trial_id=1, comparability={"status": UNVERIFIED,
                                                           "promotion_gate": gate}, **base))
    journal.record(JournalEntry(trial_id=2, comparability={"status": UNVERIFIED}, **base))
    rows = ExperimentJournal(journal_dir=tmp_path).all_entries()
    assert rows[0].measurement["ap55_gate"] == {
        "mode": "enforce", "seed_rerun": g.MISSING,
        "batch_homogeneity": g.INSUFFICIENT, "hold": True,
    }
    assert rows[0].comparability["promotion_gate"]["batch_homogeneity"]["status"] == g.INSUFFICIENT
    assert "ap55_gate" not in rows[1].measurement


def _force(autopilot, journal, state, trial, *, enabled):
    return autopilot._maybe_force_seq_baseline_draw(
        {"type": "numeric_trial"}, state=state, journal=journal, tier=1, blacklist=[],
        rationale={}, trial_counter=trial, enabled=enabled)


def test_seq_on_with_knob_unset_never_forces_a_regime_rerun(autopilot, monkeypatch):
    """Review fix 1: AUTOPILOT_SEQ_VERDICT=1 must not imply AP-55 forcing."""
    monkeypatch.setattr(autopilot, "SEQ_BASELINE_REFRESH_CADENCE", 100)
    monkeypatch.setattr(autopilot, "AP55_REGIME_REFRESH_MIN_TRIALS", 0)
    monkeypatch.delenv("AUTOPILOT_AP55_SEED_RERUN", raising=False)
    calls = []
    monkeypatch.setattr(autopilot, "_infra_fingerprint_for_trial", lambda: calls.append(1) or _fp())
    legacy_ref = _Journal([_entry(1, seed=True), _entry(2)])          # unfingerprinted draw
    moved = _Journal([_entry(1, fp=_fp(recipe="old"), seed=True), _entry(2)])
    for journal in (legacy_ref, moved):
        assert _force(autopilot, journal, {}, 5, enabled=True)[2] is None
    assert calls == []  # no fingerprinting at all with the knob unset
    monkeypatch.setenv("AUTOPILOT_AP55_SEED_RERUN", "1")
    assert _force(autopilot, moved, {}, 5, enabled=True)[2]["regime_due"]


def test_seq_on_still_refreshes_a_stale_reference(autopilot, monkeypatch):
    """The staleness leg the clock pin must not mask: age is fixture-relative, not calendar-relative."""
    monkeypatch.setattr(autopilot, "SEQ_BASELINE_REFRESH_CADENCE", 100)
    monkeypatch.delenv("AUTOPILOT_AP55_SEED_RERUN", raising=False)
    stale_age = autopilot.SEQ_BASELINE_REFERENCE_STALE_AFTER_S + 60
    journal = _Journal([_entry(1, fp=_fp(), seed=True, age_s=stale_age), _entry(2, fp=_fp())])
    forced, rationale, reference = _force(autopilot, journal, {}, 5, enabled=True)
    assert reference is not None and reference["stale_reference"] and not reference["regime_due"]
    assert reference["latest_reference_age_s"] == pytest.approx(stale_age)
    assert "stale threshold" in reference["reason"]
    assert forced["type"] == "seed_batch" and rationale["seq_baseline_reference_draw"]
    # seq off with the knob unset: staleness alone never forces a draw
    assert _force(autopilot, journal, {}, 5, enabled=False)[2] is None


def test_seq_off_bootstrap_forces_first_reference_draw(autopilot, monkeypatch):
    """Review fix 2: no reference draw at all must not leave enforce holding forever."""
    monkeypatch.setattr(autopilot, "SEQ_BASELINE_REFRESH_CADENCE", 100)
    monkeypatch.setattr(autopilot, "_infra_fingerprint_for_trial", lambda: _fp())
    monkeypatch.setenv("AUTOPILOT_AP55_SEED_RERUN", "1")
    journal = _Journal([_entry(1, fp=_fp()), _entry(2, fp=_fp())])  # no reference draw
    forced, rationale, reference = _force(autopilot, journal, {}, 3, enabled=False)
    assert reference["regime_status"] == "NO_REFERENCE" and reference["regime_due"]
    assert "bootstrap" in reference["reason"]
    assert forced["type"] == "seed_batch" and rationale["seq_baseline_reference_draw"]
    # without the knob the bootstrap is not scheduled with seq off
    monkeypatch.delenv("AUTOPILOT_AP55_SEED_RERUN")
    assert _force(autopilot, journal, {}, 3, enabled=False)[2] is None


def test_invalid_forced_reruns_are_spaced_and_capped(autopilot, monkeypatch, caplog):
    """Review fix 3: a re-run whose eval is invalid is neither a reference nor a trial."""
    monkeypatch.setattr(autopilot, "SEQ_BASELINE_REFRESH_CADENCE", 100)
    monkeypatch.setattr(autopilot, "AP55_REGIME_REFRESH_MIN_TRIALS", 3)
    monkeypatch.setattr(autopilot, "AP55_SEED_RERUN_MAX_ATTEMPTS", 3)
    monkeypatch.setattr(autopilot, "_infra_fingerprint_for_trial", lambda: _fp())
    monkeypatch.setenv("AUTOPILOT_AP55_SEED_RERUN", "1")
    old = _fp(recipe="old")
    entries = [_entry(1, fp=old, seed=True)] + [_entry(i, fp=_fp()) for i in (2, 3, 4)]
    journal = _Journal(entries)
    state: dict = {}
    key = autopilot.AP55_SEED_RERUN_ATTEMPTS_STATE_KEY
    fired = []
    for trial in range(5, 20):
        if _force(autopilot, journal, state, trial, enabled=False)[2] is not None:
            fired.append(trial)
            # the forced draw comes back invalid: journaled, but ignored by the state
            invalid = _entry(trial, fp=_fp(), seed=True)
            invalid.outcome_status = "invalid"
            journal._entries.append(invalid)
    assert fired == [5, 8, 11]
    assert state[key]["count"] == 3
    assert "AP-55 seed re-run NOT forced" in caplog.text
    # a landed reference draw (in the old regime again, so still due) resets the count
    journal._entries.append(_entry(30, fp=old, seed=True))
    journal._entries.extend(_entry(i, fp=_fp()) for i in (31, 32, 33))
    assert _force(autopilot, journal, state, 34, enabled=False)[2] is not None
    assert state[key]["count"] == 1 and "reference=30" in state[key]["key"]


def test_capped_attempts_fall_back_to_seq_cadence_when_seq_on(autopilot, monkeypatch):
    monkeypatch.setattr(autopilot, "SEQ_BASELINE_REFRESH_CADENCE", 2)
    monkeypatch.setattr(autopilot, "AP55_REGIME_REFRESH_MIN_TRIALS", 0)
    monkeypatch.setattr(autopilot, "AP55_SEED_RERUN_MAX_ATTEMPTS", 1)
    monkeypatch.setattr(autopilot, "_infra_fingerprint_for_trial", lambda: _fp())
    monkeypatch.setenv("AUTOPILOT_AP55_SEED_RERUN", "1")
    journal = _Journal([_entry(1, fp=_fp(recipe="old"), seed=True), _entry(2)])
    state = {autopilot.AP55_SEED_RERUN_ATTEMPTS_STATE_KEY: {
        "key": "tier=1:reference=1", "count": 1, "last_trial_id": 0}}
    # capped, and the seq cadence (1 trial < 2) is not due -> nothing forced
    assert _force(autopilot, journal, state, 9, enabled=True)[2] is None
    journal._entries.append(_entry(3))
    _, _, reference = _force(autopilot, journal, state, 9, enabled=True)
    assert reference is not None and not reference["regime_due"]
    assert state[autopilot.AP55_SEED_RERUN_ATTEMPTS_STATE_KEY]["count"] == 1
