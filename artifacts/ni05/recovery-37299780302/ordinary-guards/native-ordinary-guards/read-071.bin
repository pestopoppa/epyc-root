"""Tests for the extracted autopilot.actions module dispatcher."""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[2]
AUTOPILOT_DIR = ROOT / "scripts" / "autopilot"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(AUTOPILOT_DIR))

actions = importlib.import_module("actions")
autopilot = importlib.import_module("autopilot")
tier_specs = importlib.import_module("src.autopilot_core.tier_specs")


def _ctx(**overrides):
    """Build a minimal _ActionContext with all the fields zeroed/None unless overridden."""
    defaults = dict(
        seeder=None,
        swarm=None,
        forge=None,
        lab=None,
        tower=None,
        gate=None,
        archive=None,
        journal=None,
        state={},
        strategy_store=None,
        evo=None,
    )
    defaults.update(overrides)
    return actions._ActionContext(**defaults)


# ----- dispatcher routing -----


def test_dispatcher_rejects_ap9_scope_violation(caplog) -> None:
    # numeric_trial with 2 explicit params violates AP-9. The dispatcher now
    # returns a structured SkipOutcome (not bare None) so the main loop can
    # journal/count/feed-back the reason.
    result, species = actions.dispatch_action(
        {"type": "numeric_trial", "params": {"a": 1, "b": 2}},
        seeder=None,
        swarm=None,
        forge=None,
        lab=None,
        tower=None,
        gate=None,
        archive=None,
        journal=None,
        state={},
    )
    assert isinstance(result, actions.SkipOutcome)
    assert result.status == "skipped"
    assert "AP-9" in result.reason
    assert species == "numeric_trial"


def test_consult_gate_result_from_summary_is_tiered() -> None:
    summary = {
        "turns_requested_per_arm": 10,
        "rows_path": "/tmp/rows.jsonl",
        "artifact_dir": "/tmp/artifact",
        "summary": {
            "baseline": {"turns": 10, "quality": 0.7, "passes": 7},
            "consult": {"turns": 10, "quality": 0.8, "passes": 8, "consult_calls": 10},
            "gated": {
                "turns": 10,
                "quality": 0.8,
                "passes": 8,
                "consult_calls": 4,
                "consult_skips": 6,
                "rerun_requests": 2,
                "gate_reason_counts": {
                    "parser_data_contract": 3,
                    "plain_single_file_edit": 6,
                },
            },
            "gated_comparison": {"quality_delta_pp": 10.0},
        },
    }

    result = actions._consult_gate_result_from_summary(summary, elapsed_s=60.0, tier=3)

    assert result.tier == 3
    assert result.quality == 2.4
    assert result.speed == 1800.0
    assert result.cost == 0.4
    assert result.reliability == 0.8
    assert result.per_suite_quality == {"consult_gate_targeted": 2.4}
    assert result.details["consult_calls"] == 4
    assert result.details["consult_skips"] == 6
    assert result.details["gate_reason_counts"]["parser_data_contract"] == 3


def test_dispatcher_allows_current_forced_seq_candidate_replay(monkeypatch) -> None:
    action = {
        "type": "numeric_trial",
        "surface": "repl_executor",
        "params": {
            "repl.turn_token_cap": 1964,
            "repl.frontdoor_non_tool_token_cap": 866,
        },
    }
    expected = actions.EvalResult(
        tier=1,
        quality=2.0,
        speed=20.0,
        cost=0.5,
        reliability=1.0,
    )

    def fake_numeric_handler(handler_action, _ctx):  # noqa: ANN001
        assert handler_action == action
        return expected, "numeric_swarm"

    monkeypatch.setitem(actions._ACTION_HANDLERS, "numeric_trial", fake_numeric_handler)

    result, species = actions.dispatch_action(
        action,
        seeder=None,
        swarm=None,
        forge=None,
        lab=None,
        tower=None,
        gate=None,
        archive=None,
        journal=None,
        state={
            "trial_counter": 1213,
            "seq_candidate_replay_forced": {
                "trial_id": 1213,
                "action": action,
            },
        },
    )

    assert result is expected
    assert species == "numeric_swarm"


def test_dispatcher_rejects_suppressed_forced_seq_candidate_replay(monkeypatch) -> None:
    action = {
        "type": "numeric_trial",
        "surface": "kv_compaction",
        "params": {"kv.keep_ratio": 0.5},
    }

    def fail_handler(*_args, **_kwargs):  # noqa: ANN002, ANN003
        raise AssertionError("suppressed forced replay must not reach its handler")

    monkeypatch.setitem(actions._ACTION_HANDLERS, "numeric_trial", fail_handler)
    monkeypatch.setattr(actions, "suppressed_numeric_surfaces", lambda: {"kv_compaction"})

    result, species = actions.dispatch_action(
        action,
        seeder=None,
        swarm=None,
        forge=None,
        lab=None,
        tower=None,
        gate=None,
        archive=None,
        journal=None,
        state={
            "trial_counter": 1213,
            "seq_candidate_replay_forced": {"trial_id": 1213, "action": action},
        },
    )

    assert isinstance(result, actions.SkipOutcome)
    assert result.status == "skipped"
    assert "operator suppresses" in result.reason
    assert species == "numeric_trial"


def test_dispatcher_rejects_deep_eval_sampling_knobs(monkeypatch) -> None:
    def fail_handler(action, ctx):  # noqa: ANN001, ARG001
        raise AssertionError("deep_eval handler should not run for invalid schema")

    monkeypatch.setitem(actions._ACTION_HANDLERS, "deep_eval", fail_handler)

    result, species = actions.dispatch_action(
        {"type": "deep_eval", "tier": 2, "n_questions": 7, "seed": 999},
        seeder=None,
        swarm=None,
        forge=None,
        lab=None,
        tower=None,
        gate=None,
        archive=None,
        journal=None,
        state={},
    )

    assert isinstance(result, actions.SkipOutcome)
    assert result.status == "skipped"
    assert "AP-9" in result.reason
    assert "unsupported keys" in result.reason
    assert species == "deep_eval"


def test_dispatcher_unknown_action_type() -> None:
    result, species = actions.dispatch_action(
        {"type": "nonexistent_action"},
        seeder=None,
        swarm=None,
        forge=None,
        lab=None,
        tower=None,
        gate=None,
        archive=None,
        journal=None,
        state={},
    )
    assert isinstance(result, actions.SkipOutcome)
    assert result.status == "skipped"
    assert "unknown action type" in result.reason
    assert species == "unknown"


def test_dispatcher_rejects_action_outside_live_allowlist(monkeypatch) -> None:
    def fail_handler(action, ctx):  # noqa: ANN001, ARG001
        raise AssertionError("unpromoted action handler should not run")

    monkeypatch.setitem(actions._ACTION_HANDLERS, "code_mutation", fail_handler)

    result, species = actions.dispatch_action(
        {"type": "code_mutation", "target": "shadow"},
        seeder=None,
        swarm=None,
        forge=None,
        lab=None,
        tower=None,
        gate=None,
        archive=None,
        journal=None,
        state={},
        allowed_action_types=["seed_batch", "numeric_trial"],
    )

    assert isinstance(result, actions.SkipOutcome)
    assert result.status == "skipped"
    assert "active live-loop allowlist" in result.reason
    assert "shadow lane" in result.reason
    assert species == "code_mutation"


def test_blacklisted_action_becomes_invalid_skip() -> None:
    result = autopilot._blacklisted_action_skip(
        {"type": "seed_batch", "n_questions": 10},
        "Auto-blacklisted: 3 consecutive failures",
    )
    assert isinstance(result, actions.SkipOutcome)
    assert result.status == "invalid"
    assert result.reason == "action blacklisted: Auto-blacklisted: 3 consecutive failures"
    assert result.action_type == "seed_batch"


def test_slot_compact_handler_rejects_placeholder_port_zero() -> None:
    result, species = actions._action_slot_compact(
        {"type": "slot_compact", "port": 0},
        _ctx(),
    )

    assert isinstance(result, actions.SkipOutcome)
    assert result.status == "invalid"
    assert "port must be" in result.reason
    assert result.action_type == "slot_compact"
    assert species == "slot_management"


def test_blacklist_prompt_includes_older_enforced_patterns(monkeypatch) -> None:
    monkeypatch.setattr(autopilot, "BLACKLIST_RENDER_CAP", 2)

    text = autopilot._format_blacklist_for_prompt(
        [
            {
                "pattern": {
                    "type": "structural_experiment",
                    "flags": {"skillbank": True},
                },
                "reason": "old hidden reason",
                "source_trial": 505,
            },
            {
                "pattern": {"type": "numeric_trial", "surface": "monitor"},
                "reason": "recent monitor reason",
                "source_trial": 747,
            },
            {
                "pattern": {"type": "train_routing_models"},
                "reason": "recent routing reason",
                "source_trial": 781,
            },
        ]
    )

    assert "recent monitor reason" in text
    assert "recent routing reason" in text
    assert "Older enforced patterns" in text
    assert '{"flags":{"skillbank":true},"type":"structural_experiment"}' in text
    assert "source_trial=505" in text
    assert "no-expiry-metadata" in text


def test_blacklist_prompt_separates_p0_3_retryable_entries(monkeypatch) -> None:
    monkeypatch.setattr(autopilot, "BLACKLIST_RENDER_CAP", 4)

    text = autopilot._format_blacklist_for_prompt(
        [
            {
                "pattern": {
                    "type": "structural_experiment",
                    "flags": {"architect_delegation": True},
                },
                "reason": "Auto-blacklisted: 3 consecutive failures ending at trial 655",
                "source_trial": 655,
            },
            {
                "pattern": {"type": "prompt_mutation", "file": "frontdoor.md"},
                "reason": "MANUAL FREEZE: remove after restart",
                "source_trial": -1,
            },
        ]
    )

    assert "Retryable blacklist re-exploration entries" in text
    assert "architect_delegation_t655_tool_use_axis_bug" in text
    assert "target=architect_delegation_t655_tool_use_axis_bug; source_trial=655" in text
    assert "Recent enforced entries" in text
    assert "non-expiring" in text
    assert "purge-scoped=frontdoor_prompt_mutation_restart_freeze" in text
    assert "manual-purge-approval-required" in text
    assert '{"file":"frontdoor.md","type":"prompt_mutation"}' in text


def test_p0_3_retryable_blacklist_match_excludes_manual_freeze() -> None:
    blacklist = [
        {
            "pattern": {
                "type": "structural_experiment",
                "flags": {"specialist_routing": True},
            },
            "reason": "Auto-blacklisted: 3 consecutive failures ending at trial 664",
            "source_trial": 664,
        },
        {
            "pattern": {"type": "gepa_optimize", "file": "frontdoor.md"},
            "reason": "MANUAL FREEZE companion",
            "source_trial": -1,
        },
    ]

    retry = autopilot._p0_3_retryable_blacklist_match(
        {"type": "structural_experiment", "flags": {"specialist_routing": True}},
        blacklist,
    )

    assert retry is not None
    assert retry["target_key"] == "specialist_routing_t664_tool_use_axis_bug"
    assert (
        autopilot._p0_3_retryable_blacklist_match(
            {"type": "gepa_optimize", "file": "frontdoor.md", "max_evals": 50},
            blacklist,
        )
        is None
    )


def test_retryable_infra_seed_blacklist_is_not_replaced() -> None:
    requested = {"type": "seed_batch", "n_questions": 50}
    action, rationale = autopilot._replace_blacklisted_seed_fallback(
        requested,
        [
            {
                "pattern": {"type": "seed_batch", "n_questions": 50},
                "reason": "Auto-blacklisted: 3 consecutive failures ending at trial 1317",
                "source_trial": 1317,
            }
        ],
        {"falsifier": "original"},
    )

    assert action == requested
    assert rationale["falsifier"] == "original"
    assert rationale["p0_3_blacklist_reexploration"] is True
    assert (
        rationale["p0_3_blacklist_reexploration_scope"]
        == "infra_contaminated_blacklist_recheck"
    )


def test_structural_experiment_invalid_flags_returns_skip_outcome() -> None:
    """Invalid flag dependency surfaces the validator reason as a SkipOutcome,
    not a bare None — this is the graph_router-deadlock fix."""

    class FakeLab:
        def propose_flag_experiment(self, flags):
            return {
                "status": "invalid",
                "errors": ["graph_router feature requires specialist_routing feature"],
                "proposed_flags": flags,
            }

    result, species = actions._action_structural_experiment(
        {"type": "structural_experiment", "flags": {"graph_router": True}},
        _ctx(lab=FakeLab()),
    )
    assert isinstance(result, actions.SkipOutcome)
    assert result.status == "invalid"
    assert "specialist_routing" in result.reason
    assert species == "structural_lab"


def test_dispatch_structural_experiment_dependency_skip_stops_before_eval() -> None:
    class FakeLab:
        def current_flags(self):
            return {"memrl": True, "specialist_routing": False}

        def propose_flag_experiment(self, flags):
            return {
                "status": "invalid",
                "errors": ["graph_router feature requires specialist_routing feature"],
                "proposed_flags": flags,
            }

    class FakeTower:
        def hybrid_eval(self):  # pragma: no cover
            raise AssertionError("dependency-blocked structural candidate must not eval")

    result, species = actions.dispatch_action(
        {"type": "structural_experiment", "flags": {"graph_router": True}},
        seeder=None,
        swarm=None,
        forge=None,
        lab=FakeLab(),
        tower=FakeTower(),
        gate=None,
        archive=None,
        journal=None,
        state={},
    )

    assert isinstance(result, actions.SkipOutcome)
    assert result.status == "invalid"
    assert "specialist_routing" in result.reason
    assert species == "structural_lab"


def test_structural_experiment_error_status_is_skipped_not_invalid() -> None:
    """A transient validator 'error' (e.g. orchestrator unreachable) maps to a
    non-blacklisting 'skipped' SkipOutcome, never 'invalid' — so a blip cannot
    permanently blacklist a valid flag."""

    class FakeLab:
        def propose_flag_experiment(self, flags):
            return {"status": "error", "error": "live flag state unavailable"}

    result, species = actions._action_structural_experiment(
        {"type": "structural_experiment", "flags": {"graph_router": True}},
        _ctx(lab=FakeLab()),
    )
    assert isinstance(result, actions.SkipOutcome)
    assert result.status == "skipped"
    assert "unavailable" in result.reason
    assert species == "structural_lab"


def test_structural_experiment_noop_skips_before_validation_or_eval() -> None:
    class FakeLab:
        def current_flags(self):
            return {"graph_router": False, "specialist_routing": True}

        def propose_flag_experiment(self, _flags):  # pragma: no cover
            raise AssertionError("no-op structural candidate must not validate")

        def apply_flag_experiment(self, _flags):  # pragma: no cover
            raise AssertionError("no-op structural candidate must not apply")

    class FakeTower:
        def hybrid_eval(self):  # pragma: no cover
            raise AssertionError("no-op structural candidate must not eval")

    result, species = actions._action_structural_experiment(
        {"type": "structural_experiment", "flags": {"graph_router": False}},
        _ctx(lab=FakeLab(), tower=FakeTower()),
    )

    assert isinstance(result, actions.SkipOutcome)
    assert result.status == "skipped"
    assert "would not change live flag state" in result.reason
    assert "graph_router=false" in result.reason
    assert species == "structural_lab"


def test_structural_experiment_failed_revert_marks_eval_corrupted() -> None:
    class FakeLab:
        def __init__(self):
            self.applied = []

        def current_flags(self):
            return {"plan_review": False}

        def propose_flag_experiment(self, flags):
            return {"status": "valid", "flags": flags}

        def apply_flag_experiment(self, flags):
            self.applied.append(dict(flags))
            if flags == {"plan_review": True}:
                return {
                    "status": "ok",
                    "attestation": {"status": "ok", "expected": flags},
                }
            return {"status": "error", "error": "connection refused"}

    class FakeTower:
        def hybrid_eval(self):
            return actions.EvalResult(
                tier=1,
                quality=0.5,
                speed=10.0,
                cost=0.5,
                reliability=1.0,
            )

    class FakeGate:
        use_sequential = False

        def check(self, _eval_result):
            return False

    lab = FakeLab()
    result, species = actions._action_structural_experiment(
        {"type": "structural_experiment", "flags": {"plan_review": True}},
        _ctx(lab=lab, tower=FakeTower(), gate=FakeGate()),
    )

    assert isinstance(result, actions.EvalResult)
    assert species == "structural_lab"
    assert lab.applied == [{"plan_review": True}, {"plan_review": False}]
    assert result.details["flag_prior_values"] == {"plan_review": False}
    assert result.details["flag_revert_failed"] is True
    assert result.bug_corrupted_by == "structural_flag_revert_failure"
    assert "connection refused" in result.bug_corrupted_reason


