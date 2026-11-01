#!/usr/bin/env python3
"""Split image linkage: own frontend DSO, immutable exact production kernel DSOs."""
import json
import os
import pathlib
import re
import subprocess
import sys


VERIFIER = pathlib.Path('/mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh')
PRODUCTION = pathlib.Path('/mnt/raid0/llm/kernels/production')


def main():
    binary = pathlib.Path(sys.argv[1]).absolute()
    instrument_dir = pathlib.Path(sys.argv[2]).absolute()
    role = instrument_dir.parent.name
    if role not in ('cpu', 'gpu') or binary.parent != instrument_dir:
        raise RuntimeError('instrumented binary/role path mismatch')
    production_dir = (PRODUCTION / role).resolve(strict=True)
    frozen = production_dir / 'llama-server'
    official = subprocess.run([str(VERIFIER), str(frozen), str(production_dir)],
             env={**os.environ, 'LD_LIBRARY_PATH': str(production_dir) + (':/opt/rocm/lib' if role == 'gpu' else '')},
             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if official.returncode:
        raise RuntimeError(f'official frozen-kernel linkage failed: {official.stdout[-1000:]}')
    result = subprocess.run(['ldd', str(binary)],
             env={**os.environ, 'LD_LIBRARY_PATH': str(instrument_dir) + (':/opt/rocm/lib' if role == 'gpu' else '')},
             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if result.returncode or 'not found' in result.stdout:
        raise RuntimeError('instrumented loader unresolved: ' + result.stdout[-1200:])
    paths = {}
    for line in result.stdout.splitlines():
        match = re.match(r'\s*(lib(?:llama|ggml|mtmd)[^\s]*)\s+=>\s+(\S+)', line)
        if match:
            paths[match.group(1)] = pathlib.Path(match.group(2)).resolve(strict=True)
    if not any(key.startswith('libllama-server-impl.so') for key in paths):
        raise RuntimeError('instrumented server implementation absent from dynamic link')
    for name, path in paths.items():
        wanted = instrument_dir / 'libllama-server-impl.so' if name.startswith('libllama-server-impl.so') else production_dir
        if (path != wanted if name.startswith('libllama-server-impl.so') else path.parent != wanted):
            raise RuntimeError(f'{name} linked wrong image: {path}')
    for prefix in ('libllama.so', 'libggml.so', 'libggml-base.so', 'libggml-cpu.so', 'libmtmd.so', 'libllama-common.so'):
        if not any(name.startswith(prefix) for name in paths):
            raise RuntimeError(f'expected kernel DSO missing: {prefix}')
    hip = instrument_dir / 'libggml-hip.so'
    if role == 'gpu' and (not hip.is_symlink() or hip.resolve(strict=True).parent != production_dir):
        raise RuntimeError('GPU HIP plugin symlink is not exact production store')
    print(json.dumps({'pass': True, 'scope': 'instrumented frontend + exact frozen production kernel DSOs',
                      'official_frozen_verifier_rc': official.returncode,
                      'dynamic_link_paths': {key: str(value) for key, value in paths.items()},
                      'hip_plugin_residency': 'REQUIRES_NATIVE_KFD_VRAM_AND_PROC_MAPS' if role == 'gpu' else 'N/A'}, sort_keys=True))


if __name__ == '__main__':
    main()
