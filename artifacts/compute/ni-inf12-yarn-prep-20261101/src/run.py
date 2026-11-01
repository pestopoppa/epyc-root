#!/usr/bin/env python3
"""YARN-E1-MEM native A0/A1 phase replay, diagnostic only."""
import argparse
import hashlib
import json
import os
import signal
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT_ROOT = Path(os.environ.get('FILLER_RESULTS_DIR', HERE / 'out')).resolve()
ROW_ID = 'codex-ni-yarn-e1-mem-phase-r2-20261101'
MODEL = Path('/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf')
TEMPLATE = Path('/mnt/raid0/llm/models/chat-templates/epyc-qwen3x-v1-terse.jinja')
IMAGES = {'E1': Path('/mnt/raid0/llm/kernels/builds/gpu-20261004-9a3f1392a/bin'),
          'W': Path('/mnt/raid0/llm/kernels/builds/gpu-20261004-b0ba1d427/bin')}
SHIM = HERE / 'helper/libhipmalloc_trace.so'
KFD = Path('/sys/class/kfd/kfd/proc')
VRAM_CEILING = 63.8 * 1024**3
STEPS = [('E1', 'A0', 'low'), ('W', 'A0', 'low'), ('E1', 'A1', 'low'),
         ('W', 'A1', 'low'), ('E1', 'A1', 'high'), ('W', 'A1', 'high')]
PORT = 18437
CHILDREN = []
ACTIVE_STEP = None


def partial(reason):
    done = [list(x) for x in STEPS if (OUT_ROOT / '-'.join(x) / 'complete.json').is_file()]
    write(OUT_ROOT / 'RESULT.json', {'status': 'PARTIAL', 'partial': True,
                                     'reason': reason, 'completed_steps': done,
                                     'active_step': ACTIVE_STEP, 'at': time.time()})


def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(obj, indent=2) + '\n')
    tmp.replace(path)


def file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def stop_child(p):
    if p.poll() is None:
        p.terminate()
        try:
            p.wait(timeout=15)
        except subprocess.TimeoutExpired:
            p.kill()
            p.wait(timeout=15)
    assert p.poll() is not None


def cleanup():
    for p in CHILDREN[::-1]:
        stop_child(p)


def sigterm(_s, _f):
    partial('signal-window-end')
    cleanup()
    raise SystemExit(75)


def health():
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{PORT}/health', timeout=2) as r:
            return r.status == 200
    except Exception:
        return False


def pin():
    assert MODEL.is_file() and TEMPLATE.is_file()
    with MODEL.open('rb') as f:
        edge = f.read(64 * 2**20)
        f.seek(max(0, MODEL.stat().st_size - 64 * 2**20))
        edge += f.read(64 * 2**20)
    return {'model': str(MODEL), 'size': MODEL.stat().st_size,
            'edge_sha256': hashlib.sha256(edge + str(MODEL.stat().st_size).encode()).hexdigest()}


