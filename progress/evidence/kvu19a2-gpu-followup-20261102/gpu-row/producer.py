#!/usr/bin/env python3
"""Source-pinned KVU-19a-2 repeatability capture; no inference or model load."""
import ctypes
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time
import tempfile

import types
# Compile the checked source bytes directly; stale .pyc files cannot replace it.
device_identity = types.ModuleType('device_identity')
_device_source = Path(__file__).with_name('device_identity.py')
exec(compile(_device_source.read_bytes(), str(_device_source), 'exec'), device_identity.__dict__)

HERE = Path(__file__).resolve().parent
EVIDENCE = HERE
OUT = Path('/mnt/raid0/llm/tmp/kvu/kvu19a2-gpu-repeat-20261104')
ASSETS = HERE / 'assets.json'
CASES = EVIDENCE / 'historical/cases.json'
LINKAGE = HERE / 'verify_ggml_linkage.sh'
LINKAGE_SHA = '57585b405f2d7c6062db2db7786c594d4c428f6952bd27db5a86c0d999cffe33'
CAPTURE_RESULT_SHA = 'c7214d22e185e0be68c1411c97d4426d28ee6837437591fcc5db7c5e1292f82f'
EXPECTED_BYTES = {78: 131072, 79: 8388608, 80: 65536}
GIB = 1024 ** 3


class Refusal(RuntimeError):
    pass


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def file_record(path):
    p = Path(path)
    st = p.lstat()
    if not p.is_file() or p.is_symlink():
        raise Refusal(f'not a regular non-symlink file: {p}')
    return {'path': str(p), 'size': st.st_size, 'sha256': sha256(p)}


def validate_stdout(text, case_id):
    if re.search(rf'^case\s+{case_id}\s+unsupported\b', text, re.M):
        raise Refusal(f'case {case_id} unsupported by ROCm0')
    hits = re.findall(r'^case\s+\d+\b.*$', text, re.M)
    if hits and not re.match(rf'^case\s+{case_id}\b', hits[0]):
        raise Refusal('unexpected case ID in stdout')
    if len(hits) != 1 or 'unsupported' in hits[0]:
        raise Refusal(f'expected exactly one supported stdout result for case {case_id}')
    if not re.search(r'\bhash=[0-9a-f]{16}\b', hits[0]) or not re.search(r'\bnan=0\b', hits[0]):
        raise Refusal(f'case {case_id} stdout lacks output hash or reports NaN')
    cases = json.loads(CASES.read_text())['cases']
    case = next(c for c in cases if c['id'] == case_id)
    fields = re.findall(r'(\w+)=([^\s]+)', hits[0])
    values = dict(fields)
    expected = {'hs': f"{case['hsk']}/{case['hsv']}", 'nh': str(case['nh']), 'nr2': str(case['nr2']), 'kv': str(case['kv']), 'nb': str(case['nb']), 'nseq': str(case['nseq']), 'run': str(case['run']), 'free': str(case['free']), 'type': case['type']}
    if any(values.get(k) != v for k, v in expected.items()) or len(fields) != len(values):
        raise Refusal('stdout case dimensions/recipe mismatch')
    if float(values.get('bias', 'nan')) != case['bias'] or float(values.get('cap', 'nan')) != case['softcap']:
        raise Refusal('stdout bias/cap mismatch')
    return hits[0]


def summarize_hashes(hashes, target=5):
    if any(h != hashes[0] for h in hashes[1:]):
        return 'observed_mismatch'
    if len(hashes) == target:
        return 'no_mismatch_observed_in_five'
    return 'incomplete'


def birth_ticks(pid):
    s = (Path('/proc') / str(pid) / 'stat').read_text()
    return int(s[s.rfind(')') + 2:].split()[19])


def proc_group_members(pgid):
    members = []
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():
            continue
        try:
            rest = (p / 'stat').read_text().split(')', 1)[1].split()
            state, pgrp = rest[0], int(rest[2])
            if pgrp == pgid and state != 'Z':
                members.append(int(p.name))
        except (FileNotFoundError, ProcessLookupError, IndexError, ValueError):
            continue
    return members


