"""Tests for the dashboard helper modules extracted in the 2026-05-21 refactor.

Covers dashboard_topology, dashboard_tap, dashboard_tasks, dashboard_snapshot.
Route handlers themselves are unchanged (smoke-tested only via module import).
"""

from __future__ import annotations

import asyncio
import json
import os
import sqlite3
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.api.routes import (
    dashboard,
    dashboard_snapshot,
    dashboard_tap,
    dashboard_tasks,
    dashboard_topology,
)
from scripts.autopilot import optimization_brief as optimization_brief_module

ROOT = Path(__file__).resolve().parents[2]

# Lineup-independence (2026-09-26). Several port-hint / listener tests used to
# restate the gemma `worker` server's ports (8072 full, 8082/8182 quarters) as
# worker_general's. The operator-signed 2026-09-22 lineup cutover (orchestrator
# 860b0b2d) made worker_general an ALIAS of frontdoor's :8070 fleet and deleted
# its NUMA_CONFIG entry, so those ports resolve to nothing. The fleet is now
# DERIVED: worker_general's host from orchestration/model_registry.yaml
# server_mode, its full/sibling ports from NUMA_CONFIG.


def _registry_server_mode() -> dict:
    import yaml

    return yaml.safe_load(
        (ROOT / "orchestration" / "model_registry.yaml").read_text(encoding="utf-8")
    )["server_mode"]


def _host_fleet_of(role: str) -> str:
    """The server_mode row that physically hosts ``role`` (shared_with/alias_of)."""
    for host, row in _registry_server_mode().items():
        if row.get("alias_of"):
            continue
        if host == role or role in (row.get("shared_with") or []):
            return host
    raise AssertionError(f"registry declares no host fleet for {role!r}")


def _full_and_sibling_ports(role: str) -> tuple[int, list[int]]:
    """(idx-0 full port, sibling ports in instance order) from NUMA_CONFIG."""
    from scripts.server.stack_numa import NUMA_CONFIG

    instances = NUMA_CONFIG[role]["instances"]
    return int(instances[0][1]), [int(inst[1]) for inst in instances[1:]]


_WG_HOST = _host_fleet_of("worker_general")


@pytest.fixture(autouse=True)
def _neutralize_realized_numa_probe(monkeypatch):
    """The realized-fleet-first NUMA resolver (audit C1) probes localhost sockets.

    Unit tests must be hermetic and network-free, so default the realized probe to
    "no realized signal" — the lower-precedence layers (manifest/env) then drive
    the mode exactly as they did before this layer existed, which is what the
    pre-existing tests assert. Tests that exercise realized-first behavior override
    ``_probe_realized_numa_mode`` / ``_cached_realized_numa_mode`` themselves.
    """
    dashboard_topology._REALIZED_NUMA_CACHE.update({"ts": 0.0, "value": None, "probed": False})
    monkeypatch.setattr(dashboard_topology, "_probe_realized_numa_mode", lambda: None)
    yield
    dashboard_topology._REALIZED_NUMA_CACHE.update({"ts": 0.0, "value": None, "probed": False})


@pytest.mark.asyncio
async def test_optimization_brief_is_threaded_cached_and_fails_open(monkeypatch) -> None:
    calls = 0

    def build() -> dict[str, object]:
        nonlocal calls
        calls += 1
        return {"read_only": True, "checkpoint": {"trial_counter": 7}}

    monkeypatch.setattr(optimization_brief_module, "build_optimization_brief", build)
    monkeypatch.setitem(dashboard._OPTIMIZATION_BRIEF_CACHE, "payload", None)
    monkeypatch.setitem(dashboard._OPTIMIZATION_BRIEF_CACHE, "created_monotonic", 0.0)
    monkeypatch.setitem(dashboard._OPTIMIZATION_BRIEF_CACHE, "generated_at", None)

    first = await dashboard._optimization_brief_payload()
    second = await dashboard._optimization_brief_payload()

    assert calls == 1
    assert first["checkpoint"] == {"trial_counter": 7}
    assert first["synthesis"]["stale"] is False
    assert second["synthesis"]["age_s"] >= 0

    def fail() -> dict[str, object]:
        raise RuntimeError("cold rebuild failed")

    monkeypatch.setattr(optimization_brief_module, "build_optimization_brief", fail)
    dashboard._OPTIMIZATION_BRIEF_CACHE["created_monotonic"] = 0.0
    stale = await dashboard._optimization_brief_payload()

    assert stale["checkpoint"] == {"trial_counter": 7}
    assert stale["synthesis"]["stale"] is True
    assert stale["synthesis"]["warning"] == "cold rebuild failed"


# ----- dashboard_topology -----


def test_role_color_known_role() -> None:
    assert dashboard_topology._role_color("frontdoor") == "#3b82f6"


def test_role_color_strips_quarter_suffix() -> None:
    assert dashboard_topology._role_color("frontdoor.q0") == dashboard_topology._role_color("frontdoor")


def test_role_color_strips_numeric_sibling_suffix() -> None:
    # _ROLE_COLORS has "embedder"; "embedder_3" should fall back to embedder
    assert dashboard_topology._role_color("embedder_3") == dashboard_topology._role_color("embedder")


def test_role_color_unknown_falls_back_to_gray() -> None:
    assert dashboard_topology._role_color("unknown_role") == "#64748b"


def test_port_hints_follow_current_both_mode_priors() -> None:
    # Public compatibility hints are built from generated stack_priors, which
    # describe the BOTH-mode lineup: the big (idx-0) instance AND its sibling
    # replicas are all loaded, so both appear in the hints. Ports are derived
    # from NUMA_CONFIG for frontdoor and for worker_general's registry host
    # (the same fleet since the 2026-09-22 cutover).
    for role in dict.fromkeys(("frontdoor", _WG_HOST)):
        full_port, siblings = _full_and_sibling_ports(role)
        assert len(siblings) >= 2, (role, siblings)  # non-vacuous sibling labelling
        assert dashboard_topology._PORT_HINTS[full_port] == role
        for k, port in enumerate(siblings):
            assert dashboard_topology._PORT_HINTS[port] == f"{role}.q{k}"
    # An alias bound onto a host fleet has no server of its own, so it must never
    # surface as a port hint (the retired gemma worker ports were exactly that).
    aliases = set(_registry_server_mode()[_WG_HOST].get("shared_with") or [])
    assert "worker_general" in aliases
    assert not {
        hint.split(".")[0] for hint in dashboard_topology._PORT_HINTS.values()
    } & aliases


def test_active_stack_numa_mode_defaults_to_both(monkeypatch) -> None:
    # Nothing exports ORCHESTRATOR_STACK_NUMA_MODE and the stack runs every
    # instance (full + 4 quarters per multi-instance role), so the dashboard
    # defaults to "both" to reflect the running instances rather than hiding them.
    monkeypatch.delenv("ORCHESTRATOR_STACK_NUMA_MODE", raising=False)
    monkeypatch.setattr(dashboard_topology, "read_runtime_stack_numa_mode", lambda: None)
    assert dashboard_topology.active_stack_numa_mode() == "both"

    monkeypatch.setenv("ORCHESTRATOR_STACK_NUMA_MODE", "quarter")
    assert dashboard_topology.active_stack_numa_mode() == "quarter"

    # Unknown values fall back to the "both" default.
    monkeypatch.setenv("ORCHESTRATOR_STACK_NUMA_MODE", "stale-quarter")
    assert dashboard_topology.active_stack_numa_mode() == "both"


def test_active_stack_numa_mode_uses_runtime_facts_manifest(monkeypatch) -> None:
    monkeypatch.delenv("ORCHESTRATOR_STACK_NUMA_MODE", raising=False)
    monkeypatch.setattr(dashboard_topology, "read_runtime_stack_numa_mode", lambda: "quarter")
    # WP-14: honoring the manifest mode now also requires a non-empty, consistent
    # selected-server lineup (the URL reader's fail-closed contract).
    monkeypatch.setattr(
        dashboard_topology,
        "read_runtime_stack_selected_servers",
        lambda: [{"port": 8082, "roles": ["worker_general"]}],
    )

    assert dashboard_topology.active_stack_numa_mode() == "quarter"


_PHANTOM_RUNTIME_FACTS = {
    "schema": "epyc.orchestrator.runtime_facts",
    "schema_version": 1,
    "runtime_stack": {
        # Real current phantom shape: mode null, empty selected_ports, but a
        # left-behind full-era server lineup.
        "stack_numa_mode": None,
        "selected_servers": [
            {"port": 8070, "roles": ["frontdoor", "coder_escalation"], "numa_instance": 0},
            {"port": 8072, "roles": ["worker_general", "worker_math"], "numa_instance": 0},
        ],
        "selected_ports": [],
    },
}

_WELLFORMED_QUARTER_RUNTIME_FACTS = {
    "schema": "epyc.orchestrator.runtime_facts",
    "schema_version": 1,
    "runtime_stack": {
        "stack_numa_mode": "quarter",
        "selected_servers": [
            {"port": 8082, "roles": ["worker_general", "worker_math"], "numa_instance": 1},
            {"port": 8182, "roles": ["worker_general"], "numa_instance": 2},
        ],
        "selected_ports": [8082, 8182],
    },
}


def _install_dashboard_runtime_facts(monkeypatch, tmp_path: Path, payload: dict) -> None:
    from scripts.server import stack_paths
    from scripts.server.runtime_facts_manifest import runtime_facts_manifest_path

    monkeypatch.setitem(stack_paths._PATHS, "tmp_dir", tmp_path)
    runtime_facts_manifest_path().write_text(json.dumps(payload), encoding="utf-8")


def test_active_stack_numa_mode_rejects_phantom_runtime_facts_manifest(
    monkeypatch, tmp_path, caplog
) -> None:
    """WP-14: a phantom full-era manifest (mode null, empty selected_ports) is
    rejected fail-closed; the dashboard falls back to its historical ``both``
    default with one loud log line instead of surfacing a phantom mode."""
    import logging

    monkeypatch.delenv("ORCHESTRATOR_STACK_NUMA_MODE", raising=False)
    _install_dashboard_runtime_facts(monkeypatch, tmp_path, _PHANTOM_RUNTIME_FACTS)

    with caplog.at_level(logging.WARNING, logger="src.api.routes.dashboard_topology"):
        assert dashboard_topology.active_stack_numa_mode() == "both"

    rejections = [
        rec for rec in caplog.records if "runtime-facts manifest rejected" in rec.getMessage()
    ]
    assert len(rejections) == 1


def test_active_stack_numa_mode_consumes_wellformed_quarter_runtime_facts(
    monkeypatch, tmp_path, caplog
) -> None:
    """WP-14: a well-formed quarter manifest (concrete mode + consistent lineup)
    is consumed and no fail-closed warning is emitted."""
    import logging

    monkeypatch.delenv("ORCHESTRATOR_STACK_NUMA_MODE", raising=False)
    _install_dashboard_runtime_facts(monkeypatch, tmp_path, _WELLFORMED_QUARTER_RUNTIME_FACTS)

    with caplog.at_level(logging.WARNING, logger="src.api.routes.dashboard_topology"):
        assert dashboard_topology.active_stack_numa_mode() == "quarter"

    assert not [
        rec for rec in caplog.records if "runtime-facts manifest rejected" in rec.getMessage()
    ]


def test_active_stack_numa_mode_env_is_last_resort_when_nothing_higher_resolves(monkeypatch) -> None:
    """C1: env is demoted below realized + manifest. It is honored ONLY when the
    realized probe yields nothing AND the manifest is absent/rejected."""
    monkeypatch.setenv("ORCHESTRATOR_STACK_NUMA_MODE", "full")
    # realized neutralized by the autouse fixture; manifest absent/rejected.
    monkeypatch.setattr(dashboard_topology, "_fail_closed_runtime_stack_numa_mode", lambda: None)

    resolution = dashboard_topology.active_stack_numa_mode_resolution()
    assert resolution["mode"] == "full"
    assert resolution["source"] == "env"
    assert resolution["disagreements"] == []
    assert dashboard_topology.active_stack_numa_mode() == "full"


def test_active_stack_numa_mode_prefers_realized_fleet_over_contradicting_env(monkeypatch) -> None:
    """C1 core: a worker that inherited env=full must render the realized quarter
    fleet, with the env contradiction surfaced as provenance (not silently trusted)."""
    monkeypatch.setenv("ORCHESTRATOR_STACK_NUMA_MODE", "full")
    monkeypatch.setattr(dashboard_topology, "_cached_realized_numa_mode", lambda: "quarter")
    monkeypatch.setattr(dashboard_topology, "_fail_closed_runtime_stack_numa_mode", lambda: None)

    resolution = dashboard_topology.active_stack_numa_mode_resolution()
    assert resolution["mode"] == "quarter"
    assert resolution["source"] == "realized_fleet"
    assert resolution["realized"] == "quarter"
    assert resolution["env"] == "full"
    assert resolution["disagreements"] == ["env disagrees: full"]


def test_active_stack_numa_mode_manifest_beats_env_when_no_realized(monkeypatch) -> None:
    """Precedence rung 2: with no realized signal, the hardened manifest outranks a
    contradicting env, and the env disagreement is annotated."""
    monkeypatch.setenv("ORCHESTRATOR_STACK_NUMA_MODE", "full")
    monkeypatch.setattr(dashboard_topology, "_cached_realized_numa_mode", lambda: None)
    monkeypatch.setattr(dashboard_topology, "_fail_closed_runtime_stack_numa_mode", lambda: "quarter")

    resolution = dashboard_topology.active_stack_numa_mode_resolution()
    assert resolution["mode"] == "quarter"
    assert resolution["source"] == "runtime_manifest"
    assert resolution["disagreements"] == ["env disagrees: full"]


def test_active_stack_numa_mode_rejected_manifest_falls_through_to_env(monkeypatch, tmp_path) -> None:
    """Manifest-rejected fallback ordering: a phantom manifest (mode null / empty
    lineup) is rejected fail-closed and, with no realized signal, the env hint is
    used — proving env is reached only AFTER the manifest is rejected."""
    monkeypatch.setenv("ORCHESTRATOR_STACK_NUMA_MODE", "quarter")
    _install_dashboard_runtime_facts(monkeypatch, tmp_path, _PHANTOM_RUNTIME_FACTS)

    resolution = dashboard_topology.active_stack_numa_mode_resolution()
    assert resolution["manifest"] is None  # rejected
    assert resolution["mode"] == "quarter"
    assert resolution["source"] == "env"


def test_cached_realized_numa_mode_ttl_collapses_probe_storm(monkeypatch) -> None:
    """TTL cache: repeated resolutions within the TTL window probe the fleet once;
    the probe re-runs only after the entry expires."""
    dashboard_topology._REALIZED_NUMA_CACHE.update({"ts": 0.0, "value": None, "probed": False})
    calls = {"n": 0}

    def _counting_probe() -> str:
        calls["n"] += 1
        return "quarter"

    monkeypatch.setattr(dashboard_topology, "_probe_realized_numa_mode", _counting_probe)

    assert dashboard_topology._cached_realized_numa_mode() == "quarter"
    assert dashboard_topology._cached_realized_numa_mode() == "quarter"
    assert calls["n"] == 1  # second call served from cache

    # Expire the cache entry and confirm the probe re-runs exactly once more.
    dashboard_topology._REALIZED_NUMA_CACHE["ts"] = (
        time.monotonic() - dashboard_topology._REALIZED_NUMA_TTL_S - 1.0
    )
    assert dashboard_topology._cached_realized_numa_mode() == "quarter"
    assert calls["n"] == 2


def test_expected_stack_services_are_numa_mode_filtered() -> None:
    # Test the FILTER CONTRACT directly against the manifest (the
    # expected_stack_services() wrapper falls open to the unfiltered list when
    # the scripts.server import chain is partially initialized inside pytest —
    # a known circular-import flake, filed 2026-07-23; the contract itself is
    # deterministic).
    #
    # The full/non-full port split is DERIVED from NUMA_CONFIG — the same table
    # `_filter_by_numa_mode` itself branches on — rather than restated as port
    # literals. The deployable shape moves (982adb0c retired the 4-quarter shape
    # on 2026-07-30 for 1 full + 2 halves and freed 8280/8380/8282/8382 with an
    # explicit "must not be revived"); what must NOT move is the contract: full
    # mode keeps exactly the full instances, quarter mode keeps exactly the
    # non-full ones, and the two modes never overlap.
    from scripts.server.stack_manifest import (
        HOT_SERVERS,
        WARM_SERVERS,
        NUMA_CONFIG,
        _filter_by_numa_mode,
    )

    def _port(instance) -> int:
        return instance["port"] if isinstance(instance, dict) else instance[1]

    expected_full: set[int] = set()
    expected_non_full: set[int] = set()
    for cfg in NUMA_CONFIG.values():
        instances = cfg.get("instances") or []
        # Same guard as the filter: single-shape roles pass through untouched.
        if "full_instance_idx" not in cfg or len(instances) <= 1:
            continue
        full_idx = cfg["full_instance_idx"]
        for idx, instance in enumerate(instances):
            target = expected_full if idx == full_idx else expected_non_full
            target.add(_port(instance))

    # Teeth: if the manifest ever loses one side of the split entirely, the
    # disjointness assertions below would pass vacuously.
    assert expected_full, "no role declares a full instance alongside siblings"
    assert expected_non_full, "no role declares a non-full sibling instance"

    full_ports = {
        s["port"]
        for s in _filter_by_numa_mode(HOT_SERVERS + WARM_SERVERS, "full")
        if isinstance(s, dict) and "port" in s
    }
    assert expected_full.issubset(full_ports)
    assert full_ports.isdisjoint(expected_non_full)

    quarter_ports = {
        s["port"]
        for s in _filter_by_numa_mode(HOT_SERVERS + WARM_SERVERS, "quarter")
        if isinstance(s, dict) and "port" in s
    }
    assert expected_non_full.issubset(quarter_ports)
    assert quarter_ports.isdisjoint(expected_full)

    both_ports = {
        s["port"]
        for s in _filter_by_numa_mode(HOT_SERVERS + WARM_SERVERS, "both")
        if isinstance(s, dict) and "port" in s
    }
    # The restored 2026-07-23 lineup: both mode carries big + quarters.
    assert (expected_full | expected_non_full).issubset(both_ports)


def test_expected_stack_services_uses_runtime_facts_manifest(monkeypatch) -> None:
    monkeypatch.delenv("ORCHESTRATOR_STACK_NUMA_MODE", raising=False)
    monkeypatch.setattr(
        dashboard_topology,
        "read_runtime_stack_selected_servers",
        lambda: [{
            "port": 18070,
            "roles": ["eval_batch_frontdoor"],
            "embedding": False,
            "vision": False,
            "worker_pool": False,
            "numa_instance": 0,
        }],
    )

    services = dashboard_topology.expected_stack_services()

    assert services == [{
        "name": "eval_batch_frontdoor",
        "role": "eval_batch_frontdoor",
        "port": 18070,
        "roles": ["eval_batch_frontdoor"],
        "embedding": False,
        "vision": False,
        "worker_pool": False,
        "numa_instance": 0,
    }]


def test_expected_stack_services_env_override_skips_runtime_facts_manifest(monkeypatch) -> None:
    monkeypatch.setenv("ORCHESTRATOR_STACK_NUMA_MODE", "full")
    # Neutralize the realized-first mode resolver's manifest read (audit C1) so the
    # env mode drives filtering; the fail_reader below then proves the *separate*
    # runtime-selected-servers branch of expected_stack_services is not taken.
    monkeypatch.setattr(dashboard_topology, "_fail_closed_runtime_stack_numa_mode", lambda: None)

    def fail_reader():
        raise AssertionError("env override should use static manifest")

    monkeypatch.setattr(
        dashboard_topology,
        "read_runtime_stack_selected_servers",
        fail_reader,
    )

    ports = {service["port"] for service in dashboard_topology.expected_stack_services()}

    assert 8070 in ports
    assert 8080 not in ports


def test_port_hint_labels_known_numa_ports_independent_of_expected_mode(monkeypatch) -> None:
    monkeypatch.setenv("ORCHESTRATOR_STACK_NUMA_MODE", "full")
    assert dashboard_topology._port_hint(8080) == "frontdoor.q0"

    monkeypatch.setenv("ORCHESTRATOR_STACK_NUMA_MODE", "quarter")
    assert dashboard_topology._port_hint(8080) == "frontdoor.q0"
    # Second sibling of worker_general's host fleet (was the gemma 8182 quarter).
    _full, host_siblings = _full_and_sibling_ports(_WG_HOST)
    assert len(host_siblings) >= 2
    assert dashboard_topology._port_hint(host_siblings[1]) == f"{_WG_HOST}.q1"


def test_port_hint_uses_runtime_selected_servers_when_env_unset(monkeypatch) -> None:
    monkeypatch.delenv("ORCHESTRATOR_STACK_NUMA_MODE", raising=False)
    monkeypatch.setattr(
        dashboard_topology,
        "read_runtime_stack_selected_servers",
        lambda: [{
            "port": 18070,
            "roles": ["eval_batch_frontdoor"],
            "numa_instance": 0,
        }],
    )

    assert dashboard_topology._port_hint(18070) == "eval_batch_frontdoor"
    assert dashboard_topology._port_hint(8080) == "frontdoor.q0"


