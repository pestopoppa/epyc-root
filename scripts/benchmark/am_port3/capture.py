#!/usr/bin/env python3
"""Read bounded native captures and compare their output to a numpy oracle.

This is a capture-integrity diagnostic, not the compact-cache cosine gate.
"""
import argparse
import json
from pathlib import Path

import numpy as np

from fit import digest


def load_layer(directory, layer):
    directory = Path(directory)
    complete = json.loads((directory / 'COMPLETE.json').read_text())
    if complete.get('schema') != 'epyc.am.native-capture.v1' or layer not in complete['layers']:
        raise ValueError('capture is incomplete or does not contain requested layer')
    path = directory / f'layer-{layer}.json'
    meta = json.loads(path.read_text())
    if meta.get('schema') != 'epyc.am.native-layer.v1' or meta.get('layer') != layer:
        raise ValueError('layer manifest mismatch')
    tensors, hashes = {}, {path.name: digest(path), 'COMPLETE.json': digest(directory / 'COMPLETE.json')}
    for name, desc in meta['tensors'].items():
        if name not in ('Q', 'K', 'V', 'mask', 'output'):
            raise ValueError('unknown capture tensor')
        ne = desc['ne']
        if len(ne) != 4 or any(type(n) is not int or n <= 0 for n in ne):
            raise ValueError('invalid tensor dimensions')
        # Capture files are siblings; never follow a manifest outside its directory.
        filename = desc['file']
        if filename != f'layer-{layer}-{name}.f32' or (directory / filename).is_symlink():
            raise ValueError('invalid tensor path')
        tensor_path = directory / filename
        expected = 4
        for n in ne:
            expected *= n
        if expected > 4 * 1024**3 or tensor_path.stat().st_size != expected:
            raise ValueError('tensor byte count mismatch or budget exceeded')
        a = np.fromfile(tensor_path, dtype='<f4').reshape(tuple(reversed(ne)))
        if name == 'mask':
            if np.isnan(a).any() or np.isposinf(a).any():
                raise ValueError('invalid mask values')
        elif not np.isfinite(a).all():
            raise ValueError('nonfinite capture values')
        tensors[name] = a
        hashes[filename] = digest(tensor_path)
    if not {'Q', 'K', 'V', 'output'} <= tensors.keys():
        raise ValueError('missing attention tensors')
    return meta, tensors, hashes


def check_layer(directory, layer):
    meta, t, hashes = load_layer(directory, layer)
    q, k, v, actual = (t[name].astype(np.float64) for name in ('Q', 'K', 'V', 'output'))
    if any(x.shape[0] != 1 for x in (q, k, v, actual)):
        raise ValueError('only one stream is supported')
    q, k, v, actual = q[0], k[0], v[0], actual[0]
    if (k.shape[:2] != v.shape[:2] or q.shape[2] != k.shape[2]
            or q.shape[0] % k.shape[0] or actual.shape != (q.shape[1], q.shape[0], v.shape[2])):
        raise ValueError('incompatible attention geometry')
    scale = meta['attention_scale']
    if not np.isfinite(scale) or scale <= 0:
        raise ValueError('invalid graph attention scale')
    repeats = q.shape[0] // k.shape[0]
    k, v = np.repeat(k, repeats, axis=0), np.repeat(v, repeats, axis=0)
    scores = np.einsum('hnd,htd->hnt', q, k) * scale
    if 'mask' in t:
        mask = t['mask']
        if mask.shape[:2] != (1, 1) or mask.shape[2] < q.shape[1] or mask.shape[3] != k.shape[1]:
            raise ValueError('incompatible mask geometry')
        scores += mask[0, 0, :q.shape[1], :]
    if not np.isfinite(scores.max(axis=2)).all():
        raise ValueError('fully masked captured query')
    weights = np.exp(scores - scores.max(axis=2, keepdims=True))
    weights /= weights.sum(axis=2, keepdims=True)
    reference = np.einsum('hnt,htd->nhd', weights, v)
    error = np.linalg.norm(actual - reference)
    return {'layer': layer, 'sha256': hashes,
            'native_vs_numpy_relative_l2': float(error / max(np.linalg.norm(reference), 1e-30)),
            'native_vs_numpy_max_abs': float(np.max(np.abs(actual - reference))),
            'query_heads': q.shape[0], 'kv_heads': q.shape[0] // repeats,
            'queries': q.shape[1], 'kv_rows_including_padding': k.shape[1]}


def check(directory):
    complete = json.loads((Path(directory) / 'COMPLETE.json').read_text())
    layers = complete['layers']
    if not layers or len(set(layers)) != len(layers) or any(type(x) is not int or x < 0 for x in layers):
        raise ValueError('invalid completed layer set')
    return {'schema': 'epyc.am.capture-check.v1',
            'scope': 'capture integrity only; not compact-cache quality or decode',
            'checker_sha256': digest(__file__),
            'layers': [check_layer(directory, layer) for layer in layers]}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', required=True, help='completed native capture directory')
    args = parser.parse_args()
    print(json.dumps(check(args.check), indent=2, allow_nan=False))
