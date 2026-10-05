"""Tests for the unified orch CLI helpers."""

from __future__ import annotations

from pathlib import Path

import yaml

from src import cli_orch
from src.cli_orch import _fallback_status_targets, _stack_status_targets
from src.roles import Role

_RETIRED_ARCHITECT_ROLE = "architect_" "coding"
_ROOT = Path(__file__).resolve().parents[2]


def _registry_server_mode() -> dict:
    return yaml.safe_load(
        (_ROOT / "orchestration" / "model_registry.yaml").read_text(encoding="utf-8")
    )["server_mode"]


def _registry_host_groups() -> dict[str, tuple[str, int]]:
    """host row -> (canonical '/'-joined role group, port) for each physical host.

    Derived from the registry's ``server_mode`` — an INDEPENDENT source from the
    launch manifest the fallback reads — so a registry/manifest disagreement
    still fails while a ratified lineup change moves both sides together. A
    host's group is the host, its ``shared_with`` roles and every ``alias_of``
    row pointing at it, canonicalized the way the fallback spells them
    (``Role.from_string``; e.g. worker_explore -> worker_general).
    """
    server_mode = _registry_server_mode()
    groups: dict[str, tuple[str, int]] = {}
    for host, row in server_mode.items():
        if row.get("alias_of") or not row.get("port"):
            continue
        members = {host, *(row.get("shared_with") or [])}
        members |= {k for k, v in server_mode.items() if v.get("alias_of") == host}
        canonical = {str(Role.from_string(m) or m) for m in members}
        groups[host] = ("/".join(sorted(canonical)), int(row["port"]))
    return groups


def _host_of(role: str) -> str:
    for host, row in _registry_server_mode().items():
        if row.get("alias_of"):
            continue
        if host == role or role in (row.get("shared_with") or []):
            return host
    raise AssertionError(f"registry declares no host row for {role!r}")


def test_stack_status_targets_group_live_roles_by_port(tmp_path: Path) -> None:
    priors = tmp_path / "stack_priors.yaml"
    priors.write_text(
        """
roles:
  architect_general:
    deployment_status: live_stack
    serving:
      endpoint: http://localhost:8083
  coder_escalation:
    deployment_status: live_stack
    serving:
      endpoint: http://localhost:8070
  frontdoor:
    deployment_status: live_stack
    serving:
      endpoint: http://localhost:8070
  ingest_long_context:
    deployment_status: live_stack
    serving:
      endpoint: http://localhost:notaport
      ports: [8085]
  reap_25b_frontdoor:
    deployment_status: benchmark_or_candidate
    serving:
      endpoint: http://localhost:8090
""",
        encoding="utf-8",
    )

    targets = _stack_status_targets(priors)

    assert targets == [
        ("coder_escalation/frontdoor", 8070),
        ("architect_general", 8083),
        ("ingest_long_context", 8085),
    ]


def test_stack_status_targets_fallback_excludes_retired_ports(tmp_path: Path) -> None:
    targets = _stack_status_targets(tmp_path / "missing.yaml")

    assert (_RETIRED_ARCHITECT_ROLE, 8084) not in targets
    groups = _registry_host_groups()
    # frontdoor's :8070 fleet hosts the worker lane since the 2026-09-22 cutover
    # (orchestrator 860b0b2d); architect_general's :8083 hosts coder_escalation
    # and ingest_long_context; architect_critic has its own :8074 process;
    # vision_escalation is an alias on worker_vision's :8086.
    for host in ("frontdoor", "architect_general", "architect_critic", "worker_vision"):
        assert groups[host] in targets, host
    # Retired ports (history, deliberately literal): the :8087 vision_escalation
    # server (2026-08-01) and the :8072 worker server (2026-09-22). The embedder
    # :8090 is excluded by mode.
    assert all(port not in (8072, 8087, 8090) for _, port in targets)


def test_fallback_status_targets_derive_alias_groups_from_manifest() -> None:
    """Every registry host row's alias group is one fallback status target.

    Was a literal list pinned to the 2026-08-01 lineup (incl. a separate
    ``toolrunner/worker_general/worker_math`` server on :8072); now derived from
    registry server_mode so it survives the next ratified cutover.
    """
    targets = _fallback_status_targets()
    groups = _registry_host_groups()

    # Non-vacuity: the roles this test is about must still be registry-hosted.
    assert len(groups) >= 4
    for role in ("worker_general", "worker_math", "toolrunner", "coder_escalation"):
        assert groups[_host_of(role)][0].split("/").count(role) == 1, role
    for host, target in groups.items():
        assert target in targets, f"{host}: {target} missing from {targets}"
    # worker_explore is canonicalized, never surfaced under its alias name.
    assert all("worker_explore" not in name for name, _ in targets)
    assert all(port not in (8072, 8087, 8090) for _, port in targets)


def test_fallback_status_targets_follow_manifest_without_literal_port_list(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        cli_orch,
        "HOT_SERVERS",
        [{"port": 9001, "roles": ["frontdoor", "coder_escalation"]}],
    )
    monkeypatch.setattr(
        cli_orch,
        "WARM_SERVERS",
        [{"port": 9002, "roles": ["worker_general", "embedder"]}],
    )
    monkeypatch.setattr(
        cli_orch,
        "ROLE_LAUNCH_META",
        {
            "frontdoor": {"mode": "default"},
            "worker_general": {"mode": "worker_pool"},
            "embedder": {"mode": "embedding"},
        },
    )

    targets = _fallback_status_targets()

    assert targets == [
        ("coder_escalation/frontdoor", 9001),
        ("worker_general", 9002),
    ]


def test_fallback_status_targets_exclude_embedding_mode_roles_from_manifest(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        cli_orch,
        "HOT_SERVERS",
        [{"port": 9001, "roles": ["frontdoor"]}],
    )
    monkeypatch.setattr(
        cli_orch,
        "WARM_SERVERS",
        [{"port": 9002, "roles": ["worker_general", "embedder", "embedder_1"]}],
    )
    monkeypatch.setattr(
        cli_orch,
        "ROLE_LAUNCH_META",
        {
            "frontdoor": {"mode": "default"},
            "worker_general": {"mode": "worker_pool"},
            "embedder": {"mode": "embedding"},
            "embedder_1": {"mode": "embedding"},
        },
    )

    targets = _fallback_status_targets()

    assert targets == [
        ("frontdoor", 9001),
        ("worker_general", 9002),
    ]
