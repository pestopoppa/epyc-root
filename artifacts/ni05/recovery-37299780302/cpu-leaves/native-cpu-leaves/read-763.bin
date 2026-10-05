"""Unit tests for benchmark seeding_legacy helper module."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock, patch

import pytest


_ROOT = Path(__file__).resolve().parents[2] / "scripts" / "benchmark"
sys.path.insert(0, str(_ROOT))
_SPEC = importlib.util.spec_from_file_location("seeding_legacy_test", _ROOT / "seeding_legacy.py")
_MOD = importlib.util.module_from_spec(_SPEC)
sys.modules["seeding_legacy_test"] = _MOD
_SPEC.loader.exec_module(_MOD)


@pytest.fixture(autouse=True)
def _reset_shutdown_state():
    """Isolate cross-module global shutdown state between tests."""
    _MOD.state.shutdown = False
    yield
    _MOD.state.shutdown = False


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


def _comp(qid: str, *, rewards_injected: int = 0, error: str | None = None):
    rr = _rr(error=error)
    return _MOD.ComparativeResult(
        suite="math",
        question_id=qid,
        prompt="p",
        expected="e",
        role_results={"frontdoor:direct": rr},
        rewards={"frontdoor:direct": 1.0},
        rewards_injected=rewards_injected,
    )


def test_build_role_mode_combos_handles_light_heavy_and_architect_modes():
    combos = _MOD._build_role_mode_combos(
        roles=["worker_math", "frontdoor", "architect_general"],
        modes=["direct", "repl"],
    )
    # Light combos present
    assert ("worker_math", "direct") in combos
    assert ("worker_math", "repl") in combos
    # Architect delegated mode is auto-added via ARCHITECT_MODES
    assert ("architect_general", "delegated") in combos
    # Heavy frontdoor combos also included
    assert ("frontdoor", "direct") in combos


def test_build_role_mode_combos_edge_cases_no_heavy_or_no_light():
    # No heavy combos
    light_only = _MOD._build_role_mode_combos(["worker_math"], ["direct"])
    assert light_only == [("worker_math", "direct")]

    # No light combos
    heavy_only = _MOD._build_role_mode_combos(["architect_general"], ["direct"])
    assert ("architect_general", "direct") in heavy_only
    assert ("architect_general", "delegated") in heavy_only


def test_build_role_mode_combos_strict_modes_keeps_explicit_modes_only():
    combos = _MOD._build_role_mode_combos(
        ["architect_general", "frontdoor"],
        ["direct"],
        strict_modes=True,
    )

    assert ("architect_general", "direct") in combos
    assert ("frontdoor", "direct") in combos
    assert ("architect_general", "delegated") not in combos
    assert ("architect_general", "repl") not in combos


def test_build_role_mode_combos_vision_branch_uses_vision_modes():
    vision_modes = sorted(_MOD.VISION_MODES.get("worker_vision", {"direct"}))
    with (
        patch.object(_MOD, "ROLE_PORT", {"worker_vision": 8086}),
        patch.object(_MOD, "HEAVY_PORTS", {8086}),
    ):
        combos = _MOD._build_role_mode_combos(["worker_vision"], vision_modes)
    assert all(role == "worker_vision" for role, _ in combos)
    assert set(mode for _, mode in combos) == set(vision_modes)


def test_deduplicate_roles_with_explicit_and_default_server_maps():
    unique, aliases = _MOD._deduplicate_roles(
        ["r1", "r2", "r3"],
        server_urls={"r1": "http://a", "r2": "http://a", "r3": ""},
    )
    assert unique == ["r1", "r3"]
    assert aliases == {"r2": "r1"}

    fake_cfg = SimpleNamespace(server_urls=SimpleNamespace(as_dict=lambda: {"x": "u", "y": "u"}))
    with patch("src.config.get_config", return_value=fake_cfg):
        unique2, aliases2 = _MOD._deduplicate_roles(["x", "y"], server_urls=None)
    assert unique2 == ["x"]
    assert aliases2 == {"y": "x"}


def test_modes_for_role_architect_vision_and_default():
    assert _MOD._modes_for_role("architect_general", ["direct"]) == sorted(_MOD.ARCHITECT_MODES)
    assert _MOD._modes_for_role("worker_vision", ["direct", "repl"]) == sorted(
        _MOD.VISION_MODES.get("worker_vision", {"direct"})
    )
    assert _MOD._modes_for_role("frontdoor", ["direct", "repl"]) == ["direct", "repl"]


def test_modes_for_role_strict_modes_keeps_explicit_modes_for_aliases():
    assert _MOD._modes_for_role(
        "architect_general",
        ["direct"],
        strict_modes=True,
    ) == ["direct"]


def test_evaluate_question_text_path_alias_clone_and_escalation_injection():
    prompt_info = {
        "suite": "math",
        "id": "q1",
        "prompt": "What is 2+2?",
        "expected": "4",
        "reference": "Four",
    }
    combos = [("frontdoor", "direct"), ("worker_math", "direct")]

    with (
        patch.object(_MOD, "ROLE_PORT", {"frontdoor": 8080, "worker_math": 8082}),
        patch.object(_MOD, "HEAVY_PORTS", {8080}),
        patch.object(_MOD, "_wait_for_heavy_models_idle"),
        patch.object(
            _MOD,
            "call_orchestrator_forced",
            side_effect=[
                {"answer": "4", "error": None, "tokens_generated": 5, "tools_used": 0, "tools_called": []},
                {"answer": "3", "error": None, "tokens_generated": 4, "tools_used": 1, "tools_called": ["calc"]},
            ],
        ) as call_mock,
        patch.object(_MOD, "score_answer_or_error", side_effect=[(True, None), (False, None)]),
        patch.object(_MOD, "compute_comparative_rewards", return_value={"frontdoor:direct": 1.0, "worker_math:direct": 0.2}),
        patch.object(_MOD, "_inject_rewards_http", return_value=2),
        patch.object(
            _MOD,
            "detect_escalation_chains",
            return_value=[{"from_role": "worker_math", "from_mode": "direct", "to_role": "architect_general", "to_mode": "delegated", "reward": 0.8}],
        ),
        patch.object(_MOD, "_inject_escalation_chains_http", return_value=1),
        patch.object(_MOD.logger, "info"),
    ):
        comp = _MOD.evaluate_question(
            prompt_info=prompt_info,
            combos=combos,
            alias_map={"worker_explore": "worker_math"},
            modes=["direct"],
            url="http://localhost:8000",
            timeout=60,
            client=object(),
            dry_run=False,
            escalation_chains=True,
            max_tokens=1024,
        )

    assert comp is not None
    assert [call.kwargs["max_tokens"] for call in call_mock.call_args_list] == [1024, 1024]
    assert comp.rewards_injected == 3
    assert comp.reference == "Four"
    # Alias clone path
    assert comp.rewards["worker_explore:direct"] == 0.2
    assert "worker_explore:direct" in comp.role_results


def test_evaluate_question_vl_filters_combos_and_erases_heavy_on_zero_token_error():
    prompt_info = {
        "suite": "vl",
        "id": "q2",
        "prompt": "Describe image",
        "expected": "cat",
        "image_path": "/tmp/fake.png",
    }
    combos = [("frontdoor", "direct"), ("worker_vision", "repl"), ("worker_math", "direct")]

    with (
        patch.object(_MOD, "ROLE_PORT", {"frontdoor": 8080, "worker_vision": 8086, "worker_math": 8082}),
        patch.object(_MOD, "HEAVY_PORTS", {8080}),
        patch.object(_MOD, "_wait_for_heavy_models_idle"),
        patch.object(_MOD, "_erase_slots") as erase,
        patch.object(
            _MOD,
            "call_orchestrator_forced",
            side_effect=[
                {"answer": "", "error": "backend down", "tokens_generated": 0},
                {"answer": "cat", "error": None, "tokens_generated": 3},
            ],
        ),
        patch.object(_MOD, "score_answer_or_error", return_value=(True, None)),
        patch.object(_MOD, "compute_comparative_rewards", return_value={}),
        patch.object(_MOD.logger, "info"),
    ):
        comp = _MOD.evaluate_question(
            prompt_info=prompt_info,
            combos=combos,
            alias_map={},
            modes=["direct", "repl"],
            url="http://localhost:8000",
            timeout=60,
            client=object(),
            dry_run=True,
        )

    assert comp is not None
    assert set(comp.role_results.keys()) == {"frontdoor:direct", "worker_vision:repl"}
    erase.assert_called_once_with(8080)


def test_evaluate_question_inband_error_is_infrastructure_and_skips_rewards():
    prompt_info = {"suite": "math", "id": "inband", "prompt": "p", "expected": "e"}
    with (
        patch.object(_MOD, "ROLE_PORT", {"frontdoor": 8080}),
        patch.object(_MOD, "HEAVY_PORTS", set()),
        patch.object(
            _MOD,
            "call_orchestrator_forced",
            return_value={"answer": "[ERROR: circuit open]", "error": None},
        ),
        patch.object(_MOD, "compute_comparative_rewards") as compute_rewards,
        patch.object(_MOD, "_inject_rewards_http") as inject_rewards,
    ):
        result = _MOD.evaluate_question(
            prompt_info=prompt_info,
            combos=[("frontdoor", "direct")],
            alias_map={},
            modes=["direct"],
            url="http://localhost:8000",
            timeout=30,
            client=object(),
        )

    assert result is not None
    rr = result.role_results["frontdoor:direct"]
    assert rr.error_type == "infrastructure"
    assert result.rewards == {}
    compute_rewards.assert_not_called()
    inject_rewards.assert_not_called()


def test_evaluate_question_unavailable_scorer_is_infrastructure_and_skips_rewards():
    prompt_info = {"suite": "math", "id": "scorer", "prompt": "p", "expected": "e"}
    with (
        patch.object(_MOD, "ROLE_PORT", {"frontdoor": 8080}),
        patch.object(_MOD, "HEAVY_PORTS", set()),
        patch.object(
            _MOD,
            "call_orchestrator_forced",
            return_value={"answer": "answer", "error": None},
        ),
        patch.object(
            _MOD,
            "score_answer_or_error",
            return_value=(None, "scoring_unavailable: oracle unavailable"),
        ),
        patch.object(_MOD, "compute_comparative_rewards") as compute_rewards,
        patch.object(_MOD, "_inject_rewards_http") as inject_rewards,
    ):
        result = _MOD.evaluate_question(
            prompt_info=prompt_info,
            combos=[("frontdoor", "direct")],
            alias_map={},
            modes=["direct"],
            url="http://localhost:8000",
            timeout=30,
            client=object(),
        )

    assert result is not None
    rr = result.role_results["frontdoor:direct"]
    assert rr.error_type == "infrastructure"
    assert rr.error == "scoring_unavailable: oracle unavailable"
    assert result.rewards == {}
    compute_rewards.assert_not_called()
    inject_rewards.assert_not_called()


def test_evaluate_question_returns_none_when_shutdown_requested():
    _MOD.state.shutdown = True
    try:
        out = _MOD.evaluate_question(
            prompt_info={"suite": "math", "id": "q", "prompt": "p"},
            combos=[("frontdoor", "direct")],
            alias_map={},
            modes=["direct"],
            url="http://localhost:8000",
            timeout=30,
            client=object(),
        )
        assert out is None
    finally:
        _MOD.state.shutdown = False


def test_evaluate_question_logging_and_cooldown_paths():
    prompt_info = {"suite": "math", "id": "qlog", "prompt": "p", "expected": "e"}
    combos = [("frontdoor", "direct"), ("worker_math", "direct")]
    log_lines: list[str] = []
    with (
        patch.object(_MOD, "ROLE_PORT", {"frontdoor": 8080, "worker_math": 8082}),
        patch.object(_MOD, "HEAVY_PORTS", set()),
        patch.object(_MOD, "call_orchestrator_forced", side_effect=[
            {
                "answer": "e",
                "error": None,
                "tokens_generated": 7,
                "tools_used": 1,
                "tools_called": [],
                "role_history": ["frontdoor", "worker_math"],
                "formalization_applied": True,
                "predicted_tps": 2.0,
                "generation_ms": 1000.0,
                "prompt_eval_ms": 2000.0,
            },
            {"answer": "e", "error": None, "tokens_generated": 2},
        ]),
        patch.object(_MOD, "score_answer_or_error", return_value=(True, None)),
        patch.object(_MOD, "compute_comparative_rewards", return_value={}),
        patch.object(_MOD.time, "sleep") as sleep_mock,
        patch.object(_MOD.logger, "info", side_effect=lambda line, *a, **k: log_lines.append(str(line))),
    ):
        comp = _MOD.evaluate_question(
            prompt_info=prompt_info,
            combos=combos,
            alias_map={},
            modes=["direct"],
            url="http://localhost:8000",
            timeout=60,
            client=object(),
            cooldown=0.1,
            dry_run=True,
        )

    assert comp is not None
    sleep_mock.assert_called_once_with(0.1)
    assert any("2.0 t/s" in line for line in log_lines)
    assert any("chain:" in line for line in log_lines)
    assert any("tools(1): ?" in line for line in log_lines)
    assert any("gen=1.0s, prompt=2.0s, formalized" in line for line in log_lines)


def test_run_batch_raises_when_server_unreachable():
    with patch.object(_MOD, "_check_server_health", return_value=False):
        with pytest.deprecated_call(match="Legacy comparative seeding is deprecated"):
            with pytest.raises(_MOD.HealthCheckError):
                _MOD.run_batch(
                    suites=["math"],
                    roles=["frontdoor"],
                    modes=["direct"],
                    sample_per_suite=1,
                    seed=1,
                    url="http://localhost:8000",
                    timeout=60,
                    session_id="sess-x",
                    no_dedup=True,
                )


def test_run_batch_returns_completed_when_no_new_questions():
    stub = ModuleType("seed_specialist_routing")
    stub.sample_unseen_questions = lambda *a, **k: []
    prev = sys.modules.get("seed_specialist_routing")
    sys.modules["seed_specialist_routing"] = stub
    try:
        with (
            patch.object(_MOD, "_check_server_health", return_value=True),
            patch.object(_MOD, "load_checkpoint", return_value=[_comp("q-done")]),
            patch.object(_MOD, "load_seen_questions", return_value={"q-done"}),
            patch.object(_MOD, "_build_role_mode_combos", return_value=[("frontdoor", "direct")]),
            patch.object(_MOD.logger, "info"),
        ):
            with pytest.deprecated_call(match="Legacy comparative seeding is deprecated"):
                out = _MOD.run_batch(
                    suites=["math"],
                    roles=["frontdoor"],
                    modes=["direct"],
                    sample_per_suite=1,
                    seed=1,
                    url="http://localhost:8000",
                    timeout=60,
                    session_id="sess-empty",
                    no_dedup=True,
                )
    finally:
        if prev is None:
            sys.modules.pop("seed_specialist_routing", None)
        else:
            sys.modules["seed_specialist_routing"] = prev

    assert len(out) == 1
    assert out[0].question_id == "q-done"


def test_run_batch_forwards_prompt_source_overrides_to_imported_sampler(tmp_path):
    calls = []
    stub = ModuleType("seed_specialist_routing")

    def _sample_unseen_questions(*_args, **kwargs):
        calls.append(
            {
                "kwargs": kwargs,
                "debug_prompts_dir": getattr(stub, "DEBUG_PROMPTS_DIR", None),
            }
        )
        return []

    stub.sample_unseen_questions = _sample_unseen_questions
    prev = sys.modules.get("seed_specialist_routing")
    sys.modules["seed_specialist_routing"] = stub
    prompt_dir = tmp_path / "prompts"
    try:
        with (
            patch.object(_MOD, "_check_server_health", return_value=True),
            patch.object(_MOD, "load_checkpoint", return_value=[]),
            patch.object(_MOD, "load_seen_questions", return_value=set()),
            patch.object(_MOD, "_build_role_mode_combos", return_value=[("frontdoor", "direct")]),
            patch.object(_MOD.logger, "info"),
        ):
            with pytest.deprecated_call(match="Legacy comparative seeding is deprecated"):
                out = _MOD.run_batch(
                    suites=["instruction_precision"],
                    roles=["frontdoor"],
                    modes=["direct"],
                    sample_per_suite=1,
                    seed=1,
                    url="http://localhost:8000",
                    timeout=60,
                    session_id="sess-prompt-source",
                    no_dedup=True,
                    question_source="yaml",
                    debug_prompts_dir=prompt_dir,
                )
    finally:
        if prev is None:
            sys.modules.pop("seed_specialist_routing", None)
        else:
            sys.modules["seed_specialist_routing"] = prev

    assert out == []
    assert calls == [
        {
            "kwargs": {
                "use_pool": True,
                "allow_reseen": False,
                "question_source": "yaml",
            },
            "debug_prompts_dir": prompt_dir.resolve(),
        }
    ]


def test_run_batch_main_loop_records_checkpoint_and_stops_after_three_zero_success():
    questions = [
        {"suite": "math", "id": "q1", "prompt": "p1"},
        {"suite": "math", "id": "q2", "prompt": "p2"},
        {"suite": "math", "id": "q3", "prompt": "p3"},
        {"suite": "math", "id": "q4", "prompt": "p4"},
    ]
    stub = ModuleType("seed_specialist_routing")
    stub.sample_unseen_questions = lambda *a, **k: questions
    prev = sys.modules.get("seed_specialist_routing")
    sys.modules["seed_specialist_routing"] = stub

    comp1 = _comp("q1", rewards_injected=1, error="err")
    comp2 = _comp("q2", rewards_injected=0, error="err")
    comp3 = _comp("q3", rewards_injected=0, error="err")

    fake_client = Mock()
    try:
        with (
            patch.object(_MOD, "_check_server_health", return_value=True),
            patch.object(_MOD, "load_checkpoint", return_value=[]),
            patch.object(_MOD, "load_seen_questions", return_value=set()),
            patch.object(_MOD, "_build_role_mode_combos", return_value=[("frontdoor", "direct")]),
            patch.object(_MOD, "evaluate_question", side_effect=[comp1, comp2, comp3]) as eval_q,
            patch.object(_MOD, "append_checkpoint") as append_cp,
            patch.object(_MOD, "record_seen") as rec_seen,
            patch("httpx.Client", return_value=fake_client),
            patch.object(_MOD.logger, "info"),
            patch.object(_MOD.logger, "error"),
        ):
            with pytest.deprecated_call(match="Legacy comparative seeding is deprecated"):
                out = _MOD.run_batch(
                    suites=["math"],
                    roles=["frontdoor"],
                    modes=["direct"],
                    sample_per_suite=4,
                    seed=1,
                    url="http://localhost:8000",
                    timeout=60,
                    session_id="sess-loop",
                    no_dedup=True,
                )
    finally:
        if prev is None:
            sys.modules.pop("seed_specialist_routing", None)
        else:
            sys.modules["seed_specialist_routing"] = prev

    assert len(out) == 3
    assert eval_q.call_count == 3  # stopped early after 3 consecutive zero-success questions
    assert append_cp.call_count == 3
    rec_seen.assert_called_once_with("q1", "math", "sess-loop")
    fake_client.close.assert_called_once()


def test_run_batch_dedup_logs_alias_and_stops_when_shutdown_set():
    stub = ModuleType("seed_specialist_routing")
    stub.sample_unseen_questions = lambda *a, **k: [{"suite": "math", "id": "q1", "prompt": "p1"}]
    prev = sys.modules.get("seed_specialist_routing")
    sys.modules["seed_specialist_routing"] = stub
    cfg = SimpleNamespace(server_urls=SimpleNamespace(as_dict=lambda: {"frontdoor": "http://localhost:8080"}))
    _MOD.state.shutdown = True
    try:
        with (
            patch.object(_MOD, "_check_server_health", return_value=True),
            patch.object(_MOD, "_deduplicate_roles", return_value=(["frontdoor"], {"worker_math": "frontdoor"})),
            patch("src.config.get_config", return_value=cfg),
            patch.object(_MOD, "load_checkpoint", return_value=[]),
            patch.object(_MOD, "load_seen_questions", return_value=set()),
            patch.object(_MOD, "_build_role_mode_combos", return_value=[("frontdoor", "direct")]),
            patch.object(_MOD, "evaluate_question") as eval_q,
            patch.object(_MOD.logger, "info") as info_mock,
        ):
            with pytest.deprecated_call(match="Legacy comparative seeding is deprecated"):
                out = _MOD.run_batch(
                    suites=["math"],
                    roles=["frontdoor", "worker_math"],
                    modes=["direct"],
                    sample_per_suite=1,
                    seed=1,
                    url="http://localhost:8000",
                    timeout=60,
                    session_id="sess-shutdown",
                )
    finally:
        _MOD.state.shutdown = False
        if prev is None:
            sys.modules.pop("seed_specialist_routing", None)
        else:
            sys.modules["seed_specialist_routing"] = prev

    assert out == []
    eval_q.assert_not_called()
    logged = [str(c.args[0]) for c in info_mock.call_args_list if c.args]
    assert any("Dedup: worker_math" in line for line in logged)
    assert any("Stopped after 0 questions" in line for line in logged)


def test_run_batch_breaks_when_evaluate_question_returns_none_after_success():
    questions = [
        {"suite": "math", "id": "q1", "prompt": "p1"},
        {"suite": "math", "id": "q2", "prompt": "p2"},
    ]
    stub = ModuleType("seed_specialist_routing")
    stub.sample_unseen_questions = lambda *a, **k: questions
    prev = sys.modules.get("seed_specialist_routing")
    sys.modules["seed_specialist_routing"] = stub
    fake_client = Mock()
    comp_ok = _comp("q1", rewards_injected=1, error=None)
    try:
        with (
            patch.object(_MOD, "_check_server_health", return_value=True),
            patch.object(_MOD, "load_checkpoint", return_value=[]),
            patch.object(_MOD, "load_seen_questions", return_value=set()),
            patch.object(_MOD, "_build_role_mode_combos", return_value=[("frontdoor", "direct")]),
            patch.object(_MOD, "evaluate_question", side_effect=[comp_ok, None]) as eval_q,
            patch.object(_MOD, "append_checkpoint") as append_cp,
            patch.object(_MOD, "record_seen") as rec_seen,
            patch("httpx.Client", return_value=fake_client),
            patch.object(_MOD.logger, "info"),
            patch.object(_MOD.logger, "error"),
        ):
            with pytest.deprecated_call(match="Legacy comparative seeding is deprecated"):
                out = _MOD.run_batch(
                    suites=["math"],
                    roles=["frontdoor"],
                    modes=["direct"],
                    sample_per_suite=2,
                    seed=1,
                    url="http://localhost:8000",
                    timeout=60,
                    session_id="sess-none-break",
                    no_dedup=True,
                )
    finally:
        if prev is None:
            sys.modules.pop("seed_specialist_routing", None)
        else:
            sys.modules["seed_specialist_routing"] = prev

    assert len(out) == 1
    assert eval_q.call_count == 2
    append_cp.assert_called_once()
    rec_seen.assert_called_once_with("q1", "math", "sess-none-break")
    fake_client.close.assert_called_once()


def test_print_batch_summary_emits_expected_sections(capsys):
    results = [
        _MOD.ComparativeResult(
            suite="math",
            question_id="q1",
            prompt="p",
            expected="e",
            role_results={
                "frontdoor:direct": _rr(role="frontdoor", mode="direct", passed=True, error=None, tokens_generated=10, elapsed_seconds=2.0, predicted_tps=5.0),
            },
            rewards={"frontdoor:direct": 1.0},
            rewards_injected=1,
        )
    ]
    _MOD.print_batch_summary(results, roles=["frontdoor"], modes=["direct"], alias_map={"worker_explore": "worker_math"})
    out = capsys.readouterr().out
    assert "COMPARATIVE EVALUATION SUMMARY" in out
    assert "Rewards injected: 1" in out
    assert "Role:Mode" in out


def test_print_batch_summary_handles_unknown_keys_error_fail_and_tps_fallback(capsys):
    result = _MOD.ComparativeResult(
        suite="math",
        question_id="qmix",
        prompt="p",
        expected="e",
        role_results={
            "frontdoor:direct": _rr(role="frontdoor", mode="direct", passed=False, error="boom", tokens_generated=0, elapsed_seconds=1.0, predicted_tps=0.0),
            "worker_math:direct": _rr(role="worker_math", mode="direct", passed=False, error=None, tokens_generated=10, elapsed_seconds=2.0, predicted_tps=0.0),
            "unknown:direct": _rr(role="unknown", mode="direct", passed=True, error=None, tokens_generated=5, elapsed_seconds=1.0, predicted_tps=0.0),
        },
        rewards={"frontdoor:direct": -0.5, "worker_math:direct": -0.3, "unknown:direct": 1.0},
        rewards_injected=0,
    )
    _MOD.print_batch_summary([result], roles=["frontdoor", "worker_math"], modes=["direct"])
    out = capsys.readouterr().out
    assert "frontdoor:direct" in out
    assert "worker_math:direct" in out
    assert "unknown:direct" not in out
    # worker_math avg_tps fallback: 10 tokens / 2.0s
    assert "5.0" in out


def test_print_stats_handles_no_data_and_aggregate_output(capsys, tmp_path: Path):
    # No eval dir
    import seeding_types as st

    missing = tmp_path / "missing"
    old_eval_dir = st.EVAL_DIR
    st.EVAL_DIR = missing
    try:
        _MOD.print_stats()
        out1 = capsys.readouterr().out
        assert "No evaluation data found." in out1
    finally:
        st.EVAL_DIR = old_eval_dir

    # Aggregate output path
    eval_dir = tmp_path / "eval"
    eval_dir.mkdir(parents=True, exist_ok=True)
    (eval_dir / "seeding_a.jsonl").write_text("{}\n")
    (eval_dir / "seeding_b.jsonl").write_text("{}\n")

    st.EVAL_DIR = eval_dir
    try:
        with (
            patch.object(_MOD, "load_checkpoint", side_effect=[[_comp("q1")], [_comp("q2")]]),
            patch.object(_MOD, "load_seen_questions", return_value={"q1", "q2", "q3"}),
        ):
            _MOD.print_stats()
        out2 = capsys.readouterr().out
    finally:
        st.EVAL_DIR = old_eval_dir

    assert "ALL SEEDING SESSIONS" in out2
    assert "Total questions: 2" in out2
    assert "Unique questions seen: 3" in out2
    assert "MemRL coverage:" in out2


def test_print_stats_handles_empty_eval_dir_and_pass_error_aggregation(capsys, tmp_path: Path):
    import seeding_types as st

    eval_dir = tmp_path / "eval_empty"
    eval_dir.mkdir(parents=True, exist_ok=True)
    old_eval_dir = st.EVAL_DIR
    st.EVAL_DIR = eval_dir
    try:
        _MOD.print_stats()
        out_empty = capsys.readouterr().out
        assert "No seeding sessions found." in out_empty

        (eval_dir / "seeding_s1.jsonl").write_text("{}\n")
        comp = _MOD.ComparativeResult(
            suite="math",
            question_id="q1",
            prompt="p",
            expected="e",
            role_results={
                "frontdoor:direct": _rr(role="frontdoor", mode="direct", passed=True, error=None),
                "worker_math:direct": _rr(role="worker_math", mode="direct", passed=False, error="err"),
            },
            rewards={},
        )
        with (
            patch.object(_MOD, "load_checkpoint", return_value=[comp]),
            patch.object(_MOD, "load_seen_questions", return_value={"q1"}),
        ):
            _MOD.print_stats()
        out = capsys.readouterr().out
    finally:
        st.EVAL_DIR = old_eval_dir

    assert "ALL SEEDING SESSIONS" in out
    assert "frontdoor:direct" in out
    assert "worker_math:direct" in out