def test_structural_experiment_requires_apply_attestation() -> None:
    class FakeLab:
        def __init__(self):
            self.applied = []

        def current_flags(self):
            return {"plan_review": False}

        def propose_flag_experiment(self, flags):
            return {"status": "valid", "flags": flags}

        def apply_flag_experiment(self, flags):
            self.applied.append(dict(flags))
            if flags == {"plan_review": True}:
                return {"status": "ok"}
            return {
                "status": "ok",
                "attestation": {"status": "ok", "expected": flags},
            }

    class FakeTower:
        def hybrid_eval(self):  # pragma: no cover
            raise AssertionError("must not eval without apply attestation")

    lab = FakeLab()
    result, species = actions._action_structural_experiment(
        {"type": "structural_experiment", "flags": {"plan_review": True}},
        _ctx(lab=lab, tower=FakeTower()),
    )

    assert isinstance(result, actions.SkipOutcome)
    assert species == "structural_lab"
    assert lab.applied == [{"plan_review": True}, {"plan_review": False}]
    assert result.bug_corrupted_by == "structural_flag_apply_failure"
    assert "attestation failed" in result.reason


def test_structural_experiment_requires_revert_attestation() -> None:
    class FakeLab:
        def __init__(self):
            self.applied = []

        def current_flags(self):
            return {"plan_review": False}

        def propose_flag_experiment(self, flags):
            return {"status": "valid", "flags": flags}

        def apply_flag_experiment(self, flags):
            self.applied.append(dict(flags))
            if flags == {"plan_review": True}:
                return {
                    "status": "ok",
                    "attestation": {"status": "ok", "expected": flags},
                }
            return {"status": "ok"}

    class FakeTower:
        def hybrid_eval(self):
            return actions.EvalResult(
                tier=1,
                quality=0.5,
                speed=10.0,
                cost=0.5,
                reliability=1.0,
            )

    class FakeGate:
        use_sequential = False

        def check(self, _eval_result):
            return False

    lab = FakeLab()
    result, species = actions._action_structural_experiment(
        {"type": "structural_experiment", "flags": {"plan_review": True}},
        _ctx(lab=lab, tower=FakeTower(), gate=FakeGate()),
    )

    assert isinstance(result, actions.EvalResult)
    assert species == "structural_lab"
    assert lab.applied == [{"plan_review": True}, {"plan_review": False}]
    assert result.details["flag_revert_failed"] is True
    assert result.bug_corrupted_by == "structural_flag_revert_failure"


def test_structural_experiment_refuses_eval_without_restore_snapshot() -> None:
    class FakeLab:
        def current_flags(self):
            return {}

        def propose_flag_experiment(self, flags):
            return {"status": "valid", "flags": flags}

        def apply_flag_experiment(self, _flags):  # pragma: no cover
            raise AssertionError("must not apply without a restore snapshot")

    class FakeTower:
        def hybrid_eval(self):  # pragma: no cover
            raise AssertionError("must not eval without a restore snapshot")

    result, species = actions._action_structural_experiment(
        {"type": "structural_experiment", "flags": {"plan_review": True}},
        _ctx(lab=FakeLab(), tower=FakeTower()),
    )

    assert isinstance(result, actions.SkipOutcome)
    assert result.status == "skipped"
    assert "restore snapshot" in result.reason
    assert species == "structural_lab"


def test_planner_convention_bindings_are_default_off(monkeypatch) -> None:
    monkeypatch.setattr(actions, "_PLANNER_HINTS_ENABLED", False)

    class FakeStore:
        def retrieve_conventions(self, **_kwargs):
            raise AssertionError("default-off path must not read StrategyStore")

    assert (
        actions._planner_convention_bindings(
            _ctx(strategy_store=FakeStore()), species="numeric_swarm"
        )
        == set()
    )


def test_structural_experiment_convention_denylist_blocks_live_bound_flag(
    monkeypatch,
) -> None:
    monkeypatch.setattr(actions, "_PLANNER_HINTS_ENABLED", True)

    class FakeStore:
        def retrieve_conventions(self, *, species, journal):
            assert species == "structural_lab"
            assert journal == "journal"
            return [
                SimpleNamespace(
                    metadata={
                        "bind_status": "live",
                        "bind_identifiers": ["graph_router"],
                    }
                ),
                SimpleNamespace(
                    metadata={
                        "bind_status": "future",
                        "bind_identifiers": ["specialist_routing"],
                    }
                ),
            ]

    class FakeLab:
        def propose_flag_experiment(self, _flags):  # pragma: no cover
            raise AssertionError("denylisted flag must not reach StructuralLab")

    result, species = actions._action_structural_experiment(
        {"type": "structural_experiment", "flags": {"graph_router": True}},
        _ctx(lab=FakeLab(), strategy_store=FakeStore(), journal="journal"),
    )

    assert isinstance(result, actions.SkipOutcome)
    assert result.status == "invalid"
    assert "graph_router" in result.reason
    assert species == "structural_lab"


def test_numeric_trial_convention_suppresses_live_bound_surface(
    monkeypatch,
) -> None:
    monkeypatch.setattr(actions, "_PLANNER_HINTS_ENABLED", True)

    class FakeStore:
        def retrieve_conventions(self, *, species, journal):
            assert species == "numeric_swarm"
            assert journal is None
            return [
                SimpleNamespace(
                    metadata={
                        "bind_status": "live",
                        "bind_identifiers": ["kv_compaction"],
                    }
                )
            ]

    class FakeSwarm:
        def suggest_trial(self, _surface):  # pragma: no cover
            raise AssertionError("suppressed surface must not reach NumericSwarm")

    result, species = actions._action_numeric_trial(
        {"type": "numeric_trial", "surface": "kv_compaction"},
        _ctx(swarm=FakeSwarm(), strategy_store=FakeStore()),
    )

    assert isinstance(result, actions.SkipOutcome)
    assert result.status == "invalid"
    assert "kv_compaction" in result.reason
    assert species == "numeric_swarm"


def test_dispatch_numeric_trial_convention_skip_stops_before_eval(
    monkeypatch,
) -> None:
    monkeypatch.setattr(actions, "_PLANNER_HINTS_ENABLED", True)

    class FakeStore:
        def retrieve_conventions(self, *, species, journal):
            assert species == "numeric_swarm"
            assert journal == "journal"
            return [
                SimpleNamespace(
                    metadata={
                        "bind_status": "live",
                        "bind_identifiers": ["kv_compaction"],
                    }
                )
            ]

    class FakeSwarm:
        def suggest_trial(self, _surface):  # pragma: no cover
            raise AssertionError("suppressed surface must not reach NumericSwarm")

    class FakeTower:
        def hybrid_eval(self):  # pragma: no cover
            raise AssertionError("suppressed numeric candidate must not eval")

    result, species = actions.dispatch_action(
        {"type": "numeric_trial", "surface": "kv_compaction", "params": {}},
        seeder=None,
        swarm=FakeSwarm(),
        forge=None,
        lab=None,
        tower=FakeTower(),
        gate=None,
        archive=None,
        journal="journal",
        state={},
        strategy_store=FakeStore(),
    )

    assert isinstance(result, actions.SkipOutcome)
    assert result.status == "invalid"
    assert "kv_compaction" in result.reason
    assert species == "numeric_swarm"


def test_numeric_trial_records_applied_optuna_params(monkeypatch) -> None:
    monkeypatch.setattr(
        actions,
        "_apply_params",
        lambda params: {"status": "ok", "applied": dict(params)},
    )

    class FakeSwarm:
        def suggest_trial(self, surface):
            assert surface == "monitor"
            return {
                "trial_number": 7,
                "surface": surface,
                "params": {"ORCHESTRATOR_MONITOR_THRESHOLD": 0.42},
            }

        def report_result(self, surface, trial_number, objectives):
            self.reported = (surface, trial_number, objectives)

    class FakeTower:
        def hybrid_eval(self):
            return actions.EvalResult(
                tier=1,
                quality=2.0,
                speed=10.0,
                cost=0.1,
                reliability=1.0,
                # Axis 1 of the live objective is questions/hour (W3 flip, 2026-08-04), so
                # a result must carry the wall clock and the question ledger to be
                # scoreable at all. Without them the rate is UNMEASURED — and unmeasured
                # deliberately raises rather than scoring 0 qph, which would archive this
                # config as maximally slow on an axis it never measured.
                n_questions=2,
                eval_wall_s=120.0,
                question_results=[{"qid": "q1"}, {"qid": "q2"}],
            )

    action = {"type": "numeric_trial", "surface": "monitor", "params": {}}
    swarm = FakeSwarm()
    result, species = actions._action_numeric_trial(
        action,
        _ctx(swarm=swarm, tower=FakeTower(), state={}),
    )

    assert species == "numeric_swarm"
    assert action["params"] == {"ORCHESTRATOR_MONITOR_THRESHOLD": 0.42}
    assert result.details["numeric_trial_applied_params"] == action["params"]
    # Compare against the canonical chokepoint, NOT the raw `EvalResult.objectives`
    # property — tier_specs.objectives_from is documented as the single source of truth
    # and the property is the ad-hoc tuple it exists to replace. The two diverged at the
    # W3 flip: the property still reports tokens/second on axis 1 while the swarm is
    # correctly fed questions/hour, so asserting the property would have flagged the
    # right behaviour as a regression.
    expected_objectives = tier_specs.objectives_from(result)
    assert swarm.reported == ("monitor", 7, expected_objectives)
    assert expected_objectives[1] == pytest.approx(
        tier_specs.seq_task_rate_qph_from(result)
    )


def test_numeric_trial_unmeasured_rate_fails_the_trial_instead_of_killing_it(
    monkeypatch,
) -> None:
    """An aborted batch must FAIL its Optuna trial, never raise out of the action.

    `objectives_from` raises `UnmeasuredObjectiveError` when the rate axis is
    unmeasured — here an `eval_wall_s` below the s/question validity floor, the
    shape a fast-rejected batch really produces. The trial dict has already been
    popped from `ctx.state` by then, so an escaping exception strands an Optuna
    trial that is neither reported nor failed and permanently occupies a slot in
    the study. autopilot.py guards the same condition at both of its
    `objectives_from` call sites.
    """

    monkeypatch.setattr(
        actions,
        "_apply_params",
        lambda params: {"status": "ok", "applied": dict(params)},
    )

    class FakeSwarm:
        def __init__(self):
            self.reported = None
            self.failed = None

        def suggest_trial(self, surface):
            return {"trial_number": 11, "surface": surface, "params": {}}

        def report_result(self, surface, trial_number, objectives):
            self.reported = (surface, trial_number, objectives)

        def mark_failed(self, surface, trial_number, reason=""):
            self.failed = (surface, trial_number, reason)

    unmeasured = actions.EvalResult(
        tier=1,
        quality=2.0,
        speed=10.0,
        cost=0.1,
        reliability=1.0,
        n_questions=2,
        eval_wall_s=0.5,  # below the 1.0 s/question validity floor
        question_results=[{"qid": "q1"}, {"qid": "q2"}],
    )
    # Precondition: this really is the raising shape, so the test cannot pass
    # merely because the guard is unreachable.
    with pytest.raises(tier_specs.UnmeasuredObjectiveError):
        tier_specs.objectives_from(unmeasured)

    class FakeTower:
        def hybrid_eval(self):
            return unmeasured

    swarm = FakeSwarm()
    state: dict = {}
    result, species = actions._action_numeric_trial(
        {"type": "numeric_trial", "surface": "monitor", "params": {}},
        _ctx(swarm=swarm, tower=FakeTower(), state=state),
    )

    assert species == "numeric_swarm"
    assert result is unmeasured
    assert swarm.reported is None, "must not fabricate an objective for an unmeasured axis"
    assert swarm.failed is not None, "the Optuna trial must be closed out, not stranded"
    assert swarm.failed[0] == "monitor" and swarm.failed[1] == 11
    assert "unmeasured" in swarm.failed[2]
    # The trial is consumed exactly once either way.
    assert "_current_optuna_trial" not in state


def test_numeric_trial_explicit_no_changes_skips_eval(monkeypatch) -> None:
    monkeypatch.setattr(
        actions,
        "_apply_params",
        lambda _params: {"status": "no_changes"},
    )

    class FakeTower:
        def hybrid_eval(self):  # pragma: no cover
            raise AssertionError("no-change numeric candidate must not eval")

    result, species = actions._action_numeric_trial(
        {
            "type": "numeric_trial",
            "surface": "monitor",
            "params": {"monitor.entropy_threshold": 0.42},
        },
        _ctx(tower=FakeTower(), state={}),
    )

    assert isinstance(result, actions.SkipOutcome)
    assert result.status == "skipped"
    assert "no live config changes" in result.reason
    assert species == "numeric_swarm"


def test_numeric_trial_suggested_no_changes_marks_failed_and_skips_eval(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        actions,
        "_apply_params",
        lambda _params: {"env_result": {"status": "no_changes"}},
    )

    class FakeSwarm:
        def suggest_trial(self, surface):
            return {
                "trial_number": 17,
                "surface": surface,
                "params": {"monitor.entropy_threshold": 0.42},
            }

        def mark_failed(self, surface, trial_number, reason):
            self.failed = (surface, trial_number, reason)

    class FakeTower:
        def hybrid_eval(self):  # pragma: no cover
            raise AssertionError("no-change numeric candidate must not eval")

    swarm = FakeSwarm()
    result, species = actions._action_numeric_trial(
        {"type": "numeric_trial", "surface": "monitor", "params": {}},
        _ctx(swarm=swarm, tower=FakeTower(), state={}),
    )

    assert isinstance(result, actions.SkipOutcome)
    assert result.status == "skipped"
    assert swarm.failed == (
        "monitor",
        17,
        "suggested params produced no live config changes",
    )
    assert species == "numeric_swarm"


def test_numeric_trial_normalizes_short_explicit_surface_param(monkeypatch) -> None:
    applied: list[dict] = []

    def fake_apply_params(params):
        applied.append(dict(params))
        return {"status": "ok", "applied": dict(params)}

    monkeypatch.setattr(actions, "_apply_params", fake_apply_params)

    class FakeTower:
        def hybrid_eval(self):
            return actions.EvalResult(
                tier=1,
                quality=2.0,
                speed=10.0,
                cost=0.1,
                reliability=1.0,
            )

    action = {
        "type": "numeric_trial",
        "surface": "kv_compaction",
        "params": {"keep_ratio": 0.5},
    }
    result, species = actions._action_numeric_trial(
        action,
        _ctx(tower=FakeTower(), state={}),
    )

    assert species == "numeric_swarm"
    assert applied == [{"kv.keep_ratio": 0.5}]
    assert action["params"] == {"kv.keep_ratio": 0.5}
    assert result.details["numeric_trial_applied_params"] == action["params"]


def test_dispatcher_routes_to_correct_handler(monkeypatch) -> None:
    """Smoke test that each registered handler is callable from dispatch_action."""
    captured = {}

    def fake_handler(action, ctx):
        captured["action"] = action
        captured["ctx_type"] = type(ctx).__name__
        return ("EVAL_SENTINEL", "test_species")

    monkeypatch.setitem(actions._ACTION_HANDLERS, "seed_batch", fake_handler)

    result, species = actions.dispatch_action(
        {"type": "seed_batch", "n_questions": 5},
        seeder="seeder_obj",
        swarm="swarm_obj",
        forge=None,
        lab=None,
        tower=None,
        gate=None,
        archive=None,
        journal=None,
        state={},
    )
    assert result == "EVAL_SENTINEL"
    assert species == "test_species"
    assert captured["action"]["n_questions"] == 5
    assert captured["ctx_type"] == "_ActionContext"


