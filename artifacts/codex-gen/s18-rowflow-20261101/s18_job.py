#!/usr/bin/env python3
"""S-18 CPU first-start job. The R11 smoke and full cohort share this path."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import signal
import socket
import shlex
import re
import datetime
import subprocess
import sys
import threading
import time
import urllib.request

ROOT = Path(__file__).resolve().parent
RESEARCH = Path('/mnt/raid0/llm/epyc-inference-research')
HARNESS_PATH = ROOT / 'harness.py'
MODEL = Path('/mnt/raid0/llm/models/lmstudio-community/Qwen3-VL-30B-A3B-Instruct-GGUF/Qwen3-VL-30B-A3B-Instruct-Q4_K_M.gguf')
MMPROJ = Path('/mnt/raid0/llm/models/lmstudio-community/Qwen3-VL-30B-A3B-Instruct-GGUF/mmproj-Qwen3-VL-30B-A3B-Instruct-F16.gguf')
SERVER = Path('/mnt/raid0/llm/kernels/production/cpu/llama-server')
LIBPATH = '/mnt/raid0/llm/kernels/production/cpu'
VERIFY = RESEARCH / 'scripts/utils/verify_ggml_linkage.sh'
PORT = 19883
MODEL_SHA = '7bd52989f39ddca3dde36edb902fef72c5fde81e9211ca0f5ceca0119bd16d9c'
MMPROJ_SHA = 'a31d2c298f28735f6d27847851b8e3662ceb29cd6a1e66aa13d54b17f45aefca'


def read_start_ticks(pid: int) -> str:
    fields = Path(f'/proc/{pid}/stat').read_text().split()
    return fields[21]


def file_edge_pin(path: Path) -> dict:
    size = path.stat().st_size
    h = hashlib.sha256()
    with path.open('rb') as source:
        h.update(str(size).encode() + b'\0')
        h.update(source.read(64 * 1024 * 1024))
        source.seek(max(0, size - 64 * 1024 * 1024))
        h.update(source.read(64 * 1024 * 1024))
    return {'size_bytes': size, 'first_last_64m_sha256': h.hexdigest()}


def rss_bytes(pid: int) -> int:
    try:
        for line in Path(f'/proc/{pid}/status').read_text().splitlines():
            if line.startswith('VmRSS:'):
                return int(line.split()[1]) * 1024
    except FileNotFoundError:
        pass
    return 0


def proc_maps(pid: int) -> str:
    return Path(f'/proc/{pid}/maps').read_text(errors='replace')


def process_group_records(pgid: int) -> list[dict]:
    records = []
    for stat in Path('/proc').glob('[0-9]*/stat'):
        try:
            raw = stat.read_text()
            pid_text, rest = raw.split(' (', 1)
            _comm, tail = rest.rsplit(') ', 1)
            fields = tail.split()  # field 3 (state) is index 0
            if int(fields[2]) == pgid:
                records.append({'pid': int(pid_text), 'start_ticks': fields[19]})
        except (FileNotFoundError, ProcessLookupError, ValueError, IndexError):
            continue
    return records


def process_group_rss_and_maps(pgid: int):
    total, chunks, server_found, identities = 0, [], False, []
    for rec in process_group_records(pgid):
        pid = rec['pid']
        try:
            total += rss_bytes(pid)
            chunks.append(proc_maps(pid))
            cmd = Path(f'/proc/{pid}/cmdline').read_bytes().replace(b'\0', b' ').decode(errors='replace')
            if str(SERVER) in cmd:
                server_found = True
                rec['server_cmdline'] = cmd
                rec['exe'] = str(Path(f'/proc/{pid}/exe').resolve())
                if Path(f'/proc/{pid}/exe').resolve() != SERVER.resolve():
                    raise RuntimeError('actual server image mismatch')
                rec['status'] = Path(f'/proc/{pid}/status').read_text()
            identities.append(rec)
        except FileNotFoundError:
            continue
    return total, '\n'.join(chunks), server_found, identities


ADMISSION_CLASS_VALUES = {
    'correctness', 'diagnostic', 'block-correctness',
    'block-timing-pairable', 'block-timing-quiet', 'filler',
}
ADMISSION_CLASSES_ALLOWED = {'correctness', 'diagnostic', 'block-correctness'}


def _manifest_records(flags: Path, rid: str) -> tuple[dict | None, list[dict]]:
    """Load an active manifest and same-ID archived legacy manifests without trusting their class yet."""
    active_path = flags / 'ready' / f'{rid}.json'
    archive_paths = sorted((flags / 'ready').glob(f'legacy-*/{rid}.json'))
    def read(path):
        try:
            record = json.loads(path.read_text())
        except (OSError, ValueError):
            return None
        if not isinstance(record, dict) or record.get('id') != rid:
            return None
        if record.get('schema') not in (None, 'epyc.ready.v2', 'epyc.row.v3'):
            raise RuntimeError(f'unsupported row manifest schema for {rid}: {record.get("schema")}')
        return record
    active = read(active_path) if active_path.is_file() else None
    archived = [r for path in archive_paths if (r := read(path)) is not None]
    if active is None and archived:
        signatures = {tuple(json.dumps(r.get(k), sort_keys=True)
                            for k in ('class', 'admission_class', 'decision_rule', 'owner', 'regions', 'result_path', 'row', 'handoff'))
                      for r in archived}
        if len(signatures) != 1:
            raise RuntimeError(f'conflicting archived row manifests for {rid}')
    return active, archived


def _launcher_identity(path: Path) -> tuple[str, str]:
    """Parse the pinned filler engine's id/resource class without executing the launcher."""
    text = path.read_text(errors='strict')
    assigns = {}
    for m in re.finditer(r'^(?:export\s+)?([A-Za-z_][A-Za-z_0-9]*)=("?)([^\n"]*)\2\s*$', text, re.M):
        assigns[m.group(1)] = m.group(3)
    assigns.setdefault('HERE', str(path.parent))
    def expand(value):
        for _ in range(3):
            value = re.sub(r'\$\{([A-Za-z_][A-Za-z_0-9]*)(?::[-?][^}]*)?\}|\$([A-Za-z_][A-Za-z_0-9]*)',
                           lambda m: assigns.get(m.group(1) or m.group(2), m.group(0)), value)
        return value
    joined = re.sub(r'\\\n', ' ', text)
    line = next((expand(line) for line in joined.splitlines()
                 if re.search(r'filler_run\d+\.sh', expand(line)) and '--id' in expand(line)), None)
    if not line:
        raise RuntimeError(f'launcher has no static filler engine/id invocation: {path}')
    tokens = shlex.split(line, comments=True)
    engine_at = next((i for i, token in enumerate(tokens) if re.search(r'filler_run\d+\.sh$', token)), None)
    if engine_at is None:
        raise RuntimeError(f'launcher engine token missing: {path}')
    identity = {'id': None, 'class': None}
    i = engine_at + 1
    while i < len(tokens):
        if tokens[i] in ('--id', '--class') and i + 1 < len(tokens):
            identity['id' if tokens[i] == '--id' else 'class'] = tokens[i + 1]
            i += 2
        else:
            i += 1
    if not identity['id'] or identity['class'] not in ('cpu', 'gpu', 'cpu+gpu'):
        raise RuntimeError(f'launcher identity/class invalid: {path}')
    return identity['id'], identity['class']


