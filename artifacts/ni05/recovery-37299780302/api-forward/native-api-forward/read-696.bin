"""Guards for the ColBERT [Q]/[D] prefix convention (OP-24, 2026-08-12).

The defect these exist to prevent: `colbert_encoder.encode()` had no role
parameter, so indexing and querying both fed raw text to a model trained with
`[Q] ` / `[D] ` prefixes. Measured on the reference model, no ONNX involved,
the omission moves MaxSim by max |delta| 1.63e-01 and flips top-1 on 37.5% of
queries — ~25x the perturbation of the INT8 quantization we accept.

The subtle half is worse than the obvious half. Prefixing ONLY the query side
puts prefixed query vectors against unprefixed stored vectors, which is
strictly worse than the consistent-but-off-distribution status quo. So the
invariant under test is not "prefixes are applied" — it is:

    the INDEX declares the convention, and BOTH sides follow that declaration.

Every test here is a module-level `test_*` so pytest collects and counts it.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

from src.retrieval import colbert_encoder, kb_rag


# ─── encode() contract ───────────────────────────────────────────────────────

def test_encode_requires_an_explicit_role() -> None:
    """No default role. A default is how the prefix-less path survived."""
    with pytest.raises(TypeError):
        colbert_encoder.encode("hello", 32)  # type: ignore[call-arg]


def test_encode_rejects_an_unknown_role() -> None:
    with pytest.raises(ValueError, match="unknown ColBERT role"):
        colbert_encoder.encode("hello", 32, role="passage")


def test_role_is_keyword_only() -> None:
    """Positional roles invite silently swapping query/document at a call site."""
    with pytest.raises(TypeError):
        colbert_encoder.encode("hello", 32, "query")  # type: ignore[misc]


def test_prefix_for_role_maps_the_three_roles() -> None:
    assert colbert_encoder.prefix_for_role(colbert_encoder.ROLE_NONE) == ""
    assert colbert_encoder.prefix_for_role(colbert_encoder.ROLE_QUERY).strip() == "[Q]"
    assert colbert_encoder.prefix_for_role(colbert_encoder.ROLE_DOCUMENT).strip() == "[D]"


def test_prefixed_role_refuses_a_model_without_the_trained_tokens() -> None:
    """Prepending '[Q] ' to a model that lacks the token emits sub-word junk.

    Better to refuse loudly than to write garbage vectors into a store.
    """
    with patch.object(colbert_encoder, "_prefix_tokens_ok", False), \
         patch.object(colbert_encoder, "_session", object()), \
         patch.object(colbert_encoder, "_tokenizer", object()):
        with pytest.raises(ValueError, match="no such token"):
            colbert_encoder.encode("hello", 32, role=colbert_encoder.ROLE_QUERY)
        # ROLE_NONE stays usable so a legacy store is still readable.
        assert colbert_encoder.prefix_for_role(colbert_encoder.ROLE_NONE) == ""


# ─── real model (skipped when the ONNX model is not on disk) ─────────────────

_MODEL_MISSING = not colbert_encoder.is_available()
_skip_no_model = pytest.mark.skipif(_MODEL_MISSING, reason="ColBERT ONNX model not on disk")


@_skip_no_model
def test_prefixes_are_single_trained_tokens_in_the_real_tokenizer() -> None:
    """Prepending the STRING must equal pylate's id-insertion at index 1."""
    assert colbert_encoder.ensure_loaded()
    tok = colbert_encoder._tokenizer
    q_prefix = colbert_encoder.prefix_for_role(colbert_encoder.ROLE_QUERY)
    d_prefix = colbert_encoder.prefix_for_role(colbert_encoder.ROLE_DOCUMENT)

    assert tok.token_to_id(q_prefix) is not None, "[Q] is not a single vocab token"
    assert tok.token_to_id(d_prefix) is not None, "[D] is not a single vocab token"
    assert colbert_encoder.prefix_tokens_available()

    tok.no_truncation()
    tok.no_padding()
    bare = tok.encode("hello world").ids
    prefixed = tok.encode(q_prefix + "hello world").ids
    # [CLS] PREFIX <same body> — the prefix lands at index 1 and nothing else moves.
    assert prefixed[0] == bare[0]
    assert prefixed[1] == tok.token_to_id(q_prefix)
    assert prefixed[2:] == bare[1:]