def test_expected_stack_services_include_embedder_fleet(monkeypatch) -> None:
    monkeypatch.setenv("ORCHESTRATOR_STACK_NUMA_MODE", "both")
    services = dashboard_topology.expected_stack_services()
    embedders = [s for s in services if s.get("embedding")]

    assert [s["port"] for s in embedders] == [
        8090, 8091, 8092, 8093, 8094, 8095, 8096, 8097, 8098,
    ]
    assert [s["role"] for s in embedders] == [
        "embedder",
        "embedder_1",
        "embedder_2",
        "embedder_3",
        "embedder_4",
        "embedder_5",
        "embedder_granite_97m_r2",
        "embedder_multilingual_e5_base",
        "embedder_bge_m3",
    ]


def test_topology_emits_expected_unloaded_stack_servers(monkeypatch) -> None:
    monkeypatch.setattr(dashboard, "_discover_llama_ports", lambda: {})
    monkeypatch.setattr(dashboard, "_discover_llama_models", lambda: {})
    monkeypatch.setattr(dashboard, "_load_state_services", lambda: [])

    response = asyncio.run(dashboard.topology())
    data = json.loads(response.body)
    by_port = {node["port"]: node for node in data["nodes"]}

    embedder = by_port[8090]
    assert embedder["role"] == "embedder"
    assert embedder["kind"] == "expected-stack-server"
    assert embedder["expected"] is True
    assert embedder["running"] is False


def _split_full_and_non_full_ports() -> tuple[dict[int, str], tuple[int, ...]]:
    """Derive (non-full ports -> hint, full ports) from the LIVE NUMA_CONFIG.

    Hard-coding these used to name 8280/8380/8282/8382, which 982adb0c
    ("topology: retire quarters, deploy 1 full + 2 halves", 2026-07-30) FREED
    with an explicit "must not be revived". A port that appears on no launch
    surface is correctly rendered rogue, so a fixture that still lists it is
    describing a fleet that does not exist — and the fix must be to describe the
    real one, never to teach the dashboard to expect a retired port.
    """
    from scripts.server.stack_manifest import NUMA_CONFIG

    non_full: dict[int, str] = {}
    full: list[int] = []
    for cfg in NUMA_CONFIG.values():
        instances = cfg.get("instances") or []
        if "full_instance_idx" not in cfg or len(instances) <= 1:
            continue
        full_idx = cfg["full_instance_idx"]
        for idx, instance in enumerate(instances):
            port = instance["port"] if isinstance(instance, dict) else instance[1]
            if idx == full_idx:
                full.append(port)
            else:
                non_full[port] = dashboard_topology._port_hint(port)
    return non_full, tuple(sorted(full))


_LIVE_QUARTER_PORTS, _DEAD_FULL_PORTS = _split_full_and_non_full_ports()


def test_topology_inversion_regression_live_quarters_not_rogue_under_env_full(monkeypatch) -> None:
    """C1/M2 capstone regression (the proven live inversion):

    Realized fleet = quarters-only, but the serving worker inherited env=full.
    Before the fix this rendered the 12 live quarters ``expected=False`` (rogue)
    and the 3 dead full ports as ``expected-stack-server`` down rows — a fully
    inverted fleet-health picture. Realized-first resolution must instead render
    the quarters as ``expected=True`` and never surface the dead fulls as expected,
    while annotating the env contradiction as provenance.
    """
    monkeypatch.setenv("ORCHESTRATOR_STACK_NUMA_MODE", "full")
    monkeypatch.setattr(dashboard_topology, "_cached_realized_numa_mode", lambda: "quarter")
    monkeypatch.setattr(dashboard_topology, "_fail_closed_runtime_stack_numa_mode", lambda: None)
    monkeypatch.setattr(dashboard, "_discover_llama_ports", lambda: dict(_LIVE_QUARTER_PORTS))
    monkeypatch.setattr(dashboard, "_discover_llama_models", lambda: {})
    monkeypatch.setattr(dashboard, "_load_state_services", lambda: [])

    # Both halves of the fixture must be non-empty or the loops below pass
    # vacuously and the inversion pin has no teeth.
    assert _LIVE_QUARTER_PORTS and _DEAD_FULL_PORTS
    assert set(_LIVE_QUARTER_PORTS).isdisjoint(_DEAD_FULL_PORTS)

    response = asyncio.run(dashboard.topology())
    data = json.loads(response.body)
    by_port = {node["port"]: node for node in data["nodes"]}

    assert data["stack_numa_mode"] == "quarter"
    prov = data["stack_numa_mode_provenance"]
    assert prov["source"] == "realized_fleet"
    assert prov["disagreements"] == ["env disagrees: full"]

    # Every live quarter reads as expected (NOT rogue) and running.
    for port in _LIVE_QUARTER_PORTS:
        node = by_port[port]
        assert node["running"] is True, f"quarter {port} should be running"
        assert node["expected"] is True, f"quarter {port} inverted to rogue (expected=False)"

    # The dead full ports are absent-by-policy in quarter mode: no expected-down rows.
    for port in _DEAD_FULL_PORTS:
        assert port not in by_port, f"dead full {port} must not surface as expected-stack-server"


def test_topology_parity_smoke_for_expected_listener_ports(monkeypatch) -> None:
    from scripts.server import stack_commands

    mode = "both"
    expected_services = dashboard_topology.expected_stack_services(mode)
    expected_by_port = {
        int(s["port"]): s
        for s in expected_services
        if isinstance(s.get("port"), int)
    }
    assert expected_by_port

    def port_for_base_role(base: str) -> int:
        for port, service in sorted(expected_by_port.items()):
            if dashboard_topology.base_role(str(service.get("role") or "")) == base:
                return port
        raise AssertionError(f"expected stack service missing for base role {base}")

    # A second, physically distinct LLM fleet (was worker_general, now an alias
    # of frontdoor's fleet): the first non-alias registry server_mode row other
    # than frontdoor that the expected stack actually serves.
    expected_bases = {
        dashboard_topology.base_role(str(s.get("role") or "")) for s in expected_by_port.values()
    }
    second_fleet = next(
        host
        for host, row in _registry_server_mode().items()
        if not row.get("alias_of") and host != "frontdoor" and host in expected_bases
    )
    listener_ports = {
        port_for_base_role("frontdoor"),
        port_for_base_role(second_fleet),
        port_for_base_role("embedder"),
    }
    assert len(listener_ports) == 3, listener_ports
    scan_inputs: list[list[int]] = []

    def fake_scan_known_ports(ports):
        scanned = sorted(int(port) for port in ports)
        scan_inputs.append(scanned)
        return {
            port: [100_000 + port]
            for port in sorted(listener_ports)
            if port in scanned
        }

    monkeypatch.setattr(
        stack_commands._stack_processes,
        "scan_known_ports",
        fake_scan_known_ports,
    )
    discovered_listeners = stack_commands._scan_known_ports()

    assert scan_inputs
    assert set(expected_by_port).issubset(set(scan_inputs[0]))
    assert set(discovered_listeners) == listener_ports

    monkeypatch.setattr(
        dashboard,
        "_discover_llama_ports",
        lambda: {
            port: str(expected_by_port[port]["role"])
            for port in sorted(discovered_listeners)
        },
    )
    monkeypatch.setattr(dashboard, "_discover_llama_models", lambda: {})
    monkeypatch.setattr(dashboard, "_load_state_services", lambda: [])

    topology_by_port = {
        node["port"]: node
        for node in dashboard._build_topology_nodes(mode)
        if isinstance(node.get("port"), int)
    }

    assert set(expected_by_port).issubset(set(topology_by_port))
    for port, service in expected_by_port.items():
        node = topology_by_port[port]
        assert node["expected"] is True
        assert node["role"] == service["role"]
        assert node["manifest_roles"] == service["roles"]
        if port in listener_ports:
            assert node["running"] is True
            assert node["kind"] == "llama-server"
        else:
            assert node["running"] is False
            assert node["kind"] == "expected-stack-server"


def test_topology_activity_initializes_expected_embedder_bucket(monkeypatch, tmp_path) -> None:
    # Hermetic: with no explicit mode, expected_stack_services() prefers the LIVE
    # host's runtime facts (which list only the currently-selected servers) over
    # the stack manifest. The claim here is about bucket initialisation from the
    # manifest's expected embedder ports, so pin the manifest path and mode.
    monkeypatch.delenv("ORCHESTRATOR_STACK_NUMA_MODE", raising=False)
    monkeypatch.setattr(dashboard_topology, "read_runtime_stack_selected_servers", lambda: None)
    monkeypatch.setattr(dashboard_topology, "active_stack_numa_mode", lambda: "full")
    monkeypatch.setattr(dashboard, "_read_tail", lambda *a, **kw: "")
    monkeypatch.setattr(dashboard, "_read_tap_events_tail", lambda *a, **kw: "")
    monkeypatch.setattr(dashboard, "_parse_inference_sections", lambda *a, **kw: [])
    monkeypatch.setattr(dashboard, "_todays_progress_log", lambda: tmp_path / "missing.jsonl")
    monkeypatch.setattr(
        dashboard,
        "_discover_llama_ports",
        lambda: {
            8090: "embedder",
            8091: "embedder_1",
            8092: "embedder_2",
            8093: "embedder_3",
            8094: "embedder_4",
            8095: "embedder_5",
        },
    )

    response = asyncio.run(dashboard.topology_activity())
    data = json.loads(response.body)

    embedder = data["per_role"]["embedder"]
    assert embedder["expected"] is True
    assert embedder["running"] is True
    assert embedder["expected_ports"] == [8090, 8091, 8092, 8093, 8094, 8095]
    assert embedder["running_ports"] == [8090, 8091, 8092, 8093, 8094, 8095]
    assert embedder["expected_instance_count"] == 6
    assert embedder["running_instance_count"] == 6
    assert embedder["n_recent"] == 0
    assert embedder["n_completed"] == 0


def _quiet_activity_sources(monkeypatch, tmp_path) -> None:
    """Silence tap/journal inputs so only /slots occupancy drives the result."""
    monkeypatch.setattr(dashboard, "_read_tail", lambda *a, **kw: "")
    monkeypatch.setattr(dashboard, "_read_tap_events_tail", lambda *a, **kw: "")
    monkeypatch.setattr(dashboard, "_parse_inference_sections", lambda *a, **kw: [])
    monkeypatch.setattr(dashboard, "_todays_progress_log", lambda: tmp_path / "missing.jsonl")


def test_topology_activity_busy_slots_are_not_reported_as_idle(monkeypatch, tmp_path) -> None:
    """A role whose llama-server has a processing slot must read BUSY.

    Regression for the defect where the topology panel derived its busy/idle
    claim from a reachability probe: a saturated role rendered "idle · servers
    up" because no orchestrator-side tap record or CPU region lock existed for
    the traffic. Occupancy comes from /slots and nothing else.
    """
    _quiet_activity_sources(monkeypatch, tmp_path)
    monkeypatch.setattr(dashboard, "_discover_llama_ports", lambda: {8072: "worker_general"})

    payload = dashboard._topology_activity_payload(
        window_s=600.0,
        # Two slots, one actively decoding, and ZERO tap/journal corroboration.
        slots_by_port={8072: [{"is_processing": True}, {"is_processing": False}]},
    )
    role = payload["per_role"]["worker_general"]
    assert role["occupancy_observed"] is True
    assert role["busy"] is True
    assert role["slots_busy"] == 1
    assert role["slots_total"] == 2
    assert role["busy_ports"] == [8072]
    assert payload["occupancy_source"] == "llama_server_slots"
    assert payload["fleet_slots_busy"] == 1
    assert payload["fleet_slots_total"] == 2


def test_topology_activity_unmeasured_port_is_unknown_not_idle(monkeypatch, tmp_path) -> None:
    """A port that did not answer /slots must NOT read as idle.

    `_poll_slot` maps every failure to [] in `slots_by_port`. Treating that as
    "answered with zero busy slots" is what let a server too busy to service a
    trivial GET disappear from the occupancy count and be rendered as idle.
    """
    _quiet_activity_sources(monkeypatch, tmp_path)
    monkeypatch.setattr(dashboard, "_discover_llama_ports", lambda: {8182: "worker_general.q1"})

    payload = dashboard._topology_activity_payload(
        window_s=600.0,
        slots_by_port={8182: []},  # did not answer
    )
    role = payload["per_role"]["worker_general"]
    assert role["occupancy_observed"] is False
    assert role["busy"] is None, "unmeasured must be None (unknown), never False (idle)"
    assert role["unreachable_ports"] == [8182]
    assert payload["occupancy_observed"] is False


def test_topology_activity_partial_answer_marks_lower_bound(monkeypatch, tmp_path) -> None:
    """Some instances measured, others not -> busy count is a lower bound."""
    _quiet_activity_sources(monkeypatch, tmp_path)
    monkeypatch.setattr(
        dashboard,
        "_discover_llama_ports",
        lambda: {8072: "worker_general", 8182: "worker_general.q1"},
    )
    payload = dashboard._topology_activity_payload(
        window_s=600.0,
        slots_by_port={8072: [{"is_processing": False}], 8182: []},
    )
    role = payload["per_role"]["worker_general"]
    assert role["occupancy_observed"] is True
    assert role["slots_busy"] == 0
    assert role["unreachable_ports"] == [8182], "the unmeasured instance must stay visible"


def test_topology_activity_without_slots_is_unknown_not_idle(monkeypatch, tmp_path) -> None:
    """No /slots data at all -> occupancy unknown, never a silent zero."""
    _quiet_activity_sources(monkeypatch, tmp_path)
    monkeypatch.setattr(dashboard, "_discover_llama_ports", lambda: {8072: "worker_general"})
    payload = dashboard._topology_activity_payload(window_s=600.0, slots_by_port=None)
    role = payload["per_role"]["worker_general"]
    assert role["occupancy_observed"] is False
    assert role["slots_busy"] is None
    assert payload["occupancy_source"] == "unavailable"
    assert payload["fleet_slots_busy"] is None
    # Reachability is a SEPARATE signal and must survive independently.
    assert role["running"] is True


def test_poll_all_slots_marks_failed_port_unanswered(monkeypatch) -> None:
    """A per-request failure must not be counted as a successful answer.

    `_poll_slot` used to swallow timeouts and return [], so its task completed
    normally and the fan-out meta reported answered=N, timed_out=0 while a port
    contributed nothing to the occupancy total.
    """
    monkeypatch.setattr(dashboard, "_discover_llama_ports", lambda: {8072: "a", 8182: "b"})

    async def fake_poll(_client, port):
        return [{"is_processing": True}] if port == 8072 else None

    monkeypatch.setattr(dashboard, "_poll_slot", fake_poll)
    slots_by_port, meta = asyncio.run(dashboard._poll_all_slots())
    assert slots_by_port == {8072: [{"is_processing": True}], 8182: []}
    assert meta["answered"] == 1
    assert meta["timed_out"] == 1
    assert meta["unanswered_ports"] == [8182]


def test_region_locks_payload_surfaces_global_lock_domain() -> None:
    """The host-wide GLOBAL.* admission lock must be reported.

    It is not a contention-matrix role, so the per-role filter dropped it
    entirely — the panel could read "no locks held" while GLOBAL quarters were
    flocked by a live request.
    """
    payload = dashboard._region_locks_payload()
    assert "global_lock" in payload
    g = payload["global_lock"]
    assert set(g) >= {"regions", "held", "holder_pids", "held_region_count"}
    for region in g["regions"]:
        assert region["lock_path"].endswith(".lock")
        assert "GLOBAL" in region["lock_path"]


def test_service_port_hints_are_auxiliary_only() -> None:
    hints = dashboard_topology._service_port_hints()
    assert hints[8000] == "orchestrator"
    assert hints[8090] == "embedder"
    assert "worker_fast" not in hints.values()


def test_stack_prior_port_hints_skip_alias_records(tmp_path) -> None:
    priors = tmp_path / "stack_priors.yaml"
    priors.write_text(
        json.dumps(
            {
                "roles": {
                    "frontdoor": {
                        "deployment_status": "live_stack",
                        "serving": {
                            "ports": [8070, 8080, 8180],
                            "launch": {
                                "primary_roles": ["frontdoor"],
                                "entries": [
                                    {
                                        "port": 8070,
                                        "primary_role": "frontdoor",
                                        "alias": False,
                                        "numa_instance": 0,
                                    },
                                    {
                                        "port": 8080,
                                        "primary_role": "frontdoor",
                                        "alias": False,
                                        "numa_instance": 1,
                                    },
                                    {
                                        "port": 8180,
                                        "primary_role": "frontdoor",
                                        "alias": False,
                                        "numa_instance": 2,
                                    },
                                ],
                            },
                        },
                    },
                    "coder_escalation": {
                        "deployment_status": "live_stack",
                        "serving": {
                            "ports": [8070],
                            "launch": {
                                "primary_roles": ["frontdoor"],
                                "entries": [
                                    {
                                        "port": 8070,
                                        "primary_role": "frontdoor",
                                        "alias": True,
                                        "numa_instance": 0,
                                    },
                                ],
                            },
                        },
                    },
                    "candidate_only": {
                        "deployment_status": "benchmark_or_candidate",
                        "serving": {
                            "ports": [9999],
                            "launch": {"primary_roles": [], "entries": []},
                        },
                    },
                }
            }
        ),
        encoding="utf-8",
    )

    hints = dashboard_topology._stack_prior_port_hints(priors)
    assert hints[8070] == "frontdoor"
    assert hints[8080] == "frontdoor.q0"
    assert hints[8180] == "frontdoor.q1"
    assert 9999 not in hints
    assert "coder_escalation" not in hints.values()


def test_load_state_services_missing_file_returns_empty(tmp_path) -> None:
    services = dashboard_topology._load_state_services(tmp_path / "no_such.json")
    assert services == []


def test_load_state_services_parses_known_fields(tmp_path) -> None:
    state_file = tmp_path / "state.json"
    state_file.write_text(json.dumps({
        "orchestrator": {
            "role": "orchestrator", "port": 8000, "pid": 123,
            "model_path": "api", "log_file": "api.log",
        },
        "embedder": {
            "role": "embedder", "port": 8090, "pid": 999999999,
            "model_path": "/m/bge.gguf", "log_file": "emb.log",
        },
        "junk": "not a dict, must be skipped",
    }))
    services = dashboard_topology._load_state_services(state_file)
    assert {s["name"] for s in services} == {"orchestrator", "embedder"}
    embedder = next(s for s in services if s["name"] == "embedder")
    assert embedder["port"] == 8090
    assert embedder["model"] == "/m/bge.gguf"
    assert embedder["running"] is False


def _isolate_llama_attribution_plane(monkeypatch, tmp_path: Path) -> None:
    """Pin the M3 attribution plane to "no signal" so label resolution is hermetic.

    ``_discover_llama_processes`` demotes lane labels to ``extern_<port>`` when
    the host carries fleet markers or a runtime launch contract that do not vouch
    for the listener. These tests assert port->label resolution, not M3 demotion
    (covered in test_dashboard_extern_attribution.py), so the host's live markers
    and runtime-facts manifest must not leak in: with neither plane present the
    classifier fails open (``unverified``) and keeps the configured labels.
    """
    from scripts.server import stack_paths

    monkeypatch.setitem(stack_paths._PATHS, "tmp_dir", tmp_path)
    monkeypatch.setattr(dashboard_topology, "_llama_fleet_markers", lambda: {})
    monkeypatch.setattr(dashboard_topology, "_launch_contract_ports", lambda: set())


def test_discover_llama_ports_parses_ps_output(monkeypatch, tmp_path) -> None:
    _isolate_llama_attribution_plane(monkeypatch, tmp_path)
    fake_ps = (
        "1234 /opt/llama-server --port 8070 -m /m/frontdoor.gguf\n"
        "5678 /opt/llama-server --port 9999 -m /m/mystery.gguf\n"
        "4242 /mnt/raid0/llm/llama.cpp-mi210-hip/build-hip/bin/llama-server --port 8802 -m /m/Qwen.gguf\n"
        "9999 some-other-process --port 1234\n"
    )
    monkeypatch.setattr(
        dashboard_topology.subprocess, "run",
        lambda *a, **kw: SimpleNamespace(stdout=fake_ps),
    )
    ports = dashboard_topology._discover_llama_ports()
    assert ports[8070] == "frontdoor"
    # Unmapped ports get an honest role, never a model-mangled one — the old
    # "port_9999(mystery)" fallback leaked garbled keys into live_busy_by_role.
    assert ports[9999] == "extern_9999"
    # MI210 HIP builds are the GPU testbed (operator-decided first-class role).
    assert ports[8802] == "mi210_gpu"
    assert 1234 not in ports  # filtered out (no llama-server in cmd)


