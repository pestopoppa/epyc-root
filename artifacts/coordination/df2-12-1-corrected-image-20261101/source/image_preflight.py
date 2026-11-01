#!/usr/bin/env python3
"""Exact-image DF2 preflight. Native test requires an admitted resource scope."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import signal
import subprocess
import threading
import time


def digest(path):
    hasher = hashlib.sha256()
    with pathlib.Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            hasher.update(block)
    return hasher.hexdigest()


def command(argv, env=None, timeout=30, native=False, native_receipt=None):
    launched = time.time()
    proc = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, env=env, start_new_session=not native)
    if native and os.getpgid(proc.pid) != os.getpgrp():
        proc.terminate()
        proc.wait(timeout=5)
        raise RuntimeError('native test escaped canonical owned process group')
    birth = int((pathlib.Path('/proc') / str(proc.pid) / 'stat').read_text().rsplit(') ', 1)[1].split()[19])
    group = os.getpgid(proc.pid)
    observed_cpus = sorted(os.sched_getaffinity(proc.pid))
    peak_rss = 0
    kfd_seen = False
    peak_vram_used = 0
    mapped_libraries = set()
    monitoring = threading.Event()
    def sample_native():
        nonlocal peak_rss, kfd_seen, peak_vram_used
        while not monitoring.wait(.1):
            try:
                peak_rss = max(peak_rss, int((pathlib.Path('/proc') / str(proc.pid) / 'statm').read_text().split()[1]) * os.sysconf('SC_PAGE_SIZE'))
                kfd_seen |= (pathlib.Path('/sys/class/kfd/kfd/proc') / str(proc.pid)).exists()
                vram_file = pathlib.Path('/sys/class/drm/card2/device/mem_info_vram_used')
                if vram_file.exists():
                    peak_vram_used = max(peak_vram_used, int(vram_file.read_text().strip()))
                for line in (pathlib.Path('/proc') / str(proc.pid) / 'maps').read_text().splitlines():
                    path = line.rsplit(' ', 1)[-1]
                    if path.startswith('/') and ('libllama' in path or 'libggml' in path):
                        mapped_libraries.add(str(pathlib.Path(path).resolve()))
            except (FileNotFoundError, ProcessLookupError, ValueError):
                pass
    monitor = threading.Thread(target=sample_native, daemon=True) if native else None
    pidfile = os.environ.get('FILLER_PIDFILE') if native else None
    if native and os.environ.get('FILLER_ID') and not pidfile:
        proc.terminate()
        proc.wait(timeout=5)
        raise RuntimeError('native test missing canonical PIDFILE')
    if pidfile:
        state = os.environ.get('FILLER_STATE_DIR')
        path = pathlib.Path(pidfile)
        if not state or path.parent != pathlib.Path(state):
            proc.terminate()
            proc.wait(timeout=5)
            raise RuntimeError('native test PIDFILE outside engine state')
        with path.open('a') as stream:
            stream.write(f'{proc.pid} {birth}\n')
            stream.flush()
            os.fsync(stream.fileno())
    if monitor:
        monitor.start()
    try:
        output, _ = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        if native:
            proc.terminate()
        else:
            os.killpg(proc.pid, signal.SIGTERM)
        try:
            output, _ = proc.communicate(timeout=3)
        except subprocess.TimeoutExpired:
            if native:
                proc.kill()
            else:
                os.killpg(proc.pid, signal.SIGKILL)
            output, _ = proc.communicate(timeout=3)
        raise RuntimeError(f'timeout for captured PID {proc.pid}: {output[-1000:]}')
    finally:
        if native and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=3)
        if pidfile and proc.poll() is not None:
            path = pathlib.Path(pidfile)
            lines = path.read_text().splitlines()
            if any(line.split()[:1] == [str(proc.pid)] and line.split() != [str(proc.pid), str(birth)] for line in lines):
                raise RuntimeError('native test PID birth changed in engine PIDFILE')
            temporary = path.with_name(path.name + f'.{os.getpid()}.tmp')
            temporary.write_text(''.join(line + '\n' for line in lines if line.split() != [str(proc.pid), str(birth)]))
            temporary.replace(path)
        if monitor:
            monitoring.set()
            monitor.join(timeout=2)
        if native_receipt:
            pathlib.Path(native_receipt).write_text(json.dumps({
                'pid': proc.pid, 'birth_ticks': birth, 'pgid': group,
                'observed_cpus': observed_cpus, 'peak_rss_bytes': peak_rss,
                'kfd_seen': kfd_seen, 'peak_host_vram_used_bytes': peak_vram_used,
                'launched_epoch': launched,
                'ended_epoch': time.time(), 'returncode': proc.returncode,
                'own_pid_dead': not pathlib.Path('/proc').joinpath(str(proc.pid)).exists(),
                'mapped_llama_ggml_libraries': {path: digest(path) for path in sorted(mapped_libraries)},
                'argv': argv}, indent=2) + '\n')
    if pathlib.Path('/proc').joinpath(str(proc.pid)).exists():
        raise RuntimeError(f'captured PID {proc.pid} still alive')
    return proc.returncode, output


def identity(args):
    binary = pathlib.Path(args.binary).resolve(strict=True)
    test = pathlib.Path(args.test_binary).resolve(strict=True)
    source = pathlib.Path(args.source_root).resolve(strict=True)
    if binary.parent != test.parent:
        raise RuntimeError('server and rollback test must be from exact same image/bin')
    source_sha = command(['git', '-C', str(source), 'rev-parse', 'HEAD'])[1].strip()
    commit_time = int(command(['git', '-C', str(source), 'show', '-s', '--format=%ct', 'HEAD'])[1].strip())
    files = [binary, test]
    for pattern in ('libllama*.so*', 'libggml*.so*'):
        files.extend(binary.parent.glob(pattern))
    files = list(dict.fromkeys(p.resolve(strict=True) for p in files))
    artifacts = {}
    for file in sorted(files):
        artifacts[str(file)] = {'sha256': digest(file), 'mtime_ns': file.stat().st_mtime_ns,
                                'size': file.stat().st_size}
    server_impl = binary.parent / 'libllama-server-impl.so'
    server_mtime = min(binary.stat().st_mtime, server_impl.stat().st_mtime)
    fresh = server_mtime >= commit_time and test.stat().st_mtime >= commit_time
    rc, version = command([str(binary), '--version'], env={**os.environ, 'LD_LIBRARY_PATH': args.ld_library_path}, timeout=20)
    rc_strings, symbols = command(['strings', str(test)], timeout=20)
    dirty_symbol = rc_strings == 0 and 'dirty-ctx logits mismatch' in symbols
    trace_symbol = 'DF2_NATIVE_ROUND_V1' in command(['strings', str(server_impl)], timeout=20)[1]
    linkage = pathlib.Path(args.linkage_verifier)
    # Store images live outside their source tree; the verifier's second argument
    # is the expected library directory, not the source checkout.
    link_rc, link_text = command([str(linkage), str(binary), str(binary.parent)],
                                 env={**os.environ, 'LD_LIBRARY_PATH': args.ld_library_path}, timeout=60)
    build_receipt_path = pathlib.Path(args.corrected_build_receipt).resolve(strict=True)
    build_receipt = json.loads(build_receipt_path.read_text())
    corrected_ok = (build_receipt.get('base_source_commit') == source_sha and
                    build_receipt.get('server_binary') == str(binary) and
                    build_receipt.get('test_binary') == str(test) and
                    build_receipt.get('test_binary_sha256') == digest(test) and
                    build_receipt.get('server_impl_sha256') == digest(server_impl) and
                    build_receipt.get('original_test_source_sha256') == digest(source / 'tests/test-recurrent-state-rollback.cpp') and
                    build_receipt.get('corrected_test_source_sha256') == digest(build_receipt['corrected_test_source']) and
                    build_receipt.get('test_patch_sha256') == digest(build_receipt['test_patch']) and
                    all(digest(path) == checksum for path, checksum in build_receipt['frozen_inputs_sha256'].items()))
    result = {'schema': 'epyc.df2_12_1.image_preflight.v1', 'binary': str(binary),
              'test_binary': str(test), 'source_root': str(source), 'source_sha': source_sha,
              'source_commit_epoch': commit_time, 'artifacts': artifacts,
              'binary_mtime_after_commit': fresh, 'version_rc': rc, 'version': version,
              'dirty_context_test_symbol': dirty_symbol, 'native_round_trace_symbol': trace_symbol,
              'linkage_rc': link_rc, 'linkage_output': link_text,
              'ld_library_path': args.ld_library_path, 'utc': dt.datetime.now(dt.timezone.utc).isoformat(),
              'corrected_test_binding': {
                  'pass': corrected_ok, 'build_receipt_path': str(build_receipt_path),
                  'build_receipt_sha256': digest(build_receipt_path),
                  'base_source_commit': source_sha,
                  'original_test_source_sha256': build_receipt['original_test_source_sha256'],
                  'corrected_test_source_path': build_receipt['corrected_test_source'],
                  'corrected_test_source_sha256': build_receipt['corrected_test_source_sha256'],
                  'test_patch_path': build_receipt['test_patch'],
                  'test_patch_sha256': build_receipt['test_patch_sha256'],
                  'corrected_test_binary_sha256': build_receipt['test_binary_sha256']},
              'pass': bool(fresh and rc == 0 and dirty_symbol and trace_symbol and link_rc == 0 and corrected_ok)}
    pathlib.Path(args.out).write_text(json.dumps(result, indent=2) + '\n')
    return 0 if result['pass'] else 2


def test(args):
    proof = json.loads(pathlib.Path(args.identity).read_text())
    if not proof.get('pass') or proof['test_binary'] != str(pathlib.Path(args.test_binary).resolve(strict=True)):
        raise RuntimeError('identity preflight must PASS for exact test image')
    binding = proof.get('corrected_test_binding', {})
    if (not binding.get('pass') or
        digest(binding['build_receipt_path']) != binding['build_receipt_sha256'] or
        digest(binding['corrected_test_source_path']) != binding['corrected_test_source_sha256'] or
        digest(binding['test_patch_path']) != binding['test_patch_sha256'] or
        digest(args.test_binary) != binding['corrected_test_binary_sha256']):
        raise RuntimeError('corrected test source/build/patch/image binding drifted')
    model = pathlib.Path(args.hybrid_model).resolve(strict=True)
    model_sha = digest(model)
    if model_sha != args.hybrid_model_sha:
        raise RuntimeError('target hybrid GGUF changed before rollback test')
    if args.backend not in pathlib.Path(proof['binary']).parts:
        raise RuntimeError('rollback backend differs from exact instrumented image')
    started = time.time()
    env = {**os.environ, 'LD_LIBRARY_PATH': args.ld_library_path}
    rc, output = command([str(args.test_binary), '--model', str(model), '--ctx-size', '1024',
                          '--batch-size', '128', '--ubatch-size', '128', '--n-gpu-layers',
                          '99' if args.backend == 'gpu' else '0'], env=env, timeout=args.timeout,
                         native=True, native_receipt=str(args.out) + '.process.json')
    process = json.loads(pathlib.Path(str(args.out) + '.process.json').read_text())
    dirty_reached = any(marker in output for marker in (
        'dirty-ctx logits mismatch', 'dirty replay failed', 'missing dirty logits',
        'recurrent rollback checkpoint restored successfully'))
    passed = (rc == 0 and 'recurrent rollback checkpoint restored successfully' in output
              and 'skipping' not in output.lower() and 'dirty-ctx logits mismatch' not in output)
    if args.backend == 'gpu':
        actual_maps = process['mapped_llama_ggml_libraries']
        exact_maps = bool(actual_maps) and all(
            path in proof['artifacts'] and proof['artifacts'][path]['sha256'] == checksum
            for path, checksum in actual_maps.items())
        hip_mapped = any(pathlib.Path(path).name.startswith('libggml-hip.so')
                         for path in actual_maps)
        passed = (passed and process['kfd_seen'] and
                  process['peak_host_vram_used_bytes'] > 0 and
                  process['own_pid_dead'] and exact_maps and hip_mapped)
    result = {'schema': 'epyc.df2_12_1.rollback_test.v1', 'identity_sha256': digest(args.identity),
              'test_binary_sha256': digest(args.test_binary), 'hybrid_model': str(model),
              'hybrid_model_size': model.stat().st_size, 'hybrid_model_sha256': model_sha,
              'rc': rc, 'output': output,
              'wall_s': time.time() - started, 'dirty_context_reached': dirty_reached,
              'pass': passed, 'utc': dt.datetime.now(dt.timezone.utc).isoformat()}
    result['native_process_receipt_sha256'] = digest(str(args.out) + '.process.json')
    pathlib.Path(args.out).write_text(json.dumps(result, indent=2) + '\n')
    return 0 if passed else 2


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='mode', required=True)
    ident = sub.add_parser('identity')
    ident.add_argument('--binary', required=True)
    ident.add_argument('--test-binary', required=True)
    ident.add_argument('--source-root', required=True)
    ident.add_argument('--ld-library-path', required=True)
    ident.add_argument('--linkage-verifier', required=True)
    ident.add_argument('--corrected-build-receipt', required=True)
    ident.add_argument('--out', required=True)
    check = sub.add_parser('test')
    check.add_argument('--identity', required=True)
    check.add_argument('--test-binary', required=True)
    check.add_argument('--backend', choices=('cpu', 'gpu'), required=True)
    check.add_argument('--hybrid-model', required=True)
    check.add_argument('--hybrid-model-sha', required=True)
    check.add_argument('--ld-library-path', required=True)
    check.add_argument('--timeout', type=int, default=900)
    check.add_argument('--out', required=True)
    args = parser.parse_args()
    return identity(args) if args.mode == 'identity' else test(args)


if __name__ == '__main__':
    raise SystemExit(main())
