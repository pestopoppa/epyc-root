"""Tests for the autopilot-plane coherence fixes (H2 shared epoch + H4 lock).

H2: the four autopilot-state panels (pareto / autopilot_progress /
process_status / insight_graph) each independently re-read
autopilot_state.json + the rotating journal at their own instant, so a client
could splice panel A (trial N) beside panel B (trial N-1). The combined
``/dashboard/api/autopilot_snapshot`` frame builds all four inside ONE call,
stamps them with ONE shared ``state_generation`` token, and re-checks the token
after the build so a mid-build state change is detected and the frame rebuilt
(or flagged incoherent).

H4: the dashboard pause/resume control does a whole-file read-modify-write of
autopilot_state.json under ``uvicorn --workers 6``; it must serialize that RMW
under the shared ``state_write_lock`` flock.
"""
from __future__ import annotations

import asyncio
import contextlib
import json

from fastapi.responses import JSONResponse

from src.api.routes import dashboard as d


def _run(coro):
    return asyncio.run(coro)


def _body(resp) -> dict:
    return json.loads(resp.body)


# --- H2: shared state_generation token --------------------------------------


def test_state_generation_changes_when_state_or_journal_changes(tmp_path, monkeypatch):
    """Two panels reading at different instants get DIFFERENT tokens, so a client
    holding a torn set (panel A vs panel B) can detect + discard it."""
    state = tmp_path / "autopilot_state.json"
    journal = tmp_path / "autopilot_journal.jsonl"
    state.write_text(json.dumps({"trial_counter": 100}))
    journal.write_text(json.dumps({"trial_id": 100}) + "\n")
    monkeypatch.setattr(d, "_AUTOPILOT_STATE_PATH", state)
    monkeypatch.setattr(d, "_AUTOPILOT_JOURNAL_PATH", journal)

    gen1 = d._autopilot_state_generation()
    # Unchanged on-disk state -> identical token.
    assert d._autopilot_state_generation() == gen1

    # A state.json write flips the token (the lost-update class the lock guards).
    state.write_text(json.dumps({"trial_counter": 101}))
    gen2 = d._autopilot_state_generation()
    assert gen2 != gen1

    # A journal append flips the token too (the rotating-journal source).
    with journal.open("a") as fh:
        fh.write(json.dumps({"trial_id": 101}) + "\n")
    gen3 = d._autopilot_state_generation()
    assert gen3 != gen2


def test_state_generation_tracks_newest_rotation_shard(tmp_path, monkeypatch):
    base = tmp_path / "autopilot_journal.jsonl"
    rot = tmp_path / "autopilot_journal_1.jsonl"
    base.write_text(json.dumps({"trial_id": 999}) + "\n")
    rot.write_text(json.dumps({"trial_id": 1000}) + "\n")
    monkeypatch.setattr(d, "_AUTOPILOT_STATE_PATH", tmp_path / "missing_state.json")
    monkeypatch.setattr(d, "_AUTOPILOT_JOURNAL_PATH", base)

    gen1 = d._autopilot_state_generation()
    # Appending to the live (rotation) shard must change the token.
    with rot.open("a") as fh:
        fh.write(json.dumps({"trial_id": 1001}) + "\n")
    assert d._autopilot_state_generation() != gen1


def _patch_four_panels(monkeypatch):
    """Replace the four panel endpoints with trivial JSONResponses so the
    combined-frame coherence logic can be tested in isolation."""
    for name in ("process_status", "autopilot_progress", "pareto", "insight_graph"):

        def _fake(_name=name, *args, **kwargs):
            async def _coro():
                return JSONResponse({"panel": _name})

            return _coro()

        monkeypatch.setattr(d, name, _fake)


def test_combined_snapshot_yields_one_generation_for_all_panels(monkeypatch):
    _patch_four_panels(monkeypatch)
    monkeypatch.setattr(d, "_autopilot_state_generation", lambda **kw: "GEN-X")
    monkeypatch.setattr(d, "_read_autopilot_journal_rows", lambda: [{"trial_id": 7}])
    monkeypatch.setattr(d, "_state_trial_counter", lambda **kw: 7)

    body = _body(_run(d._autopilot_snapshot_impl()))

    assert body["coherent"] is True
    assert body["state_generation"] == "GEN-X"
    assert set(body["panels"]) == {
        "process_status",
        "autopilot_progress",
        "pareto",
        "insight_graph",
    }
    # All four panels carry the SAME single generation token (drawn from one read).
    for panel in body["panels"].values():
        assert panel["state_generation"] == "GEN-X"


