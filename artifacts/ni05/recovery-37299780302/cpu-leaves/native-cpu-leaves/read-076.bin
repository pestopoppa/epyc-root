"""Tests for the extracted autopilot.controller_io module."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[2]
AUTOPILOT_DIR = ROOT / "scripts" / "autopilot"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(AUTOPILOT_DIR))

controller_io = importlib.import_module("controller_io")


# ----- extract_action -----


def test_extract_action_marker_block() -> None:
    text = """Some reasoning here.

```json:autopilot_actions
{"type": "seed_batch", "n_questions": 10}
```

More text after."""
    action = controller_io.extract_action(text)
    assert action == {"type": "seed_batch", "n_questions": 10}


def test_extract_action_recovers_trailing_bracket_noise() -> None:
    text = """Local draft leaked prose first.

```json:autopilot_actions
{"type": "structural_experiment", "flags": {"plan_review": true}}
}
```
"""
    action = controller_io.extract_action(text)
    assert action == {"type": "structural_experiment", "flags": {"plan_review": True}}


def test_extract_action_marker_unwraps_list() -> None:
    text = """```json:autopilot_actions
[{"type": "numeric_trial", "surface": "x"}]
```"""
    action = controller_io.extract_action(text)
    assert action == {"type": "numeric_trial", "surface": "x"}


def test_extract_action_falls_back_to_generic_json_block() -> None:
    text = """No marker here.

```json
{"type": "rollback", "to_checkpoint": "production_best"}
```"""
    action = controller_io.extract_action(text)
    assert action == {"type": "rollback", "to_checkpoint": "production_best"}


def test_extract_action_accepts_leading_json_with_rationale_sidecar() -> None:
    text = """{
  "type": "deep_eval",
  "tier": 3
}

```json:autopilot_rationale
{"falsifier": "tier 3 does not improve"}
```"""
    action = controller_io.extract_action(text)
    assert action == {"type": "deep_eval", "tier": 3}


def test_extract_action_rejects_leading_json_with_arbitrary_trailing_prose() -> None:
    text = """{"type": "deep_eval", "tier": 3}

This action should be accepted because it is safe."""
    assert controller_io.extract_action(text) is None


def test_extract_action_returns_none_when_no_block() -> None:
    assert controller_io.extract_action("plain text, no json") is None


def test_extract_action_returns_none_when_no_type_field() -> None:
    text = """```json
{"foo": "bar"}
```"""
    assert controller_io.extract_action(text) is None


def test_extract_action_returns_none_on_invalid_json() -> None:
    text = """```json:autopilot_actions
{not valid json
```"""
    assert controller_io.extract_action(text) is None


def test_extract_action_returns_none_on_marker_with_no_closing_fence() -> None:
    # A truncated generation: the marker opens but the fence never closes.
    # Pre-fix this raised an uncaught ValueError from `text.index("```", start)`
    # instead of returning None like every other malformed shape here.
    text = '```json:autopilot_actions\n{"type": "deep_eval", "reason": "quality plateaued'
    assert controller_io.extract_action(text) is None


def test_extract_action_returns_none_on_generic_fence_with_no_closing_fence() -> None:
    text = '```json\n{"type": "deep_eval"'
    assert controller_io.extract_action(text) is None


# ----- extract_rationale -----


def test_extract_rationale_well_formed() -> None:
    text = """Action below.

```json:autopilot_actions
{"type": "seed_batch"}
```

