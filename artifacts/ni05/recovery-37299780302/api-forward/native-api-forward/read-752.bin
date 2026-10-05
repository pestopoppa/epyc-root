"""Helper-focused tests for scripts/benchmark/seed_specialist_routing.py."""

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
    spec = importlib.util.spec_from_file_location(name, _BENCH / "seed_specialist_routing.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_signal_handlers_update_shutdown_and_close_paths():
    mod = _load_module("seed_specialist_routing_helpers_sig")
    mod.state.shutdown = False
    close_mock = Mock()
    mod.state.close_poll_client = close_mock

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


def test_load_from_dataset_adapter_import_and_success_paths(monkeypatch):
    mod = _load_module("seed_specialist_routing_helpers_adapter")

    monkeypatch.setattr(
        mod._seeding_sampling,
        "_load_research_benchmark_module",
        Mock(side_effect=ImportError("missing")),
    )
    assert mod._load_from_dataset_adapter("suite", 1, 1) == []

    class _Adapter:
        total_available = 10

        @staticmethod
        def sample(n, seed):  # noqa: ANN001
            return [{"id": "q1", "suite": "s", "prompt": "p"}][:n]

    stale = ModuleType("dataset_adapters")
    stale.ADAPTER_SUITES = {"suite"}
    stale.get_adapter = lambda _name: None
    monkeypatch.setitem(sys.modules, "dataset_adapters", stale)
    fake = ModuleType("dataset_adapters")
    fake.ADAPTER_SUITES = {"suite", "none"}
    fake.get_adapter = lambda name: _Adapter() if name == "suite" else None
    monkeypatch.setattr(
        mod._seeding_sampling,
        "_load_research_benchmark_module",
        Mock(return_value=fake),
    )

    out = mod._load_from_dataset_adapter("suite", 1, 1)
    assert out == [{"id": "q1", "suite": "s", "prompt": "p"}]
    assert mod._load_from_dataset_adapter("unknown", 1, 1) == []
    assert mod._load_from_dataset_adapter("none", 1, 1) == []


def test_load_from_yaml_paths(tmp_path, monkeypatch):
    mod = _load_module("seed_specialist_routing_helpers_yaml")
    monkeypatch.setattr(mod, "DEBUG_PROMPTS_DIR", tmp_path)

    import builtins

    orig_import = builtins.__import__

    def _fail_yaml(name, *args, **kwargs):
        if name == "yaml":
            raise ImportError("missing yaml")
        return orig_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _fail_yaml)
    assert mod._load_from_yaml("math", 1, 1) == []
    monkeypatch.setattr(builtins, "__import__", orig_import)

    # Missing file
    assert mod._load_from_yaml("math", 1, 1) == []

    # Empty questions
    (tmp_path / "empty.yaml").write_text("questions: []\n")
    assert mod._load_from_yaml("empty", 1, 1) == []

    # Existing YAML path
    (tmp_path / "math.yaml").write_text(
        "questions:\n"
        "  - id: q1\n"
        "    prompt: 'What is 2+2?'\n"
        "    expected: '4'\n"
        "    image_path: ''\n"
    )
    out = mod._load_from_yaml("math", 2, 1)
    assert len(out) == 1
    assert out[0]["id"] == "q1"
    assert out[0]["dataset_source"] == "yaml"

    # Legacy prompt bundles use a top-level `prompts` mapping. A9 uses this
    # path to keep reference-token-coverage source rows scoreable.
    (tmp_path / "legacy.yaml").write_text(
        "prompts:\n"
        "  legacy_q1:\n"
        "    tier: 1\n"
        "    prompt: 'Follow this exact format.'\n"
        "    expected: 'Exact format reference'\n"
        "    auto_score: 'format_pattern:^ok$'\n"
    )
    legacy_out = mod._load_from_yaml("legacy", 1, 1)
    assert len(legacy_out) == 1
    assert legacy_out[0]["id"] == "legacy_q1"
    assert legacy_out[0]["expected"] == "Exact format reference"
    assert legacy_out[0]["dataset_source"] == "yaml_legacy_prompts"
    assert legacy_out[0]["scoring_config"]["legacy_auto_score"] == "format_pattern:^ok$"

    (tmp_path / "legacy_reference.yaml").write_text(
        "prompts:\n"
        "  instruction_q1:\n"
        "    tier: 1\n"
        "    prompt: 'Answer with a constrained sentence.'\n"
        "    expected: ''\n"
        "    reference_answer: 'A compliant answer containing the scored tokens.'\n"
        "    auto_score: 'rubric:instruction_precision'\n"
    )
    legacy_reference_out = mod._load_from_yaml("legacy_reference", 1, 1)
    assert len(legacy_reference_out) == 1
    assert legacy_reference_out[0]["expected"] == ""
    assert (
        legacy_reference_out[0]["reference"]
        == "A compliant answer containing the scored tokens."
    )


