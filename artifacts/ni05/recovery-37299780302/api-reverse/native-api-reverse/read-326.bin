"""Unit tests for scripts/benchmark/eval_log_format.py."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


_ROOT = Path(__file__).resolve().parents[2] / "scripts" / "benchmark"
sys.path.insert(0, str(_ROOT))
_SPEC = importlib.util.spec_from_file_location("eval_log_format_test", _ROOT / "eval_log_format.py")
_MOD = importlib.util.module_from_spec(_SPEC)
sys.modules["eval_log_format_test"] = _MOD
_SPEC.loader.exec_module(_MOD)


def test_compute_tps_elapsed_generation_predicted_and_zero():
    assert _MOD.compute_tps({"tokens_generated": 10}, elapsed=2.0) == 5.0
    assert _MOD.compute_tps({"tokens_generated": 8, "generation_ms": 4000.0}, elapsed=0.0) == 2.0
    assert _MOD.compute_tps({"predicted_tps": 3.5}, elapsed=0.0) == 3.5
    assert _MOD.compute_tps({}, elapsed=0.0) == 0.0


def test_compute_effective_tps_with_tools_delegates_and_fallback():
    resp = {
        "tokens_generated": 20,
        "tool_output_tokens": 5,
        "delegation_events": [{"tokens_generated": 15}, {"tokens_generated": 0}],
    }
    assert _MOD.compute_effective_tps(resp, elapsed=4.0) == 10.0
    assert _MOD.compute_effective_tps({"tokens_generated": 6, "generation_ms": 3000.0}, elapsed=0.0) == 2.0


def test_tps_str_and_effective_tokens_helpers():
    assert _MOD._tps_str(0.0, 0.0) == ""
    assert _MOD._tps_str(3.2, 3.25) == ", 3.2 t/s"
    assert _MOD._tps_str(3.0, 4.0) == ", 4.0 eff t/s (3.0 model)"
    assert _MOD._effective_tokens(
        {
            "tokens_generated": 10,
            "tool_output_tokens": 7,
            "delegation_events": [{"tokens_generated": 3}],
        }
    ) == 20


def test_token_and_status_helpers():
    assert _MOD._token_str({"tokens_generated": 0, "tokens_generated_estimate": 42}, "INFRA") == "0 tok, est 42 tok"
    assert _MOD._token_str(
        {"tokens_generated": 5, "tool_output_tokens": 2, "delegation_events": [{"tokens_generated": 3}]},
        "PASS",
    ) == "10 eff tok (5 model)"
    assert _MOD._token_str({"tokens_generated": 5}, "PASS") == "5 tok"

    assert _MOD._status_str(None, None) == "INFRA"
    assert _MOD._status_str(True, None) == "PASS"
    assert _MOD._status_str(False, "boom") == "ERROR"
    assert _MOD._status_str(False, None) == "FAIL"


def test_timing_str_paths():
    assert _MOD._timing_str({}) == ""

    prompt_only = _MOD._timing_str(
        {
            "prompt_eval_ms": 2000.0,
            "cache_stats": {
                "frontdoor": {"total_prompt_tokens": 1000},
            },
        }
    )
    assert "prefill=2.0s" in prompt_only
    assert "500 pp/s" in prompt_only

    prompt_flat_fallback = _MOD._timing_str(
        {
            "prompt_eval_ms": 1000.0,
            "cache_stats": {"total_prompt_tokens": 200},
        }
    )
    assert "200 pp/s" in prompt_flat_fallback

    gen_only = _MOD._timing_str({"generation_ms": 2500.0, "tokens_generated": 5})
    assert gen_only == " [gen=2.5s 2.0 t/s]"

    both = _MOD._timing_str(
        {
            "prompt_eval_ms": 1000.0,
            "generation_ms": 2000.0,
            "tokens_generated": 10,
            "cache_stats": {"frontdoor": {"total_prompt_tokens": 500}},
        }
    )
    assert "prefill=1.0s 500 pp/s" in both
    assert "gen=2.0s 5.0 t/s" in both


def test_dedup_consecutive():
    assert _MOD._dedup_consecutive([]) == []
    assert _MOD._dedup_consecutive(["a", "a", "b", "b", "a"]) == ["a", "b", "a"]


def test_format_self_direct_variants():
    lines = _MOD.format_self_direct(
        "SELF:direct",
        passed=True,
        error=None,
        elapsed=2.0,
        resp={"tokens_generated": 10, "generation_ms": 1000.0},
    )
    assert len(lines) == 1
    assert "SELF:direct → PASS" in lines[0]
    assert "10 tok" in lines[0]

    infra = _MOD.format_self_direct(
        "SELF:direct",
        passed=False,
        error="down",
        elapsed=1.0,
        resp={"tokens_generated": 0, "tokens_generated_estimate": 12},
        infra=True,
    )[0]
    assert "INFRA" in infra
    assert "est 12 tok" in infra


def test_format_self_repl_with_tools_and_timings():
    lines = _MOD.format_self_repl(
        "SELF:repl",
        passed=False,
        error="oops",
        elapsed=4.0,
        resp={
            "tokens_generated": 8,
            "tools_used": 3,
            "tools_called": ["peek", "peek", "grep"],
            "tool_timings": [
                {"tool_name": "peek", "elapsed_ms": 120.0, "success": True},
                {"tool_name": "grep", "elapsed_ms": 85.0, "success": False},
            ],
        },
    )
    assert "SELF:repl → ERROR" in lines[0]
    assert "3 tools" in lines[0]
    assert "tools: peek, grep" in lines[1]
    assert "peek: 120ms (ok)" in lines[2]
    assert "grep: 85ms (fail)" in lines[3]


def test_format_architect_result_with_tools_delegates_chain_and_infra():
    lines = _MOD.format_architect_result(
        "ARCHITECT",
        passed=True,
        error=None,
        elapsed=10.0,
        resp={
            "tokens_generated": 20,
            "tools_used": 1,
            "tools_called": ["peek"],
            "tool_timings": [{"tool_name": "peek", "elapsed_ms": 12.0, "success": True}],
            "delegation_events": [
                {"to_role": "worker_math", "elapsed_ms": 2000.0, "tokens_generated": 20, "success": True},
                {"to_role": "worker_math", "elapsed_ms": 1500.0, "tokens_generated": 0, "success": None},
                {"to_role": "coder_escalation", "elapsed_ms": 1000.0, "tokens_generated": 10, "success": False},
            ],
            "role_history": ["architect_general", "worker_math", "coder_escalation"],
        },
    )
    assert "ARCHITECT → PASS" in lines[0]
    assert "tools: peek" in lines[1]
    assert "delegates: 3 (2x worker_math, coder_escalation)" in lines[3]
    assert any("delegate: worker_math" in line for line in lines)
    assert any("chain: architect_general → worker_math → coder_escalation" in line for line in lines)

    infra_line = _MOD.format_architect_result(
        "ARCHITECT",
        passed=None,
        error="down",
        elapsed=1.0,
        resp={},
    )[0]
    assert "INFRA" in infra_line


def test_reward_skip_helpers_and_subformatters():
    assert _MOD.format_reward_skip("SELF:direct") == ["    SELF:direct -> INFRA_SKIP (not injecting reward)"]
    assert _MOD.format_reward_skip("SELF:direct", reason="X") == ["    SELF:direct -> X (not injecting reward)"]
    assert _MOD.format_all_infra_skip("ARCHITECT") == ["    ARCHITECT -> ALL INFRA_SKIP"]

    timings = _MOD._format_tool_timings(
        [
            {"tool_name": "peek", "elapsed_ms": 10.0, "success": True},
            {"tool_name": "grep", "elapsed_ms": 20.0, "success": False},
        ]
    )
    assert timings == ["      peek: 10ms (ok)", "      grep: 20ms (fail)"]

    single = _MOD._format_delegation_events(
        [{"to_role": "worker_math", "elapsed_ms": 0.0, "tokens_generated": 0, "success": None}]
    )
    assert single == ["      delegate: worker_math → ? (0ms, 0 tok)"]
