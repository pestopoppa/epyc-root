from __future__ import annotations

from pathlib import Path

import yaml

from src.runtime import concurrency


def _write_stack_priors(path: Path, roles: dict) -> Path:
    path.write_text(yaml.safe_dump({"roles": roles}, sort_keys=True), encoding="utf-8")
    return path


def _role(
    *,
    status: str = "live_stack",
    tier: str = "warm",
    slots: int | None = 2,
) -> dict:
    serving = {"tier": tier}
    if slots is not None:
        serving["slots"] = slots
    return {"deployment_status": status, "serving": serving}


def test_live_worker_concurrency_reads_live_warm_workers_only(tmp_path: Path) -> None:
    priors = _write_stack_priors(
        tmp_path / "stack_priors.yaml",
        {
            "worker_batch": _role(tier="warm", slots=4),
            "worker_general": _role(tier="hot", slots=4),
            "worker_fast": _role(status="benchmark_or_candidate", tier="warm", slots=4),
            "toolrunner": _role(tier="warm", slots=4),
            "architect_general": _role(tier="warm", slots=4),
        },
    )

    assert concurrency._live_worker_concurrency(priors) == {"worker_batch": 4}


def test_live_worker_concurrency_defaults_missing_slots_to_one(tmp_path: Path) -> None:
    priors = _write_stack_priors(
        tmp_path / "stack_priors.yaml",
        {"worker_batch": _role(tier="warm", slots=None)},
    )

    assert concurrency._live_worker_concurrency(priors) == {"worker_batch": 1}


def test_live_worker_concurrency_fails_closed_when_missing(tmp_path: Path) -> None:
    assert concurrency._live_worker_concurrency(tmp_path / "missing.yaml") == {}


def test_public_concurrency_api_uses_derived_policy(monkeypatch) -> None:
    monkeypatch.setattr(concurrency, "_ROLE_MAX_CONCURRENCY", {"worker_batch": 3})
    monkeypatch.setattr(concurrency, "_SMALL_WORKER_ROLES", frozenset({"worker_batch"}))

    assert concurrency.is_small_worker_role("worker_batch") is True
    assert concurrency.is_small_worker_role("worker_general") is False
    assert concurrency.get_role_max_concurrency("worker_batch") == 3
    assert concurrency.get_role_max_concurrency("worker_general") == 1
    assert concurrency.small_worker_roles() == frozenset({"worker_batch"})


class TestFleetRoleConcurrency:
    """C10-F1: flag-gated fleet-derived role concurrency (default OFF)."""

    def test_flag_off_keeps_legacy_default(self, monkeypatch):
        monkeypatch.delenv("ORCHESTRATOR_FLEET_ROLE_CONCURRENCY", raising=False)
        from src.runtime import concurrency as rc

        called = []
        monkeypatch.setattr(
            rc, "_fleet_disjoint_capacity", lambda role: called.append(role) or 4
        )
        assert rc.get_role_max_concurrency("worker_math") == 1
        assert called == []  # fleet path never consulted with the flag off

    def test_flag_on_uses_fleet_quarter_capacity(self, monkeypatch):
        monkeypatch.setenv("ORCHESTRATOR_FLEET_ROLE_CONCURRENCY", "1")
        from src.runtime import concurrency as rc

        monkeypatch.setattr(rc, "_fleet_disjoint_capacity", lambda role: 4)
        assert rc.get_role_max_concurrency("worker_math") == 4

    def test_flag_on_falls_back_when_fleet_unavailable(self, monkeypatch):
        monkeypatch.setenv("ORCHESTRATOR_FLEET_ROLE_CONCURRENCY", "1")
        from src.runtime import concurrency as rc

        monkeypatch.setattr(rc, "_fleet_disjoint_capacity", lambda role: None)
        assert rc.get_role_max_concurrency("made_up_role") == 1

    def test_fleet_capacity_from_synthetic_state(self, monkeypatch):
        from src.runtime import concurrency as rc

        class _Fleet:
            quarter_endpoints = (object(), object(), object(), object())

        class _Binding:
            fleet_id = "worker"

        import src.fleet as fleet_mod

        monkeypatch.setattr(
            fleet_mod, "get_fleets_and_bindings", lambda: ({"worker": _Fleet()}, {})
        )
        monkeypatch.setattr(fleet_mod, "resolve_binding", lambda role, b: _Binding())
        assert rc._fleet_disjoint_capacity("worker_math") == 4

    def test_single_endpoint_fleet_caps_at_one(self, monkeypatch):
        from src.runtime import concurrency as rc

        class _Fleet:
            quarter_endpoints = ()

        class _Binding:
            fleet_id = "architect"

        import src.fleet as fleet_mod

        monkeypatch.setattr(
            fleet_mod, "get_fleets_and_bindings", lambda: ({"architect": _Fleet()}, {})
        )
        monkeypatch.setattr(fleet_mod, "resolve_binding", lambda role, b: _Binding())
        assert rc._fleet_disjoint_capacity("architect_general") == 1
