#!/usr/bin/env python3
"""Bounded native lifecycle validation; consumes inputs prepared outside grants."""
import dataclasses
import importlib.util
import json
import os
from pathlib import Path
import signal
import sys
import time
import threading

D = Path(__file__).resolve().parent
MODEL = Path('/mnt/raid0/llm/models/Qwen3.6-35B-A3B-MTP-Q8_0.gguf')
BINARY = Path('/mnt/raid0/llm/kernels/production/gpu/llama-server')
PORT = 19761
ACTIVE = None
STOPPED = False


def load_runner():
    spec = importlib.util.spec_from_file_location('k35_native', D / 'scripts/benchmark/k35_stack_context_matrix_runner.py')
    m = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    return m


def identity(path):
    s = path.stat()
    return {'path': str(path.resolve()), 'dev': s.st_dev, 'ino': s.st_ino,
            'size': s.st_size, 'mtime_ns': s.st_mtime_ns}


def scenarios(m):
    base = next(s for s in m.SCENARIOS if s.name == 'frontdoor_gpu_native_mtp')
    if base.model != MODEL:
        raise RuntimeError('expected existing 35B same-file native MTP scenario')
    no = dataclasses.replace(base, name='kvu16h_35b_no_spec', request_spec_n_max=0,
                             model=MODEL, threads=4 if os.environ.get('FILLER_SMOKE') == '1' else 8,
                             parallel=1, ubatch=512,
                             slot_save_path=None, max_context=4096)
    yes = dataclasses.replace(no, name='kvu16h_35b_native_mtp', request_spec_n_max=None,
                              description='Independent native MTP server for lifecycle validation')
    return (no, yes)


def check_result(m, r):
    return r.get('status') == 'ok' and m.cleanup_proved_complete(r.get('cleanup'))


def stopped():
    return STOPPED or Path(os.environ['FILLER_STOPFILE']).exists() or time.time() + 150 >= float(os.environ['FILLER_DEADLINE'])


def stop(signum, frame):
    global STOPPED
    STOPPED = True
    if ACTIVE is not None and ACTIVE.poll() is None:
        ACTIVE.send_signal(signal.SIGTERM)


def grant_affinity():
    declared = set()
    for chunk in os.environ['FILLER_CPUS'].split(','):
        ends = [int(n) for n in chunk.split('-')]
        declared.update(range(ends[0], ends[-1] + 1))
    allowed = sorted(os.sched_getaffinity(0) & declared)
    if os.environ.get('FILLER_SMOKE') == '1':
        if len(allowed) < 4:
            raise RuntimeError('smoke requires four CPUs within actual grant affinity')
        allowed = allowed[:4]
    if not allowed:
        raise RuntimeError('no CPUs within actual grant affinity')
    os.sched_setaffinity(0, allowed)
    if os.sched_getaffinity(0) != set(allowed):
        raise RuntimeError('failed to apply actual grant affinity')
    return allowed


def watch_stop(done):
    while not done.wait(0.1):
        if stopped():
            stop(None, None)
            # Bound a server that ignores TERM; retain the captured Popen handle.
            if not done.wait(3):
                child = ACTIVE
                if child is not None and child.poll() is None:
                    child.kill()
            return


def owned_spawn(original_spawn, argv, **kwargs):
    global ACTIVE
    is_server = str(BINARY) in argv
    if is_server:
        kwargs['start_new_session'] = False
        argv = [sys.executable, str(D / 'parent_exec.py'), str(os.getpid()), *argv]
    child = original_spawn(argv, **kwargs)
    if is_server:
        ACTIVE = child
        try:
            with open(os.environ['FILLER_PIDFILE'], 'a') as f:
                f.write(str(child.pid) + '\n'); f.flush(); os.fsync(f.fileno())
        except BaseException:
            child.kill(); child.wait(timeout=10)
            raise
        if STOPPED:
            child.send_signal(signal.SIGTERM)
    return child


def main():
    global ACTIVE
    m = load_runner()
    prepared = json.loads((D / 'prepared.json').read_text())
    # Cheap identity checks only. Source/binary digests and GGUF header were verified in preparation.
    for item in prepared['identities']:
        if identity(Path(item['path'])) != item:
            raise RuntimeError('prepared input identity changed: ' + item['path'])
    affinity = grant_affinity()
    prompt = (D / 'prompt.txt').read_text()
    m.prompt_for_context = lambda *_: prompt
    ss = scenarios(m)
    m.SCENARIOS = ss
    native = os.environ.get('FILLER_DRYRUN') == '1'
    output = Path(os.environ.get('FILLER_DRYRUN_DIR', str(D / 'run'))) / 'native-cells' if native else D / 'run'
    output.mkdir(parents=True, exist_ok=True)
    destination = Path(os.environ['FILLER_DRYRUN_RESULT_PATH']) if native else D / 'RESULT.json'
    if destination.exists():
        raise RuntimeError('refusing stale result path')
    args = m.parse_args(['--binary', str(BINARY), '--max-tokens', '16', '--min-completion-tokens', '1',
                         '--startup-timeout', '120', '--request-timeout', '45'])
    original_spawn = m.subprocess.Popen
    def spawn(argv, **kwargs):
        return owned_spawn(original_spawn, argv, **kwargs)
    m.subprocess.Popen = spawn
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    done = threading.Event()
    watcher = threading.Thread(target=watch_stop, args=(done,), daemon=True)
    watcher.start()
    try:
        return execute_cells(m, args, ss, native, output, destination, affinity)
    finally:
        done.set()
        watcher.join(timeout=5)
        m.subprocess.Popen = original_spawn


def execute_cells(m, args, ss, native, output, destination, affinity):
    global ACTIVE
    results = []
    for i, s in enumerate(ss[:1] if native else ss):
        if stopped():
            return 75
        blockers = m.collect_process_blockers()
        if blockers:
            raise RuntimeError('host has other inference workloads: ' + repr(blockers))
        cell = {'scenario': s.name, 'port': PORT + i, 'nominal_context': 2048, 'rep': 1,
                'server_argv': m.build_server_argv(s, binary=BINARY, port=PORT + i,
                                                  nominal_context=2048, max_tokens=16)}
        m.write_json(output / ('cell-' + str(i) + '.json'), cell)
        r = m.run_cell(cell, args, output)
        ACTIVE = None
        if not check_result(m, r) or STOPPED:
            return 2
        if i == 0 and r.get('server_no_draft') is not True:
            raise RuntimeError('missing dedicated no-draft evidence')
        results.append(r)
    payload = {'schema': 'epyc.kvu16h.native-lifecycle.v1', 'status': 'ok',
               'scope': 'single no-draft qualification' if native else 'two independent server lifetimes',
               'results': results, 'measurement_claim': False, 'worker_affinity': affinity}
    m.write_json(destination, payload)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
