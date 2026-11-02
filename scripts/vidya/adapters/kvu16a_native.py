"""Original-run KVU-16a sampled load observations; projection, not grading."""
from __future__ import annotations
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import Any
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from claim_tuple import ProjectionError, register, to_frames
from adapters import _native_sidecar as ns

SCHEMA = 'epyc.vidya.kvu16a.sampled_load.v1'
SOURCE_KIND = 'kvu16a-sampled-load'
ADAPTER_ID = 'vidya.adapters.kvu16a_native/v1'
SIDECAR_NAME = 'kvu16a_sampled_load.beliefs.jsonl'


def _derive(root: Path):
    plan = json.loads((root / 'plan.json').read_text())
    result = json.loads((root / 'result.json').read_text())
    records = [json.loads(x) for x in (root / 'samples.jsonl').read_text().splitlines()]
    if result.get('schema') != 'kvu16a.load.sampled.v1' or plan.get('belief_adapter_sha256') != ns.file_sha256(Path(__file__)):
        raise ValueError('not a prospective original-run record')
    files = plan.get('producer_files_sha256')
    if (not ns.SHA256.fullmatch(str(plan.get('producer_sha256', ''))) or not isinstance(files, dict) or
        set(files) != {'producer.py', 'sampler.py', 'device_identity.py', 'server_lifecycle.py'} or
        files.get('producer.py') != plan['producer_sha256'] or
        any(not ns.SHA256.fullmatch(str(value)) for value in files.values())):
        raise ValueError('missing producer identity')
    state = result['state']; cleanup = result['cleanup']; runtime = result['runtime_identity']; grant = result['grant']
    if (state.get('error') is not None or not cleanup.get('verified_dead') or
        grant.get('FILLER_NEEDGPU') != '1' or not grant.get('FILLER_DEADLINE') or
        not runtime or runtime.get('argv') != plan.get('argv') or runtime.get('effective_env') != plan.get('effective_env') or
        not runtime.get('mapped_libraries_sha256') or not plan.get('identities')):
        raise ValueError('incomplete run identity, grant, or cleanup')
    if not records or any(x.get('status') != 'observed' or x.get('own_vram_b') is None for x in records):
        raise ValueError('missing or unknown original sample')
    if any(not ns.nonneg_int(x.get('own_vram_b')) or x.get('pid') != cleanup.get('pid') or
           x.get('birth_ticks') != cleanup.get('birth_ticks') or x.get('phase') not in ('startup', 'healthy') or
           not ns.finite(x.get('sample_start_monotonic_s')) or not ns.finite(x.get('sample_end_monotonic_s')) or
           x['sample_start_monotonic_s'] > x['sample_end_monotonic_s'] for x in records):
        raise ValueError('invalid sample or process identity')
    starts = [x['sample_start_monotonic_s'] for x in records] + [state['ended_at']]
    ends = [state['started_at']] + [x['sample_end_monotonic_s'] for x in records]
    gaps = [max(0, b-a) for a,b in zip(ends, starts)]
    if any(b < a for a, b in zip(ends, starts)) or gaps != result['sampling_gaps_s'] or max(gaps) > plan['max_gap_seconds'] or not result['coverage_qualified']:
        raise ValueError('sampling coverage not qualified')
    healthy = [x['own_vram_b'] for x in records if x.get('phase') == 'healthy' and x.get('hip_resident') is True and x['own_vram_b'] > 0]
    if (len(healthy) < plan['healthy_samples'] or
        len(healthy) != len([x for x in records if x.get('phase') == 'healthy']) or result['sample_count'] != len(records)):
        raise ValueError('insufficient healthy resident samples')
    kv = result['target_kv_b_from_log']
    matches = re.findall(r'llama_kv_cache: size =\s*([0-9.]+) MiB \(393216 cells,\s*16 layers,\s*4/1 seqs\), K \(q8_0\)', (root / 'server.log').read_text(errors='replace'))
    if not ns.finite(kv) or kv < 0 or len(matches) != 1 or float(matches[0]) * 1024**2 != kv:
        raise ValueError('target KV allocation unknown')
    value = max(healthy) - kv
    if value < 0 or value != result.get('healthy_sampled_max_non_kv_b'):
        raise ValueError('sampled non-KV value differs from records')
    return plan, result, records, value


