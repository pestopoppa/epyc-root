"""Real FastMCP argument validation, including the future separate memory server."""

import asyncio
import importlib.util
from pathlib import Path

import pytest

fastmcp = pytest.importorskip("fastmcp")
_PATH = Path(__file__).resolve().parents[2] / "scripts/harness/hs4_mcp_session_contract.py"
_SPEC = importlib.util.spec_from_file_location("hs4_mcp_session_contract", _PATH)
gate = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(gate)


def test_memory_server_accepts_stamp_and_refuses_unknown_before_execution():
    server = fastmcp.FastMCP("memory")
    calls = []

    @server.tool
    def profile_get(session_id: str = "") -> str:
        calls.append(session_id)
        return "{}"

    result = asyncio.run(gate.check_server(server, probe_tool="profile_get", probe_args={}))
    assert result["verdict"] == "pass"
    assert calls == ["ses_hs4_contract"]  # The refused call never executes.


@pytest.mark.parametrize("kind", ["missing", "required", "wrong_type", "permissive"])
def test_bad_memory_contract_is_rejected_before_any_tool_runs(kind):
    server = fastmcp.FastMCP("memory")

    def missing() -> str:
        raise AssertionError("must not execute")

    def required(session_id: str) -> str:
        raise AssertionError("must not execute")

    def wrong_type(session_id: int = 0) -> str:
        raise AssertionError("must not execute")

    # FastMCP itself rejects **kwargs; test its permissive-schema boundary using
    # the registered tool's schema, without calling a possibly unsafe handler.
    server.tool(name="profile_get")({"missing": missing, "required": required,
                                      "wrong_type": wrong_type, "permissive": missing}[kind])
    if kind == "permissive":
        tool = asyncio.run(server.get_tool("profile_get"))
        tool.parameters = {"type": "object", "properties": {
            "session_id": {"type": "string"}}, "additionalProperties": True}
    with pytest.raises(ValueError, match="optional string|undeclared arguments"):
        asyncio.run(gate.check_server(server, probe_tool="profile_get", probe_args={}))


def test_absent_memory_server_surface_does_not_vacuously_pass():
    server = fastmcp.FastMCP("empty")
    with pytest.raises(ValueError, match="no selected tools"):
        asyncio.run(gate.check_server(server, probe_tool="profile_get", probe_args={}))


def test_probe_must_be_in_selected_server_surface():
    server = fastmcp.FastMCP("memory")

    @server.tool
    def profile_get(session_id: str = "") -> str:
        raise AssertionError("must not execute")

    with pytest.raises(ValueError, match="outside selection"):
        asyncio.run(gate.check_server(server, probe_tool="profile_get", probe_args={}, prefix="memory_"))


def test_absent_memory_server_does_not_pass_vacuously():
    server = fastmcp.FastMCP("empty-memory")
    with pytest.raises(ValueError, match="no selected tools"):
        asyncio.run(gate.check_server(server, probe_tool="profile_get", probe_args={}))


@pytest.mark.parametrize("key", ["session_id", "hs4_undeclared_probe"])
def test_probe_cannot_override_contract_arguments(key):
    server = fastmcp.FastMCP("memory")
    with pytest.raises(ValueError, match="must not override"):
        asyncio.run(gate.check_server(server, probe_tool="profile_get", probe_args={key: "x"}))