def test_dispatcher_sets_tower_trial_context(monkeypatch) -> None:
    captured = {}

    class FakeTower:
        def set_trial_context(self, trial_id):
            captured["trial_id"] = trial_id

    def fake_handler(action, ctx):
        captured["handler_saw_trial_id"] = captured.get("trial_id")
        return ("EVAL_SENTINEL", "test_species")

    monkeypatch.setitem(actions._ACTION_HANDLERS, "seed_batch", fake_handler)

    result, species = actions.dispatch_action(
        {"type": "seed_batch", "n_questions": 5},
        seeder="seeder_obj",
        swarm="swarm_obj",
        forge=None,
        lab=None,
        tower=FakeTower(),
        gate=None,
        archive=None,
        journal=None,
        state={"trial_counter": 817},
    )

    assert result == "EVAL_SENTINEL"
    assert species == "test_species"
    assert captured["trial_id"] == 817
    assert captured["handler_saw_trial_id"] == 817


def test_action_handlers_registered_for_all_known_types() -> None:
    """Sanity check: every documented action type has a handler."""
    expected = {
        "seed_batch",
        "numeric_trial",
        "prompt_mutation",
        "gepa_optimize",
        "code_mutation",
        "structural_experiment",
        "consult_gate_probe",
        "structural_prune",
        "train_routing_models",
        "distill_skillbank",
        "reset_memories",
        "deep_eval",
        "rollback",
        "distill_knowledge",
        "slot_compact",
        # Reviewer control-plane actions (H8 AP-5) — plan-generation, inference-gated.
        "review_policy_trial",
        "screening_tier_driver",
    }
    assert expected == set(actions._ACTION_HANDLERS.keys())


def test_bsv2_payload_uses_avg_prompt_tokens_not_instruction_tokens() -> None:
    result = actions.EvalResult(
        tier=1,
        quality=2.1,
        speed=50.0,
        cost=0.5,
        reliability=1.0,
        avg_prompt_tokens=321,
        instruction_token_count=9999,
    )

    payload = actions._bsv2_eval_payload(
        result,
        label="candidate",
        artifact_kind="prompt",
        target="frontdoor.md",
        mutation_type="compress",
    )

    assert payload["avg_prompt_tokens"] == 321


# ----- individual action handler unit (seed_batch is the simplest) -----


def test_seed_batch_handler_runs_eval_after_seed() -> None:
    """seed_batch must call seeder.run_batch then tower.hybrid_eval."""
    calls = []

    class FakeSeeder:
        def run_batch(self, *, n_questions, suites, watcher=None):
            calls.append(("seed", n_questions, suites))
            return None

    class FakeTower:
        def hybrid_eval(self):
            calls.append(("eval",))
            return "EVAL_RESULT"

    ctx = _ctx(seeder=FakeSeeder(), tower=FakeTower())
    result, species = actions._action_seed_batch(
        {"type": "seed_batch", "n_questions": 12, "suites": ["math"]}, ctx
    )
    assert result == "EVAL_RESULT"
    assert species == "seeder"
    assert calls == [("seed", 12, ["math"]), ("eval",)]


def test_seed_batch_handler_does_not_inject_strategy_hints_into_prompts(monkeypatch) -> None:
    monkeypatch.setattr(actions, "_PLANNER_HINTS_ENABLED", True)
    calls = []

    class FakeSeeder:
        def run_batch(self, *, n_questions, suites, watcher=None):
            calls.append(("seed", n_questions, suites))
            return None

    class FakeTower:
        def hybrid_eval(self):
            calls.append(("eval",))
            return "EVAL_RESULT"

    class FakeStore:
        def retrieve_for_journal(self, query, *, journal, k, species=None):
            calls.append(("retrieve", query, journal, k, species))
            return [
                SimpleNamespace(
                    source_trial_id=22,
                    species="seeder",
                    title="Seed guidance",
                    description="seed_batch guidance",
                    insight="Prefer balanced suites",
                    generalized_content="Prefer balanced suites",
                )
            ]

    journal = object()
    ctx = _ctx(
        seeder=FakeSeeder(),
        tower=FakeTower(),
        journal=journal,
        strategy_store=FakeStore(),
    )
    result, species = actions._action_seed_batch(
        {"type": "seed_batch", "n_questions": 12, "suites": ["math"]},
        ctx,
    )

    assert result == "EVAL_RESULT"
    assert species == "seeder"
    assert calls[0] == ("retrieve", "seed_batch seeder math n_questions=12", journal, 5, "seeder")
    assert calls[1] == ("seed", 12, ["math"])
    assert calls[2] == ("eval",)


def test_deep_eval_handler_calls_tower_evaluate_with_tier() -> None:
    class FakeTower:
        def __init__(self):
            self.calls = []

        def evaluate(self, **kwargs):
            self.calls.append(kwargs)
            return "DEEP_EVAL"

    tower = FakeTower()
    result, species = actions._action_deep_eval(
        {"type": "deep_eval", "tier": 2, "n": 7, "n_questions": 7, "seed": 999},
        _ctx(tower=tower),
    )
    assert result == "DEEP_EVAL"
    assert species == "seeder"
    assert tower.calls == [{"tier": 2}]


def test_deep_eval_replays_seq_promotion_numeric_candidate(monkeypatch) -> None:
    applied: list[dict] = []

    def fake_apply_params(params):
        applied.append(dict(params))
        return {"status": "ok", "applied": dict(params)}

    monkeypatch.setattr(actions, "_apply_params", fake_apply_params)

    class FakeTower:
        def __init__(self):
            self.calls = []

        def evaluate(self, **kwargs):
            self.calls.append(kwargs)
            return actions.EvalResult(
                tier=2,
                quality=2.0,
                speed=10.0,
                cost=0.1,
                reliability=1.0,
            )

    tower = FakeTower()
    state = {
        "trial_counter": 21,
        "_seq_promotion_candidate_replay": {
            "candidate": "candidate-a",
            "source_trial_id": 12,
            "action": {
                "type": "numeric_trial",
                "surface": "monitor",
                "params": {"ORCHESTRATOR_MONITOR_THRESHOLD": 0.42},
            },
        },
    }
    journal = SimpleNamespace(
        recent=lambda _limit: [
            SimpleNamespace(
                eval_details={
                    "question_results": [
                        {"qid": "recent-qid", "question_id": "recent-pool-id"}
                    ]
                }
            )
        ]
    )

    result, species = actions._action_deep_eval(
        {"type": "deep_eval", "tier": 2},
        _ctx(tower=tower, state=state, journal=journal),
    )

    assert species == "seeder"
    assert applied == [{"ORCHESTRATOR_MONITOR_THRESHOLD": 0.42}]
    assert tower.calls == [
        {
            "tier": 2,
            "promotion_eval": True,
            "trial_id": 21,
            "exclude_qids": {"recent-qid", "recent-pool-id"},
        }
    ]
    assert "_seq_promotion_candidate_replay" not in state
    assert result.details["seq_promotion_candidate_replay"] == {
        "candidate_action_type": "numeric_trial",
        "surface": "monitor",
        "applied_params": {"ORCHESTRATOR_MONITOR_THRESHOLD": 0.42},
        "apply_result": {
            "status": "ok",
            "applied": {"ORCHESTRATOR_MONITOR_THRESHOLD": 0.42},
        },
    }


def test_deep_eval_rejects_unreplayable_seq_promotion_numeric_candidate() -> None:
    state = {
        "_seq_promotion_candidate_replay": {
            "candidate": "candidate-a",
            "source_trial_id": 12,
            "action": {
                "type": "numeric_trial",
                "surface": "monitor",
                "params": {},
            },
        }
    }

    result, species = actions._action_deep_eval(
        {"type": "deep_eval", "tier": 2},
        _ctx(tower=SimpleNamespace(evaluate=lambda **_: "should not run"), state=state),
    )

    assert species == "seeder"
    assert isinstance(result, actions.SkipOutcome)
    assert result.status == "invalid"
    assert "lacks replayable applied params" in result.reason
    assert "_seq_promotion_candidate_replay" not in state


def test_recent_eval_qids_excludes_only_rows_inside_recency_window(monkeypatch) -> None:
    monkeypatch.setattr(actions, "SEQ_PROMOTION_RECENT_QID_DAYS", 60)
    # Timestamps are generated relative to wall-clock now (the code under test
    # reads datetime.now) so the fixture cannot age out of the 60-day window.
    now = datetime.now(timezone.utc)
    old_ts = (now - timedelta(days=180)).isoformat().replace("+00:00", "Z")
    fresh_ts = (now - timedelta(days=5)).isoformat().replace("+00:00", "Z")
    journal = SimpleNamespace(
        entries_with_supersessions=lambda: [
            SimpleNamespace(
                timestamp=old_ts,
                eval_details={"question_results": [{"qid": "old-q"}]},
            ),
            SimpleNamespace(
                timestamp=fresh_ts,
                eval_details={
                    "question_results": [
                        {
                            "qid": "fresh-q",
                            "question_id": "fresh-pool-id",
                            "id": "fresh-legacy-id",
                        }
                    ]
                },
            ),
            SimpleNamespace(
                timestamp="not-a-date",
                eval_details={"question_results": [{"qid": "malformed-time-q"}]},
            ),
        ]
    )

    assert actions._recent_eval_qids(journal, days=60) == {
        "fresh-q",
        "fresh-pool-id",
        "fresh-legacy-id",
        "malformed-time-q",
    }


def _eval_result(
    *,
    quality: float = 1.0,
    per_suite_quality: dict[str, float] | None = None,
    question_results: list[dict] | None = None,
) -> actions.EvalResult:
    return actions.EvalResult(
        tier=1,
        quality=quality,
        speed=10.0,
        cost=0.0,
        reliability=1.0,
        per_suite_quality=per_suite_quality or {},
        question_results=question_results or [],
    )


class _AlwaysPassGate:
    def check(self, result):
        return True


class _FakeJournal:
    def recent_failures(self, *, species, n):
        return []

    def insights_text(self, n):
        return "(no insights yet)"

    def all_entries(self):
        return []

    def recent(self, n):
        return []


class _RecordingGate:
    def __init__(self, *, use_sequential: bool):
        self.use_sequential = use_sequential
        self.calls: list[dict] = []

    def check(self, result, **kwargs):
        self.calls.append({"result": result, "kwargs": kwargs})
        return SimpleNamespace(seq={"state": "confirmed"} if kwargs else None)


def test_action_gate_check_default_off_uses_legacy_call() -> None:
    gate = _RecordingGate(use_sequential=False)
    result = _eval_result()

    verdict = actions._action_gate_check(
        {"type": "prompt_mutation"},
        _ctx(gate=gate),
        result,
    )

    assert verdict.seq is None
    assert len(gate.calls) == 1
    assert gate.calls[0]["kwargs"] == {}
    assert "seq_action_gate_check" not in result.details


def test_action_gate_check_threads_seq_inputs(monkeypatch) -> None:
    gate = _RecordingGate(use_sequential=True)
    result = _eval_result()
    result.question_results = [{"qid": 1, "ok": True}]

    monkeypatch.setattr(
        autopilot,
        "_seq_inputs_for_trial",
        lambda **kwargs: {
            "baseline_profile": {1: True},
            "baseline_task_rate": 12.5,
            "prior_quality_obs": [(7, 1.2)],
            "prior_rate_obs": [(8, 0.3)],
            "candidate": "candidate-x",
            "core_id": "core-v",
        },
    )
    # SEQ-B: the action gate must resolve the PAIRED rate helper, not the Pareto/goodput
    # one. `task_rate_qph_from` divides the decision-partition question count by the full
    # batch's wall clock, which does not match the incumbent comparator
    # `_seq_inputs_for_trial` builds — that mismatch scored an unchanged config as a 15%
    # throughput regression on every trial and froze the rate e-process.
    monkeypatch.setattr(autopilot, "seq_task_rate_qph_from", lambda _result: 42.0)
    monkeypatch.setattr(
        autopilot,
        "task_rate_qph_from",
        lambda _result: pytest.fail("action gate must not use the unpaired rate helper"),
    )

    verdict = actions._action_gate_check(
        {"type": "prompt_mutation"},
        _ctx(gate=gate, journal=_FakeJournal()),
        result,
    )

    assert verdict.seq == {"state": "confirmed"}
    kwargs = gate.calls[0]["kwargs"]
    assert kwargs["question_results"] == [{"qid": 1, "ok": True}]
    assert kwargs["task_rate"] == 42.0
    assert kwargs["baseline_profile"] == {1: True}
    assert kwargs["baseline_task_rate"] == 12.5
    assert kwargs["prior_quality_obs"] == [(7, 1.2)]
    assert kwargs["prior_rate_obs"] == [(8, 0.3)]
    assert kwargs["candidate"] == "candidate-x"
    assert kwargs["core_id"] == "core-v"
    assert result.details["seq_action_gate_check"] == {
        "enabled": True,
        "applied": True,
        "reason": "",
        "candidate": "candidate-x",
        "core_id": "core-v",
    }


class _FakeSwarm:
    def __init__(self):
        self.epochs: list[str] = []

    def mark_epoch(self, epoch):
        self.epochs.append(epoch)


class _QueuedTower:
    def __init__(self, results):
        self.results = list(results)
        self.calls = 0

    def hybrid_eval(self):
        self.calls += 1
        return self.results.pop(0)


def test_prompt_mutation_skill_gate_default_off_single_eval(monkeypatch) -> None:
    monkeypatch.delenv("AUTOPILOT_SKILL_EFFICACY_GATE", raising=False)
    monkeypatch.delenv("AUTOPILOT_BSV2_ACCEPT_GATE", raising=False)

    class FakeForge:
        def __init__(self):
            self.applied = 0
            self.reverted = 0

        def propose_mutation(self, **kwargs):
            return SimpleNamespace(
                file=kwargs["target_file"],
                mutation_type=kwargs["mutation_type"],
                description="test",
                original_content="old",
                mutated_content="new",
            )

        def apply_mutation(self, mutation):
            self.applied += 1

        def revert_mutation(self, mutation):
            self.reverted += 1

    tower = _QueuedTower([_eval_result(per_suite_quality={"math": 1.1})])
    forge = FakeForge()
    swarm = _FakeSwarm()
    result, species = actions._action_prompt_mutation(
        {"type": "prompt_mutation", "file": "frontdoor.md", "mutation": "targeted_fix"},
        _ctx(forge=forge, tower=tower, gate=_AlwaysPassGate(), swarm=swarm, journal=_FakeJournal()),
    )

    assert species == "prompt_forge"
    assert result.details.get("skill_efficacy") is None
    assert result.details.get("bsv2_accept_gate") is None
    assert tower.calls == 1
    assert forge.applied == 1
    assert forge.reverted == 0
    assert swarm.epochs == ["prompt_mutation:frontdoor.md/targeted_fix"]


