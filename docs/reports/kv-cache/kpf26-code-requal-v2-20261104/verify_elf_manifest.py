#!/usr/bin/env python3
"""Validate complete retained-bin inventory and the pinned native loader closure."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

PROJECT_LIBS = ('libggml', 'libllama', 'libmtmd')


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def read_manifest(path):
    result = {}
    for line in Path(path).read_text().splitlines():
        sha, name = line.split(None, 1)
        name = name.lstrip('*')
        if len(sha) != 64 or any(c not in '0123456789abcdef' for c in sha) or Path(name).name != name or name in result:
            raise ValueError('invalid or duplicate bin manifest entry')
        result[name] = sha
    return result


def loader_paths(text):
    rows = {}
    for line in text.splitlines():
        parts = line.strip().split()
        if not parts:
            continue
        if len(parts) > 2 and parts[1] == '=>':
            if parts[2] == 'not':
                raise ValueError('unresolved loader dependency')
            name, path = parts[0], parts[2]
        elif parts[0].startswith('/'):
            name, path = Path(parts[0]).name, parts[0]
        else:
            continue  # linux-vdso has no on-disk ELF identity.
        if not path.startswith('/') or name in rows:
            raise ValueError('ambiguous loader dependency')
        rows[name] = str(Path(path).resolve(strict=True))
    if not rows:
        raise ValueError('empty native loader closure')
    return rows


def native_closure(bin_dir):
    env = dict(os.environ, LD_LIBRARY_PATH=str(bin_dir))
    p = subprocess.run(['ldd', str(bin_dir / 'llama-server')], env=env, capture_output=True, text=True, check=True)
    return loader_paths(p.stdout)


def verify(bin_dir, manifest, baseline, closure=None):
    bin_dir = Path(bin_dir).resolve(strict=True)
    expected = read_manifest(manifest)
    actual = {p.name for p in bin_dir.iterdir() if p.is_file()}
    if actual != set(expected):
        raise ValueError(f'bin inventory mismatch: uncovered={sorted(actual-set(expected))}, missing={sorted(set(expected)-actual)}')
    for name, sha in expected.items():
        if digest(bin_dir / name) != sha:
            raise ValueError(f'bin digest mismatch: {name}')
    closure = native_closure(bin_dir) if closure is None else closure
    if set(closure) != set(baseline):
        raise ValueError('loader closure membership changed')
    for name, path in closure.items():
        resolved = Path(path).resolve(strict=True)
        if name.startswith(PROJECT_LIBS):
            if resolved.parent != bin_dir or name not in expected:
                raise ValueError(f'project DSO outside manifest/bin: {name}')
        if str(resolved) != baseline[name]['path'] or digest(resolved) != baseline[name]['sha256']:
            raise ValueError(f'loader identity changed: {name}')
    return {'bin_files': len(expected), 'loader_files': len(closure),
            'own_dsos': sorted(n for n in closure if n.startswith(PROJECT_LIBS))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--bin', type=Path, required=True)
    ap.add_argument('--manifest', type=Path, required=True)
    ap.add_argument('--closure', type=Path, required=True)
    a = ap.parse_args()
    result = verify(a.bin, a.manifest, json.loads(a.closure.read_text()))
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__': main()
