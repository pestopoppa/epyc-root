"""Single-writer ownership of daemon-owned autopilot_state.json fields.

The prohibition — "external processes must never write daemon-owned state fields
while the daemon lives" — was PROSE until 2026-08-12: a comment above
``_EXTERNAL_CONTROL_FIELDS`` and a hand-rolled ``pgrep`` gate inside exactly one
operator script. It had already cost a 59-minute E8 calibration on 2026-08-03,
written correctly, reported APPLIED, and destroyed by the daemon's next save.

These tests pin the enforcement in ``scripts/autopilot/state_ownership.py`` in
BOTH directions:

  * a violation is REFUSED — an external process changing a daemon-owned field
    while the AutoPilot singleton lock is held raises, and the state file on disk
    is left byte-identical;
  * the compliant paths still WORK — the daemon writes its own state, an
    out-of-band pause writes control fields, and every writer proceeds normally
    once the daemon is absent.

The ownership question is answered by the kernel (``/proc/locks`` names the PID
holding ``orchestration/.autopilot.lock``), never by anything a caller declares
about itself, and never by scanning source text — so a doc or a test naming these
fields is unaffected by construction.
"""

from __future__ import annotations

import fcntl
import json
import os
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "autopilot"))

import state_ownership as so  # noqa: E402
import state_store  # noqa: E402


# ── fixtures / helpers ──────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _clean_ownership_baseline():
    """The last-written baseline is process-global; isolate every test from it."""
    so.forget_writes()
    yield
    so.forget_writes()


def _state_dir(tmp_path: Path) -> tuple[Path, Path]:
    orchestration = tmp_path / "orchestration"
    orchestration.mkdir()
    return orchestration / "autopilot_state.json", orchestration / so.DAEMON_LOCK_NAME


def _write_state(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2))


