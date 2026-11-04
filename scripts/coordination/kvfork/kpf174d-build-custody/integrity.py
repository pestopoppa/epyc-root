#!/usr/bin/env python3
"""Reopen source snapshot and reference options at each build boundary."""
import hashlib
import pathlib
import subprocess
import sys

ROOT = pathlib.Path('/mnt/raid0/llm/tmp/kvfork/kpf174d-build')
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
    inputs, source = root/'input', root/'v3/source'
    for name, expected in HASHES.items():
        if digest(inputs/name) != expected: raise ValueError('input digest mismatch: '+name)
    entries = list(source.rglob('*'))
    if any(p.is_symlink() for p in entries): raise ValueError('source symlink refused')
    inventory = ''.join('./'+str(p.relative_to(source))+'\n' for p in sorted((p for p in entries if p.is_file()),key=lambda p: str(p.relative_to(source)).encode()))
    if inventory != (inputs/'source-file-list.txt').read_text(): raise ValueError('source inventory mismatch')
    subprocess.run(['sha256sum','--check','--quiet',str(inputs/'source-files.sha256')], cwd=source, check=True, stdout=subprocess.DEVNULL)
    reference = cache(inputs/'reference-cache.txt')
    actual = cache(actual_cache) if actual_cache is not None else reference
    if actual != reference: raise ValueError('configured options do not match reference')
    return {'input_sha256':dict(HASHES), 'source_snapshot':str(source), 'configured_options':actual}

if __name__ == '__main__':
    try:
        verify(actual_cache=sys.argv[1] if len(sys.argv)>1 else None)
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        raise SystemExit('integrity refused: '+str(exc))
