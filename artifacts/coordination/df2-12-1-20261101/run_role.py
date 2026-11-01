#!/usr/bin/env python3
"""Scratch-only DF2-12.1 role launcher. Canonical filler_run14 owns the grant."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import signal
import subprocess
import sys
import threading
import time
import urllib.request

from recipe_snapshot import ARCHITECT, FRONTDOOR, make
from df2_parity import phase_requests

ROOT = pathlib.Path(__file__).resolve().parent
VRAM = pathlib.Path('/sys/class/drm/card2/device/mem_info_vram_used')
KFD = pathlib.Path('/sys/class/kfd/kfd/proc')


class PartialStop(Exception):
    pass


def deadline_epoch():
    value = os.environ.get('FILLER_DEADLINE', os.environ.get('FILLER_END'))
    try:
        return float(value) if value else None
    except ValueError:
        return dt.datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp()


def signal_stop(_signum, _frame):
    raise PartialStop('captured launcher received termination signal')


def sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def write(path, obj):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2) + '\n')


def source_recipe(shape):
    return FRONTDOOR if shape == 'frontdoor_mtp' else ARCHITECT


def server_env(bin_dir, shape, trace_mode='on'):
    env = dict(os.environ)
    env['LD_LIBRARY_PATH'] = str(bin_dir) + (':/opt/rocm/lib' if shape == 'architect_dflash' else '')
    if trace_mode == 'on':
        env['DF2_NATIVE_TRACE'] = '1'
    else:
        env.pop('DF2_NATIVE_TRACE', None)
    env['OMP_NUM_THREADS'] = '1'
    if shape == 'frontdoor_mtp':
        env['HIP_VISIBLE_DEVICES'] = '-1'
        env['ROCR_VISIBLE_DEVICES'] = ''
        env['GGML_IQK'] = '1'
    return env


def alive_port(port):
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{port}/health', timeout=2) as response:
            return response.status == 200
    except Exception:
        return False


def read_int(path):
    try:
        return int(path.read_text().strip())
    except Exception:
        return None


def kfd_has(pid):
    return (KFD / str(pid)).exists()


def capture_maps(pid, args, shape, out):
    identity = json.loads((pathlib.Path(args.proof_dir) / shape / 'IMAGE-PREFLIGHT.json').read_text())
    expected = {str(pathlib.Path(path).resolve(strict=True)) for path in identity['artifacts']}
    lines = (pathlib.Path('/proc') / str(pid) / 'maps').read_text().splitlines()
    mapped_set = set()
    for line in lines:
        fields = line.split(maxsplit=5)
        if len(fields) != 6 or not fields[-1].startswith('/'):
            continue
        path = pathlib.Path(fields[-1]).resolve()
        if path.name.startswith(('libllama', 'libggml')):
            mapped_set.add(str(path))
    mapped = sorted(mapped_set)
    required = ('libllama-server-impl.so', 'libllama.so', 'libggml.so', 'libggml-base.so')
    if shape == 'architect_dflash':
        required += ('libggml-hip.so',)
    absent = [prefix for prefix in required if not any(pathlib.Path(path).name.startswith(prefix) for path in mapped)]
    foreign = [path for path in mapped if path not in expected]
    proof = {'mapped_paths': mapped, 'expected_artifact_paths': sorted(expected),
             'required_absent': absent, 'foreign_kernel_paths': foreign,
             'pass': not absent and not foreign, 'pid': pid, 'sample_epoch': time.time()}
    write(out / 'SERVER-MAPS.json', proof)
    if not proof['pass']:
        raise RuntimeError(f'actual server DSO maps failed exact image: absent={absent}, foreign={foreign}')


def stop_owned(proc):
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=10)
    if pathlib.Path('/proc').joinpath(str(proc.pid)).exists():
        raise RuntimeError(f'own server PID {proc.pid} survived drain')


def pidfile_update(pid, birth, add):
    value = os.environ.get('FILLER_PIDFILE')
    if not value:
        if os.environ.get('FILLER_QUAL_PHASE') or os.environ.get('FILLER_ID'):
            raise RuntimeError('canonical engine omitted FILLER_PIDFILE')
        return
    path = pathlib.Path(value)
    state_dir = os.environ.get('FILLER_STATE_DIR')
    if not state_dir or not path.is_absolute() or path.parent != pathlib.Path(state_dir):
        raise RuntimeError('PID file is outside canonical engine state directory')
    if add:
        with path.open('a') as stream:
            stream.write(f'{pid} {birth}\n')
            stream.flush()
            os.fsync(stream.fileno())
    else:
        lines = path.read_text().splitlines() if path.exists() else []
        if any(line.split()[:1] == [str(pid)] and line.split() != [str(pid), str(birth)] for line in lines):
            raise RuntimeError('captured PID birth differs from canonical pidfile entry')
        retained = [line for line in lines if line.split() != [str(pid), str(birth)]]
        temporary = path.with_name(path.name + f'.{os.getpid()}.tmp')
        temporary.write_text(''.join(line + '\n' for line in retained))
        temporary.replace(path)


def phase_specs():
    out = []
    for c in (2, 3, 5):
        out.extend((name, c, 1, True) for name in ('baseline-np1', 'repeat-np1'))
        out.extend((name, c, 1, False) for name in ('baseline-off-np1', 'repeat-off-np1',
                                                   'logits-off-np1', 'logits-repeat-off-np1'))
        out.extend((name, c, 4, True) for name in ('joint-np4', 'joint-repeat-np4', 'single-np4'))
        out.extend((name, c, 4, False) for name in ('off-np4', 'off-repeat-np4',
                                                   'logits-off-np4', 'logits-repeat-off-np4'))
    out.extend((name, 2, 1, True) for name in ('lowentropy-np1', 'planted-np1'))
    out.extend((name, 2, 4, True) for name in
               ('lowentropy-np4', 'planted-np4', 'reuse-np4', 'cold-b-np4', 'cold-b-repeat-np4'))
    out.extend((name, 2, 4, False) for name in
               ('lowentropy-off-np4', 'planted-off-np4', 'reuse-off-np4', 'cold-b-off-np4',
                'cold-b-off-repeat-np4', 'cold-b-logits-off-np4', 'cold-b-logits-repeat-off-np4'))
    return out


def validate_exact_image(args, out):
    image = pathlib.Path(args.proof_dir) / args.shape / 'IMAGE-PREFLIGHT.json'
    rollback = pathlib.Path(args.proof_dir) / args.shape / 'ROLLBACK-TEST.json'
    if not image.exists() or not rollback.exists():
        raise RuntimeError('exact-image and dirty-context test proofs required before target request')
    image_record, rollback_record = json.loads(image.read_text()), json.loads(rollback.read_text())
    if not image_record.get('pass') or not rollback_record.get('pass'):
        raise RuntimeError('exact-image or dirty-context test did not PASS')
    if image_record.get('binary') != str(pathlib.Path(args.binary).resolve(strict=True)):
        raise RuntimeError('identity proof is for a different server binary')
    if rollback_record.get('identity_sha256') != sha(image):
        raise RuntimeError('rollback test is not bound to exact identity receipt')
    for path, metadata in image_record.get('artifacts', {}).items():
        if sha(path) != metadata.get('sha256'):
            raise RuntimeError(f'image artifact changed after proof: {path}')
    (out / 'IMAGE-PREFLIGHT.json').write_bytes(image.read_bytes())
    (out / 'ROLLBACK-TEST.json').write_bytes(rollback.read_bytes())


def run_server_phase(args, phase, c, np, spec, out, qualification=False, calibration=False):
    if qualification and args.shape == 'architect_dflash' and os.environ.get('WS58_QUAL_GPU_HELD') != '1':
        raise RuntimeError('GPU target qualification requires canonical keeper gpu-quiet claim')
    if alive_port(args.port):
        raise RuntimeError(f'scratch port {args.port} already in use')
    binary = pathlib.Path(args.binary).resolve(strict=True)
    bin_dir = binary.parent
    slot_dir = out / 'slot-state'
    slot_dir.mkdir(parents=True, exist_ok=False)
    recipe = make(args.shape, source_recipe(args.shape), str(binary), args.port, str(slot_dir),
                  np, 'on' if spec else 'off')
    if calibration:
        expected_threads = '96' if args.shape == 'frontdoor_mtp' else '8'
        scratch_argv = recipe['scratch_argv']
        if ('-t' not in scratch_argv or scratch_argv[scratch_argv.index('-t') + 1] != expected_threads or
            recipe['n_ctx_total'] != (262144 if args.shape == 'frontdoor_mtp' else 393216) or
            recipe['np'] != 4 or recipe['spec'] != 'on'):
            raise RuntimeError('calibration actual argv is not production-thread role recipe')
    write(out / 'ARGV.json', recipe)
    argv = recipe['scratch_argv']
    if args.shape == 'frontdoor_mtp':
        claim = os.environ.get('FILLER_CPUS', '')
        if not qualification and claim != '0-95':
            raise RuntimeError(f'full frontdoor claim must be 0-95 physical; got {claim!r}')
        if not claim:
            raise RuntimeError('FILLER_CPUS required by canonical grant')
        argv = ['numactl', '--interleave=all', '--', 'taskset', '-c', claim] + argv
    else:
        claim = os.environ.get('FILLER_CPUS', '')
        if not claim:
            raise RuntimeError('FILLER_CPUS required by canonical grant')
        argv = ['numactl', '--membind=3', '--', 'taskset', '-c', claim] + argv
    write(out / 'ACTUAL-LAUNCH.json', {'argv': argv, 'env_keys': {
        name: server_env(bin_dir, args.shape, args.trace_mode).get(name) for name in
        ('LD_LIBRARY_PATH', 'DF2_NATIVE_TRACE', 'GGML_IQK', 'HIP_VISIBLE_DEVICES', 'ROCR_VISIBLE_DEVICES')},
        'claimed_cpus': claim, 'utc': dt.datetime.now(dt.timezone.utc).isoformat()})
    server_log = (out / 'server.log').open('wb')
    proc = subprocess.Popen(argv, stdout=server_log, stderr=subprocess.STDOUT,
                            env=server_env(bin_dir, args.shape, args.trace_mode))
    try:
        server_pgid = os.getpgid(proc.pid)
    except ProcessLookupError:
        server_pgid = None
    if server_pgid != os.getpgrp():
        stop_owned(proc)
        server_log.close()
        raise RuntimeError('scratch server escaped canonical engine process group')
    try:
        birth = (pathlib.Path('/proc') / str(proc.pid) / 'stat').read_text().split()[21]
    except FileNotFoundError:
        stop_owned(proc)
        server_log.close()
        raise RuntimeError('scratch server exited before PID birth capture')
    try:
        pidfile_update(proc.pid, birth, True)
    except BaseException:
        stop_owned(proc)
        server_log.close()
        raise
    readings = []
    done = threading.Event()
    def sample():
        while not done.wait(0.5):
            readings.append({'epoch': time.time(), 'vram_used': read_int(VRAM),
                             'own_pid_in_kfd': kfd_has(proc.pid), 'own_pid_alive': proc.poll() is None})
    sampler = threading.Thread(target=sample, daemon=True)
    sampler.start()
    child_rc = None
    child = None
    error = None
    caught = None
    try:
        deadline = time.monotonic() + args.load_timeout
        while time.monotonic() < deadline:
            if deadline_epoch() is not None and time.time() >= deadline_epoch() - 30:
                raise PartialStop('deadline during server load')
            if proc.poll() is not None:
                raise RuntimeError(f'server exited before health, rc={proc.returncode}')
            if alive_port(args.port):
                break
            time.sleep(0.5)
        else:
            raise RuntimeError('server load/health timeout')
        capture_maps(proc.pid, args, args.shape, out)
        if calibration:
            if np != 4 or not spec:
                raise RuntimeError('calibrated-production sample must use exact role np4 spec-on shape')
            command = ['taskset', '-c', claim, sys.executable, str(ROOT / 'calibrate_rate.py'),
                       '--shape', args.shape, '--url', f'http://127.0.0.1:{args.port}', '--manifest', args.manifest,
                       '--server-log', str(out / 'server.log'), '--production-recipe',
                       str(source_recipe(args.shape)), '--image-proof',
                       str(pathlib.Path(args.proof_dir) / args.shape / 'IMAGE-PREFLIGHT.json'),
                       '--argv-record', str(out / 'ARGV.json'), '--out', str(out / 'CALIBRATION-RATE.json')]
        elif qualification:
            command = [sys.executable, str(ROOT / 'qual_fixture.py'), '--mode', 'target',
                       '--url', f'http://127.0.0.1:{args.port}', '--n-ctx-required',
                       str(recipe['n_ctx_total']), '--n-ctx-per-slot-required',
                       str(recipe['n_ctx_per_slot']), '--server-log', str(out / 'server.log'),
                       '--manifest', args.manifest, '--production-recipe', str(source_recipe(args.shape)),
                       '--image-proof', str(pathlib.Path(args.proof_dir) / args.shape / 'IMAGE-PREFLIGHT.json'),
                       '--argv-record', str(out / 'ARGV.json')]
        else:
            command = [sys.executable, str(ROOT / 'df2_parity.py'), 'run', '--manifest', args.manifest,
                       '--manifest-sha', args.manifest_sha, '--url', f'http://127.0.0.1:{args.port}',
                       '--shape', args.shape, '--server-np', str(np),
                       '--spec-enabled', 'true' if spec else 'false',
                       '--server-identity', sha(out / 'ARGV.json'), '--phase', phase,
                       '--concurrency', str(c), '--out', str(out / 'responses')]
        client_env = server_env(bin_dir, args.shape, args.trace_mode)
        if qualification and os.environ.get('FILLER_QUAL_PHASE') == 'cutoff':
            client_env.update(DF2_NATIVE_PID=str(proc.pid), DF2_NATIVE_BIRTH=str(birth))
        with (out / 'client.log').open('wb') as client_log:
            child = subprocess.Popen(command, stdout=client_log, stderr=subprocess.STDOUT,
                                     env=client_env)
            if os.getpgid(child.pid) != os.getpgrp():
                raise RuntimeError('scratch client escaped canonical engine process group')
            try:
                time_left = deadline_epoch() - time.time() - 30 if deadline_epoch() is not None else args.phase_timeout
                child_rc = child.wait(timeout=min(args.phase_timeout, max(0.001, time_left)))
            except subprocess.TimeoutExpired:
                stop_owned(child)
                if deadline_epoch() is not None and time.time() >= deadline_epoch() - 35:
                    raise PartialStop('deadline during request phase')
                raise RuntimeError('client phase timeout')
        if child_rc != 0 and not (qualification and os.environ.get('FILLER_QUAL_PHASE') == 'cutoff' and child_rc == 75):
            raise RuntimeError(f'client phase rc={child_rc}')
    except BaseException as exc:
        error = repr(exc)
        caught = exc
    finally:
        done.set()
        sampler.join(timeout=3)
        cleanup_errors = []
        if child is not None:
            try:
                stop_owned(child)
            except Exception as exc:
                cleanup_errors.append(repr(exc))
        try:
            stop_owned(proc)
        except Exception as exc:
            cleanup_errors.append(repr(exc))
        if not pathlib.Path('/proc').joinpath(str(proc.pid)).exists():
            try:
                pidfile_update(proc.pid, birth, False)
            except Exception as exc:
                cleanup_errors.append(repr(exc))
        server_log.close()
        startup_text = (out / 'server.log').read_text(errors='replace')
        total_context_values = [int(value) for value in re.findall(r'llama_context: n_ctx\s+=\s+(\d+)', startup_text)]
        write(out / 'SERVER-DRAIN.json', {'pid': proc.pid, 'birth': birth, 'rc': proc.returncode,
              'child_rc': child_rc, 'error': error, 'readings': readings,
              'cleanup_errors': cleanup_errors, 'server_pgid': server_pgid,
              'launcher_pgid': os.getpgrp(),
              'n_ctx_total_values': total_context_values,
              'server_log_sha256': sha(out / 'server.log'),
              'own_pid_dead': not pathlib.Path('/proc').joinpath(str(proc.pid)).exists()})
        if cleanup_errors:
            raise RuntimeError('own child/server drain failed: ' + '; '.join(cleanup_errors))
    if error:
        raise caught
    if qualification and os.environ.get('FILLER_QUAL_PHASE') == 'cutoff':
        if child_rc != 75:
            raise RuntimeError('active cutoff did not return partial rc75')
        return
    if args.shape == 'architect_dflash' and not any(x['own_pid_in_kfd'] and (x['vram_used'] or 0) > 0 for x in readings):
        raise RuntimeError('GPU residency unproven during target run')
    if calibration:
        rate_path = out / 'CALIBRATION-RATE.json'
        rate = json.loads(rate_path.read_text())
        if not rate.get('measured_tok_s') or not json.loads((out / 'SERVER-DRAIN.json').read_text())['own_pid_dead']:
            raise RuntimeError('calibration rate or server drain missing')
        capture_dir = out
        rate.update({'raw_rate_result_sha256': sha(rate_path),
                     'first_request_intent_sha256': sha(capture_dir / 'FIRST-REQUEST-INTENT.json'),
                     'first_request_attempt_sha256': sha(capture_dir / 'FIRST-REQUEST-ATTEMPT.json'),
                     'first_request_disposition_sha256': sha(capture_dir / 'FIRST-REQUEST-DISPOSITION.json'),
                     'first_request_wire_status_sha256': sha(capture_dir / 'FIRST-COMPLETION.wire.json'),
                     'first_request_raw_response_sha256': sha(capture_dir / 'FIRST-COMPLETION.response.bin'),
                     'argv_sha256': sha(out / 'ARGV.json'),
                     'actual_launch_sha256': sha(out / 'ACTUAL-LAUNCH.json'),
                     'server_drain_sha256': sha(out / 'SERVER-DRAIN.json'),
                     'server_log_sha256': sha(out / 'server.log'),
                     'image_preflight_sha256': sha(pathlib.Path(args.proof_dir) / args.shape / 'IMAGE-PREFLIGHT.json'),
                     'rollback_test_sha256': sha(pathlib.Path(args.proof_dir) / args.shape / 'ROLLBACK-TEST.json'),
                     'binary_sha256': sha(args.binary)})
        write(out / 'CALIBRATION-RATE-SEALED.json', rate)
        return
    if not qualification:
        trace = subprocess.run([sys.executable, str(ROOT / 'native_trace.py'), '--log', str(out / 'server.log'),
                                '--out', str(out / 'responses/NATIVE-TRACE.json')], check=False)
        belief_dir = out / 'responses' / 'BELIEF-WRITE'
        if belief_dir.exists():
            write(belief_dir / 'NATIVE-BINDING.json', {
                'schema': 'epyc.df2_12_1.native_binding.v1',
                'phase': phase, 'shape': args.shape, 'manifest_sha256': args.manifest_sha,
                'image_preflight_sha256': sha(pathlib.Path(args.proof_dir) / args.shape / 'IMAGE-PREFLIGHT.json'),
                'rollback_test_sha256': sha(pathlib.Path(args.proof_dir) / args.shape / 'ROLLBACK-TEST.json'),
                'argv_sha256': sha(out / 'ARGV.json'),
                'actual_launch_sha256': sha(out / 'ACTUAL-LAUNCH.json'),
                'server_drain_sha256': sha(out / 'SERVER-DRAIN.json'),
                'server_maps_sha256': sha(out / 'SERVER-MAPS.json') if (out / 'SERVER-MAPS.json').exists() else None,
                'server_log_sha256': sha(out / 'server.log'),
                'native_trace_sha256': sha(out / 'responses/NATIVE-TRACE.json') if (out / 'responses/NATIVE-TRACE.json').exists() else None,
                'native_trace_rc': trace.returncode, 'grant_id': os.environ.get('FILLER_ID'),
                'claimed_cpus': claim, 'server_pid': proc.pid, 'server_birth': birth,
                'server_pgid': server_pgid,
                'server_drain_pass': json.loads((out / 'SERVER-DRAIN.json').read_text())['own_pid_dead'],
                'gpu_residency_sampled': any(x['own_pid_in_kfd'] and (x['vram_used'] or 0) > 0 for x in readings)})
        if phase in ('joint-np4', 'reuse-np4', 'lowentropy-np4', 'planted-np4') and trace.returncode != 0:
            raise RuntimeError(f'native trace incomplete for {phase}')


def role_closure(args, out, status):
    manifest = json.loads(pathlib.Path(args.manifest).read_text())
    identities = []
    for phase, c, _np, _spec in phase_specs():
        folder = out / f'{phase}-c{c}' / 'responses' / 'BELIEF-WRITE'
        binding = folder / 'NATIVE-BINDING.json'
        for request_id, _prompt in phase_requests(manifest, phase, c):
            record = folder / (request_id + '.json')
            identities.append({'phase': phase, 'c': c, 'request_id': request_id,
                               'status': json.loads(record.read_text()).get('status', 'invalid') if record.exists() else 'missing',
                               'record_sha256': sha(record) if record.exists() else None,
                               'native_binding_sha256': sha(binding) if binding.exists() else None})
    write(out / 'BELIEF-ROLE-CLOSURE.json', {'schema': 'epyc.df2_12_1.role_closure.v1',
          'shape': args.shape, 'manifest_sha256': args.manifest_sha, 'status': status,
          'planned_request_count': len(identities), 'identities': identities,
          'utc': dt.datetime.now(dt.timezone.utc).isoformat()})


def trace_control_pair(args, out):
    if args.trace_mode != 'on':
        raise RuntimeError('trace control pair sets own on/off mode')
    for mode in ('on', 'off'):
        args.trace_mode = mode
        run_server_phase(args, 'baseline-np1', 2, 1, True, out / f'trace-{mode}-np1-c2')
    responses = {}
    for mode in ('on', 'off'):
        folder = out / f'trace-{mode}-np1-c2' / 'responses'
        responses[mode] = {salt: json.loads((folder / f'salt-{salt}.response.json').read_text())
                           for salt in 'AB'}
    tokens_equal = all(responses['on'][salt].get('status') == responses['off'][salt].get('status') == 'ok'
                       and responses['on'][salt].get('tokens') == responses['off'][salt].get('tokens')
                       for salt in 'AB')
    write(out / 'TRACE-ON-OFF-PAIR.json', {'schema': 'epyc.df2_12_1.trace_on_off_pair.v1',
          'scope': 'INSTRUMENTED_FRONTEND_ONLY', 'manifest_sha256': args.manifest_sha,
          'shape': args.shape, 'same_prompt_token_id_parity': tokens_equal,
          'token_sha256': {mode: {salt: hashlib.sha256(json.dumps(responses[mode][salt].get('tokens'),
              separators=(',', ':')).encode()).hexdigest() for salt in 'AB'} for mode in ('on', 'off')},
          'response_record_sha256': {mode: {salt: sha(out / f'trace-{mode}-np1-c2' / 'responses' /
              f'salt-{salt}.response.json') for salt in 'AB'} for mode in ('on', 'off')},
          'utc': dt.datetime.now(dt.timezone.utc).isoformat()})
    if not tokens_equal:
        raise RuntimeError('instrument trace on/off token parity failed')


def main():
    signal.signal(signal.SIGTERM, signal_stop)
    signal.signal(signal.SIGINT, signal_stop)
    ap = argparse.ArgumentParser()
    ap.add_argument('--shape', required=True, choices=['frontdoor_mtp', 'architect_dflash'])
    ap.add_argument('--binary', required=True)
    ap.add_argument('--port', type=int, required=True)
    ap.add_argument('--manifest', default=str(ROOT / 'PROMPTS.json'))
    ap.add_argument('--manifest-sha', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--proof-dir', default=str(ROOT), help='retained exact-image proof directory')
    ap.add_argument('--load-timeout', type=int, default=600)
    ap.add_argument('--phase-timeout', type=int, default=1800)
    ap.add_argument('--calibrate-only', action='store_true',
                    help='one exact role production-thread rate sample under keeper-owned pregrant authority')
    ap.add_argument('--trace-control-pair', action='store_true',
                    help='two np1 same-prompt arms, trace on then off, under owner native control authority')
    ap.add_argument('--trace-mode', choices=('on', 'off'), default='on')
    args = ap.parse_args()
    if args.trace_mode != 'on':
        raise SystemExit('CLI trace-off is reserved for the internally paired control arm')
    if args.manifest_sha != sha(args.manifest):
        raise SystemExit('prompt manifest SHA mismatch before server load')
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    qual_phase = os.environ.get('FILLER_QUAL_PHASE')
    if qual_phase == 'cutoff':
        validate_exact_image(args, out)
        run_server_phase(args, 'qual-target-cutoff', 2, 4, True, out / 'qual-target-cutoff', qualification=True)
        return 75
    if qual_phase == 'normal':
        validate_exact_image(args, out)
        run_server_phase(args, 'qual-target', 2, 4, True, out / 'qual-target', qualification=True)
        return 0
    if qual_phase:
        raise RuntimeError(f'unknown qualification phase {qual_phase}')
    validate_exact_image(args, out)
    if args.trace_control_pair:
        if args.calibrate_only or args.trace_mode != 'on' or not os.environ.get('WS58_TRACE_CONTROL_AUTHORITY'):
            raise RuntimeError('trace control pair needs distinct owner native control authority')
        trace_control_pair(args, out)
        return 0
    if args.calibrate_only:
        if args.trace_mode != 'on':
            raise RuntimeError('production-thread calibration requires trace on')
        expected_cpus = '0-95' if args.shape == 'frontdoor_mtp' else '184-191'
        expected_regions = '0-95' if args.shape == 'frontdoor_mtp' else 'mi210_0'
        if not os.environ.get('FILLER_ID') or os.environ.get('FILLER_CPUS') != expected_cpus:
            raise RuntimeError('calibration needs keeper-owned role production-thread claim wiring')
        if args.shape == 'architect_dflash' and os.environ.get('WS58_CALIBRATION_GPU_HELD') != '1':
            raise RuntimeError('architect calibration requires keeper-owned GPU quiet claim marker')
        authority_path = os.environ.get('WS58_CALIBRATION_AUTHORITY')
        if not authority_path:
            raise RuntimeError('keeper-owned pregrant calibration authority absent')
        authority = json.loads(pathlib.Path(authority_path).read_text())
        if (authority.get('kind') != 'ws58.pregrant.calibration.v1' or
            authority.get('id') != os.environ['FILLER_ID'] or
            authority.get('regions') != expected_regions or
            authority.get('host_cpus') != expected_cpus or
            authority.get('manifest_sha256') != args.manifest_sha or
            authority.get('binary_sha256') != sha(args.binary) or
            not float(authority.get('start_epoch', 0)) <= time.time() < float(authority.get('end_epoch', 0))):
            raise RuntimeError('keeper pregrant calibration authority does not match image/manifest/window')
        write(out / 'CALIBRATION-AUTHORITY-SNAPSHOT.json', {'path': str(pathlib.Path(authority_path).resolve()),
              'sha256': sha(authority_path), 'authority': authority})
        os.environ['FILLER_DEADLINE'] = str(authority['end_epoch'])
        run_server_phase(args, 'calibration-np4', 1, 4, True, out / 'calibration-np4', calibration=True)
        return 0
    try:
        for phase, c, np, spec in phase_specs():
            if deadline_epoch() is not None and time.time() >= deadline_epoch() - 30:
                raise PartialStop('deadline before next phase')
            run_server_phase(args, phase, c, np, spec, out / f'{phase}-c{c}')
    except PartialStop as exc:
        write(out / 'PARTIAL.json', {'partial': True, 'reason': str(exc), 'shape': args.shape,
              'completed_phase_count': sum((out / f'{name}-c{count}' / 'responses' / 'TERMINAL.json').exists()
                  for name, count, _np, _spec in phase_specs()),
              'utc': dt.datetime.now(dt.timezone.utc).isoformat()})
        role_closure(args, out, 'PARTIAL')
        return 75
    except BaseException:
        role_closure(args, out, 'FAILED')
        raise
    role_closure(args, out, 'COMPLETE')
    write(out / 'TERMINAL.json', {'schema': 'epyc.df2_12_1.role_terminal.v1', 'shape': args.shape,
          'manifest_sha256': args.manifest_sha, 'phases': len(phase_specs()),
          'state': 'COMPLETE', 'utc': dt.datetime.now(dt.timezone.utc).isoformat()})
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
