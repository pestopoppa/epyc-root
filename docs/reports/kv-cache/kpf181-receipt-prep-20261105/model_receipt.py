#!/usr/bin/env python3
"""Pre-grant content receipt and grant-time stat binding for KPF-18.1.

A stat match binds a previously measured digest; it is not a fresh hash.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat

EXPECTED = {
    '/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf': 'a680f44a06920e5d689774823782006aa3acc8db95750323373b24139b67e348',
    '/mnt/raid0/llm/models/Qwen3.8-27B-DFlash2-Q8_0.gguf': '7f1c9a31a6ed40044c69f6508b50fd63b87abd8e1fb7fe4290303df549153751',
}

def identity(s):
    if not stat.S_ISREG(s.st_mode):
        raise ValueError('model is not a regular file')
    return {k: getattr(s, k) for k in ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns')}

def capture(path, expected):
    # O_NOFOLLOW avoids swapping the final pathname for a symlink during open.
    fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        before = identity(os.fstat(fd))
        h = hashlib.sha256()
        with os.fdopen(fd, 'rb', closefd=False) as f:
            for chunk in iter(lambda: f.read(4 << 20), b''):
                h.update(chunk)
        after = identity(os.fstat(fd))
        if before != after or identity(os.stat(path, follow_symlinks=False)) != before:
            raise ValueError('model changed during capture')
        if h.hexdigest() != expected:
            raise ValueError('model digest mismatch')
        return {'path': path, 'sha256': expected, 'identity': before}
    finally:
        os.close(fd)

def prepare(output):
    if os.environ.get('FILLER_ID') or os.environ.get('FILLER_SMOKE') == '1':
        raise ValueError('full model hashing is forbidden in row execution')
    data = {'schema': 'kpf181-model-receipt.v1', 'models': [capture(p, h) for p, h in EXPECTED.items()]}
    # Exclusive creation preserves the previous receipt if preparation is repeated.
    with open(output, 'x', encoding='utf-8') as f:
        json.dump(data, f, sort_keys=True, indent=2)
        f.write('\n')
        f.flush()
        os.fsync(f.fileno())

def verify(receipt, expected_receipt_sha):
    raw = Path(receipt).read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_receipt_sha:
        raise ValueError('receipt digest mismatch')
    data = json.loads(raw)
    if data.get('schema') != 'kpf181-model-receipt.v1' or len(data.get('models', [])) != len(EXPECTED):
        raise ValueError('invalid receipt')
    seen = set()
    for model in data['models']:
        path = model['path']
        if path in seen or EXPECTED.get(path) != model['sha256']:
            raise ValueError('unexpected model or digest')
        seen.add(path)
        if identity(os.stat(path, follow_symlinks=False)) != model['identity']:
            raise ValueError('model identity changed since hashing')
    if seen != EXPECTED.keys():
        raise ValueError('missing model')

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('prepare'); p.add_argument('receipt')
    v = sub.add_parser('verify'); v.add_argument('receipt'); v.add_argument('receipt_sha256')
    args = parser.parse_args()
    if args.cmd == 'prepare':
        prepare(args.receipt)
    else:
        verify(args.receipt, args.receipt_sha256)
