#!/usr/bin/env python3
"""Convert a bounded native suffix capture into fits of ONE frozen prefix.

Calibration tokens are never included in the fitted cache. The model driver
must restore the prefix recurrent state before pruning/installing this bundle.
"""
import argparse
import json
from pathlib import Path
import struct

import numpy as np

from capture import load_layer
from fit import digest, run


def seal_provenance(driver_out):
    """Bind completed driver OUTPUTS; never hashes model weights or inputs."""
    root = Path(driver_out)
    result = json.loads((root / 'RESULT.json').read_text())
    if result.get('schema') != 'epyc.am.native-driver.v1' or result.get('mode') != 'capture':
        raise ValueError('completed capture driver result required')
    p = json.loads((root / 'PROVENANCE.raw.json').read_text())
    p['prefix_state_sha256'] = digest(root / 'prefix.state')
    p['complete_sha256'] = digest(root / 'native' / 'COMPLETE.json')
    path = root / 'PROVENANCE.json'
    with path.open('x') as f:
        f.write(json.dumps(p, indent=2) + '\n')
    provenance(path, root / 'native')
    return path


def verify_reload(config, converted):
    """Required before invoking the native reload driver; bind state/carrier."""
    record = json.loads((Path(converted) / 'CONVERT.json').read_text())
    if (record.get('schema') != 'epyc.am.converted-prefix.v1' or config.get('mode') != 'reload'
            or digest(config['carrier']) != record['carrier_sha256']
            or digest(config['prefix_state']) != record['provenance']['prefix_state_sha256']
            or any(config.get(k) != record['provenance'][k]
                   for k in ('source_commit', 'model_identity', 'capture_id'))
            or len(config['prefix_tokens']) != record['provenance']['prefix_tokens']):
        raise ValueError('reload content/identity binding mismatch')
    return record


def integers(value, name):
    if (not isinstance(value, list) or not value
            or any(type(x) is not int or x < 0 for x in value)
            or any(a >= b for a, b in zip(value, value[1:]))):
        raise ValueError(name + ' must be sorted unique nonnegative integers')
    return np.asarray(value, dtype=np.int64)


def uniform_selection(size, keep):
    """Deterministic shared selection including first/last original positions."""
    if type(keep) is not int or not 2 <= keep <= size:
        raise ValueError('keep must be between two and the frozen prefix size')
    return np.arange(keep, dtype=np.int64) * (size - 1) // (keep - 1)


def provenance(path, directory):
    p = json.loads(Path(path).read_text())
    if p.get('schema') != 'epyc.am.calibration-provenance.v1' or p.get('sequence') != 0:
        raise ValueError('invalid calibration provenance schema/sequence')
    for key in ('source_commit', 'model_identity', 'capture_id', 'prefix_state_sha256'):
        if not isinstance(p.get(key), str) or not p[key].strip():
            raise ValueError('missing provenance identity: ' + key)
    for key in ('source_commit', 'prefix_state_sha256'):
        width = 40 if key == 'source_commit' else 64
        if len(p[key]) != width or any(c not in '0123456789abcdef' for c in p[key]):
            raise ValueError('invalid provenance digest: ' + key)
    # Explicit physical row mapping, with -1 for unused/padded rows. Never infer
    # original positions from ggml's padded cache row axis.
    rows = p.get('cache_row_positions')
    if (not isinstance(rows, list) or not rows or len(rows) > 36864
            or any(type(x) is not int or x < -1 for x in rows)):
        raise ValueError('invalid cache row positions')
    used = [x for x in rows if x >= 0]
    if len(set(used)) != len(used):
        raise ValueError('duplicate cache row positions')
    prefix = p.get('prefix_tokens')
    if type(prefix) is not int or not 2 <= prefix <= 36864:
        raise ValueError('invalid frozen prefix length')
    queries = integers(p.get('query_positions'), 'query positions')
    if (len(queries) > 512 or queries.tolist() != list(range(prefix, prefix + len(queries)))
            or sorted(used) != list(range(prefix + len(queries)))):
        raise ValueError('capture must contain a contiguous prefix and calibration suffix')
    fit = integers(p.get('fit_positions'), 'fit positions')
    evaluation = integers(p.get('eval_positions'), 'eval positions')
    if (set(fit) & set(evaluation) or set(fit) | set(evaluation) != set(queries)):
        raise ValueError('query split must be disjoint and cover the capture')
    complete = Path(directory) / 'COMPLETE.json'
    if p.get('complete_sha256') != digest(complete):
        raise ValueError('capture completion digest mismatch')
    c = json.loads(complete.read_text())
    layers = integers(c.get('layers'), 'completed layers').tolist()
    if c.get('schema') != 'epyc.am.native-capture.v1' or p.get('layers') != layers:
        raise ValueError('capture/provenance layer coverage mismatch')
    return p, layers


