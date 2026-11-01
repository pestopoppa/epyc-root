#!/usr/bin/env python3
"""Source-bound KVU-12.6 matrix preflight; never starts a model or publishes a row."""
from __future__ import annotations
import argparse
import ast
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

BASE_SHA256 = '43e4fcad361693cddbed8f616bb0f02895e0f4fd7ab2dc01233cca74459ecdf0'
OLD = 'LS = {"8k": 8192, "32k": 32768, "64k": 65536, "128k": 131072, "t8short": 1024}'
NEW = 'LS = {"8k": 8192, "32k": 32768, "48k": 49152, "64k": 65536, "96k": 98304, "128k": 131072, "t8short": 1024}'
# Equal nominal input-token pairs; measured resident cells must still be checked.
PAIRS = ((8, '32k', 4, '64k'), (8, '48k', 4, '96k'), (8, '64k', 4, '128k'))


def patched_source(data: bytes) -> bytes:
    if hashlib.sha256(data).hexdigest() != BASE_SHA256:
        raise ValueError('driver SHA-256 does not match pinned source')
    source = data.decode('utf-8')
    if source.count(OLD) != 1:
        raise ValueError('expected exactly one original length map')
    patched = source.replace(OLD, NEW, 1)
    ast.parse(patched)
    return patched.encode('utf-8')


def driver_matrix(source: bytes, np: int, length: str) -> list[dict]:
    """Execute only hash-bound driver matrix definitions, never driver entrypoint."""
    tree = ast.parse(source.decode('utf-8'))
    selected = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'LS' for t in node.targets):
            selected.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name in ('fits', 'build_launches'):
            selected.append(node)
    if len(selected) != 3:
        raise ValueError('driver definitions missing or ambiguous')
    ns = {'FORK_BIN_DEFAULT': ''}
    exec(compile(ast.Module(body=selected, type_ignores=[]), '<hash-bound-driver-matrix>', 'exec'), ns)
    args = SimpleNamespace(lens=length, pmodes='depth', nps=str(np), kv_modes='unified', pools='524288',
                           fork_binary='', fork_min_tokens=1024, extra_argv='', anchor=False, mtp_off=False, stress=False)
    launches = ns['build_launches'](args)
    expected = f'unified_np{np}_pool524288'
    if len(launches) != 1 or launches[0]['id'] != expected or launches[0]['cells'] != [(length, 'depth')]:
        raise ValueError(f'driver failed to select exact cell np={np} L={length}')
    return launches


def plan(data: bytes) -> dict:
    source = patched_source(data)
    cells = []
    for left_np, left_l, right_np, right_l in PAIRS:
        for np, label in ((left_np, left_l), (right_np, right_l)):
            launch = driver_matrix(source, np, label)[0]
            cells.append({'np': np, 'length': label, 'context_tokens': ast.literal_eval(label[:-1]) * 1024,
                          'pool': 524288, 'driver_launch': launch['id'], 'prompt_mode': 'depth'})
    for left, right in zip(cells[::2], cells[1::2]):
        if left['np'] * left['context_tokens'] != right['np'] * right['context_tokens']:
            raise ValueError('nominal pair mismatch')
    return {'schema': 'kvu12.6.matrix-preflight.v1', 'base_driver_sha256': BASE_SHA256,
            'patched_driver_sha256': hashlib.sha256(source).hexdigest(), 'cells': cells,
            'scope': 'nominal scheduling only; native residency, resume depth and inference unverified'}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('driver', type=Path)
    args = parser.parse_args()
    print(json.dumps(plan(args.driver.read_bytes()), sort_keys=True, indent=2))


if __name__ == '__main__':
    main()