@_skip_no_model
def test_query_and_document_roles_produce_different_embeddings() -> None:
    """If the role were a no-op, this migration would be pointless."""
    assert colbert_encoder.ensure_loaded()
    text = "the KB-RAG index stores per-token ColBERT embeddings"
    q = colbert_encoder.encode(text, 48, role=colbert_encoder.ROLE_QUERY)
    d = colbert_encoder.encode(text, 48, role=colbert_encoder.ROLE_DOCUMENT)
    n = colbert_encoder.encode(text, 48, role=colbert_encoder.ROLE_NONE)
    assert q is not None and d is not None and n is not None
    assert q.shape[0] == n.shape[0] + 1, "the prefix must occupy one real token"
    assert not np.allclose(q[1:], n, atol=1e-4), "[Q] did not change the encoding"
    assert not np.allclose(q, d, atol=1e-4), "[Q] and [D] encode identically"


# ─── index-declares-the-convention invariant ─────────────────────────────────

def _tiny_corpus(tmp_path: Path) -> tuple[kb_rag.CorpusConfig, Path]:
    root = tmp_path / "corpus"
    root.mkdir()
    (root / "a.md").write_text("# Doc A\n\nFirst doc, mentions cats.\n")
    (root / "b.md").write_text("# Doc B\n\n## S\n\nSecond doc, dogs and birds.\n")
    cfg = kb_rag.CorpusConfig(
        roots=[str(root)], include_globs=["*.md"], exclude_patterns=[]
    )
    return cfg, tmp_path / "idx"


def _recording_encoder():
    """A fake encode() that records the role of every call."""
    seen: list[str] = []

    def fake_encode(text, max_tokens, *, role):
        seen.append(role)
        arr = np.zeros((3, 4), dtype=np.float32)
        arr[0, 0] = (len(text) % 7) * 0.1 + 0.01
        arr[1, 1] = 0.5
        arr[2, 2] = 0.7
        return arr / np.maximum(np.linalg.norm(arr, axis=1, keepdims=True), 1e-8)

    return seen, fake_encode


def _build(cfg, index_dir, **kw):
    seen, fake_encode = _recording_encoder()
    with patch.object(kb_rag.colbert_encoder, "is_available", return_value=True), \
         patch.object(kb_rag.colbert_encoder, "ensure_loaded", return_value=True), \
         patch.object(kb_rag.colbert_encoder, "encode", side_effect=fake_encode):
        result = kb_rag.build_index(cfg, index_dir=index_dir, **kw)
    return result, seen


def _query(index_dir, text="cats"):
    seen, fake_encode = _recording_encoder()
    with patch.object(kb_rag.colbert_encoder, "ensure_loaded", return_value=True), \
         patch.object(kb_rag.colbert_encoder, "encode", side_effect=fake_encode):
        rows = kb_rag.query(text, top_k=3, index_dir=index_dir)
    return rows, seen


def test_fresh_index_stamps_the_current_convention_and_encodes_documents(tmp_path: Path) -> None:
    cfg, index_dir = _tiny_corpus(tmp_path)
    result, seen = _build(cfg, index_dir)

    assert result["ok"] is True
    assert result["prefix_convention"] == colbert_encoder.PREFIX_CONVENTION
    assert seen and set(seen) == {colbert_encoder.ROLE_DOCUMENT}

    meta = kb_rag.stats(index_dir=index_dir)["meta"]
    assert meta["prefix_convention"] == colbert_encoder.PREFIX_CONVENTION
    assert meta["query_prefix"].strip() == "[Q]"
    assert meta["document_prefix"].strip() == "[D]"
    # The store must be able to name the encoder that produced it.
    assert meta["encoder_model_dir"] == str(colbert_encoder._MODEL_DIR)
    assert meta["encoder_model_file"] == colbert_encoder._MODEL_PATH.name


