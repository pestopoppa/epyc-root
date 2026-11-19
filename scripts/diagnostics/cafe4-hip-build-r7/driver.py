#!/usr/bin/env python3
"""Bounded, model-free modes build qualification; invoked only by rowflow."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

D = Path('/mnt/raid0/llm/tmp/df2/cafe4-modes-hip-r7-20261119')
S = Path('/mnt/raid0/llm/tmp/df2/cafe4-modes-source')
COMMIT = 'ffc1bac82eeca6f9099e1ccd9ba49703c460a115'
PATCH = '351a431702613a5cad8d165c6959dbcde12a928963b8833bfa4668abb743e4dd'
CLANGXX = '/opt/rocm/llvm/bin/clang++'
IQK_COMPAT = '-Wno-enum-constexpr-conversion'
MARKERS = (b'CAFE4_MTP_LOAD_ENABLED', b'CAFE4_MTP_ROLLBACK',
           b'CAFE4_DRAFT_REWIND_V4', b'--verify-batch', b'--fault-injection',
           b'FAIL injected-fault', b'CAFE4_TRIAL_FAILURE', b'CAFE4_CONTROL_FAILURE',
           b'CAFE4_BOUNDARY', b'CAFE4_PROPOSAL', b'CAFE4_VERIFY_TOKEN', b'rollback-configure')


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def inputs():
    record = json.loads((D / 'inputs.json').read_text())
    for path, expected in record['files'].items():
        if digest(path) != expected:
            raise ValueError(f'input digest mismatch: {path}')
    head = subprocess.check_output(['git', '-C', str(S), 'rev-parse', 'HEAD'], text=True).strip()
    diff = subprocess.check_output(['git', '-C', str(S), 'diff', '--binary', '--abbrev=10', 'HEAD'])
    if head != COMMIT or hashlib.sha256(diff).hexdigest() != PATCH:
        raise ValueError('experimental source identity mismatch')
    if subprocess.check_output(['git', '-C', str(S), 'ls-files', '--others', '--exclude-standard']):
        raise ValueError('untracked experimental source')
    return record


def require_exports(library, required):
    """Require exact, defined code exports, never imports or substring matches."""
    output = subprocess.check_output(
        ['nm', '-D', '--defined-only', '--format=posix', str(library)], text=True)
    defined = {fields[0] for line in output.splitlines()
               if len(fields := line.split()) >= 2 and fields[1] in ('T', 'W')}
    missing = set(required) - defined
    if missing:
        raise ValueError(f'compiled exports missing from {library}: {sorted(missing)}')


def validate(record):
    native = inputs()
    if record['input_files'] != native['files'] or record['source_commit'] != COMMIT or record['patch_sha256'] != PATCH:
        raise ValueError('receipt input binding mismatch')
    run = Path(record['run']).resolve(strict=True)
    if run.parent != (D / 'runs').resolve():
        raise ValueError('unexpected run directory')
    for path, expected in record['files'].items():
        resolved = Path(path).resolve(strict=True)
        if not resolved.is_relative_to(run) or digest(resolved) != expected:
            raise ValueError(f'artifact mismatch: {path}')
    mode = record['mode']
    artifact = run / ('candidate.o' if mode == 'smoke' else 'build/bin/cafe4-mtp-rollback')
    strings = subprocess.check_output(['strings', str(artifact)])
    if not all(marker in strings for marker in MARKERS):
        raise ValueError('compiled option/control marker missing')
    if mode == 'build':
        linkage = (run / 'linkage.log').read_text()
        required = ('libllama.so', 'libllama-common.so', 'libggml.so', 'libggml-base.so', 'libggml-cpu.so', 'libggml-hip.so')
        if 'not found' in linkage:
            raise ValueError('unresolved library')
        for library in required:
            matches = [line for line in linkage.splitlines() if line.strip().startswith(library)]
            if len(matches) != 1 or ' => ' not in matches[0]:
                raise ValueError(f'missing linkage: {library}')
            target = Path(matches[0].split(' => ', 1)[1].split()[0]).resolve()
            if target.parent != run / 'build/bin':
                raise ValueError(f'nonlocal library: {target}')
        cache = (run / 'build/CMakeCache.txt').read_text()
        if IQK_COMPAT not in cache or CLANGXX not in cache:
            raise ValueError('missing Clang IQK compatibility configuration')
        cpu_lib = (run / 'build/bin/libggml-cpu.so').resolve(strict=True)
        if str(cpu_lib) not in record['files']:
            raise ValueError('IQK library not hash-bound')
        require_exports(cpu_lib, ('iqk_mul_mat', 'ggml_iqk_try_mul_mat'))
        if 'GGML_HIP:BOOL=ON' not in cache or 'CMAKE_HIP_ARCHITECTURES:UNINITIALIZED=gfx90a' not in cache and 'CMAKE_HIP_ARCHITECTURES:STRING=gfx90a' not in cache:
            raise ValueError('missing HIP/gfx90a build configuration')
        hip_lib = (run / 'build/bin/libggml-hip.so').resolve(strict=True)
        if str(hip_lib) not in record['files']:
            raise ValueError('HIP library not hash-bound')
        # v10 HIP uses the CUDA API registration name, in libggml-hip.
        require_exports(hip_lib, ('ggml_backend_cuda_reg',))
        if b'gfx90a' not in subprocess.check_output(['strings', str(hip_lib)]):
            raise ValueError('compiled gfx90a image marker missing')
    elif mode == 'smoke':
        if 'enum-constexpr-conversion' not in (run / 'iqk-negative.log').read_text():
            raise ValueError('missing IQK regression witness')
        if (run / 'iqk-fixed.log').read_text().find('error:') >= 0:
            raise ValueError('IQK compatibility syntax check failed')
    elif mode != 'smoke':
        raise ValueError('unknown qualification mode')


def write(mode, run, out):
    native = inputs()
    files = [run / 'candidate.o', run / 'iqk-negative.log', run / 'iqk-fixed.log'] if mode == 'smoke' else [
        run / 'build/bin/cafe4-mtp-rollback', run / 'build/CMakeCache.txt',
        run / 'configure.log', run / 'build.log', run / 'linkage.log',
        *list((run / 'build/bin').glob('libllama*.so*')),
        *list((run / 'build/bin').glob('libggml*.so*'))]
    record = dict(schema='epyc.cafe4.modes.build.v1', mode=mode, run=str(run),
                  source_commit=COMMIT, patch_sha256=PATCH, input_files=native['files'],
                  files={str(p.resolve()): digest(p) for p in files},
                  scope='HIP gfx90a build qualification only; no native rollback, GPU execution or performance verdict')
    validate(record)
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', dir=out.parent, delete=False) as stream:
        json.dump(record, stream, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(stream.name, out)


def build():
    native = inputs()
    stop = Path(os.environ['FILLER_STOPFILE'])
    deadline = int(os.environ['FILLER_DEADLINE'])
    def check():
        if stop.exists() or time.time() >= deadline:
            raise SystemExit(75)
    def run(command, log=None, env=None):
        check()
        command = [sys.executable, native['supervisor'], str(stop), str(deadline), *command]
        if log:
            with log.open('w') as stream:
                subprocess.run(command, check=True, stdout=stream, stderr=subprocess.STDOUT, env=env)
        else:
            subprocess.run(command, check=True, env=env)
        check()
    check()
    (D / 'runs').mkdir(exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix='build-', dir=D / 'runs'))
    includes = [str(D), native['modes_include'], native['bridge_include'],
                str(S / 'common'), str(S / 'src'), str(S / 'include'), str(S / 'ggml/include')]
    if os.environ.get('FILLER_DRYRUN') == '1':
        # Reproduce the original Clang enum error, then require the same IQK
        # translation unit to pass with only the compatibility diagnostic disabled.
        iqk = [CLANGXX, '-std=c++17', '-march=native', '-DGGML_USE_IQK_MULMAT',
               '-D_GNU_SOURCE', '-D_XOPEN_SOURCE=600',
               *['-I' + str(S / q) for q in ('ggml/include', 'ggml/src',
                   'ggml/src/ggml-cpu', 'ggml/src/ggml-cpu/iqk')],
               '-fsyntax-only', str(S / 'ggml/src/ggml-cpu/iqk/iqk_mul_mat.cpp')]
        try:
            run(iqk, work / 'iqk-negative.log')
        except subprocess.CalledProcessError as error:
            if error.returncode != 1 or 'enum-constexpr-conversion' not in (work / 'iqk-negative.log').read_text():
                raise
        else:
            raise ValueError('unfixed IQK unexpectedly passed')
        run([*iqk, IQK_COMPAT], work / 'iqk-fixed.log')
        run([CLANGXX, IQK_COMPAT, '-std=c++17', '-O2', *['-I' + p for p in includes],
             '-c', str(D / 'candidate.cpp'), '-o', str(work / 'candidate.o')])
        write('smoke', work, Path(os.environ['FILLER_DRYRUN_RESULT_PATH']))
        # First-progress checker owns STOP after validating the compiled object.
        while not stop.exists() and time.time() < deadline:
            time.sleep(0.2)
        return 75
    flags = IQK_COMPAT + ' ' + ' '.join('-I' + p for p in includes)
    run(['cmake', '-G', 'Unix Makefiles', '-S', str(S), '-B', str(work / 'build'),
         '-DCAFE4_MTP_DIR=' + str(D), '-DCMAKE_BUILD_TYPE=Release',
         '-DCMAKE_CXX_FLAGS=' + flags, '-DGGML_HIP=ON', '-DGGML_BACKEND_DL=OFF',
         '-DCMAKE_C_COMPILER=/opt/rocm/llvm/bin/clang',
         '-DCMAKE_CXX_COMPILER=/opt/rocm/llvm/bin/clang++',
         '-DCMAKE_HIP_COMPILER=/opt/rocm/llvm/bin/clang++',
         '-DCMAKE_HIP_ARCHITECTURES=gfx90a', '-DLLAMA_BUILD_COMMON=ON',
         '-DLLAMA_BUILD_TESTS=OFF', '-DLLAMA_BUILD_EXAMPLES=ON',
         '-DLLAMA_BUILD_TOOLS=OFF', '-DLLAMA_BUILD_SERVER=OFF', '-DLLAMA_CURL=OFF'], work / 'configure.log')
    run(['cmake', '--build', str(work / 'build'), '--target', 'cafe4-mtp-rollback',
         '--parallel', os.environ['FILLER_THREADS']], work / 'build.log')
    env = {**os.environ, 'LD_LIBRARY_PATH': str(work / 'build/bin'),
           'FILLER_ID': os.environ['FILLER_ID']}
    run(['ldd', str(work / 'build/bin/cafe4-mtp-rollback')], work / 'linkage.log', env)
    write('build', work, D / 'RESULT.json')
    return 0


def main():
    action = sys.argv[1]
    if action == 'inputs':
        inputs()
    elif action == 'predicate':
        path = Path(os.environ['FILLER_DRYRUN_RESULT_PATH'])
        if path.stat().st_mtime < int(os.environ['FILLER_SMOKE_T0']):
            return 1
        record = json.loads(path.read_text())
        if record['mode'] != 'smoke':
            return 1
        validate(record)
    elif action == 'check':
        record = json.loads((D / 'RESULT.json').read_text())
        if record['mode'] != 'build':
            return 1
        validate(record)
    elif action == 'build':
        return build()
    else:
        return 64
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, KeyError, ValueError, subprocess.CalledProcessError) as error:
        print(f'CAFE4 BUILD REFUSED: {error}', file=sys.stderr)
        sys.exit(1)
