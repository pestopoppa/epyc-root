"""Loose-end fix 4: KV migration ported into per-region-locks dispatch.

Verifies that when ORCHESTRATOR_PER_REGION_LOCKS=1 and a NEW session arrives
on the full instance while an OLD session was just there, _dispatch kicks off
an async _migrate_kv thread for the OLD session.
"""

from __future__ import annotations

import importlib
import sys
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

ca_mod = importlib.import_module("src.backends.concurrency_aware")


class _StubBackend:
    def __init__(self, url: str):
        self.config = type("C", (), {"base_url": url})()
        self.url = url

    def infer_stream_text(self, *_a, **_kw):
        return "OK"


def _make_cab(role: str = "frontdoor", *, per_region_locks: bool = True):
    """Build a ConcurrencyAwareBackend for testing."""
    import os
    os.environ["ORCHESTRATOR_PER_REGION_LOCKS"] = "1" if per_region_locks else "0"
    full = _StubBackend("http://localhost:8070")
    quarters = [_StubBackend(f"http://localhost:{p}") for p in (8080, 8180, 8280, 8380)]
    return ca_mod.ConcurrencyAwareBackend(
        full_backend=full,
        quarter_backends=quarters,
        role=role,
        full_port=8070,
    )


@contextmanager
def _fake_lock_ctx():
    """Stub the cpu_region_lock_for_instance context manager — always succeeds."""
    yield frozenset()


def _patch_lock_grants_full_only(cab):
    """Patch cpu_region_lock so only the full instance acquires (quarter locks fail)."""
    def _grants_full_or_disjoint(role, instance_idx, *, timeout_s=None, deadline_s=None, **kw):
        # Only succeed for full (idx 0). Quarters return a context that raises CpuRegionLockTimeout.
        if instance_idx == 0:
            return _fake_lock_ctx()
        class _Failing:
            def __enter__(self_inner):
                from src.runtime.cpu_region_lock import CpuRegionLockTimeout
                raise CpuRegionLockTimeout("test: quarter locked")
            def __exit__(self_inner, *_a):
                return False
        return _Failing()
    return mock.patch("src.runtime.cpu_region_lock.cpu_region_lock_for_instance",
                      side_effect=_grants_full_or_disjoint)


def _patch_lock_grants_all(cab):
    """Patch cpu_region_lock to always succeed (first acquired wins)."""
    return mock.patch("src.runtime.cpu_region_lock.cpu_region_lock_for_instance",
                      side_effect=lambda *a, **kw: _fake_lock_ctx())


def test_get_base_url_handles_live_prefix_cache_wrapper_shape() -> None:
    inner = _StubBackend("http://localhost:8070")
    wrapper = type("Wrapper", (), {"backend": inner})()

    assert ca_mod._get_base_url(wrapper) == "http://localhost:8070"


def test_per_region_locks_dispatch_kicks_off_migration_on_session_swap(monkeypatch) -> None:
    """When OLD session is on full and NEW session arrives, _dispatch should
    kick off async _migrate_kv(OLD, quarter_idx)."""
    cab = _make_cab(per_region_locks=True)
    # Pre-condition: OLD session is the last-on-full
    cab._full_last_session = "session_OLD"

    migrate_calls: list[tuple[str, int]] = []
    migrate_event = threading.Event()

    def fake_migrate(session_id, target_quarter, transaction=None):
        migrate_calls.append((session_id, target_quarter))
        migrate_event.set()

    monkeypatch.setattr(cab, "_migrate_kv", fake_migrate)

    with _patch_lock_grants_all(cab):
        with cab._dispatch(session_id="session_NEW") as (backend, idx, is_full):
            assert is_full  # acquired full first per preference

    # Migration thread should fire
    assert migrate_event.wait(timeout=2.0), "migration thread did not start"
    assert len(migrate_calls) == 1
    old_session, target_q = migrate_calls[0]
    assert old_session == "session_OLD"
    # Target should be a disjoint quarter (frontdoor full on NUMA_NODE0 → q2 or q3)
    assert target_q in cab._quarter_preference_order[:2]


