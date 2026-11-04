#!/usr/bin/env python3
"""Predeclare and collect an architect_critic load-only, sampled VRAM record.

Run from the pinned orchestrator checkout, with that checkout's Python path.
No completion or generation request is ever sent. A sample maximum is not a peak.
"""
import argparse
import hashlib
import http.client
import json
import os
import re
from pathlib import Path
import signal
import sys
import time

import device_identity
import sampler
import server_lifecycle

ENV_PREFIXES = ('LLAMA_', 'GGML_', 'OMP_', 'KMP_', 'HIP_', 'HSA_', 'ROCR_', 'CUDA_', 'LD_')
ENV_NAMES = {'PATH', 'ROCM_PATH'}
ASSET_FLAGS = ('-m', '-md', '--chat-template-file')


def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def selected_env(env):
    return {k: v for k, v in env.items() if k in ENV_NAMES or k.startswith(ENV_PREFIXES)}


def replace_single(argv, flag, value):
    if argv.count(flag) != 1:
        raise ValueError('expected exactly one ' + flag)
    result = list(argv)
    result[result.index(flag) + 1] = str(value)
    return result


def render(port, slots):
    # Native launch consumes an immutable compiler render prepared before publication.
    record = json.loads((Path(__file__).parent / 'preflight.json').read_text())
    for asset in record['assets']:
        if stat_identity(asset['path']) != asset['stat']:
            raise RuntimeError('preflight asset identity changed: ' + asset['path'])
    plan = dict(record['plan'])
    plan['argv'] = replace_single(replace_single(plan['rendered_argv'], '--port', port), '--slot-save-path', slots) + ['-lv', '4']
    if os.environ.get('FILLER_DRYRUN') == '1':
        allowed = sorted(os.sched_getaffinity(0) & set(range(184, 192)))
        if len(allowed) != 4: raise RuntimeError('native smoke affinity is not exactly four granted CPUs')
        plan['prefix'] = replace_single(plan['prefix'], '-c', ','.join(map(str, allowed)))
        plan['qualification_affinity'] = allowed
    else:
        if os.sched_getaffinity(0) != set(range(184,192)):
            raise RuntimeError('full load must retain all eight recipe CPUs')
    return plan, dict(plan['effective_env'])


def stat_identity(path):
    s = os.stat(path)
    return {'dev': s.st_dev, 'ino': s.st_ino, 'size': s.st_size,
            'mtime_ns': s.st_mtime_ns, 'ctime_ns': s.st_ctime_ns}


def proc_identity(pid, birth, plan):
    proc = Path('/proc') / str(pid)
    if sampler.start_ticks(proc) != birth:
        raise RuntimeError('process birth changed')
    actual = (proc / 'cmdline').read_bytes().rstrip(b'\0').split(b'\0')
    actual = [os.fsdecode(x) for x in actual]
    if actual != plan['argv']:
        raise RuntimeError('executed argv differs from rendered argv')
    observed_env = dict(os.fsdecode(x).split('=', 1) for x in (proc / 'environ').read_bytes().split(b'\0') if b'=' in x)
    if selected_env(observed_env) != plan['effective_env']:
        raise RuntimeError('effective environment differs from rendered environment')
    executable = str((proc / 'exe').resolve())
    if executable != str(Path(plan['argv'][0]).resolve()):
        raise RuntimeError('executed binary differs from rendered binary')
    maps = (proc / 'maps').read_text().splitlines()
    libs = sorted({line.split()[-1] for line in maps if line.split() and line.split()[-1].startswith('/')
                   and any(x in Path(line.split()[-1]).name for x in ('libggml', 'libllama', 'libmtmd'))})
    if not any('libggml-hip' in p for p in libs):
        raise RuntimeError('no mapped HIP backend')
    lib_ids = {}
    for path in libs:
        stat = os.stat(path)
        rows = [line.split() for line in maps if line.split() and line.split()[-1] == path]
        if not rows or any(int(row[4]) != stat.st_ino or row[3] != f'{os.major(stat.st_dev):02x}:{os.minor(stat.st_dev):02x}' for row in rows):
            raise RuntimeError('mapped library identity changed: ' + path)
        expected = json.loads((Path(__file__).parent/'preflight.json').read_text())['runtime'].get(path)
        actual_hash = digest(path)
        if expected is None or actual_hash != expected: raise RuntimeError('mapped library differs from approved store: '+path)
        lib_ids[path] = {'sha256': actual_hash, 'device': stat.st_dev, 'inode': stat.st_ino}
    for path, sha in plan['identities'].items():
        entry = next(x for x in json.loads((Path(__file__).parent/'preflight.json').read_text())['assets'] if x['path'] == path)
        if entry['sha256'] != sha or stat_identity(path) != entry['stat']:
            raise RuntimeError('preflight identity changed: ' + path)
    if sampler.start_ticks(proc) != birth:
        raise RuntimeError('process birth changed during identity capture')
    return {'exe': executable, 'argv': actual, 'effective_env': selected_env(observed_env), 'mapped_libraries_sha256': lib_ids}


