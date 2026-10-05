"""Phase E — KV migration status reporting under per-region-locks."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

ca_mod = importlib.import_module("src.backends.concurrency_aware")


class _StubBackend:
    def __init__(self, url: str = "http://localhost:0"):
        self.config = type("C", (), {"base_url": url})()
        self.url = url


def _build(role: str = "frontdoor"):
    return ca_mod.ConcurrencyAwareBackend(
        full_backend=_StubBackend(),
        quarter_backends=[_StubBackend(), _StubBackend(), _StubBackend(), _StubBackend()],
        role=role,
    )


def test_migration_enabled_under_per_region_locks(monkeypatch) -> None:
    """2026-05-24: migration is now ported into the per-region-locks dispatch
    path, so the flag should be True under PER_REGION_LOCKS=1 (assuming httpx)."""
    monkeypatch.setenv("ORCHESTRATOR_PER_REGION_LOCKS", "1")
    cab = _build()
    assert cab._kv_migration_enabled is ca_mod._HTTPX_AVAILABLE
    status = cab.kv_migration_status()
    assert status["enabled"] is ca_mod._HTTPX_AVAILABLE
    assert status["per_region_locks"] is True
    assert status["dispatch_path"] == "per_region_locks"


def test_migration_enabled_under_legacy_select(monkeypatch) -> None:
    """Under PER_REGION_LOCKS=0, the legacy _select path migrates (status reports
    dispatch_path='legacy_select')."""
    monkeypatch.setenv("ORCHESTRATOR_PER_REGION_LOCKS", "0")
    cab = _build()
    assert cab._kv_migration_enabled is ca_mod._HTTPX_AVAILABLE
    status = cab.kv_migration_status()
    assert status["per_region_locks"] is False
    assert status["dispatch_path"] == "legacy_select"


def test_migration_status_keys_present(monkeypatch) -> None:
    monkeypatch.setenv("ORCHESTRATOR_PER_REGION_LOCKS", "1")
    cab = _build()
    s = cab.kv_migration_status()
    for key in ("enabled", "per_region_locks", "reason", "dispatch_path"):
        assert key in s


def test_migration_status_reports_httpx_unavailable_reason(monkeypatch) -> None:
    monkeypatch.setenv("ORCHESTRATOR_PER_REGION_LOCKS", "1")
    monkeypatch.setattr(ca_mod, "_HTTPX_AVAILABLE", False)
    cab = _build()

    assert cab.kv_migration_status() == {
        "enabled": False,
        "per_region_locks": True,
        "dispatch_path": "per_region_locks",
        "reason": "httpx unavailable",
    }


def test_chat_request_carries_migration_budget_ms() -> None:
    """The advisory request field should be parsable + default None."""
    sys.path.insert(0, str(ROOT))
    from src.api.models.requests import ChatRequest
    r = ChatRequest(prompt="x")
    assert r.migration_budget_ms is None
    r2 = ChatRequest(prompt="x", migration_budget_ms=200)
    assert r2.migration_budget_ms == 200
