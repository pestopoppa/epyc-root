"""Tests for AutoPilot preflight diagnostics."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import yaml

from src.autopilot_core.journal_reconstruction import reconstruct_archive_from_journal_rows
from src.roles import Role
from scripts.autopilot import preflight_audit as _MOD

_ROOT = Path(__file__).resolve().parents[2]


def _registry_server_mode() -> dict[str, Any]:
    return yaml.safe_load(
        (_ROOT / "orchestration" / "model_registry.yaml").read_text(encoding="utf-8")
    )["server_mode"]


def _canonical(role: str) -> str:
    """Canonical role name, exactly as the preflight fallback spells it."""
    return str(Role.from_string(role) or role)


def _registry_host_of(role: str) -> str:
    """The server_mode row that physically hosts ``role`` (shared_with / alias_of)."""
    server_mode = _registry_server_mode()
    for host, row in server_mode.items():
        if row.get("alias_of"):
            continue
        if host == role or role in (row.get("shared_with") or []):
            return host
    raise AssertionError(f"registry declares no host server for {role!r}")


def _registry_host_groups() -> dict[int, str]:
    """port -> '/'-joined canonical role group of every physical host row.

    A host row's group is the host itself, its ``shared_with`` roles and every
    ``alias_of`` row pointing at it — i.e. every role that one process serves.
    """
    server_mode = _registry_server_mode()
    groups: dict[int, str] = {}
    for host, row in server_mode.items():
        if row.get("alias_of") or not row.get("port"):
            continue
        members = {host, *(row.get("shared_with") or [])}
        members |= {k for k, v in server_mode.items() if v.get("alias_of") == host}
        groups[int(row["port"])] = "/".join(sorted({_canonical(m) for m in members}))
    return groups


def _journal_row(
    trial_id: int,
    *,
    quality: float = 1.0,
    speed: float = 40.0,
    timestamp: str | None = None,
) -> dict[str, Any]:
    return {
        "trial_id": trial_id,
        "timestamp": timestamp or f"2026-06-14T00:00:0{trial_id}Z",
        "species": "unit",
        "action_type": "seed_batch",
        "tier": 1,
        "quality": quality,
        "speed": speed,
        "cost": 0.2,
        "reliability": 0.9,
        "pareto_status": "frontier",
    }


def _archive(rows: list[dict[str, Any]]) -> dict[str, Any]:
    archive = reconstruct_archive_from_journal_rows(rows, None, current_run_only=False)
    assert archive is not None
    return archive


def _empty_frontier_state(*, scoring_schedule_id: str = "judge-tail-test") -> dict[str, Any]:
    boundary = 1781481600.0
    return {
        "trial_counter": 2,
        "pareto_objective_policy": "legacy_4d_v1",
        "eval_execution_instrument_id": "resource-lanes-test",
        "eval_scoring_schedule_id": scoring_schedule_id,
        "pareto_epoch_ts": boundary,
        "pareto_exclude_before_ts": boundary,
        "quality_exclude_before_ts": boundary,
        "_allow_empty_frontier_rebase": True,
        "_allow_empty_frontier_rebase_note": "Operator-ratified test boundary.",
        "eval_instrument_empty_frontier_bootstrap": {
            "status": "pending",
            "opened_at": "2026-06-15T00:00:00Z",
            "objective_policy": "legacy_4d_v1",
            "execution_instrument_id": "resource-lanes-test",
            "scoring_schedule_id": scoring_schedule_id,
            "completion_condition": "first post-boundary Pareto point",
        },
    }


def test_model_server_targets_derive_from_stack_priors(tmp_path: Path) -> None:
    priors = tmp_path / "stack_priors.yaml"
    priors.write_text(
        """
roles:
  frontdoor:
    deployment_status: live_stack
    serving:
      endpoint: http://localhost:8070
  coder_escalation:
    deployment_status: live_stack
    serving:
      endpoint: http://localhost:8070
  worker_vision:
    deployment_status: live_stack
    serving:
      endpoint: http://localhost:8086
  reap_25b_frontdoor:
    deployment_status: benchmark_or_candidate
    serving:
      endpoint: http://localhost:8196
