#!/usr/bin/env python3
"""D-LSA capture + PCA tooling for any hybrid (GDN + global attention) Qwen3.x geometry (LSA-MOE-1).

Pure tooling: no llama.cpp is touched or launched here.  Scope (box LSA-MOE-1, long-context-program.md):

  * frozen-teacher capture: a streaming worker speaking the experimental LSA worker protocol
    (header "=III" n_query n_kv layer, then q f32, k f32, mask f32; reply "=i" status + mask f32),
    so it can be dropped in where `experiments/lsa-screen/mask_worker.py` runs; plus an `ingest`
    path for q/k dumps.  It accumulates RoPE-free key statistics per global layer and can also
    emit the dense-attention teacher (per-head softmax averaged over heads, top-k) for sampled queries.
  * exact GQA / head aggregation (`group_sum_queries`, `flatten_keys`) and RoPE-free coordinate
    handling (only head dims [rope_dim:] enter the index; partial RoPE never touches them).
  * model-specific PCA projections (`fit_pca`) written as the released `.pt` layout
    ("<layer>.W_Q_idx" / "<layer>.W_K_idx", float32 [kv_heads*(head_dim-rope_dim), 64]) and as the
    native LSAMAP1 file the experimental loader reads (`write_lsamap`, BF16).

Released-map facts this follows (checked against the 27B step0 map, see test file): W_Q_idx == W_K_idx
(PCA initialises both), columns orthonormal, shape [768, 64] for 24/4/256/rope 64.

NOT here (gated, needs inference): the model-side hook that feeds q/k from a qwen35moe graph, the
bounded paired screen, and the timed distillation pilot.  Never reuse 27B maps on the 35B.
"""
import argparse
import hashlib
import json
import math
import os
import struct
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

INDEX_DIM = 64


@dataclass(frozen=True)
class Geometry:
    name: str
    q_heads: int
    kv_heads: int
    head_dim: int
    rope_dim: int
    layers: tuple

    @property
    def group(self):
        return self.q_heads // self.kv_heads

    @property
    def free(self):
        return self.head_dim - self.rope_dim

    @property
    def rows(self):
        return self.kv_heads * self.free

    def validate(self):
        if self.q_heads % self.kv_heads or not (0 <= self.rope_dim < self.head_dim) or not self.layers:
            raise ValueError(f"bad geometry {self}")


GEOMETRIES = {
    # 48 GDN + 16 global (every 4th layer), released PCA/distilled maps exist
    "qwen38_27b": Geometry("qwen38_27b", 24, 4, 256, 64, tuple(range(3, 64, 4))),
    # Qwen3.6-35B-A3B (arch qwen35moe): 30 GDN + 10 global; GGUF block_count 41 includes one NextN/MTP layer
    # that is NOT a trunk global layer.  full_attention_interval 4, 16/2 heads, key_length 256, rope dim 64.
    "qwen36_35b_a3b": Geometry("qwen36_35b_a3b", 16, 2, 256, 64, tuple(range(3, 40, 4))),
}


def geometry_from_gguf(path, gguf_py="/mnt/raid0/llm/llama.cpp/gguf-py"):
    """Derive the geometry from GGUF metadata (read-only) so a hand table cannot drift from the file."""
    sys.path.insert(0, gguf_py)
    from gguf import GGUFReader  # noqa: E402

    r = GGUFReader(path, "r")
    arch = bytes(r.fields["general.architecture"].parts[-1]).decode()

    def val(key, default=None):
        f = r.fields.get(f"{arch}.{key}")
        if f is None:
            if default is None:
                raise KeyError(f"{arch}.{key}")
            return default
        return f.parts[f.data[0]].tolist()[0]

    nl = int(val("block_count"))
    nextn = int(val("nextn_predict_layers", 0))
    interval = int(val("full_attention_interval", 1))
    layers = tuple(i for i in range(nl - nextn) if (i + 1) % interval == 0)
    g = Geometry(arch, int(val("attention.head_count")), int(val("attention.head_count_kv")),
                 int(val("attention.key_length")), int(val("rope.dimension_count")), layers)
    g.validate()
    return g


