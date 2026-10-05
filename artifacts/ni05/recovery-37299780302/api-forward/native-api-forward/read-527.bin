"""INF-78 OAB-1: per-request task_root + edit_mode on /chat.

Offline and inference-free. Acceptance (handoff autokernel-orchestrator-actor-backend.md):
  * a write outside task_root is refused; one inside lands (edit_mode="direct");
  * an edit_mode="none" request cannot write at all;
  * read-only tools are confined to task_root + read_roots;
  * two CONCURRENT requests with different roots do not cross (ContextVar, not a global);
  * no scope == production behaviour, unchanged.

Run: .venv/bin/python -m pytest tests/unit/test_oab1_task_scope.py -q
"""
from __future__ import annotations

import asyncio
import os
import shutil
import threading
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from src.repl_environment import task_root as TR

SCRATCH_BASE = Path("/mnt/raid0/llm/tmp")


@pytest.fixture(autouse=True)
def _no_leaked_scope(monkeypatch):
    monkeypatch.delenv(TR.ENV_VAR, raising=False)
    TR.clear_request_scope()
    yield
    TR.clear_request_scope()


@pytest.fixture()
def roots():
    """Two lane 'worktrees' plus a read-only reference dir, strictly below the llm root."""
    base = SCRATCH_BASE / f"test_oab1_{uuid.uuid4().hex[:10]}"
    lane_a, lane_b, ref, outside = base / "lane_a", base / "lane_b", base / "ref", base / "outside"
    for d in (lane_a, lane_b, ref, outside):
        d.mkdir(parents=True)
    (lane_a / "kernel.c").write_text("int a;\n")
    (lane_b / "kernel.c").write_text("int b;\n")
    (ref / "notes.md").write_text("reference\n")
    (outside / "secret.txt").write_text("SECRET\n")
    yield SimpleNamespace(base=base, a=lane_a, b=lane_b, ref=ref, outside=outside)
    shutil.rmtree(base, ignore_errors=True)


@pytest.fixture()
def repl():
    from src.repl_environment.environment import REPLEnvironment

    return REPLEnvironment(context="oab1 test context")


# ── accessors: precedence + default-off parity ──────────────────────────────


def test_no_scope_is_unchanged():
    assert TR.request_scope() is None
    assert TR.task_root_active() is False
    assert TR.resolve_task_path("cart.py") == os.path.realpath("cart.py")
    assert TR.scope_refusal("run_python_code") is None
    assert TR.check_shell_scope(["cat", "/etc/hostname"], "/") is None
    assert TR.check_registry_tool_scope("write_json", {"path": "/x"}, []) is None


def test_request_scope_overrides_env(monkeypatch, roots):
    monkeypatch.setenv(TR.ENV_VAR, str(roots.b))
    assert TR.get_task_root() == roots.b
    TR.begin_request_scope(str(roots.a), "direct")
    assert TR.task_root_active() is True
    assert TR.get_task_root() == Path(os.path.realpath(roots.a))
    assert TR.resolve_task_path("kernel.c") == os.path.realpath(roots.a / "kernel.c")
    TR.clear_request_scope()
    assert TR.get_task_root() == roots.b  # env mode back once the request is gone


@pytest.mark.parametrize("bad", ["relative/dir", "/etc", "/mnt/raid0/llm", "/tmp"])
def test_scope_root_validation_rejects(bad):
    with pytest.raises(ValueError):
        TR.validate_scope_dir(bad)


def test_scope_root_validation_rejects_missing_and_project_ancestor(roots):
    with pytest.raises(ValueError):
        TR.validate_scope_dir(str(roots.base / "nope"))
    project = os.path.realpath(str(TR._project_root()))
    if project.startswith("/mnt/raid0/llm/") and project != "/mnt/raid0/llm":
        with pytest.raises(ValueError):
            TR.validate_scope_dir(project)


