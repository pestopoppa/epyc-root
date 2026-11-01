#!/usr/bin/env python3
"""Read-only FA-8 source identity preflight; does not build, schedule or measure."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ARMS = {
    'A': {
        'commit': '90c12df4247e417053ffc59e2188294826d04ca2',
        'tree': '6c1bb5c21184fd15be079469bb77dae4c734a16e',
        'path': 'ggml/src/ggml-cuda/fattn-wmma-f16.cu',
        'sha256': 'e6edc0c1f71241b1c91bfcb017b0843ea88ec8cf07312d17cc476af27d7d9b58',
        'route': 'historical ROCWMMA ON; runtime route not proven',
        'anchors': ('threadIdx.y % VKQ_ratio', 'KQ_f16 + j0*(kqar*kqs_padded) + k', 'KQ_rowsum_add'),
    },
    'C': {
        'commit': '5026470c6c5882042aa543ae54fe5410357b41ae',
        'tree': '130bb58bdca0c6a365ff0a26e779d343dd76aa44',
        'path': 'ggml/src/ggml-cuda/fattn-mma-f16.cuh',
        'sha256': 'ca71142306b427fead04a1e708daad53f43ab3cd426587c23dee2be316855af1',
        'route': 'historical ROCWMMA OFF; runtime route not proven',
        'anchors': ('KQ_rowsum_add', '__shfl_xor_sync', 'VKQ_C'),
    },
}


def inspect(git, spec):
    commit = spec['commit']
    get = lambda *args: subprocess.check_output(['git', '-C', str(git), *args], stderr=subprocess.PIPE)
    full = get('rev-parse', '--verify', commit + '^{commit}').decode().strip()
    tree = get('rev-parse', '--verify', commit + '^{tree}').decode().strip()
    if full != commit or tree != spec['tree']:
        raise ValueError('commit or tree mismatch')
    raw = get('show', commit + ':' + spec['path'])
    if hashlib.sha256(raw).hexdigest() != spec['sha256']:
        raise ValueError('source object hash mismatch')
    source = raw.decode('utf-8')
    if any(anchor not in source for anchor in spec['anchors']):
        raise ValueError('expected source anchor missing')
    return {key: spec[key] for key in ('commit', 'tree', 'path', 'sha256', 'route')}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repo', type=Path, required=True, help='read-only Git object database with both commits')
    args = ap.parse_args()
    try:
        results = {arm: inspect(args.repo, spec) for arm, spec in ARMS.items()}
    except (subprocess.CalledProcessError, OSError, UnicodeError, ValueError) as exc:
        ap.exit(1, f'FA-8 source preflight refused: {exc}\n')
    print(json.dumps({'schema': 'v11-fa8-source-preflight.v1', 'arms': results,
                      'scope': 'Git source objects only; no build, binary, routing, or measurement proof'}, indent=2))


if __name__ == '__main__':
    main()
