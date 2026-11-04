"""Prospective native context for YARN-E1-MEM phase peaks; no grade or retrospective capture."""
import hashlib
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def emit(d, attribution):
    d = Path(d)
    root = d.parent.parent
    launch = json.loads((d / 'launch.json').read_text())
    proof = json.loads((d / 'runtime-proof.json').read_text())
    model = json.loads((root / 'model-pin.json').read_text())
    image = json.loads((root / 'image-binding.json').read_text())
    record = d / 'phase-attribution.json'
    raw = json.loads(record.read_text())
    if raw != attribution or proof['pid'] != launch['pid'] or not image['source_commit'] or not model['sha256']:
        raise ValueError('missing or inconsistent native launch context')
    kfd = Path(attribution['kfd'])
    shim = Path(attribution['shim'])
    calls = Path(attribution['native_calls'])
    if any(not p.is_file() or not p.resolve().is_relative_to(d.resolve()) for p in (kfd, shim, calls)):
        raise ValueError('missing or out-of-run native trace')
    samples = [json.loads(line) for line in kfd.read_text().splitlines() if line.strip()]
    native_calls = [json.loads(line) for line in calls.read_text().splitlines() if line.strip()]
    # Native artifact locators are relative to this retained run directory.
    # Absolute scratch paths would be invalid after keeper reclamation.
    locator = lambda p: p.resolve().relative_to(d.resolve()).as_posix()
    rows = []
    for stage in ('128k', '240k'):
        a = attribution['stages'].get(stage, {})
        value = a.get('own_kfd_peak_gib')
        if type(value) not in (int, float) or not math.isfinite(value) or value <= 0 or a.get('requests', 0) < 6:
            raise ValueError('missing phase samples')
        stage_calls = [x for x in native_calls if x.get('stage') == stage]
        needles = [x for x in stage_calls if x.get('kind') == 'needle']
        local = [x for x in stage_calls if x.get('kind') == 'local']
        if (len(stage_calls) != 6 or len(needles) != 5 or len(local) != 1
                or {x.get('q_index') for x in needles} != set(range(5))
                or any(x.get('http_ok') is not True for x in stage_calls)
                or a.get('requests') != len(stage_calls)):
            raise ValueError('incomplete, duplicated or failed stage requests')
        if not (a['start'] <= a['end'] and a['start'] >= launch['at']):
            raise ValueError('phase outside process lifetime')
        inside = [x for x in samples if a['start'] <= x['t'] <= a['end'] and x.get('pid_vram_gib') is not None and proof['pid'] in x.get('kfd_pids', [])]
        if not inside or max(x['pid_vram_gib'] for x in inside) != value:
            raise ValueError('phase peak is not reproduced by own-PID in-window samples')
        row = {'schema': 'yarn-e1-mem.native-measurement.v1', 'source_kind': 'yarn-e1-mem-phase',
               'measurement_id': f"{os.environ.get('FILLER_ID', 'missing-run')}:{stage}:own-kfd-peak",
               'metric': 'own_pid_kfd_peak', 'value': value, 'unit': 'GiB',
               'metric_direction': 'lower_better', 'category': 'BASELINE',
               'claim': 'own-PID VRAM peak sampled during phase requests', 'protocol_id': '',
               'reps': 1, 'reps_basis': 'one phase from one server run; samples are not independent repetitions', 'date': datetime.now(timezone.utc).date().isoformat(),
               'record_file': locator(record), 'record_sha256': digest(record),
               'run_id': os.environ.get('FILLER_ID'), 'window': {'start': a['start'], 'end': a['end']},
               'arm': 'A0', 'phase': stage, 'pid': launch['pid'], 'launch': launch,
               'runtime_proof': proof, 'model_pin': model, 'image_binding': image,
               'input_manifest_sha256': digest(root / 'inputs/manifest.json'),
               'producer_manifest_sha256': digest(root / 'SOURCE.sha256'),
               'kfd_path': locator(kfd), 'kfd_sha256': digest(kfd),
               'hip_trace_path': locator(shim), 'hip_trace_sha256': digest(shim),
               'native_calls': locator(calls), 'native_calls_sha256': digest(calls), 'requests': a['requests']}
        if not row['run_id']:
            raise ValueError('missing run identity')
        row['row_sha256'] = hashlib.sha256(json.dumps(row, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
        rows.append(row)
    target = d / 'belief_measurements.jsonl'
    tmp = target.with_suffix('.tmp')
    tmp.write_text(''.join(json.dumps(row, sort_keys=True, allow_nan=False) + '\n' for row in rows))
    tmp.replace(target)
    return target