def terminate_owned(proc, birth, timeout=5):
    """Signal only this Popen-created session/process group, then verify drain."""
    if proc.poll() is None:
        try:
            if birth_ticks(proc.pid) != birth:
                raise Refusal('captured child PID birth identity changed')
            os.killpg(proc.pid, signal.SIGTERM)
        except (ProcessLookupError, FileNotFoundError):
            pass
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        try:
            proc.wait(timeout=0.05)
        except subprocess.TimeoutExpired:
            pass
        if not proc_group_members(proc.pid):
            break
    if proc_group_members(proc.pid):
        os.killpg(proc.pid, signal.SIGKILL)
        end = time.monotonic() + timeout
        while time.monotonic() < end and proc_group_members(proc.pid):
            time.sleep(0.05)
    try:
        proc.wait(timeout=1)
    except subprocess.TimeoutExpired as e:
        raise Refusal('captured child did not reap') from e
    if proc_group_members(proc.pid):
        raise Refusal('captured child process group did not drain')
    if Path('/proc', str(proc.pid)).exists():
        try:
            if birth_ticks(proc.pid) == birth:
                raise Refusal('captured child PID remains alive after cleanup')
        except FileNotFoundError:
            pass
    return {'pid': proc.pid, 'birth_ticks': birth, 'verified_dead': True}


def child_setup(parent_pid):
    # Linux PR_SET_PDEATHSIG: child receives KILL if its owning producer dies.
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(1, signal.SIGKILL, 0, 0, 0) != 0 or os.getppid() != parent_pid:
        os._exit(127)


def maps_proof(pid, birth, libdir, expected):
    if birth_ticks(pid) != birth:
        raise Refusal('captured process PID was reused')
    paths = set()
    for line in (Path('/proc') / str(pid) / 'maps').read_text().splitlines():
        fields = line.split()
        if fields and fields[-1].startswith('/'):
            p = fields[-1].removesuffix(' (deleted)')
            try:
                paths.add(str(Path(p).resolve()))
            except FileNotFoundError:
                continue
    wanted = {name: str((libdir / name).resolve(strict=True)) for name in expected}
    loaded = {name: path in paths for name, path in wanted.items()}
    return loaded


def read_kfd(pid, birth, device, libdir, expected):
    mapped = maps_proof(pid, birth, libdir, expected)
    device_identity.revalidate(device)
    d = Path('/sys/class/kfd/kfd/proc') / str(pid)
    target = d / f"vram_{device['gpu_id']}"
    own = int(target.read_text().strip()) if target.is_file() else 0
    for other in d.glob('vram_*'):
        if other != target and int(other.read_text().strip()) > 0:
            raise Refusal('captured process has VRAM on a non-target KFD device')
    card = int(Path(device['card_vram_path']).read_text().strip())
    device_identity.revalidate(device)
    if birth_ticks(pid) != birth:
        raise Refusal('captured process identity changed during KFD sample')
    return {'t_monotonic': time.monotonic(), 'pid': pid, 'birth_ticks': birth,
            'gpu_id': device['gpu_id'], 'gpu_bdf': device['bdf'],
            'own_vram_b': own, 'card_vram_b': card, 'mapped_libraries': mapped}


