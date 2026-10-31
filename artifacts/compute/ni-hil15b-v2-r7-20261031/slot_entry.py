#!/usr/bin/env python3
"""One native HIL15a driver attempt at an explicit frozen repeat index.

The native driver has no repeat-start CLI. This shim changes only its run_all
loop's index origin, keeping all native setup, grading, writers, and verification.
Its input is a one-task JSON array containing exact bytes from the frozen set.
"""
import argparse
import importlib.util
import os
from pathlib import Path
import sys

DRIVER = Path('/mnt/raid0/llm/worktrees/mains/codex-ni-orchestrator/scripts/trace/hil15a_flagon_run.py')
DRIVER_SHA256 = '75abff0842a550051b3a25f3bf079a505044120a9ee57e80cc08ef2661bb4c63'


async def one_slot(native, repeat_index, tasks, repeats, deps_for, state_cls, run_task, max_wall_s=None):
    if len(tasks) != 1 or repeats != 1:
        raise RuntimeError('slot entry requires one exact task and one repeat')
    t = tasks[0]
    rid = f"{t['task_key']}-r{repeat_index}"
    import time
    state = state_cls(task_id=rid, prompt=t['prompt'], context=t['prompt'])
    start, err = time.time(), None
    try:
        result = await run_task(state, deps_for(t, rid), start_role=t.get('start_role', 'frontdoor'))
        answer = getattr(result, 'answer', None)
    except Exception as exc:
        answer, err = None, f'{type(exc).__name__}: {exc}'[:300]
    passed = err is None and native.grade(t, answer)
    return ({rid: [t['task_key'], passed]}, [
        {'run_id': rid, 'task_key': t['task_key'], 'pass': passed,
         'answer': None if answer is None else str(answer)[:300],
         'error': err, 'wall_s': round(time.time() - start, 3)}
    ])


def main():
    import hashlib
    if hashlib.sha256(DRIVER.read_bytes()).hexdigest() != DRIVER_SHA256:
        raise SystemExit('native driver bytes changed')
    p = argparse.ArgumentParser()
    p.add_argument('--repeat-index', type=int, required=True)
    p.add_argument('driver_args', nargs=argparse.REMAINDER)
    a = p.parse_args()
    if a.repeat_index not in (0, 1, 2):
        raise SystemExit('repeat index outside frozen 0..2')
    spec = importlib.util.spec_from_file_location('hil15a_native', DRIVER)
    native = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = native
    spec.loader.exec_module(native)

    async def run_selected(tasks, repeats, deps_for, state_cls, run_task, max_wall_s=None):
        return await one_slot(native, a.repeat_index, tasks, repeats, deps_for, state_cls, run_task, max_wall_s)

    native.run_all = run_selected
    driver_args = a.driver_args[1:] if a.driver_args[:1] == ['--'] else a.driver_args
    return native.main(driver_args)


if __name__ == '__main__':
    raise SystemExit(main())
