"""Interlock between an operator pause and an in-flight config-apply.

THE WINDOW. Two out-of-band pausers bracket slow work with
"remember paused_pre -> set paused=True -> do slow work -> restore paused=False":

  * ``config_applicator._pause_autopilot_dispatch`` /
    ``_restore_autopilot_dispatch_pause`` around ``restart_role`` — a stack
    reload plus health check plus smoke check plus a possible rollback;
  * ``host_health.flush_cache_with_pause`` around an 11 s grace sleep,
    ``drop_caches`` and a serial NUMA-interleave rewarm of every live GGUF.

An operator ``autopilot.py pause`` landing INSIDE that window used to be honoured
on disk and then silently undone by the restore, because an operator pause and
the applicator's own pause are the same byte on disk (``"paused": true``). The
2026-08-03 outage: the apply left the API down, the operator paused, the
applicator's ``finally:`` resumed AutoPilot, and the loop retried
``Connection refused`` forever behind a pause the operator believed was in force.

THE INTERLOCK is a pause LEASE (``pause_owner``/``pause_token``): an automated
pauser may only clear a pause it still holds, the operator SUPERSEDES the lease
rather than being refused or deferred (quiesce-and-drain semantics: the apply is
never aborted mid-operation, it just loses the right to resume), and the
supersession is RECORDED so the collision is legible afterwards.
"""

from __future__ import annotations

import argparse
import json
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

from src.api.routes import dashboard  # noqa: E402


def _state_file(tmp_path: Path, **fields) -> Path:
    path = tmp_path / "autopilot_state.json"
    payload = {"paused": False, "trial_counter": 7}
    payload.update(fields)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


# ───────────────── lease primitives (state_lock) ─────────────────


def test_claim_pause_lease_stamps_owner_and_unique_token() -> None:
    a: dict = {}
    b: dict = {}
    token_a = state_lock.claim_pause_lease(a, "config_applicator")
    token_b = state_lock.claim_pause_lease(b, "config_applicator")

    assert a["paused"] is True
    assert a["pause_owner"] == "config_applicator"
    assert a["pause_token"] == token_a
    # Same owner, different acquisitions -> different leases. A per-owner
    # constant would let a stale restore clear a fresh pause.
    assert token_a != token_b


def test_release_pause_lease_refuses_a_token_it_does_not_hold() -> None:
    state: dict = {}
    stale = state_lock.claim_pause_lease(state, "config_applicator")
    state_lock.claim_pause_lease(state, "host_health_cache_flush")

    assert state_lock.release_pause_lease(state, stale) is False
    assert state["paused"] is True  # untouched

    assert state_lock.release_pause_lease(state, state["pause_token"]) is True
    assert state["paused"] is False
    assert state["pause_owner"] is None
    assert state["pause_token"] is None


def test_release_pause_lease_refuses_an_empty_token() -> None:
    """A missing token must never be treated as 'holds every lease'."""
    state: dict = {}
    state_lock.claim_pause_lease(state, "config_applicator")

    assert state_lock.release_pause_lease(state, None) is False
    assert state_lock.release_pause_lease(state, "") is False
    assert state["paused"] is True


def test_supersede_pause_lease_records_the_displaced_owner() -> None:
    state: dict = {}
    state_lock.claim_pause_lease(state, "config_applicator")

    collision = state_lock.supersede_pause_lease(state, state_lock.OPERATOR_PAUSE_OWNER)

    assert collision is not None
    assert collision["superseded_owner"] == "config_applicator"
    assert collision["new_owner"] == state_lock.OPERATOR_PAUSE_OWNER
    assert state["pause_owner"] == state_lock.OPERATOR_PAUSE_OWNER
    assert state["paused"] is True
    assert state["pause_collision"] == collision


def test_supersede_pause_lease_is_not_a_collision_when_no_lease_is_held() -> None:
    state = {"paused": False}
    assert state_lock.supersede_pause_lease(state, state_lock.OPERATOR_PAUSE_OWNER) is None
    assert state["pause_collision"] is None
    assert state["paused"] is True


# ───────────── config_applicator: the restart-window collision ─────────────


def test_config_applicator_pause_stamps_a_lease(tmp_path: Path, monkeypatch) -> None:
    sp = _state_file(tmp_path)
    monkeypatch.setattr(config_applicator.time, "sleep", lambda _s: None)

    result = config_applicator._pause_autopilot_dispatch(state_path=sp, grace_s=11.0)

    assert result["status"] == "ok"
    assert result["pause_owner"] == config_applicator.DISPATCH_PAUSE_OWNER
    on_disk = _read(sp)
    assert on_disk["paused"] is True
    assert on_disk["pause_token"] == result["pause_token"]


