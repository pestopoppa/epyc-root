"""Prospective E1 phase peaks: project only source-bound native observations.

This reader does not issue a gate or reconstruct warrants for old logs. The
writer, source manifest and raw observations must all survive the original run.
"""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime
from pathlib import Path, PurePosixPath

from claim_tuple import ClaimTuple, ProjectionError, register

ADAPTER_ID = 'vidya.adapters.yarn_e1_mem_phase/v1'
AUTHORITY = 'measurement'
TRUSTED_SOURCE_SHA256 = '328450b09e5c0ed60f1ecfa2527fa1e86b40c0505aabbfbb9a0122bade763ab7'
RUN_ID = 'codex-gpu-serving-yarn-e1-a0-low-20261102'
MODEL_SHA256 = 'a680f44a06920e5d689774823782006aa3acc8db95750323373b24139b67e348'
IMAGE_COMMIT = '9a3f1392a74d22f50e093791d14ea207a6170368'


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical(row):
    return json.dumps(row, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def _native_file(d, value, digest):
    locator = PurePosixPath(value)
    if locator.is_absolute() or not locator.parts or any(x in ('', '.', '..') for x in locator.parts):
        raise ValueError('invalid native artifact locator')
    path = (d / locator).resolve(strict=True)
    if not path.is_relative_to(d.resolve()) or not path.is_file() or _sha(path) != digest:
        raise ValueError('missing, escaped or modified native artifact')
    return path


def native_rows(path):
    p = Path(path)
    p = p / 'belief_measurements.jsonl' if p.is_dir() else p
    if not p.is_file():
        return ()
    try:
        d = p.parent
        root = d.parent.parent
        if _sha(root / 'SOURCE.sha256') != TRUSTED_SOURCE_SHA256:
            raise ValueError('unreviewed producer manifest')
        for line in (root / 'SOURCE.sha256').read_text().splitlines():
            digest, name = line.split('  ', 1)
            source = (root / name).resolve(strict=True)
            if not source.is_relative_to(root.resolve()) or _sha(source) != digest:
                raise ValueError('producer source changed')
        rows = [json.loads(line) for line in p.read_text().splitlines() if line.strip()]
        if len(rows) != 2 or {r.get('phase') for r in rows} != {'128k', '240k'}:
            raise ValueError('expected both unique phases')
        launch = json.loads((d / 'launch.json').read_text())
        proof = json.loads((d / 'runtime-proof.json').read_text())
        if launch.get('pid') != proof.get('pid') or not isinstance(proof.get('pid'), int):
            raise ValueError('process identity mismatch')
        for row in rows:
            content = dict(row); recorded = content.pop('row_sha256', '')
            if hashlib.sha256(_canonical(content)).hexdigest() != recorded:
                raise ValueError('changed native row')
            phase = row['phase']
            expected = {'schema': 'yarn-e1-mem.native-measurement.v1', 'source_kind': 'yarn-e1-mem-phase',
                        'run_id': RUN_ID, 'arm': 'A0', 'metric': 'own_pid_kfd_peak', 'unit': 'GiB',
                        'metric_direction': 'lower_better', 'category': 'BASELINE', 'protocol_id': '', 'reps': 1,
                        'measurement_id': f'{RUN_ID}:{phase}:own-kfd-peak'}
            if any(row.get(k) != v for k, v in expected.items()):
                raise ValueError('wrong measurement scope')
            if row.get('producer_manifest_sha256') != TRUSTED_SOURCE_SHA256 or row.get('model_pin', {}).get('sha256') != MODEL_SHA256 or row.get('image_binding', {}).get('source_commit') != IMAGE_COMMIT:
                raise ValueError('producer, model or image identity mismatch')
            if row.get('launch') != launch or row.get('runtime_proof') != proof or row.get('pid') != proof['pid']:
                raise ValueError('native process proof mismatch')
            record = _native_file(d, row['record_file'], row['record_sha256'])
            kfd = _native_file(d, row['kfd_path'], row['kfd_sha256'])
            _native_file(d, row['hip_trace_path'], row['hip_trace_sha256'])
            calls_path = _native_file(d, row['native_calls'], row['native_calls_sha256'])
            a = json.loads(record.read_text())['stages'][phase]
            win = row['window']; start, end = win['start'], win['end']
            if start != a['start'] or end != a['end'] or not (launch['at'] <= start <= end) or row['requests'] != a['requests'] or a['requests'] < 6:
                raise ValueError('phase window or request mismatch')
            calls = [json.loads(line) for line in calls_path.read_text().splitlines() if line.strip()]
            calls = [x for x in calls if x.get('stage') == phase]
            needles = [x for x in calls if x.get('kind') == 'needle']
            local = [x for x in calls if x.get('kind') == 'local']
            if (len(calls) != 6 or len(needles) != 5 or len(local) != 1
                    or {x.get('q_index') for x in needles} != set(range(5))
                    or any(x.get('http_ok') is not True for x in calls)):
                raise ValueError('incomplete, duplicated or failed stage requests')
            stamp = lambda x: datetime.fromisoformat(x['at'].replace('Z', '+00:00')).timestamp()
            if len(calls) != a['requests'] or min(stamp(x) - float((x.get('timings') or {}).get('wall_s') or 0) for x in calls) != start or max(stamp(x) for x in calls) != end:
                raise ValueError('phase window not reproduced from request records')
            samples = [json.loads(line) for line in kfd.read_text().splitlines() if line.strip()]
            values = [x['pid_vram_gib'] for x in samples if start <= x['t'] <= end and x.get('pid_vram_gib') is not None and proof['pid'] in x.get('kfd_pids', [])]
            if not values or any(type(v) not in (float, int) or not math.isfinite(v) for v in values) or max(values) != row['value'] or row['value'] != a['own_kfd_peak_gib']:
                raise ValueError('peak not reproduced by in-window own-PID samples')
            if row.get('input_manifest_sha256') != _sha(root / 'inputs/manifest.json'):
                raise ValueError('input manifest mismatch')
            row['_validated_path'] = str(p.resolve())
        return tuple(rows)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ProjectionError(f'YARN E1 phase: {exc}') from exc


@register('yarn-e1-mem-phase')
def project(row):
    phase = row['phase']
    return ClaimTuple(measurement_id=row['measurement_id'], metric='own_pid_kfd_peak', value=row['value'],
                      date=datetime.fromisoformat(row['date']).date().isoformat(), category='BASELINE',
                      claim='Own-PID sampled VRAM peak during one historical E1 A0 phase; no causal or promotion verdict',
                      metric_direction='lower_better', protocol_id='', reps=1,
                      reps_basis='one phase in one server run; samples are not independent repetitions', unit='GiB',
                      attestation_path=row['_validated_path'], attestation_present=True,
                      source_kind='yarn-e1-mem-phase',
                      applicability={'surface': 'yarn-e1-a0-' + phase, 'model_sha256': MODEL_SHA256,
                                     'kernel': {'build_commit': IMAGE_COMMIT}, 'backend': 'gpu',
                                     'scope_basis': 'native'},
                      extra={'window': row['window'], 'pid': row['pid'], 'requests': row['requests'],
                             'source_manifest_sha256': TRUSTED_SOURCE_SHA256,
                             'limitations': 'uncodified historical phase observation; no independent repetitions'})
