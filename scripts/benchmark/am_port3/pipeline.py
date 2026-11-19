"""Verified-build, bounded AM-PORT-3 model pipeline. Run only in an admitted row.

No downloads, tokenization, weight hashing or automatic handoff verdicts.
"""
import argparse
import json
import math
import os
from pathlib import Path
import re

from apply_integration import PIN
import build
import controls
from convert import convert
from fit import digest
import run_driver
from residency import Executor

KINDS = ('baseline_cpu', 'patched_cpu', 'baseline_hip', 'patched_hip')
STAT_KEYS = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns')


def save(path, value):
    with Path(path).open('x') as f:
        f.write(json.dumps(value, indent=2, allow_nan=False) + '\n')


def model_stat(path):
    s = Path(path).stat()
    return {k: getattr(s, k) for k in STAT_KEYS}


def validate(plan):
    if plan.get('schema') != 'epyc.am.pipeline-plan.v1' or plan.get('source_commit') != PIN:
        raise ValueError('approved pipeline schema/source pin required')
    if not re.fullmatch('[0-9a-f]{64}', plan.get('model_identity', '')):
        raise ValueError('model digest prepared before row publication required')
    if model_stat(plan['model']) != plan['model_stat'] or plan['model_stat']['st_size'] <= 0:
        raise ValueError('prepared model file identity changed')
    if digest(plan['tokens']) != plan['tokens_sha256']:
        raise ValueError('prepared token content changed')
    tokens = json.loads(Path(plan['tokens']).read_text())
    lengths = {'prefix_tokens': (5, 4096), 'calibration_tokens': (2, 512),
               'warmup_tokens': (1, 256), 'probe_tokens': (1, 256)}
    for key, (lo, hi) in lengths.items():
        a = tokens.get(key)
        if (not isinstance(a, list) or not lo <= len(a) <= hi
                or any(type(t) is not int or not 0 <= t < 2**31 for t in a)):
            raise ValueError('bounded prepared token array required: ' + key)
    if len(tokens['prefix_tokens']) % 5:
        raise ValueError('prefix must permit exactly 5x compression')
    layers = plan.get('expected_layers')
    if (not isinstance(layers, list) or len(layers) != 16
            or any(type(i) is not int or i < 0 for i in layers) or sorted(set(layers)) != layers):
        raise ValueError('exactly 16 sorted distinct attention layers required')
    for key, lo, hi in [('threads', 1, len(os.sched_getaffinity(0))), ('control_pairs', 3, 9),
                        ('phase_timeout_s', 1, 86400), ('n_gpu_layers', 1, 999)]:
        if type(plan.get(key)) is not int or not lo <= plan[key] <= hi:
            raise ValueError('bounded integer setting required: ' + key)
    for key, hi in [('min_throughput_ratio', 1), ('native_relative_l2_limit', .01)]:
        x = plan.get(key)
        if type(x) not in (int, float) or not math.isfinite(x) or not 0 < x <= hi:
            raise ValueError('explicit finite screen threshold required: ' + key)
    if not re.fullmatch(r'/sys/class/drm/card[0-9]+/device/mem_info_vram_used', plan.get('device_vram_path', '')):
        raise ValueError('real DRM device VRAM counter required')
    builds = {}
    if set(plan['builds']) != set(KINDS):
        raise ValueError('all four full-build manifests required')
    for key in KINDS:
        m = build.verify(plan['builds'][key])
        variant, backend = key.split('_')
        if (m['variant'], m['backend']) != (variant, backend):
            raise ValueError('manifest variant/backend differs from plan key')
        if backend == 'hip' and m['architecture'] != 'gfx90a':
            raise ValueError('MI210 gfx90a full build required')
        builds[key] = m
    if len({str(Path(plan['builds'][k]).resolve()) for k in KINDS}) != 4:
        raise ValueError('distinct full-build receipts required')
    return tokens, builds


def quality(check, layers, tolerance):
    rows = check['layers']
    if check.get('schema') != 'epyc.am.compact-check.v1' or sorted(r['layer'] for r in rows) != layers:
        raise ValueError('complete exact native attention-layer coverage required')
    good, native = [], True
    for r in rows:
        q = r['frozen_prefix_quality_on_reload_queries']
        n = r['native_vs_compact_oracle']
        cosine, error = q['cosine_min'], n['relative_l2']
        if (cosine is not None and (not math.isfinite(cosine) or not -1.00001 <= cosine <= 1.00001)
                or not math.isfinite(error) or error < 0):
            raise ValueError('invalid native quality metrics')
        if cosine is not None and cosine >= .95 and q['undefined_cosines'] == 0:
            good.append(r['layer'])
        native = native and error <= tolerance
    return dict(layers_at_cosine_095=good, required_layers=14,
                prefix_quality_screen_pass=len(good) >= 14,
                native_integrity_screen_pass=bool(native),
                scope='minimum query-head prefix cosine on compact-trajectory Q; local approximation, not full-model quality')