# ----------------------------------------------------------------------------------------------
# GQA / RoPE-free coordinates

def group_sum_queries(q, geom):
    """q [T, q_heads, head_dim] -> [T, kv_heads*free]: sum the `group` query heads that share a KV head
    (head h belongs to kv head h // group, contiguous groups as in llama.cpp / the reference), over the
    RoPE-free dims only.  Summation is exact (float64); projection after it equals the sum of per-head
    projections because the map is linear."""
    q = np.asarray(q)
    if q.ndim != 3 or q.shape[1:] != (geom.q_heads, geom.head_dim):
        raise ValueError(f"q shape {q.shape} != [T,{geom.q_heads},{geom.head_dim}]")
    free = q[:, :, geom.rope_dim:].astype(np.float64)
    return free.reshape(len(q), geom.kv_heads, geom.group, geom.free).sum(2).reshape(len(q), geom.rows)


def flatten_keys(k, geom):
    """k [T, kv_heads, head_dim] -> [T, kv_heads*free] (RoPE-free dims, kv-head-major)."""
    k = np.asarray(k)
    if k.ndim != 3 or k.shape[1:] != (geom.kv_heads, geom.head_dim):
        raise ValueError(f"k shape {k.shape} != [T,{geom.kv_heads},{geom.head_dim}]")
    return k[:, :, geom.rope_dim:].astype(np.float64).reshape(len(k), geom.rows)


def l2norm(x, eps=1e-30):
    return x / np.maximum(np.linalg.norm(x, axis=-1, keepdims=True), eps)


def index_vectors(q, k, wq, wk, geom):
    """Equation (1) of the paper: q_idx = l2(sum_h q_h W_Q), k_idx = l2(k W_K) on RoPE-free dims."""
    return l2norm(group_sum_queries(q, geom) @ np.asarray(wq, np.float64)), \
        l2norm(flatten_keys(k, geom) @ np.asarray(wk, np.float64))


# ----------------------------------------------------------------------------------------------
# dense teacher (per-head softmax over the causal prefix, averaged over query heads)

def teacher_mass(q, k, position, scale, softcap, geom):
    """q [q_heads, head_dim] (post-RoPE), k [T, kv_heads, head_dim] (post-RoPE).  Returns [position+1].
    Same arithmetic as the 27B `oracle_mass` of the reference branch, generalised to the geometry."""
    q = np.asarray(q, np.float64)
    k = np.asarray(k, np.float64)
    if q.shape != (geom.q_heads, geom.head_dim) or k.ndim != 3 or k.shape[1:] != (geom.kv_heads, geom.head_dim):
        raise ValueError("teacher Q/K geometry")
    if not (0 <= position < len(k)) or not math.isfinite(scale) or scale <= 0 or not math.isfinite(softcap) or softcap < 0:
        raise ValueError("teacher position / scale / softcap")
    kk = k[:position + 1]
    if not (np.isfinite(q).all() and np.isfinite(kk).all()):
        raise ValueError("teacher non-finite Q/K")
    logits = np.einsum("gnd,kgd->gnk", q.reshape(geom.kv_heads, geom.group, geom.head_dim), kk) * scale
    if softcap > 0:
        logits = softcap * np.tanh(logits / softcap)
    logits = logits.reshape(geom.q_heads, position + 1)
    logits -= logits.max(axis=1, keepdims=True)
    p = np.exp(logits)
    p /= p.sum(axis=1, keepdims=True)
    return p.mean(axis=0)


def selection_recall(selected, mass, top=4096):
    """(attention mass held by `selected`, fraction of the oracle's top-`top` keys that `selected` contains)."""
    sel = np.unique(np.asarray(selected, np.int64))
    sel = sel[(sel >= 0) & (sel < len(mass))]
    held = float(mass[sel].sum())
    top = min(top, len(mass))
    oracle = np.argsort(-mass, kind="stable")[:top]
    return held, float(np.isin(oracle, sel).mean())


# ----------------------------------------------------------------------------------------------
# streaming second-moment statistics