def _verify_manifest_launcher(flags: Path, rid: str, manifest: dict) -> tuple[str, str]:
    launcher = manifest.get('launcher')
    if not isinstance(launcher, dict) or not launcher.get('path') or not launcher.get('sha256'):
        raise RuntimeError(f'row manifest has no sealed launcher: {rid}')
    path = Path(launcher['path'])
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != launcher['sha256']:
        raise RuntimeError(f'launcher source hash mismatch for {rid}: {path}')
    parsed_id, resource_class = _launcher_identity(path)
    if parsed_id != rid or manifest.get('id') != rid:
        raise RuntimeError(f'launcher/manifest id mismatch for {rid}: {parsed_id}')
    lane = manifest.get('lane')
    regions = str(manifest.get('regions') or '')
    expected_lane = lane or ('gpu' if 'mi210' in regions else 'cpu')
    if (expected_lane == 'cpu' and resource_class != 'cpu') or (expected_lane == 'gpu' and resource_class not in ('gpu', 'cpu+gpu')):
        raise RuntimeError(f'launcher resource class disagrees with row lane for {rid}')
    return str(path), resource_class


def _verified_archived_class(flags: Path, rid: str, active: dict, archived: list[dict]) -> str | None:
    """Recover a legacy explicit class only when its sealed launcher is the exact source of the active v3 launcher."""
    if active.get('schema') != 'epyc.row.v3' or active.get('admission_class') is not None:
        return None
    candidates = [m for m in archived if m.get('class') or m.get('admission_class')]
    if not candidates:
        return None
    keys = ('class', 'admission_class', 'decision_rule', 'owner', 'regions', 'result_path')
    signatures = {tuple(json.dumps(m.get(k), sort_keys=True) for k in keys) for m in candidates}
    if len(signatures) != 1:
        raise RuntimeError(f'conflicting archived class/source records for {rid}')
    legacy = candidates[0]
    for k in ('id', 'owner', 'regions', 'result_path', 'decision_rule'):
        if active.get(k) != legacy.get(k):
            raise RuntimeError(f'active/legacy row identity mismatch for {rid}: {k}')
    old_path, old_class = _verify_manifest_launcher(flags, rid, legacy)
    new_path, new_class = _verify_manifest_launcher(flags, rid, active)
    if old_class != new_class:
        raise RuntimeError(f'legacy/current launcher resource class changed for {rid}')
    old_text = Path(old_path).read_text(errors='strict')
    canonical_engine = str(flags / 'bin' / 'rowflow' / 'filler_run15.sh')
    expected_text = re.sub(r'[A-Za-z0-9_$./{}:-]*filler_run\d+\.sh', canonical_engine, old_text)
    if Path(new_path).read_text(errors='strict') != expected_text:
        raise RuntimeError(f'active launcher is not the sealed legacy-to-v3 migration for {rid}')
    row_class = legacy.get('admission_class') or legacy.get('class')
    if row_class not in ADMISSION_CLASS_VALUES:
        raise RuntimeError(f'legacy admission class invalid for {rid}: {row_class!r}')
    return row_class