def test_per_region_locks_pending_migration_suppresses_duplicate_start(monkeypatch) -> None:
    cab = _make_cab(per_region_locks=True)
    cab._full_last_session = "session_OLD"
    cab._set_session_state(
        "session_OLD",
        state=ca_mod._STATE_MIGRATION_PENDING,
        quarter=2,
    )

    migrate_calls: list[tuple[str, int]] = []

    def fake_migrate(session_id, target_quarter, transaction=None):
        migrate_calls.append((session_id, target_quarter))

    monkeypatch.setattr(cab, "_migrate_kv", fake_migrate)

    with _patch_lock_grants_all(cab):
        with cab._dispatch(session_id="session_NEW_1") as (_backend, _idx, is_full):
            assert is_full

    time.sleep(0.1)
    assert migrate_calls == []


def test_per_region_locks_distinct_full_handoffs_can_start_distinct_migrations(monkeypatch) -> None:
    cab = _make_cab(per_region_locks=True)
    cab._full_last_session = "session_OLD"

    migrate_calls: list[tuple[str, int]] = []

    def fake_migrate(session_id, target_quarter, transaction=None):
        migrate_calls.append((session_id, target_quarter))

    monkeypatch.setattr(cab, "_migrate_kv", fake_migrate)

    with _patch_lock_grants_all(cab):
        with cab._dispatch(session_id="session_NEW_1") as (_backend, _idx, is_full):
            assert is_full
        with cab._dispatch(session_id="session_NEW_2") as (_backend, _idx, is_full):
            assert is_full

    time.sleep(0.1)
    assert [call[0] for call in migrate_calls] == ["session_OLD", "session_NEW_1"]


def test_dispatch_does_NOT_migrate_when_same_session_returns(monkeypatch) -> None:
    """If the same session_id reuses full, no migration should fire."""
    cab = _make_cab(per_region_locks=True)
    cab._full_last_session = "session_SAME"

    migrate_calls: list[tuple[str, int]] = []
    monkeypatch.setattr(cab, "_migrate_kv", lambda *a: migrate_calls.append(a))

    with _patch_lock_grants_all(cab):
        with cab._dispatch(session_id="session_SAME") as (_b, _i, is_full):
            assert is_full

    time.sleep(0.1)
    assert migrate_calls == []


def test_dispatch_does_NOT_migrate_when_old_already_in_quarter(monkeypatch) -> None:
    """If OLD session already has a quarter assignment, no migration needed."""
    cab = _make_cab(per_region_locks=True)
    cab._full_last_session = "session_OLD"
    cab._session_quarter["session_OLD"] = 2  # already migrated previously

    migrate_calls: list[tuple[str, int]] = []
    monkeypatch.setattr(cab, "_migrate_kv", lambda *a: migrate_calls.append(a))

    with _patch_lock_grants_all(cab):
        with cab._dispatch(session_id="session_NEW") as (_b, _i, _f):
            pass

    time.sleep(0.1)
    assert migrate_calls == []


def test_dispatch_does_NOT_migrate_when_migration_disabled(monkeypatch) -> None:
    """If _kv_migration_enabled is False (e.g. httpx missing), no migration."""
    cab = _make_cab(per_region_locks=True)
    cab._full_last_session = "session_OLD"
    cab._kv_migration_enabled = False

    migrate_calls: list[tuple[str, int]] = []
    monkeypatch.setattr(cab, "_migrate_kv", lambda *a: migrate_calls.append(a))

    with _patch_lock_grants_all(cab):
        with cab._dispatch(session_id="session_NEW") as (_b, _i, _f):
            pass

    time.sleep(0.1)
    assert migrate_calls == []


def test_dispatch_prefers_sticky_quarter_for_known_session(monkeypatch) -> None:
    """When session_id has a quarter affinity in _session_quarter, _dispatch
    should try THAT quarter first (warm KV continuity post-migration)."""
    cab = _make_cab(per_region_locks=True)
    # session S has been migrated to quarter 3 previously
    cab._session_quarter["session_S"] = 3

    attempted_instances: list[int] = []

    def _track_attempts(role, instance_idx, **kw):
        attempted_instances.append(instance_idx)
        return _fake_lock_ctx()

    with mock.patch("src.runtime.cpu_region_lock.cpu_region_lock_for_instance",
                    side_effect=_track_attempts):
        with cab._dispatch(session_id="session_S") as (_b, idx, is_full):
            # The first acquired wins; sticky should be tried first
            pass

    # First attempt should be the sticky quarter (NUMA_CONFIG idx = quarter_ca_idx + 1)
    # quarter 3 → topology idx 4
    assert attempted_instances[0] == 4
