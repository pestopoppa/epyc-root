#!/usr/bin/env python3
"""Build a versioned corrected rollback test beside the pinned D2 scratch frontend."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import shutil
import subprocess

from owner_pregrant import ROOT, sha

SOURCE = pathlib.Path('/mnt/raid0/llm/llama.cpp')
COMMIT = 'ffc1bac82eeca6f9099e1ccd9ba49703c460a115'
ORIGINAL_TEST_SHA = 'b200438e63d75b051782b4f2face659d1fb62c4b7da45d2266e2096abe22d3e3'
CORRECTED_TEST_SHA = 'e0a4b418b8d7d4f7e59cbc3d7aa8941baf2d0f794bbbe18b71fa7166ee72a9db'
PATCH_SHA = 'e55c0418c0468948450af20440364a4c9f4e51e00f5bc04dac8aec010e6562ed'
BUILD = {
    'cpu': pathlib.Path('/mnt/raid0/llm/kernels/builds/cpu-20260921-ffc1bac82'),
    'gpu': pathlib.Path('/mnt/raid0/llm/kernels/builds/gpu-20260921-ffc1bac82'),
}


def run(argv):
    subprocess.run(argv, check=True, cwd=ROOT, stdout=subprocess.PIPE,
                   stderr=subprocess.STDOUT, text=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('role', choices=('cpu', 'gpu'))
    args = ap.parse_args()
    old = ROOT / 'frontend-instrument' / args.role
    new = ROOT / 'frontend-instrument-corrected' / args.role
    if new.exists():
        raise RuntimeError('refuse to overwrite versioned corrected image')
    if subprocess.check_output(['git', '-C', str(SOURCE), 'rev-parse', 'HEAD'], text=True).strip() != COMMIT:
        raise RuntimeError('frozen source commit drifted')
    original = SOURCE / 'tests/test-recurrent-state-rollback.cpp'
    corrected = ROOT / 'dirty-diagnostic/test-oracle-fix-minimal.cpp'
    patch = ROOT / 'dirty-diagnostic/TEST-ORACLE-FIX.patch'
    if (sha(original), sha(corrected), sha(patch)) != (ORIGINAL_TEST_SHA, CORRECTED_TEST_SHA, PATCH_SHA):
        raise RuntimeError('corrected test source or patch changed')
    build = BUILD[args.role]
    frozen_bin = build / 'bin'
    old_bin = old / 'bin'
    old_receipt = old / 'BUILD-RECEIPT.json'
    prior = json.loads(old_receipt.read_text())
    if (prior['source_commit'] != COMMIT or prior['role'] != args.role or
        sha(old_bin / 'libllama-server-impl.so') != prior['output_hashes']['libllama-server-impl.so']):
        raise RuntimeError('prior D2 frontend image changed')
    get_model_obj = build / 'tests/CMakeFiles/test-recurrent-state-rollback.dir/get-model.cpp.o'
    static_common = build / 'common/libllama-common-base.a'
    shared_names = ['libllama-common.so.0.0.10303', 'libllama.so.0.0.10303',
                    'libggml.so.0.16.0', 'libggml-cpu.so.0.16.0']
    if args.role == 'gpu':
        shared_names.append('libggml-hip.so.0.16.0')
    shared_names.append('libggml-base.so.0.16.0')
    frozen_inputs = [get_model_obj, static_common, *[frozen_bin / name for name in shared_names],
                     frozen_bin / 'llama-server', old_bin / 'libllama-server-impl.so']
    before = {str(p): sha(p) for p in frozen_inputs}
    obj = new / 'obj'
    bin_dir = new / 'bin'
    obj.mkdir(parents=True)
    bin_dir.mkdir()
    shutil.copy2(old_bin / 'llama-server', bin_dir / 'llama-server')
    shutil.copy2(old_bin / 'libllama-server-impl.so', bin_dir / 'libllama-server-impl.so')
    for item in old_bin.glob('*.so*'):
        dest = bin_dir / item.name
        if dest.exists() or dest.is_symlink():
            continue
        if not item.is_symlink():
            raise RuntimeError(f'unexpected regular prior library: {item}')
        target = item.resolve(strict=True)
        if target.parent != frozen_bin:
            raise RuntimeError(f'prior library points outside exact frozen image: {item}')
        dest.symlink_to(target)
    macros = ['-DGGML_BACKEND_SHARED', '-DGGML_SHARED', '-DGGML_USE_CPU', '-DLLAMA_SHARED']
    if args.role == 'gpu':
        macros += ['-DGGML_USE_CUDA', '-DGGML_USE_HIP']
    compile_argv = ['/usr/bin/c++', '-O3', '-DNDEBUG', *macros,
                    '-I' + str(SOURCE / 'include'), '-I' + str(SOURCE / 'ggml/include'),
                    '-I' + str(SOURCE / 'common'), '-I' + str(SOURCE / 'vendor'),
                    '-c', str(corrected), '-o', str(obj / 'test-oracle-fix-minimal.o')]
    run(compile_argv)
    link_argv = ['/usr/bin/c++', '-O3', '-DNDEBUG', str(obj / 'test-oracle-fix-minimal.o'),
                 str(get_model_obj), '-o', str(bin_dir / 'test-recurrent-state-rollback'),
                 '-Wl,-rpath,$ORIGIN' + (':/opt/rocm/lib' if args.role == 'gpu' else ''),
                 *[str(frozen_bin / name) for name in shared_names], str(static_common)]
    if args.role == 'gpu':
        link_argv.append('-Wl,-rpath-link,/opt/rocm/lib')
    run(link_argv)
    after = {str(p): sha(p) for p in frozen_inputs}
    if before != after:
        raise RuntimeError('immutable frozen/prior instrument input changed')
    test = bin_dir / 'test-recurrent-state-rollback'
    record = {'schema': 'epyc.df2_12_1.corrected_test_image.v1',
              'scope': 'D2_SCRATCH_INSTRUMENTED_FRONTEND_CORRECTED_TEST_NOT_LIVE_FROZEN_BINARY',
              'role': args.role, 'base_source_commit': COMMIT,
              'original_test_source': str(original), 'original_test_source_sha256': ORIGINAL_TEST_SHA,
              'corrected_test_source': str(corrected), 'corrected_test_source_sha256': CORRECTED_TEST_SHA,
              'test_patch': str(patch), 'test_patch_sha256': PATCH_SHA,
              'prior_frontend_receipt_sha256': sha(old_receipt),
              'prior_frontend_dso_sha256': before[str(old_bin / 'libllama-server-impl.so')],
              'frozen_inputs_sha256': before, 'compile_argv': compile_argv, 'link_argv': link_argv,
              'server_binary': str(bin_dir / 'llama-server'),
              'server_binary_sha256': sha(bin_dir / 'llama-server'),
              'server_impl_sha256': sha(bin_dir / 'libllama-server-impl.so'),
              'test_binary': str(test), 'test_binary_sha256': sha(test),
              'utc': dt.datetime.now(dt.timezone.utc).isoformat()}
    (new / 'CORRECTED-BUILD-RECEIPT.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps({'role': args.role, 'test_binary': str(test),
                      'test_binary_sha256': record['test_binary_sha256'],
                      'receipt_sha256': sha(new / 'CORRECTED-BUILD-RECEIPT.json')}))


if __name__ == '__main__':
    main()
