#!/usr/bin/env python3
"""Compare two retained fixture blobs against each other and the fixed oracle.

The caller supplies original per-file SHA-256 digests; this program verifies
content, not source identity, capture provenance or measurement warrant.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import sys

ORACLE_PATH = Path(__file__).resolve().parent.parent / 'kpf60-f16-writer-oracle-20261104' / 'oracle.py'
SPEC = importlib.util.spec_from_file_location('kpf60_fixed_oracle', ORACLE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError('fixed oracle is unavailable')
ORACLE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ORACLE)
SHA = re.compile(r'[0-9a-f]{64}\Z')
ARM_NAMES = ('baseline', 'observed')


def _read_blob(root, entry):
    if not isinstance(entry, dict) or set(entry) != {'file', 'sha256'}:
        raise ValueError('each arm requires exactly file and sha256')
    name = entry['file']
    if not isinstance(name, str) or not name or Path(name).name != name or name in ('.', '..'):
        raise ValueError('blob path must be a single filename')
    if not isinstance(entry['sha256'], str) or SHA.fullmatch(entry['sha256']) is None:
        raise ValueError('invalid original digest')
    dfd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        fd = os.open(name, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW, dir_fd=dfd)
        try:
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode) or before.st_size > 1024 * 1024:
                raise ValueError('blob is not a small regular file')
            with os.fdopen(fd, 'rb', closefd=False) as f:
                data = f.read(1024 * 1024 + 1)
            after = os.fstat(fd)
            attrs = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
            if any(getattr(before, k) != getattr(after, k) for k in attrs) or len(data) != before.st_size:
                raise ValueError('blob changed during read')
        finally:
            os.close(fd)
    finally:
        os.close(dfd)
    actual = hashlib.sha256(data).hexdigest()
    if actual != entry['sha256']:
        raise ValueError('blob digest mismatch')
    return data, actual, (before.st_dev, before.st_ino)


def verify(root, manifest):
    root = Path(root)
    if not root.is_absolute() or root.is_symlink() or not root.is_dir() or root.resolve(strict=True) != root:
        raise ValueError('root must be a canonical absolute non-symlink directory')
    if not isinstance(manifest, dict) or set(manifest) != {'schema', 'baseline', 'observed'}:
        raise ValueError('invalid manifest fields')
    if manifest['schema'] != 'kpf60.fixture-blob-pair.v1':
        raise ValueError('invalid manifest schema')
    data = {name: _read_blob(root, manifest[name]) for name in ARM_NAMES}
    if data['baseline'][2] == data['observed'][2]:
        raise ValueError('arms must be separately captured files')
    checks = {name: ORACLE.compare(data[name][0]) for name in ARM_NAMES}
    return {
        'schema': 'kpf60.fixture-blob-comparison.v1',
        'status': 'MATCH' if all(x[0] for x in checks.values()) and data['baseline'][0] == data['observed'][0] else 'MISMATCH',
        'arm_results': {name: {'sha256': data[name][1], 'size_bytes': len(data[name][0]),
                               'matches_fixed_oracle': checks[name][0], 'detail': checks[name][1]}
                        for name in ARM_NAMES},
        'arms_identical': data['baseline'][0] == data['observed'][0],
        'scope': 'fixed fixture data-section comparison only; no source, device, provenance or measurement warrant',
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', help='absolute directory containing two captured blob files')
    parser.add_argument('manifest', help='JSON file containing schema and both file/digest pairs')
    args = parser.parse_args(argv)
    try:
        manifest = json.loads(Path(args.manifest).read_text(encoding='utf-8'))
        result = verify(args.root, manifest)
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(json.dumps({'status': 'INVALID', 'reason': str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0 if result['status'] == 'MATCH' else 1


if __name__ == '__main__':
    raise SystemExit(main())