""",
        encoding="utf-8",
    )

    targets = set(_MOD._model_server_targets(priors, "http://orchestrator.local:8001"))

    assert ("API", "http://orchestrator.local:8001/health") in targets
    assert ("coder_escalation/frontdoor", "http://localhost:8070/health") in targets
    assert ("worker_vision", "http://localhost:8086/health") in targets
    assert all("8196" not in health_url for _, health_url in targets)


def test_model_server_targets_fallback_is_current(tmp_path: Path) -> None:
    """Drift canary: with no stack_priors, preflight probes the DECLARED launch
    manifest, so this asserts the fallback still describes the current stack.

    The fallback reads ``orchestration/launch_manifest.yaml`` (HOT/WARM_SERVERS);
    the expectation is derived from an INDEPENDENT source, the registry's
    ``server_mode`` (each physical host row plus its ``shared_with`` roles and
    ``alias_of`` rows), so a manifest/registry disagreement still fails here
    while a ratified lineup change moves both sides together. (It used to be a
    literal list; the operator-signed 2026-09-22 cutover, orchestrator 860b0b2d,
    folded worker_general/worker_math/toolrunner onto frontdoor's :8070 fleet and
    ingest_long_context onto architect_general's :8083, and every literal went
    stale at once.)

    Retired ports stay literal on purpose: they are history, not topology —
    :8071, the 2026-08-01 :8087 vision_escalation server (now an alias on
    worker_vision's :8086), and the 2026-09-22 :8072 worker server.
    """
    targets = _MOD._model_server_targets(tmp_path / "missing.yaml", "http://localhost:8002")
    health_urls = {health_url for _, health_url in targets}

    assert ("API", "http://localhost:8002/health") in targets

    host_groups = _registry_host_groups()
    # Non-vacuity: the registry must still declare the hosts this canary is about.
    for role in ("frontdoor", "architect_general", "worker_vision", "worker_general"):
        assert int(_registry_server_mode()[_registry_host_of(role)]["port"]) in host_groups
    for port, group in host_groups.items():
        assert (group, f"http://localhost:{port}/health") in targets, (
            f"fallback does not probe registry host :{port} as {group!r}"
        )
    # Alias collapse: worker_general shares frontdoor's process (one target, not two).
    assert _registry_host_of("worker_general") == _registry_host_of("frontdoor")

    for retired_port in (8071, 8072, 8087):
        assert f"http://localhost:{retired_port}/health" not in health_urls
    # embedding-mode roles are excluded from health probing.
    assert "http://localhost:8090/health" not in health_urls


def test_model_server_targets_fallback_follows_manifest_without_literal_port_list(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        _MOD,
        "HOT_SERVERS",
        [{"port": 9001, "roles": ["frontdoor", "coder_escalation"]}],
    )
    monkeypatch.setattr(
        _MOD,
        "WARM_SERVERS",
        [{"port": 9002, "roles": ["worker_general", "embedder"]}],
    )
    monkeypatch.setattr(
        _MOD,
        "ROLE_LAUNCH_META",
        {
            "frontdoor": {"mode": "default"},
            "worker_general": {"mode": "worker_pool"},
            "embedder": {"mode": "embedding"},
        },
    )

    targets = _MOD._model_server_targets(tmp_path / "missing.yaml", "http://localhost:8002")

    assert targets == [
        ("API", "http://localhost:8002/health"),
        ("coder_escalation/frontdoor", "http://localhost:9001/health"),
        ("worker_general", "http://localhost:9002/health"),
    ]


def test_model_server_targets_fallback_excludes_embedding_mode_roles_from_manifest(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        _MOD,
        "HOT_SERVERS",
        [{"port": 9001, "roles": ["frontdoor"]}],
    )
    monkeypatch.setattr(
        _MOD,
        "WARM_SERVERS",
        [{"port": 9002, "roles": ["worker_general", "embedder", "embedder_1"]}],
    )
    monkeypatch.setattr(
        _MOD,
        "ROLE_LAUNCH_META",
        {
            "frontdoor": {"mode": "default"},
            "worker_general": {"mode": "worker_pool"},
            "embedder": {"mode": "embedding"},
            "embedder_1": {"mode": "embedding"},
        },
    )

    targets = _MOD._model_server_targets(tmp_path / "missing.yaml", "http://localhost:8002")

    assert targets == [
        ("API", "http://localhost:8002/health"),
        ("frontdoor", "http://localhost:9001/health"),
        ("worker_general", "http://localhost:9002/health"),
    ]


def test_model_server_targets_fallback_canonicalizes_worker_aliases(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        _MOD,
        "HOT_SERVERS",
        [{"port": 9001, "roles": ["frontdoor"]}],
    )
    monkeypatch.setattr(
        _MOD,
        "WARM_SERVERS",
        [{"port": 9002, "roles": ["worker_explore", "worker_fast", "embedder"]}],
    )
    monkeypatch.setattr(
        _MOD,
        "ROLE_LAUNCH_META",
        {
            "frontdoor": {"mode": "default"},
            "worker_general": {"mode": "worker_pool"},
            "worker_fast": {"mode": "worker_pool"},
            "embedder": {"mode": "embedding"},
        },
    )

    targets = _MOD._model_server_targets(tmp_path / "missing.yaml", "http://localhost:8002")

    assert targets == [
        ("API", "http://localhost:8002/health"),
        ("frontdoor", "http://localhost:9001/health"),
        ("worker_general", "http://localhost:9002/health"),
    ]


def test_model_server_targets_fallback_when_live_records_have_no_health_urls(
    tmp_path: Path,
) -> None:
    priors = tmp_path / "stack_priors.yaml"
    priors.write_text(
        """
roles:
  frontdoor:
    deployment_status: live_stack
    serving:
      endpoint: not-a-url
  worker_general:
    deployment_status: live_stack
    serving: {}
""",
        encoding="utf-8",
    )

    targets = _MOD._model_server_targets(priors, "http://localhost:8002")
    health_urls = {health_url for _, health_url in targets}

    # Both live records are unusable, so preflight must fall back to the declared
    # topology and still probe the process that serves each of them. The ports
    # are the registry's (worker_general is hosted on frontdoor's fleet since the
    # 2026-09-22 cutover; it used to be a literal :8072).
    assert ("API", "http://localhost:8002/health") in targets
    server_mode = _registry_server_mode()
    for role in ("frontdoor", "worker_general"):
        port = int(server_mode[_registry_host_of(role)]["port"])
        assert f"http://localhost:{port}/health" in health_urls, role
    assert "http://not-a-url/health" not in health_urls
    assert "http://localhost:8090/health" not in health_urls


def test_audit_stack_change_gate_runs_canonical_command(monkeypatch) -> None:
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs))
        return SimpleNamespace(returncode=0, stdout="summary: ok\n", stderr="")

    monkeypatch.setattr(_MOD.subprocess, "run", fake_run)

    assert _MOD.audit_stack_change_gate() is True
    assert calls == [
        (
            _MOD.STACK_CHANGE_GATE_COMMAND,
            {
                "cwd": _MOD.REPO_ROOT,
                "capture_output": True,
                "text": True,
                "timeout": _MOD.STACK_CHANGE_GATE_TIMEOUT_S,
            },
        )
    ]


def test_audit_stack_change_gate_blocks_on_failure(monkeypatch) -> None:
    def fake_run(cmd, **kwargs):
        return SimpleNamespace(
            returncode=1,
            stdout="summary: failed\n",
            stderr="promotion gate rejected stack change\n",
        )

    monkeypatch.setattr(_MOD.subprocess, "run", fake_run)

    assert _MOD.audit_stack_change_gate() is False


def test_audit_stack_change_gate_fails_closed_on_timeout(monkeypatch) -> None:
    def fake_run(cmd, **kwargs):
        raise _MOD.subprocess.TimeoutExpired(cmd, kwargs["timeout"])

    monkeypatch.setattr(_MOD.subprocess, "run", fake_run)

    assert _MOD.audit_stack_change_gate() is False


def test_audit_blacklist_detects_superseded_corrupted_sources(
    tmp_path: Path,
    monkeypatch,
) -> None:
    script_dir = tmp_path / "scripts" / "autopilot"
    orchestration_dir = tmp_path / "orchestration"
    script_dir.mkdir(parents=True)
    orchestration_dir.mkdir()
    (script_dir / "failure_blacklist.yaml").write_text(
        """
blacklist:
  - reason: manual
    source_trial: -1
  - reason: contaminated
    source_trial: 2
""",
        encoding="utf-8",
    )
    rows = [
        {"trial_id": 2, "bug_corrupted_by": ""},
        {
            "type": "supersession",
            "target_trial_ids": [2],
            "fields": {"bug_corrupted_by": "resource_contention"},
        },
    ]
    (orchestration_dir / "autopilot_journal_1.jsonl").write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(_MOD, "SCRIPT_DIR", script_dir)

    assert _MOD.audit_blacklist() is False


def test_archive_authority_diagnostic_matches_reconstructed_state() -> None:
    rows = [_journal_row(1, quality=1.2)]
    archive = _archive(rows)
    state = {"trial_counter": 2, "pareto_archive": archive}

    diagnostic = _MOD.archive_authority_diagnostic(state, rows)

    assert diagnostic["status"] == "match"
    assert diagnostic["state_archive_present"] is True
    assert diagnostic["state_entry_count"] == 1
    assert diagnostic["journal_entry_count"] == 1
    assert diagnostic["state_frontier_count"] == 1
    assert diagnostic["journal_frontier_count"] == 1
    assert diagnostic["snapshot_tail_trial_count"] == 0
    assert diagnostic["snapshot_tail_max_trial_id"] is None
    assert diagnostic["snapshot_journal_max_trial_id"] is None


def test_archive_authority_diagnostic_accepts_missing_state_cache() -> None:
    rows = [_journal_row(1, quality=1.2)]
    state = {"trial_counter": 2}

    diagnostic = _MOD.archive_authority_diagnostic(state, rows)

    assert diagnostic["status"] == "match"
    assert diagnostic["state_archive_present"] is False
    assert diagnostic["state_entry_count"] == 0
    assert diagnostic["journal_entry_count"] == 1
    assert diagnostic["state_frontier_count"] == 0
    assert diagnostic["journal_frontier_count"] == 1


def test_archive_authority_diagnostic_honors_epoch_exclusion() -> None:
    rows = [
        _journal_row(1, quality=2.0, timestamp="2026-06-14T00:00:01Z"),
        _journal_row(2, quality=1.2, timestamp="2026-06-15T00:00:01Z"),
    ]
    state = {
        "trial_counter": 3,
        "pareto_exclude_before_ts": 1781481600.0,
    }

    diagnostic = _MOD.archive_authority_diagnostic(state, rows)

    assert diagnostic["status"] == "match"
    assert diagnostic["journal_entry_count"] == 1
    assert diagnostic["journal_frontier_count"] == 1
    assert diagnostic["replay_kwargs"] == {"exclude_before_ts": 1781481600.0}


def test_archive_authority_accepts_ratified_empty_current_era() -> None:
    rows = [_journal_row(1, timestamp="2026-06-14T00:00:01Z")]

    diagnostic = _MOD.archive_authority_diagnostic(
        _empty_frontier_state(),
        rows,
    )

    assert diagnostic["status"] == "match"
    assert diagnostic["authority_mode"] == "authorized_empty_current_era"
    assert diagnostic["journal_entry_count"] == 0
    assert diagnostic["empty_frontier_bootstrap"]["authorized"] is True
    assert diagnostic["empty_frontier_bootstrap"]["current_era_trial_row_count"] == 0


def test_archive_authority_accepts_admitted_baseline_pending_frontier() -> None:
    rows = [_journal_row(1, timestamp="2026-06-14T00:00:01Z")]
    state = _empty_frontier_state()
    state["eval_instrument_empty_frontier_bootstrap"]["status"] = (
        "baseline_admitted_frontier_pending"
    )

    diagnostic = _MOD.archive_authority_diagnostic(state, rows)

    assert diagnostic["status"] == "match"
    assert diagnostic["authority_mode"] == "authorized_empty_current_era"
    assert diagnostic["empty_frontier_bootstrap"]["authorized"] is True


def test_archive_authority_rejects_incomplete_empty_frontier_marker() -> None:
    rows = [_journal_row(1, timestamp="2026-06-14T00:00:01Z")]
    state = _empty_frontier_state()
    state["_allow_empty_frontier_rebase"] = False

    diagnostic = _MOD.archive_authority_diagnostic(state, rows)

    assert diagnostic["status"] == "journal_unreconstructable"
    assert diagnostic["empty_frontier_bootstrap"]["authorized"] is False
    assert "_allow_empty_frontier_rebase is not true" in diagnostic["warnings"]


def test_archive_authority_rejects_mismatched_empty_frontier_marker() -> None:
    rows = [_journal_row(1, timestamp="2026-06-14T00:00:01Z")]
    state = _empty_frontier_state()
    state["eval_instrument_empty_frontier_bootstrap"]["scoring_schedule_id"] = "stale"

    diagnostic = _MOD.archive_authority_diagnostic(state, rows)

    assert diagnostic["status"] == "journal_unreconstructable"
    assert any("scoring_schedule_id" in warning for warning in diagnostic["warnings"])


def test_archive_authority_rejects_hidden_current_era_objective_row(
    monkeypatch,
) -> None:
    rows = [_journal_row(2, timestamp="2026-06-15T00:00:01Z")]
    monkeypatch.setattr(_MOD, "reconstruct_archive_from_journal_rows", lambda *a, **k: None)

    diagnostic = _MOD.archive_authority_diagnostic(_empty_frontier_state(), rows)

    assert diagnostic["status"] == "journal_unreconstructable"
    assert diagnostic["empty_frontier_bootstrap"]["current_era_objective_row_count"] == 1
    assert any("reconstructable current-era" in warning for warning in diagnostic["warnings"])


def test_archive_authority_rejects_empty_bootstrap_with_state_archive() -> None:
    old_rows = [_journal_row(1, timestamp="2026-06-14T00:00:01Z")]
    state = _empty_frontier_state()
    state["pareto_archive"] = _archive(old_rows)

    diagnostic = _MOD.archive_authority_diagnostic(state, old_rows)

    assert diagnostic["status"] == "journal_unreconstructable"
    assert "state pareto_archive is present" in diagnostic["warnings"]


def test_archive_authority_diagnostic_ignores_nonsemantic_entry_metadata() -> None:
    rows = [_journal_row(1, quality=1.2)]
    archive = json.loads(json.dumps(_archive(rows)))
    for entries in (
        archive["all_entries"],
        archive["frontier"],
        archive["frontiers_by_tier"]["1"],
    ):
        entries[0].update(
            {
                "config_fingerprint": "",
                "git_tag": "",
                "n_reproductions": 1,
                "species": "runtime-only-label",
                "timestamp": "2026-06-14T00:00:01.001Z",
            }
        )
    state = {"trial_counter": 2, "pareto_archive": archive}

    diagnostic = _MOD.archive_authority_diagnostic(state, rows)

    assert diagnostic["status"] == "match"


def test_archive_authority_diagnostic_detects_archive_drift() -> None:
    rows = [_journal_row(1, quality=1.2)]
    archive = json.loads(json.dumps(_archive(rows)))
    archive["frontier"][0]["objectives"][0] = 0.5
    state = {"trial_counter": 2, "pareto_archive": archive}

    diagnostic = _MOD.archive_authority_diagnostic(state, rows)

    assert diagnostic["status"] == "drift"
    assert diagnostic["state_entry_count"] == 1
    assert diagnostic["journal_entry_count"] == 1


def test_archive_authority_diagnostic_flags_journal_ahead_of_state() -> None:
    rows = [_journal_row(1)]
    state = {"trial_counter": 1, "pareto_archive": _archive(rows)}

    diagnostic = _MOD.archive_authority_diagnostic(state, rows)

    assert diagnostic["status"] == "drift"
    assert diagnostic["warnings"] == [
        "journal max trial 1 is not below state trial_counter 1"
    ]


def test_audit_archive_authority_uses_state_and_journal_paths(
    tmp_path: Path,
    monkeypatch,
) -> None:
    rows = [_journal_row(1)]
    state_path = tmp_path / "autopilot_state.json"
    journal_path = tmp_path / "autopilot_journal.jsonl"
    state_path.write_text(
        json.dumps({"trial_counter": 2, "pareto_archive": _archive(rows)}),
        encoding="utf-8",
    )
    journal_path.write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(_MOD, "STATE_PATH", state_path)
    monkeypatch.setattr(_MOD, "JOURNAL_PATH", journal_path)

    assert _MOD.audit_archive_authority() is True

    state_path.write_text(
        json.dumps(
            {
                "trial_counter": 2,
                "pareto_archive": {"frontier": [], "all_entries": []},
            }
        ),
        encoding="utf-8",
    )

    assert _MOD.audit_archive_authority() is False


def test_load_jsonl_includes_autopilot_journal_rollover_batches(tmp_path: Path) -> None:
    journal_path = tmp_path / "autopilot_journal.jsonl"
    journal_path.write_text(
        json.dumps({"trial_id": 999}) + "\n",
        encoding="utf-8",
    )
    (tmp_path / "autopilot_journal_1.jsonl").write_text(
        json.dumps({"trial_id": 1000}) + "\n",
        encoding="utf-8",
    )
    (tmp_path / "autopilot_journal_2.jsonl").write_text(
        json.dumps({"trial_id": 2000}) + "\n",
        encoding="utf-8",
    )

    assert [row["trial_id"] for row in _MOD._load_jsonl(journal_path)] == [
        999,
        1000,
        2000,
    ]


def test_load_jsonl_accepts_journal_directory_with_rollover_batches(
    tmp_path: Path,
) -> None:
    (tmp_path / "autopilot_journal_10.jsonl").write_text(
        json.dumps({"trial_id": 10}) + "\n",
        encoding="utf-8",
    )
    (tmp_path / "autopilot_journal_1.jsonl").write_text(
        json.dumps({"trial_id": 1}) + "\n",
        encoding="utf-8",
    )
    (tmp_path / "autopilot_journal.jsonl").write_text(
        json.dumps({"trial_id": 0}) + "\n",
        encoding="utf-8",
    )

    assert [row["trial_id"] for row in _MOD._load_jsonl(tmp_path)] == [0, 1, 10]


def test_load_jsonl_keeps_explicit_batch_path_scoped(tmp_path: Path) -> None:
    (tmp_path / "autopilot_journal.jsonl").write_text(
        json.dumps({"trial_id": 999}) + "\n",
        encoding="utf-8",
    )
    batch_path = tmp_path / "autopilot_journal_1.jsonl"
    batch_path.write_text(
        json.dumps({"trial_id": 1000}) + "\n",
        encoding="utf-8",
    )

    assert [row["trial_id"] for row in _MOD._load_jsonl(batch_path)] == [1000]


def test_audit_archive_authority_accepts_invalidated_snapshot_with_full_replay(
    tmp_path: Path,
    monkeypatch,
) -> None:
    rows = [_journal_row(1)]
    state_path = tmp_path / "autopilot_state.json"
    journal_path = tmp_path / "autopilot_journal.jsonl"
    state_path.write_text(
        json.dumps({"trial_counter": 2, "pareto_archive": _archive(rows)}),
        encoding="utf-8",
    )
    journal_path.write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(_MOD, "STATE_PATH", state_path)
    monkeypatch.setattr(_MOD, "JOURNAL_PATH", journal_path)
    monkeypatch.setattr(
        _MOD,
        "build_snapshot_replay_diagnostic",
        lambda rows, events: SimpleNamespace(
            bounded_replay_readiness="prefix_invalidated",
            status="archive_prefix_drift",
        ),
    )

    assert _MOD.audit_archive_authority() is True
