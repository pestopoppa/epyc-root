#!/usr/bin/env python3
"""Source-only packet anchor preflight. Never launches or admits target work."""
import hashlib
import json
import os
from pathlib import Path
import stat
import sys

ROOT = Path('/mnt/raid0/llm/tmp/heterogeneous-slot-fabric-residency')
PACKET = ROOT / 'kpf50-supervisor-20261105'
ANCHOR = '6867c224b2742daf798c51cd5f4851644367883f533826fa7e4e0cbd8f0095c2'
LOCAL = {'supervisor.py', 'plan.json', 'dependencies.json'}
EXTERNAL = {
    str(ROOT / 'kpf50-model-admission-20261105' / name)
    for name in ('seals.json', 'check_models.py', 'models.stat.json')
}

def read_regular(path):
    # Traverse each directory with O_NOFOLLOW: final-component protection alone
    # would still allow a substituted packet or ancestor directory.
    path = Path(path)
    if not path.is_absolute() or '..' in path.parts:
        raise ValueError('noncanonical absolute path')
    directory = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in path.parts[1:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                            dir_fd=directory)
            os.close(directory)
            directory = child
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                     dir_fd=directory)
        with os.fdopen(fd, 'rb') as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode) or before.st_size > 1048576:
                raise ValueError('nonregular or oversized anchor input')
            data = stream.read(1048577)
            after = os.fstat(stream.fileno())
            fields = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
            if len(data) > 1048576 or any(getattr(before, k) != getattr(after, k) for k in fields):
                raise ValueError('anchor input changed while reading')
            return data
    finally:
        os.close(directory)

def verify(path, digest):
    if not isinstance(digest, str) or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
        raise ValueError('invalid digest')
    data = read_regular(path)
    if hashlib.sha256(data).hexdigest() != digest:
        raise ValueError('anchor mismatch: ' + str(path))
    return data

def main():
    if len(sys.argv) != 1:
        raise ValueError('no overrides permitted')
    seals = json.loads(verify(PACKET / 'seals.json', ANCHOR))
    if not isinstance(seals, dict) or set(seals) != LOCAL:
        raise ValueError('unexpected supervisor seal set')
    contents = {name: verify(PACKET / name, digest) for name, digest in seals.items()}
    dependencies = json.loads(contents['dependencies.json'])
    if not isinstance(dependencies, dict) or set(dependencies) != EXTERNAL:
        raise ValueError('unexpected external dependency set')
    for path, digest in dependencies.items():
        verify(path, digest)
    # This receipt deliberately cannot satisfy a supervisor/window result schema.
    print(json.dumps({'schema': 'kpf50.anchor-preflight.v1',
                      'status': 'SOURCE_BYTES_MATCH_ONLY', 'target_enabled': False,
                      'supervisor_seals_sha256': ANCHOR,
                      'native_validator_qualified': False}, sort_keys=True))

if __name__ == '__main__':
    main()
