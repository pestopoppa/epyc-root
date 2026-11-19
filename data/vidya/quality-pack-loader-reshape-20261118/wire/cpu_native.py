#!/usr/bin/env python3
"""Native CPU request, process identity, and cleanup capture."""
import base64
from datetime import datetime, timezone
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import time

D = Path(__file__).resolve().parent
PORT = 19489


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write(path, contents):
    with path.open('xb') as stream:
        stream.write(contents)
        stream.flush()
        os.fsync(stream.fileno())


def write_json(path, obj):
    write(path, canonical(obj) + b'\n')
    return file_sha(path)


def stat_id(path):
    st = path.stat()
    return [st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns]


def deadline_epoch(text):
    if re.fullmatch(r'[0-9]+', text):
        return int(text)
    deadline = datetime.fromisoformat(text.removesuffix('Z') + '+00:00' if text.endswith('Z') else text)
    if deadline.utcoffset() is None:
        raise ValueError('FILLER_DEADLINE requires a time zone')
    return deadline.astimezone(timezone.utc).timestamp()


def budget(deadline, stop, maximum):
    remaining = deadline - time.time()
    if stop.exists() or remaining <= 0:
        raise InterruptedError('STOP or grant deadline reached')
    return min(maximum, remaining)


def listeners():
    found = set()
    for table in (Path('/proc/net/tcp'), Path('/proc/net/tcp6')):
        if not table.exists():
            continue
        for row in table.read_text().splitlines()[1:]:
            fields = row.split()
            if fields[3] == '0A' and int(fields[1].split(':')[1], 16) == PORT:
                found.add(f'socket:[{fields[9]}]')
    return found


def owns_listener(child):
    proc = Path('/proc') / str(child.pid)
    owned = set()
    for fd in (proc / 'fd').iterdir():
        try:
            owned.add(os.readlink(fd))
        except FileNotFoundError:
            continue
    active = listeners()
    return bool(active) and active <= owned


def prove_server(child, runtime, cpus):
    proc = Path('/proc') / str(child.pid)
    if child.poll() is not None or (proc / 'exe').resolve(strict=True) != Path(runtime['binary']):
        raise RuntimeError('tracked process differs from the pinned server')
    if not owns_listener(child):
        raise RuntimeError('tracked server does not own the isolated listener')
    if os.sched_getaffinity(child.pid) != set(cpus):
        raise RuntimeError('server affinity drift')
    observed = set()
    for row in (proc / 'maps').read_text().splitlines():
        fields = row.split(maxsplit=5)
        if len(fields) != 6 or not Path(fields[5]).name.startswith(('libggml', 'libllama')):
            continue
        path = Path(fields[5]).resolve(strict=True)
        major, minor = (int(field, 16) for field in fields[3].split(':'))
        loaded = (os.makedev(major, minor), int(fields[4]))
        current = path.stat()
        if loaded != (current.st_dev, current.st_ino):
            raise RuntimeError(f'mapped library inode differs from pinned path: {path}')
        observed.add(str(path))
    expected = set(runtime['runtime_files']) - {runtime['binary']}
    if observed != expected:
        raise RuntimeError(f'unpinned or missing server libraries: {observed ^ expected}')
    return sorted(observed)


def request_process_witness(child, runtime, cpus):
    mapped = prove_server(child, runtime, cpus)
    return {'pid': child.pid, 'binary': runtime['binary'], 'cpus': cpus, 'mapped_libraries': mapped,
            'observed_at': datetime.now(timezone.utc).isoformat(timespec='microseconds')}


def request(path, timeout, body=None):
    connection = http.client.HTTPConnection('127.0.0.1', PORT, timeout=timeout)
    try:
        method = 'GET' if body is None else 'POST'
        connection.request(method, path, body, {'Content-Type': 'application/json'})
        response = connection.getresponse()
        raw = response.read(4 * 1024 * 1024 + 1)
        if len(raw) > 4 * 1024 * 1024:
            raise ValueError('response exceeds native capture limit')
        return response.status, raw
    finally:
        connection.close()


def capture_arm(arm, runtime, recipe, items, out, cpus, deadline, stop):
    if listeners():
        raise RuntimeError('isolated port already in use')
    arm_dir = out / arm
    arm_dir.mkdir()
    binary = Path(runtime['binary'])
    env = {'PATH': '/usr/bin:/bin', 'LD_LIBRARY_PATH': str(binary.parent), 'GGML_IQK': '1',
           'ROCR_VISIBLE_DEVICES': '-1', 'HIP_VISIBLE_DEVICES': '-1', 'CUDA_VISIBLE_DEVICES': '',
           'OMP_NUM_THREADS': '1', 'FILLER_ID': os.environ['FILLER_ID']}
    argv = [str(binary), '--host', '127.0.0.1', '--port', str(PORT), '--threads', str(len(cpus)),
            *recipe['args']]
    if 'external_chat_template' in recipe:
        argv.extend(('--chat-template-file', str(D / recipe['external_chat_template'])))
    records = []
    with (arm_dir / 'server.log').open('xb') as log:
        child = subprocess.Popen(argv, stdout=log, stderr=subprocess.STDOUT, env=env, cwd=arm_dir)
        try:
            ready = time.monotonic() + budget(deadline, stop, recipe['startup_s'])
            while time.monotonic() < ready and child.poll() is None:
                remaining = budget(deadline, stop, 1)
                try:
                    if owns_listener(child) and request('/health', remaining)[0] == 200:
                        break
                except InterruptedError:
                    raise
                except (OSError, http.client.HTTPException):
                    pass
                time.sleep(.25)
            else:
                raise RuntimeError('isolated server failed health before startup limit')
            mapped = prove_server(child, runtime, cpus)
            write_json(arm_dir / 'server.json', {'argv': argv, 'pid': child.pid, 'cpus': cpus,
                       'mapped_libraries': mapped, 'image': runtime, 'recipe': recipe, 'environment': env})
            for item in items:
                before = request_process_witness(child, runtime, cpus)
                wire = canonical(item['request_body'])
                name = item['id']
                write(arm_dir / f'{name}.request.json', wire)
                status, raw = request(recipe['endpoint'], budget(deadline, stop, recipe['request_s']), wire)
                write(arm_dir / f'{name}.response.json', raw)
                after = request_process_witness(child, runtime, cpus)
                write_json(arm_dir / f'{name}.custody.json', {
                    'before': before, 'after': after, 'http_status': status,
                    'request_sha256': sha(wire), 'response_sha256': sha(raw),
                })
                if status != 200:
                    raise RuntimeError(f'{arm}/{name} response status {status}')
                data = json.loads(raw)
                if not isinstance(data, dict) or 'error' in data:
                    raise ValueError(f'{arm}/{name} response is not a successful object')
                records.append({'id': name, 'request_sha256': sha(wire), 'response_sha256': sha(raw),
                                'response_b64': base64.b64encode(raw).decode('ascii')})
        finally:
            if child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait(timeout=5)
            write_json(arm_dir / 'cleanup.json', {'pid': child.pid, 'dead': child.poll() is not None,
                       'port_closed': not listeners(), 'exit_status': child.returncode})
            if child.poll() is None or listeners():
                raise RuntimeError('captured server or listener remains after cleanup')
    return records


def stop_signal(signum, _frame):
    raise InterruptedError(f'interrupted by signal {signum}')


