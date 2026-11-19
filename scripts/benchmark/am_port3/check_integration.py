"""Bounded model-free checks; does not build a model runner or run inference."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

from apply_integration import PIN, HERE


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check(source, manifest, out):
    source, manifest, out = map(lambda p: Path(p).resolve(), (source, manifest, out))
    out.mkdir(exist_ok=False, parents=True)
    build = json.loads(manifest.read_text())
    if build['source_sha'] != PIN or not build['ok']:
        raise ValueError('unapproved build manifest')
    bindir = Path(build['output']) / 'bin'
    if sha(bindir / 'libggml-cpu.so') != build['sha256']['libggml-cpu.so']:
        raise ValueError('CPU library differs from its manifest')
    if subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip() != PIN:
        raise ValueError('source pin mismatch')
    patch = (HERE / 'integration.patch').read_bytes()
    if subprocess.check_output(['git', '-C', str(source), 'diff', '--', 'src']) != patch:
        raise ValueError('source changes differ from lane integration patch')
    for name in ('native_carrier.h', 'native_runtime.h'):
        if (source / 'src' / name).read_bytes() != (HERE / name).read_bytes():
            raise ValueError('installed header differs: ' + name)
    includes = ['-I' + str(source / p) for p in ('ggml/include', 'include', 'src')]
    flags = ['-std=c++17', '-Wall', '-Wextra', '-Werror', '-Wno-unused-parameter']
    # The suppression matches existing upstream virtual stub parameters.
    subprocess.run(['c++', *flags, '-fsyntax-only', *includes,
                    *[str(source / 'src' / p) for p in
                      ('llama-graph.cpp', 'llama-context.cpp', 'llama-kv-cache.cpp')]], check=True)
    runs = {}
    env = {**os.environ, 'LD_LIBRARY_PATH': str(bindir), 'OMP_NUM_THREADS': '1'}
    for name in ('test_native_carrier', 'test_native_runtime'):
        executable = out / name
        subprocess.run(['c++', *flags, '-O2', *includes, str(HERE / (name + '.cpp')),
                        '-L' + str(bindir), '-lggml-cpu', '-lggml-base', '-lggml',
                        '-Wl,-rpath,' + str(bindir), '-o', str(executable)], check=True)
        runs[name] = subprocess.check_output([str(executable)], env=env, text=True).strip()
    record = {
        'schema': 'epyc.am.integration-model-free-test.v1', 'status': 'PASS',
        'scope': 'patch syntax and native cell/graph input tests; no linked patched kernel or model/GPU verdict',
        'source_commit': PIN, 'manifest_path': str(manifest), 'manifest_sha256': sha(manifest),
        'cpu_library_sha256': sha(bindir / 'libggml-cpu.so'), 'compile_flags': flags,
        'syntax_checked': ['llama-graph.cpp', 'llama-context.cpp', 'llama-kv-cache.cpp'],
        'sha256': {p.name: sha(p) for p in (HERE / 'integration.patch', HERE / 'native_carrier.h',
                   HERE / 'native_runtime.h', HERE / 'test_native_carrier.cpp', HERE / 'test_native_runtime.cpp',
                   HERE / 'apply_integration.py', HERE / 'check_integration.py')},
        'runs': runs,
    }
    (out / 'TEST.json').write_text(json.dumps(record, indent=2) + '\n')
    return record


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(check(args.source, args.manifest, args.out), indent=2))
