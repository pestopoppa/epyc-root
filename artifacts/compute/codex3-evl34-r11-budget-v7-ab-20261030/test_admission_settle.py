import datetime

import campaign_smoke as smoke


def setup_guard(tmp_path, monkeypatch):
    flags = tmp_path / 'flags'
    (flags / 'grants').mkdir(parents=True)
    (flags / 'FILLERS.md').write_text('')
    monkeypatch.setattr(smoke, 'FLAGS', flags)
    monkeypatch.setattr(smoke, 'D', tmp_path)
    monkeypatch.setattr(smoke, 'last', [0.0, True])
    clock = [10.0]
    monkeypatch.setattr(smoke.time, 'monotonic', lambda: clock[0])
    monkeypatch.setattr(smoke.time, 'sleep', lambda s: clock.__setitem__(0, clock[0] + s))
    now = datetime.datetime.now(datetime.timezone.utc)
    grant = flags / 'grants' / 'gpu.grant'
    grant.write_text(f"start={(now-datetime.timedelta(minutes=1)).isoformat()} end={(now+datetime.timedelta(minutes=1)).isoformat()} regions=mi210_0\n")
    return flags, grant, clock


def test_removed_old_grant_settles_without_cached_block(tmp_path, monkeypatch):
    flags, grant, clock = setup_guard(tmp_path, monkeypatch)
    def sleep(seconds):
        clock[0] += seconds
        grant.unlink(missing_ok=True)
    monkeypatch.setattr(smoke.time, 'sleep', sleep)
    assert smoke.admission_clear()
    assert 0 < clock[0] - 10 < 1.5


def test_unknown_gpu_grant_never_bypassed(tmp_path, monkeypatch):
    flags, grant, clock = setup_guard(tmp_path, monkeypatch)
    assert not smoke.admission_clear()
    assert 1.5 <= clock[0] - 10 < 1.6
    assert grant.exists()


def test_stop_and_hold_refuse_immediately(tmp_path, monkeypatch):
    flags, grant, clock = setup_guard(tmp_path, monkeypatch)
    for path in (tmp_path / 'STOP', flags / 'HOLD_test'):
        path.touch()
        assert not smoke.admission_clear()
        assert clock[0] == 10
        path.unlink()


def test_forced_recheck_sees_new_grant_despite_cached_clear(tmp_path, monkeypatch):
    flags, grant, clock = setup_guard(tmp_path, monkeypatch)
    data = grant.read_text()
    grant.unlink()
    assert not smoke.stopped(force=True)
    grant.write_text(data)
    assert smoke.stopped(force=True)


def set_grant_class(flags, name, grant_class):
    cells = [name] + ['x'] * 7 + [grant_class] + ['x'] * 9
    (flags / 'FILLERS.md').write_text('| ' + ' | '.join(cells) + ' |\n')


def test_correctness_and_diagnostic_gpu_metadata_allowed_after_lock(tmp_path, monkeypatch):
    flags, grant, clock = setup_guard(tmp_path, monkeypatch)
    for kind in ('block-correctness', 'diagnostic'):
        set_grant_class(flags, 'gpu', kind)
        assert smoke.admission_clear()
        assert grant.exists()


def test_timing_gpu_metadata_refused(tmp_path, monkeypatch):
    flags, grant, clock = setup_guard(tmp_path, monkeypatch)
    set_grant_class(flags, 'gpu', 'timing')
    assert not smoke.admission_clear()
    assert grant.exists()
