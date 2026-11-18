"""Allocator-owned native prefix-rewrite pricing; no production flags change."""
import argparse
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import secrets
import signal
import statistics
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

HERE = Path(__file__).resolve().parent
ROOT = Path('/mnt/raid0/llm/tmp/delegation-context-preassembly/cf-plan-boundary')
ROW = 'cf-plan-boundary-20261118'
PORT = 19386
SOURCE_REF = '12afe2858f9dbd4691447926d6cf1864de64348c'
HTTP = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    temporary.replace(path)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tokens(length, salt):
    # Native pre-encoded synthetic token fixture. No tokenizer/prep in a grant.
    return [100 + salt] + [110 + (i % 16) for i in range(length - 1)]


def evaluate(reply, expected, warm):
    timing = reply['timings']
    cache, processed = timing['cache_n'], timing['prompt_n']
    if (type(cache) is not int or type(processed) is not int
            or cache < 0 or processed <= 0 or cache + processed != expected
            or reply['tokens_evaluated'] != expected or reply['id_slot'] != 0
            or reply['tokens_predicted'] != 1 or not reply['stop']
            or (warm and cache <= 0) or (not warm and cache != 0)):
        raise ValueError('native token/slot/cache witness mismatch')
    for field in ('prompt_ms', 'predicted_ms'):
        if (type(timing[field]) not in (int, float) or not math.isfinite(timing[field])
                or timing[field] < 0):
            raise ValueError('invalid native timing')
    return {'cached_tokens': cache, 'processed_tokens': processed,
            'prompt_ms': timing['prompt_ms'], 'decode_ms': timing['predicted_ms']}


def pricing(raw, compact):
    """Point extrapolation only; do not turn timing noise into an adoption test."""
    extra = compact[0] - raw[0]
    savings = statistics.mean(a - b for a, b in zip(raw[1:], compact[1:], strict=True))
    return {'rewrite_extra_ms': extra, 'mean_later_savings_ms': savings,
            'point_break_even_requests': (1 + math.ceil(max(0, extra) / savings)
                                          if savings > 0 else None),
            'measured_horizon_delta_ms': sum(compact) - sum(raw)}


def verify():
    sys.path.insert(0, str(HERE))
    import cmp4_runner as live
    manifest = read(HERE / 'inputs.json')
    if (manifest['source'] != SOURCE_REF
            or manifest['model_path'] != str(live.MODEL)
            or manifest['model_sha256'] != live.MODEL_SHA
            or digest(HERE / 'prior-model-receipt.json') != manifest['prior_receipt_sha256']):
        raise ValueError('source/model/retained receipt pin mismatch')
    # Only small binary/config hashes and retained model stat; never reread weights.
    live.verify_inputs(manifest)
    source = ROOT / 'source'
    actual = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    dirty = subprocess.check_output(['git', '-C', str(source), 'status', '--porcelain'], text=True)
    if actual != SOURCE_REF or dirty:
        raise ValueError('source worktree differs from pin')
    sys.path.insert(0, str(source))
    from scripts.benchmark import own_port_proof
    if not Path(own_port_proof.__file__).resolve().is_relative_to(source.resolve()):
        raise ValueError('listener proof escaped pinned source')
    return live, own_port_proof, manifest


def payload_for(prompt, cache):
    return {'prompt': prompt, 'id_slot': 0, 'cache_prompt': cache, 'n_predict': 1,
            'temperature': 0, 'seed': 5801, 'ignore_eos': True, 'stream': False,
            'grammar': 'root ::= \"x\"'}


