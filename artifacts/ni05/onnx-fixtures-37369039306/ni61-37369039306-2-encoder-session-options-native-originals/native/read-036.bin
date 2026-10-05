"""Shared cross-encoder reranker primitives (ONNX Runtime).

A cross-encoder scores a (query, document) PAIR jointly and emits a single
relevance logit — strictly more expressive than the bi-encoder MaxSim used
for first-stage retrieval, at the cost of one forward pass per candidate.
Used as an optional final rerank stage over the top-N KB-RAG candidates
(handoffs/active/internal-kb-rag.md K9).

Default model: cross-encoder/ms-marco-MiniLM-L-6-v2 exported to ONNX
(BERT backbone, num_labels=1). Override the directory via
`KB_RAG_CROSS_ENCODER_PATH`. The module mirrors colbert_encoder.py:
ONNX session + tokenizer are module-level singletons, lazy-loaded on first
call, and every entry point degrades gracefully (returns False / None /
unmodified input) when the model is absent or deps are missing — so callers
can wire the rerank stage unconditionally and have it no-op until the model
is downloaded.

Public API:
    is_available() -> bool
    ensure_loaded() -> bool
    score_pairs(query, docs) -> np.ndarray | None   # raw logits, shape (len(docs),)
    rerank(query, items, text_key, weight, base_key) -> list   # blended re-sort
"""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

# Model dir resolution. The ONNX export is expected to contain a *.onnx graph
# (quantized preferred for CPU) and a tokenizer.json.
DEFAULT_MODEL_DIR = Path("/mnt/raid0/llm/models/ms-marco-minilm-l6-v2-onnx")
_MODEL_DIR = Path(os.environ.get("KB_RAG_CROSS_ENCODER_PATH") or DEFAULT_MODEL_DIR)
_MAX_PAIR_TOKENS = 256

# ONNX Runtime intra-op thread bound.
#
# `score_pairs()` feeds N rows in ONE run(), so unlike the single-row siblings this
# is a genuinely batched pass with real parallel work — and it still oversubscribes
# under ORT's default pool (one thread per visible core) on this 192-thread host.
# Measured 2026-08-12 on EPYC 9655, model_int8.onnx, 10 calls x 3 interleaved
# rounds, medians in ms:
#
#     batch=10:  2t=87.6   4t=38.9   8t=24.2   16t=19.9   32t=21.2   (192t=44.5)
#     batch=50:  2t=417.9  4t=277.9  8t=214.8  16t=129.7  32t=152.2  (192t=200.0)
#
# 16 wins at BOTH batch sizes and 32 is worse at both, so it is a real optimum, not
# an edge of the swept range. Unbounded costs 2.03x at batch=10 and 1.45x at
# batch=50 — the penalty narrows as batch grows, because there is more parallel work
# to amortise the coordination over, but it never disappears.
#
# NOTE this is 16, not the 8 used by the single-row colbert encoder/reranker.
# Copying their value here costs ~40% at batch=50. The optimum is call-shape
# dependent; measure before reusing.
_DEFAULT_ONNX_THREADS = 16


def _onnx_threads() -> int:
    """Resolve the ONNX intra-op thread count (env-overridable, positive int)."""
    raw = os.environ.get("CROSS_ENCODER_ONNX_THREADS")
    if not raw:
        return _DEFAULT_ONNX_THREADS
    try:
        value = int(raw)
    except ValueError:
        logger.warning(
            "CROSS_ENCODER_ONNX_THREADS=%r is not an integer; using %d",
            raw, _DEFAULT_ONNX_THREADS,
        )
        return _DEFAULT_ONNX_THREADS
    if value <= 0:
        logger.warning(
            "CROSS_ENCODER_ONNX_THREADS=%d must be positive; using %d",
            value, _DEFAULT_ONNX_THREADS,
        )
        return _DEFAULT_ONNX_THREADS
    return value


# Module-level singletons (lazy-loaded).
_session = None
_tokenizer = None
_input_names: tuple[str, ...] = ()


def _find_onnx() -> Path | None:
    """Pick the ONNX graph in the model dir, preferring a quantized variant."""
    if not _MODEL_DIR.is_dir():
        return None
    candidates = sorted(_MODEL_DIR.rglob("*.onnx"))
    if not candidates:
        return None
    # Prefer int8/quantized graphs for CPU; else the first.
    for c in candidates:
        if "int8" in c.name or "quant" in c.name:
            return c
    return candidates[0]


def _find_tokenizer() -> Path | None:
    if not _MODEL_DIR.is_dir():
        return None
    hits = sorted(_MODEL_DIR.rglob("tokenizer.json"))
    return hits[0] if hits else None


