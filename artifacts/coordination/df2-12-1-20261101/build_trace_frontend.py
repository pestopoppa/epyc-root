#!/usr/bin/env python3
"""Build only an instrumented server frontend in NI scratch from frozen v10 objects."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import shlex
import shutil
import subprocess


ROOT = pathlib.Path(__file__).resolve().parent
SOURCE = pathlib.Path('/mnt/raid0/llm/tmp/champ2')
COMMIT = 'ffc1bac82eeca6f9099e1ccd9ba49703c460a115'
BASE = pathlib.Path('/mnt/raid0/llm/kernels/builds')
BUILD = {'cpu': 'cpu-20260921-ffc1bac82', 'gpu': 'gpu-20260921-ffc1bac82'}
ORIGINAL_SERVER_CONTEXT_SHA = 'f45a212c0a71e648fae6133ef7ae541ad8c2e00d850240a9d100339993bca902'


def sha(path):
    h = hashlib.sha256()
    with pathlib.Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def run(argv, **kwargs):
    subprocess.run(argv, check=True, **kwargs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--role', choices=('cpu', 'gpu'), required=True)
    args = ap.parse_args()
    source = SOURCE / 'tools/server/server-context.cpp'
    patched = ROOT / 'trace-patch-build/server-context.cpp'
    assert sha(source) == ORIGINAL_SERVER_CONTEXT_SHA
    current = subprocess.check_output(['git', '-C', str(SOURCE), 'rev-parse', 'HEAD'], text=True).strip()
    if current != COMMIT:
        raise RuntimeError('reference source commit changed')
    if b'DF2_NATIVE_BATCH_V1' not in patched.read_bytes() or b'DF2_NATIVE_ROUND_V1' not in patched.read_bytes():
        raise RuntimeError('trace source is not the reviewed patch')
    build = BASE / BUILD[args.role]
    bin_source = build / 'bin'
    out = ROOT / 'frontend-instrument' / args.role
    if out.exists():
        raise RuntimeError('refuse to overwrite prior frontend build')
    obj_dir = out / 'obj'
    bin_dir = out / 'bin'
    obj_dir.mkdir(parents=True)
    bin_dir.mkdir()
    compilation = json.loads((build / 'compile_commands.json').read_text())
    matches = [item for item in compilation if item['file'] == str(source)]
    if len(matches) != 1:
        raise RuntimeError('frozen compile command source identity missing')
    command = shlex.split(matches[0]['command'])
    if '-c' not in command or '-o' not in command or any(arg.startswith('-M') for arg in command):
        raise RuntimeError('compile command could emit unexpected paths')
    command[command.index('-c') + 1] = str(patched)
    object_path = obj_dir / 'server-context.cpp.o'
    command[command.index('-o') + 1] = str(object_path)
    run(command, cwd=out)
    archive_source = build / 'tools/server/libserver-context.a'
    archive = obj_dir / 'libserver-context.a'
    shutil.copy2(archive_source, archive)
    run(['ar', 'r', str(archive), str(object_path)], cwd=out)
    impl_objs = [build / 'tools/server/CMakeFiles/llama-server-impl.dir' / name
                 for name in ('server.cpp.o', 'server-http.cpp.o', 'server-models.cpp.o')]
    static = [build / 'tools/ui/libllama-ui.a', build / 'vendor/cpp-httplib/libcpp-httplib.a',
              build / 'common/libllama-common-base.a']
    shared = [bin_source / name for name in
              ('libllama-common.so.0.0.10303', 'libmtmd.so.0.0.10303',
               'libllama.so.0.0.10303', 'libggml.so.0.16.0', 'libggml-cpu.so.0.16.0')]
    if args.role == 'gpu':
        shared.append(bin_source / 'libggml-hip.so.0.16.0')
    shared.append(bin_source / 'libggml-base.so.0.16.0')
    frozen_inputs = [source, archive_source, *impl_objs, *static, *shared,
                     bin_source / 'llama-server', bin_source / 'test-recurrent-state-rollback']
    before = {str(path): {'sha256': sha(path), 'mtime_ns': path.stat().st_mtime_ns} for path in frozen_inputs}
    output_dso = bin_dir / 'libllama-server-impl.so'
    link = ['/usr/bin/c++', '-fPIC', '-O3', '-DNDEBUG', '-shared',
            '-Wl,-soname,libllama-server-impl.so', '-o', str(output_dso),
            *map(str, impl_objs), '-Wl,-rpath,$ORIGIN' + (':/opt/rocm/lib' if args.role == 'gpu' else ''),
            str(archive), str(static[0]), str(static[1]), str(shared[0]), str(static[2]),
            *map(str, shared[1:])]
    if args.role == 'gpu':
        link.append('-Wl,-rpath-link,/opt/rocm/lib')
    run(link, cwd=out)
    for name in ('llama-server', 'test-recurrent-state-rollback'):
        shutil.copy2(bin_source / name, bin_dir / name)
    for item in bin_source.glob('*.so*'):
        dest = bin_dir / item.name
        if dest.exists() or dest.is_symlink():
            continue
        dest.symlink_to(item.resolve(strict=True))
    after = {str(path): {'sha256': sha(path), 'mtime_ns': path.stat().st_mtime_ns} for path in frozen_inputs}
    if before != after:
        raise RuntimeError('immutable production input changed during frontend link')
    if b'DF2_NATIVE_ROUND_V1' not in subprocess.check_output(['strings', str(output_dso)]):
        raise RuntimeError('instrumented frontend DSO lacks native round marker')
    record = {'schema': 'epyc.df2_12_1.instrumented_frontend.v1', 'role': args.role,
              'scope': 'INSTRUMENTED_PRODUCTION_CODE_FRONTEND_NOT_LIVE_FROZEN_BINARY',
              'source_commit': COMMIT, 'source_context_sha256': sha(source),
              'patched_context_sha256': sha(patched),
              'trace_patch_sha256': sha(ROOT / 'DF2-NATIVE-TRACE-v3.patch'),
              'frozen_inputs': before, 'compile_argv': command, 'link_argv': link,
              'output_binary': str(bin_dir / 'llama-server'), 'output_test': str(bin_dir / 'test-recurrent-state-rollback'),
              'output_dso': str(output_dso),
              'output_hashes': {p.name: sha(p) for p in (bin_dir / 'llama-server',
                  bin_dir / 'test-recurrent-state-rollback', output_dso)},
              'utc': dt.datetime.now(dt.timezone.utc).isoformat()}
    (out / 'BUILD-RECEIPT.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps({'role': args.role, 'output_dso': str(output_dso),
                      'dso_sha256': sha(output_dso), 'source_commit': COMMIT}))


if __name__ == '__main__':
    main()
