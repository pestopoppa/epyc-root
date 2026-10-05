"""Unit tests for gate-3 telemetry-contract helpers (no inference).

Validates the HARD get_eval_secret contract, the request-local isolation check,
and the SOFT web_research classifier (incl. the structured-unwrap guard) against
synthetic /chat response dicts — so the gate logic is verified before deploy.
"""
from __future__ import annotations

import sys
from pathlib import Path

_AP = Path(__file__).resolve().parents[2] / "scripts" / "autopilot"
if str(_AP) not in sys.path:
    sys.path.insert(0, str(_AP))

from gate3_tool_telemetry import (  # noqa: E402
    _gate_parallelism,
    _gate_request_timeout,
    _gate_skip_soft,
    check_env,
    check_get_eval_secret_contract,
    check_isolation,
    classify_web_research,
    tool_name_counts,
)


def _ges(success: bool = True) -> dict:
    return {
        "tools_called": ["get_eval_secret"],
        "tools_used": 1,
        "tool_timings": [{"tool_name": "get_eval_secret", "elapsed_ms": 1.0, "success": success}],
    }


def test_get_eval_secret_contract_passes_on_clean_batch():
    ok, lines = check_get_eval_secret_contract([_ges(), _ges(), _ges()])
    assert ok, lines
    assert tool_name_counts([_ges(), _ges(), _ges()])["get_eval_secret"] == 3


def test_get_eval_secret_contract_fails_under_min():
    ok, _ = check_get_eval_secret_contract([_ges(), _ges()])
    assert not ok  # only 2 < 3


def test_get_eval_secret_contract_fails_on_any_failed_timing_row():
    ok, _ = check_get_eval_secret_contract([_ges(True), _ges(True), _ges(False)])
    assert not ok  # one row success is not True


def test_isolation_pass_and_fail():
    assert check_isolation({"tools_called": [], "tools_used": 0})[0] is True
    assert check_isolation({"tools_called": ["foo"], "tools_used": 1})[0] is False


def test_web_research_pass():
    status, _ = classify_web_research({
        "tools_called": ["web_research"],
        "tool_timings": [{"tool_name": "web_research", "success": True}],
        "web_research_results": [{"query": "q", "pages_fetched": 2}],
    })
    assert status == "PASS"


def test_web_research_success_with_response_error_is_infra_not_pass():
    status, lines = classify_web_research({
        "error_code": 500,
        "tools_called": ["web_research"],
        "tool_timings": [{"tool_name": "web_research", "success": True}],
        "web_research_results": [{"query": "q", "pages_fetched": 1}],
    })
    assert status == "INFRA_FAIL"
    assert "post-tool error" in " ".join(lines)


def test_web_research_success_but_empty_results_is_infra_not_pass():
    """Guards the structured-unwrap regression: success rows but empty results."""
    status, lines = classify_web_research({
        "tools_called": ["web_research"],
        "tool_timings": [{"tool_name": "web_research", "success": True}],
        "web_research_results": [],
    })
    assert status == "INFRA_FAIL"
    assert "EMPTY" in " ".join(lines)


def test_web_research_all_marked_irrelevant_is_infra_not_pass():
    status, lines = classify_web_research({
        "tools_called": ["web_research"],
        "tool_timings": [{"tool_name": "web_research", "success": True}],
        "web_research_results": [
            {
                "query": "q",
                "pages_fetched": 2,
                "pages_synthesized": 1,
                "pages_irrelevant": 0,
                "sources": [{"url": "https://example.test/a", "relevant": False}],
            }
        ],
    })
    assert status == "INFRA_FAIL"
    assert "relevant=False" in " ".join(lines)


def test_web_research_result_success_false_is_infra_not_pass():
    status, lines = classify_web_research({
        "tools_called": ["web_research"],
        "tool_timings": [{"tool_name": "web_research", "success": True}],
        "web_research_results": [
            {
                "success": False,
                "query": "q",
                "error": "Search failed",
                "no_results_reason": "search_failed",
                "sources": [],
            }
        ],
    })
    assert status == "INFRA_FAIL"
    assert "search_failed" in " ".join(lines)


def test_web_research_all_irrelevant_pages_is_infra_not_pass():
    status, lines = classify_web_research({
        "tools_called": ["web_research"],
        "tool_timings": [{"tool_name": "web_research", "success": True}],
        "web_research_results": [
            {
                "query": "q",
                "pages_fetched": 4,
                "pages_synthesized": 2,
                "pages_irrelevant": 2,
                "sources": [{"url": "https://example.test/a", "relevant": True}],
            }
        ],
    })
    assert status == "INFRA_FAIL"
    assert "pages_irrelevant == pages_synthesized" in " ".join(lines)


def test_web_research_high_irrelevant_rate_is_infra_not_pass():
    status, lines = classify_web_research({
        "tools_called": ["web_research"],
        "tool_timings": [{"tool_name": "web_research", "success": True}],
        "web_research_results": [
            {
                "query": "q",
                "pages_fetched": 10,
                "pages_synthesized": 10,
                "pages_irrelevant": 3,
                "sources": [{"url": "https://example.test/a", "relevant": True}],
            }
        ],
    })
    assert status == "INFRA_FAIL"
    assert "irrelevant_rate too high" in " ".join(lines)


