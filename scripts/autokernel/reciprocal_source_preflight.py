#!/usr/bin/env python3
"""Check an isolated candidate checkout against its preserved source manifest.

This validates source bytes and the checkout's base, not a build or runtime.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def _git(source: Path, *args: str) -> bytes:
    return subprocess.run(['git', '-C', str(source), *args], check=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout


def verify_candidate_source(source: Path, manifest: Path, expected_manifest_sha256: str) -> dict:
    raw = manifest.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != expected_manifest_sha256:
        raise ValueError('manifest SHA-256 mismatch')
    data = json.loads(raw)
    if data.get('schema') != 'autokernel-candidate-source-v1':
        raise ValueError('unexpected manifest schema')
    head = _git(source, 'rev-parse', 'HEAD').decode().strip()
    if head != data['head_commit']:
        raise ValueError('base commit mismatch')
    base_tree = _git(source, 'rev-parse', 'HEAD^{tree}').decode().strip()
    if base_tree != data['base_tree']:
        raise ValueError('base tree mismatch')
    # Never follow a checkout symlink or permit paths outside the checkout.
    root = source.resolve(strict=True)
    seen = set()
    for item in data['files']:
        path = item['path']
        parts = Path(path).parts
        if not parts or Path(path).is_absolute() or any(p in ('.', '..') for p in parts) or path in seen:
            raise ValueError(f'invalid or duplicate path: {path!r}')
        seen.add(path)
        target = root.joinpath(*parts)
        if target.is_symlink() or not target.resolve(strict=True).is_relative_to(root):
            raise ValueError(f'symlink or escaping path: {path}')
        if not target.is_file():
            raise ValueError(f'not a regular file: {path}')
        h = hashlib.sha256()
        with target.open('rb') as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b''):
                h.update(chunk)
        if h.hexdigest() != item['sha256']:
            raise ValueError(f'file SHA-256 mismatch: {path}')
        actual_mode = '100755' if os.stat(target).st_mode & 0o111 else '100644'
        if actual_mode != item['mode']:
            raise ValueError(f'file mode mismatch: {path}')
    tracked = set(os.fsdecode(p) for p in _git(source, 'ls-files', '-z').split(b'\0') if p)
    if tracked != seen:
        raise ValueError('tracked file set differs from manifest')
    if _git(source, 'ls-files', '--others', '--exclude-standard', '-z'):
        raise ValueError('untracked source files present')
    if _git(source, 'diff', '--cached', '--name-only', '-z'):
        raise ValueError('staged changes present')
    changed = set(os.fsdecode(p) for p in _git(source, 'diff', '--name-only', '-z').split(b'\0') if p)
    if changed != set(data['changed_paths']):
        raise ValueError('changed paths differ from manifest')
    return {'status': 'PASS', 'source_files': len(seen), 'head': head,
            'manifest_sha256': digest, 'scope': 'source-only; no build or execution'}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--manifest', required=True, type=Path)
    parser.add_argument('--manifest-sha256', required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(verify_candidate_source(args.source, args.manifest, args.manifest_sha256), sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError, subprocess.CalledProcessError) as exc:
        print(json.dumps({'status': 'REFUSE', 'reason': str(exc)}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
