#!/usr/bin/env python3
"""Reopen source snapshot and reference options at each build boundary."""
import hashlib
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path('/mnt/raid0/llm/tmp/kvu/kpf18-raw-build-20261105')
HASHES = {
    'instrumentation.patch': '5309fb07d49eda7ecfa373f5cb3dc51294c73eef931a4b7d03d083ef0dc5f2f1',
    'source-files.sha256': '461fc5021b990a58de11befa5a7230634fa0663145889c9cd6574becba3f81af',
    'source-file-list.txt': '7d4111398189f78d93e98bd1400521e00d56c2c5e3b803da58d4179bf56e089b',
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
    inputs, source = root/'input', pathlib.Path('/mnt/raid0/llm/tmp/kvu/kpf18-raw-logits-source-20261105')
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
    expected_content = {}
    for line in (inputs/'source-files.sha256').read_text().splitlines():
        h, sep, name = line.partition('  ./')
        if not sep or name in expected_content: raise ValueError('malformed source inventory')
        expected_content[name] = h
    if set(expected_content) != set(pin['source_stat']): raise ValueError('source hash inventory mismatch')
    for rel, expected in pin['source_stat'].items():
        p = source/rel
        if p.is_symlink() or fingerprint(p) != expected or digest(p) != expected_content[rel]:
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
