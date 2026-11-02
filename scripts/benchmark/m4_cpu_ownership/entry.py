#!/usr/bin/env python3
"""M4 CPU entry integration fixture. Real inference remains hard-disabled.

This exercises the real guard/watch ownership path with a source-pinned dummy
workload. It does not accept the retired job or a model-bearing command.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
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


def _grant(path: Path, expected_region: str, deadline: float) -> None:
    fields = path.read_text().split()
    if len(fields) != 3:
        raise ValueError('grant must contain exactly three fields')
    pieces = [field.split('=', 1) for field in fields]
    if any(len(pair) != 2 for pair in pieces):
        raise ValueError('malformed grant')
    values = dict(pieces)
    if set(values) != {'regions', 'start', 'end'} or len(values) != 3:
        raise ValueError('invalid grant fields')
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
        plan = json.loads(a.plan.read_bytes())
        if plan.get('schema') != 'epyc.m4.cpu_entry_fixture.v1' or plan.get('mode') not in ('fixture', 'native-check'):
            raise ValueError('real M4 CPU execution remains disabled pending binding')
        mode = plan['mode']
        if mode == 'fixture':
            fixture = Path(plan['fixture']).resolve(strict=True)
            if not fixture.is_file() or _sha(fixture) != plan['fixture_sha256']:
                raise ValueError('fixture source changed')
            command = [sys.executable, '-B', str(fixture)]
        else:
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
        if not isinstance(plan.get('region'), str) or not plan['region']:
            raise ValueError('region missing')
        if not a.output.is_dir() or any(a.output.iterdir()):
            raise ValueError('output must be a fresh empty directory')
        _grant(a.grant, plan['region'], a.deadline)
        if a.stop.exists() or any(a.hold.glob('HOLD_*')):
            raise ValueError('STOP or HOLD before entry')
        grant_hash = _sha(a.grant)
        env = dict(os.environ, M4_DELEGATED_CGROUP_PARENT='/sys/fs/cgroup',
                   M4_OUTER_OWNER_PID=str(a.owner_pid), M4_OUTER_OWNER_BIRTH=str(a.owner_birth))
        rc = watch.run(command, a.grant, a.stop, a.hold,
                       a.deadline, a.output, env)
        _grant(a.grant, plan['region'], a.deadline)
        if _sha(a.grant) != grant_hash or a.stop.exists() or any(a.hold.glob('HOLD_*')):
            raise ValueError('final grant, STOP or HOLD check failed')
        if rc != 0:
            raise ValueError(f'workload incomplete: {rc}')
        with (a.output / 'FIXTURE-COMPLETE.json').open('x') as f:
            json.dump({'schema': 'epyc.m4.cpu_entry_fixture_complete.v1', 'plan_sha256': a.plan_sha256,
                       'mode': mode, 'measurement': False}, f)
        return 0
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as exc:
        print(f'REFUSED: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
