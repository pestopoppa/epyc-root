"""Run only inside admitted rows; compare teacher-forced default-off controls.

Binary/library digests bind runtime bytes, not their source provenance. A full
build manifest and GPU-residency proof are separate row admission requirements.
"""
import argparse
import json
import math
import os
from pathlib import Path
import subprocess

import numpy as np

from apply_integration import PIN, HERE
from fit import digest

SETTINGS = ('model', 'model_identity', 'source_commit', 'prefix_tokens', 'warmup_tokens',
            'probe_tokens', 'n_ctx', 'threads', 'n_gpu_layers')


def validate(c):
    if c.get('mode') != 'control' or c.get('source_commit') != PIN:
        raise ValueError('control mode and approved experimental source pin required')
    if not isinstance(c.get('model_identity'), str) or not c['model_identity']:
        raise ValueError('prepared model identity required')
    if not isinstance(c.get('model'), str) or not c['model']:
        raise ValueError('prepared model path required')
    lengths = []
    for key, lo, hi in [('prefix_tokens', 2, 32768), ('warmup_tokens', 1, 256), ('probe_tokens', 1, 256)]:
        tokens = c.get(key)
        if (not isinstance(tokens, list) or not lo <= len(tokens) <= hi
                or any(type(t) is not int or not 0 <= t < 2**31 for t in tokens)):
            raise ValueError('bounded prepared token IDs required: ' + key)
        lengths.append(len(tokens))
    for key in ('n_ctx', 'threads', 'n_gpu_layers'):
        if type(c.get(key)) is not int:
            raise ValueError('integer setting required: ' + key)
    if not sum(lengths) <= c['n_ctx'] <= 36864 or c['threads'] < 1 or c['n_gpu_layers'] < 0:
        raise ValueError('invalid bounded context/threads/GPU layers')
    return {key: c[key] for key in SETTINGS}


def inventory(driver, library_dir):
    driver, library_dir = Path(driver).resolve(strict=True), Path(library_dir).resolve(strict=True)
    libs = {p.resolve(strict=True) for pattern in ('libllama*.so*', 'libggml*.so*')
            for p in library_dir.glob(pattern)}
    if (not any(p.name.startswith('libllama') for p in libs)
            or not any(p.name.startswith('libggml-base') for p in libs)
            or any(p.parent != library_dir for p in libs)):
        raise ValueError('self-contained shared llama/ggml library directory required')
    return {str(p): digest(p) for p in sorted(libs | {driver})}


def run(driver, config_path, library_dir):
    """Seal actual runtime artifacts before/after a single bounded native run."""
    config_path, driver = Path(config_path).resolve(), Path(driver).resolve()
    c = json.loads(config_path.read_text())
    settings = validate(c)
    root = Path(c['out']).resolve()
    if root.exists():
        raise ValueError('new control output directory required')
    before = inventory(driver, library_dir)
    config_hash = digest(config_path)
    source_hash = digest(HERE / 'control.cpp')
    env = dict(os.environ, LD_LIBRARY_PATH=str(Path(library_dir).resolve()))
    # A zero string is NOT portable for feature flags whose test is getenv().
    env.pop('LLAMA_KV_AM_BETA', None)
    observed_env = {k: v for k, v in env.items()
                    if k.startswith(('LLAMA_', 'GGML_', 'HIP_', 'HSA_', 'ROCR_', 'CUDA_', 'OMP_',
                                     'OPENBLAS_', 'MKL_')) or k in ('LD_PRELOAD', 'GPU_DEVICE_ORDINAL')}
    affinity = sorted(os.sched_getaffinity(0))
    subprocess.run([str(driver), str(config_path)], env=env, check=True)
    if (inventory(driver, library_dir) != before or digest(config_path) != config_hash
            or digest(HERE / 'control.cpp') != source_hash):
        raise ValueError('control executable/libraries/config/source changed during run')
    result = json.loads((root / 'RESULT.json').read_text())
    mapped = {str(Path(p).resolve(strict=True)) for p in result['mapped_libraries']}
    if (not mapped or not mapped <= before.keys() or str(driver) in mapped
            or not any(Path(p).name.startswith('libllama') for p in mapped)
            or not any(Path(p).name.startswith('libggml-base') for p in mapped)):
        raise ValueError('native mapped llama/ggml paths differ from bound build')
    seal = dict(schema='epyc.am.default-off-seal.v1', settings=settings,
                config_path=str(config_path), config_sha256=config_hash,
                control_source_sha256=source_hash, artifacts_sha256=before,
                mapped_libraries_sha256={p: before[p] for p in sorted(mapped)},
                environment=observed_env, affinity=affinity,
                result_sha256=digest(root / 'RESULT.json'), trace_sha256=digest(root / 'logits.f32'))
    # Validate dimensions/timing/finite trace before writing the completion seal.
    read_trace(root, seal)
    with (root / 'SEAL.json').open('x') as f:
        f.write(json.dumps(seal, indent=2, allow_nan=False) + '\n')
    return seal


