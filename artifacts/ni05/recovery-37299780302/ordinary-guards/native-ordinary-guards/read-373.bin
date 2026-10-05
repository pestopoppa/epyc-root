"""Operator decisions (c) and (b), 2026-09-16, exercised end to end on a real journal.

(c) the trial's own row is handed to the promotion guard before the decision and clean rows
    are stamped as frontier representatives, so a candidate can be its cluster's
    representative;
(b) while the live frontier holds no config other than the candidate's and the tier has a
    baseline, promotion needs >= N (default 3) comparable live-regime reproductions.

Every test uses the REAL autopilot provider (``_install_promotion_guard_scope``), a real
``ExperimentJournal`` in a temp dir, and ``SafetyGate.update_baseline``. Zero inference.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
for _p in (ROOT, ROOT / "scripts" / "autopilot", ROOT / "scripts" / "analysis"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import autopilot  # noqa: E402
import safety_gate as sg  # noqa: E402
from experiment_journal import ExperimentJournal, JournalEntry  # noqa: E402
from safety_gate import EvalResult, SafetyGate  # noqa: E402

from src.autopilot_core.action_identity import (  # noqa: E402
    action_config_identity,
    row_config_identity,
)
from src.autopilot_core.journal_reconstruction import reconstruct_archive_from_journal_rows  # noqa: E402
from src.autopilot_core.journal_snapshot_replay import (  # noqa: E402
    _row_requires_prefix_raw_samples,
)
from src.autopilot_core.learning_exclusions import (  # noqa: E402
    FRONTIER_ADMISSION_KEY,
    FRONTIER_ADMISSION_REPRESENTATIVE,
    row_is_representative_member,
)
from src.autopilot_core.live_reproductions import live_reproductions  # noqa: E402
from src.autopilot_core.tier_specs import RATE_4D_OBJECTIVE_POLICY  # noqa: E402

FENCE = datetime(2026, 9, 17, tzinfo=timezone.utc)
FIXTURE = ROOT / "tests" / "fixtures" / "gate_frontier_replay.json"


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    monkeypatch.delenv(sg.EMPTY_FRONTIER_MIN_REPRO_ENV, raising=False)
    sg.configure_promotion_guard_archive(None)
    yield
    sg.configure_promotion_guard_archive(None)


class Loop:
    """The slice of the trial loop around the promotion decision, with real components."""

    def __init__(self, tmp_path, *, baseline=1.5):
        self.journal = ExperimentJournal(journal_dir=tmp_path / "journal")
        self.state = {
            "pareto_objective_policy": RATE_4D_OBJECTIVE_POLICY,
            "pareto_exclude_before_ts": FENCE.timestamp(),
            "pareto_epoch_ts": FENCE.timestamp(),
        }
        autopilot._install_promotion_guard_scope(self.journal, self.state)
        self.gate = SafetyGate(baseline_path=tmp_path / "absent.yaml")
        self.gate._baseline_eligible = lambda result: (True, "test-eligible", {})
        self.gate.baseline.baselines_by_tier = {} if baseline is None else {1: baseline}
        self.gate.baseline.per_suite_quality_by_tier = {}
        self.gate.baseline.frontdoor_speed = 10.0
        self.next_id = 100
        self.clock = FENCE + timedelta(minutes=5)

    def trial(
        self,
        config: str,
        quality: float,
        *,
        speed: float = 10.0,
        wall_s: float = 900.0,
        exclusion: str = "",
        comparability: str = "UNVERIFIED",
        record: bool = True,
        promote: bool = True,
        action: dict | None = None,
        infra_digest: str = "",
        served: dict | None = None,
    ):
        tid = self.next_id
        self.next_id += 1
        self.clock += timedelta(minutes=10)
        action = action or {"type": "numeric_trial", "surface": "s", "params": {"cfg": config}}
        result = EvalResult(
            tier=1,
            quality=quality,
            speed=speed,
            cost=0.2,
            reliability=0.98,
            per_suite_quality={"coder": quality},
            n_questions=50,
            eval_wall_s=wall_s,
            question_results=[{"qid": f"q{i}", "correct": True} for i in range(50)],
        )
        clean = (
            not exclusion
            and action_config_identity(action, infra_digest, served) is not None
        )
        admission = FRONTIER_ADMISSION_REPRESENTATIVE if clean else ""
        comp = {"status": comparability}
        ts = self.clock.isoformat()
        provisional = autopilot._provisional_trial_row(
            trial_id=tid,
            timestamp=ts,
            eval_result=result,
            action=action,
            learning_excluded_by=exclusion,
            learning_excluded_reason="r" if exclusion else "",
            frontier_admission=admission,
            comparability=comp,
            regime_digest=infra_digest,
            served_content=served,
        )
        self.last_provisional = provisional
        update = None
        if promote:
            update = self.gate.update_baseline(
                result, source_trial_id=tid, pending_journal_rows=(provisional,)
            )
        entry = None
        if record:
            details = dict(provisional["eval_details"])
            details["per_suite_quality"] = result.per_suite_quality
            if update is not None:
                details["promotion_rule"] = update.promotion_rule
            entry = JournalEntry(
                trial_id=tid,
                timestamp=ts,
                species="numeric_swarm",
                action_type="numeric_trial",
                tier=1,
                quality=quality,
                speed=speed,
                cost=0.2,
                reliability=0.98,
                pareto_status="frontier",
                config_snapshot=action,
                reasoning=json.dumps(action),
                eval_details=details,
                comparability=comp,
            )
            self.journal.record(entry)
            assert autopilot._provisional_row_mismatch(provisional, asdict(entry)) == []
        return tid, update


# ── (c) ───────────────────────────────────────────────────────────────────


def test_clean_candidate_is_its_own_cluster_representative(tmp_path):
    loop = Loop(tmp_path, baseline=None)
    tid, update = loop.trial("A", 1.8)
    assert update.updated and update.promotion_rule == sg.PROMOTION_RULE_SEED
    assert sg._GUARD_CONTEXT is None  # the pending-row context is per call, never leaks
    # A second, clean run of the same config clusters with the first (not a new raw point).
    tid2, update2 = loop.trial("A", 1.8)
    rows = autopilot._journal_rows_for_archive(loop.journal)
    payload = reconstruct_archive_from_journal_rows(
        rows, None, objective_policy=RATE_4D_OBJECTIVE_POLICY,
        exclude_before_ts=FENCE.timestamp(),
    )
    reps = [e for e in payload["all_entries"] if e.get("eval_tier") == 1]
    assert len(reps) == 1 and reps[0]["n_reproductions"] == 2 and reps[0]["trial_id"] == tid2


def test_frontier_rule_promotes_on_third_clean_reproduction(tmp_path):
    loop = Loop(tmp_path)
    loop.trial("B", 1.6, wall_s=300.0, promote=False)  # another config on the frontier
    updates = [loop.trial("A", 1.8)[1] for _ in range(3)]
    assert [u.promotion_rule for u in updates] == [sg.PROMOTION_RULE_FRONTIER] * 3
    assert [u.updated for u in updates] == [False, False, True], [u.reason for u in updates]
    assert "source has 1" in updates[0].reason
    assert loop.gate.baseline.baselines_by_tier[1] == pytest.approx(1.8)


def test_stored_journal_never_marks_old_rows():
    data = json.loads(FIXTURE.read_text())
    assert not any(
        (row.get("eval_details") or {}).get(FRONTIER_ADMISSION_KEY) for row in data["rows"]
    )


def test_representative_predicate_shared_by_replay_and_snapshot():
    clean = {"eval_details": {FRONTIER_ADMISSION_KEY: FRONTIER_ADMISSION_REPRESENTATIVE}}
    assert row_is_representative_member(clean) and _row_requires_prefix_raw_samples(clean)
    corrupted = {"bug_corrupted_by": "x", "eval_details": dict(clean["eval_details"])}
    assert not row_is_representative_member(corrupted)
    refuted = {
        "eval_details": {
            FRONTIER_ADMISSION_KEY: FRONTIER_ADMISSION_REPRESENTATIVE,
            "learning_exclusion": {"by": "seq_refuted"},
        }
    }
    assert not row_is_representative_member(refuted)
    noise = {"eval_details": {"learning_exclusion": {"by": "mad_noise"}}}
    assert row_is_representative_member(noise)
    assert not row_is_representative_member({"eval_details": {}})


def test_within_noise_reproduction_reaches_update_baseline_without_multitier():
    source = Path(autopilot.__file__).read_text()
    block = source[source.index("if not MULTITIER_PROMOTION_ENABLED and rate_measured and bool(verdict):"):]
    block = block[: block.index("criticism = learning_exclusion_criticism")]
    assert "pending_journal_rows=(provisional_row,)" in block


def test_every_update_baseline_call_in_the_loop_passes_the_pending_row():
    source = Path(autopilot.__file__).read_text()
    body = source[source.index("def _run_loop_inner(") :]
    calls = body.split("gate.update_baseline(\n")[1:]
    assert len(calls) == 3
    for call in calls:
        assert "pending_journal_rows=(provisional_row,)" in call[: call.index(")\n")]


# ── (b) ───────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("n_repro, promoted", [(1, False), (2, False), (3, True)])
def test_empty_frontier_rule_needs_three_reproductions(tmp_path, n_repro, promoted):
    loop = Loop(tmp_path)
    updates = [loop.trial("A", 1.8)[1] for _ in range(n_repro)]
    assert all(u.promotion_rule == sg.PROMOTION_RULE_EMPTY_FRONTIER_REPRO for u in updates)
    assert updates[-1].updated is promoted, updates[-1].reason
    if not promoted:
        assert f"has {n_repro} of 3 required" in updates[-1].reason
        assert loop.gate.baseline.baselines_by_tier[1] == 1.5
    else:
        assert loop.gate.baseline.baselines_by_tier[1] == pytest.approx(1.8)


def test_non_comparable_reproduction_is_not_counted(tmp_path):
    loop = Loop(tmp_path)
    loop.trial("A", 1.8, comparability="COMPARABLE")
    loop.trial("A", 1.8, comparability="NON_COMPARABLE")
    _, third = loop.trial("A", 1.8, comparability="UNVERIFIED")
    assert not third.updated
    assert "has 2 of 3 required" in third.reason
    _, fourth = loop.trial("A", 1.8, comparability="COMPARABLE")
    assert fourth.updated, fourth.reason


def test_within_noise_rows_count_as_reproductions(tmp_path):
    loop = Loop(tmp_path)
    loop.trial("A", 1.8)
    loop.trial("A", 1.8, exclusion="reproduction_confirmed")
    _, third = loop.trial("A", 1.8, exclusion="mad_noise")
    assert third.updated, third.reason
    assert third.promotion_rule == sg.PROMOTION_RULE_EMPTY_FRONTIER_REPRO


def test_median_must_clear_the_quantum(tmp_path):
    loop = Loop(tmp_path)
    loop.trial("A", 1.52)
    loop.trial("A", 1.52)
    _, third = loop.trial("A", 1.52)
    assert not third.updated
    assert "does not clear baseline" in third.reason


def test_rule_switches_to_frontier_once_another_config_is_on_the_frontier(tmp_path):
    loop = Loop(tmp_path)
    _, first = loop.trial("A", 1.8)
    assert first.promotion_rule == sg.PROMOTION_RULE_EMPTY_FRONTIER_REPRO
    loop.trial("B", 1.7, speed=30.0, wall_s=300.0, promote=False)  # non-dominated elsewhere
    _, second = loop.trial("A", 1.8)
    assert second.promotion_rule == sg.PROMOTION_RULE_FRONTIER
    # Frontier rule: n_reproductions counts the whole cluster, independent of AP-55.
    assert "needs >= 3 reproductions; source has 2" in second.reason


def test_min_repro_env(monkeypatch, tmp_path):
    monkeypatch.setenv(sg.EMPTY_FRONTIER_MIN_REPRO_ENV, "2")
    assert sg.empty_frontier_min_repro() == 2
    loop = Loop(tmp_path)
    loop.trial("A", 1.8)
    _, second = loop.trial("A", 1.8)
    assert second.updated, second.reason
    for bad in ("1", "0", "-4", "x"):
        monkeypatch.setenv(sg.EMPTY_FRONTIER_MIN_REPRO_ENV, bad)
        assert sg.empty_frontier_min_repro() == 3


def test_seed_rule_when_tier_has_no_baseline(tmp_path):
    loop = Loop(tmp_path, baseline=None)
    _, update = loop.trial("A", 1.8)
    assert update.updated and update.promotion_rule == sg.PROMOTION_RULE_SEED


def test_empty_frontier_without_candidate_row_refuses(tmp_path):
    loop = Loop(tmp_path)
    result = EvalResult(tier=1, quality=1.9, speed=10.0, cost=0.2, reliability=0.98,
                        per_suite_quality={"coder": 1.9}, n_questions=50)
    update = loop.gate.update_baseline(result, source_trial_id=5)
    assert not update.updated
    assert "journal row was not supplied" in update.reason


# ── no permanent freeze ───────────────────────────────────────────────────


def test_no_path_freezes_promotions_permanently(tmp_path):
    """Epoch starts empty; a better config promotes; a later, better config promotes too."""
    loop = Loop(tmp_path)
    outcomes = [loop.trial("A", 1.8)[1] for _ in range(3)]
    assert outcomes[-1].updated
    # Later configs, with the frontier populated: a better config still promotes after 3 runs.
    loop.trial("C", 1.7, wall_s=300.0, promote=False)  # stays on the frontier (faster)
    later = [loop.trial("D", 2.1)[1] for _ in range(3)]
    assert [u.updated for u in later] == [False, False, True], [u.reason for u in later]
    assert later[-1].promotion_rule == sg.PROMOTION_RULE_FRONTIER
    assert loop.gate.baseline.baselines_by_tier[1] == pytest.approx(2.1)


def test_forward_simulation_golden_fills_the_frontier():
    fwd = json.loads(FIXTURE.read_text())["golden"]["forward_simulation"]
    rules = [d["promotion_rule"] for d in fwd["decisions"]]
    assert rules[0] == sg.PROMOTION_RULE_EMPTY_FRONTIER_REPRO
    assert set(rules[1:]) == {sg.PROMOTION_RULE_FRONTIER}
    sizes = [d["frontier_size_after"] for d in fwd["decisions"]]
    assert sizes == sorted(sizes) and sizes[-1] >= 1
    assert int(fwd["final_frontier_sizes"]["1"]) >= 1


# ── fail-closed guard (review finding 3) ──────────────────────────────────


def test_provider_exception_refuses_promotion_over_a_baseline(tmp_path):
    loop = Loop(tmp_path)
    # The reviewer's reproduction: an active speed era with no epoch params makes the live
    # provider raise inside _archive_epoch_params_from_state.
    loop.state.pop("pareto_exclude_before_ts")
    loop.state["active_instrument_eras"] = {"autopilot_speed": "E99"}
    _, update = loop.trial("A", 1.9, record=False)
    assert not update.updated
    assert update.promotion_rule == "refused_guard_unavailable"
    assert "fail-closed" in update.reason
    assert loop.gate.baseline.baselines_by_tier[1] == 1.5


def test_provider_exception_still_allows_a_seed(tmp_path):
    loop = Loop(tmp_path, baseline=None)

    def broken(pending_rows=()):
        raise RuntimeError("journal unreadable")

    sg.configure_promotion_guard_archive(broken)
    _, update = loop.trial("A", 1.9, record=False)
    assert update.updated and update.promotion_rule == sg.PROMOTION_RULE_SEED


# ── per-call cache (review finding 4) ─────────────────────────────────────


def test_provider_builds_once_per_promotion_decision(tmp_path, monkeypatch):
    loop = Loop(tmp_path)
    loop.trial("B", 1.6, promote=False)
    calls = []
    real = autopilot._journal_archive_payload_for_authority

    def counting(*args, **kwargs):
        calls.append(1)
        return real(*args, **kwargs)

    monkeypatch.setattr(autopilot, "_journal_archive_payload_for_authority", counting)
    for _ in range(3):
        loop.trial("A", 1.9)
    assert len(calls) == 3  # one rebuild per update_baseline call, not four


# ── crash between the decision and journal.record ─────────────────────────


def test_crash_before_record_leaves_no_persisted_promotion(tmp_path):
    loop = Loop(tmp_path)
    loop.trial("A", 1.8)
    loop.trial("A", 1.8)
    persisted = loop.gate.baseline.to_state_dict()
    tid, update = loop.trial("A", 1.8, record=False)  # decided, then the process dies
    assert update.updated  # in memory only
    # Restart: state on disk was saved before this trial; the WAL writes a placeholder.
    restarted = SafetyGate(baseline_path=tmp_path / "absent.yaml", baseline_state=persisted)
    assert restarted.baseline.baselines_by_tier[1] == pytest.approx(1.5)
    state = {"in_flight_trial": {"trial_id": tid, "action": {"type": "numeric_trial"}}}
    archive = sg_archive()
    autopilot._recover_from_in_flight_trial(state, loop.journal, archive, tid)
    rows = autopilot._journal_rows_for_archive(loop.journal)
    placeholder = [r for r in rows if r["trial_id"] == tid][0]
    assert placeholder["bug_corrupted_by"] == "autopilot_killed_mid_trial"
    assert not row_is_representative_member(placeholder)
    reps = live_reproductions(
        rows, tier=1, identity=action_config_identity(
            {"type": "numeric_trial", "surface": "s", "params": {"cfg": "A"}}
        ),
        objective_policy=RATE_4D_OBJECTIVE_POLICY, exclude_before_ts=FENCE.timestamp(),
    )
    assert [r["trial_id"] for r in reps] == [100, 101]


def sg_archive():
    from pareto_archive import ParetoArchive

    return ParetoArchive.from_archive_payload({}, read_only=False)


def test_loop_persists_nothing_between_decision_and_record():
    source = Path(autopilot.__file__).read_text()
    body = source[source.index("def _run_loop_inner(") :]
    first_decision = body.index("gate.update_baseline(")
    record = body.index("journal.record(journal_entry)")
    between = body[first_decision:record]
    for forbidden in ("save_state(", "_save_state_with_journal_archive_authority(",
                      "append_baseline_promotion_event", "_append_baseline_promotion_event("):
        assert forbidden not in between, forbidden
    assert body.index("_append_baseline_promotion_event(", record) > record


def test_recovered_representative_is_not_raw_reimported(tmp_path):
    loop = Loop(tmp_path)
    tid, _ = loop.trial("A", 1.8, promote=False)
    archive = sg_archive()
    assert autopilot._maybe_reimport_pareto_from_journal(archive, loop.journal, tid) is False


# ── snapshot tail fold stays correct with stamped rows ────────────────────


def test_snapshot_authority_matches_full_replay_with_stamped_rows(tmp_path):
    loop = Loop(tmp_path)
    for cfg, q in (("A", 1.8), ("A", 1.8), ("B", 1.6), ("A", 1.9)):
        loop.trial(cfg, q, promote=False)
    rows = autopilot._journal_rows_for_archive(loop.journal)
    full = reconstruct_archive_from_journal_rows(
        rows, None, objective_policy=RATE_4D_OBJECTIVE_POLICY,
        exclude_before_ts=FENCE.timestamp(),
    )
    via_authority = autopilot._journal_archive_payload_for_authority(
        loop.journal, objective_policy=RATE_4D_OBJECTIVE_POLICY,
        exclude_before_ts=FENCE.timestamp(),
    )
    key = lambda p: sorted((e["trial_id"], e.get("n_reproductions", 1)) for e in p["all_entries"])  # noqa: E731
    assert key(full) == key(via_authority)


# ── re-review B1: measurement actions are never reproduction evidence ─────


SEED = {"type": "seed_batch", "n_questions": 10}


@pytest.mark.parametrize("action", [
    {"type": "seed_batch", "n_questions": 10},
    {"type": "deep_eval", "tier": 1},
    {"type": "prompt_mutation", "file": "frontdoor.md", "mutation": "targeted_fix"},
    {"type": "numeric_trial", "surface": "s", "params": {}},
    {"type": "structural_experiment", "flags": {}},
])
def test_non_identifying_actions_have_no_served_config_identity(action):
    assert action_config_identity(action) is None


def test_identity_includes_the_infra_digest():
    action = {"type": "structural_experiment", "flags": {"x": True}}
    assert action_config_identity(action, "d1") != action_config_identity(action, "d2")
    assert action_config_identity(action, "d1") == action_config_identity(action, "d1")


def test_three_seed_batches_do_not_promote_under_rule_b(tmp_path):
    """The re-review's reproduction: seeder runs after a config change must not promote."""
    loop = Loop(tmp_path)
    updates = [loop.trial("seed", 1.9, action=dict(SEED))[1] for _ in range(4)]
    assert not any(u.updated for u in updates), [u.reason for u in updates]
    assert all("no served-config identity" in u.reason for u in updates)
    assert loop.gate.baseline.baselines_by_tier[1] == 1.5
    rows = autopilot._journal_rows_for_archive(loop.journal)
    assert not any(row_is_representative_member(r) for r in rows)  # never stamped