def test_prompt_mutation_records_diversity_coverage_detail_observe_only(
    monkeypatch,
) -> None:
    monkeypatch.delenv("AUTOPILOT_SKILL_EFFICACY_GATE", raising=False)
    monkeypatch.delenv("AUTOPILOT_BSV2_ACCEPT_GATE", raising=False)

    class FakeForge:
        def __init__(self):
            self.failure_context = ""
            self.applied = 0
            self.reverted = 0

        def propose_mutation(self, **kwargs):
            self.failure_context = kwargs["failure_context"]
            return SimpleNamespace(
                file=kwargs["target_file"],
                mutation_type=kwargs["mutation_type"],
                description="test",
                original_content="old",
                mutated_content="new",
                safety_valid=True,
            )

        def apply_mutation(self, mutation):
            self.applied += 1

        def revert_mutation(self, mutation):
            self.reverted += 1

    class FakeStrategyStore:
        def __init__(self):
            self.calls = []

        def retrieve_for_journal(self, query, *, journal, k, species=None):
            self.calls.append((query, journal, k, species))
            if k == 8:
                return [
                    SimpleNamespace(
                        id="strategy-coverage-1",
                        source_trial_id=77,
                        species="prompt_forge",
                        description="frontdoor retry loop fix",
                        insight="prefer narrow retry-loop edits",
                        similarity_score=0.5,
                    )
                ]
            return []

    journal = _FakeJournal()
    store = FakeStrategyStore()
    tower = _QueuedTower([_eval_result(per_suite_quality={"math": 1.1})])
    forge = FakeForge()
    swarm = _FakeSwarm()
    result, species = actions._action_prompt_mutation(
        {
            "type": "prompt_mutation",
            "file": "frontdoor.md",
            "mutation": "targeted_fix",
            "description": "retry loop",
        },
        _ctx(
            forge=forge,
            tower=tower,
            gate=_AlwaysPassGate(),
            swarm=swarm,
            journal=journal,
            strategy_store=store,
            state={},
        ),
    )

    assert species == "prompt_forge"
    assert tower.calls == 1
    assert forge.applied == 1
    assert forge.reverted == 0
    assert "Diversity Coverage Pressure (AP-35/AP-36 observe-only)" in forge.failure_context
    assert store.calls == [
        ("frontdoor.md targeted_fix retry loop", journal, 3, None),
        ("frontdoor.md targeted_fix retry loop", journal, 8, "prompt_forge"),
    ]
    detail = result.details["mutation_diversity_coverage"]
    assert detail["schema_version"] == "mutation_diversity_coverage.v1"
    assert detail["artifact_kind"] == "prompt"
    assert detail["target"] == "frontdoor.md"
    assert detail["mutation_type"] == "targeted_fix"
    assert detail["decision"] == "kept"
    assert detail["acceptance_effect"] == "none_observe_only"
    assert detail["density"] == pytest.approx(0.5)
    assert detail["negative_log_density"] == pytest.approx(0.6931471805599453)
    assert detail["top_matches"][0]["source_trial_id"] == 77


def test_prompt_mutation_bsv2_gate_rejects_behavior_regression(monkeypatch) -> None:
    monkeypatch.delenv("AUTOPILOT_SKILL_EFFICACY_GATE", raising=False)
    monkeypatch.setenv("AUTOPILOT_BSV2_ACCEPT_GATE", "1")
    monkeypatch.setenv("AUTOPILOT_BSV2_MIN_SHARED_QIDS", "2")

    class FakeForge:
        def __init__(self):
            self.applied = 0
            self.reverted = 0

        def propose_mutation(self, **kwargs):
            return SimpleNamespace(
                file=kwargs["target_file"],
                mutation_type=kwargs["mutation_type"],
                description="test",
                original_content="old",
                mutated_content="new",
            )

        def apply_mutation(self, mutation):
            self.applied += 1

        def revert_mutation(self, mutation):
            self.reverted += 1

    baseline = _eval_result(
        question_results=[
            {"qid": "q1", "suite": "math", "correct": True},
            {"qid": "q2", "suite": "math", "correct": True},
        ]
    )
    candidate = _eval_result(
        question_results=[
            {"qid": "q1", "suite": "math", "correct": False},
            {"qid": "q2", "suite": "math", "correct": True},
        ]
    )
    tower = _QueuedTower([baseline, candidate])
    forge = FakeForge()
    swarm = _FakeSwarm()

    result, species = actions._action_prompt_mutation(
        {"type": "prompt_mutation", "file": "frontdoor.md", "mutation": "targeted_fix"},
        _ctx(forge=forge, tower=tower, gate=_AlwaysPassGate(), swarm=swarm, journal=_FakeJournal()),
    )

    assert species == "prompt_forge"
    assert tower.calls == 2
    assert forge.applied == 1
    assert forge.reverted == 1
    assert swarm.epochs == []
    detail = result.details["bsv2_accept_gate"]
    assert detail["accept"] is False
    assert detail["gate_decision"] == "block"
    assert detail["artifact_kind"] == "prompt"
    assert detail["paired_stats"]["shared_qids"] == 2
    assert detail["paired_stats"]["delta_b_minus_a"] == pytest.approx(-0.5)
    assert detail["signature_diff"]["severity"] == "blocking"


def test_prompt_mutation_transfer_safety_skip_stops_before_apply_or_eval() -> None:
    class FakeForge:
        def __init__(self):
            self.applied = 0

        def propose_mutation(self, **kwargs):
            return SimpleNamespace(
                file=kwargs["target_file"],
                mutation_type=kwargs["mutation_type"],
                description="test",
                original_content="old",
                mutated_content="old",
                safety_valid=False,
                safety_reason="domain_mismatched_anchoring",
            )

        def apply_mutation(self, mutation):
            self.applied += 1

    tower = _QueuedTower([])
    forge = FakeForge()
    swarm = _FakeSwarm()
    result, species = actions._action_prompt_mutation(
        {"type": "prompt_mutation", "file": "frontdoor.md", "mutation": "targeted_fix"},
        _ctx(forge=forge, tower=tower, gate=_AlwaysPassGate(), swarm=swarm, journal=_FakeJournal()),
    )

    assert result is None
    assert species == "prompt_forge"
    assert forge.applied == 0
    assert tower.calls == 0
    assert swarm.epochs == []


def test_prompt_mutation_skill_gate_rejects_per_suite_regression(monkeypatch) -> None:
    monkeypatch.setenv("AUTOPILOT_SKILL_EFFICACY_GATE", "1")

    class FakeForge:
        def __init__(self):
            self.reverted = 0

        def propose_mutation(self, **kwargs):
            return SimpleNamespace(
                file=kwargs["target_file"],
                mutation_type=kwargs["mutation_type"],
                description="test",
                original_content="old",
                mutated_content="new",
            )

        def apply_mutation(self, mutation):
            pass

        def revert_mutation(self, mutation):
            self.reverted += 1

    tower = _QueuedTower(
        [
            _eval_result(per_suite_quality={"math": 1.0, "web": 1.0}),
            _eval_result(per_suite_quality={"math": 2.5, "web": 0.0}),
        ]
    )
    forge = FakeForge()
    swarm = _FakeSwarm()
    result, species = actions._action_prompt_mutation(
        {"type": "prompt_mutation", "file": "frontdoor.md", "mutation": "targeted_fix"},
        _ctx(forge=forge, tower=tower, gate=_AlwaysPassGate(), swarm=swarm, journal=_FakeJournal()),
    )

    assert species == "prompt_forge"
    assert tower.calls == 2
    assert forge.reverted == 1
    assert swarm.epochs == []
    detail = result.details["skill_efficacy"]
    assert detail["accept"] is False
    assert detail["artifact_kind"] == "prompt"
    assert detail["regressed_suites"] == [("web", -1.0)]


def test_code_mutation_skill_gate_accepts_clean_gain(monkeypatch) -> None:
    monkeypatch.setenv("AUTOPILOT_SKILL_EFFICACY_GATE", "true")
    monkeypatch.delenv("AUTOPILOT_BSV2_ACCEPT_GATE", raising=False)

    class FakeForge:
        def __init__(self):
            self.reverted = 0

        def propose_code_mutation(self, **kwargs):
            return SimpleNamespace(
                file=kwargs["target_file"],
                mutation_type=kwargs["mutation_type"],
                description="test",
                original_content="old",
                mutated_content="new",
                syntax_valid=True,
            )

        def apply_code_mutation(self, mutation):
            pass

        def revert_code_mutation(self, mutation):
            self.reverted += 1

    tower = _QueuedTower(
        [
            _eval_result(per_suite_quality={"math": 1.0, "web": 1.0}),
            _eval_result(per_suite_quality={"math": 1.2, "web": 1.1}),
        ]
    )
    forge = FakeForge()
    swarm = _FakeSwarm()
    result, species = actions._action_code_mutation(
        {"type": "code_mutation", "file": "src/escalation.py", "mutation": "targeted_fix"},
        _ctx(forge=forge, tower=tower, gate=_AlwaysPassGate(), swarm=swarm, journal=_FakeJournal()),
    )

    assert species == "prompt_forge"
    assert tower.calls == 2
    assert forge.reverted == 0
    assert swarm.epochs == ["code_mutation:src/escalation.py/targeted_fix"]
    detail = result.details["skill_efficacy"]
    assert detail["accept"] is True
    assert detail["artifact_kind"] == "code"
    assert detail["aggregate_delta"] == pytest.approx(0.15)


def test_code_mutation_bsv2_gate_accepts_watch_behavior(monkeypatch) -> None:
    monkeypatch.delenv("AUTOPILOT_SKILL_EFFICACY_GATE", raising=False)
    monkeypatch.setenv("AUTOPILOT_BSV2_ACCEPT_GATE", "true")
    monkeypatch.setenv("AUTOPILOT_BSV2_MIN_SHARED_QIDS", "2")

    class FakeForge:
        def __init__(self):
            self.reverted = 0

        def propose_code_mutation(self, **kwargs):
            return SimpleNamespace(
                file=kwargs["target_file"],
                mutation_type=kwargs["mutation_type"],
                description="test",
                original_content="old",
                mutated_content="new",
                syntax_valid=True,
                safety_valid=True,
            )

        def apply_code_mutation(self, mutation):
            pass

        def revert_code_mutation(self, mutation):
            self.reverted += 1

    shared_vector = [
        {"qid": "q1", "suite": "math", "correct": True},
        {"qid": "q2", "suite": "math", "correct": False},
    ]
    tower = _QueuedTower(
        [
            _eval_result(question_results=shared_vector),
            _eval_result(question_results=shared_vector),
        ]
    )
    forge = FakeForge()
    swarm = _FakeSwarm()

    result, species = actions._action_code_mutation(
        {"type": "code_mutation", "file": "src/escalation.py", "mutation": "targeted_fix"},
        _ctx(forge=forge, tower=tower, gate=_AlwaysPassGate(), swarm=swarm, journal=_FakeJournal()),
    )

    assert species == "prompt_forge"
    assert tower.calls == 2
    assert forge.reverted == 0
    assert swarm.epochs == ["code_mutation:src/escalation.py/targeted_fix"]
    detail = result.details["bsv2_accept_gate"]
    assert detail["accept"] is True
    assert detail["gate_decision"] == "pass"
    assert detail["artifact_kind"] == "code"
    assert detail["signature_diff"]["severity"] == "watch"


def test_code_mutation_transfer_safety_skip_stops_before_apply_or_eval() -> None:
    class FakeForge:
        def __init__(self):
            self.applied = 0

        def propose_code_mutation(self, **kwargs):
            return SimpleNamespace(
                file=kwargs["target_file"],
                mutation_type=kwargs["mutation_type"],
                description="test",
                original_content="old",
                mutated_content="old",
                syntax_valid=True,
                safety_valid=False,
                safety_reason="misapplied_best_practice",
            )

        def apply_code_mutation(self, mutation):
            self.applied += 1

    tower = _QueuedTower([])
    forge = FakeForge()
    swarm = _FakeSwarm()
    result, species = actions._action_code_mutation(
        {"type": "code_mutation", "file": "src/escalation.py", "mutation": "targeted_fix"},
        _ctx(forge=forge, tower=tower, gate=_AlwaysPassGate(), swarm=swarm, journal=_FakeJournal()),
    )

    assert result is None
    assert species == "prompt_forge"
    assert forge.applied == 0
    assert tower.calls == 0
    assert swarm.epochs == []


def test_code_mutation_file_exists_block_does_not_raise() -> None:
    class FakeForge:
        def propose_code_mutation(self, **_kwargs):
            raise FileExistsError("new file already exists")

    result, species = actions._action_code_mutation(
        {
            "type": "code_mutation",
            "file": "src/generated/new_module.py",
            "mutation": "new_file",
        },
        _ctx(
            forge=FakeForge(),
            tower=_QueuedTower([]),
            gate=_AlwaysPassGate(),
            swarm=_FakeSwarm(),
            journal=_FakeJournal(),
        ),
    )

    assert result is None
    assert species == "prompt_forge"


def test_code_mutation_noop_skips_eval() -> None:
    class FakeForge:
        def __init__(self):
            self.applied = 0

        def propose_code_mutation(self, **kwargs):
            return SimpleNamespace(
                file=kwargs["target_file"],
                mutation_type=kwargs["mutation_type"],
                description="test",
                original_content="same",
                mutated_content="same",
                syntax_valid=True,
                safety_valid=True,
            )

        def apply_code_mutation(self, mutation):
            self.applied += 1

    tower = _QueuedTower([])
    forge = FakeForge()
    swarm = _FakeSwarm()
    result, species = actions._action_code_mutation(
        {"type": "code_mutation", "file": "src/escalation.py", "mutation": "targeted_fix"},
        _ctx(forge=forge, tower=tower, gate=_AlwaysPassGate(), swarm=swarm, journal=_FakeJournal()),
    )

    assert species == "prompt_forge"
    assert isinstance(result, actions.SkipOutcome)
    assert result.status == "skipped"
    assert result.reason == "code_mutation produced no file changes"
    assert forge.applied == 0
    assert tower.calls == 0
    assert swarm.epochs == []


def test_distill_knowledge_returns_evolution_manager_species() -> None:
    """Without evo/strategy_store, distill_knowledge is a journalable invalid outcome."""
    result, species = actions._action_distill_knowledge(
        {"type": "distill_knowledge"},
        _ctx(evo=None, strategy_store=None),
    )
    assert isinstance(result, actions.SkipOutcome)
    assert result.status == "invalid"
    assert "missing evo or strategy_store" in result.reason
    assert species == "evolution_manager"


def test_distill_knowledge_uses_superseded_journal_view() -> None:
    class FakeJournal(_FakeJournal):
        def all_entries(self):
            return ["raw"]

        def entries_with_supersessions(self):
            return ["folded"]

    class FakeEvolutionManager:
        def __init__(self):
            self.journal_entries = None

        def distill(self, *, journal_entries, strategy_store, last_n, trial_id):
            self.journal_entries = journal_entries
            return {
                "status": "success",
                "strategy_store": strategy_store,
                "last_n": last_n,
                "trial_id": trial_id,
            }

    evo = FakeEvolutionManager()

    result, species = actions._action_distill_knowledge(
        {"type": "distill_knowledge", "last_n": 7},
        _ctx(
            evo=evo,
            strategy_store=object(),
            journal=FakeJournal(),
            state={"trial_counter": 42},
        ),
    )

    assert species == "evolution_manager"
    assert result is None
    assert evo.journal_entries == ["folded"]


def test_distill_knowledge_failed_result_returns_invalid_skip() -> None:
    class FakeEvolutionManager:
        def distill(self, *, journal_entries, strategy_store, last_n, trial_id):
            return {"status": "failed", "reason": "LLM invocation failed"}

    result, species = actions._action_distill_knowledge(
        {"type": "distill_knowledge", "last_n": 7},
        _ctx(
            evo=FakeEvolutionManager(),
            strategy_store=object(),
            journal=_FakeJournal(),
            state={"trial_counter": 42},
        ),
    )

    assert species == "evolution_manager"
    assert isinstance(result, actions.SkipOutcome)
    assert result.status == "invalid"
    assert result.reason == "distill_knowledge failed: LLM invocation failed"


def test_distill_skillbank_unavailable_skips_eval() -> None:
    class FakeLab:
        def __init__(self):
            self.checkpoints = []

        def checkpoint_state(self, **kwargs):
            self.checkpoints.append(kwargs)

        def distill_skillbank(self, *, teacher, categories):
            return {"status": "not_available"}

    class FakeTower:
        def hybrid_eval(self):
            raise AssertionError("unavailable distill_skillbank must not run eval")

    result, species = actions._action_distill_skillbank(
        {"type": "distill_skillbank", "teacher": "claude", "categories": ["routing"]},
        _ctx(lab=FakeLab(), tower=FakeTower(), state={"trial_counter": 42}),
    )

    assert species == "structural_lab"
    assert isinstance(result, actions.SkipOutcome)
    assert result.status == "skipped"
    assert "DistillationPipeline not available" in result.reason


