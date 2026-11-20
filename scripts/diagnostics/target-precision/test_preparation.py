import copy
import json
import os
import signal
from pathlib import Path

import pytest

import preparation as prep

GIB = prep.GIB
ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def sizing():
    return json.loads((ROOT/'docs/reports/target-precision-acquisition/converter-sizing-20261120.json').read_text())


def test_serial_peak_and_exact_boundary(sizing):
    plan = prep.preparation_schedule(sizing, 1000*GIB)
    required = plan['required_free_bytes']
    assert required == 150*GIB+GIB+sum(sizing['output_cap_bytes'].values())
    assert required < sizing['required_free_bytes']
    assert prep.preparation_schedule(sizing, required)['disk_envelope_fits']
    assert not prep.preparation_schedule(sizing, required-1)['disk_envelope_fits']
    assert not plan['execution_admitted']
    assert [s['name'] for s in plan['steps']] == [
        'acquire', 'convert', 'release_verified_source', 'quantize_Q8_0', 'quantize_Q4_K_M']
    assert plan['steps'][1]['memory_max_bytes'] == 128*GIB
    assert plan['steps'][3]['memory_max_bytes'] == 64*GIB
    assert len(plan['source_release_gate']) == 4


def test_conversion_can_dominate_peak(sizing):
    sizing['source_bytes'] = 500*GIB
    plan = prep.preparation_schedule(sizing, 1000*GIB)
    assert plan['required_free_bytes'] == 651*GIB+sizing['output_cap_bytes']['BF16']


@pytest.mark.parametrize('mutation', ['schema', 'source', 'floor', 'caps', 'boolcap', 'workspace'])
def test_plan_refusals(sizing, mutation):
    if mutation == 'schema': sizing['schema'] = 'unknown'
    if mutation == 'source': sizing['source_bytes'] = -1
    if mutation == 'floor': sizing['disk_floor_bytes'] = 149*GIB
    if mutation == 'caps': del sizing['output_cap_bytes']['BF16']
    if mutation == 'boolcap': sizing['output_cap_bytes']['BF16'] = True
    if mutation == 'workspace': sizing['workspace']['extra_disk_bytes'] = 1
    with pytest.raises(ValueError): prep.preparation_schedule(sizing, 1000*GIB)


@pytest.fixture
def leaf(tmp_path):
    leaf = tmp_path/'leaf'
    leaf.mkdir()
    for name, text in {'cgroup.procs': '', 'memory.max': str(64*GIB),
                       'memory.swap.max': '0', 'memory.oom.group': '1',
                       'memory.events': 'max 0\noom 0\noom_kill 0\n'}.items():
        (leaf/name).write_text(text)
    return leaf


def test_total_memory_not_logical_workspace(leaf):
    assert prep.check_cgroup(leaf, 64*GIB) == leaf
    assert prep._events(leaf) == dict(max=0, oom=0, oom_kill=0)


@pytest.mark.parametrize('name,value', [('cgroup.procs', '123'), ('memory.max', 'max'),
    ('memory.max', str(63*GIB)), ('memory.swap.max', '1'), ('memory.oom.group', '0')])
def test_cgroup_refusals(leaf, name, value):
    (leaf/name).write_text(value)
    with pytest.raises(ValueError): prep.check_cgroup(leaf, 64*GIB)


def test_cgroup_symlinks_refuse(leaf):
    p = leaf/'memory.max'
    p.unlink()
    p.symlink_to(leaf/'memory.swap.max')
    with pytest.raises(ValueError): prep.check_cgroup(leaf, 64*GIB)


def test_disk_counts_remaining_output_once(tmp_path):
    output = tmp_path/'out'
    output.write_bytes(b'1234')
    prep.check_disk(output, 10, 150*GIB, 150*GIB+6)
    with pytest.raises(ValueError): prep.check_disk(output, 10, 150*GIB, 150*GIB+5)
    with pytest.raises(ValueError): prep.check_disk(output, 3, 150*GIB, 1000*GIB)
    with pytest.raises(ValueError): prep.check_disk(output, 10, 149*GIB, 1000*GIB)


def test_output_symlink_refused(tmp_path):
    p = tmp_path/'out'
    p.symlink_to(tmp_path/'absent')
    with pytest.raises(ValueError): prep.check_disk(p, 10, 150*GIB, 1000*GIB)


@pytest.fixture
def fake_run(tmp_path, leaf, monkeypatch):
    output = tmp_path/'out'
    monkeypatch.setattr(prep, 'host_memory_available', lambda: 1000*GIB)
    calls = []
    class Child:
        pid = 123456
        def __init__(self, argv, **kwargs):
            calls.append(('launch', argv, kwargs))
            self.rc = 0
            reader, writer = os.pipe()
            os.write(writer, b'original tool output\n')
            os.close(writer)
            self.stdout = os.fdopen(reader, 'rb')
            output.write_bytes(b'GGUF')
        def poll(self):
            return self.rc
        def wait(self, **kwargs):
            calls.append(('wait', kwargs))
            return self.rc
    monkeypatch.setattr(prep.subprocess, 'Popen', Child)
    monkeypatch.setattr(prep.os, 'killpg', lambda pid, sig: calls.append(('kill', pid, sig)))
    monkeypatch.setattr(prep.os, 'statvfs', lambda path: type('Stat', (), dict(f_bavail=1000*GIB, f_frsize=1))())
    kwargs = dict(output=output, output_cap_bytes=100, cgroup=leaf, memory_max_bytes=64*GIB)
    return kwargs, calls