def test_seed_batch_within_noise_cluster_cannot_promote_under_frontier_rule(tmp_path):
    loop = Loop(tmp_path)
    loop.trial("B", 1.6, wall_s=300.0, promote=False)
    for _ in range(3):
        loop.trial("seed", 1.9, action=dict(SEED), exclusion="mad_noise", promote=False)
    _, update = loop.trial("seed", 1.9, action=dict(SEED), exclusion="reproduction_confirmed")
    assert update.promotion_rule == sg.PROMOTION_RULE_FRONTIER
    assert not update.updated and "no served-config identity" in update.reason


def test_reproductions_on_a_different_infra_regime_do_not_count(tmp_path):
    loop = Loop(tmp_path)
    loop.trial("A", 1.8, infra_digest="d1")
    loop.trial("A", 1.8, infra_digest="d2")
    _, third = loop.trial("A", 1.8, infra_digest="d1")
    assert not third.updated and "has 2 of 3 required" in third.reason


def test_seed_still_allowed_for_a_tier_without_baseline(tmp_path):
    loop = Loop(tmp_path, baseline=None)
    _, update = loop.trial("seed", 1.9, action=dict(SEED))
    assert update.updated and update.promotion_rule == sg.PROMOTION_RULE_SEED


def test_what_if_replay_promotions_all_carry_a_served_config_identity():
    data = json.loads(FIXTURE.read_text())
    rows = {r["trial_id"]: r for r in data["rows"]}
    promoted = [
        d for d in data["golden"]["decisions"]["live_c"]
        if d["decision"] == "promoted" and d["promotion_rule"] != "seed"
    ]
    for d in promoted:
        assert row_config_identity(rows[d["trial_id"]]) is not None, d


