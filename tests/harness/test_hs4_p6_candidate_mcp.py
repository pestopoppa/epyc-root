"""P6 isolated adapter controls against the actual shared core and FastMCP."""
import asyncio
import importlib.util
import os
from pathlib import Path
import sys

import pytest

fastmcp = pytest.importorskip("fastmcp")
CHECKOUT = Path(os.environ.get("HS4_P6_ORCHESTRATOR_ROOT", "/mnt/raid0/llm/epyc-orchestrator"))
if not (CHECKOUT / "src/repl_environment/exploration_core.py").is_file():
    pytest.skip("set HS4_P6_ORCHESTRATOR_ROOT to the pinned shared-core checkout", allow_module_level=True)
sys.path.insert(0, str(CHECKOUT))
from src.repl_environment import exploration_core as core

_PATH = Path(__file__).resolve().parents[2] / "scripts/harness/hs4_p6_candidate_mcp.py"
_SPEC = importlib.util.spec_from_file_location("hs4_p6_candidate_mcp", _PATH)
adapter = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(adapter)


@pytest.fixture
def seat(tmp_path):
    root = tmp_path / "allowed"
    root.mkdir()
    (root / "sample.py").write_text("def hello():\n    return 42\n" + "hit " * 200 + "\n")
    server = fastmcp.FastMCP("candidate")
    adapter.register_exploration_tools(server, [root], core=core)
    return server, root


def call(seat, tool, **kwargs):
    server, root = seat
    async def run():
        async with fastmcp.Client(server) as client:
            return await client.call_tool(tool, dict(root=str(root), session_id="ses_test", **kwargs),
                                          raise_on_error=False)
    return asyncio.run(run())


def test_live_catalog_and_argument_contract(seat):
    async def run():
        async with fastmcp.Client(seat[0]) as client:
            tools = await client.list_tools()
            assert {t.name for t in tools} == {"read_range", "peek", "grep", "peek_grep", "outline", "code_search"}
            for tool in tools:
                assert tool.inputSchema["additionalProperties"] is False
                assert "session_id" not in tool.inputSchema.get("required", [])
                assert tool.inputSchema["properties"]["session_id"]["type"] == "string"
    asyncio.run(run())
    assert not call(seat, "read_range", path="sample.py").is_error
    assert call(seat, "read_range", path="sample.py", undeclared="refuse").is_error


@pytest.mark.parametrize("tool,extra", [
    ("read_range", {}), ("peek", {}), ("grep", {"pattern": "secret"}),
    ("peek_grep", {"pattern": "secret"}), ("outline", {}),
])
@pytest.mark.parametrize("escape", ["../secret.py", "link.py"])
def test_every_tool_refuses_traversal_and_symlink_escape(seat, tool, extra, escape):
    root = seat[1]
    (root.parent / "secret.py").write_text("secret = 1")
    (root / "link.py").symlink_to(root.parent / "secret.py")
    assert call(seat, tool, path=escape, **extra).is_error


def test_root_admission_cannot_be_overridden_by_session(seat):
    server, root = seat
    assert call((server, root.parent), "read_range", path="allowed/sample.py").is_error
    assert call((server, Path(".")), "read_range", path="sample.py").is_error


def test_adapter_uses_shared_read_and_outline_semantics(seat):
    for tool, expected in [
        ("read_range", core.read_range(str(seat[1]), "sample.py")),
        ("peek", core.read_file_page(str(seat[1]), "sample.py")),
        ("outline", core.outline_file(str(seat[1]), "sample.py")),
    ]:
        result = call(seat, tool, path="sample.py")
        assert not result.is_error
        assert result.content[0].text == expected


def test_grep_caps_and_combined_adapter_agree(seat):
    (seat[1] / "many.txt").write_text(("hit " * 300 + "\n") * 250)
    plain = call(seat, "grep", path="many.txt", pattern="hit", context=999, max_hits=999)
    combined = call(seat, "peek_grep", path="many.txt", pattern="hit", context=999, max_hits=999)
    assert not plain.is_error and not combined.is_error
    assert plain.data == combined.data
    assert plain.data["total"] == 250 and plain.data["truncated"]
    assert len(plain.data["matches"]) == 80
    assert all(len(m["line"]) <= 240 and len(m["context"]) <= 1680
               for m in plain.data["matches"])