def test_discover_llama_ports_labels_live_quarters_as_configured_instances(
    monkeypatch, tmp_path
) -> None:
    _isolate_llama_attribution_plane(monkeypatch, tmp_path)
    # Second sibling of worker_general's host fleet (was the gemma 8182 quarter).
    _full, host_siblings = _full_and_sibling_ports(_WG_HOST)
    assert len(host_siblings) >= 2
    host_q1 = host_siblings[1]
    fake_ps = (
        "1234 /opt/llama-server --port 8080 -m /m/frontdoor-quarter.gguf\n"
        f"5678 /opt/llama-server --port {host_q1} -m /m/worker-quarter.gguf\n"
    )
    monkeypatch.setenv("ORCHESTRATOR_STACK_NUMA_MODE", "full")
    monkeypatch.setattr(
        dashboard_topology.subprocess, "run",
        lambda *a, **kw: SimpleNamespace(stdout=fake_ps),
    )

    ports = dashboard_topology._discover_llama_ports()

    assert ports[8080] == "frontdoor.q0"
    assert ports[host_q1] == f"{_WG_HOST}.q1"
    assert all(not role.startswith("extern_") for role in ports.values())


# ----- dashboard_tap -----


def test_read_tail_returns_empty_for_missing_file(tmp_path) -> None:
    assert dashboard_tap._read_tail(tmp_path / "missing.log") == ""


def test_read_tail_small_file_returns_full_content(tmp_path) -> None:
    f = tmp_path / "small.log"
    f.write_text("hello world\n")
    assert dashboard_tap._read_tail(f) == "hello world\n"


def test_read_tail_large_file_truncates_to_last_bytes(tmp_path) -> None:
    f = tmp_path / "big.log"
    f.write_text("a\n" * 200_000)  # 400KB
    out = dashboard_tap._read_tail(f, max_bytes=4_096)
    assert len(out.encode()) <= 4_096
    # All remaining lines should be the same content
    assert out.strip().split("\n")[0] == "a"


def test_parse_inference_sections_empty_input() -> None:
    assert dashboard_tap._parse_inference_sections("") == []


def test_parse_inference_sections_extracts_role_prompt_response() -> None:
    sep = "=" * 72
    sub = "-" * 72
    tap = (
        f"[2026-05-22 10:00:00] ROLE=frontdoor\n{sub}\n"
        f"PROMPT: hello world\n{sub}\n"
        f"RESPONSE:\nhi there\n{sep}\n"
    )
    sections = dashboard_tap._parse_inference_sections(tap)
    assert len(sections) == 1
    assert sections[0]["role"] == "frontdoor"
    assert sections[0]["prompt"] == "hello world"
    assert "hi there" in sections[0]["response"]


def test_parse_inference_sections_skips_timings_probes() -> None:
    """Short TIMINGS: responses are llama.cpp probes, not real inference; must be filtered."""
    sep = "=" * 72
    sub = "-" * 72
    tap = (
        f"[2026-05-22 10:00:00] ROLE=frontdoor\n{sub}\n"
        f"PROMPT: probe\n{sub}\n"
        f"RESPONSE:\nTIMINGS: short\n{sep}\n"
    )
    assert dashboard_tap._parse_inference_sections(tap) == []


def test_parse_structured_tap_requests_groups_events_by_request() -> None:
    def event(kind: str, request_id: str, **fields):
        payload = {
            "event": kind,
            "request_id": request_id,
            "role": "frontdoor",
            "ts": f"2026-05-22T10:00:0{len(lines)}+00:00",
            "ts_epoch": float(len(lines)),
            **fields,
        }
        lines.append(json.dumps(payload))

    lines: list[str] = []
    event(
        "start",
        "req-1",
        prompt="hello",
        prompt_len=629_310,
        prompt_truncated=True,
        task_id="task-1",
        trial_id=3,
        batch_id="b1",
    )
    event("metadata", "req-1", instance_idx=2, instance_shape="q1", port=8082, topology_hash="abc123")
    event("chunk", "req-1", text="hi ")
    event("chunk", "req-1", text="there")
    event("timings", "req-1", tokens=2, prompt_ms=10.0, gen_ms=20.0, tps=100.0, total_s=0.03)
    event("end", "req-1")

    parsed = dashboard_tap._parse_structured_tap_requests("\n".join(lines))

    assert len(parsed) == 1
    req = parsed[0]
    assert req["request_id"] == "req-1"
    assert req["task_id"] == "task-1"
    assert req["trial_id"] == 3
    assert req["batch_id"] == "b1"
    assert req["instance_idx"] == 2
    assert req["instance_shape"] == "q1"
    assert req["port"] == 8082
    assert req["topology_hash"] == "abc123"
    assert req["prompt"] == "hello"
    assert req["prompt_len"] == 629_310
    assert req["prompt_preview_len"] == 5
    assert req["prompt_truncated"] is True
    assert req["response"] == "hi there"
    assert req["status"] == "complete"
    assert req["is_live"] is False
    assert req["chunk_count"] == 2
    assert "2 tokens" in req["timings"]


def test_parse_structured_tap_requests_marks_quiet_open_request() -> None:
    line = json.dumps({
        "event": "start",
        "request_id": "req-quiet",
        "role": "coder_escalation",
        "topology_role": "frontdoor",
        "lock_role": "frontdoor",
        "ts": "2026-05-22T10:00:00+00:00",
        "ts_epoch": 100.0,
        "prompt": "hello",
    })

    parsed = dashboard_tap._parse_structured_tap_requests(
        line,
        now_epoch=130.0,
        quiet_after_s=10.0,
    )

    assert len(parsed) == 1
    req = parsed[0]
    assert req["status"] == "quiet"
    assert req["is_live"] is True
    assert req["age_s"] == 30.0
    assert req["quiet_s"] == 30.0
    assert req["topology_role"] == "frontdoor"
    assert "no tap output" in req["status_reason"]


def test_structured_tap_active_ignores_stale_quiet_history() -> None:
    assert dashboard._structured_tap_active(
        [
            {"status": "quiet", "quiet_s": 300.0},
            {"status": "complete", "quiet_s": 0.0},
        ]
    ) is False
    assert dashboard._structured_tap_active(
        [{"status": "running", "quiet_s": 15.0}]
    ) is False
    assert dashboard._structured_tap_active(
        [{"status": "running", "quiet_s": 2.0}]
    ) is True


def test_inference_tap_snapshot_marks_stale_sentinel_inactive(
    monkeypatch,
    tmp_path,
) -> None:
    sentinel = tmp_path / "inference_tap_active"
    sentinel.touch()
    event_line = json.dumps(
        {
            "event": "start",
            "request_id": "req-stale",
            "role": "ingest_long_context",
            "ts": "2026-05-22T10:00:00+00:00",
            "ts_epoch": 100.0,
            "prompt": "planner critique",
        }
    )

    monkeypatch.setattr(dashboard, "_TAP_SENTINEL_PATH", sentinel)
    monkeypatch.setattr(dashboard.time, "time", lambda: 130.0)
    monkeypatch.setattr(dashboard, "_read_tail", lambda *a, **kw: "")
    monkeypatch.setattr(dashboard, "_read_tap_events_tail", lambda *a, **kw: event_line)
    monkeypatch.setattr(dashboard, "_latest_tap_events_mtime", lambda: 100.0)

    response = asyncio.run(dashboard.inference_tap_snapshot())
    payload = json.loads(response.body)

    assert payload["tap_sentinel_active"] is True
    assert payload["tap_active"] is False
    assert payload["structured_requests"][0]["status"] == "quiet"


def test_structured_tap_requests_for_dashboard_uses_shared_region_lock_frame(monkeypatch) -> None:
    now = 100.0
    event_line = json.dumps(
        {
            "event": "start",
            "request_id": "chat-coder:abc",
            "role": "coder_escalation",
            "port": 8070,
            "ts": "2026-05-22T10:00:00+00:00",
            "ts_epoch": now - 1,
            "prompt": "fix code",
        }
    )
    region_locks = {
        "by_role": {
            "frontdoor": {
                "instances": [
                    {"idx": 0, "shape": "half0", "regions": ["q0", "q1"]},
                    {"idx": 3, "shape": "q2", "regions": ["q2"]},
                ],
            },
        },
    }

    monkeypatch.setattr(dashboard, "_read_tap_events_tail", lambda *a, **kw: event_line)
    enriched = dashboard._structured_tap_requests_for_dashboard(
        max_requests=20,
        now_epoch=now,
        region_locks=region_locks,
        port_roles={8070: "frontdoor"},
    )

    assert len(enriched) == 1
    req = enriched[0]
    assert req["role"] == "coder_escalation"
    assert req["topology_role"] == "frontdoor"
    assert req["lock_role"] == "frontdoor"
    assert req["instance_idx"] == 0
    assert req["instance_shape"] == "half0"
    assert req["instance_regions"] == ["q0", "q1"]


def test_offwindow_lock_holder_recovered_from_wide_tail(monkeypatch) -> None:
    """A live CPU-region holder whose `start` event aged out of the 1 MB tail
    must be recovered from the wider reverse window so it is NOT mis-rendered as
    a false "off-tap holder". Regression for the recurring worker_general.full /
    autopilot:numeric_trial warning."""
    now = 1_000.0
    held_event = json.dumps({
        "event": "start",
        "request_id": "chat-HELD:1",
        "task_id": "chat-HELD",
        "role": "worker_general",
        "topology_role": "worker_general",
        "lock_role": "worker_general",
        "instance_idx": 0,
        "instance_shape": "full",
        "port": 8072,
        "pid": 999,
        "ts": "2026-07-10T11:00:00+00:00",
        "ts_epoch": now - 3,  # recent → status "running", not complete
        "prompt": "eval prompt",
    })

    # 1 MB tail: holder absent (aged out). Wider recovery read: holder present.
    def fake_tail(_path, max_bytes=1024 * 1024):
        return held_event if max_bytes > 1024 * 1024 else ""

    monkeypatch.setattr(dashboard, "_read_tap_events_tail", fake_tail)

    region_locks = {
        "by_role": {
            "worker_general": {
                "instances": [
                    {"idx": 0, "shape": "full", "regions": ["q0", "q1", "q2", "q3"]},
                ],
                "regions": [
                    {"region": r, "held": True,
                     "holder_pids": ["999"], "holder_instance_idxs": [0]}
                    for r in ("q0", "q1", "q2", "q3")
                ],
            },
        },
    }

    recovered = dashboard._structured_tap_requests_for_dashboard(
        max_requests=20,
        now_epoch=now,
        region_locks=region_locks,
        port_roles={8072: "worker_general"},
    )

    assert [r["request_id"] for r in recovered] == ["chat-HELD:1"]
    assert recovered[0]["instance_idx"] == 0
    assert recovered[0]["status"] == "running"


def test_offwindow_recovery_skipped_when_holder_already_in_window(monkeypatch) -> None:
    """When the holder's request is already in the 1 MB tail, no wider read is
    issued and no duplicate row is injected (the common streaming path)."""
    now = 2_000.0
    live_event = json.dumps({
        "event": "start",
        "request_id": "chat-LIVE:1",
        "role": "worker_general",
        "topology_role": "worker_general",
        "lock_role": "worker_general",
        "instance_idx": 0,
        "port": 8072,
        "pid": 999,
        "ts": "2026-07-10T12:00:00+00:00",
        "ts_epoch": now - 2,
        "prompt": "live prompt",
    })

    wide_reads: list[int] = []

    def fake_tail(_path, max_bytes=1024 * 1024):
        if max_bytes > 1024 * 1024:
            wide_reads.append(max_bytes)
            return live_event  # would duplicate if erroneously merged
        return live_event

    monkeypatch.setattr(dashboard, "_read_tap_events_tail", fake_tail)

    region_locks = {
        "by_role": {
            "worker_general": {
                "instances": [{"idx": 0, "shape": "full",
                               "regions": ["q0", "q1", "q2", "q3"]}],
                "regions": [
                    {"region": r, "held": True,
                     "holder_pids": ["999"], "holder_instance_idxs": [0]}
                    for r in ("q0", "q1", "q2", "q3")
                ],
            },
        },
    }

    out = dashboard._structured_tap_requests_for_dashboard(
        max_requests=20, now_epoch=now, region_locks=region_locks,
        port_roles={8072: "worker_general"},
    )

    assert [r["request_id"] for r in out] == ["chat-LIVE:1"]  # no duplicate
    assert wide_reads == []  # holder already visible → no wider read


def test_offwindow_recovery_does_not_treat_same_pid_other_role_as_holder(
    monkeypatch,
) -> None:
    """A uvicorn PID multiplexes roles; bare PID equality cannot represent a holder."""
    now = 3_000.0
    worker_in_window = json.dumps({
        "event": "start",
        "request_id": "chat-WORKER:1",
        "task_id": "chat-WORKER",
        "role": "worker_general",
        "topology_role": "worker_general",
        "lock_role": "worker_general",
        "instance_idx": 0,
        "port": 8072,
        "pid": 999,
        "ts_epoch": now - 2,
        "prompt": "worker prompt",
    })
    frontdoor_offwindow = json.dumps({
        "event": "start",
        "request_id": "chat-FRONTDOOR:1",
        "task_id": "chat-FRONTDOOR",
        "role": "frontdoor",
        "topology_role": "frontdoor",
        "lock_role": "frontdoor",
        "instance_idx": 0,
        "port": 8070,
        "pid": 999,
        "ts_epoch": now - 3,
        "prompt": "frontdoor prompt",
    })

    def fake_tail(_path, max_bytes=1024 * 1024):
        if max_bytes > 1024 * 1024:
            return "\n".join((worker_in_window, frontdoor_offwindow))
        return worker_in_window

    monkeypatch.setattr(dashboard, "_read_tap_events_tail", fake_tail)
    region_locks = {
        "by_role": {
            "frontdoor": {
                "instances": [{"idx": 0, "shape": "full", "regions": ["q0"]}],
                "regions": [{
                    "region": "q0",
                    "held": True,
                    "holder_pids": ["999"],
                    "holder_instance_idxs": [0],
                }],
            },
        },
    }

    recovered = dashboard._structured_tap_requests_for_dashboard(
        max_requests=20,
        now_epoch=now,
        region_locks=region_locks,
        port_roles={8070: "frontdoor", 8072: "worker_general"},
    )

    assert {request["request_id"] for request in recovered} == {
        "chat-WORKER:1",
        "chat-FRONTDOOR:1",
    }


def test_topology_activity_uses_structured_tap_not_legacy_sections(monkeypatch) -> None:
    now = 1_000.0
    structured_lines = [
        json.dumps({
            "event": "start",
            "request_id": "req-worker",
            "role": "worker_general",
            "topology_role": "worker_general",
            "port": 8072,
            "ts": "2026-07-02T20:00:00+00:00",
            "ts_epoch": now - 5,
            "prompt": "worker prompt",
        }),
        json.dumps({
            "event": "timings",
            "request_id": "req-worker",
            "role": "worker_general",
            "topology_role": "worker_general",
            "port": 8072,
            "ts": "2026-07-02T20:00:01+00:00",
            "ts_epoch": now - 4,
            "tokens": 10,
            "prompt_ms": 0,
            "gen_ms": 1000,
            "tps": 42.0,
            "total_s": 1.0,
        }),
    ]
    legacy_tap = (
        f"[2026-07-02 20:00:00] ROLE=frontdoor\n{'-' * 72}\n"
        f"PROMPT: stale legacy prompt\n{'-' * 72}\n"
        f"RESPONSE:\nTIMINGS: 1 tokens in 1.00s (prompt=0ms, gen=1000ms, 9.0 t/s)\n"
        f"{'=' * 72}\n"
    )

    def fake_read_tail(path, *args, **kwargs):
        if str(path).endswith("inference_tap_events.jsonl"):
            return "\n".join(structured_lines)
        if str(path).endswith("inference_tap.log"):
            return legacy_tap
        return ""

    monkeypatch.setattr(dashboard, "_read_tail", fake_read_tail)
    monkeypatch.setattr(dashboard, "_read_tap_events_tail", fake_read_tail)
    monkeypatch.setattr(
        dashboard,
        "_discover_llama_ports",
        lambda: {8070: "frontdoor", 8072: "worker_general"},
    )
    monkeypatch.setattr(dashboard, "expected_stack_services", lambda: [
        {"role": "frontdoor", "port": 8070},
        {"role": "worker_general", "port": 8072},
    ])
    monkeypatch.setattr(dashboard, "_todays_progress_log", lambda: Path("/does/not/exist"))
    monkeypatch.setattr(dashboard, "_scan_recent_decisions", lambda _path: ([], [], []))
    monkeypatch.setattr(dashboard, "_scan_orchestrator_tasks", lambda *a, **kw: ([], []))
    monkeypatch.setattr(dashboard.time, "time", lambda: now)

    response = asyncio.run(dashboard.topology_activity(window_s=60.0))
    payload = json.loads(response.body)

    assert payload["per_role"]["worker_general"]["n_recent"] == 1
    assert payload["per_role"]["worker_general"]["avg_tps_recent"] == 42.0
    assert payload["per_role"]["frontdoor"]["n_recent"] == 0


def test_enrich_structured_tap_requests_recovers_alias_port_lock_metadata(monkeypatch) -> None:
    monkeypatch.setattr(
        dashboard,
        "role_aliases",
        lambda role: ["coder_escalation", "worker_summarize"] if role == "frontdoor" else [],
    )
    region_locks = {
        "by_role": {
            "frontdoor": {
                "instances": [
                    {"idx": 0, "shape": "half0", "regions": ["q0", "q1"]},
                    {"idx": 3, "shape": "q2", "regions": ["q2"]},
                ],
            },
            "worker_general": {
                "instances": [
                    {"idx": 0, "shape": "full", "regions": ["q0", "q1", "q2", "q3"]},
                    {"idx": 3, "shape": "q2", "regions": ["q2"]},
                ],
            },
        },
    }

    enriched = dashboard._enrich_structured_tap_requests(
        [
            {"request_id": "coder", "role": "coder_escalation", "port": 8070},
            {"request_id": "worker", "role": "worker_general", "port": 8072},
        ],
        port_roles={8070: "frontdoor", 8072: "worker_general"},
        region_locks=region_locks,
    )

    coder, worker = enriched
    assert coder["role"] == "coder_escalation"
    assert coder["topology_role"] == "frontdoor"
    assert coder["lock_role"] == "frontdoor"
    assert coder["instance_idx"] == 0
    assert coder["instance_shape"] == "half0"
    assert coder["instance_regions"] == ["q0", "q1"]
    assert worker["topology_role"] == "worker_general"
    assert worker["lock_role"] == "worker_general"
    assert worker["instance_shape"] == "full"
    assert worker["instance_regions"] == ["q0", "q1", "q2", "q3"]


def test_enrich_structured_tap_requests_uses_quarter_port_shape(monkeypatch) -> None:
    monkeypatch.setattr(dashboard, "role_aliases", lambda role: [])
    region_locks = {
        "by_role": {
            "worker_general": {
                "instances": [
                    {"idx": 0, "shape": "full", "regions": ["q0", "q1", "q2", "q3"]},
                    {"idx": 3, "shape": "q2", "regions": ["q2"]},
                ],
            },
        },
    }

    [req] = dashboard._enrich_structured_tap_requests(
        [{"request_id": "quarter", "role": "worker_general", "port": 8282}],
        port_roles={8282: "worker_general.q2"},
        region_locks=region_locks,
    )

    assert req["topology_role"] == "worker_general"
    assert req["instance_idx"] == 3
    assert req["instance_shape"] == "q2"
    assert req["instance_regions"] == ["q2"]


def test_parse_trial_state_parses_baseline_then_score() -> None:
    tail = (
        "2026-05-22 10:00 GEPA: evaluating baseline for some_file.md (12 sentinels)\n"
        "2026-05-22 10:01 GEPA: baseline score = 0.85\n"
        "2026-05-22 10:02 Dispatching action: mutate_prompt\n"
    )
    state = dashboard_tap._parse_trial_state(tail)
    assert state["current_file"] == "some_file.md"
    assert state["baseline_sentinels_total"] == 12
    assert state["baseline_score"] == 0.85
    assert state["last_event"] == "baseline_done"
    assert state["current_action"] == "mutate_prompt"


def test_read_autopilot_phase_returns_dict(tmp_path, monkeypatch) -> None:
    phase_path = tmp_path / "phase.json"
    phase_path.write_text(json.dumps({"phase": "dispatch_action", "trial_id": 12}))
    monkeypatch.setattr(dashboard, "AUTOPILOT_PHASE_PATH", phase_path)

    phase = dashboard._read_autopilot_phase()

    assert phase["phase"] == "dispatch_action"
    assert phase["trial_id"] == 12


def test_read_autopilot_phase_invalid_returns_empty(tmp_path, monkeypatch) -> None:
    phase_path = tmp_path / "phase.json"
    phase_path.write_text("not json")
    monkeypatch.setattr(dashboard, "AUTOPILOT_PHASE_PATH", phase_path)

    assert dashboard._read_autopilot_phase() == {}


