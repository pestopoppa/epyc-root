#!/usr/bin/env python3
"""Keeper-only CY2 adapter; historical fixtures and scoring remain unchanged.

Sources are loaded from immutable git objects, never copied into an evidence
packet. Preparation writes INPUTS.json before publication. No model hashing,
tokenization or download occurs under the grant. No checkpoint is fabricated.
"""
from __future__ import annotations
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time
import types

RESEARCH = '/mnt/raid0/llm/epyc-inference-research'
REV = '0e4321f24bae29355333fcf2cb712a41ce080e2f'
BASE = 'scripts/benchmark/yarn_e1/'
STORE = Path('/mnt/raid0/llm/kernels/builds/cpu-20260921-ffc1bac82')
FIXTURES = Path('/mnt/raid0/llm/tmp/yarn-e1-20261004')
PORT = 18762


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def load_pinned(name, rel):
    source = subprocess.check_output(['git', '-C', RESEARCH, 'show', REV + ':' + BASE + rel])
    module = types.ModuleType(name)
    module.__file__ = str(Path(RESEARCH) / BASE / rel)
    sys.modules[name] = module
    exec(compile(source, 'git:' + REV + ':' + rel, 'exec'), module.__dict__)
    return module


def load_runner():
    load_pinned('yarn_proof', 'yarn_proof.py')
    load_pinned('yarn_needle', 'yarn_needle.py')
    load_pinned('cpu_window_gate', 'cpu_leg/cpu_window_gate.py')
    runner = load_pinned('yarn_cpu_leg', 'cpu_leg/yarn_cpu_leg.py')
    runner.INPUTS = FIXTURES / 'cpu_leg/inputs'
    runner.YN.INPUTS = FIXTURES / 'inputs'
    runner.PORT = PORT
    return runner


def prepared_stat(path):
    st = Path(path).stat()
    return dict(size=st.st_size, mtime_ns=st.st_mtime_ns, ino=st.st_ino, dev=st.st_dev)


def check_inputs(inputs):
    if inputs['research_commit'] != REV:
        raise ValueError('wrong research revision')
    if prepared_stat(inputs['model']) != inputs['model_stat']:
        raise ValueError('model changed after preparation')
    for name, expected in inputs['files'].items():
        if digest(name) != expected:
            raise ValueError('prepared file changed: ' + name)
    if str(Path('/mnt/raid0/llm/kernels/production/cpu').resolve()) != str(STORE / 'bin'):
        raise ValueError('v10 CPU production store changed')


def server_argv(runner, cpus):
    a = runner.ARMS['CY2']
    return [str(STORE / 'bin/llama-server'), '-m', a['model'], '--host', '127.0.0.1',
            '--port', str(PORT), '-np', '1', '-c', str(a['ctx']), '-t', str(len(cpus)),
            '-tb', str(len(cpus)), '-ub', '2048', '--flash-attn', 'on', '--jinja',
            *a['kv'], '--no-mmap', '--cache-ram', '0', '--chat-template-file', runner.TEMPLATE,
            '--reasoning', 'off', '--device', 'none', '--slot-save-path', str(runner.SLOTS) + '/',
            *runner.PROOF_LOG_FLAGS, *a['flags']]


def stop_own(child):
    if child is not None and child.poll() is None:
        child.terminate()
        try:
            child.wait(timeout=20)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait(timeout=20)
    if child is not None and child.poll() is None:
        raise RuntimeError('own server did not exit')


def install_server(runner, command, deadline):
    """Replace legacy hardcoded claim/PID discovery with a direct owned child.

    The filler engine owns region-lock; this process inherits its CPU affinity.
    Every start (including startup failures and interrupted HTTP calls) is reaped
    by the adapter's finally block. Native proof remains mandatory in run().
    """
    children = []
    class Server(runner.Server):
        def argv(self):
            return command

        def start(self):
            with socket.socket() as sock:
                if sock.connect_ex(('127.0.0.1', PORT)) == 0:
                    raise RuntimeError('scratch port occupied')
            runner.SLOTS.mkdir(parents=True, exist_ok=True)
            env = dict(os.environ)
            for key in ('LLAMA_SERVER_SLOTS_DEBUG', 'GGML_CUDA_GDN_STATE_BF16', 'GGML_CUDA_FA_MASK_SKIP'):
                env.pop(key, None)
            env.update(LD_LIBRARY_PATH=str(STORE / 'bin'), GGML_IQK='1', OMP_PROC_BIND='spread',
                       OMP_PLACES='cores', OMP_WAIT_POLICY='active', OMP_DYNAMIC='false')
            with self.log.open('a') as stream:
                self.wrapper = subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT, env=env)
            children.append(self.wrapper)
            self.pid = self.wrapper.pid
            while time.time() < min(deadline, self.started + 600):
                if self.wrapper.poll() is not None:
                    raise RuntimeError('own server exited at startup')
                status, _ = runner.YN.http_json(f'http://127.0.0.1:{PORT}/health', timeout=2)
                if status == 200:
                    maps = Path(f'/proc/{self.pid}/maps').read_text()
                    dsos = {line.split()[-1] for line in maps.splitlines()
                            if '/' in line and ('libggml' in line or 'libllama' in line)}
                    if not dsos or not any('libggml-cpu' in p for p in dsos):
                        raise RuntimeError('CPU DSO residency missing')
                    if any(not Path(p).resolve().is_relative_to(STORE) for p in dsos):
                        raise RuntimeError('foreign ggml/llama DSO resident')
                    (runner.RESULTS/'live-process.json').write_text(json.dumps(dict(
                        pid=self.pid, argv=command, affinity=sorted(os.sched_getaffinity(self.pid)), dsos=sorted(dsos))))
                    return
                time.sleep(1)  # keeper-owned payload only
            raise RuntimeError('startup deadline')

        def __init__(self, *args):
            super().__init__(*args)
            self.started = time.time()

        def stop(self):
            stop_own(self.wrapper)
            self.pid = None
    runner.Server = Server
    return children