# ── re-review B2: a journal mismatch rolls the promotion back ─────────────


def test_mismatch_restores_baseline_and_suppresses_the_promotion(tmp_path):
    import copy

    loop = Loop(tmp_path)
    for _ in range(2):
        loop.trial("A", 1.8)
    before = copy.deepcopy(loop.gate.baseline)
    tid, update = loop.trial("A", 1.8, record=False)
    assert update.updated and loop.gate.baseline.baselines_by_tier[1] == pytest.approx(1.8)
    recorded = dict(loop.last_provisional)
    recorded["quality"] = 0.4  # the journal holds different evidence than the decision saw
    result = autopilot._reconcile_promotion_with_journal(
        loop.gate, update, before, loop.last_provisional, recorded, tid
    )
    assert result.updated is False and "rolled back" in result.reason
    assert loop.gate.baseline.baselines_by_tier[1] == 1.5
    assert autopilot._append_baseline_promotion_event(
        journal=loop.journal, baseline_update=result, eval_result=None,
        source_trial_id=tid, pareto_status="frontier", baseline_state={},
    ) is None


def test_matching_row_keeps_the_promotion(tmp_path):
    import copy

    loop = Loop(tmp_path)
    for _ in range(2):
        loop.trial("A", 1.8)
    before = copy.deepcopy(loop.gate.baseline)
    tid, update = loop.trial("A", 1.8, record=False)
    result = autopilot._reconcile_promotion_with_journal(
        loop.gate, update, before, loop.last_provisional, dict(loop.last_provisional), tid
    )
    assert result is update and loop.gate.baseline.baselines_by_tier[1] == pytest.approx(1.8)


