#!/usr/bin/env python3
"""Build and content-prove diagnostic C6 CPU/GPU llama-bench candidates."""
import hashlib
import json
import os
from pathlib import Path
import shlex
import signal
import struct
import subprocess
import sys
import time

ROOT = Path('/mnt/raid0/llm/tmp/pf1-loadthreads-build-20261104')
WORK = ROOT / 'loadthreads-build'
INPUTS = WORK / 'BUILD-INPUTS.json'
INPUTS_SHA256 = '1df0ca0c1d8d0c7054adbd088ea08db869141c378eb78aa543883603858a90c9'
SOURCE_TU = 'tools/llama-bench/llama-bench.cpp'


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def filler_state():
    stop = Path(os.environ['FILLER_STOPFILE'])
    deadline = float(os.environ['FILLER_DEADLINE'])
    return stop, deadline


def guard(stop, deadline, reserve_s=45):
    if stop.exists() or time.time() + reserve_s >= deadline:
        raise SystemExit(75)


def run(argv, log_path, stop, deadline, cwd=ROOT, env=None, reserve_s=45):
    guard(stop, deadline, reserve_s)
    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, 'wb') as log:
        proc = subprocess.Popen(argv, cwd=cwd, env=env, stdout=log,
                                stderr=subprocess.STDOUT, start_new_session=True)
        try:
            while proc.poll() is None:
                guard(stop, deadline, reserve_s)
                time.sleep(1)
        finally:
            if proc.poll() is None:
                try:
                    os.killpg(proc.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait(timeout=15)
                if proc.poll() is None:
                    raise RuntimeError(f'owned build process {proc.pid} survived cleanup')
    if proc.returncode:
        raise SystemExit(f"command failed rc={proc.returncode}; see {log_path}")


def verify_source(spec):
    source = Path(spec['source_worktree'])
    head = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    tree = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD^{tree}'], text=True).strip()
    if (head, tree) != (spec['base_commit'], spec['base_tree']):
        raise SystemExit('source HEAD/tree differs from pinned C6 base')
    patch = Path(spec['source_patch'])
    current_patch = subprocess.check_output(['git', '-C', str(source), 'diff', '--binary', 'HEAD'])
    if current_patch != patch.read_bytes() or sha256(patch) != spec['source_patch_sha256']:
        raise SystemExit('source patch differs from sealed patch.diff')
    changed = subprocess.check_output(['git', '-C', str(source), 'diff', '--name-only', 'HEAD'], text=True).splitlines()
    status = subprocess.check_output(['git', '-C', str(source), 'status', '--porcelain'], text=True).splitlines()
    if changed != [SOURCE_TU] or status != [f' M {SOURCE_TU}']:
        raise SystemExit(f'unexpected source changes/status: {changed!r} {status!r}')


def verify_toolchain(spec):
    versions = {}
    for name, tool in spec['tools'].items():
        path = Path(tool['resolved_path'])
        if sha256(path) != tool['sha256']:
            raise SystemExit(f'pinned tool changed: {name} {path}')
        out = subprocess.check_output([tool['path'], '--version'], text=True, stderr=subprocess.STDOUT)
        versions[name] = out.splitlines()[0]
    expected = spec['backends']['cpu']['native']
    if expected['gcc'] not in versions['cxx'] or expected['cmake'] not in versions['cmake']:
        raise SystemExit(f'tool version mismatch: {versions!r}')
    if expected['clang'] not in versions['hip_cxx']:
        raise SystemExit(f'HIP compiler version mismatch: {versions!r}')
    return versions


def store_lib_hashes(backend):
    return {item['path']: sha256(item['path']) for item in backend['expected_unchanged_artifacts']}


def verify_stores(spec):
    actual = {}
    for name, backend in spec['backends'].items():
        identity = Path(backend['build_identity'])
        sums = Path(backend['sha256sums'])
        if sha256(identity) != backend['build_identity_sha256'] or sha256(sums) != backend['sha256sums_sha256']:
            raise SystemExit(f'pinned {name} C6 identity or manifest changed')
        checked = subprocess.run(['/usr/bin/sha256sum', '--check', '--status', 'SHA256SUMS'], cwd=backend['store_root'])
        if checked.returncode:
            raise SystemExit(f'pinned {name} C6 store fails SHA256SUMS')
        hashes = store_lib_hashes(backend)
        expected = {x['path']: x['sha256'] for x in backend['expected_unchanged_artifacts']}
        if hashes != expected:
            raise SystemExit(f'pinned {name} C6 libraries/binary differ from captured hashes')
        actual[name] = hashes
    return actual


def configure_argv(backend, build_dir, export_commands=False):
    old = backend['build_dir']
    argv = [arg.replace(old, str(build_dir)) for arg in backend['configure_argv']]
    if export_commands:
        argv.append('-DCMAKE_EXPORT_COMPILE_COMMANDS:BOOL=ON')
    return argv


def compile_actual_translation_unit(spec, smoke_dir, stop, deadline):
    backend = spec['backends']['cpu']
    build_dir = smoke_dir / 'cmake-cpu'
    config_cmd = configure_argv(backend, build_dir, export_commands=True)
    run(config_cmd, smoke_dir / 'configure.log', stop, deadline)
    commands_path = build_dir / 'compile_commands.json'
    entries = json.loads(commands_path.read_text())
    expected_source = str(Path(spec['source_worktree']) / SOURCE_TU)
    def entry_source(entry):
        value = Path(entry['file'])
        return str((Path(entry['directory']) / value).resolve() if not value.is_absolute() else value.resolve())
    matches = [entry for entry in entries if entry_source(entry) == str(Path(expected_source).resolve())]
    if len(matches) != 1:
        raise SystemExit(f'expected one compile command for patched translation unit, got {len(matches)}')
    entry = matches[0]
    argv = entry.get('arguments') or shlex.split(entry['command'])
    obj = smoke_dir / 'llama-bench.cpp.o'
    try:
        oi = argv.index('-o')
    except ValueError:
        raise SystemExit('CMake compile command has no -o output argument')
    argv[oi + 1] = str(obj)
    guard(stop, deadline)
    run(argv, smoke_dir / 'compile-object.log', stop, deadline, cwd=entry['directory'])
    data = obj.read_bytes()
    if len(data) < 20 or data[:4] != b'\x7fELF':
        raise SystemExit('compiled output is not an ELF object')
    e_type, e_machine = struct.unpack_from('<HH', data, 16)
    if e_type != 1 or e_machine != 62:
        raise SystemExit(f'compiled file is not an x86-64 relocatable ELF object: type={e_type}, machine={e_machine}')
    return {
        'compiled_object': str(obj), 'object_sha256': hashlib.sha256(data).hexdigest(),
        'object_size_bytes': len(data), 'compiled_object_count': 1,
        'translation_unit': expected_source, 'compiler_argv_sha256': hashlib.sha256('\0'.join(argv).encode()).hexdigest(),
        'configure_argv': config_cmd,
        'compile_commands_sha256': sha256(commands_path),
        'configure_log_sha256': sha256(smoke_dir / 'configure.log'),
        'compile_log_sha256': sha256(smoke_dir / 'compile-object.log'),
    }


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f'.tmp.{os.getpid()}')
    tmp.write_text(json.dumps(value, indent=2) + '\n')
    os.replace(tmp, path)


