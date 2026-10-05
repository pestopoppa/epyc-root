"""Gate-frontier (2026-09-16): the promotion guard reads the LIVE frontier, and units stay apart.

Paired change (W3e follow-up, operator decision 2026-09-16):
  1. the promotion guard rebuilds its frontier under the live objective policy + epoch fence;
  2. the reproduced-promotion override routes the rate axis by UNIT — questions/hour goes to
     ``frontdoor_task_rate_qph``, never to ``speed`` / ``frontdoor_speed``;
  3. the throughput floor keeps comparing tokens/second against a tokens/second baseline.

The replay half runs ``scripts/analysis/gate_frontier_replay.py`` over the slimmed stored
journal (``tests/fixtures/gate_frontier_replay.json``) and pins the old-vs-new decisions.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
for _p in (ROOT, ROOT / "scripts" / "autopilot", ROOT / "scripts" / "analysis"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import safety_gate as sg  # noqa: E402  (the module object the autopilot imports)
from safety_gate import Baseline, EvalResult, PromotionGuardView, SafetyGate  # noqa: E402

import scripts.autopilot.host_health as hh  # noqa: E402
from src.autopilot_core.tier_specs import (  # noqa: E402
    LEGACY_OBJECTIVE_POLICY,
    PRE_RESOURCE_LANES_RATE_4D_OBJECTIVE_POLICY,
    RATE_4D_OBJECTIVE_POLICY,
    RATE_AXIS_UNIT_QUESTIONS_PER_HOUR,
    RATE_AXIS_UNIT_TOKENS_PER_SECOND,
    RESOURCE_LANES_V2_RATE_4D_OBJECTIVE_POLICY,
    TASK_RATE_OBJECTIVE_POLICY,
    rate_axis_unit,
)

FIXTURE = ROOT / "tests" / "fixtures" / "gate_frontier_replay.json"
RATE_POLICIES = (
    PRE_RESOURCE_LANES_RATE_4D_OBJECTIVE_POLICY,
    RESOURCE_LANES_V2_RATE_4D_OBJECTIVE_POLICY,
    RATE_4D_OBJECTIVE_POLICY,
)
# Trial 1472 from the handoff: live q/h vs legacy t/s for the same trial.
LIVE_OBJECTIVES = (2.025, 59.49, -0.5, 0.8)
TRIAL_TPS = 14.78


@pytest.fixture(autouse=True)
def _reset_provider():
    sg.configure_promotion_guard_archive(None)
    yield
    sg.configure_promotion_guard_archive(None)


class _Entry:
    def __init__(self, trial_id, objectives, n_reproductions=3):
        self.trial_id = trial_id
        self.objectives = tuple(objectives)
        self.n_reproductions = n_reproductions
        self.config_fingerprint = "fp"


class _Archive:
    def __init__(self, entries):
        self._entries = list(entries)

    def frontier(self, tier=None):
        return list(self._entries)


def _install(entries, policy=RATE_4D_OBJECTIVE_POLICY, scope="live"):
    view = PromotionGuardView(archive=_Archive(entries), objective_policy=policy, scope=scope)
    sg.configure_promotion_guard_archive(lambda pending_rows=(): view)


def _result(quality=2.1, speed=TRIAL_TPS, tier=1, **kw):
    return EvalResult(
        tier=tier,
        quality=quality,
        speed=speed,
        cost=0.1,
        reliability=0.99,
        per_suite_quality=kw.pop("per_suite_quality", {"coder": quality}),
        routing_distribution={"worker": 1.0},
        n_questions=kw.pop("n_questions", 50),
        **kw,
    )


def _gate(tmp_path, *, baseline_quality=1.9, frontdoor_speed=15.0):
    gate = SafetyGate(baseline_path=tmp_path / "absent.yaml")
    gate._baseline_eligible = lambda result: (True, "test-eligible", {})
    gate.baseline.baselines_by_tier = {1: baseline_quality} if baseline_quality is not None else {}
    gate.baseline.per_suite_quality_by_tier = {}
    gate.baseline.frontdoor_speed = frontdoor_speed
    return gate


# ── unit routing ──────────────────────────────────────────────────────────


def test_rate_axis_unit_is_declared_for_every_policy():
    assert rate_axis_unit(LEGACY_OBJECTIVE_POLICY) == RATE_AXIS_UNIT_TOKENS_PER_SECOND
    assert rate_axis_unit(TASK_RATE_OBJECTIVE_POLICY) == RATE_AXIS_UNIT_QUESTIONS_PER_HOUR
    for policy in RATE_POLICIES:
        assert rate_axis_unit(policy) == RATE_AXIS_UNIT_QUESTIONS_PER_HOUR
    assert rate_axis_unit("task_rate_4d_v99_future") is None
    assert rate_axis_unit(None) is None


@pytest.mark.parametrize("policy", RATE_POLICIES)
def test_rate_policy_never_writes_speed(policy):
    fields = sg.promotion_fields_from_objectives(LIVE_OBJECTIVES, 1, policy)
    assert "speed" not in fields
    assert fields[sg.PROMOTION_FIELD_TASK_RATE_QPH] == pytest.approx(59.49)
    assert fields["quality"] == pytest.approx(2.025)
    assert fields["cost"] == pytest.approx(0.5)
    assert fields["reliability"] == pytest.approx(0.8)


def test_legacy_policy_still_writes_speed():
    fields = sg.promotion_fields_from_objectives((2.0, 14.78, -0.5, 0.8), 1)
    assert fields["speed"] == pytest.approx(14.78)
    assert sg.PROMOTION_FIELD_TASK_RATE_QPH not in fields


def test_unknown_policy_is_refused_not_guessed():
    assert sg.promotion_fields_from_objectives(LIVE_OBJECTIVES, 1, "mystery_policy") is None


# ── the "every later trial fails the floor" failure cannot occur ──────────


def _no_throttle(monkeypatch):
    class _Host:
        def is_throttled(self):
            return (False, [])

    monkeypatch.setattr(hh.HostHealthState, "snapshot", staticmethod(lambda: _Host()))


# Another config's frontier point, so the normal frontier rule (not rule (b)) applies.
OTHER_CONFIG = _Entry(500, (1.0, 80.0, -0.5, 0.9))


def _promote_under_live_policy(tmp_path):
    _install([OTHER_CONFIG, _Entry(777, LIVE_OBJECTIVES)])
    gate = _gate(tmp_path)
    update = gate.update_baseline(_result(quality=2.1), source_trial_id=777)
    assert update.updated, update.reason
    return gate


def test_live_policy_promotion_keeps_frontdoor_speed_in_tokens_per_second(tmp_path):
    gate = _promote_under_live_policy(tmp_path)
    assert gate.baseline.frontdoor_speed == pytest.approx(TRIAL_TPS)  # the trial's own t/s
    assert gate.baseline.frontdoor_task_rate_qph == pytest.approx(59.49)
    assert gate.baseline.baselines_by_tier[1] == pytest.approx(2.025)  # reproduced median
    state = gate.baseline.to_state_dict()
    assert state["frontdoor_speed"] == pytest.approx(TRIAL_TPS)
    assert state["frontdoor_task_rate_qph"] == pytest.approx(59.49)


def test_later_trials_pass_the_throughput_floor_after_a_live_promotion(tmp_path, monkeypatch):
    _no_throttle(monkeypatch)
    gate = _promote_under_live_policy(tmp_path)
    gate.baseline.baselines_by_tier = {}  # isolate the throughput leg
    for speed in (TRIAL_TPS, 13.0, 12.0):  # >= 0.8 x 14.78 = 11.82
        verdict = gate.check(_result(quality=2.1, speed=speed))
        assert "throughput" not in verdict.categories, (speed, verdict.violations)
    verdict = gate.check(_result(quality=2.1, speed=10.0))  # genuinely slower: still caught
    assert "throughput" in verdict.categories


def test_mutation_old_routing_would_brick_the_floor(tmp_path, monkeypatch):
    """Mutation check: the assertion above FAILS under the pre-change routing."""
    _no_throttle(monkeypatch)

    real = sg.promotion_fields_from_objectives

    def old_routing(objectives, tier, objective_policy=LEGACY_OBJECTIVE_POLICY):
        return real(objectives, tier, LEGACY_OBJECTIVE_POLICY)  # pre-change: axis 1 -> speed

    monkeypatch.setattr(sg, "promotion_fields_from_objectives", old_routing)
    gate = _promote_under_live_policy(tmp_path)
    assert gate.baseline.frontdoor_speed == pytest.approx(59.49)  # q/h in a t/s field
    gate.baseline.baselines_by_tier = {}
    verdict = gate.check(_result(quality=2.1, speed=TRIAL_TPS))
    assert "throughput" in verdict.categories  # the failure mode the change removes


# ── live scope semantics ──────────────────────────────────────────────────


def test_empty_live_frontier_applies_rule_b_over_existing_baseline(tmp_path):
    """D2 superseded by operator decision (b): the empty live frontier routes to rule (b),
    which refuses when the candidate's reproductions cannot be counted."""
    _install([])
    gate = _gate(tmp_path)
    update = gate.update_baseline(_result(quality=2.5), source_trial_id=1)
    assert not update.updated
    assert update.promotion_rule == sg.PROMOTION_RULE_EMPTY_FRONTIER_REPRO
    assert "empty-frontier rule (b)" in update.reason
    assert gate.baseline.baselines_by_tier[1] == 1.9