def test_loop_reconciles_before_any_persistence():
    source = Path(autopilot.__file__).read_text()
    body = source[source.index("def _run_loop_inner(") :]
    record = body.index("journal.record(journal_entry)")
    reconcile = body.index("_reconcile_promotion_with_journal(", record)
    event = body.index("_append_baseline_promotion_event(", record)
    state_write = body.index('state["baseline_state"] = baseline_state', record)
    assert record < reconcile < min(event, state_write)
    assert body.index("baseline_before_decision = copy.deepcopy(gate.baseline)") < body.index(
        "gate.update_baseline(\n"
    )


# ── re-review B3: the row records a pending commit, confirmed by the ledger ─


def test_row_stamps_pending_commit_and_ledger_is_the_commit_record():
    source = Path(autopilot.__file__).read_text()
    assert '"pending_commit" if getattr(baseline_update, "updated", False) else "refused"' in source
    body = source[source.index("def _run_loop_inner(") :]
    assert body.index('eval_details_dict["promotion_status"]') < body.index(
        "journal.record(journal_entry)"
    ) < body.index("_append_baseline_promotion_event(")


# ── operator decision 2026-09-16: mutated-file sha is the content identity ─


def _sha(text: str) -> str:
    import hashlib

    return hashlib.sha256(text.encode()).hexdigest()


