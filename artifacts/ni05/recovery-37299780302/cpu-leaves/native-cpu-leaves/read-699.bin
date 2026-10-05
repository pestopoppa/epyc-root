"""WP-4 tests: quarter → full reverse migration trigger + guards.

Behavior under test (gated by ORCHESTRATOR_REVERSE_MIGRATION=1):

  When a quarter releases:
    1. Identify the session that holds affinity to the released quarter.
    2. Check four guards:
        - full has been idle for ≥ cooldown_ms (default 2s)
        - session has been seen within window_ms (default 30s)
        - per-session migration count < cap (default 5)
        - not already in flight for this session
    3. If all pass: spawn _reverse_migrate_kv(session_id, quarter_idx) in a
       daemon thread.

The actual save → restore → erase is exercised in test_migration_transaction
(transactional model) and live-server integration (deferred). These tests
mock _reverse_migrate_kv and focus on the trigger logic.
"""

from __future__ import annotations

import importlib
import sys
import time
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "server"))

ca_mod = importlib.import_module("src.backends.concurrency_aware")


class _StubBackend:
    def __init__(self, url: str):
        self.config = type("C", (), {"base_url": url})()
        self.url = url


def _make_backend(monkeypatch: pytest.MonkeyPatch) -> "ca_mod.ConcurrencyAwareBackend":
    monkeypatch.setenv("ORCHESTRATOR_REVERSE_MIGRATION", "1")
    monkeypatch.setenv("ORCHESTRATOR_REVERSE_MIGRATION_COOLDOWN_MS", "20")  # 20ms for fast tests
    monkeypatch.setenv("ORCHESTRATOR_REVERSE_MIGRATION_WINDOW_MS", "5000")
    monkeypatch.setenv("ORCHESTRATOR_REVERSE_MIGRATION_SESSION_CAP", "3")
    full = _StubBackend("http://localhost:8070")
    quarters = [_StubBackend(f"http://localhost:80{80 + i * 100}") for i in range(4)]
    return ca_mod.ConcurrencyAwareBackend(
        full_backend=full, quarter_backends=quarters, role="frontdoor", full_port=8070,
    )


def _seed_session_on_quarter(
    backend: "ca_mod.ConcurrencyAwareBackend",
    session_id: str,
    quarter_idx: int,
    last_seen_offset_s: float = 0.0,
) -> None:
    """Populate the per-session affinity + last-seen so _release sees it."""
    now = time.monotonic()
    with backend._lock:
        backend._session_quarter[session_id] = quarter_idx
        backend._session_last_seen[session_id] = now - last_seen_offset_s
        backend._full_idle_since = now - 10  # idle for "long enough" by default
        backend._full_active = False


@pytest.fixture
def _capture_reverse(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, int]]:
    """Replace _reverse_migrate_kv with a no-op recorder; return the list."""
    calls: list[tuple[str, int]] = []

    def _fake(self, session_id, source_quarter):
        calls.append((session_id, source_quarter))

    monkeypatch.setattr(ca_mod.ConcurrencyAwareBackend, "_reverse_migrate_kv", _fake)
    return calls


# ── Happy path: all guards pass → migration fires ──────────────────────


def test_release_triggers_reverse_migration_when_all_guards_pass(
    monkeypatch: pytest.MonkeyPatch, _capture_reverse: list,
) -> None:
    backend = _make_backend(monkeypatch)
    _seed_session_on_quarter(backend, "sess-warm", quarter_idx=2)

    backend._release(idx=2, is_full=False)

    # Brief sleep for daemon thread to schedule; not strictly required because
    # _capture_reverse intercepts before any thread work happens.
    time.sleep(0.01)
    assert ("sess-warm", 2) in _capture_reverse


# ── Guard: full not idle long enough ────────────────────────────────────


def test_no_reverse_migration_when_full_still_busy(
    monkeypatch: pytest.MonkeyPatch, _capture_reverse: list,
) -> None:
    backend = _make_backend(monkeypatch)
    _seed_session_on_quarter(backend, "sess-warm", quarter_idx=2)
    with backend._lock:
        backend._full_active = True  # full is currently busy

    backend._release(idx=2, is_full=False)
    assert _capture_reverse == []


def test_no_reverse_migration_during_cooldown(
    monkeypatch: pytest.MonkeyPatch, _capture_reverse: list,
) -> None:
    """Full became idle only 5ms ago — cooldown is 20ms → no migration yet."""
    backend = _make_backend(monkeypatch)
    _seed_session_on_quarter(backend, "sess-warm", quarter_idx=2)
    with backend._lock:
        backend._full_idle_since = time.monotonic() - 0.005  # 5ms < 20ms cooldown

    backend._release(idx=2, is_full=False)
    assert _capture_reverse == []


# ── Guard: session too cold (last_seen outside window) ──────────────────


