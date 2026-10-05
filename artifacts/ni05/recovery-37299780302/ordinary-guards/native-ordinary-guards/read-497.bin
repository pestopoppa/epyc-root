"""NIB2-78: the Kuzu graph layer degrades with one WARNING line, not a traceback."""

from __future__ import annotations

import logging
from types import SimpleNamespace

import pytest

import orchestration.repl_memory.failure_graph as failure_graph_mod
import orchestration.repl_memory.graph_backend as graph_backend
import orchestration.repl_memory.hypothesis_graph as hypothesis_graph_mod
import orchestration.repl_memory.retriever as retriever_mod
from src.api.services import memrl

LOGGER = "src.api.services.memrl"


def _warnings(caplog):
    return [r for r in caplog.records if r.name == LOGGER and r.levelno == logging.WARNING]


class _FakeGraph:
    instances: list["_FakeGraph"] = []

    def __init__(self, *args, **kwargs):
        self.closed = False
        _FakeGraph.instances.append(self)

    def close(self):
        self.closed = True


@pytest.fixture(autouse=True)
def _reset_fakes():
    _FakeGraph.instances = []


def test_kuzu_probe_uses_find_spec(monkeypatch):
    monkeypatch.setattr(graph_backend.importlib.util, "find_spec", lambda name: None)
    assert graph_backend.kuzu_available() is False
    reason = graph_backend.graph_backend_unavailable_reason()
    assert reason is not None and "kuzu" in reason and "[graph]" in reason

    monkeypatch.setattr(graph_backend.importlib.util, "find_spec", lambda name: object())
    assert graph_backend.kuzu_available() is True
    assert graph_backend.graph_backend_unavailable_reason() is None


def test_lock_contention_classifier():
    exc = RuntimeError("IO exception: Could not set lock on file : /x/failure_graph\nSee the docs")
    assert graph_backend.is_kuzu_lock_contention(exc)
    assert not graph_backend.is_kuzu_lock_contention(RuntimeError("disk full"))


def test_missing_kuzu_is_one_warning_without_traceback(monkeypatch, caplog):
    monkeypatch.setattr(graph_backend, "kuzu_available", lambda: False)

    def _must_not_construct(*a, **k):
        raise AssertionError("graph must not be constructed when kuzu is missing")

    monkeypatch.setattr(failure_graph_mod, "FailureGraph", _must_not_construct)
    state = SimpleNamespace(episodic_store=object())

    with caplog.at_level(logging.DEBUG, logger=LOGGER):
        assert memrl._build_graph_retriever(state, object(), object()) is None

    warnings = _warnings(caplog)
    assert len(warnings) == 1
    assert warnings[0].exc_info is None
    assert "Graph layer disabled" in warnings[0].getMessage()
    assert "kuzu" in warnings[0].getMessage()
    assert not hasattr(state, "failure_graph")


def test_lock_contention_is_one_warning_and_closes_opened_graph(monkeypatch, caplog):
    monkeypatch.setattr(graph_backend, "kuzu_available", lambda: True)
    monkeypatch.setattr(failure_graph_mod, "FailureGraph", _FakeGraph)

    def _locked(*a, **k):
        raise RuntimeError(
            "IO exception: Could not set lock on file : /x/hypothesis_graph\n"
            "See the docs: https://docs.kuzudb.com/concurrency for more information."
        )

    monkeypatch.setattr(hypothesis_graph_mod, "HypothesisGraph", _locked)
    state = SimpleNamespace(episodic_store=object())

    with caplog.at_level(logging.DEBUG, logger=LOGGER):
        assert memrl._build_graph_retriever(state, object(), object()) is None

    warnings = _warnings(caplog)
    assert len(warnings) == 1
    assert warnings[0].exc_info is None
    msg = warnings[0].getMessage()
    assert "held by another process" in msg and "\n" not in msg
    assert [g.closed for g in _FakeGraph.instances] == [True]


def test_unexpected_failure_keeps_traceback(monkeypatch, caplog):
    monkeypatch.setattr(graph_backend, "kuzu_available", lambda: True)

    def _boom(*a, **k):
        raise ValueError("schema drift")

    monkeypatch.setattr(failure_graph_mod, "FailureGraph", _boom)
    state = SimpleNamespace(episodic_store=object())

    with caplog.at_level(logging.DEBUG, logger=LOGGER):
        assert memrl._build_graph_retriever(state, object(), object()) is None

    warnings = _warnings(caplog)
    assert len(warnings) == 1
    assert warnings[0].exc_info is not None


def test_success_wires_graphs_into_state(monkeypatch, caplog):
    monkeypatch.setattr(graph_backend, "kuzu_available", lambda: True)
    monkeypatch.setattr(failure_graph_mod, "FailureGraph", _FakeGraph)
    monkeypatch.setattr(hypothesis_graph_mod, "HypothesisGraph", _FakeGraph)

    captured = {}

    def _fake_retriever(**kwargs):
        captured.update(kwargs)
        return "graph-retriever"

    monkeypatch.setattr(retriever_mod, "GraphEnhancedRetriever", _fake_retriever)
    state = SimpleNamespace(episodic_store="store")

    with caplog.at_level(logging.DEBUG, logger=LOGGER):
        result = memrl._build_graph_retriever(state, "embedder", "cfg")

    assert result == "graph-retriever"
    assert state.failure_graph is captured["failure_graph"]
    assert state.hypothesis_graph is captured["hypothesis_graph"]
    assert captured["store"] == "store" and captured["config"] == "cfg"
    assert _warnings(caplog) == []


@pytest.mark.parametrize("module_attr", ["failure", "hypothesis"])
def test_close_releases_kuzu_file_lock(tmp_path, module_attr):
    """close() used to be a no-op, so the exclusive file lock outlived the graph."""
    pytest.importorskip("kuzu", reason="kuzu not installed")
    import subprocess
    import sys

    cls = (
        failure_graph_mod.FailureGraph
        if module_attr == "failure"
        else hypothesis_graph_mod.HypothesisGraph
    )
    db_path = tmp_path / f"{module_attr}_graph"
    graph = cls(path=db_path)
    graph.close()
    graph.close()  # idempotent
    assert graph.db is None and graph.conn is None

    probe = subprocess.run(
        [sys.executable, "-c", f"import kuzu; db = kuzu.Database({str(db_path)!r}); print('ok')"],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert probe.returncode == 0, probe.stderr
    assert probe.stdout.strip() == "ok"