PROMPT = {"type": "prompt_mutation", "file": "frontdoor.md", "mutation": "targeted_fix"}


def _served(text: str, path: str = "orchestration/prompts/frontdoor.md") -> dict:
    return {"files": {path: _sha(text)}}


def test_identical_served_content_counts_as_a_reproduction(tmp_path):
    loop = Loop(tmp_path)
    updates = [
        loop.trial("p", 1.8, action=dict(PROMPT), served=_served("v2"), infra_digest="r1")[1]
        for _ in range(3)
    ]
    assert [u.updated for u in updates] == [False, False, True], [u.reason for u in updates]
    assert updates[-1].promotion_rule == sg.PROMOTION_RULE_EMPTY_FRONTIER_REPRO


def test_different_served_content_does_not_count(tmp_path):
    loop = Loop(tmp_path)
    loop.trial("p", 1.8, action=dict(PROMPT), served=_served("v2"), infra_digest="r1")
    loop.trial("p", 1.8, action=dict(PROMPT), served=_served("v3"), infra_digest="r1")
    _, third = loop.trial("p", 1.8, action=dict(PROMPT), served=_served("v2"), infra_digest="r1")
    assert not third.updated and "has 2 of 3 required" in third.reason


def test_mutation_row_without_sha_does_not_count(tmp_path):
    loop = Loop(tmp_path)
    loop.trial("p", 1.8, action=dict(PROMPT), served=None, infra_digest="r1")
    loop.trial("p", 1.8, action=dict(PROMPT), served=_served("v2"), infra_digest="r1")
    _, third = loop.trial("p", 1.8, action=dict(PROMPT), served=_served("v2"), infra_digest="r1")
    # The sha-less row is not a cluster member: whichever rule applies, only 2 count.
    assert not third.updated
    assert "has 2 of 3 required" in third.reason or "source has 2" in third.reason
    _, no_sha = loop.trial("p", 1.9, action=dict(PROMPT), served=None, infra_digest="r1")
    assert not no_sha.updated and "no served-config identity" in no_sha.reason


