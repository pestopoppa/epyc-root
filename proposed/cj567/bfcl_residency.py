"""Linux local CPU-server custody, not GPU placement or model-quality evidence.

Prepare the model record BEFORE publishing a row. At run time only stat the model;
never rehash weights in a grant. These proofs assume a trusted local kernel and
immutable prepared files, not an adversarial server or root user.
"""
import hashlib
import json
import os
from pathlib import Path
import re
from urllib.request import Request, ProxyHandler, HTTPRedirectHandler, build_opener


def file_sha256(path):
    with open(path, 'rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def fingerprint(stat):
    return {key: getattr(stat, key) for key in
            ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns')}


def checked_manifest(path, expected):
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError('manifest digest mismatch')
    return json.loads(raw)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('native endpoint redirect refused')


class LocalNativeTransport:
    """Bind a caller-owned PID to a direct IPv4 loopback listener and mmap model.

    Build manifest: {server_binary_sha256, libraries: [{path, sha256}]}.
    Runtime manifest: {model, model_file: prepare_model(...), argv: [exact argv]}.
    Both manifest digests must be in capture identity. Require a single model file;
    split GGUF and GPU servers need additional instruments before use.
    """
    def __init__(self, pid, port, identity, build_manifest, runtime_manifest,
                 timeout=300, proc_root='/proc', request_guard=None):
        self.pid, self.port = int(pid), int(port)
        if self.pid <= 0 or not 0 < self.port < 65536:
            raise ValueError('invalid PID or port')
        self.proc = Path(proc_root) / str(self.pid)
        self.start_ticks = self._start_ticks()
        self.identity = dict(identity)
        self.build = checked_manifest(build_manifest, identity['build_manifest_sha256'])
        self.runtime = checked_manifest(runtime_manifest, identity['runtime_manifest_sha256'])
        self.model = self.runtime['model_file']
        if (self.runtime['model'] != identity['model'] or
                self.model['sha256'] != identity['model_sha256'] or
                self.build['server_binary_sha256'] != identity['server_binary_sha256']):
            raise ValueError('manifest identity mismatch')
        for sha in [self.model['sha256'], self.build['server_binary_sha256']]:
            if not isinstance(sha, str) or not re.fullmatch('[a-f0-9]{64}', sha):
                raise ValueError('invalid content digest')
        self.timeout = timeout
        self.request_guard = request_guard
        self.opener = build_opener(ProxyHandler({}), NoRedirect())
        argv = self.runtime['argv']
        required = {'--model': self.model['path'], '--alias': identity['model'],
                    '--host': '127.0.0.1', '--port': str(self.port), '--n-gpu-layers': '0'}
        for flag, value in required.items():
            if argv.count(flag) != 1 or argv.index(flag) + 1 >= len(argv) or argv[argv.index(flag) + 1] != value:
                raise ValueError('explicit CPU-server argument required: ' + flag)
        # Validate small executable/library content once per launch. Sample their
        # inode metadata again at every request; no runtime model hashing.
        self.artifacts = []
        for path, sha in [(self.proc / 'exe', identity['server_binary_sha256'])] + [
                (Path(item['path']), item['sha256']) for item in self.build['libraries']]:
            before = fingerprint(path.stat())
            if file_sha256(path) != sha or before != fingerprint(path.stat()):
                raise ValueError('server/library content mismatch')
            self.artifacts.append((path, sha, before))
        self.probe()

    def _start_ticks(self):
        # comm can contain spaces and ')'; fields after its final ')' start at 3.
        return self.proc.joinpath('stat').read_text().rsplit(')', 1)[1].split()[19]

    def probe(self):
        if self._start_ticks() != self.start_ticks:
            raise ValueError('server PID reused')
        cmdline = self.proc.joinpath('cmdline').read_bytes().split(b'\0')
        argv = [os.fsdecode(arg) for arg in cmdline if arg]
        if argv != self.runtime['argv']:
            raise ValueError('server argv changed')
        for path, _, expected in self.artifacts:
            if fingerprint(path.stat()) != expected:
                raise ValueError('server/library replaced or mutated')
        model_stat = Path(self.model['path']).stat()
        if fingerprint(model_stat) != self.model['stat']:
            raise ValueError('prepared model replaced or mutated')
        mapped = set()
        ggml_mapped = set()
        for line in self.proc.joinpath('maps').read_text().splitlines():
            fields = line.split(maxsplit=5)
            major, minor = (int(x, 16) for x in fields[3].split(':'))
            item = (os.makedev(major, minor), int(fields[4]))
            mapped.add(item)
            if len(fields) == 6 and Path(fields[5]).name.startswith('libggml'):
                ggml_mapped.add(item)
        for stat in [self.model['stat']] + [entry[2] for entry in self.artifacts]:
            if (stat['st_dev'], stat['st_ino']) not in mapped:
                raise ValueError('required model/server/library not mapped by server')
        bound = {(stat['st_dev'], stat['st_ino']) for _, _, stat in self.artifacts}
        if not ggml_mapped <= bound:
            raise ValueError('unbound mapped ggml library')
        listeners = set()
        for line in self.proc.joinpath('net/tcp').read_text().splitlines()[1:]:
            fields = line.split()
            if fields[1] == f'0100007F:{self.port:04X}' and fields[3] == '0A':
                listeners.add('socket:[' + fields[9] + ']')
        owned = set()
        for fd in self.proc.joinpath('fd').iterdir():
            try:
                owned.add(os.readlink(fd))
            except FileNotFoundError:
                pass  # unrelated descriptors may close while sampling
        if len(listeners) != 1 or not listeners <= owned:
            raise ValueError('endpoint listener not owned by server PID')
        if self._start_ticks() != self.start_ticks:
            raise ValueError('server changed during sample')
        return {'pid': self.pid, 'start_ticks': self.start_ticks,
                'boot_id': self.proc.parent.joinpath('sys/kernel/random/boot_id').read_text().strip(),
                'endpoint': f'http://127.0.0.1:{self.port}/v1/chat/completions',
                'listener': sorted(listeners), 'argv': argv,
                'model_path': self.model['path'], 'model_stat': self.model['stat'],
                'model_sha256': self.model['sha256'],
                'artifacts': [{'sha256': sha, 'stat': stat} for _, sha, stat in self.artifacts],
                'scope': 'local CPU process mappings; no GPU residency claim'}

    def __call__(self, payload):
        if payload['model'] != self.identity['model']:
            raise ValueError('request model mismatch')
        self.probe()
        endpoint = f'http://127.0.0.1:{self.port}/v1/chat/completions'
        request = Request(endpoint, data=json.dumps(payload, allow_nan=False).encode(),
                          headers={'Content-Type': 'application/json'})
        if self.request_guard is not None:
            self.request_guard(payload)  # recheck after residency/serialization, before HTTP
        with self.opener.open(request, timeout=self.timeout) as response:
            result = json.load(response)
        self.probe()
        return result