def owns_listener(port, pid, birth):
    proc=Path('/proc')/str(pid)
    if sampler.start_ticks(proc)!=birth:return False
    sockets=set()
    for fd in (proc/'fd').iterdir():
        try: target=os.readlink(fd)
        except FileNotFoundError:continue
        match=re.fullmatch(r'socket:\[(\d+)\]',target)
        if match:sockets.add(match.group(1))
    local=f'0100007F:{port:04X}'
    rows=(proc/'net/tcp').read_text().splitlines()[1:]
    return any(len(x:=row.split())>=10 and x[1].upper()==local and x[3]=='0A' and x[9] in sockets for row in rows) and sampler.start_ticks(proc)==birth


def owned_health(port, pid, birth):
    return owns_listener(port,pid,birth) and health(port) and owns_listener(port,pid,birth)


def health(port):
    conn = http.client.HTTPConnection('127.0.0.1', port, timeout=1)
    try:
        conn.request('GET', '/health')
        response = conn.getresponse(); response.read()
        return response.status == 200
    except OSError:
        return False
    finally:
        conn.close()


def write_json(path, record):
    with Path(path).open('x') as f:
        json.dump(record, f, indent=2, sort_keys=True); f.write('\n'); f.flush(); os.fsync(f.fileno())


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--output-dir', required=True, type=Path)
    p.add_argument('--port', required=True, type=int)
    p.add_argument('--max-gap-seconds', required=True, type=float, help='predeclared maximum sampling gap')
    p.add_argument('--healthy-samples', required=True, type=int, help='predeclared number of post-health samples')
    p.add_argument('--run-plan-sha256', help='execute previously created plan with this SHA-256 under an existing GPU grant')
    args = p.parse_args()
    if not 1024 <= args.port <= 65535 or args.max_gap_seconds <= 0 or args.healthy_samples < 2:
        p.error('invalid port, maximum gap, or healthy sample count')
    if not args.run_plan_sha256:
        args.output_dir.mkdir(mode=0o700)
        (args.output_dir / 'slots').mkdir(mode=0o700)
    slots = args.output_dir.resolve() / 'slots'
    if not slots.is_dir() or any(slots.iterdir()):
        raise RuntimeError('isolated slot directory missing or not empty')
    plan, env = render(args.port, slots)
    adapter = Path(__file__).parent/'vidya/adapters/kvu16a_native.py'
    plan.update({'belief_adapter_sha256': digest(adapter), 'producer_path': str(Path(__file__).resolve()),
                 'producer_sha256': digest(Path(__file__)), 'producer_files_sha256': {name: digest(Path(__file__).parent/name) for name in ('producer.py','sampler.py','device_identity.py','server_lifecycle.py')}})
    plan.update({'max_gap_seconds': args.max_gap_seconds, 'healthy_samples': args.healthy_samples,
                 'meaning': 'healthy-window coverage; all startup samples and unknowns retained; sampled maximum is not a measured peak'})
    plan_path = args.output_dir / 'plan.json'
    if not args.run_plan_sha256:
        write_json(plan_path, plan)
        return 0
    if digest(plan_path) != args.run_plan_sha256 or json.loads(plan_path.read_text()) != plan:
        raise RuntimeError('predeclared plan hash or rendered launch changed')
    if os.environ.get('FILLER_NEEDGPU') != '1':
        raise RuntimeError('GPU grant missing')
    deadline = int(os.environ['FILLER_DEADLINE']) - 30
    stopfile = Path(os.environ['FILLER_STOPFILE'])
    device = device_identity.discover()
    server = server_lifecycle.Server(plan['prefix'] + plan['argv'], env, args.output_dir / 'server.log', os.environ['FILLER_PIDFILE'])
    state = {'phase': 'startup', 'healthy_at': None, 'started_at': time.monotonic(), 'error': None}
    monitor = None; cleanup = None; identity = None; stop = False
    def halt(*_):
        nonlocal stop
        stop = True
    signal.signal(signal.SIGTERM, halt); signal.signal(signal.SIGINT, halt)
    try:
        pid, birth = server.start()
        hip = str((Path(plan['argv'][0]).parent / 'libggml-hip.so.0').resolve())
        monitor = sampler.Sampler(pid, birth, hip, args.output_dir / 'all-samples.jsonl', startup=True,
                                  phase=lambda: state['phase'], device=device).start()
        while time.time() < deadline and not stop and not stopfile.exists():
            if not server.alive() or monitor.abort.is_set():
                raise RuntimeError(monitor.reason or 'server exited')
            last = monitor.last
            if last and last['hip_resident'] and (last['own_vram_b'] or 0) >= 1024**3 and owned_health(args.port, pid, birth):
                if state['healthy_at'] is None:
                    identity = proc_identity(pid, birth, plan)
                    state['healthy_at'] = time.monotonic(); state['phase'] = 'healthy'
                lines = (args.output_dir / 'all-samples.jsonl').read_text().splitlines()
                healthy_samples = [json.loads(x) for x in lines if json.loads(x).get('phase') == 'healthy']
                if len(healthy_samples) >= args.healthy_samples:
                    end_identity = proc_identity(pid, birth, plan)
                    if identity != end_identity:
                        raise RuntimeError('runtime identity changed during healthy window')
                    break
            time.sleep(0.2)
        else:
            raise RuntimeError('deadline or stop before healthy window completed')
    except BaseException as exc:
        state['error'] = f'{type(exc).__name__}: {exc}'
    finally:
        state['ended_at'] = time.monotonic()
        if monitor and not monitor.stop(): state['error'] = state['error'] or 'sampler did not stop'
        state['ended_at'] = time.monotonic()
        try: cleanup = server.close()
        except BaseException as exc: state['error'] = state['error'] or f'cleanup: {exc}'
    samples_path = args.output_dir / 'all-samples.jsonl'
    records = [json.loads(x) for x in samples_path.read_text().splitlines()] if samples_path.exists() else []
    observed = [x for x in records if x.get('status') == 'observed']
    healthy = [x for x in observed if x['phase'] == 'healthy'][:args.healthy_samples]
    load_bounds = {'started_at':state['started_at'], 'ended_at':state['ended_at']}
    if healthy:
        state['load_started_at'] = state['started_at']; state['load_ended_at'] = state['ended_at']
        state['started_at'] = healthy[0]['sample_start_monotonic_s']
        state['ended_at'] = healthy[-1]['sample_end_monotonic_s']
    window = {'start_monotonic_s':state['started_at'], 'end_monotonic_s':state['ended_at'],
              'selection':'first two post-health original samples; exact rows retained in samples.jsonl',
              'selected_pair':[{'start_monotonic_s':x['sample_start_monotonic_s'], 'end_monotonic_s':x['sample_end_monotonic_s'], 'pid':x['pid'], 'birth_ticks':x['birth_ticks']} for x in healthy]}
    with (args.output_dir/'samples.jsonl').open('x') as f:
        for x in healthy:f.write(json.dumps(x,sort_keys=True)+'\n')
        f.flush();os.fsync(f.fileno())
    begins = [x['sample_start_monotonic_s'] for x in healthy] + [state['ended_at']]
    ends = [state['started_at']] + [x['sample_end_monotonic_s'] for x in healthy]
    gaps = [max(0, b-a) for a,b in zip(ends, begins)]
    missing = [x for x in records if x.get('status') == 'missing']
    complete = not state['error'] and bool(cleanup and cleanup.get('verified_dead')) and not missing and len(healthy) >= args.healthy_samples and all(x['hip_resident'] and (x['own_vram_b'] or 0) >= 1024**3 for x in healthy) and max(gaps) <= args.max_gap_seconds
    healthy_vram = [x['own_vram_b'] for x in healthy if x['own_vram_b'] is not None]
    log = (args.output_dir / 'server.log').read_text(errors='replace') if (args.output_dir / 'server.log').exists() else ''
    kv_matches = re.findall(r'llama_kv_cache: size =\s*([0-9.]+) MiB \(393216 cells,\s*16 layers,\s*4/1 seqs\), K \(q8_0\)', log)
    kv_b = float(kv_matches[0]) * 1024**2 if len(kv_matches) == 1 else None
    if kv_b is None or not healthy_vram:
        complete = False
    result = {'schema': 'kvu16a.load.sampled.v1', 'grant': {k: os.environ.get(k) for k in ('FILLER_NEEDGPU','FILLER_DEADLINE','FILLER_STOPFILE','FILLER_PIDFILE')}, 'state': state, 'device': device, 'runtime_identity': identity,
              'cleanup': cleanup, 'sample_count': len(healthy), 'raw_load_sample_count': len(observed), 'missing': missing, 'sampling_gaps_s': gaps,
              'coverage_scope': 'post-health selected-pair window only; startup unqualified',
              'window': window, 'load_bounds': load_bounds, 'raw_load_samples_path':str(samples_path), 'raw_load_samples_sha256':digest(samples_path),
              'whole_load_coverage_qualified':False, 'peak_claim':False,
              'raw_load_sampling_gaps_s':[max(0,b-a) for a,b in zip([load_bounds['started_at']]+[x['sample_end_monotonic_s'] for x in observed],[x['sample_start_monotonic_s'] for x in observed]+[load_bounds['ended_at']])],
              'startup_unknown_samples': sum(x['phase']=='startup' and x['own_vram_b'] is None for x in observed),
              'coverage_qualified': complete, 'sampled_max_own_vram_b': max(healthy_vram, default=None),
              'target_kv_b_from_log': kv_b,
              'healthy_sampled_max_non_kv_b': max(healthy_vram) - kv_b if healthy_vram and kv_b is not None else None,
              'interpretation': 'sampled maximum only, not a peak; no registry ratification'}
    write_json(args.output_dir / 'result.json', result)
    if complete:
        import importlib.util
        spec = importlib.util.spec_from_file_location('kvu16a_native', adapter)
        capture = importlib.util.module_from_spec(spec);spec.loader.exec_module(capture)
        if capture.record_run(args.output_dir) is None: raise RuntimeError('native belief capture absent')
    return 0 if complete else 75


if __name__ == '__main__':
    try: sys.exit(main())
    except Exception as exc:
        print('load producer refused:', exc, file=sys.stderr); sys.exit(75)
