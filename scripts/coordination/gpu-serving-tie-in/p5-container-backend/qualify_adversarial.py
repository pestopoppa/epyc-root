#!/usr/bin/env python3
"""Bounded P5 container escape controls; not a complete isolation proof."""
import argparse
import hashlib
import importlib.util
import json
import shlex
import sys
from pathlib import Path

from container_backend import IsolatedContainer


# These execute inside the same model-command sandbox. EACCES is the specific
# errno used by the in-container exec_sandbox filter, not merely any failure.
PROBE = r'''import ctypes, errno, json, os, platform, socket
out = {}
for name, family in [('socket_inet', socket.AF_INET), ('socket_unix', socket.AF_UNIX)]:
    try:
        s = socket.socket(family, socket.SOCK_STREAM); s.close(); out[name] = 0
    except OSError as e: out[name] = e.errno
libc = ctypes.CDLL(None, use_errno=True)
for name, fn in [('unshare', lambda: libc.unshare(0)),
                 ('ptrace', lambda: libc.ptrace(-1, 0, None, None)),
                 ('io_uring', lambda: libc.syscall(425, 1, None))]:
    ctypes.set_errno(0); result = fn(); out[name] = ctypes.get_errno() if result == -1 else 0
out['machine'] = platform.machine()
try:
    with open('/proc/1/environ', 'rb') as f: f.read(1)
    out['foreign_proc_denied'] = False
except OSError: out['foreign_proc_denied'] = True
print(json.dumps(out, sort_keys=True))'''


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def run_checks(env):
    code, out, err = env._exec('python3 -c ' + shlex.quote(PROBE), 30)
    require(code == 0, 'sandbox syscall probe failed: ' + (err or out)[-1000:])
    observed = json.loads(out.strip())
    require(observed.get('machine') in ('x86_64', 'AMD64'), 'unexpected architecture for syscall number')
    for key in ('socket_inet', 'socket_unix', 'unshare', 'ptrace', 'io_uring'):
        require(observed.get(key) == 13, f'{key}: expected EACCES, got {observed.get(key)!r}')
    require(observed.get('foreign_proc_denied') is True, 'foreign process environment readable')
    marker = 'P5_ADVERSARIAL_CONTROL_20261102'
    require(env.write_file('p5_adversarial_control.txt', marker), 'positive file write failed')
    require(env.read_file('p5_adversarial_control.txt') == marker, 'positive file read failed')
    require(env.read_file('../etc/passwd') is None, 'traversal read accepted')
    require(not env.write_file('../p5_escape', marker), 'traversal write accepted')
    code, _ = env.run('ln -s /etc p5_adversarial_link', 15)
    require(code == 0 and env.read_file('p5_adversarial_link/passwd') is None,
            'symlink escape not refused')
    code, _ = env.run('test ! -w /opt/p5_sandbox && test ! -S /var/run/docker.sock && test ! -e /mnt/raid0/llm', 15)
    require(code == 0, 'host mount/socket or writable containment source')
    return observed


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--image-id', required=True)
    p.add_argument('--runner', required=True)
    p.add_argument('--runner-sha256', required=True)
    p.add_argument('--sandbox-source-dir', required=True)
    p.add_argument('--sandbox-sha256-json', required=True)
    p.add_argument('--output', required=True)
    a = p.parse_args()
    raw = Path(a.runner).read_bytes()
    require(hashlib.sha256(raw).hexdigest() == a.runner_sha256, 'harness changed')
    spec = importlib.util.spec_from_file_location('p5_adversarial_harness', a.runner)
    harness = importlib.util.module_from_spec(spec); sys.modules[spec.name] = harness; spec.loader.exec_module(harness)
    pins = json.loads(Path(a.sandbox_sha256_json).read_text())
    with IsolatedContainer(harness, a.image_id, a.sandbox_source_dir, pins) as env:
        observed = run_checks(env)
    # Context exit has removed the captured container before this result exists.
    result = {'schema': 'p5.adversarial-qualification.v1', 'verdict': 'PASS',
              'image_id': a.image_id, 'runner_sha256': a.runner_sha256,
              'sandbox_sha256': pins, 'syscalls': observed,
              'checks': ['syscall_denials', 'foreign_proc_denied', 'positive_file',
                         'traversal_symlink_refused', 'host_paths_and_source_guard', 'container_cleanup'],
              'scope': 'bounded controls on one image; not complete isolation or scorer qualification'}
    Path(a.output).write_text(json.dumps(result, indent=2) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
