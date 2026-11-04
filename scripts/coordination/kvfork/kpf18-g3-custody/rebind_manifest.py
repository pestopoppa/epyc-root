#!/usr/bin/env python3
"""Rebind a diagnostic manifest only to exact retained bytes; never authorizes a run."""
import hashlib
import json
import os
from pathlib import Path
import re
import stat

LINE = re.compile(r'^([0-9a-f]{64})  (/.+)$')


def parent_fd(path):
    """Open every parent relative to its predecessor, rejecting symlink traversal."""
    text = os.fspath(path)
    if not os.path.isabs(text) or '\n' in text:
        raise ValueError('path must be absolute and contain no newline')
    parts = text.split('/')[1:]
    if not parts or any(part in ('', '.', '..') for part in parts):
        raise ValueError('noncanonical path')
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in parts[:-1]:
            nxt = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = nxt
        return fd, parts[-1]
    except BaseException:
        os.close(fd)
        raise


def read_regular(path):
    parent, name = parent_fd(path)
    try:
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        try:
            if not stat.S_ISREG(os.fstat(fd).st_mode):
                raise ValueError(f'not a regular file: {path}')
            with os.fdopen(fd, 'rb', closefd=False) as stream:
                return stream.read()
        finally:
            os.close(fd)
    finally:
        os.close(parent)


def rebind(manifest: Path, mapping: dict[str, str], output: Path):
    if not isinstance(mapping, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in mapping.items()):
        raise ValueError('mapping must contain string paths')
    lines = read_regular(manifest).decode('utf-8').splitlines()
    if not lines:
        raise ValueError('empty manifest')
    seen = set()
    result = []
    for line in lines:
        match = LINE.fullmatch(line)
        if not match:
            raise ValueError('malformed manifest line')
        digest, old = match.groups()
        if old in seen:
            raise ValueError('duplicate path')
        seen.add(old)
        selected = mapping.get(old, old)
        if hashlib.sha256(read_regular(selected)).hexdigest() != digest:
            raise ValueError(f'digest mismatch: {selected}')
        result.append(f'{digest}  {selected}')
    if set(mapping) - seen:
        raise ValueError('unbound mapping')
    parent, name = parent_fd(output)
    try:
        fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as stream:
                stream.write('\n'.join(result) + '\n')
        except BaseException:
            os.unlink(name, dir_fd=parent)
            raise
    finally:
        os.close(parent)


if __name__ == '__main__':
    import sys
    if len(sys.argv) != 4:
        raise SystemExit('usage: rebind_manifest.py manifest mapping.json output')
    try:
        mapping = json.loads(read_regular(sys.argv[2]))
        rebind(Path(sys.argv[1]), mapping, Path(sys.argv[3]))
    except (OSError, ValueError, TypeError) as exc:
        raise SystemExit(f'REFUSED: {exc}')
