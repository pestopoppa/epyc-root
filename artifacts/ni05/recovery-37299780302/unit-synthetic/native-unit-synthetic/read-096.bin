"""Resuming AutoPilot must actually clear the skip/meta halt latch — or say it did not.

THE DEFECT (2026-08-12). The ``skip_action_loop`` circuit-breaker halts the loop by
latching ``paused=True`` plus ``consecutive_skip_actions`` (>= ``MAX_CONSECUTIVE_SKIP``),
``last_invalid_*`` and ``_dispatch_deficiency``. The dashboard resume button — and
``autopilot.py resume`` — cleared those counters on disk and reported success. But the
counters are DAEMON-OWNED: the AutoPilot daemon holds them in one in-memory dict for the
whole run and rewrites the file wholesale at its next save, merging back only
``_EXTERNAL_CONTROL_FIELDS``. So the operator's clearing was destroyed seconds later and
the breaker re-tripped on the very next non-executing action. The resume "succeeded" and
the halt came back — silent success over a lost write.

The equivalent bug on the META path was fixed on 2026-05-31 by having the DAEMON clear
its own latch on the paused True→False edge. The skip path never got that treatment; it
was left to the out-of-band writers, which are exactly the writers that cannot make it
stick.

WHAT THESE TESTS PIN, and why in this shape:

* the round trip, not the write — a test that only asserts "disk says 0 after resume"
  passes on the broken code, because the loss happens at the daemon's NEXT save. Every
  test here therefore replays that save through the real
  ``autopilot._merge_external_control_fields`` + ``state_store.save_state``, never a
  hand-rolled stand-in;
* the ownership ruling — these fields must stay out of the daemon's live merge set. A
  streak counter that any of 5+ writers may rewind is not a circuit breaker;
* honesty — when the daemon is up (real ``flock`` held by a real other process, so
  ``/proc/locks`` attributes it), the external resume must report
  ``delegated_to_daemon`` and must NOT pretend to have cleared anything;
* the capability — with the daemon down, an external resume still clears the latch
  outright, because a fix that removes the operator's ability to resume is not a fix.
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

from src.api.routes import dashboard  # noqa: E402


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


def _halted_state(skip_streak: int = 4) -> dict:
    """State exactly as the skip-action circuit-breaker leaves it (autopilot.py ~9021)."""
    return {
        "paused": True,
        "trial_counter": 812,
        "_dispatch_deficiency": "skip_action_loop",
        "consecutive_skip_actions": skip_streak,
        "last_invalid_action": {"type": "numeric_trial", "param": "ubatch"},
        "last_invalid_reason": "scope violation",
        "last_invalid_status": "invalid",
        "consecutive_meta_actions": 0,
        "baseline_state": {"tps": 41.9},
    }


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
    """Hold the daemon lock in a SEPARATE process — a live daemon's real shape.

    Taking it in the pytest process would make ``process_is_daemon`` answer True and
    the test would exercise the daemon branch while claiming to test the dashboard.
    """

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


def _daemon_iteration_top(daemon_memory: dict, state_path: Path) -> bool:
    """Replay the daemon's real iteration-top reload. Returns the was_paused edge.

    Mirrors ``autopilot.run_autopilot``'s reload block: only
    ``_EXTERNAL_CONTROL_FIELDS`` are copied disk→memory. Everything else — including
    every field the resume tried to clear — keeps the daemon's in-memory value. The
    merge set is imported from ``autopilot`` rather than restated, so widening it
    there is visible here.
    """
    import autopilot  # imported lazily: it is an expensive module

    was_paused = bool(daemon_memory.get("paused"))
    disk_state = json.loads(state_path.read_text())
    for key in autopilot._EXTERNAL_CONTROL_FIELDS:
        if key in disk_state:
            daemon_memory[key] = disk_state[key]
    return was_paused


def _daemon_resume_edge(daemon_memory: dict, state_path: Path) -> dict:
    """Run the daemon's REAL resume-edge handler against a temp state path.

    Calls ``autopilot.clear_halt_latch_on_resume_edge`` — the function the loop
    itself calls — rather than restating what it does. A restatement would keep
    passing if the loop stopped clearing the skip latch, which is precisely the
    defect under test.
    """
    import autopilot  # imported lazily: it is an expensive module

    original = autopilot.STATE_PATH
    try:
        autopilot.STATE_PATH = state_path
        return autopilot.clear_halt_latch_on_resume_edge(daemon_memory)
    finally:
        autopilot.STATE_PATH = original


def _daemon_save_from_memory(daemon_memory: dict, state_path: Path) -> None:
    """Replay a daemon save: merge control fields under the lock, then write the file.

    ``autopilot.save_state(..., merge_control=True)`` and ``state_store.save_state``
    are the real functions the daemon reaches; only the ``STATE_PATH`` global is
    substituted. This is the write that destroyed the operator's clearing.
    """
    import autopilot  # imported lazily: it is an expensive module

    disk_state = json.loads(state_path.read_text())
    autopilot._merge_external_control_fields(daemon_memory, disk_state)
    state_store.save_state(state_path, daemon_memory)


def _resume_via_dashboard(state_path: Path, tmp_path: Path) -> dict:
    return dashboard._apply_autopilot_control_action(
        action="resume",
        note="operator resume",
        state_path=state_path,
        audit_path=tmp_path / "autopilot_operator_control.jsonl",
    )


# ── the ruling: these counters are daemon state, not control state ──────────


def test_halt_latch_counters_are_declared_daemon_owned_and_never_merged() -> None:
    """The ruling, pinned in both directions.

    Every field a resume clears is daemon-owned, and none of them may appear in the
    daemon's live merge set. Merging a streak counter would invert its authority:
    ``_merge_external_control_fields`` copies disk→memory before a merged save, so the
    daemon's freshly incremented streak would be reverted to the value it last
    persisted and ``skip_streak >= MAX_CONSECUTIVE_SKIP`` could never be reached again.
    A breaker any of 5+ writers can rewind is not a breaker.
    """
    import autopilot  # imported lazily: it is an expensive module

    latched = set(so.halt_latch_updates({"_dispatch_deficiency": so.SKIP_LOOP_DEFICIENCY}))
    assert latched == {
        "consecutive_skip_actions",
        "last_invalid_action",
        "last_invalid_reason",
        "last_invalid_status",
        "consecutive_meta_actions",
    }
    assert latched <= set(so.DAEMON_OWNED_STATE_FIELDS)
    assert latched & set(autopilot._EXTERNAL_CONTROL_FIELDS) == set()
    assert latched & set(so.KNOWN_EXTERNAL_CONTROL_FIELDS) == set()


def test_merging_a_streak_counter_would_pin_it_and_disarm_the_breaker(tmp_path: Path) -> None:
    """Why the easy fix is wrong, demonstrated rather than asserted in prose.

    Runs the REAL merge with the counter added to the control set: the daemon's
    in-memory increment is reverted to the last persisted value. Repeat that at every
    save and the streak never grows, so the halt this whole feature exists to raise
    would never fire.
    """
    import autopilot  # imported lazily: it is an expensive module

    disk_state = {"consecutive_skip_actions": 2}
    daemon_memory = {"consecutive_skip_actions": 3}  # just incremented in memory

    original = autopilot._EXTERNAL_CONTROL_FIELDS
    try:
        autopilot._EXTERNAL_CONTROL_FIELDS = original + ("consecutive_skip_actions",)
        autopilot._merge_external_control_fields(daemon_memory, disk_state)
    finally:
        autopilot._EXTERNAL_CONTROL_FIELDS = original

    assert daemon_memory["consecutive_skip_actions"] == 2, (
        "merging the counter rewinds the daemon's own increment — the breaker would "
        "never reach MAX_CONSECUTIVE_SKIP"
    )


# ── the defect: resume → daemon save-from-memory → does the halt return? ────


def test_dashboard_resume_halt_latch_survives_the_daemons_next_save(tmp_path: Path) -> None:
    """THE regression test. Resume, then let the daemon save from memory.

    Before the fix the daemon's in-memory ``consecutive_skip_actions=4`` and
    ``_dispatch_deficiency='skip_action_loop'`` were written straight back over the
    operator's cleared values, so the halt reappeared and the next skipped action
    re-tripped the breaker. The daemon must now clear the latch in its OWN memory on
    the resume edge, which is the only place the clearing can last.
    """
    state_path, _lock_path = _state_dir(tmp_path)
    daemon_memory = _halted_state(skip_streak=4)
    state_path.write_text(json.dumps(daemon_memory))
    daemon_memory = dict(daemon_memory)  # the daemon's dict is a separate object

    _resume_via_dashboard(state_path, tmp_path)

    was_paused = _daemon_iteration_top(daemon_memory, state_path)
    assert was_paused and not daemon_memory["paused"], "the resume must reach the daemon"
    _daemon_resume_edge(daemon_memory, state_path)
    _daemon_save_from_memory(daemon_memory, state_path)

    on_disk = json.loads(state_path.read_text())
    assert on_disk["paused"] is False
    assert on_disk["consecutive_skip_actions"] == 0, (
        "the skip-loop latch came back after the daemon's save — the operator's "
        "resume was silently reverted"
    )
    assert on_disk["last_invalid_action"] is None
    assert on_disk["consecutive_meta_actions"] == 0
    assert "_dispatch_deficiency" not in on_disk
    assert "_meta_halt_reason" not in on_disk


def test_cli_resume_halt_latch_survives_the_daemons_next_save(tmp_path: Path) -> None:
    """``autopilot.py resume`` is a second out-of-band writer with the same defect.

    It runs in its own process, so its clearing is lost to the daemon's save exactly
    as the dashboard's was. Exercised through the real ``cmd_resume``.
    """
    import autopilot  # imported lazily: it is an expensive module

    state_path, _lock_path = _state_dir(tmp_path)
    daemon_memory = _halted_state(skip_streak=4)
    state_path.write_text(json.dumps(daemon_memory))
    daemon_memory = dict(daemon_memory)

    original = autopilot.STATE_PATH
    try:
        autopilot.STATE_PATH = state_path
        autopilot.cmd_resume(None)
    finally:
        autopilot.STATE_PATH = original

    _daemon_iteration_top(daemon_memory, state_path)
    _daemon_resume_edge(daemon_memory, state_path)
    _daemon_save_from_memory(daemon_memory, state_path)

    on_disk = json.loads(state_path.read_text())
    assert on_disk["paused"] is False
    assert on_disk["consecutive_skip_actions"] == 0
    assert "_dispatch_deficiency" not in on_disk


def test_meta_halt_latch_also_survives_the_daemons_next_save(tmp_path: Path) -> None:
    """The meta breaker must not regress while the skip breaker is being fixed.

    ``consecutive_meta_actions`` is daemon-owned too; the 2026-05-31 fix survives only
    because the DAEMON clears it. Same round trip, meta latch.
    """
    state_path, _lock_path = _state_dir(tmp_path)
    daemon_memory = {
        "paused": True,
        "trial_counter": 90,
        "_dispatch_deficiency": "meta_action_loop",
        "_meta_halt_reason": "5 consecutive meta actions",
        "consecutive_meta_actions": 5,
        "consecutive_skip_actions": 0,
    }
    state_path.write_text(json.dumps(daemon_memory))
    daemon_memory = dict(daemon_memory)

    _resume_via_dashboard(state_path, tmp_path)
    _daemon_iteration_top(daemon_memory, state_path)
    _daemon_resume_edge(daemon_memory, state_path)
    _daemon_save_from_memory(daemon_memory, state_path)

    on_disk = json.loads(state_path.read_text())
    assert on_disk["consecutive_meta_actions"] == 0
    assert "_meta_halt_reason" not in on_disk
    assert "_dispatch_deficiency" not in on_disk


def test_resume_does_not_rewind_a_skip_streak_it_was_not_halted_for(tmp_path: Path) -> None:
    """A resume for an unrelated reason must not silently disarm the breaker.

    Without ``_dispatch_deficiency == 'skip_action_loop'`` the streak is live evidence
    about the planner, not a latch the operator is clearing. Pausing for a config apply
    and resuming must leave it standing.
    """
    state_path, _lock_path = _state_dir(tmp_path)
    state_path.write_text(
        json.dumps(
            {
                "paused": True,
                "pause_reason": "config apply",
                "consecutive_skip_actions": 3,
                "last_invalid_action": {"type": "numeric_trial"},
            }
        )
    )

    _resume_via_dashboard(state_path, tmp_path)

    on_disk = json.loads(state_path.read_text())
    assert on_disk["paused"] is False
    assert on_disk["consecutive_skip_actions"] == 3
    assert on_disk["last_invalid_action"] == {"type": "numeric_trial"}


# ── honesty: a resume that cannot clear the latch must say so ───────────────


def test_dashboard_resume_reports_delegation_instead_of_silent_success(tmp_path: Path) -> None:
    """With the daemon up, the dashboard must not claim to have cleared the latch.

    The whole defect was a truthful-looking ``resume ok`` over a write that had already
    lost. The endpoint must now name the outcome, leave the daemon-owned fields exactly
    as they were on disk, and hand the operator a message that says who will clear them.
    """
    state_path, lock_path = _state_dir(tmp_path)
    state_path.write_text(json.dumps(_halted_state(skip_streak=4)))

    with _ForeignHeldLock(lock_path):
        result = _resume_via_dashboard(state_path, tmp_path)

    latch = result["halt_latch"]
    assert latch["outcome"] == "delegated_to_daemon"
    assert latch["deficiency"] == "skip_action_loop"
    assert "consecutive_skip_actions" in latch["fields"]
    assert "NOT cleared here" in result["halt_latch_message"]
    assert result["dispatch_deficiency"] == "skip_action_loop", (
        "the response must still show the live deficiency, not a cleared-looking one"
    )

    on_disk = json.loads(state_path.read_text())
    assert on_disk["paused"] is False, "the pause itself IS ours to clear"
    assert on_disk["consecutive_skip_actions"] == 4, (
        "the dashboard must not write daemon-owned counters while the daemon lives"
    )
    assert on_disk["_dispatch_deficiency"] == "skip_action_loop"


def test_delegated_resume_is_recorded_in_the_operator_control_audit(tmp_path: Path) -> None:
    """The audit trail must carry the delegation, not just the pause transition.

    An operator reading the audit log after the fact has to be able to tell a resume
    that cleared the latch from one that only asked the daemon to.
    """
    state_path, lock_path = _state_dir(tmp_path)
    audit_path = tmp_path / "autopilot_operator_control.jsonl"
    state_path.write_text(json.dumps(_halted_state(skip_streak=4)))

    with _ForeignHeldLock(lock_path):
        dashboard._apply_autopilot_control_action(
            action="resume",
            note="operator resume",
            state_path=state_path,
            audit_path=audit_path,
        )

    rows = [json.loads(line) for line in audit_path.read_text().splitlines()]
    assert rows[-1]["action"] == "resume"
    assert rows[-1]["halt_latch"]["outcome"] == "delegated_to_daemon"


def test_pause_records_no_halt_latch_outcome(tmp_path: Path) -> None:
    """Pause never touches the latch, so it must report nothing rather than 'noop'.

    A pause that reported a latch outcome would put a field in the audit log that
    means nothing, which is how a log stops being read.
    """
    state_path, _lock_path = _state_dir(tmp_path)
    state_path.write_text(json.dumps(_halted_state(skip_streak=4)))

    result = dashboard._apply_autopilot_control_action(
        action="pause",
        note="operator pause",
        state_path=state_path,
        audit_path=tmp_path / "autopilot_operator_control.jsonl",
    )
    assert result["halt_latch"] is None
    assert result["halt_latch_message"] == ""


# ── the capability survives: daemon down, the operator still clears it ──────


def test_resume_clears_the_latch_outright_when_the_daemon_is_down(tmp_path: Path) -> None:
    """A fix that removes the operator's ability to clear a halt is not a fix.

    With the lock file present and unheld — daemon stopped — there is no in-memory dict
    to overwrite the write, so the external resume clears the latch itself. This is the
    only path that works when the daemon has exited on the halt and is not coming back
    to observe the resume edge.
    """
    state_path, lock_path = _state_dir(tmp_path)
    state_path.write_text(json.dumps(_halted_state(skip_streak=4)))
    lock_path.touch()  # exists, nobody holds it

    result = _resume_via_dashboard(state_path, tmp_path)

    assert result["halt_latch"]["outcome"] == "cleared"
    assert result["halt_latch_message"] == "skip_action_loop latch cleared"
    assert result["dispatch_deficiency"] is None

    on_disk = json.loads(state_path.read_text())
    assert on_disk["paused"] is False
    assert on_disk["consecutive_skip_actions"] == 0
    assert on_disk["last_invalid_action"] is None
    assert on_disk["consecutive_meta_actions"] == 0
    assert "_dispatch_deficiency" not in on_disk


def test_a_freshly_started_daemon_inherits_the_cleared_latch(tmp_path: Path) -> None:
    """The daemon-down clearing must still be on disk when a daemon starts next.

    A restarted daemon loads this file as its whole in-memory state and never sees a
    paused True→False edge, so if the latch were still on disk nothing would ever clear
    it and the first skipped action would re-halt.
    """
    state_path, lock_path = _state_dir(tmp_path)
    state_path.write_text(json.dumps(_halted_state(skip_streak=4)))
    lock_path.touch()

    _resume_via_dashboard(state_path, tmp_path)

    daemon_memory = json.loads(state_path.read_text())  # fresh daemon startup load
    assert daemon_memory["consecutive_skip_actions"] == 0
    assert not daemon_memory.get("paused")

    _daemon_save_from_memory(daemon_memory, state_path)
    on_disk = json.loads(state_path.read_text())
    assert on_disk["consecutive_skip_actions"] == 0
    assert "_dispatch_deficiency" not in on_disk


# ── the helper's own contract ───────────────────────────────────────────────


def test_clear_halt_latch_reports_noop_and_mutates_nothing_without_a_latch(
    tmp_path: Path,
) -> None:
    """No latch set → nothing to clear, and no state churn claiming otherwise."""
    state_path, lock_path = _state_dir(tmp_path)
    state_path.write_text(json.dumps({"paused": False, "consecutive_meta_actions": 0}))
    lock_path.touch()

    state = {"paused": False, "consecutive_meta_actions": 0, "trial_counter": 5}
    latch = so.clear_halt_latch(state_path, state)

    assert latch["outcome"] == "noop"
    assert latch["fields"] == []
    assert so.halt_latch_message(latch) == ""
    assert state == {"paused": False, "consecutive_meta_actions": 0, "trial_counter": 5}


def test_clear_halt_latch_leaves_the_dict_untouched_when_it_delegates(
    tmp_path: Path,
) -> None:
    """Delegation must be a real no-write, not a write plus a caveat.

    If it mutated the caller's dict the caller would persist the clearing anyway and
    the honest-looking report would sit on top of the same lost write.
    """
    state_path, lock_path = _state_dir(tmp_path)
    state_path.write_text(json.dumps(_halted_state(skip_streak=4)))

    state = _halted_state(skip_streak=4)
    before = json.loads(json.dumps(state))

    with _ForeignHeldLock(lock_path):
        latch = so.clear_halt_latch(state_path, state)

    assert latch["outcome"] == "delegated_to_daemon"
    assert state == before


def test_daemon_clears_its_own_latch_even_while_holding_the_lock(tmp_path: Path) -> None:
    """The guard must not forbid the idiom it exists to protect.

    The daemon IS the lock holder, so its own resume-edge clearing must be allowed —
    a refusal here would strand the halt forever, which is worse than the bug.
    """
    state_path, lock_path = _state_dir(tmp_path)
    state_path.write_text(json.dumps(_halted_state(skip_streak=4)))

    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        state = _halted_state(skip_streak=4)
        latch = so.clear_halt_latch(state_path, state)
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)

    assert latch["outcome"] == "cleared"
    assert state["consecutive_skip_actions"] == 0
    assert "_dispatch_deficiency" not in state
