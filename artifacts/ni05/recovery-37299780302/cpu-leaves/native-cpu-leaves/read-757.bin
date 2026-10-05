"""Unit tests for benchmark seeding_eval helper module."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest


_ROOT = Path(__file__).resolve().parents[2] / "scripts" / "benchmark"
sys.path.insert(0, str(_ROOT))
_SPEC = importlib.util.spec_from_file_location("seeding_eval_test", _ROOT / "seeding_eval.py")
_MOD = importlib.util.module_from_spec(_SPEC)
sys.modules["seeding_eval_test"] = _MOD
_SPEC.loader.exec_module(_MOD)


@pytest.fixture(autouse=True)
def _reset_seeding_shutdown_flag(monkeypatch):
    """Isolate from the process-global ``seeding_types.state`` singleton.

    ``evaluate_question_per_role`` breaks out of its wave loop when
    ``state.shutdown`` is set; signal-handler tests in other files (e.g.
    test_seed_specialist_routing_v2_helpers.py) leave it True, which made these
    tests order-dependent under xdist.
    """
    monkeypatch.setattr(_MOD.state, "shutdown", False)


def _rr(**overrides):
    base = dict(
        role="frontdoor",
        mode="direct",
        answer="answer",
        passed=False,
        elapsed_seconds=1.0,
    )
    base.update(overrides)
    return _MOD.RoleResult(**base)


def test_build_role_result_infrastructure_and_success_paths():
    infra_resp = {"answer": "", "error": "timed out", "tokens_generated": 0}
    rr_infra, err_type_infra = _MOD._build_role_result(
        role="frontdoor",
        mode="direct",
        resp=infra_resp,
        elapsed=2.0,
        expected="42",
        scoring_method="exact_match",
        scoring_config={},
    )
    assert err_type_infra == "infrastructure"
    assert rr_infra.passed is False
    assert rr_infra.error == "timed out"

    success_resp = {
        "answer": "42",
        "tokens_generated": 7,
        "tokens_used": 12,
        "tools_called": ["x"],
        "delegation_events": [{"k": 1}],
        "web_research_results": [{"query": "q"}],
        "scratchpad_insights": [{"insight": "i"}],
    }
    # _build_role_result now scores via score_answer_or_error (which returns a
    # (passed, error_reason) tuple and converts scorer-unavailability into an
    # excluded row); patch that instead of the raw deterministic scorer.
    with patch.object(_MOD, "score_answer_or_error", return_value=(True, None)):
        rr_ok, err_type_ok = _MOD._build_role_result(
            role="frontdoor",
            mode="direct",
            resp=success_resp,
            elapsed=1.0,
            expected="42",
            scoring_method="exact_match",
            scoring_config={},
        )
    assert err_type_ok == "none"
    assert rr_ok.passed is True
    assert rr_ok.tokens_generated == 7
    assert rr_ok.prompt_tokens == 12
    assert rr_ok.web_research_results == [{"query": "q"}]
    assert rr_ok.scratchpad_insights == [{"insight": "i"}]


def test_build_role_result_inband_error_answer_is_excluded_not_scored():
    # REL-1 Guard 1: an HTTP-200 body whose answer IS an in-band "[ERROR: ...]"
    # banner (error=None) must be EXCLUDED as infrastructure, never scored as a
    # WRONG answer (which would inject a 0.0 MemRL reward). Also assert the
    # scorer is never consulted for such a row.
    banner = "[ERROR: Backend unavailable (circuit open): http://localhost:8082]"
    with patch.object(_MOD, "score_answer_or_error") as score_mock:
        rr, err_type = _MOD._build_role_result(
            role="frontdoor",
            mode="direct",
            resp={"answer": banner},
            elapsed=1.0,
            expected="42",
            scoring_method="exact_match",
            scoring_config={},
        )
    assert err_type == "infrastructure"
    assert rr.passed is False
    assert rr.error == banner
    score_mock.assert_not_called()


def test_build_role_result_scorer_unavailable_is_excluded_not_crash():
    # REL-1 finding 2: a scorer raise (ScoringUnavailableError / unknown method)
    # must become an EXCLUDED infrastructure row, never crash the seed run.
    with patch.object(
        _MOD, "score_answer_or_error",
        return_value=(None, "scoring_unavailable: math_verify library unavailable"),
    ):
        rr, err_type = _MOD._build_role_result(
            role="worker_math",
            mode="direct",
            resp={"answer": "0.5", "routed_to": "worker_math"},
            elapsed=1.0,
            expected="1/2",
            scoring_method="math_verify",
            scoring_config={},
        )
    assert err_type == "infrastructure"
    assert rr.passed is False
    assert rr.error.startswith("scoring_unavailable:")


def test_build_role_result_forced_role_mismatch_excluded_when_delegation_off():
    # REL-1 Guard 2: with delegation OFF, a silent circuit-open fallback that
    # served a DIFFERENT role than forced is a cross-role mis-attribution ->
    # EXCLUDED infrastructure row (never scored as the forced role's verdict).
    with patch.object(_MOD, "score_answer_or_error") as score_mock:
        rr, err_type = _MOD._build_role_result(
            role="worker_math",
            mode="direct",
            resp={"answer": "7", "routed_to": "worker_general"},
            elapsed=1.0,
            expected="42",
            scoring_method="exact_match",
            scoring_config={},
            allow_delegation=False,
        )
    assert err_type == "infrastructure"
    assert rr.passed is False
    assert "forced_role_fallback" in rr.error
    assert "served_by=worker_general" in rr.error
    score_mock.assert_not_called()


def test_build_role_result_forced_role_mismatch_not_flagged_when_delegation_on():
    # The seeding ARCHITECT config runs with delegation ENABLED, where
    # routed_to != role is the EXPECTED, correct behavior (architect delegates
    # to workers). Guard 2 MUST NOT fire there — the result is scored normally.
    with patch.object(_MOD, "score_answer_or_error", return_value=(True, None)) as score_mock:
        rr, err_type = _MOD._build_role_result(
            role="architect_general",
            mode="delegated",
            resp={"answer": "42", "routed_to": "worker_general"},
            elapsed=1.0,
            expected="42",
            scoring_method="exact_match",
            scoring_config={},
            allow_delegation=True,
        )
    assert err_type == "none"
    assert rr.passed is True
    score_mock.assert_called_once()


def test_compute_3way_metadata_includes_cost_web_and_scratchpad_sections():
    role_results = {
        "frontdoor:direct": _rr(
            role="frontdoor",
            mode="direct",
            passed=True,
            elapsed_seconds=2.0,
            tokens_generated=20,
            predicted_tps=10.0,
            prompt_eval_ms=5.0,
            generation_ms=200.0,
            backend_task_id=10,
            slot_progress_source="slots_poll",
            error_type="none",
        ),
        "frontdoor:repl": _rr(
            role="frontdoor",
            mode="repl",
            passed=False,
            elapsed_seconds=4.0,
            tokens_generated=30,
            predicted_tps=8.0,
            prompt_eval_ms=8.0,
            generation_ms=300.0,
            tools_used=2,
            backend_task_id=11,
            slot_progress_source="slots_poll",
            web_research_results=[{"query": "q1"}],
            scratchpad_insights=[{"insight": "search found source details"}],
            answer="final answer",
            error_type="none",
        ),
        "architect_general:delegated": _rr(
            role="architect_general",
            mode="delegated",
            passed=True,
            elapsed_seconds=5.0,
            tokens_generated=40,
            predicted_tps=7.0,
            prompt_eval_ms=10.0,
            generation_ms=250.0,
            role_history=["architect_general", "worker_math"],
            backend_task_id=12,
            slot_progress_source="slots_poll",
            error_type="none",
        ),
    }
    arch_results = {
        "architect_general": {
            "passed": True,
            "elapsed_seconds": 5.0,
            "generation_ms": 250.0,
        },
    }
    with (
        patch.object(
            _MOD,
            "extract_web_research_telemetry",
            return_value=SimpleNamespace(
                call_count=1,
                total_pages_fetched=2,
                total_pages_synthesized=1,
                total_elapsed_ms=10.0,
                unique_domains=1,
                queries=["q1"],
            ),
        ),
        patch.object(_MOD, "compute_web_research_rewards", return_value={"wr_accuracy": 1.0}),
        patch.object(_MOD, "score_query_strategy", return_value={"query_count": 1.0}),
        patch.object(_MOD, "compute_scratchpad_rewards", return_value={"sp_insight_count": 1.0}),
    ):
        md = _MOD._compute_3way_metadata(
            role_results=role_results,
            arch_results=arch_results,
            prompt="implement function foo",
            suite="math",
            passed_direct=True,
            passed_repl=False,
            self_role="frontdoor",
            self_direct_mode="direct",
            self_repl_mode="repl",
            arch_mode="delegated",
        )

    assert md["architect_eval"]["best"] == "architect_general"
    assert md["architect_eval"]["heuristic_would_pick"] == "architect_general"
    assert list(md["architect_eval"]["by_role"]) == ["architect_general"]
    assert md["architect_role"] == "architect_general"
    assert md["all_infra"] is False
    assert "web_research_rewards" in md
    assert "web_research_telemetry" in md
    assert "web_research_strategy" in md
    assert "scratchpad_rewards" in md
    assert _MOD.ACTION_SELF_DIRECT in md["cost_metrics"]
    assert _MOD.ACTION_SELF_REPL in md["cost_metrics"]
    assert _MOD.ACTION_ARCHITECT in md["cost_metrics"]


def _declared_wave_matrix(role_names):
    """A DECLARED ContentionMatrix for the wave-packing tests.

    `_can_add_role_to_seed_wave` consults `pair_policy`/`nway_policy`, which
    load the committed `orchestration/contention_matrix.yaml`. That file is a
    MEASUREMENT ARTIFACT regenerated by `scripts/server/contention_matrix.py`
    from whichever lineup is live at bench time — its role names, ratios and
    even its top-level sections move under the tests (the 2026-08-01 re-bench
    dropped `n_way`/`nway_light_roles` entirely, so `nway_policy` takes its
    unmeasured fail-closed branch and QUEUEs every background co-run). Same
    reasoning, and same remedy, as `tests/unit/contention_gate_fixture.py`.

    Wave packing is what this test proves, so the contention inputs are
    declared here: every named role light, every pair concurrency-positive.
    """
    from itertools import combinations

    from src.scheduling.contention import ContentionMatrix, Pair

    pairs = {}
    for key in (tuple(sorted(p)) for p in combinations(sorted(role_names), 2)):
        pairs[key] = Pair(roles=key, ratio=1.5, verdict="allow", samples=3)
    return ContentionMatrix(
        version=1,
        measured_at="2026-08-01T00:00:00+00:00",
        host="fixture",
        topology_hash="fixture-topology",
        default_floor=0.85,
        pairs=pairs,
        same_role={},
        unknown_pairs=[],
        n_way={},
        light_roles=frozenset(role_names),
        heavy_roles=frozenset(),
    )


def test_seed_role_waves_group_matrix_safe_light_with_one_heavy(monkeypatch):
    monkeypatch.delenv("AUTOPILOT_SEED_ROLE_CONCURRENCY", raising=False)
    roles = [
        {"name": "frontdoor"},
        {"name": "worker_general"},
        {"name": "ingest_long_context"},
        {"name": "architect_general"},
    ]
    role_names = [r["name"] for r in roles]

    # Declare the topology the packing rules key on (same idiom as the other
    # ROLE_PORT/HEAVY_PORTS tests in this file): three distinct heavy ports and
    # one light port, so the assertions below isolate "at most one heavy port
    # per wave" rather than restating today's port map.
    with (
        patch.object(
            _MOD,
            "ROLE_PORT",
            {
                "frontdoor": 8070,
                "worker_general": 8072,
                "ingest_long_context": 8085,
                "architect_general": 8083,
            },
        ),
        patch.object(_MOD, "HEAVY_PORTS", {8070, 8083, 8085}),
        patch(
            "src.scheduling.contention.load_contention_matrix",
            return_value=_declared_wave_matrix(role_names),
        ),
    ):
        waves = _MOD._seed_role_waves(roles)
    names = [[r["name"] for r in wave] for wave in waves]

    assert names[0] == ["frontdoor", "worker_general"]
    assert names[1] == ["ingest_long_context"]
    assert names[2] == ["architect_general"]


def test_seed_role_waves_can_be_forced_serial(monkeypatch):
    monkeypatch.setenv("AUTOPILOT_SEED_ROLE_CONCURRENCY", "1")
    roles = [{"name": "frontdoor"}, {"name": "worker_general"}]

    waves = _MOD._seed_role_waves(roles)

    assert [[r["name"] for r in wave] for wave in waves] == [
        ["frontdoor"],
        ["worker_general"],
    ]


def test_seed_timeout_helpers_use_role_timeout_and_queue_allowance(monkeypatch):
    monkeypatch.setenv("AUTOPILOT_SEED_QUEUE_ALLOWANCE_S", "30")

    assert _MOD._role_base_timeout_s({"name": "frontdoor", "timeout_s": 180}, 120) == 180
    assert _MOD._role_base_timeout_s({"name": "frontdoor", "timeout_s": "bad"}, 120) == 120
    assert _MOD._seed_request_timeout_s(180) == 210
    assert _MOD._seed_request_timeout_s(590) == 600

    monkeypatch.setenv("AUTOPILOT_SEED_QUEUE_ALLOWANCE_S", "bad")
    assert _MOD._seed_request_timeout_s(180) == 270


def test_evaluate_question_per_role_skips_hot_roles_and_records_timeouts(monkeypatch):
    monkeypatch.setenv("AUTOPILOT_SEED_QUEUE_ALLOWANCE_S", "90")
    monkeypatch.setenv("SEEDING_PER_QUESTION_BUDGET_S", "600")

    active_roles = [
        {"name": "frontdoor", "is_heavy": False, "timeout_s": 180},
        {"name": "architect_general", "is_heavy": False, "timeout_s": 600},
    ]
    rr_frontdoor = _rr(
        role="frontdoor",
        mode="",
        passed=True,
        error_type="none",
        elapsed_seconds=2.0,
    )

    def _skip(role: str, mode: str):  # noqa: ARG001
        if role == "architect_general":
            return True, "timeout rate 75% over last 4 attempts"
        return False, ""

    with (
        patch.object(_MOD, "_seed_role_waves", return_value=[[active_roles[0]], [active_roles[1]]]),
        patch.object(_MOD, "_telemetry_should_skip", side_effect=_skip),
        patch.object(_MOD, "_telemetry_timeout", side_effect=lambda _r, _m, base: base + 20),
        patch.object(_MOD, "_adaptive_timeout_s", side_effect=lambda **kw: kw["hard_timeout_s"]),
        patch.object(_MOD, "_telemetry_record") as record_mock,
        patch.object(_MOD, "_eval_single_config", return_value=(rr_frontdoor, {})) as eval_mock,
        patch.object(_MOD.logger, "info"),
    ):
        role_results, rewards, metadata = _MOD.evaluate_question_per_role(
            prompt_info={
                "prompt": "What is 2+2?",
                "expected": "4",
                "suite": "debug",
            },
            active_roles=active_roles,
            url="http://localhost:8000",
            timeout=120,
            client=object(),
        )

    assert list(role_results) == ["frontdoor"]
    assert rewards == {"frontdoor": 1.0}
    assert metadata["roles_skipped"] == {
        "architect_general": "timeout rate 75% over last 4 attempts"
    }
    assert metadata["cost_metrics"]["frontdoor"]["inference_timeout_s"] == 200
    assert metadata["cost_metrics"]["frontdoor"]["request_timeout_s"] == 290
    assert eval_mock.call_args.kwargs["timeout"] == 290
    record_mock.assert_called_once_with("frontdoor", "natural", 2.0, False)


def test_evaluate_question_per_role_logs_infra_skip_context(monkeypatch):
    monkeypatch.setenv("AUTOPILOT_SEED_QUEUE_ALLOWANCE_S", "90")
    monkeypatch.setenv("SEEDING_PER_QUESTION_BUDGET_S", "600")

    active_roles = [
        {"name": "worker_general", "is_heavy": False, "timeout_s": 60},
    ]
    rr_worker = _rr(
        role="worker_general",
        mode="",
        passed=False,
        error_type="infrastructure",
        error="slot idle while request pending after 16s on port 8072",
        elapsed_seconds=16.2,
        backend_task_id=465469,
        tokens_generated_estimate=4,
        slot_progress_source="slots_poll",
    )

    with (
        patch.object(_MOD, "_seed_role_waves", return_value=[[active_roles[0]]]),
        patch.object(_MOD, "_telemetry_should_skip", return_value=(False, "")),
        patch.object(_MOD, "_telemetry_timeout", side_effect=lambda _r, _m, base: base),
        patch.object(_MOD, "_adaptive_timeout_s", side_effect=lambda **kw: kw["hard_timeout_s"]),
        patch.object(_MOD, "_telemetry_record"),
        patch.object(_MOD, "_eval_single_config", return_value=(rr_worker, {})),
        patch.object(_MOD.logger, "info") as info_mock,
    ):
        role_results, rewards, metadata = _MOD.evaluate_question_per_role(
            prompt_info={
                "prompt": "What is 2+2?",
                "expected": "4",
                "suite": "debug",
            },
            active_roles=active_roles,
            url="http://localhost:8000",
            timeout=120,
            client=object(),
        )

    assert list(role_results) == ["worker_general"]
    assert rewards == {}
    assert metadata["all_infra"] is True
    assert any(
        args
        and args[0] == (
            "    [INFRA_SKIP] %s error=%r elapsed=%.1fs task=%s "
            "decoded=%s source=%s"
        )
        and args[1:] == (
            "worker_general",
            "slot idle while request pending after 16s on port 8072",
            16.2,
            465469,
            4,
            "slots_poll",
        )
        for args, _kwargs in info_mock.call_args_list
    )


def test_eval_single_config_merges_slot_progress_and_emits_format_lines():
    rr = _rr(role="frontdoor", mode="direct", passed=True, error_type="none")
    format_lines = []

    def _format_fn(*args, **kwargs):  # noqa: ANN001
        return ["formatted line"]

    with (
        patch.object(_MOD, "ROLE_PORT", {"frontdoor": 0}),
        patch.object(_MOD, "_call_orchestrator_with_slot_poll", return_value=({"answer": "ok", "tokens_generated": 5}, 1.2, {"max_decoded": 9, "task_id": 77, "source": "slots_poll"})),
        patch.object(_MOD, "_build_role_result", return_value=(rr, "none")),
        patch.object(_MOD, "_tap_size", side_effect=[10, 18]),
        patch.object(_MOD, "_repl_tap_size", side_effect=[30, 35]),
        patch.object(_MOD, "_log_delegation_diag"),
        patch.object(_MOD.logger, "info", side_effect=lambda line, *a, **k: format_lines.append(str(line))),
    ):
        out_rr, out_resp = _MOD._eval_single_config(
            prompt="p",
            expected="e",
            scoring_method="exact_match",
            scoring_config={},
            role="frontdoor",
            mode="direct",
            url="http://localhost:8000",
            timeout=60,
            client=object(),
            allow_delegation=False,
            log_label="SELF:direct",
            format_fn=_format_fn,
        )

    assert out_resp["tokens_generated_estimate"] == 9
    assert out_resp["backend_task_id"] == 77
    assert out_resp["slot_progress_source"] == "slots_poll"
    assert out_rr.tap_offset_bytes == 10
    assert out_rr.tap_length_bytes == 8
    assert out_rr.repl_tap_offset_bytes == 30
    assert out_rr.repl_tap_length_bytes == 5
    assert any("formatted line" in line for line in format_lines)


def test_eval_single_config_retries_after_http_5xx_recovery():
    rr1 = _rr(role="frontdoor", mode="direct", passed=False, error="Server error '503'", error_type="infrastructure")
    rr2 = _rr(role="frontdoor", mode="direct", passed=True, error=None, error_type="none")

    with (
        patch.object(_MOD, "ROLE_PORT", {"frontdoor": 8080}),
        patch.object(_MOD, "HEAVY_PORTS", {8080}),
        patch.object(_MOD, "_erase_slots"),
        patch.object(_MOD, "_wait_for_heavy_models_idle"),
        patch.object(_MOD, "_busy_heavy_ports", side_effect=[[], []]),
        patch.object(_MOD, "_recover_heavy_ports_if_stuck", return_value=True),
        patch.object(_MOD, "_force_erase_and_verify"),
        patch.object(_MOD.time, "sleep"),
        patch.object(
            _MOD,
            "_call_orchestrator_with_slot_poll",
            side_effect=[
                ({"answer": "", "error": "Server error '503'", "tokens_generated": 0}, 2.0, {"max_decoded": 3, "task_id": 1, "source": "slots_poll"}),
                ({"answer": "ok", "tokens_generated": 8}, 1.0, {"max_decoded": 10, "task_id": 2, "source": "slots_poll"}),
            ],
        ),
        patch.object(_MOD, "_build_role_result", side_effect=[(rr1, "infrastructure"), (rr2, "none")]),
        patch.object(_MOD, "_tap_size", side_effect=[100, 120, 140]),
        patch.object(_MOD, "_repl_tap_size", side_effect=[50, 60, 70]),
        patch.object(_MOD, "_log_delegation_diag"),
        patch.object(_MOD.logger, "info"),
    ):
        out_rr, out_resp = _MOD._eval_single_config(
            prompt="p",
            expected="e",
            scoring_method="exact_match",
            scoring_config={},
            role="frontdoor",
            mode="direct",
            url="http://localhost:8000",
            timeout=120,
            client=object(),
            allow_delegation=False,
            log_label="SELF:direct",
            format_fn=None,
        )

    assert out_rr.passed is True
    assert out_resp["tokens_generated_estimate"] == 10
    assert out_resp["backend_task_id"] == 2


def test_evaluate_question_3way_non_vl_happy_path():
    rr_direct = _rr(role="frontdoor", mode="direct", passed=True, error_type="none", elapsed_seconds=2.0)
    rr_repl = _rr(role="frontdoor", mode="repl", passed=False, error_type="none", elapsed_seconds=3.0)
    rr_arch_g = _rr(role="architect_general", mode="delegated", passed=False, error_type="none", elapsed_seconds=4.0)

    with (
        patch.object(_MOD, "ROLE_PORT", {"frontdoor": 8080, "architect_general": 8083}),
        patch.object(_MOD, "_erase_slots"),
        patch.object(_MOD, "_adaptive_timeout_s", return_value=100),
        patch.object(_MOD, "_bump_timeout_from_observed", side_effect=lambda **kw: kw["current_s"]),
        patch.object(_MOD, "_compute_3way_metadata", return_value={"meta": 1}),
        patch.object(_MOD, "score_delegation_chain", return_value={"WORKER": 1.0}),
        # The ARCHITECT arm fans out over every LIVE architect_* role, so the
        # number of _eval_single_config calls tracks the deployed lineup. This
        # test is about the 3-way plumbing (result keys, reward mapping,
        # scoring_context), so declare the roster instead of inheriting it.
        # Multi-architect fan-out is covered by the _compute_3way_metadata /
        # architect_eval.by_role tests.
        patch.object(_MOD, "_non_vl_architect_roles_to_eval", return_value=["architect_general"]),
        patch.object(_MOD, "_eval_single_config", side_effect=[(rr_direct, {}), (rr_repl, {}), (rr_arch_g, {})]),
        patch.object(_MOD.logger, "info"),
    ):
        role_results, rewards, metadata = _MOD.evaluate_question_3way(
            prompt_info={
                "prompt": "Implement a parser",
                "expected": "ok",
                "scoring_method": "exact_match",
                "scoring_config": {},
                "suite": "coder",
            },
            url="http://localhost:8000",
            timeout=300,
            client=object(),
        )

    assert "frontdoor:direct" in role_results
    assert "frontdoor:repl" in role_results
    assert "architect_general:delegated" in role_results
    assert rewards[_MOD.ACTION_SELF_DIRECT] == 1.0
    assert rewards[_MOD.ACTION_SELF_REPL] == 0.0
    assert rewards[_MOD.ACTION_ARCHITECT] == 0.0
    assert rewards["WORKER"] == 1.0
    assert metadata["meta"] == 1
    # REL-1 finding 3: evaluate_question_3way appends the offline re-scoring
    # context (untruncated expected + scoring method/config) so a completed
    # seed run can be re-scored without re-inference.
    assert metadata["scoring_context"] == {
        "expected": "ok",
        "scoring_method": "exact_match",
        "scoring_config": {},
    }


def test_evaluate_question_3way_direct_retry_on_5xx_replaces_result():
    rr_direct_infra = _rr(role="frontdoor", mode="direct", passed=False, error_type="infrastructure", error="Server error '503'")
    rr_direct_retry = _rr(role="frontdoor", mode="direct", passed=True, error_type="none")
    rr_repl = _rr(role="frontdoor", mode="repl", passed=True, error_type="none")
    rr_arch = _rr(role="architect_general", mode="delegated", passed=True, error_type="none")

    with (
        patch.object(_MOD, "ROLE_PORT", {"frontdoor": 8080, "architect_general": 8083}),
        patch.object(_MOD, "HEAVY_PORTS", {8080}),
        patch.object(_MOD, "_erase_slots"),
        patch.object(_MOD, "_force_erase_and_verify"),
        patch.object(_MOD, "_busy_heavy_ports", return_value=[]),
        patch.object(_MOD, "_recover_heavy_ports_if_stuck", return_value=True),
        patch.object(_MOD, "_adaptive_timeout_s", return_value=100),
        patch.object(_MOD, "_bump_timeout_from_observed", side_effect=lambda **kw: kw["current_s"]),
        patch.object(_MOD, "_compute_3way_metadata", return_value={}),
        patch.object(_MOD, "score_delegation_chain", return_value={}),
        # Declare the architect fan-out roster (see the happy-path test): this
        # test is about the 5xx retry contract, not about how many architect
        # instances are deployed.
        patch.object(_MOD, "_non_vl_architect_roles_to_eval", return_value=["architect_general"]),
        patch.object(
            _MOD,
            "_eval_single_config",
            side_effect=[
                (rr_direct_infra, {}),
                (rr_direct_retry, {}),  # retry direct
                (rr_repl, {}),
                (rr_arch, {}),
            ],
        ),
        patch.object(_MOD.logger, "info"),
    ):
        role_results, rewards, _metadata = _MOD.evaluate_question_3way(
            prompt_info={
                "prompt": "general prompt",
                "expected": "ok",
                "suite": "general",
            },
            url="http://localhost:8000",
            timeout=300,
            client=object(),
        )

    assert role_results["frontdoor:direct"].passed is True
    assert rewards[_MOD.ACTION_SELF_DIRECT] == 1.0


def test_log_delegation_diag_and_tap_helpers_cover_fallbacks():
    with patch.object(_MOD.logger, "info") as info_mock:
        _MOD._log_delegation_diag("LBL", {})
        info_mock.assert_not_called()

        _MOD._log_delegation_diag(
            "LBL",
            {
                "loops": 2,
                "cap_reached": True,
                "break_reason": "cap",
                "repeated_edges": {"a->b": 1},
                "repeated_roles": {"a": 2},
                "delegation_inference_hops": 3,
                "avg_prompt_ms": 4.0,
                "avg_gen_ms": 5.0,
                "report_handles_count": 2,
                "report_handles": [{"id": "h1"}, {"id": "h2"}, "ignore"],
            },
        )
        info_mock.assert_called_once()

    with patch.object(_MOD.os.path, "getsize", return_value=123):
        assert _MOD._tap_size() == 123
        assert _MOD._repl_tap_size() == 123
    with patch.object(_MOD.os.path, "getsize", side_effect=OSError("missing")):
        assert _MOD._tap_size() == 0
        assert _MOD._repl_tap_size() == 0


def test_build_role_result_task_failure_marks_failed_without_scoring():
    with (
        patch.object(_MOD, "_classify_error", return_value="task_failure"),
        patch.object(_MOD, "score_answer_or_error") as score_mock,
    ):
        rr, err_type = _MOD._build_role_result(
            role="frontdoor",
            mode="direct",
            resp={"answer": "bad", "error": "bad output"},
            elapsed=1.0,
            expected="good",
            scoring_method="exact_match",
            scoring_config={},
        )
    assert err_type == "task_failure"
    assert rr.passed is False
    score_mock.assert_not_called()


def test_eval_single_config_precheck_recovery_and_client_timeout_skip_retry():
    rr_timeout = _rr(
        role="frontdoor",
        mode="direct",
        passed=False,
        error="ReadTimeout while waiting",
        error_type="infrastructure",
    )
    log_lines: list[str] = []
    with (
        patch.object(_MOD, "ROLE_PORT", {"frontdoor": 8080}),
        patch.object(_MOD, "HEAVY_PORTS", {8080}),
        patch.object(_MOD, "_wait_for_heavy_models_idle"),
        patch.object(_MOD, "_erase_slots"),
        patch.object(_MOD, "_busy_heavy_ports", side_effect=[[8080], [8080]]),
        patch.object(_MOD, "_recover_heavy_ports_if_stuck", return_value=True) as recover_mock,
        patch.object(_MOD.time, "sleep"),
        patch.object(
            _MOD,
            "_call_orchestrator_with_slot_poll",
            return_value=(
                {"answer": "", "error": "ReadTimeout while waiting", "tokens_generated": 0},
                2.0,
                {"max_decoded": 0, "task_id": 9, "source": "slots_poll"},
            ),
        ) as call_mock,
        patch.object(_MOD, "_build_role_result", return_value=(rr_timeout, "infrastructure")),
        patch.object(_MOD, "_tap_size", side_effect=[10, 12]),
        patch.object(_MOD, "_repl_tap_size", side_effect=[20, 21]),
        patch.object(_MOD, "_log_delegation_diag"),
        patch.object(_MOD, "_force_erase_and_verify") as force_mock,
        patch.object(_MOD.logger, "info", side_effect=lambda line, *a, **k: log_lines.append(str(line))),
    ):
        rr, resp = _MOD._eval_single_config(
            prompt="p",
            expected="e",
            scoring_method="exact_match",
            scoring_config={},
            role="frontdoor",
            mode="direct",
            url="http://localhost:8000",
            timeout=60,
            client=object(),
            allow_delegation=False,
            log_label="SELF:direct",
            format_fn=None,
        )

    assert rr.error_type == "infrastructure"
    assert resp["backend_task_id"] == 9
    recover_mock.assert_called_once()
    force_mock.assert_called_once_with(8080)
    assert call_mock.call_count == 1
    assert any("[skip-retry]" in line for line in log_lines)


def test_compute_3way_metadata_arch_selection_and_none_skips():
    role_results = {
        "frontdoor:direct": _rr(role="frontdoor", mode="direct", passed=True, tools_called=[]),
        "frontdoor:repl": _rr(
            role="frontdoor",
            mode="repl",
            passed=False,
            tools_called=["web_research"],
            web_research_results=[{"query": "q"}],
        ),
        "architect_general:delegated": _rr(role="architect_general", mode="delegated", passed=True, generation_ms=200.0),
        "architect_code_specialist:delegated": _rr(
            role="architect_code_specialist",
            mode="delegated",
            passed=True,
            generation_ms=100.0,
        ),
        "unused:none": None,
    }
    arch_results = {
        "architect_general": {"passed": True, "elapsed_seconds": 4.0, "generation_ms": 200.0},
        "architect_code_specialist": {"passed": True, "elapsed_seconds": 5.0, "generation_ms": 100.0},
    }
    with (
        patch.object(_MOD, "_architect_result_order", return_value=["architect_general", "architect_code_specialist"]),
        patch.object(
            _MOD,
            "extract_web_research_telemetry",
            return_value=SimpleNamespace(
                call_count=0,
                total_pages_fetched=0,
                total_pages_synthesized=0,
                total_elapsed_ms=0.0,
                unique_domains=0,
                queries=[],
            ),
        ),
        patch.object(_MOD, "compute_web_research_rewards", return_value={}),
        patch.object(_MOD, "score_query_strategy", return_value={}),
        patch.object(_MOD, "compute_scratchpad_rewards", return_value={}),
    ):
        md = _MOD._compute_3way_metadata(
            role_results=role_results,
            arch_results=arch_results,
            prompt="coding task",
            suite="s",
            passed_direct=True,
            passed_repl=False,
            self_role="frontdoor",
            self_direct_mode="direct",
            self_repl_mode="repl",
            arch_mode="delegated",
        )
    assert md["architect_role"] == "architect_code_specialist"
    assert md["web_research_baseline"]["call_count"] == 1
    assert "web_research_rewards" not in md


def test_compute_3way_metadata_arch_fallback_chooses_first_non_infra():
    role_results = {
        "frontdoor:direct": _rr(role="frontdoor", mode="direct", passed=False),
        "frontdoor:repl": _rr(role="frontdoor", mode="repl", passed=False),
        "architect_general:delegated": _rr(role="architect_general", mode="delegated", passed=False),
    }
    arch_results = {
        "architect_general": {"passed": False, "elapsed_seconds": 3.0, "generation_ms": 50.0},
        "architect_code_specialist": {"passed": None, "elapsed_seconds": 4.0, "generation_ms": 70.0},
    }
    md = _MOD._compute_3way_metadata(
        role_results=role_results,
        arch_results=arch_results,
        prompt="general task",
        suite="s",
        passed_direct=False,
        passed_repl=False,
        self_role="frontdoor",
        self_direct_mode="direct",
        self_repl_mode="repl",
        arch_mode="delegated",
    )
    assert md["architect_role"] == "architect_general"
    assert _MOD.ACTION_ARCHITECT in md["cost_metrics"]


def test_evaluate_question_3way_vl_infra_skip_and_cooldown(monkeypatch):
    rr_direct = _rr(role="worker_vision", mode="direct", passed=False, error_type="infrastructure", error="fail")
    rr_repl = _rr(role="worker_vision", mode="repl", passed=False, error_type="infrastructure", error="fail")
    rr_arch = _rr(role="vision_escalation", mode="direct", passed=False, error_type="infrastructure", error="fail")

    fake_eval_log = SimpleNamespace(
        format_self_direct=lambda *a, **k: [],
        format_self_repl=lambda *a, **k: [],
        format_architect_result=lambda *a, **k: [],
        format_reward_skip=lambda action: [f"skip:{action}"],
        format_all_infra_skip=lambda action: [f"all-infra:{action}"],
    )
    monkeypatch.setitem(sys.modules, "eval_log_format", fake_eval_log)

    with (
        patch.object(_MOD, "ROLE_PORT", {"worker_vision": 8086, "vision_escalation": 8087}),
        patch.object(_MOD, "HEAVY_PORTS", set()),
        patch.object(_MOD, "_erase_slots"),
        patch.object(_MOD, "_adaptive_timeout_s", return_value=90),
        patch.object(_MOD, "_bump_timeout_from_observed", side_effect=lambda **kw: kw["current_s"]),
        patch.object(
            _MOD,
            "_eval_single_config",
            side_effect=[(rr_direct, {}), (rr_repl, {}), (rr_arch, {})],
        ),
        patch.object(_MOD, "_compute_3way_metadata", return_value={"meta": 1}),
        patch.object(_MOD, "score_delegation_chain", return_value={"WORKER": 1.0}),
        patch.object(_MOD.time, "sleep") as sleep_mock,
        patch.object(_MOD.logger, "info") as info_mock,
    ):
        role_results, rewards, metadata = _MOD.evaluate_question_3way(
            prompt_info={
                "prompt": "describe image",
                "expected": "ok",
                "suite": "vision",
                "image_path": "/tmp/x.png",
            },
            url="http://localhost:8000",
            timeout=300,
            client=object(),
            cooldown_s=0.1,
        )

    assert "worker_vision:direct" in role_results
    assert "worker_vision:repl" in role_results
    assert "vision_escalation:direct" in role_results
    assert rewards == {"WORKER": 1.0}
    assert metadata["meta"] == 1
    # REL-1 finding 3: evaluate_question_3way appends the offline re-scoring
    # context (untruncated expected + scoring method/config) so a completed
    # seed run can be re-scored without re-inference.
    assert metadata["scoring_context"] == {
        "expected": "ok",
        "scoring_method": "exact_match",
        "scoring_config": {},
    }
    assert sleep_mock.call_count == 3
    logged = [str(args[0]) for args, _ in info_mock.call_args_list if args]
    assert any("skip:SELF:direct" in line for line in logged)
    assert any("skip:SELF:repl" in line for line in logged)
    assert any("all-infra:ARCHITECT" in line for line in logged)
    assert any("reward[WORKER] = 1.0" in line for line in logged)


def test_threeway_result_checkpoint_persists_raw_answer_and_scoring_context():
    # REL-1 finding 3: a completed seed run must be re-scorable offline. The
    # checkpoint serialises ThreeWayResult via dataclasses.asdict, which
    # recursively preserves each role's raw ``answer``; evaluate_question_3way
    # additionally stores the untruncated scoring context in metadata (the
    # ThreeWayResult.expected field itself is truncated to 200 chars).
    import json
    from dataclasses import asdict

    rr = _rr(role="frontdoor", mode="direct", answer="The full raw model answer.", passed=True)
    result = _MOD.ThreeWayResult(
        suite="math",
        question_id="q1",
        prompt="p" * 500,
        expected="e" * 500,
        role_results={"frontdoor:direct": rr},
        metadata={
            "scoring_context": {
                "expected": "e" * 500,
                "scoring_method": "math_verify",
                "scoring_config": {"threshold": 1.0},
            }
        },
    )
    # Serialise exactly as checkpoint_result does (asdict + json), then read back.
    back = json.loads(json.dumps(asdict(result), ensure_ascii=False))
    assert back["role_results"]["frontdoor:direct"]["answer"] == "The full raw model answer."
    sc = back["metadata"]["scoring_context"]
    assert sc["scoring_method"] == "math_verify"
    assert sc["scoring_config"] == {"threshold": 1.0}
    assert len(sc["expected"]) == 500  # untruncated, unlike ThreeWayResult.expected