def test_no_reverse_migration_when_session_cold(
    monkeypatch: pytest.MonkeyPatch, _capture_reverse: list,
) -> None:
    backend = _make_backend(monkeypatch)
    # Window is 5000ms; seed last_seen 10s ago → outside window.
    _seed_session_on_quarter(backend, "sess-cold", quarter_idx=2, last_seen_offset_s=10.0)

    backend._release(idx=2, is_full=False)
    assert _capture_reverse == []


# ── Guard: per-session migration cap ───────────────────────────────────


def test_no_reverse_migration_after_session_cap_hit(
    monkeypatch: pytest.MonkeyPatch, _capture_reverse: list,
) -> None:
    backend = _make_backend(monkeypatch)
    _seed_session_on_quarter(backend, "sess-flappy", quarter_idx=2)
    with backend._lock:
        backend._reverse_migration_counts["sess-flappy"] = 3  # cap is 3

    backend._release(idx=2, is_full=False)
    assert _capture_reverse == []


# ── Guard: in-flight de-dup ────────────────────────────────────────────


def test_no_double_fire_when_already_in_flight(
    monkeypatch: pytest.MonkeyPatch, _capture_reverse: list,
) -> None:
    backend = _make_backend(monkeypatch)
    _seed_session_on_quarter(backend, "sess-running", quarter_idx=2)
    with backend._lock:
        backend._reverse_migration_in_flight["sess-running"] = True

    backend._release(idx=2, is_full=False)
    assert _capture_reverse == []


# ── Guard: no affinity holder for released quarter ─────────────────────


def test_no_reverse_migration_when_quarter_unowned(
    monkeypatch: pytest.MonkeyPatch, _capture_reverse: list,
) -> None:
    backend = _make_backend(monkeypatch)
    with backend._lock:
        backend._full_idle_since = time.monotonic() - 10
        backend._full_active = False
    # No session_quarter entry for any quarter.

    backend._release(idx=2, is_full=False)
    assert _capture_reverse == []


# ── Env flag off → trigger inert ───────────────────────────────────────


def test_no_reverse_migration_when_flag_off(
    monkeypatch: pytest.MonkeyPatch, _capture_reverse: list,
) -> None:
    monkeypatch.delenv("ORCHESTRATOR_REVERSE_MIGRATION", raising=False)
    full = _StubBackend("http://localhost:8070")
    quarters = [_StubBackend(f"http://localhost:80{80 + i * 100}") for i in range(4)]
    backend = ca_mod.ConcurrencyAwareBackend(
        full_backend=full, quarter_backends=quarters, role="frontdoor", full_port=8070,
    )
    _seed_session_on_quarter(backend, "sess-x", quarter_idx=2)

    backend._release(idx=2, is_full=False)
    assert _capture_reverse == []


# ── Counter increments + cap enforcement across multiple releases ──────


def test_per_session_cap_increments_and_blocks(
    monkeypatch: pytest.MonkeyPatch, _capture_reverse: list,
) -> None:
    backend = _make_backend(monkeypatch)
    _seed_session_on_quarter(backend, "sess-rep", quarter_idx=2)

    # First release: count 0→1, fires.
    backend._release(idx=2, is_full=False)
    assert len(_capture_reverse) == 1
    with backend._lock:
        assert backend._reverse_migration_counts["sess-rep"] == 1
        # Reset in-flight flag (test fixture doesn't actually run the migration).
        backend._reverse_migration_in_flight.pop("sess-rep", None)

    # Subsequent releases: count increments. Cap is 3, so 3 fires total.
    backend._release(idx=2, is_full=False)
    with backend._lock:
        backend._reverse_migration_in_flight.pop("sess-rep", None)
    backend._release(idx=2, is_full=False)
    with backend._lock:
        backend._reverse_migration_in_flight.pop("sess-rep", None)
    backend._release(idx=2, is_full=False)  # cap hit; no fire

    assert len(_capture_reverse) == 3
    with backend._lock:
        assert backend._reverse_migration_counts["sess-rep"] == 3


# ── Env var configurability ────────────────────────────────────────────


def test_env_defaults() -> None:
    import os as _os
    # Ensure no env leak from earlier tests
    for k in (
        "ORCHESTRATOR_REVERSE_MIGRATION_COOLDOWN_MS",
        "ORCHESTRATOR_REVERSE_MIGRATION_WINDOW_MS",
        "ORCHESTRATOR_REVERSE_MIGRATION_SESSION_CAP",
    ):
        _os.environ.pop(k, None)
    assert ca_mod.ConcurrencyAwareBackend._reverse_migration_cooldown_ms() == 2000
    assert ca_mod.ConcurrencyAwareBackend._reverse_migration_window_ms() == 30000
    assert ca_mod.ConcurrencyAwareBackend._reverse_migration_session_cap() == 5


def test_env_invalid_falls_back_to_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ORCHESTRATOR_REVERSE_MIGRATION_COOLDOWN_MS", "garbage")
    assert ca_mod.ConcurrencyAwareBackend._reverse_migration_cooldown_ms() == 2000