def test_multi_file_identity_is_the_sorted_path_sha_set():
    a = {"files": {"b.py": _sha("2"), "a.py": _sha("1")}}
    b = {"files": {"a.py": _sha("1"), "b.py": _sha("2")}}
    c = {"files": {"a.py": _sha("1"), "b.py": _sha("3")}}
    code = {"type": "code_mutation", "file": "a.py", "mutation": "targeted_fix"}
    assert action_config_identity(code, "", a) == action_config_identity(code, "", b)
    assert action_config_identity(code, "", a) != action_config_identity(code, "", c)
    # The same content under a different path is a different served config.
    moved = {"files": {"c.py": _sha("1"), "b.py": _sha("2")}}
    assert action_config_identity(code, "", a) != action_config_identity(code, "", moved)


@pytest.mark.parametrize("bad", [
    None, {}, {"files": {}}, {"files": {"a.py": "nothex"}}, "0" * 64, {"files": "x"},
])
def test_malformed_served_content_has_no_identity(bad):
    assert action_config_identity(dict(PROMPT), "", bad) is None


def test_served_content_never_changes_action_fingerprints():
    """Old rows keep their archive keys and repeat-detection signatures."""
    from src.autopilot_core.action_identity import (
        action_signature,
        config_fingerprint,
        config_fingerprint_from_row,
    )

    row_old = {"config_snapshot": dict(PROMPT), "eval_details": {}}
    row_new = {
        "config_snapshot": dict(PROMPT),
        "eval_details": {"served_content": _served("v2"), "infra_regime_digest": "r1"},
    }
    assert config_fingerprint_from_row(row_old) == config_fingerprint_from_row(row_new)
    assert config_fingerprint_from_row(row_old) == config_fingerprint(PROMPT)
    assert action_signature(PROMPT) == action_signature(dict(PROMPT))
    assert row_config_identity(row_old) is None
    assert row_config_identity(row_new) is not None


