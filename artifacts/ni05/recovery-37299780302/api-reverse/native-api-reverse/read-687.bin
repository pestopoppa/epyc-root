"""XREPO-1: research benchmark modules must load BY PATH, not by import order.

The audited defect (eval-tower-architecture-audit-2026-07-20, XREPO-1, HIGH ✓verified):
same-named modules exist in the orchestrator and research repos, `sys.path` ordering
decided which one a bare `import` bound, first-import-wins, and *the stale copy
demonstrably built production data*. The fix in `eval_tower._load_research_benchmark_module`
is path-based loading under a private, content-keyed `sys.modules` name.

That fix had no test. These pin the three properties that make it work, so a future
refactor back to a bare import fails here instead of silently rebinding a scorer:

  1. a same-named module already in `sys.modules` does NOT capture the load;
  2. the module is registered under a PRIVATE name, leaving the bare name untouched;
  3. the cache is keyed on mtime, so an edited research module is re-loaded rather
     than served stale — the audit's DRIFT-1 sibling.

Additive: test-only, no behaviour change (A23, 2026-08-12, `mainC`).
"""
from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import pytest

_ORCH = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location(
    "_et_for_identity", _ORCH / "scripts" / "autopilot" / "eval_tower.py")


@pytest.fixture(scope="module")
def et():
    """eval_tower is heavy; load it once, by path, like the code under test does."""
    if _SPEC is None or _SPEC.loader is None:
        pytest.skip("eval_tower.py not loadable")
    sys.path.insert(0, str(_ORCH))
    sys.path.insert(0, str(_ORCH / "scripts" / "benchmark"))
    mod = importlib.util.module_from_spec(_SPEC)
    sys.modules[_SPEC.name] = mod
    try:
        _SPEC.loader.exec_module(mod)
    except Exception as exc:                                  # pragma: no cover
        pytest.skip(f"eval_tower import side effects unavailable here: {exc}")
    return mod


@pytest.fixture()
def fake_research(tmp_path, monkeypatch, et):
    """A research tree whose module announces which copy it is."""
    bench = tmp_path / "scripts" / "benchmark"
    bench.mkdir(parents=True)
    (bench / "answer_scoring.py").write_text("WHICH_COPY = 'research'\n", encoding="utf-8")
    monkeypatch.setenv("EPYC_RESEARCH_ROOT", str(tmp_path))
    et._RESEARCH_BENCHMARK_MODULE_CACHE.clear()
    return bench / "answer_scoring.py"


def test_a_same_named_module_already_imported_does_not_capture_the_load(
        fake_research, monkeypatch, et) -> None:
    """The exact XREPO-1 failure: first-import-wins binding the WRONG repo's copy."""
    decoy = types.ModuleType("answer_scoring")
    decoy.WHICH_COPY = "orchestrator-decoy"
    monkeypatch.setitem(sys.modules, "answer_scoring", decoy)

    loaded = et._load_research_benchmark_module("answer_scoring")

    assert loaded.WHICH_COPY == "research", (
        "loaded the decoy already in sys.modules — path-based loading has regressed "
        "to bare-import semantics, which is how a stale copy built production data")
    assert sys.modules["answer_scoring"] is decoy, "must not clobber the bare name"


def test_the_module_is_registered_under_a_private_content_keyed_name(
        fake_research, et) -> None:
    et._load_research_benchmark_module("answer_scoring")
    private = [n for n in sys.modules if n.startswith("_epyc_research_answer_scoring_")]
    assert private, "expected a private, content-keyed sys.modules entry"


def test_an_edited_research_module_is_reloaded_not_served_stale(
        fake_research, et) -> None:
    """Cache is keyed on mtime_ns, so an edit must invalidate it (DRIFT-1 sibling)."""
    first = et._load_research_benchmark_module("answer_scoring")
    assert first.WHICH_COPY == "research"

    st = fake_research.stat()
    fake_research.write_text("WHICH_COPY = 'research-edited'\n", encoding="utf-8")
    import os
    os.utime(fake_research, ns=(st.st_atime_ns, st.st_mtime_ns + 1_000_000_000))

    assert et._load_research_benchmark_module("answer_scoring").WHICH_COPY == "research-edited"


def test_a_missing_research_module_raises_rather_than_falling_back(
        tmp_path, monkeypatch, et) -> None:
    """Fail-closed. A silent fallback here is what makes the wrong copy invisible."""
    monkeypatch.setenv("EPYC_RESEARCH_ROOT", str(tmp_path))
    et._RESEARCH_BENCHMARK_MODULE_CACHE.clear()
    with pytest.raises(FileNotFoundError):
        et._load_research_benchmark_module("answer_scoring")


def test_research_root_honours_the_env_override(tmp_path, monkeypatch, et) -> None:
    """PATH-1: the hardcoded path must stay overridable, as question_pool's is."""
    monkeypatch.setenv("EPYC_RESEARCH_ROOT", str(tmp_path))
    assert et._research_root() == tmp_path
    monkeypatch.delenv("EPYC_RESEARCH_ROOT", raising=False)
    assert et._research_root() == Path("/mnt/raid0/llm/epyc-inference-research")