class KeyStats:
    """Per-layer streaming sum / sum-of-outer-products of RoPE-free flattened keys (float64)."""

    def __init__(self, geom, split="fit"):
        geom.validate()
        self.geom, self.split = geom, split
        self.n = {l: 0 for l in geom.layers}
        self.s1 = {l: np.zeros(geom.rows) for l in geom.layers}
        self.s2 = {l: np.zeros((geom.rows, geom.rows)) for l in geom.layers}

    def add(self, layer, k):
        if layer not in self.n:
            raise ValueError(f"layer {layer} is not a global layer of {self.geom.name}")
        x = flatten_keys(k, self.geom)
        if not np.isfinite(x).all():
            raise ValueError("non-finite keys")
        self.n[layer] += len(x)
        self.s1[layer] += x.sum(0)
        self.s2[layer] += x.T @ x

    def merge(self, other):
        if other.geom != self.geom:
            raise ValueError("geometry mismatch")
        for l in self.n:
            self.n[l] += other.n[l]
            self.s1[l] += other.s1[l]
            self.s2[l] += other.s2[l]

    def covariance(self, layer, center=True):
        n = self.n[layer]
        if n == 0:
            raise ValueError(f"no keys for layer {layer}")
        c = self.s2[layer] / n
        if center:
            mu = self.s1[layer] / n
            c = c - np.outer(mu, mu)
        return (c + c.T) / 2

    def save(self, path):
        arrs = {"meta": np.frombuffer(json.dumps({"geometry": self.geom.__dict__ | {"layers": list(self.geom.layers)},
                                                   "split": self.split}).encode(), np.uint8)}
        for l in self.geom.layers:
            arrs[f"n_{l}"], arrs[f"s1_{l}"], arrs[f"s2_{l}"] = np.array(self.n[l]), self.s1[l], self.s2[l]
        tmp = f"{path}.tmp.npz"
        np.savez(tmp, **arrs)
        os.replace(tmp, path)

    @classmethod
    def load(cls, path):
        z = np.load(path)
        meta = json.loads(bytes(z["meta"]).decode())
        g = Geometry(**{**meta["geometry"], "layers": tuple(meta["geometry"]["layers"])})
        st = cls(g, meta["split"])
        for l in g.layers:
            st.n[l], st.s1[l], st.s2[l] = int(z[f"n_{l}"]), z[f"s1_{l}"].copy(), z[f"s2_{l}"].copy()
        return st


def fit_pca(stats, center=True, min_keys=None):
    """Return ({layer: W [rows, 64] float32}, {layer: report}).  W has orthonormal columns = the leading
    eigenvectors of the key covariance (centered by default; `center=False` is the raw second moment).
    Eigenvector signs are fixed (largest-magnitude component positive) so runs are reproducible."""
    g = stats.geom
    need = min_keys if min_keys is not None else 4 * g.rows
    maps, report = {}, {}
    for l in g.layers:
        if stats.n[l] < need:
            raise ValueError(f"layer {l}: {stats.n[l]} keys < {need} needed for a stable {g.rows}-d covariance")
        w, v = np.linalg.eigh(stats.covariance(l, center))
        order = np.argsort(-w)[:INDEX_DIM]
        v = v[:, order]
        sign = np.sign(v[np.abs(v).argmax(0), np.arange(INDEX_DIM)])
        sign[sign == 0] = 1
        maps[l] = (v * sign).astype(np.float32)
        tr = float(np.clip(w, 0, None).sum())
        report[l] = {"n_keys": stats.n[l], "explained_variance": float(np.clip(w[order], 0, None).sum() / tr) if tr > 0 else 0.0,
                     "top_eigenvalues": [float(x) for x in w[order][:4]]}
    return maps, report


def heldout_energy(maps, heldout, center=True):
    """Fraction of held-out key variance retained by each layer's projection: tr(W' C W) / tr(C)."""
    out = {}
    for l, w in maps.items():
        c = heldout.covariance(l, center)
        out[l] = float(np.trace(w.T.astype(np.float64) @ c @ w.astype(np.float64)) / np.trace(c))
    return out