```json:autopilot_rationale
{"falsifier": "no quality gain after 20 seeded questions",
 "rubric_scores": {"info_gain": 4, "coherence": 5, "usefulness": 3,
  "synthesis_note": "fused with numeric_trial"}}
```"""
    out = controller_io.extract_rationale(text)
    assert out["falsifier"] == "no quality gain after 20 seeded questions"
    assert out["rubric_scores"]["info_gain"] == 4
    assert out["rubric_scores"]["synthesis_note"] == "fused with numeric_trial"


def test_extract_rationale_missing_block_returns_defaults() -> None:
    out = controller_io.extract_rationale("no rationale here")
    assert out == {"falsifier": "", "rubric_scores": {}}


def test_extract_rationale_preserves_explicit_vidya_claim_ids() -> None:
    text = ('```json:autopilot_rationale\n'
            '{"falsifier":"x","rubric_scores":{},"vidya_claim_ids":["claim-a"]}\n'
            '```')
    assert controller_io.extract_rationale(text)["vidya_claim_ids"] == ["claim-a"]
    result = controller_io.extract_rationale_with_repair(
        text, complete=lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("clean rationale must not be repaired")))
    assert result.value["vidya_claim_ids"] == ["claim-a"]


def test_extract_rationale_malformed_json_returns_defaults() -> None:
    text = """```json:autopilot_rationale
{not valid
```"""
    out = controller_io.extract_rationale(text)
    assert out == {"falsifier": "", "rubric_scores": {}}


def test_extract_rationale_unclosed_fence_returns_defaults() -> None:
    text = """```json:autopilot_rationale
{"falsifier": "x"}
"""
    out = controller_io.extract_rationale(text)
    assert out == {"falsifier": "", "rubric_scores": {}}


def test_extract_rationale_coerces_non_string_falsifier() -> None:
    text = """```json:autopilot_rationale
{"falsifier": 42, "rubric_scores": {"info_gain": 1}}
```"""
    out = controller_io.extract_rationale(text)
    assert out["falsifier"] == "42"
    assert out["rubric_scores"] == {"info_gain": 1}


def test_extract_rationale_non_dict_rubric_falls_back_to_empty() -> None:
    text = """```json:autopilot_rationale
{"falsifier": "x", "rubric_scores": "not a dict"}
```"""
    out = controller_io.extract_rationale(text)
    assert out["falsifier"] == "x"
    assert out["rubric_scores"] == {}


# ----- validate_single_variable (AP-9) -----


def test_validate_prompt_mutation_requires_file() -> None:
    err = controller_io.validate_single_variable({"type": "prompt_mutation"})
    assert err and "must specify a single target file" in err


def test_validate_prompt_mutation_rejects_multi_file() -> None:
    err = controller_io.validate_single_variable({"type": "prompt_mutation", "file": "a.md,b.md"})
    assert err and "multiple files" in err


def test_validate_prompt_mutation_accepts_single_file() -> None:
    assert (
        controller_io.validate_single_variable({"type": "prompt_mutation", "file": "frontdoor.md"})
        is None
    )


def test_validate_code_mutation_requires_file() -> None:
    err = controller_io.validate_single_variable({"type": "code_mutation"})
    assert err and "must specify a single target file" in err


def test_validate_code_mutation_accepts_new_file() -> None:
    assert (
        controller_io.validate_single_variable(
            {
                "type": "code_mutation",
                "file": "src/generated/new_module.py",
                "mutation": "new_file",
            }
        )
        is None
    )


def test_validate_structural_experiment_blocks_multi_flag() -> None:
    err = controller_io.validate_single_variable(
        {"type": "structural_experiment", "flags": {"a": True, "b": False}}
    )
    assert err and "2 flags at once" in err


def test_validate_structural_experiment_accepts_single_flag() -> None:
    assert (
        controller_io.validate_single_variable(
            {"type": "structural_experiment", "flags": {"a": True}}
        )
        is None
    )


def test_validate_consult_gate_probe_accepts_tiered_hard_lane() -> None:
    assert (
        controller_io.validate_single_variable(
            {"type": "consult_gate_probe", "task_suite": "targeted", "turns": 10, "tier": 3}
        )
        is None
    )


def test_validate_consult_gate_probe_blocks_bad_tier() -> None:
    err = controller_io.validate_single_variable(
        {"type": "consult_gate_probe", "task_suite": "targeted", "turns": 10, "tier": 4}
    )
    assert err and "tier must be <= 3" in err


def test_validate_consult_gate_probe_blocks_oversized_run() -> None:
    err = controller_io.validate_single_variable(
        {"type": "consult_gate_probe", "task_suite": "targeted", "turns": 80, "tier": 3}
    )
    assert err and "turns must be <= 50" in err


def test_validate_numeric_trial_blocks_multi_param() -> None:
    err = controller_io.validate_single_variable(
        {"type": "numeric_trial", "params": {"x": 1, "y": 2}}
    )
    assert err and "sets 2 params explicitly" in err


def test_validate_numeric_trial_accepts_empty_params_for_optuna() -> None:
    # Empty params = Optuna will suggest; exempt from single-variable rule
    assert controller_io.validate_single_variable({"type": "numeric_trial", "params": {}}) is None


def test_validate_numeric_trial_accepts_all_configured_surfaces() -> None:
    from species.numeric_swarm import SURFACES

    assert set(SURFACES) == controller_io._NUMERIC_SURFACES
    assert (
        controller_io.validate_single_variable(
            {"type": "numeric_trial", "surface": "kv_compaction", "params": {}}
        )
        is None
    )


def test_validate_numeric_trial_rejects_unknown_surface() -> None:
    err = controller_io.validate_single_variable(
        {"type": "numeric_trial", "surface": "not_a_surface", "params": {}}
    )
    assert err and "surface must be one of" in err


def test_validate_numeric_trial_rejects_suppressed_surface() -> None:
    try:
        controller_io.set_suppressed_numeric_surfaces({"kv_compaction"})
        err = controller_io.validate_single_variable(
            {"type": "numeric_trial", "surface": "kv_compaction", "params": {}}
        )
        assert err and "surface must be one of" in err
        assert "kv_compaction" not in controller_io._NUMERIC_SURFACES
        assert controller_io.suppressed_numeric_surfaces() == {"kv_compaction"}
    finally:
        controller_io.set_suppressed_numeric_surfaces(set())


def test_validate_mutation_rejects_unknown_keys_and_bad_enums() -> None:
    err = controller_io.validate_single_variable(
        {
            "type": "code_mutation",
            "file": "src/escalation.py",
            "mutation": "targeted_fix",
            "target_function": "route",
        }
    )
    assert err and "unsupported keys" in err
    assert "target_function" in err

    err = controller_io.validate_single_variable(
        {
            "type": "prompt_mutation",
            "file": "frontdoor.md",
            "mutation": "rewrite_everything",
        }
    )
    assert err and "mutation must be one of" in err


def test_validate_gepa_rejects_unbounded_max_evals() -> None:
    err = controller_io.validate_single_variable(
        {"type": "gepa_optimize", "file": "frontdoor.md", "max_evals": 5000}
    )
    assert err and "max_evals must be <=" in err


def test_validate_slot_compact_schema_matches_handler() -> None:
    assert (
        controller_io.validate_single_variable(
            {
                "type": "slot_compact",
                "port": 8070,
                "slot_id": 0,
                "keep_ratio": 0.3,
                "scorer": "expected_attention",
                "keep_first": 5,
                "n_future": 128,
                "use_covariance": True,
            }
        )
        is None
    )

    err = controller_io.validate_single_variable(
        {
            "type": "slot_compact",
            "port": 8070,
            "slot_id": 0,
            "keep_ratio": 0.3,
            "beta": 0.5,
            "keep_last": 10,
        }
    )
    assert err and "unsupported keys" in err
    assert "beta" in err
    assert "keep_last" in err


def test_validate_slot_compact_rejects_bad_ranges() -> None:
    err = controller_io.validate_single_variable(
        {
            "type": "slot_compact",
            "port": 8070,
            "slot_id": 0,
            "keep_ratio": 1.5,
        }
    )
    assert err and "keep_ratio must be <=" in err

    err = controller_io.validate_single_variable(
        {"type": "slot_compact", "port": 8070, "n_future": 0}
    )
    assert err and "n_future must be >=" in err

    err = controller_io.validate_single_variable({"type": "slot_compact", "port": 0})
    assert err and "port must be >=" in err


def test_validate_deep_eval_rejects_ignored_schema_fields() -> None:
    err = controller_io.validate_single_variable(
        {
            "type": "deep_eval",
            "tier": 2,
            "target_trial": 38,
            "suites": ["coder"],
            "baseline_recheck": True,
            "n_questions": 500,
            "seed": 1234,
        }
    )
    assert err and "unsupported keys" in err
    assert "target_trial" in err
    assert "n_questions" in err
    assert "seed" in err


def test_validate_deep_eval_requires_valid_tier() -> None:
    assert tuple(controller_io.DEEP_EVAL_TIERS) == (0, 1, 2, 3)
    assert controller_io._ACTION_SCHEMAS["deep_eval"]["enums"]["tier"] == {0, 1, 2, 3}
    assert controller_io.validate_single_variable({"type": "deep_eval", "tier": 2}) is None
    assert controller_io.validate_single_variable({"type": "deep_eval", "tier": 3}) is None
    assert controller_io.validate_single_variable({"type": "deep_eval"})
    assert controller_io.validate_single_variable({"type": "deep_eval", "tier": 4})
    assert controller_io.validate_single_variable({"type": "deep_eval", "tier": "2"})


def test_validate_unknown_action_type_passes() -> None:
    assert controller_io.validate_single_variable({"type": "unknown_thing"}) is None


# ----- _unwrap_action -----


def test_unwrap_action_dict_with_type() -> None:
    assert controller_io._unwrap_action({"type": "x"}) == {"type": "x"}


def test_unwrap_action_list_takes_first() -> None:
    assert controller_io._unwrap_action([{"type": "x"}, {"type": "y"}]) == {"type": "x"}


def test_unwrap_action_empty_list_none() -> None:
    assert controller_io._unwrap_action([]) is None


def test_unwrap_action_dict_without_type_none() -> None:
    assert controller_io._unwrap_action({"no_type": True}) is None


def test_invoke_controller_archives_timeout_before_return(monkeypatch) -> None:
    records = []
    statuses = []

    class FakeTimeoutProcess:
        stdout = iter(())
        stderr = None
        pid = 12345
        returncode = None

        def wait(self, timeout):
            raise controller_io.subprocess.TimeoutExpired(cmd="claude", timeout=timeout)

        def kill(self):
            pass

    monkeypatch.setattr(controller_io.subprocess, "Popen", lambda *a, **k: FakeTimeoutProcess())
    monkeypatch.setattr(controller_io, "_open_planner_tap", lambda: None)
    monkeypatch.setattr(controller_io, "_append_planner_archive", records.append)
    monkeypatch.setattr(
        controller_io,
        "_write_planner_subprocess_status",
        lambda **kwargs: statuses.append(kwargs),
    )

    text, session_id = controller_io.invoke_controller(
        "prompt",
        session_id="old-session",
        timeout=1,
    )

    assert text == ""
    assert session_id == "old-session"
    assert len(records) == 1
    assert records[0]["type"] == "planner_provider_call"
    assert records[0]["provider"] == "claude"
    assert records[0]["status"] == "timeout"
    assert records[0]["ok"] is False
    assert records[0]["resume_session_id"] == "old-session"
    assert [status["status"] for status in statuses] == ["running", "timeout"]
    assert statuses[0]["child_pid"] == 12345


def test_invoke_controller_pins_planner_model_args(monkeypatch) -> None:
    captured = {}

    class FakeTimeoutProcess:
        stdout = iter(())
        stderr = None
        pid = 12345
        returncode = None

        def wait(self, timeout):
            raise controller_io.subprocess.TimeoutExpired(cmd="claude", timeout=timeout)

        def kill(self):
            pass

    def fake_popen(cmd, *args, **kwargs):
        captured["cmd"] = cmd
        captured["env"] = kwargs.get("env", {})
        return FakeTimeoutProcess()

    monkeypatch.setenv("CLAUDECODE", "parent-session")
    monkeypatch.setenv("AUTOPILOT_CLAUDE_MODEL", "opus")
    monkeypatch.setenv("AUTOPILOT_CLAUDE_FALLBACK_MODEL", "sonnet")
    monkeypatch.setattr(controller_io.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(controller_io, "_open_planner_tap", lambda: None)
    monkeypatch.setattr(controller_io, "_append_planner_archive", lambda record: None)

    controller_io.invoke_controller("prompt", timeout=1)

    assert captured["cmd"][:3] == ["claude", "-p", "prompt"]
    assert "--permission-mode" in captured["cmd"]
    assert captured["cmd"][captured["cmd"].index("--permission-mode") + 1] == "default"
    assert "--safe-mode" in captured["cmd"]
    assert "--tools" in captured["cmd"]
    assert captured["cmd"][captured["cmd"].index("--tools") + 1] == "Read,Grep,Glob"
    assert "--allowedTools" in captured["cmd"]
    assert captured["cmd"][captured["cmd"].index("--allowedTools") + 1] == "Read,Grep,Glob"
    assert "--disallowedTools" in captured["cmd"]
    disallowed = set(captured["cmd"][captured["cmd"].index("--disallowedTools") + 1].split(","))
    assert {"Bash", "Edit", "Task", "Write"}.issubset(disallowed)
    assert "MultiEdit" not in disallowed
    assert "MultiEdit" in controller_io.PLANNER_DISALLOWED_TOOLS
    assert disallowed.isdisjoint(controller_io.PLANNER_ALLOWED_TOOLS)
    assert "--model" in captured["cmd"]
    assert captured["cmd"][captured["cmd"].index("--model") + 1] == "opus"
    assert "--fallback-model" in captured["cmd"]
    assert captured["cmd"][captured["cmd"].index("--fallback-model") + 1] == "sonnet"
    assert "CLAUDECODE" not in captured["env"]


def test_invoke_controller_rejects_disallowed_tool_use(monkeypatch) -> None:
    records = []
    statuses = []

    class FakeSuccessProcess:
        stderr = None
        pid = 12345
        returncode = 0
        stdout = iter(
            [
                '{"type":"system","subtype":"init","session_id":"new-session"}\n',
                (
                    '{"type":"assistant","message":{"content":['
                    '{"type":"tool_use","name":"Write","input":{"file_path":"x"}}'
                    "]}}\n"
                ),
                (
                    '{"type":"result","subtype":"success","session_id":"new-session",'
                    '"result":"```json:autopilot_actions\\n'
                    '{\\"type\\":\\"numeric_trial\\",\\"surface\\":\\"monitor\\",\\"params\\":{}}'
                    '\\n```"}\n'
                ),
            ]
        )

        def wait(self, timeout):
            return self.returncode

        def kill(self):
            pass

    monkeypatch.setattr(controller_io.subprocess, "Popen", lambda *a, **k: FakeSuccessProcess())
    monkeypatch.setattr(controller_io, "_open_planner_tap", lambda: None)
    monkeypatch.setattr(controller_io, "_append_planner_archive", records.append)
    monkeypatch.setattr(
        controller_io,
        "_write_planner_subprocess_status",
        lambda **kwargs: statuses.append(kwargs),
    )

    text, session_id = controller_io.invoke_controller(
        "prompt",
        session_id="old-session",
        timeout=1,
    )

    assert text == ""
    assert session_id is None
    assert records[-1]["status"] == "disallowed_tool_use"
    assert records[-1]["ok"] is False
    assert "Write" in records[-1]["error"]
    assert [status["status"] for status in statuses] == [
        "running",
        "disallowed_tool_use",
    ]


