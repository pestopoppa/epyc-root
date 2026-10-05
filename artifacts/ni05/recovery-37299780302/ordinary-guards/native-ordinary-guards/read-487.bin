"""WP-3 integration: policy-gating + budget extraction on the existing
session-handover KV migration trigger in _dispatch.

The handoff's WP-3 originally proposed a proactive load-transition trigger
inside the WP-2 poll loop. That trigger was explored and removed: _migrate_kv
cannot preempt an in-flight decode, so spawning a migration while waiting
on a queue does not unblock the queue — the existing inference must finish
and release its lock, after which WP-2's re-evaluation finds a safe candidate.

What WP-3 actually ships is:
  * Transactional wrapper (test_migration_transaction.py covers this).
  * Refactored _migrate_kv that drives MigrationTransaction states.
  * Policy-gating: FULL_DISABLED / QUEUE_ONLY skip migration.
  * Per-request migration_budget_ms read from ChatRequest and passed through
    to MigrationTransaction.

This file tests the policy gate + budget extraction on the existing trigger.
"""

from __future__ import annotations

import importlib
import sys
import threading
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "server"))

ca_mod = importlib.import_module("src.backends.concurrency_aware")
mt_mod = importlib.import_module("src.scheduling.migration_transaction")


class _StubBackend:
    def __init__(self, url: str):
        self.config = type("C", (), {"base_url": url})()
        self.url = url


def _make_backend(monkeypatch: pytest.MonkeyPatch) -> "ca_mod.ConcurrencyAwareBackend":
    monkeypatch.setenv("ORCHESTRATOR_PER_REGION_LOCKS", "1")
    full = _StubBackend("http://localhost:8070")
    quarters = [_StubBackend(f"http://localhost:80{80 + i * 100}") for i in range(4)]
    return ca_mod.ConcurrencyAwareBackend(
        full_backend=full, quarter_backends=quarters, role="frontdoor", full_port=8070,
    )


# ── migration_budget_ms extraction ──────────────────────────────────────


