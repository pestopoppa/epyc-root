"""Helper-focused tests for scripts/benchmark/seed_specialist_routing_v2.py."""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock, patch

import pytest


_ROOT = Path(__file__).resolve().parents[2]
_BENCH = _ROOT / "scripts" / "benchmark"
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_BENCH))


def _load_module(name: str):
    spec = importlib.util.spec_from_file_location(name, _BENCH / "seed_specialist_routing_v2.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_signal_handlers_update_shutdown_and_close_paths_v2(monkeypatch):
    mod = _load_module("seed_specialist_routing_v2_helpers_sig")
    # NIB2-69: `state` is the shared seeding_types singleton. Leaving
    # shutdown=True made later evaluate_question_per_role tests in the same
    # xdist worker return [] (order-dependent failures in test_seeding_eval).
    monkeypatch.setattr(mod.state, "shutdown", False)
    close_mock = Mock()
    monkeypatch.setattr(mod.state, "close_poll_client", close_mock)

    mod._handle_sigint(None, None)
    assert mod.state.shutdown is True

    with patch.object(sys, "exit", side_effect=SystemExit(1)):
        with pytest.raises(SystemExit):
            mod._handle_sigint(None, None)
    close_mock.assert_called_once()

    mod.state.shutdown = False
    mod._handle_sigterm(None, None)
    assert mod.state.shutdown is True
    assert close_mock.call_count == 2


def test_loaders_and_sampling_paths_v2(tmp_path, monkeypatch):
    mod = _load_module("seed_specialist_routing_v2_helpers_loaders")

    # Dataset adapter fallback path
    class _Adapter:
        total_available = 10

        @staticmethod
        def sample(n, seed):  # noqa: ANN001
            return [{"id": "q1", "suite": "s", "prompt": "p"}][:n]

    fake = ModuleType("dataset_adapters")
    fake.ADAPTER_SUITES = {"suite", "none"}
    fake.get_adapter = lambda name: _Adapter() if name == "suite" else None
    monkeypatch.setattr(
        mod._seeding_sampling,
        "_load_research_benchmark_module",
        Mock(return_value=fake),
    )
    assert mod._load_from_dataset_adapter("suite", 1, 1) == [{"id": "q1", "suite": "s", "prompt": "p"}]
    assert mod._load_from_dataset_adapter("missing", 1, 1) == []
    assert mod._load_from_dataset_adapter("none", 1, 1) == []

    # YAML fallback path
    monkeypatch.setattr(mod, "DEBUG_PROMPTS_DIR", tmp_path)
    (tmp_path / "empty.yaml").write_text("questions: []\n")
    assert mod._load_from_yaml("empty", 1, 1) == []
    (tmp_path / "math.yaml").write_text(
        "questions:\n"
        "  - id: q1\n"
        "    prompt: 'What is 2+2?'\n"
        "    expected: '4'\n"
        "    image_path: ''\n"
    )
    yaml_out = mod._load_from_yaml("math", 2, 1)
    assert len(yaml_out) == 1
    assert yaml_out[0]["dataset_source"] == "yaml"

    # Pool fast path
    pool_mod = ModuleType("question_pool")
    pool_mod.POOL_FILE = tmp_path / "pool.json"
    pool_mod.POOL_FILE.write_text("{}")
    pool_mod.build_pool = Mock()
    pool_mod.load_pool = lambda: {"pool": 1}
    pool_mod.sample_from_pool = lambda *a, **k: [{"id": "q_fast", "suite": "s"}]
    monkeypatch.setattr(
        mod._seeding_sampling,
        "_load_research_benchmark_module",
        Mock(return_value=pool_mod),
    )
    sampled = mod.sample_unseen_questions(["suite"], 1, set(), seed=1, use_pool=True)
    assert sampled == [{"id": "q_fast", "suite": "s"}]


def test_loader_import_error_paths_v2(monkeypatch):
    mod = _load_module("seed_specialist_routing_v2_helpers_import_errors")
    import builtins

    orig_import = builtins.__import__

    def _fail_import(name, *args, **kwargs):
        if name == "yaml":
            raise ImportError("missing")
        return orig_import(name, *args, **kwargs)

    monkeypatch.setattr(
        mod._seeding_sampling,
        "_load_research_benchmark_module",
        Mock(side_effect=ImportError("missing")),
    )
    monkeypatch.setattr(builtins, "__import__", _fail_import)
    assert mod._load_from_dataset_adapter("suite", 1, 1) == []
    assert mod._load_from_yaml("suite", 1, 1) == []
    monkeypatch.setattr(builtins, "__import__", orig_import)


def test_sample_unseen_questions_fallback_interleave_and_filter_v2(monkeypatch):
    mod = _load_module("seed_specialist_routing_v2_helpers_fallback")

    pool_mod = ModuleType("question_pool")
    pool_mod.POOL_FILE = Path("/tmp/nonexistent_pool.json")
    pool_mod.build_pool = Mock(side_effect=RuntimeError("no pool"))
    pool_mod.load_pool = Mock(side_effect=RuntimeError("no pool"))
    pool_mod.sample_from_pool = Mock(return_value=[])
    monkeypatch.setattr(
        mod._seeding_sampling,
        "_load_research_benchmark_module",
        Mock(return_value=pool_mod),
    )

    def _from_adapter(suite, *_args, **_kwargs):
        if suite == "a":
            return [{"id": "a1", "suite": "a"}, {"id": "a_seen", "suite": "a"}]
        return [{"id": "b1", "suite": "b"}]

    monkeypatch.setattr(mod, "_load_from_dataset_adapter", _from_adapter)
    monkeypatch.setattr(mod, "_load_from_yaml", lambda *_a, **_k: [])

    out = mod.sample_unseen_questions(["a", "b"], 2, {"a_seen"}, seed=1, use_pool=True)
    assert [q["id"] for q in out] == ["a1", "b1"]


def test_sample_unseen_questions_pool_empty_then_yaml_fallback_v2(tmp_path, monkeypatch):
    mod = _load_module("seed_specialist_routing_v2_helpers_pool_empty")
    pool_mod = ModuleType("question_pool")
    pool_mod.POOL_FILE = tmp_path / "pool.json"
    pool_mod.POOL_FILE.write_text("{}")
    pool_mod.build_pool = Mock()
    pool_mod.load_pool = lambda: {"pool": 1}
    pool_mod.sample_from_pool = lambda *a, **k: []
    monkeypatch.setattr(
        mod._seeding_sampling,
        "_load_research_benchmark_module",
        Mock(return_value=pool_mod),
    )

    monkeypatch.setattr(mod, "_load_from_dataset_adapter", lambda *_a, **_k: [])
    monkeypatch.setattr(
        mod,
        "_load_from_yaml",
        lambda suite, *_a, **_k: [{"id": f"{suite}_y1", "suite": suite}],
    )
    out = mod.sample_unseen_questions(["a"], 1, set(), seed=1, use_pool=True)
    assert out == [{"id": "a_y1", "suite": "a"}]


def test_run_batch_3way_health_and_empty_paths_v2():
    mod = _load_module("seed_specialist_routing_v2_helpers_batch")
    with patch.object(mod, "_check_server_health", return_value=False):
        with pytest.raises(mod.HealthCheckError):
            mod.run_batch_3way(
                suites=["s"],
                sample_per_suite=1,
                seed=1,
                url="http://localhost:8000",
                timeout=30,
                session_id="sess",
            )

    with (
        patch.object(mod, "_check_server_health", return_value=True),
        patch.object(mod, "load_seen_questions", return_value=set()),
        patch.object(mod, "sample_unseen_questions", return_value=[]),
    ):
        out = mod.run_batch_3way(
            suites=["s"],
            sample_per_suite=1,
            seed=1,
            url="http://localhost:8000",
            timeout=30,
            session_id="sess",
        )
    assert out == []


def test_load_from_yaml_missing_file_v2(tmp_path, monkeypatch):
    mod = _load_module("seed_specialist_routing_v2_helpers_yaml_missing")
    monkeypatch.setattr(mod, "DEBUG_PROMPTS_DIR", tmp_path)
    assert mod._load_from_yaml("missing_suite", 1, 1) == []


def test_print_summary_and_profile_paths_v2(capsys, monkeypatch):
    mod = _load_module("seed_specialist_routing_v2_helpers_summary")
    mod.print_3way_summary([])
    assert "No results to summarize." in capsys.readouterr().out

    rr_pass = SimpleNamespace(passed=True)
    rr_fail = SimpleNamespace(passed=False)
    result = mod.ThreeWayResult(
        suite="s",
        question_id="q1",
        prompt="p",
        expected="e",
        role_results={"frontdoor:direct": rr_pass, "frontdoor:repl": rr_fail},
        rewards={
            mod.ACTION_SELF_DIRECT: 1.0,
            mod.ACTION_SELF_REPL: 0.0,
            mod.ACTION_ARCHITECT: 1.0,
            mod.ACTION_WORKER: 1.0,
        },
        metadata={"tools_helped": True},
        rewards_injected=2,
    )
    mod.print_3way_summary([result])
    out = capsys.readouterr().out
    assert "3-WAY ROUTING EVALUATION SUMMARY" in out
    assert "Rewards injected: 2" in out

    args = SimpleNamespace(
        profile="infra-stable",
        cooldown=None,
        timeout=None,
        cost_lambda=0.3,
        confidence_threshold=None,
        confidence_estimator=None,
        confidence_trim_ratio=None,
        confidence_min_neighbors=None,
        warm_probability_hit=None,
        warm_probability_miss=None,
        warm_cost_fallback_s=None,
        cold_cost_fallback_s=None,
        calibrated_confidence_threshold=None,
        conformal_margin=None,
        risk_control_enabled=None,
        risk_budget_id=None,
        risk_gate_min_samples=None,
        risk_abstain_target_role=None,
        risk_gate_rollout_ratio=None,
        risk_gate_kill_switch=None,
        risk_budget_guardrail_min_events=None,
        risk_budget_guardrail_max_abstain_rate=None,
        prior_strength=None,
    )
    cfg = mod._build_retrieval_config_from_args(args)
    assert getattr(cfg, "cost_lambda") == 0.3

    monkeypatch.delenv("ORCHESTRATOR_DEFERRED_TOOL_RESULTS", raising=False)
    mod._apply_profile(args)
    assert args.cooldown == 2.0
    assert isinstance(args.timeout, int)
    assert os.environ.get("ORCHESTRATOR_DEFERRED_TOOL_RESULTS") == "1"