def test_config_applicator_restore_refuses_after_an_operator_pause(
    tmp_path: Path, monkeypatch
) -> None:
    """DECISIVE: the exact 2026-08-03 interleaving.

    apply pauses dispatch -> operator runs `autopilot pause` mid-apply -> the
    apply finishes and its `finally:` tries to resume. It must NOT.
    """
    sp = _state_file(tmp_path)
    monkeypatch.setattr(config_applicator.time, "sleep", lambda _s: None)
    monkeypatch.setattr(autopilot, "STATE_PATH", sp)

    pause_result = config_applicator._pause_autopilot_dispatch(state_path=sp, grace_s=0.0)

    # ... the operator pauses while the stack reload is still in flight ...
    autopilot.cmd_pause(argparse.Namespace())

    restore = config_applicator._restore_autopilot_dispatch_pause(pause_result)

    assert restore["restored"] is False
    assert restore["status"] == "superseded"
    assert restore["reason"] == "pause_superseded"
    assert restore["observed_owner"] == state_lock.OPERATOR_PAUSE_OWNER
    # The operator's pause is still in force — this is the whole point.
    assert _read(sp)["paused"] is True


def test_config_applicator_restore_still_resumes_its_own_pause(
    tmp_path: Path, monkeypatch
) -> None:
    """Guard against fixing the collision by never resuming at all."""
    sp = _state_file(tmp_path)
    monkeypatch.setattr(config_applicator.time, "sleep", lambda _s: None)

    pause_result = config_applicator._pause_autopilot_dispatch(state_path=sp, grace_s=0.0)
    restore = config_applicator._restore_autopilot_dispatch_pause(pause_result)

    assert restore["status"] == "ok"
    assert restore["restored"] is True
    assert _read(sp)["paused"] is False


def test_config_applicator_does_not_steal_a_pause_it_found(tmp_path: Path, monkeypatch) -> None:
    """Operator paused BEFORE the apply: no lease is taken, nothing is resumed."""
    sp = _state_file(tmp_path, paused=True)
    monkeypatch.setattr(config_applicator.time, "sleep", lambda _s: None)

    pause_result = config_applicator._pause_autopilot_dispatch(state_path=sp, grace_s=0.0)
    assert pause_result["paused_pre"] is True
    assert pause_result["pause_token"] is None

    restore = config_applicator._restore_autopilot_dispatch_pause(pause_result)
    assert restore["restored"] is False
    assert restore["reason"] == "already_paused"
    assert _read(sp)["paused"] is True


def test_restart_role_surfaces_the_collision_in_its_apply_payload(
    tmp_path: Path, monkeypatch
) -> None:
    """Detected-but-silent is still a defect: the refusal rides out in the result.

    ``restart_role``'s ``finally:`` stores the restore outcome under
    ``dispatch_pause["restore"]``, which is what the caller journals.
    """
    sp = _state_file(tmp_path)
    monkeypatch.setattr(config_applicator.time, "sleep", lambda _s: None)
    monkeypatch.setattr(autopilot, "STATE_PATH", sp)

    def _fake_reload(*, role, env_overrides, env_unset):
        # The operator pauses while the stack reload is running.
        autopilot.cmd_pause(argparse.Namespace())
        return {"status": "error", "error": "stack reload failed"}

    monkeypatch.setattr(config_applicator, "_reload_role_via_stack", _fake_reload)
    monkeypatch.setattr(
        config_applicator, "_restore_registry_overrides", lambda **kw: {"status": "ok"}
    )

    result = config_applicator.restart_role(
        role="orchestrator",
        pause_dispatch=True,
        autopilot_state_path=sp,
        dispatch_pause_grace_s=0.0,
    )

    restore = result["dispatch_pause"]["restore"]
    assert restore["status"] == "superseded"
    assert restore["observed_owner"] == state_lock.OPERATOR_PAUSE_OWNER
    assert _read(sp)["paused"] is True


# ───────────── host_health: the same window around drop_caches ─────────────


def test_cache_flush_refuses_to_resume_after_an_operator_pause(
    tmp_path: Path, monkeypatch
) -> None:
    """The 2026-05-24 comment promised this; `paused_pre is False` could not do it."""
    sp = _state_file(tmp_path)
    monkeypatch.setattr(autopilot, "STATE_PATH", sp)

    def _pause_mid_flush() -> bool:
        autopilot.cmd_pause(argparse.Namespace())
        return True

    with (
        mock.patch.object(host_health, "remediate", side_effect=_pause_mid_flush),
        mock.patch.object(host_health, "_numa_interleave_rewarm", return_value={}),
        mock.patch("time.sleep"),
    ):
        result = host_health.flush_cache_with_pause(state_path=sp, rewarm=False)

    assert result["pause_superseded"] is True
    assert result["pause_superseded_by"] == state_lock.OPERATOR_PAUSE_OWNER
    assert _read(sp)["paused"] is True


