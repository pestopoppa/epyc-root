#!/usr/bin/env python3
"""One-shot, bounded R6 admission watcher. Foreground only; parent review required."""
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

home = Path(__file__).resolve().parent
fixture = home / 'fixture'
supervisor = Path('/mnt/raid0/llm/tmp/codex3-ap66-20261031/supervisor-esrch-fix/prep_supervisor.py')
admission = supervisor.with_name('prep_admission.py')
python = '/home/daniele/.local/share/uv/python/cpython-3.11-linux-x86_64-gnu/bin/python3.11'
site = '/mnt/raid0/llm/epyc-orchestrator/.venv/lib/python3.11/site-packages'
lockpath = Path('/mnt/raid0/llm/tmp/compute-flags/prep-locks/30-31.lock')
attempt = home / ('attempt-' + time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()) + '-' + str(os.getpid()))
attempt.mkdir(mode=0o700)
terminal = attempt / 'terminal.json'

def finish(value):
    tmp = terminal.with_suffix('.tmp')
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
    os.replace(tmp, terminal)

def sigterm(signum, frame):
    raise InterruptedError(f'signal {signum}')
signal.signal(signal.SIGTERM, sigterm)
signal.signal(signal.SIGINT, sigterm)

def manifest():
    paths = sorted(p for p in (fixture / 'dashboard').rglob('*')
                   if p.is_file() and '__pycache__' not in p.parts and not p.is_symlink())
    paths += [fixture / 'tests/test_dashboard_panels.py',
              fixture / 'tests/test_dashboard_kernel_rnd_merge.py',
              supervisor, admission, home / 'run_controls.py', Path(__file__).resolve()]
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}

result = {'schema': 'p66-admission-attempt-v1', 'state': 'FAILURE',
          'watcher_pid': os.getpid(), 'started_utc': time.strftime('%FT%TZ', time.gmtime())}
try:
    result['watcher_birth'] = int(Path(f'/proc/{os.getpid()}/stat').read_text().rsplit(') ', 1)[1].split()[19])
    before = manifest()
    (attempt / 'hashes-before.json').write_text(json.dumps(before, indent=2, sort_keys=True) + '\n')
    spec = importlib.util.spec_from_file_location('prep_admission', admission)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    deadline = time.monotonic() + 3600
    candidates = ((30, 31), (54, 55), (78, 79), (6, 7), (126, 127))
    acquired = False
    with lockpath.open('a+') as lock:
        while time.monotonic() < deadline:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                time.sleep(5)
                continue
            pair = None
            for candidate in candidates:
                try:
                    mod.live(set(candidate))
                    pair = candidate
                    break
                except (ValueError, OSError):
                    continue
            if pair is None:
                fcntl.flock(lock, fcntl.LOCK_UN)
                time.sleep(5)
                continue
            acquired = True
            lock.seek(0)
            lock.truncate()
            lock.write(','.join(map(str, pair)) + '\n')
            lock.flush()
            result['cpus'] = list(pair)
            if manifest() != before:
                raise RuntimeError('source or guard changed before launch')
            env = os.environ.copy()
            env.update({'OMP_NUM_THREADS': '1', 'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1',
                        'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONPATH': str(fixture) + ':' + site,
                        'P66_ATTEMPT': str(attempt)})
            cmd = ['/usr/bin/taskset', '-c', ','.join(map(str, pair)), '/usr/bin/python3',
                   str(supervisor), '900', '--', python, str(home / 'run_controls.py')]
            result['argv'] = cmd
            with (attempt / 'stdout.log').open('w') as out, (attempt / 'stderr.log').open('w') as err:
                proc = subprocess.Popen(cmd, cwd=fixture, env=env, stdout=out, stderr=err)
                result['supervisor_pid'] = proc.pid
                try:
                    result['supervisor_birth'] = int(Path(f'/proc/{proc.pid}/stat').read_text().rsplit(') ', 1)[1].split()[19])
                except FileNotFoundError:
                    result['supervisor_birth'] = None
                try:
                    result['returncode'] = proc.wait()
                except BaseException:
                    # The captured supervisor owns and drains its descendants on SIGTERM.
                    if proc.poll() is None:
                        proc.terminate()
                    proc.wait()
                    raise
            break
    if not acquired:
        raise TimeoutError('admission or original mutex unavailable for 3600 seconds')
    after = manifest()
    (attempt / 'hashes-after.json').write_text(json.dumps(after, indent=2, sort_keys=True) + '\n')
    if after != before:
        raise RuntimeError('source or guard changed during controls')
    if result['returncode'] != 0:
        raise RuntimeError('supervisor or controls failed; see logs')
    result['state'] = 'SUCCESS'
except BaseException as exc:
    result['error'] = f'{type(exc).__name__}: {exc}'
finally:
    try:
        (attempt / 'hashes-final.json').write_text(
            json.dumps(manifest(), indent=2, sort_keys=True) + '\n')
    except BaseException as exc:
        result['state'] = 'FAILURE'
        result['final_hash_error'] = f'{type(exc).__name__}: {exc}'
    result['finished_utc'] = time.strftime('%FT%TZ', time.gmtime())
    finish(result)
print(json.dumps(result, sort_keys=True), flush=True)
sys.exit(0 if result['state'] == 'SUCCESS' else 1)
