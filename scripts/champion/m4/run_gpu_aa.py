#!/usr/bin/env python3
"""Run independently bound, descriptive M4 GPU A/A process pairs.

Each calibration arm is an independent V2 BASELINE/off capture; A1/A2 label
pairs in the separate sealed calibration plan and never denote a candidate.
This entry remains disabled until code-owned enrollment is reviewed and bound.
"""
from __future__ import annotations
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / 'scripts/benchmark/m4_gpu_speed'))
sys.path.insert(0, str(ROOT / 'scripts/vidya'))
sys.path.insert(0, str(ROOT / 'scripts/vidya/adapters'))
import aa_enrollment
import calibrate_gpu_aa
import write_capture
from m4_gpu_speed_v2 import validate_capture


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def seal_obj(obj):
    return sha(json.dumps(obj, sort_keys=True, separators=(',', ':'), allow_nan=False).encode())


def validate_plans(aa, native):
    if aa.get('schema') != 'epyc.m4.gpu.aa.execution.v1' or aa.get('intent') != 'descriptive_only':
        raise ValueError('invalid A/A plan or intent')
    cells = aa.get('cells')
    if not isinstance(cells, list) or not cells or len(cells) % 2:
        raise ValueError('positive even cell count required')
    native_cells = native.get('cells')
    if not isinstance(native_cells, dict):
        raise ValueError('native cells missing')
    seen = set(); watches = set(); groups = {}; output = []
    fields = ('role', 'arm', 'source_commit', 'model', 'recipe', 'argv', 'environment', 'device', 'np', 'files', 'ggml', 'grant', 'request_count', 'vram_limit_bytes', 'kfd_vram_file', 'device_vram_path')
    for entry in cells:
        if not isinstance(entry, dict) or set(entry) != {'id', 'native_cell', 'arm', 'pair', 'sweep'}:
            raise ValueError('invalid calibration cell')
        key = entry['native_cell']; cell_id = entry['id']
        if not isinstance(key, str) or not isinstance(cell_id, str) or not key or not cell_id or key in seen:
            raise ValueError('duplicate or invalid native cell')
        seen.add(key)
        cell = native_cells[key]
        if cell.get('arm') != 'BASELINE' or entry['arm'] not in ('A1', 'A2') or type(entry['pair']) is not int or entry['pair'] < 0:
            raise ValueError('A/A requires BASELINE only and a valid pair label')
        if any(k not in cell for k in fields) or not isinstance(cell.get('watch_result_path'), str):
            raise ValueError('unbound native identity')
        if any(a == flag or a.startswith(flag + '=') for a in cell['argv']
               for flag in ('--prefill-order', '--prefill-contend-cap')):
            raise ValueError('calibration must use M4 off')
        watch = Path(cell['watch_result_path'])
        if not watch.is_absolute() or watch.name != 'watch-result.json' or watch in watches:
            raise ValueError('unique absolute watcher paths required')
        watches.add(watch)
        sweep = entry['sweep']
        keys = {'question_pool', 'prompt_limit', 'prompt_seed', 'tier', 'threads', 'context_size', 'ubatch_size', 'kv_type', 'n_predict', 'warmup_prompts', 'warmup_n_predict', 'startup_timeout', 'request_timeout', 'port_base', 'extra_server_args', 'no_mlock', 'no_ttft', 'allow_host_health_warning'}
        if not isinstance(sweep, dict) or set(sweep) != keys:
            raise ValueError('sweep configuration not fully bound')
        for k in ('prompt_limit', 'threads', 'context_size', 'ubatch_size', 'n_predict', 'startup_timeout', 'request_timeout', 'port_base'):
            if type(sweep[k]) is not int or sweep[k] <= 0:
                raise ValueError('invalid positive sweep parameter')
        for k in ('prompt_seed', 'tier', 'warmup_prompts', 'warmup_n_predict'):
            if type(sweep[k]) is not int or sweep[k] < 0:
                raise ValueError('invalid nonnegative sweep parameter')
        if any(type(sweep[k]) is not bool for k in ('no_mlock', 'no_ttft', 'allow_host_health_warning')):
            raise ValueError('explicit boolean sweep controls required')
        if not isinstance(sweep['extra_server_args'], list) or not all(isinstance(x, str) and x for x in sweep['extra_server_args']):
            raise ValueError('invalid server arguments')
        if any(a == flag or a.startswith(flag + '=') for a in sweep['extra_server_args']
               for flag in ('--prefill-order', '--prefill-contend-cap')):
            raise ValueError('calibration cannot override M4 treatment')
        if sweep['question_pool'] != cell['files']['prompt']['path']:
            raise ValueError('prompt input differs from native plan')
        # All execution parameters except the unique watcher path are identical
        # within an A1/A2 pair, including source, process argv and launch settings.
        identity = seal_obj({k: cell[k] for k in fields} | {'sweep': sweep})
        pair_key = (cell['role'], cell['np'], entry['pair'])
        group = groups.setdefault(pair_key, {})
        if entry['arm'] in group:
            raise ValueError('duplicate pair arm')
        group[entry['arm']] = identity
        output.append((entry, cell))
    if len({item[0]['id'] for item in output}) != len(output):
        raise ValueError('duplicate calibration id')
    if any(set(v) != {'A1', 'A2'} or v['A1'] != v['A2'] for v in groups.values()):
        raise ValueError('unmatched or unequal A/A pair')
    # Explicit alternation avoids a full-block time-order confound.
    for i in range(0, len(output), 2):
        a, b = output[i][0], output[i + 1][0]
        if (a['pair'] != b['pair'] or {a['arm'], b['arm']} != {'A1', 'A2'}
                or output[i][1]['role'] != output[i + 1][1]['role']
                or output[i][1]['np'] != output[i + 1][1]['np']):
            raise ValueError('pairs must be adjacent')
    return output


