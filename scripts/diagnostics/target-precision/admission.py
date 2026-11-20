"""Native matrix admission declarations; no execution, model hashing or grading.

Receipts are prepared before publishing a row. Checking their bindings is not
independent proof of their truth or of residency during a future run.
"""
import math
import re
from pathlib import Path


def _require(condition, message):
    if not condition:
        raise ValueError('native admission: ' + message)


def admit(plan, read):
    """Refuse incomplete native-claimed panels before any native subprocess."""
    if plan['origin'] == 'synthetic':
        return
    admission = plan.get('admission')
    _require(isinstance(admission, dict), 'missing admission receipts')

    def receipt(key):
        ref = admission.get(key)
        _require(isinstance(ref, dict) and set(ref) == {'path', 'sha256'}, key + ' receipt required')
        _require(isinstance(ref['path'], str) and Path(ref['path']).is_absolute(), key + ' absolute path required')
        value, identity = read(ref['path'])
        _require(identity['sha256'] == ref['sha256'], key + ' receipt digest mismatch')
        _require(value.get('schema') == 'epyc.target-precision.' + key + '.v1', key + ' schema mismatch')
        return value

    cells = plan['cells']
    quants = {c['target_quant'] for c in cells}
    _require(quants in ({'BF16', 'Q8_0', 'Q4_K_M'}, {'F16', 'Q8_0', 'Q4_K_M'}), 'full precision/Q8/Q4 arms required')
    targets = {}
    for c in cells:
        _require(targets.setdefault(c['target_quant'], c['target_sha256']) == c['target_sha256'], 'target artifact drift')
    groups = {}
    for c in cells:
        groups.setdefault((c['prompt_id'], c['seed'], c['repetition']), set()).add(c['target_quant'])
    _require(all(g == quants for g in groups.values()), 'unmatched prompt/seed/repetition arms')
    # Each adjacent block contains one complete matched group. Arm order may vary.
    for i in range(0, len(cells), len(quants)):
        block = cells[i:i + len(quants)]
        _require(len({(c['prompt_id'], c['seed'], c['repetition']) for c in block}) == 1
                 and {c['target_quant'] for c in block} == quants, 'arms must be interleaved in matched groups')

    holdout = receipt('holdout')
    _require(admission['holdout']['sha256'] == plan['holdout_sha256'], 'holdout digest mismatch')
    _require(holdout.get('prompt_manifest_sha256') == plan['prompt_manifest_sha256']
             and holdout.get('protocol_sha256') == plan['protocol_sha256'], 'holdout protocol mismatch')
    selected = {(c['prompt_id'], c['seed']) for c in cells}
    held = {tuple(v) for v in holdout.get('evaluation', [])}
    calibration = {tuple(v) for v in holdout.get('calibration', [])}
    _require(selected == held and not held.intersection(calibration), 'holdout overlap or coverage mismatch')

    weights = receipt('weights')
    base = weights.get('base', {})
    _require(isinstance(base.get('repo'), str) and bool(base['repo'].strip())
             and re.fullmatch('[0-9a-f]{40}', str(base.get('revision', ''))), 'pinned base revision required')
    arms = weights.get('targets', {})
    _require(set(arms) == quants, 'weight provenance arm coverage')
    artifacts = []
    for quant in quants:
        arm = arms[quant]
        _require(arm.get('sha256') == targets[quant] and arm.get('base') == base, 'unmatched base weights')
        _require(arm.get('tensor_correspondence') == 'verified', 'tensor correspondence unverified')
        for key in ('conversion_sha256', 'catalog_sha256'):
            _require(re.fullmatch('[0-9a-f]{64}', str(arm.get(key, ''))), 'missing conversion/catalog identity')
        artifacts.append(arm.get('path'))
    drafter = weights.get('drafter', {})
    _require(drafter.get('sha256') == plan['drafter_sha256'] and drafter.get('target_base') == base
             and drafter.get('training_dtype') == 'BF16', 'fixed BF16-trained target-locked drafter required')
    artifacts.append(drafter.get('path'))
    runtime = plan.get('native_worker', {})
    _require(runtime.get('targets') == {q: arms[q].get('path') for q in quants}
             and runtime.get('drafter') == drafter.get('path'), 'runtime model paths mismatch')
    _require(all(isinstance(p, str) and Path(p).is_absolute() for p in artifacts), 'prepared absolute model paths required')

    build = receipt('build')
    for key in ('backend', 'binary_sha256', 'source_sha256', 'libraries_sha256'):
        _require(build.get(key) == plan[key], 'build identity mismatch: ' + key)
    _require(re.fullmatch('[0-9a-f]{40}', str(build.get('source_commit', ''))), 'source commit required')
    libraries = build.get('libraries', {})
    _require(isinstance(libraries, dict) and bool(libraries), 'library identities required')
    for path, sha in libraries.items():
        _require(Path(path).is_absolute() and re.fullmatch('[0-9a-f]{64}', str(sha)), 'invalid library identity')
    # libraries_sha256 binds the canonical map, not an arbitrary aggregate label.
    import hashlib
    import json
    digest = hashlib.sha256(json.dumps(libraries, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    _require(digest == plan['libraries_sha256'], 'library map digest mismatch')
    env = runtime.get('env', {})
    _require(bool(env.get('LD_LIBRARY_PATH')) and build.get('ld_library_path') == env['LD_LIBRARY_PATH'], 'private library environment required')

    floor = receipt('floor')
    for key in ('backend', 'binary_sha256', 'libraries_sha256', 'source_sha256', 'drafter_sha256', 'verification', 'sampling'):
        _require(floor.get(key) == plan[key], 'floor setting mismatch: ' + key)
    _require(plan['verification'].get('replay') == 'fresh-block-serial-v1', 'fresh-block/serial profile required')
    controls = floor.get('controls', [])
    _require(isinstance(controls, list) and len(controls) == len(quants), 'floor arm coverage')
    _require({c.get('target_quant') for c in controls} == quants, 'floor arm coverage')
    for control in controls:
        _require(control.get('target_sha256') == targets[control['target_quant']], 'floor target mismatch')
        _require(control.get('comparison') == 'fresh-block-vs-serial-same-prefix'
                 and type(control.get('repetitions')) is int and control['repetitions'] >= 2, 'repeated same-prefix floor required')
        _require(type(control.get('coordinates')) is int and control['coordinates'] > 0, 'floor coordinate denominator required')
        for key in ('max_abs', 'rms'):
            v = control.get(key)
            _require(type(v) in (int, float) and math.isfinite(v) and 0 <= v <= plan['numerical_floor'], 'floor exceeds declared bound')
        _require(control['rms'] <= control['max_abs'], 'contradictory floor moments')
        original = control.get('native_output', {})
        _require(set(original) == {'path', 'sha256'} and Path(original['path']).is_absolute(), 'original floor output required')
        native, identity = read(original['path'])
        _require(identity['sha256'] == original['sha256'], 'floor original digest mismatch')
        _require(native == {k: v for k, v in control.items() if k != 'native_output'}, 'floor original telemetry mismatch')

    proof = admission.get('runtime_proof')
    _require(isinstance(proof, dict), 'runtime residency proof plan required')
    _require(proof.get('sampling_window') == 'during-each-cell'
             and proof.get('mapped_library_sha256') == libraries
             and proof.get('own_pid') is True, 'runtime mapping/ownership proof plan required')
    if plan['backend'] == 'hip':
        _require(proof.get('kfd_process') is True and proof.get('nonzero_vram') is True, 'HIP residency proof plan required')