def test_cache_flush_still_resumes_its_own_pause(tmp_path: Path) -> None:
    sp = _state_file(tmp_path)

    with (
        mock.patch.object(host_health, "remediate", return_value=True),
        mock.patch.object(host_health, "_numa_interleave_rewarm", return_value={}),
        mock.patch("time.sleep"),
    ):
        result = host_health.flush_cache_with_pause(state_path=sp, rewarm=False)

    assert result["pause_superseded"] is False
    assert _read(sp)["paused"] is False


def test_two_automated_pausers_do_not_resume_each_other(tmp_path: Path, monkeypatch) -> None:
    """Cross-pauser case: a cache flush must not resume a config-apply's pause."""
    sp = _state_file(tmp_path)
    monkeypatch.setattr(config_applicator.time, "sleep", lambda _s: None)

    apply_pause = config_applicator._pause_autopilot_dispatch(state_path=sp, grace_s=0.0)

    # host_health arrives second, finds paused=True, so it takes no lease...
    with (
        mock.patch.object(host_health, "remediate", return_value=True),
        mock.patch.object(host_health, "_numa_interleave_rewarm", return_value={}),
        mock.patch("time.sleep"),
    ):
        flush = host_health.flush_cache_with_pause(state_path=sp, rewarm=False)

    assert flush["paused_pre"] is True
    assert _read(sp)["paused"] is True
    # ...and the config-apply's own lease still works afterwards.
    assert config_applicator._restore_autopilot_dispatch_pause(apply_pause)["restored"] is True


# ───────────── operator surfaces: the collision must be legible ─────────────


def test_cmd_pause_claims_the_operator_lease(tmp_path: Path, monkeypatch) -> None:
    sp = _state_file(tmp_path)
    monkeypatch.setattr(autopilot, "STATE_PATH", sp)

    autopilot.cmd_pause(argparse.Namespace())

    on_disk = _read(sp)
    assert on_disk["paused"] is True
    assert on_disk["pause_owner"] == state_lock.OPERATOR_PAUSE_OWNER
    assert on_disk["pause_token"]
    assert on_disk["pause_collision"] is None


