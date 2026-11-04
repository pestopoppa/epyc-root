#!/usr/bin/env python3
"""Prepare a review-only source manifest for the disabled G3 driver draft.

The caller must separately bind this program and its output to an approved
entry. This is not an entry/admission check or a transitive native-source seal.
"""
import hashlib
import re
from pathlib import Path, PurePosixPath
import sys

ORIGINAL_SHA = 'c8d9a107dfe02331ee3f68b0569b93bd3ae08e36d225f4cf2249d5cbcc684ea2'
OLD_DRIVER = '917445e3ff39475690be391376015c02a5b37fc107844941e5277b4dd4bff903'
NEW_DRIVER = '48af88fa8e293efde5fbe1b2bf3112500d85f1c25bfab9ac03420d86ddb7b741'
HELPERS = {
 'adapter.py': '9ec4e80d7c0ffe7f6f2fc5e0cc3d9e1872b2a64cae8b29e77dc6744709470a1f',
 'driver_boundary.py': '6d5830c6dfc53e62a3694387edd23b337546d45c9aac8db2db4c4ed408633b79',
 'preload_integration.py': 'a7958fc86664381b287c589e14f21972473336cd3df58b4f3087e375e4a4b88d',
 'verify_receipt.py': '2f820a5a215a36aa822dee4fb43cec4eb8fddb57b94b2434a85dfa63857eb506',
 'test_preload_integration.py': '38df19e398d18437e97ff9f319a75eb5f19a7301e891491a34ec3ba0e0c3f8ab',
 'test_verify_receipt.py': '4c2e871dae0a754d61df4065752170d657d01079754d525389f5a2e6e5839d87',
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_regular(root, name):
    if not re.fullmatch(r'[A-Za-z0-9_./-]+', name):
        raise ValueError('unsafe path')
    path = PurePosixPath(name)
    if path.is_absolute() or any(part in ('.', '..') for part in name.split('/')):
        raise ValueError('unsafe path')
    current = root
    for part in path.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError('symlink in source path')
    if not current.is_file():
        raise ValueError('missing or non-file source')
    return current.read_bytes()


def transition(root, expected_manifest_sha, replacements, helpers):
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise ValueError('invalid root')
    raw = read_regular(root, 'SOURCES.sha256')
    if digest(raw) != expected_manifest_sha:
        raise ValueError('source manifest drift')
    entries = {}
    for line in raw.decode('ascii').splitlines():
        m = re.fullmatch(r'([a-f0-9]{64})  ([A-Za-z0-9_./-]+)', line)
        if not m or m[2] in entries:
            raise ValueError('invalid or duplicate entry')
        entries[m[2]] = m[1]
    for name, (old, new) in replacements.items():
        if entries.get(name) != old:
            raise ValueError('replacement baseline mismatch')
        entries[name] = new
    for name, value in helpers.items():
        if name in entries:
            raise ValueError('helper already enrolled')
        entries[name] = value
    for name, expected in entries.items():
        if digest(read_regular(root, name)) != expected:
            raise ValueError('source drift: ' + name)
    return ''.join(f'{entries[name]}  {name}\n' for name in sorted(entries)).encode('ascii')


def main():
    if len(sys.argv) != 2:
        raise SystemExit('usage: transition.py CANDIDATE_ROOT')
    result = transition(sys.argv[1], ORIGINAL_SHA, {'driver.py': (OLD_DRIVER, NEW_DRIVER)}, HELPERS)
    sys.stdout.buffer.write(result)


if __name__ == '__main__':
    main()
