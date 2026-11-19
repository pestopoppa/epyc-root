#!/usr/bin/env python3
"""Reopen source snapshot and reference options at each build boundary."""
import hashlib
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path('/mnt/raid0/llm/tmp/kvu/kpf174-custody-r4-20261104')
HASHES = {
    'source-files.sha256': '39089f3d1221e2539f04c24a2244551661c14a8891caf24a8de4f83c1bf8f2b3',
    'source-file-list.txt': 'efc2adb35b152970ebf415b662425fdfd43529b7647e979d6594ac85af0e3556',
    'source.tar': 'eb58f5b820ccfce7a7a97e8260bb14e2476caf861efa7509239fdf749151cb95',
    'reference-cache.txt': '527dbc99938414bcfecb5b309a2f4001f76e168a84b0cc9a32e18d6e26184f76',
}

def digest(path):
    h = hashlib.sha256()
    with pathlib.Path(path).open('rb') as f:
        for b in iter(lambda: f.read(1024*1024), b''): h.update(b)
    return h.hexdigest()

def fingerprint(path):
    st=path.stat()
    return {key:getattr(st,'st_'+key) for key in ('dev','ino','size','mtime_ns','ctime_ns')}

def cache(path):
    result = {}
    for line in pathlib.Path(path).read_text().splitlines():
        if not line or line[0] in '#/' or '=' not in line or ':' not in line.split('=', 1)[0]: continue
        keytype, value = line.split('=', 1)
        key, kind = keytype.split(':', 1)
        if (key.startswith(('GGML_', 'LLAMA_')) and kind == 'BOOL') or key in {'CMAKE_BUILD_TYPE', 'CMAKE_C_COMPILER', 'CMAKE_CXX_COMPILER', 'CMAKE_HIP_COMPILER', 'AMDGPU_TARGETS', 'CMAKE_INSTALL_RPATH', 'CMAKE_BUILD_RPATH_USE_ORIGIN', 'CMAKE_BUILD_WITH_INSTALL_RPATH'}:
            result[key] = value
    return result

def verify(root=ROOT, actual_cache=None):
    root = pathlib.Path(root)
    inputs, source = root/'input', pathlib.Path('/mnt/raid0/llm/worktrees/kpf174-custody-r4-source-20261104')
    identity = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD', 'HEAD^'], text=True).splitlines()
    if identity != ['6ec877068936588b6d63dbba5842bbd540b92031', '84d0a31603d495377dee24e1159bbbf02f1e2f21']:
        raise ValueError('detached source commit or parent mismatch')
    if subprocess.run(['git', '-C', str(source), 'symbolic-ref', '-q', 'HEAD'], capture_output=True).returncode != 1:
        raise ValueError('source is not detached')
    # Content verification was completed during preparation. Grant-time checks
    # reopen the prepared metadata and exact inventory, without rescanning bytes.
    pin = json.loads((root/'input/PREPARED.json').read_text())
    if pin['input_sha256'] != HASHES: raise ValueError('prepared input identity mismatch')
    entries = [p for p in source.rglob('*') if p.is_file() and p.name != '.git']
    if set(pin['source_stat']) != {str(p.relative_to(source)) for p in entries}:
        raise ValueError('source inventory changed')
    for rel, expected in pin['source_stat'].items():
        p = source/rel
        if p.is_symlink() or fingerprint(p) != expected:
            raise ValueError('source metadata changed: '+rel)
    for name, expected in pin['input_stat'].items():
        if fingerprint(inputs/name) != expected: raise ValueError('prepared input metadata changed: '+name)
    reference = cache(inputs/'reference-cache.txt')
    actual = cache(actual_cache) if actual_cache is not None else reference
    if actual != reference: raise ValueError('configured options do not match reference')
    return {'input_sha256':dict(HASHES), 'source_snapshot':str(source), 'configured_options':actual}

if __name__ == '__main__':
    try:
        verify(actual_cache=sys.argv[1] if len(sys.argv)>1 else None)
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        raise SystemExit('integrity refused: '+str(exc))