def test_cmd_pause_warns_the_operator_about_the_in_flight_apply(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    sp = _state_file(tmp_path)
    monkeypatch.setattr(config_applicator.time, "sleep", lambda _s: None)
    monkeypatch.setattr(autopilot, "STATE_PATH", sp)
    config_applicator._pause_autopilot_dispatch(state_path=sp, grace_s=0.0)

    autopilot.cmd_pause(argparse.Namespace())

    out = capsys.readouterr().out
    assert "WARNING" in out
    assert config_applicator.DISPATCH_PAUSE_OWNER in out
    assert _read(sp)["pause_collision"]["superseded_owner"] == (
        config_applicator.DISPATCH_PAUSE_OWNER
    )


def test_cmd_status_reports_the_pause_owner_and_collision(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    sp = _state_file(tmp_path)
    monkeypatch.setattr(config_applicator.time, "sleep", lambda _s: None)
    monkeypatch.setattr(autopilot, "STATE_PATH", sp)
    config_applicator._pause_autopilot_dispatch(state_path=sp, grace_s=0.0)
    autopilot.cmd_pause(argparse.Namespace())
    capsys.readouterr()

    class _Journal:
        def summary_text(self, *_a, **_k):
            return ""

        def baseline_promotion_events(self):
            return []

        def baseline_ledger_events(self):
            return []

    class _Archive:
        def summary_text(self, *_a, **_k):
            return ""

    monkeypatch.setattr(autopilot, "ExperimentJournal", lambda *a, **k: _Journal())
    monkeypatch.setattr(
        autopilot, "_archive_for_read_command", lambda *a, **k: (_Archive(), "journal")
    )
    monkeypatch.setattr(autopilot, "_baseline_promotion_summary_lines", lambda *a, **k: [])
    monkeypatch.setattr(autopilot, "_frontier_rerun_summary_lines", lambda *a, **k: [])

    autopilot.cmd_status(argparse.Namespace())

    out = capsys.readouterr().out
    assert f"Pause owner: {state_lock.OPERATOR_PAUSE_OWNER}" in out
    assert "Pause collision:" in out
    assert config_applicator.DISPATCH_PAUSE_OWNER in out


def test_cmd_resume_clears_the_lease_and_the_collision(tmp_path: Path, monkeypatch) -> None:
    sp = _state_file(tmp_path)
    monkeypatch.setattr(config_applicator.time, "sleep", lambda _s: None)
    monkeypatch.setattr(autopilot, "STATE_PATH", sp)
    config_applicator._pause_autopilot_dispatch(state_path=sp, grace_s=0.0)
    autopilot.cmd_pause(argparse.Namespace())

    autopilot.cmd_resume(argparse.Namespace())

    on_disk = _read(sp)
    assert on_disk["paused"] is False
    assert on_disk["pause_owner"] is None
    assert on_disk["pause_token"] is None
    assert on_disk["pause_collision"] is None


def test_lease_fields_are_daemon_merge_protected() -> None:
    """A trial-end whole-file save must not drop the lease off disk.

    ``_save_state_impl`` writes the daemon's in-memory dict verbatim, so a lease
    key missing from ``_EXTERNAL_CONTROL_FIELDS`` would be erased at the next
    save — and an erased token reads as 'superseded' to its own holder.
    """
    for field in ("pause_owner", "pause_token", "pause_collision"):
        assert field in autopilot._EXTERNAL_CONTROL_FIELDS


def test_daemon_merge_carries_the_lease_from_disk(tmp_path: Path, monkeypatch) -> None:
    sp = _state_file(tmp_path)
    monkeypatch.setattr(autopilot, "STATE_PATH", sp)
    monkeypatch.setattr(config_applicator.time, "sleep", lambda _s: None)
    pause_result = config_applicator._pause_autopilot_dispatch(state_path=sp, grace_s=0.0)

    # Daemon's stale in-memory dict from before the pause.
    daemon_state = {"paused": False, "trial_counter": 8}
    autopilot.save_state(daemon_state, merge_control=True)

    on_disk = _read(sp)
    assert on_disk["paused"] is True
    assert on_disk["pause_token"] == pause_result["pause_token"]
    # And the applicator can therefore still release its own pause.
    assert config_applicator._restore_autopilot_dispatch_pause(pause_result)["restored"] is True


# ───────── dashboard pause button: same authority, same interlock ─────────


def test_dashboard_pause_supersedes_an_in_flight_apply(tmp_path: Path, monkeypatch) -> None:
    """The dashboard button must not be a bypass of the CLI's interlock."""
    sp = _state_file(tmp_path)
    audit = tmp_path / "autopilot_operator_control.jsonl"
    monkeypatch.setattr(config_applicator.time, "sleep", lambda _s: None)
    pause_result = config_applicator._pause_autopilot_dispatch(state_path=sp, grace_s=0.0)

    payload = dashboard._apply_autopilot_control_action(
        action="pause", note="stop it", state_path=sp, audit_path=audit
    )

    assert payload["pause_collision"]["superseded_owner"] == (
        config_applicator.DISPATCH_PAUSE_OWNER
    )
    restore = config_applicator._restore_autopilot_dispatch_pause(pause_result)
    assert restore["status"] == "superseded"
    assert _read(sp)["paused"] is True
    # The collision is on the audit trail too, not just in the response body.
    rows = [json.loads(line) for line in audit.read_text(encoding="utf-8").splitlines()]
    assert rows[-1]["pause_collision"]["superseded_owner"] == (
        config_applicator.DISPATCH_PAUSE_OWNER
    )


def test_dashboard_resume_clears_the_lease(tmp_path: Path, monkeypatch) -> None:
    sp = _state_file(tmp_path)
    audit = tmp_path / "autopilot_operator_control.jsonl"
    monkeypatch.setattr(config_applicator.time, "sleep", lambda _s: None)
    config_applicator._pause_autopilot_dispatch(state_path=sp, grace_s=0.0)
    dashboard._apply_autopilot_control_action(
        action="pause", note="", state_path=sp, audit_path=audit
    )

    dashboard._apply_autopilot_control_action(
        action="resume", note="", state_path=sp, audit_path=audit
    )

    on_disk = _read(sp)
    assert on_disk["paused"] is False
    assert on_disk["pause_owner"] is None
    assert on_disk["pause_token"] is None
    assert on_disk["pause_collision"] is None


def test_dashboard_state_summary_exposes_owner_and_collision(
    tmp_path: Path, monkeypatch
) -> None:
    sp = _state_file(tmp_path)
    audit = tmp_path / "autopilot_operator_control.jsonl"
    monkeypatch.setattr(config_applicator.time, "sleep", lambda _s: None)
    config_applicator._pause_autopilot_dispatch(state_path=sp, grace_s=0.0)
    dashboard._apply_autopilot_control_action(
        action="pause", note="", state_path=sp, audit_path=audit
    )

    summary = dashboard._autopilot_state_summary(state_path=sp)

    assert summary["pause_owner"] == state_lock.OPERATOR_PAUSE_OWNER
    assert summary["pause_collision"]["superseded_owner"] == (
        config_applicator.DISPATCH_PAUSE_OWNER
    )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q", "-p", "no:xdist"]))
