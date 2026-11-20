#!/usr/bin/env python3
"""Row payload: launch isolated A1, adopt pinned preflight, then stop our PID.

No completions or quality measurements. Input hashing is done before publication.
"""
import hashlib
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import time
import types
import urllib.request

STORE = Path('/mnt/raid0/llm/kernels/builds/gpu-20260921-ffc1bac82')
TEMPLATE = '/mnt/raid0/llm/models/chat-templates/epyc-qwen3x-v1-terse.jinja'
CHECKER_COMMIT = '833108f9a5259b50c4f923efeaa804e44d2697c2'
ROOT_REPO = '/mnt/raid0/llm/views/epyc-root-main'
PORT = 18761


class RowStopped(RuntimeError):
    """A keeper termination must retain a result after reaping our server."""


def request_stop(signum, _frame):
    raise RowStopped(f'keeper signal {signum}')


def argv(model, slots, threads):
    # This row pins production v10, which predates --load-threads. Keep its
    # native loader; generation and batch thread counts remain explicit.
    return [str(STORE/'bin/llama-server'), '-m', model, '--host', '127.0.0.1',
            '--port', str(PORT), '-np', '1', '-t', str(threads), '-tb', str(threads),
            '-ub', '2048', '--flash-attn', 'on', '--jinja', '-ctk', 'q8_0',
            '-ctv', 'q8_0', '--no-mmap',
            '-ngl', 'all', '--cache-ram', '0', '--chat-template-file', TEMPLATE,
            '--device', 'ROCm0', '--slot-save-path', str(slots), '--verbosity', '4',
            '-c', '524288', '--rope-scaling', 'yarn', '--rope-scale', '2',
            '--yarn-orig-ctx', '262144', '--override-kv',
            'qwen35.context_length=int:524288,qwen35.rope.scaling.type=str:yarn,'
            'qwen35.rope.scaling.factor=float:2,qwen35.rope.scaling.original_context_length=int:262144']


def stop_own(child):
    """Popen owns the PID until reaped; never signal any discovered process."""
    if child.poll() is None:
        child.terminate()
        try:
            child.wait(timeout=15)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait(timeout=15)
    if child.poll() is None:
        raise RuntimeError('own server did not exit')


def check_inputs(inputs):
    p = Path(inputs['model'])
    s = p.stat()
    if {'size': s.st_size, 'mtime_ns': s.st_mtime_ns, 'ino': s.st_ino} != inputs['model_stat']:
        raise RuntimeError('model changed since publication preparation')
    for name, expected in inputs['store_hashes'].items():
        if hashlib.file_digest((STORE/name).open('rb'), 'sha256').hexdigest() != expected:
            raise RuntimeError('store identity changed: '+name)
    if hashlib.file_digest(open(TEMPLATE, 'rb'), 'sha256').hexdigest() != inputs['template_sha256']:
        raise RuntimeError('template identity changed')


def main():
    d = Path.cwd()
    smoke = bool(os.environ.get('FILLER_SMOKE')) or bool(os.environ.get('FILLER_SMOKE_T0'))
    out = d/('out-smoke' if smoke else 'out')
    out.mkdir(exist_ok=True)
    # A unique attempt retains refusal diagnostics across interrupted/resumed smokes.
    attempt = out/str(time.time_ns())
    attempt.mkdir()
    child = None
    result = {'unit_id': str(attempt.name), 'checker_commit': CHECKER_COMMIT,
              'force_preflight': False, 'ok': False}
    exit_code = 3
    try:
        inputs = json.loads((d/'INPUTS.json').read_text())
        check_inputs(inputs)
        result['model_sha256'] = inputs['model_sha256']
        # Refuse occupied ports; do not stop services, including production.
        for port in (PORT, 8083):
            with socket.socket() as sock:
                if sock.connect_ex(('127.0.0.1', port)) == 0:
                    raise RuntimeError(f'occupied port {port}')
        env = dict(os.environ)
        env['FILLER_ID'] = os.environ['FILLER_ID']
        for key in ('LLAMA_SERVER_SLOTS_DEBUG', 'GGML_CUDA_GDN_STATE_BF16', 'GGML_CUDA_FA_MASK_SKIP'):
            env.pop(key, None)
        env.update(LD_LIBRARY_PATH=f'{STORE}/bin:/opt/rocm/lib:/usr/lib/llvm-20/lib:/opt/AMD/aocc-compiler-5.0.0/lib',
                   GGML_IQK='1', HIP_PATH='/opt/rocm', ROCM_PATH='/opt/rocm')
        slots = attempt/'slots'
        slots.mkdir()
        command = argv(inputs['model'], slots, len(os.sched_getaffinity(0)))
        (attempt/'argv.json').write_text(json.dumps(command))
        log = attempt/'A1.server.log'
        with log.open('w') as stream:
            child = subprocess.Popen(command, env=env, stdout=stream, stderr=subprocess.STDOUT)
        result['pid'] = child.pid
        deadline = time.monotonic()+600
        while True:
            if child.poll() is not None:
                raise RuntimeError(f'server exited {child.returncode}')
            if (d/'STOP').exists() or time.monotonic() > deadline:
                raise RuntimeError('STOP or startup deadline')
            try:
                with urllib.request.urlopen(f'http://127.0.0.1:{PORT}/health', timeout=2) as response:
                    if response.status == 200:
                        break
            except OSError:
                pass
            time.sleep(1)  # Keeper-owned row, never run directly in an agent turn.
        source = subprocess.check_output(['git', '-C', ROOT_REPO, 'show',
            f'{CHECKER_COMMIT}:scripts/benchmark/yarn_e1/proof_preflight.py'])
        checker = types.ModuleType('pinned_checker')
        exec(compile(source, 'git:'+CHECKER_COMMIT, 'exec'), checker.__dict__)
        diagnostic = attempt/'preflight.json'
        rc = checker.main(['--arm', 'A1', '--port', str(PORT), '--server-log', str(log),
                           '--output', str(diagnostic)])
        pf = json.loads(diagnostic.read_text())
        live = pf.get('preflight', {})
        if rc or live.get('pid') != child.pid or (live.get('kfd_gib') or 0) < 20:
            raise RuntimeError('live preflight refused or PID/residency mismatch')
        linkage = subprocess.run(['/mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh',
            str(STORE/'bin/llama-server'), str(STORE)], env=env, capture_output=True, text=True, timeout=30)
        (attempt/'linkage.txt').write_text(linkage.stdout+linkage.stderr)
        if linkage.returncode:
            raise RuntimeError('linkage verifier refused')
        result.update(ok=True, verdict='LIVE_PREFLIGHT_PASS', diagnostic=str(diagnostic),
                      kfd_gib=live['kfd_gib'])
        exit_code = 0
    except RowStopped as exc:
        result.update(ok=False, verdict='PREFLIGHT_INTERRUPTED', error=str(exc))
        exit_code = 75
    except Exception as exc:
        result.update(verdict='PREFLIGHT_REFUSED', error=f'{type(exc).__name__}: {exc}')
    finally:
        if child is not None:
            stop_own(child)
    result['own_server_reaped'] = child is None or child.poll() is not None
    (out/'RESULT.json').write_text(json.dumps(result, indent=2)+'\n')
    return exit_code


if __name__ == '__main__':
    signal.signal(signal.SIGTERM, request_stop)
    raise SystemExit(main())
