#!/usr/bin/env python3
"""Draft single-arm coordinator. Native entry is intentionally disabled.

The owner must integrate process-tree cleanup and a bound runtime linkage check,
seal all fixtures and booking policy, then expose this through a keeper engine.
"""
import json
import os
import tempfile
import admission
from pathlib import Path


def _atomic_json(path, obj):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(dir=target.parent, prefix='.result-')
    try:
        with os.fdopen(fd, 'w') as out:
            json.dump(obj, out, allow_nan=False, sort_keys=True)
            out.write('\n')
            out.flush()
            os.fsync(out.fileno())
        os.replace(temp, target)
        dfd = os.open(target.parent, os.O_DIRECTORY)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def coordinate(config, lifecycle, aggregate):
    """Pure-injection seam for offline tests; no production entry enabled."""
    required = {'command','env','base_url','plan_path','fixture_root','output_dir',
                'arm','budget_s','minimum_cell_s','request_timeout_s','log_path',
                'result_path', 'stop_file', 'granted_cpus'}
    if set(config) != required:
        raise ValueError('configuration keys must match draft contract')
    if config['arm'] not in ('J', 'Y'):
        raise ValueError('invalid arm')
    run_args = {k: v for k, v in config.items() if k != 'result_path'}
    rc = lifecycle(**run_args)
    if rc not in (0, 1, 75):
        raise ValueError('unexpected lifecycle status')
    report = aggregate(config['plan_path'], config['output_dir'])
    # RC 0 means the selected arm has no unstarted cells, not campaign success.
    _atomic_json(config['result_path'], {'schema':'jetlong-segment-v1',
        'segment_rc':rc, 'arm':config['arm'], 'campaign':report})
    return rc


def coordinate_admitted(config, env, now, lifecycle, aggregate, *, startup_s, cleanup_s):
    """Validate a keeper envelope before delegating; draft only, not native entry.

    Native wiring must additionally check stop/deadline between cells, verify
    process-tree cleanup and source/build/fixture provenance, and prove the
    keeper admission path. This function is exercised with mocks only.
    """
    admitted = admission.validate(env, now=now,
        minimum_cell_s=config['minimum_cell_s'], startup_s=startup_s,
        cleanup_s=cleanup_s, result_path=config['result_path'])
    bound = dict(config, budget_s=admitted['budget_s'], granted_cpus=admitted['cpus'],
                 stop_file=admitted['stop_file'], result_path=admitted['result_path'])
    return coordinate(bound, lifecycle, aggregate)


def main():
    raise SystemExit('REFUSED: draft coordinator lacks sealed inputs, runtime provenance, verified descendant cleanup and keeper admission; do not publish')


if __name__ == '__main__':
    main()
