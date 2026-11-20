"""Fresh experimental builds only; invoke build inside an admitted compute row.

Verification hashes source/tooling and output bytes; it never loads a model.
A manifest is a local build receipt, not an independently trusted attestation.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

from apply_integration import HERE, PIN, install

OWNED = ('integration.patch', 'native_carrier.h', 'native_runtime.h',
         'native_capture.h', 'native_bundle.h', 'driver.cpp', 'control.cpp',
         'apply_integration.py', 'build.py', 'controls.py', 'run_driver.py',
         'convert.py', 'fit.py', 'capture.py', 'compact_check.py',
         'pipeline.py', 'residency.py')
ENV_KEYS = ('PATH', 'CC', 'CXX', 'CFLAGS', 'CXXFLAGS', 'CPPFLAGS', 'LDFLAGS',
            'ROCM_PATH', 'HIP_PATH', 'HIPCXX', 'CMAKE_PREFIX_PATH', 'LD_LIBRARY_PATH')


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def git(source, *args):
    return subprocess.check_output(['git', '-C', str(source), *args])


def source_state(source, variant):
    source = Path(source).resolve(strict=True)
    if (not (source / '.git').is_file() or git(source, 'branch', '--show-current').strip()
            or git(source, 'rev-parse', 'HEAD').decode().strip() != PIN):
        raise ValueError('pinned detached experimental worktree required')
    if git(source, 'diff', '--cached').strip():
        raise ValueError('staged source changes refused')
    diff = git(source, 'diff', '--binary', 'HEAD')
    if diff != ((HERE / 'integration.patch').read_bytes() if variant == 'patched' else b''):
        raise ValueError('unexpected tracked source changes')
    others = git(source, 'ls-files', '--others', '--exclude-standard', '-z')
    ignored = git(source, 'ls-files', '--others', '--ignored', '--exclude-standard', '-z')
    expected = {'src/native_carrier.h', 'src/native_runtime.h'} if variant == 'patched' else set()
    if {p.decode() for p in others.split(b'\0') if p} != expected or ignored:
        raise ValueError('unexpected untracked/ignored source files')
    for name in expected:
        if (source / name).is_symlink() or sha(source / name) != sha(HERE / Path(name).name):
            raise ValueError('installed header mismatch')
    return dict(commit=PIN, tree=git(source, 'rev-parse', 'HEAD^{tree}').decode().strip(),
                diff_sha256=hashlib.sha256(diff).hexdigest())


def artifacts(output, variant, backend):
    output = Path(output).resolve(strict=True)
    bindir = output / 'build' / 'bin'
    paths = {p for pattern in ('libllama*.so*', 'libggml*.so*')
             for p in bindir.glob(pattern)}
    required = ['am-control', 'libllama.so', 'libggml.so', 'libggml-base.so', 'libggml-cpu.so']
    if variant == 'patched':
        required.append('am-driver')
    if backend == 'hip':
        required.append('libggml-hip.so')
    for name in required:
        paths.add(bindir / name)
    if any(p.resolve(strict=True).parent != bindir or not p.is_file() or p.stat().st_size == 0 for p in paths):
        raise ValueError('nonempty self-contained build artifacts required')
    paths.update((output / 'build' / 'CMakeCache.txt', output / 'CMakeLists.txt'))
    return {str(p.relative_to(output)): sha(p) for p in sorted(paths)}


def verify(manifest):
    manifest = Path(manifest).resolve(strict=True)
    m = json.loads(manifest.read_text())
    if (m.get('schema') != 'epyc.am.full-build.v1' or m.get('variant') not in ('baseline', 'patched')
            or m.get('backend') not in ('cpu', 'hip') or m.get('status') != 'BUILT'):
        raise ValueError('complete full-build manifest required')
    if m['tooling_sha256'] != {name: sha(HERE / name) for name in OWNED}:
        raise ValueError('build tooling changed')
    if m['source_state'] != source_state(m['source'], m['variant']):
        raise ValueError('build source changed')
    if m['artifacts_sha256'] != artifacts(manifest.parent, m['variant'], m['backend']):
        raise ValueError('build artifacts changed')
    if m['logs_sha256'] != {f'build-{i}.log': sha(manifest.parent / f'build-{i}.log') for i in range(2)}:
        raise ValueError('build logs changed')
    return m


def build(source, output, variant, backend, jobs=4, arch=None):
    if variant not in ('baseline', 'patched') or backend not in ('cpu', 'hip'):
        raise ValueError('invalid build variant/backend')
    if type(jobs) is not int or not 1 <= jobs <= 64:
        raise ValueError('bounded build parallelism required')
    if backend == 'hip' and (not arch or not arch.replace(':', '').isalnum()):
        raise ValueError('explicit HIP architecture required')
    source, output = Path(source).resolve(strict=True), Path(output).resolve()
    if output == source or source in output.parents or output.exists():
        raise ValueError('new output directory outside source required')
    source_state(source, 'baseline')  # Refuse dirty/frozen trees BEFORE mutation.
    tooling = {name: sha(HERE / name) for name in OWNED}
    if variant == 'patched':
        install(source)
    before = source_state(source, variant)
    output.mkdir(parents=True)
    # A wrapper project builds the full kernel and both runners in one dependency graph.
    # JSON string quoting is compatible with CMake paths; reject its expansion syntax.
    def q(path):
        s = str(path)
        if any(c in s for c in (';', '$', '\n', '\r')):
            raise ValueError('unsafe CMake path')
        return json.dumps(s)
    cmake = ['cmake_minimum_required(VERSION 3.22)', 'project(am_full LANGUAGES C CXX)',
             'set(CMAKE_CXX_STANDARD 17)',
             'set(CMAKE_RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin")',
             'set(CMAKE_LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin")',
             f'add_subdirectory({q(source)} kernel)',
             f'add_executable(am-control {q(HERE / "control.cpp")})',
             f'target_include_directories(am-control PRIVATE {q(source / "include")} {q(source / "ggml/include")} {q(source / "vendor")})',
             'target_link_libraries(am-control PRIVATE llama ggml ggml-base)']
    if variant == 'patched':
        cmake += [f'add_executable(am-driver {q(HERE / "driver.cpp")})',
                  'target_include_directories(am-driver PRIVATE ' + ' '.join(q(p) for p in
                   (source / 'src', HERE, source / 'include', source / 'ggml/include', source / 'vendor')) + ')',
                  'target_link_libraries(am-driver PRIVATE llama ggml ggml-base)']
    (output / 'CMakeLists.txt').write_text('\n'.join(cmake) + '\n')
    configure = ['cmake', '-S', str(output), '-B', str(output / 'build'),
                 '-DCMAKE_BUILD_TYPE=Release', '-DBUILD_SHARED_LIBS=ON',
                 '-DLLAMA_BUILD_TESTS=OFF', '-DLLAMA_BUILD_EXAMPLES=OFF',
                 '-DLLAMA_BUILD_SERVER=OFF', '-DLLAMA_CURL=OFF',
                 # The pinned fused model calls CPU symbols directly. MODULE backends
                 # cannot satisfy those link dependencies; shared linked backends can.
                 '-DGGML_NATIVE=OFF', '-DGGML_BACKEND_DL=OFF', '-DGGML_CPU=ON',
                 '-DGGML_HIP=' + ('ON' if backend == 'hip' else 'OFF')]
    if backend == 'hip':
        configure.append('-DAMDGPU_TARGETS=' + arch)
    commands = [configure, ['cmake', '--build', str(output / 'build'), '--parallel', str(jobs)]]
    env = dict(os.environ)
    for i, command in enumerate(commands):
        with (output / f'build-{i}.log').open('xb') as log:
            subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    if source_state(source, variant) != before or tooling != {n: sha(HERE / n) for n in OWNED}:
        raise ValueError('source/tooling changed during build')
    m = dict(schema='epyc.am.full-build.v1', status='BUILT', source=str(source),
             source_state=before, variant=variant, backend=backend, architecture=arch,
             commands=commands, environment={k: env[k] for k in ENV_KEYS if k in env},
             tooling_sha256=tooling, artifacts_sha256=artifacts(output, variant, backend),
             logs_sha256={f'build-{i}.log': sha(output / f'build-{i}.log') for i in range(2)})
    manifest = output / 'BUILD.json'
    with manifest.open('x') as f:
        f.write(json.dumps(m, indent=2) + '\n')
    verify(manifest)
    return manifest


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='action', required=True)
    b = sub.add_parser('build')
    b.add_argument('--source', required=True)
    b.add_argument('--output', required=True)
    b.add_argument('--variant', choices=('baseline', 'patched'), required=True)
    b.add_argument('--backend', choices=('cpu', 'hip'), required=True)
    b.add_argument('--jobs', type=int, default=4)
    b.add_argument('--arch')
    v = sub.add_parser('verify')
    v.add_argument('manifest')
    a = p.parse_args()
    if a.action == 'verify':
        verify(a.manifest)
        print('VERIFIED ' + str(Path(a.manifest).resolve()))
    else:
        print(build(a.source, a.output, a.variant, a.backend, a.jobs, a.arch))