def load_assets():
    assets = json.loads(ASSETS.read_text())
    cap = json.loads((HERE / 'capture-build/RESULT.json').read_text())
    verdict = json.loads((HERE / 'capture-build/verdict.json').read_text())
    if sha256(HERE / 'capture-build/RESULT.json') != CAPTURE_RESULT_SHA:
        raise Refusal('capture build native result changed')
    if cap.get('status') != 'built' or cap.get('mode') != 'qualification':
        raise Refusal('capture harness receipt is not its recorded qualification build')
    if cap.get('binary_sha256') != assets['harness_sha256'] or cap.get('source_sha256') != assets['capture_build']['harness_source_sha256']:
        raise Refusal('capture harness binary/source receipt mismatch')
    if cap.get('input_catalog_sha256') != assets['capture_build']['input_catalog_sha256']:
        raise Refusal('capture harness input catalog receipt mismatch')
    if verdict.get('row_verdict') != 'inconclusive' or verdict.get('outcome_class') != 'PARTIAL-VERDICT':
        raise Refusal('capture build inconclusive verdict changed')
    if verdict.get('verdict', {}).get('native_result_sha256') != CAPTURE_RESULT_SHA:
        raise Refusal('capture build filed verdict does not bind native result')
    if file_record(assets['harness'])['sha256'] != assets['harness_sha256']:
        raise Refusal('preserved harness digest mismatch')
    inp = HERE / 'capture-inputs/original-inputs.json'
    if sha256(inp) != assets['capture_build']['input_catalog_sha256']:
        raise Refusal('capture build input catalog changed')
    catalog = json.loads(inp.read_text())
    for name, digest in catalog.items():
        # The compiler is represented by its pinned digest in the native receipt;
        # this runtime row rechecks lane/scratch inputs and all selected libraries.
        if name.startswith('/usr/bin/'):
            continue
        local = (HERE / 'capture-inputs' / Path(name).relative_to('/mnt/raid0/llm/tmp/kvu/kvu19a2-capture-build-20261102')) if '/kvu19a2-capture-build-20261102/' in name else HERE / 'artifacts' / Path(name).relative_to('/mnt/raid0/llm/tmp/kvu/kvu19a2-preserved-20261102')
        if sha256(local) != digest:
            raise Refusal(f'capture input changed: {local}')
    pair = json.loads((EVIDENCE / 'historical/source-pair.json').read_text())
    if pair.get('source_commit') != assets['source_pair']['source_commit'] or pair.get('git_tree') != assets['source_pair']['source_tree']:
        raise Refusal('source pair identity mismatch')
    if pair.get('tile_sha256') != assets['source_pair']['tile_sha256']:
        raise Refusal('source pair tile pins mismatch')
    for arm, name in (('base', 'fattn-tile.loop-index.cuh'), ('candidate', 'fattn-tile.branch.cuh')):
        if sha256(EVIDENCE / f'historical/{name}') != assets['source_pair']['tile_sha256'][arm]:
            raise Refusal(f'{arm} preserved source tile mismatch')
    if sha256(EVIDENCE / 'historical/branch-vs-loop-index.patch') != assets['source_pair']['branch_transition_patch_sha256']:
        raise Refusal('branch transition patch changed')
    if sha256(CASES) != assets['case_set_sha256']:
        raise Refusal('historical case set changed')
    for arm, info in assets['arms'].items():
        libdir = Path(info['directory'])
        for name, digest in info['libraries'].items():
            if sha256(libdir / name) != digest:
                raise Refusal(f'{arm} artifact digest mismatch: {name}')
        if sha256(libdir / 'test-backend-ops') != info['test_backend_ops_sha256']:
            raise Refusal(f'{arm} preserved test-backend-ops digest mismatch')
    return assets


def check_linkage(assets, runroot):
    if sha256(LINKAGE) != LINKAGE_SHA:
        raise Refusal('linkage verifier hash mismatch')
    records = {}
    for arm, info in assets['arms'].items():
        env = {'PATH': '/usr/bin:/bin', 'LD_LIBRARY_PATH': info['directory'] + ':/opt/rocm/lib'}
        log = runroot / f'linkage-{arm}.txt'
        with log.open('x') as f:
            p = subprocess.run([str(LINKAGE), assets['harness'], info['directory']],
                               env=env, stdout=f, stderr=subprocess.STDOUT, timeout=90)
        if p.returncode != 0:
            raise Refusal(f'{arm} ggml linkage verifier failed ({p.returncode})')
        records[arm] = file_record(log)
    return records


def deadline_guard(stopfile, deadline):
    if stopfile.exists():
        raise Refusal('STOP file observed')
    if time.time() >= deadline - 15:
        raise Refusal('row deadline reached')


