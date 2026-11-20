"""Model-free process-observer tests; fabricated maps are not run evidence."""
import copy
import hashlib
import importlib.util
import os
from pathlib import Path
import subprocess

import pytest

spec = importlib.util.spec_from_file_location('precision_runtime_test', Path(__file__).with_name('runtime.py'))
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)


@pytest.fixture
def observed(tmp_path):
    library = tmp_path / 'libggml-hip.so'
    library.write_bytes(b'fixture library, no model')
    s = library.stat()
    proc = tmp_path / 'proc'
    child = proc / '123'
    child.mkdir(parents=True)
    (child / 'stat').write_text('123 (fixture (child)) S ' + '0 ' * 18 + '42 0')
    (child / 'maps').write_text(f'1-2 r-xp 00000000 {os.major(s.st_dev):02x}:{os.minor(s.st_dev):02x} {s.st_ino} {library}\n')
    kfd = tmp_path / 'kfd'
    (kfd / '123').mkdir(parents=True)
    (kfd / '123/vram_7').write_text('4096')
    libraries = {str(library): hashlib.sha256(library.read_bytes()).hexdigest()}
    plan = dict(backend='hip', admission={'runtime_proof': {'mapped_library_sha256': libraries}})
    snapshot = runtime.snapshot
    def sample():
        return snapshot(123, libraries, 'hip', {}, proc, kfd)
    return sample, plan, child, kfd, library


def record_for(observed):
    sample, plan, *_ = observed
    first, second = sample(), sample()
    return dict(schema=runtime.SCHEMA, request={'case':'fixture'}, owner_pid=99,
                child_pid=123, samples=[first, second], returncode=0), plan


def test_own_pid_mapping_digest_and_hip_samples_replay(observed):
    record, plan = record_for(observed)
    assert runtime.validate(record, plan, {'case':'fixture'}) == record
    assert record['samples'][0]['vram'] == {'vram_7': 4096}


@pytest.mark.parametrize('failure', ['wrong-digest', 'wrong-inode', 'foreign-library', 'deleted', 'no-map', 'zero-vram', 'no-kfd', 'zombie', 'symlink'])
def test_snapshot_refuses_false_residency(observed, failure):
    sample, plan, child, kfd, library = observed
    if failure == 'wrong-digest':
        plan['admission']['runtime_proof']['mapped_library_sha256'][str(library)] = '0'*64
    elif failure == 'wrong-inode':
        (child/'maps').write_text((child/'maps').read_text().replace(str(library.stat().st_ino), '0'))
    elif failure == 'foreign-library':
        with (child/'maps').open('a') as stream:
            stream.write('1-2 r-xp 0 00:01 2 /foreign/libggml-cpu.so\n')
    elif failure == 'deleted':
        (child/'maps').write_text((child/'maps').read_text().rstrip()+' (deleted)\n')
    elif failure == 'no-map':
        (child/'maps').write_text('')
    elif failure == 'zero-vram':
        (kfd/'123/vram_7').write_text('0')
    elif failure == 'no-kfd':
        (kfd/'123/vram_7').unlink()
        (kfd/'123').rmdir()
    elif failure == 'zombie':
        (child/'stat').write_text((child/'stat').read_text().replace(' S ', ' Z '))
    elif failure == 'symlink':
        saved = library.with_suffix('.saved')
        library.rename(saved)
        library.symlink_to(saved)
    with pytest.raises((ValueError, OSError)):
        sample()