def test_sample_unseen_questions_pool_fastpath(tmp_path, monkeypatch):
    mod = _load_module("seed_specialist_routing_helpers_pool_fast")
    stale = ModuleType("question_pool")
    stale.POOL_FILE = tmp_path / "stale_pool.json"
    stale.POOL_FILE.write_text("{}")
    stale.build_pool = Mock(side_effect=RuntimeError("stale module used"))
    stale.load_pool = Mock(side_effect=RuntimeError("stale module used"))
    stale.sample_from_pool = Mock(side_effect=RuntimeError("stale module used"))
    monkeypatch.setitem(sys.modules, "question_pool", stale)

    pool_mod = ModuleType("question_pool")
    pool_mod.POOL_FILE = tmp_path / "pool.json"
    pool_mod.POOL_FILE.write_text("{}")
    pool_mod.build_pool = Mock()
    pool_mod.load_pool = lambda: {"pool": 1}
    pool_mod.sample_from_pool = lambda *a, **k: [{"id": "q1", "suite": "s"}]
    monkeypatch.setattr(
        mod._seeding_sampling,
        "_load_research_benchmark_module",
        Mock(return_value=pool_mod),
    )

    out = mod.sample_unseen_questions(["s"], 1, set(), seed=1, use_pool=True)
    assert out == [{"id": "q1", "suite": "s"}]


def test_sample_unseen_questions_yaml_source_bypasses_pool_and_adapter(
    tmp_path,
    monkeypatch,
):
    mod = _load_module("seed_specialist_routing_helpers_yaml_source")
    monkeypatch.setattr(mod, "DEBUG_PROMPTS_DIR", tmp_path)
    (tmp_path / "instruction_precision.yaml").write_text(
        "prompts:\n"
        "  ip_q1:\n"
        "    prompt: 'Return OK exactly.'\n"
        "    expected: 'OK'\n"
    )

    pool_mod = ModuleType("question_pool")
    pool_mod.POOL_FILE = tmp_path / "pool.json"
    pool_mod.POOL_FILE.write_text("{}")
    pool_mod.build_pool = Mock()
    pool_mod.load_pool = lambda: {"pool": 1}
    pool_mod.sample_from_pool = lambda *a, **k: [
        {"id": "pool_q", "suite": "instruction_precision", "expected": ""}
    ]
    monkeypatch.setitem(sys.modules, "question_pool", pool_mod)
    monkeypatch.setattr(
        mod._seeding_sampling,
        "_load_research_benchmark_module",
        Mock(side_effect=AssertionError("research loader should not be used")),
    )

    class _Adapter:
        total_available = 1

        @staticmethod
        def sample(n, seed):  # noqa: ANN001
            return [
                {
                    "id": "adapter_q",
                    "suite": "instruction_precision",
                    "prompt": "p",
                    "expected": "",
                }
            ][:n]

    fake = ModuleType("dataset_adapters")
    fake.ADAPTER_SUITES = {"instruction_precision"}
    fake.get_adapter = lambda _name: _Adapter()
    monkeypatch.setitem(sys.modules, "dataset_adapters", fake)

    out = mod.sample_unseen_questions(
        ["instruction_precision"],
        1,
        set(),
        seed=1,
        use_pool=True,
        question_source="yaml",
    )
    assert out[0]["id"] == "ip_q1"
    assert out[0]["expected"] == "OK"
    assert out[0]["dataset_source"] == "yaml_legacy_prompts"


def test_sample_unseen_questions_fallback_interleave_and_seen_filter(monkeypatch):
    mod = _load_module("seed_specialist_routing_helpers_pool_fallback")

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