def test_migration_budget_extracted_from_request_object(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend = _make_backend(monkeypatch)

    class _Req:
        session_id = "s"
        migration_budget_ms = 7777

    assert backend._extract_migration_budget_ms(_Req()) == 7777


def test_migration_budget_missing_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    backend = _make_backend(monkeypatch)

    class _Bare:
        pass

    assert backend._extract_migration_budget_ms(_Bare()) is None
    assert backend._extract_migration_budget_ms(None) is None


def test_migration_budget_invalid_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    backend = _make_backend(monkeypatch)

    class _Bad:
        migration_budget_ms = "garbage"

    assert backend._extract_migration_budget_ms(_Bad()) is None

    class _Neg:
        migration_budget_ms = -1

    assert backend._extract_migration_budget_ms(_Neg()) is None

    class _Zero:
        migration_budget_ms = 0

    assert backend._extract_migration_budget_ms(_Zero()) is None


# ── Policy-gating on the session-handover migration trigger ─────────────


@pytest.fixture
def _quiet_dispatcher(monkeypatch: pytest.MonkeyPatch):
    """Stub the per-region-lock path so _dispatch's session-handover branch
    runs without real lock acquisitions or background migration HTTP."""
    monkeypatch.setattr(
        "src.runtime.cpu_region_lock.cpu_region_lock_for_instance",
        lambda role, idx, **kw: _FakeFullLock(),
    )
    monkeypatch.setattr("src.runtime.cpu_region_lock.active_region_holders", lambda: {})
    monkeypatch.setattr("src.runtime.instance_topology.get_instance_regions", lambda: {})


class _FakeFullLock:
    def __enter__(self):
        return ["/tmp/mock.lock"]

    def __exit__(self, *exc):
        return False


def test_migration_fires_under_default_policy(
    monkeypatch: pytest.MonkeyPatch, _quiet_dispatcher
) -> None:
    """Default policy SOLO_PREFER_FULL → migration spawned on session handover."""
    backend = _make_backend(monkeypatch)
    backend._full_last_session = "old-sess"

    spawned_threads: list[threading.Thread] = []
    real_thread_init = threading.Thread.__init__

    def _capture_thread(self, *args, **kwargs):
        real_thread_init(self, *args, **kwargs)
        if "kv-migrate" in (kwargs.get("name") or ""):
            spawned_threads.append(self)

    monkeypatch.setattr(threading.Thread, "__init__", _capture_thread)

    with backend._dispatch(session_id="new-sess", migration_budget_ms=4242):
        pass

    assert len(spawned_threads) == 1
    assert "kv-migrate" in spawned_threads[0].name
    assert "old-sess" in spawned_threads[0].name


def test_migration_skipped_under_full_disabled_policy(
    monkeypatch: pytest.MonkeyPatch, _quiet_dispatcher
) -> None:
    """Policy FULL_DISABLED → no migration even on session handover."""
    from src.scheduling.placement_policy import RolePlacementPolicy

    monkeypatch.setattr(
        "src.scheduling.placement_policy.get_placement_policy",
        lambda role, numa_config=None: RolePlacementPolicy.FULL_DISABLED,
    )
    backend = _make_backend(monkeypatch)
    backend._full_last_session = "old-sess"

    spawned_threads: list[threading.Thread] = []
    real_thread_init = threading.Thread.__init__

    def _capture_thread(self, *args, **kwargs):
        real_thread_init(self, *args, **kwargs)
        if "kv-migrate" in (kwargs.get("name") or ""):
            spawned_threads.append(self)

    monkeypatch.setattr(threading.Thread, "__init__", _capture_thread)

    with backend._dispatch(session_id="new-sess"):
        pass

    assert spawned_threads == []  # FULL_DISABLED → migration skipped


def test_migration_skipped_under_queue_only_policy(
    monkeypatch: pytest.MonkeyPatch, _quiet_dispatcher
) -> None:
    """Policy QUEUE_ONLY → no migration."""
    from src.scheduling.placement_policy import RolePlacementPolicy

    monkeypatch.setattr(
        "src.scheduling.placement_policy.get_placement_policy",
        lambda role, numa_config=None: RolePlacementPolicy.QUEUE_ONLY,
    )
    backend = _make_backend(monkeypatch)
    backend._full_last_session = "old-sess"

    spawned_threads: list[threading.Thread] = []
    real_thread_init = threading.Thread.__init__

    def _capture_thread(self, *args, **kwargs):
        real_thread_init(self, *args, **kwargs)
        if "kv-migrate" in (kwargs.get("name") or ""):
            spawned_threads.append(self)

    monkeypatch.setattr(threading.Thread, "__init__", _capture_thread)

    with backend._dispatch(session_id="new-sess"):
        pass

    assert spawned_threads == []


def test_migration_fires_under_burst_prefer_split_policy(
    monkeypatch: pytest.MonkeyPatch, _quiet_dispatcher
) -> None:
    """Policy BURST_PREFER_SPLIT → migration still fires."""
    from src.scheduling.placement_policy import RolePlacementPolicy

    monkeypatch.setattr(
        "src.scheduling.placement_policy.get_placement_policy",
        lambda role, numa_config=None: RolePlacementPolicy.BURST_PREFER_SPLIT,
    )
    backend = _make_backend(monkeypatch)
    backend._full_last_session = "old-sess"

    spawned_threads: list[threading.Thread] = []
    real_thread_init = threading.Thread.__init__

    def _capture_thread(self, *args, **kwargs):
        real_thread_init(self, *args, **kwargs)
        if "kv-migrate" in (kwargs.get("name") or ""):
            spawned_threads.append(self)

    monkeypatch.setattr(threading.Thread, "__init__", _capture_thread)

    with backend._dispatch(session_id="new-sess"):
        pass

    assert len(spawned_threads) == 1


def test_migration_skipped_when_same_session(
    monkeypatch: pytest.MonkeyPatch, _quiet_dispatcher
) -> None:
    """Same session continuing → no migration regardless of policy."""
    backend = _make_backend(monkeypatch)
    backend._full_last_session = "same-sess"

    spawned_threads: list[threading.Thread] = []
    real_thread_init = threading.Thread.__init__

    def _capture_thread(self, *args, **kwargs):
        real_thread_init(self, *args, **kwargs)
        if "kv-migrate" in (kwargs.get("name") or ""):
            spawned_threads.append(self)

    monkeypatch.setattr(threading.Thread, "__init__", _capture_thread)

    with backend._dispatch(session_id="same-sess"):
        pass

    assert spawned_threads == []
