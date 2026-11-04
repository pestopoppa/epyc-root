#!/usr/bin/env python3
"""One native completed target call; qualification only, never the KPF-26 fan-out gate."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import urllib.request


def birth(pid):
    raw = Path(f'/proc/{pid}/stat').read_text()
    return int(raw[raw.rfind(')') + 2:].split()[19])


def owns_listener(pid, port):
    inodes = set()
    for fd in Path(f'/proc/{pid}/fd').iterdir():
        try:
            target = os.readlink(fd)
        except FileNotFoundError:
            continue
        if target.startswith('socket:['):
            inodes.add(target[8:-1])
    for table in ('tcp', 'tcp6'):
        for line in Path(f'/proc/{pid}/net/{table}').read_text().splitlines()[1:]:
            parts = line.split()
            if parts[3] == '0A' and int(parts[1].rsplit(':', 1)[1], 16) == port and parts[9] in inodes:
                return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pid', type=int, required=True)
    ap.add_argument('--port', type=int, required=True)
    ap.add_argument('--arm', choices=['off', 'on'], required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    original_birth = birth(a.pid)
    if not owns_listener(a.pid, a.port):
        raise RuntimeError('native completion endpoint is not owned by captured server')
    request = {'prompt': 'Benchmark readiness.', 'n_predict': 1, 'temperature': 0, 'seed': 35,
               'cache_prompt': False}
    raw_request = json.dumps(request).encode()
    req = urllib.request.Request(f'http://127.0.0.1:{a.port}/completion', raw_request,
                                 {'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=120) as response:
        status, raw_response = response.status, response.read()
    result = json.loads(raw_response)
    completed = result.get('tokens_predicted')
    if status != 200 or type(completed) is not int or completed < 1:
        raise RuntimeError('native completion did not produce at least one token')
    if birth(a.pid) != original_birth or not owns_listener(a.pid, a.port):
        raise RuntimeError('captured native server identity changed')
    record = {'schema': 'epyc.kpf26.native-qualification.v1', 'mode': 'qualification',
              'arm': a.arm, 'server_pid': a.pid, 'server_birth_ticks': original_birth,
              'http_status': status, 'completion_tokens': completed,
              'request_sha256': hashlib.sha256(raw_request).hexdigest(),
              'response_sha256': hashlib.sha256(raw_response).hexdigest(),
              'argv': Path(f'/proc/{a.pid}/cmdline').read_bytes().decode().split('\0')[:-1],
              'scope': 'one native completed call, not three-scout fan-out or a gate verdict'}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    with a.out.open('w') as stream:
        stream.write(json.dumps(record) + '\n'); stream.flush(); os.fsync(stream.fileno())


if __name__ == '__main__':
    main()
