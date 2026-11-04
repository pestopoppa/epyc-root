#!/usr/bin/env python3
"""One isolated CPU server and response-level recency API/cache test."""
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import urllib.request
from packet_pins import verify_packet_pin

ROOT = Path('/mnt/raid0/llm/tmp/triattention-s8c-api-real-20261104')
PACKET = ROOT / 'packet'
STATE = ROOT / 'native'
STATE.mkdir(parents=True, exist_ok=True)
attempt = STATE / ('attempt-' + str(os.getpid()))
attempt.mkdir()
PLAN_SHA256 = '1deb8eb0696075957a33f4a7dd650217c712bcebb21e23d94f4bdd14a41cfd8d'
if hashlib.sha256((ROOT / 'plan.json').read_bytes()).hexdigest() != PLAN_SHA256:
    raise SystemExit('preverified plan changed')
plan = json.loads((ROOT / 'plan.json').read_text())
stop = Path(os.environ['FILLER_STOPFILE'])
deadline = int(os.environ['FILLER_DEADLINE'])
interrupted = False
server = None
runner = None
result = {'unit': 's8c-real-api', 'status': 'invalid', 'reason': 'incomplete'}

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def signal_stop(*_):
    global interrupted
    interrupted = True

def guard():
    if interrupted or stop.exists() or time.time() >= deadline:
        raise InterruptedError('stop or deadline')

def clean(p):
    if p is None:
        return
    if p.poll() is None:
        try: os.killpg(p.pid, signal.SIGTERM)
        except ProcessLookupError: pass
        try:
            p.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, signal.SIGKILL)
            p.wait(timeout=5)
    if p.poll() is None:
        raise RuntimeError('owned process survived cleanup')

for sig in (signal.SIGTERM, signal.SIGINT):
    signal.signal(sig, signal_stop)
try:
    guard()
    verify_packet_pin(ROOT / 'packet-pin.json')
    if sha(ROOT / 'candidate-base-unit.json') != plan['build_receipt_sha256'] or sha(ROOT / 'candidate-artifact-sha256.txt') != plan['artifacts_sha256']:
        raise ValueError('candidate build receipt changed')
    st = Path(plan['model']).stat()
    if (st.st_size, st.st_ino, st.st_dev) != (plan['model_size'], plan['model_inode'], plan['model_device']):
        raise ValueError('preverified model identity changed')
    if sha(plan['server']) != plan['server_sha256']:
        raise ValueError('server binary identity changed')
    if any(sha(p) != h for p, h in plan['dsos'].items()):
        raise ValueError('candidate DSO identity changed')
    pin = attempt / 'dsos.json'
    pin.write_text(json.dumps(plan['dsos']))
    (attempt / 'slots').mkdir()
    env = {k: v for k, v in os.environ.items() if not k.startswith(('LLAMA_', 'GGML_', 'LD_'))}
    env.update(LD_LIBRARY_PATH=str(Path(plan['server']).parent), OMP_NUM_THREADS='4',
               ROCR_VISIBLE_DEVICES='', HIP_VISIBLE_DEVICES='', CUDA_VISIBLE_DEVICES='')
    argv = [plan['server'], '-m', plan['model'], '--host', '127.0.0.1', '--port', '18214',
            '-np', '1', '-t', '4', '-tb', '4', '-c', '512', '-ngl', '0', '--flash-attn', 'on',
            '--no-warmup', '--cache-ram', '0', '--ctx-checkpoints', '0', '--slot-save-path', str(attempt / 'slots')]
    with (attempt / 'server.log').open('wb') as log:
        server = subprocess.Popen(argv, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        started = time.monotonic()
        while True:
            guard()
            if server.poll() is not None:
                raise RuntimeError('candidate server exited during startup')
            try:
                with urllib.request.urlopen('http://127.0.0.1:18214/health', timeout=1) as response:
                    if response.status == 200:
                        break
            except (OSError, ValueError):
                pass
            if time.monotonic() - started > 120:
                raise TimeoutError('server startup exceeded 120 seconds')
            time.sleep(.25)
        maps = Path(f'/proc/{server.pid}/maps').read_text()
        if plan['model'] not in maps:
            raise RuntimeError('model mapping not observed')
        mapped_model = [line.split(maxsplit=5) for line in maps.splitlines() if plan['model'] in line]
        if not mapped_model or any(int(x[4]) != plan['model_inode'] for x in mapped_model):
            raise RuntimeError('model mapped inode mismatch')
        argv = [sys.executable, str(PACKET / 'api_cases.py'), '--port', '18214', '--server-pid', str(server.pid),
                '--server-sha256', plan['server_sha256'], '--dso-hashes', str(pin), '--output', str(attempt / 'cases.json')]
        with (attempt / 'test.log').open('wb') as log_test:
            runner = subprocess.Popen(argv, env=env, stdout=log_test, stderr=subprocess.STDOUT, start_new_session=True)
            while runner.poll() is None:
                guard()
                if server.poll() is not None:
                    raise RuntimeError('candidate server exited during test')
                time.sleep(.25)
            data = json.loads((attempt / 'cases.json').read_text())
            complete_inconclusive = data.get('status') == 'inconclusive'
            if (data.get('status') not in ('pass', 'fail') and not complete_inconclusive) or runner.returncode not in (0, 1):
                raise RuntimeError('API test did not complete: ' + str(data.get('reason', data.get('status'))))
            if complete_inconclusive:
                data['status'] = 'inconclusive'
            result.update(status=data['status'], reason='complete API cases', cases=len(data['cases']),
                          cases_data=data['cases'],
                          candidate=plan, evidence=str(attempt),
                          scope='One dense Qwen3-1.7B CPU server; HTTP responses and gapped-cache rejection only; no quality, speed or physical KV continuity claim.')
except BaseException as exc:
    result['reason'] = f'{type(exc).__name__}: {exc}'
finally:
    clean(runner)
    clean(server)
    if result['status'] in ('pass', 'fail', 'inconclusive'):
        (STATE / 'RESULT.json').write_text(json.dumps(result, indent=2) + '\n')
        (ROOT / 'complete').touch()
    else:
        (attempt / 'PARTIAL.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
sys.exit(0 if result['status'] in ('pass', 'fail', 'inconclusive') else (75 if interrupted or stop.exists() else 1))
