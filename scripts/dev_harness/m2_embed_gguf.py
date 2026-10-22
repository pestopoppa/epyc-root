#!/usr/bin/env python3
"""DHM-7.2 neural CPU embedder: a small embedding GGUF through the production ``llama-embedding``.

Drop-in for ``m2_cluster.embed``: ``make_embedder(gguf)`` returns ``embed(docs) -> L2-normalised float32 matrix``.
Single-threaded (``-t 1``), CPU only (``-ngl 0``), model default pooling, documents truncated to ``MAX_CHARS``.
Document text goes to a private temp file (0600, removed after) and never to argv or stdout. The caller owns nice
(``mine_m2.py`` renices itself to 19). Embedding needs no server and no generation.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile

KERNEL_STORE_CPU = os.environ.get("PP_KERNEL_STORE", "/mnt/raid0/llm/kernels/production/cpu")
DEFAULT_GGUF = "/mnt/raid0/llm/models/granite-embedding-97m-multilingual-r2-Q8_0.gguf"
SEP = "<#sep#>"
MAX_CHARS = 1200      # ~300-400 tokens, inside the 512 context
BATCH = 32            # docs per llama-embedding call (bounds one call's memory)


def _clean(text: str) -> str:
    return (text or "")[:MAX_CHARS].replace(SEP, " ") or " "


def embed_texts(texts: list[str], gguf: str = DEFAULT_GGUF, runner=subprocess.run) -> list[list[float]]:
    out: list[list[float]] = []
    for i in range(0, len(texts), BATCH):
        chunk = [_clean(t) for t in texts[i:i + BATCH]]
        fd, path = tempfile.mkstemp(prefix="m2emb-", suffix=".txt")       # 0600
        try:
            with os.fdopen(fd, "w") as f:
                f.write(SEP.join(chunk))
            r = runner([f"{KERNEL_STORE_CPU}/llama-embedding", "-m", gguf, "-t", "1", "-ngl", "0", "-c", "512",
                        "-b", "8192", "-ub", "8192", "-f", path, "--embd-separator", SEP,
                        "--embd-output-format", "json", "--no-warmup"],
                       capture_output=True, text=True, env={**os.environ, "LD_LIBRARY_PATH": KERNEL_STORE_CPU})
        finally:
            os.unlink(path)
        if r.returncode != 0:
            raise RuntimeError(f"llama-embedding rc={r.returncode}: {r.stderr[-300:]}")
        data = json.loads(r.stdout)["data"]
        if len(data) != len(chunk):
            raise RuntimeError(f"llama-embedding returned {len(data)} vectors for {len(chunk)} docs")
        out += [d["embedding"] for d in sorted(data, key=lambda d: d["index"])]
    return out


def make_embedder(gguf: str = DEFAULT_GGUF):
    def embed(docs: list[dict]):
        import numpy as np
        X = np.asarray(embed_texts([d["text"] for d in docs], gguf), dtype=np.float32)
        n = np.linalg.norm(X, axis=1, keepdims=True)
        n[n == 0] = 1.0
        return X / n
    return embed
