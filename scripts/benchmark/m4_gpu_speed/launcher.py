"""Run the enrolled native M4 GPU sweep inside the shared cgroup guardian."""
from __future__ import annotations
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'm4_cpu_ownership'))
import watch
import write_capture


def main():
    # Read-only plan binding and authoritative grant check precede containment.
    env = dict(os.environ)
    if any(env.get(k) for k in ('PYTHONPATH', 'PYTHONHOME', 'PYTHONSTARTUP', 'PYTHONINSPECT')):
        raise RuntimeError('unbound Python execution override')
    trust = write_capture.enrolled()
    plan = trust.plan()
    key = env['M4_PLAN_CELL']
    cell = plan['cells'][key]
    write_capture.grant_proof(cell, env)
    if not sys.argv[1:]:
        raise SystemExit('expected native server_np_sweep arguments')
    output = Path(env['M4_WATCH_DIR']).resolve(strict=True)
    if str(output / 'watch-result.json') != cell.get('watch_result_path'):
        raise RuntimeError('watch output does not match enrolled plan')
    if trust.capture_root != output and trust.capture_root not in output.parents:
        raise RuntimeError('watch output outside approved capture root')
    grants_dir, hold_dir = write_capture.grant_directories(env)
    grant = Path(grants_dir) / (cell['grant']['id'] + '.grant')
    command = [sys.executable, '-s', '-B', str(Path(__file__).with_name('server_np_sweep.py')), *sys.argv[1:]]
    return watch.run(command, grant, env['FILLER_STOPFILE'], hold_dir,
                     int(env['FILLER_DEADLINE']), output, env=env)


if __name__ == '__main__':
    raise SystemExit(main())