@pytest.mark.parametrize("frozen", [
    "/mnt/raid0/llm/llama.cpp",
    "/mnt/raid0/llm/whisper.cpp",
    "/mnt/raid0/llm/qwentts.cpp",
    "/mnt/raid0/llm/llama.cpp/src",
    "/mnt/raid0/llm/kernels",
])
def test_frozen_kernel_trees_denied_as_task_root_and_read_root(frozen):
    """F6: a frozen production kernel tree (or a subdirectory of one) or the kernel store is
    never a scope directory, neither as task_root nor as read_roots."""
    if not os.path.isdir(frozen):
        pytest.skip(f"{frozen} not present on this host")
    with pytest.raises(ValueError):
        TR.validate_scope_dir(frozen)
    with pytest.raises(ValueError):
        TR.validate_scope_dir(frozen, field="read_roots", writable_root=False)


def test_models_store_denied_as_task_root_allowed_as_read_root():
    """F6: models/ is the one asymmetric case — a scoped run may legitimately READ a
    GGUF/tokenizer under models/ (read_roots), but a task_root (write scope) must never
    resolve into the model store."""
    models = "/mnt/raid0/llm/models"
    if not os.path.isdir(models):
        pytest.skip(f"{models} not present on this host")
    with pytest.raises(ValueError):
        TR.validate_scope_dir(models)
    assert TR.validate_scope_dir(models, field="read_roots", writable_root=False) == (
        os.path.realpath(models)
    )


def test_begin_rejects_unknown_edit_mode(roots):
    with pytest.raises(ValueError):
        TR.begin_request_scope(str(roots.a), "patch-queue")


# ── acceptance: writes ──────────────────────────────────────────────────────


def test_direct_write_inside_task_root_lands(repl, roots):
    TR.begin_request_scope(str(roots.a), "direct")
    out = repl._file_write_safe("new_kernel.c", "int x;\n")
    assert out.startswith("Wrote "), out
    assert (roots.a / "new_kernel.c").read_text() == "int x;\n"
    # Absolute path inside the root lands too; overwrite leaves no .bak litter in the worktree.
    out = repl._file_write_safe(str(roots.a / "kernel.c"), "int a2;\n")
    assert out.startswith("Wrote "), out
    assert (roots.a / "kernel.c").read_text() == "int a2;\n"
    assert not list(roots.a.glob("*.bak.*"))


def test_direct_write_outside_task_root_is_refused(repl, roots):
    TR.begin_request_scope(str(roots.a), "direct", [str(roots.ref)])
    for target in (
        str(roots.outside / "evil.txt"),
        str(roots.b / "kernel.c"),          # another lane
        str(roots.ref / "notes.md"),        # a read root is never writable
        "../outside/evil.txt",              # traversal out of the root
        "/tmp/evil.txt",
    ):
        out = repl._file_write_safe(target, "pwned\n")
        assert out.startswith(f"[ERROR: {TR.SCOPE_DENY_PREFIX}"), (target, out)
    assert not (roots.outside / "evil.txt").exists()
    assert (roots.b / "kernel.c").read_text() == "int b;\n"
    assert (roots.ref / "notes.md").read_text() == "reference\n"


def test_symlink_escape_is_refused(repl, roots):
    TR.begin_request_scope(str(roots.a), "direct")
    (roots.a / "link").symlink_to(roots.outside)
    out = repl._file_write_safe("link/secret.txt", "pwned\n")
    assert out.startswith(f"[ERROR: {TR.SCOPE_DENY_PREFIX}"), out
    assert (roots.outside / "secret.txt").read_text() == "SECRET\n"