def test_empty_live_frontier_still_allows_a_bootstrap_seed(tmp_path):
    _install([])
    gate = _gate(tmp_path, baseline_quality=None)
    update = gate.update_baseline(_result(quality=2.5), source_trial_id=1)
    assert update.updated, update.reason
    assert gate.baseline.baselines_by_tier[1] == 2.5


def test_empty_legacy_fallback_is_bootstrap_not_refusal(tmp_path):
    _install([], policy=LEGACY_OBJECTIVE_POLICY, scope="legacy_unscoped")
    gate = _gate(tmp_path)
    update = gate.update_baseline(_result(quality=2.5), source_trial_id=1)
    assert update.updated, update.reason


def test_non_representative_source_is_refused_under_live_scope(tmp_path):
    _install([_Entry(777, LIVE_OBJECTIVES)])
    gate = _gate(tmp_path)
    update = gate.update_baseline(_result(quality=2.0), source_trial_id=778)
    assert not update.updated
    assert "not a same-tier frontier representative" in update.reason


def test_frontier_entry_carries_its_policy(tmp_path):
    _install([_Entry(777, LIVE_OBJECTIVES)])
    entry = SafetyGate._archive_frontier_entry(777, 1)
    assert entry["objective_policy"] == RATE_4D_OBJECTIVE_POLICY
    assert entry["scope"] == "live"