def _validate_synthetic_regions(manifest: dict, rid: str, record: dict) -> None:
    """Bind the dry-run grant's concrete region claim to its published row policy."""
    policy = manifest.get('regions')
    actual = record.get('regions')
    if not isinstance(policy, str) or not policy or not isinstance(actual, str) or not actual:
        raise RuntimeError(f'synthetic grant/row has no regions policy: {rid}')
    if policy == 'any-cpu-quarter' or policy.startswith('any-of'):
        if policy == 'any-cpu-quarter':
            allowed_quarters = {'q0', 'q1', 'q2', 'q3'}
        else:
            allowed_quarters = {x.strip() for x in policy[len('any-of'):].split(',') if x.strip()}
        allowed_ranges = {f'{24 * int(q[1])}-{24 * int(q[1]) + 23}'
                          for q in allowed_quarters if re.fullmatch(r'q[0-3]', q)}
        if actual not in allowed_ranges:
            raise RuntimeError(f'synthetic grant regions violate row policy for {rid}: {actual!r} not in {sorted(allowed_ranges)}')
        return
    if actual != policy:
        raise RuntimeError(f'synthetic grant regions disagree with row for {rid}: {actual!r} != {policy!r}')


def _classify_grant(flags: Path, rid: str, record: dict) -> tuple[str, str]:
    """Resolve class only from explicit v3/legacy metadata bound to the exact sealed launcher."""
    manifest, archived = _manifest_records(flags, rid)
    kind = record.get('kind')
    if kind == 'rowflow-dryrun':
        if record.get('schema') != 'epyc.rowflow.dryrun-grant.v1' or record.get('id') != rid:
            raise RuntimeError(f'invalid synthetic grant identity/schema: {rid}')
        if not manifest or manifest.get('schema') != 'epyc.row.v3' or manifest.get('id') != rid:
            raise RuntimeError(f'synthetic grant has no matching rowflow v3 manifest: {rid}')
        _validate_synthetic_regions(manifest, rid, record)
    effective = manifest or (archived[0] if archived else None)
    row_class = None
    if effective:
        if effective.get('schema') == 'epyc.row.v3':
            _verify_manifest_launcher(flags, rid, effective)
            row_class = effective.get('admission_class')
            if row_class is None:
                row_class = _verified_archived_class(flags, rid, effective, archived)
        else:
            row_class = effective.get('admission_class') or effective.get('class')
            if row_class:
                _verify_manifest_launcher(flags, rid, effective)
    if not row_class:
        classified = subprocess.run(
            ['python3', '-I', str(flags/'validate_fillers.py'), '--file', str(flags/'FILLERS.md'),
             '--print-class', rid], capture_output=True, text=True, timeout=10)
        if classified.returncode:
            raise RuntimeError(f'cannot classify active grant {rid}')
        row_class = classified.stdout.strip().removeprefix('class=')
    if kind == 'rowflow-dryrun' and record.get('admission_class') is not None and record['admission_class'] != row_class:
        raise RuntimeError(f'synthetic grant class disagrees with trusted row metadata: {rid}')
    if row_class not in ADMISSION_CLASS_VALUES:
        raise RuntimeError(f'unknown active grant class: {rid}: {row_class!r}')
    if 'timing' in row_class:
        raise RuntimeError(f'timing grant is active: {rid}')
    if row_class not in ADMISSION_CLASSES_ALLOWED:
        raise RuntimeError(f'unknown active grant class: {rid}: {row_class}')

    filler_rows = [line for line in (flags/'FILLERS.md').read_text(errors='replace').splitlines()
                   if line.startswith('| '+rid+' |')]
    if len(filler_rows) > 1:
        raise RuntimeError(f'ambiguous active grant row metadata: {rid}')
    if not effective and not filler_rows:
        raise RuntimeError(f'cannot resolve active grant row metadata: {rid}')
    metadata = (filler_rows[0] if filler_rows else '') + ' ' + json.dumps(effective or {}, sort_keys=True)
    metadata += ' ' + ' '.join(json.dumps(m, sort_keys=True) for m in archived)
    return row_class, metadata