def read_trace(root, seal):
    root = Path(root)
    if seal.get('schema') != 'epyc.am.default-off-seal.v1':
        raise ValueError('completed control seal required')
    for name, key in [('RESULT.json', 'result_sha256'), ('logits.f32', 'trace_sha256')]:
        if digest(root / name) != seal[key]:
            raise ValueError('control result/trace digest mismatch')
    r = json.loads((root / 'RESULT.json').read_text())
    s = seal['settings']
    validate(dict(s, mode='control'))
    n = len(s['probe_tokens'])
    v = r.get('n_vocab')
    if (r.get('schema') != 'epyc.am.default-off-control.v1' or r.get('mode') != 'control'
            or r.get('model_identity') != s['model_identity'] or r.get('source_commit') != s['source_commit']
            or type(r.get('probe_steps')) is not int or r['probe_steps'] != n
            or type(v) is not int or v < 1 or n * v * 4 > 512 * 1024**2
            or r.get('trace') != 'logits.f32'):
        raise ValueError('control result geometry/identity mismatch')
    times = np.asarray(r['decode_seconds'], dtype=np.float64)
    if times.shape != (n,) or not np.isfinite(times).all() or np.any(times <= 0):
        raise ValueError('positive finite per-step decode times required')
    path = root / 'logits.f32'
    if path.stat().st_size != n * v * 4:
        raise ValueError('control trace size mismatch')
    logits = np.memmap(path, dtype='<f4', mode='r', shape=(n, v))
    if not np.isfinite(logits).all():
        raise ValueError('nonfinite control logits')
    return r, logits, n / float(times.sum())


def logit_metrics(a, b):
    if (a.shape != b.shape or len(a.shape) != 2 or min(a.shape) < 1
            or not np.isfinite(a).all() or not np.isfinite(b).all()):
        raise ValueError('equal finite logit matrices required')
    klds, max_abs, greedy_equal, byte_equal = [], 0.0, True, True
    for x, y in zip(a, b):
        byte_equal = byte_equal and x.tobytes() == y.tobytes()
        x, y = x.astype(np.float64), y.astype(np.float64)
        max_abs = max(max_abs, float(np.max(np.abs(x - y))))
        greedy_equal = greedy_equal and int(np.argmax(x)) == int(np.argmax(y))
        x -= np.max(x); y -= np.max(y)
        lx, ly = x - np.log(np.exp(x).sum()), y - np.log(np.exp(y).sum())
        # KL(full baseline || patched), float64 stable log-softmax. Tiny
        # negative roundoff is clamped, never used as evidence of improvement.
        klds.append(max(0.0, float(np.dot(np.exp(lx), lx - ly))))
    return dict(logits_byte_equal=byte_equal, max_abs_logit_error=max_abs,
                greedy_tokens_equal=greedy_equal, kld_mean=float(np.mean(klds)), kld_max=max(klds))


def compare(baseline, patched, min_throughput_ratio):
    """At least three independent runs/variant; report noise, no early stopping."""
    if (len(baseline) != len(patched) or len(baseline) < 3
            or not math.isfinite(min_throughput_ratio) or not 0 < min_throughput_ratio <= 1):
        raise ValueError('>=3 equal run counts and explicit ratio threshold in (0,1] required')
    paths = [Path(p).resolve() for p in [*baseline, *patched]]
    if len(set(paths)) != len(paths):
        raise ValueError('distinct run directories required')
    records, metrics, rates, reference = [], [], [[], []], None
    fingerprints = [None, None]
    for side, group in enumerate((baseline, patched)):
        for root in group:
            seal_path = Path(root) / 'SEAL.json'
            s = json.loads(seal_path.read_text())
            _, logits, tps = read_trace(root, s)
            identity = {key: s[key] for key in ('settings', 'control_source_sha256', 'environment', 'affinity')}
            if reference is None:
                reference = identity
                base_logits = np.array(logits, copy=True)
            if identity != reference:
                raise ValueError('control inputs/source/settings/environment/affinity differ')
            # Each variant must use exactly one executable/library set.
            fingerprint = (s['artifacts_sha256'], s['mapped_libraries_sha256'])
            if fingerprints[side] is None:
                fingerprints[side] = fingerprint
            if fingerprint != fingerprints[side]:
                raise ValueError('runtime artifacts differ within variant')
            metrics.append(logit_metrics(base_logits, logits))
            rates[side].append(tps)
            records.append(dict(path=str(Path(root).resolve()), seal_sha256=digest(seal_path), side=side))
    ratio = float(np.median(rates[1]) / np.median(rates[0]))
    noise = [float(np.median(np.abs(np.array(group) - np.median(group))) / np.median(group))
             for group in rates]
    return dict(schema='epyc.am.default-off-comparison.v1', runs=records, logit_metrics=metrics,
                baseline_tokens_per_second=rates[0], patched_tokens_per_second=rates[1],
                relative_mad_baseline=noise[0], relative_mad_patched=noise[1],
                median_throughput_ratio=ratio, min_throughput_ratio=min_throughput_ratio,
                exact_logits_pass=all(m['logits_byte_equal'] for m in metrics),
                throughput_threshold_pass=ratio >= min_throughput_ratio,
                scope='finite teacher-forced sample; threshold screen, not proof of zero throughput change; '
                      'runtime hashes do not establish source provenance or GPU residency')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    subs = p.add_subparsers(dest='command', required=True)
    r = subs.add_parser('run')
    r.add_argument('--driver', required=True)
    r.add_argument('--config', required=True)
    r.add_argument('--library-dir', required=True)
    c = subs.add_parser('compare')
    c.add_argument('--baseline', nargs='+', required=True)
    c.add_argument('--patched', nargs='+', required=True)
    c.add_argument('--min-throughput-ratio', type=float, required=True)
    args = p.parse_args()
    result = (run(args.driver, args.config, args.library_dir) if args.command == 'run' else
              compare(args.baseline, args.patched, args.min_throughput_ratio))
    print(json.dumps(result, indent=2, allow_nan=False))