def test_provider_failure_refuses_promotion_over_a_baseline(tmp_path):
    """Review finding 3: an unreadable guard archive never fails open."""

    def broken(pending_rows=()):
        raise RuntimeError("journal unreadable")

    sg.configure_promotion_guard_archive(broken)
    assert SafetyGate._archive_best_quality(1) is None
    assert SafetyGate._live_frontier_empty(1) is False
    gate = _gate(tmp_path)
    update = gate.update_baseline(_result(quality=2.5), source_trial_id=1)
    assert not update.updated
    assert update.promotion_rule == "refused_guard_unavailable"
    assert "journal unreadable" in update.reason and "fail-closed" in update.reason
    assert gate.baseline.baselines_by_tier[1] == 1.9


def test_legacy_archive_unreadable_also_refuses(tmp_path, monkeypatch):
    monkeypatch.setattr(sg, "_pareto_archive_for_safety_guard", lambda: None)
    gate = _gate(tmp_path)
    update = gate.update_baseline(_result(quality=2.5), source_trial_id=1)
    assert not update.updated and "legacy archive unreadable" in update.reason


def test_legacy_fallback_without_provider_warns_once(monkeypatch, caplog):
    monkeypatch.setattr(sg, "_pareto_archive_for_safety_guard", lambda: _Archive([]))
    with caplog.at_level("WARNING", logger="autopilot.safety"):
        first = sg._promotion_guard_view()
        second = sg._promotion_guard_view()
    assert first.objective_policy == LEGACY_OBJECTIVE_POLICY
    assert first.scope == second.scope == "legacy_unscoped"
    assert len([r for r in caplog.records if "no live-scope archive provider" in r.getMessage()]) == 1