def test_distill_skillbank_available_runs_eval() -> None:
    class FakeLab:
        def checkpoint_state(self, **kwargs):
            pass

        def distill_skillbank(self, *, teacher, categories):
            return {"status": "success"}

    class FakeTower:
        def hybrid_eval(self):
            return "EVAL"

    result, species = actions._action_distill_skillbank(
        {"type": "distill_skillbank", "teacher": "claude", "categories": ["routing"]},
        _ctx(lab=FakeLab(), tower=FakeTower(), state={"trial_counter": 42}),
    )

    assert species == "structural_lab"
    assert result == "EVAL"


def test_mutation_context_filters_strategy_trials_superseded_by_journal() -> None:
    class FakeJournal(_FakeJournal):
        def entries_with_supersessions(self):
            return [
                SimpleNamespace(trial_id=1, bug_corrupted_by=""),
                SimpleNamespace(trial_id=2, bug_corrupted_by="resource_contention"),
                SimpleNamespace(trial_id=3, bug_corrupted_by="", outcome_status="error"),
                SimpleNamespace(
                    trial_id=4,
                    bug_corrupted_by="",
                    outcome_status="ok",
                    keep_revert_decision="excluded",
                ),
                SimpleNamespace(
                    trial_id=5,
                    bug_corrupted_by="",
                    outcome_status="ok",
                    keep_revert_decision="",
                    eval_details={"learning_exclusion": {"by": "mad_noise"}},
                ),
            ]

    class FakeStrategyStore:
        def __init__(self):
            self.calls = []

        def retrieve_for_journal(self, query, *, journal, k):
            self.calls.append((query, journal, k))
            return []

    store = FakeStrategyStore()

    actions._build_mutation_context(
        {
            "file": "src/example.py",
            "mutation": "targeted_fix",
            "description": "example",
        },
        _ctx(journal=FakeJournal(), strategy_store=store, state={}),
    )

    assert store.calls[0][1] is not None
    assert store.calls[0][2] == 3
    assert "src/example.py" in store.calls[0][0]
    assert store.calls[1][2] == 8


def test_mutation_context_promptforge_conventions_are_default_off(monkeypatch) -> None:
    monkeypatch.setattr(actions, "_PLANNER_HINTS_ENABLED", False)

    class FakeJournal:
        def recent_failures(self, species, n):
            return []

        def insights_text(self, n):
            return "(no insights yet)"

        def recent(self, n):
            return []

    class FakeStrategyStore:
        def retrieve_for_journal(self, query, *, journal, k):
            return []

        def retrieve_conventions(self, **_kwargs):
            raise AssertionError("default-off path must not read convention rows")

    failure_context, _ = actions._build_mutation_context(
        {
            "file": "src/example.py",
            "mutation": "targeted_fix",
            "description": "example",
        },
        _ctx(journal=FakeJournal(), strategy_store=FakeStrategyStore(), state={}),
    )

    assert "PromptForge Convention Guardrails" not in failure_context


def test_mutation_context_injects_promptforge_conventions_when_enabled(monkeypatch) -> None:
    monkeypatch.setattr(actions, "_PLANNER_HINTS_ENABLED", True)
    calls = []

    class FakeJournal:
        def recent_failures(self, species, n):
            return []

        def insights_text(self, n):
            return "(no insights yet)"

        def recent(self, n):
            return []

    class FakeStrategyStore:
        def retrieve_for_journal(self, query, *, journal, k):
            calls.append(("retrieve_for_journal", query, journal, k))
            return []

        def retrieve_conventions(self, *, species, journal, limit):
            calls.append(("retrieve_conventions", species, journal, limit))
            return [
                SimpleNamespace(
                    source_trial_id=44,
                    species="all",
                    title="Batch-1 decode exhausted",
                    description="batch=1 decode guardrail",
                    insight="Do not propose decode-kernel mutations for batch=1.",
                    generalized_content=("Do not propose decode-kernel mutations for batch=1."),
                )
            ]

    journal = FakeJournal()
    failure_context, _ = actions._build_mutation_context(
        {
            "file": "orchestration/prompts/roles/worker_general.md",
            "mutation": "targeted_fix",
            "description": "shorten answer format",
        },
        _ctx(journal=journal, strategy_store=FakeStrategyStore(), state={}),
    )

    assert calls[0][0] == "retrieve_for_journal"
    assert calls[1][0] == "retrieve_for_journal"
    assert calls[2] == ("retrieve_conventions", "prompt_forge", journal, 8)
    assert "## PromptForge Convention Guardrails" in failure_context
    assert "Batch-1 decode exhausted" in failure_context
    assert "Do not propose decode-kernel mutations for batch=1." in failure_context
    assert "Past Strategy Insights" not in failure_context


def test_mutation_context_injects_diversity_coverage_pressure() -> None:
    class FakeJournal:
        def recent_failures(self, species, n):
            return []

        def insights_text(self, n):
            return "(no insights yet)"

        def recent(self, n):
            return []

    class FakeStrategyStore:
        def __init__(self):
            self.calls = []

        def retrieve_for_journal(self, query, *, journal, k, species=None):
            self.calls.append((query, journal, k, species))
            return [
                SimpleNamespace(
                    id="strategy-1",
                    source_trial_id=88,
                    species="prompt_forge",
                    description="frontdoor retry loop fix",
                    insight="Prefer a narrow retry-loop guard over global routing edits.",
                    similarity_score=0.5,
                )
            ]

    journal = FakeJournal()
    store = FakeStrategyStore()
    failure_context, _ = actions._build_mutation_context(
        {
            "file": "frontdoor.md",
            "mutation": "targeted_fix",
            "description": "retry loop",
        },
        _ctx(journal=journal, strategy_store=store, state={}),
    )

    assert store.calls == [
        ("frontdoor.md targeted_fix retry loop", journal, 3, None),
        ("frontdoor.md targeted_fix retry loop", journal, 8, "prompt_forge"),
    ]
    assert "Diversity Coverage Pressure (AP-35/AP-36 observe-only)" in failure_context
    assert "strategy_density: 0.500000" in failure_context
    assert "negative_log_density: 0.693" in failure_context
    assert "not an acceptance score or quality gate" in failure_context
    assert "Trial #88 (prompt_forge) score=0.500000" in failure_context


def test_mutation_context_skips_legacy_strategy_store_without_journal_view(caplog) -> None:
    class LegacyStrategyStore:
        def retrieve(self, *args, **kwargs):
            raise AssertionError("raw retrieve fallback should not be called")

    failure_context, last_per_suite = actions._build_mutation_context(
        {
            "file": "src/example.py",
            "mutation": "targeted_fix",
            "description": "example",
        },
        _ctx(journal=_FakeJournal(), strategy_store=LegacyStrategyStore(), state={}),
    )

    assert last_per_suite is None
    assert "Past Strategy Insights" not in failure_context
    assert "retrieve_for_journal" in caplog.text


def test_mutation_context_prefers_contrastive_traces_from_tower() -> None:
    class FakeTower:
        def __init__(self):
            self.calls = []

        def capture_contrastive_traces(self, *, k_success, k_failure, trace_bank):
            self.calls.append((k_success, k_failure, trace_bank))
            return (
                "## Contrastive Execution Traces\n"
                "### Success Examples\n"
                "[1] trial #7\nTrace:\nSUCCESS TRACE"
            )

    tower = FakeTower()
    failure_context, _ = actions._build_mutation_context(
        {
            "file": "src/example.py",
            "mutation": "targeted_fix",
            "description": "example",
        },
        _ctx(
            journal=_FakeJournal(),
            tower=tower,
            state={
                "contrastive_trace_bank": [
                    {"outcome": "success", "trial_id": 7, "trace": "SUCCESS TRACE"}
                ],
                "last_traces": "LEGACY TRACE",
            },
        ),
    )

    assert tower.calls == [
        (
            2,
            2,
            [{"outcome": "success", "trial_id": 7, "trace": "SUCCESS TRACE"}],
        )
    ]
    assert "## Contrastive Execution Traces" in failure_context
    assert "SUCCESS TRACE" in failure_context
    assert "LEGACY TRACE" not in failure_context


def test_mutation_context_prefers_critic_trace_ir_prompt() -> None:
    class FakeTower:
        def capture_contrastive_traces(self, *, k_success, k_failure, trace_bank):
            raise AssertionError("legacy contrastive trace formatter should not run")

    failure_context, _ = actions._build_mutation_context(
        {
            "file": "src/example.py",
            "mutation": "targeted_fix",
            "description": "example",
        },
        _ctx(
            journal=_FakeJournal(),
            tower=FakeTower(),
            state={
                "critic_trace_ir_prompt": (
                    "## Harness Trace IR (MH-11 observe-only)\n"
                    '{"schema_version":"harness_trace_ir.v1"}'
                ),
                "contrastive_traces": "## Contrastive Execution Traces\nLEGACY STRUCTURED",
                "last_traces": "ROLE=frontdoor\nRESPONSE:\nlegacy",
            },
        ),
    )

    assert "## Harness Trace IR (MH-11 observe-only)" in failure_context
    assert "harness_trace_ir.v1" in failure_context
    assert "LEGACY STRUCTURED" not in failure_context
    assert "ROLE=frontdoor" not in failure_context


def test_mutation_context_formats_critic_trace_ir_from_state() -> None:
    class FakeTower:
        def format_critic_trace_ir(self, trace_ir):
            assert trace_ir == {"trace_examples": [{"outcome": "success"}]}
            return "## Harness Trace IR (MH-11 observe-only)\nFORMATTED"

    failure_context, _ = actions._build_mutation_context(
        {
            "file": "src/example.py",
            "mutation": "targeted_fix",
            "description": "example",
        },
        _ctx(
            journal=_FakeJournal(),
            tower=FakeTower(),
            state={"critic_trace_ir": {"trace_examples": [{"outcome": "success"}]}},
        ),
    )

    assert "## Harness Trace IR (MH-11 observe-only)" in failure_context
    assert "FORMATTED" in failure_context


def test_mutation_context_falls_back_to_recent_traces() -> None:
    failure_context, _ = actions._build_mutation_context(
        {
            "file": "src/example.py",
            "mutation": "targeted_fix",
            "description": "example",
        },
        _ctx(
            journal=_FakeJournal(),
            tower=None,
            state={"last_traces": "ROLE=frontdoor\nRESPONSE:\nlegacy"},
        ),
    )

    assert "## Recent Execution Traces" in failure_context
    assert "ROLE=frontdoor" in failure_context


def test_reset_memories_returns_none_eval() -> None:
    class FakeLab:
        def reset_and_reseed(self, **kw):
            return {"reset": True}

    result, species = actions._action_reset_memories(
        {"type": "reset_memories"},
        _ctx(lab=FakeLab(), state={"trial_counter": 5}),
    )
    assert result is None
    assert species == "structural_lab"


def test_repeated_meta_action_forces_metric_seed_batch() -> None:
    action, rationale = autopilot._force_metric_action_after_meta(
        {"type": "distill_knowledge", "last_n": 10},
        {"consecutive_meta_actions": 1},
        {"falsifier": "noop"},
    )
    assert action == {
        "type": "seed_batch",
        "n_questions": autopilot.SAFE_FALLBACK_SEED_N,
    }
    assert rationale == {
        "falsifier": "noop",
        "meta_action_forced_metric_trial": True,
    }


def test_repeated_meta_action_avoids_blacklisted_metric_seed_batch() -> None:
    action, rationale = autopilot._force_metric_action_after_meta(
        {"type": "distill_knowledge", "last_n": 10},
        {"consecutive_meta_actions": 1},
        {"falsifier": "noop"},
        [
            {
                "pattern": {
                    "type": "seed_batch",
                    "n_questions": autopilot.SAFE_FALLBACK_SEED_N,
                },
                "reason": "blocked",
            }
        ],
    )

    assert action == {"type": "seed_batch", "n_questions": 16}
    assert rationale["meta_action_forced_metric_trial"] is True
    assert rationale["fallback_seed_reselected"] is True
    assert rationale["fallback_seed_reselected_reason"] == "blocked"


def test_pre_dispatch_seed_fallback_reselects_blacklisted_action() -> None:
    action, rationale = autopilot._replace_blacklisted_seed_fallback(
        {
            "type": "seed_batch",
            "n_questions": autopilot.SAFE_FALLBACK_SEED_N,
            "suites": ["coder", "math"],
        },
        [
            {
                "pattern": {
                    "type": "seed_batch",
                    "n_questions": autopilot.SAFE_FALLBACK_SEED_N,
                    "suites": ["coder", "math"],
                },
                "reason": "blocked suite draw",
            }
        ],
        {"falsifier": "noop"},
        reason_label="test",
    )

    assert action == {"type": "seed_batch", "n_questions": autopilot.SAFE_FALLBACK_SEED_N}
    assert rationale["fallback_seed_reselected"] is True
    assert rationale["fallback_seed_reselected_context"] == "test"


def test_w8_replaces_blacklisted_candidate_before_invalid_skip(monkeypatch) -> None:
    monkeypatch.setattr(
        autopilot,
        "_configured_numeric_surfaces",
        lambda: ("escalation", "repl_budget"),
    )

    action, rationale = autopilot._replace_blacklisted_w8_candidate_action(
        {"type": "structural_experiment", "flags": {"graph_router": True}},
        [
            {
                "pattern": {
                    "type": "structural_experiment",
                    "flags": {"graph_router": True},
                },
                "reason": "repeated graph_router invalid",
            }
        ],
        {"falsifier": "original"},
        trial_counter=0,
        w8_replay_pressure_text=(
            "W8 replay pressure: 0/1 accumulating candidate(s) are replayable "
            "(blocked=unreplayable_action=seed_batch:1)."
        ),
    )

    assert action == {"type": "numeric_trial", "surface": "escalation", "params": {}}
    assert rationale["falsifier"] == "original"
    assert rationale["w8_blacklisted_candidate_replaced"] is True
    assert rationale["w8_blacklisted_candidate_reason"] == "repeated graph_router invalid"
    assert rationale["w8_blacklisted_candidate_original"] == {
        "type": "structural_experiment",
        "flags": {"graph_router": True},
    }


def test_w8_blacklisted_candidate_replacement_is_pressure_gated() -> None:
    requested = {"type": "structural_experiment", "flags": {"graph_router": True}}
    action, rationale = autopilot._replace_blacklisted_w8_candidate_action(
        requested,
        [
            {
                "pattern": {
                    "type": "structural_experiment",
                    "flags": {"graph_router": True},
                },
                "reason": "repeated graph_router invalid",
            }
        ],
        {"falsifier": "original"},
        trial_counter=0,
        w8_replay_pressure_text="No active W8 replay pressure.",
    )

    assert action == requested
    assert rationale == {"falsifier": "original"}


def test_w8_preserves_p0_3_retryable_structural_candidate() -> None:
    requested = {
        "type": "structural_experiment",
        "flags": {"architect_delegation": True},
    }

    action, rationale = autopilot._replace_blacklisted_w8_candidate_action(
        requested,
        [
            {
                "pattern": {
                    "type": "structural_experiment",
                    "flags": {"architect_delegation": True},
                },
                "reason": "Auto-blacklisted: 3 consecutive failures ending at trial 655",
                "source_trial": 655,
            }
        ],
        {"falsifier": "original"},
        trial_counter=0,
        w8_replay_pressure_text=(
            "W8 replay pressure: 0/1 accumulating candidate(s) are replayable "
            "(blocked=unreplayable_action=seed_batch:1)."
        ),
    )

    assert action == requested
    assert rationale["falsifier"] == "original"
    assert rationale["p0_3_blacklist_reexploration"] is True
    assert (
        rationale["p0_3_blacklist_reexploration_target"]
        == "architect_delegation_t655_tool_use_axis_bug"
    )


def test_autonomous_blacklisted_action_reselects_seed_fallback() -> None:
    action, rationale = autopilot._replace_blacklisted_autonomous_action(
        {"type": "gepa_optimize", "file": "frontdoor.md", "max_evals": 50},
        [
            {
                "pattern": {"type": "gepa_optimize", "file": "frontdoor.md"},
                "reason": "manual prompt freeze",
            }
        ],
        {"falsifier": "noop"},
    )

    assert action == {
        "type": "seed_batch",
        "n_questions": autopilot.SAFE_FALLBACK_SEED_N,
    }
    assert rationale["autonomous_blacklisted_replaced"] is True
    assert rationale["autonomous_blacklisted_reason"] == "manual prompt freeze"
    assert rationale["autonomous_blacklisted_from"] == {
        "type": "gepa_optimize",
        "file": "frontdoor.md",
        "max_evals": 50,
    }


