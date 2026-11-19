#!/usr/bin/env python3
"""Bind ggml DSOs to a build-completion receipt and verify process mappings.

A receipt lacking DSO digests cannot be upgraded retrospectively: create a new
build receipt that records the files while the build is completed instead.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re

REQUIRED = ('libggml.so', 'libggml-base.so', 'libggml-cpu.so', 'libggml-hip.so')
SOURCE = '6ec877068936588b6d63dbba5842bbd540b92031'
PARENT = '84d0a31603d495377dee24e1159bbbf02f1e2f21'
HEX = re.compile(r'^[0-9a-f]{64}$')


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def create_manifest(build_dir, receipt_path):
    root = Path(build_dir).resolve(strict=True)
    receipt_path = Path(receipt_path).resolve(strict=True)
    receipt = json.loads(receipt_path.read_text())
    if receipt.get('source_commit') != SOURCE or receipt.get('parent_source') != PARENT:
        raise ValueError('unapproved source identity')
    if receipt.get('status') != 'built' or receipt.get('schema') != 'epyc.kpf174d.build.v1':
        raise ValueError('not an accepted build receipt')
    files = receipt.get('files')
    if not isinstance(files, dict):
        raise ValueError('build receipt does not record files')
    libs = {}
    for name in REQUIRED:
        resolved = (root / name).resolve(strict=True)
        if resolved.parent != root or not resolved.is_file():
            raise ValueError('library escapes build bin: ' + name)
        actual = digest(resolved)
        if files.get(str(resolved)) != actual:
            raise ValueError('library not attested in build-completion receipt: ' + name)
        libs[name] = {'filename': resolved.name, 'sha256': actual}
    if len({entry['filename'] for entry in libs.values()}) != len(REQUIRED):
        raise ValueError('distinct ggml libraries required')
    return {'schema': 'kpf174d.ggml-custody.v1', 'source_commit': SOURCE,
            'parent_source': PARENT, 'build_receipt_sha256': digest(receipt_path),
            'libraries': libs}


def verify_maps(manifest, maps_text, bin_dir):
    if manifest.get('schema') != 'kpf174d.ggml-custody.v1' or manifest.get('source_commit') != SOURCE or manifest.get('parent_source') != PARENT:
        raise ValueError('invalid manifest identity')
    if not HEX.fullmatch(manifest.get('build_receipt_sha256', '')):
        raise ValueError('invalid receipt digest')
    libs = manifest.get('libraries')
    if not isinstance(libs, dict) or set(libs) != set(REQUIRED):
        raise ValueError('incomplete library manifest')
    root = Path(bin_dir).resolve(strict=True)
    expected = {}
    for name, entry in libs.items():
        filename, sha = entry.get('filename'), entry.get('sha256')
        if not isinstance(filename, str) or Path(filename).name != filename or not isinstance(sha, str) or not HEX.fullmatch(sha):
            raise ValueError('invalid library identity')
        p = (root / name).resolve(strict=True)
        if p.parent != root or p.name != filename or digest(p) != sha:
            raise ValueError('library content differs from build receipt: ' + name)
        st = p.stat()
        expected[str(p)] = (os.major(st.st_dev), os.minor(st.st_dev), st.st_ino)
    seen = set()
    for line in maps_text.splitlines():
        parts = line.split(None, 5)
        if len(parts) < 6 or not re.search(r'/libggml(?:[-.]|\.so)', parts[5]):
            continue
        name = parts[5]
        if name.endswith(' (deleted)'):
            raise ValueError('mapped deleted ggml library')
        try:
            major, minor = (int(x, 16) for x in parts[3].split(':'))
            inode = int(parts[4])
            path = str(Path(name).resolve(strict=True))
        except (OSError, ValueError) as exc:
            raise ValueError('invalid ggml mapping') from exc
        if expected.get(path) != (major, minor, inode):
            raise ValueError('unexpected or replaced mapped ggml library: ' + name)
        seen.add(path)
    if seen != set(expected):
        raise ValueError('not all attested ggml libraries are mapped')
    return {'status': 'PASS', 'mapped': sorted(seen)}


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='action', required=True)
    a = sub.add_parser('seal'); a.add_argument('--build-dir', required=True); a.add_argument('--build-receipt', required=True); a.add_argument('--output', required=True)
    a = sub.add_parser('verify'); a.add_argument('--bin-dir', required=True); a.add_argument('--manifest', required=True); a.add_argument('--manifest-sha256', required=True); a.add_argument('--pid', type=int, required=True)
    args = p.parse_args()
    if args.action == 'seal':
        result = create_manifest(args.build_dir, args.build_receipt)
        Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    else:
        if not HEX.fullmatch(args.manifest_sha256) or digest(args.manifest) != args.manifest_sha256:
            raise ValueError('manifest pin mismatch')
        result = verify_maps(json.loads(Path(args.manifest).read_text()), Path(f'/proc/{args.pid}/maps').read_text(), args.bin_dir)
        print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