def _assert_not_ds41_or_overlap(name: str, record: dict, metadata: str, job_cpus: set[int]) -> None:
    blob = (name + ' ' + json.dumps(record) + ' ' + metadata).lower()
    blob = re.sub(r'\b(?:no|not|without)\s+ds41\b', '', blob)
    blob = blob.replace('deepseek-v4.1', 'ds41')
    if 'ds41' in blob:
        raise RuntimeError(f'DS41 grant is active: {name}')
    cpus = str(record.get('regions'))
    if cpu_set(cpus) & job_cpus:
        raise RuntimeError(f'active grant overlaps R11 smoke CPUs: {name}: {cpus}')


def admission_snapshot():
    """Fresh conservative R11 check. Rowflow dry-run grants carry class + row identity explicitly."""
    flags = Path('/mnt/raid0/llm/tmp/compute-flags')
    active = []
    for path in sorted((flags / 'grants').glob('*.grant')):
        try:
            raw = path.read_text()
            try:
                record = json.loads(raw)
            except json.JSONDecodeError:
                record = dict(t.split('=',1) for t in shlex.split(raw) if '=' in t)
            if not isinstance(record, dict) or 'regions' not in record or 'start' not in record or 'end' not in record:
                raise ValueError('missing start/end/regions')
            end = datetime.datetime.fromisoformat(record['end'].replace('Z','+00:00')).timestamp()
            start = datetime.datetime.fromisoformat(record['start'].replace('Z','+00:00')).timestamp()
            if not start <= time.time() < end:
                continue
            rid = record.get('id') or path.stem
            if rid != path.stem:
                raise RuntimeError(f'grant filename/id mismatch: {path.name} claims {rid}')
            if rid == os.environ.get('FILLER_ID'):
                continue
            row_class, metadata = _classify_grant(flags, rid, record)
            active.append((path.name, record, row_class, metadata))
        except Exception as exc:
            raise RuntimeError(f'cannot prove active grant disposition for {path.name}: {exc}')
    if active:
        for name, rec, row_class, metadata in active:
            rid = name.removesuffix('.grant')
            _assert_not_ds41_or_overlap(name, rec, metadata, set(os.sched_getaffinity(0)))
    # Owner HOLDs are explicit marker files. Ignore historical artifacts and
    # task-local review holds; block only a fresh shared hold at the root.
    for path in flags.glob('HOLD*'):
        if path.is_file() and time.time() - path.stat().st_mtime < 24 * 3600:
            raise RuntimeError(f'shared compute HOLD is present: {path.name}')
    return {'checked_unix': time.time(), 'active_grants': len(active),
            'active_grant_ids': [name for name, *_ in active], 'job_cpus': sorted(os.sched_getaffinity(0))}