def test_none_request_cannot_write_at_all(repl, roots):
    TR.begin_request_scope(str(roots.a), "none")
    out = repl._file_write_safe("kernel.c", "overwrite\n")
    assert "edit_mode='none'" in out and out.startswith("[ERROR:")
    assert (roots.a / "kernel.c").read_text() == "int a;\n"
    for name, call in (
        ("log_append", lambda: repl._log_append("x.log", "m")),
        ("prepare_patch", lambda: repl._prepare_patch(["kernel.c"], "d")),
        ("apply_approved_patch", lambda: repl._apply_approved_patch("p.patch")),
        ("run_python_code", lambda: repl._run_python_code("open('x','w')")),
        ("checkpoint_create", lambda: repl._checkpoint_create("c")),
        ("registry_update", lambda: repl._registry_update("a.b", 1)),
    ):
        out = call()
        assert out.startswith(f"[ERROR: {TR.SCOPE_DENY_PREFIX}"), (name, out)
    assert sorted(p.name for p in roots.a.iterdir()) == ["kernel.c"]


def test_shell_writers_refused_in_both_modes(roots):
    from src.repl_environment.external_access import _ExternalAccessMixin

    env = SimpleNamespace(_exploration_calls=0, _exploration_log=MagicMock())
    for mode in ("none", "direct"):
        TR.begin_request_scope(str(roots.a), mode)
        with patch("subprocess.run") as run:
            for cmd in (
                "sed -i s/a/b/ kernel.c",
                "sed -n w/tmp/x kernel.c",
                "awk '{print > \"/tmp/x\"}' kernel.c",
                "find . -delete",
                "find . -exec cat {} ;",
                "sort -o out.txt kernel.c",
                "sort -ro /tmp/x f",
                "sed -nf s.sed f",
                "uniq kernel.c out.txt",
                "python3 -c print(1)",
                f"cat {roots.outside / 'secret.txt'}",
                f"grep -r SECRET {roots.outside}",
                "git diff --output=/tmp/x",
                "git log --output=/tmp/x",
                "git branch foo",
                "git branch -D foo",
            ):
                out = _ExternalAccessMixin._run_shell(env, cmd)
                assert out.startswith(f"[ERROR: {TR.SCOPE_DENY_PREFIX}"), (mode, cmd, out)
            run.assert_not_called()
        TR.clear_request_scope()


def test_shell_reads_inside_scope_run_in_task_root(roots):
    from src.repl_environment.external_access import _ExternalAccessMixin

    env = SimpleNamespace(_exploration_calls=0, _exploration_log=MagicMock())
    TR.begin_request_scope(str(roots.a), "none", [str(roots.ref)])
    assert _ExternalAccessMixin._run_shell(env, "cat kernel.c") == "int a;\n"
    assert _ExternalAccessMixin._run_shell(env, f"cat {roots.ref / 'notes.md'}") == "reference\n"
    assert _ExternalAccessMixin._run_shell(env, "awk '/int/ {print}' kernel.c") == "int a;\n"


def test_shell_dereference_flags_refused(roots):
    """F4: -L/-H/--dereference* (find/du/ls) and -R/--dereference-recursive (grep) can walk a
    symlink outside the scope's read set even though the link itself resolves inside it; -r on
    grep is fine (it does not follow symlinks encountered while recursing)."""
    from src.repl_environment.external_access import _ExternalAccessMixin

    env = SimpleNamespace(_exploration_calls=0, _exploration_log=MagicMock())
    TR.begin_request_scope(str(roots.a), "none")
    for cmd in (
        "find -L .",
        "find -H .",
        "find --dereference .",
        "du -L .",
        "du -sL .",
        "ls -L .",
        "ls -alL .",
        "grep -R SECRET .",
        "grep --dereference-recursive SECRET .",
    ):
        out = _ExternalAccessMixin._run_shell(env, cmd)
        assert out.startswith(f"[ERROR: {TR.SCOPE_DENY_PREFIX}"), (cmd, out)
    # -r (lowercase) stays allowed.
    assert "int a;" in _ExternalAccessMixin._run_shell(env, "grep -r int .")


# ── acceptance: reads confined to task_root + read_roots ────────────────────


