#!/usr/bin/env python3
"""Enroll one descriptive GPU A/A row into the canonical region-lock engine.

Requires the same code-owned enrollment as the native capture; default-off.
The row owner sets an independent, reviewed plan with exact id, STOP path,
result path, host-thread claim and minimum window; no grant is manufactured.
"""
from __future__ import annotations
import hashlib
import json
import os
import shlex
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
import run_gpu_aa as run

ENGINE = ROOT / 'scripts/coordination/rowflow/filler_run15.sh'


def launch_spec(aa, native, trust):
    pairs = run.validate_plans(aa, native)
    row = aa.get('row')
    if not isinstance(row, dict) or set(row) != {'id', 'regions', 'stopfile', 'min_window_s', 'port', 'dryrun_native_result', 'cgroup_parent', 'champion_git', 'champion_ref', 'champion_commit'}:
        raise ValueError('reviewed row binding required')
    if any(cell['source_commit'] != row['champion_commit'] for _, cell in pairs):
        raise ValueError('native source differs from champion')
    rid = row['id']
    if not isinstance(rid, str) or not rid or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for c in rid):
        raise ValueError('invalid row id')
    if row['regions'] != 'mi210_0,184-191':
        raise ValueError('unexpected GPU resource shape')
    stop = Path(row['stopfile'])
    if not stop.is_absolute() or '..' in stop.parts or stop.parent.resolve(strict=True) != stop.parent:
        raise ValueError('invalid stopfile')
    if type(row['min_window_s']) is not int or row['min_window_s'] < 300:
        raise ValueError('reviewed minimum window required')
    if type(row['port']) is not int or not 1024 <= row['port'] <= 65535:
        raise ValueError('invalid port')
    if any(cell['grant'] != {'id': rid, 'regions': row['regions'], 'stopfile': str(stop)}
           or entry['sweep']['port_base'] != row['port'] for entry,cell in pairs):
        raise ValueError('row, native plan and port differ')
    cgroup = Path(row['cgroup_parent'])
    if (not cgroup.is_absolute() or cgroup.resolve(strict=True) != cgroup
            or (cgroup != Path('/sys/fs/cgroup') and Path('/sys/fs/cgroup') not in cgroup.parents)
            or not (cgroup/'cgroup.controllers').is_file()):
        raise ValueError('delegated cgroup parent unavailable')
    if row['dryrun_native_result'] is not True:
        raise ValueError('rowflow must use a unique dryrun native result')
    result = Path(aa.get('result_path', ''))
    if (not result.is_absolute() or '..' in result.parts or result.parent.resolve(strict=True) != result.parent
            or (trust.capture_root != result.parent and trust.capture_root not in result.parent.parents)):
        raise ValueError('result outside capture root')
    cmd = shlex.join([sys.executable, '-B', str(HERE/'run_gpu_aa.py')])
    verify = shlex.join([sys.executable, '-B', str(HERE/'launch_gpu_aa.py'), '--verify-result'])
    return ['bash', str(ENGINE), '--id', rid, '--class', 'gpu', '--gpu-quiet', 'exclusive',
            '--claim-cpus', '72-95', '--role', 'bench', '--min-window', str(row['min_window_s']),
            '--stop', str(stop), '--port', str(row['port']), '--workdir', str(ROOT),
            '--cmd', cmd, '--complete-cmd', verify]