def test_autonomous_meta_action_reselects_seed_fallback() -> None:
    action, rationale = autopilot._replace_blacklisted_autonomous_action(
        {"type": "distill_knowledge", "last_n": 10},
        [],
        {"falsifier": "noop"},
    )

    assert action == {
        "type": "seed_batch",
        "n_questions": autopilot.SAFE_FALLBACK_SEED_N,
    }
    assert rationale["autonomous_blacklisted_replaced"] is True
    assert rationale["autonomous_blacklisted_reason"] == (
        "autonomous meta action does not collect metrics"
    )
    assert rationale["autonomous_blacklisted_from"] == {
        "type": "distill_knowledge",
        "last_n": 10,
    }


def test_autonomous_blacklisted_action_stays_when_seed_fallbacks_exhausted() -> None:
    requested = {"type": "gepa_optimize", "file": "frontdoor.md", "max_evals": 50}
    blacklist = [
        {
            "pattern": {"type": "gepa_optimize", "file": "frontdoor.md"},
            "reason": "manual prompt freeze",
        },
        *[
            {
                "pattern": {"type": "seed_batch", "n_questions": n_questions},
                "reason": f"blocked {n_questions}",
            }
            for n_questions in autopilot.FALLBACK_SEED_CANDIDATES
        ],
    ]

    action, rationale = autopilot._replace_blacklisted_autonomous_action(
        requested,
        blacklist,
        {"falsifier": "noop"},
    )

    assert action == requested
    assert rationale == {"falsifier": "noop"}


def test_first_unblacklisted_seed_action_reports_exhaustion() -> None:
    blacklist = [
        {
            "pattern": {"type": "seed_batch", "n_questions": n_questions},
            "reason": f"blocked {n_questions}",
        }
        for n_questions in autopilot.FALLBACK_SEED_CANDIDATES
    ]

    action, reason = autopilot._first_unblacklisted_seed_action(blacklist)

    assert action is None
    assert reason == f"blocked {autopilot.FALLBACK_SEED_CANDIDATES[-1]}"


def test_first_unblacklisted_seed_action_uses_extended_seed_ladder() -> None:
    legacy_exhausted = (14, 16, 18, 20, 24, 30)
    blacklist = [
        {
            "pattern": {"type": "seed_batch", "n_questions": n_questions},
            "reason": f"blocked {n_questions}",
        }
        for n_questions in legacy_exhausted
    ]

    action, reason = autopilot._first_unblacklisted_seed_action(blacklist)

    assert action == {"type": "seed_batch", "n_questions": 40}
    assert reason == ""


def test_critic_fallback_seed_skip_when_seed_candidates_exhausted() -> None:
    skip = autopilot._critic_fallback_seed_skip(
        {"type": "seed_batch", "n_questions": autopilot.SAFE_FALLBACK_SEED_N},
        [
            {
                "pattern": {"type": "seed_batch", "n_questions": n_questions},
                "reason": f"blocked {n_questions}",
            }
            for n_questions in autopilot.FALLBACK_SEED_CANDIDATES
        ],
    )

    assert skip is not None
    assert skip.status == "skipped"
    assert skip.action_type == "planner_coordinator"
    assert "critic fallback seed_batch unavailable" in skip.reason


def test_exhausted_critic_seed_fallback_uses_numeric_trial(monkeypatch) -> None:
    monkeypatch.setattr(
        autopilot,
        "_configured_numeric_surfaces",
        lambda: ("memrl_retrieval", "think_harder"),
    )
    seed_blacklist = [
        {
            "pattern": {"type": "seed_batch", "n_questions": n_questions},
            "reason": f"blocked {n_questions}",
        }
        for n_questions in autopilot.FALLBACK_SEED_CANDIDATES
    ]

    action, rationale, skip = autopilot._replace_exhausted_critic_seed_fallback(
        {"type": "seed_batch", "n_questions": autopilot.SAFE_FALLBACK_SEED_N},
        seed_blacklist,
        {"falsifier": "fallback remains metric-bearing"},
        trial_counter=0,
    )

    assert skip is None
    assert action == {
        "type": "numeric_trial",
        "surface": "memrl_retrieval",
        "params": {},
    }
    assert rationale is not None
    assert rationale["falsifier"] == "fallback remains metric-bearing"
    assert rationale["critic_seed_fallback_replaced"] is True
    assert (
        "critic fallback seed_batch unavailable"
        in (rationale["critic_seed_fallback_unavailable_reason"])
    )


def test_exhausted_critic_seed_fallback_pauses_when_numeric_exhausted(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        autopilot,
        "_configured_numeric_surfaces",
        lambda: ("memrl_retrieval",),
    )
    blacklist = [
        {
            "pattern": {"type": "seed_batch", "n_questions": n_questions},
            "reason": f"blocked {n_questions}",
        }
        for n_questions in autopilot.FALLBACK_SEED_CANDIDATES
    ]
    blacklist.append(
        {
            "pattern": {
                "type": "numeric_trial",
                "surface": "memrl_retrieval",
                "params": {},
            },
            "reason": "numeric blocked",
            "scope": "surface",
        }
    )

    action, rationale, skip = autopilot._replace_exhausted_critic_seed_fallback(
        {"type": "seed_batch", "n_questions": autopilot.SAFE_FALLBACK_SEED_N},
        blacklist,
        {"falsifier": "noop"},
        trial_counter=0,
    )

    assert action == {
        "type": "seed_batch",
        "n_questions": autopilot.SAFE_FALLBACK_SEED_N,
    }
    assert rationale == {"falsifier": "noop"}
    assert skip is not None
    assert "critic fallback seed_batch unavailable" in skip.reason
    assert "numeric fallback unavailable" in skip.reason


def test_exhausted_critic_seed_fallback_uses_numeric_when_surface_ban_is_legacy(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        autopilot,
        "_configured_numeric_surfaces",
        lambda: ("memrl_retrieval",),
    )
    blacklist = [
        {
            "pattern": {"type": "seed_batch", "n_questions": n_questions},
            "reason": f"blocked {n_questions}",
        }
        for n_questions in autopilot.FALLBACK_SEED_CANDIDATES
    ]
    blacklist.append(
        {
            "pattern": {
                "type": "numeric_trial",
                "surface": "memrl_retrieval",
                "params": {},
            },
            "reason": "legacy numeric blocked",
        }
    )

    action, rationale, skip = autopilot._replace_exhausted_critic_seed_fallback(
        {"type": "seed_batch", "n_questions": autopilot.SAFE_FALLBACK_SEED_N},
        blacklist,
        {"falsifier": "noop"},
        trial_counter=0,
    )

    assert action == {
        "type": "numeric_trial",
        "surface": "memrl_retrieval",
        "params": {},
    }
    assert rationale["critic_seed_fallback_replaced"] is True
    assert skip is None


def test_critic_reject_seed_fallback_repairs_to_w8_candidate(monkeypatch) -> None:
    monkeypatch.setattr(
        autopilot,
        "_configured_numeric_surfaces",
        lambda: ("repl_budget",),
    )

    action, rationale, skip, repaired = autopilot._repair_critic_reject_fallback_for_w8(
        {"type": "seed_batch", "n_questions": autopilot.SAFE_FALLBACK_SEED_N},
        [],
        {"falsifier": "original"},
        trial_counter=0,
        w8_replay_pressure_text=(
            "W8 replay pressure: 0/1 accumulating candidate(s) are replayable "
            "(blocked=unreplayable_action=seed_batch:1)."
        ),
    )

    assert skip is None
    assert repaired is True
    assert action == {"type": "numeric_trial", "surface": "repl_budget", "params": {}}
    assert rationale["w8_candidate_generation_replaced"] is True
    assert rationale["critic_reject_loop_repaired_by_w8_candidate"] is True
    assert rationale["falsifier"] == "original"


def test_critic_reject_fallback_not_repaired_without_w8_pressure() -> None:
    action, rationale, skip, repaired = autopilot._repair_critic_reject_fallback_for_w8(
        {"type": "seed_batch", "n_questions": autopilot.SAFE_FALLBACK_SEED_N},
        [],
        {"falsifier": "original"},
        trial_counter=0,
        w8_replay_pressure_text="No active W8 replay pressure.",
    )

    assert skip is None
    assert repaired is False
    assert action == {"type": "seed_batch", "n_questions": autopilot.SAFE_FALLBACK_SEED_N}
    assert rationale == {"falsifier": "original"}


def test_first_meta_action_is_allowed() -> None:
    action, rationale = autopilot._force_metric_action_after_meta(
        {"type": "distill_knowledge", "last_n": 10},
        {"consecutive_meta_actions": 0},
        {"falsifier": "noop"},
    )
    assert action == {"type": "distill_knowledge", "last_n": 10}
    assert rationale == {"falsifier": "noop"}


# ----- experiment quota (passive-action ceiling) -----


def test_quota_passes_passive_below_memory_threshold() -> None:
    state = {"consecutive_passive_actions": 99}
    action, _ = autopilot._enforce_experiment_quota(
        {"type": "seed_batch", "n_questions": 10},
        state,
        memory_count=10,
        rationale=None,
        trial_counter=1,
    )
    # Below threshold seeding is legitimate — never overridden.
    assert action["type"] == "seed_batch"
    assert state["consecutive_passive_actions"] == 100


def test_quota_forces_experiment_after_consecutive_passive_when_memory_large() -> None:
    state = {"consecutive_passive_actions": autopilot.MAX_CONSECUTIVE_PASSIVE}
    action, rationale = autopilot._enforce_experiment_quota(
        {"type": "seed_batch", "n_questions": 10},
        state,
        memory_count=autopilot.QUOTA_MEMORY_THRESHOLD + 1,
        rationale={"falsifier": "x"},
        trial_counter=0,
    )
    assert action["type"] == "numeric_trial"
    assert action["params"] == {}
    assert rationale["experiment_quota_forced"] is True
    # Counter resets after forcing an experiment.
    assert state["consecutive_passive_actions"] == 0


def test_quota_numeric_surfaces_follow_numeric_swarm_registry() -> None:
    from species.numeric_swarm import SURFACES

    assert tuple(SURFACES) == autopilot._QUOTA_NUMERIC_SURFACES
    assert "chat_pipeline" in autopilot._QUOTA_NUMERIC_SURFACES
    assert "repl_budget" in autopilot._QUOTA_NUMERIC_SURFACES
    assert "kv_compaction" in autopilot._QUOTA_NUMERIC_SURFACES


def test_quota_skips_blacklisted_numeric_surface() -> None:
    state = {"consecutive_passive_actions": autopilot.MAX_CONSECUTIVE_PASSIVE}
    blocked_surface = autopilot._QUOTA_NUMERIC_SURFACES[0]
    expected_surface = autopilot._QUOTA_NUMERIC_SURFACES[1]
    action, rationale = autopilot._enforce_experiment_quota(
        {"type": "seed_batch", "n_questions": 10},
        state,
        memory_count=autopilot.QUOTA_MEMORY_THRESHOLD + 1,
        rationale={"falsifier": "x"},
        trial_counter=0,
        blacklist=[
            {
                "pattern": {
                    "type": "numeric_trial",
                    "surface": blocked_surface,
                    "params": {},
                },
                "reason": f"blocked {blocked_surface}",
                "scope": "surface",
            }
        ],
    )

    assert action == {"type": "numeric_trial", "surface": expected_surface, "params": {}}
    assert rationale["experiment_quota_forced"] is True
    assert state["consecutive_passive_actions"] == 0


def test_quota_ignores_legacy_unscoped_numeric_surface_blacklist() -> None:
    state = {"consecutive_passive_actions": autopilot.MAX_CONSECUTIVE_PASSIVE}
    first_surface = autopilot._QUOTA_NUMERIC_SURFACES[0]
    action, rationale = autopilot._enforce_experiment_quota(
        {"type": "seed_batch", "n_questions": 10},
        state,
        memory_count=autopilot.QUOTA_MEMORY_THRESHOLD + 1,
        rationale={"falsifier": "x"},
        trial_counter=0,
        blacklist=[
            {
                "pattern": {
                    "type": "numeric_trial",
                    "surface": first_surface,
                    "params": {},
                },
                "reason": f"legacy broad ban {first_surface}",
            }
        ],
    )

    assert action == {"type": "numeric_trial", "surface": first_surface, "params": {}}
    assert rationale["experiment_quota_forced"] is True
    assert state["consecutive_passive_actions"] == 0


def test_quota_records_block_when_all_numeric_surfaces_blacklisted() -> None:
    state = {"consecutive_passive_actions": autopilot.MAX_CONSECUTIVE_PASSIVE}
    requested = {"type": "seed_batch", "n_questions": 10}
    action, rationale = autopilot._enforce_experiment_quota(
        requested,
        state,
        memory_count=autopilot.QUOTA_MEMORY_THRESHOLD + 1,
        rationale={"falsifier": "x"},
        trial_counter=2,
        blacklist=[
            {
                "pattern": {
                    "type": "numeric_trial",
                    "surface": surface,
                    "params": {},
                },
                "reason": f"blocked {surface}",
                "scope": "surface",
            }
            for surface in autopilot._QUOTA_NUMERIC_SURFACES
        ],
    )

    assert action == requested
    assert rationale == {"falsifier": "x"}
    assert state["consecutive_passive_actions"] == autopilot.MAX_CONSECUTIVE_PASSIVE + 1
    assert state["experiment_quota_blocked"]["trial_id"] == 2


def test_quota_resets_counter_on_nonpassive_action() -> None:
    state = {"consecutive_passive_actions": 5}
    action, _ = autopilot._enforce_experiment_quota(
        {"type": "prompt_mutation", "file": "frontdoor.md"},
        state,
        memory_count=99999,
        rationale=None,
        trial_counter=0,
    )
    assert action["type"] == "prompt_mutation"
    assert state["consecutive_passive_actions"] == 0


def test_higher_tier_probe_forces_t2_when_empty() -> None:
    state = {}
    journal = SimpleNamespace(entries_with_supersessions=lambda: [])
    archive = SimpleNamespace(summary=lambda tier: {"frontier_size": 0})

    action, rationale = autopilot._maybe_force_higher_tier_probe(
        {"type": "numeric_trial", "surface": "think_harder"},
        state,
        journal=journal,
        archive=archive,
        rationale={"falsifier": "x"},
        trial_counter=100,
    )

    assert action == {"type": "deep_eval", "tier": 2}
    assert rationale["higher_tier_probe_forced"] is True
    assert rationale["higher_tier_probe_tier"] == 2
    assert state["higher_tier_probe_guard"]["last_forced_tier"] == 2


def test_higher_tier_probe_selects_staler_t3_after_t2_has_rows() -> None:
    state = {}
    journal = SimpleNamespace(
        entries_with_supersessions=lambda: [
            SimpleNamespace(
                bug_corrupted_by="",
                tier=2,
                trial_id=95,
            )
            for _ in range(3)
        ]
    )
    archive = SimpleNamespace(summary=lambda tier: {"frontier_size": 1 if tier == 2 else 0})

    action, rationale = autopilot._maybe_force_higher_tier_probe(
        {"type": "structural_experiment", "flags": {"tool_use": True}},
        state,
        journal=journal,
        archive=archive,
        rationale={},
        trial_counter=100,
    )

    assert action == {"type": "deep_eval", "tier": 3}
    assert rationale["higher_tier_probe_tier"] == 3


def test_higher_tier_probe_respects_cooldown() -> None:
    state = {
        "higher_tier_probe_guard": {
            "last_forced_trial_id": 95,
            "last_forced_tier": 2,
        }
    }
    requested = {"type": "numeric_trial", "surface": "monitor"}

    action, rationale = autopilot._maybe_force_higher_tier_probe(
        requested,
        state,
        journal=SimpleNamespace(entries_with_supersessions=lambda: []),
        archive=SimpleNamespace(summary=lambda tier: {"frontier_size": 0}),
        rationale={},
        trial_counter=100,
    )

    assert action == requested
    assert rationale == {}