def test_autopilot_phase_health_reports_active(tmp_path, monkeypatch) -> None:
    phase_path = tmp_path / "phase.json"
    phase_path.write_text(json.dumps({
        "phase": "dispatch_action",
        "trial_id": 12,
        "action_type": "numeric_trial",
        "pid": os.getpid(),
        "updated_at": time.time(),
    }))
    monkeypatch.setattr(dashboard, "AUTOPILOT_PHASE_PATH", phase_path)

    health = dashboard._autopilot_phase_health()

    assert health["ok"] is True
    assert health["status"] == "active"
    assert health["trial_id"] == 12
    assert health["pid_alive"] is True


def test_autopilot_phase_health_reports_stale(tmp_path, monkeypatch) -> None:
    phase_path = tmp_path / "phase.json"
    phase_path.write_text(json.dumps({
        "phase": "dispatch_action",
        "trial_id": 12,
        "action_type": "deep_eval",
        "pid": os.getpid(),
        "updated_at": time.time() - 3600,
    }))
    monkeypatch.setattr(dashboard, "AUTOPILOT_PHASE_PATH", phase_path)

    health = dashboard._autopilot_phase_health()

    assert health["ok"] is False
    assert health["status"] == "stale"
    assert health["blockers"]


def test_autopilot_current_code_health_includes_restart_advice(monkeypatch) -> None:
    def fake_phase_health(**_kwargs):
        return {
            "ok": False,
            "status": "code_stale",
            "phase": "dispatch_action",
            "pid": os.getpid(),
            "pid_alive": True,
            "trial_id": 1207,
            "action_type": "seed_batch",
            "idle_reason": "evaluating question",
            "code_stale": True,
            "blockers": ["autopilot process predates runtime source changes: autopilot.py"],
        }

    monkeypatch.setattr(dashboard, "build_phase_health_report", fake_phase_health)

    health = dashboard._autopilot_current_code_health()

    assert health is not None
    assert health["restart_advice"]["restart_needed"] is True
    assert health["restart_advice"]["safe_to_restart_now"] is False
    assert health["restart_advice"]["status"] == "wait_for_boundary"


def test_process_status_includes_autopilot_phase_health(tmp_path, monkeypatch) -> None:
    phase_path = tmp_path / "phase.json"
    phase_path.write_text(json.dumps({
        "phase": "dispatch_action",
        "trial_id": 12,
        "action_type": "numeric_trial",
        "pid": os.getpid(),
        "updated_at": time.time(),
    }))
    monkeypatch.setattr(dashboard, "AUTOPILOT_PHASE_PATH", phase_path)
    monkeypatch.setattr(dashboard, "AUTOPILOT_LOG", tmp_path / "missing.log")
    monkeypatch.setattr(
        dashboard,
        "_process_info_by_match",
        lambda _match: {"running": True, "pid": os.getpid()},
    )
    monkeypatch.setattr(
        dashboard,
        "_autopilot_phase_health",
        lambda: {
            "status": "active",
            "heartbeat_age_s": 12.5,
            "outcome_progress": {
                "status": "attention",
                "latest_trial_id": 12,
                "frontier_admissions": 1,
                "trials_since_frontier": 151,
                "baseline_promotions": 2,
                "trials_since_promotion": 301,
                "rates": {
                    "keepable_rate": {"count": 4, "total": 10, "rate": 0.4},
                    "wasted_eval_rate": {"count": 3, "total": 10, "rate": 0.3},
                    "learning_excluded_rate": {"count": 2, "total": 10, "rate": 0.2},
                },
                "blockers": ["frontier admission stale: 151 trial(s) since frontier > 150"],
            },
        },
    )

    response = asyncio.run(dashboard.process_status())
    payload = json.loads(response.body)

    assert payload["autopilot_phase"]["trial_id"] == 12
    assert payload["autopilot_phase_health"]["status"] == "active"
    assert payload["autopilot_outcome_progress"]["status"] == "attention"
    assert payload["autopilot_outcome_progress"]["blockers"] == [
        "frontier admission stale: 151 trial(s) since frontier > 150",
    ]
    assert payload["autopilot_phase_age_s"] == payload["autopilot_phase_health"]["heartbeat_age_s"]


def test_repo_readiness_summary_loads_latest_advisory_queue(tmp_path) -> None:
    data_dir = tmp_path / "data"
    progress_dir = tmp_path / "progress"
    data_dir.mkdir()
    progress_dir.mkdir()
    (data_dir / "repo_readiness_2026-06-19.json").write_text(
        json.dumps({"generated_at": "old", "repos": {}}),
        encoding="utf-8",
    )
    report = data_dir / "repo_readiness_2026-06-20.json"
    report.write_text(
        json.dumps(
            {
                "generated_at": "2026-06-20T00:00:00Z",
                "portfolio": {"maturity": {"achieved_level": 2}},
                "repos": {
                    "epyc-root": {"maturity": {"achieved_level": 4}},
                },
            }
        ),
        encoding="utf-8",
    )
    queue = data_dir / "repo_readiness_remediation_queue_2026-06-20.json"
    queue.write_text(
        json.dumps(
            {
                "generated_at": "2026-06-20T00:00:01Z",
                "version": 1,
                "item_count": 2,
                "items": [
                    {"priority": "P1", "repo": "epyc-root", "criterion_id": "L5.auto_eval"},
                    {"priority": "P0", "repo": "epyc-orchestrator", "criterion_id": "L3.security"},
                ],
            }
        ),
        encoding="utf-8",
    )
    markdown = progress_dir / "repo-readiness-remediation-2026-06-20.md"
    markdown.write_text("# queue\n", encoding="utf-8")

    summary = dashboard._repo_readiness_summary(
        data_dir=data_dir,
        progress_dir=progress_dir,
        top_n=1,
    )

    assert summary["available"] is True
    assert summary["authority"] == "advisory"
    assert summary["autopilot_gate"] is False
    assert summary["report_path"] == str(report)
    assert summary["queue_path"] == str(queue)
    assert summary["markdown_path"] == str(markdown)
    assert summary["generated_at"] == "2026-06-20T00:00:01Z"
    assert summary["portfolio_level"] == {"achieved_level": 2}
    assert summary["repo_levels"]["epyc-root"] == {"achieved_level": 4}
    assert summary["priority_counts"] == {"P1": 1, "P0": 1}
    assert summary["top_items"] == [
        {"priority": "P0", "repo": "epyc-orchestrator", "criterion_id": "L3.security"}
    ]


def test_repo_readiness_route_is_advisory_when_missing(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(dashboard, "REPO_READINESS_DIR", tmp_path / "missing-data")
    monkeypatch.setattr(dashboard, "REPO_READINESS_PROGRESS_DIR", tmp_path / "missing-progress")

    response = asyncio.run(dashboard.repo_readiness())
    payload = json.loads(response.body)

    assert payload["available"] is False
    assert payload["authority"] == "advisory"
    assert payload["autopilot_gate"] is False
    assert payload["item_count"] == 0
    assert payload["top_items"] == []


# ----- dashboard_tasks -----


def test_task_events_filters_by_task_id(tmp_path) -> None:
    log = tmp_path / "progress.jsonl"
    log.write_text(
        json.dumps({"task_id": "chat-1", "event_type": "task_started", "timestamp": "t1", "data": {}}) + "\n"
        + json.dumps({"task_id": "chat-2", "event_type": "task_started", "timestamp": "t2", "data": {}}) + "\n"
        + json.dumps({"task_id": "chat-1", "event_type": "routing_decision", "timestamp": "t3", "data": {"src": "x"}}) + "\n"
        + "not-valid-json\n"
        + json.dumps({"task_id": "chat-1", "event_type": "task_completed", "timestamp": "t4", "data": {}}) + "\n"
    )
    events = dashboard_tasks._task_events("chat-1", log)
    assert len(events) == 3
    assert [e["event_type"] for e in events] == ["task_started", "routing_decision", "task_completed"]


def test_task_events_returns_empty_when_path_missing(tmp_path) -> None:
    assert dashboard_tasks._task_events("chat-1", tmp_path / "no_such.log") == []


def test_objective_for_task_extracts_from_task_started_event() -> None:
    events = [
        {"event_type": "routing_decision", "data": {"chosen_action": "x"}},
        {"event_type": "task_started", "data": {"objective": "Solve fizzbuzz"}},
    ]
    assert dashboard_tasks._objective_for_task(events) == "Solve fizzbuzz"


def test_objective_for_task_returns_empty_when_no_started_event() -> None:
    events = [{"event_type": "task_completed", "data": {}}]
    assert dashboard_tasks._objective_for_task(events) == ""


def test_terminal_answer_for_task_reads_completed_work_answer() -> None:
    events = [
        {"event_type": "task_started", "data": {"objective": "read image"}},
        {
            "event_type": "task_completed",
            "data": {"producer_role": "worker_vision", "work": {"answer": "0.0g"}},
        },
    ]

    assert dashboard_tasks._terminal_answer_for_task(events) == "0.0g"


def test_task_text_snapshot_uses_slot_prompt_when_available() -> None:
    slot = {"prompt": "live prompt", "content": "streaming output"}
    events = [{"event_type": "task_started", "timestamp": "2026-05-22T10:00:00Z", "data": {"objective": "from event"}}]
    out = dashboard_tasks._task_text_snapshot("chat-1", events, slot)
    assert "live prompt" in out
    assert "streaming output" in out
    # Slot prompt wins in the PROMPT block (the event's objective still appears
    # later in the REPL HISTORY event dump, which is by design).
    prompt_block = out.split("INFERENCE STREAM:")[0]
    assert "live prompt" in prompt_block
    assert "from event" not in prompt_block


def test_pareto_from_journal_excludes_tier0(tmp_path, monkeypatch) -> None:
    """T0 sentinel rows (10q, quality saturates ~2.4=8/10) must not enter the
    dashboard-reconstructed frontier/hypervolume — mirrors ec9622d's archive
    exclusion so the operator panel shows the real T1/T2 frontier, not a phantom 2.4."""
    journal = tmp_path / "autopilot_journal.jsonl"
    rows = [
        # T0 sentinel: saturated quality that WOULD dominate if admitted
        {"trial_id": 10, "tier": 0, "quality": 2.4, "speed": 60.0, "cost": 0.5,
         "reliability": 0.9, "timestamp": "2026-05-31T10:00:00+00:00"},
        # honest T1 entry — the real frontier point
        {"trial_id": 11, "tier": 1, "quality": 1.9, "speed": 70.0, "cost": 0.5,
         "reliability": 0.9, "timestamp": "2026-05-31T10:01:00+00:00"},
    ]
    journal.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    monkeypatch.setattr(dashboard, "_AUTOPILOT_JOURNAL_PATH", journal)

    archive = dashboard._pareto_from_journal(None, current_run_only=False)
    assert archive is not None
    frontier_ids = {e["trial_id"] for e in archive["frontier"]}
    assert frontier_ids == {11}, "only the honest T1 entry belongs on the frontier"
    assert all(e["trial_id"] != 10 for e in archive["all_entries"]), "T0 excluded entirely"


def test_pareto_from_journal_segregates_tiers(tmp_path, monkeypatch) -> None:
    """Validation/stress quality must not dominate the canonical T1 dashboard frontier."""
    journal = tmp_path / "autopilot_journal.jsonl"
    rows = [
        {"trial_id": 20, "tier": 1, "quality": 1.5, "speed": 30.0, "cost": 0.5,
         "reliability": 0.9, "timestamp": "2026-05-31T10:00:00+00:00"},
        {"trial_id": 21, "tier": 2, "quality": 2.4, "speed": 40.0, "cost": 0.5,
         "reliability": 0.9, "timestamp": "2026-05-31T10:01:00+00:00"},
        {"trial_id": 22, "tier": 3, "quality": 1.2, "speed": 45.0, "cost": 0.5,
         "reliability": 0.9, "timestamp": "2026-05-31T10:02:00+00:00"},
    ]
    journal.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    monkeypatch.setattr(dashboard, "_AUTOPILOT_JOURNAL_PATH", journal)

    archive = dashboard._pareto_from_journal(None, current_run_only=False)
    assert archive is not None
    assert [e["trial_id"] for e in archive["frontier"]] == [20]
    assert [e["trial_id"] for e in archive["frontiers_by_tier"]["2"]] == [21]
    assert [e["trial_id"] for e in archive["frontiers_by_tier"]["3"]] == [22]


def test_task_text_snapshot_falls_back_to_objective_when_no_slot() -> None:
    events = [{"event_type": "task_started", "timestamp": "t", "data": {"objective": "fallback objective"}}]
    out = dashboard_tasks._task_text_snapshot("chat-2", events, None)
    assert "fallback objective" in out
    # The empty-placeholder text was made more descriptive (2026-05-23):
    # "(empty)" → "(empty — no live slot and no matching tap section)".
    # Match the prefix so the test stays robust to minor copy tweaks.
    assert "(empty" in out  # no inference stream
    assert "INFERENCE STREAM:" in out


def test_task_text_snapshot_falls_back_to_terminal_work_answer() -> None:
    events = [
        {"event_type": "task_started", "timestamp": "t", "data": {"objective": "read image"}},
        {
            "event_type": "task_completed",
            "timestamp": "t",
            "data": {"producer_role": "worker_vision", "work": {"answer": "0.0g"}},
        },
    ]

    out = dashboard_tasks._task_text_snapshot("chat-vision", events, None)

    assert "0.0g" in out
    assert "source: terminal task event work.answer" in out


def test_task_text_snapshot_uses_structured_tap_section() -> None:
    tap_section = {
        "source": "structured_tap",
        "request_id": "req-1",
        "started_at": "2026-05-22T10:00:00+00:00",
        "role": "frontdoor",
        "prompt": "structured prompt",
        "response": "structured response",
    }
    out = dashboard_tasks._task_text_snapshot(
        "tap_req-1", [], None, tap_section=tap_section
    )
    assert "structured prompt" in out
    assert "structured response" in out
    assert "inference_tap_events.jsonl request req-1" in out


def test_task_text_snapshot_elides_noisy_keys() -> None:
    events = [{
        "event_type": "routing_decision",
        "timestamp": "2026-05-22T10:00:00Z",
        "data": {
            "chosen_action": "worker",
            "stack_state": "x" * 4000,  # noisy
            "similarity_topk": [1, 2, 3],  # noisy
        },
    }]
    out = dashboard_tasks._task_text_snapshot("chat-3", events, None)
    assert "_elided_keys" in out
    assert "stack_state" not in out or "_elided_keys" in out  # noisy key removed from data dump


def test_find_section_by_objective_short_objective_returns_none() -> None:
    assert dashboard_tasks._find_section_by_objective("short") is None
    assert dashboard_tasks._find_section_by_objective("") is None


def test_find_structured_request_by_id_strips_tap_prefix(monkeypatch) -> None:
    lines = [
        json.dumps({
            "event": "start",
            "request_id": "req-1",
            "role": "frontdoor",
            "ts": "2026-05-22T10:00:00+00:00",
            "ts_epoch": 1.0,
            "prompt": "hello",
        }),
        json.dumps({
            "event": "response",
            "request_id": "req-1",
            "role": "frontdoor",
            "ts": "2026-05-22T10:00:01+00:00",
            "ts_epoch": 2.0,
            "text": "world",
        }),
    ]
    monkeypatch.setattr(
        dashboard_tasks, "_grep_lines_reverse", lambda *a, **kw: "\n".join(lines)
    )
    monkeypatch.setattr(
        dashboard_tasks, "_read_tail", lambda *args, **kwargs: "\n".join(lines)
    )

    out = dashboard_tasks._find_structured_request_by_id("tap_req-1")

    assert out is not None
    assert out["source"] == "structured_tap"
    assert out["request_id"] == "req-1"
    assert out["prompt"] == "hello"
    assert out["response"] == "world"


def test_find_section_by_objective_matches_recent_first(monkeypatch) -> None:
    fake_sections = [
        {"prompt": "recent: solve fizzbuzz again", "response": "..."},
        {"prompt": "older: solve fizzbuzz now", "response": "..."},
    ]
    monkeypatch.setattr(dashboard_tasks, "_read_tail", lambda *a, **kw: "irrelevant")
    monkeypatch.setattr(dashboard_tasks, "_parse_inference_sections", lambda *a, **kw: fake_sections)
    out = dashboard_tasks._find_section_by_objective("solve fizzbuzz")
    assert out is not None
    assert out["prompt"].startswith("recent:")
    assert out["source"] == "legacy_inference_tap"
    assert out["legacy_source"] is True
    assert out["non_authoritative"] is True


def test_find_section_by_objective_role_filtered_no_global_fallback(monkeypatch) -> None:
    # Caller knows the task ran under frontdoor; the global pass would
    # otherwise return a syntactically-valid but cross-contaminated section
    # written by worker_explore (regression guard for the 2026-05-30
    # chat-83123001/chat-c7bf9580 interleaved-write incident).
    fake_sections = [
        {"role": "worker_explore", "prompt": "solve fizzbuzz now", "response": "wrong"},
    ]
    monkeypatch.setattr(dashboard_tasks, "_read_tail", lambda *a, **kw: "irrelevant")
    monkeypatch.setattr(dashboard_tasks, "_parse_inference_sections", lambda *a, **kw: fake_sections)
    out = dashboard_tasks._find_section_by_objective(
        "solve fizzbuzz", expected_role="frontdoor"
    )
    assert out is None


def test_find_section_by_objective_role_alias_canonicalizes_worker_explore(monkeypatch) -> None:
    fake_sections = [
        {"role": "worker_general", "prompt": "solve fizzbuzz now", "response": "ok"},
    ]
    monkeypatch.setattr(dashboard_tasks, "_read_tail", lambda *a, **kw: "irrelevant")
    monkeypatch.setattr(dashboard_tasks, "_parse_inference_sections", lambda *a, **kw: fake_sections)
    out = dashboard_tasks._find_section_by_objective(
        "solve fizzbuzz", expected_role="worker_explore"
    )
    assert out is not None
    assert out["role"] == "worker_general"
    assert out["legacy_source"] is True


def test_task_text_snapshot_marks_legacy_tap_source_non_authoritative() -> None:
    out = dashboard_tasks._task_text_snapshot(
        "chat-legacy",
        [],
        None,
        tap_section={
            "source": "legacy_inference_tap",
            "legacy_source": True,
            "non_authoritative": True,
            "timestamp": "2026-05-22T10:00:00+00:00",
            "role": "frontdoor",
            "prompt": "hello",
            "response": "world",
        },
    )

    assert "legacy best-effort/non-authoritative" in out


def test_find_structured_request_by_task_id_matches_chat_id(monkeypatch) -> None:
    # Each chat task has its own derived request_id; resolving by task_id
    # gives a deterministic mapping for chat-* dashboard task ids.
    lines = [
        json.dumps({
            "event": "start",
            "request_id": "chat-83123001:b763498c",
            "task_id": "chat-83123001",
            "role": "frontdoor",
            "ts": "2026-05-30T22:16:24+00:00",
            "ts_epoch": 1.0,
            "prompt": "count monkey collisions",
        }),
        json.dumps({
            "event": "response",
            "request_id": "chat-83123001:b763498c",
            "task_id": "chat-83123001",
            "role": "frontdoor",
            "ts": "2026-05-30T22:16:53+00:00",
            "ts_epoch": 2.0,
            "text": "the actual frontdoor answer",
        }),
        # Interleaved worker_explore request that previously confused the
        # plaintext fallback — verify the task_id lookup does not return it.
        json.dumps({
            "event": "start",
            "request_id": "chat-c7bf9580:aaaa1111",
            "task_id": "chat-c7bf9580",
            "role": "worker_explore",
            "ts": "2026-05-30T22:16:25+00:00",
            "ts_epoch": 1.5,
            "prompt": "count spaces in pirate's speak",
        }),
        json.dumps({
            "event": "response",
            "request_id": "chat-c7bf9580:aaaa1111",
            "task_id": "chat-c7bf9580",
            "role": "worker_explore",
            "ts": "2026-05-30T22:16:28+00:00",
            "ts_epoch": 1.6,
            "text": "5",
        }),
    ]
    # The resolver reverse-greps the tap file first (recovers a request of any age
    # from a multi-GB tap), then falls back to the small live tail. Stub both seams
    # so the matching logic is exercised against the fixture, not the real file.
    monkeypatch.setattr(
        dashboard_tasks, "_grep_lines_reverse", lambda *a, **kw: "\n".join(lines)
    )
    monkeypatch.setattr(
        dashboard_tasks, "_read_tail", lambda *args, **kwargs: "\n".join(lines)
    )

    out = dashboard_tasks._find_structured_request_by_task_id("chat-83123001")

    assert out is not None
    assert out["source"] == "structured_tap"
    assert out["task_id"] == "chat-83123001"
    assert out["role"] == "frontdoor"
    assert out["prompt"] == "count monkey collisions"
    assert out["response"] == "the actual frontdoor answer"


def test_find_structured_request_by_task_id_missing_returns_none(monkeypatch) -> None:
    monkeypatch.setattr(dashboard_tasks, "_grep_lines_reverse", lambda *a, **kw: "")
    monkeypatch.setattr(dashboard_tasks, "_read_tail", lambda *a, **kw: "")
    assert dashboard_tasks._find_structured_request_by_task_id("chat-83123001") is None
    assert dashboard_tasks._find_structured_request_by_task_id("") is None


# ----- dashboard_snapshot -----


def test_todays_progress_log_uses_iso_date(tmp_path) -> None:
    today_iso = date.today().isoformat()
    assert dashboard_snapshot.todays_progress_log(tmp_path).name == f"{today_iso}.jsonl"


def test_scan_recent_decisions_empty_when_missing(tmp_path) -> None:
    decisions, rolling, cumulative = dashboard_snapshot.scan_recent_decisions(tmp_path / "no.jsonl")
    assert decisions == []
    assert rolling == {}
    assert cumulative == {}


def test_scan_recent_decisions_counts_cumulative_vs_rolling(tmp_path) -> None:
    log = tmp_path / "p.jsonl"
    # Old decision (outside rolling window)
    old_ts = datetime.fromtimestamp(0, tz=timezone.utc).isoformat()
    new_ts = datetime.now(timezone.utc).isoformat()
    log.write_text(
        json.dumps({"event_type": "routing_decision", "timestamp": old_ts, "task_id": "a",
                    "data": {"decision_source": "classifier", "chosen_action": "x"}}) + "\n"
        + json.dumps({"event_type": "routing_decision", "timestamp": new_ts, "task_id": "b",
                      "data": {"decision_source": "classifier", "chosen_action": "y"}}) + "\n"
        + json.dumps({"event_type": "routing_decision", "timestamp": new_ts, "task_id": "c",
                      "data": {"decision_source": "rules", "chosen_action": "z"}}) + "\n"
    )
    decisions, rolling, cumulative = dashboard_snapshot.scan_recent_decisions(log, window_s=600)
    # All 3 go in cumulative; only 2 (new) in rolling
    assert cumulative == {"classifier": 2, "rules": 1}
    rolling_public = {k: v for k, v in rolling.items() if not k.startswith("_")}
    assert rolling_public == {"classifier": 1, "rules": 1}


def test_scan_orchestrator_tasks_separates_in_flight_from_completed(tmp_path) -> None:
    log = tmp_path / "p.jsonl"
    new_ts = datetime.now(timezone.utc).isoformat()
    log.write_text(
        json.dumps({"event_type": "task_started", "timestamp": new_ts, "task_id": "chat-1",
                    "data": {"objective": "live"}}) + "\n"
        + json.dumps({"event_type": "task_started", "timestamp": new_ts, "task_id": "chat-2",
                      "data": {"objective": "done"}}) + "\n"
        + json.dumps({"event_type": "task_completed", "timestamp": new_ts, "task_id": "chat-2",
                      "data": {}}) + "\n"
    )
    in_flight, completed = dashboard_snapshot.scan_orchestrator_tasks(log)
    assert [t["task_id"] for t in in_flight] == ["chat-1"]
    assert [t["task_id"] for t in completed] == ["chat-2"]


def test_scan_orchestrator_tasks_attaches_plan_review_to_terminal_outcome(tmp_path) -> None:
    log = tmp_path / "p.jsonl"
    ts = datetime.now(timezone.utc).isoformat()
    log.write_text(
        json.dumps({"event_type": "task_started", "timestamp": ts, "task_id": "chat-1",
                    "data": {"objective": "verify code"}}) + "\n"
        + json.dumps({"event_type": "plan_reviewed", "timestamp": ts, "task_id": "chat-1",
                      "agent_role": "architect_general",
                      "data": {"decision": "drop", "feedback": "Synthetic plan repeated prompt"}}) + "\n"
        + json.dumps({"event_type": "task_failed", "timestamp": ts, "task_id": "chat-1",
                      "data": {}}) + "\n"
    )
    _in_flight, completed = dashboard_snapshot.scan_orchestrator_tasks(log)
    assert completed[0]["plan_review_decision"] == "drop"
    assert completed[0]["plan_review_role"] == "architect_general"


def test_scan_orchestrator_tasks_skips_non_chat_task_ids(tmp_path) -> None:
    log = tmp_path / "p.jsonl"
    new_ts = datetime.now(timezone.utc).isoformat()
    log.write_text(
        json.dumps({"event_type": "task_started", "timestamp": new_ts, "task_id": "internal-99",
                    "data": {"objective": "skipped"}}) + "\n"
    )
    in_flight, completed = dashboard_snapshot.scan_orchestrator_tasks(log)
    assert in_flight == []
    assert completed == []


def _aged_ts(seconds_ago: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(seconds=seconds_ago)).isoformat()


def test_base_role_normalization() -> None:
    assert dashboard_topology.base_role("frontdoor.q2") == "frontdoor"
    assert dashboard_topology.base_role("embedder_3") == "embedder"
    assert dashboard_topology.base_role("worker_general.q0") == "worker_general"
    # Multi-word roles without a numeric instance suffix are left intact.
    assert dashboard_topology.base_role("architect_general") == "architect_general"
    assert dashboard_topology.base_role("ingest_long_context") == "ingest_long_context"
    assert dashboard_topology.base_role("") == ""


def test_role_color_canonicalizes_worker_aliases() -> None:
    assert dashboard_topology._role_color("worker_general") == "#10b981"
    assert dashboard_topology._role_color("worker_explore") == "#10b981"
    assert dashboard_topology._role_color("worker_explore.q1") == "#10b981"


def test_scan_orchestrator_tasks_role_aware_inflight_cutoff(tmp_path) -> None:
    """Slow roles keep a wider in-flight ceiling; default roles are truncated."""
    log = tmp_path / "p.jsonl"
    old = _aged_ts(600)  # past the 300s default, inside the 900s architect ceiling
    log.write_text(
        json.dumps({"event_type": "task_started", "timestamp": old, "task_id": "chat-slow",
                    "data": {"objective": "long reasoning"}}) + "\n"
        + json.dumps({"event_type": "routing_decision", "timestamp": old, "task_id": "chat-slow",
                      "data": {"chosen_action": "architect_general"}}) + "\n"
        + json.dumps({"event_type": "task_started", "timestamp": old, "task_id": "chat-fd",
                      "data": {"objective": "chat"}}) + "\n"
        + json.dumps({"event_type": "routing_decision", "timestamp": old, "task_id": "chat-fd",
                      "data": {"chosen_action": "frontdoor"}}) + "\n"
    )
    in_flight, _ = dashboard_snapshot.scan_orchestrator_tasks(log)
    ids = {t["task_id"] for t in in_flight}
    assert "chat-slow" in ids  # architect_general ceiling is 900s
    assert "chat-fd" not in ids  # frontdoor uses the 300s default


def test_scan_orchestrator_tasks_stamps_canonical_role(tmp_path) -> None:
    """In-flight tasks carry a base-normalised `role` for consistent grouping."""
    log = tmp_path / "p.jsonl"
    now = _aged_ts(2)
    log.write_text(
        json.dumps({"event_type": "task_started", "timestamp": now, "task_id": "chat-q",
                    "data": {"objective": "q"}}) + "\n"
        + json.dumps({"event_type": "routing_decision", "timestamp": now, "task_id": "chat-q",
                      "data": {"chosen_action": "frontdoor.q2"}}) + "\n"
    )
    in_flight, _ = dashboard_snapshot.scan_orchestrator_tasks(log)
    assert in_flight and in_flight[0]["role"] == "frontdoor"


def test_gate_inflight_drops_idle_orphans() -> None:
    """An old started-but-unterminated task with no busy slot is a restart-orphan."""
    orphan = [{"task_id": "chat-x", "age_s": 500.0, "role": "frontdoor"}]
    assert dashboard._gate_inflight_by_live_slots(orphan, {}) == []
    assert dashboard._gate_inflight_by_live_slots(orphan, {"frontdoor": 0}) == []


def test_gate_inflight_keeps_fresh_without_busy_slot() -> None:
    """A just-started task is kept even before its slot flips to processing."""
    fresh = [{"task_id": "chat-y", "age_s": 3.0, "role": "frontdoor"}]
    gated = dashboard._gate_inflight_by_live_slots(fresh, {})
    assert len(gated) == 1
    assert gated[0]["live_state"] == "pending"


def test_gate_inflight_keeps_live_long_task() -> None:
    """An old task is kept while its role's server reports a busy slot."""
    long_task = [{"task_id": "chat-z", "age_s": 500.0, "role": "ingest_long_context"}]
    gated = dashboard._gate_inflight_by_live_slots(long_task, {"ingest_long_context": 1})
    assert len(gated) == 1
    assert gated[0]["live_state"] == "decoding"


def test_gate_inflight_maps_alias_roles_to_topology_busy_slots() -> None:
    """Logical aliases sharing a physical pool should track that pool's live slots."""
    task = [{"task_id": "chat-coder", "age_s": 45.0, "role": "coder_escalation"}]
    gated = dashboard._gate_inflight_by_live_slots(
        task,
        {"frontdoor": 1},
        alias_to_topology_role={"coder_escalation": "frontdoor"},
    )

    assert len(gated) == 1
    assert gated[0]["topology_role"] == "frontdoor"
    assert gated[0]["live_state"] == "decoding"


def test_gate_inflight_canonicalizes_worker_explore_alias_to_general() -> None:
    task = [{"task_id": "chat-worker", "age_s": 45.0, "role": "worker_explore"}]
    gated = dashboard._gate_inflight_by_live_slots(task, {"worker_general": 1})

    assert len(gated) == 1
    assert gated[0]["topology_role"] == "worker_general"
    assert gated[0]["live_state"] == "decoding"


def test_gate_inflight_strips_route_modifier_before_slot_match() -> None:
    task = [{"task_id": "chat-frontdoor", "age_s": 45.0, "role": "frontdoor:direct"}]
    gated = dashboard._gate_inflight_by_live_slots(task, {"frontdoor": 1})

    assert len(gated) == 1
    assert gated[0]["topology_role"] == "frontdoor"
    assert gated[0]["live_state"] == "decoding"


def test_gate_inflight_caps_to_busy_slots() -> None:
    """With one busy slot, only the newest non-fresh candidate is shown."""
    many = [{"task_id": f"chat-{i}", "age_s": 100.0 + i * 10, "role": "frontdoor"} for i in range(3)]
    gated = dashboard._gate_inflight_by_live_slots(many, {"frontdoor": 1})
    assert [t["task_id"] for t in gated] == ["chat-0"]


def test_count_log_events_counts_pattern_matches(tmp_path) -> None:
    log = tmp_path / "app.log"
    log.write_text(
        "INFO: server started\n"
        "ERROR: connection refused\n"
        "WARN: retrying\n"
        "ERROR: timeout\n"
    )
    counts = dashboard_snapshot.count_log_events(
        log, {"errors": r"^ERROR:", "warns": r"^WARN:"}
    )
    assert counts == {"errors": 2, "warns": 1}


def test_count_log_events_missing_file_returns_zeros(tmp_path) -> None:
    counts = dashboard_snapshot.count_log_events(tmp_path / "no.log", {"foo": "bar"})
    assert counts == {"foo": 0}


def test_read_strategy_store_rows_reads_read_only_sqlite(tmp_path, monkeypatch) -> None:
    store_dir = tmp_path / "strategies"
    store_dir.mkdir()
    db_path = store_dir / "strategies.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE strategies (
            id TEXT PRIMARY KEY,
            description TEXT NOT NULL,
            insight TEXT NOT NULL,
            source_trial_id INTEGER,
            species TEXT NOT NULL,
            created_at TEXT NOT NULL,
            metadata_json TEXT DEFAULT '{}',
            entry_type TEXT DEFAULT 'raw',
            evidence_trial_ids TEXT DEFAULT '[]'
        )
        """
    )
    conn.execute(
        """
        INSERT INTO strategies (
            id, description, insight, source_trial_id, species, created_at,
            metadata_json, entry_type, evidence_trial_ids
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "row-1",
            "operator handoff row",
            "keep prompt graphs compact",
            12,
            "prompt_forge",
            "2026-06-28T00:00:00+00:00",
            json.dumps({"bind_status": "future", "seed_campaign": "graph-panel"}),
            "pattern",
            json.dumps([12]),
        ),
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(dashboard, "_STRATEGY_STORE_PATH", store_dir)

    rows = dashboard._read_strategy_store_rows()

    assert rows is not None
    assert len(rows) == 1
    row = rows[0]
    assert row["id"] == "row-1"
    assert row["entry_type"] == "pattern"
    assert row["metadata"]["bind_status"] == "future"
    assert row["evidence_trial_ids"] == [12]