def cpu_set(value):
    result = set()
    for part in value.replace('q0', '0-23').replace('q1','24-47').replace('q2','48-71').replace('q3','72-95').split(','):
        if not part.strip(): continue
        if '-' in part:
            a,b = part.split('-'); result.update(range(int(a), int(b)+1))
        elif part.isdigit(): result.add(int(part))
    return result

class WindowEnd(Exception): pass

def request_json(url, payload=None, timeout=20):
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data,
        headers={} if data is None else {'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def check_pid(proc, birth):
    if proc.poll() is not None:
        raise RuntimeError(f'server exited early: rc={proc.returncode}')
    if read_start_ticks(proc.pid) != birth:
        raise RuntimeError('server PID was reused; refusing to inspect/stop another process')


def stop_server(proc, birth):
    if proc.poll() is None:
        check_pid(proc, birth)
        os.killpg(proc.pid, signal.SIGTERM)
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                raise RuntimeError('captured server did not exit after SIGKILL')
    try:
        alive = read_start_ticks(proc.pid) == birth
    except FileNotFoundError:
        alive = False
    if alive:
        raise RuntimeError('captured server remains alive after shutdown')
    if process_group_records(proc.pid):
        raise RuntimeError('captured server process group remains alive after shutdown')
    return proc.returncode


def output_dir_for(root: Path, mode: str, control: str | None, requested: str | None) -> Path:
    base = root.resolve()
    if requested is None:
        return base / ('smoke-' + (control or 'normal') if mode == 'smoke' else 'run')
    rel = Path(requested)
    if rel.is_absolute():
        raise ValueError('output directory must be relative to S18 root')
    out = (base / rel).resolve()
    if out == base or base not in out.parents:
        raise ValueError('output directory must remain below S18 root')
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mode', choices=('smoke', 'full'), required=True)
    ap.add_argument('--seconds', type=int, default=300)
    ap.add_argument('--max-tokens', type=int, default=512)
    ap.add_argument('--port', type=int, default=PORT)
    ap.add_argument('--control', choices=('normal','cutoff'))
    ap.add_argument('--output-dir', help='isolated output directory relative to the sealed S18 source root')
    args = ap.parse_args()
    if args.mode == 'smoke' and args.seconds > 300:
        ap.error('R11 smoke limit is 300 seconds including drain')
    if args.mode == 'full' and args.max_tokens != 512:
        ap.error('primary S-18 parity must preserve the recorded MI210 max_tokens=512 recipe')

    whole_start = time.monotonic()
    try:
        out = output_dir_for(ROOT, args.mode, args.control, args.output_dir)
    except ValueError as exc:
        ap.error(str(exc))
    out.mkdir(parents=True, exist_ok=True)
    results = out / 'results.jsonl'
    log_path = out / 'server.log'
    manifest = out / 'run.json'
    # Each attempt writes a fresh private result record; no stale failure is
    # allowed to masquerade as the outcome of a later retry.
    for stale in (out / 'error.txt', out / 'drain-error.txt',
                  out / 'server.log', out / 'server.identity.json', out / 'run.json',
                  out / 'pre-evict.log', out / 'runtime-samples.jsonl'):
        try:
            stale.unlink()
        except FileNotFoundError:
            pass
    if hashlib.sha256((ROOT / 'dataset/cohort.json').read_bytes()).hexdigest() != '232fe3a8339db98cb9cb3ddc03c64cae798404bf4aaef4a8f677fe471690ca2e':
        raise RuntimeError('cohort digest changed')
    rows = json.loads((ROOT / 'dataset/cohort.json').read_text())
    rows = rows[:2 if args.control == 'cutoff' else 1] if args.mode == 'smoke' else rows
    if args.mode == 'smoke':
        results.unlink(missing_ok=True)
    done = {json.loads(x)['id'] for x in results.read_text().splitlines()} if results.exists() else set()
    expected_rows = len(rows)
    rows = [r for r in rows if r['id'] not in done]
    if not MODEL.is_file() or not MMPROJ.is_file() or not SERVER.is_file():
        raise RuntimeError('canonical model, mmproj, or CPU server missing')
    pins = json.loads((ROOT / 'MODEL-EDGE-PINS.json').read_text())
    if file_edge_pin(MODEL) != pins['model']:
        raise RuntimeError('canonical model edge fingerprint/size changed')
    if file_edge_pin(MMPROJ) != pins['mmproj']:
        raise RuntimeError('canonical mmproj edge fingerprint/size changed')
    with socket.socket() as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
        sock.bind(('127.0.0.1', args.port))
    admission = admission_snapshot()

    # Import the original evaluation prompt and exact scorer; do not fork a grading rule.
    sys.path.insert(0, str(HARNESS_PATH.parent))
    import harness

    env = os.environ.copy()
    env.update(LD_LIBRARY_PATH=LIBPATH, OMP_NUM_THREADS='1',
               OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1')
    verify = subprocess.run([str(VERIFY), str(SERVER), LIBPATH], env=env,
                            capture_output=True, text=True, timeout=30)
    if verify.returncode:
        raise RuntimeError('CPU ggml linkage verification failed: ' + verify.stderr)
    admission_snapshot()
    evict = subprocess.run(['python3', str(RESEARCH / 'scripts/utils/numa_evict.py'),
                            '--nodes', '0,1', '--target-gib', '40', '--passes', '2'],
                           capture_output=True, text=True, timeout=180)
    (out / 'pre-evict.log').write_text(evict.stdout + evict.stderr)
    if evict.returncode != 0:
        raise RuntimeError(f'NUMA_HALF_A 40 GiB/node pre-eviction failed rc={evict.returncode}')
    cmd = ['numactl', '--interleave=0,1', '--', str(SERVER), '-m', str(MODEL), '--mmproj', str(MMPROJ),
           '--host', '127.0.0.1', '--port', str(args.port), '-np', '1',
           '-c', '16384',
           '-t', os.environ.get('THREADS', '48' if args.mode == 'full' else '2'),
           '-tb', os.environ.get('THREADS', '48' if args.mode == 'full' else '2'),
           '-ngl', '0', '--jinja', '--log-colors', 'off', '--image-min-tokens', '1024',
           '--cache-ram', '0']
    deadline = min(whole_start + args.seconds, time.monotonic()+float(os.environ.get('FILLER_DEADLINE',str(time.time()+args.seconds)))-time.time())
    cutoff = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: cutoff.set())
    signal.signal(signal.SIGINT, lambda *_: cutoff.set())
    proc = None
    born = None
    peak_rss = 0
    sampler_stop = threading.Event()
    sampler_errors = []
    loaded = False
    request_ok = False
    final_rc = 1
    with open(log_path, 'w', buffering=1) as log:
        try:
            proc = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, env=env,
                                    start_new_session=True)
            born = read_start_ticks(proc.pid)
            if os.environ.get('FILLER_PIDFILE'):
                with open(os.environ['FILLER_PIDFILE'], 'a') as pidfile:
                    pidfile.write(str(proc.pid)+'\n'); pidfile.flush(); os.fsync(pidfile.fileno())
            (out / 'server.identity.json').write_text(json.dumps(
                {'pid': proc.pid, 'start_ticks': born, 'argv': cmd, 'cpus': sorted(os.sched_getaffinity(0))}, indent=2) + '\n')
            def sample_runtime():
                nonlocal peak_rss
                seen = {}
                cutoff_at = None
                last_admission = 0.0
                while not sampler_stop.wait(.25):
                    try:
                        if cutoff.is_set() or time.monotonic() >= deadline - 15 or (os.environ.get('FILLER_STOPFILE') and Path(os.environ['FILLER_STOPFILE']).exists()):
                            cutoff.set()
                            if cutoff_at is None:
                                cutoff_at = time.monotonic()
                                check_pid(proc, born)
                                os.killpg(proc.pid, signal.SIGTERM)
                            if proc.poll() is not None:
                                return
                            if time.monotonic()-cutoff_at >= 3:
                                check_pid(proc, born)
                                os.killpg(proc.pid, signal.SIGKILL)
                                return
                            continue
                        check_pid(proc, born)
                        sample_rss, maps_now, server_found, identities = process_group_rss_and_maps(proc.pid)
                        for ident in identities:
                            prior = seen.get(ident['pid'])
                            if prior is not None and prior != ident['start_ticks']:
                                raise RuntimeError(f'owned PID reuse detected: {ident["pid"]}')
                            seen[ident['pid']] = ident['start_ticks']
                        peak_rss = max(peak_rss, sample_rss)
                        if server_found and str(MODEL) in maps_now :
                            if 'libggml-hip' in maps_now or 'libhip' in maps_now.lower() or 'libamdhip' in maps_now.lower():
                                raise RuntimeError('HIP backend/library mapped in CPU run')
                        if peak_rss > 48 * 1024**3:
                            raise MemoryError('sampled server RSS exceeded 48 GiB safety ceiling')
                        if time.monotonic()-last_admission >= 1:
                            try:
                                observed = admission_snapshot()
                            except RuntimeError as exc:
                                cutoff.set()
                                observed = {'paused':str(exc), 'checked_unix':time.time()}
                            with (out/'runtime-samples.jsonl').open('a') as trace:
                                trace.write(json.dumps({'rss_bytes':sample_rss,'owned':identities,'admission':observed})+'\n')
                            last_admission = time.monotonic()
                    except Exception as exc:
                        sampler_errors.append(f'{type(exc).__name__}: {exc}')
                        try:
                            check_pid(proc, born)
                            os.killpg(proc.pid, signal.SIGTERM)
                            try:
                                proc.wait(timeout=3)
                            except subprocess.TimeoutExpired:
                                check_pid(proc, born)
                                os.killpg(proc.pid, signal.SIGKILL)
                        except Exception:
                            pass
                        return
            sampler = threading.Thread(target=sample_runtime, name='s18-rss-admission-sampler', daemon=True)
            sampler.start()
            while time.monotonic() < deadline - 20:
                check_pid(proc, born)
                if sampler_errors:
                    raise RuntimeError(sampler_errors[0])
                try:
                    request_json(f'http://127.0.0.1:{args.port}/health', timeout=3)
                    loaded = 'model loaded' in log_path.read_text(errors='ignore').lower()
                    if loaded:
                        break
                except Exception:
                    pass
                time.sleep(1)
            if not loaded:
                raise TimeoutError('server did not finish model load before request deadline')
            _, maps, server_found, identities = process_group_rss_and_maps(proc.pid)
            (out / 'server.process-maps').write_text(maps)
            (out / 'process-witness.json').write_text(json.dumps(identities, indent=2)+'\n')
            if not server_found or str(MODEL) not in maps or f"loaded multimodal model, '{MMPROJ}'" not in log_path.read_text():
                raise RuntimeError('owned server lacks exact model mapping or pinned mmproj load log')
            mapped_libs = sorted({line.split()[-1] for line in maps.splitlines() if 'libggml' in line or 'libllama' in line})
            (out / 'mapped-closure.json').write_text(json.dumps(mapped_libs, indent=2)+'\n')
            if any(not Path(x).resolve().is_relative_to(SERVER.resolve().parent) for x in mapped_libs):
                raise RuntimeError('mapped ggml/llama closure escaped CPU store image')
            if any(x in maps.lower() for x in ('libggml-hip', 'libhip', 'libamdhip')):
                raise RuntimeError('HIP backend/library mapped in CPU run')

            import base64
            nothink = False
            with results.open('a', buffering=1) as writer:
                for idx, row in enumerate(rows):
                    if cutoff.is_set() or time.monotonic() >= deadline - 20:
                        raise WindowEnd('window ended between items')
                    image_ref = Path(row['image_path'])
                    image_path = image_ref if image_ref.is_absolute() else (ROOT / 'dataset' / image_ref)
                    img = image_path.read_bytes()
                    if hashlib.sha256(img).hexdigest() != row['image_sha256']:
                        raise RuntimeError(f'image digest mismatch: {row["id"]}')
                    payload = {'messages': [{'role': 'user', 'content': [
                        {'type': 'image_url', 'image_url': {'url': 'data:image/png;base64,' + base64.b64encode(img).decode()}},
                        {'type': 'text', 'text': harness.build_prompt(row)}]}],
                        'max_tokens': 4 if args.mode == 'smoke' else args.max_tokens,
                        'temperature': 0.2, 'seed': 42}
                    if nothink:
                        payload['chat_template_kwargs'] = {'enable_thinking': False}
                    t0 = time.monotonic()
                    if args.control == 'cutoff' and idx == 1:
                        threading.Timer(2, cutoff.set).start()
                    (out / 'active-request.json').write_text(json.dumps({'row': row['id'], 'started_unix': time.time(), 'idx': idx}))
                    response = request_json(f'http://127.0.0.1:{args.port}/v1/chat/completions',
                                            payload, timeout=max(1, int(deadline-time.monotonic()-5)))
                    if sampler_errors:
                        raise RuntimeError(sampler_errors[0])
                    elapsed = time.monotonic() - t0
                    message = response['choices'][0]['message']
                    content = (message.get('content') or '').strip()
                    reasoning = (message.get('reasoning_content') or '').strip()
                    if not content and reasoning and not nothink:
                        nothink = True
                        payload['chat_template_kwargs'] = {'enable_thinking': False}
                        response = request_json(f'http://127.0.0.1:{args.port}/v1/chat/completions',
                                                payload, timeout=max(1, int(deadline-time.monotonic()-5)))
                        message = response['choices'][0]['message']
                        content = (message.get('content') or '').strip()
                        reasoning = (message.get('reasoning_content') or '').strip()
                    elapsed = time.monotonic()-t0
                    if not content:
                        raise RuntimeError(f'empty first response for {row["id"]}')
                    request_ok = True
                    pred, parse = harness.extract_letter(content, row['options'])
                    usage = response.get('usage', {})
                    timings = response.get('timings') or {}
                    rec = {'idx': row['idx'], 'id': row['id'], 'subject': row['subject'],
                           'expected': row['expected'], 'raw': content,
                           'reasoning': reasoning[:400] or None, 'pred': pred, 'parse': parse,
                           'correct': pred == row['expected'], 'elapsed_s': elapsed,
                           'completion_tokens': usage.get('completion_tokens'),
                           'decode_tok_s': timings.get('predicted_per_second'),
                           'decode_tokens': timings.get('predicted_n'),
                           'request_elapsed_s': elapsed, 'nothink': nothink, 'prompt_tokens': usage.get('prompt_tokens'), 'usage': usage, 'timings': timings}
                    writer.write(json.dumps(rec, ensure_ascii=False) + '\n')
                    writer.flush()
                    os.fsync(writer.fileno())
                    if args.mode == 'smoke' and args.control != 'cutoff':
                        break
            final_rc = 0 if sum(1 for _ in results.open()) == expected_rows else 75
        except Exception as exc:
            (out / 'error.txt').write_text(f'{type(exc).__name__}: {exc}\n')
            written = sum(1 for _ in results.open()) if results.exists() else 0
            final_rc = 75 if cutoff.is_set() or isinstance(exc, WindowEnd) or time.monotonic() >= deadline - 20 else 1
        finally:
            sampler_stop.set()
            if 'sampler' in locals():
                sampler.join(timeout=2)
            if proc is not None:
                try:
                    stop_server(proc, born)
                except Exception as exc:
                    (out / 'drain-error.txt').write_text(f'{type(exc).__name__}: {exc}\n')
                    final_rc = 1
    wall = time.monotonic() - whole_start
    if args.mode == 'smoke' and wall > 300:
        final_rc = 1
    payload = {'task': 'S-18 Qwen3-VL-30B CPU first-start', 'mode': args.mode,
               'model_sha256': MODEL_SHA, 'mmproj_sha256': MMPROJ_SHA,
               'model_edge_pin': pins['model'], 'mmproj_edge_pin': pins['mmproj'],
               'port': args.port, 'max_tokens': 4 if args.mode == 'smoke' else args.max_tokens,
               'temperature': 0.2, 'seed': 42, 'cpu_backend': True,
               'request_ok': request_ok, 'peak_sampled_server_rss_bytes': peak_rss,
               'r11_admission': admission,
               'rows_written': sum(1 for _ in results.open()) if results.exists() else 0,
               'expected_rows': expected_rows, 'partial': final_rc == 75,
               'wall_s_including_drain': wall, 'exit_code': final_rc,
               'drained': proc is None or not process_group_records(proc.pid), 'control': args.control,
               'active_cutoff': cutoff.is_set(), 'server_log': str(log_path), 'results': str(results)}
    manifest.write_text(json.dumps(payload, indent=2) + '\n')
    return final_rc


if __name__ == '__main__':
    raise SystemExit(main())
