#!/usr/bin/env python3
"""Strictly bind fixture blobs to a caller-pinned declaration and artifacts.

This checks retained content, not the truth or independent origin of receipts.
Never use it to invent a historical measurement warrant.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

import verify_pair

HEX = re.compile(r'[0-9a-f]{64}\Z')
COMMIT = re.compile(r'[0-9a-f]{40}\Z')
MAX = 1024 * 1024 * 512


def read_bound(root, entry, limit=MAX):
    if not isinstance(entry, dict) or set(entry) != {'file', 'sha256'}:
        raise ValueError('artifact must contain file and sha256')
    name, expected = entry['file'], entry['sha256']
    if not isinstance(name, str) or not name or Path(name).name != name or name in ('.', '..') or name.lower().endswith('.gguf'):
        raise ValueError('artifact name is invalid or model weights')
    if not isinstance(expected, str) or not HEX.fullmatch(expected):
        raise ValueError('invalid artifact digest')
    directory = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        fd = os.open(name, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW, dir_fd=directory)
        try:
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
                raise ValueError('artifact is not a bounded regular file')
            chunks = []
            while True:
                chunk = os.read(fd, 1024 * 1024)
                if not chunk: break
                chunks.append(chunk)
            after = os.fstat(fd)
            attrs = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns')
            data = b''.join(chunks)
            if any(getattr(before, k) != getattr(after, k) for k in attrs) or len(data) != before.st_size:
                raise ValueError('artifact changed during read')
        finally:
            os.close(fd)
    finally:
        os.close(directory)
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError('artifact digest mismatch')
    return data, (before.st_dev, before.st_ino)


def verify(root, contract, expected_contract_sha):
    root = Path(root)
    if not root.is_absolute() or root.is_symlink() or not root.is_dir() or root.resolve(strict=True) != root:
        raise ValueError('root must be canonical absolute non-symlink directory')
    if not isinstance(expected_contract_sha, str) or not HEX.fullmatch(expected_contract_sha):
        raise ValueError('independent contract digest required')
    canonical = json.dumps(contract, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()
    if hashlib.sha256(canonical).hexdigest() != expected_contract_sha:
        raise ValueError('contract digest mismatch')
    keys = {'schema', 'source_commit', 'selection', 'patch', 'binary', 'build_receipt', 'baseline', 'observed'}
    if not isinstance(contract, dict) or set(contract) != keys or contract['schema'] != 'kpf60.fixture-bound-pair.v1':
        raise ValueError('invalid contract')
    commit = contract['source_commit']
    if not isinstance(commit, str) or not COMMIT.fullmatch(commit):
        raise ValueError('invalid source commit')
    if contract['selection'] != {'cells': [1, 2, 5], 'layers': 2, 'row_bytes': 8, 'dtype': 'f16', 'v_transposed': False}:
        raise ValueError('selection does not match fixed oracle')
    artifacts = {}
    for name in ('patch', 'binary', 'build_receipt'):
        artifacts[name] = read_bound(root, contract[name])
    identities = [v[1] for v in artifacts.values()]
    if len(set(identities)) != len(identities):
        raise ValueError('source/build artifacts alias')
    try:
        build = json.loads(artifacts['build_receipt'][0])
    except (ValueError, UnicodeError) as exc:
        raise ValueError('invalid build receipt') from exc
    if not isinstance(build, dict) or set(build) != {'schema', 'source_commit', 'patch_sha256', 'binary_sha256', 'status'}:
        raise ValueError('invalid build receipt fields')
    if build != {'schema': 'kpf60.fixture-build.v1', 'source_commit': commit,
                 'patch_sha256': contract['patch']['sha256'], 'binary_sha256': contract['binary']['sha256'],
                 'status': 'built'}:
        raise ValueError('build receipt does not bind source, patch and binary')
    pair = {'schema': 'kpf60.fixture-blob-pair.v1'}
    capture_ids = []
    blobs = {}
    for arm in ('baseline', 'observed'):
        value = contract[arm]
        if not isinstance(value, dict) or set(value) != {'blob', 'receipt'}:
            raise ValueError('each arm requires blob and receipt')
        if not isinstance(value['blob'], dict):
            raise ValueError('invalid blob binding')
        blob_data, blob_identity = read_bound(root, value['blob'], 1024 * 1024)
        blobs[arm] = blob_data
        if blob_identity in identities: raise ValueError('blob aliases artifact')
        identities.append(blob_identity)
        raw, identity = read_bound(root, value['receipt'], 1024 * 1024)
        if identity in identities: raise ValueError('capture receipt aliases artifact')
        identities.append(identity)
        try:
            receipt = json.loads(raw)
        except (ValueError, UnicodeError) as exc:
            raise ValueError('invalid capture receipt') from exc
        fields = {'schema', 'arm', 'capture_id', 'source_commit', 'binary_sha256', 'selection', 'blob_sha256', 'exit_code'}
        if not isinstance(receipt, dict) or set(receipt) != fields:
            raise ValueError('invalid capture receipt fields')
        if (receipt['schema'] != 'kpf60.fixture-capture.v1' or receipt['arm'] != arm or
            receipt['source_commit'] != commit or receipt['binary_sha256'] != contract['binary']['sha256'] or
            receipt['selection'] != contract['selection'] or receipt['blob_sha256'] != value['blob'].get('sha256') or
            type(receipt['exit_code']) is not int or receipt['exit_code'] != 0 or
            not isinstance(receipt['capture_id'], str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', receipt['capture_id'])):
            raise ValueError('capture receipt does not bind declared attempt')
        capture_ids.append(receipt['capture_id'])
        pair[arm] = value['blob']
    if capture_ids[0] == capture_ids[1]: raise ValueError('capture identities must differ')
    checks = {arm: verify_pair.ORACLE.compare(blobs[arm]) for arm in ('baseline', 'observed')}
    result = {
        'schema': 'kpf60.fixture-blob-comparison.v1',
        'status': 'MATCH' if all(v[0] for v in checks.values()) and blobs['baseline'] == blobs['observed'] else 'MISMATCH',
        'arm_results': {arm: {'sha256': pair[arm]['sha256'], 'size_bytes': len(blobs[arm]),
                              'matches_fixed_oracle': checks[arm][0], 'detail': checks[arm][1]}
                        for arm in ('baseline', 'observed')},
        'arms_identical': blobs['baseline'] == blobs['observed'],
    }
    result['contract_sha256'] = expected_contract_sha
    result['scope'] = ('content and producer-declared structural bindings only; no independent source/build '
                       'authenticity, device, race-freedom or measurement warrant')
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root')
    parser.add_argument('contract')
    parser.add_argument('--expected-contract-sha256', required=True)
    args = parser.parse_args(argv)
    try:
        contract = json.loads(Path(args.contract).read_text())
        result = verify(args.root, contract, args.expected_contract_sha256)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({'status': 'INVALID', 'reason': str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0 if result['status'] == 'MATCH' else 1


if __name__ == '__main__':
    raise SystemExit(main())
