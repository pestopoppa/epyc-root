#!/usr/bin/env python3
"""CH-18.b local Gemma correctness probe; run only under an admitted CPU grant.

This does not replace the upstream tinygemma3 tests or the full design matrix.
Inputs must first be prepared in the separate admitted preparation window.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.request

ROOT = Path('/dev/shm/codex-ch18b-20261102')
MODEL = Path('/mnt/raid0/llm/models/gemma-3-1b-it-Q8_0.gguf')
SERVER = ROOT / 'build-cpu/bin/llama-server'
PORT = 19183
TOL = 1e-3
assert os.environ.get('FILLER_ID') == 'codex-ch18b-runtime-cpu-20261102'
assert os.environ.get('FILLER_PIDFILE') and os.environ.get('FILLER_DEADLINE')
assert (ROOT / 'out/BUILD_COMPLETE').is_file()
inputs = Path('/dev/shm/codex-ch18b-inputs-20261102')
expected = 'b205840c5dcef55078e37d344677869a714ffd42a4ae448c48dcfb52e4bb10d5'
assert (inputs / 'PREP_COMPLETE').is_file()
assert (inputs / 'model.sha256').read_text().strip() == expected

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        while data := f.read(4 * 1024 * 1024):
            h.update(data)
    return h.hexdigest()

st = MODEL.stat()
assert json.loads((inputs / 'model.stat').read_text()) == [st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns], 'model changed since admitted hash'
tokens_path = inputs / 'tokens.json'
assert (inputs / 'tokens.sha256').read_text().split()[0] == sha(tokens_path)
tokens = json.loads(tokens_path.read_text())
assert isinstance(tokens, list) and len(tokens) > 100 and all(type(t) is int for t in tokens)
# Bind the executed server to the completed build's recorded digest.
binary_hash = sha(SERVER)
entries = (ROOT / 'out/SHA256SUMS-cpu').read_text().splitlines()
assert f'{binary_hash}  ./llama-server' in entries
for entry in entries:
    digest, relative = entry.split('  ', 1)
    assert relative.startswith('./') and '/' not in relative[2:]
    assert sha(ROOT / 'build-cpu/bin' / relative) == digest, f'changed build artifact: {relative}'
with socket.socket() as sock:
    assert sock.connect_ex(('127.0.0.1', PORT)) != 0, 'port already in use'

dryrun = os.environ.get('FILLER_DRYRUN') == '1'
tag = f'dryrun-{os.getpid()}' if dryrun else 'run'
out = ROOT / f'out/local-gemma-runtime-{tag}.jsonl'
assert not out.exists(), 'refuse to overwrite run evidence'
slotdir = ROOT / f'slots-{tag}'
slotdir.mkdir(exist_ok=False)
args = [str(SERVER), '-m', str(MODEL), '--host', '127.0.0.1', '--port', str(PORT),
        '-ngl', '0', '-t', os.environ['FILLER_THREADS'], '-c', '2048', '-np', '2',
        '-b', '128', '-ub', '32', '--slots', '--slot-save-path', str(slotdir),
        '--cache-ram', '0', '--override-kv', 'gemma3.attention.sliding_window=int:64']
env = dict(os.environ, LD_LIBRARY_PATH=f'{ROOT}/build-cpu/bin:/opt/rocm/lib')

def request(path, data=None):
    body = None if data is None else json.dumps(data).encode()
    req = urllib.request.Request(f'http://127.0.0.1:{PORT}{path}', body,
                                 {'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=120) as response:
        return json.load(response)

def emit(obj):
    with out.open('a') as f:
        f.write(json.dumps(obj, sort_keys=True, allow_nan=False) + '\n')

def completion(slot, tokens, cache):
    return request('/completion', {'id_slot': slot, 'prompt': tokens, 'cache_prompt': cache,
                                   'n_predict': 1, 'temperature': 0, 'seed': 42,
                                   'n_probs': 5, 'return_tokens': True})

def compare(a, b):
    # Do not accept two identically incomplete server responses as parity.
    for response in (a, b):
        assert len(response['tokens']) == 1 and type(response['tokens'][0]) is int
        probs = response['completion_probabilities']
        assert len(probs) == 1 and probs[0]['id'] == response['tokens'][0]
        top = probs[0]['top_logprobs']
        assert len(top) == 5 and len({p['id'] for p in top}) == 5
    assert a['tokens'] == b['tokens'], (a['tokens'], b['tokens'])
    ap = a['completion_probabilities'][0]['top_logprobs']
    bp = b['completion_probabilities'][0]['top_logprobs']
    assert [p['id'] for p in ap] == [p['id'] for p in bp]
    for x, y in zip(ap, bp):
        assert math.isfinite(x['logprob']) and math.isfinite(y['logprob'])
        assert abs(x['logprob'] - y['logprob']) <= TOL, (x, y)

with (ROOT / f'out/local-gemma-server-{tag}.log').open('xb') as log:
    proc = subprocess.Popen(args, stdout=log, stderr=subprocess.STDOUT, env=env)
    with open(os.environ['FILLER_PIDFILE'], 'a') as f:
        f.write(f'{proc.pid}\n')
    try:
        for _ in range(120):
            assert proc.poll() is None, 'server exited during startup'
            try:
                request('/health')
                break
            except (OSError, ValueError):
                time.sleep(1)
        else:
            raise RuntimeError('server health timeout')
        # A healthy foreign process must never satisfy our health check.
        listeners = subprocess.check_output(['ss', '-ltnp', f'sport = :{PORT}'], text=True)
        assert f'pid={proc.pid},' in listeners, listeners
        emit({'event': 'start', 'model': str(MODEL), 'model_sha256': expected,
              'server_sha256': binary_hash, 'argv': args, 'abs_logprob_tolerance': TOL})
        # Lengths exercise below/at/above the overridden SWA window. Each warm
        # result is compared with a separately cold slot, not a speed baseline.
        for length in (32, 64, 65, 96):
            for mode in ('identical', 'extension', 'divergent'):
                assert time.time() < int(os.environ['FILLER_DEADLINE'])
                assert not Path(os.environ['FILLER_STOPFILE']).exists()
                for slot in (0, 1):
                    request(f'/slots/{slot}?action=erase', {})
                prefix = tokens[:length]
                completion(0, prefix, True)
                if mode == 'identical':
                    query = prefix
                elif mode == 'extension':
                    query = tokens[:length + 3]
                else:
                    query = tokens[:length - 2] + tokens[length + 3:length + 6]
                    assert query[:length] != prefix, 'divergent fixture unexpectedly shares the full prefix'
                warm = completion(0, query, True)
                cold = completion(1, query, False)
                compare(warm, cold)
                emit({'event': 'case', 'length': length, 'mode': mode,
                      'warm_timings': warm['timings'], 'cold_timings': cold['timings'],
                      'warm': warm, 'cold': cold, 'result': 'pass'})
                if dryrun:
                    native = os.environ.get('FILLER_DRYRUN_RESULT_PATH')
                    assert native
                    Path(native).write_text(json.dumps({'stage': 'first-comparison', 'result': 'pass'}) + '\n')
                    sys.exit(0)
        for slot in (0, 1):
            request(f'/slots/{slot}?action=erase', {})
        completion(0, tokens[:32], True)
        request('/slots/0?action=save', {'filename': 'ch18b-slot.bin'})
        request('/slots/0?action=erase', {})
        request('/slots/0?action=restore', {'filename': 'ch18b-slot.bin'})
        restored = completion(0, tokens[:35], True)
        cold = completion(1, tokens[:35], False)
        compare(restored, cold)
        emit({'event': 'case', 'length': 32, 'mode': 'slot-save-restore',
              'warm_timings': restored['timings'], 'cold_timings': cold['timings'],
              'warm': restored, 'cold': cold, 'result': 'pass'})
        emit({'event': 'complete', 'result': '13 comparisons passed',
              'scope': 'local model; no upstream-fixture equivalence or full-matrix claim'})
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=15)
