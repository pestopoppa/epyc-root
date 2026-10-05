"""WP-4 unit tests: kv_migration_direction_total + thrash_skipped counters.

Covers the counter primitive, the direction wiring via MigrationTransaction's
COMMITTED transition (forward + reverse), and the thrash-skip wiring at the
anti-thrash guards in ConcurrencyAwareBackend._maybe_spawn_reverse_migration.
"""

from __future__ import annotations

import importlib
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.metrics import migration_counters as mc  # noqa: E402
from src.scheduling.migration_transaction import (  # noqa: E402
    MigrationState,
    MigrationTransaction,
)

ca_mod = importlib.import_module("src.backends.concurrency_aware")


@pytest.fixture(autouse=True)
def _reset_counters():
    mc.reset()
    yield
    mc.reset()


# ── counter primitive ─────────────────────────────────────────────────────


def test_direction_for_target_quarter():
    assert mc.direction_for_target_quarter(-1) == mc.REVERSE
    assert mc.direction_for_target_quarter(0) == mc.FORWARD
    assert mc.direction_for_target_quarter(3) == mc.FORWARD


def test_record_direction_and_totals():
    mc.record_migration_direction(mc.FORWARD, session_id="s-a")
    mc.record_migration_direction(mc.FORWARD, session_id="s-b")
    mc.record_migration_direction(mc.REVERSE, session_id="s-a")
    assert mc.direction_total(mc.FORWARD) == 2
    assert mc.direction_total(mc.REVERSE) == 1
    assert mc.direction_total() == 3
    snap = mc.snapshot()
    assert snap[mc.DIRECTION_TOTAL] == {"forward": 2, "reverse": 1}
    assert [
        (e["direction"], e["session_id"], e["committed"])
        for e in snap[mc.RECENT_EVENTS]
    ] == [
        ("forward", "s-a", True),
        ("forward", "s-b", True),
        ("reverse", "s-a", True),
    ]


def test_record_thrash_skip_and_totals():
    mc.record_thrash_skip("cooldown")
    mc.record_thrash_skip("cooldown")
    mc.record_thrash_skip("session_cap")
    assert mc.thrash_skipped_total("cooldown") == 2
    assert mc.thrash_skipped_total("session_cap") == 1
    assert mc.thrash_skipped_total() == 3


def test_render_prometheus_shape():
    mc.record_migration_direction(mc.FORWARD)
    mc.record_thrash_skip("cooldown")
    text = mc.render_prometheus()
    assert 'kv_migration_direction_total{direction="forward"} 1' in text
    assert 'kv_migration_thrash_skipped_total{reason="cooldown"} 1' in text
    assert "# TYPE kv_migration_direction_total counter" in text


# ── direction wiring via MigrationTransaction COMMITTED ───────────────────


def _drive_to_committed(txn: MigrationTransaction) -> None:
    assert txn.advance(MigrationState.SAVING)
    assert txn.advance(MigrationState.RESTORING)
    assert txn.advance(MigrationState.VERIFIED)
    assert txn.advance(MigrationState.SOURCE_ERASED)
    assert txn.advance(MigrationState.COMMITTED)


def _txn(target_quarter: int) -> MigrationTransaction:
    return MigrationTransaction(
        role="frontdoor",
        session_id="s-1",
        source_url="http://localhost:8070",
        target_quarter=target_quarter,
        target_url="http://localhost:8280",
    )


def test_forward_migration_commit_increments_forward():
    _drive_to_committed(_txn(target_quarter=2))
    assert mc.direction_total(mc.FORWARD) == 1
    assert mc.direction_total(mc.REVERSE) == 0


def test_reverse_migration_commit_increments_reverse():
    _drive_to_committed(_txn(target_quarter=-1))
    assert mc.direction_total(mc.REVERSE) == 1
    assert mc.direction_total(mc.FORWARD) == 0


def test_aborted_migration_does_not_increment_direction():
    txn = _txn(target_quarter=1)
    assert txn.advance(MigrationState.SAVING)
    assert txn.advance(MigrationState.ABORTED, detail="save_failed")
    assert mc.direction_total() == 0


# ── thrash-skip wiring via _maybe_spawn_reverse_migration guards ──────────


class _StubBackend:
    def __init__(self, url: str = "http://localhost:0"):
        self.config = type("C", (), {"base_url": url})()
        self.url = url


def _backend(role: str = "frontdoor"):
    return ca_mod.ConcurrencyAwareBackend(
        full_backend=_StubBackend(),
        quarter_backends=[_StubBackend(), _StubBackend(), _StubBackend(), _StubBackend()],
        role=role,
    )


def test_cooldown_guard_records_thrash_skip():
    cab = _backend()
    now = time.monotonic()
    sid = "sess-cool"
    cab._session_quarter[sid] = 0
    cab._full_active = False
    cab._full_idle_since = now  # just released -> inside the cooldown window
    cab._session_last_seen[sid] = now
    cab._maybe_spawn_reverse_migration(0)
    assert mc.thrash_skipped_total("cooldown") == 1
    # No actual reverse migration should have been counted.
    assert mc.direction_total() == 0


def test_session_cap_guard_records_thrash_skip():
    cab = _backend()
    now = time.monotonic()
    sid = "sess-cap"
    cab._session_quarter[sid] = 1
    cab._full_active = False
    cab._full_idle_since = now - 10.0  # past the 2s cooldown
    cab._session_last_seen[sid] = now  # recent -> passes the window guard
    cab._reverse_migration_counts[sid] = cab._reverse_migration_session_cap()
    cab._maybe_spawn_reverse_migration(1)
    assert mc.thrash_skipped_total("session_cap") == 1
    assert mc.thrash_skipped_total("cooldown") == 0


def test_no_affinity_owner_records_nothing():
    cab = _backend()
    cab._maybe_spawn_reverse_migration(2)  # no session pinned to quarter 2
    assert mc.thrash_skipped_total() == 0