def request(folder, label, prompt, cache, key, deadline, live):
    live.check_window(deadline)
    payload = payload_for(prompt, cache)
    body = json.dumps(payload).encode()
    (folder / f'{label}.request.json').write_bytes(body)
    req = urllib.request.Request(f'http://127.0.0.1:{PORT}/completion', data=body,
                                 headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'})
    started = time.monotonic()
    try:
        response = HTTP.open(req, timeout=max(0.1, min(180, deadline - time.time())))
    except urllib.error.HTTPError as exc:
        (folder / f'{label}.response.json').write_bytes(exc.read())
        write(folder / f'{label}.http.json', {'status': exc.code, 'wall_ms': (time.monotonic() - started) * 1000})
        raise
    with response:
        data = response.read()
    elapsed = (time.monotonic() - started) * 1000
    (folder / f'{label}.response.json').write_bytes(data)
    result = evaluate(json.loads(data), len(prompt), warm=cache and label != 'rewrite-1')
    result['wall_ms'] = elapsed
    write(folder / f'{label}.metric.json', result)
    return result


def pair(window, size, repeat, dry, key, deadline, live):
    folder = window / f'pair-{size}-{repeat}'
    folder.mkdir()
    horizon, suffix = (2, 4) if dry else (4, 32)
    original, rewritten = tokens(size, 0), tokens(size // 4, 1)
    records = {}
    # Counterbalance pair path order by replicate; every path primes the raw prefix.
    order = ('raw', 'rewrite') if repeat % 2 == 0 else ('rewrite', 'raw')
    for arm in order:
        request(folder, arm + '-prime', original, False, key, deadline, live)
        values = []
        prefix = original if arm == 'raw' else rewritten
        for step in range(1, horizon + 1):
            prompt = prefix + tokens(step * suffix, 2)
            values.append(request(folder, f'{arm}-{step}', prompt, True, key, deadline, live))
        records[arm] = values
    native = pricing([v['prompt_ms'] + v['decode_ms'] for v in records['raw']],
                     [v['prompt_ms'] + v['decode_ms'] for v in records['rewrite']])
    wall = pricing([v['wall_ms'] for v in records['raw']], [v['wall_ms'] for v in records['rewrite']])
    result = {'unit': f'{size}/{repeat}', 'raw_tokens': size, 'compact_tokens': size // 4,
              'horizon': horizon, 'order': order, 'records': records,
              'native_pricing': native, 'wall_pricing': wall}
    write(folder / 'PAIR.json', result)
    return result


def guard_attempt(out, dry):
    if not dry and any(out.glob('window-*')):
        raise ValueError('no automatic retry of an attempted official window')


def run():
    if os.environ.get('FILLER_ID') != ROW:
        raise ValueError('allocator grant or publisher smoke required')
    live, owner, manifest = verify()
    dry = os.environ.get('FILLER_DRYRUN') == '1'
    out = Path(os.environ['FILLER_DRYRUN_DIR']) / 'cf-pb-native' if dry else ROOT / 'native'
    out.mkdir(parents=True, exist_ok=True)
    with (out / 'run.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        guard_attempt(out, dry)
        window = Path(tempfile.mkdtemp(prefix='window-', dir=out))
        cpus = live.bind_four_cores()
        if not live.file_port_available(PORT) or owner.listen_inodes(PORT):
            raise ValueError('private listener unavailable')
        argv = live.server_argv(4, PORT)
        key = secrets.token_urlsafe(24)
        env = {k: v for k, v in os.environ.items()
               if not k.startswith(('LLAMA_', 'GGML_', 'OMP_', 'KMP_', 'GOMP_'))}
        env.update(LD_LIBRARY_PATH=str(live.BIN.resolve()), LLAMA_API_KEY=key)
        deadline = min(float(os.environ['FILLER_DEADLINE']), time.time() + 1800)
        signal.signal(signal.SIGTERM, live.handle_stop)
        signal.signal(signal.SIGINT, live.handle_stop)
        schedule = [(32, 0)] if dry else [(n, r) for r in range(3) for n in (1024, 4096)]
        write(window / 'WINDOW.json', {'argv': argv, 'cpus': cpus, 'schedule': schedule,
                                      'inputs': manifest, 'deadline': deadline, 'smoke': dry})
        records, error, exited = [], None, False
        try:
            linkage = subprocess.run(['bash', str(live.LINKAGE), argv[0], str(live.BIN.resolve())],
                                     env=env, capture_output=True, text=True, check=True, timeout=20)
            (window / 'LINKAGE.txt').write_text(linkage.stdout)
            with (window / 'server.log').open('wb') as log:
                proc = subprocess.Popen(argv, env=env, stdout=log, stderr=subprocess.STDOUT)
                try:
                    with open(os.environ['FILLER_PIDFILE'], 'a') as pids:
                        pids.write(f'{proc.pid}\n')
                    proof = live.server_ready(proc, owner, key, min(deadline, time.time() + 160),
                                              window / 'server.log', port=PORT)
                    write(window / 'SERVER.json', proof)
                    for size, repeat in schedule:
                        live.check_window(deadline)
                        if proc.poll() is not None or not (owner.listen_inodes(PORT) & owner.pid_socket_inodes(proc.pid)):
                            raise ValueError('listener ownership lost')
                        records.append(pair(window, size, repeat, dry, key, deadline, live))
                        write(out / 'PROGRESS.json', {'unit': records[-1]['unit'], 'completed': len(records)})
                finally:
                    if proc.poll() is None:
                        proc.terminate()
                        try:
                            proc.wait(timeout=6)
                        except subprocess.TimeoutExpired:
                            proc.kill()
                            proc.wait(timeout=6)
                    exited = proc.poll() is not None and not owner.listen_inodes(PORT)
        except (Exception, live.WindowEnded) as exc:
            error = f'{type(exc).__name__}: {exc}'
        qualified = error is None and exited and len(records) == len(schedule)
        result = {'schema': 'epyc.cf_plan_boundary.native.v1', 'row': ROW, 'completed': len(records),
                  'cache_witness_valid': qualified, 'qualified': qualified, 'server_exited': exited,
                  'error': error, 'pairs': records, 'window': str(window),
                  'inputs_sha256': digest(HERE / 'inputs.json'),
                  'window_sha256': {str(p.relative_to(window)): digest(p) for p in sorted(window.rglob('*')) if p.is_file()},
                  'limits': 'Synthetic cache-pricing diagnostic; excludes summary-generation cost. No quality or trigger-adoption claim.'}
        name = ('SMOKE.json' if dry else 'RESULT.json') if qualified else 'PARTIAL.json'
        write(out / name, result)
        return int(not qualified)


def main():
    mode = argparse.ArgumentParser()
    mode.add_argument('mode', choices=('run', 'verify', 'smoke', 'complete', 'precondition'))
    selected = mode.parse_args().mode
    if selected == 'run':
        return run()
    if selected == 'verify':
        verify()
        return 0
    if selected == 'precondition':
        import socket
        with socket.socket() as sock:
            try:
                sock.bind(('127.0.0.1', PORT))
                return 0
            except OSError:
                return 1
    if selected == 'complete':
        p = ROOT / 'native/RESULT.json'
        return int(not (p.exists() and read(p)['completed'] == 6 and read(p)['cache_witness_valid']))
    start = float(os.environ.get('FILLER_SMOKE_T0', '0'))
    root = os.environ.get('FILLER_DRYRUN_DIR')
    p = Path(root) / 'cf-pb-native/SMOKE.json' if root else None
    return int(not (start > 0 and p and p.exists() and p.stat().st_mtime >= start and read(p)['qualified']))


if __name__ == '__main__':
    sys.exit(main())