def test_higher_tier_probe_skips_when_w8_candidate_generation_is_strict() -> None:
    state = {}
    requested = {"type": "seed_batch", "n_questions": 14}

    action, rationale = autopilot._maybe_force_higher_tier_probe(
        requested,
        state,
        journal=SimpleNamespace(entries_with_supersessions=lambda: []),
        archive=SimpleNamespace(summary=lambda tier: {"frontier_size": 0}),
        rationale={},
        trial_counter=100,
        w8_replay_pressure_text=(
            "W8 replay pressure: no accumulating candidate exists; 0/3 are replayable"
        ),
    )

    assert action == requested
    assert rationale == {}
    assert "higher_tier_probe_guard" not in state


def test_higher_tier_probe_respects_critic_reject_numeric_fallback() -> None:
    state = {}
    requested = {
        "type": "numeric_trial",
        "surface": "memrl_retrieval",
        "params": {},
    }
    safe_rationale = {
        "falsifier": "critic reject numeric fallback fails to produce replayable evidence",
        "critic_reject_numeric_fallback": True,
        "critic_reject_original_action": {"type": "deep_eval", "tier": 3},
    }

    action, rationale = autopilot._maybe_force_higher_tier_probe(
        requested,
        state,
        journal=SimpleNamespace(entries_with_supersessions=lambda: []),
        archive=SimpleNamespace(summary=lambda tier: {"frontier_size": 0}),
        rationale=safe_rationale,
        trial_counter=100,
    )

    assert action == requested
    assert rationale == safe_rationale
    assert "higher_tier_probe_guard" not in state


def test_higher_tier_probe_skips_when_outcome_progress_is_frontier_stalled() -> None:
    state = {}
    requested = {"type": "train_routing_models", "min_memories": 500}

    action, rationale = autopilot._maybe_force_higher_tier_probe(
        requested,
        state,
        journal=SimpleNamespace(entries_with_supersessions=lambda: []),
        archive=SimpleNamespace(summary=lambda tier: {"frontier_size": 0}),
        rationale={"falsifier": "train routing should improve frontier flow"},
        trial_counter=100,
        outcome_progress_pressure_text=(
            "Outcome blockers: frontier admission stale: 205 trial(s) since frontier > 150"
        ),
    )

    assert action == requested
    assert rationale["higher_tier_probe_skipped_outcome_stalled"] is True
    assert "higher_tier_probe_guard" not in state


def test_outcome_progress_guard_forces_numeric_when_frontier_stalled() -> None:
    state = {}

    action, rationale = autopilot._maybe_force_outcome_progress_action(
        {"type": "deep_eval", "tier": 3},
        state,
        blacklist=[],
        rationale={"falsifier": "higher tier probe should improve coverage"},
        trial_counter=100,
        outcome_progress_pressure_text=(
            "Outcome blockers: frontier admission stale: 205 trial(s) since frontier > 150"
        ),
    )

    assert action["type"] == "numeric_trial"
    assert action["surface"] in autopilot._configured_numeric_surfaces()
    assert rationale["outcome_progress_forced"] is True
    assert rationale["outcome_progress_original"] == {"type": "deep_eval", "tier": 3}
    assert state["outcome_progress_forced"]["forced_action"] == action


def test_outcome_progress_guard_preserves_frontier_moving_action() -> None:
    state = {}
    requested = {"type": "train_routing_models", "min_memories": 500}

    action, rationale = autopilot._maybe_force_outcome_progress_action(
        requested,
        state,
        blacklist=[],
        rationale={"falsifier": "routing training should improve frontier flow"},
        trial_counter=100,
        outcome_progress_pressure_text=(
            "Outcome blockers: frontier admission stale: 205 trial(s) since frontier > 150"
        ),
    )

    assert action == requested
    assert rationale["outcome_progress_satisfied_by_selected_action"] is True
    assert state["outcome_progress_forced"] is None


def test_higher_tier_probe_accepts_selected_t3_deep_eval() -> None:
    selected = {"type": "deep_eval", "tier": 3}

    action, rationale = autopilot._maybe_force_higher_tier_probe(
        selected,
        {},
        journal=SimpleNamespace(entries_with_supersessions=lambda: []),
        archive=SimpleNamespace(summary=lambda tier: {"frontier_size": 0}),
        rationale={},
        trial_counter=100,
    )

    assert action == selected
    assert rationale["higher_tier_probe_satisfied_by_selected_action"] is True
    assert rationale["higher_tier_probe_tier"] == 3


def test_seq_candidate_replay_accepts_materialized_optuna_params() -> None:
    action = {
        "type": "numeric_trial",
        "surface": "memrl_retrieval",
        "params": {
            "memrl_retrieval.q_weight": 0.61,
            "memrl_retrieval.semantic_k": 25,
            "memrl_retrieval.prior_strength": 0.43,
        },
    }
    journal = SimpleNamespace(
        entries_with_supersessions=lambda: [
            SimpleNamespace(
                trial_id=1212,
                bug_corrupted_by="",
                outcome_status="ok",
                tier=autopilot.DEFAULT_FRONTIER_TIER,
                keep_revert_decision="excluded",
                failure_analysis="",
                config_snapshot=action,
                seq={
                    "candidate": "candidate-optuna",
                    "core_id": autopilot.DEFAULT_EVIDENCE_CORE_ID,
                    "state": "accumulating",
                    "k": 1,
                    "E_quality": 1.02,
                    "E_rate_noninf": 0.94,
                },
            )
        ]
    )

    payload = autopilot._seq_candidate_replay_payload(journal, tier=1)

    assert payload is not None
    assert payload["candidate"] == "candidate-optuna"
    assert payload["action"] == action


def test_seq_candidate_replay_rejects_multi_flag_structural_candidate() -> None:
    assert autopilot._seq_promotion_replay_blocker(
        {
            "type": "structural_experiment",
            "flags": {"plan_review": True, "graph_router": True},
        }
    ).startswith("candidate structural_experiment changes 2 flags at once")


def test_frontier_rerun_forces_numeric_trial() -> None:
    state = {
        "frontier_rerun_required": {
            "required": True,
            "reason": "v6 kernel era opened",
        }
    }
    action, rationale = autopilot._maybe_force_frontier_rerun_action(
        {"type": "structural_prune", "file": "rules.md"},
        state,
        rationale={"falsifier": "x"},
        trial_counter=0,
    )

    assert action == {
        "type": "numeric_trial",
        "surface": autopilot._QUOTA_NUMERIC_SURFACES[0],
        "params": {},
    }
    assert rationale["frontier_rerun_forced"] is True
    assert rationale["frontier_rerun_reason"] == "v6 kernel era opened"
    assert state["frontier_rerun_forced"]["original_action"]["type"] == "structural_prune"


def test_frontier_rerun_accepts_selected_numeric_trial() -> None:
    state = {
        "frontier_rerun_required": {
            "required": True,
            "reason": "v6 kernel era opened",
        }
    }
    selected = {"type": "numeric_trial", "surface": "monitor", "params": {}}
    action, rationale = autopilot._maybe_force_frontier_rerun_action(
        selected,
        state,
        rationale={},
        trial_counter=1,
    )

    assert action == selected
    assert rationale["frontier_rerun_satisfied_by_selected_action"] is True
    assert state["frontier_rerun_forced"] is None
    assert state["frontier_rerun_pending_clear"] == {
        "trial_id": 1,
        "action": selected,
        "reason": "v6 kernel era opened",
    }


def test_frontier_rerun_pending_clear_does_not_force_again() -> None:
    state = {
        "frontier_rerun_required": {
            "required": True,
            "reason": "v6 kernel era opened",
        },
        "frontier_rerun_pending_clear": {
            "trial_id": 7,
            "action": {"type": "numeric_trial", "surface": "monitor", "params": {}},
            "reason": "v6 kernel era opened",
        },
    }
    requested = {"type": "structural_prune", "file": "rules.md"}
    action, rationale = autopilot._maybe_force_frontier_rerun_action(
        requested,
        state,
        rationale={"falsifier": "x"},
        trial_counter=8,
    )

    assert action == requested
    assert rationale["frontier_rerun_pending_clear"] is True
    assert rationale["frontier_rerun_pending_trial_id"] == 7


def test_frontier_rerun_pending_clear_keeps_forcing_until_min_trials() -> None:
    state = {
        "frontier_rerun_required": {
            "required": True,
            "reason": "v6 kernel era opened",
            "opened_at": "2026-06-28T01:40:00Z",
            "min_numeric_trials": 4,
        },
        "frontier_rerun_pending_clear": {
            "trial_id": 7,
            "action": {"type": "numeric_trial", "surface": "monitor", "params": {}},
            "reason": "v6 kernel era opened",
        },
    }
    journal = SimpleNamespace(
        entries_with_supersessions=lambda: [
            SimpleNamespace(
                bug_corrupted_by="",
                action_type="numeric_trial",
                tier=1,
                timestamp="2026-06-28T01:41:00Z",
            )
        ]
    )

    action, rationale = autopilot._maybe_force_frontier_rerun_action(
        {"type": "structural_prune", "file": "rules.md"},
        state,
        journal=journal,
        rationale={},
        trial_counter=8,
    )

    assert action["type"] == "numeric_trial"
    assert rationale["frontier_rerun_forced"] is True
    assert rationale["frontier_rerun_completed_numeric_trials"] == 1
    assert rationale["frontier_rerun_min_numeric_trials"] == 4


def test_frontier_rerun_pending_clear_stops_after_min_trials() -> None:
    state = {
        "frontier_rerun_required": {
            "required": True,
            "reason": "v6 kernel era opened",
            "opened_at": "2026-06-28T01:40:00Z",
            "min_numeric_trials": 2,
        },
        "frontier_rerun_pending_clear": {
            "trial_id": 7,
            "action": {"type": "numeric_trial", "surface": "monitor", "params": {}},
            "reason": "v6 kernel era opened",
        },
    }
    journal = SimpleNamespace(
        entries_with_supersessions=lambda: [
            SimpleNamespace(
                bug_corrupted_by="",
                action_type="numeric_trial",
                tier=1,
                timestamp="2026-06-28T01:41:00Z",
            ),
            SimpleNamespace(
                bug_corrupted_by="",
                action_type="numeric_trial",
                tier=1,
                timestamp="2026-06-28T01:42:00Z",
            ),
        ]
    )
    archive = SimpleNamespace(
        summary=lambda tier: {
            "tier": tier,
            "frontier_size": 1,
            "total_entries": 2,
            "hypervolume": 12.5,
            "best_quality": 2.16,
            "best_speed": 70.0,
        },
        frontier=lambda tier: [SimpleNamespace(trial_id=1005)],
    )
    requested = {"type": "structural_prune", "file": "rules.md"}

    action, rationale = autopilot._maybe_force_frontier_rerun_action(
        requested,
        state,
        journal=journal,
        archive=archive,
        rationale={},
        trial_counter=9,
    )

    assert action == requested
    assert rationale["frontier_rerun_cleared"] is True
    assert rationale["frontier_rerun_completed_numeric_trials"] == 2
    assert rationale["frontier_rerun_min_numeric_trials"] == 2
    assert state["frontier_rerun_required"]["required"] is False
    assert state["frontier_rerun_required"]["cleared_after_trial_id"] == 7
    assert state["frontier_rerun_required"]["completed_numeric_trials"] == 2
    assert state["frontier_rerun_required"]["min_numeric_trials"] == 2
    assert "frontier rerun satisfied" in state["frontier_rerun_required"]["reason"]
    snapshot = state["frontier_rerun_required"]["archive_snapshot"]
    assert snapshot["status"] == "ok"
    assert snapshot["tier"] == autopilot.DEFAULT_FRONTIER_TIER
    assert snapshot["frontier_size"] == 1
    assert snapshot["total_entries"] == 2
    assert snapshot["best_quality"] == 2.16
    assert snapshot["best_speed"] == 70.0
    assert snapshot["trial_ids"] == [1005]
    assert rationale["frontier_rerun_archive_snapshot"] == snapshot
    assert state["frontier_rerun_forced"] is None
    assert "frontier_rerun_pending_clear" not in state


def test_frontier_rerun_records_block_when_all_numeric_surfaces_blacklisted() -> None:
    state = {
        "frontier_rerun_required": {
            "required": True,
            "reason": "v6 kernel era opened",
        }
    }
    requested = {"type": "structural_prune", "file": "rules.md"}
    action, rationale = autopilot._maybe_force_frontier_rerun_action(
        requested,
        state,
        blacklist=[
            {
                "pattern": {
                    "type": "numeric_trial",
                    "surface": surface,
                    "params": {},
                },
                "reason": f"blocked {surface}",
                "scope": "surface",
            }
            for surface in autopilot._QUOTA_NUMERIC_SURFACES
        ],
        rationale={"falsifier": "x"},
        trial_counter=3,
    )

    assert action == requested
    assert rationale == {"falsifier": "x"}
    assert state["frontier_rerun_blocked"]["trial_id"] == 3


def test_frontier_rerun_summary_reports_live_progress() -> None:
    state = {
        "frontier_rerun_required": {
            "required": True,
            "reason": "v6 kernel era opened",
            "opened_at": "2026-06-28T01:40:00Z",
            "min_numeric_trials": 4,
        },
        "frontier_rerun_pending_clear": {
            "trial_id": 8,
            "action": {"type": "numeric_trial", "surface": "think_harder"},
        },
    }
    journal = SimpleNamespace(
        entries_with_supersessions=lambda: [
            SimpleNamespace(
                bug_corrupted_by="",
                action_type="numeric_trial",
                tier=1,
                timestamp="2026-06-28T01:41:00Z",
            ),
            SimpleNamespace(
                bug_corrupted_by="autopilot_killed_mid_trial",
                action_type="numeric_trial",
                tier=1,
                timestamp="2026-06-28T01:42:00Z",
            ),
        ]
    )

    lines = autopilot._frontier_rerun_summary_lines(state, journal)

    assert "Frontier rerun: required (1/4 numeric trials complete)" in lines
    assert "Frontier rerun reason: v6 kernel era opened" in lines
    assert "Frontier rerun opened: 2026-06-28T01:40:00Z" in lines
    assert "Frontier rerun pending: trial #8 numeric_trial/think_harder" in lines


def test_frontier_rerun_summary_reports_inactive_marker() -> None:
    journal = SimpleNamespace(entries_with_supersessions=lambda: [])

    assert autopilot._frontier_rerun_summary_lines({}, journal) == ["Frontier rerun: not required"]


def test_numeric_swarm_epoch_label_prefers_autopilot_speed_era() -> None:
    state = {
        "active_instrument_eras": {
            "cpu_bench": "E5-cpu-kernel",
            "autopilot_speed": "E5-autopilot-speed",
        }
    }

    assert autopilot._numeric_swarm_epoch_label_from_state(state) == "E5-autopilot-speed"


def test_numeric_swarm_epoch_label_absent_without_speed_era() -> None:
    assert autopilot._numeric_swarm_epoch_label_from_state({}) is None
    assert (
        autopilot._numeric_swarm_epoch_label_from_state(
            {"active_instrument_eras": {"cpu_bench": "E5-cpu-kernel"}}
        )
        is None
    )


def test_numeric_swarm_epoch_label_required_for_active_frontier_rerun() -> None:
    with pytest.raises(
        ValueError,
        match="frontier rerun requires active_instrument_eras.autopilot_speed",
    ):
        autopilot._numeric_swarm_epoch_label_from_state(
            {"frontier_rerun_required": {"required": True}}
        )


def test_archive_epoch_params_require_timestamps_for_active_speed_era() -> None:
    with pytest.raises(
        ValueError,
        match="active speed era requires pareto_epoch_ts and pareto_exclude_before_ts",
    ):
        autopilot._archive_epoch_params_from_state(
            {"active_instrument_eras": {"autopilot_speed": "E5-autopilot-speed"}}
        )


