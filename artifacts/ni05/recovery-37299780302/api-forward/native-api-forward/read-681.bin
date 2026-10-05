"""Regression: per-request tool telemetry must be request-local, not read from
the process-global ToolRegistry invocation log.

Repro (review finding, 2026-06-04): the orchestrator creates ONE shared
ToolRegistry (src/api/__init__.py); its invocation log is never cleared per
request. repl_executor used to fall back to that log (and count len(tool_timings)
from it), so a later NO-TOOL request reported a prior request's tools
(tools_called=['foo'], tools_used=1). The fix captures records per-REPL in
_invoke_tool (context.py) and repl_executor reads ONLY repl._invoked_tools.
"""
from __future__ import annotations

from types import SimpleNamespace

from src.repl_environment import REPLConfig, REPLEnvironment


class _SharedLogRegistry:
    """Mimics the real registry: invoke() appends to a PROCESS-GLOBAL log that is
    shared across REPLs and never cleared per request."""

    def __init__(self) -> None:
        self._log: list = []

    def invoke(self, tool_name: str, role: str, **kwargs):
        self._log.append(
            SimpleNamespace(
                tool_name=tool_name, success=True, elapsed_ms=1.0,
                chain_id=kwargs.get("chain_id"),
                caller_type=kwargs.get("caller_type", "direct"),
                result="r",
            )
        )
        return "r"

    def get_invocation_log(self):
        return list(self._log)

    def list_tools(self, role=None):
        return []

    def get_read_only_tools(self):
        return set()

    def get_chainable_tools(self):
        return set()


class _StructuredRegistry:
    """Mimics invoke() under ORCHESTRATOR_STRUCTURED_TOOL_OUTPUT=1: returns a
    ToolOutput envelope and converts a handler FAILURE to ok=False WITHOUT
    raising (mirrors src/registry/tool_registry.py invoke())."""

    def __init__(self, ok: bool = True, output=None) -> None:
        self._ok = ok
        self._output = output

    def invoke(self, tool_name: str, role: str, **kwargs):
        from src.registry.tool_registry import ToolOutput

        return ToolOutput(
            ok=self._ok,
            status="success" if self._ok else "error",
            output=self._output,
        )

    def list_tools(self, role=None):
        return []

    def get_read_only_tools(self):
        return set()

    def get_chainable_tools(self):
        return set()


def _repl(reg) -> REPLEnvironment:
    return REPLEnvironment(context="x", config=REPLConfig(structured_mode=True), tool_registry=reg)


def test_no_tool_request_reports_no_tools_despite_shared_log():
    reg = _SharedLogRegistry()
    r1 = _repl(reg)
    r2 = _repl(reg)

    # Request 1 calls a tool -> shared registry log now holds it.
    r1.execute('TOOL("foo")')
    assert reg.get_invocation_log(), "precondition: shared log accumulated request 1's call"

    # Request 2 makes NO tool call.
    r2.execute("x = 1 + 1")

    # Request-local telemetry: r2 reports nothing even though the shared log is
    # non-empty (the old fallback would have leaked ['foo']/used=1 here).
    r2_names = [rec.tool_name for rec in r2._invoked_tools]
    assert r2_names == [], f"no-tool request leaked tools from shared log: {r2_names}"
    assert max(r2._tool_invocations, len(r2._invoked_tools)) == 0

    # Request 1's own telemetry is intact and records the ToolInvocation-like
    # interface repl_executor consumes.
    r1_names = [rec.tool_name for rec in r1._invoked_tools]
    assert r1_names == ["foo"]
    rec = r1._invoked_tools[0]
    assert rec.success is True
    for attr in ("tool_name", "elapsed_ms", "success", "chain_id", "caller_type", "result"):
        assert hasattr(rec, attr), f"record missing {attr}"


def test_structured_success_records_raw_output_not_envelope():
    """Under structured output, invoke() returns ToolOutput(ok=True, output=dict);
    the request-local record must hold the RAW dict (not the envelope) so
    consumers like web_research extraction (isinstance(result, dict)) work."""
    reg = _StructuredRegistry(ok=True, output={"query": "q", "pages_fetched": 3})
    r = _repl(reg)
    r.execute('TOOL("web_research")')
    rec = r._invoked_tools[-1]
    assert rec.success is True
    assert isinstance(rec.result, dict), f"result should be the raw dict, got {type(rec.result)}"
    assert rec.result["pages_fetched"] == 3


def test_structured_failure_records_success_false():
    """A handler failure converted to ToolOutput(ok=False) (no exception) must be
    recorded success=False, NOT True-because-no-exception."""
    reg = _StructuredRegistry(ok=False, output="boom")
    r = _repl(reg)
    r.execute('TOOL("foo")')
    rec = r._invoked_tools[-1]
    assert rec.success is False, "structured ok=False must record success=False"
