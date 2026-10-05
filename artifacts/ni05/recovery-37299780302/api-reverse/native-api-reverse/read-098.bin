from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "autopilot"))

import autopilot  # type: ignore[import-not-found]  # noqa: E402
from experiment_journal import ExperimentJournal, JournalEntry  # noqa: E402
from safety_gate import EvalResult, SafetyGate  # type: ignore[import-not-found]  # noqa: E402
from src.autopilot_core.authority_consent import (  # noqa: E402
    SEQ_P0_2_BRIDGE_CONSENT,
    SEQ_P0_2_BRIDGE_ENV,
    SEQ_P0_2_BRIDGE_MODE,
)


def _enable_seq_p0_2_bridge(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    grant = tmp_path / "authority_consent.json"
    grant.write_text(json.dumps({SEQ_P0_2_BRIDGE_CONSENT: "allow"}), encoding="utf-8")
    monkeypatch.setenv("AUTOPILOT_AUTHORITY_CONSENT_PATH", str(grant))
    monkeypatch.setenv(SEQ_P0_2_BRIDGE_ENV, "1")


def test_eval_progress_callback_refreshes_dispatch_heartbeat() -> None:
    calls: list[tuple[str, dict[str, Any]]] = []
    prompts: list[str] = []

    class FakePhase:
        def set(self, phase: str, **fields: Any) -> dict[str, Any]:
            calls.append((phase, fields))
            return {}

    class FakeTui:
        def set_prompt(self, prompt: str) -> None:
            prompts.append(prompt)

    action = {"type": "numeric_trial"}
    callback = autopilot._make_eval_progress_callback(
        phase=FakePhase(),  # type: ignore[arg-type]
        tui=FakeTui(),  # type: ignore[arg-type]
        trial_id=lambda: 895,
        action=lambda: action,
    )

    callback("question prompt")

    assert prompts == ["question prompt"]
    assert calls == [
        (
            "dispatch_action",
            {
                "trial_id": 895,
                "action_type": "numeric_trial",
                "idle_reason": "evaluating question",
                "prompt_preview": "question prompt",
            },
        )
    ]


def test_eval_batch_progress_callback_refreshes_dispatch_heartbeat() -> None:
    calls: list[tuple[str, dict[str, Any]]] = []

    class FakePhase:
        def set(self, phase: str, **fields: Any) -> dict[str, Any]:
            calls.append((phase, fields))
            return {}

    action = {"type": "deep_eval"}
    callback = autopilot._make_eval_batch_progress_callback(
        phase=FakePhase(),  # type: ignore[arg-type]
        trial_id=lambda: 902,
        action=lambda: action,
    )

    callback(
        {
            "label": "T2",
            "completed_questions": 200,
            "total_questions": 500,
            "correct_questions": 144,
            "correct_pct": 72.0,
            "concurrency": 1,
        }
    )

    assert calls == [
        (
            "dispatch_action",
            {
                "trial_id": 902,
                "action_type": "deep_eval",
                "idle_reason": "evaluating question",
                "eval_label": "T2",
                "eval_completed_questions": 200,
                "eval_total_questions": 500,
                "eval_correct_questions": 144,
                "eval_correct_pct": 72.0,
                "eval_concurrency": 1,
            },
        )
    ]


def _entry(
    trial_id: int,
    action: dict,
    *,
    tier: int = 1,
    correct: bool = True,
    seq: dict | None = None,
    corrupt: str = "",
    outcome_status: str = "ok",
    timestamp: str = "2026-06-18T00:00:00Z",
    eval_details_extra: dict | None = None,
    keep_revert_decision: str = "",
    failure_analysis: str = "",
    pareto_status: str = "candidate",
) -> JournalEntry:
    eval_details = {
        "eval_wall_s": 1800.0,
        "question_results": [{"qid": "q1", "correct": correct}],
    }
    if eval_details_extra:
        eval_details.update(eval_details_extra)
    return JournalEntry(
        trial_id=trial_id,
        timestamp=timestamp,
        species="test",
        action_type=str(action.get("type") or "seed_batch"),
        tier=tier,
        quality=3.0 if correct else 0.0,
        speed=10.0,
        cost=0.2,
        reliability=1.0,
        pareto_status=pareto_status,
        config_snapshot=dict(action),
        failure_analysis=failure_analysis,
        eval_details=eval_details,
        seq=seq or {},
        bug_corrupted_by=corrupt,
        outcome_status=outcome_status,
        keep_revert_decision=keep_revert_decision,
    )


def test_update_contrastive_trace_state_labels_frontier_success() -> None:
    state: dict[str, Any] = {}

    class FakeTower:
        update_contrastive_trace_bank = staticmethod(
            autopilot.EvalTower.update_contrastive_trace_bank
        )

        def capture_contrastive_traces(self, **kwargs):
            return autopilot.EvalTower().capture_contrastive_traces(**kwargs)

        build_critic_trace_ir = staticmethod(autopilot.EvalTower.build_critic_trace_ir)
        format_critic_trace_ir = staticmethod(autopilot.EvalTower.format_critic_trace_ir)

    autopilot._update_contrastive_trace_state(
        state,
        FakeTower(),
        trace_text="ROLE=worker_general\nRESPONSE:\nok",
        trial_id=21,
        species="prompt_forge",
        action_type="prompt_mutation",
        pareto_status="frontier",
        verdict=SimpleNamespace(passed=True),
        eval_result=SimpleNamespace(tier=1, quality=2.2, speed=33.0),
    )

    assert state["contrastive_trace_bank"][0]["outcome"] == "success"
    assert state["contrastive_trace_bank"][0]["trial_id"] == 21
    assert "## Contrastive Execution Traces" in state["contrastive_traces"]
    assert state["critic_trace_ir"]["schema_version"] == "harness_trace_ir.v1"
    assert state["critic_trace_ir"]["trace_examples"][0]["outcome"] == "success"
    assert "## Harness Trace IR (MH-11 observe-only)" in state["critic_trace_ir_prompt"]


def test_update_contrastive_trace_state_skips_bug_corrupted_rows() -> None:
    state: dict[str, Any] = {}

    class FakeTower:
        def update_contrastive_trace_bank(self, *args, **kwargs):  # pragma: no cover
            raise AssertionError("bug-corrupted trace should not be stored")

    autopilot._update_contrastive_trace_state(
        state,
        FakeTower(),
        trace_text="ROLE=worker_general\nRESPONSE:\npartial",
        trial_id=22,
        species="prompt_forge",
        action_type="prompt_mutation",
        pareto_status="dominated",
        verdict=SimpleNamespace(passed=False),
        bug_corrupted_by="resource_contention",
        failure_analysis="Excluded reload",
    )

    assert "contrastive_trace_bank" not in state


def test_seq_inputs_use_trusted_same_tier_prior_rows(tmp_path: Path) -> None:
    # B4 / SEQ-1: the null profile is built ONLY from incumbent-representative trials
    # (pareto_status == "frontier" or keep_revert_decision == "keep"), and it needs at
    # least SEQ_BASELINE_PROFILE_MIN_TRIALS of them. Three frontier rows qualify; the
    # corrupt / skipped / wrong-tier rows are still excluded by the pre-existing filters.
    action = {"type": "seed_batch", "n_questions": 10}
    candidate = autopilot._config_fingerprint(action)
    journal = ExperimentJournal(journal_dir=tmp_path)
    journal.record(_entry(1, action, correct=True, pareto_status="frontier"))
    journal.record(
        _entry(
            2,
            action,
            correct=False,
            pareto_status="frontier",
            seq={
                "candidate": candidate,
                "core_id": "core_v1",
                "z": 0.25,
                "z_rate": 0.1,
                "state": "accumulating",
                "policy_version": "seq-v1",
            },
        )
    )
    journal.record(_entry(6, action, correct=True, keep_revert_decision="keep"))
    journal.record(_entry(3, action, correct=True, corrupt="resource_contention"))
    journal.record(_entry(4, action, correct=True, outcome_status="skipped"))
    journal.record(_entry(5, action, tier=2, correct=True))

    inputs = autopilot._seq_inputs_for_trial(journal=journal, action=action, tier=1)

    assert inputs["candidate"] == candidate
    assert inputs["core_id"] == "core_v1"
    # q1 correctness across the 3 qualifying rows: [True, False, True] -> mean 2/3.
    assert inputs["baseline_profile"] == {"q1": pytest.approx(2 / 3)}
    assert inputs["baseline_task_rate"] == pytest.approx(2.0)
    assert inputs["prior_quality_obs"] == [(2, 0.25)]
    assert inputs["prior_rate_obs"] == [(2, 0.1)]
    assert inputs["baseline_reference"]["due"] is True


def test_seq_null_profile_excludes_non_incumbent_config_changes(tmp_path: Path) -> None:
    # B4 / SEQ-1: a dominated/unpromoted experiment (pareto_status != frontier and NOT
    # kept) must be dropped from the null profile even though it is a trusted (non-corrupt,
    # non-skipped, same-tier) same-tier row — otherwise its depressed outcomes contaminate
    # the mixture and accrue e-process wealth anti-conservatively. Here only the 3 frontier
    # rows (all correct) survive, so the profile is a clean {"q1": 1.0}, NOT pulled down by
    # the three dominated wrong rows.
    action = {"type": "prompt_mutation", "file": "x"}
    journal = ExperimentJournal(journal_dir=tmp_path)
    for tid in (1, 2, 3):
        journal.record(_entry(tid, action, correct=True, pareto_status="frontier"))
    for tid in (4, 5, 6):
        journal.record(_entry(tid, action, correct=False, pareto_status="dominated"))

    inputs = autopilot._seq_inputs_for_trial(journal=journal, action=action, tier=1)

    assert inputs["baseline_profile"] == {"q1": pytest.approx(1.0)}


def test_seq_inputs_unavailable_when_too_few_incumbent_trials(tmp_path: Path) -> None:
    # B4 / SEQ-1: below SEQ_BASELINE_PROFILE_MIN_TRIALS incumbent-representative trials
    # the null profile is treated as UNAVAILABLE (empty) so gate.check() skips the
    # sequential path and seq_confirmed resolves to None downstream — never a thin mixture.
    action = {"type": "prompt_mutation", "file": "y"}
    journal = ExperimentJournal(journal_dir=tmp_path)
    # Two frontier rows (qualify) + several dominated rows (excluded) => only 2 < min 3.
    journal.record(_entry(1, action, correct=True, pareto_status="frontier"))
    journal.record(_entry(2, action, correct=True, pareto_status="frontier"))
    for tid in (3, 4, 5):
        journal.record(_entry(tid, action, correct=True, pareto_status="dominated"))

    inputs = autopilot._seq_inputs_for_trial(journal=journal, action=action, tier=1)

    assert inputs["baseline_profile"] == {}
    assert inputs["baseline_task_rate"] is None


def test_seq_inputs_unavailable_on_fresh_journal(tmp_path: Path) -> None:
    # B4 / SEQ-1 + SEQ-2 precondition: a fresh (empty) journal yields no incumbent
    # profile => seq inputs unavailable. This is the state that drives seq_confirmed=None
    # and the gate's seq_inputs_unavailable promotion refusal.
    action = {"type": "seed_batch"}
    journal = ExperimentJournal(journal_dir=tmp_path)

    inputs = autopilot._seq_inputs_for_trial(journal=journal, action=action, tier=1)

    assert inputs["baseline_profile"] == {}
    assert inputs["baseline_task_rate"] is None


def test_log_baseline_update_result_surfaces_seq_inputs_unavailable(caplog) -> None:
    # B4 / SEQ-2: a promotion refused because the sequential inputs were unavailable
    # (seq_confirmed=None -> BaselineUpdateResult.seq_refused_reason ==
    # 'seq_inputs_unavailable') is surfaced DISTINCTLY, not as a generic 'baseline
    # update skipped' line. Mirrors the real gate object: the machine token rides on
    # seq_refused_reason while `reason` is the long human sentence.
    refusal = SimpleNamespace(
        updated=False,
        reason="sequential verdict UNAVAILABLE (no per-question evidence); REFUSED",
        seq_refused_reason="seq_inputs_unavailable",
        tier=2,
        previous_quality=2.0,
        new_quality=2.5,
    )
    with caplog.at_level(logging.INFO, logger="autopilot"):
        autopilot._log_baseline_update_result(41, refusal)

    assert "seq_inputs_unavailable" in caplog.text
    assert "SEQ-2" in caplog.text
    assert "baseline update skipped" not in caplog.text


def test_log_baseline_update_result_logs_promotion_and_generic_skip(caplog) -> None:
    # B4 / SEQ-2: the pre-existing 'auto-raised' and generic 'skipped' lines are preserved.
    with caplog.at_level(logging.INFO, logger="autopilot"):
        autopilot._log_baseline_update_result(
            7,
            SimpleNamespace(
                updated=True, reason="", tier=2, previous_quality=2.0, new_quality=2.5
            ),
        )
    assert "baseline auto-raised" in caplog.text

    caplog.clear()
    with caplog.at_level(logging.INFO, logger="autopilot"):
        autopilot._log_baseline_update_result(
            8,
            SimpleNamespace(
                updated=False,
                reason="not a monotonic same-tier improvement",
                tier=2,
                previous_quality=2.0,
                new_quality=1.9,
            ),
        )
    assert "baseline update skipped (not a monotonic same-tier improvement)" in caplog.text
    assert "SEQ-2" not in caplog.text


def test_seq_flag_on_fresh_journal_refuses_promotion_with_reason(tmp_path, monkeypatch) -> None:
    # B4 / SEQ-2 end-to-end contract: with the sequential flag ON and no confirmed/refuted
    # verdict (seq_confirmed=None, the state a fresh journal produces), update_baseline must
    # REFUSE the write and surface the seq_inputs_unavailable machine token — the anti-ratchet
    # the autopilot call site relies on. (Eligibility is stubbed so the seq gate is reached.)
    gate = SafetyGate(baseline_path=tmp_path / "absent.yaml", use_sequential=True)
    monkeypatch.setattr(gate, "_baseline_eligible", lambda result: (True, "test-eligible", {}))
    result = EvalResult(
        tier=2,
        quality=2.9,
        speed=99.0,
        cost=0.1,
        reliability=0.99,
        per_suite_quality={"coder": 2.9},
        n_questions=50,
        speed_metric_mode="aggregate_batch_tps",
    )

    res = gate.update_baseline(result, seq_confirmed=None)

    assert res.updated is False
    assert res.seq_refused_reason == "seq_inputs_unavailable"


def test_seq_paired_baseline_diagnostics_compares_latest_reference(
    tmp_path: Path,
) -> None:
    action = {"type": "seed_batch", "n_questions": 10}
    journal = ExperimentJournal(journal_dir=tmp_path)
    journal.record(
        _entry(
            1,
            action,
            eval_details_extra={
                "seq_baseline_reference_draw": True,
                "question_results": [
                    {"qid": "q1", "suite": "math", "correct": False},
                ],
            },
        )
    )
    journal.record(
        _entry(
            2,
            action,
            eval_details_extra={
                "seq_baseline_reference_draw": True,
                "seq_baseline_reference_reason": "cadence",
                "question_results": [
                    {"qid": "q1", "suite": "math", "correct": True},
                    {"qid": "q2", "suite": "math", "correct": False},
                    {"qid": "q3", "suite": "math", "correct": False},
                ],
            },
        )
    )

    diag = autopilot._seq_paired_baseline_diagnostics(
        journal=journal,
        tier=1,
        candidate="candidate-a",
        candidate_trial_id=20,
        question_results=[
            {"qid": "q1", "suite": "math", "correct": True},
            {"qid": "q2", "suite": "math", "correct": True},
            {"qid": "q4", "suite": "math", "correct": False},
        ],
    )

    assert diag["status"] == "ok"
    assert diag["used_for_gating"] is False
    assert diag["baseline_reference_trial_id"] == 2
    assert diag["baseline_reference_reason"] == "cadence"
    assert diag["candidate_trial_id"] == 20
    assert diag["shared_qids"] == 2
    assert diag["same_correct"] == 1
    assert diag["a_wrong_b_correct"] == 1
    assert diag["delta_b_minus_a"] == pytest.approx(0.5)
    assert diag["mcnemar_verdict"] == {
        "verdict": "indistinguishable",
        "method": "mcnemar",
        "approximation": "exact_binomial",
        "n_discordant": 1,
        "p_value": pytest.approx(1.0),
        "z": None,
        "alpha": 0.05,
        "exact_max_discordant": 25,
    }


def test_seq_paired_baseline_diagnostics_reports_missing_reference(
    tmp_path: Path,
) -> None:
    journal = ExperimentJournal(journal_dir=tmp_path)

    diag = autopilot._seq_paired_baseline_diagnostics(
        journal=journal,
        tier=1,
        candidate="candidate-a",
        candidate_trial_id=20,
        question_results=[{"qid": "q1", "suite": "math", "correct": True}],
    )

    assert diag == {
        "status": "no_baseline_reference_vector",
        "candidate": "candidate-a",
        "candidate_trial_id": 20,
        "candidate_vector_qids": 1,
        "used_for_gating": False,
    }


def test_seq_gate_preflight_blocks_rate_axis_unreachable_candidate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(autopilot, "SEQ_GATE_PREFLIGHT_MIN_SEQ_ROWS", 2)
    monkeypatch.setattr(autopilot, "SEQ_GATE_PREFLIGHT_RECENT_WINDOW", 2)
    monkeypatch.setattr(autopilot, "SEQ_GATE_PREFLIGHT_MAX_RATE_E", 2.0)
    journal = ExperimentJournal(journal_dir=tmp_path)
    base_action = {"type": "numeric_trial", "surface": "memrl_retrieval", "params": {"x": 1}}
    for trial_id, wall_s in enumerate([60.0, 60.0, 1800.0, 1800.0], start=1):
        journal.record(
            _entry(
                trial_id,
                {**base_action, "params": {"x": trial_id}},
                eval_details_extra={"eval_wall_s": wall_s},
                seq={
                    "candidate": f"candidate-{trial_id}",
                    "core_id": "core_v1",
                    "z": 0.1,
                    "z_rate": -0.9,
                    "E_quality": 2.0,
                    "E_rate_noninf": 1.05,
                    "state": "accumulating",
                    "policy_version": "seq-v1",
                },
            )
        )

    proposed = {"type": "numeric_trial", "surface": "new_surface", "params": {"x": 99}}
    action, rationale, payload = autopilot._maybe_defer_seq_unreachable_candidate_action(
        proposed,
        state={},
        journal=journal,
        blacklist=[],
        rationale={},
        trial_counter=10,
        tier=1,
        enabled=True,
    )

    assert payload is not None
    assert payload["status"] == "blocked_unreachable"
    assert payload["reason"] == "rate_axis_unreachable"
    assert payload["replacement_action"] is None
    assert action == proposed
    assert rationale == {}


def test_seq_gate_preflight_bridge_allows_rate_axis_advisory_candidate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _enable_seq_p0_2_bridge(monkeypatch, tmp_path)
    monkeypatch.setattr(autopilot, "SEQ_GATE_PREFLIGHT_MIN_SEQ_ROWS", 2)
    monkeypatch.setattr(autopilot, "SEQ_GATE_PREFLIGHT_RECENT_WINDOW", 2)
    monkeypatch.setattr(autopilot, "SEQ_GATE_PREFLIGHT_MAX_RATE_E", 2.0)
    journal = ExperimentJournal(journal_dir=tmp_path)
    base_action = {"type": "numeric_trial", "surface": "memrl_retrieval", "params": {"x": 1}}
    for trial_id, wall_s in enumerate([60.0, 60.0, 1800.0, 1800.0], start=1):
        journal.record(
            _entry(
                trial_id,
                {**base_action, "params": {"x": trial_id}},
                eval_details_extra={"eval_wall_s": wall_s},
                seq={
                    "candidate": f"candidate-{trial_id}",
                    "core_id": "core_v1",
                    "z": 0.1,
                    "z_rate": -0.9,
                    "E_quality": 2.0,
                    "E_rate_noninf": 1.05,
                    "state": "accumulating",
                    "policy_version": "seq-v1",
                },
            )
        )
    state: dict[str, Any] = {}
    proposed = {"type": "numeric_trial", "surface": "new_surface", "params": {"x": 99}}

    action, rationale, payload = autopilot._maybe_defer_seq_unreachable_candidate_action(
        proposed,
        state=state,
        journal=journal,
        blacklist=[],
        rationale={},
        trial_counter=10,
        tier=1,
        enabled=True,
    )

    assert payload is None
    assert action == proposed
    assert rationale == {}
    preflight = state["seq_gate_reachability_preflight"]
    assert preflight["status"] == "passed"
    assert preflight["reachability"]["status"] == "rate_axis_advisory_bridge"
    assert preflight["reachability"]["rate_axis_mode"] == SEQ_P0_2_BRIDGE_MODE
    assert preflight["reachability"]["rate_axis_binding"] is False


def test_seq_gate_preflight_does_not_use_retryable_seed_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(autopilot, "SEQ_GATE_PREFLIGHT_MIN_SEQ_ROWS", 2)
    monkeypatch.setattr(autopilot, "SEQ_GATE_PREFLIGHT_RECENT_WINDOW", 2)
    monkeypatch.setattr(autopilot, "SEQ_GATE_PREFLIGHT_MAX_RATE_E", 2.0)
    journal = ExperimentJournal(journal_dir=tmp_path)
    base_action = {"type": "numeric_trial", "surface": "memrl_retrieval", "params": {"x": 1}}
    for trial_id, wall_s in enumerate([60.0, 60.0, 1800.0, 1800.0], start=1):
        journal.record(
            _entry(
                trial_id,
                {**base_action, "params": {"x": trial_id}},
                eval_details_extra={"eval_wall_s": wall_s},
                seq={
                    "candidate": f"candidate-{trial_id}",
                    "core_id": "core_v1",
                    "z": 0.1,
                    "z_rate": -0.9,
                    "E_quality": 2.0,
                    "E_rate_noninf": 1.05,
                    "state": "accumulating",
                    "policy_version": "seq-v1",
                },
            )
        )
    blacklist = [
        {
            "pattern": {"type": "seed_batch", "n_questions": n_questions},
            "reason": f"blocked {n_questions}",
        }
        for n_questions in (14, 16, 18, 20, 24, 30, 40)
    ]
    blacklist.append(
        {
            "pattern": {"type": "seed_batch", "n_questions": 50},
            "reason": "Auto-blacklisted: 3 consecutive failures ending at trial 1317",
            "source_trial": 1317,
        }
    )

    proposed = {"type": "numeric_trial", "surface": "new_surface", "params": {"x": 99}}
    action, rationale, payload = autopilot._maybe_defer_seq_unreachable_candidate_action(
        proposed,
        state={},
        journal=journal,
        blacklist=blacklist,
        rationale={},
        trial_counter=10,
        tier=1,
        enabled=True,
    )

    assert payload is not None
    assert payload["status"] == "blocked_unreachable"
    assert payload["reason"] == "rate_axis_unreachable"
    assert payload["replacement_action"] is None
    assert payload["retryable_blacklist_target"] is None
    assert action == proposed
    assert rationale == {}


def test_seq_gate_preflight_blocks_alpha_exhausted_new_candidate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(autopilot, "SEQ_GATE_PREFLIGHT_MIN_SEQ_ROWS", 1000)
    journal = ExperimentJournal(journal_dir=tmp_path)
    for trial_id in range(1, 23):
        journal.record(
            _entry(
                trial_id,
                {"type": "numeric_trial", "surface": "memrl_retrieval", "params": {"x": trial_id}},
                seq={
                    "candidate": f"candidate-{trial_id}",
                    "core_id": "core_v1",
                    "z": 0.1,
                    "z_rate": 0.1,
                    "E_quality": 1.2,
                    "E_rate_noninf": 1.2,
                    "state": "accumulating",
                    "policy_version": "seq-v1",
                },
            )
        )

    proposed = {"type": "prompt_mutation", "file": "frontdoor.md", "mutation": "new"}
    action, rationale, payload = autopilot._maybe_defer_seq_unreachable_candidate_action(
        proposed,
        state={},
        journal=journal,
        blacklist=[],
        rationale={},
        trial_counter=30,
        tier=1,
        enabled=True,
    )

    assert payload is not None
    assert payload["status"] == "blocked_unreachable"
    assert payload["reason"] == "alpha_wealth_exhausted"
    assert payload["alpha_wealth"]["new_fingerprint_confirmations_allowed"] is False
    assert payload["replacement_action"] is None
    assert action == proposed
    assert rationale == {}


def test_seq_gate_preflight_bridge_reprices_alpha_at_confirmation_stage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _enable_seq_p0_2_bridge(monkeypatch, tmp_path)
    monkeypatch.setattr(autopilot, "SEQ_GATE_PREFLIGHT_MIN_SEQ_ROWS", 1000)
    journal = ExperimentJournal(journal_dir=tmp_path)
    for trial_id in range(1, 23):
        journal.record(
            _entry(
                trial_id,
                {"type": "numeric_trial", "surface": "memrl_retrieval", "params": {"x": trial_id}},
                seq={
                    "candidate": f"candidate-{trial_id}",
                    "core_id": "core_v1",
                    "z": 0.1,
                    "z_rate": 0.1,
                    "E_quality": 1.2,
                    "E_rate_noninf": 1.2,
                    "state": "accumulating",
                    "confirmed": False,
                    "policy_version": "seq-v1",
                },
            )
        )

    proposed = {"type": "prompt_mutation", "file": "frontdoor.md", "mutation": "new"}
    action, rationale, payload = autopilot._maybe_defer_seq_unreachable_candidate_action(
        proposed,
        state={},
        journal=journal,
        blacklist=[],
        rationale={},
        trial_counter=30,
        tier=1,
        enabled=True,
    )

    assert payload is None
    assert action == proposed
    assert rationale == {}
    alpha = autopilot._seq_inputs_for_trial(journal=journal, action=proposed, tier=1)[
        "alpha_wealth"
    ]
    assert alpha["alpha_wealth_mode"] == "confirmed_fresh_eval_stage"
    assert alpha["fingerprints_tested"] == 22
    assert alpha["fingerprints_charged"] == 0
    assert alpha["legacy_tested_fingerprint_alpha_spent"] > alpha["budget"]
    assert alpha["new_fingerprint_dispatch_allowed"] is True
    assert alpha["new_fingerprint_confirmations_allowed"] is True


def test_seq_alpha_bridge_still_blocks_when_confirmed_stage_budget_exhausted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _enable_seq_p0_2_bridge(monkeypatch, tmp_path)

    alpha = autopilot._seq_alpha_wealth_state(
        {f"candidate-{idx}" for idx in range(25)},
        candidate="candidate-new",
        confirmed_candidates={f"candidate-{idx}" for idx in range(20)},
    )

    assert alpha["alpha_wealth_mode"] == "confirmed_fresh_eval_stage"
    assert alpha["fingerprints_charged"] == 20
    assert alpha["budget_exhausted"] is True
    assert alpha["new_fingerprint_confirmations_allowed"] is False
    assert alpha["new_fingerprint_dispatch_allowed"] is False


def test_seq_gate_preflight_dispatch_block_reason() -> None:
    assert (
        autopilot._seq_gate_preflight_dispatch_block_reason(
            {"status": "blocked_unreachable", "reason": "alpha_wealth_exhausted"}
        )
        == "seq_gate_preflight_alpha_wealth_exhausted"
    )
    assert (
        autopilot._seq_gate_preflight_dispatch_block_reason(
            {"status": "deferred", "reason": "rate_axis_unreachable"}
        )
        == ""
    )


def test_seq_baseline_reference_state_tracks_cadence_and_staleness(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(autopilot, "SEQ_BASELINE_REFRESH_CADENCE", 2)
    monkeypatch.setattr(autopilot, "SEQ_BASELINE_REFERENCE_STALE_AFTER_S", 3600.0)
    action = {"type": "seed_batch", "n_questions": 12}
    journal = ExperimentJournal(journal_dir=tmp_path)
    journal.record(
        _entry(
            1,
            action,
            timestamp="2026-06-18T00:00:00Z",
            eval_details_extra={"seq_baseline_reference_draw": True},
        )
    )
    journal.record(_entry(2, action, timestamp="2026-06-18T00:10:00Z"))

    fresh = autopilot._seq_baseline_reference_state(
        journal,
        tier=1,
        now_ts=autopilot._parse_journal_timestamp("2026-06-18T00:20:00Z"),
    )

    assert fresh["due"] is False
    assert fresh["stale_reference"] is False
    assert fresh["trials_since_reference"] == 1

    journal.record(_entry(3, action, timestamp="2026-06-18T00:30:00Z"))
    cadence_due = autopilot._seq_baseline_reference_state(
        journal,
        tier=1,
        now_ts=autopilot._parse_journal_timestamp("2026-06-18T00:40:00Z"),
    )
    assert cadence_due["due"] is True
    assert cadence_due["trials_since_reference"] == 2
    assert "trusted profile trials" in cadence_due["reason"]

    stale = autopilot._seq_baseline_reference_state(
        journal,
        tier=1,
        now_ts=autopilot._parse_journal_timestamp("2026-06-18T02:30:01Z"),
    )
    assert stale["due"] is True
    assert stale["stale_reference"] is True


def test_seq_candidate_replay_payload_selects_replayable_accumulating_candidate(
    tmp_path: Path,
) -> None:
    action = {
        "type": "numeric_trial",
        "surface": "repl_budget",
        "params": {"repl.worker_call_budget_cap": 31},
    }
    candidate = autopilot._config_fingerprint(action)
    journal = ExperimentJournal(journal_dir=tmp_path)
    journal.record(
        _entry(
            10,
            action,
            seq={
                "candidate": candidate,
                "core_id": "core_v1",
                "k": 1,
                "z": 0.1,
                "z_rate": -0.1,
                "E_quality": 1.02,
                "E_rate_noninf": 0.96,
                "state": "accumulating",
                "confirmed": False,
            },
        )
    )

    payload = autopilot._seq_candidate_replay_payload(journal, tier=1)

    assert payload == {
        "candidate": candidate,
        "source_trial_id": 10,
        "action": action,
        "k": 1,
        "combined_E": 0.96,
        "E_quality": 1.02,
        "E_rate_noninf": 0.96,
    }


def test_seq_candidate_replay_payload_skips_unreplayable_and_refuted_rows(
    tmp_path: Path,
) -> None:
    seed_action = {"type": "seed_batch", "n_questions": 18}
    numeric_action = {
        "type": "numeric_trial",
        "surface": "repl_budget",
        "params": {"repl.worker_call_budget_cap": 31},
    }
    journal = ExperimentJournal(journal_dir=tmp_path)
    journal.record(
        _entry(
            10,
            seed_action,
            seq={
                "candidate": autopilot._config_fingerprint(seed_action),
                "core_id": "core_v1",
                "k": 1,
                "z": 0.1,
                "z_rate": 0.1,
                "E_quality": 1.1,
                "E_rate_noninf": 1.1,
                "state": "accumulating",
            },
        )
    )
    journal.record(
        _entry(
            11,
            numeric_action,
            seq={
                "candidate": autopilot._config_fingerprint(numeric_action),
                "core_id": "core_v1",
                "k": 8,
                "z": 0.1,
                "z_rate": 0.1,
                "E_quality": 1.8,
                "E_rate_noninf": 0.96,
                "state": "refuted",
            },
        )
    )

    assert autopilot._seq_candidate_replay_payload(journal, tier=1) is None


def test_seq_candidate_replay_payload_uses_latest_candidate_state(
    tmp_path: Path,
) -> None:
    action = {
        "type": "numeric_trial",
        "surface": "repl_budget",
        "params": {"repl.worker_call_budget_cap": 31},
    }
    candidate = autopilot._config_fingerprint(action)
    journal = ExperimentJournal(journal_dir=tmp_path)
    journal.record(
        _entry(
            10,
            action,
            seq={
                "candidate": candidate,
                "core_id": "core_v1",
                "k": 1,
                "z": 0.1,
                "z_rate": -0.1,
                "E_quality": 1.02,
                "E_rate_noninf": 0.96,
                "state": "accumulating",
            },
        )
    )
    journal.record(
        _entry(
            11,
            action,
            seq={
                "candidate": candidate,
                "core_id": "core_v1",
                "k": 2,
                "z": -0.8,
                "z_rate": -0.8,
                "E_quality": 0.04,
                "E_rate_noninf": 0.04,
                "state": "refuted",
            },
        )
    )

    assert autopilot._seq_candidate_replay_payload(journal, tier=1) is None


def test_seq_candidate_replay_payload_skips_latest_reverted_candidate(
    tmp_path: Path,
) -> None:
    action = {
        "type": "numeric_trial",
        "surface": "repl_budget",
        "params": {"repl.worker_call_budget_cap": 31},
    }
    candidate = autopilot._config_fingerprint(action)
    journal = ExperimentJournal(journal_dir=tmp_path)
    seq = {
        "candidate": candidate,
        "core_id": "core_v1",
        "k": 1,
        "z": 0.1,
        "z_rate": -0.1,
        "E_quality": 1.02,
        "E_rate_noninf": 0.96,
        "state": "accumulating",
    }
    journal.record(
        _entry(
            10,
            action,
            seq=seq,
            keep_revert_decision="keep",
        )
    )
    journal.record(
        _entry(
            11,
            action,
            seq={**seq, "k": 2},
            keep_revert_decision="revert",
        )
    )

    assert autopilot._seq_candidate_replay_payload(journal, tier=1) is None


def test_seq_candidate_replay_payload_allows_benign_excluded_accumulating_candidate(
    tmp_path: Path,
) -> None:
    action = {
        "type": "numeric_trial",
        "surface": "repl_budget",
        "params": {"repl.worker_call_budget_cap": 31},
    }
    candidate = autopilot._config_fingerprint(action)
    journal = ExperimentJournal(journal_dir=tmp_path)
    seq = {
        "candidate": candidate,
        "core_id": "core_v1",
        "k": 2,
        "z": 0.1,
        "z_rate": -0.1,
        "E_quality": 1.02,
        "E_rate_noninf": 0.96,
        "state": "accumulating",
        "confirmed": False,
    }
    journal.record(
        _entry(
            10,
            action,
            seq=seq,
            keep_revert_decision="keep",
        )
    )
    journal.record(
        _entry(
            11,
            action,
            seq={**seq, "k": 3},
            keep_revert_decision="excluded",
        )
    )

    payload = autopilot._seq_candidate_replay_payload(journal, tier=1)

    assert payload is not None
    assert payload["candidate"] == candidate
    assert payload["source_trial_id"] == 11
    assert payload["k"] == 3


def test_seq_candidate_replay_payload_skips_terminal_excluded_candidate(
    tmp_path: Path,
) -> None:
    action = {
        "type": "numeric_trial",
        "surface": "repl_budget",
        "params": {"repl.worker_call_budget_cap": 31},
    }
    candidate = autopilot._config_fingerprint(action)
    journal = ExperimentJournal(journal_dir=tmp_path)
    journal.record(
        _entry(
            10,
            action,
            seq={
                "candidate": candidate,
                "core_id": "core_v1",
                "k": 1,
                "z": 0.1,
                "z_rate": -0.1,
                "E_quality": 1.02,
                "E_rate_noninf": 0.96,
                "state": "accumulating",
                "confirmed": False,
            },
            keep_revert_decision="excluded",
            failure_analysis="VIOLATIONS:\n  - Suite 'general' regression",
        )
    )

    assert autopilot._seq_candidate_replay_payload(journal, tier=1) is None


def test_seq_candidate_replay_payload_requires_neutral_quality_e(
    tmp_path: Path,
) -> None:
    action = {
        "type": "numeric_trial",
        "surface": "repl_budget",
        "params": {"repl.worker_call_budget_cap": 31},
    }
    journal = ExperimentJournal(journal_dir=tmp_path)
    journal.record(
        _entry(
            10,
            action,
            seq={
                "candidate": autopilot._config_fingerprint(action),
                "core_id": "core_v1",
                "k": 1,
                "z": -0.01,
                "z_rate": -0.1,
                "E_quality": 0.99,
                "E_rate_noninf": 0.96,
                "state": "accumulating",
            },
        )
    )

    # 2026-08-04: WITHIN the grace period (k=1 < SEQ_CANDIDATE_REPLAY_MIN_K) a
    # sub-neutral E is NOT evidence the candidate is dead — it is one noisy sample.
    # This test previously asserted the opposite, and that assertion WAS the defect:
    # measured over the journal, 89 of 141 candidates were stranded at k=1 with a
    # median E_quality of 0.999 against this 1.0 filter, which is why `confirmed` was
    # 0 in 396 trials. An e-process cannot clear any bar at k=1.
    payload = autopilot._seq_candidate_replay_payload(journal, tier=1)
    assert payload is not None, "a k=1 candidate must be replayed, not judged on one sample"
    assert payload["k"] == 1

    # ABOVE the grace period the filter still bites — the point is to delay the
    # judgement until it means something, not to remove it.
    journal_mature = ExperimentJournal(journal_dir=tmp_path / "mature")
    journal_mature.record(
        _entry(
            11,
            action,
            seq={
                "candidate": autopilot._config_fingerprint(action),
                "core_id": "core_v1",
                "k": autopilot.SEQ_CANDIDATE_REPLAY_MIN_K + 1,
                "z": -0.01,
                "z_rate": -0.1,
                "E_quality": 0.99,
                "E_rate_noninf": 0.96,
                "state": "accumulating",
            },
        )
    )
    assert autopilot._seq_candidate_replay_payload(journal_mature, tier=1) is None


def test_seq_candidate_replay_payload_allows_materialized_numeric_replay(
    tmp_path: Path,
) -> None:
    optuna_action = {
        "type": "numeric_trial",
        "surface": "repl_executor",
        "params": {
            "repl.turn_token_cap": 3684,
            "repl.frontdoor_non_tool_token_cap": 1988,
        },
    }
    valid_action = {
        "type": "numeric_trial",
        "surface": "repl_budget",
        "params": {"repl.worker_call_budget_cap": 31},
    }
    journal = ExperimentJournal(journal_dir=tmp_path)
    journal.record(
        _entry(
            10,
            optuna_action,
            seq={
                "candidate": autopilot._config_fingerprint(optuna_action),
                "core_id": "core_v1",
                "k": 1,
                "z": 0.2,
                "z_rate": -0.1,
                "E_quality": 1.4,
                "E_rate_noninf": 1.2,
                "state": "accumulating",
            },
        )
    )
    journal.record(
        _entry(
            11,
            valid_action,
            seq={
                "candidate": autopilot._config_fingerprint(valid_action),
                "core_id": "core_v1",
                "k": 1,
                "z": 0.1,
                "z_rate": -0.1,
                "E_quality": 1.02,
                "E_rate_noninf": 0.96,
                "state": "accumulating",
            },
        )
    )

    payload = autopilot._seq_candidate_replay_payload(journal, tier=1)

    assert payload is not None
    assert payload["action"] == optuna_action


def test_seq_candidate_replay_payload_prefers_under_observed_candidate(
    tmp_path: Path,
) -> None:
    concentrated_action = {
        "type": "numeric_trial",
        "surface": "repl_budget",
        "params": {"repl.worker_call_budget_cap": 31},
    }
    under_observed_action = {
        "type": "numeric_trial",
        "surface": "repl_budget",
        "params": {"repl.worker_call_budget_cap": 35},
    }
    journal = ExperimentJournal(journal_dir=tmp_path)
    journal.record(
        _entry(
            20,
            concentrated_action,
            seq={
                "candidate": autopilot._config_fingerprint(concentrated_action),
                "core_id": "core_v1",
                "k": 7,
                "z": 0.1,
                "z_rate": -0.1,
                "E_quality": 1.4,
                "E_rate_noninf": 0.98,
                "state": "accumulating",
                "confirmed": False,
            },
        )
    )
    journal.record(
        _entry(
            21,
            under_observed_action,
            seq={
                "candidate": autopilot._config_fingerprint(under_observed_action),
                "core_id": "core_v1",
                "k": 1,
                "z": 0.1,
                "z_rate": -0.1,
                "E_quality": 1.02,
                "E_rate_noninf": 0.96,
                "state": "accumulating",
                "confirmed": False,
            },
        )
    )

    payload = autopilot._seq_candidate_replay_payload(journal, tier=1)

    assert payload is not None
    assert payload["action"] == under_observed_action
    assert payload["k"] == 1


def test_maybe_force_seq_candidate_replay_respects_blacklist(tmp_path: Path) -> None:
    action = {
        "type": "numeric_trial",
        "surface": "repl_budget",
        "params": {"repl.worker_call_budget_cap": 31},
    }
    candidate = autopilot._config_fingerprint(action)
    journal = ExperimentJournal(journal_dir=tmp_path)
    journal.record(
        _entry(
            10,
            action,
            seq={
                "candidate": candidate,
                "core_id": "core_v1",
                "k": 1,
                "z": 0.1,
                "z_rate": -0.1,
                "E_quality": 1.02,
                "E_rate_noninf": 0.96,
                "state": "accumulating",
                "confirmed": False,
            },
        )
    )
    state: dict[str, Any] = {}
    blacklist = [{"pattern": action, "reason": "blocked replay"}]

    forced, rationale, payload = autopilot._maybe_force_seq_candidate_replay(
        {"type": "seed_batch", "n_questions": 14},
        state=state,
        journal=journal,
        tier=1,
        blacklist=blacklist,
        rationale=None,
        trial_counter=20,
        enabled=True,
    )

    assert forced == {"type": "seed_batch", "n_questions": 14}
    assert rationale is None
    assert payload is None
    assert state["seq_candidate_replay_blocked"]["candidate"] == candidate
    assert state["seq_candidate_replay_blocked"]["reason"] == "blocked replay"


def test_maybe_force_seq_candidate_replay_forces_action_and_rationale(
    tmp_path: Path,
) -> None:
    action = {
        "type": "numeric_trial",
        "surface": "repl_budget",
        "params": {"repl.worker_call_budget_cap": 31},
    }
    candidate = autopilot._config_fingerprint(action)
    journal = ExperimentJournal(journal_dir=tmp_path)
    journal.record(
        _entry(
            10,
            action,
            seq={
                "candidate": candidate,
                "core_id": "core_v1",
                "k": 1,
                "z": 0.1,
                "z_rate": -0.1,
                "E_quality": 1.02,
                "E_rate_noninf": 0.96,
                "state": "accumulating",
                "confirmed": False,
            },
        )
    )
    state: dict[str, Any] = {}

    forced, rationale, payload = autopilot._maybe_force_seq_candidate_replay(
        {"type": "seed_batch", "n_questions": 14},
        state=state,
        journal=journal,
        tier=1,
        blacklist=[],
        rationale={"planner": "kept"},
        trial_counter=20,
        enabled=True,
    )

    assert forced == action
    assert payload is not None
    assert rationale == {
        "planner": "kept",
        "seq_candidate_replay": True,
        "seq_candidate": candidate,
        "seq_candidate_source_trial_id": 10,
    }
    assert state["seq_candidate_replay_forced"]["candidate"] == candidate
    assert state["seq_candidate_replay_forced"]["action"] == action


def test_maybe_force_seq_candidate_replay_blocks_noop_structural_candidate(
    tmp_path: Path,
) -> None:
    action = {
        "type": "structural_experiment",
        "flags": {"langgraph_coder": False},
    }
    candidate = autopilot._config_fingerprint(action)
    journal = ExperimentJournal(journal_dir=tmp_path)
    journal.record(
        _entry(
            10,
            action,
            seq={
                "candidate": candidate,
                "core_id": "core_v1",
                "k": 1,
                "z": 0.1,
                "z_rate": -0.1,
                "E_quality": 1.02,
                "E_rate_noninf": 0.96,
                "state": "accumulating",
                "confirmed": False,
            },
        )
    )
    state: dict[str, Any] = {}
    lab = SimpleNamespace(current_flags=lambda: {"langgraph_coder": False})
    original = {"type": "seed_batch", "n_questions": 14}

    forced, rationale, payload = autopilot._maybe_force_seq_candidate_replay(
        original,
        state=state,
        journal=journal,
        tier=1,
        blacklist=[],
        rationale={"planner": "kept"},
        trial_counter=20,
        enabled=True,
        lab=lab,
    )

    assert forced == original
    assert rationale == {"planner": "kept"}
    assert payload is None
    assert state["seq_candidate_replay_blocked"]["candidate"] == candidate
    assert (
        state["seq_candidate_replay_blocked"]["reason"]
        == "structural_experiment would not change live flag state: langgraph_coder=false"
    )
    assert "seq_candidate_replay_forced" not in state


def test_maybe_force_seq_baseline_draw_marks_rationale_and_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(autopilot, "SEQ_BASELINE_REFRESH_CADENCE", 10)
    journal = ExperimentJournal(journal_dir=tmp_path)
    action = {"type": "noop"}
    state: dict = {}

    forced, rationale, reference = autopilot._maybe_force_seq_baseline_draw(
        action,
        state=state,
        journal=journal,
        tier=1,
        blacklist=[],
        rationale={"source": "test"},
        trial_counter=8,
        enabled=True,
    )

    assert forced == {"type": "seed_batch", "n_questions": 14}
    assert rationale == {
        "source": "test",
        "seq_baseline_reference_draw": True,
        "seq_baseline_reference_reason": "no marked seq baseline-reference draw",
    }
    assert reference is not None
    assert state["seq_baseline_draw_forced"]["trial_id"] == 8


def test_maybe_force_seq_baseline_draw_uses_alternate_when_default_blacklisted(
    tmp_path: Path,
) -> None:
    journal = ExperimentJournal(journal_dir=tmp_path)
    action = {"type": "noop"}
    state: dict = {}

    forced, rationale, reference = autopilot._maybe_force_seq_baseline_draw(
        action,
        state=state,
        journal=journal,
        tier=1,
        blacklist=[{"pattern": {"type": "seed_batch", "n_questions": 14}, "reason": "test"}],
        rationale=None,
        trial_counter=9,
        enabled=True,
    )

    assert forced == {"type": "seed_batch", "n_questions": 16}
    assert rationale == {
        "seq_baseline_reference_draw": True,
        "seq_baseline_reference_reason": "no marked seq baseline-reference draw",
    }
    assert reference is not None
    assert state["seq_baseline_draw_forced"]["action"] == forced


def test_maybe_force_seq_baseline_draw_uses_retryable_infra_seed(
    tmp_path: Path,
) -> None:
    journal = ExperimentJournal(journal_dir=tmp_path)
    action = {"type": "noop"}
    state: dict = {}
    blacklist = [
        {
            "pattern": {"type": "seed_batch", "n_questions": n_questions},
            "reason": f"blocked {n_questions}",
        }
        for n_questions in (14, 16, 18, 20, 24, 30, 40)
    ]
    blacklist.append(
        {
            "pattern": {"type": "seed_batch", "n_questions": 50},
            "reason": "Auto-blacklisted: 3 consecutive failures ending at trial 1317",
            "source_trial": 1317,
        }
    )

    forced, rationale, reference = autopilot._maybe_force_seq_baseline_draw(
        action,
        state=state,
        journal=journal,
        tier=1,
        blacklist=blacklist,
        rationale=None,
        trial_counter=9,
        enabled=True,
    )

    assert forced == {"type": "seed_batch", "n_questions": 50}
    assert reference is not None
    assert rationale is not None
    assert rationale["seq_baseline_reference_draw"] is True
    assert rationale["seq_baseline_reference_retryable_blacklist"] is True
    assert (
        rationale["p0_3_blacklist_reexploration_target"]
        == "seed_batch_n50_t1317_no_progress_infra"
    )
    assert state["seq_baseline_draw_blocked"] is None
    assert state["seq_baseline_draw_forced"]["action"] == forced


def test_maybe_force_seq_baseline_draw_suppresses_recent_blocked_latch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(autopilot, "SEQ_BASELINE_BLOCK_RETRY_CADENCE", 5)
    journal = ExperimentJournal(journal_dir=tmp_path)
    action = {"type": "noop"}
    forced_default = {"type": "seed_batch", "n_questions": 14}
    state: dict = {
        "seq_baseline_draw_blocked": {
            "trial_id": 9,
            "action": forced_default,
            "reference_key": "tier=1:reference=none",
            "reason": "all seed fallbacks were blacklisted",
        }
    }

    forced, rationale, reference = autopilot._maybe_force_seq_baseline_draw(
        action,
        state=state,
        journal=journal,
        tier=1,
        blacklist=[{"pattern": forced_default, "reason": "default still blocked"}],
        rationale={"planner": "kept"},
        trial_counter=12,
        enabled=True,
    )

    assert forced == action
    assert rationale == {"planner": "kept"}
    assert reference is None
    assert state["seq_baseline_draw_blocked"]["trial_id"] == 9


def test_maybe_force_seq_baseline_draw_retries_old_blocked_latch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(autopilot, "SEQ_BASELINE_BLOCK_RETRY_CADENCE", 5)
    journal = ExperimentJournal(journal_dir=tmp_path)
    action = {"type": "noop"}
    forced_default = {"type": "seed_batch", "n_questions": 14}
    state: dict = {
        "seq_baseline_draw_blocked": {
            "trial_id": 9,
            "action": forced_default,
            "reference_key": "tier=1:reference=none",
            "reason": "all seed fallbacks were blacklisted",
        }
    }

    forced, rationale, reference = autopilot._maybe_force_seq_baseline_draw(
        action,
        state=state,
        journal=journal,
        tier=1,
        blacklist=[{"pattern": forced_default, "reason": "default still blocked"}],
        rationale=None,
        trial_counter=14,
        enabled=True,
    )

    assert forced == {"type": "seed_batch", "n_questions": 16}
    assert rationale == {
        "seq_baseline_reference_draw": True,
        "seq_baseline_reference_reason": "no marked seq baseline-reference draw",
    }
    assert reference is not None
    assert state["seq_baseline_draw_blocked"] is None
    assert state["seq_baseline_draw_forced"]["action"] == forced


def test_maybe_force_seq_baseline_draw_records_block_when_all_fallbacks_blacklisted(
    tmp_path: Path,
) -> None:
    journal = ExperimentJournal(journal_dir=tmp_path)
    action = {"type": "noop"}
    state: dict = {}
    blacklist = [
        {"pattern": candidate, "reason": f"blocked-{idx}"}
        for idx, candidate in enumerate(autopilot._seed_action_candidates())
    ]

    forced, rationale, reference = autopilot._maybe_force_seq_baseline_draw(
        action,
        state=state,
        journal=journal,
        tier=1,
        blacklist=blacklist,
        rationale=None,
        trial_counter=9,
        enabled=True,
    )

    assert forced == action
    assert rationale is None
    assert reference is None
    assert state["seq_baseline_draw_blocked"]["reason"]
    assert state["seq_baseline_draw_blocked"]["trial_id"] == 9


def test_seq_promotion_finalization_requires_fresh_eval_fresh_reference_and_e() -> None:
    seq = {
        "confirmed": True,
        "E_quality": 120.0,
        "E_rate_noninf": 110.0,
        "z": 0.2,
        "r_eff": 200,
    }
    reference = {
        "tier": 2,
        "latest_reference_trial_id": 4,
        "latest_reference_age_s": 120.0,
        "trials_since_reference": 1,
        "stale_reference": False,
    }

    finalized = autopilot._annotate_seq_promotion_finalization(
        seq,
        baseline_reference=reference,
        is_fresh_eval=True,
        fresh_eval_context={"candidate": "abc", "source_trial_id": 3},
    )

    assert finalized is True
    assert seq["baseline_promotion_finalized"] is True
    assert seq["baseline_promotion_combined_E"] == pytest.approx(110.0)
    assert seq["baseline_promotion_delta_ci"]["excludes_regression"] is True
    assert seq["baseline_promotion_fresh_eval_for"] == {
        "candidate": "abc",
        "source_trial_id": 3,
    }

    not_fresh = {
        "confirmed": True,
        "E_quality": 120.0,
        "E_rate_noninf": 110.0,
        "z": 0.2,
        "r_eff": 200,
    }
    assert (
        autopilot._annotate_seq_promotion_finalization(
            not_fresh,
            baseline_reference=reference,
            is_fresh_eval=False,
        )
        is False
    )

    stale = {
        "confirmed": True,
        "E_quality": 120.0,
        "E_rate_noninf": 110.0,
        "z": 0.2,
        "r_eff": 200,
    }
    stale_reference = dict(reference, stale_reference=True)
    assert (
        autopilot._annotate_seq_promotion_finalization(
            stale,
            baseline_reference=stale_reference,
            is_fresh_eval=True,
        )
        is False
    )
    assert stale["baseline_reference_state"] == "stale-reference"

    low_e = {
        "confirmed": True,
        "E_quality": 120.0,
        "E_rate_noninf": 99.0,
        "z": 0.2,
        "r_eff": 200,
    }
    assert (
        autopilot._annotate_seq_promotion_finalization(
            low_e,
            baseline_reference=reference,
            is_fresh_eval=True,
        )
        is False
    )


def test_seq_promotion_finalization_uses_quality_when_rate_axis_advisory() -> None:
    seq = {
        "confirmed": True,
        "E_quality": 120.0,
        "E_rate_noninf": 1.05,
        "rate_axis_mode": SEQ_P0_2_BRIDGE_MODE,
        "rate_axis_binding": False,
        "z": 0.2,
        "r_eff": 200,
    }
    reference = {
        "tier": 2,
        "latest_reference_trial_id": 4,
        "latest_reference_age_s": 120.0,
        "trials_since_reference": 1,
        "stale_reference": False,
    }

    finalized = autopilot._annotate_seq_promotion_finalization(
        seq,
        baseline_reference=reference,
        is_fresh_eval=True,
    )

    assert finalized is True
    assert seq["baseline_promotion_finalized"] is True
    assert seq["baseline_promotion_combined_E"] == pytest.approx(120.0)
    assert seq["baseline_promotion_rate_axis_mode"] == SEQ_P0_2_BRIDGE_MODE
    assert seq["baseline_promotion_combined_E_mode"] == "quality_only_rate_advisory"


def test_seq_promotion_finalization_requires_delta_ci_excluding_regression() -> None:
    reference = {
        "tier": 2,
        "latest_reference_trial_id": 4,
        "latest_reference_age_s": 120.0,
        "trials_since_reference": 1,
        "stale_reference": False,
    }
    missing_delta = {"confirmed": True, "E_quality": 120.0, "E_rate_noninf": 110.0}

    assert (
        autopilot._annotate_seq_promotion_finalization(
            missing_delta,
            baseline_reference=reference,
            is_fresh_eval=True,
        )
        is False
    )
    assert missing_delta["baseline_promotion_delta_ci"] == {
        "status": "missing",
        "excludes_regression": False,
        "reason": "missing z/r_eff promotion-delta evidence",
    }

    noisy_delta = {
        "confirmed": True,
        "E_quality": 120.0,
        "E_rate_noninf": 110.0,
        "z": 0.01,
        "r_eff": 200,
    }
    assert (
        autopilot._annotate_seq_promotion_finalization(
            noisy_delta,
            baseline_reference=reference,
            is_fresh_eval=True,
        )
        is False
    )
    assert noisy_delta["baseline_promotion_delta_ci"]["status"] == "ok"
    assert noisy_delta["baseline_promotion_delta_ci"]["lower_bound"] < 0.0
    assert noisy_delta["baseline_promotion_delta_ci"]["excludes_regression"] is False


def test_seq_promotion_state_queues_and_forces_one_fresh_eval() -> None:
    state: dict = {}
    action = {
        "type": "numeric_trial",
        "surface": "monitor",
        "params": {"ORCHESTRATOR_MONITOR_THRESHOLD": 0.42},
    }
    eval_result = autopilot.EvalResult(
        tier=2,
        quality=3.0,
        speed=10.0,
        cost=0.1,
        reliability=1.0,
    )

    autopilot._update_seq_promotion_fresh_eval_state(
        state,
        seq={
            "candidate": "candidate-a",
            "confirmed": True,
            "baseline_reference_state": "fresh",
            "baseline_promotion_combined_E": 25.0,
        },
        action=action,
        eval_result=eval_result,
        trial_counter=11,
        is_fresh_eval=False,
        finalized=False,
    )

    assert state["seq_pending_promotion_fresh_eval"]["candidate"] == "candidate-a"
    forced, rationale, context = autopilot._maybe_force_seq_promotion_fresh_eval(
        {"type": "noop"},
        state=state,
        blacklist=[],
        rationale=None,
        trial_counter=12,
        enabled=True,
    )

    assert forced == {"type": "deep_eval", "tier": 2}
    assert rationale == {
        "seq_promotion_fresh_eval": True,
        "seq_promotion_candidate": "candidate-a",
    }
    assert context is not None
    assert context["candidate"] == "candidate-a"
    assert state["seq_pending_promotion_fresh_eval"]["attempts"] == 1
    assert state["_seq_promotion_candidate_replay"] == {
        "trial_id": 12,
        "candidate": "candidate-a",
        "source_trial_id": 11,
        "action": action,
    }


def test_seq_promotion_blocks_new_candidate_when_alpha_wealth_exhausted() -> None:
    state: dict = {}
    action = {
        "type": "numeric_trial",
        "surface": "monitor",
        "params": {"ORCHESTRATOR_MONITOR_THRESHOLD": 0.42},
    }
    eval_result = autopilot.EvalResult(
        tier=2,
        quality=3.0,
        speed=10.0,
        cost=0.1,
        reliability=1.0,
    )

    autopilot._update_seq_promotion_fresh_eval_state(
        state,
        seq={
            "candidate": "candidate-new",
            "confirmed": True,
            "baseline_reference_state": "fresh",
            "baseline_promotion_combined_E": 25.0,
        },
        action=action,
        eval_result=eval_result,
        trial_counter=11,
        is_fresh_eval=False,
        finalized=False,
        seq_alpha_wealth={
            "candidate": "candidate-new",
            "candidate_is_new": True,
            "fingerprints_tested": 20,
            "alpha_spent": 1.0,
            "budget": 1.0,
            "new_fingerprint_confirmations_allowed": False,
        },
    )

    assert "seq_pending_promotion_fresh_eval" not in state
    assert state["seq_last_promotion_blocked"] == {
        "trial_id": 11,
        "candidate": "candidate-new",
        "reason": "alpha-wealth-budget-exhausted",
        "alpha_wealth": {
            "candidate": "candidate-new",
            "candidate_is_new": True,
            "fingerprints_tested": 20,
            "alpha_spent": 1.0,
            "budget": 1.0,
            "new_fingerprint_confirmations_allowed": False,
        },
    }


def test_seq_promotion_unreplayable_candidate_blocks_without_fresh_eval() -> None:
    state: dict = {}
    action = {"type": "numeric_trial", "surface": "monitor", "params": {}}
    eval_result = autopilot.EvalResult(
        tier=2,
        quality=3.0,
        speed=10.0,
        cost=0.1,
        reliability=1.0,
    )

    autopilot._update_seq_promotion_fresh_eval_state(
        state,
        seq={
            "candidate": "candidate-a",
            "confirmed": True,
            "baseline_reference_state": "fresh",
            "baseline_promotion_combined_E": 25.0,
        },
        action=action,
        eval_result=eval_result,
        trial_counter=11,
        is_fresh_eval=False,
        finalized=False,
    )

    original = {"type": "seed_batch", "n_questions": 12}
    forced, rationale, context = autopilot._maybe_force_seq_promotion_fresh_eval(
        original,
        state=state,
        blacklist=[],
        rationale={"source": "test"},
        trial_counter=12,
        enabled=True,
    )

    assert forced == original
    assert rationale == {"source": "test"}
    assert context is None
    assert "seq_pending_promotion_fresh_eval" not in state
    assert state["seq_last_promotion_blocked"] == {
        "trial_id": 12,
        "candidate": "candidate-a",
        "source_trial_id": 11,
        "reason": "candidate numeric_trial lacks replayable applied params",
    }


def test_seq_promotion_failed_fresh_eval_consumes_pending_attempt() -> None:
    state = {
        "seq_pending_promotion_fresh_eval": {
            "candidate": "candidate-a",
            "source_trial_id": 20,
            "tier": 2,
            "attempts": 1,
        }
    }
    eval_result = autopilot.EvalResult(
        tier=2,
        quality=2.5,
        speed=10.0,
        cost=0.1,
        reliability=1.0,
    )

    autopilot._update_seq_promotion_fresh_eval_state(
        state,
        seq={
            "candidate": "candidate-a",
            "confirmed": False,
            "baseline_reference_state": "fresh",
            "baseline_promotion_combined_E": 0.4,
        },
        action={"type": "deep_eval", "tier": 2},
        eval_result=eval_result,
        trial_counter=21,
        is_fresh_eval=True,
        finalized=False,
    )

    assert "seq_pending_promotion_fresh_eval" not in state
    assert state["seq_last_promotion_blocked"] == {
        "trial_id": 21,
        "candidate": "candidate-a",
        "reason": "fresh-eval did not confirm",
        "combined_E": 0.4,
    }


def test_seq_promotion_finalized_requires_baseline_update_acceptance() -> None:
    state = {
        "seq_pending_promotion_fresh_eval": {
            "candidate": "candidate-a",
            "source_trial_id": 20,
            "tier": 2,
            "attempts": 1,
        }
    }
    eval_result = autopilot.EvalResult(
        tier=2,
        quality=2.5,
        speed=10.0,
        cost=0.1,
        reliability=1.0,
    )

    autopilot._update_seq_promotion_fresh_eval_state(
        state,
        seq={
            "candidate": "candidate-a",
            "confirmed": True,
            "baseline_reference_state": "fresh",
            "baseline_promotion_combined_E": 120.0,
            "baseline_promotion_delta_ci": {"excludes_regression": True},
        },
        action={"type": "deep_eval", "tier": 2},
        eval_result=eval_result,
        trial_counter=21,
        is_fresh_eval=True,
        finalized=True,
        baseline_update=SimpleNamespace(
            updated=False,
            reason="not a monotonic same-tier improvement",
        ),
    )

    assert "seq_pending_promotion_fresh_eval" not in state
    assert "seq_last_promotion_finalized" not in state
    assert state["seq_last_promotion_blocked"] == {
        "trial_id": 21,
        "candidate": "candidate-a",
        "reason": "baseline-update-refused",
        "baseline_update_reason": "not a monotonic same-tier improvement",
        "combined_E": 120.0,
        "delta_ci": {"excludes_regression": True},
    }


def test_seq_promotion_fresh_eval_blacklist_suppresses_retry() -> None:
    state = {
        "seq_pending_promotion_fresh_eval": {
            "candidate": "candidate-a",
            "source_trial_id": 20,
            "tier": 2,
            "attempts": 0,
            "action": {
                "type": "numeric_trial",
                "surface": "monitor",
                "params": {"ORCHESTRATOR_MONITOR_THRESHOLD": 0.42},
            },
        }
    }

    action = {"type": "noop"}
    first, _, context = autopilot._maybe_force_seq_promotion_fresh_eval(
        action,
        state=state,
        blacklist=[{"pattern": {"type": "deep_eval", "tier": 2}, "reason": "test"}],
        rationale=None,
        trial_counter=21,
        enabled=True,
    )

    assert first == action
    assert context is None
    pending = state["seq_pending_promotion_fresh_eval"]
    assert pending["attempts"] == 1
    assert pending["blocked_reason"] == "test"

    second, _, second_context = autopilot._maybe_force_seq_promotion_fresh_eval(
        action,
        state=state,
        blacklist=[{"pattern": {"type": "deep_eval", "tier": 2}, "reason": "test"}],
        rationale=None,
        trial_counter=22,
        enabled=True,
    )

    assert second == action
    assert second_context is None
    assert state["seq_pending_promotion_fresh_eval"]["blocked_at_trial"] == 21


def _run_loop_inner_seq_harness(
    monkeypatch: pytest.MonkeyPatch,
    *,
    state: dict[str, Any],
    verdict_seq: dict[str, Any],
    force_fresh_eval_context: dict[str, Any] | None = None,
    seq_gate_preflight_payload: dict[str, Any] | None = None,
    learning_exclusion: tuple[str | None, str, Any] = (None, "", None),
    use_controller: bool = False,
    planner_should_not_run: bool = False,
    journal_entries_out: list[JournalEntry] | None = None,
    dispatch_actions_out: list[dict[str, Any]] | None = None,
    gate_check_raises_on_seq: bool = False,
) -> tuple[dict[str, Any], list[tuple[bool, int]]]:
    baseline_update_calls: list[tuple[bool, int]] = []

    class FakeJournal:
        def __init__(self) -> None:
            self._entries: list[JournalEntry] = []
            self._promotions: list[dict[str, Any]] = []

        def record(self, entry: JournalEntry) -> None:
            self._entries.append(entry)
            if journal_entries_out is not None:
                journal_entries_out.append(entry)

        def all_entries(self) -> list[JournalEntry]:
            return list(self._entries)

        def entries_with_supersessions(self) -> list[JournalEntry]:
            return list(self._entries)

        def by_species(self, species: str) -> list[JournalEntry]:
            return [entry for entry in self._entries if entry.species == species]

        def species_effectiveness(self, window: int = 50) -> dict[str, float]:
            return {}

        def baseline_promotion_events(self) -> list[dict[str, Any]]:
            return list(self._promotions)

        def baseline_ledger_events(self) -> list[dict[str, Any]]:
            return list(self._promotions)

        def append_baseline_promotion_event(self, **payload: Any) -> dict[str, Any]:
            self._promotions.append(payload)
            return payload

        def supersession_events(self) -> list[dict[str, Any]]:
            return []

    class FakeVerdict:
        def __init__(self, seq: dict[str, Any]) -> None:
            self.seq = dict(seq)
            self.passed = True
            self.categories: list[str] = []
            self.violations: list[str] = []

        def __bool__(self) -> bool:
            return self.passed

    class FakeCriticism:
        keep_or_revert = "keep"

        def as_text(self) -> str:
            return "ok"

        def directions_text(self) -> str:
            return ""

    class FakeSafetyGate:
        def __init__(
            self,
            consecutive_failures: int = 0,
            quality_history: list[Any] | None = None,
            quality_history_by_tier: dict[str, Any] | None = None,
            baseline_state: dict[str, Any] | None = None,
            *args: Any,
            **kwargs: Any,
        ) -> None:
            self.consecutive_failures = consecutive_failures
            self.quality_history = quality_history if quality_history is not None else []
            self.quality_history_by_tier = (
                quality_history_by_tier if quality_history_by_tier is not None else {}
            )
            # Defect #4: real SafetyGate now exposes the provenance-bearing window that
            # _run_loop_inner persists to state["quality_history_provenance_by_tier"].
            self.quality_history_provenance_by_tier = (
                kwargs.get("quality_history_provenance_by_tier") or {}
            )
            self.baseline = SimpleNamespace(
                quality_for_tier=lambda *_args: 0.0,
                to_state_dict=lambda: baseline_state or {},
            )
            self.use_sequential = True

        def check(self, *args: Any, **kwargs: Any) -> FakeVerdict:
            # SEQ-3b: when opted in, raise on the SEQUENTIAL check (the call that
            # threads baseline_profile) but succeed on the bare legacy fallback call
            # (`gate.check(eval_result)`, no kwargs) so the main loop must catch and
            # fall back instead of crashing.
            if gate_check_raises_on_seq and "baseline_profile" in kwargs:
                raise RuntimeError("corrupt sequential inputs (SEQ-3b test)")
            return FakeVerdict(verdict_seq)

        def analyze_failure(self, *args: Any, **kwargs: Any) -> str:
            return ""

        def should_rollback(self) -> bool:
            return False

        def reset_failures(self) -> None:
            self.consecutive_failures = 0

        def update_baseline(
            self,
            *_args: Any,
            seq_confirmed: bool | None = None,
            source_trial_id: int | None = None,
            **kwargs: Any,
        ) -> Any:
            baseline_update_calls.append((bool(seq_confirmed), int(source_trial_id or 0)))
            return SimpleNamespace(
                updated=True,
                reason="",
                tier=2,
                previous_quality=2.0,
                new_quality=2.5,
                proof=None,
            )

    class FakeMetaOptimizer:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.budget = autopilot.SpeciesBudget()

        def select_species(self) -> str:
            return "seed_batch"

        def should_rebalance(self, _trial_counter: int) -> bool:
            return False

        def rebalance(self, *args: Any, **kwargs: Any) -> None:
            return None

    class FakeSeeder:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def get_memory_count(self) -> int:
            return 0

        def restore_state(self, _state: dict[str, Any]) -> None:
            return None

        def export_state(self) -> dict[str, Any]:
            return {"td_errors": []}

        @property
        def is_converged(self) -> bool:
            return False

    class FakeEvalTower:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def capture_recent_traces(self, _limit: int = 50) -> str:
            return ""

    class FakePromptForge:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

    class FakeStructuralLab:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def restore_checkpoint(self) -> None:
            return None

        def checkpoint_state(self, *args: Any, **kwargs: Any) -> None:
            return None

    class FakeEvolutionManager:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

    class FakeParetoArchive:
        def frontier_size(self, *_args: Any, **_kwargs: Any) -> int:
            return 1

        def add(self, *args: Any, **kwargs: Any) -> bool:
            return True

        def update(self, *args: Any, **kwargs: Any) -> str:
            return "frontier"

        def hypervolume_slope(self, *_args: Any, **_kwargs: Any) -> float:
            return 0.0

        def hypervolume(self, *_args: Any, **_kwargs: Any) -> float:
            return 0.0

        def get_frontier(self, *args: Any, **kwargs: Any) -> list[Any]:
            return []

        def summary(self) -> dict[str, Any]:
            return {}

    class FakeShortTermMemory:
        def __init__(self) -> None:
            pass

        def refresh_from_journal(self, _journal: Any) -> None:
            return None

    class FakeStrategyStore:
        def count(self) -> int:
            return 0

        def store(self, *args: Any, **kwargs: Any) -> None:
            return None

        def close(self) -> None:
            return None

    class FakePhaseTracker:
        def set(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
            return {}

        def clear(self, *args: Any, **kwargs: Any) -> None:
            return None

    class FakeAsyncTaskRunner:
        def reap(self, *args: Any, **kwargs: Any) -> None:
            return None

        def submit_subprocess(
            self,
            *args: Any,
            **kwargs: Any,
        ) -> None:
            return None

        def submit(self, *args: Any, **kwargs: Any) -> Any:
            return None

        def shutdown(self) -> None:
            return None

    fake_journal = FakeJournal()

    def fake_check_blacklist(action: dict[str, Any], _blacklist: list[dict[str, Any]]) -> None:
        return None

    def fake_replace_blacklisted_seed_fallback(
        action: dict[str, Any],
        blacklist: list[dict[str, Any]],  # noqa: ARG001
        rationale: dict[str, Any] | None,
        reason_label: str = "",  # noqa: ARG001
    ) -> tuple[dict[str, Any], dict[str, Any] | None]:
        return action, rationale

    def fake_replace_blacklisted_autonomous_action(
        action: dict[str, Any], _blacklist: list[dict[str, Any]], rationale: dict[str, Any]
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        return action, rationale

    def fake_enforce_experiment_quota(
        action: dict[str, Any],
        _state: dict[str, Any],
        _memory_count: int,
        rationale: dict[str, Any],
        _trial_counter: int,
        _blacklist: list[dict[str, Any]],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        return action, rationale

    def fake_force_metric_action_after_meta(
        action: dict[str, Any],
        _state: dict[str, Any],
        rationale: dict[str, Any],
        _blacklist: list[dict[str, Any]],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        return action, rationale

    def fake_maybe_force_seq_promotion_fresh_eval(
        action: dict[str, Any],
        state: dict[str, Any],  # noqa: ARG001
        blacklist: list[dict[str, Any]],  # noqa: ARG001
        rationale: dict[str, Any] | None,
        trial_counter: int,  # noqa: ARG001
        enabled: bool,  # noqa: ARG001
    ) -> tuple[dict[str, Any], dict[str, Any] | None, dict[str, Any] | None]:
        if force_fresh_eval_context is None:
            return action, rationale, None
        return (
            {"type": "deep_eval", "tier": 2},
            (rationale or {}) | {"seq_promotion_fresh_eval": True},
            dict(force_fresh_eval_context),
        )

    def fake_maybe_force_seq_baseline_draw(
        action: dict[str, Any],
        state: dict[str, Any],  # noqa: ARG001
        journal: Any,  # noqa: ARG001
        tier: int,  # noqa: ARG001
        blacklist: list[dict[str, Any]],  # noqa: ARG001
        rationale: dict[str, Any] | None,
        trial_counter: int,  # noqa: ARG001
        enabled: bool,  # noqa: ARG001
    ) -> tuple[dict[str, Any], dict[str, Any] | None, dict[str, Any] | None]:
        return action, rationale, None

    def fake_dispatch_action(*args: Any, **kwargs: Any) -> tuple[Any, str]:
        if dispatch_actions_out is not None and args:
            dispatch_actions_out.append(dict(args[0]))
        return (
            autopilot.EvalResult(
                tier=2,
                quality=2.5,
                speed=10.0,
                cost=0.1,
                reliability=1.0,
            ),
            "seed_batch",
        )

    class FakeSelfCriticism:
        def __call__(self, *args: Any, **kwargs: Any) -> FakeCriticism:
            return FakeCriticism()

    monkeypatch.setattr(autopilot, "load_state", lambda: state)
    monkeypatch.setattr(autopilot, "save_state", lambda *args: None)
    monkeypatch.setattr(autopilot, "ExperimentJournal", lambda: fake_journal)
    monkeypatch.setattr(autopilot, "ParetoArchive", FakeParetoArchive)
    monkeypatch.setattr(autopilot, "SafetyGate", FakeSafetyGate)
    monkeypatch.setattr(autopilot, "MetaOptimizer", FakeMetaOptimizer)
    monkeypatch.setattr(autopilot, "Seeder", FakeSeeder)
    monkeypatch.setattr(autopilot, "NumericSwarm", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(autopilot, "PromptForge", FakePromptForge)
    monkeypatch.setattr(autopilot, "StructuralLab", FakeStructuralLab)
    monkeypatch.setattr(autopilot, "EvolutionManager", FakeEvolutionManager)
    monkeypatch.setattr(autopilot, "ShortTermMemory", FakeShortTermMemory)
    monkeypatch.setattr(autopilot, "StrategyStore", FakeStrategyStore)
    monkeypatch.setattr(autopilot, "EvalTower", FakeEvalTower)
    monkeypatch.setattr(autopilot, "AsyncTaskRunner", FakeAsyncTaskRunner)
    monkeypatch.setattr(autopilot, "PhaseTracker", FakePhaseTracker)
    monkeypatch.setattr(autopilot, "check_blacklist", fake_check_blacklist)
    monkeypatch.setattr(
        autopilot,
        "_replace_blacklisted_seed_fallback",
        fake_replace_blacklisted_seed_fallback,
    )
    monkeypatch.setattr(
        autopilot,
        "_replace_blacklisted_autonomous_action",
        fake_replace_blacklisted_autonomous_action,
    )
    monkeypatch.setattr(
        autopilot,
        "_enforce_experiment_quota",
        fake_enforce_experiment_quota,
    )
    monkeypatch.setattr(
        autopilot,
        "_force_metric_action_after_meta",
        fake_force_metric_action_after_meta,
    )
    monkeypatch.setattr(autopilot, "_auto_action", lambda *args, **kwargs: {"type": "seed_batch"})
    monkeypatch.setattr(
        autopilot,
        "_maybe_force_seq_promotion_fresh_eval",
        fake_maybe_force_seq_promotion_fresh_eval,
    )
    monkeypatch.setattr(
        autopilot,
        "_maybe_force_seq_baseline_draw",
        fake_maybe_force_seq_baseline_draw,
    )
    if seq_gate_preflight_payload is not None:

        def fake_maybe_defer_seq_unreachable_candidate_action(
            action: dict[str, Any],
            *,
            state: dict[str, Any],
            journal: Any,  # noqa: ARG001
            blacklist: list[dict[str, Any]],  # noqa: ARG001
            rationale: dict[str, Any] | None,
            trial_counter: int,  # noqa: ARG001
            tier: int,  # noqa: ARG001
            enabled: bool,  # noqa: ARG001
        ) -> tuple[dict[str, Any], dict[str, Any] | None, dict[str, Any] | None]:
            payload = dict(seq_gate_preflight_payload)
            payload.setdefault("original_action", dict(action))
            state["seq_gate_reachability_preflight"] = payload
            return action, rationale, payload

        monkeypatch.setattr(
            autopilot,
            "_maybe_defer_seq_unreachable_candidate_action",
            fake_maybe_defer_seq_unreachable_candidate_action,
        )
    monkeypatch.setattr(autopilot, "dispatch_action", fake_dispatch_action)
    monkeypatch.setattr(
        autopilot,
        "_journal_archive_payload_for_authority",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        autopilot, "_sync_startup_archive_from_journal_authority", lambda *args, **kwargs: False
    )
    monkeypatch.setattr(
        autopilot,
        "_recover_from_in_flight_trial",
        lambda _state, _journal, _archive, trial_counter: trial_counter,
    )
    monkeypatch.setattr(
        autopilot, "_save_state_with_journal_archive_authority", lambda *args, **kwargs: None
    )
    monkeypatch.setattr(autopilot, "_append_baseline_promotion_event", lambda *args, **kwargs: None)
    monkeypatch.setattr(autopilot, "health_check", lambda *args, **kwargs: object())
    monkeypatch.setattr(autopilot, "should_generate_today", lambda _state: False)
    monkeypatch.setattr(autopilot.subprocess, "run", lambda *args, **kwargs: None)
    monkeypatch.setattr(autopilot, "_git_tag", lambda *args, **kwargs: None)
    monkeypatch.setattr(autopilot, "generate_self_criticism", FakeSelfCriticism())
    monkeypatch.setattr(
        autopilot,
        "classify_learning_exclusion",
        lambda *args, **kwargs: learning_exclusion,
    )
    monkeypatch.setattr(autopilot.peaf, "compute_surprise", lambda *args, **kwargs: 0.0)
    monkeypatch.setattr(
        autopilot.peaf,
        "actual_objectives_from_eval",
        lambda *args, **kwargs: {},
    )
    monkeypatch.setattr(autopilot, "get_preflight_diagnostics", None)
    if planner_should_not_run:

        def fail_plan_with_providers(*args: Any, **kwargs: Any) -> Any:
            raise AssertionError("planner should be bypassed for forced seq action")

        monkeypatch.setattr(autopilot, "plan_with_providers", fail_plan_with_providers)

    autopilot._run_loop_inner(
        max_trials=1,
        dry_run=False,
        use_controller=use_controller,
        tui=None,
    )

    return state, baseline_update_calls


def test_run_loop_inner_journals_report_only_rlvr_reward(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state: dict[str, Any] = {
        "trial_counter": 0,
        "paused": False,
        "td_errors": [],
        "seeder_state": {},
        "consecutive_failures": 0,
        "quality_history": [],
        "quality_history_by_tier": {},
        "baseline_state": {},
    }
    journal_entries: list[JournalEntry] = []

    _run_loop_inner_seq_harness(
        monkeypatch,
        state=state,
        verdict_seq={
            "candidate": "candidate-a",
            "confirmed": False,
            "state": "accumulating",
        },
        journal_entries_out=journal_entries,
    )

    assert len(journal_entries) == 1
    rlvr = journal_entries[0].eval_details["rlvr_reward"]
    assert rlvr["policy"] == "ap27_rlvr_tier_reward_v1"
    assert rlvr["reward_signal"] == "process_attributed"
    assert rlvr["ready_for_training"] is False
    assert "auroc_missing_or_degenerate" in rlvr["blockers"]
    assert "question_results_missing" in rlvr["blockers"]


def test_run_loop_inner_gate_check_falls_back_when_seq_inputs_raise(
    monkeypatch: pytest.MonkeyPatch,
    caplog,
) -> None:
    # SEQ-3b: if the main-loop sequential gate.check(...) raises (e.g. corrupt
    # journal-derived seq inputs), the loop must catch it, log a fallback warning, and
    # complete via the legacy gate.check(eval_result) — NOT crash. Mirrors the
    # actions.py _action_gate_check fallback semantics.
    state: dict[str, Any] = {
        "trial_counter": 0,
        "paused": False,
        "td_errors": [],
        "seeder_state": {},
        "consecutive_failures": 0,
        "quality_history": [],
        "quality_history_by_tier": {},
        "baseline_state": {},
    }
    journal_entries: list[JournalEntry] = []

    with caplog.at_level(logging.WARNING, logger="autopilot"):
        _run_loop_inner_seq_harness(
            monkeypatch,
            state=state,
            verdict_seq={
                "candidate": "candidate-a",
                "confirmed": False,
                "state": "accumulating",
            },
            journal_entries_out=journal_entries,
            gate_check_raises_on_seq=True,
        )

    # The loop survived the raise and still journaled the trial.
    assert len(journal_entries) == 1
    assert "fell back to legacy check" in caplog.text


def test_run_loop_inner_halts_on_blocked_seq_gate_preflight(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state: dict[str, Any] = {
        "trial_counter": 0,
        "paused": False,
        "td_errors": [],
        "seeder_state": {},
        "consecutive_failures": 0,
        "quality_history": [],
        "quality_history_by_tier": {},
        "baseline_state": {},
    }
    journal_entries: list[JournalEntry] = []
    dispatched: list[dict[str, Any]] = []

    returned_state, _ = _run_loop_inner_seq_harness(
        monkeypatch,
        state=state,
        verdict_seq={
            "candidate": "candidate-a",
            "confirmed": False,
            "state": "accumulating",
        },
        seq_gate_preflight_payload={
            "status": "blocked_unreachable",
            "reason": "alpha_wealth_exhausted",
            "original_action": {"type": "numeric_trial", "surface": "think_harder"},
            "replacement_action": None,
        },
        journal_entries_out=journal_entries,
        dispatch_actions_out=dispatched,
    )

    assert returned_state["paused"] is True
    assert returned_state["_dispatch_deficiency"] == "seq_gate_preflight_blocked"
    assert returned_state["last_invalid_reason"] == "seq_gate_preflight_alpha_wealth_exhausted"
    assert returned_state["last_invalid_status"] == "seq_gate_preflight_blocked"
    assert "in_flight_trial" not in returned_state
    assert journal_entries == []
    assert dispatched == []


def test_run_loop_inner_forwards_finalized_seq_to_gate_and_clears_pending(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state: dict[str, Any] = {
        "trial_counter": 0,
        "paused": False,
        "td_errors": [],
        "seeder_state": {},
        "consecutive_failures": 0,
        "quality_history": [],
        "quality_history_by_tier": {},
        "baseline_state": {},
    }

    returned_state, baseline_update_calls = _run_loop_inner_seq_harness(
        monkeypatch,
        state=state,
        verdict_seq={
            "candidate": "candidate-a",
            "confirmed": True,
            "E_quality": 120.0,
            "E_rate_noninf": 120.0,
            "z": 0.2,
            "r_eff": 200,
        },
        force_fresh_eval_context={
            "candidate": "candidate-a",
            "source_trial_id": 13,
        },
    )

    assert baseline_update_calls == [(True, 0)]
    assert returned_state["seq_last_promotion_finalized"] == {
        "trial_id": 0,
        "candidate": "candidate-a",
        "combined_E": 120.0,
        "baseline_update_reason": "",
        "delta_ci": {
            "status": "ok",
            "confidence": 0.95,
            "alpha": 0.05,
            "n_eff": 200,
            "mean_delta": 0.2,
            "half_width": 0.173082,
            "lower_bound": 0.026918,
            "excludes_regression": True,
        },
    }
    assert "seq_pending_promotion_fresh_eval" not in returned_state


def test_run_loop_inner_forced_seq_fresh_eval_bypasses_controller_planner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state: dict[str, Any] = {
        "trial_counter": 0,
        "paused": False,
        "td_errors": [],
        "seeder_state": {},
        "consecutive_failures": 0,
        "quality_history": [],
        "quality_history_by_tier": {},
        "baseline_state": {},
    }

    returned_state, baseline_update_calls = _run_loop_inner_seq_harness(
        monkeypatch,
        state=state,
        verdict_seq={
            "candidate": "candidate-controller",
            "confirmed": True,
            "E_quality": 120.0,
            "E_rate_noninf": 120.0,
            "z": 0.2,
            "r_eff": 200,
        },
        force_fresh_eval_context={
            "candidate": "candidate-controller",
            "source_trial_id": 17,
        },
        use_controller=True,
        planner_should_not_run=True,
    )

    assert baseline_update_calls == [(True, 0)]
    assert returned_state["seq_last_promotion_finalized"]["candidate"] == ("candidate-controller")
    assert "session_id" not in returned_state


def test_run_loop_inner_forced_frontier_rerun_bypasses_controller_planner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state: dict[str, Any] = {
        "trial_counter": 0,
        "paused": False,
        "td_errors": [],
        "seeder_state": {},
        "consecutive_failures": 0,
        "quality_history": [],
        "quality_history_by_tier": {},
        "baseline_state": {},
        "active_instrument_eras": {"autopilot_speed": "E5-autopilot-speed"},
        "pareto_epoch_ts": 1_782_511_631.0,
        "pareto_exclude_before_ts": 1_782_511_631.0,
        "frontier_rerun_required": {
            "required": True,
            "reason": "v6 kernel era opened",
        },
    }

    returned_state, _ = _run_loop_inner_seq_harness(
        monkeypatch,
        state=state,
        verdict_seq={
            "candidate": "candidate-controller",
            "confirmed": True,
            "E_quality": 10.0,
            "E_rate_noninf": 10.0,
            "z": 0.0,
            "r_eff": 50,
        },
        use_controller=True,
        planner_should_not_run=True,
    )

    assert returned_state["frontier_rerun_forced"]["forced_action"]["type"] == ("numeric_trial")


def test_run_loop_inner_nonfinalized_seq_does_not_promote_and_leaves_pending(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state: dict[str, Any] = {
        "trial_counter": 0,
        "paused": False,
        "td_errors": [],
        "seeder_state": {},
        "consecutive_failures": 0,
        "quality_history": [],
        "quality_history_by_tier": {},
        "baseline_state": {},
        "seq_pending_promotion_fresh_eval": {
            "candidate": "candidate-a",
            "source_trial_id": 13,
            "tier": 2,
            "attempts": 3,
        },
    }

    returned_state, baseline_update_calls = _run_loop_inner_seq_harness(
        monkeypatch,
        state=state,
        verdict_seq={
            "candidate": "candidate-a",
            "confirmed": True,
            "E_quality": 90.0,
            "E_rate_noninf": 90.0,
        },
        force_fresh_eval_context=None,
    )

    assert baseline_update_calls == [(False, 0)]
    assert "seq_last_promotion_finalized" not in returned_state
    assert "seq_pending_promotion_fresh_eval" in returned_state


def test_run_loop_inner_fresh_eval_exclusion_consumes_pending_promotion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state: dict[str, Any] = {
        "trial_counter": 0,
        "paused": False,
        "td_errors": [],
        "seeder_state": {},
        "consecutive_failures": 0,
        "quality_history": [],
        "quality_history_by_tier": {},
        "baseline_state": {},
        "seq_pending_promotion_fresh_eval": {
            "candidate": "candidate-a",
            "source_trial_id": 13,
            "tier": 2,
            "attempts": 1,
        },
    }

    returned_state, baseline_update_calls = _run_loop_inner_seq_harness(
        monkeypatch,
        state=state,
        verdict_seq={
            "candidate": "candidate-a",
            "confirmed": False,
            "E_quality": 12.0,
            "E_rate_noninf": 11.0,
            "z": 0.0,
            "r_eff": 200,
        },
        force_fresh_eval_context={
            "candidate": "candidate-a",
            "source_trial_id": 13,
        },
        learning_exclusion=("seq_accumulating", "sequential evidence accumulating", None),
    )

    assert baseline_update_calls == []
    assert "seq_pending_promotion_fresh_eval" not in returned_state
    assert returned_state["seq_last_promotion_blocked"] == {
        "trial_id": 0,
        "candidate": "candidate-a",
        "reason": "fresh-eval did not confirm",
        "combined_E": 11.0,
        "delta_ci": {
            "status": "ok",
            "confidence": 0.95,
            "alpha": 0.05,
            "n_eff": 200,
            "mean_delta": 0.0,
            "half_width": 0.173082,
            "lower_bound": -0.173082,
            "excludes_regression": False,
        },
    }
