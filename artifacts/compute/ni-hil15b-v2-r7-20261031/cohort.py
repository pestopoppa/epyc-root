#!/usr/bin/env python3
"""Resume only unexposed slots of the frozen HIL15b-v2 20 x 3 cohort."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
TASKSET_SHA = '0089c2a840bc40367433de754424b17ad9a5edca954b312513e6ecaa0abd4312'
MODEL = '/mnt/raid0/llm/models/Qwen3.6-35B-A3B-MTP-Q8_0.gguf'
PY = '/workspace/repos/epyc-orchestrator/.venv/bin/python'
SOURCE = '/mnt/raid0/llm/worktrees/mains/codex-ni-orchestrator'
EPYC_ROOT = '/mnt/raid0/llm/tmp/codex-ni-ap-legacy-status-wrap-20261030'
EPYC_ROOT_ADAPTER_SHA = {
    'l2_scan_capture.py':'abf418f5825fd520e1ce38ad49a4a961bbd72546b3b416f4370bfb220bc0bc81',
    'hil15a_auc.py':'c8a133eb0e38038892b8a830d598c01e7a0f76817914ff90414648faa8250c7f',
}


def atomic_json(path, data):
    with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, prefix=path.name+'.', delete=False) as f:
        tmp = Path(f.name)
        json.dump(data, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def status(out):
    slots = list((out / 'slots').glob('*')) if (out / 'slots').exists() else []
    exposed = len([p for p in slots if p.is_dir()])
    complete = len([p for p in slots if (p / 'COMPLETE.json').exists()])
    state = {'frozen_total':60, 'complete':complete,
             'exposed_incomplete_unknown':exposed-complete,
             'unexposed':60-exposed, 'full_result':complete==60,
             'terminal_exposure_complete':exposed==60,
             'partial':complete!=60,
             'state':('full' if complete==60 else
                      'terminal_inconclusive' if exposed==60 else 'resumable_window_partial')}
    atomic_json(out / 'STATUS.json', state)
    atomic_json(out / 'ASSESSMENT.json', {
        'schema':'hil15b_v2_frozen60_checkpoint/v1',
        'frozen_taskset_sha256':TASKSET_SHA,
        **state,
        'verdict':('PENDING GLOBAL ANALYSIS' if complete==60 else
                   'INCONCLUSIVE: original-denominator slots incomplete; unknowns are not failures or successes'),
        'quality_verdict':None,
    })
    return state


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--out-dir', required=True)
    p.add_argument('--server-url', required=True)
    p.add_argument('--server-pid', type=int, required=True)
    p.add_argument('--deadline-epoch', type=int, required=True)
    p.add_argument('--qualification', action='store_true')
    a = p.parse_args()
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    active_proc = None

    def interrupted(_sig, _frame):
        if active_proc is not None and active_proc.poll() is None:
            os.killpg(active_proc.pid, signal.SIGTERM)
            try:
                active_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(active_proc.pid, signal.SIGKILL)
                active_proc.wait(timeout=5)
        if not a.qualification:
            status(out)
        raise SystemExit(75)

    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    taskset = HERE / 'hil15b_v2_tasks.json'
    if hashlib.sha256(taskset.read_bytes()).hexdigest() != TASKSET_SHA:
        raise SystemExit('frozen taskset digest changed')
    tasks = json.loads(taskset.read_text())
    if len(tasks) != 20 or len({t['task_key'] for t in tasks}) != 20:
        raise SystemExit('frozen taskset shape changed')
    if a.qualification:
        # The native default task is outside the frozen set. Its result is only a
        # path/writer qualification, never a cohort attempt or efficacy verdict.
        tasks = [{'task_key':'qualification-arith-1','prompt':'Compute 17 * 23 and give only the number.',
                  'expect':r'\b391\b'}]
        slots = [(0, 0, tasks[0])]
        reserve_s = 15
    else:
        slots = [(rep, i, t) for rep in range(3) for i, t in enumerate(tasks)]
        reserve_s = 300
    for rep, index, task in slots:
        slot_id = f"{task['task_key']}-r{rep}"
        slot = out / ('qualification' if a.qualification else 'slots') / slot_id
        intent = slot / 'ATTEMPT-INTENT.json'
        complete = slot / 'COMPLETE.json'
        if slot.exists():
            # An exposed incomplete attempt stays UNKNOWN. Never redraw it.
            continue
        if time.time() + reserve_s >= a.deadline_epoch:
            if not a.qualification:
                status(out)
            return 75
        source_check = subprocess.run(['/usr/bin/python3', str(HERE / 'verify_source.py')],
                                      capture_output=True, text=True)
        if source_check.returncode != 0:
            (out / 'SOURCE-DRIFT.txt').write_text(source_check.stdout + source_check.stderr)
            if not a.qualification:
                status(out)
            return 75
        for name, expected in EPYC_ROOT_ADAPTER_SHA.items():
            path = Path(EPYC_ROOT) / 'scripts' / 'vidya' / 'adapters' / name
            if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                (out / 'ROOT-ADAPTER-DRIFT.txt').write_text(f'{path} changed')
                if not a.qualification:
                    status(out)
                return 75
        slot.mkdir(parents=True, exist_ok=False)
        task_file = slot / 'task.json'
        task_file.write_text(json.dumps([task], ensure_ascii=False))
        atomic_json(intent, {'slot_id':slot_id,'repeat_index':rep,'frozen_index':index,
                             'taskset_sha256':TASKSET_SHA,'task_json_sha256':hashlib.sha256(task_file.read_bytes()).hexdigest(),
                             'exposed_at_epoch':time.time(),'scope':'qualification' if a.qualification else 'frozen_cohort'})
        cmd = [PY, str(HERE / 'slot_entry.py'), '--repeat-index', str(rep), '--',
               '--out-dir', str(slot / 'native'), '--tasks', str(task_file), '--repeats', '1',
               '--min-task-keys', '1', '--min-dep-task-keys', '1', '--server-url', a.server_url,
               '--server-pid', str(a.server_pid), '--served-model', MODEL,
               '--epyc-root', EPYC_ROOT, '--belief-sidecar', '--run-id', slot_id]
        env = dict(os.environ, WINDOW_CONFIRMED='1', PYTHONHASHSEED='0')
        with (slot / 'native.log').open('w') as log:
            proc = subprocess.Popen(cmd, cwd=SOURCE, env=env, stdout=log,
                                    stderr=subprocess.STDOUT, start_new_session=True)
            active_proc = proc
            try:
                rc = proc.wait(timeout=max(1, a.deadline_epoch - time.time() - reserve_s))
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGTERM)
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait(timeout=5)
                if not a.qualification:
                    status(out)
                return 75
            finally:
                active_proc = None
        manifest = slot / 'native' / 'manifest.json'
        if rc != 0 or not manifest.exists():
            if not a.qualification:
                status(out)
            return 75
        m = json.loads(manifest.read_text())
        if m.get('verdict') != 'OK' or len(m.get('runs', [])) != 1 or m['runs'][0]['run_id'] != slot_id:
            if not a.qualification:
                status(out)
            return 75
        atomic_json(complete, {'slot_id':slot_id,'native_rc':rc,'native_manifest_sha256':
                               hashlib.sha256(manifest.read_bytes()).hexdigest(), 'at_epoch':time.time()})
        if a.qualification:
            return 0
        status(out)
    if a.qualification:
        return 75
    state = status(out)
    if state['terminal_exposure_complete']:
        env = dict(os.environ, PYTHONPATH=SOURCE)
        result = subprocess.run([PY, str(HERE / 'analyze.py')], cwd=SOURCE, env=env,
                                stdout=(out / 'analysis.log').open('w'), stderr=subprocess.STDOUT)
        if result.returncode != 0:
            return 1
    return 0 if state['terminal_exposure_complete'] else 75


if __name__ == '__main__':
    raise SystemExit(main())
