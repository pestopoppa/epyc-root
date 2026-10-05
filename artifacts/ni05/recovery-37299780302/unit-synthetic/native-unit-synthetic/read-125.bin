"""BEP/DCP no-inference real-path CANARY (operator-required gate, 2026-05-27).

Run this BEFORE any live BEP-2/DCP-6 A/B. It exercises the REAL request-gating + REPL write
path with NO inference, asserting the exact invariants whose violation caused the expensive
live-run failures:

  * mock_mode=False + real_mode=True is NOT routed to the mock branch
        (caught: the all-`[MOCK] Processed prompt` run — the driver omitted the real-mode flags);
  * force_mode="repl" is an accepted forced mode
        (caught: the turns=1 'direct' run — the coder never entered the REPL edit loop);
  * a model file write via the REPL lands inside the scratch task-root, NOT cwd/project-root;
  * a model write to a path OUTSIDE the scratch root is REJECTED (isolation — the leak the
        operator reproduced with `/tmp/outside_abs.py` / `../outside.py`);
  * `open()` is forbidden by the REPL sandbox (which is WHY the interleaved-edit rider must
        instruct `file_write_safe(...)`, not `open(...)` — the original rider's root-cause bug).

No live stack / no inference: `_route_request` is the real routing gate and
`REPLEnvironment.execute()` is the real sandbox. Deterministic + CI-safe.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from src.api.models import ChatRequest
from src.api.routes.chat_pipeline.routing import _route_request
from src.repl_environment.environment import REPLEnvironment

# The exact forced-mode set gated in src/api/routes/chat.py (_handle_chat).
_FORCED_MODES = ("direct", "react", "repl", "delegated")


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    monkeypatch.delenv("ORCHESTRATOR_EDIT_ROOT", raising=False)


def _repl() -> REPLEnvironment:
    return REPLEnvironment(context="canary", role="coder_escalation")


# ── request gating: mock_mode / real_mode (caught the all-[MOCK] run) ─────────────

def test_real_mode_request_not_routed_to_mock(mock_app_state):
    r = _route_request(ChatRequest(prompt="hi", mock_mode=False, real_mode=True), mock_app_state)
    assert r.use_mock is False, "real-mode request must NOT hit the mock branch"


def test_default_request_is_mock(mock_app_state):
    # Safety default: a request that does not opt into real mode IS mock — this is exactly why
    # the driver must send mock_mode=False/real_mode=True explicitly.
    r = _route_request(ChatRequest(prompt="hi"), mock_app_state)
    assert r.use_mock is True


# ── force_mode contract (caught the turns=1 'direct' run) ─────────────────────────

def test_force_mode_repl_is_accepted():
    req = ChatRequest(prompt="x", force_mode="repl")
    assert req.force_mode == "repl"
    assert req.force_mode in _FORCED_MODES  # else chat.py drops it → falls back to _select_mode


# ── REPL real write path → scratch task-root (caught the no-file-written run) ──────

def test_repl_write_lands_in_scratch(monkeypatch, tmp_path):
    monkeypatch.setenv("ORCHESTRATOR_EDIT_ROOT", str(tmp_path))
    _repl().execute('file_write_safe("cart.py", "X = 1\\n")')
    assert (tmp_path / "cart.py").read_text() == "X = 1\n"


def test_repl_write_outside_scratch_rejected(monkeypatch, tmp_path):
    monkeypatch.setenv("ORCHESTRATOR_EDIT_ROOT", str(tmp_path))
    escape = Path("/tmp/bep_canary_escape_should_reject.py")
    escape.unlink(missing_ok=True)
    _repl().execute(f'file_write_safe({str(escape)!r}, "X = 1\\n")')
    assert not escape.exists(), "model write escaped the scratch task-root (isolation leak)"


def test_repl_open_is_forbidden(monkeypatch, tmp_path):
    # The REPL security layer forbids open() — this is why the interleaved rider must use
    # file_write_safe(...). If open() ever became allowed, the rider's mechanism would be wrong.
    monkeypatch.setenv("ORCHESTRATOR_EDIT_ROOT", str(tmp_path))
    _repl().execute('open("cart_via_open.py", "w").write("X")')
    assert not (tmp_path / "cart_via_open.py").exists()


# ── REPL real READ path → must resolve to the scratch task-root (2026-05-27) ──────
# Root cause of the BEP-2 multi-file read-loop: reads (peek/grep/file_info/peek_grep) opened
# the RAW relative path (orchestrator cwd), while writes resolve to the task-root. So a model
# that read an existing task file got "[ERROR: File not found]", had nothing to act on, and
# re-emitted the identical peek every turn until timeout. Reads must mirror writes.

def test_repl_peek_reads_task_root_file(monkeypatch, tmp_path):
    monkeypatch.setenv("ORCHESTRATOR_EDIT_ROOT", str(tmp_path))
    (tmp_path / "calc.py").write_text("def double(x):\n    return x * 2\n")
    out = _repl()._peek(file_path="calc.py")
    assert "def double" in out, f"peek must read the task-root file; got: {out!r}"
    assert "File not found" not in out


def test_repl_grep_reads_task_root_file(monkeypatch, tmp_path):
    monkeypatch.setenv("ORCHESTRATOR_EDIT_ROOT", str(tmp_path))
    (tmp_path / "calc.py").write_text("def double(x):\n    return x * 2\n")
    hits = _repl()._grep("double", file_path="calc.py")
    assert any("double" in h for h in hits), f"grep must read the task-root file; got: {hits!r}"


def test_repl_peek_absolute_path_no_taskroot(monkeypatch, tmp_path):
    # Prod no-op invariant: with no task-root active, resolve_task_path == realpath, so an
    # absolute path still reads exactly as before (the fix must not change prod read behavior).
    monkeypatch.delenv("ORCHESTRATOR_EDIT_ROOT", raising=False)
    f = tmp_path / "abs_mod.py"
    f.write_text("ABSOLUTE_OK = 1\n")
    out = _repl()._peek(file_path=str(f))
    assert "ABSOLUTE_OK" in out, f"absolute-path read must still work; got: {out!r}"


# ── solution_file path must anchor in the task-root (2026-05-27) ───────────────────
# The prompt shows the model `solution_file=<path>`. The old hardcoded /mnt/raid0/llm/tmp path
# mis-anchored the model: after reading, it wrote `/mnt/raid0/llm/tmp/calc.py` (outside the
# task-root → rejected → a 2nd loop). The shown path must be inside the task-root.

def test_solution_file_anchored_in_task_root(monkeypatch, tmp_path):
    from types import SimpleNamespace
    from src.graph.file_artifacts import _solution_file_path
    monkeypatch.setenv("ORCHESTRATOR_EDIT_ROOT", str(tmp_path))
    p = _solution_file_path(SimpleNamespace(task_id="t2_add_and_use"))
    assert p.startswith(str(tmp_path)), f"solution file must be inside the task-root; got {p!r}"


def test_solution_file_default_path_in_prod(monkeypatch):
    from types import SimpleNamespace
    from src.graph.file_artifacts import _solution_file_path
    monkeypatch.delenv("ORCHESTRATOR_EDIT_ROOT", raising=False)
    p = _solution_file_path(SimpleNamespace(task_id="prod_task"))
    assert p == "/mnt/raid0/llm/tmp/prod_task_solution.py"  # prod behavior unchanged