def test_read_planner_hint_seed_rows_reads_yaml(tmp_path, monkeypatch) -> None:
    seed_path = tmp_path / "operator_seed_strategies.yaml"
    seed_path.write_text(
        """
- slug: graph-panel
  tranche: green
  species: prompt_forge
  entry_type: pattern
  title: Graph panel
  description: keep the dashboard graph small
  insight: Keep the dashboard panel compact.
  evidence_trial_ids: [12]
  source_handoff: dashboard-graph-panel
  seeded_reason: Keep the dashboard panel compact
  confidence: medium
  bind_status: future
  bind_identifiers: [graph_panel]
""".strip()
    )

    monkeypatch.setattr(dashboard, "_PLANNER_HINT_SEEDS_PATH", seed_path)

    rows = dashboard._read_planner_hint_seed_rows()

    assert rows is not None
    assert len(rows) == 1
    row = rows[0]
    assert row["id"] == "seed:graph-panel"
    assert row["planner_hint"] is True
    assert row["metadata"]["source_handoff"] == "dashboard-graph-panel"
    assert row["metadata"]["bind_identifiers"] == ["graph_panel"]
    assert row["evidence_trial_ids"] == [12]


def test_insight_graph_endpoint_merges_strategy_and_journal_rows(monkeypatch) -> None:
    journal_rows = [
        {
            "trial_id": 12,
            "timestamp": "2026-06-28T00:01:00+00:00",
            "species": "prompt_forge",
            "action_type": "prompt_mutation",
            "pareto_status": "frontier",
            "quality": 1.5,
            "speed": 42.0,
            "hypothesis": "Keep prompt graphs compact",
            "reasoning": "The operator hint panel should stay small.",
        },
        {
            "trial_id": 13,
            "timestamp": "2026-06-28T00:02:00+00:00",
            "species": "prompt_forge",
            "action_type": "prompt_mutation",
            "pareto_status": "dominated",
            "quality": 1.2,
            "speed": 39.0,
            "parent_trial": 12,
            "reasoning": "A longer prompt was slower.",
        },
    ]
    strategy_rows = [
        {
            "id": "journal-frontier-trial-12",
            "description": "prompt mutation",
            "insight": "q=1.5 s=42.0 mechanism=compact graph",
            "source_trial_id": 12,
            "species": "prompt_forge",
            "created_at": "2026-06-28T00:01:05+00:00",
            "metadata": {
                "generated_from": "journal_frontier",
                "journal_trial_id": 12,
            },
            "entry_type": "raw",
            "evidence_trial_ids": [12],
        },
        {
            "id": "opseed-graph-panel",
            "description": "Graph panel seed",
            "insight": "Show compact insight graphs in the dashboard",
            "source_trial_id": 12,
            "species": "prompt_forge",
            "created_at": "2026-06-28T00:03:00+00:00",
            "metadata": {
                "seed_campaign": "graph-panel",
                "source_handoff": "dashboard-graph-panel",
                "bind_status": "future",
                "seeded_by": "operator",
                "seeded_reason": "Keep the dashboard panel compact",
            },
            "entry_type": "pattern",
            "evidence_trial_ids": [12],
        },
        {
            "id": "opseed-graph-panel-live",
            "description": "Graph panel seed live",
            "insight": "Applied insight path",
            "source_trial_id": 13,
            "species": "prompt_forge",
            "created_at": "2026-06-28T00:04:00+00:00",
            "metadata": {
                "seed_campaign": "graph-panel",
                "source_handoff": "dashboard-graph-panel",
                "bind_status": "live",
                "seeded_by": "operator",
            },
            "entry_type": "convention",
            "evidence_trial_ids": [13],
        },
    ]
    monkeypatch.setattr(dashboard, "_read_autopilot_journal_rows", lambda path=None: journal_rows)
    monkeypatch.setattr(dashboard, "_read_strategy_store_rows", lambda path=None: strategy_rows)

    response = asyncio.run(dashboard.insight_graph(focus="campaign:graph-panel", depth=2))
    data = json.loads(response.body)

    assert data["available"] is True
    assert data["read_only"] is True
    assert data["focus"]["focus_kind"] == "campaign"
    assert data["focus"]["reason"] == "matched focus query"
    assert data["summary"]["state_counts"]["applied"] >= 1
    assert data["summary"]["state_counts"]["pending"] >= 1

    kinds = {node["kind"] for node in data["nodes"]}
    assert {"journal", "strategy", "campaign", "handoff"} <= kinds

    edge_kinds = {edge["kind"] for edge in data["edges"]}
    assert {"projection", "campaign", "handoff", "parent"} <= edge_kinds


def test_insight_graph_endpoint_falls_back_to_planner_hints(monkeypatch, tmp_path) -> None:
    seed_path = tmp_path / "operator_seed_strategies.yaml"
    seed_path.write_text(
        """
- slug: graph-panel
  tranche: green
  species: prompt_forge
  entry_type: pattern
  title: Graph panel
  description: keep the dashboard graph small
  insight: Keep the dashboard panel compact.
  evidence_trial_ids: []
  source_handoff: dashboard-graph-panel
  seeded_reason: Keep the dashboard panel compact
  confidence: medium
  bind_status: future
  bind_identifiers: [graph_panel]
""".strip()
    )

    monkeypatch.setattr(dashboard, "_PLANNER_HINT_SEEDS_PATH", seed_path)
    monkeypatch.setattr(dashboard, "_read_strategy_store_rows", lambda path=None: None)
    monkeypatch.setattr(dashboard, "_read_autopilot_journal_rows", lambda path=None: None)

    response = asyncio.run(dashboard.insight_graph(focus="dashboard-graph-panel", depth=1))
    data = json.loads(response.body)

    assert data["available"] is True
    assert data["source"]["graph_source"] == "planner_hint_seed"
    assert data["summary"]["strategy_rows"] == 0
    assert data["summary"]["planner_hint_rows"] == 1
    kinds = {node["kind"] for node in data["nodes"]}
    assert "planner_hint" in kinds


# ----- dashboard.py route module smoke test -----


def test_dashboard_module_router_still_exported() -> None:
    """The only external API is `router`; verify it survives the refactor."""
    from src.api.routes import dashboard
    assert dashboard.router is not None


def test_dashboard_module_html_loads_from_file() -> None:
    """The 918-line HTML block is now loaded from dashboard.html — verify length."""
    from src.api.routes import dashboard
    assert len(dashboard._DASHBOARD_HTML) > 40_000
    assert "<!doctype html>" in dashboard._DASHBOARD_HTML
    assert "</body></html>" in dashboard._DASHBOARD_HTML


def test_dashboard_html_surfaces_autopilot_phase_health() -> None:
    from src.api.routes import dashboard

    html = dashboard._DASHBOARD_HTML
    assert "autopilot_phase_health" in html
    assert "phase health" in html


def test_dashboard_html_surfaces_autopilot_outcome_health() -> None:
    from src.api.routes import dashboard

    html = dashboard._DASHBOARD_HTML
    assert "autopilot_outcome_progress" in html
    assert "_autopilotOutcomeProgressLabel" in html
    assert "autopilot-health-chip" in html


def test_dashboard_html_repaints_topology_after_region_lock_refresh() -> None:
    """Live inference/topology/CPU-lock panels should share one lock-cache frame."""
    from src.api.routes import dashboard

    html = dashboard._DASHBOARD_HTML
    assert "const overlayInflight = snapshotSeq != null" in html
    assert "updateTopologyInflight(overlayInflight, snapshotSeq);" in html
    assert "Single-writer coherence" in html
    assert "requestCoherentDashboardSnapshot('region_locks_refresh')" in html
    assert "t/s hist" in html
    assert "idle, not an active-holder signal" in html
    assert "last <span class=\"stat-stale\">${formatTopologyActivityAge(age)}</span>" in html


def test_dashboard_effective_journal_rows_fold_supersession_events() -> None:
    rows = [
        {
            "trial_id": 1,
            "timestamp": "2026-06-13T00:00:00+00:00",
            "bug_corrupted_by": "",
        },
        {
            "trial_id": 2,
            "timestamp": "2026-06-13T00:01:00+00:00",
            "bug_corrupted_by": "",
        },
        {
            "type": "supersession",
            "timestamp": "2026-06-13T00:02:00+00:00",
            "target_trial_ids": [2],
            "fields": {"bug_corrupted_by": "resource_contention"},
        },
    ]

    effective = dashboard._effective_journal_trial_rows(rows)

    assert [row["trial_id"] for row in effective] == [1, 2]
    assert effective[1]["bug_corrupted_by"] == "resource_contention"
    assert rows[1]["bug_corrupted_by"] == ""


