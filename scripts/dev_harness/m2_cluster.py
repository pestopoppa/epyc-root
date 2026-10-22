#!/usr/bin/env python3
"""DHM-7.2 — no-LLM failure-clustering baseline over tool-error and denial segments.

One document per AgentRun segment that holds a tool error or a denial: the failing tool names
plus each error text, normalised (paths, numbers, hex, uuids masked). Features are signed-hashed
word unigrams+bigrams (D=1024) with TF-IDF weighting and L2 norm — the CPU "sentence embedding"
of this baseline is this hashed TF-IDF vector: no model, no server, no inference, deterministic.
(A neural CPU embedder is a later drop-in: ``embed()`` is the only function to replace; the host's
/usr/bin/python3 has no onnxruntime/sentence-transformers.) Spherical k-means (k-means++ init,
fixed seed).

Validation by PLANTED RECOVERY: synthetic documents of known incident classes (refusal text of the
pattern-kill, filesystem-containment, pytest-workers, wholesale-git-add and git-stash guards, with
randomised paths and numbers) are added across synthetic sessions/days; a class is recovered when
>= 75% of its planted docs land in one cluster AND >= 75% of the planted docs in that cluster are of
that class (two incident classes merged into one cluster are not both "recovered"). Planted docs never appear in reported clusters.

A cluster is REPORTED only with >= 3 distinct sessions and >= 2 distinct days (DHM-7 rule).
Facets are mechanical: harness / source / tool / denial-class mixes and log-odds top terms.
"""
from __future__ import annotations

import math
import random
import re
import zlib
from collections import Counter, defaultdict

from m2_common import Unit

D = 1024
MIN_SESSIONS, MIN_DAYS = 3, 2
_NORM = [
    (re.compile(r"…\[truncated \d+ chars\]"), " "),
    (re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I), " uuid "),
    (re.compile(r"(?:~|\.{0,2})?/[\w.@+-]+(?:/[\w.@+-]*)+"), " path "),
    (re.compile(r"\b[0-9a-f]{7,40}\b"), " hex "),
    (re.compile(r"\d+(?:\.\d+)?"), " num "),
]
_TOK = re.compile(r"[a-z_][a-z_-]{1,30}")

PLANTED = {
    "pattern_kill": "BLOCKED: pkill against a NAME PATTERN. This is a shared host, so a name pattern is a wildcard "
                    "over other sessions' processes. Kill only PIDs you captured: kill {n}. pkill -f llama-server {p}",
    "fs_containment": "BLOCKED: filesystem containment (INC-20260823). write_outside_containment_root: path '{p}' is "
                      "outside the containment root. Allowed: /mnt/raid0/llm/**, /workspace/**",
    "pytest_workers": "BLOCKED: pytest -n auto would spawn ~{n} workers and crash this machine. Use -n 8 (default) "
                      "or -n 4. command: pytest -n auto {p}",
    "wholesale_add": "BLOCKED: wholesale `git add` on a shared repo ({p}). Stage only your paths: "
                     "git add path/one path/two; {n} other files carry uncommitted work",
    "git_stash": "BLOCKED: `git stash` in a shared repo ({p}). stash captures UNTRACKED files too, and the runtime "
                 "plane gains files between your stash and your pop ({n} untracked)",
}


def normalise(text: str) -> str:
    t = (text or "")[:1500].lower()
    for rx, rep in _NORM:
        t = rx.sub(rep, t)
    return t


def tokens(text: str) -> list[str]:
    toks = _TOK.findall(normalise(text))
    return toks + [a + "_" + b for a, b in zip(toks, toks[1:])]


def segment_docs(u: Unit) -> list[dict]:
    """One doc per segment with a tool error or denial."""
    by_seg: dict = defaultdict(list)
    calls = {c.tool_call_id: c for c in u.calls if c.tool_call_id}
    for m, seg in zip(u.messages, u.seg_of):
        if m.get("role") != "tool" or not m.get("error"):
            continue
        err = m["error"]
        fn = m.get("function") or (calls.get(m.get("tool_call_id")) or type("x", (), {"function": "?"})).function
        body = m.get("content") if isinstance(m.get("content"), str) and m.get("content") else err.get("message")
        by_seg[seg].append((fn or "?", err.get("type") or "tool_error", (body or "")[:1500]))
    docs = []
    for seg, errs in by_seg.items():
        row = next((r for r in u.rows if r.get("segment_index") == seg), u.rows[0])
        docs.append({"id": row.get("id") or f"{u.unit_key}:{seg}", "session": u.unit_key, "harness": u.harness,
                     "source": u.source, "day": row.get("day") or (row.get("first_ts") or "")[:10],
                     "tools": Counter(e[0] for e in errs), "etypes": Counter(e[1] for e in errs),
                     "text": " \n ".join(f"{fn} {msg}" for fn, _, msg in errs)[:4000]})
    return docs


def planted_docs(per_class: int = 12, seed: int = 7) -> list[dict]:
    rnd = random.Random(seed)
    out = []
    for cls, tpl in PLANTED.items():
        for i in range(per_class):
            p = "/" + "/".join(rnd.choice(["mnt", "raid0", "llm", "tmp", "work", "repo", "x" + str(rnd.randint(1, 99))])
                               for _ in range(rnd.randint(2, 5)))
            out.append({"id": f"planted:{cls}:{i}", "session": f"planted-{cls}-{i % 4}", "harness": "planted",
                        "source": "planted", "day": f"2026-01-0{1 + i % 3}", "planted": cls,
                        "tools": Counter({"Bash": 1}), "etypes": Counter({"denial:hook_block": 1}),
                        "text": "Bash " + tpl.format(p=p, n=rnd.randint(2, 900))})
    return out