def _fingerprint(**overrides):
    base = {
        "orchestrator": "o1", "evaluator": "e1", "kernel": "k1",
        "recipe": "r1", "models": "m1", "host": "h1",
    }
    base.update(overrides)
    return {"component_digests": base, "digest": "|".join(sorted(base.values()))}


def test_regime_ignores_orchestrator_commits_but_not_kernel_or_models():
    from src.autopilot_core.infra_fingerprint import regime_digest

    same = regime_digest(_fingerprint())
    assert regime_digest(_fingerprint(orchestrator="o2")) == same
    assert regime_digest(_fingerprint(kernel="k2")) != same
    assert regime_digest(_fingerprint(models="m2")) != same
    assert regime_digest(_fingerprint(recipe="r2")) != same
    assert regime_digest(_fingerprint(host="h2")) != same
    assert regime_digest(_fingerprint(evaluator="e2")) != same
    assert regime_digest(None) == "" and regime_digest({"status": "capture_error"}) == ""


def test_reproduction_survives_an_unrelated_orchestrator_commit(tmp_path):
    from src.autopilot_core.infra_fingerprint import regime_digest

    loop = Loop(tmp_path)
    digests = [
        regime_digest(_fingerprint(orchestrator=f"commit{i}")) for i in range(3)
    ]
    updates = [
        loop.trial("A", 1.8, infra_digest=d)[1] for d in digests
    ]
    assert updates[-1].updated, updates[-1].reason


