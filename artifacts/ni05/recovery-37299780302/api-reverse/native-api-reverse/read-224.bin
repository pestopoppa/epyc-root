"""M3 — extern/unmanaged llama-process attribution (2026-07-23).

A llama-server listener may render under a production-lane label ONLY when the
stack vouches for it: a fresh per-port fleet marker or launch-contract
membership (runtime-facts selected_servers). Anything else — bench harnesses,
GPU warmups (the observed extern_18072 class) — must render as
``extern_<port>`` and never inherit a role/lane label from a stale marker or a
static lineup.

Spec: handoffs/active/autopilot-dashboard-fidelity-audit-2026-07-22.md (M3)
and stack-lineup-dossier-2026-07-23.md §4 item 9 / §6 contradiction 2
(epyc-root repo).

All fixtures are synthetic (ps output, markers, contract ports are
monkeypatched) — no live processes, sockets, or marker files are touched.
"""

from __future__ import annotations

import time

import pytest

from src.api.routes import dashboard, dashboard_topology


@pytest.fixture(autouse=True)
def _neutralize_realized_numa_probe(monkeypatch):
    """Keep unit tests hermetic and network-free (mirrors test_dashboard_helpers)."""
    dashboard_topology._REALIZED_NUMA_CACHE.update({"ts": 0.0, "value": None, "probed": False})
    monkeypatch.setattr(dashboard_topology, "_probe_realized_numa_mode", lambda: None)
    yield
    dashboard_topology._REALIZED_NUMA_CACHE.update({"ts": 0.0, "value": None, "probed": False})


# Controlled port→label hints: hint resolution has its own tests
# (test_dashboard_helpers); here we pin the hint layer so the attribution layer
# is exercised in isolation.
_LANE_HINTS = {
    8080: "frontdoor.q0",
    18070: "eval_batch_frontdoor",
    8090: "embedder",
    8096: "embedder_granite_97m_r2",
}


def _fake_port_hint(port: int) -> str:
    return _LANE_HINTS.get(port, f"port_{port}")


def _ps_line(pid: int, etimes: int, port: int, binary: str = "llama-server") -> str:
    return (
        f"{pid:>7} {etimes:>7} /mnt/raid0/llm/llama.cpp/build/bin/{binary}"
        f" -m /models/model.gguf --port {port} -t 48"
    )


def _wire(monkeypatch, *, ps_lines, markers, contract_ports):
    monkeypatch.setattr(dashboard_topology, "_port_hint", _fake_port_hint)
    monkeypatch.setattr(
        dashboard_topology,
        "_ps_llama_scan",
        lambda: "    PID ELAPSED CMD\n" + "\n".join(ps_lines) + "\n",
    )
    monkeypatch.setattr(dashboard_topology, "_llama_fleet_markers", lambda: dict(markers))
    monkeypatch.setattr(
        dashboard_topology, "_launch_contract_ports", lambda: set(contract_ports)
    )


def _fresh_marker(roles: list[str], *, age_s: float) -> dict:
    return {
        "started_at": time.time() - age_s,
        "source": "stack_commands",
        "roles": roles,
    }


# ---------------------------------------------------------------------------
# Fixture 1 — marker-attributed port: fresh fleet marker vouches for the lane.
# ---------------------------------------------------------------------------


def test_marker_attributed_port_keeps_lane_label(monkeypatch) -> None:
    # Marker written ~5s before Popen (the stack_commands ordering).
    _wire(
        monkeypatch,
        ps_lines=[_ps_line(411223, 3600, 8080)],
        markers={8080: _fresh_marker(["frontdoor"], age_s=3605)},
        contract_ports=set(),
    )

    procs = dashboard_topology._discover_llama_processes()

    info = procs[8080]
    assert info["role"] == "frontdoor.q0"
    assert info["attribution"] == dashboard_topology.ATTRIBUTION_FLEET_MARKER
    assert "lane_hint" not in info
    assert "marker_stale" not in info
    assert info["pid"] == 411223


# ---------------------------------------------------------------------------
# Fixture 2 — launch-contract port: selected_servers membership vouches for it.
# ---------------------------------------------------------------------------


def test_launch_contract_port_keeps_lane_label(monkeypatch) -> None:
    _wire(
        monkeypatch,
        ps_lines=[_ps_line(52001, 120, 18070)],
        markers={},
        contract_ports={18070},
    )

    procs = dashboard_topology._discover_llama_processes()

    info = procs[18070]
    assert info["role"] == "eval_batch_frontdoor"
    assert info["attribution"] == dashboard_topology.ATTRIBUTION_LAUNCH_CONTRACT
    assert "lane_hint" not in info


# ---------------------------------------------------------------------------
# Fixture 3 — unmanaged port: no marker, no contract → extern_<port>.
# ---------------------------------------------------------------------------