# ----- TD-21.2/.3: repair-aware extraction -----

import json as _json  # noqa: E402

from src.structured_output.repair import (  # noqa: E402
    STRUCTURED_OUTPUT_REPAIR_COUNTS,
    reset_counts_for_tests,
)


@pytest.fixture(autouse=True)
def _reset_repair_counts():
    reset_counts_for_tests()
    yield
    reset_counts_for_tests()


def _never_called_complete(messages, schema):
    raise AssertionError("repair completer must not be invoked on a clean fish")


def test_autopilot_action_schema_covers_every_known_action_type():
    schema = controller_io.autopilot_action_schema()
    assert schema["type"] == "object"
    assert schema["additionalProperties"] is True
    branches = schema["oneOf"]
    assert len(branches) == len(controller_io._ACTION_SCHEMAS)
    by_type = {b["properties"]["type"]["const"]: b for b in branches}
    seed_batch = by_type["seed_batch"]
    assert seed_batch["required"] == ["type"]
    assert set(seed_batch["properties"]) == {"type", "n_questions", "suites"}
    assert seed_batch["additionalProperties"] is False
    prompt_mutation = by_type["prompt_mutation"]
    assert prompt_mutation["required"] == ["file", "type"]
    assert set(prompt_mutation["properties"]["mutation"]["enum"]) == {
        "targeted_fix",
        "compress",
        "few_shot_evolution",
    }


