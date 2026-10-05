"""H4 single-writer discipline for autopilot_state.json.

autopilot_state.json is a whole-file JSON rewritten by 5+ independent processes
(autopilot daemon, dashboard API, host_health cache-flush, config_applicator,
archiver). Atomic tmp+os.replace prevents torn reads but NOT lost updates: a
whole-file write based on a stale read clobbers another writer's committed
change. These tests pin the fix:

  * the daemon's periodic (merge_control) save re-reads out-of-band control
    fields under the write lock and MERGES them before writing, so an operator /
    dashboard / host_health pause set while a trial was in flight SURVIVES;
  * every wrapped writer serializes on scripts.autopilot.state_lock;
  * host_health / config_applicator take the lock for a BRIEF read-modify-write
    and RELEASE it across their ~11s sleep — never holding it across the sleep.
"""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import json
import os
import sys
from pathlib import Path
from unittest import mock

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "autopilot"))

import autopilot  # noqa: E402
import config_applicator  # noqa: E402
import host_health  # noqa: E402
import state_lock  # noqa: E402


# ───────── STEP 4: daemon merge-under-lock (the correctness heart) ──────────


def test_daemon_merge_save_preserves_out_of_band_pause(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """DECISIVE: an out-of-band pause written to disk survives the daemon save.

    Reproduces the H4 incoherence: the daemon holds state IN MEMORY (paused=False,
    stale) and periodically overwrites the disk file. Between the daemon's last
    save and its next one, a dashboard/operator/host_health pause writes paused=True
    (+ pause_reason) straight to disk. The daemon's merge_control save must re-read
    those control fields UNDER THE LOCK and keep them — while retaining its own
    ownership of trial/frontier counters.
    """
    sp = tmp_path / "autopilot_state.json"
    monkeypatch.setattr(autopilot, "STATE_PATH", sp)

    # Daemon persisted trial 100, not paused.
    in_memory = {"trial_counter": 100, "paused": False, "frontier_size": 7}
    autopilot.save_state(dict(in_memory))

    # OUT-OF-BAND: a pause is written directly to disk by another process.
    disk = json.loads(sp.read_text())
    disk["paused"] = True
    disk["pause_reason"] = "operator pause via dashboard"
    sp.write_text(json.dumps(disk))

    # Daemon advances a trial in memory (still paused=False in memory) and does
    # its periodic merge-aware save.
    in_memory["trial_counter"] = 101
    autopilot.save_state(in_memory, merge_control=True)

    out = json.loads(sp.read_text())
    assert out["paused"] is True  # out-of-band pause SURVIVED (not clobbered)
    assert out["pause_reason"] == "operator pause via dashboard"  # reason preserved
    assert out["trial_counter"] == 101  # daemon keeps counter ownership
    assert out["frontier_size"] == 7  # daemon keeps frontier ownership


def test_daemon_save_without_merge_would_clobber(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Negative control: without merge_control the stale save loses the pause.

    Documents WHY merge_control is load-bearing — a plain daemon save writes the
    stale in-memory paused=False over the out-of-band paused=True on disk.
    """
    sp = tmp_path / "autopilot_state.json"
    monkeypatch.setattr(autopilot, "STATE_PATH", sp)

    autopilot.save_state({"trial_counter": 100, "paused": False})
    disk = json.loads(sp.read_text())
    disk["paused"] = True
    sp.write_text(json.dumps(disk))

    # merge_control defaults False (used by daemon internal-pause / CLI paths).
    autopilot.save_state({"trial_counter": 101, "paused": False})

    assert json.loads(sp.read_text())["paused"] is False  # clobbered (the H4 bug)


def test_daemon_merge_does_not_clobber_daemon_internal_pause(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """merge only overrides when disk DIFFERS; equal disk state leaves memory be."""
    sp = tmp_path / "autopilot_state.json"
    monkeypatch.setattr(autopilot, "STATE_PATH", sp)

    # Disk already reflects paused=True (e.g. daemon persisted its own safety pause).
    autopilot.save_state({"trial_counter": 5, "paused": True})
    # Daemon in memory also paused=True, advancing counter.
    autopilot.save_state({"trial_counter": 6, "paused": True}, merge_control=True)

    out = json.loads(sp.read_text())
    assert out["paused"] is True
    assert out["trial_counter"] == 6


# ───────── STEP 2: every wrapped writer serializes on the lock ──────────


def test_save_state_acquires_write_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sp = tmp_path / "autopilot_state.json"
    monkeypatch.setattr(autopilot, "STATE_PATH", sp)

    acquisitions: list[Path] = []

    @contextlib.contextmanager
    def spy(path, *args, **kwargs):
        acquisitions.append(Path(os.fspath(path)))
        yield True

    monkeypatch.setattr(autopilot, "state_write_lock", spy)
    autopilot.save_state({"trial_counter": 1})

    assert acquisitions == [sp]


def test_save_state_lock_false_skips_reacquire(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """_lock=False lets a caller that already holds the lock write without a
    reentrant (self-blocking) second flock acquisition."""
    sp = tmp_path / "autopilot_state.json"
    monkeypatch.setattr(autopilot, "STATE_PATH", sp)

    acquisitions: list[Path] = []

    @contextlib.contextmanager
    def spy(path, *args, **kwargs):
        acquisitions.append(Path(os.fspath(path)))
        yield True

    monkeypatch.setattr(autopilot, "state_write_lock", spy)
    autopilot.save_state({"trial_counter": 2}, _lock=False)

    assert acquisitions == []  # did NOT acquire — caller owns the lock
    assert json.loads(sp.read_text())["trial_counter"] == 2  # still wrote


def _single_lock_spy(module, monkeypatch):
    """Replace ``module.state_write_lock`` with a spy over the REAL lock and
    return the list recording each acquisition path. Bounds the real acquire
    timeout so a reentrancy regression fails fast instead of hanging ~10s."""
    real = module.state_write_lock
    acquisitions: list[Path] = []

    @contextlib.contextmanager
    def spy(path, *args, **kwargs):
        acquisitions.append(Path(os.fspath(path)))
        with real(path, timeout=0.5) as held:
            yield held

    monkeypatch.setattr(module, "state_write_lock", spy)
    return acquisitions


def test_cmd_pause_holds_single_lock_across_rmw(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sp = tmp_path / "autopilot_state.json"
    monkeypatch.setattr(autopilot, "STATE_PATH", sp)
    autopilot.save_state({"trial_counter": 5, "paused": False})

    acquisitions = _single_lock_spy(autopilot, monkeypatch)
    autopilot.cmd_pause(argparse.Namespace())

    # Exactly one acquisition wraps the whole load->modify->save (the inner
    # save_state runs with _lock=False, so it does NOT re-acquire).
    assert acquisitions == [sp]
    assert json.loads(sp.read_text())["paused"] is True


def test_cmd_resume_holds_single_lock_across_rmw(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sp = tmp_path / "autopilot_state.json"
    monkeypatch.setattr(autopilot, "STATE_PATH", sp)
    autopilot.save_state({"trial_counter": 5, "paused": True, "pause_reason": "x"})

    acquisitions = _single_lock_spy(autopilot, monkeypatch)
    autopilot.cmd_resume(argparse.Namespace())

    assert acquisitions == [sp]
    out = json.loads(sp.read_text())
    assert out["paused"] is False
    assert "pause_reason" not in out


# ───────── STEP 3: host_health / config_applicator do NOT hold across sleep ──


def _lock_depth_spy(module, monkeypatch):
    """Spy that tracks lock nesting depth over the REAL lock, returning
    (acquisitions, depth) where depth['n'] is the count of locks currently held."""
    real = module.state_write_lock
    acquisitions: list[Path] = []
    depth = {"n": 0}

    @contextlib.contextmanager
    def spy(path, *args, **kwargs):
        acquisitions.append(Path(os.fspath(path)))
        depth["n"] += 1
        try:
            with real(path, timeout=0.5) as held:
                yield held
        finally:
            depth["n"] -= 1

    monkeypatch.setattr(module, "state_write_lock", spy)
    return acquisitions, depth


def test_host_health_flush_brackets_sleep_with_two_locked_rmws(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sp = tmp_path / "state.json"
    sp.write_text(json.dumps({"paused": False, "trial_counter": 1}))

    acquisitions, depth = _lock_depth_spy(host_health, monkeypatch)
    sleep_depths: list[int] = []

    with (
        mock.patch.object(host_health, "remediate", return_value=True),
        mock.patch.object(host_health, "_numa_interleave_rewarm", return_value={}),
        mock.patch("time.sleep", side_effect=lambda _s: sleep_depths.append(depth["n"])),
    ):
        result = host_health.flush_cache_with_pause(state_path=sp, rewarm=False)

    assert result["flush_ok"] is True
    # Two brief locked RMWs: set-pause and restore-pause.
    assert len(acquisitions) == 2
    # The ~11s grace sleep runs with NO lock held (bracketed by the two RMWs).
    assert sleep_depths == [0]
    assert json.loads(sp.read_text())["paused"] is False


def test_host_health_lock_is_free_during_sleep(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Independent probe: another fd can take the flock during the sleep window."""
    sp = tmp_path / "state.json"
    sp.write_text(json.dumps({"paused": False, "trial_counter": 1}))
    lock_path = f"{sp}.lock"
    free_during_sleep: dict[str, bool] = {}

    def probe(_seconds):
        fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o644)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            free_during_sleep["free"] = True
            fcntl.flock(fd, fcntl.LOCK_UN)
        except OSError:
            free_during_sleep["free"] = False
        finally:
            os.close(fd)

    with (
        mock.patch.object(host_health, "remediate", return_value=True),
        mock.patch.object(host_health, "_numa_interleave_rewarm", return_value={}),
        mock.patch("time.sleep", side_effect=probe),
    ):
        host_health.flush_cache_with_pause(state_path=sp, rewarm=False)

    assert free_during_sleep.get("free") is True


def test_config_applicator_pause_releases_lock_before_grace_sleep(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sp = tmp_path / "autopilot_state.json"
    sp.write_text(json.dumps({"paused": False}))

    acquisitions, depth = _lock_depth_spy(config_applicator, monkeypatch)
    sleep_depths: list[int] = []
    monkeypatch.setattr(
        config_applicator.time, "sleep", lambda _s: sleep_depths.append(depth["n"])
    )

    result = config_applicator._pause_autopilot_dispatch(state_path=sp, grace_s=11.0)

    assert result["paused_set"] is True
    assert len(acquisitions) == 1  # one brief locked RMW to set the pause flag
    assert sleep_depths == [0]  # grace sleep runs unlocked
    assert json.loads(sp.read_text())["paused"] is True


def test_config_applicator_restore_takes_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The restore now clears only a pause whose LEASE it still holds (see
    # tests/unit/test_autopilot_pause_apply_interlock.py), so the fixture has to
    # be a pause this applicator actually took. The H4 property this test was
    # written for is unchanged: the restore is one locked read-modify-write.
    sp = tmp_path / "autopilot_state.json"
    leased: dict = {}
    token = state_lock.claim_pause_lease(leased, config_applicator.DISPATCH_PAUSE_OWNER)
    sp.write_text(json.dumps(leased))

    acquisitions, _ = _lock_depth_spy(config_applicator, monkeypatch)
    result = config_applicator._restore_autopilot_dispatch_pause(
        {
            "status": "ok",
            "state_path": str(sp),
            "paused_set": True,
            "paused_pre": False,
            "pause_token": token,
        }
    )

    assert result["restored"] is True
    assert acquisitions == [sp]
    assert json.loads(sp.read_text())["paused"] is False


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q", "-p", "no:xdist"]))