def command(entry, cell, work):
    sweep = entry['sweep']; binary = cell['files']['binary']['path']
    cmd = [sys.executable, '-B', str(ROOT / 'scripts/benchmark/m4_gpu_speed/launcher.py'),
           '--run-id', 'run', '--output-root', str(work), '--model', 'gate=' + cell['model'],
           '--question-pool', sweep['question_pool'], '--np-levels', str(cell['np']), '--llama-server', binary]
    for flag, field in (('--prompt-limit','prompt_limit'),('--prompt-seed','prompt_seed'),('--tier','tier'),('--threads','threads'),('--context-size','context_size'),('--ubatch-size','ubatch_size'),('--kv-type','kv_type'),('--n-predict','n_predict'),('--warmup-prompts','warmup_prompts'),('--warmup-n-predict','warmup_n_predict'),('--startup-timeout','startup_timeout'),('--request-timeout','request_timeout'),('--port-base','port_base')):
        cmd.extend((flag, str(sweep[field])))
    for arg in sweep['extra_server_args']:
        cmd.append('--extra-server-arg=' + arg)
    for field, flag in (('no_mlock','--no-mlock'),('no_ttft','--no-ttft'),('allow_host_health_warning','--allow-host-health-warning')):
        if sweep[field]: cmd.append(flag)
    return cmd


def check_champion(aa):
    row = aa.get('row', {})
    repo, ref, expected = row.get('champion_git'), row.get('champion_ref'), row.get('champion_commit')
    if (repo != '/mnt/raid0/llm/llama.cpp'
            or ref != 'refs/heads/ak/champion/llama-cpp-ffc1bac82eec'
            or not isinstance(expected, str) or not re.fullmatch('[0-9a-f]{40}', expected)):
        raise RuntimeError('invalid independent champion binding')
    proc = subprocess.run(['git', '-C', repo, 'rev-parse', '--verify', ref],
                          capture_output=True, text=True, timeout=10, check=True)
    if proc.stdout.strip() != expected:
        raise RuntimeError('champion ref moved; recut required')
    return expected


def execute_cell(command_argv, env, qualification_only):
    """Return 75 on the keeper's controlled first-unit qualification stop."""
    stop = Path(env.get('FILLER_STOPFILE', ''))
    if qualification_only and stop.is_absolute() and stop.exists():
        return 75
    try:
        subprocess.run(command_argv, env=env, check=True)
    except subprocess.CalledProcessError:
        if qualification_only and stop.is_absolute() and stop.exists():
            return 75
        raise
    return 0


def qualification_unit(env, capture_path, doc, plan_digest):
    """Emit the keeper's nonce-scoped first unit, never a measurement warrant."""
    dd = Path(env.get('FILLER_DRYRUN_DIR', ''))
    result = Path(env.get('FILLER_DRYRUN_RESULT_PATH', ''))
    if (not dd.is_absolute() or dd.resolve(strict=True) != dd or not result.is_absolute()
            or result.name != 'native-result.json' or not result.parent.name.startswith('attempt-')
            or result.parent.parent != dd / 'native-attempts'
            or result.parent.resolve(strict=True) != result.parent):
        raise RuntimeError('invalid keeper qualification result path')
    payload = {'schema':'epyc.m4.gpu.aa.qualification-unit.v1', 'qualification_only':True,
               'native_capture':str(capture_path), 'native_capture_sha256':sha(capture_path.read_bytes()),
               'plan_sha256':plan_digest, 'native_plan_sha256':doc['plan_sha256']}
    with result.open('x') as fh:
        json.dump(payload, fh, sort_keys=True, allow_nan=False)
        fh.write('\n'); fh.flush(); os.fsync(fh.fileno())


