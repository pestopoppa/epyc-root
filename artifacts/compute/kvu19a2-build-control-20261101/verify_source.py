#!/usr/bin/env python3
"""Validate frozen, non-target control source without executing it."""
import hashlib
import json
import os
import stat
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EXPECTED = {'CMakeLists.txt', 'control.c'}


def verify(root=ROOT):
    manifest = json.loads((root / 'SOURCE.json').read_text())
    if manifest.get('schema') != 'kvu19.build-control-source.v1' or set(manifest.get('files', {})) != EXPECTED:
        raise ValueError('invalid inventory')
    source = root / 'source'
    if source.is_symlink() or not source.is_dir() or {p.name for p in source.iterdir()} != EXPECTED:
        raise ValueError('unexpected control source entries')
    for name in sorted(EXPECTED):
        fd = os.open(source / name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode):
                raise ValueError('non-regular control input')
            with os.fdopen(fd, 'rb', closefd=False) as f:
                digest = hashlib.file_digest(f, 'sha256').hexdigest()
            if digest != manifest['files'][name]:
                raise ValueError('control source hash mismatch')
        finally:
            os.close(fd)
    return True


if __name__ == '__main__':
    verify()
    print('control source verified')