@pytest.mark.parametrize('change', [
    lambda r: r.update(request={}),
    lambda r: r.update(owner_pid=123),
    lambda r: r.update(samples=r['samples'][:1]),
    lambda r: r.update(returncode=7),
    lambda r: r.update(timed_out=True),
    lambda r: r.update(fatal_error='foreign library'),
    lambda r: r['samples'][1].update(pid=124),
    lambda r: r['samples'][1].update(start_ticks=43),
    lambda r: r['samples'][1].update(monotonic_ns=0),
    lambda r: r['samples'][1].update(maps=''),
    lambda r: r['samples'][1].update(libraries={}),
    lambda r: r['samples'][1].update(kfd_registered=False),
    lambda r: r['samples'][1].update(vram={'vram_7':0}),
])
def test_replay_refuses_cross_cell_missing_or_edited_observations(observed, change):
    record, plan = record_for(observed)
    change(record)
    with pytest.raises(ValueError):
        runtime.validate(record, plan, {'case':'fixture'})


def test_replay_refuses_inode_tamper(observed):
    record, plan = record_for(observed)
    for identity in record['samples'][1]['libraries'].values():
        identity['inode'] += 1
    with pytest.raises(ValueError, match='inode mismatch'):
        runtime.validate(record, plan, {'case':'fixture'})


@pytest.mark.parametrize('mode', ['timeout', 'fatal-mapping'])
def test_execute_captures_only_spawned_pid_and_reaps_timeout(observed, monkeypatch, mode):
    sample, plan, *_ = observed
    evidence = sample()
    class Child:
        pid = 123
        returncode = None
        killed = False
        reaped = False
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def poll(self): return None
        def wait(self, timeout=None):
            if not self.killed:
                raise subprocess.TimeoutExpired('fixture', timeout)
            self.reaped = True
            self.returncode = -9
        def kill(self): self.killed = True
    child = Child()
    monkeypatch.setattr(runtime.subprocess, 'Popen', lambda *a, **k: child)
    def snapshot(pid, *args):
        assert pid == 123
        if mode == 'fatal-mapping':
            raise ValueError('mapped library digest mismatch')
        return copy.deepcopy(evidence)
    monkeypatch.setattr(runtime, 'snapshot', snapshot)
    times = iter([0, 1])
    monkeypatch.setattr(runtime.time, 'monotonic', lambda: next(times))
    record = runtime.execute(['fixture'], {}, None, None, .5, plan, {'case':'fixture'})
    assert child.killed and child.reaped
    assert record['returncode'] == -9 and record['child_pid'] == 123
    if mode == 'timeout':
        assert record['timed_out'] and record['samples']
    else:
        assert record['fatal_error'] == 'mapped library digest mismatch'


def test_hash_cache_detects_changed_library(observed):
    _, plan, child, kfd, library = observed
    cache = {}
    runtime.snapshot(123, plan['admission']['runtime_proof']['mapped_library_sha256'], 'hip', cache, child.parent, kfd)
    library.write_bytes(b'changed fixture library')
    with pytest.raises(ValueError, match='digest mismatch'):
        runtime.snapshot(123, plan['admission']['runtime_proof']['mapped_library_sha256'], 'hip', cache, child.parent, kfd)


def test_cpu_panel_refuses_accelerator_library(observed):
    record, plan = record_for(observed)
    plan['backend'] = 'cpu'
    with pytest.raises(ValueError, match='accelerator'):
        runtime.validate(record, plan, {'case':'fixture'})


def test_execute_collects_two_observations_without_repeated_unbounded_records(observed, monkeypatch):
    sample, plan, *_ = observed
    class Child:
        pid = 123
        returncode = None
        waits = 0
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def poll(self): return self.returncode
        def wait(self, timeout=None):
            self.waits += 1
            if self.waits < 4:
                raise subprocess.TimeoutExpired('fixture', timeout)
            self.returncode = 0
    child = Child()
    monkeypatch.setattr(runtime.subprocess, 'Popen', lambda *a, **k: child)
    monkeypatch.setattr(runtime, 'snapshot', lambda pid, *a: sample() if pid == 123 else pytest.fail('foreign PID'))
    record = runtime.execute(['fixture'], {}, None, None, 10, plan, {'case':'fixture'})
    assert record['attempts'] == 4 and len(record['samples']) == 2
    runtime.validate(record, plan, {'case':'fixture'})
