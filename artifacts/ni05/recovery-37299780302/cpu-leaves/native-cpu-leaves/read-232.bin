"""RTG-47 — per-process substrate (gpu/cpu) on topology nodes (2026-08-10).

Role names carry no substrate — ``architect_general`` runs on the MI210 today
and nothing in its name says so — so the topology payload derives substrate
from PROCESS evidence: the llama-server binary path (CPU tree ``build/``, GPU
tree ``build-hip/`` on this host), and for aux services argv[0] from /proc or
an explicit HIP/ROCm marker in the state file's model label. A hardcoded
role→substrate list in a dashboard page is exactly the drift class RTG-47
removes.

Spec: epyc-root handoffs/active/dashboard-architecture-restructure.md
(operator eyeball pass, 2026-08-10). All fixtures are synthetic (ps output is
monkeypatched; /proc reads point at a nonexistent pid) — no live processes are
touched.
"""

from __future__ import annotations

import pytest

from src.api.routes import dashboard_topology


@pytest.fixture(autouse=True)
def _neutralize_realized_numa_probe(monkeypatch):
    """Keep unit tests hermetic and network-free (mirrors test_dashboard_helpers)."""
    dashboard_topology._REALIZED_NUMA_CACHE.update({"ts": 0.0, "value": None, "probed": False})
    monkeypatch.setattr(dashboard_topology, "_probe_realized_numa_mode", lambda: None)
    yield
    dashboard_topology._REALIZED_NUMA_CACHE.update({"ts": 0.0, "value": None, "probed": False})


def _wire_ps(monkeypatch, ps_lines):
    monkeypatch.setattr(
        dashboard_topology,
        "_ps_llama_scan",
        lambda: "    PID ELAPSED CMD\n" + "\n".join(ps_lines) + "\n",
    )
    monkeypatch.setattr(dashboard_topology, "_llama_fleet_markers", lambda: {})
    monkeypatch.setattr(dashboard_topology, "_launch_contract_ports", lambda: set())
    monkeypatch.setattr(dashboard_topology, "_port_hint", lambda port: f"role_{port}")


def test_hip_binary_reads_gpu(monkeypatch) -> None:
    _wire_ps(monkeypatch, [
        "   1001    500 /mnt/raid0/llm/llama.cpp/build-hip/bin/llama-server"
        " -m /models/Qwen3.6-27B-MTP-Q8_0.gguf --port 8083 -np 2",
    ])
    procs = dashboard_topology._discover_llama_processes()
    assert procs[8083]["substrate"] == "gpu"


def test_plain_binary_reads_cpu(monkeypatch) -> None:
    _wire_ps(monkeypatch, [
        "   1002    500 /mnt/raid0/llm/llama.cpp/build/bin/llama-server"
        " -m /models/model.gguf --port 8070 -t 48",
    ])
    procs = dashboard_topology._discover_llama_processes()
    assert procs[8070]["substrate"] == "cpu"


def test_model_path_marker_does_not_leak_into_substrate(monkeypatch) -> None:
    """The marker must come from the BINARY path, never the model path."""
    _wire_ps(monkeypatch, [
        "   1003    500 /mnt/raid0/llm/llama.cpp/build/bin/llama-server"
        " -m /models/gfx90a-tuned-model.gguf --port 8071 -t 48",
    ])
    procs = dashboard_topology._discover_llama_processes()
    assert procs[8071]["substrate"] == "cpu"


def test_service_substrate_from_model_hint() -> None:
    """No readable /proc entry + HIP marker in the state's model label → gpu."""
    assert dashboard_topology._service_substrate(-1, "whisper.cpp large-v3-turbo (HIP)") == "gpu"


def test_service_substrate_unknown_stays_none() -> None:
    """An arbitrary service binary without a marker proves nothing: None, not cpu."""
    assert dashboard_topology._service_substrate(-1, "searxng:latest") is None


# ---------------------------------------------------------------------------
# RTG-47 data plane (2026-09-17): manifest-DECLARED substrate for
# expected-but-not-running nodes. No process exists for them, so none of the
# process rules above can speak; the value comes from the stack manifest's
# `device` declaration and is labelled as such via `substrate_source`.
# ---------------------------------------------------------------------------