def principal_angle_overlap(a, b):
    """Mean squared cosine of the principal angles between the column spaces of a and b (1.0 = same subspace)."""
    qa, _ = np.linalg.qr(np.asarray(a, np.float64))
    qb, _ = np.linalg.qr(np.asarray(b, np.float64))
    s = np.linalg.svd(qa.T @ qb, compute_uv=False)
    return float((s ** 2).mean())


# ----------------------------------------------------------------------------------------------
# map formats

def to_bf16_bits(x):
    """float32 -> bfloat16 bit pattern, round to nearest even (NaN preserved)."""
    u = np.ascontiguousarray(x, np.float32).view(np.uint32)
    nan = (u & 0x7FFFFFFF) > 0x7F800000
    r = (u + 0x7FFF + ((u >> 16) & 1)) >> 16
    return np.where(nan, (u >> 16) | 0x40, r).astype(np.uint16)


def from_bf16_bits(b):
    return (np.asarray(b, np.uint16).astype(np.uint32) << 16).view(np.float32)


def write_lsamap(path, geom, maps_q, maps_k, model_identity, map_identity, source_sha256):
    """LSAMAP1 (experimental loader `llama_lsa_h12::load_lsamap`): header 108 bytes, then payload
    model + identity strings + per layer {u32 layer, bf16 Q[rows*64], bf16 K[rows*64]} row-major."""
    geom.validate()
    if len(source_sha256) != 64:
        raise ValueError("source sha256 must be 64 hex chars")
    mid, iid = model_identity.encode(), map_identity.encode()
    body = bytearray(mid + iid)
    for l in sorted(maps_q):
        for m in (maps_q[l], maps_k[l]):
            if m.shape != (geom.rows, INDEX_DIM):
                raise ValueError(f"layer {l} map shape {m.shape}")
        body += struct.pack("<I", l) + to_bf16_bits(maps_q[l]).tobytes() + to_bf16_bits(maps_k[l]).tobytes()
    head = b"LSAMAP1\0" + struct.pack("<9I", 1, geom.q_heads, geom.kv_heads, geom.head_dim, geom.rope_dim, INDEX_DIM,
                                      len(maps_q), len(mid), len(iid)) \
        + bytes.fromhex(source_sha256) + hashlib.sha256(bytes(body)).digest()
    tmp = f"{path}.tmp"
    Path(tmp).write_bytes(head + bytes(body))
    os.replace(tmp, path)
    return hashlib.sha256(head + bytes(body)).hexdigest()


def read_lsamap(path):
    """Python mirror of the C++ loader, including its payload-hash and size checks."""
    b = Path(path).read_bytes()
    if len(b) < 108 or b[:8] != b"LSAMAP1\0":
        raise ValueError("malformed map header")
    ver, q, kv, d, rope, idx, nl, mlen, ilen = struct.unpack_from("<9I", b, 8)
    if ver != 1 or idx != INDEX_DIM or q % kv or rope >= d:
        raise ValueError("unsupported map geometry")
    source, payload = b[44:76], b[76:108]
    body = b[108:]
    if hashlib.sha256(body).digest() != payload:
        raise ValueError("map payload hash mismatch")
    rows = kv * (d - rope)
    if mlen + ilen + nl * (4 + rows * INDEX_DIM * 4) != len(body):
        raise ValueError("map payload size mismatch")
    at = mlen + ilen
    out = {"q_heads": q, "kv_heads": kv, "head_dim": d, "rope_dim": rope, "model": body[:mlen].decode(),
           "identity": body[mlen:mlen + ilen].decode(), "source_sha256": source.hex(), "layers": {}}
    for _ in range(nl):
        (layer,) = struct.unpack_from("<I", body, at)
        at += 4
        n = rows * INDEX_DIM
        wq = from_bf16_bits(np.frombuffer(body, np.uint16, n, at)).reshape(rows, INDEX_DIM)
        wk = from_bf16_bits(np.frombuffer(body, np.uint16, n, at + 2 * n)).reshape(rows, INDEX_DIM)
        at += 4 * n
        out["layers"][layer] = (wq, wk)
    return out


def write_pt(path, maps):
    """Released-map layout; needs torch (only used for this file format)."""
    import torch

    torch.save({f"{l}.W_{t}_idx": torch.from_numpy(np.ascontiguousarray(w)) for l, w in maps.items() for t in ("Q", "K")}, path)