def test_bounded_command_success_is_not_weight_receipt(fake_run):
    kwargs, calls = fake_run
    result = prep.run_bounded(['audited-tool'], **kwargs)
    assert result['output_bytes'] == 4 and not result['verified_weights']
    assert kwargs['output'].with_suffix('.log').read_bytes() == b'original tool output\n'
    assert ('kill', 123456, signal.SIGKILL) in calls
    assert calls[-1] == ('wait', {})


def test_child_enters_cgroup_before_exec(fake_run, monkeypatch):
    kwargs, calls = fake_run
    prep.run_bounded(['tool'], **kwargs)
    child_setup = calls[0][2]['preexec_fn']
    # A fake regular directory cannot attest kernel cgroup membership.
    with pytest.raises(RuntimeError, match='membership'):
        child_setup()


@pytest.mark.parametrize('mode', ['memory', 'oom', 'badrc', 'oversize', 'missing', 'timeout', 'disk', 'hostdrop'])
def test_failed_child_reaped(fake_run, monkeypatch, mode):
    kwargs, calls = fake_run
    original = prep.subprocess.Popen
    def start(*a, **k):
        child = original(*a, **k)
        if mode == 'oom': (kwargs['cgroup']/'memory.events').write_text('max 1\noom 1\noom_kill 1\n')
        if mode == 'badrc': child.rc = 1
        if mode == 'oversize': kwargs['output'].write_bytes(b'x'*101)
        if mode == 'missing': kwargs['output'].unlink()
        if mode == 'disk': monkeypatch.setattr(prep.os, 'statvfs', lambda p: type('Stat', (), dict(f_bavail=1, f_frsize=1))())
        if mode == 'hostdrop': monkeypatch.setattr(prep, 'host_memory_available', lambda: 249*GIB)
        return child
    monkeypatch.setattr(prep.subprocess, 'Popen', start)
    if mode == 'memory': monkeypatch.setattr(prep, 'host_memory_available', lambda: 300*GIB)
    if mode == 'timeout': kwargs['timeout_s'] = 1e-12
    with pytest.raises(ValueError): prep.run_bounded(['tool'], **kwargs)
    if mode == 'memory': assert not calls
    else:
        assert ('kill', 123456, signal.SIGKILL) in calls
        assert calls[-1] == ('wait', {})


def test_no_launch_over_existing_output(fake_run):
    kwargs, calls = fake_run
    kwargs['output'].write_bytes(b'retained')
    with pytest.raises(ValueError): prep.run_bounded(['tool'], **kwargs)
    assert not calls


def test_log_hard_cap_reaps_child(fake_run):
    kwargs, calls = fake_run
    kwargs['log_cap_bytes'] = 2
    with pytest.raises(ValueError, match='log cap'):
        prep.run_bounded(['tool'], **kwargs)
    assert kwargs['output'].with_suffix('.log').stat().st_size == 0
    assert calls[-1] == ('wait', {})


def test_log_must_be_fresh_and_separate(fake_run):
    kwargs, calls = fake_run
    kwargs['log_path'] = kwargs['output']
    with pytest.raises(ValueError): prep.run_bounded(['tool'], **kwargs)
    assert not calls



def test_explicit_volatile_placement_separately_budgets_ram_tmpfs_disk(sizing):
    plan = prep.preparation_schedule(sizing, 300*GIB, placement='tmpfs-intermediates',
                                     tmpfs_available_bytes=500*GIB, host_available_bytes=1000*GIB)
    assert plan['resource_envelope_fits'] and not plan['execution_admitted']
    assert plan['required_free_bytes'] == 151*GIB+sum(
        sizing['output_cap_bytes'][arm] for arm in ['Q8_0', 'Q4_K_M'])
    assert plan['tmpfs_peak_bytes'] == sizing['source_bytes']+sizing['output_cap_bytes']['BF16']
    assert plan['host_required_bytes'] == 378*GIB+plan['tmpfs_peak_bytes']
    assert plan['steps'][-1]['tmpfs_bytes'] == sizing['output_cap_bytes']['BF16']
    assert 'reboot' in plan['volatile_recovery']
    for key, value in [('available_bytes', plan['required_free_bytes']-1),
                       ('tmpfs_available_bytes', plan['tmpfs_required_free_bytes']-1),
                       ('host_available_bytes', plan['host_required_bytes']-1)]:
        kwargs = dict(available_bytes=300*GIB, placement='tmpfs-intermediates',
                      tmpfs_available_bytes=500*GIB, host_available_bytes=1000*GIB)
        kwargs[key] = value
        assert not prep.preparation_schedule(sizing, **kwargs)['resource_envelope_fits']


def test_volatile_placement_requires_explicit_capacity(sizing):
    assert not prep.preparation_schedule(sizing, 1000*GIB, placement='tmpfs-intermediates')['resource_envelope_fits']
    with pytest.raises(ValueError): prep.preparation_schedule(sizing, 1000*GIB, placement='other')