@pytest.mark.parametrize("tool,extra", [("peek", {}), ("read_range", {}),
    ("grep", {"pattern": "x"}), ("peek_grep", {"pattern": "x"}), ("outline", {})])
def test_every_tool_refuses_oversized_file(seat, tool, extra):
    with (seat[1] / "big.py").open("wb") as handle:
        handle.truncate(core.MAX_FILE_BYTES + 1)
    assert call(seat, tool, path="big.py", **extra).is_error


@pytest.mark.parametrize("n", [-1, 0, 80001])
def test_peek_cannot_request_unbounded_output(seat, n):
    assert call(seat, "peek", path="sample.py", n=n).is_error


def test_empty_admission_refused():
    with pytest.raises(ValueError, match="read-root"):
        adapter.register_exploration_tools(fastmcp.FastMCP("empty"), [], core=core)


def test_search_is_root_bound_and_skips_escape_links(seat):
    root = seat[1]
    (root.parent / "secret.py").write_text("needle = 1")
    (root / "link.py").symlink_to(root.parent / "secret.py")
    (root / "external").symlink_to(root.parent, target_is_directory=True)
    (root / "local.py").write_text("needle = 2")
    result = call(seat, "code_search", query="needle")
    assert not result.is_error
    assert result.data["engine"] == "root-lexical"
    assert [h["path"] for h in result.data["matches"]] == ["local.py"]
    assert call((seat[0], root.parent), "code_search", query="needle").is_error
    assert call(seat, "code_search", query="needle", path="../secret.py").is_error


def test_search_empty_query_and_caps(seat):
    assert call(seat, "code_search", query=" ").is_error
    assert call(seat, "code_search", query="!!!").is_error
    assert call(seat, "code_search", query="x" * 1025).is_error
    for i in range(25):
        (seat[1] / f"hit{i:02}.py").write_text("needle = 1\n")
    result = call(seat, "code_search", query="needle", k=999)
    assert len(result.data["matches"]) == 20
    assert result.data["matches"][0]["path"] == "hit00.py"
    assert len(call(seat, "code_search", query="needle", k=-1).data["matches"]) == 1


def test_search_budget_reports_incomplete_coverage(seat, monkeypatch):
    from scripts.harness import hs4_p6_root_search as search
    monkeypatch.setattr(search, "MAX_TOTAL_BYTES", 1)
    result = call(seat, "code_search", query="hello")
    assert result.data["truncated"]
    assert result.data["bytes_read_budget_used"] <= 1
    monkeypatch.setattr(search, "MAX_TOTAL_BYTES", 1024)
    monkeypatch.setattr(search, "MAX_ENTRIES", 1)
    (seat[1] / "another.py").write_text("hello")
    result = call(seat, "code_search", query="hello")
    assert result.data["truncated"] and result.data["entries_visited"] == 1


def test_search_never_uses_global_clients_or_subprocess(seat, monkeypatch):
    import subprocess
    import socket
    def forbidden(*args, **kwargs):
        raise AssertionError("search attempted external retrieval")
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    before = sorted(p.relative_to(seat[1]) for p in seat[1].rglob("*"))
    assert not call(seat, "code_search", query="hello").is_error
    assert sorted(p.relative_to(seat[1]) for p in seat[1].rglob("*")) == before


def test_search_skips_hidden_binary_large_and_special_inputs(seat):
    root = seat[1]
    (root / ".hidden").mkdir()
    (root / ".hidden/secret.py").write_text("needle")
    (root / "binary.py").write_bytes(b"needle\x00")
    with (root / "big.py").open("wb") as handle:
        handle.truncate(core.MAX_FILE_BYTES + 1)
    os.mkfifo(root / "pipe.py")
    (root / "nested").mkdir()
    (root / "nested/hit.py").write_text("needle\n")
    result = call(seat, "code_search", query="needle")
    assert not result.is_error
    assert [h["path"] for h in result.data["matches"]] == ["nested/hit.py"]
    assert result.data["matches"][0]["start_line"] == 1
    assert result.data["matches"][0]["end_line"] == 1
    assert result.data["skipped"] >= 4
