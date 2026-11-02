#!/usr/bin/env python3
"""Check a build custody packet's contents; does not attest who built them.

Never runs a build or hashes model weights. The manifest's build provenance is a
self-report; a protected contemporaneous capture is still needed to bind outputs
and source, and runtime process mappings must be checked during an admitted run.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

HEX = re.compile(r'^[0-9a-f]{64}$')
COMMIT = re.compile(r'^[0-9a-f]{40}$')
REQUIRED = {'source_archive', 'cmake_cache', 'compile_commands', 'build_log',
            'server', 'libllama', 'libggml', 'libggml_cpu', 'toolchain_record'}

def _hash(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1048576), b''):
            h.update(chunk)
    return h.hexdigest()

def verify(packet, source_repo):
    manifest_path = Path(packet).resolve(strict=True)
    root = manifest_path.parent
    data = json.loads(manifest_path.read_text())
    if data.get('schema') != 'jetlong-build-custody-v1':
        raise ValueError('unsupported schema')
    if not COMMIT.fullmatch(data.get('source_commit', '')) or not COMMIT.fullmatch(data.get('source_tree', '')):
        raise ValueError('invalid source identity')
    if any(type(data.get(k)) is not int or data[k] != 0 for k in ('configure_rc', 'build_rc')):
        raise ValueError('configure or build failed')
    if data.get('network_access') != 'disabled':
        raise ValueError('build network isolation not recorded')
    entries = data.get('files')
    if not isinstance(entries, dict) or not REQUIRED.issubset(entries):
        raise ValueError('missing required custody files')
    for key, entry in entries.items():
        if not isinstance(entry, dict) or not HEX.fullmatch(entry.get('sha256', '')):
            raise ValueError(f'invalid digest for {key}')
        rel = Path(entry.get('path', ''))
        if rel.is_absolute() or '..' in rel.parts:
            raise ValueError(f'unsafe path for {key}')
        path = (root / rel).resolve(strict=True)
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError(f'path escapes packet for {key}')
        if _hash(path) != entry['sha256']:
            raise ValueError(f'digest mismatch for {key}')
    repo = str(Path(source_repo).resolve(strict=True))
    commit = data['source_commit']
    tree = subprocess.run(['git', '-C', repo, 'rev-parse', '--verify', f'{commit}^{{tree}}'],
                          check=True, capture_output=True, text=True).stdout.strip()
    if tree != data['source_tree']:
        raise ValueError('source tree mismatch')
    tree_entries = subprocess.run(['git', '-C', repo, 'ls-tree', '-r', commit],
                                  check=True, capture_output=True, text=True).stdout
    if any(line.startswith('160000 ') for line in tree_entries.splitlines()):
        raise ValueError('gitlinks require separately sealed dependency custody')
    # Compare byte-for-byte digest of canonical git archive to custody packet.
    proc = subprocess.Popen(['git', '-C', repo, 'archive', '--format=tar', commit], stdout=subprocess.PIPE)
    h = hashlib.sha256()
    for chunk in iter(lambda: proc.stdout.read(1048576), b''):
        h.update(chunk)
    proc.stdout.close()
    if proc.wait() != 0 or h.hexdigest() != entries['source_archive']['sha256']:
        raise ValueError('archive does not match source commit')
    return {'checks': 'pass', 'source_commit': commit, 'source_tree': tree,
            'limitation': 'file and archive checks only; source-to-build custody and runtime linkage are not established'}

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('manifest'); ap.add_argument('--source-repo', required=True)
    args = ap.parse_args()
    try:
        print(json.dumps(verify(args.manifest, args.source_repo), sort_keys=True))
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        ap.exit(1, f'REFUSE: {exc}\n')

if __name__ == '__main__':
    main()