def main():
    plan_path, plan_digest, qualification_only = aa_enrollment.selected()
    trust = write_capture.enrolled()
    if getattr(trust, 'qualification_only', False) is not qualification_only:
        raise RuntimeError('A/A and V2 qualification modes differ')
    seals = {str(p.resolve()): h for p, h in trust.sources}
    # Enrollment and orchestrator/reducer are part of the separately reviewed
    # native trust root, so replacing the A/A driver also invalidates the run.
    for path in (HERE / 'run_gpu_aa.py', HERE / 'aa_enrollment.py', HERE / 'calibrate_gpu_aa.py', HERE / 'launch_gpu_aa.py', ROOT / 'scripts/coordination/rowflow/filler_run15.sh'):
        path = path.resolve(strict=True)
        if seals.get(str(path)) != sha(path.read_bytes()):
            raise RuntimeError('A/A source not independently enrolled')
    aa_path = Path(plan_path).resolve(strict=True)
    raw = aa_path.read_bytes()
    if sha(raw) != plan_digest:
        raise RuntimeError('A/A plan seal changed')
    aa = json.loads(raw); native = trust.plan()
    if aa.get('native_plan_sha256') != trust.plan_sha256:
        raise RuntimeError('native plan is not independently bound')
    selected = validate_plans(aa, native)
    expected_champion = check_champion(aa)
    if any(cell['source_commit'] != expected_champion for _, cell in selected):
        raise RuntimeError('native source is not the bound champion')
    output = Path(aa['result_path'])
    if (not output.is_absolute() or '..' in output.parts or output.exists()
            or output.parent.resolve(strict=True) != output.parent
            or (trust.capture_root != output.parent and trust.capture_root not in output.parent.parents)):
        raise RuntimeError('result path unavailable, noncanonical or outside capture root')
    records = []; reduction_cells = []
    for entry, cell in selected:
        # Re-resolve immediately before each admitted process.
        check_champion(aa)
        # grant and STOP/HOLD are enforced again by the actual V2 launcher.
        watch_dir = Path(cell['watch_result_path']).parent
        if (not watch_dir.is_absolute() or '..' in watch_dir.parts
                or watch_dir.parent.resolve(strict=True) != watch_dir.parent
                or (trust.capture_root != watch_dir.parent and trust.capture_root not in watch_dir.parent.parents)):
            raise RuntimeError('watcher outside capture root or noncanonical path')
        watch_dir.mkdir(mode=0o700, exist_ok=False)
        work = watch_dir / 'native'
        env = dict(os.environ, M4_PLAN_CELL=entry['native_cell'], M4_WATCH_DIR=str(watch_dir))
        sensitive = ('LD_', 'GGML_', 'LLAMA_', 'HSA_', 'HIP_', 'ROCR_', 'OMP_', 'KMP_')
        planned_env = cell['environment']
        if any(not isinstance(k, str) or not isinstance(v, str) or not k.startswith(sensitive)
               for k, v in planned_env.items()):
            raise RuntimeError('invalid independently bound runtime environment')
        # Do not inherit unbound device or library overrides from the caller.
        env = {k: v for k, v in env.items() if not k.startswith(sensitive)}
        env.update(planned_env)
        if execute_cell(command(entry, cell, work), env, qualification_only) == 75:
            return 75
        capture_path = work / 'run' / 'capture-v2-0.json'
        doc, expected, value = validate_capture(capture_path, trust)
        if qualification_only and not records:
            qualification_unit(env, capture_path, doc, plan_digest)
        rows = [json.loads(line) for line in Path(doc['requests_path']).read_text().splitlines() if line.strip()]
        x = {'id': entry['id'], 'role': cell['role'], 'source_commit': cell['source_commit'],
             'image_sha256': cell['files']['binary']['sha256'], 'recipe_sha256': seal_obj(cell['recipe']),
             'model_sha256': cell['files']['model']['sha256'], 'prompt_sha256': cell['files']['prompt']['sha256'],
             'np': cell['np'], 'pair': entry['pair'], 'arm': entry['arm'], 'request_count': cell['request_count']}
        reduction_cells.append(x)
        records.append({k: v for k,v in x.items() if k not in ('id','request_count')} | {
            'cell_id': entry['id'], 'plan_sha256': plan_digest, 'status': 'COMPLETE',
            'cleanup_verified': True, 'requests': rows, 'aggregate_decode_tps': value})
    check_champion(aa)
    result = calibrate_gpu_aa.reduce({'schema':'epyc.m4.gpu.aa.plan.v1', 'intent':'descriptive_only', 'cells':reduction_cells}, records, plan_digest)
    result.update({'qualification_only': qualification_only, 'native_plan_sha256': trust.plan_sha256, 'capture_paths': [str(Path(c['watch_result_path']).parent / 'native/run/capture-v2-0.json') for _,c in selected]})
    with output.open('x') as fh:
        json.dump(result, fh, sort_keys=True, allow_nan=False)
        fh.write('\n'); fh.flush(); os.fsync(fh.fileno())
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