def one_run(assets, case, arm, repeat, device, stopfile, deadline, runroot):
    info = assets['arms'][arm]
    libdir = Path(info['directory'])
    stamp = f"{arm}-case{case['id']}-r{repeat:02d}"
    run = runroot / f"run-{stamp}"
    run.mkdir(mode=0o700, exist_ok=False)
    dump = run / 'raw'
    dump.mkdir(mode=0o700, exist_ok=False)
    stdout_path = run / 'stdout.log'
    sample_path = run / 'residency.jsonl'
    output = dump / f"out_{case['id']:02d}.bin"
    expected_libs = tuple(info['libraries'].keys())
    cmd = [assets['harness'], 'ROCm0', 'exact']
    env = {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8',
           'LD_LIBRARY_PATH': str(libdir) + ':/opt/rocm/lib',
           'GGML_CUDA_FA_MASK_SKIP': '0', 'FA_CASE': str(case['id']),
           'FA_DUMP_DIR': str(dump)}
    deadline_guard(stopfile, deadline)
    with stdout_path.open('x') as out, sample_path.open('x') as samples:
        parent_pid = os.getpid()
        proc = subprocess.Popen(cmd, cwd=run, env=env, stdout=out, stderr=subprocess.STDOUT,
                                start_new_session=True,
                                preexec_fn=lambda ppid=parent_pid: child_setup(ppid))
        birth = None
        proof = []
        cleanup = None
        try:
            birth = birth_ticks(proc.pid)
            pidfile = Path(os.environ['FILLER_PIDFILE'])
            with pidfile.open('a') as registry:
                registry.write(f'{proc.pid} {birth}\n')
                registry.flush()
                os.fsync(registry.fileno())
            while proc.poll() is None:
                deadline_guard(stopfile, deadline)
                try:
                    sample = read_kfd(proc.pid, birth, device, libdir, expected_libs)
                    proof.append(sample)
                    samples.write(json.dumps(sample, sort_keys=True) + '\n')
                    samples.flush()
                    os.fsync(samples.fileno())
                except FileNotFoundError:
                    # Kernel files can be absent until ROCm registers this process.
                    pass
                if proc.poll() is None:
                    time.sleep(0.02)
            rc = proc.wait()
            cleanup = terminate_owned(proc, birth)
        except BaseException:
            if birth is not None:
                cleanup = terminate_owned(proc, birth)
            raise
    for name, digest in info['libraries'].items():
        if sha256(libdir / name) != digest:
            raise Refusal(f'{arm} library changed during case {case["id"]}')
    if sha256(assets['harness']) != assets['harness_sha256']:
        raise Refusal('harness changed during run')
    stdout = stdout_path.read_text(errors='replace')
    case_line = validate_stdout(stdout, case['id'])
    if rc != 0:
        raise Refusal(f'harness exited rc={rc} for {stamp}')
    if not output.is_file() or output.is_symlink():
        raise Refusal(f'missing raw output for {stamp}')
    size = output.stat().st_size
    if size != EXPECTED_BYTES[case['id']]:
        raise Refusal(f'wrong output size for {stamp}: {size}')
    positive = [s for s in proof if s['own_vram_b'] > 0 and
                all(s['mapped_libraries'].values())]
    if not positive:
        raise Refusal(f'no contemporaneous own-PID KFD VRAM and expected HIP/library maps for {stamp}')
    return {'case_id': case['id'], 'arm': arm, 'repeat': repeat,
            'process': cleanup, 'argv': cmd, 'environment': env,
            'parent_death_signal': 'SIGKILL',
            'case_stdout': case_line, 'stdout_sha256': sha256(stdout_path),
            'raw_output': file_record(output), 'sample_count': len(proof),
            'hip_kfd_positive_sample_count': len(positive),
            'residency_log': file_record(sample_path), 'status': 'captured'}