def test_dashboard_baseline_promotion_summary_scopes_to_current_run() -> None:
    rows = [
        {
            "trial_id": 50,
            "timestamp": "2026-05-28T08:59:00+00:00",
        },
        {
            "type": "baseline_promotion",
            "source_trial_id": 50,
            "tier": 1,
            "previous_quality": 1.0,
            "new_quality": 1.1,
            "timestamp": "2026-05-28T08:59:30+00:00",
            "reason": "old run",
        },
        {
            "trial_id": 0,
            "timestamp": "2026-05-28T09:00:00+00:00",
        },
        {
            "trial_id": 1,
            "timestamp": "2026-05-28T09:01:00+00:00",
        },
        {
            "type": "baseline_promotion",
            "source_trial_id": 1,
            "tier": 1,
            "previous_quality": 1.1,
            "new_quality": 1.4,
            "timestamp": "2026-05-28T09:01:30+00:00",
            "reason": "current run",
            "proof": {
                "matrix_status": "ok",
                "speed_metric_mode": "aggregate_batch_tps",
            },
            "result_metrics": {
                "quality": 1.4,
                "speed": 42.0,
                "pareto_status": "frontier",
            },
        },
    ]

    summary = dashboard._baseline_promotion_summary(rows, current_run_only=True)

    assert summary["count"] == 1
    assert summary["latest_trial_id"] == 1
    assert summary["latest_promotion_trial_id"] == 1
    assert summary["trials_since_promotion"] == 0
    event = summary["recent"][0]
    assert event["source_trial_id"] == 1
    assert round(event["quality_delta"], 3) == 0.3
    assert event["matrix_status"] == "ok"
    assert event["result_speed"] == 42.0


def test_autopilot_progress_uses_superseded_journal_rows(
    tmp_path: Path,
    monkeypatch,
) -> None:
    state_path = tmp_path / "autopilot_state.json"
    journal_path = tmp_path / "autopilot_journal.jsonl"
    started_at = datetime.now(timezone.utc).timestamp() - 45
    state_path.write_text(json.dumps({
        "in_flight_trial": {
            "trial_id": 4,
            "started_at": started_at,
            "action": {"type": "seed_batch"},
        }
    }))
    rows = [
        {
            "trial_id": 0,
            "timestamp": "2026-06-13T00:00:00+00:00",
            "action_type": "seed_batch",
        },
        {
            "trial_id": 1,
            "timestamp": "2026-06-13T00:01:00+00:00",
            "action_type": "seed_batch",
        },
        {
            "trial_id": 2,
            "timestamp": "2026-06-13T00:02:00+00:00",
            "action_type": "seed_batch",
        },
        {
            "trial_id": 3,
            "timestamp": "2026-06-13T00:03:00+00:00",
            "action_type": "seed_batch",
        },
        {
            "type": "supersession",
            "timestamp": "2026-06-13T00:04:00+00:00",
            "target_trial_ids": [2],
            "fields": {"bug_corrupted_by": "resource_contention"},
        },
    ]
    journal_path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    monkeypatch.setattr(dashboard, "_AUTOPILOT_STATE_PATH", state_path)
    monkeypatch.setattr(dashboard, "_AUTOPILOT_JOURNAL_PATH", journal_path)

    response = asyncio.run(dashboard.autopilot_progress())
    payload = json.loads(response.body)

    assert payload["percent_source"] == "action_p50"
    assert payload["n_action_type_samples"] == 2


def test_autopilot_progress_surfaces_eval_label_from_log_tail(
    tmp_path: Path,
    monkeypatch,
) -> None:
    state_path = tmp_path / "autopilot_state.json"
    log_dir = tmp_path / "logs"
    log_path = log_dir / "autopilot_restart_1.log"
    started_at = datetime.now(timezone.utc).timestamp() - 90
    state_path.write_text(json.dumps({
        "in_flight_trial": {
            "trial_id": 9,
            "started_at": started_at,
            "action": {"type": "deep_eval"},
        }
    }))
    log_dir.mkdir()
    log_path.write_text("\n".join([
        "2026-07-04 19:14:09 [autopilot] INFO: Trial 9: {\"type\": \"deep_eval\"}",
        "2026-07-04 21:43:41 [autopilot.eval] INFO: T3 progress: 40/160 (58% correct)",
    ]) + "\n")
    monkeypatch.setattr(dashboard, "_AUTOPILOT_STATE_PATH", state_path)
    monkeypatch.setattr(dashboard, "_AUTOPILOT_LOG_DIR", log_dir)
    monkeypatch.setattr(dashboard, "_AUTOPILOT_TMP_LOG_DIR", tmp_path / "tmp")
    monkeypatch.setattr(dashboard, "AUTOPILOT_LOG", tmp_path / "missing.log")
    monkeypatch.setattr(dashboard, "_AUTOPILOT_JOURNAL_PATH", tmp_path / "missing.jsonl")

    response = asyncio.run(dashboard.autopilot_progress())
    payload = json.loads(response.body)

    assert payload["percent_source"] == "log_tail"
    assert payload["eval_label"] == "T3"
    assert payload["log_tail_progress"] == {"completed": 40, "total": 160}


def test_autopilot_progress_surfaces_baseline_promotion_summary(
    tmp_path: Path,
    monkeypatch,
) -> None:
    state_path = tmp_path / "autopilot_state.json"
    journal_path = tmp_path / "autopilot_journal.jsonl"
    journal_shard_path = tmp_path / "autopilot_journal_1.jsonl"
    started_at = datetime.now(timezone.utc).timestamp() - 90
    state_path.write_text(json.dumps({
        "in_flight_trial": {
            "trial_id": 4,
            "started_at": started_at,
            "action": {"type": "seed_batch"},
        }
    }))
    rows = [
        {
            "trial_id": 0,
            "timestamp": "2026-07-05T00:00:00+00:00",
            "action_type": "seed_batch",
        },
        {
            "trial_id": 1,
            "timestamp": "2026-07-05T00:01:00+00:00",
            "action_type": "seed_batch",
        },
        {
            "type": "baseline_promotion",
            "source_trial_id": 1,
            "tier": 1,
            "previous_quality": 1.0,
            "new_quality": 1.2,
            "timestamp": "2026-07-05T00:01:30+00:00",
            "reason": "kept",
        },
        {
            "trial_id": 2,
            "timestamp": "2026-07-05T00:02:00+00:00",
            "action_type": "seed_batch",
        },
    ]
    shard_rows = [
        {
            "trial_id": 4,
            "timestamp": "2026-07-05T00:03:00+00:00",
            "action_type": "seed_batch",
        },
    ]
    journal_path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    journal_shard_path.write_text("\n".join(json.dumps(row) for row in shard_rows) + "\n")
    monkeypatch.setattr(dashboard, "_AUTOPILOT_STATE_PATH", state_path)
    monkeypatch.setattr(dashboard, "_AUTOPILOT_JOURNAL_PATH", journal_path)

    response = asyncio.run(dashboard.autopilot_progress())
    payload = json.loads(response.body)

    assert payload["baseline_promotions"]["count"] == 1
    assert payload["baseline_promotions"]["latest_trial_id"] == 4
    assert payload["baseline_promotions"]["latest_promotion_trial_id"] == 1
    assert payload["baseline_promotions"]["trials_since_promotion"] == 3


def test_autopilot_progress_surfaces_outcome_kpis_and_current_code_health(
    tmp_path: Path,
    monkeypatch,
) -> None:
    state_path = tmp_path / "autopilot_state.json"
    journal_path = tmp_path / "autopilot_journal.jsonl"
    started_at = datetime.now(timezone.utc).timestamp() - 90
    state_path.write_text(json.dumps({
        "in_flight_trial": {
            "trial_id": 4,
            "started_at": started_at,
            "action": {"type": "seed_batch"},
        }
    }))
    rows = [
        {
            "trial_id": 1,
            "timestamp": "2026-07-05T00:00:00+00:00",
            "action_type": "seed_batch",
            "keep_revert_decision": "keep",
        },
        {
            "trial_id": 2,
            "timestamp": "2026-07-05T00:01:00+00:00",
            "action_type": "seed_batch",
            "keep_revert_decision": "revert",
            "deficiency_category": "regression",
            "failure_analysis": "VIOLATIONS: regression vs baseline",
        },
        {
            "trial_id": 3,
            "timestamp": "2026-07-05T00:02:00+00:00",
            "action_type": "seed_batch",
            "keep_revert_decision": "excluded",
            "eval_details": {
                "learning_exclusion": {"by": "mad_noise"},
            },
        },
        {
            "type": "baseline_promotion",
            "source_trial_id": 1,
            "tier": 1,
            "previous_quality": 1.0,
            "new_quality": 1.2,
            "timestamp": "2026-07-05T00:02:30+00:00",
            "reason": "kept",
        },
        {
            "trial_id": 4,
            "timestamp": "2026-07-05T00:03:00+00:00",
            "action_type": "seed_batch",
        },
    ]
    journal_path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    monkeypatch.setattr(dashboard, "_AUTOPILOT_STATE_PATH", state_path)
    monkeypatch.setattr(dashboard, "_AUTOPILOT_JOURNAL_PATH", journal_path)
    monkeypatch.setattr(
        dashboard,
        "_autopilot_current_code_health",
        lambda: {
            "ok": True,
            "status": "active",
            "code_stale": False,
            "require_current_code": True,
        },
    )

    response = asyncio.run(dashboard.autopilot_progress())
    payload = json.loads(response.body)

    assert payload["baseline_promotions"]["count"] == 1
    assert payload["outcome_kpis"]["keepable_rate"] == {
        "count": 1,
        "total": 3,
        "rate": 0.333,
    }
    assert payload["outcome_kpis"]["wasted_eval_rate"] == {
        "count": 1,
        "total": 3,
        "rate": 0.333,
    }
    assert payload["outcome_kpis"]["learning_excluded_rate"] == {
        "count": 1,
        "total": 3,
        "rate": 0.333,
    }
    assert payload["outcome_kpis"]["active_trial_count"] == 4
    assert payload["outcome_kpis"]["regression_per_active_trial"] == {
        "count": 1,
        "total": 4,
        "rate": 0.25,
    }
    assert payload["outcome_kpis"]["promotions_per_100_active_trials"] == {
        "count": 1,
        "total": 4,
        "per_100": 25.0,
    }
    assert payload["current_code_health"] == {
        "ok": True,
        "status": "active",
        "code_stale": False,
        "require_current_code": True,
    }