def shard(t, meta, p, head, indices):
    q, k, v, output = (t[n] for n in ('Q', 'K', 'V', 'output'))
    rows = np.asarray(p['cache_row_positions'])
    nqueries = len(p['query_positions'])
    if (any(a.ndim != 4 or a.shape[0] != 1 for a in (q, k, v, output))
            or k.shape[:3] != v.shape[:3] or q.shape[-1] != k.shape[-1]
            or k.shape[2] != len(rows) or q.shape[2] != nqueries
            or q.shape[1] % k.shape[1]
            or output.shape != (1, nqueries, q.shape[1], v.shape[-1])):
        raise ValueError('capture/provenance attention geometry mismatch')
    # Sort PHYSICAL rows by original prefix position; do not include calibration
    # tokens, future rows or cache padding in either full or compact attention.
    physical = np.asarray([int(np.flatnonzero(rows == pos)[0])
                           for pos in range(p['prefix_tokens'])])
    if 'mask' not in t:
        raise ValueError('causal capture mask is required')
    mask = t['mask']
    if (mask.shape[:2] != (1, 1) or mask.shape[2] < nqueries or mask.shape[3] != len(rows)
            or not np.all(mask[0, 0, :nqueries, physical] == 0)):
        raise ValueError('frozen prefix must be visible with zero bias to every query')
    scale = meta['attention_scale']
    if isinstance(scale, bool) or not np.isfinite(scale) or scale <= 0:
        raise ValueError('invalid captured attention scale')
    group = q.shape[1] // k.shape[1]
    result = dict(K=k[0, head, physical], V=v[0, head, physical], indices=indices)
    for name, positions in (('fit', p['fit_positions']), ('eval', p['eval_positions'])):
        offsets = [p['query_positions'].index(pos) for pos in positions]
        result['Q_' + name] = q[0, head*group:(head+1)*group][:, offsets, :].reshape(-1, q.shape[-1])
        result[name + '_ids'] = np.asarray([
            f"layer={meta['layer']}:seq=0:pos={pos}:head={h}"
            for h in range(head*group, (head+1)*group) for pos in positions])
    return result


def write_bundle(path, positions, layers):
    """Little-endian bounded native wire format, no NPZ/JSON parser in C++."""
    with Path(path).open('xb') as out:
        out.write(b'EPYCAM03')
        out.write(struct.pack('<II', len(layers), len(positions)))
        out.write(np.asarray(positions, dtype='<i8').tobytes())
        for layer, beta, values in layers:
            out.write(struct.pack('<III', layer, beta.shape[0], values.shape[-1]))
            out.write(np.asarray(beta, dtype='<f4').tobytes())
            out.write(np.asarray(values, dtype='<f4').tobytes())


def convert(directory, provenance_path, out, keep):
    directory, out = Path(directory), Path(out)
    p, layer_ids = provenance(provenance_path, directory)
    indices = uniform_selection(p['prefix_tokens'], keep)
    out.mkdir(parents=True, exist_ok=False)
    fits, hashes, layers = [], {}, []
    for layer in layer_ids:
        meta, tensors, native_hashes = load_layer(directory, layer)
        hashes.update(native_hashes)
        beta, values = [], []
        for head in range(tensors['K'].shape[1]):
            arrays = shard(tensors, meta, p, head, indices)
            stem = f'layer-{layer}-head-{head}'
            npz, sidecar = out / (stem + '.npz'), out / (stem + '.json')
            np.savez(npz, **arrays)
            metadata = {key: p[key] for key in ('source_commit', 'model_identity', 'capture_id')}
            metadata.update(layer=layer, kv_head=head, attention_scale=meta['attention_scale'],
                            coordinates='post_rope', capture_sha256=digest(npz))
            sidecar.write_text(json.dumps(metadata, indent=2) + '\n')
            fit_dir = out / (stem + '-fit')
            fitted = run(npz, sidecar, fit_dir)
            fits.append({'layer': layer, 'kv_head': head,
                         'fit_sha256': digest(fit_dir / 'FIT.json'), 'heldout': fitted['heldout']})
            with np.load(fit_dir / 'carrier.npz', allow_pickle=False) as z:
                b, c = z['beta'], z['C2']
                if (not np.array_equal(z['indices'], indices) or np.any(np.abs(b) > 60000)
                        or np.any(np.abs(c) > 65504)):
                    raise ValueError('carrier selection mismatch or F16 overflow')
                beta.append(b)
                values.append(c)
        layers.append((layer, np.stack(beta), np.stack(values)))
    bundle = out / 'carrier.bin'
    write_bundle(bundle, indices, layers)
    result = {'schema': 'epyc.am.converted-prefix.v1', 'provenance': p,
              'provenance_sha256': digest(provenance_path), 'converter_sha256': digest(__file__),
              'native_sha256': hashes, 'positions': indices.tolist(), 'layers': fits,
              'carrier_sha256': digest(bundle),
              'scope': 'offline frozen-prefix fit; restore prefix recurrent state before install; '
                       'heldout outputs are recomputed on that prefix, not native causal suffix outputs; '
                       'not a GPU, native reload, full-layer cosine or decode verdict'}
    # Completion manifest last. A failed/partial conversion is never loadable.
    (out / 'CONVERT.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', required=True)
    parser.add_argument('--provenance', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--keep', type=int, required=True)
    args = parser.parse_args()
    convert(args.capture, args.provenance, args.out, args.keep)