def test_archive_epoch_params_reject_malformed_epoch_for_active_speed_era() -> None:
    state = {
        "active_instrument_eras": {"autopilot_speed": "E5-autopilot-speed"},
        "pareto_epoch_ts": "not-a-timestamp",
        "pareto_exclude_before_ts": 1782511631.0,
    }

    with pytest.raises(ValueError, match="invalid pareto_epoch_ts"):
        autopilot._archive_epoch_params_from_state(state)


def test_archive_epoch_params_keep_legacy_tolerance_without_speed_era() -> None:
    assert autopilot._archive_epoch_params_from_state(
        {
            "pareto_epoch_ts": "not-a-timestamp",
            "pareto_pre_epoch_speed_factor": "bad-factor",
            "pareto_exclude_before_ts": "bad-exclude",
        }
    ) == (None, 1.0, None)


# ----- non-executing-action residue feedback -----


def test_last_invalid_feedback_none_when_clean() -> None:
    assert "none" in autopilot._build_last_invalid_feedback({}).lower()


def test_last_invalid_feedback_surfaces_reason_and_count() -> None:
    act = {"type": "structural_experiment", "flags": {"graph_router": True}}
    sig = autopilot._action_signature(act)
    state = {
        "last_invalid_action": act,
        "last_invalid_reason": "graph_router feature requires specialist_routing feature",
        "last_invalid_status": "invalid",
        "invalid_signature_counts": {sig: 3},
    }
    text = autopilot._build_last_invalid_feedback(state)
    assert "specialist_routing" in text
    assert "3×" in text
    assert "DO NOT repeat" in text


def test_last_invalid_feedback_surfaces_repeats_after_clear() -> None:
    """A repeated signature must still surface even when last_invalid_action was
    cleared by a successful (substituted) trial — the persistent counter drives
    the feedback so a critic-rejected draft cannot silently vanish."""
    state = {
        "last_invalid_action": None,
        "invalid_signature_counts": {'{"type": "x"}': 4},
    }
    text = autopilot._build_last_invalid_feedback(state)
    assert "Repeatedly non-executing" in text
    assert "4×" in text


def test_last_invalid_feedback_does_not_poison_observational_deep_eval() -> None:
    deep_eval = {"type": "deep_eval", "tier": 3}
    numeric = {
        "type": "numeric_trial",
        "surface": "think_harder",
        "params": {"think_harder.min_expected_roi": 0.05},
    }
    state = {
        "last_invalid_action": deep_eval,
        "last_invalid_reason": "critic rejected: repeated T3 probe",
        "last_invalid_status": "critic_rejected",
        "invalid_signature_counts": {
            autopilot._action_signature(deep_eval): 8,
            autopilot._action_signature(numeric): 3,
        },
    }

    text = autopilot._build_last_invalid_feedback(state)

    assert "remains schedulable" in text
    assert '"deep_eval"' not in text
    assert "8×" not in text
    assert "think_harder" in text
    assert "3×" in text


def test_prior_planner_decision_digest_summarizes_bounded_archive(tmp_path) -> None:
    archive = tmp_path / "planner_archive.jsonl"
    archive.write_text(
        "\n".join(
            [
                '{"type":"planner_coordinator","action_type":"seed_batch",'
                '"draft_provider":"claude","critic_provider":"codex",'
                '"critique_decision":"approve","degraded":false}',
                '{"type":"planner_provider_call","provider":"claude","role":"draft",'
                '"status":"timeout","ok":false,"error":"timeout after 600s"}',
                '{"type":"planner_coordinator","action_type":"numeric_trial",'
                '"draft_provider":"claude","critic_provider":"codex",'
                '"critique_decision":"unavailable","degraded":true,'
                '"fallback_reason":"critic timeout",'
                '"critique_issues":["review unavailable"]}',
            ]
        )
        + "\n"
    )

    text = autopilot._build_prior_planner_decision_digest(archive, limit=2)

    assert "seed_batch" not in text
    assert "timeout after 600s" in text
    assert "numeric_trial" in text
    assert "fallback=critic timeout" in text


def test_prior_planner_decision_digest_handles_missing_archive(tmp_path) -> None:
    text = autopilot._build_prior_planner_decision_digest(
        tmp_path / "missing.jsonl",
        limit=2,
    )

    assert "none yet" in text


def test_repo_readiness_advisory_disabled_without_env(monkeypatch) -> None:
    monkeypatch.delenv(autopilot.REPO_READINESS_PICKUP_ENV, raising=False)

    text = autopilot._build_repo_readiness_advisory()

    assert "disabled" in text
    assert autopilot.REPO_READINESS_PICKUP_ENV in text


def test_repo_readiness_advisory_renders_passive_candidates(tmp_path) -> None:
    pickup = tmp_path / "pickup.json"
    pickup.write_text(
        json.dumps(
            {
                "mode": "advisory_only",
                "authority_gate": False,
                "generated_at": "2026-06-21T09:53:20Z",
                "source_item_count": 49,
                "item_count": 2,
                "pickup_rules": ["review handoff", "run GitNexus impact"],
                "items": [
                    {
                        "id": "readiness:epyc-orchestrator:L3.security_automation",
                        "priority": "P0",
                        "repo": "epyc-orchestrator",
                        "criterion_id": "L3.security_automation",
                        "objective": "Automates secret/PII/security checks.",
                    },
                    {
                        "id": "readiness:epyc-llama:L3.machine_task_index",
                        "priority": "P0",
                        "repo": "epyc-llama",
                        "criterion_id": "L3.machine_task_index",
                        "objective": "Has structured or indexed task coordination.",
                    },
                ],
            }
        )
    )

    text = autopilot._build_repo_readiness_advisory(pickup, limit=1)

    assert "Planner context only" in text
    assert "NOT an acceptance gate" in text
    assert "readiness:epyc-orchestrator:L3.security_automation" in text
    assert "readiness:epyc-llama:L3.machine_task_index" not in text
    assert "review handoff; run GitNexus impact" in text


def test_repo_readiness_advisory_ignores_authority_gate(tmp_path) -> None:
    pickup = tmp_path / "pickup.json"
    pickup.write_text(
        json.dumps(
            {
                "mode": "advisory_only",
                "authority_gate": True,
                "items": [{"id": "readiness:x"}],
            }
        )
    )

    text = autopilot._build_repo_readiness_advisory(pickup)

    assert "ignored" in text
    assert "authority_gate=false" in text
    assert "readiness:x" not in text


def test_model_gate_advisory_reports_missing_artifact(tmp_path) -> None:
    text = autopilot._build_model_gate_advisory(reports_dir=tmp_path)

    assert "no model gate report artifact found" in text
    assert "model_gate_report.py" in text


def test_model_gate_advisory_renders_latest_next_actions(tmp_path) -> None:
    older = tmp_path / "fable5_gate_report_20260704T000000Z.json"
    older.write_text(json.dumps({"ready": True, "next_actions": []}))
    report = tmp_path / "fable5_gate_report_20260704T010000Z.json"
    report.write_text(
        json.dumps(
            {
                "ready": False,
                "summary": {
                    "active_next_action_keys": [
                        "collect_w8_promotion_eval_evidence",
                        "collect_ri10_canary_arm_telemetry",
                    ],
                    "blocked_next_action_keys": ["run_ds_e1_kv_measurements"],
                },
                "next_actions": [
                    {
                        "key": "run_ds_e1_kv_measurements",
                        "priority": "P0",
                        "status": "blocked",
                        "reason": "Needs direct production KV-size rows.",
                        "blocked_by": ["active AutoPilot process 123"],
                    },
                    {
                        "key": "collect_w8_promotion_eval_evidence",
                        "priority": "P0",
                        "status": "active",
                        "reason": "W8 still needs promotion evidence.",
                        "evidence": {
                            "latest_seq_trial_id": 1119,
                            "latest_combined_E": 0.931557,
                            "latest_required_E": 100.0,
                            "latest_fresh_eval": False,
                            "latest_seq_state": "accumulating",
                            "open_requirements": [
                                "combined_E_below_required",
                                "fresh_promotion_eval_required",
                            ],
                        },
                    },
                    {
                        "key": "collect_ri10_canary_arm_telemetry",
                        "priority": "P0",
                        "status": "active",
                        "reason": "RI-10 needs canary arm telemetry.",
                        "evidence": {
                            "canary_role_sample_deficit": 30,
                            "canary_arm_volume_deficit": 30,
                        },
                    },
                ],
            }
        )
    )

    text = autopilot._build_model_gate_advisory(reports_dir=tmp_path, limit=3)

    assert "Planner context only" in text
    assert "NOT an acceptance gate" in text
    assert report.name in text
    assert "ready=False" in text
    assert "active_next_actions=['collect_w8_promotion_eval_evidence'" in text
    assert "P0 active collect_w8_promotion_eval_evidence" in text
    assert "latest_combined_E=0.931557" in text
    assert "P0 active collect_ri10_canary_arm_telemetry" in text
    assert "canary_role_sample_deficit=30" in text
    assert "P0 blocked run_ds_e1_kv_measurements" in text
    assert "blocked_by=active AutoPilot process 123" in text


# ----- draft_critique: rejected-draft feedback (req #3) -----


class _FakeCritique:
    def __init__(self, decision="reject", issues=None):
        self.decision = decision
        self.issues = issues or ["unsafe"]


def test_record_rejected_draft_counts_and_sets_feedback() -> None:
    state = {}
    draft = {"type": "structural_experiment", "flags": {"graph_router": True}}
    blacklisted = autopilot._record_rejected_draft(state, draft, _FakeCritique(), trial_id=10)
    assert blacklisted is False  # first occurrence
    sig = autopilot._action_signature(draft)
    assert state["invalid_signature_counts"][sig] == 1
    assert state["critic_rejected_signatures"][sig]["trial_id"] == 10
    assert state["critic_rejected_signatures"][sig]["action"] == draft
    assert state["last_invalid_status"] == "critic_rejected"
    assert state["last_invalid_action"] == draft
    assert "critic rejected" in state["last_invalid_reason"]
    assert state["consecutive_rejected_drafts"] == 1


def test_record_rejected_draft_blacklists_on_repeat(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(
        autopilot,
        "append_blacklist",
        lambda action, tid, reason, **_: calls.append((action, reason)),
    )
    state = {}
    draft = {"type": "structural_experiment", "flags": {"graph_router": True}}
    autopilot._record_rejected_draft(state, draft, _FakeCritique(), trial_id=1)
    blacklisted = autopilot._record_rejected_draft(state, draft, _FakeCritique(), trial_id=2)
    assert blacklisted is True
    assert len(calls) == 1  # blacklisted exactly once, at the threshold (2x)
    assert state["consecutive_rejected_drafts"] == 2


def test_record_rejected_draft_keeps_observational_deep_eval_advisory() -> None:
    state = {
        "invalid_signature_counts": {
            autopilot._action_signature({"type": "deep_eval", "tier": 3}): 7
        },
        "consecutive_rejected_drafts": 1,
    }
    draft = {"type": "deep_eval", "tier": 3}

    blacklisted = autopilot._record_rejected_draft(
        state,
        draft,
        _FakeCritique(issues=["repeated T3 probe"]),
        trial_id=1208,
    )

    assert blacklisted is False
    assert state["invalid_signature_counts"] == {autopilot._action_signature(draft): 7}
    assert "critic_rejected_signatures" not in state
    assert state["consecutive_rejected_drafts"] == 1
    assert (
        state["critic_rejected_observational_signatures"][autopilot._action_signature(draft)][
            "trial_id"
        ]
        == 1208
    )


def test_operator_domain_critique_detection() -> None:
    assert autopilot._is_operator_domain_critique(
        _FakeCritique(issues=["baseline refresh is operator-domain"])
    )
    assert autopilot._is_operator_domain_critique(
        _FakeCritique(issues=["measurement trust boundary requires an era row"])
    )
    assert not autopilot._is_operator_domain_critique(
        _FakeCritique(issues=["graph_router dependency is missing"])
    )


def test_append_operator_outbox_item_dedupes_open_signature(tmp_path) -> None:
    path = tmp_path / "operator_outbox.jsonl"
    draft = {"type": "deep_eval", "tier": 3}
    critique = _FakeCritique(issues=["operator-domain T3 policy amendment"])

    assert autopilot._append_operator_outbox_item(
        draft,
        critique,
        trial_id=12,
        path=path,
    )
    assert not autopilot._append_operator_outbox_item(
        draft,
        critique,
        trial_id=13,
        path=path,
    )

    rows = [json.loads(line) for line in path.read_text().splitlines()]
    assert len(rows) == 1
    assert rows[0]["kind"] == "critic_rejected_operator_domain"
    assert rows[0]["source_trial"] == 12
    assert rows[0]["action"] == draft
    assert rows[0]["status"] == "open"


def test_operator_outbox_feedback_renders_open_items(tmp_path) -> None:
    path = tmp_path / "operator_outbox.jsonl"
    draft = {"type": "numeric_trial", "surface": "think_harder"}
    autopilot._append_operator_outbox_item(
        draft,
        _FakeCritique(issues=["baseline refresh is operator-domain"]),
        trial_id=21,
        path=path,
    )

    text = autopilot._build_operator_outbox_feedback(path, limit=2)

    assert "Open operator-domain items" in text
    assert "trial 21" in text
    assert "think_harder" in text
    assert "Do NOT re-propose" in text


def test_record_rejected_draft_outboxes_operator_domain(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(
        autopilot,
        "_append_operator_outbox_item",
        lambda action, critique, trial_id: calls.append((action, trial_id)) or True,
    )
    state = {}
    draft = {"type": "deep_eval", "tier": 3}

    autopilot._record_rejected_draft(
        state,
        draft,
        _FakeCritique(issues=["operator-domain tier policy requires approval"]),
        trial_id=30,
    )

    assert calls == [(draft, 30)]


def test_critic_rejected_signature_skip_blocks_exact_concrete_repeat() -> None:
    draft = {
        "type": "numeric_trial",
        "surface": "think_harder",
        "params": {"think_harder.min_expected_roi": 0.05},
    }
    sig = autopilot._action_signature(draft)
    state = {
        "critic_rejected_signatures": {
            sig: {"trial_id": 44, "reason": "critic rejected: unsupported claim"}
        }
    }

    result = autopilot._critic_rejected_signature_skip(draft, state)

    assert isinstance(result, actions.SkipOutcome)
    assert result.status == "invalid"
    assert "trial 44" in result.reason
    assert "change a material field" in result.reason
    assert result.action_type == "numeric_trial"


def test_critic_rejected_signature_skip_allows_empty_numeric_optuna_request() -> None:
    draft = {"type": "numeric_trial", "surface": "think_harder", "params": {}}
    state = {
        "critic_rejected_signatures": {
            autopilot._action_signature(draft): {
                "trial_id": 44,
                "reason": "critic rejected",
            }
        }
    }

    assert autopilot._critic_rejected_signature_skip(draft, state) is None


def test_critic_rejected_signature_skip_allows_observational_deep_eval() -> None:
    draft = {"type": "deep_eval", "tier": 3}
    state = {
        "critic_rejected_signatures": {
            autopilot._action_signature(draft): {
                "trial_id": 44,
                "reason": "critic rejected",
            }
        }
    }

    assert autopilot._critic_rejected_signature_skip(draft, state) is None


def test_critic_rejected_signature_skip_allows_material_change() -> None:
    rejected = {"type": "numeric_trial", "surface": "think_harder", "params": {}}
    retry = {
        "type": "numeric_trial",
        "surface": "think_harder",
        "params": {"think_harder.min_expected_roi": 0.05},
    }
    state = {
        "critic_rejected_signatures": {
            autopilot._action_signature(rejected): {
                "trial_id": 44,
                "reason": "critic rejected",
            }
        }
    }

    assert autopilot._critic_rejected_signature_skip(retry, state) is None


# ----- ActionContext bundle -----


def test_action_context_is_dataclass() -> None:
    ctx = actions._ActionContext(
        seeder="s",
        swarm="sw",
        forge="f",
        lab="l",
        tower="t",
        gate="g",
        archive="a",
        journal="j",
        state={},
    )
    assert ctx.seeder == "s"
    assert ctx.strategy_store is None
    assert ctx.evo is None
