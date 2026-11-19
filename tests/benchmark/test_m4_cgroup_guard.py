"""Real watcher tests: captured PIDs only, a unique owned cgroup or a private session."""
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import uuid

MODULE = Path(__file__).resolve().parents[2] / 'scripts/benchmark/m4_cpu_ownership/m4_cgroup_guard.py'
spec = importlib.util.spec_from_file_location('m4_cgroup_guard', MODULE)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)

HELPER = '''import os, sys, time
import watch
env=dict(os.environ)
if sys.argv[1]: env['M4_DELEGATED_CGROUP_PARENT']=sys.argv[1]
else: env.pop('M4_DELEGATED_CGROUP_PARENT',None)
env.pop('M4_OWNED_CGROUP',None)
raise SystemExit(watch.run([sys.executable,'-c',sys.argv[2]],sys.argv[3],sys.argv[4],sys.argv[5],time.time()+float(sys.argv[7]),sys.argv[6],env))
'''


def watcher(tmp_path, parent, code, deadline_s=20):
    out = tmp_path / 'output'; out.mkdir()
    grant = tmp_path / 'grant'; grant.write_text('authorized')
    stop = tmp_path / 'stop'; hold = tmp_path / 'hold'; hold.mkdir()
    helper = tmp_path / 'entry.py'; helper.write_text(HELPER)
    env = {k: v for k, v in os.environ.items() if k != 'M4_OWNED_CGROUP'}
    env['PYTHONPATH'] = str(MODULE.parent)
    argv = [sys.executable, str(helper), parent, code, str(grant), str(stop), str(hold), str(out), str(deadline_s)]
    return argv, env, out, stop


def test_drain_kills_detached_member():
    cg = Path('/sys/fs/cgroup') / ('m4-private-' + uuid.uuid4().hex)
    cg.mkdir(mode=0o700)
    child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'], start_new_session=True)
    try:
        (cg/'cgroup.procs').write_text(str(child.pid))
        guard.drain(cg)
        child.wait(timeout=5)
        assert child.returncode == -signal.SIGKILL and guard._empty(cg)
    finally:
        if child.poll() is None: child.kill(); child.wait(timeout=5)
        if cg.exists(): guard.drain(cg); cg.rmdir()


def test_cgroup_watcher_success_closes_and_removes_group(tmp_path):
    argv, env, out, _ = watcher(tmp_path, '/sys/fs/cgroup', 'pass')
    result = subprocess.run(argv, env=env, capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr
    recorded = json.loads((out/'watch-result.json').read_text())
    assert recorded['status'] == 'closed' and recorded['containment_empty'] is True
    assert recorded['containment'] == 'cgroup'
    assert not Path(json.loads((out/'containment.json').read_text())['path']).exists()


def test_cgroup_watcher_stop_kills_detached_descendant(tmp_path):
    code = ('import subprocess,sys,time;subprocess.Popen([sys.executable,"-c","import time;time.sleep(60)"],'
            'start_new_session=True);time.sleep(60)')
    argv, env, out, stop = watcher(tmp_path, '/sys/fs/cgroup', code)
    proc = subprocess.Popen(argv, env=env)
    try:
        end = time.monotonic() + 5
        while time.monotonic() < end and not (out/'supervisor.json').exists(): time.sleep(.02)
        time.sleep(.3); stop.touch()
        assert proc.wait(timeout=20) == 124
        recorded = json.loads((out/'watch-result.json').read_text())
        assert recorded['reason'] == 'STOP' and recorded['containment_empty'] is True
    finally:
        if proc.poll() is None: proc.kill(); proc.wait(timeout=5)


def test_bare_run_without_owned_cgroup_starts_and_drains_session(tmp_path):
    # No delegated cgroup, no M4_OWNED_CGROUP: the run must start (no KeyError) and
    # cleanup must still reach the workload's whole session.
    marker = tmp_path / 'started'
    code = (f'import os,pathlib,subprocess,sys,time;assert "M4_OWNED_CGROUP" not in os.environ;'
            f'assert os.environ["M4_SERVER_PID_REGISTRY"];'
            f'subprocess.Popen([sys.executable,"-c","import time;time.sleep(60)"]);'
            f'pathlib.Path({str(marker)!r}).write_text("x");time.sleep(60)')
    argv, env, out, stop = watcher(tmp_path, '', code)
    proc = subprocess.Popen(argv, env=env)
    try:
        end = time.monotonic() + 10
        while time.monotonic() < end and not marker.exists():
            assert proc.poll() is None, 'watcher exited before workload started'
            time.sleep(.02)
        assert marker.exists()
        sid = json.loads((out/'supervisor.json').read_text())['pid']
        stop.touch()
        assert proc.wait(timeout=30) == 124
        recorded = json.loads((out/'watch-result.json').read_text())
        assert recorded['containment'] == 'session' and recorded['containment_empty'] is True
        assert recorded['reason'] == 'STOP' and recorded['status'] == 'closed'
        assert not [p for p in os.listdir('/proc') if p.isdigit() and _sid(int(p)) == sid]
    finally:
        if proc.poll() is None: proc.kill(); proc.wait(timeout=5)


def test_bare_run_success_returns_child_rc(tmp_path):
    argv, env, out, _ = watcher(tmp_path, '', 'raise SystemExit(0)')
    result = subprocess.run(argv, env=env, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert json.loads((out/'watch-result.json').read_text())['containment'] == 'session'


def _sid(pid):
    try: return os.getsid(pid)
    except OSError: return None
