#!/usr/bin/env python3
"""M4 CPU entry integration fixture. Real inference remains hard-disabled.

This exercises the real guard/watch ownership path with a source-pinned dummy
workload. It does not accept the retired job or a model-bearing command.
"""
from __future__ import annotations

import argparse
import fcntl
from datetime import datetime, timezone
import hashlib
import json
import re
import os
from pathlib import Path
import sys
import subprocess
import shutil
import native_authorization
import time
import watch

NATIVE_ROOT = Path('/mnt/raid0/llm/tmp/refactor-01a16fc3/m4-full-fold-ready-20261028/cpu-fold')
NATIVE_SEALS = {
    'dispatch.py': '29431e53b973be9a9392a450a66394aea7075cd57137a8f442ff522a2c21155f',
    'capture.py': '701168d58ef67bdc1e130cff9a0fa0f8576516df9fe743bcdaf0794501965479',
    'native/k35_stack_context_matrix_runner.py': '056bb6a0743dc52ccc063db2ecdb8bc1be554306fa6d37e664eaba00878fee89',
    'native/compare_v9_promotion_arms.py': '83e1ea40499cbca531849af454209d45011b55bc2684c841a09068a15c3fd94e',
}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _time(value: str) -> float:
    return datetime.strptime(value, '%Y-%m-%dT%H:%MZ').replace(tzinfo=timezone.utc).timestamp()


def _row_id(value: object) -> str:
    if not isinstance(value, str) or not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,127}', value):
        raise ValueError('invalid bound row identity')
    return value