def test_autopilot_rationale_schema_shape():
    schema = controller_io.autopilot_rationale_schema()
    assert schema["type"] == "object"
    assert schema["additionalProperties"] is False
    assert schema["properties"]["falsifier"] == {"type": "string"}
    assert schema["properties"]["rubric_scores"] == {"type": "object"}


def test_action_repair_base_url_explicit_env_override_skips_role_resolution(monkeypatch):
    # Setting the explicit URL override must short-circuit BEFORE any config
    # lookup happens -- role resolution touching _get_orchestrator_config at
    # all here would be a bug.
    def _must_not_be_called():
        raise AssertionError("role resolution must not run when URL is explicit")

    monkeypatch.setattr(controller_io, "_get_orchestrator_config", _must_not_be_called)
    monkeypatch.setenv("AUTOPILOT_LOCAL_PLANNER_URL", "http://10.0.0.5:9001/chat/completions")
    assert controller_io._local_planner_base_url() == "http://10.0.0.5:9001"


def test_resolve_role_server_base_url_strips_full_prefix_and_takes_first_instance():
    fake_server_urls = SimpleNamespace(
        as_dict=lambda: {
            "frontdoor": "full:http://localhost:8070,http://localhost:8080,http://localhost:8180"
        }
    )
    fake_config = SimpleNamespace(server_urls=fake_server_urls)
    with patch.object(controller_io, "_get_orchestrator_config", lambda: fake_config):
        assert controller_io._resolve_role_server_base_url("frontdoor") == "http://localhost:8070/v1"


