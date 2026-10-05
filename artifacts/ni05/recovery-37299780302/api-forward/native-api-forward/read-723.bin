"""Tests for runtime-facts manifest generation."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from scripts.server.fleet_markers import (
    LAUNCH_SOURCE_STACK_COMMANDS,
    write_llama_marker,
    write_orchestrator_marker,
)
from scripts.server.runtime_facts_manifest import (
    RUNTIME_FACTS_MANIFEST_NAME,
    build_runtime_facts_manifest,
    read_runtime_stack_numa_mode,
    read_runtime_stack_selected_servers,
    realized_stack_numa_mode_from_state,
    runtime_facts_manifest_path,
    write_runtime_facts_manifest,
)
from scripts.server.stack_state import ProcessInfo


def _write_yaml(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def _quarter_frontdoor_state() -> dict[str, ProcessInfo]:
    """A realized quarters-only frontdoor fleet, with the alias role rows the
    launcher writes (state[alias] = same ProcessInfo) and a stale dead embedder
    row that liveness filtering must drop."""
    q0 = ProcessInfo(
        role="frontdoor",
        pid=111,
        port=8080,
        started_at="2026-07-22T00:00:00Z",
        model_path="/models/frontdoor.gguf",
        log_file="/logs/frontdoor-8080.log",
    )
    q1 = ProcessInfo(
        role="frontdoor",
        pid=112,
        port=8180,
        started_at="2026-07-22T00:00:00Z",
        model_path="/models/frontdoor.gguf",
        log_file="/logs/frontdoor-8180.log",
    )
    stale_embedder = ProcessInfo(
        role="embedder_granite_97m_r2",
        pid=999,  # dead pid — must be filtered out
        port=8096,
        started_at="2026-07-01T00:00:00Z",
        model_path="/models/granite.gguf",
        log_file="/logs/embedder-8096.log",
    )
    return {
        "server_8080": q0,
        "server_8180": q1,
        "server_8096": stale_embedder,
        # role-keyed alias rows point at the first frontdoor quarter
        "frontdoor": q0,
        "coder_escalation": q0,
        "worker_summarize": q0,
        "orchestrator": ProcessInfo(
            role="orchestrator",
            pid=113,
            port=8000,
            started_at="2026-07-22T00:00:00Z",
            model_path="uvicorn",
            log_file="/logs/orchestrator.log",
        ),
    }


def _alive_only(alive: set[int]):
    return lambda pid: pid in alive


def test_build_runtime_facts_manifest_serializes_realized_state_and_markers(
    tmp_path: Path,
) -> None:
    stack_priors_path = _write_yaml(
        tmp_path / "stack_priors.yaml",
        """
stack_priors_version: 4
compiled_at: "2026-07-11T00:00:00Z"
status: live
source_artifacts: {}
roles:
  frontdoor:
    deployment_status: live_stack
    serving: {}
