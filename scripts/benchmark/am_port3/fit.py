#!/usr/bin/env python3
"""Offline AM fit for ONE layer/KV-head shard; never opens a model or server.

K and Q must be in the same post-RoPE coordinates used by native attention.
Grouped query heads may be pooled along Q's row axis. The caller supplies the
same retained position indices to every shard: native KV cells share positions.
The fast beta solve is log(clamped least squares), not an iterative NNLS solver.
See README.md for the capture contract and limits of this offline diagnostic.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def matrix(value, name):
    a = np.asarray(value, dtype=np.float64)
    if a.ndim != 2 or not all(a.shape) or not np.isfinite(a).all():
        raise ValueError(f'{name} must be a nonempty finite matrix')
    return a


def selected_indices(value, size):
    a = np.asarray(value)
    if (a.ndim != 1 or not a.size or a.dtype.kind not in 'iu'
            or np.any(a < 0) or np.any(a >= size) or np.any(np.diff(a.astype(np.int64)) <= 0)):
        raise ValueError('indices must be sorted unique integers in the cache range')
    return a.astype(np.int64)


def weights(q, k, scale, bias=None):
    scores = q @ k.T * scale
    if bias is not None:
        b = np.asarray(bias, dtype=np.float64)
        if b.shape not in ((k.shape[0],), scores.shape):
            raise ValueError('bias must have shape (tokens,) or (queries,tokens)')
        if np.isnan(b).any() or np.isposinf(b).any():
            raise ValueError('bias may contain only finite values or negative infinity')
        scores += b
    if not np.isfinite(scores.max(axis=1)).all():
        raise ValueError('each query must attend at least one finite key')
    exp = np.exp(scores - scores.max(axis=1, keepdims=True))
    return exp, exp / exp.sum(axis=1, keepdims=True)


def fit(k, v, queries, indices, scale, bias=None):
    """Return beta[t], rewritten V[t,dv], and fit diagnostics, in float32.

    Matches attention_matching.py's unregularized fast path, using float64 SVD
    internally to handle rank-deficient calibration matrices deterministically.
    Bias is the full-cache additive mask; compact attention uses beta alone,
    matching the reference. Calibration must describe the intended decode view.
    """
    k, v, q = matrix(k, 'K'), matrix(v, 'V'), matrix(queries, 'Q')
    if k.shape[0] != v.shape[0] or q.shape[1] != k.shape[1]:
        raise ValueError('K/V token counts and K/Q key dimensions must agree')
    if not np.isfinite(scale) or scale <= 0:
        raise ValueError('scale must be positive and finite')
    ix = selected_indices(indices, len(k))
    exp, full = weights(q, k, scale, bias)
    mass = exp.sum(axis=1)
    b, _, rank_beta, _ = np.linalg.lstsq(exp[:, ix], mass, rcond=None)
    beta = np.log(np.maximum(b, 1e-12))
    _, compact = weights(q, k[ix], scale, beta)
    c2, _, rank_values, _ = np.linalg.lstsq(compact, full @ v, rcond=None)
    beta, c2 = beta.astype(np.float32), c2.astype(np.float32)
    if not np.isfinite(beta).all() or not np.isfinite(c2).all():
        raise ValueError('fit cannot be represented in finite float32')
    return beta, c2, {'beta_rank': int(rank_beta), 'value_rank': int(rank_values),
                     'clamped_beta_count': int(np.sum(b < 1e-12)),
                     'fit_queries': len(q), 'original_tokens': len(k), 'kept_tokens': len(ix)}


def evaluate(k, v, queries, indices, beta, c2, scale, bias=None):
    """Evaluate held-out attention output using the actual float32 carrier."""
    k, v, q = matrix(k, 'K'), matrix(v, 'V'), matrix(queries, 'Q_eval')
    ix = selected_indices(indices, len(k))
    beta, c2 = np.asarray(beta, dtype=np.float64), matrix(c2, 'C2')
    if (v.shape[0] != len(k) or q.shape[1] != k.shape[1]
            or beta.shape != (len(ix),) or not np.isfinite(beta).all()
            or c2.shape != (len(ix), v.shape[1]) or not np.isfinite(scale) or scale <= 0):
        raise ValueError('incompatible or nonfinite evaluation carrier')
    _, full = weights(q, k, scale, bias)
    _, compact = weights(q, k[ix], scale, beta)
    expected, actual = full @ v, compact @ c2
    denom = np.linalg.norm(expected, axis=1) * np.linalg.norm(actual, axis=1)
    # Zero output has no directional cosine; do not silently grade it as 1.
    valid = denom > 0
    cos = np.sum(expected * actual, axis=1)[valid] / denom[valid]
    return {'queries': len(q), 'undefined_cosines': int(np.sum(~valid)),
            'cosine_mean': float(np.clip(cos, -1, 1).mean()) if cos.size else None,
            'cosine_min': float(np.clip(cos, -1, 1).min()) if cos.size else None,
            'relative_l2': float(np.linalg.norm(actual - expected) /
                                 max(np.linalg.norm(expected), 1e-30))}


def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def run(capture, metadata, out):
    """Consume an immutable per-head NPZ and emit a content-bound fit package."""
    meta = json.loads(Path(metadata).read_text())
    required = ('source_commit', 'model_identity', 'capture_id', 'layer', 'kv_head',
                'attention_scale', 'coordinates', 'capture_sha256')
    if any(key not in meta for key in required):
        raise ValueError('capture metadata is incomplete')
    if any(type(meta[key]) is not int or meta[key] < 0 for key in ('layer', 'kv_head')):
        raise ValueError('layer and kv_head must be nonnegative integers')
    if any(not isinstance(meta[key], str) or not meta[key].strip()
           for key in ('source_commit', 'model_identity', 'capture_id')):
        raise ValueError('capture identity fields must be nonempty strings')
    if meta['coordinates'] != 'post_rope' or meta['capture_sha256'] != digest(capture):
        raise ValueError('capture coordinates or digest mismatch')
    with np.load(capture, allow_pickle=False) as z:
        # IDs encode (sequence, position, query head). Fit/eval leakage is refused.
        fit_ids, eval_ids = z['fit_ids'], z['eval_ids']
        for ids, q in ((fit_ids, z['Q_fit']), (eval_ids, z['Q_eval'])):
            if ids.ndim != 1 or ids.dtype.kind not in 'US' or len(ids) != len(q):
                raise ValueError('query IDs must be a string vector matching query count')
            if len(set(ids.tolist())) != len(ids):
                raise ValueError('duplicate query IDs')
        if set(fit_ids.tolist()) & set(eval_ids.tolist()):
            raise ValueError('fit/eval query IDs overlap')
        scale = float(meta['attention_scale'])
        beta, c2, diag = fit(z['K'], z['V'], z['Q_fit'], z['indices'], scale,
                            z['bias_fit'] if 'bias_fit' in z else None)
        heldout = evaluate(z['K'], z['V'], z['Q_eval'], z['indices'], beta, c2, scale,
                           z['bias_eval'] if 'bias_eval' in z else None)
        out = Path(out)
        out.mkdir(parents=True, exist_ok=False)
        np.savez(out / 'carrier.npz', indices=z['indices'], beta=beta, C2=c2)
    result = {'schema': 'epyc.am.offline-fit.v1', 'capture': meta,
              'metadata_sha256': digest(metadata), 'fitter_sha256': digest(__file__),
              'carrier_sha256': digest(out / 'carrier.npz'), 'fit': diag,
              'heldout': heldout, 'scope': 'offline diagnostic; no native decode verdict'}
    (out / 'FIT.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--capture', required=True)
    p.add_argument('--metadata', required=True)
    p.add_argument('--out', required=True)
    args = p.parse_args()
    run(args.capture, args.metadata, args.out)
