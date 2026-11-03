"""M4's lease verifier must preserve an exclusive GPU quiet claim."""
import fcntl
import importlib.util
import os
from pathlib import Path
import sys

import pytest

ROOT=Path(__file__).resolve().parents[2]
DIRECTORY=ROOT/'scripts/benchmark/m4_cpu_ownership'
sys.path.insert(0,str(DIRECTORY))
spec=importlib.util.spec_from_file_location('m4_lease_test',DIRECTORY/'lease_owner.py')
owner=importlib.util.module_from_spec(spec);spec.loader.exec_module(owner)


def test_exclusive_gpu_quiet_is_not_downgraded(tmp_path, monkeypatch):
    names=[f'cpu_region.GLOBAL.q{i}.lock' for i in range(4)]+['gpu_quiet.lock']
    handles=[(tmp_path/name).open('w') for name in names]
    try:
        for handle in handles: fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        fds={str(h.fileno()):'/mnt/raid0/llm/tmp/'+name for h,name in zip(handles,names,strict=True)}
        orig_listdir=os.listdir; orig_readlink=os.readlink
        monkeypatch.setattr(owner.os,'listdir',lambda p: list(fds) if p=='/proc/self/fd' else orig_listdir(p))
        monkeypatch.setattr(owner.os,'readlink',lambda p: fds[p.rsplit('/',1)[-1]] if p.startswith('/proc/self/fd/') else orig_readlink(p))
        assert set(owner.lease_fds('exclusive')) == {h.fileno() for h in handles}
        competitor=(tmp_path/'gpu_quiet.lock').open('r')
        try:
            with pytest.raises(BlockingIOError): fcntl.flock(competitor,fcntl.LOCK_SH|fcntl.LOCK_NB)
        finally: competitor.close()
    finally:
        for handle in handles: handle.close()


# Operator co-residency policy 2026-10-22: a shared GPU-quiet lease may run on a full-host grant without gpu-quiet;
# every other host-hold check stays strict.
def _host_grant(tmp_path, holds):
    import time
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    grant = tmp_path/'row.grant'
    grant.write_text('regions=0-95 start=' + (now-timedelta(minutes=1)).strftime('%Y-%m-%dT%H:%MZ')
                     + ' end=' + (now+timedelta(minutes=5)).strftime('%Y-%m-%dT%H:%MZ') + ' holds=' + holds)
    return grant, time.time() + 60


@pytest.mark.parametrize('mode,holds,ok', [
    ('shared', 'q0,q1,q2,q3', True),
    ('shared', 'q0,q1,q2,q3,gpu-quiet', True),
    ('exclusive', 'q0,q1,q2,q3,gpu-quiet', True),
    (None, 'q0,q1,q2,q3,gpu-quiet', True),
    ('exclusive', 'q0,q1,q2,q3', False),
    (None, 'q0,q1,q2,q3', False),
    ('shared', 'q0,q1,q2', False),
    ('shared', 'q0,q1,q2,q3,q3', False),
])
def test_host_holds_relaxed_only_under_shared_lease(tmp_path, monkeypatch, mode, holds, ok):
    import entry
    if mode is None: monkeypatch.delenv('M4_GPU_QUIET_MODE', raising=False)
    else: monkeypatch.setenv('M4_GPU_QUIET_MODE', mode)
    grant, deadline = _host_grant(tmp_path, holds)
    if ok:
        entry._grant(grant, '0-95', deadline, require_host_holds=True)
    else:
        with pytest.raises(ValueError, match='holds'):
            entry._grant(grant, '0-95', deadline, require_host_holds=True)
