#!/usr/bin/env python3
"""Source-bound CAFE-3 full HIP gfx90a build, executed only by rowflow."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

D = Path('/mnt/raid0/llm/tmp/df2/cafe3-hip-build-20261119')
S = Path('/mnt/raid0/llm/tmp/df2/cafe3-full-source-20261119')
CLANGXX = '/opt/rocm/llvm/bin/clang++'
IQK_COMPAT = '-Wno-enum-constexpr-conversion'
BASE = 'ffc1bac82eeca6f9099e1ccd9ba49703c460a115'
MARKERS = (b'LLAMA_CAFE3_ADAPTIVE', b'LLAMA_CAFE3_CONTEXT_SHA256', b'epyc.cafe3.round.v1', b'CAFE3 journal poisoned')


def digest(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def inputs():
    record = json.loads((D / 'inputs.json').read_text())
    if record.get('supervisor_protocol') != 'epyc.cafe3.supervisor.v1':
        raise ValueError('supervisor protocol mismatch: prepare replacement inputs')
    if subprocess.check_output(['git', '-C', str(S), 'rev-parse', 'HEAD'], text=True).strip() != BASE:
        raise ValueError('wrong base')
    diff = subprocess.check_output(['git', '-C', str(S), 'diff', '--binary', 'HEAD'])
    if hashlib.sha256(diff).hexdigest() != record['diff_sha256']:
        raise ValueError('source diff drift')
    for path, expected in record['files'].items():
        if digest(path) != expected:
            raise ValueError('input drift: ' + path)
    untracked = subprocess.check_output(['git', '-C', str(S), 'ls-files', '--others', '--exclude-standard'], text=True).splitlines()
    if set(untracked) != set(record['untracked']):
        raise ValueError('unexpected untracked source')
    return record


def require_exports(library, required):
    output = subprocess.check_output(['nm', '-D', '--defined-only', '--format=posix', str(library)], text=True)
    defined = {f[0] for line in output.splitlines()
               if len(f := line.split()) >= 2 and f[1] in ('T', 'W')}
    if not set(required) <= defined:
        raise ValueError('compiled exports missing: ' + str(sorted(set(required) - defined)))


def validate(record):
    if record['inputs'] != inputs() or record['base'] != BASE:
        raise ValueError('receipt binding mismatch')
    run = Path(record['run']).resolve(strict=True)
    if run.parent != (D / 'runs').resolve() or record['mode'] not in ('smoke', 'build'):
        raise ValueError('invalid run')
    for name, expected in record['files'].items():
        path = Path(name).resolve(strict=True)
        if not path.is_relative_to(run) or digest(path) != expected:
            raise ValueError('artifact mismatch')
    artifact = run / ('server.o' if record['mode'] == 'smoke' else 'build/bin/libllama-server-impl.so')
    if str(artifact.resolve()) not in record['files']:
        raise ValueError('unbound compiled artifact')
    strings = subprocess.check_output(['strings', str(artifact)])
    if any(marker not in strings for marker in MARKERS):
        raise ValueError('compiled CAFE3 marker missing')
    if record['mode'] == 'build':
        for relative in ('build/bin/llama-server', 'build/CMakeCache.txt', 'linkage.log'):
            if str((run / relative).resolve(strict=True)) not in record['files']:
                raise ValueError('unbound build control: ' + relative)
        cache = (run / 'build/CMakeCache.txt').read_text()
        if 'GGML_HIP:BOOL=ON' not in cache or 'GGML_BACKEND_DL:BOOL=OFF' not in cache:
            raise ValueError('wrong backend configuration')
        if IQK_COMPAT not in cache or CLANGXX not in cache or not any('CMAKE_HIP_ARCHITECTURES:'+kind+'=gfx90a' in cache for kind in ('STRING', 'UNINITIALIZED')):
            raise ValueError('missing HIP compiler/IQK/gfx90a binding')
        if 'LLAMA_BUILD_UI:BOOL=OFF' not in cache or 'LLAMA_USE_PREBUILT_UI:BOOL=OFF' not in cache:
            raise ValueError('unexpected UI build/download')
        linkage = (run / 'linkage.log').read_text()
        if 'not found' in linkage:
            raise ValueError('unresolved library')
        found = set()
        for line in linkage.splitlines():
            if line.strip().startswith(('libggml', 'libllama')):
                target = Path(line.split(' => ')[1].split()[0]).resolve(strict=True)
                if target.parent != run / 'build/bin' or str(target) not in record['files']:
                    raise ValueError('nonlocal/unbound library')
                found.add(line.strip().split()[0])
        if not {'libllama.so', 'libggml.so', 'libggml-base.so', 'libggml-cpu.so', 'libggml-hip.so', 'libllama-server-impl.so'} <= found:
            raise ValueError('missing required libraries')

        cpu = (run / 'build/bin/libggml-cpu.so').resolve(strict=True)
        hip = (run / 'build/bin/libggml-hip.so').resolve(strict=True)
        require_exports(cpu, ('iqk_mul_mat', 'ggml_iqk_try_mul_mat'))
        require_exports(hip, ('ggml_backend_cuda_reg',))
        if b'gfx90a' not in subprocess.check_output(['strings', str(hip)]):
            raise ValueError('compiled gfx90a image marker missing')
    else:
        for name in ('iqk-negative.log', 'iqk-fixed.log'):
            if str((run / name).resolve()) not in record['files']:
                raise ValueError('unbound IQK control')
        if 'enum-constexpr-conversion' not in (run / 'iqk-negative.log').read_text():
            raise ValueError('missing IQK negative witness')
        if 'error:' in (run / 'iqk-fixed.log').read_text():
            raise ValueError('IQK compatibility check failed')


def build():
    native = inputs()
    stop, deadline = Path(os.environ['FILLER_STOPFILE']), int(os.environ['FILLER_DEADLINE'])
    def run(command, log, env=None):
        with log.open('w') as f:
            subprocess.run([sys.executable, native['supervisor'], str(stop), str(deadline), str(log.with_suffix('.supervisor.json')), *command],
                           stdout=f, stderr=subprocess.STDOUT, check=True, env=env)
    (D / 'runs').mkdir(exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix='build-', dir=D / 'runs'))
    smoke = os.environ.get('FILLER_DRYRUN') == '1'
    if smoke:
        includes = ['common', 'tools/server', 'include', 'src', 'ggml/include', 'vendor', 'tools/mtmd']
        iqk = [CLANGXX, '-std=c++17', '-march=native', '-DGGML_USE_IQK_MULMAT',
               '-D_GNU_SOURCE', '-D_XOPEN_SOURCE=600',
               *['-I'+str(S / p) for p in ('ggml/include', 'ggml/src', 'ggml/src/ggml-cpu', 'ggml/src/ggml-cpu/iqk')],
               '-fsyntax-only', str(S / 'ggml/src/ggml-cpu/iqk/iqk_mul_mat.cpp')]
        try:
            run(iqk, work / 'iqk-negative.log')
        except subprocess.CalledProcessError as error:
            if error.returncode != 1 or 'enum-constexpr-conversion' not in (work / 'iqk-negative.log').read_text():
                raise
        else:
            raise ValueError('unfixed IQK unexpectedly passed')
        run([*iqk, IQK_COMPAT], work / 'iqk-fixed.log')
        run([CLANGXX, IQK_COMPAT, '-std=c++17', '-O0', *['-I'+str(S / p) for p in includes],
             '-c', str(S / 'tools/server/server-context.cpp'), '-o', str(work / 'server.o')], work / 'compile.log')
        files = [work / 'server.o', work / 'compile.log', work / 'iqk-negative.log', work / 'iqk-fixed.log']
    else:
        run(['cmake', '-S', str(S), '-B', str(work / 'build'), '-DCMAKE_BUILD_TYPE=Release',
             '-DGGML_HIP=ON', '-DCMAKE_HIP_ARCHITECTURES=gfx90a',
             '-DCMAKE_C_COMPILER=/opt/rocm/llvm/bin/clang',
             '-DCMAKE_CXX_COMPILER='+CLANGXX, '-DCMAKE_HIP_COMPILER='+CLANGXX,
             '-DCMAKE_CXX_FLAGS='+IQK_COMPAT, '-DGGML_BACKEND_DL=OFF', '-DLLAMA_BUILD_SERVER=ON',
             '-DLLAMA_BUILD_TESTS=OFF', '-DLLAMA_CURL=OFF',
             '-DLLAMA_BUILD_UI=OFF', '-DLLAMA_USE_PREBUILT_UI=OFF'], work / 'configure.log')
        run(['cmake', '--build', str(work / 'build'), '--target', 'llama-server', '--parallel', os.environ['FILLER_THREADS']], work / 'build.log')
        run(['ldd', str(work / 'build/bin/llama-server')], work / 'linkage.log',
            {**os.environ, 'LD_LIBRARY_PATH': str(work / 'build/bin')})
        files = [work / 'build/bin/llama-server', work / 'build/CMakeCache.txt',
                 work / 'configure.log', work / 'build.log', work / 'linkage.log',
                 *list((work / 'build/bin').glob('libllama*.so*')),
                 *list((work / 'build/bin').glob('libggml*.so*'))]
    files.extend(work.glob('*.supervisor.json'))
    record = dict(schema='epyc.cafe3.hip-build.v1', base=BASE, inputs=native,
                  mode='smoke' if smoke else 'build', run=str(work),
                  files={str(p.resolve()): digest(p) for p in files})
    validate(record)
    out = Path(os.environ['FILLER_DRYRUN_RESULT_PATH']) if smoke else D / 'RESULT.json'
    with tempfile.NamedTemporaryFile(mode='w', dir=out.parent, delete=False) as f:
        json.dump(record, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(f.name, out)
    if smoke:
        while not stop.exists() and time.time() < deadline:
            time.sleep(.2)
        return 75
    return 0


def main():
    action = sys.argv[1]
    if action == 'inputs':
        inputs()
    elif action == 'build':
        return build()
    elif action in ('predicate', 'check'):
        p = Path(os.environ['FILLER_DRYRUN_RESULT_PATH']) if action == 'predicate' else D / 'RESULT.json'
        r = json.loads(p.read_text())
        if r['mode'] != ('smoke' if action == 'predicate' else 'build'):
            return 1
        if action == 'predicate' and p.stat().st_mtime < int(os.environ['FILLER_SMOKE_T0']):
            return 1
        validate(r)
    else:
        return 64
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as e:
        print(f'CAFE3 BUILD REFUSED: {e}', file=sys.stderr)
        sys.exit(1)