def row_problems(row: Any):
    problems = ns.common_problems(row, schema=SCHEMA, optional_text=('protocol_id',))
    if not isinstance(row, dict) or not isinstance(row.get('extra'), dict): return problems
    try:
        extra = row['extra']; root = Path(row['results_path']).parent
        if not ns.results_present(row): raise ValueError('result changed')
        plan, result, records, value = _derive(root)
        for name in ('plan.json', 'samples.jsonl', 'server.log'):
            if ns.file_sha256(root / name) != extra['raw_sha256'][name]: raise ValueError(name + ' changed')
        if row['value'] != value or row['metric'] != 'sampled_healthy_non_kv_bytes' or row['protocol_id'] != '':
            raise ValueError('metric differs')
        if (extra['producer_sha256'] != plan['producer_sha256'] or extra['producer_files_sha256'] != plan['producer_files_sha256'] or
            extra['runtime_identity'] != result['runtime_identity'] or extra['grant'] != result['grant'] or
            extra['device'] != result['device'] or extra['coverage'] != result['sampling_gaps_s'] or
            row['reps'] != len([x for x in records if x['phase'] == 'healthy'])):
            raise ValueError('source or sample count differs')
        problems += ns.check_identity(row, {'result': row['results_sha256'], 'plan': extra['raw_sha256']['plan.json']}, 'kvu16a')
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        problems.append('native evidence missing, unknown, changed, or inconsistent')
    return problems + ns.self_hash_problems(row)


def record_run(output_dir: Path):
    """Called at original producer finalization; unknown observations emit no tuple."""
    root = Path(output_dir).resolve()
    try: plan, result, records, value = _derive(root)
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError): return None
    result_path = root / 'result.json'; result_hash = ns.file_sha256(result_path)
    raw = {name: ns.file_sha256(root / name) for name in ('plan.json', 'samples.jsonl', 'server.log')}
    now = datetime.now(timezone.utc).isoformat()
    row = {'schema': SCHEMA, 'run_id': root.name, 'producer': plan['producer_path'], 'emitted_at': now, 'date': now,
           'measurement_id': 'kvu16a_' + ns.content_hash({'result': result_hash, 'plan': raw['plan.json']})[:24],
           'metric': 'sampled_healthy_non_kv_bytes', 'value': value, 'unit': 'bytes', 'metric_direction': 'lower_better',
           'category': 'BASELINE', 'claim': 'Sampled healthy own-PID VRAM maximum minus observed target KV; not a peak or bound',
           'protocol_id': '', 'reps': len([x for x in records if x['phase'] == 'healthy']),
           'reps_basis': 'healthy in-window samples within one load-only process; not independent runs',
           'results_path': str(result_path), 'results_sha256': result_hash,
           'extra': {'raw_sha256': raw, 'producer_sha256': plan['producer_sha256'],
                     'producer_files_sha256': plan['producer_files_sha256'],
                     'coverage': result['sampling_gaps_s'], 'runtime_identity': result['runtime_identity'],
                     'grant': result['grant'], 'device': result['device']}}
    ns.seal(row)
    if problems := row_problems(row): raise ns.CaptureError('; '.join(problems))
    path = root / SIDECAR_NAME
    with path.open('x') as stream:
        stream.write(ns.canonical_json(row) + '\n'); stream.flush(); os.fsync(stream.fileno())
    return path


@register(SOURCE_KIND)
def project(native: Any):
    row = native.get('row') if isinstance(native, dict) else None
    if problems := row_problems(row): raise ProjectionError('invalid producer row: ' + '; '.join(problems))
    return ns.to_claim_tuple(row, source_kind=SOURCE_KIND, locator='kvu16a:' + row['run_id'],
                             sidecar_path=native.get('sidecar_path', ''))


def native_rows(sidecar: Path):
    sidecar = Path(sidecar)
    if not sidecar.is_file(): return ()
    rows = ns.load_rows(sidecar, row_problems)
    if rows is None: raise ProjectionError('KVU16a sidecar invalid or changed')
    return tuple({'row': row, 'sidecar_path': str(sidecar), 'attestation_present': ns.results_present(row)} for row in rows)


def frames_for_sidecar(sidecar: Path, *, as_of: str):
    return [frame for native in native_rows(sidecar) for frame in
            to_frames(project(native), as_of=as_of, adapter_id=ADAPTER_ID, authority='measurement')]
