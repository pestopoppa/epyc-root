"""A-1: cross-role region mutual exclusion (global region-mutex layer).

The per-role region locks (`cpu_region.{role}.{region}.lock`) provide NO
cross-role exclusion: frontdoor.q0.lock and ingest_long_context.q0.lock are
different inodes, so two DIFFERENT roles can both hold region q0 at once
(the TOCTOU that makes cross-role disjoint placement only advisory).

A-1 adds an additional role-agnostic layer `cpu_region.GLOBAL.{region}.lock`,
acquired FIRST (sorted by region), gated behind
ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT. Flag off → today's behavior
(overlap allowed). Flag on → cross-role same-region acquisition serializes.

These tests use real OS processes (multiprocessing, spawn) because flock
semantics within a single process are misleading: the same process can
re-acquire (or appear to hold) its own flock, so a single-process test could
not distinguish "mutually excluded" from "both think they hold it".
"""

from __future__ import annotations

import json
import multiprocessing as mp
import os
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _hold_region_worker(
    root: str,
    tmpdir: str,
    flag_on: bool,
    barrier_path: str,
    result_path: str,
    role: str,
    region: str,
    hold_s: float,
) -> None:
    """Child process: acquire `region` for `role`, hold `hold_s`, record the
    acquire/release wall-clock window to result_path as JSON. Synchronizes its
    start by spinning on barrier_path so both children race together."""
    if root not in sys.path:
        sys.path.insert(0, root)
    os.environ["ORCHESTRATOR_TMP_DIR"] = tmpdir
    # Keep lock polling snappy so the second waiter acquires promptly on release.
    os.environ["ORCHESTRATOR_INFERENCE_LOCK_POLL_MS"] = "10"
    if flag_on:
        os.environ["ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT"] = "1"
    else:
        os.environ.pop("ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT", None)

    from src.runtime.cpu_region_lock import cpu_region_lock

    # Barrier: spin until the parent signals both children are launched.
    deadline = time.time() + 10.0
    while not os.path.exists(barrier_path):
        if time.time() > deadline:
            break
        time.sleep(0.005)

    with cpu_region_lock(role, {region}, timeout_s=30.0):
        acq = time.time()
        time.sleep(hold_s)
        rel = time.time()
    with open(result_path, "w", encoding="utf-8") as fh:
        json.dump({"acq": acq, "rel": rel, "role": role}, fh)


def _run_two_role_race(tmp_path: Path, flag_on: bool, hold_s: float = 0.4):
    """Launch two processes, different roles, BOTH wanting region q0. Return
    the two (acq, rel) windows."""
    # fork (Linux default): child inherits the imported test module + sys.path,
    # so the target unpickles without a re-import. Real separate processes →
    # honest cross-process flock semantics (spawn fails to import the pytest
    # test module in the child).
    ctx = mp.get_context("fork")
    barrier = tmp_path / "barrier"
    r1 = tmp_path / "r1.json"
    r2 = tmp_path / "r2.json"
    common = (str(ROOT), str(tmp_path), flag_on, str(barrier))
    p1 = ctx.Process(
        target=_hold_region_worker,
        args=(*common, str(r1), "frontdoor", "q0", hold_s),
    )
    p2 = ctx.Process(
        target=_hold_region_worker,
        args=(*common, str(r2), "ingest_long_context", "q0", hold_s),
    )
    try:
        p1.start()
        p2.start()
        time.sleep(0.3)  # let both reach the barrier spin
        barrier.write_text("go")
        # Hard wall-clock guard: pytest-timeout is not installed in this venv,
        # so @pytest.mark.timeout is inert. Bound the join ourselves and kill
        # any straggler in the finally so a hung worker can never hang the run.
        p1.join(timeout=30)
        p2.join(timeout=30)
        assert not p1.is_alive() and not p2.is_alive(), "worker hung past 30s"
        assert p1.exitcode == 0 and p2.exitcode == 0, (p1.exitcode, p2.exitcode)
        w1 = json.loads(r1.read_text())
        w2 = json.loads(r2.read_text())
        return w1, w2
    finally:
        for p in (p1, p2):
            if p.is_alive():
                p.terminate()
            p.join(timeout=5)
            if p.is_alive():  # terminate didn't take → SIGKILL
                p.kill()
                p.join(timeout=5)


def _windows_overlap(w1: dict, w2: dict, eps: float = 0.0) -> bool:
    return (w1["acq"] < w2["rel"] - eps) and (w2["acq"] < w1["rel"] - eps)


def test_flag_off_allows_cross_role_same_region_overlap(tmp_path: Path) -> None:
    """Documents the TOCTOU: with the flag OFF, two different roles BOTH hold
    region q0 simultaneously (per-role lock files don't exclude each other)."""
    w1, w2 = _run_two_role_race(tmp_path, flag_on=False)
    assert _windows_overlap(w1, w2), (
        f"expected overlap with flag off (TOCTOU), got {w1} {w2}"
    )


def test_flag_on_serializes_cross_role_same_region(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A-1: with the flag ON, the GLOBAL region mutex serializes cross-role
    same-region acquisition — hold windows are disjoint (one waits)."""
    w1, w2 = _run_two_role_race(tmp_path, flag_on=True)
    assert not _windows_overlap(w1, w2, eps=0.01), (
        f"expected serialized (disjoint) windows with flag on, got {w1} {w2}"
    )
    # And no leftover GLOBAL lock is held after both exit (clean release):
    from src.runtime.cpu_region_lock import global_region_lock_path

    monkeypatch.setenv("ORCHESTRATOR_TMP_DIR", str(tmp_path))
    gpath = global_region_lock_path("q0")
    # File may exist (created on demand) but must be acquirable now.
    import fcntl

    fh = open(gpath, "a+b")
    try:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)  # must not raise
    finally:
        fh.close()


def test_active_region_holders_ignores_global_pseudo_role(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Attribution must stay role-only: a held GLOBAL lock must NOT surface as
    a 'GLOBAL' role in active_region_holders()."""
    monkeypatch.setenv("ORCHESTRATOR_TMP_DIR", str(tmp_path))
    from src.runtime.cpu_region_lock import active_region_holders, global_region_lock_path
    import fcntl

    gpath = global_region_lock_path("q0")
    gpath.parent.mkdir(parents=True, exist_ok=True)
    fh = open(gpath, "a+b")
    try:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        holders = active_region_holders(
            instance_regions={("frontdoor", 1): frozenset({"q0"})}
        )
        assert "GLOBAL" not in holders
    finally:
        fh.close()
