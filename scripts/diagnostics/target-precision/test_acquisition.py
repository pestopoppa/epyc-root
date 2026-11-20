import copy
import hashlib
import io
import json
from pathlib import Path

import pytest

import acquisition as acq

GIB = acq.GIB


@pytest.fixture
def plan():
    sources = []
    for name, data, field in [('shard', b'abcdefgh', 'sha256'), ('config.json', b'{}', 'git_blob_sha1')]:
        digest = (hashlib.sha256(data).hexdigest() if field == 'sha256' else
                  hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest())
        sources.append(dict(path=name, size=len(data), **{field: digest},
            url='https://huggingface.co/Qwen/Qwen3.8-27B/resolve/'+'a'*40+'/'+name))
    return dict(schema='epyc.target-precision.weight-plan.v1',
                base=dict(repo='Qwen/Qwen3.8-27B', revision='a'*40), sources=sources)


@pytest.fixture
def budget(tmp_path, monkeypatch):
    source, controls = tmp_path/'source', tmp_path/'controls'
    source.mkdir(); controls.mkdir()
    monkeypatch.setattr(acq, 'is_tmpfs', lambda p: p == source)
    monkeypatch.setattr(acq, 'free_bytes', lambda p: 1000*GIB)
    monkeypatch.setattr(acq.prep, 'host_memory_available', lambda: 1000*GIB)
    return acq.Budget(source, controls, 'tmpfs-intermediates')


@pytest.fixture
def transfer(budget, monkeypatch):
    calls = []
    def enter(leaf, cap):
        calls.append(('cgroup', cap))
        return Path(leaf)
    monkeypatch.setattr(acq, 'enter_leaf', enter)
    monkeypatch.setattr(acq.prep, '_events', lambda leaf: dict(max=0, oom=0, oom_kill=0))
    def urlopen(request, **kwargs):
        calls.append(('network', request))
        data = b'abcdefgh' if request.full_url.endswith('/shard') else b'{}'
        offset = int(request.headers.get('Range', 'bytes=0-')[6:-1])
        response = io.BytesIO(data[offset:])
        response.status = 206 if offset else 200
        response.headers = {'Content-Length': str(len(data)-offset),
                            'Content-Range': f'bytes {offset}-{len(data)-1}/{len(data)}'}
        return response
    monkeypatch.setattr(acq.urllib.request, 'urlopen', urlopen)
    return calls


def test_pinned_sha_and_git_payloads(plan, budget, transfer):
    receipt = acq.acquire(plan, budget, '/dedicated')
    assert receipt['status'] == 'COMPLETE' and len(receipt['files']) == 2
    assert receipt['memory_max_bytes'] == 4*GIB+10
    assert not receipt['verified_weights']
    assert transfer[0] == ('cgroup', 4*GIB+10)
    assert (budget.source/'shard').read_bytes() == b'abcdefgh'
    assert not list(budget.source.glob('*.part'))


def test_exact_range_retry_and_completed_reverification(plan, budget, transfer):
    (budget.source/'shard.part').write_bytes(b'abc')
    (budget.source/'config.json').write_bytes(b'{}')
    acq.acquire(plan, budget, '/dedicated')
    assert len(transfer) == 2
    assert transfer[1][1].headers['Range'] == 'bytes=3-'


@pytest.mark.parametrize('mode', ['length', 'range', 'status', 'oversized', 'short', 'corrupt'])
def test_bad_network_retains_unverified_prefix(plan, budget, transfer, monkeypatch, mode):
    (budget.source/'shard.part').write_bytes(b'abc')
    def response(request, **kwargs):
        value = io.BytesIO(b'defgh' if mode not in ('oversized', 'short', 'corrupt') else
                           {'oversized': b'defghi', 'short': b'defg', 'corrupt': b'xxxxx'}[mode])
        value.status = 200 if mode == 'status' else 206
        value.headers = {'Content-Length': '4' if mode == 'length' else '5',
                         'Content-Range': 'bad' if mode == 'range' else 'bytes 3-7/8'}
        return value
    monkeypatch.setattr(acq.urllib.request, 'urlopen', response)
    with pytest.raises(ValueError): acq.acquire(plan, budget, '/dedicated')
    assert not (budget.source/'shard').exists()
    assert (budget.source/'shard.part').exists()


def test_corrupt_completed_file_never_redownloaded(plan, budget, transfer):
    (budget.source/'shard').write_bytes(b'xxxxxxxx')
    with pytest.raises(ValueError, match='digest'): acq.acquire(plan, budget, '/dedicated')
    assert len(transfer) == 1


@pytest.mark.parametrize('mode', ['foreign', 'symlink', 'ambiguous', 'oversize'])
def test_unsafe_source_state_before_admission(plan, budget, transfer, mode):
    if mode == 'foreign': (budget.source/'foreign').write_bytes(b'')
    if mode == 'symlink': (budget.source/'shard').symlink_to('/absent')
    if mode == 'ambiguous':
        (budget.source/'shard').write_bytes(b'abcdefgh')
        (budget.source/'shard.part').write_bytes(b'abc')
    if mode == 'oversize': (budget.source/'shard.part').write_bytes(b'x'*9)
    with pytest.raises(ValueError): acq.acquire(plan, budget, '/dedicated')
    assert not transfer


@pytest.mark.parametrize('mode', ['revision', 'url', 'digest', 'traversal', 'duplicate', 'size'])
def test_unpinned_plan_before_admission(plan, budget, transfer, mode):
    if mode == 'revision': plan['base']['revision'] = 'main'
    if mode == 'url': plan['sources'][0]['url'] += '?other'
    if mode == 'digest': plan['sources'][0]['sha256'] = 'x'*64
    if mode == 'traversal': plan['sources'][0]['path'] = '../outside'
    if mode == 'duplicate': plan['sources'].append(copy.deepcopy(plan['sources'][0]))
    if mode == 'size': plan['sources'][0]['size'] = True
    with pytest.raises(ValueError): acq.acquire(plan, budget, '/dedicated')
    assert not transfer