def test_combined_snapshot_detects_and_rebuilds_torn_frame(monkeypatch):
    """A state change BETWEEN two panel reads is detectable via the generation
    token: gen_before != gen_after -> rebuild until coherent."""
    _patch_four_panels(monkeypatch)
    monkeypatch.setattr(d, "_read_autopilot_journal_rows", lambda: [])
    monkeypatch.setattr(d, "_state_trial_counter", lambda **kw: 0)
    # attempt 1: before=G1, after=G2 (state advanced mid-build) -> torn -> retry
    # attempt 2: before=G3, after=G3 -> coherent
    gens = iter(["G1", "G2", "G3", "G3"])
    monkeypatch.setattr(d, "_autopilot_state_generation", lambda **kw: next(gens))

    body = _body(_run(d._autopilot_snapshot_impl()))

    assert body["coherence_attempts"] == 2
    assert body["coherent"] is True
    assert body["state_generation"] == "G3"


def test_combined_snapshot_flags_incoherent_when_state_keeps_moving(monkeypatch):
    """If the state never settles across the retry budget, the frame is returned
    but explicitly flagged incoherent rather than silently torn."""
    _patch_four_panels(monkeypatch)
    monkeypatch.setattr(d, "_read_autopilot_journal_rows", lambda: [])
    monkeypatch.setattr(d, "_state_trial_counter", lambda **kw: 0)
    gens = iter(["G1", "G2", "G3", "G4"])
    monkeypatch.setattr(d, "_autopilot_state_generation", lambda **kw: next(gens))

    body = _body(_run(d._autopilot_snapshot_impl()))

    assert body["coherent"] is False
    assert body["coherence_attempts"] == 2


def test_combined_snapshot_surfaces_value_divergence(monkeypatch):
    """H5 surfaced through the combined frame: state trial_counter behind the
    journal max -> value_consistency badges 'divergent'."""
    _patch_four_panels(monkeypatch)
    monkeypatch.setattr(d, "_autopilot_state_generation", lambda **kw: "GEN")
    monkeypatch.setattr(
        d, "_read_autopilot_journal_rows", lambda: [{"trial_id": 105}]
    )
    monkeypatch.setattr(d, "_state_trial_counter", lambda **kw: 100)

    body = _body(_run(d._autopilot_snapshot_impl()))

    assert body["state_trial_counter"] == 100
    assert body["journal_max_trial_id"] == 105
    assert body["value_consistency"]["class"] == "divergent"
    assert body["_freshness"]["consistency_class"] == "divergent"


# --- H4: control action serializes its RMW under the shared lock -------------


def test_control_action_creates_the_state_lockfile(tmp_path):
    """The real state_write_lock is used, so its flock sidecar file is created
    next to autopilot_state.json during the pause RMW."""
    state = tmp_path / "autopilot_state.json"
    audit = tmp_path / "audit.jsonl"
    state.write_text(json.dumps({"trial_counter": 5, "paused": False}))

    result = d._apply_autopilot_control_action(
        action="pause", note="t", state_path=state, audit_path=audit
    )

    assert result["status"] == "ok"
    assert result["paused"] is True
    assert (tmp_path / "autopilot_state.json.lock").exists()
    # The write actually landed.
    assert json.loads(state.read_text())["paused"] is True


def test_control_action_holds_lock_around_read_modify_write(tmp_path, monkeypatch):
    """The lock must WRAP the read->modify->write, not just bracket the write:
    the read and the atomic write both happen while the lock is held."""
    state = tmp_path / "autopilot_state.json"
    audit = tmp_path / "audit.jsonl"
    state.write_text(json.dumps({"trial_counter": 5, "paused": True}))

    events: list[str] = []
    real_read = d._read_json_object
    real_write = d._atomic_write_json
    lock_state = {"held": False}

    @contextlib.contextmanager
    def spy_lock(path, *args, **kwargs):
        events.append(f"lock_acquire:{path}")
        lock_state["held"] = True
        try:
            yield True
        finally:
            lock_state["held"] = False
            events.append("lock_release")

    def spy_read(path):
        events.append(f"read:held={lock_state['held']}")
        return real_read(path)

    def spy_write(path, payload):
        events.append(f"write:held={lock_state['held']}")
        return real_write(path, payload)

    monkeypatch.setattr(d, "state_write_lock", spy_lock)
    monkeypatch.setattr(d, "_read_json_object", spy_read)
    monkeypatch.setattr(d, "_atomic_write_json", spy_write)

    d._apply_autopilot_control_action(
        action="resume", note="", state_path=state, audit_path=audit
    )

    assert events[0] == f"lock_acquire:{state}"
    # Both the READ and the WRITE happened while the lock was held.
    assert "read:held=True" in events
    assert "write:held=True" in events
    # The lock was released after the write (order: acquire ... write ... release).
    assert events.index("lock_release") > events.index("write:held=True")


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-q", "-p", "no:xdist"]))