def test_manifest_declared_substrate_reads_declared_gpu_device(monkeypatch) -> None:
    import scripts.server.stack_manifest as manifest

    monkeypatch.setattr(
        manifest, "master_declared",
        lambda role, key: ("ROCm0", "architect_general/direct") if role == "architect_general" else (None, None),
    )
    out = dashboard_topology.manifest_declared_substrate(["architect_general"])
    assert out == {
        "substrate": "gpu",
        "source": "manifest",
        "declared_by": "architect_general/direct device=ROCm0",
    }


def test_manifest_declared_substrate_reads_omitted_device_as_host_lane(monkeypatch) -> None:
    """The manifest books a device-less role against host RAM — omission IS
    the declaration of a host lane, and `declared_by` says so explicitly."""
    import scripts.server.stack_manifest as manifest

    monkeypatch.setattr(manifest, "master_declared", lambda role, key: (None, None))
    monkeypatch.setattr(manifest, "master_server_row", lambda role: ("frontdoor", {"port": 8070}, "direct"))
    out = dashboard_topology.manifest_declared_substrate(["frontdoor", "worker_summarize"])
    assert out == {"substrate": "cpu", "source": "manifest", "declared_by": "device-omitted"}


def test_manifest_declared_substrate_says_nothing_for_unknown_roles(monkeypatch) -> None:
    import scripts.server.stack_manifest as manifest

    monkeypatch.setattr(manifest, "master_declared", lambda role, key: (None, None))
    monkeypatch.setattr(manifest, "master_server_row", lambda role: (None, None, ""))
    assert dashboard_topology.manifest_declared_substrate(["no_such_role"]) is None
    assert dashboard_topology.manifest_declared_substrate([]) is None
    assert dashboard_topology.manifest_declared_substrate("frontdoor") is None


def test_non_running_expected_stack_server_takes_manifest_substrate_marked_declared(monkeypatch) -> None:
    """The node under test: expected, not running, no process evidence. Its
    substrate comes from the manifest and is marked `declared`; a RUNNING
    node's substrate stays marked `process` so the two never blur."""
    from src.api.routes import dashboard

    monkeypatch.setenv("ORCHESTRATOR_STACK_NUMA_MODE", "full")
    monkeypatch.setattr(dashboard, "_discover_llama_ports", lambda: {8070: "frontdoor"})
    monkeypatch.setattr(dashboard, "_discover_llama_models", lambda: {})
    monkeypatch.setattr(dashboard, "_load_state_services", lambda: [])
    monkeypatch.setattr(
        dashboard, "_discover_llama_processes",
        lambda: {8070: {"role": "frontdoor", "substrate": "cpu"}},
    )
    monkeypatch.setattr(
        dashboard, "expected_stack_services",
        lambda mode: [
            {"name": "frontdoor", "role": "frontdoor", "port": 8070, "roles": ["frontdoor"]},
            {"name": "architect_general", "role": "architect_general", "port": 8085,
             "roles": ["architect_general"]},
            {"name": "mystery", "role": "mystery", "port": 8999, "roles": ["mystery"]},
        ],
    )

    def fake_declared(roles):
        if roles == ["architect_general"]:
            return {"substrate": "gpu", "source": "manifest",
                    "declared_by": "architect_general/direct device=ROCm0"}
        return None

    monkeypatch.setattr(dashboard, "manifest_declared_substrate", fake_declared)

    by_port = {n["port"]: n for n in dashboard._build_topology_nodes("full")
               if isinstance(n.get("port"), int)}

    expected = by_port[8085]
    assert expected["kind"] == "expected-stack-server"
    assert expected["running"] is False
    assert expected["substrate"] == "gpu"
    assert expected["substrate_source"] == "manifest"
    assert expected["substrate_declared_by"] == "architect_general/direct device=ROCm0"

    running = by_port[8070]
    assert running["kind"] == "llama-server"
    assert running["substrate"] == "cpu"
    assert running["substrate_source"] == "process"
    assert "substrate_declared_by" not in running

    # A role the manifest knows nothing about carries NO substrate — the page
    # may fall back to its heuristic there, but the producer asserts nothing.
    unknown = by_port[8999]
    assert unknown["kind"] == "expected-stack-server"
    assert "substrate" not in unknown
    assert "substrate_source" not in unknown