def test_unmanaged_unmapped_port_renders_extern(monkeypatch) -> None:
    # The observed 18072 class: bench/GPU-warmup listener on a port no lineup
    # maps. The plane is active (a marker exists for 8080), so the verdict is
    # confidently "unmanaged", not "unverified".
    _wire(
        monkeypatch,
        ps_lines=[
            _ps_line(411223, 3600, 8080),
            _ps_line(97001, 500, 18072),
        ],
        markers={8080: _fresh_marker(["frontdoor"], age_s=3605)},
        contract_ports={8080},
    )

    procs = dashboard_topology._discover_llama_processes()

    info = procs[18072]
    assert info["role"] == "extern_18072"
    assert info["attribution"] == dashboard_topology.ATTRIBUTION_UNMANAGED


def test_unmanaged_lane_labeled_port_demoted_to_extern(monkeypatch) -> None:
    # A bench process squatting on the CONFIGURED eval-batch lane port must not
    # inherit the "eval_batch_frontdoor" label from the static lineup.
    _wire(
        monkeypatch,
        ps_lines=[
            _ps_line(411223, 3600, 8080),
            _ps_line(97002, 500, 18070),
        ],
        markers={8080: _fresh_marker(["frontdoor"], age_s=3605)},
        contract_ports={8080},
    )

    procs = dashboard_topology._discover_llama_processes()

    info = procs[18070]
    assert info["role"] == "extern_18070"
    assert info["attribution"] == dashboard_topology.ATTRIBUTION_UNMANAGED
    assert info["lane_hint"] == "eval_batch_frontdoor"


# ---------------------------------------------------------------------------
# Fixture 4 — stale-marker-mismatched port: a left-behind marker (previous
# process on the port) must never vouch for the current listener.
# ---------------------------------------------------------------------------


def test_stale_marker_mismatched_port_demoted(monkeypatch) -> None:
    # The 2026-07-05 llama_18070 marker vs a listener started much later.
    _wire(
        monkeypatch,
        ps_lines=[_ps_line(97003, 3600, 18070)],
        markers={18070: _fresh_marker(["eval_batch_frontdoor"], age_s=18 * 86400)},
        contract_ports=set(),
    )

    procs = dashboard_topology._discover_llama_processes()

    info = procs[18070]
    assert info["role"] == "extern_18070"
    assert info["attribution"] == dashboard_topology.ATTRIBUTION_UNMANAGED
    assert info["marker_stale"] is True
    assert info["lane_hint"] == "eval_batch_frontdoor"


def test_stale_marker_on_unmapped_port_never_names_roles(monkeypatch) -> None:
    # A stale marker must not relabel an unmapped listener either.
    _wire(
        monkeypatch,
        ps_lines=[_ps_line(97004, 600, 18075)],
        markers={18075: _fresh_marker(["eval_batch_frontdoor"], age_s=18 * 86400)},
        contract_ports=set(),
    )

    procs = dashboard_topology._discover_llama_processes()

    info = procs[18075]
    assert info["role"] == "extern_18075"
    assert info["attribution"] == dashboard_topology.ATTRIBUTION_UNMANAGED
    assert info["marker_stale"] is True


# ---------------------------------------------------------------------------
# Guard rails: fail-open, service exemptions, marker-named unmapped ports.
# ---------------------------------------------------------------------------


def test_fail_open_when_attribution_plane_has_no_signal(monkeypatch) -> None:
    # No markers, no contract (dev checkout / hermetic test): keep legacy
    # labels — never demote a fleet the attribution plane cannot see.
    _wire(
        monkeypatch,
        ps_lines=[_ps_line(97005, 500, 18070)],
        markers={},
        contract_ports=set(),
    )

    procs = dashboard_topology._discover_llama_processes()

    info = procs[18070]
    assert info["role"] == "eval_batch_frontdoor"
    assert info["attribution"] == dashboard_topology.ATTRIBUTION_UNVERIFIED


def test_service_and_embedder_ports_never_lane_demoted(monkeypatch) -> None:
    # Auxiliary service hints (8090 in _BASE_SERVICE_PORT_HINTS) and embedder
    # siblings (8096, manifest-labeled) are not production lanes — M3 demotion
    # never applies even when they carry no marker/contract evidence.
    _wire(
        monkeypatch,
        ps_lines=[
            _ps_line(411223, 3600, 8080),
            _ps_line(97006, 700, 8090),
            _ps_line(97007, 700, 8096),
        ],
        markers={8080: _fresh_marker(["frontdoor"], age_s=3605)},
        contract_ports={8080},
    )

    procs = dashboard_topology._discover_llama_processes()

    assert procs[8090]["role"] == "embedder"
    assert procs[8090]["attribution"] == dashboard_topology.ATTRIBUTION_SERVICE_HINT
    assert procs[8096]["role"] == "embedder_granite_97m_r2"
    assert procs[8096]["attribution"] == dashboard_topology.ATTRIBUTION_SERVICE_HINT


