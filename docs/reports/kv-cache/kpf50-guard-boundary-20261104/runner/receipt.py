"""Prospective KPF-50 completion receipt producer; not wired to a runner.

Structural custody only: these checks do not grade a profiler measurement or
prove that a producer's cleanup, clock or outcome assertions are truthful.
"""
import hashlib
import json
import os
import re
import stat
import uuid
from pathlib import Path

ORDER = ('full-a', 'mask-a', 'mask-b', 'full-b')
KEYS = ('outcome', 'cleanup', 'clock_before', 'clock_after', 'trace_manifest')
SAFE = re.compile(r'[A-Za-z0-9_.-]{1,160}\Z')
DIGEST = re.compile(r'[0-9a-f]{64}\Z')

def _read(dfd, name):
    if not isinstance(name, str) or not SAFE.fullmatch(name) or name in ('.', '..') or name.lower().endswith('.gguf'):
        raise ValueError('unsafe evidence name')
    fd = os.open(name, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW, dir_fd=dfd)
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_size > 10 * 1024 * 1024:
            raise ValueError('invalid evidence file')
        chunks = []
        while True:
            block = os.read(fd, 1048576)
            if not block:
                break
            chunks.append(block)
        return b''.join(chunks)
    finally:
        os.close(fd)

def _uint(v):
    return type(v) is int and 0 <= v < 2**64

def _bound(obj, schema, window, run_id):
    return isinstance(obj, dict) and obj.get('schema') == schema and obj.get('window') == window and obj.get('run_id') == run_id

def publish(directory, window, run_id, files):
    """Publish once after validating and hashing all supplied evidence files.

    Files must already be finalized in the marker directory. Missing or
    unverifiable evidence prevents publication. A crash may leave a harmless
    staging file; an existing completion is never overwritten.
    """
    if window not in ORDER or not isinstance(run_id, str) or not SAFE.fullmatch(run_id) or run_id in ('.', '..'):
        raise ValueError('invalid window or run identity')
    if not isinstance(files, dict) or set(files) != set(KEYS) or len(set(files.values())) != len(KEYS):
        raise ValueError('missing or duplicate evidence')
    dfd = os.open(Path(directory), os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW)
    staging = '.receipt-' + uuid.uuid4().hex
    created = False
    try:
        start = _read(dfd, window + '.start.json')
        if json.loads(start) != {'schema':'kpf50.window-start.v1', 'window':window, 'run_id':run_id}:
            raise ValueError('start identity mismatch')
        decoded, evidence = {}, {}
        for key in KEYS:
            raw = _read(dfd, files[key])
            decoded[key] = json.loads(raw)
            evidence[key] = {'file':files[key], 'sha256':hashlib.sha256(raw).hexdigest()}
        out, clean = decoded['outcome'], decoded['cleanup']
        if not _bound(out, 'kpf50.window-outcome.v1', window, run_id) or out.get('complete') is not True:
            raise ValueError('missing complete outcome')
        if not _bound(clean, 'kpf50.cleanup.v1', window, run_id) or clean.get('verified_dead') is not True or type(clean.get('remaining_children')) is not int or clean['remaining_children'] != 0:
            raise ValueError('cleanup unverified')
        clocks = []
        for key in ('clock_before', 'clock_after'):
            c = decoded[key]
            if not _bound(c, 'kpf50.clock-sample.v1', window, run_id) or c.get('phase') != key or not all(_uint(c.get(x)) for x in ('hsa_tick','hsa_hz','mono_before_ns','mono_after_ns')) or c['hsa_hz'] == 0 or c['mono_before_ns'] > c['mono_after_ns']:
                raise ValueError('invalid clock proof')
            clocks.append(c)
        if clocks[0]['hsa_hz'] != clocks[1]['hsa_hz'] or clocks[0]['hsa_tick'] >= clocks[1]['hsa_tick'] or clocks[0]['mono_after_ns'] > clocks[1]['mono_before_ns']:
            raise ValueError('clock samples do not bracket window')
        trace = decoded['trace_manifest']
        if not _bound(trace, 'kpf50.trace-manifest.v1', window, run_id) or trace.get('complete') is not True or not isinstance(trace.get('files'), list) or not trace['files']:
            raise ValueError('missing trace proof')
        trace_names = set()
        for entry in trace['files']:
            if not isinstance(entry, dict) or set(entry) != {'file','sha256'} or not isinstance(entry['sha256'], str) or not DIGEST.fullmatch(entry['sha256']) or entry['file'] in trace_names:
                raise ValueError('invalid trace entry')
            if entry['file'] in files.values() or entry['file'] in (window + '.start.json', window + '.complete.json'):
                raise ValueError('trace overlaps control evidence')
            trace_names.add(entry['file'])
            trace_data = _read(dfd, entry['file'])
            if not trace_data or hashlib.sha256(trace_data).hexdigest() != entry['sha256']:
                raise ValueError('trace digest mismatch')
        receipt = {'schema':'kpf50.window-complete.v1', 'window':window, 'run_id':run_id, 'start_sha256':hashlib.sha256(start).hexdigest(), 'evidence':evidence}
        raw = (json.dumps(receipt, sort_keys=True, separators=(',', ':')) + '\n').encode()
        fd = os.open(staging, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW, 0o600, dir_fd=dfd)
        created = True
        try:
            view = memoryview(raw)
            while view:
                n = os.write(fd, view)
                if n <= 0: raise OSError('short receipt write')
                view = view[n:]
            os.fsync(fd)
        finally:
            os.close(fd)
        os.link(staging, window + '.complete.json', src_dir_fd=dfd, dst_dir_fd=dfd, follow_symlinks=False)
        os.fsync(dfd)
        return receipt
    finally:
        if created:
            try:
                os.unlink(staging, dir_fd=dfd)
                os.fsync(dfd)
            except FileNotFoundError:
                pass
        os.close(dfd)
