"""Actual cgroup tests use only captured PIDs and a unique owned group."""
import importlib.util
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import uuid

import pytest

MODULE = Path(__file__).resolve().parents[2] / 'scripts/benchmark/m4_cpu_ownership/m4_cgroup_guard.py'
spec = importlib.util.spec_from_file_location('m4_cgroup_guard', MODULE)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


@pytest.mark.parametrize('victim_owner', ['watcher', 'owner'])
def test_guard_drains_detached_work_after_identity_dies(victim_owner):
    cg = Path('/sys/fs/cgroup') / ('m4-private-' + uuid.uuid4().hex)
    cg.mkdir(mode=0o700)
    watcher = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])
    owner = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])
    unrelated = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])
    child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'], start_new_session=True)
    guardian = None
    ready_r, ready_w = os.pipe()
    done_r, done_w = os.pipe()
    try:
        (cg/'cgroup.procs').write_text(str(child.pid))
        guardian = subprocess.Popen([sys.executable, str(MODULE), '--cgroup', str(cg),
            '--watcher', str(watcher.pid), '--watcher-birth', str(guard.birth(watcher.pid)),
            '--owner', str(owner.pid), '--owner-birth', str(guard.birth(owner.pid)),
            '--ready-fd', str(ready_w), '--done-fd', str(done_r)], pass_fds=(ready_w, done_r))
        os.close(ready_w); ready_w = -1
        os.close(done_r); done_r = -1
        assert os.read(ready_r, 1) == b'R'
        captured = watcher if victim_owner == 'watcher' else owner
        captured.send_signal(signal.SIGKILL)
        captured.wait(timeout=5)
        assert guardian.wait(timeout=10) == 0
        child.wait(timeout=5)
        assert child.returncode == -signal.SIGKILL
        assert guard._empty(cg)
        assert unrelated.poll() is None
    finally:
        for fd in (ready_r, ready_w, done_r, done_w):
            if fd >= 0:
                os.close(fd)
        for proc in (guardian, child, watcher, owner, unrelated):
            if proc and proc.poll() is None:
                proc.kill(); proc.wait(timeout=5)
        if cg.exists():
            guard.drain(cg)
            cg.rmdir()


def test_mismatched_birth_refuses():
    with pytest.raises(RuntimeError, match='identity'):
        guard._pin_process(os.getpid(), guard.birth(os.getpid()) + 1)


def test_real_watcher_aborts_when_guardian_is_killed(tmp_path):
    import json
    own_dir = MODULE.parent
    out = tmp_path / 'output'; out.mkdir()
    grant = tmp_path / 'grant'; grant.write_text('authorized')
    stop = tmp_path / 'stop'; hold = tmp_path / 'hold'; hold.mkdir()
    helper = tmp_path / 'entry.py'
    helper.write_text('''import os, sys, time\nimport watch\nenv=dict(os.environ, M4_DELEGATED_CGROUP_PARENT='/sys/fs/cgroup', M4_OUTER_OWNER_PID=sys.argv[1], M4_OUTER_OWNER_BIRTH=sys.argv[2])\nraise SystemExit(watch.run([sys.executable,'-c','import time;time.sleep(60)'],sys.argv[3],sys.argv[4],sys.argv[5],time.time()+50,sys.argv[6],env))\n''')
    env = dict(os.environ, PYTHONPATH=str(own_dir))
    watch = subprocess.Popen([sys.executable, str(helper), str(os.getpid()), str(guard.birth(os.getpid())), str(grant), str(stop), str(hold), str(out)], env=env)
    try:
        deadline=time.monotonic()+5
        while time.monotonic()<deadline and not (out/'supervisor.json').exists():
            if watch.poll() is not None:
                raise AssertionError('watcher exited before child started')
            time.sleep(.02)
        guardian = json.loads((out/'guardian.json').read_text())
        supervisor = json.loads((out/'supervisor.json').read_text())
        assert guard.birth(guardian['pid']) == guardian['birth']
        pidfd = os.pidfd_open(guardian['pid'])
        try:
            signal.pidfd_send_signal(pidfd, signal.SIGKILL)
        finally:
            os.close(pidfd)
        assert watch.wait(timeout=15) != 0
        assert not Path('/proc', str(supervisor['pid'])).exists()
        result = json.loads((out/'watch-result.json').read_text())
        assert result.get('containment_empty') is True
        assert result.get('reason') == 'GUARDIAN_LOST'
    finally:
        if watch.poll() is None:
            watch.kill(); watch.wait(timeout=10)


def test_real_watcher_sigkill_drains_its_group(tmp_path):
    import json
    import select
    out = tmp_path / 'output'; out.mkdir()
    grant = tmp_path / 'grant'; grant.write_text('authorized')
    stop = tmp_path / 'stop'; hold = tmp_path / 'hold'; hold.mkdir()
    helper = tmp_path / 'entry.py'
    helper.write_text('''import os, sys, time\nimport watch\nenv=dict(os.environ, M4_DELEGATED_CGROUP_PARENT='/sys/fs/cgroup', M4_OUTER_OWNER_PID=sys.argv[1], M4_OUTER_OWNER_BIRTH=sys.argv[2])\nraise SystemExit(watch.run([sys.executable,'-c','import time;time.sleep(60)'],sys.argv[3],sys.argv[4],sys.argv[5],time.time()+50,sys.argv[6],env))\n''')
    watch = subprocess.Popen([sys.executable, str(helper), str(os.getpid()), str(guard.birth(os.getpid())), str(grant), str(stop), str(hold), str(out)], env=dict(os.environ, PYTHONPATH=str(MODULE.parent)))
    cg = None
    try:
        deadline=time.monotonic()+5
        while time.monotonic()<deadline and not (out/'supervisor.json').exists():
            if watch.poll() is not None:
                raise AssertionError('watcher exited before child started')
            time.sleep(.02)
        cg = Path(json.loads((out/'containment.json').read_text())['path'])
        guardian = json.loads((out/'guardian.json').read_text())
        supervisor = json.loads((out/'supervisor.json').read_text())
        assert guard.birth(guardian['pid']) == guardian['birth']
        assert guard.birth(supervisor['pid']) == supervisor['birth']
        guardian_fd = os.pidfd_open(guardian['pid'])
        supervisor_fd = os.pidfd_open(supervisor['pid'])
        try:
            watch.send_signal(signal.SIGKILL); watch.wait(timeout=5)
            assert select.select([supervisor_fd], [], [], 10)[0]
            assert select.select([guardian_fd], [], [], 10)[0]
            assert guard._empty(cg)
        finally:
            os.close(guardian_fd); os.close(supervisor_fd)
    finally:
        if watch.poll() is None:
            watch.kill(); watch.wait(timeout=5)
        if cg and cg.exists():
            guard.drain(cg); cg.rmdir()
