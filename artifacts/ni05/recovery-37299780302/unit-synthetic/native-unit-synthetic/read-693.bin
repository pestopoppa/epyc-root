"""Unit tests for src/retrieval/.

Encoder is mocked — onnxruntime is not always available in devcontainers.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent
from unittest.mock import patch

import numpy as np
import pytest

from src.retrieval.markdown_chunker import (
    Chunk,
    chunk_file,
    chunk_markdown,
)


# ─── chunker ──────────────────────────────────────────────────────────────────

def test_chunk_empty_returns_empty() -> None:
    assert chunk_markdown("", "/p") == []
    assert chunk_markdown("   \n  \n", "/p") == []


def test_chunk_no_headings_single_chunk() -> None:
    text = "just some prose without any headings"
    chunks = chunk_markdown(text, "/p")
    assert len(chunks) == 1
    assert chunks[0].heading_path == []
    assert chunks[0].text == text


def test_chunk_h1_h2_h3_breadcrumb() -> None:
    text = dedent(
        """
        # Top

        intro

        ## Mid A

        body A

        ### Sub

        sub body

        ## Mid B

        body B
        """
    ).strip()
    chunks = chunk_markdown(text, "/p")
    headings = [c.heading_path for c in chunks]
    assert ["Top"] in headings
    assert ["Top", "Mid A"] in headings
    assert ["Top", "Mid A", "Sub"] in headings
    assert ["Top", "Mid B"] in headings
    # Sub closes when Mid B opens — so Mid B should NOT include Sub.
    mid_b = next(c for c in chunks if c.heading_path == ["Top", "Mid B"])
    assert "sub body" not in mid_b.text


def test_chunk_long_section_splits_at_paragraphs() -> None:
    # 6 paragraphs, each 800 chars; total ~5000 chars -> must split.
    para = "x" * 800
    body = "\n\n".join(para for _ in range(6))
    text = f"# Top\n\n{body}"
    chunks = chunk_markdown(text, "/p", max_chars=2000)
    assert len(chunks) >= 2
    for c in chunks:
        assert len(c.text) <= 2200  # max_chars + small slack for boundary
        assert c.heading_path == ["Top"]


def test_chunk_content_hash_stable() -> None:
    text = "# h\n\nbody"
    a = chunk_markdown(text, "/p")[0]
    b = chunk_markdown(text, "/p")[0]
    assert a.content_hash == b.content_hash
    # Different text -> different hash
    c = chunk_markdown("# h\n\nother body", "/p")[0]
    assert a.content_hash != c.content_hash


def test_chunk_file_absent_returns_empty(tmp_path: Path) -> None:
    assert chunk_file(tmp_path / "nope.md") == []


def test_chunk_breadcrumb_property() -> None:
    c = Chunk(file_path="/x", heading_path=["A", "B"], line_range=(1, 2), text="t")
    assert c.heading_breadcrumb == "A > B"
    c2 = Chunk(file_path="/x", heading_path=[], line_range=(1, 2), text="t")
    assert c2.heading_breadcrumb == "(no headings)"


def test_chunk_line_ranges_cover_file(tmp_path: Path) -> None:
    md = tmp_path / "f.md"
    md.write_text("# A\n\nbody1\n\n## B\n\nbody2\n")
    chunks = chunk_file(md)
    # Every line should fall within at least one chunk's range.
    line_count = md.read_text().count("\n") + 1
    covered = set()
    for c in chunks:
        for ln in range(c.line_range[0], c.line_range[1] + 1):
            covered.add(ln)
    # Allow off-by-one slack at the file tail.
    assert len(covered) >= line_count - 2


# ─── kb_rag (mocked encoder) ──────────────────────────────────────────────────

def test_kb_rag_build_with_mock_encoder(tmp_path: Path) -> None:
    from src.retrieval import kb_rag

    # Set up tiny corpus.
    corpus_root = tmp_path / "corpus"
    corpus_root.mkdir()
    (corpus_root / "a.md").write_text("# Doc A\n\nFirst doc, mentions cats.\n")
    (corpus_root / "b.md").write_text("# Doc B\n\n## Section\n\nSecond doc, dogs and birds.\n")

    cfg = kb_rag.CorpusConfig(
        roots=[str(corpus_root)],
        include_globs=["*.md"],
        exclude_patterns=[],
        max_chunk_chars=4000,
    )
    index_dir = tmp_path / "idx"

    # Mock encoder to return deterministic embeddings keyed by text length.
    def fake_encode(text: str, max_tokens: int, *, role: str):
        # 3 tokens of dim-4: deterministic hash-based vector.
        arr = np.zeros((3, 4), dtype=np.float32)
        arr[0, 0] = (len(text) % 7) * 0.1
        arr[1, 1] = 0.5
        arr[2, 2] = 0.7
        # L2 normalize per token.
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        norms = np.maximum(norms, 1e-8)
        return arr / norms

    with patch.object(kb_rag.colbert_encoder, "is_available", return_value=True), \
         patch.object(kb_rag.colbert_encoder, "ensure_loaded", return_value=True), \
         patch.object(kb_rag.colbert_encoder, "encode", side_effect=fake_encode):
        result = kb_rag.build_index(cfg, index_dir=index_dir)

    assert result["ok"] is True
    assert result["files"] == 2
    assert result["chunks_encoded"] >= 2
    assert (index_dir / "catalog.sqlite").exists()
    assert (index_dir / "emb").exists()


def test_kb_rag_build_skips_unchanged_on_rebuild(tmp_path: Path) -> None:
    from src.retrieval import kb_rag

    corpus_root = tmp_path / "corpus"
    corpus_root.mkdir()
    (corpus_root / "a.md").write_text("# Doc\n\nbody\n")
    cfg = kb_rag.CorpusConfig(roots=[str(corpus_root)], include_globs=["*.md"], exclude_patterns=[])
    index_dir = tmp_path / "idx"

    def fake_encode(text, max_tokens, *, role):
        arr = np.eye(3, 4, dtype=np.float32)
        return arr

    with patch.object(kb_rag.colbert_encoder, "is_available", return_value=True), \
         patch.object(kb_rag.colbert_encoder, "ensure_loaded", return_value=True), \
         patch.object(kb_rag.colbert_encoder, "encode", side_effect=fake_encode):
        first = kb_rag.build_index(cfg, index_dir=index_dir)
        second = kb_rag.build_index(cfg, index_dir=index_dir)

    assert first["chunks_encoded"] >= 1
    # Content unchanged -> all chunks skipped on rebuild.
    assert second["chunks_encoded"] == 0
    assert second["chunks_skipped_unchanged"] == first["chunks_encoded"]


def test_kb_rag_query_returns_ranked_results(tmp_path: Path) -> None:
    from src.retrieval import kb_rag

    corpus_root = tmp_path / "corpus"
    corpus_root.mkdir()
    (corpus_root / "cats.md").write_text("# cats\n\nfeline body\n")
    (corpus_root / "dogs.md").write_text("# dogs\n\ncanine body\n")
    cfg = kb_rag.CorpusConfig(roots=[str(corpus_root)], include_globs=["*.md"], exclude_patterns=[])
    index_dir = tmp_path / "idx"

    # Encoder returns vectors that prefer the "cats" file when query mentions feline.
    def fake_encode(text, max_tokens, *, role):
        text_l = text.lower()
        v = np.zeros((2, 4), dtype=np.float32)
        if "feline" in text_l or "cats" in text_l:
            v[0, 0] = 1.0
            v[1, 1] = 0.5
        else:
            v[0, 2] = 1.0
            v[1, 3] = 0.5
        norms = np.linalg.norm(v, axis=1, keepdims=True)
        return v / np.maximum(norms, 1e-8)

    with patch.object(kb_rag.colbert_encoder, "is_available", return_value=True), \
         patch.object(kb_rag.colbert_encoder, "ensure_loaded", return_value=True), \
         patch.object(kb_rag.colbert_encoder, "encode", side_effect=fake_encode):
        kb_rag.build_index(cfg, index_dir=index_dir)
        results = kb_rag.query("tell me about cats", top_k=2, index_dir=index_dir)

    assert len(results) == 2
    # Top result should be the cats file.
    assert "cats.md" in results[0]["file"]
    assert results[0]["score"] >= results[1]["score"]


def test_kb_rag_query_opt_in_embedding_cache_reuses_np_load(tmp_path: Path) -> None:
    from src.retrieval import kb_rag

    corpus_root = tmp_path / "corpus"
    corpus_root.mkdir()
    (corpus_root / "cats.md").write_text("# cats\n\nfeline body\n")
    (corpus_root / "dogs.md").write_text("# dogs\n\ncanine body\n")
    cfg = kb_rag.CorpusConfig(roots=[str(corpus_root)], include_globs=["*.md"], exclude_patterns=[])
    index_dir = tmp_path / "idx"

    def fake_encode(text, max_tokens, *, role):
        text_l = text.lower()
        v = np.zeros((2, 4), dtype=np.float32)
        v[0, 0 if ("feline" in text_l or "cats" in text_l) else 1] = 1.0
        v[1, 2 if ("canine" in text_l or "dogs" in text_l) else 3] = 0.5
        norms = np.linalg.norm(v, axis=1, keepdims=True)
        return v / np.maximum(norms, 1e-8)

    with patch.object(kb_rag.colbert_encoder, "is_available", return_value=True), \
         patch.object(kb_rag.colbert_encoder, "ensure_loaded", return_value=True), \
         patch.object(kb_rag.colbert_encoder, "encode", side_effect=fake_encode):
        kb_rag.build_index(cfg, index_dir=index_dir)
        chunk_count = kb_rag.stats(index_dir=index_dir)["chunks"]
        kb_rag._clear_embedding_cache()
        with patch.object(kb_rag, "_EMB_CACHE_DEFAULT", True), \
             patch.object(kb_rag.np, "load", wraps=kb_rag.np.load) as load_spy:
            kb_rag.query("tell me about cats", top_k=2, index_dir=index_dir)
            kb_rag.query("tell me about dogs", top_k=2, index_dir=index_dir)

    kb_rag._clear_embedding_cache()
    assert load_spy.call_count == chunk_count


def test_kb_rag_update_files_replaces_specific_files(tmp_path: Path) -> None:
    from src.retrieval import kb_rag

    corpus_root = tmp_path / "corpus"
    corpus_root.mkdir()
    f = corpus_root / "a.md"
    f.write_text("# v1\n\nbody v1\n")
    cfg = kb_rag.CorpusConfig(roots=[str(corpus_root)], include_globs=["*.md"], exclude_patterns=[])
    index_dir = tmp_path / "idx"

    def fake_encode(text, max_tokens, *, role):
        return np.eye(3, 4, dtype=np.float32)

    with patch.object(kb_rag.colbert_encoder, "is_available", return_value=True), \
         patch.object(kb_rag.colbert_encoder, "ensure_loaded", return_value=True), \
         patch.object(kb_rag.colbert_encoder, "encode", side_effect=fake_encode):
        kb_rag.build_index(cfg, index_dir=index_dir)
        # Edit file.
        f.write_text("# v2\n\ncompletely different body\n")
        result = kb_rag.update_files([str(f)], cfg, index_dir=index_dir)

    assert result["ok"] is True
    s = kb_rag.stats(index_dir=index_dir)
    assert s["files"] == 1
    # Old chunks for f are gone, replaced.
    assert s["chunks"] >= 1


def test_kb_rag_remove_files_prunes_catalog_rows(tmp_path: Path) -> None:
    from src.retrieval import kb_rag

    corpus_root = tmp_path / "corpus"
    corpus_root.mkdir()
    f = corpus_root / "removed.md"
    f.write_text("# Old\n\nbody\n")
    cfg = kb_rag.CorpusConfig(roots=[str(corpus_root)], include_globs=["*.md"], exclude_patterns=[])
    index_dir = tmp_path / "idx"

    def fake_encode(text, max_tokens, *, role):
        return np.eye(3, 4, dtype=np.float32)

    with patch.object(kb_rag.colbert_encoder, "is_available", return_value=True), \
         patch.object(kb_rag.colbert_encoder, "ensure_loaded", return_value=True), \
         patch.object(kb_rag.colbert_encoder, "encode", side_effect=fake_encode):
        kb_rag.build_index(cfg, index_dir=index_dir)

    assert kb_rag.stats(index_dir=index_dir)["files"] == 1
    f.unlink()
    result = kb_rag.remove_files([str(f)], index_dir=index_dir)

    assert result["ok"] is True
    assert result["files_removed"] == 1
    assert result["chunks_removed"] >= 1
    assert kb_rag.stats(index_dir=index_dir)["files"] == 0


def test_kb_rag_query_returns_empty_when_no_index(tmp_path: Path) -> None:
    from src.retrieval import kb_rag

    assert kb_rag.query("anything", index_dir=tmp_path / "no_index") == []


# ─── encoder back-compat ──────────────────────────────────────────────────────

def test_existing_reranker_imports_still_work() -> None:
    """The K1 refactor must not break src.tools.web.colbert_reranker."""
    # Import-only test — no runtime call.
    from src.tools.web.colbert_reranker import is_available, rerank_snippets

    assert callable(is_available)
    assert callable(rerank_snippets)


def test_new_retrieval_exports_match_handoff() -> None:
    """Public API per handoffs/active/internal-kb-rag.md K1."""
    from src.retrieval import encode, ensure_loaded, is_available, maxsim

    assert callable(encode)
    assert callable(ensure_loaded)
    assert callable(is_available)
    assert callable(maxsim)


# ─── K10: temporal recency signal ─────────────────────────────────────────────

def test_recency_score_monotonic_and_bounds() -> None:
    from src.retrieval import kb_rag

    now = 1_000_000_000.0
    fresh = kb_rag._recency_score(now, now, sigma_days=90.0)
    week_old = kb_rag._recency_score(now - 7 * 86400, now, sigma_days=90.0)
    year_old = kb_rag._recency_score(now - 365 * 86400, now, sigma_days=90.0)
    assert fresh == 1.0
    assert 0.0 < year_old < week_old < fresh <= 1.0
    # sigma<=0 disables decay (always 1.0); future mtime clamps to age 0.
    assert kb_rag._recency_score(now - 99 * 86400, now, sigma_days=0.0) == 1.0
    assert kb_rag._recency_score(now + 5 * 86400, now, sigma_days=90.0) == 1.0


def test_kb_rag_query_recency_reorders_on_tie(tmp_path: Path) -> None:
    """With equal MaxSim, a high recency_weight ranks the newer file first;
    recency_weight=0 (default) preserves MaxSim-only behaviour (back-compat)."""
    import os as _os
    import time

    from src.retrieval import kb_rag

    corpus_root = tmp_path / "corpus"
    corpus_root.mkdir()
    old_f = corpus_root / "old.md"
    new_f = corpus_root / "new.md"
    old_f.write_text("# topic\n\nshared body\n")
    new_f.write_text("# topic\n\nshared body\n")
    # old.md = 400 days old, new.md = now.
    now = time.time()
    _os.utime(old_f, (now - 400 * 86400, now - 400 * 86400))
    _os.utime(new_f, (now, now))

    cfg = kb_rag.CorpusConfig(roots=[str(corpus_root)], include_globs=["*.md"], exclude_patterns=[])
    index_dir = tmp_path / "idx"

    # Constant embedding → identical MaxSim for both files.
    def fake_encode(text, max_tokens, *, role):
        return np.eye(2, 4, dtype=np.float32)

    with patch.object(kb_rag.colbert_encoder, "is_available", return_value=True), \
         patch.object(kb_rag.colbert_encoder, "ensure_loaded", return_value=True), \
         patch.object(kb_rag.colbert_encoder, "encode", side_effect=fake_encode):
        kb_rag.build_index(cfg, index_dir=index_dir)
        recent_first = kb_rag.query(
            "topic", top_k=2, index_dir=index_dir,
            recency_weight=0.9, recency_sigma_days=90.0,
        )
        baseline = kb_rag.query("topic", top_k=2, index_dir=index_dir, recency_weight=0.0)

    assert "new.md" in recent_first[0]["file"]
    assert recent_first[0]["recency"] > recent_first[1]["recency"]
    # Default path adds no recency key (pure MaxSim).
    assert "recency" not in baseline[0]


# ─── K11: FTS5 lexical signal ────────────────────────────────────────────────

def test_kb_rag_query_lexical_signal_backfills_on_rebuild(tmp_path: Path) -> None:
    """FTS5 stays optional, but rebuilds must repopulate it for unchanged rows."""
    import sqlite3

    from src.retrieval import kb_rag

    corpus_root = tmp_path / "corpus"
    corpus_root.mkdir()
    a = corpus_root / "a.md"
    b = corpus_root / "b.md"
    a.write_text("# A\n\nshared body\n")
    b.write_text("# B\n\nneedle only here\n")

    cfg = kb_rag.CorpusConfig(roots=[str(corpus_root)], include_globs=["*.md"], exclude_patterns=[])
    index_dir = tmp_path / "idx"

    def fake_encode(text, max_tokens, *, role):
        return np.eye(2, 4, dtype=np.float32)

    with patch.object(kb_rag.colbert_encoder, "is_available", return_value=True), \
         patch.object(kb_rag.colbert_encoder, "ensure_loaded", return_value=True), \
         patch.object(kb_rag.colbert_encoder, "encode", side_effect=fake_encode):
        first = kb_rag.build_index(cfg, index_dir=index_dir)
        baseline = kb_rag.query("needle", top_k=2, index_dir=index_dir)

    assert first["chunks_encoded"] >= 2
    assert "a.md" in baseline[0]["file"]

    catalog_path = index_dir / "catalog.sqlite"
    conn = sqlite3.connect(str(catalog_path))
    has_fts = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='chunk_fts'"
    ).fetchone()
    if has_fts is None:
        conn.close()
        pytest.skip("SQLite FTS5 is unavailable in this environment")
    conn.execute("DROP TABLE chunk_fts")
    conn.commit()
    conn.close()

    with patch.object(kb_rag.colbert_encoder, "is_available", return_value=True), \
         patch.object(kb_rag.colbert_encoder, "ensure_loaded", return_value=True), \
         patch.object(kb_rag.colbert_encoder, "encode", side_effect=fake_encode):
        second = kb_rag.build_index(cfg, index_dir=index_dir)
        results = kb_rag.query("needle", top_k=2, index_dir=index_dir, lexical_weight=1.0)

    assert second["chunks_skipped_unchanged"] >= 2
    assert "b.md" in results[0]["file"]
    assert results[0]["lexical"] == 1.0
    assert results[0]["score"] >= results[1]["score"]


def test_kb_rag_rebuild_backfills_duplicate_content_chunks(tmp_path: Path) -> None:
    """Unchanged duplicate chunks in one file must each get an FTS row."""
    import sqlite3

    from src.retrieval import kb_rag
    from src.retrieval.markdown_chunker import Chunk

    corpus_root = tmp_path / "corpus"
    corpus_root.mkdir()
    doc = corpus_root / "dup.md"
    doc.write_text("# Dup\n\nneedle\n\nneedle\n")

    chunks = [
        Chunk(str(doc), ["Dup"], (1, 2), "needle"),
        Chunk(str(doc), ["Dup"], (4, 5), "needle"),
    ]
    cfg = kb_rag.CorpusConfig(roots=[str(corpus_root)], include_globs=["*.md"], exclude_patterns=[])
    index_dir = tmp_path / "idx"

    def fake_encode(text, max_tokens, *, role):
        return np.eye(2, 4, dtype=np.float32)

    with patch.object(kb_rag.colbert_encoder, "is_available", return_value=True), \
         patch.object(kb_rag.colbert_encoder, "ensure_loaded", return_value=True), \
         patch.object(kb_rag.colbert_encoder, "encode", side_effect=fake_encode), \
         patch.object(kb_rag, "chunk_file", return_value=chunks):
        kb_rag.build_index(cfg, index_dir=index_dir)

    catalog_path = index_dir / "catalog.sqlite"
    conn = sqlite3.connect(str(catalog_path))
    has_fts = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='chunk_fts'"
    ).fetchone()
    if has_fts is None:
        conn.close()
        pytest.skip("SQLite FTS5 is unavailable in this environment")
    assert conn.execute("SELECT COUNT(*) FROM chunk").fetchone()[0] == 2
    assert conn.execute("SELECT COUNT(*) FROM chunk_fts").fetchone()[0] == 2
    conn.execute("DROP TABLE chunk_fts")
    conn.commit()
    conn.close()

    with patch.object(kb_rag.colbert_encoder, "is_available", return_value=True), \
         patch.object(kb_rag.colbert_encoder, "ensure_loaded", return_value=True), \
         patch.object(kb_rag.colbert_encoder, "encode", side_effect=fake_encode), \
         patch.object(kb_rag, "chunk_file", return_value=chunks):
        second = kb_rag.build_index(cfg, index_dir=index_dir)

    conn = sqlite3.connect(str(catalog_path))
    try:
        assert second["chunks_skipped_unchanged"] == 2
        assert conn.execute("SELECT COUNT(*) FROM chunk").fetchone()[0] == 2
        assert conn.execute("SELECT COUNT(*) FROM chunk_fts").fetchone()[0] == 2
    finally:
        conn.close()


# ─── K9: cross-encoder rerank stage ───────────────────────────────────────────

def test_cross_encoder_rerank_noop_when_unavailable() -> None:
    from src.retrieval import cross_encoder

    items = [{"snippet": "a", "score": 0.9}, {"snippet": "b", "score": 0.1}]
    with patch.object(cross_encoder, "ensure_loaded", return_value=False):
        out = cross_encoder.rerank("q", items, weight=0.3)
    assert out == items  # unchanged, safe to call unconditionally
    assert cross_encoder.score_pairs("q", ["a"]) is None  # not loaded


def test_cross_encoder_rerank_blends_and_reorders() -> None:
    from src.retrieval import cross_encoder

    # Item B has lower base score but the CE strongly prefers it → should flip.
    items = [
        {"snippet": "high base, low ce", "score": 0.80},
        {"snippet": "low base, high ce", "score": 0.40},
    ]
    logits = np.array([-4.0, 4.0], dtype=np.float32)  # sigmoid → ~0.018, ~0.982
    with patch.object(cross_encoder, "ensure_loaded", return_value=True), \
         patch.object(cross_encoder, "score_pairs", return_value=logits):
        out = cross_encoder.rerank("q", items, weight=0.6)
    assert "high ce" in out[0]["snippet"]
    assert out[0]["ce_score"] > out[1]["ce_score"]


def test_cross_encoder_real_model_discriminates() -> None:
    """End-to-end with the actual ONNX model if it is on disk (skips in CI
    containers without it). Relevant pair must outscore an irrelevant one."""
    from src.retrieval import cross_encoder

    if not cross_encoder.is_available():
        pytest.skip("cross-encoder ONNX model not on disk")
    # is_available() checks FILES ONLY (documented: "does not load"). The load
    # path additionally needs the runtime, which pyproject keeps behind the
    # optional `colbert-export` extra — so the skip condition must cover it too,
    # otherwise this test reports a missing optional dep as a source defect.
    pytest.importorskip("onnxruntime")
    pytest.importorskip("tokenizers")
    assert cross_encoder.ensure_loaded()
    logits = cross_encoder.score_pairs(
        "How do I reset my password?",
        [
            "Click 'Forgot password' on the login page to reset it.",
            "The mitochondria is the powerhouse of the cell.",
        ],
    )
    assert logits is not None and logits[0] > logits[1]


def test_kb_rag_query_invokes_rerank_when_enabled(tmp_path: Path) -> None:
    from src.retrieval import cross_encoder, kb_rag

    corpus_root = tmp_path / "corpus"
    corpus_root.mkdir()
    (corpus_root / "a.md").write_text("# a\n\nalpha body\n")
    (corpus_root / "b.md").write_text("# b\n\nbeta body\n")
    cfg = kb_rag.CorpusConfig(roots=[str(corpus_root)], include_globs=["*.md"], exclude_patterns=[])
    index_dir = tmp_path / "idx"

    def fake_encode(text, max_tokens, *, role):
        return np.eye(2, 4, dtype=np.float32)

    with patch.object(kb_rag.colbert_encoder, "is_available", return_value=True), \
         patch.object(kb_rag.colbert_encoder, "ensure_loaded", return_value=True), \
         patch.object(kb_rag.colbert_encoder, "encode", side_effect=fake_encode):
        kb_rag.build_index(cfg, index_dir=index_dir)
        with patch.object(cross_encoder, "rerank", side_effect=lambda q, items, **kw: items) as rr:
            kb_rag.query("alpha", top_k=2, index_dir=index_dir, rerank=True, rerank_weight=0.3)
            assert rr.called
        with patch.object(cross_encoder, "rerank", side_effect=lambda q, items, **kw: items) as rr2:
            kb_rag.query("alpha", top_k=2, index_dir=index_dir, rerank=False)
            assert not rr2.called
