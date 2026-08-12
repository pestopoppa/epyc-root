"""Tests for scripts/coordination/hardware_backfill.py (task hardware-idle-supervisor).

Run:
    /mnt/raid0/llm/epyc-orchestrator/.venv/bin/python -m pytest \
        scripts/coordination/tests/test_hardware_backfill.py -q

Two dependency-injection seams keep every test off real fleet state (see the
module's own header for the authoritative description):
  * `HARDWARE_BACKFILL_REGION_LOCK_BIN` env var — points launched jobs at a
    throwaway shim (`_region_lock_shim` fixture below) that execs the
    trailing `-- <cmd>` directly, so no test ever touches the real
    cpu_region.occupancy.json or the orchestrator venv.
  * `BackfillRunner(bus_emit_fn=...)` — a stub replacing the real
    `session_bus.py append` subprocess call, so detector dedup/retry logic is
    exercised deterministically without depending on the live bus roster
    (`hardware-backfill` is not currently a roster id, so the REAL call fails
    closed by design — see coordination/backfill/README.md).
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import hardware_backfill as hb  # noqa: E402


# --------------------------------------------------------------------------- fixtures


@pytest.fixture
def region_lock_shim(tmp_path, monkeypatch):
    """A fake `region-lock` executable: ignores every flag, execs whatever
    follows `--` directly. Points HARDWARE_BACKFILL_REGION_LOCK_BIN at it so
    launched jobs never touch the real lock implementation or its occupancy
    file."""
    shim = tmp_path / "fake_region_lock.py"
    shim.write_text(
        "#!/usr/bin/env python3\n"
        "import os, sys\n"
        "argv = sys.argv[1:]\n"
        "cmd = argv[argv.index('--') + 1:] if '--' in argv else argv\n"
        "os.execvp(cmd[0], cmd)\n",
        encoding="utf-8",
    )
    shim.chmod(0o755)
    monkeypatch.setenv("HARDWARE_BACKFILL_REGION_LOCK_BIN", str(shim))
    return shim


def _spec(id_, *, regions=("q1",), role="backfill-test", cmd=("true",), max_runtime_s=30,
          enqueued_by="test", ts="2026-08-12T00:00:00Z"):
    return {
        "id": id_, "regions": list(regions), "role": role, "cmd": list(cmd),
        "max_runtime_s": max_runtime_s, "enqueued_by": enqueued_by, "ts": ts,
    }


def _write_queue(queue_dir: Path, specs: list[dict]) -> None:
    queue_dir.mkdir(parents=True, exist_ok=True)
    with (queue_dir / "queue.jsonl").open("w", encoding="utf-8") as fh:
        for s in specs:
            fh.write(json.dumps(s) + "\n")


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _runner(tmp_path, **kw) -> hb.BackfillRunner:
    return hb.BackfillRunner(queue_dir=tmp_path / "backfill", **kw)


# --------------------------------------------------------------------------- validate_spec


def test_validate_spec_accepts_well_formed():
    ok, reason = hb.validate_spec(_spec("a"))
    assert ok is True
    assert reason == "ok"


def test_validate_spec_refuses_missing_max_runtime_s():
    obj = _spec("a")
    del obj["max_runtime_s"]
    ok, reason = hb.validate_spec(obj)
    assert ok is False
    assert "max_runtime_s" in reason


def test_validate_spec_refuses_max_runtime_s_over_ceiling():
    ok, reason = hb.validate_spec(_spec("a", max_runtime_s=hb.MAX_RUNTIME_S_CEILING + 1))
    assert ok is False
    assert "0 < max_runtime_s <=" in reason


def test_validate_spec_refuses_zero_or_negative_max_runtime_s():
    for bad in (0, -5):
        ok, reason = hb.validate_spec(_spec("a", max_runtime_s=bad))
        assert ok is False
        assert "max_runtime_s" in reason


def test_validate_spec_refuses_gpu_region():
    ok, reason = hb.validate_spec(_spec("a", regions=["gpu0"]))
    assert ok is False
    assert "GPU" in reason


def test_validate_spec_refuses_non_backfill_role():
    ok, reason = hb.validate_spec(_spec("a", role="frontdoor"))
    assert ok is False
    assert "backfill-" in reason


def test_validate_spec_refuses_empty_cmd():
    ok, reason = hb.validate_spec(_spec("a", cmd=[]))
    assert ok is False
    assert "cmd" in reason


def test_validate_spec_accepts_ceiling_exactly():
    ok, _ = hb.validate_spec(_spec("a", max_runtime_s=hb.MAX_RUNTIME_S_CEILING))
    assert ok is True


# --------------------------------------------------------------------------- queue parsing


def test_load_queue_partitions_valid_and_refused(tmp_path):
    _write_queue(tmp_path / "backfill", [
        _spec("good-1"),
        _spec("bad-unbounded", max_runtime_s=999999),
    ])
    # A raw malformed JSON line appended directly.
    with (tmp_path / "backfill" / "queue.jsonl").open("a", encoding="utf-8") as fh:
        fh.write("{not valid json\n")

    runner = _runner(tmp_path)
    specs, refusals = runner.load_queue()
    assert [s["id"] for s in specs] == ["good-1"]
    assert len(refusals) == 2
    ids = {r["id"] for r in refusals}
    assert "bad-unbounded" in ids
    assert any(rid.startswith("malformed-L") for rid in ids)


def test_refusal_is_persisted_once_not_every_tick(tmp_path):
    """Regression: a refusal must be written to done.jsonl exactly once, keyed
    by its own id — never re-derived from the (possibly id-less) raw spec,
    which would silently write `id: null` and cause the SAME refusal to be
    reprocessed and rewritten on every subsequent tick (the 590-records
    failure shape this runner exists to avoid)."""
    _write_queue(tmp_path / "backfill", [_spec("bad", max_runtime_s=999999)])
    runner = _runner(tmp_path)
    for _ in range(3):
        assert runner.queue_depth() == 0  # the sole spec is refused, never pending
    rows = _read_jsonl(runner.done_file)
    assert len(rows) == 1
    assert rows[0]["id"] == "bad"
    assert rows[0]["status"] == "refused"


def test_missing_queue_file_is_legitimately_empty(tmp_path):
    runner = _runner(tmp_path)
    assert runner.queue_depth() == 0


def test_queue_depth_counts_only_pending(tmp_path):
    _write_queue(tmp_path / "backfill", [_spec("p1"), _spec("p2"), _spec("bad", max_runtime_s=-1)])
    runner = _runner(tmp_path)
    assert runner.queue_depth() == 2


# --------------------------------------------------------------------------- concurrency cap


def test_concurrency_cap_honored(tmp_path, region_lock_shim):
    _write_queue(tmp_path / "backfill", [
        _spec("c1", cmd=["sleep", "0.4"]),
        _spec("c2", cmd=["sleep", "0.4"]),
        _spec("c3", cmd=["sleep", "0.4"]),
    ])
    runner = _runner(tmp_path, max_concurrent=2)

    runner.tick()
    assert len(runner.jobs) == 2, "only max_concurrent jobs launch even with 3 pending"
    assert set(runner.jobs) <= {"c1", "c2", "c3"}

    deadline = time.time() + 5
    while time.time() < deadline and len(runner.jobs) > 0:
        time.sleep(0.05)
        runner.reap()
    assert len(runner.jobs) == 0, "first batch did not finish in time"

    runner.tick()  # reaps (no-op, already reaped) + dispatches the 3rd
    assert len(runner.jobs) <= 2

    deadline = time.time() + 5
    while time.time() < deadline and len(runner.jobs) > 0:
        time.sleep(0.05)
        runner.reap()
    assert len(runner.jobs) == 0

    done_ids = {r["id"] for r in _read_jsonl(runner.done_file)}
    assert done_ids == {"c1", "c2", "c3"}


def test_concurrency_cap_never_exceeded_across_many_ticks(tmp_path, region_lock_shim):
    specs = [_spec(f"j{i}", cmd=["sleep", "0.2"]) for i in range(5)]
    _write_queue(tmp_path / "backfill", specs)
    runner = _runner(tmp_path, max_concurrent=2)

    peak = 0
    deadline = time.time() + 10
    while time.time() < deadline:
        runner.tick()
        peak = max(peak, len(runner.jobs))
        done = {r["id"] for r in _read_jsonl(runner.done_file)}
        if done == {s["id"] for s in specs}:
            break
        time.sleep(0.05)
    assert peak <= 2
    done = {r["id"] for r in _read_jsonl(runner.done_file)}
    assert done == {s["id"] for s in specs}


# --------------------------------------------------------------------------- done.jsonl


def test_done_record_shape_on_success(tmp_path, region_lock_shim):
    _write_queue(tmp_path / "backfill", [_spec("ok1", cmd=["true"], role="backfill-shape-test",
                                                regions=["q3"], enqueued_by="tester")])
    runner = _runner(tmp_path, max_concurrent=1)
    runner.tick()
    deadline = time.time() + 5
    while time.time() < deadline and runner.jobs:
        time.sleep(0.05)
        runner.reap()
    rows = _read_jsonl(runner.done_file)
    assert len(rows) == 1
    row = rows[0]
    assert row["id"] == "ok1"
    assert row["status"] == "completed"
    assert row["exit_code"] == 0
    assert row["role"] == "backfill-shape-test"
    assert row["regions"] == ["q3"]
    assert row["enqueued_by"] == "tester"
    assert row["started_at"] is not None and row["ended_at"] is not None
    assert row["duration_s"] >= 0


def test_done_record_nonzero_exit_code(tmp_path, region_lock_shim):
    _write_queue(tmp_path / "backfill", [_spec("fail1", cmd=["false"])])
    runner = _runner(tmp_path, max_concurrent=1)
    runner.tick()
    deadline = time.time() + 5
    while time.time() < deadline and runner.jobs:
        time.sleep(0.05)
        runner.reap()
    rows = _read_jsonl(runner.done_file)
    assert rows[0]["exit_code"] != 0
    assert rows[0]["status"] == "completed"  # ran to completion; a nonzero rc is not a refusal


# --------------------------------------------------------------------------- detector


class _BusStub:
    def __init__(self, ok=True):
        self.calls: list[dict] = []
        self.ok = ok

    def __call__(self, message: dict) -> bool:
        self.calls.append(message)
        return self.ok


def test_detector_no_emit_when_no_hint(tmp_path):
    """Sustained-empty queue but NO ready_hint.txt at all -> never emits."""
    stub = _BusStub()
    runner = _runner(tmp_path, detector_threshold=3, bus_emit_fn=stub)
    for _ in range(6):
        runner.detector_tick()
    assert stub.calls == []


def test_detector_no_emit_when_queue_nonempty(tmp_path):
    """Hint present, but the queue is never empty -> never emits."""
    (tmp_path / "backfill").mkdir(parents=True, exist_ok=True)
    (tmp_path / "backfill" / "ready_hint.txt").write_text("see handoffs/active/x.md\n")
    _write_queue(tmp_path / "backfill", [_spec("perpetual", cmd=["sleep", "999"])])
    stub = _BusStub()
    runner = _runner(tmp_path, detector_threshold=3, bus_emit_fn=stub)
    for _ in range(6):
        runner.detector_tick()
    assert stub.calls == []


def test_detector_emits_exactly_once_on_sustained_empty_with_hint(tmp_path):
    (tmp_path / "backfill").mkdir(parents=True, exist_ok=True)
    (tmp_path / "backfill" / "ready_hint.txt").write_text("19 READY tasks — see handoff Y\n")
    stub = _BusStub()
    runner = _runner(tmp_path, detector_threshold=3, bus_emit_fn=stub)

    runner.detector_tick()  # streak 1
    assert stub.calls == []
    runner.detector_tick()  # streak 2
    assert stub.calls == []
    runner.detector_tick()  # streak 3 == threshold -> emits
    assert len(stub.calls) == 1
    msg = stub.calls[0]
    assert msg["kind"] == "finding"
    assert msg["needs_routing_to"] == ["coordinator-agent"]
    assert msg["action_required"] is True
    assert "READY tasks" in msg["payload"]["ready_hint"]

    # HOLD: further checks on the same unbroken state must not re-emit.
    for _ in range(10):
        runner.detector_tick()
    assert len(stub.calls) == 1


def test_detector_reemits_on_new_episode_after_queue_recovers(tmp_path):
    """Queue going non-empty and back to empty (with the SAME hint) is a new
    episode and gets a fresh finding — dedup suppresses repeats WITHIN an
    unbroken streak, not forever."""
    bf = tmp_path / "backfill"
    bf.mkdir(parents=True, exist_ok=True)
    (bf / "ready_hint.txt").write_text("same hint throughout\n")
    stub = _BusStub()
    runner = _runner(tmp_path, detector_threshold=2, bus_emit_fn=stub)

    runner.detector_tick()
    runner.detector_tick()
    assert len(stub.calls) == 1

    # Queue becomes non-empty -> streak breaks.
    _write_queue(bf, [_spec("busy", cmd=["sleep", "999"])])
    runner.detector_tick()
    assert len(stub.calls) == 1

    # Queue empties again (remove the queue file outright).
    (bf / "queue.jsonl").unlink()
    runner.detector_tick()
    runner.detector_tick()
    assert len(stub.calls) == 2, "a new empty episode with the same hint re-emits once"


def test_detector_retries_on_bus_failure_without_marking_emitted(tmp_path):
    bf = tmp_path / "backfill"
    bf.mkdir(parents=True, exist_ok=True)
    (bf / "ready_hint.txt").write_text("hint content\n")
    stub = _BusStub(ok=False)
    runner = _runner(tmp_path, detector_threshold=1, bus_emit_fn=stub)

    runner.detector_tick()
    runner.detector_tick()
    runner.detector_tick()
    assert len(stub.calls) == 3, "a failed send must retry on the NEXT check, never dedup on failure"
    assert runner._emitted_signature is None


# --------------------------------------------------------------------------- crash recovery


def test_reconcile_requeues_orphaned_inflight(tmp_path, region_lock_shim):
    bf = tmp_path / "backfill"
    _write_queue(bf, [_spec("orphan-1", cmd=["true"], role="backfill-orphan", regions=["q1"])])
    # Simulate a previous runner instance that claimed the job and crashed
    # before it could ever be reaped/recorded in done.jsonl.
    hb._write_atomic_json(bf / "inflight.json", {
        "orphan-1": {"pid": 999999, "started_at": time.time() - 100,
                     "role": "backfill-orphan", "regions": ["q1"]},
    })

    runner = _runner(tmp_path)  # __init__ runs reconcile_orphans()
    assert json.loads((bf / "inflight.json").read_text()) == {}
    assert runner.queue_depth() == 1, "orphaned job is eligible for dispatch again"

    runner.tick()
    assert "orphan-1" in runner.jobs
    deadline = time.time() + 5
    while time.time() < deadline and runner.jobs:
        time.sleep(0.05)
        runner.reap()
    rows = _read_jsonl(runner.done_file)
    assert [r["id"] for r in rows] == ["orphan-1"]
    assert rows[0]["status"] == "completed"


def test_reconcile_orphans_returns_the_cleared_ids(tmp_path):
    bf = tmp_path / "backfill"
    bf.mkdir(parents=True, exist_ok=True)
    # Constructed BEFORE inflight.json exists, so __init__'s own reconcile is a
    # harmless no-op and does not consume the entries written below.
    runner = _runner(tmp_path)

    hb._write_atomic_json(bf / "inflight.json", {
        "x": {"pid": 1, "started_at": 0, "role": "backfill-x", "regions": ["q0"]},
        "y": {"pid": 2, "started_at": 0, "role": "backfill-y", "regions": ["q1"]},
    })
    assert runner.reconcile_orphans() == ["x", "y"]
    assert json.loads((bf / "inflight.json").read_text()) == {}
    # Idempotent: a second call on the now-empty file clears nothing further.
    assert runner.reconcile_orphans() == []


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