def test_resolve_role_server_base_url_falls_back_to_default_role():
    fake_server_urls = SimpleNamespace(as_dict=lambda: {"frontdoor": "http://localhost:8070"})
    fake_config = SimpleNamespace(server_urls=fake_server_urls)
    with patch.object(controller_io, "_get_orchestrator_config", lambda: fake_config):
        assert (
            controller_io._resolve_role_server_base_url("some_unconfigured_role")
            == "http://localhost:8070/v1"
        )


def test_resolve_role_server_base_url_raises_when_nothing_resolves():
    fake_server_urls = SimpleNamespace(as_dict=lambda: {})
    fake_config = SimpleNamespace(server_urls=fake_server_urls)
    with patch.object(controller_io, "_get_orchestrator_config", lambda: fake_config):
        with pytest.raises(RuntimeError):
            controller_io._resolve_role_server_base_url("frontdoor")


def test_local_planner_base_url_resolves_a_llama_server_role_not_the_orchestrator_api(
    monkeypatch,
):
    """The point of this fix: the default target must be a llama-server role
    URL, never the orchestrator's own :8000 API (HS-OD-1 refuses
    response_format there -- src/api/models/openai.py)."""
    monkeypatch.delenv("AUTOPILOT_LOCAL_PLANNER_URL", raising=False)
    monkeypatch.delenv("AUTOPILOT_LOCAL_PLANNER_ROLE", raising=False)
    fake_server_urls = SimpleNamespace(as_dict=lambda: {"frontdoor": "http://localhost:8070"})
    fake_config = SimpleNamespace(server_urls=fake_server_urls)
    with patch.object(controller_io, "_get_orchestrator_config", lambda: fake_config):
        url = controller_io._local_planner_base_url()
    assert url == "http://localhost:8070/v1"
    assert ":8000" not in url