def _grant(path: Path, expected_region: str, deadline: float, *, require_host_holds: bool = False,
           allow_dryrun: bool = False, expected_row_id: str | None = None) -> None:
    fields = path.read_text().split()
    pieces = [field.split('=', 1) for field in fields]
    if any(len(pair) != 2 for pair in pieces) or len({pair[0] for pair in pieces}) != len(pieces):
        raise ValueError('malformed or duplicate grant fields')
    values = dict(pieces)
    keys = set(values)
    required = {'regions', 'start', 'end'}
    if require_host_holds:
        if keys != required | {'holds'}:
            raise ValueError('live v3 grant must include host and GPU holds')
        holds = values['holds'].split(',')
        if len(holds) != 5 or set(holds) != {'q0', 'q1', 'q2', 'q3', 'gpu-quiet'}:
            raise ValueError('full host and GPU-quiet holds required')
    elif keys == required | {'holds', 'schema', 'id', 'kind'}:
        if (not allow_dryrun or os.environ.get('FILLER_DRYRUN') != '1'
                or values['schema'] != 'epyc.rowflow.dryrun-grant.v1'
                or values['kind'] != 'rowflow-dryrun'
                or expected_row_id is None or values['id'] != _row_id(expected_row_id)):
            raise ValueError('unbound synthetic rowflow grant')
    elif keys not in (required, required | {'holds'}):
        raise ValueError('invalid fixture grant fields')
    start, end = _time(values['start']), _time(values['end'])
    if values['regions'] != expected_region or not start <= time.time() < deadline <= end:
        raise ValueError('grant region or interval mismatch')


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('plan', 'grant', 'stop', 'hold', 'output'):
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--plan-sha256', required=True)
    p.add_argument('--deadline', type=float, required=True)
    p.add_argument('--owner-pid', type=int, required=True)
    p.add_argument('--owner-birth', type=int, required=True)
    a = p.parse_args()
    try:
        if _sha(a.plan) != a.plan_sha256:
            raise ValueError('plan digest mismatch')
        if a.owner_pid != os.getppid() or watch.m4_cgroup_guard.birth(a.owner_pid) != a.owner_birth:
            raise ValueError('outer owner must be the actual birth-verified parent')
        plan = json.loads(a.plan.read_bytes())
        if not isinstance(plan, dict):
            raise ValueError('plan must be an object')
        mode = plan.get('mode')
        expected_schema = 'epyc.m4.cpu_entry_plan.v1' if mode == 'owned-execute' else 'epyc.m4.cpu_entry_fixture.v1'
        if plan.get('schema') != expected_schema or mode not in ('fixture', 'native-check', 'owned-execute'):
            raise ValueError('real M4 CPU execution remains disabled pending binding')
        if mode == 'fixture':
            fixture = Path(plan['fixture']).resolve(strict=True)
            if not fixture.is_file() or _sha(fixture) != plan['fixture_sha256']:
                raise ValueError('fixture source changed')
            command = [sys.executable, '-B', str(fixture)]
        elif mode == 'native-check':
            # The exact registered topology producer runs *without* --execute;
            # this validates its real source and full plan but cannot load models.
            for name, digest in NATIVE_SEALS.items():
                if _sha(NATIVE_ROOT / name) != digest:
                    raise ValueError(f'native producer seal changed: {name}')
            native_inputs = []
            for key in ('scope', 'native_plan'):
                path = Path(plan[key]).resolve(strict=True)
                if _sha(path) != plan[key + '_sha256']:
                    raise ValueError(f'{key} input changed')
                native_inputs.append(path)
            base = Path(plan['baseline_image']).resolve(strict=True)
            candidate = Path(plan['candidate_image']).resolve(strict=True)
            if not base.is_dir() or not candidate.is_dir():
                raise ValueError('image path missing')
            command = [sys.executable, '-B', str(NATIVE_ROOT/'dispatch.py'),
                       '--scope', str(native_inputs[0]), '--plan', str(native_inputs[1]),
                       '--baseline-image', str(base), '--candidate-image', str(candidate),
                       '--out', str(a.output/'native-out')]
            if plan.get('role'):
                command.extend(['--role', plan['role']])
        else:
            command = None  # resolved only after canonical grant and enrollment
        if not isinstance(plan.get('region'), str) or not plan['region']:
            raise ValueError('region missing')
        if not a.output.is_dir() or any(a.output.iterdir()):
            raise ValueError('output must be a fresh empty directory')
        _grant(a.grant, plan['region'], a.deadline, require_host_holds=(mode == 'owned-execute'),
               allow_dryrun=(mode != 'owned-execute'), expected_row_id=plan.get('row_id'))
        if not a.hold.is_dir() or a.stop.exists() or any(a.hold.glob('HOLD_*')):
            raise ValueError('STOP or HOLD before entry')
        grant_hash = _sha(a.grant)
        if mode == 'owned-execute':
            # The independently sealed entry and native plan bind one fresh
            # queue row; an environment variable alone cannot select authority.
            filler_id = _row_id(plan.get('row_id'))
            canonical_grant = Path('/mnt/raid0/llm/tmp/compute-flags/grants') / (filler_id + '.grant')
            if (a.grant != canonical_grant or plan['region'] != '0-95'
                    or os.environ.get('FILLER_ID') != filler_id):
                raise ValueError('native execution requires its bound canonical full-host grant')
            if (not isinstance(plan.get('stopfile'), str) or Path(plan['stopfile']) != a.stop
                    or os.environ.get('FILLER_STOPFILE') != str(a.stop)
                    or a.hold != Path('/mnt/raid0/llm/tmp/compute-flags')):
                raise ValueError('native STOP/HOLD path differs from bound row')
            if sorted(os.sched_getaffinity(0)) != list(range(96)):
                raise ValueError('native execution requires exact full-host affinity')
            # Require the exact open lease descriptions, not stale lock-file text.
            # The guardian inherits these FDs before any workload is released.
            lease_fds = [int(x) for x in os.environ.get('M4_LEASE_FDS','').split(',') if x]
            lock_names = {f'cpu_region.GLOBAL.q{i}.lock' for i in range(4)} | {'gpu_quiet.lock'}
            found = {}
            for fd in lease_fds:
                path = Path(os.readlink(f'/proc/self/fd/{fd}'))
                name = path.name
                if path.parent == Path('/mnt/raid0/llm/tmp') and name in lock_names:
                    if name in found: raise ValueError('ambiguous inherited lease FD')
                    found[name] = fd
            if set(found) != lock_names:
                raise ValueError('inherited cross-role/GPU lease descriptors missing')
            for name,fd in found.items():
                target = os.stat(Path('/mnt/raid0/llm/tmp')/name)
                held = os.fstat(fd)
                if (target.st_dev,target.st_ino) != (held.st_dev,held.st_ino):
                    raise ValueError('lease descriptor inode changed')
            quiet_mode = plan.get('gpu_quiet')
            if quiet_mode not in ('shared', 'exclusive') or os.environ.get('M4_GPU_QUIET_MODE') != quiet_mode:
                raise ValueError('GPU-quiet lease mode differs from bound plan')
            for name,fd in found.items():
                operation = fcntl.LOCK_SH if name == 'gpu_quiet.lock' and quiet_mode == 'shared' else fcntl.LOCK_EX
                fcntl.flock(fd, operation | fcntl.LOCK_NB)
            resource = plan['resource']
            minimum = resource['min_remaining_s']; output_bytes = resource['estimated_output_bytes']
            max_ram = resource['max_ram_bytes']; reserve = resource['memory_reserve_bytes']
            if any(type(v) is not int for v in (minimum,output_bytes,max_ram,reserve)) or minimum < 300 or output_bytes < 0 or max_ram <= 0 or reserve < 0:
                raise ValueError('resource envelope incomplete')
            if a.deadline - time.time() < minimum:
                raise ValueError('insufficient remaining grant window')
            mem = dict(line.split(':',1) for line in Path('/proc/meminfo').read_text().splitlines() if ':' in line)
            available = int(mem['MemAvailable'].split()[0]) * 1024
            if available < max_ram + reserve:
                raise ValueError('insufficient available RAM')
            if shutil.disk_usage('/mnt/raid0/llm').free - output_bytes < 150 * 1024**3:
                raise ValueError('insufficient free-after-estimate disk')
            producer = Path(__file__).resolve().parent.parent/'m4_cpu_producer'
            output = Path(plan['capture_output'])
            if not output.is_absolute() or '..' in output.parts or output.exists():
                raise ValueError('native capture output is not fresh')
            # Only a reviewed/deployed reader may grant source enrollment.
            sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'vidya'))
            from adapters import m4_cpu_speed as reader
            config = reader._trusted_config_for(output/'model-000/process-captures/future.json')
            if config.producer_root != producer:
                raise ValueError('deployed reader does not enroll this producer')
            champion = subprocess.check_output(['git','-C','/mnt/raid0/llm/llama.cpp','rev-parse',
                'refs/heads/ak/champion/llama-cpp-ffc1bac82eec'], text=True).strip()
            bound = native_authorization.verify(plan, current_champion=champion, enrolled=True)
            with (a.output/'PLANNER-CANARY-BEFORE.json').open('x',encoding='utf-8') as receipt:
                json.dump(bound['canary_receipt'],receipt,sort_keys=True,indent=2)
            command = [sys.executable, '-B', str(producer/'dispatch.py'), '--scope', str(bound['scope']),
                       '--plan', str(bound['native_plan']), '--baseline-image', str(bound['images']['baseline']),
                       '--candidate-image', str(bound['images']['candidate']), '--out', str(output),
                       '--role', bound['role'], '--execute']
        env = dict(os.environ, M4_DELEGATED_CGROUP_PARENT='/sys/fs/cgroup',
                   M4_OUTER_OWNER_PID=str(a.owner_pid), M4_OUTER_OWNER_BIRTH=str(a.owner_birth))
        if mode == 'owned-execute':
            env.update(FILLER_ID=filler_id, FILLER_STOPFILE=str(a.stop), FILLER_DEADLINE=str(int(a.deadline)), M4_SPEED_WRITER_WIRED='1')
        rc = watch.run(command, a.grant, a.stop, a.hold,
                       a.deadline, a.output, env)
        if mode == 'owned-execute':
            config = reader._trusted_config_for(output/'model-000/process-captures/future.json')
            if config.producer_root != producer:
                raise ValueError('deployed reader changed after work')
            champion = subprocess.check_output(['git','-C','/mnt/raid0/llm/llama.cpp','rev-parse',
                'refs/heads/ak/champion/llama-cpp-ffc1bac82eec'], text=True).strip()
            final_binding = native_authorization.verify(plan, current_champion=champion, enrolled=True)
            with (a.output/'PLANNER-CANARY-AFTER.json').open('x',encoding='utf-8') as receipt:
                json.dump(final_binding['canary_receipt'],receipt,sort_keys=True,indent=2)
        _grant(a.grant, plan['region'], a.deadline, require_host_holds=(mode == 'owned-execute'),
               allow_dryrun=(mode != 'owned-execute'), expected_row_id=plan.get('row_id'))
        if _sha(a.grant) != grant_hash or not a.hold.is_dir() or a.stop.exists() or any(a.hold.glob('HOLD_*')):
            raise ValueError('final grant, STOP or HOLD check failed')
        if rc != 0:
            raise ValueError(f'workload incomplete: {rc}')
        name = 'NATIVE-CAPTURE-COMPLETE.json' if mode == 'owned-execute' else 'FIXTURE-COMPLETE.json'
        with (a.output / name).open('x') as f:
            json.dump({'schema': 'epyc.m4.cpu_entry_complete.v1', 'plan_sha256': a.plan_sha256,
                       'mode': mode, 'fixture_only': mode != 'owned-execute', 'gate_verdict': None}, f)
        return 0
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, ImportError, subprocess.CalledProcessError) as exc:
        print(f'REFUSED: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