def test_aggregate_same_volume_obligations(budget, monkeypatch):
    # Test directories share st_dev: one floor, both remaining obligations.
    monkeypatch.setattr(acq, 'free_bytes', lambda p: 150*GIB+GIB+10)
    budget.check(10)
    monkeypatch.setattr(acq, 'free_bytes', lambda p: 150*GIB+GIB+9)
    with pytest.raises(ValueError, match='per-volume'): budget.check(10)
    (budget.controls/'receipt').write_bytes(b'12345')
    budget.check(10)  # already-written control bytes reduce pending reserve


def test_separate_tmpfs_and_disk_floors(budget, monkeypatch):
    original = Path.stat
    def stat(path, *a, **k):
        if path == budget.source:
            value = original(path, *a, **k)
            return type('Stat', (), dict(st_dev=value.st_dev+1))()
        return original(path, *a, **k)
    monkeypatch.setattr(Path, 'stat', stat)
    monkeypatch.setattr(acq, 'free_bytes', lambda p: 10 if p == budget.source else 151*GIB)
    budget.check(10)
    with pytest.raises(ValueError): budget.check(11)
    monkeypatch.setattr(acq, 'free_bytes', lambda p: 10 if p == budget.source else 151*GIB-1)
    with pytest.raises(ValueError): budget.check(10)


def test_host_remaining_tmpfs_floor(budget, monkeypatch):
    monkeypatch.setattr(acq.prep, 'host_memory_available', lambda: 250*GIB+9)
    with pytest.raises(ValueError, match='host memory'): budget.check(10)
    budget.check(9)


def test_control_aggregate_cap_and_symlink(budget):
    budget.reserve = 4
    (budget.controls/'one').write_bytes(b'123')
    (budget.controls/'two').write_bytes(b'45')
    with pytest.raises(ValueError, match='aggregate'): budget.check(0)
    (budget.controls/'two').unlink()
    (budget.controls/'link').symlink_to('/absent')
    with pytest.raises(ValueError, match='unsafe'): budget.check(0)


@pytest.mark.parametrize('mode', ['disk', 'host', 'oom', 'deadline'])
def test_continuous_refusal_retains_partial(plan, budget, transfer, monkeypatch, mode):
    original = acq.urllib.request.urlopen
    def start(*a, **k):
        response = original(*a, **k)
        if mode == 'disk': monkeypatch.setattr(acq, 'free_bytes', lambda p: 0)
        if mode == 'host': monkeypatch.setattr(acq.prep, 'host_memory_available', lambda: 249*GIB)
        if mode == 'oom': monkeypatch.setattr(acq.prep, '_events', lambda p: dict(max=1))
        if mode == 'deadline': monkeypatch.setattr(acq.time, 'monotonic', lambda: 1e20)
        return response
    monkeypatch.setattr(acq.urllib.request, 'urlopen', start)
    with pytest.raises(ValueError): acq.acquire(plan, budget, '/dedicated')
    assert not (budget.source/'shard').exists()


def test_non_kernel_cgroup_refused_before_network(plan, budget, monkeypatch):
    def no_network(*a, **k): pytest.fail('network before cgroup admission')
    monkeypatch.setattr(acq.urllib.request, 'urlopen', no_network)
    with pytest.raises(ValueError, match='kernel cgroup'):
        acq.acquire(plan, budget, budget.controls)


@pytest.mark.parametrize('mode', ['durable', 'controls_tmpfs', 'nested', 'symlink'])
def test_explicit_placement_refusals(budget, monkeypatch, mode):
    if mode == 'controls_tmpfs': monkeypatch.setattr(acq, 'is_tmpfs', lambda p: True)
    source, controls = budget.source, budget.controls
    if mode == 'nested': controls = source
    if mode == 'symlink':
        source = source.parent/'alias'
        source.symlink_to(budget.source, target_is_directory=True)
    with pytest.raises(ValueError):
        acq.Budget(source, controls, 'durable' if mode == 'durable' else 'tmpfs-intermediates')


def test_production_manifest_is_supported():
    path = Path(__file__).resolve().parents[3]/'docs/reports/target-precision-acquisition/matched-source-plan-20261120.json'
    assert len(acq.source_list(json.loads(path.read_text()))) == 25


def test_event_has_reserved_space(budget):
    budget.reserve = acq.EVENT_CAP+4
    (budget.controls/'existing').write_bytes(b'1234')
    budget.check(0)
    (budget.controls/'extra').write_bytes(b'x')
    with pytest.raises(ValueError, match='aggregate'): budget.check(0)


def test_cli_records_admission_failure_without_network(budget, plan, monkeypatch):
    source_plan = budget.controls/'plan.json'
    source_plan.write_text(json.dumps(plan))
    event = budget.controls/'event.json'
    monkeypatch.setattr('sys.argv', ['acquisition.py', '--plan', str(source_plan),
        '--source', str(budget.source), '--controls', str(budget.controls),
        '--cgroup', str(budget.controls), '--placement', 'tmpfs-intermediates', '--event', str(event)])
    def no_network(*a, **k): pytest.fail('network before cgroup admission')
    monkeypatch.setattr(acq.urllib.request, 'urlopen', no_network)
    assert acq.main() == 1
    result = json.loads(event.read_text())
    assert result['status'] == 'FAILED' and 'kernel cgroup' in result['error']
    with pytest.raises(ValueError, match='fresh event'): acq.main()