def test_sample_unseen_questions_pool_empty_then_yaml_fallback(tmp_path, monkeypatch):
    mod = _load_module("seed_specialist_routing_helpers_pool_empty")
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


def test_run_batch_3way_health_and_empty_paths():
    mod = _load_module("seed_specialist_routing_helpers_batch")
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


def test_print_3way_summary_no_results_and_with_data(capsys):
    mod = _load_module("seed_specialist_routing_helpers_summary")
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
        rewards_injected=3,
    )
    mod.print_3way_summary([result])
    out = capsys.readouterr().out
    assert "3-WAY ROUTING EVALUATION SUMMARY" in out
    assert "Tools helped: 1" in out
    assert "Rewards injected: 3" in out


def test_retrieval_config_and_profile_application(monkeypatch):
    mod = _load_module("seed_specialist_routing_helpers_profile")
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


# ── EVL-12 A2 residue: --rebuild-pool / --question-ids bind the research pool by path ──

_FAKE_RESEARCH_POOL = '''
WHICH_COPY = "research"
BUILD_CALLS = []

def build_pool(output_path=None):
    BUILD_CALLS.append(output_path)
    return {"research_suite": 2}

def load_pool(pool_path=None, warn_stale=True):
    assert warn_stale is False
    return {
        "suite_a": [{"id": "q1", "suite": "suite_a"}, {"id": "q2", "suite": "suite_a"}],
        "suite_b": [{"id": "suite_b/raw", "suite": "suite_b"}],
    }
'''


@pytest.fixture()
def research_pool_tree(tmp_path, monkeypatch):
    import seeding_sampling

    bench = tmp_path / "scripts" / "benchmark"
    bench.mkdir(parents=True)
    (bench / "question_pool.py").write_text(_FAKE_RESEARCH_POOL, encoding="utf-8")
    monkeypatch.setenv("EPYC_RESEARCH_ROOT", str(tmp_path))
    monkeypatch.setattr(seeding_sampling, "_RESEARCH_BENCHMARK_MODULE_CACHE", {})
    decoy = ModuleType("question_pool")
    decoy.WHICH_COPY = "orchestrator-decoy"
    decoy.build_pool = Mock(side_effect=AssertionError("bare-import copy used"))
    decoy.load_pool = Mock(side_effect=AssertionError("bare-import copy used"))
    decoy.load_questions_by_ids = Mock(side_effect=AssertionError("bare-import copy used"))
    monkeypatch.setitem(sys.modules, "question_pool", decoy)
    return seeding_sampling, decoy


def test_build_question_pool_binds_research_copy_not_sys_modules(research_pool_tree):
    seeding_sampling, decoy = research_pool_tree
    assert seeding_sampling.build_question_pool() == {"research_suite": 2}
    decoy.build_pool.assert_not_called()
    assert sys.modules["question_pool"] is decoy, "must not clobber the bare name"


def test_load_questions_by_ids_binds_research_copy_and_preserves_semantics(research_pool_tree):
    seeding_sampling, decoy = research_pool_tree
    log = Mock()
    out = seeding_sampling.load_questions_by_ids(
        ["suite_a/q2", "q1", "suite_a/q1", "suite_b/raw", "nope"], logger=log,
    )
    # input order, suite/ prefix stripped, de-duplicated, raw slash id matched
    assert [q["id"] for q in out] == ["q2", "q1", "suite_b/raw"]
    decoy.load_pool.assert_not_called()
    decoy.load_questions_by_ids.assert_not_called()
    log.warning.assert_called_once()
    assert "nope" in str(log.warning.call_args)


def test_load_questions_by_ids_fails_closed_without_research_module(tmp_path, monkeypatch):
    import seeding_sampling

    monkeypatch.setenv("EPYC_RESEARCH_ROOT", str(tmp_path))
    monkeypatch.setattr(seeding_sampling, "_RESEARCH_BENCHMARK_MODULE_CACHE", {})
    decoy = ModuleType("question_pool")
    decoy.load_questions_by_ids = Mock(return_value=[{"id": "stale"}])
    monkeypatch.setitem(sys.modules, "question_pool", decoy)
    with pytest.raises(FileNotFoundError):
        seeding_sampling.load_questions_by_ids(["q1"], logger=Mock())
    decoy.load_questions_by_ids.assert_not_called()
