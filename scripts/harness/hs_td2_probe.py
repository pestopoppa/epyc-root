#!/usr/bin/env python3
"""Keeper-only HS-TD-2 shadow self-check screen on frozen authored turns.

Measures an extra call on the registered worker's weights, not production
session overhead. Never changes the candidate answer or gates a real action.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time
import urllib.request


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify(records):
    for record in records:
        stat = Path(record['path']).stat()
        if [stat.st_size, stat.st_mtime_ns, stat.st_ino, stat.st_dev] != [
                record[k] for k in ('size', 'mtime_ns', 'inode', 'device')]:
            raise ValueError('prepared input changed: ' + record['path'])


def decision(response):
    """Malformed, truncated and non-finite judgments remain unknown."""
    choice = response['choices'][0]
    if choice['finish_reason'] != 'stop':
        raise ValueError('unfinished judgment')
    value = json.loads(choice['message']['content'])
    if set(value) != {'satisfied', 'confidence', 'reason'}:
        raise ValueError('judgment schema')
    if type(value['satisfied']) is not bool:
        raise ValueError('satisfied must be boolean')
    confidence = value['confidence']
    if type(confidence) not in (float, int) or not math.isfinite(confidence) or not 0 <= confidence <= 1:
        raise ValueError('confidence outside [0,1]')
    if not isinstance(value['reason'], str) or not value['reason'].strip():
        raise ValueError('missing reason')
    return value


def summarize(records, expected):
    full = [r for r in records if r['phase'] == 'full']
    valid = [r for r in full if r['status'] == 'ok']
    costs = sorted(r['elapsed_s'] for r in valid)
    return {'complete': len(full) == expected, 'expected': expected,
            'observed': len(full), 'valid': len(valid),
            'unknown': expected - len(valid),
            'agreement': sum(r['judgment']['satisfied'] == r['reference_satisfied'] for r in valid),
            'disagreements': [r['record_path'] for r in valid
                              if r['judgment']['satisfied'] != r['reference_satisfied']],
            'mean_valid_call_s': sum(costs) / len(costs) if costs else None,
            'p95_valid_call_s': costs[math.ceil(.95 * len(costs)) - 1] if costs else None,
            'all_attempt_call_s': sum(r['elapsed_s'] for r in full),
            'scope': 'authored frozen turns; extra-call wall cost on worker weights, CPU no MTP; no live-session or production-overhead claim',
            'gate': False}


def append(path, value):
    with path.open('a') as stream:
        stream.write(json.dumps(value, sort_keys=True, allow_nan=False) + '\n')
        stream.flush()
        os.fsync(stream.fileno())


def stopped():
    return (Path(os.environ['FILLER_STOPFILE']).exists() if os.environ.get('FILLER_STOPFILE') else False) or time.time() >= float(os.environ.get('FILLER_DEADLINE', 'inf'))


def owns_listener(pid, port):
    inodes = set()
    for fd in Path(f'/proc/{pid}/fd').iterdir():
        try:
            link = os.readlink(fd)
        except FileNotFoundError:
            continue
        if link.startswith('socket:['):
            inodes.add(link[8:-1])
    for line in Path(f'/proc/{pid}/net/tcp').read_text().splitlines()[1:]:
        fields = line.split()
        if int(fields[1].split(':')[1], 16) == port and fields[3] == '0A' and fields[9] in inodes:
            return True
    return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('inputs', 'run', 'check', 'progress'))
    parser.add_argument('--job', type=Path, required=True)
    args = parser.parse_args()
    job = args.job
    if args.action == 'check':
        path = job / 'RESULT.json'
        return 0 if path.exists() and json.loads(path.read_text()).get('complete') else 1
    if args.action == 'progress':
        path = job / 'results.jsonl'
        if path.exists():
            for line in path.read_text().splitlines():
                row = json.loads(line)
                if row['captured_unix'] >= float(os.environ.get('FILLER_SMOKE_T0', 'inf')) and row.get('response_received'):
                    return 0
        return 1
    manifest = json.loads((job / 'manifest.json').read_text())
    records = manifest['prepared_inputs']
    verify(records)
    if digest(__file__) != manifest['runtime_sha256'] or digest(job / 'cases.json') != manifest['cases_sha256']:
        raise ValueError('source/corpus digest mismatch')
    if args.action == 'inputs':
        return 0
    if not os.environ.get('FILLER_ID'):
        raise RuntimeError('keeper execution required')
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(75))
    attempt = job / ('attempt-' + str(time.time_ns()))
    attempt.mkdir()
    cases = json.loads((job / 'cases.json').read_text())
    phase = 'smoke' if os.environ.get('FILLER_DRYRUN') else 'full'
    expected = len(cases) * manifest['repetitions']
    results = []
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    server = manifest['server']
    threads = min(int(os.environ.get('FILLER_THREADS', '4')), len(os.sched_getaffinity(0)))
    argv = [server, '-m', manifest['model'], '--alias', 'worker-selfcheck',
            '--host', '127.0.0.1', '--port', str(port), '-ngl', '0', '-c', '4096',
            '-np', '1', '-t', str(threads), '-tb', str(threads), '--jinja', '--no-warmup']
    env = dict(os.environ, LD_LIBRARY_PATH=str(Path(server).parent), GGML_BACKEND_PATH=str(Path(server).parent))
    with (attempt / 'server.log').open('wb') as log:
        child = subprocess.Popen(argv, env=env, stdout=log, stderr=subprocess.STDOUT)
        if os.environ.get('FILLER_PIDFILE'):
            with open(os.environ['FILLER_PIDFILE'], 'a') as stream:
                stream.write(str(child.pid) + '\n')
        try:
            endpoint = f'http://127.0.0.1:{port}'
            deadline = time.monotonic() + 180
            while True:
                if stopped() or child.poll() is not None or time.monotonic() > deadline:
                    raise RuntimeError('server unavailable')
                try:
                    with urllib.request.urlopen(endpoint + '/health', timeout=1) as health:
                        if health.status == 200 and owns_listener(child.pid, port):
                            break
                except OSError:
                    time.sleep(.2)  # Keeper payload only.
            mappings = Path(f'/proc/{child.pid}/maps').read_text()
            mapped = {line.split()[-1] for line in mappings.splitlines() if '/' in line.split()[-1]}
            ggml = [str(Path(p).resolve()) for p in mapped if 'libggml' in p]
            pinned = {r['path'] for r in records}
            if not any('libggml-cpu' in p for p in ggml) or any(p not in pinned for p in ggml):
                raise RuntimeError('unprepared ggml mapping')
            if str(Path(f'/proc/{child.pid}/exe').resolve()) != server or manifest['model'] not in mapped:
                raise RuntimeError('model/binary mapping mismatch')
            custody = {'manifest': manifest, 'argv': argv, 'mapped_ggml': ggml, 'pid': child.pid,
                       'keeper': {k: os.environ.get(k) for k in ('FILLER_ID', 'FILLER_CPUS', 'FILLER_THREADS', 'FILLER_DEADLINE', 'FILLER_DRYRUN')},
                       'category': 'CANDIDATE', 'instrument_class': 'bench', 'phase': phase}
            (attempt / 'custody.json').write_text(json.dumps(custody, indent=2))
            errors = 0
            for repetition in range(manifest['repetitions']):
                for case in cases:
                    if stopped():
                        return 75
                    path = attempt / f"{repetition}-{case['id']}.json"
                    request = {'model': 'worker-selfcheck', 'temperature': 0, 'seed': 42 + repetition,
                               'max_tokens': 128, 'chat_template_kwargs': {'enable_thinking': False},
                               'messages': [{'role': 'system', 'content': manifest['system_prompt']},
                                            {'role': 'user', 'content': json.dumps({'task': case['task'], 'candidate_turn': case['answer']})}]}
                    record = {'case_id': case['id'], 'repetition': repetition, 'phase': phase,
                              'reference_satisfied': case['satisfied'], 'reference_reason': case['rationale'],
                              'record_path': str(path), 'custody': str(attempt / 'custody.json'),
                              'request': request, 'status': 'unknown', 'response_received': False}
                    start = time.monotonic()
                    try:
                        req = urllib.request.Request(endpoint + '/v1/chat/completions', json.dumps(request).encode(), {'Content-Type': 'application/json'})
                        with urllib.request.urlopen(req, timeout=90) as response:
                            record['response_raw'] = response.read().decode()
                        record['response_received'] = True
                        record['elapsed_s'] = time.monotonic() - start
                        native = json.loads(record['response_raw'])
                        record['usage'] = native.get('usage')
                        record['timings'] = native.get('timings')
                        record['judgment'] = decision(native)
                        record['status'] = 'ok'
                        errors = 0
                    except (OSError, ValueError, KeyError, IndexError, TypeError) as exc:
                        record.setdefault('elapsed_s', time.monotonic() - start)
                        record['error'] = str(exc)
                        errors += 1
                    record['captured_unix'] = time.time()
                    path.write_text(json.dumps(record, indent=2, allow_nan=False))
                    append(job / 'results.jsonl', record)
                    results.append(record)
                    if phase == 'full':
                        (job / 'RESULT.json').write_text(json.dumps(summarize(results, expected), indent=2))
                    if errors >= 2:
                        return 2
        finally:
            if child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait(timeout=10)
            if child.poll() is None:
                raise RuntimeError('own server survived shutdown')
    return 0


if __name__ == '__main__':
    sys.exit(main())
