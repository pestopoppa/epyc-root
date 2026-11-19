"""Pinned SR-7 startup evidence; no inference is initiated here.

Construct before a grant: runtime artifacts are hashed there, weights are not.
A caller must authenticate the preflight digest and complete argv independently.
"""
import hashlib
import http.client
import json
import os
from pathlib import Path
import threading
import time

from contained_lifecycle import _SR6
from runtime_manifest import REQUIRED, verify_runtime_manifest
from process_linkage import verify_process_linkage
from verified_post import process_starttime, verify_owned_loopback_listener


def _stat(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError('pinned input unavailable')
    st = path.stat()
    return dict(dev=st.st_dev, ino=st.st_ino, size=st.st_size,
                mtime_ns=st.st_mtime_ns, ctime_ns=st.st_ctime_ns)


class StartupIdentity:
    """Readiness verifier suitable as capture_contained(..., verify=instance).

    Hashes runtime during construction, binds model to a pre-hashed stat receipt,
    then checks the actual process and health. CPU affinity is exact for every
    observed server thread; this is a snapshot, not continuous residency proof.
    """
    def __init__(self, *, preflight, preflight_sha256, expected_argv, cpus,
                 admission, timeout_s, smoke=False):
        if (not isinstance(preflight, Path) or not preflight.is_absolute() or
            preflight.is_symlink() or not isinstance(preflight_sha256, str) or
            not isinstance(expected_argv, list) or not expected_argv or
            not isinstance(cpus, set) or not cpus or any(type(x) is not int or x < 0 for x in cpus) or
            not callable(admission) or type(timeout_s) not in (int, float) or
            not 0 < timeout_s <= 1800 or type(smoke) is not bool or (smoke and len(cpus) > 4)):
            raise ValueError('invalid startup identity configuration')
        raw = preflight.read_bytes()
        if len(raw) > 1024 * 1024 or hashlib.sha256(raw).hexdigest() != preflight_sha256:
            raise ValueError('preflight digest mismatch')
        receipt = json.loads(raw)
        if receipt.get('schema') != 'sr7.reused-preflight.v1':
            raise ValueError('unknown preflight schema')
        self.build_root = Path(receipt['build_root'])
        self.model = receipt['smoke_model' if smoke else 'model']
        self.model_path = Path(self.model['path'])
        if not self.model_path.is_absolute() or _stat(self.model_path) != self.model['stat']:
            raise ValueError('model stat does not match preflight')
        self.argv = list(expected_argv)
        if self.argv[0] != str(self.build_root / 'bin/llama-server'):
            raise ValueError('expected server is not pinned build')
        flags = [i for i, arg in enumerate(self.argv) if arg in ('-m', '--model')]
        if len(flags) != 1 or flags[0] + 1 >= len(self.argv) or self.argv[flags[0] + 1] != str(self.model_path):
            raise ValueError('argv does not bind selected model')
        before = {x: _stat(self.build_root / x) for x in REQUIRED}
        self.manifest = verify_runtime_manifest(self.build_root, receipt['runtime_manifest_sha256'])
        self.artifact_stats = {x: _stat(self.build_root / x) for x in REQUIRED}
        if before != self.artifact_stats:
            raise ValueError('runtime changed during preflight')
        self.receipt_sha256 = preflight_sha256
        self.cpus, self.admission, self.timeout_s, self.smoke = cpus.copy(), admission, timeout_s, smoke

    def __call__(self, process, port):
        if type(port) is not int or not 1 <= port <= 65535:
            raise ValueError('invalid port')
        deadline = min(time.monotonic() + self.timeout_s,
                       time.monotonic() + max(0, self.admission.deadline - time.time()))
        done = threading.Event()
        result = {}
        def work():
            try:
                while time.monotonic() < deadline:
                    if self.admission() is not True or process.poll() is not None:
                        raise ValueError('admission revoked or server exited')
                    try:
                        result['evidence'] = self._check(process, port)
                        return
                    except (OSError, ValueError, http.client.HTTPException) as exc:
                        result['last'] = exc
                    time.sleep(min(0.1, max(0, deadline - time.monotonic())))
                raise ValueError('startup deadline expired') from result.get('last')
            except Exception as exc:
                result['error'] = exc
            finally:
                done.set()
        threading.Thread(target=work, daemon=True).start()
        while not done.wait(0.05):
            if (time.monotonic() >= deadline or os.path.lexists(self.admission.stop_path)
                    or process.poll() is not None):
                raise ValueError('startup cancelled or deadline expired')
        if (time.monotonic() >= deadline or os.path.lexists(self.admission.stop_path)
                or process.poll() is not None):
            raise ValueError('startup cancelled or deadline expired')
        if 'error' in result:
            raise result['error']
        return result['evidence']

    def _check(self, process, port):
        pid = process.pid
        birth = process_starttime(pid)
        proc = Path('/proc') / str(pid)
        cmd = (proc / 'cmdline').read_bytes()
        if cmd != b'\0'.join(x.encode() for x in self.argv) + b'\0':
            raise ValueError('server command mismatch')
        env = (proc / 'environ').read_bytes().split(b'\0')
        if [x for x in env if x.startswith(b'LD_LIBRARY_PATH=')] != [b'LD_LIBRARY_PATH=' + str(self.build_root / 'bin').encode()]:
            raise ValueError('server library environment mismatch')
        if _stat(self.model_path) != self.model['stat']:
            raise ValueError('model identity changed')
        if any(_stat(self.build_root / x) != st for x, st in self.artifact_stats.items()):
            raise ValueError('runtime identity changed')
        linkage = verify_process_linkage(pid, birth, self.build_root)
        # Require the actual preflight model inode to be mapped by this process.
        maps = (proc / 'maps').read_text()
        st = self.model['stat']
        expected_dev = (os.major(st['dev']), os.minor(st['dev']))
        found = False
        for line in maps.splitlines():
            parts = line.split(maxsplit=5)
            if len(parts) == 6 and parts[5] == str(self.model_path):
                dev = tuple(int(x, 16) for x in parts[3].split(':'))
                found |= dev == expected_dev and int(parts[4]) == st['ino']
        if not found:
            raise ValueError('selected model not mapped')
        tids = sorted(int(p.name) for p in (proc / 'task').iterdir() if p.name.isdigit())
        if not tids or any(os.sched_getaffinity(tid) != self.cpus for tid in tids):
            raise ValueError('server thread CPU affinity mismatch')
        verify_owned_loopback_listener(pid, birth, port)
        conn = http.client.HTTPConnection('127.0.0.1', port, timeout=0.25)
        try:
            conn.request('GET', '/health', headers={'Connection':'close'})
            response = conn.getresponse()
            body = response.read(4097)
            if response.status != 200 or len(body) > 4096 or json.loads(body) != {'status':'ok'}:
                raise ValueError('server not ready')
        finally:
            conn.close()
        if process.poll() is not None or process_starttime(pid) != birth or self.admission() is not True:
            raise ValueError('identity or admission changed')
        verify_owned_loopback_listener(pid, birth, port)
        return {'schema':'sr7.startup-identity.v1', 'pid':pid, 'starttime_ticks':birth,
                'preflight_sha256':self.receipt_sha256, 'model_sha256':self.model['sha256'],
                'model_stat':st, 'argv':self.argv, 'cpus':sorted(self.cpus), 'thread_ids':tids,
                'linkage':linkage, 'science':not self.smoke,
                'limitations':['snapshot; future loads and affinity changes not observed',
                               'preflight approval and source attribution external']}