def test_reads_confined_to_root_and_read_roots(repl, roots):
    TR.begin_request_scope(str(roots.a), "none", [str(roots.ref)])
    assert "int a;" in repl._peek(100, file_path="kernel.c")
    assert "reference" in repl._peek(100, file_path=str(roots.ref / "notes.md"))
    for path in (str(roots.outside / "secret.txt"), str(roots.b / "kernel.c"), "/etc/hostname"):
        out = repl._peek(100, file_path=path)
        assert TR.SCOPE_DENY_PREFIX in out and "SECRET" not in out, (path, out)
    listing = repl._list_dir(".")
    assert "kernel.c" in listing
    assert TR.SCOPE_DENY_PREFIX in repl._list_dir(str(roots.outside))
    assert TR.SCOPE_DENY_PREFIX in repl._doc_search("anything")


def test_registry_tools_read_only_and_confined(roots):
    from src.builtin_tools import register_builtin_tools
    from src.registry.tool_registry import ToolPermissions, ToolRegistry
    from src.tool_registry import ToolCategory

    reg = ToolRegistry()
    register_builtin_tools(reg)
    reg.set_role_permissions(
        "frontdoor", ToolPermissions(allowed_categories=[ToolCategory.FILE, ToolCategory.DATA])
    )
    TR.begin_request_scope(str(roots.a), "direct")
    inside = reg.invoke("read_file", "frontdoor", path=str(roots.a / "kernel.c"))
    outside = reg.invoke("read_file", "frontdoor", path=str(roots.outside / "secret.txt"))

    def _ok(res):
        return res.ok if hasattr(res, "ok") else res.get("success")

    assert _ok(inside), inside
    assert not _ok(outside) and TR.SCOPE_DENY_PREFIX in str(outside)
    if "write_json" in reg._tools:
        wrote = reg.invoke("write_json", "frontdoor", path=str(roots.a / "x.json"), data={})
        assert not _ok(wrote) and TR.SCOPE_DENY_PREFIX in str(wrote)
        assert not (roots.a / "x.json").exists()


# ── acceptance: two concurrent requests do not cross ────────────────────────


@pytest.mark.asyncio
async def test_concurrent_requests_with_different_roots_do_not_cross(roots):
    """Two asyncio tasks (== two concurrent /chat requests in one uvicorn worker), each with
    its own scope, interleave their tool calls in worker threads. A barrier forces both
    scopes to be live at the same time before either writes."""
    from src.repl_environment.environment import REPLEnvironment

    barrier = threading.Barrier(2, timeout=10)

    async def one_request(root: Path, tag: str) -> dict:
        TR.begin_request_scope(str(root), "direct")
        repl = REPLEnvironment(context=f"req {tag}")

        def tools() -> dict:
            barrier.wait()  # both requests' scopes are now installed
            seen_root = str(TR.get_task_root())
            wrote = repl._file_write_safe("out.txt", f"from {tag}\n")
            barrier.wait()
            read = repl._peek(100, file_path="out.txt")
            return {"root": seen_root, "wrote": wrote, "read": read}

        try:
            return await asyncio.to_thread(tools)
        finally:
            TR.clear_request_scope()

    res_a, res_b = await asyncio.gather(
        asyncio.create_task(one_request(roots.a, "A")),
        asyncio.create_task(one_request(roots.b, "B")),
    )
    assert res_a["root"] == os.path.realpath(roots.a)
    assert res_b["root"] == os.path.realpath(roots.b)
    assert (roots.a / "out.txt").read_text() == "from A\n"
    assert (roots.b / "out.txt").read_text() == "from B\n"
    assert "from A" in res_a["read"] and "from B" in res_b["read"]
    assert TR.request_scope() is None  # the parent context never saw either scope


def test_parallel_dispatch_workers_see_their_scope(roots):
    from src.repl_environment.parallel_dispatch import _ParallelCall, execute_parallel_calls

    TR.begin_request_scope(str(roots.a), "none")
    calls = [
        _ParallelCall(func_name="probe", args=(), kwargs={}, target_var=f"v{i}", index=i)
        for i in range(3)
    ]
    out = execute_parallel_calls(calls, {"probe": lambda: str(TR.get_task_root())}, state_lock=None)
    assert set(out.values()) == {os.path.realpath(roots.a)}