def test_kernel_change_splits_the_cluster(tmp_path):
    from src.autopilot_core.infra_fingerprint import regime_digest

    loop = Loop(tmp_path)
    loop.trial("A", 1.8, infra_digest=regime_digest(_fingerprint()))
    loop.trial("A", 1.8, infra_digest=regime_digest(_fingerprint(kernel="k2")))
    _, third = loop.trial("A", 1.8, infra_digest=regime_digest(_fingerprint()))
    assert not third.updated and "has 2 of 3 required" in third.reason


def test_row_regime_digest_falls_back_to_the_recorded_fingerprint():
    from src.autopilot_core.action_identity import row_regime_digest
    from src.autopilot_core.infra_fingerprint import regime_digest

    fp = _fingerprint()
    assert row_regime_digest({"infra_fingerprint": fp, "eval_details": {}}) == regime_digest(fp)
    assert row_regime_digest({"eval_details": {"infra_regime_digest": "x"}}) == "x"
    assert row_regime_digest({"eval_details": {}}) == ""


# ── the sha is taken from the served file at eval time, never from the action ──


def test_served_content_record_hashes_the_file_on_disk(tmp_path):
    import actions

    target = tmp_path / "orchestration" / "prompts" / "frontdoor.md"
    target.parent.mkdir(parents=True)
    target.write_text("served v2")
    record = actions.served_content_record([target], root=tmp_path)
    assert record == {"files": {"orchestration/prompts/frontdoor.md": _sha("served v2")}}
    assert actions.served_content_record([tmp_path / "missing"], root=tmp_path) is None


def test_handlers_hash_after_apply_and_before_eval_without_touching_the_action():
    import actions

    source = Path(actions.__file__).read_text()
    for handler, apply_call in (
        ("def _action_prompt_mutation(", "ctx.forge.apply_mutation(mutation)"),
        ("def _action_gepa_optimize(", "ctx.forge.apply_mutation(mutation)"),
        ("def _action_code_mutation(", "ctx.forge.apply_code_mutation(mutation)"),
    ):
        body = source[source.index(handler):]
        body = body[: body.index("\ndef ", 1)]
        applied = body.index(apply_call)
        recorded = body.index("_record_served_content(", applied)
        evaluated = body.index("ctx.tower.hybrid_eval()", applied)
        assert applied < recorded < evaluated, handler
        assert 'action["served_content"]' not in body


def test_loop_clears_and_pops_the_served_content_around_dispatch():
    source = Path(autopilot.__file__).read_text()
    body = source[source.index("def _run_loop_inner(") :]
    clear = body.index("state.pop(SERVED_CONTENT_STATE_KEY, None)")
    dispatch = body.index("eval_result, species_name = dispatch_action(")
    take = body.index("trial_served_content = state.pop(SERVED_CONTENT_STATE_KEY, None)")
    assert clear < dispatch < take


def test_record_served_content_on_state(tmp_path):
    import actions

    target = tmp_path / "f.md"
    target.write_text("x")

    class Ctx:
        state: dict = {}

    ctx = Ctx()
    ctx.state = {}
    actions._record_served_content(ctx, [target])
    record = ctx.state[actions.SERVED_CONTENT_STATE_KEY]
    assert list(record["files"].values()) == [_sha("x")] and record["captured_at"]
    actions._record_served_content(ctx, [tmp_path / "gone"])
    assert actions.SERVED_CONTENT_STATE_KEY not in ctx.state
    assert autopilot._served_content_for_row(record)["files"] == record["files"]
    assert autopilot._served_content_for_row({"files": {"a": "bad"}}) is None