def test_local_planner_base_url_honors_role_env_override(monkeypatch):
    monkeypatch.delenv("AUTOPILOT_LOCAL_PLANNER_URL", raising=False)
    monkeypatch.setenv("AUTOPILOT_LOCAL_PLANNER_ROLE", "worker_general")
    fake_server_urls = SimpleNamespace(
        as_dict=lambda: {
            "frontdoor": "http://localhost:8070",
            "worker_general": "http://localhost:8072",
        }
    )
    fake_config = SimpleNamespace(server_urls=fake_server_urls)
    with patch.object(controller_io, "_get_orchestrator_config", lambda: fake_config):
        assert controller_io._local_planner_base_url() == "http://localhost:8072/v1"


def test_action_repair_completer_defers_resolution_failure_to_invocation(monkeypatch):
    monkeypatch.delenv("AUTOPILOT_LOCAL_PLANNER_URL", raising=False)

    def _raise_config():
        raise RuntimeError("config unavailable in this context")

    with patch.object(controller_io, "_get_orchestrator_config", _raise_config):
        complete = controller_io.action_repair_completer()  # must not raise here
        with pytest.raises(RuntimeError):
            complete([{"role": "user", "content": "x"}], {"type": "object"})


def test_extract_action_with_repair_clean_parse_never_calls_completer():
    text = """```json:autopilot_actions
{"type": "seed_batch", "n_questions": 10}
```"""
    result = controller_io.extract_action_with_repair(text, complete=_never_called_complete, site="t.a1")
    assert result.status == "parsed"
    assert result.value == {"type": "seed_batch", "n_questions": 10}
    assert result.repair_calls == 0