class _SelfHeldLock:
    """Hold the daemon lock in THIS process, so /proc/locks attributes it to us."""

    def __init__(self, lock_path: Path) -> None:
        self._path = lock_path
        self._fd: int | None = None

    def __enter__(self) -> "_SelfHeldLock":
        self._fd = os.open(self._path, os.O_CREAT | os.O_RDWR, 0o644)
        fcntl.flock(self._fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return self

    def __exit__(self, *exc: object) -> None:
        if self._fd is not None:
            fcntl.flock(self._fd, fcntl.LOCK_UN)
            os.close(self._fd)


_HOLDER_SRC = textwrap.dedent(
    """
    import fcntl, os, sys, time
    fd = os.open(sys.argv[1], os.O_CREAT | os.O_RDWR, 0o644)
    fcntl.flock(fd, fcntl.LOCK_EX)
    sys.stdout.write("held\\n")
    sys.stdout.flush()
    time.sleep(float(sys.argv[2]))
    """
)


class _ForeignHeldLock:
    """Hold the daemon lock in a SEPARATE process — the real-world shape."""

    def __init__(self, lock_path: Path, ttl: float = 30.0) -> None:
        self._path = lock_path
        self._ttl = ttl
        self._proc: subprocess.Popen | None = None

    def __enter__(self) -> int:
        self._proc = subprocess.Popen(
            [sys.executable, "-c", _HOLDER_SRC, str(self._path), str(self._ttl)],
            stdout=subprocess.PIPE,
            text=True,
        )
        assert self._proc.stdout is not None
        deadline = time.monotonic() + 10.0
        while time.monotonic() < deadline:
            if self._proc.stdout.readline().strip() == "held":
                return self._proc.pid
            if self._proc.poll() is not None:
                break
        raise AssertionError("lock holder subprocess never reported holding the lock")

    def __exit__(self, *exc: object) -> None:
        if self._proc is not None and self._proc.poll() is None:
            self._proc.terminate()
            self._proc.wait(timeout=10)


# ── the field-ownership declaration itself ──────────────────────────────────


def test_daemon_owned_and_control_field_sets_are_disjoint() -> None:
    """The guard must not forbid its own idiom.

    Out-of-band control fields are written by the dashboard / host_health /
    config_applicator / operator CLI *while the daemon runs* — that is the design.
    If any of them were also declared daemon-owned, this enforcement would refuse
    the pause path it exists to protect.
    """
    overlap = set(so.DAEMON_OWNED_STATE_FIELDS) & set(so.KNOWN_EXTERNAL_CONTROL_FIELDS)
    assert overlap == set(), f"field claimed by both owners: {sorted(overlap)}"
    assert so.DAEMON_OWNED_STATE_FIELDS, "the ownership declaration must not be empty"


def test_autopilot_control_fields_agree_with_the_ownership_declaration() -> None:
    """Cross-module pin: the daemon's live merge set must not touch daemon-owned keys.

    ``autopilot._EXTERNAL_CONTROL_FIELDS`` is the set the daemon actually re-reads
    from disk before overwriting the file. If a daemon-owned field were ever added
    there the guard and the daemon would disagree about who owns it, which is the
    ambiguity that produced the 2026-08-03 loss in the first place.
    """
    import autopilot  # imported lazily: it is an expensive module

    live = set(autopilot._EXTERNAL_CONTROL_FIELDS)
    assert live, "the daemon's merge set must not be empty"
    assert live & set(so.DAEMON_OWNED_STATE_FIELDS) == set()
    assert live <= set(so.KNOWN_EXTERNAL_CONTROL_FIELDS), (
        "autopilot gained an out-of-band control field the ownership declaration "
        f"does not know about: {sorted(live - set(so.KNOWN_EXTERNAL_CONTROL_FIELDS))}"
    )


def test_lock_derived_from_the_state_path_is_the_daemons_real_singleton_lock() -> None:
    """The guard must probe the lock the daemon actually takes, not a lookalike.

    Ownership is derived by locating ``.autopilot.lock`` next to the state file.
    If ``autopilot`` ever moved either path the derivation would quietly probe a
    file nobody holds, and every external write would be waved through — a check
    that passes because it is looking in the wrong place.
    """
    import autopilot  # imported lazily: it is an expensive module

    assert so.daemon_lock_path_for(autopilot.STATE_PATH) == autopilot.LOCK_PATH


# ── who holds the lock ──────────────────────────────────────────────────────


def test_lock_holder_is_empty_when_the_lock_file_is_free(tmp_path: Path) -> None:
    _state_path, lock_path = _state_dir(tmp_path)
    lock_path.touch()
    assert so.daemon_lock_holder_pids(lock_path) == set()
    assert so.process_is_daemon(lock_path) is False


def test_lock_held_by_a_separate_process_is_attributed_to_that_pid(
    tmp_path: Path,
) -> None:
    """Not an artifact of same-process flock semantics: a real other process holds it.

    ``flock`` conflicts with its own process across two fds, so a same-process test
    could pass while the real cross-process case failed. This pins the real shape:
    the holder PID is the child's, and this process is therefore NOT the daemon.
    """
    _state_path, lock_path = _state_dir(tmp_path)
    with _ForeignHeldLock(lock_path) as holder_pid:
        assert so.daemon_lock_holder_pids(lock_path) == {holder_pid}
        assert holder_pid != os.getpid()
        assert so.process_is_daemon(lock_path) is False


def test_self_held_lock_identifies_this_process_as_the_daemon(tmp_path: Path) -> None:
    _state_path, lock_path = _state_dir(tmp_path)
    with _SelfHeldLock(lock_path):
        assert so.daemon_lock_holder_pids(lock_path) == {os.getpid()}
        assert so.process_is_daemon(lock_path) is True


def test_read_state_file_returns_none_for_corrupt_or_absent_json(tmp_path: Path) -> None:
    state_path, _lock = _state_dir(tmp_path)
    assert so.read_state_file(state_path) is None
    state_path.write_text("{not json")
    assert so.read_state_file(state_path) is None


# ── layer 1: the violation is refused ───────────────────────────────────────


def test_external_write_of_daemon_owned_field_is_refused_while_daemon_runs(
    tmp_path: Path,
) -> None:
    """THE DECISIVE CASE — the 2026-08-03 loss, reproduced and now refused."""
    state_path, lock_path = _state_dir(tmp_path)
    _write_state(state_path, {"baseline_state": {"quality": 0.51}, "trial_counter": 9})

    with _ForeignHeldLock(lock_path):
        with pytest.raises(so.DaemonOwnedStateWriteError) as excinfo:
            so.assert_external_write_allowed(
                state_path,
                {"baseline_state": {"quality": 0.83}, "trial_counter": 9},
            )
    assert "baseline_state" in str(excinfo.value)
    assert "trial_counter" not in str(excinfo.value)


def test_refused_write_leaves_the_state_file_byte_identical(tmp_path: Path) -> None:
    """End to end through the real writer: a refusal must not half-write the file."""
    state_path, lock_path = _state_dir(tmp_path)
    _write_state(state_path, {"baseline_state": {"quality": 0.51}, "paused": False})
    before = state_path.read_bytes()

    with _ForeignHeldLock(lock_path):
        with pytest.raises(so.DaemonOwnedStateWriteError):
            state_store.save_state(state_path, {"baseline_state": {"quality": 0.83}})

    assert state_path.read_bytes() == before
    assert not list(state_path.parent.glob("*.tmp.*"))


def test_stale_snapshot_rewrite_is_refused_even_without_an_intentional_edit(
    tmp_path: Path,
) -> None:
    """A whole-file write from a stale read IS a write of every field it carries.

    The external process here never meant to touch ``trial_counter``; it just read
    the file before the daemon advanced it. Writing its snapshot back would roll
    the counter backwards — the lost-update half of the same defect.
    """
    state_path, lock_path = _state_dir(tmp_path)
    _write_state(state_path, {"trial_counter": 41, "paused": False})

    with _ForeignHeldLock(lock_path):
        with pytest.raises(so.DaemonOwnedStateWriteError) as excinfo:
            so.assert_external_write_allowed(
                state_path, {"trial_counter": 40, "paused": True}
            )
    assert "trial_counter" in str(excinfo.value)


# ── layer 1: the compliant paths still work ─────────────────────────────────


def test_daemon_may_write_its_own_daemon_owned_state(tmp_path: Path) -> None:
    """The guard must not forbid its own idiom: the owner writes what it owns."""
    state_path, lock_path = _state_dir(tmp_path)
    _write_state(state_path, {"baseline_state": {"quality": 0.51}, "trial_counter": 9})

    with _SelfHeldLock(lock_path):
        state_store.save_state(
            state_path, {"baseline_state": {"quality": 0.83}, "trial_counter": 10}
        )

    written = json.loads(state_path.read_text())
    assert written["baseline_state"] == {"quality": 0.83}
    assert written["trial_counter"] == 10


def test_out_of_band_control_write_is_allowed_while_the_daemon_runs(
    tmp_path: Path,
) -> None:
    """A dashboard / host_health / operator pause is the ALLOWED out-of-band write."""
    state_path, lock_path = _state_dir(tmp_path)
    _write_state(state_path, {"baseline_state": {"quality": 0.51}, "paused": False})

    with _ForeignHeldLock(lock_path):
        for field in so.KNOWN_EXTERNAL_CONTROL_FIELDS:
            payload = json.loads(state_path.read_text())
            payload[field] = "set-out-of-band"
            so.assert_external_write_allowed(state_path, payload)


def test_external_write_is_allowed_when_the_daemon_is_absent(tmp_path: Path) -> None:
    """Daemon absence is the documented safe window and must stay usable."""
    state_path, lock_path = _state_dir(tmp_path)
    _write_state(state_path, {"baseline_state": {"quality": 0.51}})
    lock_path.touch()  # the daemon has run here before, but is not running now

    state_store.save_state(state_path, {"baseline_state": {"quality": 0.83}})
    assert json.loads(state_path.read_text())["baseline_state"] == {"quality": 0.83}


def test_rewriting_an_identical_daemon_owned_value_is_not_a_write(
    tmp_path: Path,
) -> None:
    state_path, lock_path = _state_dir(tmp_path)
    _write_state(state_path, {"baseline_state": {"quality": 0.51}, "paused": False})

    with _ForeignHeldLock(lock_path):
        so.assert_external_write_allowed(
            state_path, {"baseline_state": {"quality": 0.51}, "paused": True}
        )


def test_absent_state_file_has_nothing_to_lose(tmp_path: Path) -> None:
    state_path, lock_path = _state_dir(tmp_path)
    with _ForeignHeldLock(lock_path):
        so.assert_external_write_allowed(state_path, {"baseline_state": {"q": 1}})


# ── layer 2: the daemon's own save cannot destroy a write silently ──────────


def test_quarantine_preserves_the_daemon_owned_value_a_save_destroys(
    tmp_path: Path,
) -> None:
    """The victim-side detector: recoverable and attributed, not silently gone."""
    state_path, _lock = _state_dir(tmp_path)

    # This process writes, establishing what it believes it owns.
    state_store.save_state(state_path, {"baseline_state": {"quality": 0.51}})
    # Somebody else lands a 59-minute measurement straight on disk.
    _write_state(state_path, {"baseline_state": {"quality": 0.83, "n": 100}})

    doomed = {"baseline_state": {"quality": 0.51}}
    state_store.save_state(state_path, doomed)

    sidecars = sorted(state_path.parent.glob("*.external-write-*.json"))
    assert len(sidecars) == 1, "the destroyed value must be preserved on disk"
    record = json.loads(sidecars[0].read_text())
    assert record["fields"]["baseline_state"]["on_disk_destroyed"] == {
        "quality": 0.83,
        "n": 100,
    }
    marker = json.loads(state_path.read_text())[so.CONFLICT_MARKER_FIELD]
    assert marker["fields"] == ["baseline_state"]
    assert marker["quarantine_path"] == str(sidecars[0])


def test_no_quarantine_when_nobody_else_wrote(tmp_path: Path) -> None:
    """Negative control: the daemon's own advancing counters are not a conflict.

    Every daemon save legitimately differs from disk — it just incremented the
    trial counter. Firing on that would make the detector noise and it would be
    ignored, which is how a real alert gets lost.
    """
    state_path, _lock = _state_dir(tmp_path)
    state_store.save_state(state_path, {"trial_counter": 9, "baseline_state": {"q": 1}})
    state_store.save_state(state_path, {"trial_counter": 10, "baseline_state": {"q": 1}})

    assert list(state_path.parent.glob("*.external-write-*.json")) == []
    assert so.CONFLICT_MARKER_FIELD not in json.loads(state_path.read_text())


def test_first_write_of_a_process_has_no_baseline_and_does_not_quarantine(
    tmp_path: Path,
) -> None:
    """A freshly started daemon just loaded this file; its first save is not a clobber."""
    state_path, _lock = _state_dir(tmp_path)
    _write_state(state_path, {"baseline_state": {"quality": 0.83}})

    state_store.save_state(state_path, {"baseline_state": {"quality": 0.51}})

    assert list(state_path.parent.glob("*.external-write-*.json")) == []
    assert so.CONFLICT_MARKER_FIELD not in json.loads(state_path.read_text())


def test_externally_written_fields_ignores_out_of_band_control_changes(
    tmp_path: Path,
) -> None:
    """An out-of-band pause between two saves is legal and must not be quarantined."""
    state_path, _lock = _state_dir(tmp_path)
    state_store.save_state(state_path, {"trial_counter": 9, "paused": False})
    _write_state(state_path, {"trial_counter": 9, "paused": True})

    assert so.externally_written_fields(state_path, so.read_state_file(state_path)) == []
