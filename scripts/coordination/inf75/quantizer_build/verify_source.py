#!/usr/bin/env python3
"""Verify a source tree against a pinned tree-manifest.json."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

SHA256_RE = re.compile(r'[0-9a-f]{64}\Z')


def file_digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def parse_manifest(rows):
    if not isinstance(rows, list):
        raise ValueError('manifest root must be a list')
    expected = {}
    for row in rows:
        if not isinstance(row, list) or len(row) not in (3, 4):
            raise ValueError('malformed manifest row')
        name, kind = row[:2]
        if (not isinstance(name, str) or not name or name.startswith('/') or
                any(part in ('', '.', '..') for part in name.split('/')) or name in expected):
            raise ValueError(f'invalid or duplicate manifest path: {name!r}')
        if kind == 'dir' and len(row) == 3:
            mode, value = row[2], None
        elif kind == 'file' and len(row) == 4:
            value, mode = row[2:]
            if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
                raise ValueError(f'invalid file digest for {name}')
        elif kind == 'symlink' and len(row) == 3:
            value, mode = row[2], None
            if not isinstance(value, str):
                raise ValueError(f'invalid symlink target for {name}')
        else:
            raise ValueError(f'invalid manifest entry type or shape: {name}')
        if kind != 'symlink' and (not isinstance(mode, int) or isinstance(mode, bool) or
                                  mode < 0 or mode > 0o7777):
            raise ValueError(f'invalid mode for {name}')
        expected[name] = (kind, value, mode)
    return expected


def actual_entries(root):
    actual = {}

    def walk_error(error):
        raise error

    try:
        for current, dirs, files in os.walk(root, topdown=True, followlinks=False,
                                            onerror=walk_error):
            base = Path(current)
            for name in list(dirs) + files:
                path = base / name
                rel = path.relative_to(root).as_posix()
                info = path.lstat()
                mode = stat.S_IMODE(info.st_mode)
                if stat.S_ISLNK(info.st_mode):
                    actual[rel] = ('symlink', os.readlink(path), None)
                    if name in dirs:
                        dirs.remove(name)
                elif stat.S_ISDIR(info.st_mode):
                    actual[rel] = ('dir', None, mode)
                elif stat.S_ISREG(info.st_mode):
                    actual[rel] = ('file', file_digest(path), mode)
                else:
                    actual[rel] = ('special', None, mode)
    except OSError as exc:
        raise ValueError(f'could not walk source tree: {exc}') from exc
    return actual


def verify(root, manifest, expected_sha256):
    """Raise ValueError unless root matches manifest, whose bytes match the pin."""
    root, manifest = Path(root), Path(manifest)
    if not isinstance(expected_sha256, str) or not SHA256_RE.fullmatch(expected_sha256):
        raise ValueError('expected manifest SHA-256 must be 64 lowercase hex characters')
    try:
        raw = manifest.read_bytes()
        actual_sha256 = hashlib.sha256(raw).hexdigest()
        if actual_sha256 != expected_sha256:
            raise ValueError(f'manifest SHA-256 mismatch: expected {expected_sha256}, got {actual_sha256}')
        expected = parse_manifest(json.loads(raw))
        if root.is_symlink() or not root.is_dir():
            raise ValueError(f'source root is missing or not a directory: {root}')
        actual = actual_entries(root)
    except (OSError, json.JSONDecodeError, TypeError) as exc:
        raise ValueError(f'could not read source manifest/tree: {exc}') from exc

    errors = []
    for name in sorted(expected.keys() - actual.keys()):
        errors.append(f'missing: {name}')
    for name in sorted(actual.keys() - expected.keys()):
        errors.append(f'added: {name} ({actual[name][0]})')
    for name in sorted(expected.keys() & actual.keys()):
        if expected[name] != actual[name]:
            errors.append(f'changed: {name} expected={expected[name]!r} actual={actual[name]!r}')
    if errors:
        raise ValueError('\n'.join(errors))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', help='source tree root')
    parser.add_argument('manifest', help='tree-manifest.json path')
    parser.add_argument('expected_sha256', help='pinned SHA-256 of manifest bytes')
    args = parser.parse_args(argv)
    try:
        verify(args.root, args.manifest, args.expected_sha256)
    except ValueError as exc:
        print(f'source verification failed: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