# ----------------------------------------------------------------------------------------------
# capture worker (experimental LSA worker protocol, geometry generic)

class Capture:
    """Accumulates RoPE-free keys per layer from protocol calls.  Calls resend the whole causal K prefix, so only
    keys beyond what was already seen for the current document are added; a call whose first query is at position 0
    after keys were seen starts a new document.  Keeps the dense mask untouched (capture runs dense)."""

    def __init__(self, geom, split, teacher_dir=None, teacher_queries=0, scale=None, softcap=0.0, top=2048, seed=0):
        self.stats = {"fit": KeyStats(geom, "fit"), "heldout": KeyStats(geom, "heldout")}
        self.geom, self.split = geom, split
        self.seen = {l: 0 for l in geom.layers}
        self.calls, self.seconds = 0, 0.0
        self.teacher_dir, self.teacher_queries, self.scale, self.softcap, self.top = teacher_dir, teacher_queries, scale, softcap, top
        self.rng = np.random.default_rng(seed)
        self.teacher_rows = {l: [] for l in geom.layers}

    @staticmethod
    def positions(mask):
        pos = []
        for row in mask:
            ok = np.isfinite(row)
            n = int(ok.sum())
            if n == 0 or not ok[:n].all() or ok[n:].any() or (row[ok] != 0).any():
                raise ValueError("capture requires one contiguous causal sequence starting at slot zero")
            pos.append(n - 1)
        return pos

    def feed(self, q, k, mask, layer):
        t0 = time.time()
        g = self.geom
        q = np.asarray(q, np.float32).reshape(-1, g.q_heads, g.head_dim)
        k = np.asarray(k, np.float32).reshape(-1, g.kv_heads, g.head_dim)
        pos = self.positions(np.asarray(mask).reshape(len(q), len(k)))
        if layer not in self.seen:
            raise ValueError(f"layer {layer} is not a global layer of {g.name}")
        if min(pos) == 0 and self.seen[layer] > 0:
            self.seen[layer] = 0
        end = max(pos) + 1
        if end > self.seen[layer]:
            self.stats[self.split].add(layer, k[self.seen[layer]:end])
            self.seen[layer] = end
        if self.teacher_queries and self.scale:
            for r in self.rng.permutation(len(pos))[: self.teacher_queries]:
                mass = teacher_mass(q[r], k, pos[r], self.scale, self.softcap, g)
                top = np.argsort(-mass, kind="stable")[: self.top]
                self.teacher_rows[layer].append((pos[r], top.astype(np.int32), (mass[top] / mass[top].sum()).astype(np.float32)))
        self.calls += 1
        self.seconds += time.time() - t0

    def save(self, out_dir):
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        for s, st in self.stats.items():
            if any(st.n.values()):
                st.save(str(out / f"keystats-{s}.npz"))
        if self.teacher_dir:
            for l, rows in self.teacher_rows.items():
                if rows:
                    np.savez_compressed(Path(self.teacher_dir) / f"teacher-L{l}.npz", pos=np.array([r[0] for r in rows]),
                                        idx=np.stack([np.pad(r[1], (0, self.top - len(r[1])), constant_values=-1) for r in rows]),
                                        mass=np.stack([np.pad(r[2], (0, self.top - len(r[2]))) for r in rows]))
        (out / "capture-timing.json").write_text(json.dumps({"calls": self.calls, "seconds": self.seconds,
                                                              "keys": {s: sum(st.n.values()) for s, st in self.stats.items()}}))


def _read_exact(stream, n):
    chunks = []
    while n:
        part = stream.read(n)
        if not part:
            raise EOFError("short worker input")
        chunks.append(part)
        n -= len(part)
    return b"".join(chunks)