def is_available() -> bool:
    """Return True iff an ONNX graph + tokenizer exist on disk. Does not load."""
    return _find_onnx() is not None and _find_tokenizer() is not None


def ensure_loaded() -> bool:
    """Lazily load ONNX session + tokenizer. Returns True on success.

    No-op when already loaded. Returns False if deps are missing or the
    model files cannot be opened — callers must check the return value.
    """
    global _session, _tokenizer, _input_names

    if _session is not None and _tokenizer is not None:
        return True

    onnx_path = _find_onnx()
    tok_path = _find_tokenizer()
    if onnx_path is None or tok_path is None:
        logger.warning("cross-encoder model not found under %s", _MODEL_DIR)
        return False

    try:
        import onnxruntime as ort
        from tokenizers import Tokenizer

        start = time.perf_counter()
        sess_options = ort.SessionOptions()
        sess_options.intra_op_num_threads = _onnx_threads()
        sess_options.inter_op_num_threads = 1
        _session = ort.InferenceSession(
            str(onnx_path),
            sess_options=sess_options,
            providers=["CPUExecutionProvider"],
        )
        _input_names = tuple(i.name for i in _session.get_inputs())
        _tokenizer = Tokenizer.from_file(str(tok_path))
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "cross-encoder loaded: %s (inputs=%s, %.0fms)",
            onnx_path.name, ",".join(_input_names), elapsed_ms,
        )
        return True
    except ImportError as e:
        logger.warning("cross-encoder dependencies missing: %s", e)
        return False
    except Exception as e:  # noqa: BLE001 — defensive; caller checks return.
        logger.error("cross-encoder load failed: %s", e)
        return False


def score_pairs(query: str, docs: list[str]) -> np.ndarray | None:
    """Score each (query, doc) pair; return raw relevance logits.

    Returns an array shape (len(docs),) or None on failure. The feed dict is
    built dynamically from the model's declared input names so it works for
    BERT-style graphs (input_ids + attention_mask [+ token_type_ids]).
    """
    if _session is None or _tokenizer is None:
        return None
    if not docs:
        return np.empty((0,), dtype=np.float32)

    try:
        _tokenizer.enable_truncation(max_length=_MAX_PAIR_TOKENS)
        _tokenizer.enable_padding(length=_MAX_PAIR_TOKENS)
        encs = _tokenizer.encode_batch([(query, d) for d in docs])

        input_ids = np.array([e.ids for e in encs], dtype=np.int64)
        attention_mask = np.array([e.attention_mask for e in encs], dtype=np.int64)
        feed: dict[str, np.ndarray] = {}
        if "input_ids" in _input_names:
            feed["input_ids"] = input_ids
        if "attention_mask" in _input_names:
            feed["attention_mask"] = attention_mask
        if "token_type_ids" in _input_names:
            feed["token_type_ids"] = np.array(
                [e.type_ids for e in encs], dtype=np.int64
            )

        logits = _session.run(None, feed)[0]  # (n, num_labels) or (n,)
        logits = np.asarray(logits, dtype=np.float32).reshape(len(docs), -1)
        # num_labels==1 cross-encoders emit a single relevance score per pair.
        return logits[:, 0]
    except Exception as e:  # noqa: BLE001
        logger.debug("cross-encoder score_pairs failed: %s", e)
        return None


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


def rerank(
    query: str,
    items: list[dict],
    text_key: str = "snippet",
    weight: float = 0.3,
    base_key: str = "score",
) -> list[dict]:
    """Blend cross-encoder relevance into an existing first-stage ranking.

    final = (1 - weight) * base_score + weight * sigmoid(cross_encoder_logit)

    Mirrors agentmemory's 0.70 fusion + 0.30 CE blend (intake-611). Each item
    gets a `ce_score` (sigmoid of the logit) and an updated `score`; the list
    is returned re-sorted by the blended score. Returns `items` unchanged if
    the model is unavailable or scoring fails — safe to call unconditionally.
    """
    if not items or weight <= 0.0:
        return items
    if not ensure_loaded():
        return items
    logits = score_pairs(query, [str(it.get(text_key, "")) for it in items])
    if logits is None:
        return items
    ce = _sigmoid(logits)
    for it, c in zip(items, ce):
        base = float(it.get(base_key, 0.0))
        it["ce_score"] = round(float(c), 4)
        it[base_key] = round((1.0 - weight) * base + weight * float(c), 4)
    return sorted(items, key=lambda it: it.get(base_key, 0.0), reverse=True)