# ── API model + route ───────────────────────────────────────────────────────


def test_chat_request_contract(roots):
    from pydantic import ValidationError

    from src.api.models import ChatRequest

    req = ChatRequest(prompt="q")
    assert (req.task_root, req.edit_mode, req.read_roots, req.quiescent_after) == (
        None, "none", None, False)
    ok = ChatRequest(prompt="q", task_root=str(roots.a), edit_mode="direct",
                     read_roots=[str(roots.ref)], max_turns=80)
    assert ok.task_root == os.path.realpath(roots.a)
    assert ok.read_roots == [os.path.realpath(roots.ref)]
    for kwargs in (
        {"edit_mode": "direct"},                                  # direct needs task_root
        {"read_roots": [str(roots.ref)]},                         # read_roots needs task_root
        {"max_turns": 51},                                        # >50 needs task_root
        {"task_root": str(roots.a), "max_turns": 101},            # scoped ceiling
        {"task_root": "/etc"},                                    # outside allowed prefixes
        {"task_root": str(roots.base / "missing")},
        {"task_root": str(roots.a), "edit_mode": "yolo"},
    ):
        with pytest.raises(ValidationError):
            ChatRequest(prompt="q", **kwargs)


def test_chat_response_without_scope_is_unchanged():
    from src.api.models import ChatResponse

    dumped = ChatResponse(answer="a", turns=1, elapsed_seconds=0.1, mock_mode=True).model_dump()
    assert "task_scope" not in dumped and "quiescence" not in dumped


class _FakeHttpRequest:
    async def is_disconnected(self) -> bool:
        return False


@pytest.mark.asyncio
async def test_chat_route_installs_echoes_and_clears_scope(roots):
    from src.api.models import ChatRequest, ChatResponse
    from src.api.routes.chat import chat
    from src.repl_environment.environment import REPLEnvironment

    seen: dict = {}

    async def fake_handle_chat(*_args, **_kwargs):
        repl = REPLEnvironment(context="route")
        seen["root"] = str(TR.get_task_root())
        seen["write"] = await asyncio.to_thread(repl._file_write_safe, "route.txt", "ok\n")
        return ChatResponse(answer="ok", turns=1, elapsed_seconds=0.01, mock_mode=True)

    request = ChatRequest(prompt="t", task_root=str(roots.a), edit_mode="direct")
    with patch("src.api.routes.chat._handle_chat", new=fake_handle_chat):
        response = await chat(request, _FakeHttpRequest(), MagicMock())
    assert TR.request_scope() is None
    assert seen["root"] == os.path.realpath(roots.a)
    assert seen["write"].startswith("Wrote ")
    assert (roots.a / "route.txt").read_text() == "ok\n"
    assert response.task_scope == {"task_root": os.path.realpath(roots.a),
                                   "edit_mode": "direct", "read_roots": []}


# ── R3 + side paths ─────────────────────────────────────────────────────────


def test_scoped_request_may_extend_timeout(roots):
    from src.api.models import ChatRequest
    from src.api.routes.chat_pipeline.routing_decision import resolve_timeout

    plain = ChatRequest(prompt="q", timeout_s=3000)
    scoped = ChatRequest(prompt="q", timeout_s=3000, task_root=str(roots.a))
    assert resolve_timeout(plain, ["frontdoor"]) <= 3000
    assert resolve_timeout(scoped, ["frontdoor"]) == 3000


def test_solution_file_never_lands_in_scoped_worktree(roots):
    from src.graph.file_artifacts import _solution_file_path

    state = SimpleNamespace(task_id="t-1")
    TR.begin_request_scope(str(roots.a), "direct")
    assert not _solution_file_path(state).startswith(os.path.realpath(roots.a))