def serve(cap, out_dir, inp=None, out=None):
    inp, out = inp or sys.stdin.buffer, out or sys.stdout.buffer
    g = cap.geom
    while True:
        header = inp.read(12)
        if not header:
            cap.save(out_dir)
            return
        try:
            if len(header) != 12:
                raise EOFError("short worker header")
            nq, nk, layer = struct.unpack("=III", header)
            if not nq or not nk or nq > nk or layer not in g.layers:
                raise ValueError("invalid worker dimensions or layer")
            raw = _read_exact(inp, (nq * g.q_heads * g.head_dim + nk * g.kv_heads * g.head_dim + nq * nk) * 4)
            f = np.frombuffer(raw, np.float32)
            qe, ke = nq * g.q_heads * g.head_dim, nq * g.q_heads * g.head_dim + nk * g.kv_heads * g.head_dim
            mask = f[ke:].reshape(nq, nk)
            cap.feed(f[:qe], f[qe:ke], mask, layer)
            out.write(struct.pack("=i", 0) + mask.tobytes())
            out.flush()
        except Exception as exc:  # protocol: report and stop, like the reference worker
            print(f"LSA capture worker: {exc}", file=sys.stderr, flush=True)
            out.write(struct.pack("=i", -1))
            out.flush()
            cap.save(out_dir)
            return


# ----------------------------------------------------------------------------------------------
# CLI

def _geom(name):
    return GEOMETRIES[name]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("serve", help="capture worker on stdin/stdout")
    s.add_argument("--geometry", default="qwen36_35b_a3b", choices=GEOMETRIES)
    s.add_argument("--out", required=True)
    s.add_argument("--split", default=os.environ.get("LSA_CAPTURE_SPLIT", "fit"), choices=("fit", "heldout"))
    s.add_argument("--teacher-queries", type=int, default=0, help="sampled query rows per call to keep a dense teacher for")
    s.add_argument("--scale", type=float, default=None, help="attention scale (1/sqrt(head_dim) normally)")
    s.add_argument("--softcap", type=float, default=0.0)
    i = sub.add_parser("ingest", help="accumulate key stats from .npz dumps with arrays k[T,kv,hd] and layer")
    i.add_argument("--geometry", default="qwen36_35b_a3b", choices=GEOMETRIES)
    i.add_argument("--out", required=True)
    i.add_argument("--split", default="fit", choices=("fit", "heldout"))
    i.add_argument("dumps", nargs="+")
    f = sub.add_parser("fit", help="keystats -> PCA maps (.pt and LSAMAP1) + report")
    f.add_argument("--fit-stats", required=True)
    f.add_argument("--heldout-stats")
    f.add_argument("--out", required=True)
    f.add_argument("--no-center", action="store_true")
    f.add_argument("--model-identity", required=True)
    f.add_argument("--no-pt", action="store_true")
    a = ap.parse_args(argv)

    if a.cmd == "serve":
        os.makedirs(a.out, exist_ok=True)
        serve(Capture(_geom(a.geometry), a.split, a.out if a.teacher_queries else None, a.teacher_queries, a.scale, a.softcap), a.out)
    elif a.cmd == "ingest":
        st = KeyStats(_geom(a.geometry), a.split)
        for d in a.dumps:
            z = np.load(d)
            st.add(int(z["layer"]), z["k"])
        os.makedirs(a.out, exist_ok=True)
        st.save(os.path.join(a.out, f"keystats-{a.split}.npz"))
    elif a.cmd == "fit":
        fit = KeyStats.load(a.fit_stats)
        maps, rep = fit_pca(fit, center=not a.no_center)
        os.makedirs(a.out, exist_ok=True)
        if a.heldout_stats:
            for l, e in heldout_energy(maps, KeyStats.load(a.heldout_stats), not a.no_center).items():
                rep[l]["heldout_retained_variance"] = e
        src = hashlib.sha256(Path(a.fit_stats).read_bytes()).hexdigest()
        ident = f"pca-{'raw' if a.no_center else 'centered'}-src{src[:12]}"
        digest = write_lsamap(os.path.join(a.out, "pca.lsamap"), fit.geom, maps, maps, a.model_identity, ident, src)
        if not a.no_pt:
            write_pt(os.path.join(a.out, "pca.pt"), maps)
        Path(a.out, "pca-report.json").write_text(json.dumps({"geometry": fit.geom.name, "identity": ident, "lsamap_sha256": digest,
                                                              "layers": rep}, indent=1))
        print(digest)


if __name__ == "__main__":
    main()