def run_step(image, arm, level, mode, deadline):
    global ACTIVE_STEP
    ACTIVE_STEP = [image, arm, level]
    d = OUT_ROOT / f'{image}-{arm}-{level}'
    d.mkdir(parents=True, exist_ok=True)
    (d / 'slots').mkdir(exist_ok=True)
    bindir = IMAGES[image]
    binary = bindir / 'llama-server'
    assert binary.is_file() and SHIM.is_file()
    commit = {'E1': '9a3f1392a', 'W': 'b0ba1d427'}[image]
    stamp = int(subprocess.check_output(['git', '-C', '/mnt/raid0/llm/llama.cpp',
                                         'show', '-s', '--format=%ct', commit], text=True).strip())
    assert binary.stat().st_mtime >= stamp, 'binary predates source commit'
    assert b'KVU16H_SHIM_LOG' in subprocess.check_output(['strings', str(SHIM)]), 'shim knob absent'
    subprocess.run(['/mnt/raid0/llm/epyc-inference-research/scripts/utils/verify_ggml_linkage.sh',
                    str(binary), str(bindir.parent)], check=True, stdout=(d / 'linkage.txt').open('w'))
    assert not subprocess.check_output(['ss', '-ltnH', f'sport = :{PORT}']).strip(), f'port {PORT} already bound'
    assert not any(x.name.isdigit() for x in KFD.iterdir()), 'GPU has foreign KFD process'
    common = [str(binary), '-m', str(MODEL), '--host', '127.0.0.1', '--port', str(PORT),
              '-np', '1', '-t', '8', '-ub', '2048', '--flash-attn', 'on', '--jinja',
              '-ctk', 'q8_0', '-ctv', 'q8_0', '--no-kv-unified', '--no-mmap', '-ngl', 'all', '--cache-ram', '0',
              '--chat-template-file', str(TEMPLATE), '--device', 'ROCm0',
              '--slot-save-path', str(d / 'slots'), '--verbosity', '4']
    if arm == 'A0':
        common += ['-c', '262144']
    else:
        common += ['-c', '524288', '--rope-scaling', 'yarn', '--rope-scale', '2',
                   '--yarn-orig-ctx', '262144', '--override-kv',
                   'qwen35.context_length=int:524288,qwen35.rope.scaling.type=str:yarn,'
                   'qwen35.rope.scaling.factor=float:2,'
                   'qwen35.rope.scaling.original_context_length=int:262144']
    env = dict(os.environ)
    for key in list(env):
        if key.startswith(('LLAMA_ARG_', 'GGML_CUDA_', 'ROCBLAS_')) or key in ('LD_PRELOAD', 'LD_LIBRARY_PATH'):
            env.pop(key)
    env.update(LD_LIBRARY_PATH=f'{bindir}:/opt/rocm/lib:/usr/lib/llvm-20/lib:/opt/AMD/aocc-compiler-5.0.0/lib',
               HSA_OVERRIDE_CPU_AFFINITY_DEBUG='0', GGML_IQK='1', OMP_NUM_THREADS='1',
               LD_PRELOAD=str(SHIM), KVU16H_SHIM_LOG=str(d / 'hipmalloc.jsonl'))
    log = d / 'server.log'
    with log.open('ab') as fh:
        fh.write(f'=== launch {time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())} {image}-{arm}-{level}\n'.encode())
        fh.flush()
        qualification = os.environ.get('WS58_QUAL') == '1'
        p = subprocess.Popen(['taskset', '-c', os.environ['FILLER_CPUS'], *common], env=env,
                             stdout=fh, stderr=subprocess.STDOUT,
                             start_new_session=not qualification)
        CHILDREN.append(p)
        write(d / 'launch.json', {'argv': common, 'pid': p.pid, 'at': time.time(),
                                  'image': str(bindir), 'model_pin': pin(), 'deadline': deadline})
        sample = subprocess.Popen([sys.executable, str(HERE / 'helper/kfd_sampler.py'),
                                   '--pid', str(p.pid), '--out', str(d / 'kfd.jsonl')],
                                  stdout=(d / 'sampler.log').open('w'), stderr=subprocess.STDOUT)
        CHILDREN.append(sample)
        guard_stop = threading.Event()
        guard_hit = threading.Event()
        def watch_vram():
            while not guard_stop.wait(0.5):
                try:
                    used = sum(int(x.read_text()) for x in (KFD / str(p.pid)).glob('vram_*'))
                except (OSError, ValueError):
                    continue
                if used > VRAM_CEILING:
                    write(d / 'guard.json', {'status': 'VRAM_CEILING', 'own_pid': p.pid,
                                             'bytes': used, 'ceiling_bytes': int(VRAM_CEILING),
                                             'at': time.time()})
                    guard_hit.set()
                    break
        guard_thread = threading.Thread(target=watch_vram, daemon=True)
        guard_thread.start()
        try:
            end_load = min(time.time() + 280, deadline - 30)
            while time.time() < end_load and p.poll() is None and not health():
                time.sleep(2)
            assert health() and (KFD / str(p.pid)).is_dir(), 'native GPU load/residency failed'
            assert not guard_hit.is_set(), 'own VRAM ceiling during load'
            maps = Path(f'/proc/{p.pid}/maps').read_text()
            ggml_paths = sorted({x.split()[-1] for x in maps.splitlines()
                                 if 'libggml' in x and '.so' in x})
            assert ggml_paths and all(str(bindir) in x for x in ggml_paths), 'wrong ggml image'
            proc_stat = Path(f'/proc/{p.pid}/stat').read_text().rsplit(') ', 1)[1].split()
            birth_ticks = int(proc_stat[19])
            write(d / 'runtime-proof.json', {'pid': p.pid, 'birth_ticks': birth_ticks,
                                              'image': image, 'arm': arm, 'level': level,
                                              'ggml_paths': ggml_paths,
                                              'kfd': str(KFD / str(p.pid)),
                                              'binary_mtime': binary.stat().st_mtime,
                                              'source_commit_time': stamp,
                                              'shim_knob_compiled': True})
            if mode == 'smoke':
                body = json.dumps({'prompt': 'Explain one memory allocation in one sentence.', 'n_predict': 8}).encode()
                req = urllib.request.Request(f'http://127.0.0.1:{PORT}/completion', data=body,
                                             headers={'Content-Type': 'application/json'})
                with urllib.request.urlopen(req, timeout=max(1, min(20, deadline-time.time()-25))) as resp:
                    reply = json.load(resp)
                assert reply.get('content'), 'native first response empty'
                assert not guard_hit.is_set(), 'own VRAM ceiling during smoke request'
                write(d / 'smoke-result.json', {'qualification_only': True, 'first_request_ok': True,
                                                 'result_writer_ok': True, 'pid': p.pid, 'image': image,
                                                 'arm': arm, 'level': level, 'at': time.time()})
                return 0
            if time.time() > deadline - 45:
                return 75
            stages = '128k,240k' if level == 'low' else '400k,500k'
            runenv = dict(os.environ, YARN_E1_RESULTS=str(d / 'native'))
            if os.environ.get('FILLER_QUAL_PHASE') in ('normal', 'cutoff'):
                qualification_manifest = json.loads(Path(os.environ['WS58_MANIFEST_PATH']).read_text())
                qualification_recipe_sha = os.environ['WS58_PRODUCTION_RECIPE_SHA256']
                runenv.update(YARN_QUAL_PHASE=os.environ['FILLER_QUAL_PHASE'],
                              YARN_QUAL_IMAGE=image,
                              YARN_QUAL_EVENT_FILE=(os.environ.get('WS58_QUAL_CUTOFF_EVENT') or
                                                    str(d / 'native-first-event.json')),
                              YARN_QUAL_PROOF=os.environ.get('WS58_QUAL_PROOF', ''),
                              YARN_QUAL_FIXTURE=os.environ.get('WS58_QUAL_FIXTURE', ''),
                              YARN_QUAL_NATIVE_PID=str(p.pid),
                              YARN_QUAL_SERVER_LOG=str(log))
            cmd = ['/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python', str(HERE / 'yarn_needle.py'), '--arm', arm,
                   '--i-own-the-window', '--port', str(PORT), '--server-log', str(log),
                   '--suites', 'smoke,needle', '--stages', stages]
            with (d / 'runner.log').open('w') as rf:
                runner = subprocess.Popen(cmd, env=runenv, stdout=rf, stderr=subprocess.STDOUT)
                CHILDREN.append(runner)
                while runner.poll() is None and time.time() < deadline - 25:
                    if (os.environ.get('FILLER_QUAL_PHASE') == 'cutoff' and
                            Path(os.environ.get('FILLER_STOPFILE', '/dev/null')).is_file()):
                        stop_child(runner)
                        write(d / 'partial.json', {'partial': True, 'reason': 'active-qualification-cutoff',
                                                   'unknown_disposition': 'UNKNOWN', 'at': time.time()})
                        return 75
                    if guard_hit.is_set():
                        stop_child(runner)
                        write(d / 'partial.json', {'partial': True, 'reason': 'own-vram-ceiling', 'at': time.time()})
                        return 72
                    time.sleep(1)
                if runner.poll() is None:
                    stop_child(runner)
                    write(d / 'partial.json', {'partial': True, 'reason': 'window-end', 'at': time.time()})
                    return 75
                if runner.returncode:
                    return runner.returncode
            reports = list((d / 'native' / arm).glob('*/report.json'))
            assert reports, 'native result writer missing'
            report = json.loads(max(reports).read_text())
            assert report.get('needle') and not any('aborted' in x for x in report['needle'].values()), 'native chain aborted'
            assert (d / 'kfd.jsonl').is_file() and (d / 'hipmalloc.jsonl').is_file(), 'phase evidence missing'
            subprocess.run([sys.executable, str(HERE / 'analyze_phase.py'), str(d)], check=True,
                           stdout=(d / 'analyze.log').open('w'))
            completion = {'status': 'COMPLETE', 'report': str(max(reports)),
                                         'image': image, 'arm': arm, 'level': level,
                                         'kfd_samples': str(d / 'kfd.jsonl'),
                                         'shim_log': str(d / 'hipmalloc.jsonl'),
                                         'phase_attribution': str(d / 'phase-attribution.json')}
            if os.environ.get('FILLER_QUAL_PHASE') in ('normal', 'cutoff'):
                event_path = d / 'native-first-event.json'
                event = json.loads(event_path.read_text())
                completion.update({
                    'row_id': ROW_ID,
                    'request_manifest_sha256': qualification_manifest['request_manifest_sha256'],
                    'production_recipe_sha256': qualification_recipe_sha,
                    'native_event_path': str(event_path),
                    'native_event_sha256': hashlib.sha256(event_path.read_bytes()).hexdigest(),
                    'native_pid': event.get('native_pid'),
                    'native_birth_ticks': event.get('native_birth_ticks'),
                    'runtime_proof_path': str(d / 'runtime-proof.json'),
                })
            write(d / 'complete.json', completion)
            return 0
        finally:
            guard_stop.set()
            guard_thread.join(timeout=2)
            stop_child(p)
            stop_child(sample)
            assert p.poll() is not None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', choices=['full', 'job'])
    ap.add_argument('--deadline', type=float, default=time.time() + 3600)
    a = ap.parse_args()
    signal.signal(signal.SIGTERM, sigterm)
    if a.mode == 'job':
        phase = os.environ.get('FILLER_QUAL_PHASE')
        if os.environ.get('WS58_QUAL') != '1' or phase not in ('normal', 'cutoff'):
            partial('job-entry-without-keeper-qualification-phase')
            return 70
        if not (os.environ.get('WS58_QUAL_PROOF') and os.environ.get('WS58_MANIFEST_PATH') and
                os.environ.get('WS58_QUAL_FIXTURE') and os.environ.get('WS58_PRODUCTION_RECIPE_SHA256')):
            partial('qualification-proof-plumbing-missing')
            return 70
        manifest = json.loads(Path(os.environ['WS58_MANIFEST_PATH']).read_text())
        recipe_path = Path(manifest.get('production_recipe', {}).get('path', ''))
        recipe = json.loads(recipe_path.read_text())
        fixture_path = Path(os.environ['WS58_QUAL_FIXTURE'])
        request_manifest_path = HERE / 'qualification/request_manifest.json'
        if (manifest.get('id') != ROW_ID or manifest.get('request_manifest_sha256') != file_sha256(request_manifest_path) or
                manifest.get('production_recipe', {}).get('sha256') != os.environ['WS58_PRODUCTION_RECIPE_SHA256'] or
                file_sha256(recipe_path) != os.environ['WS58_PRODUCTION_RECIPE_SHA256'] or
                manifest.get('qual_fixture', {}).get('sha256') != file_sha256(fixture_path)):
            partial('qualification-pins-do-not-match-current-r2-source')
            return 70
        # The qualification work unit is the paired E1/W A1/high group: each
        # image executes the real 400k cache seed and exact maximum 500k request.
        # It does not rerun the six-cell science cohort or declare a verdict.
        deadline = float(os.environ.get('FILLER_DEADLINE', a.deadline))
        work_unit_started = time.monotonic()
        rc = run_step('E1', 'A1', 'high', 'full', deadline)
        if phase == 'normal' and rc == 0:
            rc = run_step('W', 'A1', 'high', 'full', deadline)
        if phase == 'normal' and rc == 0:
            event_path = OUT_ROOT / 'E1-A1-high' / 'native-first-event.json'
            event = json.loads(event_path.read_text())
            result = {'status': 'COMPLETE', 'qualification_only': True,
                      'row_id': ROW_ID,
                      'request_manifest_sha256': manifest['request_manifest_sha256'],
                      'production_recipe_sha256': os.environ['WS58_PRODUCTION_RECIPE_SHA256'],
                      'nonce': os.environ['WS58_QUAL_NONCE'],
                      'work_unit': recipe['qualification_work_unit'],
                      'steps': [['E1', 'A1', 'high'], ['W', 'A1', 'high']],
                      'work_unit_wall_s': time.monotonic() - work_unit_started,
                      'native_first_event_sha256': hashlib.sha256(event_path.read_bytes()).hexdigest()}
            write(OUT_ROOT / 'RESULT.json', result)
            proof = {'id': os.environ['FILLER_ID'], 'nonce': os.environ['WS58_QUAL_NONCE'],
                     'phase': 'normal', 'first_request': event['first_request'],
                     'observed_cpus': sorted(os.sched_getaffinity(0)),
                     'result_writer': {'ok': True, 'result_path': str(OUT_ROOT / 'RESULT.json'),
                                       'sha256': hashlib.sha256((OUT_ROOT / 'RESULT.json').read_bytes()).hexdigest()},
                     'disk': {'job_floor_gib': 150}}
            write(Path(os.environ['WS58_QUAL_PROOF']), proof)
            return 0
        if phase == 'cutoff' and rc == 75:
            event_path = Path(os.environ['WS58_QUAL_CUTOFF_EVENT'])
            event = json.loads(event_path.read_text())
            result = {'status': 'PARTIAL', 'partial': True, 'unknown_disposition': 'UNKNOWN',
                      'row_id': ROW_ID,
                      'request_manifest_sha256': manifest['request_manifest_sha256'],
                      'production_recipe_sha256': os.environ['WS58_PRODUCTION_RECIPE_SHA256'],
                      'nonce': os.environ['WS58_QUAL_NONCE'],
                      'reason': 'keeper-active-cutoff-after-native-first-event'}
            write(OUT_ROOT / 'RESULT.json', result)
            write(Path(os.environ['WS58_QUAL_PROOF']), {
                'id': os.environ['FILLER_ID'], 'nonce': os.environ['WS58_QUAL_NONCE'],
                'phase': 'cutoff', 'partial': True, 'stop_observed': True,
                'unknown_disposition': 'UNKNOWN', 'first_request': event['first_request'],
                'observed_cpus': sorted(os.sched_getaffinity(0)),
                'result_writer': {'ok': True, 'result_path': str(OUT_ROOT / 'RESULT.json'),
                                  'sha256': hashlib.sha256((OUT_ROOT / 'RESULT.json').read_bytes()).hexdigest()},
                'disk': {'job_floor_gib': 150}})
            return 75
        partial(f'qualification-{phase}-did-not-reach-required-boundary-rc-{rc}')
        return 70 if rc != 75 else rc
    if (os.environ.get('FILLER_ID') != ROW_ID or not os.environ.get('FILLER_CPUS') or
            not os.environ.get('FILLER_DEADLINE') or not os.environ.get('FILLER_STOPFILE')):
        partial('full-job-outside-canonical-filler-entry')
        return 70
    manifest_path = os.environ.get('WS58_MANIFEST_PATH')
    recipe_sha = os.environ.get('WS58_PRODUCTION_RECIPE_SHA256')
    if not manifest_path or not recipe_sha:
        partial('production-pins-missing-from-canonical-entry')
        return 70
    manifest = json.loads(Path(manifest_path).read_text())
    recipe = manifest.get('production_recipe', {})
    if (manifest.get('id') != ROW_ID or manifest.get('request_manifest_sha256') !=
            file_sha256(HERE / 'qualification/request_manifest.json') or
            recipe.get('sha256') != recipe_sha or file_sha256(recipe.get('path', '')) != recipe_sha):
        partial('production-pins-do-not-match-current-r2-source')
        return 70
    for image, arm, level in STEPS:
        if (OUT_ROOT / f'{image}-{arm}-{level}' / 'complete.json').is_file():
            continue
        if Path(os.environ.get('FILLER_STOPFILE', '/dev/null')).is_file() or time.time() > a.deadline - 300:
            partial('stop-file-or-window-end-before-step')
            return 75
        rc = run_step(image, arm, level, 'full', a.deadline)
        if rc:
            if rc == 75:
                partial('window-end-in-step')
            return rc
        if time.time() > a.deadline - 300:
            partial('window-end-between-steps')
            return 75
    analysis = {f'{i}-{a}-{l}': json.loads((OUT_ROOT / f'{i}-{a}-{l}' / 'phase-attribution.json').read_text())
                for i, a, l in STEPS}
    comparison = {}
    for arm, level in [('A0', 'low'), ('A1', 'low'), ('A1', 'high')]:
        old = analysis[f'E1-{arm}-{level}']['stages']
        new = analysis[f'W-{arm}-{level}']['stages']
        for stage in sorted(old.keys() & new.keys()):
            a, b = old[stage], new[stage]
            comparison[f'{arm}:{stage}'] = {'E1_peak_gib': a['own_kfd_peak_gib'],
                                            'W_peak_gib': b['own_kfd_peak_gib'],
                                            'W_minus_E1_peak_gib': (b['own_kfd_peak_gib'] - a['own_kfd_peak_gib']
                                                                     if a['own_kfd_peak_gib'] is not None
                                                                     and b['own_kfd_peak_gib'] is not None else None),
                                            'E1_shim_delta_bytes': a['shim_live_delta_bytes'],
                                            'W_shim_delta_bytes': b['shim_live_delta_bytes']}
    write(OUT_ROOT / 'RESULT.json', {'status': 'COMPLETE', 'diagnostic': True,
                                     'row_id': ROW_ID,
                                     'request_manifest_sha256': manifest['request_manifest_sha256'],
                                     'production_recipe_sha256': recipe_sha,
                                     'historical_comparison': True, 'stage_group_reset': True,
                                     'steps': [list(x) for x in STEPS], 'comparison': comparison,
                                     'at': time.time()})
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    finally:
        cleanup()
