#!/usr/bin/env python3
"""Owner-granted build/capture bodies. DRY mode never assembles, builds or loads a model."""
from __future__ import annotations
import argparse
import ast
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
BASE = Path(__file__).resolve().parent
FLAGS = Path('/mnt/raid0/llm/tmp/compute-flags')

def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''): h.update(block)
    return h.hexdigest()

def now(): return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
def write(path, obj): path.write_text(json.dumps(obj, sort_keys=True, indent=2) + '\n')
def hold():
    if list(FLAGS.rglob('HOLD_*')) or list(Path('/mnt/raid0/llm/tmp').glob('HOLD_*')) or (BASE / 'STOP').exists():
        raise ValueError('HOLD/STOP')

def guard():
    hold()
    ident = os.environ.get('FILLER_ID', '')
    if ident not in ('kpf62-native-g1-fixed-build-20261027', 'kpf62-native-g1-fixed-capture-20261027'):
        raise ValueError('actual official filler identity required')
    if os.environ.get('FILLER_STOPFILE') != str(BASE / 'STOP'):
        raise ValueError('wrong owner STOP')
    p = FLAGS / 'grants' / (ident + '.grant')
    if not p.is_file() or p.is_symlink(): raise ValueError('canonical grant missing')
    fields = dict(piece.split('=', 1) for piece in p.read_text().strip().split())
    if set(fields) != {'regions', 'start', 'end'}: raise ValueError('grant syntax')
    current = now()
    if not datetime.fromisoformat(fields['start'].replace('Z','+00:00')) <= datetime.now(timezone.utc) <= datetime.fromisoformat(fields['end'].replace('Z','+00:00')): raise ValueError('grant not live')
    if int(datetime.now(timezone.utc).timestamp()) >= int(os.environ['FILLER_DEADLINE']):
        raise ValueError('no new work after filler deadline')
    if set(os.sched_getaffinity(0)) != expand(os.environ['FILLER_CPUS']):
        raise ValueError('actual affinity differs from official literal CPU list')
    tokens = fields['regions'].replace(';', ',').split(',')
    numeric = [t for t in tokens if t and t[0].isdigit()]
    quarters = [t for t in tokens if t in ('q0','q1','q2','q3')]
    if len(numeric) + len(quarters) != len(tokens): raise ValueError('unexpected non-CPU grant region')
    declared = expand(','.join(numeric)) if numeric else set()
    if not numeric:
        for q in quarters:
            first = int(q[1]) * 24
            declared.update(range(first, first + 24))
            declared.update(range(first + 96, first + 112))
    if declared != set(os.sched_getaffinity(0)): raise ValueError('canonical grant/actual CPU shape mismatch')
    if len({c % 96 for c in declared}) != 24 or len({(c % 96) // 24 for c in declared}) != 1:
        raise ValueError('this row is predeclared for one CPU quarter')
    threads = int(os.environ['FILLER_THREADS'])
    if threads < 1 or threads > len({x % 96 for x in os.sched_getaffinity(0)}): raise ValueError('thread cap')
    # The claimed official region-lock launcher must be OUR ancestor.
    parent, found = os.getppid(), False
    while parent > 1:
        cmd = Path(f'/proc/{parent}/cmdline').read_bytes().replace(b'\0', b' ')
        if b'src.runtime.region_lock_cli run --cpu-list ' in cmd and b' --role build ' in cmd:
            found = True
        status = Path(f'/proc/{parent}/status').read_text()
        parent = int(next(line.split()[1] for line in status.splitlines() if line.startswith('PPid:')))
    if not found: raise ValueError('official ancestor claim missing')
    return {'grant_id': ident, 'path': str(p), 'sha256': sha(p), 'regions': fields['regions'],
            'start_utc': fields['start'], 'end_utc': fields['end']}, threads

def expand(s):
    out = set()
    for part in s.split(','):
        a, _, b = part.partition('-')
        out.update(range(int(a), int(b or a) + 1))
    return out

def run(argv, log, env=None, expected=0):
    guard()
    started = now()
    with log.open('wb') as stdout, log.with_suffix('.stderr').open('wb') as stderr:
        child = subprocess.Popen([str(x) for x in argv], stdout=stdout, stderr=stderr, env=env)
        rc = child.wait()
    # All compute subprocesses remain in the launcher's captured session/group.
    # Never use setsid or detached children here. Official launcher owns hard timeout.
    result = {'argv': [str(x) for x in argv], 'pid': child.pid, 'started_at_utc': started,
              'finished_at_utc': now(), 'exit_code': rc, 'child_drained': child.poll() is not None,
              'stdout': {'path': str(log), 'sha256': sha(log)},
              'stderr': {'path': str(log.with_suffix('.stderr')), 'sha256': sha(log.with_suffix('.stderr'))}}
    write(log.with_suffix('.receipt.json'), result)
    if rc != expected: raise ValueError(f'child exit {rc}, expected {expected}: {argv[0]}')
    return result

def dry():
    # Called only by pf.sh after its live parent fd9 + official 26/27 proof.
    if os.environ.get('KPF62_REAL_PF') != '1': raise ValueError('PF context not established')
    hold()
    if os.sched_getaffinity(0) != {26, 27}: raise ValueError('PF actual affinity')
    for path in BASE.glob('*.py'): ast.parse(path.read_text(), filename=str(path))
    from prepare_candidate import CHAMPION, API, ROOT
    for repo, pin in (('/mnt/raid0/llm/llama.cpp', CHAMPION), ('/mnt/raid0/llm/llama.cpp', API), ('/workspace', ROOT)):
        subprocess.run(['git', '-C', repo, 'cat-file', '-e', pin + '^{commit}'], check=True)
    if (BASE / 'assembly.json').exists() or (BASE / 'build').exists():
        raise ValueError('dry requires unused source packet: stale assembly/build')
    print('DRY_RUN: actual PF source/deps verified; assembly/build/models/nativecapture NOT_RUN')

def check_cache(build, kind):
    reference = Path('/mnt/raid0/llm/kernels/builds') / (kind + '-20261024-c72ec82f5-c5') / 'CMakeCache.txt'
    def flags(path):
        return sorted(line for line in path.read_text().splitlines()
                      if line.startswith(('GGML_', 'LLAMA_')) and
                      not any(x in line for x in ('CCACHE', '_DIR', 'PATH')))
    expected, actual = flags(reference), flags(build / 'CMakeCache.txt')
    diff = {'reference': str(reference), 'reference_sha256': sha(reference),
            'missing_or_changed': sorted(set(expected) - set(actual)),
            'new_or_changed': sorted(set(actual) - set(expected))}
    write(BASE / (kind + '-cache-diff.json'), diff)
    if diff['missing_or_changed'] or diff['new_or_changed']:
        raise ValueError(kind + ' C5 cache profile drift')

def build():
    grant, threads = guard()
    if os.environ['FILLER_ID'] != 'kpf62-native-g1-fixed-build-20261027': raise ValueError('wrong build row')
    if shutil.disk_usage(BASE).free < 150 * 1024**3: raise ValueError('150 GiB disk floor')
    run([sys.executable, '-B', '-s', BASE / 'prepare_candidate.py'], BASE / 'assembly.log')
    candidate, builddir = BASE / 'candidate', BASE / 'build'
    pmap = f'-ffile-prefix-map={candidate}=. -fmacro-prefix-map={candidate}=. -ffile-prefix-map={builddir}=.build -fmacro-prefix-map={builddir}=.build'
    args = ['cmake', '-S', candidate, '-B', builddir, '-DCMAKE_BUILD_TYPE=Release',
            '-DGGML_NATIVE=ON', '-DGGML_HIP=OFF', '-DGGML_OPENMP=ON', '-DLLAMA_CURL=OFF',
            '-DCMAKE_C_COMPILER=/usr/bin/gcc-15', '-DCMAKE_CXX_COMPILER=/usr/bin/g++-15',
            '-DCMAKE_C_FLAGS=' + pmap, '-DCMAKE_CXX_FLAGS=' + pmap,
            '-DCMAKE_BUILD_RPATH_USE_ORIGIN=ON', '-DCMAKE_BUILD_WITH_INSTALL_RPATH=ON',
            '-DCMAKE_INSTALL_RPATH=$ORIGIN']
    # Existing tests/CMakeLists links server-context from chat tests at configure
    # time; enable its target, but never build/launch a server for this row.
    configure = run(args, BASE / 'configure.log')
    check_cache(builddir, 'cpu')
    compiled = run(['cmake', '--build', builddir, '-j', str(threads), '--target', 'test-llama-archs', 'test-chunk-kv'], BASE / 'build.log')
    gpu = BASE / 'build-hip'
    if shutil.disk_usage(BASE).free < 150 * 1024**3: raise ValueError('150 GiB disk floor before HIP build')
    hpmap = f'-ffile-prefix-map={candidate}=. -fmacro-prefix-map={candidate}=. -ffile-prefix-map={gpu}=.build -fmacro-prefix-map={gpu}=.build'
    hip_args = ['cmake', '-S', candidate, '-B', gpu, '-DCMAKE_BUILD_TYPE=Release', '-DGGML_NATIVE=ON', '-DGGML_HIP=ON',
                '-DGGML_HIP_ROCWMMA_FATTN=ON', '-DGGML_HIP_MMQ_MFMA=ON', '-DAMDGPU_TARGETS=gfx90a',
                '-DCMAKE_C_FLAGS=' + hpmap, '-DCMAKE_CXX_FLAGS=' + hpmap, '-DCMAKE_HIP_FLAGS=' + hpmap,
                '-DCMAKE_BUILD_RPATH_USE_ORIGIN=ON', '-DCMAKE_BUILD_WITH_INSTALL_RPATH=ON',
                '-DCMAKE_INSTALL_RPATH=$ORIGIN;/opt/rocm/lib']
    hip_configure = run(hip_args, BASE / 'hip-configure.log')
    check_cache(gpu, 'gpu')
    hip_compiled = run(['cmake', '--build', gpu, '-j', str(threads), '--target', 'test-chunk-kv'], BASE / 'hip-build.log')
    verifier = '/workspace/repos/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh'
    for build, name in ((builddir, 'cpu'), (gpu, 'hip')):
        env = os.environ.copy()
        env['LD_LIBRARY_PATH'] = str(build / 'bin') + ':/opt/rocm/lib'
        run([verifier, build / 'bin/test-chunk-kv', build], BASE / (name + '-linkage.log'), env)
        run(['/usr/bin/readelf', '-h', '-n', build / 'bin/test-chunk-kv'], BASE / (name + '-elf.log'))
    for tool, name in (('/usr/bin/gcc-15', 'gcc'), ('/usr/bin/g++-15', 'gxx'),
                       ('/opt/rocm/lib/llvm/bin/clang++', 'hip-clang'), ('/usr/bin/cmake', 'cmake')):
        run([tool, '--version'], BASE / ('toolchain-' + name + '.log'))
    files = {}
    for directory in (builddir, gpu):
        for path in sorted((directory / 'bin').glob('*')):
            if path.is_file(): files[str(path)] = sha(path)
    receipt = {'schema': 'epyc.kpf62.build.v1', 'grant': grant, 'configure': configure, 'compiled': compiled,
               'source_assembly_sha256': sha(BASE / 'assembly.json'), 'files': files, 'threads': threads,
               'hip_configure': hip_configure, 'hip_compiled': hip_compiled,
               'cpus': os.environ['FILLER_CPUS'], 'completed_at_utc': now(),
               'manifest_evidence': {name: sha(BASE / name) for name in
                   ('SOURCE.SHA256SUMS', 'NATIVE-SOURCES.sha256', 'cpu-elf.log', 'hip-elf.log',
                    'cpu-linkage.log', 'hip-linkage.log', 'toolchain-gcc.log', 'toolchain-gxx.log',
                    'toolchain-hip-clang.log', 'toolchain-cmake.log')}}
    write(BASE / 'build-receipt.json', receipt)

def capture():
    grant, threads = guard()
    if os.environ['FILLER_ID'] != 'kpf62-native-g1-fixed-capture-20261027': raise ValueError('wrong capture row')
    import finalize
    assembly = finalize.verify_sources()
    receipt = json.loads((BASE / 'build-receipt.json').read_text())
    if receipt['source_assembly_sha256'] != sha(BASE / 'assembly.json'): raise ValueError('build source drift')
    for name, digest in receipt['files'].items():
        if sha(name) != digest: raise ValueError('ELF/library build drift')
    run_dir = BASE / ('native-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    run_dir.mkdir()
    env = {k: os.environ[k] for k in ('PATH', 'HOME', 'TMPDIR', 'LANG', 'TZ') if k in os.environ}
    env.update(LD_LIBRARY_PATH=str(BASE / 'build/bin'), GGML_IQK='1', CKV_N_CHUNK='24', CKV_G1_REF_INFORMATIONAL='1',
               OMP_NUM_THREADS=str(threads), OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1', LD_DEBUG='libs')
    for k in ('CKV_SKIP_K_GATE', 'GGML_FUSED_DECODE_ON', 'GGML_BACKEND_PATH'): env.pop(k, None)
    binary, generator = BASE / 'build/bin/test-chunk-kv', BASE / 'build/bin/test-llama-archs'
    artifacts = []
    def artifact(kind, path): artifacts.append({'kind': kind, 'path': str(path), 'sha256': sha(path)})
    authority = run_dir / 'authority.json'
    write(authority, {'grant': grant, 'cpus': os.environ['FILLER_CPUS'], 'threads': threads,
                      'parent_pid': os.getppid(), 'observed_at_utc': now()})
    artifact('authority', authority)
    artifact('build_receipt', BASE / 'build-receipt.json')
    for kind, path in (('binary_elf', binary), ('generator_elf', generator)):
        if path.read_bytes()[:4] != b'\x7fELF': raise ValueError('not native ELF')
        info = run_dir / (kind + '.txt')
        info.write_bytes(subprocess.check_output(['readelf', '-h', '-n', str(path)]))
        artifact(kind, info)
    library_log = run_dir / 'libraries.json'
    write(library_log, {'LD_LIBRARY_PATH': env['LD_LIBRARY_PATH'], 'files': receipt['files'],
                       'note': 'CPU-only configured instrument; no HIP residency claim'})
    artifact('libraries', library_log)
    # Generated-model creation itself is compute and stays inside this capture row.
    for arch in ('qwen3', 'qwen35'):
        run([generator, '-a', arch, '-s', '1234', '-o', run_dir], run_dir / ('generate-' + arch + '.log'), env)
    for arch in ('qwen3', 'qwen35'):
        for suffix in ('.log', '.stderr', '.receipt.json'):
            artifact('generator_provenance', run_dir / ('generate-' + arch + suffix))
        artifact('generated_model', run_dir / (arch + '-dense.gguf'))
    raw = run_dir / 'g1-position.jsonl'
    argv = [binary, '-m', run_dir / 'qwen3-dense.gguf', '-ctk', 'f32', '-ctv', 'f32', '-t', str(threads), '--g1-capture-jsonl', raw]
    before = run_dir / 'cpu-before.txt'; before.write_text(Path('/proc/self/status').read_text()); artifact('cpu_before', before)
    native = run(argv, run_dir / 'native.log', env)
    after = run_dir / 'cpu-after.txt'; after.write_text(Path('/proc/self/status').read_text()); artifact('cpu_after', after)
    artifact('native_stdout', run_dir / 'native.log'); artifact('native_stderr', run_dir / 'native.stderr')
    # Independent unsupported-memory run: model loads/decode happen under this
    # grant, API refuses, and decoder usability/off-identical checks still gate.
    control = run([binary, '-m', run_dir / 'qwen35-dense.gguf', '-ctk', 'f32', '-ctv', 'f32', '-t', str(threads)], run_dir / 'hybrid-refusal.log', env)
    refused_raw = run_dir / 'unsupported-position.jsonl'
    capture_refusal = run([binary, '-m', run_dir / 'qwen35-dense.gguf', '-ctk', 'f32', '-ctv', 'f32', '-t', str(threads), '--g1-capture-jsonl', refused_raw], run_dir / 'hybrid-capture-refusal.log', env, 2)
    if refused_raw.exists(): raise ValueError('unsupported model emitted G1 positions')
    controls = run_dir / 'native-controls.json'
    write(controls, {'unsupported_memory_api_and_decode': control, 'unsupported_capture': capture_refusal,
                     'native_attention_controls': 'overlap, negative delta, corrupt magic, truncated blob, source hole and OFF-identical are CHECK-gated in native.log'})
    artifact('native_controls', controls)
    for stem in ('hybrid-refusal', 'hybrid-capture-refusal'):
        for suffix in ('.log', '.stderr', '.receipt.json'):
            artifact('control_provenance', run_dir / (stem + suffix))
    from prepare_candidate import CHAMPION, ROOT
    record = {'schema': 'epyc.chunk_kv.g1_invocation.v1', 'run_id': run_dir.name,
              'producer_commit': CHAMPION, 'root_adapter_commit': ROOT,
              'source_assembly_sha256': sha(BASE / 'assembly.json'), 'source_digest': assembly['source_digest'],
              'role': 'generated-tiny-cpu-correctness', 'argv': [str(x) for x in argv],
              'model': {'name': 'qwen3-dense-generated-seed1234', 'path': str(run_dir / 'qwen3-dense.gguf'), 'sha256': sha(run_dir / 'qwen3-dense.gguf')},
              'binary': {'path': str(binary), 'sha256': sha(binary)}, 'grant': grant,
              'window': {'window_id': grant['grant_id'], 'region_lock_claim': 'official ancestor --role build; cpus=' + os.environ['FILLER_CPUS'],
                         'start_utc': grant['start_utc'], 'end_utc': grant['end_utc']},
              'capture': {'path': str(raw), 'sha256': sha(raw), 'exit_code': native['exit_code'],
                          'started_at_utc': native['started_at_utc'], 'finished_at_utc': native['finished_at_utc'],
                          'deltas': [1,17,300], 'n_chunk': 24, 'n_suffix': 6, 'environment': env},
              'context': {'n_ctx_seq':1024,'n_ctx':8192,'n_seq_max':8,'n_batch':512,'n_ubatch':512,'n_suffix':6,'deltas':[1,17,300],'seed':1234},
              'lifecycle': {'child_drained': native['child_drained'], 'timed_out': False}, 'artifacts': artifacts,
              'finalized_at_utc': now()}
    invocation = run_dir / 'invocation.json'; write(invocation, record)
    guard()
    final = finalize.finalize(raw, invocation, run_dir / 'finalized')
    run([sys.executable, '-B', '-s', BASE / 'native_refusal_controls.py', '--raw', raw, '--invocation', invocation, '--finalized', final], run_dir / 'reader-controls.log', env)
    write(run_dir / 'CAPTURE-COMPLETE.json', {'finalized': str(final), 'shared_grades_sha256': sha(final / 'grades.json'), 'completed_at_utc': now()})
    write(BASE / 'CAPTURE-DONE.json', {'run': str(run_dir), 'completed_at_utc': now()})

if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--mode', choices=('dry','build','capture'), required=True); a = p.parse_args()
    try: {'dry': dry, 'build': build, 'capture': capture}[a.mode]()
    except Exception as exc:
        print('REFUSE ' + str(exc), file=sys.stderr)
        raise SystemExit(2)