def write_result(path, obj):
    """Durable atomic publication with no replacement of an existing result."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(obj, sort_keys=True, indent=2) + '\n').encode()
    fd, temporary = tempfile.mkstemp(prefix='.' + path.name + '-', suffix='.tmp', dir=path.parent)
    temporary = Path(temporary)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.link(temporary, path)  # atomic and fails if target already exists
        dfd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(dfd)
            temporary.unlink()
            os.fsync(dfd)
        finally:
            os.close(dfd)
    finally:
        temporary.unlink(missing_ok=True)


def validate_cpu_grant(text, qualification):
    if not re.fullmatch(r'[0-9]+(?:-[0-9]+)?(?:,[0-9]+(?:-[0-9]+)?)*', text):
        raise Refusal('missing/invalid actual CPU grant')
    cpus = set()
    for token in text.split(','):
        lo, _, hi = token.partition('-')
        lo, hi = int(lo), int(hi or lo)
        if hi < lo or hi > 191: raise Refusal('invalid CPU grant range')
        cpus.update(range(lo, hi + 1))
    inherited = set(os.sched_getaffinity(0))
    if qualification:
        available = sorted(cpus & inherited)
        if len(available) < 4:
            raise Refusal('GPU smoke needs four CPUs inside both grant and inherited affinity')
        actual = set(available[:4])
        os.sched_setaffinity(0, actual)
        if set(os.sched_getaffinity(0)) != actual:
            raise Refusal('failed to restrict smoke to exactly four granted CPUs')
    else:
        actual = inherited
        if cpus != actual or len(actual) != 8:
            raise Refusal('full affinity must equal the eight CPU grant')
    return {'declared': text, 'inherited_affinity': sorted(inherited),
            'affinity': sorted(actual), 'count': len(actual)}


def new_attempt(qualification):
    parent = OUT / ('smoke-runs' if qualification else 'full-runs')
    parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix='attempt-', dir=parent))


def main():
    if os.environ.get('FILLER_ID') != 'handoff-kvu-kvu19a2-repeatability-20261104':
        raise Refusal('wrong row ID')
    dry = os.environ.get('FILLER_DRYRUN', '0')
    offline = os.environ.get('KVU_OFFLINE_CONTROL', '0') == '1'
    qual = dry == '1' or os.environ.get('KVU_GPU_QUALIFICATION', '0') == '1'
    if dry not in ('0', '1'):
        raise Refusal('invalid dryrun mode')
    if dry == '1':
        target = Path(os.environ['FILLER_DRYRUN_RESULT_PATH'])
    elif qual:
        target = OUT / 'QUALIFICATION.json'
    else:
        target = OUT / 'RESULT.json'
    if offline:
        target = OUT / 'OFFLINE-CONTROL.json'
    if target.exists() or target.is_symlink():
        raise Refusal('result path already exists')
    result = {'schema': 'kvu19a2.gpu-repeatability.v1', 'row_id': os.environ['FILLER_ID'],
              'mode': 'offline_control' if offline else ('qualification' if qual else 'full'),
              'status': 'inconclusive', 'question': 'within-arm repeatability for fixed case inputs',
              'capture_build_limitation': json.loads((HERE / 'capture-build/verdict.json').read_text()),
              'source_pair': json.loads((EVIDENCE / 'historical/source-pair.json').read_text()),
              'runs': [], 'arm_case_summary': {}, 'stop_reason': None}
    runroot = None
    try:
        if not offline:
            runroot = new_attempt(qual)
            result['attempt_root'] = str(runroot)
        assets = load_assets()
        cases_doc = json.loads(CASES.read_text())
        cases = cases_doc['cases'][:1] if qual else cases_doc['cases']
        if offline:
            result.update(status='inconclusive', detail='OFFLINE CONTROL ONLY: custody checked; no GPU child executed; not a qualifying native result')
            write_result(target, result)
            return 1
        if OUT.exists() and target == OUT / 'RESULT.json':
            # Existing row outputs are never overwritten; each run gets a new root.
            if any(OUT.glob('run-*')):
                raise Refusal('scratch run root already contains run directories')
        if os.environ.get('FILLER_NEEDGPU') != '1':
            raise Refusal('GPU grant proof FILLER_NEEDGPU=1 required')
        if not os.environ.get('FILLER_PIDFILE'):
            raise Refusal('captured-child PID registry required')
        result['cpu_grant'] = validate_cpu_grant(os.environ.get('FILLER_CPUS', ''), qual)
        stop = Path(os.environ['FILLER_STOPFILE'])
        deadline = float(os.environ['FILLER_DEADLINE'])
        device = device_identity.discover()
        result['gpu_binding'] = device
        result['linkage_receipts'] = check_linkage(assets, runroot)
        mismatch = False
        for case in cases:
            for arm in ('base', 'candidate'):
                hashes = []
                rows = []
                for repeat in range(1, 2 if qual else 6):
                    deadline_guard(stop, deadline)
                    row = one_run(assets, case, arm, repeat, device, stop, deadline, runroot)
                    result['runs'].append(row)
                    rows.append(row)
                    hashes.append(row['raw_output']['sha256'])
                    state = summarize_hashes(hashes)
                    if state == 'observed_mismatch':
                        mismatch = True
                        break
                result['arm_case_summary'][f'{arm}:{case["id"]}'] = {
                    'status': summarize_hashes(hashes), 'repeats': len(hashes),
                    'output_sha256': hashes, 'scope': 'this arm/case/sample only'}
        result['status'] = 'qualified_gpu_smoke' if qual else ('observed_mismatch' if mismatch else 'completed_sample')
        result['interpretation'] = 'case78 both arms captured with live HIP/KFD proof; no repeatability conclusion from smoke' if qual else ('at least one within-arm case produced different raw outputs under the fixed harness input recipe'
                                    if mismatch else 'no within-arm mismatch observed in five runs for each completed arm/case')
    except BaseException as exc:
        result['status'] = 'inconclusive'
        result['stop_reason'] = f'{type(exc).__name__}: {exc}'
        if isinstance(exc, KeyboardInterrupt):
            result['stop_reason'] = 'producer interrupted'
    if runroot is not None:
        write_result(runroot / 'RESULT.json', result)
    if qual and result['status'] != 'qualified_gpu_smoke':
        return 1
    write_result(target, result)
    return 0 if result['status'] in ('qualified_gpu_smoke', 'completed_sample', 'observed_mismatch') else 75


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as exc:
        print(f'KVU GPU row refused: {exc}', file=sys.stderr)
        sys.exit(1 if os.environ.get('FILLER_DRYRUN') == '1' or os.environ.get('KVU_GPU_QUALIFICATION') == '1' else 75)
