"""J2/J3: placement-SM forward + reverse migration triggers (operator audit #5, 2026-05-27).

Verifies the ConcurrencyAwareBackend migration STATE MACHINE in-process (no multi-worker confound):
  J2 forward — a NEW session arriving while the full instance was last held by another session
               migrates the prior session full→quarter.
  J3 reverse — a warm quartered session released after the full instance is idle ≥ cooldown
               migrates back full.
The KV-HTTP slot save/restore is stubbed (separately unit-tested in test_*_migration.py); these
assert the SM TRIGGERS fire under the right conditions.

WHY this is in-process rather than live-via-API: the production API runs `--workers 6`, so the CAB
state (session→quarter affinity, `_session_last_seen`, migration counters) is per-worker while requests
round-robin across workers — so a live `/chat` probe can neither reliably trigger nor observe migrations
(this is why J6 and the 2026-05-27 live probe both saw 0 migrations). This drive verifies the SM logic
directly; live-under-traffic verification would require a single-worker API.
"""
from __future__ import annotations

import time
from types import SimpleNamespace

import pytest


def _stub(url: str):
    # _get_base_url reads backend._backend.config.base_url (or backend.config.base_url).
    return SimpleNamespace(config=SimpleNamespace(base_url=url))


@pytest.fixture
def cab(monkeypatch):
    monkeypatch.setenv("ORCHESTRATOR_PLACEMENT_STATE_MACHINE", "1")
    monkeypatch.setenv("ORCHESTRATOR_REVERSE_MIGRATION", "1")
    monkeypatch.setenv("ORCHESTRATOR_PER_REGION_LOCKS", "0")
    monkeypatch.setenv("ORCHESTRATOR_REVERSE_MIGRATION_COOLDOWN_MS", "10")  # fast, deterministic
    import src.backends.concurrency_aware as CA
    # Stub the KV-HTTP slot ops to succeed so the SM state transitions complete; the slot HTTP
    # itself is covered by the KV-migration unit tests, not here.
    monkeypatch.setattr(CA, "_slot_save", lambda *a, **k: True)
    monkeypatch.setattr(CA, "_slot_restore", lambda *a, **k: True)
    monkeypatch.setattr(CA, "_slot_erase", lambda *a, **k: True)
    return CA.ConcurrencyAwareBackend(
        _stub("http://localhost:8070"),
        [_stub(f"http://localhost:{p}") for p in (8080, 8180, 8280, 8380)],
        role="frontdoor", full_port=8070,
    )


def test_j2_forward_migration_on_session_displacement(cab):
    a = cab._select("sess-A")
    cab._session_last_seen["sess-A"] = time.monotonic()
    cab._release(a[1], a[2])
    assert cab._migrations == 0
    cab._select("sess-B")          # NEW session → displaces A from full (forward migration)
    time.sleep(0.3)                # stubbed _migrate_kv finalizes A onto its quarter
    assert cab._migrations >= 1
    assert cab._session_quarter.get("sess-A") is not None, "A should be migrated to a quarter"


def test_j3_reverse_migration_on_quarter_release(cab):
    # Set up the forward migration: A on full, then B displaces A → A on a quarter.
    a = cab._select("sess-A")
    cab._session_last_seen["sess-A"] = time.monotonic()
    cab._release(a[1], a[2])
    b = cab._select("sess-B")
    time.sleep(0.3)
    cab._release(b[1], b[2])        # release full → full goes idle
    assert cab._session_quarter.get("sess-A") is not None
    # Reverse: full idle ≥ cooldown, re-request A (records last_seen), release its quarter.
    time.sleep(0.1)                 # full idle ≥ 10ms cooldown
    a2 = cab._select("sess-A")
    cab._session_last_seen["sess-A"] = time.monotonic()
    assert a2[2] is False, "A should route to its quarter via session affinity, not full"
    cab._release(a2[1], a2[2])      # release quarter → reverse-migration trigger
    time.sleep(0.4)
    assert sum(cab._reverse_migration_counts.values()) >= 1, "reverse migration should have fired"
