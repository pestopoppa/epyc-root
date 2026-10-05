"""Regression guards for the ONNX retrieval stack's *declared* runtime dependencies.

Origin (2026-08-12, backlog B13). `onnxruntime` is a direct runtime import in three
modules — `src/retrieval/colbert_encoder.py` (first-stage KB-RAG MaxSim),
`src/retrieval/cross_encoder.py` (K9 cross-encoder rerank) and
`src/tools/web/colbert_reranker.py` (web-research snippet rerank) — but it was declared
*nowhere* in `[project] dependencies`. It appeared only inside the optional
`colbert-export` extra, whose own comment asserted it was "not needed at runtime". The
orchestrator `.venv` consequently had no `onnxruntime` at all, and every loader caught the
ImportError, emitted a `logger.warning`, and returned False — so callers degraded to
un-reranked order with no health probe, preflight or metric asserting otherwise.
`src/retrieval/federation.py` grew an entire three-tier site-packages search
(`ensure_encoder_importable`) to work around the absence rather than fix the manifest.
Same defect family as the `matplotlib` entry documented in `pyproject.toml`.

Production-caller status, so these tests do not overstate what is live:
  * `src/retrieval/kb_rag.py:630` calls `cross_encoder.rerank(...)`, but only when the
    `rerank` flag is true; its default is `_env_flag("KB_RAG_RERANK")`, i.e. **False**, and
    `KB_RAG_RERANK` is set nowhere in either repo. The K7 evaluation
    (`handoffs/active/internal-kb-rag.md` K9) deliberately left it off as "not default-safe".
  * `src/tools/web/research.py:928` calls `colbert_reranker.rerank_snippets(...)` behind the
    `web_research_rerank` feature flag, which `src/features.py:191` defaults to False and an
    autopilot seed strategy explicitly pins off.
  * `src/retrieval/colbert_encoder.py` is the exception: it is on the *unconditional*
    first-stage KB-RAG query path (`kb_rag.py:259,266,408,564`) and needs `onnxruntime`
    whenever KB-RAG is used at all.
So the cross-encoder rerank stage is off by CONFIG, not merely by the missing dependency —
but the dependency is genuinely missing, and the first-stage encoder needs it regardless.
"""

from __future__ import annotations

import logging
import re
import sys
import tomllib
from pathlib import Path

import pytest

# Repo root: tests/unit/ -> tests/ -> <repo>
_REPO_ROOT = Path(__file__).resolve().parents[2]
_PYPROJECT = _REPO_ROOT / "pyproject.toml"

# A dependency entry may carry extras, a version specifier, an environment marker or a
# direct URL: "optimum[onnxruntime]>=1.21.0", "pkg @ git+https://...", 'x; python_version<"3.12"'.
_REQ_NAME_RE = re.compile(r"^\s*([A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?)")


def _canonical(name: str) -> str:
    """PEP 503 canonical form so `onnx_runtime` / `ONNXRuntime` cannot slip past."""
    return re.sub(r"[-_.]+", "-", name).lower()


def _declared_runtime_dependencies(pyproject_path: Path) -> set[str]:
    """Canonical names in `[project] dependencies` — parsed, never string-matched.

    Fails loudly rather than vacuously: a missing file, a missing/empty `dependencies`
    list, or an unparseable entry is an error, not an empty set that trivially "passes"
    a negative assertion.
    """
    assert pyproject_path.is_file(), f"manifest not found: {pyproject_path}"
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    deps = data.get("project", {}).get("dependencies")
    assert isinstance(deps, list) and deps, (
        f"[project] dependencies missing or empty in {pyproject_path} — "
        "the manifest this test inspects is gone, not satisfied"
    )
    names: set[str] = set()
    for entry in deps:
        m = _REQ_NAME_RE.match(str(entry))
        assert m, f"unparseable dependency entry: {entry!r}"
        names.add(_canonical(m.group(1)))
    return names


def _runtime_dependencies() -> set[str]:
    names = _declared_runtime_dependencies(_PYPROJECT)
    # Anchor: if the parse silently returned the wrong table, this canary is missing and
    # the test fails here instead of reporting a false negative on onnxruntime.
    assert "fastapi" in names, (
        "parsed dependency set does not contain the known-good anchor 'fastapi' — "
        f"parser is reading the wrong table; got: {sorted(names)}"
    )
    return names


@pytest.mark.parametrize(
    "package, importer",
    [
        ("onnxruntime", "src/retrieval/colbert_encoder.py, cross_encoder.py, colbert_reranker.py"),
        ("tokenizers", "src/retrieval/cross_encoder.py, colbert_encoder.py, colbert_reranker.py"),
    ],
)
def test_onnx_retrieval_deps_are_declared_at_runtime(package: str, importer: str) -> None:
    """The guard that would have caught B13: a direct runtime import must be declared.

    Declaring it only in an optional extra (`colbert-export`) does NOT count — a venv built
    from `[project] dependencies` alone will not have it, which is exactly what happened.
    """
    names = _runtime_dependencies()
    assert _canonical(package) in names, (
        f"{package!r} is imported at runtime by {importer} but is not declared in "
        f"[project] dependencies of {_PYPROJECT}. A venv built from this manifest will "
        f"silently degrade: the loader catches the ImportError, logs a warning and "
        f"returns False, and callers fall back to un-reranked results."
    )