def load():
    plan_path, plan_digest, qualification_only = run.aa_enrollment.selected()
    trust = run.write_capture.enrolled()
    if getattr(trust, 'qualification_only', False) is not qualification_only:
        raise RuntimeError('A/A and V2 qualification modes differ')
    seals = {str(p.resolve()): h for p, h in trust.sources}
    for path in (HERE/'run_gpu_aa.py', HERE/'aa_enrollment.py', HERE/'calibrate_gpu_aa.py', Path(__file__), ENGINE):
        path = path.resolve(strict=True)
        if seals.get(str(path)) != hashlib.sha256(path.read_bytes()).hexdigest():
            raise RuntimeError('A/A source not independently enrolled')
    raw = Path(plan_path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != plan_digest:
        raise RuntimeError('A/A plan seal changed')
    aa = json.loads(raw); native = trust.plan()
    if aa.get('native_plan_sha256') != trust.plan_sha256:
        raise RuntimeError('native plan seal mismatch')
    spec = launch_spec(aa, native, trust)
    return trust, aa, native, spec, plan_digest, qualification_only


def verify_result(trust, aa, native, plan_digest, qualification_only):
    result = json.loads(Path(aa['result_path']).read_bytes())
    if (result.get('schema') != 'epyc.m4.gpu.aa.descriptive.v1' or result.get('gate_authorized') is not False
            or result.get('plan_sha256') != plan_digest
            or result.get('qualification_only') is not qualification_only
            or result.get('native_plan_sha256') != trust.plan_sha256):
        raise ValueError('invalid descriptive result')
    pairs = run.validate_plans(aa, native)
    expected = [str(Path(c['watch_result_path']).parent / 'native/run/capture-v2-0.json') for _, c in pairs]
    if result.get('capture_paths') != expected or len(result.get('pairs', [])) * 2 != len(expected):
        raise ValueError('capture denominator mismatch')
    records = []; reduction_cells = []
    for (entry, cell), path in zip(pairs, expected, strict=True):
        doc, _, value = run.validate_capture(Path(path), trust)
        rows = [json.loads(line) for line in Path(doc['requests_path']).read_text().splitlines() if line.strip()]
        x = {'id': entry['id'], 'role': cell['role'], 'source_commit': cell['source_commit'],
             'image_sha256': cell['files']['binary']['sha256'], 'recipe_sha256': run.seal_obj(cell['recipe']),
             'model_sha256': cell['files']['model']['sha256'], 'prompt_sha256': cell['files']['prompt']['sha256'],
             'np': cell['np'], 'pair': entry['pair'], 'arm': entry['arm'], 'request_count': cell['request_count']}
        reduction_cells.append(x)
        records.append({k: v for k,v in x.items() if k not in ('id','request_count')} | {
            'cell_id': entry['id'], 'plan_sha256': plan_digest, 'status':'COMPLETE',
            'cleanup_verified':True, 'requests':rows, 'aggregate_decode_tps':value})
    replay = run.calibrate_gpu_aa.reduce({'schema':'epyc.m4.gpu.aa.plan.v1',
        'intent':'descriptive_only', 'cells':reduction_cells}, records, plan_digest)
    if result.get('pairs') != replay['pairs'] or result.get('decision') is not None:
        raise ValueError('descriptive aggregate does not rederive')
    return True


def spec_digest(spec):
    return hashlib.sha256(json.dumps(spec, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


def render_launcher(spec, cgroup_parent):
    """A static rowflow-readable engine invocation, checked against real enrollment."""
    checker = shlex.join([sys.executable, '-B', str(Path(__file__).resolve()), '--check-launcher', spec_digest(spec)])
    return ('#!/bin/bash\nset -euo pipefail\n'
            'export M4_OUTER_OWNER_PID=$$\n'
            "export M4_OUTER_OWNER_BIRTH=$(sed 's/.*) //' /proc/$$/stat | awk '{print $20}')\n"
            'export M4_DELEGATED_CGROUP_PARENT=' + shlex.quote(cgroup_parent) + '\n'
            + checker + '\nexec ' + shlex.join(spec) + '\n')


def main():
    if len(sys.argv) == 3 and sys.argv[1] == '--check-launcher':
        # The static engine invocation always derives from the sealed *real*
        # row. run15 itself substitutes the fixture STOP in dry-run mode.
        old = os.environ.get('FILLER_DRYRUN')
        os.environ['FILLER_DRYRUN'] = '0'
        try:
            _, _, _, spec, _, _ = load()
        finally:
            if old is None: os.environ.pop('FILLER_DRYRUN', None)
            else: os.environ['FILLER_DRYRUN'] = old
        if spec_digest(spec) != sys.argv[2]:
            raise RuntimeError('static launcher differs from sealed real row')
        return 0
    trust, aa, native, spec, plan_digest, qualification_only = load()
    if sys.argv[1:] == ['--verify-result']:
        return 0 if verify_result(trust, aa, native, plan_digest, qualification_only) else 1
    if len(sys.argv) == 3 and sys.argv[1] == '--emit-launcher':
        output = Path(sys.argv[2])
        if not output.is_absolute(): raise ValueError('absolute launcher path required')
        with output.open('x') as fh:
            fh.write(render_launcher(spec, aa['row']['cgroup_parent'])); fh.flush(); os.fsync(fh.fileno())
        output.chmod(0o750)
        return 0
    if len(sys.argv) != 1:
        raise ValueError('unexpected argument')
    os.execv('/usr/bin/bash', spec)


if __name__ == '__main__':
    raise SystemExit(main())