""".strip()
        + "\n",
    )
    orchestrator_marker = write_orchestrator_marker(tmp_dir=tmp_path, git_sha="cafebabe")
    llama_marker = write_llama_marker(
        port=8080,
        roles=["frontdoor", "coder_escalation"],
        source=LAUNCH_SOURCE_STACK_COMMANDS,
        tmp_dir=tmp_path,
    )

    state = _quarter_frontdoor_state()
    manifest = build_runtime_facts_manifest(
        state=state,
        launch_contracts={
            "frontdoor": {
                "ports": [8080, 8180],
                "binary": "llama.cpp",
                "launch": {"entries": [{"port": 8080, "alias": False}]},
            }
        },
        stack_priors_path=stack_priors_path,
        # No explicit mode — must be DERIVED from realized ports.
        stack_numa_mode=None,
        tmp_dir=tmp_path,
        repo_short_sha="abc1234",
        source="unit-test",
        pid_alive=_alive_only({111, 112, 113}),  # 999 (embedder) is dead
    )

    runtime_stack = manifest["runtime_stack"]
    # Derived from the realized quarters — NOT the declarative full lineup.
    assert runtime_stack["stack_numa_mode"] == "quarter"
    assert runtime_stack["selected_ports"] == [8080, 8180]
    assert 8070 not in runtime_stack["selected_ports"]  # dead full port never recorded
    assert 8096 not in runtime_stack["selected_ports"]  # dead embedder filtered
    assert 8000 not in runtime_stack["selected_ports"]  # orchestrator API is not a llama role
    by_port = {srv["port"]: srv for srv in runtime_stack["selected_servers"]}
    assert by_port[8080]["numa_instance"] == 1  # topology idx of 8080 in frontdoor
    assert by_port[8180]["numa_instance"] == 2
    assert "coder_escalation" in by_port[8080]["roles"]  # alias row folded in

    assert manifest["runtime_stack"]["paths"] == {
        "tmp_dir": str(tmp_path),
        "state_file": str(manifest["runtime_stack"]["paths"]["state_file"]),
        "stack_priors_path": str(stack_priors_path),
        "log_dir": str(manifest["runtime_stack"]["paths"]["log_dir"]),
        "llama_server": str(manifest["runtime_stack"]["paths"]["llama_server"]),
    }
    # Raw state block is still serialized verbatim (debugging/attestation value).
    assert manifest["state"]["server_8080"] == asdict(state["server_8080"])
    assert manifest["stack_priors"]["live_roles"] == ["frontdoor"]

    orchestrator = manifest["fleet_markers"]["orchestrator"]
    assert orchestrator is not None
    assert orchestrator["git_sha"] == "cafebabe"

    assert orchestrator_marker.exists()
    assert llama_marker.exists()


def test_realized_stack_numa_mode_from_state_derives_quarter_and_ignores_dead() -> None:
    state = _quarter_frontdoor_state()
    assert (
        realized_stack_numa_mode_from_state(state, pid_alive=_alive_only({111, 112, 113}))
        == "quarter"
    )
    # Everything dead → undetermined (never fabricated as "full").
    assert realized_stack_numa_mode_from_state(state, pid_alive=_alive_only(set())) is None
    assert realized_stack_numa_mode_from_state({}, pid_alive=_alive_only(set())) is None


def test_runtime_facts_resolve_worker_logical_alias_to_physical_topology(
    tmp_path: Path,
) -> None:
    """A logical alias resolves to its HOST's physical topology, per instance.

    2026-09-22 lineup cutover (860b0b2d): worker_general / worker_explore stopped
    being their own CPU fleet (:8072/:8082/:8182, numa_config deleted) and became
    aliases on frontdoor's process, whose full + halves carry the worker lane. The
    fixture is therefore built from the CURRENT declarations — the host comes from
    master's shared_with binding and the ports from the host's NUMA_CONFIG — not
    restated. The invariant is unchanged: a process whose ProcessInfo.role is a
    logical alias with no topology of its own (the launcher's worker rows) must
    still get ``numa_instance``/``topology_role`` from the physical owner of its
    port; dropping them degrades config to plain round-robin URLs.
    """
    from scripts.server.stack_manifest import master_server_row
    from scripts.server.stack_numa import NUMA_CONFIG

    host, _row, binding = master_server_row("worker_explore")
    assert binding == "shared_with"
    assert master_server_row("worker_general")[0] == host
    # The aliases own no topology of their own — resolution MUST go via the host.
    assert "worker_general" not in NUMA_CONFIG
    assert "worker_explore" not in NUMA_CONFIG
    host_ports = [int(inst[1]) for inst in NUMA_CONFIG[host]["instances"]]
    assert len(host_ports) > 1  # non-vacuous: per-instance resolution is exercised

    infos = {
        port: ProcessInfo(
            # The primary instance's ProcessInfo carries a logical alias as its
            # role (the hard case); the sub-full instances carry the host's.
            role="worker_explore" if idx == 0 else host,
            pid=201 + idx,
            port=port,
            started_at="2026-08-07T00:00:00Z",
            model_path="/models/worker.gguf",
            log_file=f"/logs/worker-{port}.log",
        )
        for idx, port in enumerate(host_ports)
    }
    state: dict[str, ProcessInfo] = {f"server_{port}": info for port, info in infos.items()}
    # Role-keyed alias rows the launcher writes (state[alias] = same ProcessInfo).
    state["worker_general"] = infos[host_ports[0]]
    state["worker_explore"] = infos[host_ports[0]]

    manifest = build_runtime_facts_manifest(
        state=state,
        launch_contracts={},
        stack_priors_path=_write_yaml(
            tmp_path / "stack_priors.yaml",
            "stack_priors_version: 4\nstatus: live\nroles: {}\n",
        ),
        tmp_dir=tmp_path,
        source="unit-test",
        pid_alive=_alive_only({info.pid for info in infos.values()}),
    )

    by_port = {row["port"]: row for row in manifest["runtime_stack"]["selected_servers"]}
    primary = by_port[host_ports[0]]
    assert {"worker_general", "worker_explore"} <= set(primary["roles"])
    for idx, port in enumerate(host_ports):
        assert by_port[port]["numa_instance"] == idx, port
        assert by_port[port]["topology_role"] == host, port


def test_write_runtime_facts_manifest_writes_valid_json_and_handles_missing_inputs(
    tmp_path: Path,
) -> None:
    malformed_stack_priors_path = _write_yaml(
        tmp_path / "stack_priors.yaml",
        "{not: valid: yaml",
    )

    manifest_path = write_runtime_facts_manifest(
        state={
            "frontdoor": ProcessInfo(
                role="frontdoor",
                pid=123,
                port=8070,
                started_at="2026-07-11T00:00:00Z",
                model_path="/models/frontdoor.gguf",
                log_file="/logs/frontdoor.log",
            )
        },
        launch_contracts={"frontdoor": {"ports": [8070], "launch": {"entries": []}}},
        stack_priors_path=malformed_stack_priors_path,
        stack_numa_mode="full",
        tmp_dir=tmp_path,
        repo_short_sha=None,
        source="unit-test",
    )

    assert manifest_path == runtime_facts_manifest_path(tmp_path)
    assert manifest_path.name == RUNTIME_FACTS_MANIFEST_NAME
    assert manifest_path.exists()

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["schema"] == "epyc.orchestrator.runtime_facts"
    assert manifest["schema_version"] == 1
    assert manifest["source"] == "unit-test"
    assert manifest["repo"] == {"short_sha": None}
    assert manifest["runtime_stack"]["stack_numa_mode"] == "full"
    assert manifest["launch_contracts"]["frontdoor"]["ports"] == [8070]
    assert manifest["state"]["frontdoor"]["pid"] == 123
    assert manifest["stack_priors"] == {
        "path": str(malformed_stack_priors_path),
        "available": False,
        "live_role_count": 0,
        "live_roles": [],
    }
    assert manifest["fleet_markers"]["orchestrator"] is None
    assert manifest["fleet_markers"]["llama"] == {}


def test_write_runtime_facts_manifest_uses_atomic_replace_no_tmp_left_behind(
    tmp_path: Path,
) -> None:
    stack_priors_path = _write_yaml(
        tmp_path / "stack_priors.yaml",
        """
stack_priors_version: 4
compiled_at: "2026-07-11T00:00:00Z"
status: live
source_artifacts: {}
roles: {}
""".strip()
        + "\n",
    )

    manifest_path = write_runtime_facts_manifest(
        state={},
        launch_contracts={},
        stack_priors_path=stack_priors_path,
        stack_numa_mode="both",
        tmp_dir=tmp_path,
        repo_short_sha="abc1234",
        source="unit-test",
    )

    assert manifest_path.exists()
    leftover = [entry for entry in tmp_path.iterdir() if ".tmp." in entry.name]
    assert leftover == []


def test_read_runtime_stack_selected_servers_rejects_malformed_or_stale_manifest(
    tmp_path: Path,
) -> None:
    manifest_path = tmp_path / "facts.json"
    state_file = tmp_path / "orchestrator_state.json"

    manifest_path.write_text("{}", encoding="utf-8")
    assert (
        read_runtime_stack_selected_servers(
            manifest_path=manifest_path,
            state_file=state_file,
        )
        is None
    )

    manifest_path.write_text(
        json.dumps(
            {
                "schema": "epyc.orchestrator.runtime_facts",
                "schema_version": 1,
                "runtime_stack": {
                    "stack_numa_mode": "full",
                    "selected_ports": [8070],
                    "selected_servers": [
                        {"port": 8070, "roles": ["frontdoor"]},
                        {"port": 8070, "roles": ["duplicate"]},
                    ],
                },
            }
        ),
        encoding="utf-8",
    )
    assert (
        read_runtime_stack_selected_servers(
            manifest_path=manifest_path,
            state_file=state_file,
        )
        is None
    )

    manifest_path.write_text(
        json.dumps(
            {
                "schema": "epyc.orchestrator.runtime_facts",
                "schema_version": 1,
                "runtime_stack": {
                    "stack_numa_mode": "full",
                    "selected_ports": [8070],
                    "selected_servers": [{"port": 8070, "roles": ["frontdoor"]}],
                },
            }
        ),
        encoding="utf-8",
    )
    state_file.write_text("{}", encoding="utf-8")
    assert (
        read_runtime_stack_selected_servers(
            manifest_path=manifest_path,
            state_file=state_file,
        )
        is None
    )


def test_read_runtime_stack_numa_mode_rejects_malformed_stale_or_unknown_mode(
    tmp_path: Path,
) -> None:
    manifest_path = tmp_path / "facts.json"
    state_file = tmp_path / "orchestrator_state.json"

    manifest_path.write_text("{}", encoding="utf-8")
    assert (
        read_runtime_stack_numa_mode(
            manifest_path=manifest_path,
            state_file=state_file,
        )
        is None
    )

    manifest_path.write_text(
        json.dumps(
            {
                "schema": "epyc.orchestrator.runtime_facts",
                "schema_version": 1,
                "runtime_stack": {"stack_numa_mode": "bogus"},
            }
        ),
        encoding="utf-8",
    )
    assert (
        read_runtime_stack_numa_mode(
            manifest_path=manifest_path,
            state_file=state_file,
        )
        is None
    )

    manifest_path.write_text(
        json.dumps(
            {
                "schema": "epyc.orchestrator.runtime_facts",
                "schema_version": 1,
                "runtime_stack": {"stack_numa_mode": "quarter"},
            }
        ),
        encoding="utf-8",
    )
    state_file.write_text("{}", encoding="utf-8")
    assert (
        read_runtime_stack_numa_mode(
            manifest_path=manifest_path,
            state_file=state_file,
        )
        is None
    )


def test_read_runtime_stack_selected_servers_accepts_valid_manifest(tmp_path: Path) -> None:
    stack_priors_path = _write_yaml(
        tmp_path / "stack_priors.yaml",
        """
stack_priors_version: 4
compiled_at: "2026-07-11T00:00:00Z"
status: live
source_artifacts: {}
roles: {}
""".strip()
        + "\n",
    )
    manifest_path = write_runtime_facts_manifest(
        state=_quarter_frontdoor_state(),
        launch_contracts={},
        stack_priors_path=stack_priors_path,
        stack_numa_mode=None,  # derive from realized quarters
        tmp_dir=tmp_path,
        repo_short_sha="abc1234",
        source="unit-test",
        pid_alive=_alive_only({111, 112, 113}),
    )

    servers = read_runtime_stack_selected_servers(
        manifest_path=manifest_path,
        state_file=tmp_path / "missing-state.json",
    )

    assert servers is not None
    ports = {server["port"] for server in servers}
    # Realized quarter ports are recorded; the dead full port never is.
    assert 8080 in ports
    assert 8070 not in ports
    assert (
        read_runtime_stack_numa_mode(
            manifest_path=manifest_path,
            state_file=tmp_path / "missing-state.json",
        )
        == "quarter"
    )


def test_read_runtime_stack_numa_mode_accepts_valid_manifest(tmp_path: Path) -> None:
    stack_priors_path = _write_yaml(
        tmp_path / "stack_priors.yaml",
        """
stack_priors_version: 4
compiled_at: "2026-07-11T00:00:00Z"
status: live
source_artifacts: {}
roles: {}
""".strip()
        + "\n",
    )
    manifest_path = write_runtime_facts_manifest(
        state={},
        launch_contracts={},
        stack_priors_path=stack_priors_path,
        stack_numa_mode="quarter",
        tmp_dir=tmp_path,
        repo_short_sha="abc1234",
        source="unit-test",
    )

    assert (
        read_runtime_stack_numa_mode(
            manifest_path=manifest_path,
            state_file=tmp_path / "missing-state.json",
        )
        == "quarter"
    )
