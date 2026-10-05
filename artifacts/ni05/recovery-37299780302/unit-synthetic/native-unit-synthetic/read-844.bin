"""Phase 1 exit-gate tests: model-facing surfaces honor the task-root when
ORCHESTRATOR_EDIT_ROOT is active, and are byte-for-byte unchanged when unset.

Covers the Phase-0 audit surfaces that are unit-testable without inference:
  #1/#2 _validate_file_path (relative resolves under scratch + task-root allowed)
  #5    run_shell cwd
  #7    code_search (index-free scratch search)
  #8    _batch_edit_repo_root
(#10 DCP file_reader is covered in test_dcp4_wiring.py; full write/read tool round-trips
land in the Phase 3 driver dry-run.)
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.repl_environment.environment import REPLEnvironment

_REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    monkeypatch.delenv("ORCHESTRATOR_EDIT_ROOT", raising=False)


def _env():
    return REPLEnvironment(context="test", role="frontdoor")


# ─── #1/#2 _validate_file_path ────────────────────────────────────────────────────


def test_validate_relative_path_resolves_under_scratch(monkeypatch, tmp_path):
    monkeypatch.setenv("ORCHESTRATOR_EDIT_ROOT", str(tmp_path))
    env = _env()
    ok, err = env._validate_file_path("cart.py")  # relative → under scratch task-root
    assert ok, err


def test_validate_absolute_scratch_path_ok(monkeypatch, tmp_path):
    monkeypatch.setenv("ORCHESTRATOR_EDIT_ROOT", str(tmp_path))
    env = _env()
    ok, err = env._validate_file_path(str(tmp_path / "pkg" / "mod.py"))
    assert ok, err


def test_validate_default_off_unchanged(tmp_path):
    # env unset: a /tmp path is allowed (ALLOWED_FILE_PATHS includes /tmp/), an /etc path is not
    env = _env()
    ok_tmp, _ = env._validate_file_path(str(tmp_path / "x.py"))
    ok_etc, _ = env._validate_file_path("/etc/hostname")
    assert ok_tmp is True
    assert ok_etc is False  # parity: outside allowed prefixes


# ─── #1 task-root ISOLATION leak regression (operator-found 2026-05-27) ────────────
# Prior bug: _validate_file_path APPENDED the scratch root to the global allowed set
# (llm_root + /tmp). Since the scratch lives under /tmp, the global /tmp prefix made every
# outside path validate (/tmp/x, ../x, the orchestrator tree). When a task-root is active the
# allowed set must be the scratch root ONLY.


def test_validate_rejects_outside_paths_when_task_root_active(monkeypatch, tmp_path):
    monkeypatch.setenv("ORCHESTRATOR_EDIT_ROOT", str(tmp_path))
    env = _env()
    # sibling of the scratch root (a /tmp path NOT under scratch), an absolute /tmp escape,
    # the orchestrator tree, and a relative ../ escape — all must be rejected.
    assert env._validate_file_path(str(tmp_path.parent / "outside_abs.py"))[0] is False
    assert env._validate_file_path("/tmp/outside_abs.py")[0] is False
    assert env._validate_file_path(str(_REPO_ROOT / "src/x.py"))[0] is False
    assert env._validate_file_path("../outside.py")[0] is False  # relative escape collapses out


def test_file_write_safe_lands_in_scratch_not_project(monkeypatch, tmp_path):
    # Operator-required regression: with the task-root active, _file_write_safe("cart.py", …)
    # writes <scratch>/cart.py, NOT cwd/project-root (validate-resolved + write-redirected).
    monkeypatch.setenv("ORCHESTRATOR_EDIT_ROOT", str(tmp_path))
    env = _env()
    cwd_leak = Path.cwd() / "cart.py"
    pre_existed = cwd_leak.exists()
    result = env._file_write_safe("cart.py", "X = 1\n", backup=False)
    assert "Wrote" in result, result
    assert (tmp_path / "cart.py").read_text() == "X = 1\n"
    if not pre_existed:
        assert not cwd_leak.exists(), "write leaked to cwd/project-root instead of scratch"


def test_file_write_safe_rejects_escape_when_task_root_active(monkeypatch, tmp_path):
    monkeypatch.setenv("ORCHESTRATOR_EDIT_ROOT", str(tmp_path))
    env = _env()
    result = env._file_write_safe("/tmp/escape_abs_should_reject.py", "X = 1\n", backup=False)
    assert result.startswith("[ERROR"), result
    assert not Path("/tmp/escape_abs_should_reject.py").exists()


# ─── #8 _batch_edit_repo_root ─────────────────────────────────────────────────────


def test_batch_edit_repo_root_follows_task_root(monkeypatch, tmp_path):
    from src.graph.helpers import _batch_edit_repo_root

    monkeypatch.setenv("ORCHESTRATOR_EDIT_ROOT", str(tmp_path))
    assert _batch_edit_repo_root() == tmp_path


def test_batch_edit_repo_root_default_is_project_root(monkeypatch):
    from src.graph.helpers import _batch_edit_repo_root
    from src.repl_environment.task_root import _project_root

    # unset → project_root (parity with the prior _get_project_root())
    assert _batch_edit_repo_root() == _project_root()


# ─── #7 code_search (index-free scratch search) ───────────────────────────────────


def test_code_search_returns_scratch_files(monkeypatch, tmp_path):
    (tmp_path / "cart.py").write_text("def total():\n    return sum(items)\n")
    (tmp_path / "checkout.py").write_text("from cart import total\n")
    (tmp_path / "unrelated.py").write_text("X = 1\n")
    monkeypatch.setenv("ORCHESTRATOR_EDIT_ROOT", str(tmp_path))
    env = _env()
    out = env._code_search("total cart", limit=5)
    hits = json.loads(out)
    paths = {h["path"] for h in hits}
    assert "cart.py" in paths  # matched by name + body
    assert "checkout.py" in paths  # matched by body ("cart", "total")
    # each hit is ColGREP-JSON-shaped (path/score/start_line/end_line)
    assert all("path" in h and "score" in h and "start_line" in h and "end_line" in h for h in hits)
    by_path = {h["path"]: h for h in hits}
    assert by_path["cart.py"]["start_line"] == 1
    assert by_path["cart.py"]["end_line"] == 2


def test_code_search_pads_large_scratch_file_match(monkeypatch, tmp_path):
    lines = [f"value_{i} = 0" for i in range(1, 101)]
    lines[49] = "target_marker = compute_total(items)"
    (tmp_path / "large.py").write_text("\n".join(lines) + "\n")
    monkeypatch.setenv("ORCHESTRATOR_EDIT_ROOT", str(tmp_path))
    env = _env()
    hits = json.loads(env._code_search("target_marker compute_total", limit=5))
    hit = next(h for h in hits if h["path"] == "large.py")
    assert hit["start_line"] == 30
    assert hit["end_line"] == 70


def test_code_search_discovers_cpp_and_systems_language_files(monkeypatch, tmp_path):
    # DCP-10a: the task-root whitelist must cover C/C++/Go/Rust/Java, not only Python/web files.
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "ring_buffer.cpp").write_text("void ring_buffer_push(int v) {}\n")
    (tmp_path / "src" / "ring_buffer.h").write_text("void ring_buffer_push(int v);\n")
    for name in ("ring.c", "ring.cc", "ring.cxx", "ring.hpp", "ring.go", "ring.rs", "Ring.java"):
        (tmp_path / "src" / name).write_text("ring_buffer_push\n")
    monkeypatch.setenv("ORCHESTRATOR_EDIT_ROOT", str(tmp_path))
    env = _env()
    paths = {h["path"] for h in json.loads(env._code_search("ring_buffer_push", limit=20))}
    assert "src/ring_buffer.cpp" in paths
    assert "src/ring_buffer.h" in paths
    for name in ("ring.c", "ring.cc", "ring.cxx", "ring.hpp", "ring.go", "ring.rs", "Ring.java"):
        assert f"src/{name}" in paths


def test_code_search_default_off_uses_indexed_engine(monkeypatch):
    # env unset → must NOT take the scratch path; falls through to ColGREP/NextPLAID.
    # Patch the indexed engine to confirm it's the one invoked (parity).
    from unittest.mock import patch

    env = _env()
    with (
        patch.object(env, "_task_root_code_search") as scratch,
        patch.object(env, "_colgrep_search", return_value="[]"),
        patch.object(env, "_nextplaid_search", return_value="[]"),
    ):
        env._code_search("anything", limit=5)
    scratch.assert_not_called()  # scratch path never taken when env unset


# ─── #5 run_shell cwd ─────────────────────────────────────────────────────────────


def test_run_shell_cwd_is_scratch(monkeypatch, tmp_path):
    import os

    monkeypatch.setenv("ORCHESTRATOR_EDIT_ROOT", str(tmp_path))
    env = _env()
    out = env._run_shell("pwd")
    # pwd prints the cwd; should be the scratch task-root (realpath to handle /tmp symlinks)
    assert os.path.realpath(str(tmp_path)) in out or str(tmp_path) in out