def summarize(out, rc):
    path = out/'CY2/probe_510000.json'
    result = dict(schema='yarn-cpu-continuation-v1', rc=rc, research_commit=REV,
                  verdict='INCOMPLETE', higher_better=['needle_correct', 'decode_tps'])
    if path.exists():
        probe = json.loads(path.read_text())
        needles, dec = probe['needles'], probe['decode']
        result.update(depth=dec['depth'], needle_correct=sum(n['grade'] == 'correct' for n in needles),
                      needle_attempted=len(needles), decode_tps=dec['decode_tps'],
                      predicted_n=dec.get('predicted_n'), decode_http=dec['http'],
                      local=probe['local']['degeneracy']['cls'])
        if rc == 0 and result['depth'] >= 500000 and len(needles) == 5 and dec['http'] == 200 and \
                dec.get('predicted_n') == 128 and isinstance(dec['decode_tps'], (float, int)) and dec['decode_tps'] > 0:
            result['verdict'] = 'PASS' if result['needle_correct'] >= 4 and result['local'] == 'OK' else 'FAIL'
    return result


def main():
    # Guard before importing the legacy runner or creating any state.
    if not os.environ.get('FILLER_ID') or not os.environ.get('FILLER_END'):
        raise RuntimeError('keeper grant required')
    deadline = min(float(os.environ['FILLER_END']), float(os.environ.get('FILLER_DEADLINE', os.environ['FILLER_END'])))
    if deadline <= time.time():
        raise RuntimeError('expired keeper grant')
    smoke = bool(os.environ.get('FILLER_SMOKE') or os.environ.get('FILLER_SMOKE_T0'))
    d = Path.cwd()
    out = d/('out-smoke' if smoke else 'out')/'continuation'
    out.mkdir(parents=True, exist_ok=True)
    lock = (out/'.owner.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    runner = load_runner()
    inputs = json.loads((d/'INPUTS.json').read_text())
    check_inputs(inputs)
    runner.RESULTS, runner.SLOTS = out, out/'slots'
    command = server_argv(runner, sorted(os.sched_getaffinity(0)))
    identity = dict(model_sha256=inputs['model_sha256'], build_sha256=inputs['build_sha256'],
                    argv_sha256=hashlib.sha256(json.dumps(command).encode()).hexdigest())
    (out/'identity.json').write_text(json.dumps(identity))
    # Stable slot directory and exact argv identity survive keeper relaunches.
    # Historical unsealed slots remain refused by the guard.
    children = install_server(runner, command, deadline)
    args = types.SimpleNamespace(arm='CY2', i_own_the_window=True, wait=False, max_hours=24,
        margin_min=0, budget_cpus=None, block_until=dt.datetime.fromtimestamp(deadline, dt.timezone.utc).isoformat(),
        save_every=8, force_preflight=False, selftest_external=False, cg_path=str(FIXTURES/'vendor/scripts/lib'))
    rc = 75
    error = None
    try:
        import cpu_resume
        rc = cpu_resume.run_guarded(runner, args, identity, out/'checkpoint.json', checkpoint=True)
    except Exception as exc:
        rc, error = 3, f'{type(exc).__name__}: {exc}'
    finally:
        for child in children:
            stop_own(child)
        result = summarize(out, rc)
        result.update(error=error, own_server_reaped=all(p.poll() is not None for p in children),
                      attempt=str(out), smoke=smoke)
        (d/('SMOKE-RESULT.json' if smoke else 'RESULT.json')).write_text(json.dumps(result, indent=2)+'\n')
        lock.close()
    return rc


if __name__ == '__main__':
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(SystemExit(75)))
    raise SystemExit(main())
