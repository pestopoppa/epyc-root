from pathlib import Path

import pytest

import cgroup_leaf as cg


@pytest.fixture
def delegated(tmp_path, monkeypatch):
    parent = tmp_path/'delegated'
    parent.mkdir()
    for name, value in {'cgroup.type': 'domain', 'cgroup.subtree_control': 'memory cpu',
                        'cgroup.procs': ''}.items():
        (parent/name).write_text(value)
    monkeypatch.setattr(cg, '_mounted_cgroup2', lambda p: None)
    def create(leaf):
        leaf.mkdir()
        for name, value in {'memory.max': 'max', 'memory.swap.max': 'max',
                            'memory.oom.group': '0', 'memory.events': 'oom 0\n',
                            'cgroup.procs': ''}.items():
            (leaf/name).write_text(value)
    monkeypatch.setattr(cg, '_new_leaf', create)
    # Emulate kernfs replacement semantics rather than regular-file overwrite.
    monkeypatch.setattr(cg, '_write_control', lambda p, v: p.write_text(str(v)))
    return parent


def test_new_leaf_only(delegated):
    before = {p.name: p.read_bytes() for p in delegated.iterdir()}
    result = cg.provision(delegated, 'df2-tp-acquire', 4096)
    assert result['status'] == 'CONFIGURED'
    assert not result['execution_admitted'] and not result['processes_moved']
    assert result['inode'] == Path(result['path']).stat().st_ino
    assert {name: (delegated/name).read_bytes() for name in before} == before
    with pytest.raises(FileExistsError): cg.provision(delegated, 'df2-tp-acquire', 4096)


@pytest.mark.parametrize('name', ['../other', 'shared', 'df2-tp-', 'df2-tp-x/y', 'df2-tp-X'])
def test_names_refuse(delegated, name):
    with pytest.raises(ValueError): cg.provision(delegated, name, 4096)
    assert len(list(delegated.iterdir())) == 3


@pytest.mark.parametrize('control,value', [('cgroup.type', 'threaded'),
    ('cgroup.subtree_control', 'cpu'), ('cgroup.procs', '123')])
def test_parent_refusals(delegated, control, value):
    (delegated/control).write_text(value)
    with pytest.raises(ValueError): cg.provision(delegated, 'df2-tp-x', 4096)
    assert not (delegated/'df2-tp-x').exists()


def test_symlink_ancestor_refused(delegated):
    alias = delegated.parent/'alias'
    alias.symlink_to(delegated, target_is_directory=True)
    with pytest.raises(ValueError): cg.provision(alias, 'df2-tp-x', 4096)


def test_parent_control_symlink_refused(delegated):
    (delegated/'cgroup.procs').unlink()
    (delegated/'cgroup.procs').symlink_to(delegated/'cgroup.type')
    with pytest.raises(ValueError): cg.provision(delegated, 'df2-tp-x', 4096)


@pytest.mark.parametrize('cap', [True, 0, -1, '4096'])
def test_bad_cap(delegated, cap):
    with pytest.raises(ValueError): cg.provision(delegated, 'df2-tp-x', cap)


def test_failed_configuration_retained(delegated, monkeypatch):
    def fail(path, value): raise PermissionError('not delegated')
    monkeypatch.setattr(cg, '_write_control', fail)
    with pytest.raises(PermissionError): cg.provision(delegated, 'df2-tp-x', 4096)
    assert (delegated/'df2-tp-x').is_dir()
    with pytest.raises(FileExistsError): cg.provision(delegated, 'df2-tp-x', 4096)


def test_writer_never_creates_control(tmp_path):
    with pytest.raises(FileNotFoundError): cg._write_control(tmp_path/'absent', 1)
    assert not (tmp_path/'absent').exists()


def test_writer_refuses_symlink(tmp_path):
    target = tmp_path/'target'
    target.write_text('unchanged')
    link = tmp_path/'control'
    link.symlink_to(target)
    with pytest.raises(OSError): cg._write_control(link, 1)
    assert target.read_text() == 'unchanged'


def test_real_non_cgroup_mount_refused(tmp_path):
    with pytest.raises(ValueError, match='cgroup2'): cg._mounted_cgroup2(tmp_path)
