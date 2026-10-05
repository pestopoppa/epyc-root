"""embed_soft_label_dataset: prompts must fit ONE embedder slot, never zero-fill.

Regression for the 2026-09-26 audit finding: the fixed 1400-char cap was sized
for a -c 2048 -np 4 pool (512 tokens/slot) and could reach ~518 tokens, but the
live pool runs -c 512 -np 4 (n_ctx 256/slot). llama-server rejects an
over-slot input with HTTP 400 exceed_context_size_error, and the per-item
fallback then substituted a ZERO VECTOR -- a structurally valid feature row
that silently poisoned the training NPZ.

All HTTP is faked (module-level ``requests`` is monkeypatched); no live servers.
The fake tokenizer is worst-case: 1 token per character.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location(
    "embed_soft_label_dataset_under_test",
    ROOT / "scripts" / "graph_router" / "embed_soft_label_dataset.py",
)
esl = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(esl)

SLOT = 256


class _Resp:
    def __init__(self, status: int, payload):
        self.status_code = status
        self._payload = payload
        self.text = json.dumps(payload)

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}: {self.text}")


class _FakePool:
    """Fake llama-server embedder pool with a per-slot context of ``slot``."""

    def __init__(self, slot: int = SLOT, props=None, embed_status: int | None = None):
        self.slot = slot
        self.props = props  # port -> n_ctx, or None for "unreachable"
        self.embed_status = embed_status
        self.embedded: list[str] = []

    def get(self, url, timeout=None):
        port = int(url.split(":")[2].split("/")[0])
        if self.props is None or port not in self.props:
            raise ConnectionError(f"no server on {port}")
        return _Resp(200, {"default_generation_settings": {"n_ctx": self.props[port]}})

    def post(self, url, json=None, timeout=None):  # noqa: A002 - mirrors requests
        content = json["content"]
        if url.endswith("/tokenize"):
            return _Resp(200, {"tokens": list(range(len(content)))})  # 1 tok/char
        assert url.endswith("/embedding"), url
        if self.embed_status is not None:
            return _Resp(self.embed_status, {"error": "transient"})
        texts = content if isinstance(content, list) else [content]
        out = []
        for text in texts:
            n_prompt = len(text) + 2  # [CLS] + [SEP]
            if n_prompt > self.slot:
                return _Resp(
                    400,
                    {"error": {"code": 400, "type": "exceed_context_size_error",
                               "n_prompt_tokens": n_prompt, "n_ctx": self.slot}},
                )
            self.embedded.append(text)
            vec = np.zeros(1024, dtype=np.float32)
            vec[len(text) % 1024] = 1.0
            vec[1023] = 0.5
            out.append({"index": len(out), "embedding": [vec.tolist()]})
        return _Resp(200, out)


@pytest.fixture
def pool(monkeypatch):
    fake = _FakePool(props={8090: SLOT, 8091: SLOT})
    monkeypatch.setattr(esl.requests, "get", fake.get)
    monkeypatch.setattr(esl.requests, "post", fake.post)
    return fake


# ── budget / cap ────────────────────────────────────────────────────────────


def test_budget_reserves_special_tokens_and_old_cap_was_over_slot():
    assert esl.DEFAULT_SLOT_CTX_TOKENS == SLOT
    assert esl.token_budget(SLOT) == SLOT - 2
    # The retired fixed cap (1400 chars at ~2.7 chars/token ~= 518 tokens)
    # overflowed a 256-token slot; the derived pre-truncation cap must not.
    assert 1400 / 2.7 > SLOT
    assert esl.max_prompt_chars(SLOT) / 2.7 < SLOT
    # BGE's own 512 ceiling still binds for bigger slots.
    assert esl.token_budget(2048) == 512 - 2


def test_probe_reads_smallest_slot_from_props(monkeypatch):
    fake = _FakePool(props={8090: 256, 8091: 128})
    monkeypatch.setattr(esl.requests, "get", fake.get)
    assert esl.probe_slot_ctx_tokens([8090, 8091, 8092]) == 128


def test_probe_falls_back_to_safe_default_when_unreachable(monkeypatch):
    fake = _FakePool(props=None)
    monkeypatch.setattr(esl.requests, "get", fake.get)
    assert esl.probe_slot_ctx_tokens([8090, 8091]) == esl.DEFAULT_SLOT_CTX_TOKENS


def test_probe_caps_at_bge_max(monkeypatch):
    fake = _FakePool(props={8090: 2048})
    monkeypatch.setattr(esl.requests, "get", fake.get)
    assert esl.probe_slot_ctx_tokens([8090]) == esl.BGE_MAX_TOKENS


# ── exact fit ───────────────────────────────────────────────────────────────


def test_fit_truncates_to_exact_token_budget(pool):
    budget = esl.token_budget(SLOT)
    fitted = esl.fit_to_token_budget("x" * 2000, 8090, budget)
    assert 0 < len(fitted) <= budget  # 1 token/char worst case
    short = "short prompt"
    assert esl.fit_to_token_budget(short, 8090, budget) == short


def test_fit_raises_when_it_cannot_converge(monkeypatch):
    monkeypatch.setattr(esl, "_count_tokens", lambda text, port: 10_000)
    with pytest.raises(esl.EmbeddingInputTooLong):
        esl.fit_to_token_budget("y" * 500, 8090, 254)


# ── loud failure instead of zero vectors ────────────────────────────────────


def test_over_slot_input_raises_not_zero_vector(pool):
    texts = ["ok text", "z" * 1400]  # the second is over the 256-token slot
    with pytest.raises(esl.EmbeddingInputTooLong):
        esl._embed_indexed(0, texts, [8090, 8091])


def test_item_failing_on_every_port_raises_embedding_failed(monkeypatch):
    fake = _FakePool(embed_status=503)
    monkeypatch.setattr(esl.requests, "post", fake.post)
    with pytest.raises(esl.EmbeddingFailed):
        esl._embed_indexed(0, ["a", "b"], [8090, 8091])


def test_zero_or_nonfinite_rows_are_refused():
    good = np.ones((2, 1024), dtype=np.float32)
    esl._assert_embeddings_valid(good)
    zero = good.copy()
    zero[1] = 0.0
    with pytest.raises(esl.EmbeddingFailed, match="all-zero"):
        esl._assert_embeddings_valid(zero)
    nan = good.copy()
    nan[0, 3] = np.nan
    with pytest.raises(esl.EmbeddingFailed, match="non-finite"):
        esl._assert_embeddings_valid(nan)


# ── end to end ──────────────────────────────────────────────────────────────


def test_build_dataset_fits_long_prompts_to_live_slot(pool, tmp_path):
    prompts = {
        "gpqa": "short question?",
        "cruxeval": "def f(x):\n    return [x] * 3\n" * 120,  # ~3.7k chars, dense
        "hotpotqa": "w " * 1500,
    }
    pool_path = tmp_path / "pool.jsonl"
    labels_path = tmp_path / "soft_labels.jsonl"
    with open(pool_path, "w") as pf, open(labels_path, "w") as lf:
        for suite, prompt in prompts.items():
            pf.write(json.dumps({"suite": suite, "prompt": prompt}) + "\n")
            n = len(esl.CANONICAL_ROLES)
            lf.write(json.dumps({
                "qid": esl._stable_qid(suite, prompt),
                "suite": suite,
                "soft_labels": [1.0 / n] * n,
                "correctness_vector": [0.5] * n,
            }) + "\n")

    out = tmp_path / "out.npz"
    summary = esl.build_dataset(
        soft_labels_path=labels_path,
        pool_path=pool_path,
        output_path=out,
        base_port=8090,
        servers=2,
        batch_size=2,
    )  # slot size probed from the fake /props

    assert summary["resolved"] == 3
    # Every text the server embedded fitted one slot including [CLS]/[SEP].
    assert len(pool.embedded) == 3
    assert all(len(t) + 2 <= SLOT for t in pool.embedded)
    X = np.load(out, allow_pickle=True)["X"]
    assert X.shape == (3, 1031)
    assert np.all(np.any(X[:, :1024] != 0.0, axis=1))  # no zero-vector rows
