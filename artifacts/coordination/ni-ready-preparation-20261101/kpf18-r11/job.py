#!/usr/bin/python3
"""Exact R7 X1 bridge replay through one v2 CPU job entry.

The historical R6 evidence remains diagnostic. This job never authors a new
native measurement warrant or mutates the original replay packet.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time

ROOT = Path('/mnt/raid0/llm/tmp/codex-ni-kpf18-cpu-repair-20261101/r11')
SOURCE = Path('/mnt/raid0/llm/tmp/codex-ni-kpf18-native-segfault-r7-20261030')
RAW = Path('/mnt/raid0/llm/tmp/cal-1026/kpf18-g3-native-control-r6/out/capture/X1.native.raw')
LEDGER = RAW.parent / 'EVENT-LEDGER.json'
ID = 'codex-ni-kpf18-r11-full-bridge-v2-20261101'
WORK_UNIT = 'original-X1-native-observation'
STAGES = {'target_prefix', 'target_suffix', 'draft_initial', 'draft_first_decode'}
RAW_SHA = '7cbf105def05e9f874080f6def041754b19c109c7c9ddab5b2d64bf4666a33ee'
LEDGER_SHA = 'a6b18b1b96bc773fa74559c9bfc28248287c1dfcf08deb7ef07278d95d9f304a'
SOURCE_SHA = 'e6beebeaeb9b996437fcfaef2dac56bc178e601a1bc6ea77cd6cfedd8cc5c19b'
DATA_SHA = '3dbaad39c1354d0f47173c78b85ccb60722fb84b4c57857055265d083730885f'
TERMINATE_REQUESTED = False


def request_termination(_signum, _frame) -> None:
    global TERMINATE_REQUESTED
    TERMINATE_REQUESTED = True


def sha(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def atomic_json(path: Path, value: dict) -> None:
    tmp = path.with_name('.' + path.name + '.tmp-' + str(os.getpid()))
    with tmp.open('x') as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(tmp, path)


def parse_grant(path: Path, cpus: str, now: int, deadline: int, *, qualifier: bool = False) -> tuple[int, int]:
    if path.is_symlink() or not path.is_file():
        raise ValueError('own grant missing or symlink')
    lines = path.read_text().splitlines()
    if len(lines) != 1:
        raise ValueError('own grant is not one line')
    match = re.fullmatch(r'regions=([^ ]+) start=(\d{4}-\d\d-\d\dT\d\d:\d\dZ) end=(\d{4}-\d\d-\d\dT\d\d:\d\dZ)', lines[0])
    if not match or match[1] != cpus:
        raise ValueError('own grant CPU region differs from engine claim')
    start = int(dt.datetime.strptime(match[2], '%Y-%m-%dT%H:%MZ').replace(tzinfo=dt.timezone.utc).timestamp())
    end = int(dt.datetime.strptime(match[3], '%Y-%m-%dT%H:%MZ').replace(tzinfo=dt.timezone.utc).timestamp())
    deadline_limit = end if qualifier else end - 90
    if not start <= now < end or end - start != 3600 or deadline > deadline_limit:
        raise ValueError('own 3600-second grant/deadline invalid')
    return start, end


def identity(pid: int) -> tuple[int, int] | None:
    try:
        tail = Path(f'/proc/{pid}/stat').read_text().rsplit(') ', 1)[1].split()
        return int(tail[19]), int(tail[2])
    except (OSError, ValueError, IndexError):
        return None


def drain(proc: subprocess.Popen, birth: int, *, same_group: bool = False) -> bool:
    wanted_group = os.getpgrp() if same_group else proc.pid
    if proc.poll() is None and identity(proc.pid) == (birth, wanted_group):
        if same_group:
            proc.terminate()
        else:
            os.killpg(proc.pid, signal.SIGTERM)
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            if identity(proc.pid) == (birth, wanted_group):
                if same_group:
                    proc.kill()
                else:
                    os.killpg(proc.pid, signal.SIGKILL)
            proc.wait(timeout=10)
    return proc.poll() is not None and identity(proc.pid) != (birth, wanted_group)


def validate_bridge(path: Path, *, bounded: bool) -> dict:
    result = json.loads(path.read_text())
    if (result.get('raw_sha256') != RAW_SHA or result.get('ledger_sha256') != LEDGER_SHA
            or result.get('source_seal_sha256') != SOURCE_SHA
            or set(result.get('stages', [])) != STAGES
            or result.get('historical_r6_verdict') != 'INVALID unchanged'
            or not result.get('fork_bindings_sha256') or not result.get('layouts_sha256')):
        raise ValueError('R7 bridge full input/stage/source evidence incomplete')
    if bounded:
        if result.get('smoke_pass') is not True or result.get('partial') is not True or result.get('framing_pass') is not False:
            raise ValueError('bounded native replay result misclassified')
    elif result.get('framing_pass') is not True or result.get('partial') is True:
        raise ValueError('full R7 bridge framing did not pass')
    return result


def source_check() -> None:
    if sha(SOURCE / 'SOURCES.sha256') != SOURCE_SHA:
        raise ValueError('R7 root source manifest changed')
    subprocess.run(['sha256sum', '--quiet', '-c', 'SOURCES.sha256'], cwd=SOURCE, check=True)
    data = SOURCE / 'data-candidate'
    if sha(data / 'SHA256SUMS') != DATA_SHA:
        raise ValueError('R7 data source manifest changed')
    subprocess.run(['sha256sum', '--quiet', '-c', 'SHA256SUMS'], cwd=data, check=True)
    if sha(RAW) != RAW_SHA or sha(LEDGER) != LEDGER_SHA:
        raise ValueError('immutable X1 raw/ledger changed')


def resource_check() -> None:
    fields = dict(line.split(':', 1) for line in Path('/proc/meminfo').read_text().splitlines() if ':' in line)
    available_kib = int(fields['MemAvailable'].strip().split()[0])
    if available_kib < 128 * 1024 * 1024:
        raise ValueError('64 GiB replay plus 64 GiB host RAM margin unavailable')
    stat = os.statvfs(ROOT)
    free_gib = stat.f_bavail * stat.f_frsize / 1024**3
    if free_gib < 150.1:
        raise ValueError('150 GiB disk floor plus bounded output unavailable')


def run_bridge(out: Path, *, bounded: bool, deadline: int, stop: Path,
               same_group: bool = True, on_first_event=None) -> tuple[int, bool, float]:
    if TERMINATE_REQUESTED or stop.exists() or int(time.time()) >= deadline:
        return 75, True, 0.0
    out.mkdir(parents=True, exist_ok=False)
    argv = ['/usr/bin/python3', '-B', '-I', str(SOURCE / 'integration_replay.py'), str(out / 'bridge')]
    if bounded:
        argv.append('--bounded-smoke')
    start = time.monotonic()
    with (out / 'worker.log').open('x') as log:
        proc = subprocess.Popen(argv, cwd=SOURCE, stdout=log, stderr=subprocess.STDOUT,
                                start_new_session=not same_group,
                                env=dict(os.environ, OMP_NUM_THREADS='1', PYTHONDONTWRITEBYTECODE='1'))
        own = identity(proc.pid)
        wanted_group = os.getpgrp() if same_group else proc.pid
        if own is None or own[1] != wanted_group:
            # Popen still owns the unreaped direct child even if /proc raced.
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=10)
            raise ValueError('owned worker identity not captured')
        birth = own[0]
        cutoff = False
        first_sent = False
        try:
            while proc.poll() is None:
                if on_first_event is not None and not first_sent:
                    phase_path = out / 'bridge' / 'PHASES.jsonl'
                    if phase_path.is_file() and '"phase": "view.build.done"' in phase_path.read_text():
                        on_first_event(proc, birth, time.monotonic() - start)
                        first_sent = True
                if TERMINATE_REQUESTED or stop.exists() or int(time.time()) >= deadline:
                    cutoff = True
                    break
                time.sleep(0.25)
            if TERMINATE_REQUESTED or stop.exists() or int(time.time()) >= deadline:
                cutoff = True
        finally:
            drained = drain(proc, birth, same_group=same_group)
    wall = time.monotonic() - start
    atomic_json(out / 'SUPERVISOR.json', {'child_pid': proc.pid, 'child_birth_ticks': birth,
                'child_rc': proc.returncode, 'cutoff': cutoff, 'partial': cutoff,
                'drained': drained, 'wall_s': wall, 'argv': argv, 'cwd': str(SOURCE),
                'first_event_sent': first_sent})
    if not drained:
        return 70, False, wall
    if cutoff:
        return 75, True, wall
    return (proc.returncode if proc.returncode else 0), False, wall


def first_record(wall: float, completed: float) -> dict:
    work_wall = max(wall, 0.001)
    return {'ok': completed > 0, 'scope': 'COMMAND_NATIVE',
            'manifest_sha256': sha(ROOT / 'REQUEST.json'),
            'production_recipe_sha256': sha(ROOT / 'REQUEST.json'),
            'work_unit': WORK_UNIT, 'work_completed': completed,
            'wall_s': work_wall, 'measured_work_units_per_s': completed / work_wall,
            'partial': True, 'full_bridge_completed': False,
            'historical_r6_verdict': 'INVALID unchanged'}


def proof(phase: str, result: Path | None, wall: float, *, partial: bool,
          first: dict | None = None, stop_observed: bool = False) -> None:
    nonce = os.environ['WS58_QUAL_NONCE']
    out = Path(os.environ['WS58_QUAL_PROOF'])
    if first is None:
        first = first_record(wall, 1 if result else 0)
    record = {'id': ID, 'phase': phase, 'nonce': nonce, 'partial': partial,
              'observed_cpus': sorted(os.sched_getaffinity(0)),
              'stop_observed': stop_observed,
              'unknown_disposition': 'UNKNOWN' if partial else None,
              'disk': {'job_floor_gib': 150}, 'first_request': first,
              'result_writer': {'ok': result is not None, 'result_path': str(result) if result else None,
                                'sha256': sha(result) if result else None}}
    atomic_json(out, record)


def main() -> int:
    signal.signal(signal.SIGTERM, request_termination)
    signal.signal(signal.SIGINT, request_termination)
    if os.environ.get('FILLER_ID') != ID:
        raise ValueError('engine row identity missing')
    cpus = os.environ['FILLER_CPUS']
    deadline = int(os.environ['FILLER_DEADLINE'])
    stop = Path(os.environ['FILLER_STOPFILE'])
    phase = os.environ.get('FILLER_QUAL_PHASE') if os.environ.get('WS58_QUAL') == '1' else None
    grant_dir = Path(os.environ.get('FILLER_GRANTS_DIR', '/mnt/raid0/llm/tmp/compute-flags/grants'))
    parse_grant(grant_dir / (ID + '.grant'), cpus, int(time.time()), deadline,
                qualifier=phase is not None)
    if set(os.sched_getaffinity(0)) - {int(x) for part in cpus.split(',') for x in
          (range(int(part.split('-')[0]), int(part.split('-')[-1]) + 1) if '-' in part else [part])}:
        raise ValueError('job affinity escapes granted CPUs')
    if phase == 'cutoff':
        # The keeper issues STOP after observing the native parser at work in
        # our live child. The child remains in the qualifier's process group.
        source_check()
        out = Path(os.environ['FILLER_RESULTS_DIR']) / 'native-bridge-cutoff'
        seen = {}
        def first_event(proc, birth, wall):
            first = first_record(wall, 1)
            first.update(native_phase='view.build.done', actual_raw_bytes=1_777_442_608,
                         resolved_shape_count=0)
            seen['first'] = first
            atomic_json(Path(os.environ['WS58_QUAL_PROOF']).parent / 'cutoff-event.json',
                        {'id': ID, 'nonce': os.environ['WS58_QUAL_NONCE'], 'phase': 'cutoff',
                         'native_pid': proc.pid, 'native_birth_ticks': birth,
                         'native_first_event': True, 'first_request': first,
                         'native_phase': 'view.build.done', 'raw_sha256': RAW_SHA})
        rc, partial, wall = run_bridge(out, bounded=True, deadline=deadline, stop=stop,
                                       same_group=True, on_first_event=first_event)
        if rc != 75 or not partial or 'first' not in seen:
            raise ValueError('active native cutoff did not produce observed partial')
        atomic_json(Path(os.environ['FILLER_RESULTS_DIR']) / 'cutoff.json',
                    {'partial': True, 'rc': 75, 'disposition': 'UNKNOWN',
                     'supervisor_sha256': sha(out / 'SUPERVISOR.json')})
        proof('cutoff', None, wall, partial=True, first=seen['first'], stop_observed=stop.exists())
        return 75
    if phase not in (None, 'normal'):
        raise ValueError('unknown qualification phase')
    resource_check()
    source_check()
    if phase == 'normal':
        out = Path(os.environ['FILLER_RESULTS_DIR']) / 'native-bridge-normal'
        rc, partial, wall = run_bridge(out, bounded=True, deadline=deadline, stop=stop, same_group=True)
        if rc != 0 or partial:
            return rc
        bridge = out / 'bridge' / 'RESULT.json'
        native = validate_bridge(bridge, bounded=True)
        result = Path(os.environ['FILLER_RESULTS_DIR']) / 'normal.json'
        atomic_json(result, {'schema': 'kpf18.r11.v2.qual.v1', 'native_bridge_sha256': sha(bridge),
                            'bridge': json.loads(bridge.read_text()), 'partial': True})
        first = first_record(wall, 1)
        first.update(native_phase='trial.done', actual_grid_count=native['grid_count'],
                     actual_event_count=native['event_count'], resolved_shape_count=2,
                     actual_stage_count=len(native['stages']))
        proof('normal', result, wall, partial=False, first=first)
        return 0
    out = ROOT / 'runs' / (str(int(time.time())) + '-' + str(os.getpid()))
    if (ROOT / 'COMPLETE.json').exists():
        raise ValueError('full replay already complete')
    rc, partial, wall = run_bridge(out, bounded=False, deadline=deadline, stop=stop, same_group=True)
    if rc == 75 and partial:
        atomic_json(out / 'PARTIAL.json', {'schema': 'kpf18.r11.v2.partial.v1', 'rc': 75,
                    'partial': True, 'disposition': 'UNKNOWN', 'supervisor_sha256': sha(out / 'SUPERVISOR.json')})
        return 75
    if rc != 0:
        return rc
    bridge = out / 'bridge' / 'RESULT.json'
    validate_bridge(bridge, bounded=False)
    atomic_json(ROOT / 'COMPLETE.json', {'schema': 'kpf18.r11.v2.complete.v1', 'rc': 0,
                'framing_pass': True, 'historical_r6_verdict': 'INVALID unchanged',
                'bridge_result_path': str(bridge), 'bridge_result_sha256': sha(bridge),
                'supervisor_sha256': sha(out / 'SUPERVISOR.json'), 'wall_s': wall})
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f'REFUSED: {type(exc).__name__}: {exc}', file=sys.stderr, flush=True)
        raise SystemExit(70)