def test_web_research_post_tool_error_is_infra_not_pass():
    status, lines = classify_web_research({
        "tools_called": ["web_research"],
        "tool_timings": [{"tool_name": "web_research", "success": True}],
        "web_research_results": [
            {
                "query": "q",
                "pages_fetched": 1,
                "pages_synthesized": 1,
                "pages_irrelevant": 0,
                "sources": [{"url": "https://example.test/a", "relevant": True}],
            }
        ],
        "error": "[FAILED: terminal post-tool failure]",
    })
    assert status == "INFRA_FAIL"
    assert "post-tool error" in " ".join(lines)


def test_web_research_tool_failure_is_infra():
    status, _ = classify_web_research({
        "tools_called": ["web_research"],
        "tool_timings": [{"tool_name": "web_research", "success": False}],
        "web_research_results": [],
    })
    assert status == "INFRA_FAIL"


def test_web_research_not_routed_is_inconclusive():
    status, _ = classify_web_research({"tools_called": [], "tool_timings": []})
    assert status == "INCONCLUSIVE"


def test_web_research_request_error_is_infra():
    status, _ = classify_web_research({"error": "500 Server Error"})
    assert status == "INFRA_FAIL"


def test_gate_request_timeout_defaults_and_clamps(monkeypatch):
    monkeypatch.delenv("AUTOPILOT_GATE3_REQUEST_TIMEOUT_S", raising=False)
    assert _gate_request_timeout(270) == 270

    monkeypatch.setenv("AUTOPILOT_GATE3_REQUEST_TIMEOUT_S", "120")
    assert _gate_request_timeout(270) == 120

    monkeypatch.setenv("AUTOPILOT_GATE3_REQUEST_TIMEOUT_S", "999")
    assert _gate_request_timeout(270) == 270

    monkeypatch.setenv("AUTOPILOT_GATE3_REQUEST_TIMEOUT_S", "bad")
    assert _gate_request_timeout(270) == 270


def test_gate_skip_soft_parses_truthy_values(monkeypatch):
    monkeypatch.delenv("AUTOPILOT_GATE3_SKIP_SOFT", raising=False)
    assert _gate_skip_soft() is False

    monkeypatch.setenv("AUTOPILOT_GATE3_SKIP_SOFT", "1")
    assert _gate_skip_soft() is True

    monkeypatch.setenv("AUTOPILOT_GATE3_SKIP_SOFT", "yes")
    assert _gate_skip_soft() is True

    monkeypatch.setenv("AUTOPILOT_GATE3_SKIP_SOFT", "false")
    assert _gate_skip_soft() is False


def test_gate_parallelism_defaults_to_serial(monkeypatch):
    monkeypatch.delenv("AUTOPILOT_GATE3_PARALLELISM", raising=False)
    monkeypatch.delenv("AUTOPILOT_EVAL_CONCURRENCY", raising=False)
    assert _gate_parallelism() == 1


def test_gate_parallelism_uses_gate_override_first(monkeypatch):
    monkeypatch.setenv("AUTOPILOT_EVAL_CONCURRENCY", "2")
    monkeypatch.setenv("AUTOPILOT_GATE3_PARALLELISM", "4")
    assert _gate_parallelism() == 4


def test_gate_parallelism_falls_back_to_eval_concurrency(monkeypatch):
    monkeypatch.delenv("AUTOPILOT_GATE3_PARALLELISM", raising=False)
    monkeypatch.setenv("AUTOPILOT_EVAL_CONCURRENCY", "3")
    assert _gate_parallelism() == 3


def test_gate_parallelism_invalid_or_low_values_are_serial(monkeypatch):
    monkeypatch.setenv("AUTOPILOT_GATE3_PARALLELISM", "bad")
    monkeypatch.setenv("AUTOPILOT_EVAL_CONCURRENCY", "3")
    assert _gate_parallelism() == 1

    monkeypatch.setenv("AUTOPILOT_GATE3_PARALLELISM", "0")
    assert _gate_parallelism() == 1


def test_check_env_suggests_gate3_profile_when_api_lacks_sentinel(monkeypatch):
    import gate3_tool_telemetry as gate3

    monkeypatch.setenv("AUTOPILOT_TOOL_SENTINELS", "1")
    monkeypatch.setattr(gate3, "_orchestrator_pid", lambda: 12345)
    monkeypatch.setattr(
        gate3,
        "_read_environ",
        lambda _pid: {"ORCHESTRATOR_STRUCTURED_TOOL_OUTPUT": "1"},
    )

    ok, lines = check_env()

    assert not ok
    text = " ".join(lines)
    assert "gate3-tool-telemetry" in text
    assert "reload orchestrator" in text


def test_check_env_suggests_driver_env_when_driver_flag_missing(monkeypatch):
    import gate3_tool_telemetry as gate3

    monkeypatch.delenv("AUTOPILOT_TOOL_SENTINELS", raising=False)
    monkeypatch.setattr(gate3, "_orchestrator_pid", lambda: 12345)
    monkeypatch.setattr(
        gate3,
        "_read_environ",
        lambda _pid: {
            "AUTOPILOT_TOOL_SENTINELS": "1",
            "ORCHESTRATOR_STRUCTURED_TOOL_OUTPUT": "1",
        },
    )

    ok, lines = check_env()

    assert not ok
    assert "launch this driver with AUTOPILOT_TOOL_SENTINELS=1" in " ".join(lines)
