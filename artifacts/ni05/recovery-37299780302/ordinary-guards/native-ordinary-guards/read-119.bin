"""Tests for the ColBERT rerank benchmark harness."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.benchmark import bench_colbert_rerank as bench


class FakeReranker:
    _MODEL_SLOT = "fake_slot"
    _MODEL_DIR = Path("/tmp/fake-colbert")

    def __init__(self, available: bool = True) -> None:
        self.available = available
        self.calls: list[tuple[str, int, int]] = []

    def is_available(self) -> bool:
        return self.available

    def rerank_snippets(self, query, snippets, top_k=3):
        self.calls.append((query, len(snippets), top_k))
        return list(snippets[:top_k])


def test_build_snippets_creates_search_like_records():
    snippets = bench.build_snippets(3)

    assert len(snippets) == 3
    assert {"title", "snippet", "url"} <= set(snippets[0])
    assert snippets[0]["url"].startswith("https://example.invalid/colbert-bench/")


def test_run_benchmark_excludes_warmup_from_measured_count():
    reranker = FakeReranker()
    config = bench.BenchmarkConfig(
        iterations=4,
        warmup=2,
        snippets=6,
        queries=2,
        top_k=3,
    )

    report = bench.run_benchmark(config, reranker)

    assert report.status == "ok"
    assert report.model_slot == "fake_slot"
    assert report.model_dir == "/tmp/fake-colbert"
    assert report.warmup_calls == 2
    assert report.measured_calls == 4
    assert report.total_snippets == 24
    assert len(reranker.calls) == 6
    assert {call[1] for call in reranker.calls} == {6}
    assert {call[2] for call in reranker.calls} == {3}
    assert report.mean_ms >= 0.0
    assert report.p95_ms >= 0.0


def test_run_benchmark_refuses_unavailable_model():
    reranker = FakeReranker(available=False)

    with pytest.raises(bench.ModelUnavailableError, match="unavailable"):
        bench.run_benchmark(bench.BenchmarkConfig(), reranker)


def test_run_benchmark_rejects_invalid_query_count():
    reranker = FakeReranker()
    config = bench.BenchmarkConfig(queries=0)

    with pytest.raises(ValueError, match="queries"):
        bench.run_benchmark(config, reranker)


def test_configure_model_env_sets_only_selected_slot(monkeypatch):
    monkeypatch.setenv(bench.LATEON_ENV, "old-lateon")
    monkeypatch.setenv(bench.REASON_MXBAI_ENV, "old-reason")
    config = bench.BenchmarkConfig(
        model_path=Path("/models/reason"),
        model_slot="reason_mxbai",
    )

    bench.configure_model_env(config)

    assert bench.LATEON_ENV not in bench.os.environ
    assert bench.os.environ[bench.REASON_MXBAI_ENV] == "/models/reason"


def test_main_skip_if_unavailable_outputs_json(monkeypatch, capsys):
    fake = FakeReranker(available=False)
    monkeypatch.setattr(bench, "load_reranker", lambda config: fake)

    rc = bench.main(["--skip-if-unavailable", "--json"])

    assert rc == 0
    out = capsys.readouterr().out
    assert '"status": "skipped_unavailable"' in out
    assert '"measured_calls": 0' in out
