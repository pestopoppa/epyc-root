#!/usr/bin/env python3
"""Offline input manifest for prospective builds; not a build launcher."""
import argparse
import hashlib
import json
import os
import stat
from pathlib import Path


def file_hash(path):
    # A non-regular entry can otherwise block at open (notably a FIFO).
    # fstat after opening remains authoritative even if the path changes.
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK
    fd = os.open(path, flags)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise ValueError(f'not a regular file: {path}')
        h = hashlib.sha256()
        while True:
            data = os.read(fd, 1024 * 1024)
            if not data:
                break
            h.update(data)
        after = os.fstat(fd)
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            raise ValueError(f'file changed during hashing: {path}')
        return {'sha256': h.hexdigest(), 'size': after.st_size, 'mode': stat.S_IMODE(after.st_mode)}
    finally:
        os.close(fd)


def source_manifest(root):
    if root.is_symlink() or not root.is_dir():
        raise ValueError('source root must be a real directory')
    result = {}
    def fail_walk(error):
        raise error

    for directory, dirs, files in os.walk(root, followlinks=False, onerror=fail_walk):
        base = Path(directory)
        for name in dirs + files:
            p = base / name
            if p.is_symlink():
                raise ValueError(f'symlink refused: {p}')
        for name in sorted(files):
            p = base / name
            result[p.relative_to(root).as_posix()] = file_hash(p)
    return dict(sorted(result.items()))


def snapshot(source, tools):
    return {'schema': 'kvu19.build-inputs.v1', 'source': source_manifest(source),
            'tools': {name: file_hash(path) for name, path in sorted(tools.items())}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--tool', action='append', default=[], metavar='NAME=PATH')
    parser.add_argument('--verify', type=Path, help='expected JSON manifest; mismatch exits nonzero')
    args = parser.parse_args()
    tools = {}
    for arg in args.tool:
        name, sep, path = arg.partition('=')
        if not sep or not name or not path or name in tools:
            parser.error('each tool must be a unique NAME=PATH')
        tools[name] = Path(path)
    if not tools:
        parser.error('at least one explicit tool is required')
    actual = snapshot(args.source, tools)
    if args.verify:
        if json.loads(args.verify.read_text()) != actual:
            raise SystemExit('input manifest mismatch')
    print(json.dumps(actual, sort_keys=True, indent=2))


if __name__ == '__main__':
    main()