def test_quality_ceiling_load_path_is_not_epoch_fenced(monkeypatch):
    """D3: an EMPTY live frontier must not make the load-path ceiling drop a reseeded baseline,
    and a LOW young live frontier must not either — the ceiling reads the unscoped view."""
    _install([_Entry(1, (1.0, 50.0, -0.5, 0.9))])  # live max quality 1.0
    monkeypatch.setattr(
        sg, "_pareto_archive_for_safety_guard", lambda: _Archive([_Entry(2, (2.4, 20.0, -0.5, 0.9))])
    )
    tiers = {1: 1.5}
    sg._drop_over_archive_max_tiers(tiers, Path("state"))
    assert tiers == {1: 1.5}


# ── persistence: old records stay readable ────────────────────────────────


def test_old_state_payload_without_qph_is_readable_and_byte_identical():
    b = Baseline()
    b.apply_state({"frontdoor_speed": 23.89})
    assert b.frontdoor_task_rate_qph is None
    assert "frontdoor_task_rate_qph" not in b.to_state_dict()


def test_qph_round_trips_through_state_and_yaml(tmp_path):
    b = Baseline(source_path=tmp_path / "b.yaml")
    b.apply_state({"frontdoor_task_rate_qph": 59.49})
    assert b.frontdoor_task_rate_qph == pytest.approx(59.49)
    b.save()
    loaded = Baseline.load(tmp_path / "b.yaml")
    assert loaded.frontdoor_task_rate_qph == pytest.approx(59.49)
    b2 = Baseline()
    b2.apply_state({"frontdoor_task_rate_qph": "bogus"})
    assert b2.frontdoor_task_rate_qph is None


# ── autopilot wiring reuses the W3 authority path ────────────────────────


def test_autopilot_installs_live_scope_from_state(monkeypatch):
    import autopilot

    calls = []

    def fake_authority(journal, **kwargs):
        calls.append(kwargs)
        return {"objective_policy": kwargs["objective_policy"], "all_entries": [], "frontiers": {}}

    monkeypatch.setattr(autopilot, "_journal_archive_payload_for_authority", fake_authority)
    state = {
        "pareto_objective_policy": RATE_4D_OBJECTIVE_POLICY,
        "pareto_exclude_before_ts": 1786378983.880697,
        "pareto_epoch_ts": 1786378983.880697,
    }
    autopilot._install_promotion_guard_scope(object(), state)
    view = sg._promotion_guard_view()
    assert view.scope == "live"
    assert view.objective_policy == RATE_4D_OBJECTIVE_POLICY
    assert calls[-1]["objective_policy"] == RATE_4D_OBJECTIVE_POLICY
    assert calls[-1]["exclude_before_ts"] == pytest.approx(1786378983.880697)
    # The provider reads the LIVE state dict on every call.
    state["pareto_exclude_before_ts"] = 1790000000.0
    sg._promotion_guard_view()
    assert calls[-1]["exclude_before_ts"] == pytest.approx(1790000000.0)
    source = Path(autopilot.__file__).read_text()
    body = source[source.index("def _run_loop_inner(") :]
    assert body.index("_install_promotion_guard_scope(journal, state)") < body.index(
        "gate = SafetyGate("
    )


# ── replay of the stored journal ──────────────────────────────────────────


def _fixture():
    return json.loads(FIXTURE.read_text())


