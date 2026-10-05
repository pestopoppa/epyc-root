"""DCP-4 (J7) wiring tests: render_bundle (context_discovery) + the flag-gated
advisory seed helper (_maybe_dcp_seed_context in chat_delegation).

The DCP-1/2/3 core (assemble/discover/pack) is tested in test_context_*.py; these
cover the new render step and the delegation attach point:
  * render_bundle materializes included entries per inclusion mode (full/slices/codemap);
  * _maybe_dcp_seed_context is a no-op when the flag is off (zero behavior change) and
    augments the base context with relevant code when on; failures fall back silently.
"""

from __future__ import annotations

from types import SimpleNamespace


from src.context_discovery import assemble_delegation_bundle, render_bundle
from src.api.routes import chat_delegation as CD


# ─── render_bundle ───────────────────────────────────────────────────────────────

def _files() -> dict[str, str]:
    return {
        "mod/foo.py": "def foo():\n    return 1\n\n\ndef bar(x):\n    return x + 1\n",
        "mod/data.py": "VALUE = 42\n",
    }


def test_render_bundle_full_mode():
    files = _files()
    def reader(p: str) -> str | None:
        return files.get(p)

    def code_search(q: str, limit: int = 20) -> list[dict]:
        return [
            {"path": "mod/foo.py", "score": 0.9},
            {"path": "mod/data.py", "score": 0.5},
        ]

    # no line_ranges in hits → FULL desired; big budget → all FULL
    bundle = assemble_delegation_bundle(
        "foo",
        budget=100_000,
        code_search_fn=code_search,
        file_reader_fn=reader,
    )
    text = render_bundle(bundle, file_reader_fn=reader)
    assert "mod/foo.py" in text
    assert "def foo():" in text          # full body materialized
    assert "VALUE = 42" in text


def test_render_bundle_skips_unreadable_entries():
    files = {"present.py": "X = 1\n"}
    def reader(p: str) -> str | None:
        return files.get(p)

    def code_search(q: str, limit: int = 20) -> list[dict]:
        return [
            {"path": "present.py", "score": 0.9},
            {"path": "gone.py", "score": 0.8},
        ]

    bundle = assemble_delegation_bundle(
        "x",
        budget=100_000,
        code_search_fn=code_search,
        file_reader_fn=reader,
    )
    text = render_bundle(bundle, file_reader_fn=reader)
    assert "present.py" in text
    assert "gone.py" not in text  # unreadable → skipped, no crash


def test_render_bundle_empty_when_no_hits():
    bundle = assemble_delegation_bundle(
        "q", budget=1000, code_search_fn=lambda q, limit=20: [], file_reader_fn=lambda p: None
    )
    assert render_bundle(bundle, file_reader_fn=lambda p: None) == ""


# ─── _maybe_dcp_seed_context (flag-gated attach point) ───────────────────────────

def test_seed_flag_off_returns_base_unchanged(monkeypatch):
    monkeypatch.setattr("src.features.features", lambda: SimpleNamespace(dcp_pre_assembly=False))
    # code_search_fn would raise if called — proves the flag short-circuits first
    def _boom(*a, **k):
        raise AssertionError("code_search must not run when flag is off")
    out = CD._maybe_dcp_seed_context("anything", code_search_fn=_boom, base_ctx="BASE")
    assert out == "BASE"


def test_seed_flag_on_augments_context(monkeypatch, tmp_path):
    monkeypatch.setattr("src.features.features", lambda: SimpleNamespace(dcp_pre_assembly=True))
    # DCP file_reader now sources get_task_root() (Phase 1 #10) — drive it via the real
    # ORCHESTRATOR_EDIT_ROOT task-root mechanism instead of the old _get_project_root.
    monkeypatch.setenv("ORCHESTRATOR_EDIT_ROOT", str(tmp_path))
    (tmp_path / "target.py").write_text("def target():\n    return 99\n")
    out = CD._maybe_dcp_seed_context(
        "target",
        code_search_fn=lambda q, limit=20: [{"path": "target.py", "score": 0.95}],
        base_ctx="BASE",
    )
    assert out.startswith("BASE")
    assert "DCP pre-assembled context" in out
    assert "def target():" in out


def test_seed_flag_on_failure_falls_back(monkeypatch):
    monkeypatch.setattr("src.features.features", lambda: SimpleNamespace(dcp_pre_assembly=True))
    def _boom(*a, **k):
        raise RuntimeError("colgrep down")
    # assembly raises → advisory fallback returns base_ctx unchanged (never blocks delegation)
    out = CD._maybe_dcp_seed_context("q", code_search_fn=_boom, base_ctx="BASE")
    assert out == "BASE"


def test_seed_empty_base_returns_only_bundle(monkeypatch, tmp_path):
    monkeypatch.setattr("src.features.features", lambda: SimpleNamespace(dcp_pre_assembly=True))
    monkeypatch.setenv("ORCHESTRATOR_EDIT_ROOT", str(tmp_path))  # task-root (Phase 1 #10)
    (tmp_path / "only.py").write_text("ONLY = 1\n")
    out = CD._maybe_dcp_seed_context(
        "only",
        code_search_fn=lambda q, limit=20: [{"path": "only.py", "score": 0.9}],
        base_ctx="",
    )
    assert "ONLY = 1" in out
    assert not out.startswith("[DCP")  # no leading separator when base is empty