def test_extract_action_with_repair_recovers_malformed_block_no_fallback_needed():
    # The fence is missing its closing marker entirely -- extract_action()'s
    # deterministic fish has nothing usable to find here.
    text = "I will run a seed batch of 10 questions next, type seed_batch."
    calls = []

    def fake_complete(messages, schema):
        calls.append(schema)
        return _json.dumps({"type": "seed_batch", "n_questions": 10})

    result = controller_io.extract_action_with_repair(text, complete=fake_complete, site="t.a2")
    assert result.status == "repaired"
    assert result.value == {"type": "seed_batch", "n_questions": 10}
    assert result.repair_calls == 1
    assert len(calls) == 1
    assert STRUCTURED_OUTPUT_REPAIR_COUNTS[("t.a2", "repaired")] == 1


def test_extract_action_with_repair_never_invents_a_tier_the_draft_never_states():
    """Reproduces the 2026-09-24 live smoke exactly: draft prose plus a
    truncated deep_eval action with no stated tier repaired, pre-fix, to a
    fabricated tier=2 that would have driven a real autopilot action.
    require_evidence=True (now on by default inside extract_action_with_repair)
    must reject this instead of dispatching an invented value."""
    text = (
        "The architect's quality has plateaued over the last several trials; "
        'it is time for another evaluation round. ```json:autopilot_actions\n'
        '{"type": "deep_eval", "reason": "architect quality plateaued'
    )  # truncated mid-string, exactly like the live draft; no tier anywhere

    def fake_complete(messages, schema):
        return _json.dumps({"type": "deep_eval", "tier": 2})

    result = controller_io.extract_action_with_repair(text, complete=fake_complete, site="t.notier")
    assert result.status == "failed"
    assert result.value is None  # never a fabricated tier
    assert "tier" in result.reason


def test_extract_action_with_repair_accepts_a_stated_tier():
    text = (
        "The architect's quality has plateaued; run a deep_eval at tier 1 to "
        "confirm before any structural change."
    )

    def fake_complete(messages, schema):
        return _json.dumps({"type": "deep_eval", "tier": 1})

    result = controller_io.extract_action_with_repair(text, complete=fake_complete, site="t.withtier")
    assert result.status == "repaired"
    assert result.value == {"type": "deep_eval", "tier": 1}


def test_extract_action_with_repair_unrepairable_matches_pre_repair_failure_shape():
    text = "no action here at all, just prose"

    def fake_complete(messages, schema):
        return "still not json"

    result = controller_io.extract_action_with_repair(text, complete=fake_complete, site="t.a3")
    assert result.status == "failed"
    assert result.value is None  # never a fabricated action
    assert STRUCTURED_OUTPUT_REPAIR_COUNTS[("t.a3", "failed")] == 1


def test_extract_action_with_repair_transport_failure_is_typed_failed():
    def raising_complete(messages, schema):
        raise ConnectionError("no local planner")

    result = controller_io.extract_action_with_repair(
        "prose only, no action", complete=raising_complete, site="t.a4"
    )
    assert result.status == "failed"
    assert result.value is None
    assert "transport_error" in result.reason


def test_extract_rationale_with_repair_absent_marker_never_calls_completer():
    text = "```json:autopilot_actions\n{\"type\": \"seed_batch\"}\n```"
    result = controller_io.extract_rationale_with_repair(
        text, complete=_never_called_complete, site="t.r1"
    )
    assert result.status == "parsed"
    assert result.value == {"falsifier": "", "rubric_scores": {}}
    assert result.repair_calls == 0


def test_extract_rationale_with_repair_recovers_malformed_block():
    text = (
        "```json:autopilot_rationale\n"
        '{"falsifier": "x", "rubric_scores": {"info_gain": 4},\n'  # trailing comma / no close
        "```\n"
    )

    def fake_complete(messages, schema):
        return _json.dumps({"falsifier": "x", "rubric_scores": {"info_gain": 4}})

    result = controller_io.extract_rationale_with_repair(text, complete=fake_complete, site="t.r2")
    assert result.status == "repaired"
    assert result.value == {"falsifier": "x", "rubric_scores": {"info_gain": 4}}
    assert result.repair_calls == 1


def test_extract_rationale_with_repair_unrepairable_falls_back_to_empty_default():
    text = "```json:autopilot_rationale\nnot json at all\n```"

    def fake_complete(messages, schema):
        return "still garbage"

    result = controller_io.extract_rationale_with_repair(text, complete=fake_complete, site="t.r3")
    assert result.status == "failed"
    # Same empty-default SHAPE the pre-repair extract_rationale() always
    # returned on a malformed block -- the caller can distinguish via .status.
    assert result.value == {"falsifier": "", "rubric_scores": {}}