def embed(docs: list[dict]):
    import numpy as np
    n = len(docs)
    X = np.zeros((n, D), dtype=np.float32)
    df = np.zeros(D, dtype=np.float32)
    for i, d in enumerate(docs):
        for t in tokens(d["text"]):
            h = zlib.crc32(t.encode())
            X[i, h % D] += 1.0 if (h >> 16) & 1 else -1.0
        df += (X[i] != 0)
    idf = np.log((1 + n) / (1 + df)) + 1.0
    X = np.sign(X) * np.log1p(np.abs(X)) * idf
    norms = np.linalg.norm(X, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return X / norms


def kmeans(X, k: int, iters: int = 40, seed: int = 0):
    import numpy as np
    rng = np.random.default_rng(seed)
    n = X.shape[0]
    centers = [X[rng.integers(n)]]
    dist = 1.0 - X @ centers[0]
    for _ in range(1, k):
        p = np.clip(dist, 0, None) ** 2
        s = p.sum()
        idx = rng.integers(n) if s <= 0 else rng.choice(n, p=p / s)
        centers.append(X[idx])
        dist = np.minimum(dist, 1.0 - X @ X[idx])
    C = np.stack(centers)
    labels = np.zeros(n, dtype=int)
    for _ in range(iters):
        new = np.argmax(X @ C.T, axis=1)
        if _ and (new == labels).all():
            break
        labels = new
        for j in range(k):
            members = X[labels == j]
            if len(members):
                c = members.sum(axis=0)
                nrm = np.linalg.norm(c)
                C[j] = c / nrm if nrm else C[j]
    return labels


def run(docs: list[dict], k: int | None = None, seed: int = 0, embedder=None) -> tuple[dict, list[dict]]:
    """Returns (aggregate counts tree, per-doc membership rows). `embedder(docs) -> L2-normalised matrix`
    replaces the hashed TF-IDF (see m2_embed_gguf.make_embedder)."""
    plant = planted_docs()
    alldocs = docs + plant
    if len(alldocs) < 4:
        return {"status_too_few_docs": 1, "n_docs": len(docs)}, []
    k = k or max(len(PLANTED) + 2, min(80, round(math.sqrt(len(alldocs) / 2))))
    X = (embedder or embed)(alldocs)
    labels = kmeans(X, k, seed=seed)
    members = defaultdict(list)
    for d, lab in zip(alldocs, labels):
        members[int(lab)].append(d)
    recovery = {}
    for cls in PLANTED:
        where = Counter(int(lab) for d, lab in zip(alldocs, labels) if d.get("planted") == cls)
        top, cnt = where.most_common(1)[0]
        size = len(members[top])
        planted_there = [d["planted"] for d in members[top] if d.get("planted")]
        share = cnt / sum(where.values())
        separation = planted_there.count(cls) / len(planted_there)
        recovery[cls] = {"share_in_best_cluster": round(share, 3),
                         "best_cluster_purity": round(planted_there.count(cls) / size, 3),
                         "separation_from_other_planted": round(separation, 3),
                         "recovered": int(share >= 0.75 and separation >= 0.75)}
    gtok = Counter()
    ctok: dict = {}
    for j, ds in members.items():
        c = Counter()
        for d in ds:
            if not d.get("planted"):
                c.update(set(tokens(d["text"])))
        ctok[j] = c
        gtok.update(c)
    gtot = sum(gtok.values()) or 1
    clusters, reported = {}, 0
    rows = []
    for j in sorted(members):
        real = [d for d in members[j] if not d.get("planted")]
        sessions = {d["session"] for d in real}
        days = {d["day"] for d in real if d["day"]}
        ok = len(sessions) >= MIN_SESSIONS and len(days) >= MIN_DAYS
        for d in real:
            rows.append({"id": d["id"], "session": d["session"], "harness": d["harness"], "source": d["source"],
                         "day": d["day"], "cluster": j, "reported": ok})
        if not ok:
            continue
        reported += 1
        ctot = sum(ctok[j].values()) or 1
        lo = {t: math.log((n + 0.5) / ctot) - math.log((gtok[t] + 0.5) / gtot)
              for t, n in ctok[j].items() if n >= 2}
        top_terms = sorted(lo, key=lambda t: -lo[t])[:8]
        cnt = lambda key: dict(sum((d[key] for d in real), Counter()).most_common(6))  # noqa: E731
        clusters[f"c{j:02d}"] = {
            "n_docs": len(real), "n_sessions": len(sessions), "n_days": len(days),
            "harness": dict(Counter(d["harness"] for d in real)), "source": dict(Counter(d["source"] for d in real)),
            "tool": {"tool:" + t: n for t, n in cnt("tools").items()},
            "error_type": cnt("etypes"),
            "top_terms": {"t:" + t: round(lo[t], 3) for t in top_terms},
            "planted_in_cluster": sum(1 for d in members[j] if d.get("planted")),
        }
    agg = {"n_docs": len(docs), "n_planted": len(plant), "k": k, "clusters_total": len(members),
           "clusters_reported": reported, "reported_doc_share": round(
               sum(c["n_docs"] for c in clusters.values()) / len(docs), 4) if docs else 0,
           "planted_recovery": recovery,
           "planted_recovered": sum(r["recovered"] for r in recovery.values()),
           "clusters": clusters}
    return agg, rows