def test_replay_fixture_provenance():
    data = _fixture()
    shards = data["_provenance"]["source_shards"]
    assert [Path(s["path"]).name for s in shards] == [
        "autopilot_journal.jsonl",
        "autopilot_journal_1.jsonl",
    ]
    assert len(data["rows"]) == 1372


def test_replay_old_and_live_agree_on_every_legacy_era_row():
    golden = _fixture()["golden"]
    for diff in golden["differences"]["old_vs_live"]:
        assert diff["row_policy"] != LEGACY_OBJECTIVE_POLICY, diff


def test_replay_promotions_carry_genuine_tps():
    golden = _fixture()["golden"]
    old = [d for d in golden["decisions"]["old"] if d["decision"] == "promoted"]
    live = [d for d in golden["decisions"]["live"] if d["decision"] == "promoted"]
    assert [d["trial_id"] for d in old] == [d["trial_id"] for d in live]
    for run, decisions in golden["decisions"].items():
        for d in decisions:
            if d["decision"] == "promoted" and d["tier"] == 1 and d["promotion_rule"] == "seed":
                # A seed writes the trial's own measurement: tokens/second, never q/h.
                assert d["frontdoor_speed_after"] == pytest.approx(d["row_speed_tps"]), (run, d)


def test_replay_old_vs_live_differences_are_refusal_reason_changes_only():
    golden = _fixture()["golden"]
    for diff in golden["differences"]["old_vs_live"]:
        assert diff["old"] != "promoted" and diff["live"] != "promoted", diff


def test_replay_live_c_records_a_rule_for_every_decision():
    golden = _fixture()["golden"]
    rules = {d["promotion_rule"] for d in golden["decisions"]["live_c"]}
    assert rules <= {"frontier", "empty_frontier_repro", "seed"}
    assert "frontier" in rules


def test_replay_compare_restores_the_safety_logger_level():
    """Review finding 1: compare() must not leave autopilot.safety at CRITICAL."""
    import logging

    import gate_frontier_replay as gfr

    logger = logging.getLogger("autopilot.safety")
    before = logger.level
    logger.setLevel(logging.INFO)
    try:
        gfr.compare(_fixture()["rows"][-40:], start_trial_id=10**9)
        assert logger.level == logging.INFO
    finally:
        logger.setLevel(before)


def test_live_restart_probe_documents_empty_live_frontier():
    probe = _fixture()["golden"]["live_restart_probe"]
    assert probe["objective_policy"] == RATE_4D_OBJECTIVE_POLICY
    assert probe["frontier_sizes"] == {"1": 0, "2": 0, "3": 0}


def test_replay_window_reproduces_golden_decisions():
    """Re-run the replay for the rate era (trial >= 1472) and compare to the golden."""
    import gate_frontier_replay as gfr

    data = _fixture()
    golden = data["golden"]["decisions"]
    start = 1472
    initial = {run: gfr.baselines_before(decisions, start) for run, decisions in golden.items()}
    result = gfr.compare(data["rows"], start_trial_id=start, initial_baselines=initial)
    for run, payload in result["runs"].items():
        expected = [
            {k: d[k] for k in ("trial_id", "decision", "previous_quality", "promotion_rule")}
            for d in golden[run]
            if d["trial_id"] >= start
        ]
        actual = [
            {k: d[k] for k in ("trial_id", "decision", "previous_quality", "promotion_rule")}
            for d in payload["decisions"]
        ]
        assert actual == expected, run


@pytest.mark.skipif(
    os.environ.get("GATE_FRONTIER_FULL_REPLAY") != "1",
    reason="full replay takes minutes; set GATE_FRONTIER_FULL_REPLAY=1",
)
def test_full_replay_matches_golden():
    import hashlib

    import gate_frontier_replay as gfr

    data = _fixture()
    result = gfr.compare(data["rows"])
    for run, payload in result["runs"].items():
        digest = hashlib.sha256(
            json.dumps(payload["decisions"], sort_keys=True).encode()
        ).hexdigest()
        assert digest == data["golden"]["decisions_sha256"][run], run
    assert result["differences"] == data["golden"]["differences"]