def test_onnxruntime_not_only_in_optional_extra() -> None:
    """Regression on the specific historical mistake: runtime dep parked in an extra."""
    data = tomllib.loads(_PYPROJECT.read_text(encoding="utf-8"))
    runtime = _runtime_dependencies()
    extras = data.get("project", {}).get("optional-dependencies", {})
    assert isinstance(extras, dict) and extras, "optional-dependencies table vanished"
    # `colbert-export` may legitimately still pull optimum[onnxruntime] for the export
    # path; what must not happen is that being the ONLY place onnxruntime is reachable.
    assert "onnxruntime" in runtime, (
        "onnxruntime is reachable only via an optional extra — the runtime install "
        "will not have it."
    )


def test_dependency_parser_detects_absence() -> None:
    """Positive control: the detector must FAIL a manifest that omits the dep.

    Without this, `test_onnx_retrieval_deps_are_declared_at_runtime` could pass because the
    parser always returns a set containing everything, or because the assertion is
    unreachable. Here the parser is pointed at a synthetic manifest that deliberately
    omits onnxruntime and declares it only in an extra — the B13 state exactly.
    """
    synthetic = (
        "[project]\n"
        'name = "synthetic"\n'
        "dependencies = [\n"
        '    "fastapi>=0.109.0",\n'
        '    "numpy>=1.26.0",\n'
        "]\n"
        "[project.optional-dependencies]\n"
        'colbert-export = ["optimum[onnxruntime]>=1.21.0"]\n'
    )
    names = _parse_synthetic(synthetic)
    assert "fastapi" in names, "sanity: the synthetic manifest does declare fastapi"
    assert "onnxruntime" not in names, (
        "detector is broken: it reported onnxruntime as a runtime dependency of a "
        "manifest that only lists it inside the colbert-export extra"
    )


def _parse_synthetic(text: str) -> set[str]:
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "pyproject.toml"
        p.write_text(text, encoding="utf-8")
        return _declared_runtime_dependencies(p)


def test_cross_encoder_import_failure_is_observable(monkeypatch, caplog) -> None:
    """The degradation must never be fully silent.

    Forces the `import onnxruntime` inside `ensure_loaded()` to fail (a None entry in
    sys.modules makes `import` raise ImportError) while the model files look present, then
    asserts the documented contract: returns False AND emits a WARNING-or-higher record.
    """
    from src.retrieval import cross_encoder

    # Model-file discovery must look successful, so we exercise the *import* branch and
    # not the earlier "model not found" branch — regardless of what is on this host's disk.
    monkeypatch.setattr(cross_encoder, "_find_onnx", lambda: Path("/nonexistent/model.onnx"))
    monkeypatch.setattr(cross_encoder, "_find_tokenizer", lambda: Path("/nonexistent/tokenizer.json"))
    # Reset the module singletons so ensure_loaded() does not short-circuit on a session
    # where a previous test already loaded the real model. monkeypatch restores them.
    monkeypatch.setattr(cross_encoder, "_session", None)
    monkeypatch.setattr(cross_encoder, "_tokenizer", None)
    monkeypatch.setitem(sys.modules, "onnxruntime", None)

    caplog.clear()
    with caplog.at_level(logging.DEBUG, logger=cross_encoder.__name__):
        loaded = cross_encoder.ensure_loaded()

    assert loaded is False, "ensure_loaded() must report failure when onnxruntime is absent"
    warnings = [
        r for r in caplog.records
        if r.name == cross_encoder.__name__ and r.levelno >= logging.WARNING
    ]
    assert warnings, (
        "cross_encoder.ensure_loaded() failed silently: no WARNING-or-higher record was "
        f"emitted on {cross_encoder.__name__}. Records seen: "
        f"{[(r.name, r.levelname, r.getMessage()) for r in caplog.records]}"
    )


def test_cross_encoder_rerank_returns_input_unchanged_when_deps_missing(monkeypatch) -> None:
    """Fail-open characterisation: the caller cannot tell reranked from not-reranked.

    `rerank()` returns the input list unmodified when the dependency is missing — no
    exception, no sentinel, no `ce_score` key. This test pins that as *known* behaviour so
    the silent-fallback surface is at least documented and counted; the observability that
    does exist is the WARNING asserted above, nothing else.
    """
    from src.retrieval import cross_encoder

    monkeypatch.setattr(cross_encoder, "_find_onnx", lambda: Path("/nonexistent/model.onnx"))
    monkeypatch.setattr(cross_encoder, "_find_tokenizer", lambda: Path("/nonexistent/tok.json"))
    monkeypatch.setattr(cross_encoder, "_session", None)
    monkeypatch.setattr(cross_encoder, "_tokenizer", None)
    monkeypatch.setitem(sys.modules, "onnxruntime", None)

    items = [{"snippet": "a", "score": 0.9}, {"snippet": "b", "score": 0.1}]
    out = cross_encoder.rerank("q", items, weight=0.3)

    assert out == items
    assert all("ce_score" not in it for it in out), (
        "no rerank marker is added on the degraded path — a downstream consumer cannot "
        "distinguish 'reranked' from 'not reranked' from the payload alone"
    )
