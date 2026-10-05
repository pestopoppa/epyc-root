"""WP-3 unit tests: MigrationTransaction state machine + observability."""

from __future__ import annotations

import threading
import time

import pytest

from src.scheduling.migration_transaction import (
    MigrationState,
    MigrationTransaction,
)


def _new_txn(**overrides) -> MigrationTransaction:
    defaults = dict(
        role="frontdoor",
        session_id="s-test",
        source_url="http://localhost:8070",
        target_quarter=2,
        target_url="http://localhost:8280",
    )
    defaults.update(overrides)
    return MigrationTransaction(**defaults)


# ── Construction ──────────────────────────────────────────────────────


def test_initial_state_is_planned() -> None:
    txn = _new_txn()
    assert txn.state is MigrationState.PLANNED
    assert not txn.is_terminal
    assert not txn.is_safe_to_proceed
    assert txn.elapsed_ms >= 0


def test_unique_txn_ids() -> None:
    t1 = _new_txn()
    t2 = _new_txn()
    assert t1.txn_id != t2.txn_id
    assert len(t1.txn_id) == 12  # uuid hex prefix


def test_state_history_starts_with_planned_entry() -> None:
    txn = _new_txn()
    assert len(txn.state_history) == 1
    assert txn.state_history[0][0] is MigrationState.PLANNED


# ── Legal forward path ─────────────────────────────────────────────────


def test_full_legal_progression_to_committed() -> None:
    txn = _new_txn()
    assert txn.advance(MigrationState.SAVING)
    assert txn.advance(MigrationState.RESTORING)
    assert txn.advance(MigrationState.VERIFIED)
    assert txn.is_safe_to_proceed
    assert txn.advance(MigrationState.SOURCE_ERASED)
    assert txn.advance(MigrationState.COMMITTED)
    assert txn.is_terminal
    assert txn.state is MigrationState.COMMITTED
    assert len(txn.state_history) == 6  # PLANNED + 5 transitions


def test_verified_releases_event() -> None:
    txn = _new_txn()
    txn.advance(MigrationState.SAVING)
    txn.advance(MigrationState.RESTORING)
    assert not txn.event.is_set()
    txn.advance(MigrationState.VERIFIED)
    assert txn.event.is_set()


# ── Illegal transitions ────────────────────────────────────────────────


@pytest.mark.parametrize(
    "from_state, to_state",
    [
        (MigrationState.PLANNED, MigrationState.RESTORING),    # skip SAVING
        (MigrationState.PLANNED, MigrationState.VERIFIED),     # skip 2 steps
        (MigrationState.SAVING, MigrationState.SOURCE_ERASED),  # skip 2 steps
        (MigrationState.RESTORING, MigrationState.COMMITTED),   # skip 3 steps
        (MigrationState.VERIFIED, MigrationState.SAVING),       # backwards
    ],
)
def test_illegal_transitions_rejected(
    from_state: MigrationState, to_state: MigrationState
) -> None:
    txn = _new_txn()
    # Drive to from_state legally
    progression = [
        MigrationState.SAVING,
        MigrationState.RESTORING,
        MigrationState.VERIFIED,
        MigrationState.SOURCE_ERASED,
        MigrationState.COMMITTED,
    ]
    for step in progression:
        if step is from_state:
            txn.state = from_state  # we already advanced via attempts; align
            break
        if not txn.advance(step):
            break
    txn.state = from_state  # ensure clean alignment

    assert not txn.advance(to_state), f"{from_state} → {to_state} should be illegal"
    assert txn.state is from_state  # state unchanged on rejection


# ── Abort handling ─────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "intermediate",
    [MigrationState.PLANNED, MigrationState.SAVING, MigrationState.RESTORING, MigrationState.VERIFIED],
)
def test_abort_from_any_non_terminal_state(intermediate: MigrationState) -> None:
    txn = _new_txn()
    if intermediate is not MigrationState.PLANNED:
        txn.advance(MigrationState.SAVING)
    if intermediate in (MigrationState.RESTORING, MigrationState.VERIFIED):
        txn.advance(MigrationState.RESTORING)
    if intermediate is MigrationState.VERIFIED:
        txn.advance(MigrationState.VERIFIED)

    assert txn.advance(MigrationState.ABORTED, detail="test abort")
    assert txn.state is MigrationState.ABORTED
    assert txn.detail == "test abort"
    assert txn.is_terminal
    assert txn.event.is_set()


def test_cannot_abort_terminal_states() -> None:
    txn = _new_txn()
    for s in [MigrationState.SAVING, MigrationState.RESTORING, MigrationState.VERIFIED,
              MigrationState.SOURCE_ERASED, MigrationState.COMMITTED]:
        txn.advance(s)
    assert txn.state is MigrationState.COMMITTED
    assert not txn.advance(MigrationState.ABORTED)


# ── wait_for_completion semantics ──────────────────────────────────────


def test_wait_for_completion_blocks_until_verified() -> None:
    txn = _new_txn(migration_budget_ms=5_000)

    def _advancer():
        time.sleep(0.05)
        txn.advance(MigrationState.SAVING)
        time.sleep(0.05)
        txn.advance(MigrationState.RESTORING)
        time.sleep(0.05)
        txn.advance(MigrationState.VERIFIED)

    t = threading.Thread(target=_advancer, daemon=True)
    t.start()
    state = txn.wait_for_completion()
    assert state is MigrationState.VERIFIED
    t.join(timeout=1.0)


def test_wait_for_completion_unblocks_on_abort() -> None:
    txn = _new_txn(migration_budget_ms=5_000)

    def _aborter():
        time.sleep(0.02)
        txn.advance(MigrationState.ABORTED, detail="save_failed")

    threading.Thread(target=_aborter, daemon=True).start()
    state = txn.wait_for_completion()
    assert state is MigrationState.ABORTED


def test_wait_for_completion_honors_budget_deadline() -> None:
    # Budget of 50ms, no advancement → wait returns PLANNED at deadline.
    txn = _new_txn(migration_budget_ms=50)
    t0 = time.monotonic()
    state = txn.wait_for_completion()
    elapsed = time.monotonic() - t0
    assert state is MigrationState.PLANNED  # never advanced
    assert 0.04 <= elapsed <= 0.3  # ~50ms with scheduling slack


# ── Snapshot for telemetry ─────────────────────────────────────────────


def test_snapshot_includes_state_history() -> None:
    txn = _new_txn()
    txn.advance(MigrationState.SAVING)
    txn.advance(MigrationState.RESTORING)
    snap = txn.snapshot()

    assert snap["txn_id"] == txn.txn_id
    assert snap["role"] == "frontdoor"
    assert snap["state"] == "restoring"
    assert snap["is_terminal"] is False
    assert snap["is_safe_to_proceed"] is False
    assert len(snap["state_history"]) == 3  # planned + saving + restoring
    assert snap["state_history"][0]["state"] == "planned"
    assert snap["state_history"][-1]["state"] == "restoring"


def test_snapshot_terminal_safe_after_verified() -> None:
    txn = _new_txn()
    for s in [MigrationState.SAVING, MigrationState.RESTORING, MigrationState.VERIFIED]:
        txn.advance(s)
    snap = txn.snapshot()
    assert snap["is_safe_to_proceed"] is True
    assert snap["is_terminal"] is False  # VERIFIED isn't terminal; SOURCE_ERASED/COMMITTED are
