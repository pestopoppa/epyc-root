"""Prospective precision-panel native field binding, without grading authority.

A runner must open the capture before executing cells and finalize after writing
native cell records. This module validates declarations, not process residency or
weight equivalence. Existing DFlash concurrency carriers remain unchanged.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re

SCHEMA = 'epyc.target-precision.capture.v1'
SHARED = ('drafter_sha256', 'backend', 'binary_sha256', 'libraries_sha256',
          'verification', 'sampling', 'prompt_manifest_sha256', 'holdout_sha256',
          'protocol_sha256', 'source_sha256', 'decision_rule', 'numerical_floor')


def _digest(raw):
    return hashlib.sha256(raw).hexdigest()


def _encode(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def _pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError('duplicate JSON key: ' + key)
        value[key] = item
    return value


def _read(path):
    # Reuse the existing no-follow stable same-FD declaration reader, including
    # metadata and inode race checks; never hash model weights inside a grant.
    from scripts.vidya.qwen4exp_quality_capture import stable_bytes_identity
    raw, identity = stable_bytes_identity(Path(path))
    value = json.loads(raw, object_pairs_hook=_pairs,
                       parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))
    if not isinstance(value, dict):
        raise ValueError('record must be an object')
    return value, identity


def _sha(value):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{64}', value):
        raise ValueError('invalid SHA-256')


def _count(value):
    if type(value) is not int or value < 0:
        raise ValueError('count must be a nonnegative integer')


def _plan(plan):
    for key in ('run_id', 'origin', *SHARED, 'cells'):
        if key not in plan or plan[key] is None or plan[key] == '' or plan[key] == {}:
            raise ValueError('missing plan field: ' + key)
    if plan['origin'] not in ('synthetic', 'native_claimed'):
        raise ValueError('explicit source origin required')
    if not isinstance(plan['run_id'], str) or not plan['run_id']:
        raise ValueError('invalid run id')
    for key in SHARED:
        if key.endswith('_sha256'):
            _sha(plan[key])
    if plan['backend'] not in ('cpu', 'hip'):
        raise ValueError('backend must identify one panel')
    if (isinstance(plan['numerical_floor'], bool)
            or not isinstance(plan['numerical_floor'], (int, float))
            or not math.isfinite(plan['numerical_floor']) or plan['numerical_floor'] < 0):
        raise ValueError('invalid numerical floor')
    for key in ('verification', 'sampling'):
        if not isinstance(plan[key], dict) or not plan[key]:
            raise ValueError('missing native settings: ' + key)
    if not isinstance(plan['decision_rule'], str) or not plan['decision_rule'].strip():
        raise ValueError('missing prospective decision rule')
    cells = plan['cells']
    if not isinstance(cells, list) or not cells:
        raise ValueError('missing cells')
    seen = set()
    for cell in cells:
        for key in ('cell_id', 'prompt_id', 'seed', 'repetition', 'target_quant', 'target_sha256'):
            if key not in cell:
                raise ValueError('missing cell field: ' + key)
        for key in ('cell_id', 'prompt_id'):
            if not isinstance(cell[key], str) or not cell[key]:
                raise ValueError('invalid cell identity')
        for key in ('seed', 'repetition'):
            _count(cell[key])
        if cell['target_quant'] not in ('BF16', 'F16', 'Q8_0', 'Q4_K_M'):
            raise ValueError('unknown precision arm')
        _sha(cell['target_sha256'])
        case = (cell['prompt_id'], cell['seed'], cell['repetition'], cell['target_quant'])
        if cell['cell_id'] in seen or case in seen:
            raise ValueError('duplicate cell or case')
        seen.update((cell['cell_id'], case))
    labels = plan.get('measurement_labels')
    if labels is not None:
        if not isinstance(labels, dict) or set(labels) != {'id_prefix', 'date', 'category', 'claim'}:
            raise ValueError('invalid measurement labels')
        if any(not isinstance(v, str) or not v.strip() for v in labels.values()):
            raise ValueError('empty measurement label')
        if labels['category'] not in ('BASELINE', 'CANDIDATE', 'OPTIMUM'):
            raise ValueError('invalid measurement category')
    return plan


def admit_native(plan):
    module_spec = importlib.util.spec_from_file_location('precision_admission', Path(__file__).with_name('admission.py'))
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    module.admit(plan, _read)


def _exclusive(path, value):
    with Path(path).open('xb') as stream:
        stream.write(_encode(value) + b'\n')
        stream.flush()
        import os
        os.fsync(stream.fileno())


def open_capture(plan_path, opened_path):
    """Seal the prospective native plan; runner calls this before first cell."""
    plan, identity = _read(plan_path)
    _plan(plan)
    record = {'schema': SCHEMA, 'phase': 'opened', 'plan': plan,
              'plan_file': identity, 'producer_sha256': _digest(Path(__file__).read_bytes())}
    if 'admission' in plan:
        record['admission_producer_sha256'] = _digest(Path(__file__).with_name('admission.py').read_bytes())
        record['floor_worker_sha256'] = _digest(Path(__file__).with_name('worker.py').read_bytes())
        record['floor_producer_sha256'] = _digest(Path(__file__).with_name('floor.py').read_bytes())
        record['runtime_producer_sha256'] = _digest(Path(__file__).with_name('runtime.py').read_bytes())
    _exclusive(opened_path, record)
    return record


def _finalized(opened_path, cell_paths):
    """Bind every planned cell, including failures, to original native records.

    Missing counts remain null; weighted acceptance uses summed accepted/drafted
    counts over successful cells only. Missing cells refuse finalization rather
    than silently shrinking the denominator. No ClaimTuple or causal grade is
    invented; projection and native runner integration remain explicit gates.
    """
    opened, opened_identity = _read(opened_path)
    if opened.get('schema') != SCHEMA or opened.get('phase') != 'opened':
        raise ValueError('not a prospective opening')
    if opened['producer_sha256'] != _digest(Path(__file__).read_bytes()):
        raise ValueError('producer bytes changed')
    plan = _plan(opened['plan'])
    if 'admission' in plan:
        if opened.get('floor_worker_sha256') != _digest(Path(__file__).with_name('worker.py').read_bytes()):
            raise ValueError('floor worker bytes changed')
        if opened.get('floor_producer_sha256') != _digest(Path(__file__).with_name('floor.py').read_bytes()):
            raise ValueError('floor producer bytes changed')
        if opened.get('admission_producer_sha256') != _digest(Path(__file__).with_name('admission.py').read_bytes()):
            raise ValueError('admission producer bytes changed')
        if opened.get('runtime_producer_sha256') != _digest(Path(__file__).with_name('runtime.py').read_bytes()):
            raise ValueError('runtime producer bytes changed')
        admit_native(plan)
    current_plan, identity = _read(opened['plan_file']['path'])
    if identity['sha256'] != opened['plan_file']['sha256'] or current_plan != plan:
        raise ValueError('plan bytes changed')
    expected = {cell['cell_id']: cell for cell in plan['cells']}
    outcomes, seen = [], set()
    totals = {'ok': 0, 'failed': 0, 'invalid': 0, 'abstained': 0}
    accepted = drafted = 0
    by_quant = {}
    for path in cell_paths:
        cell, source = _read(path)
        cid = cell.get('cell_id')
        if cid not in expected or cid in seen:
            raise ValueError('unknown or duplicate cell')
        seen.add(cid)
        if cell.get('run_id') != plan['run_id']:
            raise ValueError('run identity mismatch')
        if cell.get('plan_sha256') != opened['plan_file']['sha256']:
            raise ValueError('cell plan binding mismatch')
        if cell.get('settings') != {key: plan[key] for key in SHARED}:
            raise ValueError('native shared settings mismatch')
        if cell.get('case') != expected[cid]:
            raise ValueError('native case identity mismatch')
        for artifact in cell.get('native_artifacts', []):
            from scripts.vidya.qwen4exp_quality_capture import stable_bytes_identity
            _, observed = stable_bytes_identity(Path(artifact['path']))
            if observed['sha256'] != artifact['sha256']:
                raise ValueError('native artifact bytes changed')
        status = cell.get('status')
        if status not in totals:
            raise ValueError('unknown terminal status')
        totals[status] += 1
        raw_path = cell.get('raw_output_path')
        raw_sha = cell.get('raw_output_sha256')
        if raw_path is None:
            if raw_sha is not None or status == 'ok':
                raise ValueError('missing native output')
        else:
            raw_output, raw_identity = _read(raw_path)
            if raw_identity['sha256'] != raw_sha:
                raise ValueError('raw output bytes changed')
            if status == 'ok' and any(raw_output.get(key) != cell.get(key) for key in
                                      ('positions', 'accepted', 'drafted', 'numerical_divergence')):
                raise ValueError('native output telemetry mismatch')
        if status == 'ok':
            if plan['origin'] == 'native_claimed':
                proof_ref = cell.get('runtime_proof', {})
                proof, proof_identity = _read(proof_ref.get('path', ''))
                if (proof_identity != proof_ref or raw_output.get('runtime_proof') != proof_ref
                        or proof_ref not in cell.get('native_artifacts', [])):
                    raise ValueError('runtime proof identity mismatch')
                request = raw_output.get('request', {})
                if (request.get('plan_sha256') != opened['plan_file']['sha256']
                        or request.get('case') != expected[cid]
                        or request.get('settings') != cell['settings']
                        or request.get('runtime') != plan['native_worker']):
                    raise ValueError('runtime request plan/cell mismatch')
                module_spec = importlib.util.spec_from_file_location('precision_runtime_replay', Path(__file__).with_name('runtime.py'))
                module = importlib.util.module_from_spec(module_spec)
                module_spec.loader.exec_module(module)
                module.validate(proof, plan, request)
            positions = cell.get('positions')
            if not isinstance(positions, list) or not positions:
                raise ValueError('missing per-position acceptance')
            ids = set()
            a = d = 0
            for position in positions:
                index = position['position']
                _count(index)
                if index in ids:
                    raise ValueError('duplicate position')
                ids.add(index)
                for key in ('accepted', 'drafted'):
                    _count(position[key])
                if position['accepted'] > position['drafted']:
                    raise ValueError('accepted exceeds drafted')
                a += position['accepted']
                d += position['drafted']
            if not d or type(cell.get('accepted')) is not int or type(cell.get('drafted')) is not int or (a, d) != (cell['accepted'], cell['drafted']):
                raise ValueError('acceptance denominator mismatch')
            divergence = cell.get('numerical_divergence')
            if not isinstance(divergence, dict) or not divergence:
                raise ValueError('missing numerical divergence')
            for value in divergence.values():
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                    raise ValueError('invalid numerical divergence')
            accepted += a
            drafted += d
            arm = by_quant.setdefault(expected[cid]['target_quant'], {'accepted': 0, 'drafted': 0})
            arm['accepted'] += a
            arm['drafted'] += d
        elif not isinstance(cell.get('error'), str) or not cell['error'].strip():
            raise ValueError('terminal failure requires reason')
        outcomes.append({'native': cell, 'source_file': source})
    if seen != set(expected):
        raise ValueError('missing planned cells')
    result = {'schema': SCHEMA, 'phase': 'finalized', 'opened_file': opened_identity,
              'plan': plan, 'cells': outcomes, 'counts': totals,
              'weighted_acceptance': accepted / drafted if drafted else None,
              'accepted': accepted, 'drafted': drafted, 'by_quant': by_quant,
              'causal_gate': 'UNRESOLVED', 'projection_ready': False,
              'authority': 'declared_native_fields_only_no_runtime_or_weight_equivalence_proof'}
    labels = plan.get('measurement_labels')
    result['measurements'] = []
    if labels:
        for quant, counts in sorted(by_quant.items()):
            result['measurements'].append(dict(
                measurement_id=labels['id_prefix'] + ':' + quant,
                metric='successful_cell_weighted_acceptance',
                value=counts['accepted'] / counts['drafted'], date=labels['date'],
                category=labels['category'], claim=labels['claim'],
                metric_direction='higher_better', unit='fraction',
                target_quant=quant, accepted=counts['accepted'], drafted=counts['drafted']))
    return result


def finalize_precision(opened_path, cell_paths, output_path):
    result = _finalized(opened_path, cell_paths)
    _exclusive(output_path, result)
    return result


def read_precision(output_path):
    """Reopen originals and replay every field, refusing edited or lost evidence."""
    result, identity = _read(output_path)
    if result.get('schema') != SCHEMA or result.get('phase') != 'finalized':
        raise ValueError('not a prospective precision closure')
    opened = result['opened_file']
    _, observed = _read(opened['path'])
    if observed != opened:
        raise ValueError('opening identity changed')
    paths = [cell['source_file']['path'] for cell in result['cells']]
    if _finalized(opened['path'], paths) != result:
        raise ValueError('closure differs from retained originals')
    return result, identity
