import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys

import pytest

import acquisition_supervisor as sup
from test_acquisition import budget, plan  # shared tiny pinned inputs, no network


@pytest.fixture
def setup_worker(budget, plan, monkeypatch):
    plan_path = budget.controls/'plan.json'
    raw = json.dumps(plan).encode()
    plan_path.write_bytes(raw)
    event = budget.controls/'terminal.json'
    leaf = budget.controls/'fake-leaf'
    monkeypatch.setattr(sup, 'validate_leaf', lambda *a: leaf)
    monkeypatch.setattr(sup.acq.prep, '_events', lambda p: {})
    return raw, plan_path, event


def run(budget, setup_worker, **kwargs):
    raw, path, event = setup_worker
    result = sup.supervise(raw, path, budget, '/unused', event, **kwargs)
    assert json.loads(event.read_text()) == result
    assert event.stat().st_size == sup.acq.EVENT_CAP
    assert not event.with_name(event.name+'.reserved').exists()
    return result


def fake_worker(monkeypatch, code):
    original = subprocess.Popen
    captured = []
    def launch(argv, **kwargs):
        child = original([sys.executable, '-c', code], **kwargs)
        captured.append(child)
        return child
    monkeypatch.setattr(sup.subprocess, 'Popen', launch)
    return captured


def test_real_worker_sigkill_gets_durable_failure(budget, setup_worker, monkeypatch):
    children = fake_worker(monkeypatch, 'import os,signal; os.kill(os.getpid(),signal.SIGKILL)')
    result = run(budget, setup_worker)
    assert result['status'] == 'FAILED' and 'exit -9' in result['error']
    assert result['worker_returncode'] == -signal.SIGKILL and result['worker_reaped']
    with pytest.raises(ProcessLookupError): os.kill(children[0].pid, 0)


@pytest.mark.parametrize('mode', ['disk', 'host', 'oom', 'deadline'])
def test_external_checks_drain_blocked_worker(budget, setup_worker, monkeypatch, mode):
    # No transfer progress or worker cooperation is needed for parent checks.
    children = fake_worker(monkeypatch, 'import signal; signal.pause()')
    original = sup.subprocess.Popen
    def launch(*args, **kwargs):
        child = original(*args, **kwargs)
        if mode == 'disk': monkeypatch.setattr(sup.acq, 'free_bytes', lambda p: 0)
        if mode == 'host': monkeypatch.setattr(sup.acq.prep, 'host_memory_available', lambda: 0)
        if mode == 'oom': monkeypatch.setattr(sup.acq.prep, '_events', lambda p: {'oom_kill': 1})
        if mode == 'deadline': monkeypatch.setattr(sup.time, 'monotonic', lambda: 1e20)
        return child
    monkeypatch.setattr(sup.subprocess, 'Popen', launch)
    result = run(budget, setup_worker)
    assert result['status'] == 'FAILED' and result['worker_reaped']
    assert result['worker_returncode'] is not None
    with pytest.raises(ProcessLookupError): os.kill(children[0].pid, 0)


def test_root_admission_failure_is_persisted_without_launch(budget, setup_worker, monkeypatch):
    monkeypatch.setattr(sup, 'validate_leaf', lambda *a: (_ for _ in ()).throw(ValueError('dedicated leaf required')))
    monkeypatch.setattr(sup.subprocess, 'Popen', lambda *a, **k: pytest.fail('launched before admission'))
    result = run(budget, setup_worker)
    assert result['status'] == 'FAILED' and 'dedicated leaf' in result['error']


@pytest.mark.parametrize('mode', ['missing', 'foreign-plan', 'incomplete', 'bad-file', 'valid'])
def test_zero_exit_requires_bound_completion(budget, plan, setup_worker, monkeypatch, mode):
    raw, path, event = setup_worker
    worker_event = event.with_name(event.name+'.worker')
    if mode != 'incomplete':
        (budget.source/'shard').write_bytes(b'abcdefgh')
        (budget.source/'config.json').write_bytes(b'{}')
    records = [dict(source=s, path=str(budget.source/s['path']), size=s['size'],
                    sha256=hashlib.sha256(data).hexdigest())
               for s, data in zip(plan['sources'], [b'abcdefgh', b'{}'])]
    if mode == 'bad-file': records[0]['sha256'] = '0'*64
    receipt = dict(status='COMPLETE', verified_weights=False, files=records,
                   plan_sha256='bad' if mode == 'foreign-plan' else hashlib.sha256(raw).hexdigest())
    code = 'pass' if mode == 'missing' else f'from pathlib import Path; Path({str(worker_event)!r}).write_text({json.dumps(receipt)!r})'
    fake_worker(monkeypatch, code)
    result = run(budget, setup_worker)
    assert (result['status'] == 'COMPLETE') == (mode == 'valid')


def test_existing_event_not_overwritten(budget, setup_worker):
    raw, path, event = setup_worker
    event.write_text('original')
    with pytest.raises(ValueError, match='fresh event'):
        sup.supervise(raw, path, budget, '/unused', event)
    assert event.read_text() == 'original'


def test_real_kernel_root_refused():
    with pytest.raises(ValueError, match='dedicated kernel'):
        sup.validate_leaf('/sys/fs/cgroup', 4*sup.acq.GIB)


def test_changed_plan_refused_before_launch(budget, setup_worker, monkeypatch):
    setup_worker[1].write_text('{}')
    monkeypatch.setattr(sup.subprocess, 'Popen', lambda *a, **k: pytest.fail('plan drift launched'))
    result = run(budget, setup_worker)
    assert result['status'] == 'FAILED' and 'plan changed' in result['error']