def test_autopilot_control_pause_and_resume_updates_state_latch(tmp_path: Path) -> None:
    state_path = tmp_path / "autopilot_state.json"
    audit_path = tmp_path / "autopilot_operator_control.jsonl"
    state_path.write_text(
        json.dumps(
            {
                "paused": False,
                "trial_counter": 12,
                "_dispatch_deficiency": "skip_action_loop",
                "consecutive_skip_actions": 3,
                "last_invalid_action": {"type": "skip"},
                "last_invalid_reason": "loop",
                "last_invalid_status": "rejected",
                "consecutive_meta_actions": 2,
                "_meta_halt_reason": "operator review",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    paused = dashboard._apply_autopilot_control_action(
        action="pause",
        note="operator pause",
        state_path=state_path,
        audit_path=audit_path,
    )

    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert paused["status"] == "ok"
    assert paused["paused_pre"] is False
    assert paused["paused"] is True
    assert state["paused"] is True
    assert state["pause_reason"] == "operator pause"

    resumed = dashboard._apply_autopilot_control_action(
        action="resume",
        note="operator resume",
        state_path=state_path,
        audit_path=audit_path,
    )

    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert resumed["status"] == "ok"
    assert resumed["paused_pre"] is True
    assert resumed["paused"] is False
    assert state["paused"] is False
    assert "pause_reason" not in state
    assert "_dispatch_deficiency" not in state
    assert "_meta_halt_reason" not in state
    assert state["consecutive_skip_actions"] == 0
    assert state["last_invalid_action"] is None
    assert state["last_invalid_reason"] is None
    assert state["last_invalid_status"] is None
    assert state["consecutive_meta_actions"] == 0

    audit_rows = [
        json.loads(line)
        for line in audit_path.read_text(encoding="utf-8").splitlines()
    ]
    assert [row["action"] for row in audit_rows] == ["pause", "resume"]
    assert [row["paused_post"] for row in audit_rows] == [True, False]


def test_autopilot_progress_leaves_outcome_kpis_unknown_without_source_data(
    tmp_path: Path,
    monkeypatch,
) -> None:
    state_path = tmp_path / "autopilot_state.json"
    journal_path = tmp_path / "autopilot_journal.jsonl"
    started_at = datetime.now(timezone.utc).timestamp() - 45
    state_path.write_text(json.dumps({
        "in_flight_trial": {
            "trial_id": 8,
            "started_at": started_at,
            "action": {"type": "seed_batch"},
        }
    }))
    journal_path.write_text("\n".join(json.dumps({
        "trial_id": trial_id,
        "timestamp": f"2026-07-05T00:0{trial_id}:00+00:00",
        "action_type": "seed_batch",
    }) for trial_id in [1, 2, 3]) + "\n")
    monkeypatch.setattr(dashboard, "_AUTOPILOT_STATE_PATH", state_path)
    monkeypatch.setattr(dashboard, "_AUTOPILOT_JOURNAL_PATH", journal_path)
    monkeypatch.setattr(dashboard, "_autopilot_current_code_health", lambda: None)

    response = asyncio.run(dashboard.autopilot_progress())
    payload = json.loads(response.body)

    assert payload["outcome_kpis"]["keepable_rate"] == {
        "count": 0,
        "total": 0,
        "rate": None,
    }
    assert payload["outcome_kpis"]["wasted_eval_rate"] == {
        "count": 0,
        "total": 0,
        "rate": None,
    }
    assert payload["outcome_kpis"]["learning_excluded_rate"] == {
        "count": 0,
        "total": 0,
        "rate": None,
    }
    assert payload["outcome_kpis"]["active_trial_count"] == 3
    assert payload["outcome_kpis"]["regression_per_active_trial"] == {
        "count": 0,
        "total": 3,
        "rate": 0.0,
    }
    assert payload["outcome_kpis"]["promotions_per_100_active_trials"] == {
        "count": 0,
        "total": 3,
        "per_100": 0.0,
    }
    assert payload["current_code_health"] is None


def test_autopilot_progress_prefers_active_autopilot_log_over_stale_restart_log(
    tmp_path: Path,
    monkeypatch,
) -> None:
    state_path = tmp_path / "autopilot_state.json"
    log_dir = tmp_path / "logs"
    restart_log = log_dir / "autopilot_restart_1.log"
    active_log = log_dir / "autopilot.log"
    started_at = datetime.now(timezone.utc).timestamp() - 90
    state_path.write_text(json.dumps({
        "in_flight_trial": {
            "trial_id": 1156,
            "started_at": started_at,
            "action": {"type": "deep_eval", "tier": 3},
        }
    }))
    log_dir.mkdir()
    restart_log.write_text("\n".join([
        "2026-07-05 06:24:34 [autopilot.eval] INFO: T1 progress: 30/38 (67% correct)",
    ]) + "\n")
    active_log.write_text("\n".join([
        "2026-07-05 06:45:34 [autopilot] INFO: Trial 1156: {\"type\": \"deep_eval\", \"tier\": 3}",
        "2026-07-05 07:25:24 [autopilot.eval] INFO: T3 progress: 100/160 (57% correct)",
    ]) + "\n")
    now = datetime.now(timezone.utc).timestamp()
    os.utime(restart_log, (now - 100, now - 100))
    os.utime(active_log, (now, now))
    monkeypatch.setattr(dashboard, "_AUTOPILOT_STATE_PATH", state_path)
    monkeypatch.setattr(dashboard, "_AUTOPILOT_LOG_DIR", log_dir)
    monkeypatch.setattr(dashboard, "_AUTOPILOT_TMP_LOG_DIR", tmp_path / "tmp")
    monkeypatch.setattr(dashboard, "AUTOPILOT_LOG", active_log)
    monkeypatch.setattr(dashboard, "_AUTOPILOT_JOURNAL_PATH", tmp_path / "missing.jsonl")

    response = asyncio.run(dashboard.autopilot_progress())
    payload = json.loads(response.body)

    assert payload["percent_source"] == "log_tail"
    assert payload["eval_label"] == "T3"
    assert payload["log_tail_progress"] == {"completed": 100, "total": 160}


def test_gepa_status_uses_superseded_journal_rows(
    tmp_path: Path,
    monkeypatch,
) -> None:
    log_path = tmp_path / "autopilot.log"
    journal_path = tmp_path / "autopilot_journal.jsonl"
    log_path.write_text("2026-06-13 00:00:00,000 GEPA: Trial active\n")
    rows = [
        {
            "trial_id": 1,
            "timestamp": "2026-06-13T00:00:00+00:00",
            "species": "prompt_forge",
            "quality": 1.0,
            "speed": 10.0,
            "cost": 0.5,
            "reliability": 1.0,
            "pareto_status": "frontier",
        },
        {
            "trial_id": 2,
            "timestamp": "2026-06-13T00:01:00+00:00",
            "species": "prompt_forge",
            "quality": 9.0,
            "speed": 99.0,
            "cost": 0.5,
            "reliability": 1.0,
            "pareto_status": "frontier",
        },
        {
            "type": "supersession",
            "timestamp": "2026-06-13T00:02:00+00:00",
            "target_trial_ids": [2],
            "fields": {"bug_corrupted_by": "resource_contention"},
        },
    ]
    journal_path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    monkeypatch.setattr(dashboard, "AUTOPILOT_LOG", log_path)
    monkeypatch.setattr(dashboard, "_AUTOPILOT_JOURNAL_PATH", journal_path)

    response = asyncio.run(dashboard.gepa_status())
    payload = json.loads(response.body)

    # Superseded/corrupted trials are no longer dropped from the trajectory list —
    # they ride along tagged so a mid-trial kill stays visible. The supersession
    # fold must still be APPLIED, so trial 2 carries the corruption tag while the
    # clean trial 1 does not.
    by_trial = {t["trial_id"]: t for t in payload["recent_trials"]}
    assert set(by_trial) == {1, 2}
    assert by_trial[1]["bug_corrupted_by"] is None
    assert by_trial[2]["bug_corrupted_by"] == "resource_contention"
    assert by_trial[2]["quarantine_label"] == "corrupted"


def test_gepa_status_recent_trials_labels_seq_refuted_without_corruption(
    tmp_path: Path, monkeypatch
) -> None:
    log_path = tmp_path / "autopilot.log"
    journal_path = tmp_path / "autopilot_journal.jsonl"
    log_path.write_text("2026-07-08 00:00:00,000 GEPA: Trial active\n")
    rows = [
        {
            "trial_id": 10,
            "timestamp": "2026-07-08T00:00:00+00:00",
            "species": "seeder",
            "action_type": "seed_batch",
            "tier": 1,
            "quality": 2.0,
            "speed": 25.0,
            "cost": 0.5,
            "reliability": 0.9,
            "pareto_status": "dominated",
            "keep_revert_decision": "excluded",
            "eval_details": {
                "learning_exclusion": {
                    "by": "seq_refuted",
                    "reason": "sequential e-process refuted the candidate improvement",
                }
            },
        }
    ]
    journal_path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    monkeypatch.setattr(dashboard, "AUTOPILOT_LOG", log_path)
    monkeypatch.setattr(dashboard, "_AUTOPILOT_JOURNAL_PATH", journal_path)

    response = asyncio.run(dashboard.gepa_status())
    payload = json.loads(response.body)

    row = payload["recent_trials"][0]
    assert row["bug_corrupted_by"] is None
    assert row["quarantine_label"] is None
    assert row["learning_excluded_by"] == "seq_refuted"
    assert row["keep_revert_decision"] == "excluded"
    assert row["exclusion_label"] == "seq-refuted"


def test_gepa_status_recent_trials_carry_tier(tmp_path: Path, monkeypatch) -> None:
    """Trajectory rows must expose `tier` so the dashboard can label per-tier
    quality (a by-design-low T3 row must not read as a T1 regression)."""
    log_path = tmp_path / "autopilot.log"
    journal_path = tmp_path / "autopilot_journal.jsonl"
    log_path.write_text("2026-07-04 00:00:00,000 GEPA: Trial active\n")
    rows = [
        {
            "trial_id": 30, "tier": 1, "timestamp": "2026-07-04T00:00:00+00:00",
            "species": "prompt_forge", "quality": 1.8, "speed": 30.0,
            "cost": 0.5, "reliability": 1.0, "pareto_status": "frontier",
            "eval_details": {"details": {
                "question_tier_mix": {"1": 17, "2": 17, "3": 16},
                "tier_mix_provenance": {
                    "tier_mix_policy": "equal_thirds_v1",
                    "tier_mix_targets": {"1": 17, "2": 17, "3": 16},
                    "drawn_n": 50,
                },
                "n_scored": 49,
            }},
        },
        {
            "trial_id": 31, "tier": 3, "timestamp": "2026-07-04T00:01:00+00:00",
            "species": "prompt_forge", "quality": 1.2, "speed": 45.0,
            "cost": 0.5, "reliability": 1.0, "pareto_status": "frontier",
        },
    ]
    journal_path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    monkeypatch.setattr(dashboard, "AUTOPILOT_LOG", log_path)
    monkeypatch.setattr(dashboard, "_AUTOPILOT_JOURNAL_PATH", journal_path)

    response = asyncio.run(dashboard.gepa_status())
    payload = json.loads(response.body)

    tier_by_trial = {t["trial_id"]: t["tier"] for t in payload["recent_trials"]}
    assert tier_by_trial == {30: 1, 31: 3}
    by_trial = {t["trial_id"]: t for t in payload["recent_trials"]}
    assert by_trial[30]["decision_question_mix"]["targets"] == {
        "1": 17, "2": 17, "3": 16,
    }
    assert by_trial[30]["decision_question_mix"]["scored_n"] == 49
    assert by_trial[31]["decision_question_mix"] is None
    assert payload["current_decision_question_mix"] == by_trial[30]["decision_question_mix"]


def test_gepa_status_recent_trials_carry_real_suite_metric(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Real-suite rows should be visible in the GEPA trajectory panel."""
    log_path = tmp_path / "autopilot.log"
    journal_path = tmp_path / "autopilot_journal.jsonl"
    log_path.write_text("2026-07-05 00:00:00,000 Trial 40 complete\n")
    rows = [
        {
            "trial_id": 40,
            "tier": 3,
            "timestamp": "2026-07-05T00:00:00+00:00",
            "species": "structural_lab",
            "quality": 1.2,
            "speed": 45.0,
            "cost": 0.5,
            "reliability": 1.0,
            "pareto_status": "dominated",
            "eval_details": {
                "per_suite_quality": {"real_suite_v1": 1.5},
                "details": {"per_suite_counts": {"real_suite_v1": 4}},
                "question_results": [
                    {"suite": "real_suite_v1", "qid": "a", "correct": True},
                    {"suite": "real_suite_v1", "qid": "b", "correct": False},
                ],
            },
        }
    ]
    journal_path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    monkeypatch.setattr(dashboard, "AUTOPILOT_LOG", log_path)
    monkeypatch.setattr(dashboard, "_AUTOPILOT_JOURNAL_PATH", journal_path)

    response = asyncio.run(dashboard.gepa_status())
    payload = json.loads(response.body)

    metric = payload["recent_trials"][0]["real_suite_v1"]
    assert metric == {
        "suite": "real_suite_v1",
        "quality": 1.5,
        "count": 4,
        "correct": 1,
    }


def test_shape_pareto_entry_carries_real_suite_metric() -> None:
    shaped = dashboard._shape_pareto_entry(
        {
            "trial_id": 50,
            "objectives": [1.0, 20.0, -0.2, 1.0],
            "eval_details": {
                "details": {"per_suite_counts": {"real_suite_v1": 2}},
                "question_results": [
                    {"suite": "real_suite_v1", "correct": True},
                    {"suite": "real_suite_v1", "correct": True},
                ],
            },
        }
    )

    assert shaped["real_suite_v1"] == {
        "suite": "real_suite_v1",
        "quality": 3.0,
        "count": 2,
        "correct": 2,
    }


def test_pareto_endpoint_prefers_current_journal_run_over_old_rows_and_state(
    tmp_path: Path, monkeypatch
) -> None:
    """Stale pre-reset journal rows and stale state should not pollute plots."""
    state_path = tmp_path / "autopilot_state.json"
    journal_path = tmp_path / "autopilot_journal.jsonl"
    session_start = datetime(2026, 5, 28, 9, 0, tzinfo=timezone.utc)
    state_path.write_text(json.dumps({
        "autopilot_fleet_started_at": session_start.timestamp(),
        "trial_counter": 12,
        "pareto_archive": {
            "frontier": [{"trial_id": 99, "objectives": [9.0, 9.0, 0.0, 0.0]}],
            "all_entries": [{"trial_id": 99, "objectives": [9.0, 9.0, 0.0, 0.0]}],
            "hypervolume_history": [[99, 999.0]],
        },
    }))
    rows = [
        {
            "trial_id": 568,
            "timestamp": "2026-05-28T08:59:00+00:00",
            "species": "old",
            "quality": 10.0,
            "speed": 100.0,
            "cost": 0.5,
            "reliability": 1.0,
        },
        {
            "trial_id": 0,
            "timestamp": "2026-05-28T09:00:00+00:00",
            "species": "reset",
            "quality": 0.8,
            "speed": 7.0,
            "cost": 0.5,
            "reliability": 0.7,
        },
        {
            "trial_id": 10,
            "timestamp": "2026-05-28T09:01:00+00:00",
            "species": "seeder",
            "quality": 1.0,
            "speed": 10.0,
            "cost": 0.5,
            "reliability": 0.8,
        },
        {
            "trial_id": 11,
            "timestamp": "2026-05-28T09:02:00+00:00",
            "species": "seeder",
            "quality": 0.5,
            "speed": 5.0,
            "cost": 0.5,
            "reliability": 0.7,
        },
        {
            "trial_id": 12,
            "timestamp": "2026-05-28T09:03:00+00:00",
            "species": "numeric_swarm",
            "quality": 1.2,
            "speed": 9.0,
            "cost": 0.5,
            "reliability": 0.9,
        },
        {
            "trial_id": 13,
            "timestamp": "2026-05-28T09:04:00+00:00",
            "species": "corrupt",
            "quality": 20.0,
            "speed": 200.0,
            "cost": 0.5,
            "reliability": 1.0,
            "bug_corrupted_by": "test",
        },
        {
            "type": "baseline_promotion",
            "source_trial_id": 12,
            "tier": 1,
            "previous_quality": 1.0,
            "new_quality": 1.2,
            "timestamp": "2026-05-28T09:04:30+00:00",
            "reason": "accepted",
            "proof": {"matrix_status": "ok"},
            "result_metrics": {
                "quality": 1.2,
                "speed": 9.0,
                "pareto_status": "frontier",
            },
        },
    ]
    journal_path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    monkeypatch.setattr(dashboard, "_AUTOPILOT_STATE_PATH", state_path)
    monkeypatch.setattr(dashboard, "_AUTOPILOT_JOURNAL_PATH", journal_path)

    response = asyncio.run(dashboard.pareto())
    payload = json.loads(response.body)

    assert payload["source"] == "journal_current_run"
    assert payload["legacy_state_archive_warning"] is None
    assert payload["archive_authority"] == {
        "source": "journal_current_run",
        "journal_rows_available": 7,
        "state_archive_present": True,
        "state_error": None,
        "using_legacy_state_archive": False,
    }
    assert payload["totals"] == {
        "frontier_size": 2,
        "all_entries": 4,
        "hv_points": 4,
    }
    assert {point["trial_id"] for point in payload["frontier"]} == {10, 12}
    assert [point["trial_id"] for point in payload["dominated"]] == [11, 0]
    assert payload["hypervolume_history"][-1][0] == 12
    assert payload["journal_run_start_trial_id"] == 0
    assert payload["baseline_promotions"]["count"] == 1
    assert payload["baseline_promotions"]["recent"][0]["source_trial_id"] == 12


def test_pareto_endpoint_uses_current_run_when_restart_marker_is_newer(
    tmp_path: Path, monkeypatch
) -> None:
    """A new run marker just after the last row must not collapse the plots."""
    state_path = tmp_path / "autopilot_state.json"
    journal_path = tmp_path / "autopilot_journal.jsonl"
    session_start = datetime(2026, 5, 28, 9, 43, 33, 596323, tzinfo=timezone.utc)
    state_path.write_text(json.dumps({
        "autopilot_fleet_started_at": session_start.timestamp(),
        "trial_counter": 73,
        "pareto_archive": {
            "frontier": [{"trial_id": 99, "objectives": [9.0, 9.0, 0.0, 0.0]}],
            "all_entries": [{"trial_id": 99, "objectives": [9.0, 9.0, 0.0, 0.0]}],
            "hypervolume_history": [[99, 999.0]],
        },
    }))
    rows = [
        {
            "trial_id": 72,
            "timestamp": "2026-05-28T09:05:40.024205+00:00",
            "species": "seeder",
            "quality": 1.2,
            "speed": 28.0,
            "cost": 0.5,
            "reliability": 0.8,
        },
        {
            "trial_id": 73,
            "timestamp": "2026-05-28T09:43:33.596165+00:00",
            "species": "(killed)",
            "quality": 0.0,
            "speed": 0.0,
            "cost": 0.0,
            "reliability": 0.0,
            "bug_corrupted_by": "autopilot_killed_mid_trial",
        },
    ]
    journal_path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    monkeypatch.setattr(dashboard, "_AUTOPILOT_STATE_PATH", state_path)
    monkeypatch.setattr(dashboard, "_AUTOPILOT_JOURNAL_PATH", journal_path)

    response = asyncio.run(dashboard.pareto())
    payload = json.loads(response.body)

    assert payload["source"] == "journal_current_run"
    assert payload["totals"] == {
        "frontier_size": 1,
        "all_entries": 1,
        "hv_points": 1,
    }
    assert payload["frontier"][0]["trial_id"] == 72
    assert payload["hypervolume_history"][-1][0] == 72


def test_pareto_endpoint_marks_legacy_state_archive_fallback(
    tmp_path: Path, monkeypatch
) -> None:
    """State-cache fallback should be visible enough to block decision use."""
    state_path = tmp_path / "autopilot_state.json"
    journal_path = tmp_path / "autopilot_journal.jsonl"
    state_path.write_text(json.dumps({
        "trial_counter": 5,
        "pareto_archive": {
            "frontier": [{"trial_id": 5, "objectives": [1.0, 2.0, -0.1, 0.9]}],
            "all_entries": [{"trial_id": 5, "objectives": [1.0, 2.0, -0.1, 0.9]}],
            "hypervolume_history": [[5, 2.0]],
        },
    }))
    journal_path.write_text("")
    monkeypatch.setattr(dashboard, "_AUTOPILOT_STATE_PATH", state_path)
    monkeypatch.setattr(dashboard, "_AUTOPILOT_JOURNAL_PATH", journal_path)

    response = asyncio.run(dashboard.pareto())
    payload = json.loads(response.body)

    assert payload["source"] == "state_archive"
    assert payload["legacy_state_archive_warning"] == {
        "state_archive_present": True,
        "journal_rows_available": 0,
        "detail": (
            "dashboard fell back to autopilot_state.json:pareto_archive; "
            "treat this as a legacy state-cache view and run strict archive "
            "authority validation before using it for decisions"
        ),
    }
    assert payload["archive_authority"] == {
        "source": "state_archive",
        "journal_rows_available": 0,
        "state_archive_present": True,
        "state_error": None,
        "using_legacy_state_archive": True,
    }


# ----- _poll_all_slots fan-out deadline -----


def test_poll_all_slots_deadline_bounds_hung_ports(monkeypatch) -> None:
    """A hung /slots endpoint must cost at most the fan-out deadline, not its
    own per-request budget times the port count — the snapshot serve path
    feeds the topology/region-locks/live-tap panels."""
    monkeypatch.setattr(
        dashboard, "_discover_llama_ports",
        lambda: {8070: "frontdoor", 8071: "hung_a", 8072: "hung_b"},
    )

    async def fake_poll(client, port):
        if port == 8070:
            return [{"id": 0, "is_processing": False}]
        await asyncio.sleep(30)
        return [{"id": 99}]

    monkeypatch.setattr(dashboard, "_poll_slot", fake_poll)
    monkeypatch.setattr(dashboard, "_SLOTS_FANOUT_DEADLINE_S", 0.3)

    started = time.time()
    slots_by_port, meta = asyncio.run(dashboard._poll_all_slots())
    elapsed = time.time() - started

    assert elapsed < 2.0
    assert slots_by_port[8070] == [{"id": 0, "is_processing": False}]
    assert slots_by_port[8071] == []
    assert slots_by_port[8072] == []
    assert meta["ports"] == 3
    assert meta["answered"] == 1
    assert meta["timed_out"] == 2
    assert meta["duration_s"] >= 0.3


def test_poll_all_slots_empty_ports_meta() -> None:
    from unittest.mock import patch

    with patch.object(dashboard, "_discover_llama_ports", lambda: {}):
        slots_by_port, meta = asyncio.run(dashboard._poll_all_slots())
    assert slots_by_port == {}
    assert meta == {
        "ports": 0,
        "answered": 0,
        "timed_out": 0,
        "duration_s": 0.0,
        # `unanswered_ports` names the ports that could not be measured, so a
        # caller can mark their roles' occupancy as a lower bound instead of
        # letting an unmeasured port read as an idle one.
        "unanswered_ports": [],
    }


# ----- region-locks cache + tap-enrich fail-open (serve-path decoupling) -----


def test_region_locks_cached_ttl_and_fail_open(monkeypatch) -> None:
    calls = {"n": 0}

    def fake_payload(_numa_mode=None):
        calls["n"] += 1
        if calls["n"] >= 3:
            raise RuntimeError("proc scan exploded")
        return {"entries": [{"role": "frontdoor"}], "by_role": {"frontdoor": {}}}

    monkeypatch.setattr(dashboard, "_region_locks_payload", fake_payload)
    monkeypatch.setitem(dashboard._REGION_LOCKS_CACHE, "ts", 0.0)
    monkeypatch.setitem(dashboard._REGION_LOCKS_CACHE, "payload", None)

    first = dashboard._region_locks_cached()
    second = dashboard._region_locks_cached()  # inside TTL → no rebuild
    assert calls["n"] == 1
    assert first is second

    # Expire the TTL twice: second rebuild succeeds, third raises → the cached
    # payload is served marked stale instead of raising into the serve path.
    dashboard._REGION_LOCKS_CACHE["ts"] = 0.0
    dashboard._region_locks_cached()
    assert calls["n"] == 2
    dashboard._REGION_LOCKS_CACHE["ts"] = 0.0
    failed = dashboard._region_locks_cached()
    assert calls["n"] == 3
    assert failed["stale_cache"] is True
    assert "proc scan exploded" in failed["error"]
    assert failed["entries"] == [{"role": "frontdoor"}]


def test_snapshot_uses_fresh_region_lock_scan(monkeypatch) -> None:
    fresh = {"generated_at": 123.0, "entries": [{"role": "fresh"}], "by_role": {"fresh": {}}}
    activity = {"per_role": {"frontdoor": {"n_recent": 1}}, "window_s": 600.0, "now": 456.0}

    async def fake_poll_all_slots():
        return {}, {"ports": 0, "answered": 0, "timed_out": 0, "duration_s": 0.0}

    def fake_cached():
        raise AssertionError("snapshot must not use the cached region-lock payload")

    monkeypatch.setattr(dashboard, "_poll_all_slots", fake_poll_all_slots)
    monkeypatch.setattr(dashboard, "_todays_progress_log", lambda: Path("/does/not/exist"))
    monkeypatch.setattr(dashboard, "_scan_recent_decisions", lambda _path: ([], {}, {}))
    monkeypatch.setattr(dashboard, "_count_log_events", lambda *_a, **_k: {})
    monkeypatch.setattr(dashboard, "_discover_llama_ports", lambda: {})
    monkeypatch.setattr(
        dashboard, "_gate_inflight_by_live_slots", lambda in_flight, *_a, **_k: in_flight
    )
    monkeypatch.setattr(dashboard, "_region_locks_payload", lambda _numa_mode=None: fresh)
    monkeypatch.setattr(dashboard, "_region_locks_cached", fake_cached)
    monkeypatch.setattr(dashboard, "_structured_tap_requests_for_dashboard", lambda **_k: [])
    monkeypatch.setattr(dashboard, "_topology_activity_payload", lambda **_k: activity)
    monkeypatch.setattr(dashboard, "_topology_nodes_cached", lambda _numa_mode=None: [])
    monkeypatch.setattr(dashboard_topology, "read_runtime_stack_numa_mode", lambda: None)

    response = asyncio.run(dashboard._snapshot_impl())
    payload = json.loads(response.body)

    assert payload["region_locks"]["entries"] == fresh["entries"]
    assert payload["region_locks"]["live_frame"]["status"] == "unknown"
    assert payload["frame_id"] == payload["region_locks"]["frame_id"]
    assert payload["topology_activity"] == activity
    assert payload["display_activity"] == {}
    # active_stack_numa_mode() now defaults to "both" (env unset) so the dashboard
    # reflects the running full + quarter instances.
    assert payload["stack_numa_mode"] == "both"
    assert payload["topology"]["stack_numa_mode"] == "both"


def _live_region_payload(role: str, tokens: list[str]) -> dict[str, object]:
    entries = [
        {
            "token": token,
            "role": role,
            "instance_idx": 0,
            "capacity": 4,
            "shared": True,
            "request_tag": "eval-batch",
        }
        for token in tokens
    ]
    return {
        "by_role": {role: {}},
        "occupancy": {"entries": entries},
        "coherence": {"status": "coherent"},
        "global_lock": {"holder_pids": []},
        "display_matrix": {
            "rows": [
                {
                    "role": role,
                    "cells": [
                        {
                            "state": "active",
                            "shape": "full",
                            "active": len(entries),
                            "capacity": 4,
                            "label": f"⚡ {len(entries)}/4",
                        }
                    ],
                }
            ],
        },
    }


def test_live_window_retries_request_handoff_between_slots_and_lease(monkeypatch) -> None:
    observations = iter(
        (
            _live_region_payload("frontdoor", ["fd-1"]),
            _live_region_payload("worker_general", ["wg-1", "wg-2"]),
            _live_region_payload("worker_general", ["wg-1", "wg-2"]),
            _live_region_payload("worker_general", ["wg-1", "wg-2"]),
        )
    )
    polls = 0

    async def fake_poll():
        nonlocal polls
        polls += 1
        return {8072: [{"is_processing": True}, {"is_processing": True}]}, {
            "ports": 1,
            "answered": 1,
            "timed_out": 0,
            "duration_s": 0.01,
            "unanswered_ports": [],
        }

    monkeypatch.setattr(dashboard, "_region_locks_payload", lambda _mode: next(observations))
    monkeypatch.setattr(dashboard, "_poll_all_slots", fake_poll)

    sample = asyncio.run(dashboard._sample_slots_with_placement_window("both"))

    assert polls == 2
    assert sample["attempt"] == 2
    assert sample["placement_stable"] is True
    assert dashboard._placement_frame_signature(sample["placement_after"])[0][0][1] == (
        "worker_general"
    )


def test_live_window_does_not_retry_unavailable_slots_into_false_certainty(monkeypatch) -> None:
    region = _live_region_payload("frontdoor", ["fd-1"])
    region_reads = 0
    polls = 0

    def fake_region(_mode):
        nonlocal region_reads
        region_reads += 1
        return region

    async def fake_poll():
        nonlocal polls
        polls += 1
        return {8070: []}, {
            "ports": 1,
            "answered": 0,
            "timed_out": 1,
            "duration_s": 8.0,
            "unanswered_ports": [8070],
        }

    monkeypatch.setattr(dashboard, "_region_locks_payload", fake_region)
    monkeypatch.setattr(dashboard, "_poll_all_slots", fake_poll)

    sample = asyncio.run(dashboard._sample_slots_with_placement_window("both"))

    assert region_reads == 2
    assert polls == 1
    assert sample["attempt"] == 1
    assert sample["placement_stable"] is True
    assert sample["slots_poll_meta"]["unanswered_ports"] == [8070]


def test_live_window_exhaustion_remains_torn(monkeypatch) -> None:
    observations = iter(
        (
            _live_region_payload("frontdoor", ["fd-1"]),
            _live_region_payload("worker_general", ["wg-1"]),
            _live_region_payload("worker_general", ["wg-1"]),
            _live_region_payload("frontdoor", ["fd-2"]),
        )
    )

    async def fake_poll():
        return {8070: [{"is_processing": True}]}, {
            "ports": 1,
            "answered": 1,
            "timed_out": 0,
            "duration_s": 0.1,
            "unanswered_ports": [],
        }

    monkeypatch.setattr(dashboard, "_region_locks_payload", lambda _mode: next(observations))
    monkeypatch.setattr(dashboard, "_poll_all_slots", fake_poll)

    sample = asyncio.run(dashboard._sample_slots_with_placement_window("both"))

    assert sample["attempt"] == 2
    assert sample["placement_stable"] is False


def test_live_frame_exposes_stage_divergence_without_normalizing_counts() -> None:
    region = _live_region_payload("frontdoor", ["fd-1", "fd-2", "fd-3"])
    telemetry = {"conflict": False, "capacity_conflicts": []}
    sample = {
        "attempt": 1,
        "max_attempts": 2,
        "frame_started_at": 100.0,
        "placement_before_at": 100.0,
        "slots_started_at": 101.0,
        "slots_completed_at": 102.0,
        "placement_after_at": 103.0,
        "placement_stable": True,
        "slots_poll_meta": {
            "ports": 1,
            "answered": 1,
            "timed_out": 0,
            "unanswered_ports": [],
        },
    }
    activity = {
        8070: {
            "n_total": 4,
            "n_active": 1,
            "active_slots": [{"task_id": 91}],
        },
    }
    taps = [
        {
            "request_id": f"chat-{idx}",
            "topology_role": "frontdoor",
            "status": "running",
            "is_live": True,
            "chunk_count": 2,
            "event_count": idx + 1,
            "updated_at_epoch": 103.0 + idx / 10,
        }
        for idx in range(3)
    ]

    frame = dashboard._annotate_live_observability_frame(
        region_locks=region,
        activity=activity,
        port_roles={8070: "frontdoor"},
        structured_requests=taps,
        placement_telemetry=telemetry,
        sample=sample,
        tap_observed_at=104.0,
    )

    assert frame["status"] == "stage_divergence"
    assert frame["window_certified"] is True
    assert frame["roles"]["frontdoor"]["placement"]["active"] == 3
    assert frame["roles"]["frontdoor"]["backend"]["active"] == 1
    assert frame["roles"]["frontdoor"]["tap"]["decoding"] == 3
    cell = region["display_matrix"]["rows"][0]["cells"][0]
    assert cell["lease_active"] == 3
    assert cell["backend_active"] == 1
    assert cell["label"] == "🔒 3/4 lease · ⚙ 1/4 slots · ✦ 3 tap"
    assert telemetry["status"] == "stage_divergence"
    assert frame["push_bridge"]["token_events_excluded"] is True
    assert frame["push_bridge"]["gap_status"] == "sequenced_in_process"
    assert [item["request_id"] for item in frame["causal_observations"]] == [
        "chat-0",
        "chat-1",
        "chat-2",
    ]


def test_live_frame_marks_unavailable_slots_unknown_without_hiding_lease() -> None:
    region = _live_region_payload("worker_general", ["wg-1"])
    telemetry = {"conflict": False, "capacity_conflicts": []}
    frame = dashboard._annotate_live_observability_frame(
        region_locks=region,
        activity={8072: {"n_total": 0, "n_active": 0, "active_slots": []}},
        port_roles={8072: "worker_general"},
        structured_requests=[],
        placement_telemetry=telemetry,
        sample={
            "attempt": 1,
            "max_attempts": 2,
            "frame_started_at": 200.0,
            "placement_before_at": 200.0,
            "slots_started_at": 201.0,
            "slots_completed_at": 202.0,
            "placement_after_at": 203.0,
            "placement_stable": True,
            "slots_poll_meta": {
                "ports": 1,
                "answered": 0,
                "timed_out": 1,
                "unanswered_ports": [8072],
            },
        },
        tap_observed_at=204.0,
    )

    assert frame["status"] == "unknown"
    assert frame["window_certified"] is False
    assert frame["roles"]["worker_general"]["placement"]["active"] == 1
    assert frame["roles"]["worker_general"]["backend"]["unknown"] is True
    assert region["display_matrix"]["rows"][0]["cells"][0]["label"] == (
        "🔒 1/4 lease · ⚙ ?/4 slots · ✦ 0 tap"
    )


def test_live_frame_preserves_gpu_no_lock_semantics() -> None:
    region = {"by_role": {}, "occupancy": {"entries": []}, "display_matrix": {"rows": []}}
    frame = dashboard._annotate_live_observability_frame(
        region_locks=region,
        activity={8083: {"n_total": 2, "n_active": 1, "active_slots": []}},
        port_roles={8083: "architect_general"},
        structured_requests=[],
        placement_telemetry={"conflict": False, "capacity_conflicts": []},
        sample={
            "attempt": 1,
            "max_attempts": 2,
            "frame_started_at": 300.0,
            "placement_before_at": 300.0,
            "slots_started_at": 301.0,
            "slots_completed_at": 302.0,
            "placement_after_at": 303.0,
            "placement_stable": True,
            "slots_poll_meta": {
                "ports": 1,
                "answered": 1,
                "timed_out": 0,
                "unanswered_ports": [],
            },
        },
        tap_observed_at=304.0,
    )

    assert frame["status"] == "certified"
    assert frame["roles"]["architect_general"]["lock_domain"] == "none"
    assert frame["roles"]["architect_general"]["backend"]["active"] == 1
    assert frame["count_disagreements"] == []


def test_coherent_display_activity_suppresses_uncorroborated_cpu_slots() -> None:
    activity = {
        8072: {"n_total": 1, "n_active": 1, "active_slots": [{"slot_id": 0}]},
        8802: {"n_total": 1, "n_active": 1, "active_slots": [{"slot_id": 0}]},
    }
    out = dashboard._coherent_display_activity(
        activity,
        structured_requests=[],
        region_locks={"by_role": {}},
        port_roles={8072: "worker_general.q0", 8802: "mi210_gpu"},
        topology_nodes=[
            {"port": 8072, "kind": "llama-server"},
            {"port": 8802, "kind": "gpu-llama-server"},
        ],
    )

    assert out[8072]["n_active"] == 0
    assert out[8072]["active_slots"] == []
    assert out[8802]["n_active"] == 1


def test_coherent_display_activity_keeps_structured_tap_cpu_slots() -> None:
    activity = {
        8072: {"n_total": 1, "n_active": 1, "active_slots": [{"slot_id": 0}]},
    }
    out = dashboard._coherent_display_activity(
        activity,
        structured_requests=[{
            "status": "running",
            "quiet_s": 1.0,
            "port": 8072,
        }],
        region_locks={"by_role": {}},
        port_roles={8072: "worker_general.q0"},
        topology_nodes=[{"port": 8072, "kind": "llama-server"}],
    )

    assert out[8072]["n_active"] == 1
    assert out[8072]["active_slots"] == [{"slot_id": 0}]


def test_enrich_structured_tap_requests_fails_open(monkeypatch) -> None:
    """Tap content must render even when the locks/topology domain raises."""
    def boom():
        raise RuntimeError("locks domain down")

    monkeypatch.setattr(dashboard, "_port_roles_cached", boom)
    monkeypatch.setattr(dashboard, "_region_locks_cached", boom)
    reqs = [{"request_id": "chat-1:aa", "role": "frontdoor", "port": 8070}]
    out = dashboard._enrich_structured_tap_requests(reqs)
    assert out == reqs


def test_read_tap_events_tail_stitches_rotation_window(tmp_path) -> None:
    """Right after a rotation the base is missing/tiny; the tail must include
    the rotated shard so parsers keep a full window (empty-panel bug)."""
    base = tmp_path / "inference_tap_events.jsonl"
    rotated = tmp_path / "inference_tap_events.jsonl.1"
    rotated.write_text('{"seq":1}\n{"seq":2}\n')

    # Base absent entirely (rotation happened, no append yet).
    out = dashboard_tap._read_tap_events_tail(base, max_bytes=1024)
    assert '{"seq":2}' in out

    # Base tiny: stitched = rotated tail + base, in order.
    base.write_text('{"seq":3}\n')
    out = dashboard_tap._read_tap_events_tail(base, max_bytes=1024)
    assert out.index('{"seq":2}') < out.index('{"seq":3}')

    # Base large enough (>= half budget): no stitching, base only.
    base.write_text('{"seq":4}\n' * 200)
    out = dashboard_tap._read_tap_events_tail(base, max_bytes=1024)
    assert '{"seq":2}' not in out


# ----- health serve-path coverage (hang/crash visibility) ---------------------


def _reset_snapshot_stats(monkeypatch, **overrides) -> None:
    fresh = {
        "last_attempt_ts": None, "last_success_ts": None, "last_duration_s": None,
        "last_error": None, "last_error_ts": None, "build_count": 0,
    }
    fresh.update(overrides)
    for k, v in fresh.items():
        monkeypatch.setitem(dashboard._SNAPSHOT_BUILD_STATS, k, v)


def test_serve_path_health_idle_worker_is_fresh(monkeypatch) -> None:
    now = 1_000_000.0
    _reset_snapshot_stats(monkeypatch)  # never built: idle, not degraded
    assert dashboard._serve_path_health(now)["staleness_class"] == "fresh"
    _reset_snapshot_stats(  # built long ago, no demand since: still fresh
        monkeypatch, last_attempt_ts=now - 5000, last_success_ts=now - 5000,
        last_duration_s=0.9, build_count=42,
    )
    assert dashboard._serve_path_health(now)["staleness_class"] == "fresh"


def test_serve_path_health_flags_hang_and_crash(monkeypatch) -> None:
    now = 1_000_000.0
    # Hang: attempt outstanding past the stall threshold, no success since.
    _reset_snapshot_stats(
        monkeypatch, last_attempt_ts=now - 45, last_success_ts=now - 300,
        build_count=10,
    )
    out = dashboard._serve_path_health(now)
    assert out["staleness_class"] == "stale"
    assert "stalled" in out["reason"]
    # In-flight but young: not yet a hang.
    _reset_snapshot_stats(
        monkeypatch, last_attempt_ts=now - 5, last_success_ts=now - 300,
        build_count=10,
    )
    assert dashboard._serve_path_health(now)["staleness_class"] == "fresh"
    # Crash loop: newest attempt errored.
    _reset_snapshot_stats(
        monkeypatch, last_attempt_ts=now - 1, last_success_ts=now - 60,
        last_error="boom", last_error_ts=now - 1, build_count=10,
    )
    out = dashboard._serve_path_health(now)
    assert out["staleness_class"] == "stale"
    assert "erroring" in out["reason"]
    assert "boom" in out["reason"]


def test_health_folds_serve_path_and_probe(monkeypatch) -> None:
    now_ref = time.time()
    # Healthy stats → health ok, serve_path present.
    _reset_snapshot_stats(
        monkeypatch, last_attempt_ts=now_ref, last_success_ts=now_ref,
        last_duration_s=0.5, build_count=3,
    )
    resp = asyncio.run(dashboard.dashboard_health())
    payload = json.loads(resp.body)
    assert payload["serve_path"]["staleness_class"] == "fresh"
    assert "probe" not in payload

    # Stalled stats must degrade the folded verdict.
    _reset_snapshot_stats(
        monkeypatch, last_attempt_ts=now_ref - 120, last_success_ts=now_ref - 600,
        build_count=3,
    )
    resp = asyncio.run(dashboard.dashboard_health())
    payload = json.loads(resp.body)
    assert payload["serve_path"]["staleness_class"] == "stale"
    assert payload["status"] == "degraded"


def test_health_probe_reports_timeout_and_error(monkeypatch) -> None:
    async def timing_out_snapshot():
        raise asyncio.TimeoutError()

    monkeypatch.setattr(dashboard, "snapshot", timing_out_snapshot)
    resp = asyncio.run(dashboard.dashboard_health(probe="snapshot"))
    payload = json.loads(resp.body)
    assert payload["probe"]["ok"] is False
    assert "timeout_s" in payload["probe"]
    assert payload["status"] == "degraded"

    async def crashing_snapshot():
        raise RuntimeError("serve path exploded")

    monkeypatch.setattr(dashboard, "snapshot", crashing_snapshot)
    resp = asyncio.run(dashboard.dashboard_health(probe="snapshot"))
    payload = json.loads(resp.body)
    assert payload["probe"]["ok"] is False
    assert "serve path exploded" in payload["probe"]["error"]
    assert payload["status"] == "degraded"


def test_gepa_status_ships_provenance_windows(tmp_path: Path, monkeypatch) -> None:
    """Task C (2026-07-26): the gepa panel payload carries the GEPA no-op
    provenance window (2026-06-04T00:00:00Z → fix commit ed6288ea author date
    2026-07-25T11:27:13Z) so the client can hatch/grey in-window trials and
    show the caveat badge. Display-only — trials are never dropped."""
    log_path = tmp_path / "autopilot.log"
    journal_path = tmp_path / "autopilot_journal.jsonl"
    log_path.write_text("2026-07-20 00:00:00,000 GEPA: Trial active\n")
    journal_path.write_text(
        json.dumps(
            {
                "trial_id": 900,
                "timestamp": "2026-07-01T00:00:00+00:00",  # inside the no-op window
                "species": "prompt_forge",
                "quality": 1.0,
                "speed": 10.0,
                "cost": 0.5,
                "reliability": 1.0,
                "pareto_status": "dominated",
            }
        )
        + "\n"
    )
    monkeypatch.setattr(dashboard, "AUTOPILOT_LOG", log_path)
    monkeypatch.setattr(dashboard, "_AUTOPILOT_JOURNAL_PATH", journal_path)

    payload = json.loads(asyncio.run(dashboard.gepa_status()).body)

    assert payload["provenance_windows"] == [
        {
            "from_ts": 1780531200.0,  # 2026-06-04T00:00:00Z (trial-521 evidence)
            "until_ts": 1784978833.0,  # 2026-07-25T11:27:13Z (ed6288ea author date)
            "label": "reflective-mutation no-op — optimizer provenance broken",
        }
    ]
    # The in-window trial still ships (label-only honesty, no data loss).
    assert [t["trial_id"] for t in payload["recent_trials"]] == [900]


def test_gepa_status_hides_provenance_window_when_visible_rows_are_post_fix(
    tmp_path: Path, monkeypatch
) -> None:
    log_path = tmp_path / "autopilot.log"
    journal_path = tmp_path / "autopilot_journal.jsonl"
    log_path.write_text("2026-08-09 00:00:00,000 Trial active\n")
    journal_path.write_text(
        json.dumps(
            {
                "trial_id": 1498,
                "timestamp": "2026-08-09T09:38:08+00:00",
                "species": "numeric_swarm",
                "quality": 1.5,
                "speed": 12.0,
                "cost": 0.5,
                "reliability": 1.0,
                "pareto_status": "dominated",
            }
        )
        + "\n"
    )
    monkeypatch.setattr(dashboard, "AUTOPILOT_LOG", log_path)
    monkeypatch.setattr(dashboard, "_AUTOPILOT_JOURNAL_PATH", journal_path)

    payload = json.loads(asyncio.run(dashboard.gepa_status()).body)

    assert [t["trial_id"] for t in payload["recent_trials"]] == [1498]
    assert payload["provenance_windows"] == []


def test_scan_orchestrator_tasks_carries_vision_image_reference(tmp_path) -> None:
    """Vision image reference reaches BOTH in-flight and completed task cards.

    End-to-end guard for the vision capture pipe: routing_meta writes
    `image_path` into the routing_decision event, and the snapshot scan must
    carry it onto the task payload the dashboard consumes. Before the capture
    fix, `image_path` appeared in no progress event at all, so this panel had
    an empty pipe rather than a rendering bug.
    """
    log = tmp_path / "p.jsonl"
    now_ts = datetime.now(timezone.utc).isoformat()
    img = "/mnt/raid0/llm/epyc-orchestrator/benchmarks/images/vl/chartqa/chart_test_0452.png"
    routing = {
        "chosen_action": "worker_vision",
        "decision_source": "vision_input",
        "image_path": img,
        "has_image": True,
        "image_source": "path",
    }
    log.write_text(
        json.dumps({"event_type": "task_started", "timestamp": now_ts, "task_id": "chat-live",
                    "data": {"objective": "What is the peak?"}}) + "\n"
        + json.dumps({"event_type": "routing_decision", "timestamp": now_ts,
                      "task_id": "chat-live", "data": routing}) + "\n"
        + json.dumps({"event_type": "task_started", "timestamp": now_ts, "task_id": "chat-done",
                      "data": {"objective": "Read the chart"}}) + "\n"
        + json.dumps({"event_type": "routing_decision", "timestamp": now_ts,
                      "task_id": "chat-done", "data": routing}) + "\n"
        + json.dumps({"event_type": "task_completed", "timestamp": now_ts,
                      "task_id": "chat-done",
                      "data": {"producer_role": "worker_vision"}}) + "\n"
    )

    in_flight, completed = dashboard_snapshot.scan_orchestrator_tasks(log)

    assert [t["task_id"] for t in in_flight] == ["chat-live"]
    assert [t["task_id"] for t in completed] == ["chat-done"]
    for task in (in_flight[0], completed[0]):
        assert task["image_path"] == img
        assert task["has_image"] is True
        assert task["image_source"] == "path"


def test_scan_orchestrator_tasks_text_task_has_no_image(tmp_path) -> None:
    """Text traffic reports has_image False with an empty path (never None)."""
    log = tmp_path / "p.jsonl"
    now_ts = datetime.now(timezone.utc).isoformat()
    log.write_text(
        json.dumps({"event_type": "task_started", "timestamp": now_ts, "task_id": "chat-text",
                    "data": {"objective": "2+2?"}}) + "\n"
        + json.dumps({"event_type": "routing_decision", "timestamp": now_ts,
                      "task_id": "chat-text", "data": {"chosen_action": "frontdoor"}}) + "\n"
    )

    in_flight, _completed = dashboard_snapshot.scan_orchestrator_tasks(log)

    assert in_flight[0]["has_image"] is False
    assert in_flight[0]["image_path"] == ""


def test_image_reference_for_task_reads_routing_metadata() -> None:
    events = [
        {"event_type": "task_started", "data": {"objective": "read this"}},
        {
            "event_type": "routing_decision",
            "data": {
                "has_image": True,
                "image_source": "path",
                "image_path": "/tmp/example.png",
            },
        },
    ]

    assert dashboard_tasks._image_reference_for_task(events) == {
        "has_image": True,
        "source": "path",
        "path": "/tmp/example.png",
    }


def test_task_detail_exposes_renderable_image_url(tmp_path, monkeypatch) -> None:
    image_path = tmp_path / "input.png"
    image_path.write_bytes(b"\x89PNG\r\n\x1a\n")
    log_path = tmp_path / "progress.jsonl"
    log_path.write_text(
        json.dumps(
            {
                "event_type": "task_started",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "task_id": "chat-image",
                "data": {"objective": "read this"},
            }
        )
        + "\n"
        + json.dumps(
            {
                "event_type": "routing_decision",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "task_id": "chat-image",
                "data": {
                    "has_image": True,
                    "image_source": "path",
                    "image_path": str(image_path),
                },
            }
        )
        + "\n"
    )
    monkeypatch.setattr(dashboard, "_todays_progress_log", lambda: log_path)
    monkeypatch.setattr(
        dashboard, "_find_structured_request_by_task_id", lambda _task_id: None
    )
    monkeypatch.setattr(
        dashboard, "_find_section_by_objective", lambda *_args, **_kwargs: None
    )

    payload = json.loads(asyncio.run(dashboard.task_detail("chat-image")).body)

    assert payload["image"] == {
        "has_image": True,
        "source": "path",
        "available": True,
        "url": "/dashboard/api/task/chat-image/image",
        "filename": "input.png",
        "reason": "",
    }


def test_task_detail_exposes_terminal_answer_when_vision_has_no_tap(tmp_path, monkeypatch) -> None:
    log_path = tmp_path / "progress.jsonl"
    now = datetime.now(timezone.utc).isoformat()
    log_path.write_text(
        json.dumps(
            {
                "event_type": "task_started",
                "timestamp": now,
                "task_id": "chat-vision",
                "data": {"objective": "read image"},
            }
        )
        + "\n"
        + json.dumps(
            {
                "event_type": "task_completed",
                "timestamp": now,
                "task_id": "chat-vision",
                "data": {
                    "producer_role": "worker_vision",
                    "work": {"answer": "0.0g"},
                },
            }
        )
        + "\n"
    )
    monkeypatch.setattr(dashboard, "_todays_progress_log", lambda: log_path)
    monkeypatch.setattr(
        dashboard, "_find_structured_request_by_task_id", lambda _task_id: None
    )
    monkeypatch.setattr(
        dashboard, "_find_section_by_objective", lambda *_args, **_kwargs: None
    )

    payload = json.loads(asyncio.run(dashboard.task_detail("chat-vision")).body)

    assert payload["tap_section"] is None
    assert payload["terminal_answer"] == "0.0g"


def test_task_image_serves_recorded_path_with_safe_headers(tmp_path, monkeypatch) -> None:
    image_path = tmp_path / "input.png"
    image_path.write_bytes(b"\x89PNG\r\n\x1a\n")
    events = [
        {
            "event_type": "routing_decision",
            "data": {
                "has_image": True,
                "image_source": "path",
                "image_path": str(image_path),
            },
        }
    ]
    monkeypatch.setattr(
        dashboard, "_todays_progress_log", lambda: tmp_path / "progress.jsonl"
    )
    monkeypatch.setattr(dashboard, "_task_events", lambda *_args, **_kwargs: events)

    response = asyncio.run(dashboard.task_image("chat-image"))

    assert response.path == image_path
    assert response.media_type == "image/png"
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["x-content-type-options"] == "nosniff"


def test_task_detail_marks_base64_image_unavailable() -> None:
    events = [
        {
            "event_type": "routing_decision",
            "data": {"has_image": True, "image_source": "base64"},
        }
    ]

    metadata = dashboard._task_image_metadata("chat-base64", events)

    assert metadata["has_image"] is True
    assert metadata["source"] == "base64"
    assert metadata["available"] is False
    assert metadata["url"] is None
    assert "not retained" in metadata["reason"]