def test_query_against_a_prefixed_index_uses_the_query_role(tmp_path: Path) -> None:
    cfg, index_dir = _tiny_corpus(tmp_path)
    _build(cfg, index_dir)
    rows, seen = _query(index_dir)
    assert rows
    assert seen == [colbert_encoder.ROLE_QUERY]


def _strip_meta(index_dir: Path) -> None:
    """Turn a fresh index into a faithful pre-OP-24 one: chunks, no stamp."""
    conn = sqlite3.connect(str(index_dir / "catalog.sqlite"))
    conn.execute("DROP TABLE IF EXISTS index_meta")
    conn.commit()
    conn.close()


def test_legacy_index_is_queried_prefix_free(tmp_path: Path) -> None:
    """THE anti-mismatch guard.

    Prefixed queries against unprefixed stored vectors is the one outcome that
    is worse than not migrating at all. An unstamped, populated catalog must
    therefore pull the query side back to ROLE_NONE.
    """
    cfg, index_dir = _tiny_corpus(tmp_path)
    _build(cfg, index_dir)
    _strip_meta(index_dir)

    rows, seen = _query(index_dir)
    assert rows, "a legacy index must keep serving"
    assert seen == [colbert_encoder.ROLE_NONE], (
        "queries were prefixed against a prefix-free store — this is the "
        "mismatch the migration exists to avoid"
    )


def test_legacy_index_keeps_its_convention_under_force_rebuild(tmp_path: Path) -> None:
    """--force re-encodes but must NOT re-stamp: no half-migrated live index."""
    cfg, index_dir = _tiny_corpus(tmp_path)
    _build(cfg, index_dir)
    _strip_meta(index_dir)

    result, seen = _build(cfg, index_dir, force=True)
    assert result["prefix_convention"] == colbert_encoder.LEGACY_CONVENTION
    assert set(seen) == {colbert_encoder.ROLE_NONE}
    _, qseen = _query(index_dir)
    assert qseen == [colbert_encoder.ROLE_NONE]


def test_incremental_update_follows_the_stored_convention(tmp_path: Path) -> None:
    """The post-commit hook must not inject prefixed docs into a legacy index."""
    cfg, index_dir = _tiny_corpus(tmp_path)
    _build(cfg, index_dir)
    _strip_meta(index_dir)

    target = str(Path(cfg.roots[0]) / "a.md")
    seen, fake_encode = _recording_encoder()
    with patch.object(kb_rag.colbert_encoder, "ensure_loaded", return_value=True), \
         patch.object(kb_rag.colbert_encoder, "encode", side_effect=fake_encode):
        result = kb_rag.update_files([target], cfg, index_dir=index_dir)

    assert result["ok"] is True
    assert result["prefix_convention"] == colbert_encoder.LEGACY_CONVENTION
    assert set(seen) == {colbert_encoder.ROLE_NONE}


def test_unknown_stored_convention_fails_closed(tmp_path: Path) -> None:
    """A future convention bump must not be served by old code guessing."""
    cfg, index_dir = _tiny_corpus(tmp_path)
    _build(cfg, index_dir)
    conn = sqlite3.connect(str(index_dir / "catalog.sqlite"))
    conn.execute("UPDATE index_meta SET value='qd-v99' WHERE key='prefix_convention'")
    conn.commit()
    conn.close()

    rows, seen = _query(index_dir)
    assert rows == []
    assert seen == [], "no vector should be encoded under an unreadable convention"


def test_rollback_lever_is_wired(tmp_path: Path) -> None:
    """KB_RAG_INDEX_DIR is the documented no-code-change rollback."""
    import importlib

    import src.retrieval.kb_rag as mod

    with patch.dict("os.environ", {"KB_RAG_INDEX_DIR": str(tmp_path / "rollback")}):
        reloaded = importlib.reload(mod)
        try:
            assert reloaded.DEFAULT_INDEX_DIR == tmp_path / "rollback"
        finally:
            importlib.reload(mod)