def dryrun(spec, stop, deadline, tool_versions, store_hashes):
    if os.environ.get('FILLER_DRYRUN') != '1':
        raise SystemExit('dryrun path requires FILLER_DRYRUN=1')
    smoke_dir = Path(os.environ['FILLER_DRYRUN_DIR']).resolve(strict=True)
    result_path = Path(os.environ['FILLER_DRYRUN_RESULT_PATH'])
    if not result_path.parent.is_dir() or result_path.exists():
        raise SystemExit('dry-run result destination must be a fresh file in the engine-created attempt directory')
    obj = compile_actual_translation_unit(spec, smoke_dir, stop, deadline)
    guard(stop, deadline)
    result = {
        'schema': 'pf1.loadthreads.native-dryrun.v1', 'mode': 'native-dryrun',
        'source_commit': spec['base_commit'], 'source_tree': spec['base_tree'],
        'patch_sha256': spec['source_patch_sha256'], 'cpu_store_sha256sums_sha256': spec['backends']['cpu']['sha256sums_sha256'],
        'build_inputs_sha256': sha256(INPUTS),
        'base_store_identity_sha256': {k: v['build_identity_sha256'] for k, v in spec['backends'].items()},
        'tool_versions': tool_versions, 'base_store_library_hashes': store_hashes,
        'claim_scope': 'engineering compilation only', 'model_read': False, **obj,
    }
    atomic_json(result_path, result)
    return result


