#!/usr/bin/env python3
"""Native reload integrity and frozen-prefix quality on actual reload queries.

This is conditional on the compact trajectory's Q, not an end-to-end full-model
baseline. The actual native output includes the newly appended key/value; the
prefix-only quality calculation excludes it on BOTH sides.
"""
import argparse
import json
from pathlib import Path

import numpy as np

from capture import load_layer, reference
from convert import provenance
from fit import digest, weights


def inputs(original, converted):
    original, converted = Path(original), Path(converted)
    record = json.loads((converted / 'CONVERT.json').read_text())
    p, layers = provenance(original.parent / 'PROVENANCE.json', original)
    if (record.get('schema') != 'epyc.am.converted-prefix.v1'
            or record['provenance'] != p
            or record['provenance_sha256'] != digest(original.parent / 'PROVENANCE.json')
            or record['carrier_sha256'] != digest(converted / 'carrier.bin')):
        raise ValueError('original capture/conversion binding mismatch')
    return record, p, layers


def metrics(actual, expected):
    a, b = np.asarray(actual, dtype=np.float64), np.asarray(expected, dtype=np.float64)
    na, nb = np.linalg.norm(a, axis=-1), np.linalg.norm(b, axis=-1)
    valid = (na > 0) & (nb > 0)
    cos = np.sum(a*b, axis=-1)[valid] / (na[valid]*nb[valid])
    return {'relative_l2': float(np.linalg.norm(a-b) / max(np.linalg.norm(b), 1e-30)),
            'max_abs': float(np.max(np.abs(a-b))),
            'cosine_mean': float(np.mean(cos)) if cos.size else None,
            'cosine_min': float(np.min(cos)) if cos.size else None,
            'undefined_cosines': int(np.size(valid) - np.sum(valid))}


def check(original, converted, reloaded):
    original, converted, reloaded = map(Path, (original, converted, reloaded))
    record, p, layers = inputs(original, converted)
    cp = json.loads((reloaded / 'COMPACT.json').read_text())
    if (cp.get('schema') != 'epyc.am.compact-provenance.v1'
            or any(cp.get(k) != p[k] for k in ('source_commit', 'model_identity', 'capture_id'))
            or cp.get('query_positions') != [p['prefix_tokens']]
            or cp.get('conversion_sha256') != digest(converted / 'CONVERT.json')
            or cp.get('complete_sha256') != digest(reloaded / 'native' / 'COMPLETE.json')):
        raise ValueError('compact capture binding mismatch')
    complete = json.loads((reloaded / 'native' / 'COMPLETE.json').read_text())
    if complete.get('layers') != layers:
        raise ValueError('compact layer coverage mismatch')
    rows = cp.get('cache_row_positions')
    positions = record['positions']
    if (not isinstance(rows, list) or len(rows) > 36864
            or any(type(x) is not int or x < -1 for x in rows)
            or sorted(x for x in rows if x >= 0) != sorted(positions + [p['prefix_tokens']])):
        raise ValueError('compact physical row map mismatch')
    physical = np.array([rows.index(pos) for pos in positions])
    original_rows = p['cache_row_positions']
    full_rows = np.array([original_rows.index(pos) for pos in range(p['prefix_tokens'])])
    selected_full = np.array([original_rows.index(pos) for pos in positions])
    results = []
    for layer in layers:
        meta, full, full_hashes = load_layer(original, layer)
        cm, compact, compact_hashes = load_layer(reloaded / 'native', layer)
        if any(record['native_sha256'].get(k) != v for k, v in full_hashes.items()):
            raise ValueError('original capture content changed after conversion')
        # reference() validates stream/head/output/mask shapes before indexing.
        expected = reference(cm, compact)
        if (cm['attention_scale'] != meta['attention_scale']
                or compact['Q'].shape[2] != 1 or compact['K'].shape[2] != len(rows)
                or compact['K'].shape[1] != full['K'].shape[1]
                or compact['Q'].shape[1] != full['Q'].shape[1]
                or compact['K'].shape[-1] != full['K'].shape[-1]
                or compact['V'].shape[-1] != full['V'].shape[-1]):
            raise ValueError('compact/original geometry or scale mismatch')
        heads = compact['Q'].shape[1]
        group = heads // compact['K'].shape[1]
        if compact['mask'].shape[1] != heads:
            raise ValueError('fitted capture must contain every query-head beta mask')
        prefix_actual, prefix_full = [], []
        for h in range(heads):
            kh = h // group
            fit_dir = converted / f'layer-{layer}-head-{kh}-fit'
            fr = json.loads((fit_dir / 'FIT.json').read_text())
            bound = next(x for x in record['layers'] if x['layer'] == layer and x['kv_head'] == kh)
            if digest(fit_dir / 'FIT.json') != bound['fit_sha256']:
                raise ValueError('fit record content changed')
            with np.load(fit_dir / 'carrier.npz', allow_pickle=False) as carrier:
                # FIT.json binds the actual exported NPZ, not just its declared axes.
                if digest(fit_dir / 'carrier.npz') != fr['carrier_sha256']:
                    raise ValueError('fit carrier content changed')
                if not np.array_equal(carrier['indices'], positions):
                    raise ValueError('fit selection mismatch')
                beta = carrier['beta'].astype(np.float16).astype(np.float32)
                c2 = carrier['C2'].astype(np.float16).astype(np.float32)
            k = compact['K'][0, kh]
            v = compact['V'][0, kh]
            mask = compact['mask'][0, h, 0]
            if (not np.array_equal(k[physical], full['K'][0, kh, selected_full])
                    or not np.array_equal(v[physical], c2)
                    or not np.array_equal(mask[physical], beta)
                    or mask[rows.index(p['prefix_tokens'])] != 0
                    or any(not np.isneginf(mask[r]) for r, pos in enumerate(rows) if pos == -1)):
                raise ValueError('native K/C2/beta or padding differs from fitted carrier')
            q = compact['Q'][0, h].astype(np.float64)
            _, compact_weights = weights(q, k[physical], cm['attention_scale'], mask[physical])
            _, full_weights = weights(q, full['K'][0, kh, full_rows], meta['attention_scale'])
            prefix_actual.append(compact_weights @ v[physical])
            prefix_full.append(full_weights @ full['V'][0, kh, full_rows])
        results.append({'layer': layer, 'native_sha256': compact_hashes,
                        'native_vs_compact_oracle': metrics(compact['output'][0], expected),
                        'frozen_prefix_quality_on_reload_queries': metrics(prefix_actual, prefix_full)})
    return {'schema': 'epyc.am.compact-check.v1', 'checker_sha256': digest(__file__),
            'conversion_sha256': digest(converted / 'CONVERT.json'),
            'compact_provenance_sha256': digest(reloaded / 'COMPACT.json'),
            'scope': 'native output includes appended row; prefix quality excludes it; '
                     'conditional on compact trajectory Q, not full-model logits or 32K stability',
            'layers': results}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ('original', 'converted', 'reloaded'):
        parser.add_argument('--' + arg, required=True)
    a = parser.parse_args()
    print(json.dumps(check(a.original, a.converted, a.reloaded), indent=2, allow_nan=False))