def test_fresh_marker_names_roles_for_unmapped_port(monkeypatch) -> None:
    # A stack launch on a port absent from the static hints: the fresh marker
    # carries the role list written at launch and names the node.
    _wire(
        monkeypatch,
        ps_lines=[_ps_line(97008, 60, 18075)],
        markers={18075: _fresh_marker(["eval_batch_frontdoor"], age_s=65)},
        contract_ports=set(),
    )

    procs = dashboard_topology._discover_llama_processes()

    info = procs[18075]
    assert info["role"] == "eval_batch_frontdoor"
    assert info["attribution"] == dashboard_topology.ATTRIBUTION_FLEET_MARKER


def test_discover_llama_ports_wrapper_matches_process_roles(monkeypatch) -> None:
    _wire(
        monkeypatch,
        ps_lines=[
            _ps_line(411223, 3600, 8080),
            _ps_line(97001, 500, 18072),
        ],
        markers={8080: _fresh_marker(["frontdoor"], age_s=3605)},
        contract_ports={8080},
    )

    ports = dashboard_topology._discover_llama_ports()

    assert ports == {8080: "frontdoor.q0", 18072: "extern_18072"}


# ---------------------------------------------------------------------------
# Topology nodes carry the attribution metadata (additive fields only).
# ---------------------------------------------------------------------------


def test_topology_nodes_carry_attribution_and_extern_kind(monkeypatch) -> None:
    monkeypatch.setenv("ORCHESTRATOR_STACK_NUMA_MODE", "quarter")
    monkeypatch.setattr(
        dashboard,
        "_discover_llama_ports",
        lambda: {8080: "frontdoor.q0", 18072: "extern_18072"},
    )
    monkeypatch.setattr(dashboard, "_discover_llama_models", lambda: {})
    monkeypatch.setattr(dashboard, "_load_state_services", lambda: [])
    monkeypatch.setattr(
        dashboard,
        "_discover_llama_processes",
        lambda: {
            8080: {
                "role": "frontdoor.q0",
                "attribution": dashboard_topology.ATTRIBUTION_FLEET_MARKER,
            },
            18072: {
                "role": "extern_18072",
                "attribution": dashboard_topology.ATTRIBUTION_UNMANAGED,
                "lane_hint": "eval_batch_frontdoor",
                "marker_stale": True,
            },
        },
    )

    by_port = {
        node["port"]: node
        for node in dashboard._build_topology_nodes("quarter")
        if isinstance(node.get("port"), int)
    }

    extern = by_port[18072]
    assert extern["kind"] == "external-llama-server"
    assert extern["role"] == "extern_18072"
    assert extern["attribution"] == dashboard_topology.ATTRIBUTION_UNMANAGED
    assert extern["lane_hint"] == "eval_batch_frontdoor"
    assert extern["marker_stale"] is True

    managed = by_port[8080]
    assert managed["kind"] == "llama-server"
    assert managed["attribution"] == dashboard_topology.ATTRIBUTION_FLEET_MARKER
    assert "lane_hint" not in managed
    assert "marker_stale" not in managed


def test_topology_nodes_without_attribution_map_keep_pre_m3_shape(monkeypatch) -> None:
    # Tests/callers that stub `_discover_llama_ports` alone (the pre-M3
    # surface) must see the exact pre-M3 node shape: no attribution fields.
    monkeypatch.setenv("ORCHESTRATOR_STACK_NUMA_MODE", "quarter")
    monkeypatch.setattr(dashboard, "_discover_llama_ports", lambda: {8080: "frontdoor.q0"})
    monkeypatch.setattr(dashboard, "_discover_llama_models", lambda: {})
    monkeypatch.setattr(dashboard, "_load_state_services", lambda: [])
    monkeypatch.setattr(dashboard, "_discover_llama_processes", lambda: {})

    by_port = {
        node["port"]: node
        for node in dashboard._build_topology_nodes("quarter")
        if isinstance(node.get("port"), int)
    }

    node = by_port[8080]
    assert "attribution" not in node
    assert "lane_hint" not in node
    assert "marker_stale" not in node


def test_fresh_marker_never_vouches_for_older_squatter():
    """Verifier finding 1 (symmetric staleness): a listener that predates the
    marker by more than the launch gap is not the marker process — a bench
    squatter must not inherit the lane label when a fresh launch dies."""
    from src.api.routes.dashboard_topology import _classify_llama_attribution

    now = 1_000_000.0
    out = _classify_llama_attribution(
        18070,
        now - 3600.0,  # squatter listening for an hour
        {18070: {"started_at": now - 10.0, "roles": ["eval_batch_frontdoor"]}},
        set(),
    )
    assert out["attribution"] == "unmanaged"
    assert out["marker_stale"] is True


def test_marker_never_vouches_when_proc_start_unknown():
    """Verifier finding 2: unknown listener start time -> the marker cannot be
    matched to the process, so it must not vouch (fail toward demotion)."""
    from src.api.routes.dashboard_topology import _classify_llama_attribution

    out = _classify_llama_attribution(
        18070,
        None,
        {18070: {"started_at": 123.0, "roles": ["eval_batch_frontdoor"]}},
        set(),
    )
    assert out["attribution"] == "unmanaged"
    assert out["marker_stale"] is True