def full_build(spec, stop, deadline, tool_versions, before_store_hashes):
    receipt_path = WORK / 'BUILD-RECEIPT.json'
    if receipt_path.exists():
        raise SystemExit(f'refusing to reuse existing build receipt: {receipt_path}')
    outputs = {}
    commands = {}
    for name, backend in spec['backends'].items():
        build_dir = Path(backend['build_dir'])
        if build_dir.exists():
            raise SystemExit(f'refusing to reuse output build directory: {build_dir}')
        config_cmd = configure_argv(backend, build_dir)
        run(config_cmd, WORK / f'configure-{name}.log', stop, deadline)
        run(backend['build_argv'], WORK / f'build-{name}.log', stop, deadline)
        binary = Path(backend['binary'])
        env = os.environ.copy()
        env['LD_LIBRARY_PATH'] = ':'.join((str(build_dir / 'bin'), str(Path(backend['store_root']) / 'bin'), '/opt/rocm/lib', '/usr/lib/llvm-20/lib'))
        guard(stop, deadline)
        help_text = subprocess.check_output([str(binary), '--load-threads', '1', '--help'], text=True, env=env, stderr=subprocess.STDOUT)
        if '--load-threads <n>' not in help_text:
            raise SystemExit(f'{name} compiled help omits --load-threads')
        outputs[name] = {
            'binary': str(binary), 'binary_sha256': sha256(binary),
            'configure_log_sha256': sha256(WORK / f'configure-{name}.log'),
            'build_log_sha256': sha256(WORK / f'build-{name}.log'),
            'help_syntax_probe': '--load-threads 1 --help', 'help_accepts_option': True,
            'linked_libraries': linked_libs(binary, env),
        }
        commands[name] = {'configure_argv': config_cmd, 'build_argv': backend['build_argv']}
    guard(stop, deadline)
    after_store_hashes = verify_stores(spec)
    if before_store_hashes != after_store_hashes:
        raise SystemExit('C6 source stores changed during diagnostic build')
    receipt = {
        'schema': 'pf1.loadthreads.build-receipt.v1',
        'completed_at_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'source': {'commit': spec['base_commit'], 'tree': spec['base_tree'], 'worktree': spec['source_worktree'],
                   'patch_path': spec['source_patch'], 'patch_sha256': spec['source_patch_sha256'],
                   'changed_files': [SOURCE_TU]},
        'build_inputs_sha256': sha256(INPUTS), 'tool_binary_hashes': {k: v['sha256'] for k, v in spec['tools'].items()}, 'tool_versions': tool_versions,
        'base_c6': {k: {'store_root': v['store_root'], 'source_commit': v['source_commit'],
                       'source_tree': v['source_tree'], 'build_identity': v['build_identity'],
                       'build_identity_sha256': v['build_identity_sha256'], 'sha256sums': v['sha256sums'],
                       'sha256sums_sha256': v['sha256sums_sha256'],
                       'configure_argv': v['configure_argv'],
                       'library_and_binary_hashes': before_store_hashes[k],
                       'store_files_checksum_check': 'PASS before and after'} for k, v in spec['backends'].items()},
        'commands': commands, 'output_builds': outputs,
        'build_only': True, 'model_run': False, 'store_modified': False,
    }
    atomic_json(receipt_path, receipt)
    return receipt


def linked_libs(binary, env):
    out = subprocess.check_output(['/usr/bin/ldd', str(binary)], text=True, env=env)
    result = {}
    for line in out.splitlines():
        if '=>' not in line:
            continue
        name, rhs = line.split('=>', 1)
        candidate = rhs.strip().split()[0]
        if candidate.startswith('/') and ('libggml' in name or 'libllama' in name):
            resolved = str(Path(candidate).resolve())
            result[name.strip()] = {'path': candidate, 'resolved_path': resolved, 'sha256': sha256(resolved)}
    if not any('libggml' in name for name in result) or not any('libllama' in name for name in result):
        raise SystemExit(f'could not prove local ggml/llama linked libraries: {out}')
    return result


def main():
    if sha256(INPUTS) != INPUTS_SHA256:
        raise SystemExit('pinned BUILD-INPUTS.json changed')
    spec = json.loads(INPUTS.read_text())
    stop, deadline = filler_state()
    guard(stop, deadline)
    verify_source(spec)
    tool_versions = verify_toolchain(spec)
    store_hashes = verify_stores(spec)
    if os.environ.get('FILLER_DRYRUN') == '1':
        print(json.dumps(dryrun(spec, stop, deadline, tool_versions, store_hashes), indent=2))
    else:
        print(json.dumps(full_build(spec, stop, deadline, tool_versions, store_hashes), indent=2))


def terminated(_signal, _frame):
    raise SystemExit(75)


if __name__ == '__main__':
    signal.signal(signal.SIGTERM, terminated)
    main()