def run(plan_path, out):
    plan_path, out = Path(plan_path).resolve(), Path(out).resolve()
    plan_hash = digest(plan_path)
    plan = json.loads(plan_path.read_text())
    tokens, _ = validate(plan)
    manifests = {k: digest(plan['builds'][k]) for k in KINDS}
    out.mkdir(parents=True, exist_ok=False)
    save(out / 'PLAN.json', plan)
    comparisons = {}

    def bound():
        if digest(plan_path) != plan_hash:
            raise ValueError('plan changed during execution')
        validate(plan)
        if manifests != {k: digest(plan['builds'][k]) for k in KINDS}:
            raise ValueError('build receipts changed during execution')

    def execute(key, name):
        bindir = Path(plan['builds'][key]).resolve().parent / 'build/bin'
        executor = Executor(out / 'execution' / name, bindir, gpu=key.endswith('_hip'),
                            device=plan['device_vram_path'], timeout_s=plan['phase_timeout_s'])
        def checked(argv, **kwargs):
            bound()
            result = executor(argv, **kwargs)
            bound()
            return result
        return bindir, checked

    common = dict(model=plan['model'], model_identity=plan['model_identity'], source_commit=PIN,
                  prefix_tokens=tokens['prefix_tokens'], n_ctx=36864, threads=plan['threads'])

    def finish(stopped_at, extra):
        bound()
        result = dict(schema='epyc.am.pipeline-result.v1', status='MEASURED',
                      plan_sha256=plan_hash, build_manifests_sha256=manifests,
                      stopped_at=stopped_at, controls=comparisons, **extra)
        result['execution_sha256'] = {str(p.relative_to(out)): digest(p)
                                     for p in sorted((out / 'execution').rglob('*')) if p.is_file()}
        result['outputs_sha256'] = {str(p.relative_to(out)): digest(p)
                                   for p in sorted(out.rglob('*')) if p.is_file()}
        save(out / 'RESULT.json', result)
        return result

    for backend in ('cpu', 'hip'):
        groups = {'baseline': [], 'patched': []}
        # Paired, alternating order reduces fixed order bias without changing inputs.
        for i in range(plan['control_pairs']):
            for variant in (('baseline', 'patched') if i % 2 == 0 else ('patched', 'baseline')):
                key, name = variant + '_' + backend, f'control-{backend}-{i}-{variant}'
                bindir, executor = execute(key, name)
                root = out / name
                c = dict(common, mode='control', out=str(root),
                         n_gpu_layers=0 if backend == 'cpu' else plan['n_gpu_layers'],
                         warmup_tokens=tokens['warmup_tokens'], probe_tokens=tokens['probe_tokens'])
                config = out / (name + '.json')
                save(config, c)
                controls.run(bindir / 'am-control', config, bindir, execute=executor)
                groups[variant].append(root)
        comparison = controls.compare(groups['baseline'], groups['patched'], plan['min_throughput_ratio'])
        comparisons[backend] = comparison
        save(out / ('CONTROL-' + backend + '.json'), comparison)
        if not comparison['exact_logits_pass'] or not comparison['throughput_threshold_pass']:
            return finish('default-off-' + backend, {'scope': 'default-off screen failed; no fitted-cache model run'})

    key = 'patched_hip'
    capture = out / 'capture'
    c = dict(common, mode='capture', out=str(capture), capture_id=plan_hash,
             n_gpu_layers=plan['n_gpu_layers'], calibration_tokens=tokens['calibration_tokens'])
    config = out / 'capture.json'
    save(config, c)
    bindir, executor = execute(key, 'capture')
    run_driver.run(bindir / 'am-driver', config, execute=executor)
    converted = out / 'converted'
    convert(capture / 'native', capture / 'PROVENANCE.json', converted, len(tokens['prefix_tokens']) // 5)
    first = json.loads((capture / 'RESULT.json').read_text())['prefix_greedy_token']
    reload = out / 'reload'
    c = dict(common, mode='reload', out=str(reload), capture_id=plan_hash,
             n_gpu_layers=plan['n_gpu_layers'], prefix_state=str(capture / 'prefix.state'),
             carrier=str(converted / 'carrier.bin'), first_decode_token=first,
             decode_steps=1, capture_reload=True)
    config = out / 'reload.json'
    save(config, c)
    bindir, executor = execute(key, 'reload')
    # Original must be the native directory, not the capture driver's root.
    run_driver.run(bindir / 'am-driver', config, converted=converted, original=capture / 'native', execute=executor)
    raw = json.loads((reload / 'RESULT.json').read_text())
    if raw.get('decoded_tokens') != 1 or raw.get('captured_reload') is not True:
        raise ValueError('one-token compact decode with first-append capture required')
    check_path = reload / 'CHECK.json'
    scores = quality(json.loads(check_path.read_text()), plan['expected_layers'], plan['native_relative_l2_limit'])
    if not scores['prefix_quality_screen_pass'] or not scores['native_integrity_screen_pass']:
        return finish('compact-quality', dict(quality=scores, decoded_tokens=1,
                      compact_check_sha256=digest(check_path),
                      scope='compact quality/integrity screen failed; 32K stability not run'))
    stability = out / 'stability'
    c.update(out=str(stability), decode_steps=32768, capture_reload=False)
    config = out / 'stability.json'
    save(config, c)
    bindir, executor = execute(key, 'stability')
    run_driver.run(bindir / 'am-driver', config, converted=converted, execute=executor)
    raw = json.loads((stability / 'RESULT.json').read_text())
    if raw.get('decoded_tokens') != 32768 or raw.get('captured_reload') is not False:
        raise ValueError('full 32K compact stability decode required')
    return finish('complete', dict(quality=scores, decoded_tokens=32768,
                  compact_check_sha256=digest(check_path),
                  scope='model screen and sampled GPU residency/budget; throughput threshold is not proof of zero default-off change'))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--plan', required=True)
    p.add_argument('--out', required=True)
    a = p.parse_args()
    print(json.dumps(run(a.plan, a.out), indent=2))
