"""Evidence projections added by the 2026-08-12 Kernel-R&D re-audit."""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from dashboard import server


def _write(path: Path, value: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _signed(value: dict) -> dict:
    value = dict(value)
    value["receipt_sha256"] = server._canonical_receipt_hash(value)
    return value


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True,
                   capture_output=True, text=True)


def test_mainline_counter_uses_first_parent_merges_not_path_history(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "dashboard@example.invalid")
    _git(repo, "config", "user.name", "Dashboard Test")
    (repo / "scripts/kernel_rnd/autokernel").mkdir(parents=True)
    (repo / "scripts/kernel_rnd/autokernel/loop.py").write_text("A=1\n")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "base")
    _git(repo, "checkout", "-b", "feature")
    (repo / "scripts/kernel_rnd/autokernel/loop.py").write_text("A=2\n")
    _git(repo, "commit", "-am", "feature")
    _git(repo, "checkout", "main")
    (repo / "main-only").write_text("main\n")
    _git(repo, "add", "main-only")
    _git(repo, "commit", "-m", "main advance")
    _git(repo, "merge", "--no-ff", "feature", "-m", "merge feature")

    result = server._mainline_integration_summary(
        repo, "fixture", since="2020-01-01T00:00:00Z")

    assert result["available"] is True
    assert result["ref"] == "refs/heads/main"
    assert result["first_parent_merges"] == 1
    assert result["newest_merge"]["subject"] == "merge feature"
    assert "--first-parent" in result["method"]


def test_arena_progress_counts_checkpoint_evidence_without_claiming_liveness(
        tmp_path: Path) -> None:
    run = tmp_path / "campaigns/inf03-r1"
    audit = _signed({
        "schema": "epyc.autokernel.arena_available_source_campaign_audit.v1",
        "authority": "diagnostic_only",
    })
    _write(run / "audit.json", audit)
    manifest = _signed({
        "schema": "epyc.autokernel.arena_campaign_run_manifest.v1",
        "campaign_id": "inf03", "authority": "diagnostic_only",
        "available_source": True, "audit_receipt_sha256": audit["receipt_sha256"],
        "constraints": {"partial_results_rankable": False,
                        "aggregate_atomic_after_complete_matrix_only": True},
        "matrix": {"task_ids": ["task"],
                   "arm_ids": ["starting_state_baseline", "controller"],
                   "checkpoint_hours": [2, 8]},
    })
    _write(run / "campaign-manifest.json", manifest)
    _write(run / "execution/cells/001/checkpoint-receipt.json", _signed({
        "schema": "epyc.autokernel.arena_checkpoint.v1",
        "campaign_id": "inf03", "task_id": "task",
        "arm_id": "starting_state_baseline", "checkpoint_hours": None,
        "ended_at": "2026-08-12T01:00:00Z",
        "device_claim_released": {"released_at": "now"},
        "belief_receipt": {"belief_measurements": [{}, {}]},
    }))
    _write(run / "execution/cells/001/worker-request.json", {})
    _write(run / "execution/cells/002/worker-request.json", {})

    result = server._arena_campaign_progress(tmp_path)

    assert result["planned_checkpoints"] == 3
    assert result["completed_checkpoints"] == 1
    assert result["belief_measurement_count"] == 2
    assert result["terminal_aggregate_present"] is False
    assert result["rankable"] is False
    assert "no file marker is liveness" in result["note"]


def test_arena_progress_selects_newest_semantic_evidence_and_verifies_v2_windows(
        tmp_path: Path) -> None:
    def make_attempt(name: str, ended_at: str, *, tamper: bool = False) -> None:
        run = tmp_path / "campaigns" / name
        audit = _signed({
            "schema": "epyc.autokernel.arena_available_source_campaign_audit.v1",
            "authority": "availability_conditioned_diagnostic_only",
        })
        _write(run / "audit.json", audit)
        manifest = _signed({
            "schema": "epyc.autokernel.arena_campaign_run_manifest.v1",
            "campaign_id": "same-logical-id", "authority": "diagnostic_only",
            "available_source": True, "audit_receipt_sha256": audit["receipt_sha256"],
            "runner": {"attempt": name},
            "constraints": {"partial_results_rankable": False,
                            "aggregate_atomic_after_complete_matrix_only": True},
            "matrix": {"task_ids": ["task"],
                       "arm_ids": ["starting_state_baseline", "controller"],
                       "checkpoint_hours": [2]},
        })
        _write(run / "campaign-manifest.json", manifest)
        windows = []
        for ordinal in (1, 2):
            opened = {"claim_id": f"claim-{ordinal}", "campaign_id": "same-logical-id",
                      "device_id": "mi210_0", "acquired_at": f"t{ordinal}"}
            released = dict(opened, released_at=f"r{ordinal}")
            windows.append(_signed({
                "schema": "epyc.autokernel.arena_gpu_measurement_window.v1",
                "status": "complete", "device_claim_open": opened,
                "device_claim_released": released,
                "device_sampling": {"sample_count": 4, "duration_s": 1.25},
            }))
        checkpoint = _signed({
            "schema": "epyc.autokernel.arena_checkpoint.v2",
            "campaign_id": "same-logical-id", "task_id": "task",
            "arm_id": "starting_state_baseline", "checkpoint_hours": None,
            "ended_at": ended_at, "measurement_windows": windows,
            "evaluation": {"average_speedup": 1.1, "pass_compilation": True,
                           "pass_correctness": True, "valid_baseline_cases": 4,
                           "valid_optimized_cases": 4},
        })
        if tamper:
            checkpoint["evaluation"]["average_speedup"] = 99
        _write(run / "execution/cells/001/checkpoint-receipt.json", checkpoint)
        _write(run / "execution/cell-receipts/001.json", _signed({
            "schema": "epyc.autokernel.arena_cell_runner.v3",
            "campaign_id": "same-logical-id", "task_id": "task",
            "arm_id": "starting_state_baseline", "runs": [],
        }))

    make_attempt("r3", "2026-08-12T01:00:00Z")
    make_attempt("r4", "2026-08-12T02:00:00Z")
    make_attempt("tampered-r5", "2026-08-12T03:00:00Z", tamper=True)

    result = server._arena_campaign_progress(tmp_path)

    assert result["run_directory"] == "r4"
    assert result["completed_checkpoints"] == 1
    assert result["completed_cells"] == 1
    assert result["released_measurement_windows"] == 2
    assert result["measurement_samples"] == 8
    assert result["measurement_claimed_seconds"] == 2.5
    assert result["terminal_aggregate_present"] is False
    assert result["rankable"] is False
    assert [a["run_directory"] for a in result["attempts"]] == ["r4", "r3"]
    assert result["attempts"][0]["attempt_id"] != result["attempts"][1]["attempt_id"]
    assert result["rejected_attempts"] == 1


def test_arena_progress_exact_retraction_keeps_history_but_withholds_authority(
        tmp_path: Path) -> None:
    run = tmp_path / "campaigns/inf03-r4"
    audit = _signed({
        "schema": "epyc.autokernel.arena_available_source_campaign_audit.v1",
        "authority": "availability_conditioned_diagnostic_only",
    })
    _write(run / "audit.json", audit)
    manifest = _signed({
        "schema": "epyc.autokernel.arena_campaign_run_manifest.v1",
        "campaign_id": "inf03", "authority": "diagnostic_only",
        "available_source": True, "audit_receipt_sha256": audit["receipt_sha256"],
        "constraints": {"partial_results_rankable": False,
                        "aggregate_atomic_after_complete_matrix_only": True},
        "matrix": {"task_ids": ["task"],
                   "arm_ids": ["starting_state_baseline", "controller"],
                   "checkpoint_hours": [2]},
    })
    _write(run / "campaign-manifest.json", manifest)
    _write(run / "execution/cells/001/checkpoint-receipt.json", _signed({
        "schema": "epyc.autokernel.arena_checkpoint.v1",
        "campaign_id": "inf03", "task_id": "task",
        "arm_id": "starting_state_baseline", "checkpoint_hours": None,
        "ended_at": "2026-08-12T01:00:00Z",
        "device_claim_released": {"released_at": "now"},
    }))
    dispositions = _write(tmp_path / "dispositions.json", {
        "schema": "epyc.dashboard.arena_attempt_dispositions.v1",
        "attempts": [{
            "attempt_id": manifest["receipt_sha256"],
            "run_directory": "inf03-r4",
            "disposition": "invalid_diagnostic_history",
            "execution_state": "stopped", "resume_permitted": False,
            "ranking_authority": False, "release_authority": False,
            "reason": "intermediate evaluations escaped claim windows",
        }],
    })

    result = server._arena_campaign_progress(tmp_path, dispositions)

    assert result["available"] is True
    assert result["campaign_evidence_valid"] is False
    assert result["execution_state"] == "stopped"
    assert result["active"] is False
    assert result["rankable"] is False
    assert result["retraction"]["resume_permitted"] is False
    assert result["completed_checkpoints"] == 1
    assert result["attempts"][0]["disposition"] == "invalid_diagnostic_history"


def test_scaffold_panel_requires_hash_bound_evaluation(tmp_path: Path) -> None:
    panel_dir = tmp_path / "campaigns/ak-le-3/panel"
    evaluation = {
        "schema": "epyc.autokernel.ak_le_3_arena_evaluation.v1",
        "cell_id": "cell-a", "average_speedup": 1.25,
        "pass_compilation": True, "pass_correctness": True,
        "valid_baseline_cases": 4, "valid_optimized_cases": 4,
    }
    encoded = json.dumps(evaluation).encode()
    evaluation_path = panel_dir / "cells/001-cell-a/arena-evaluation.json"
    evaluation_path.parent.mkdir(parents=True)
    evaluation_path.write_bytes(encoded)
    _write(panel_dir / "panel.json", {
        "schema": "epyc.autokernel.ak_le_3_scaffold_panel.v1",
        "experiment_id": "ak-le-3", "status": "complete",
        "authority": "diagnostic_scaffold_observation_only", "capture_mode": "measured",
        "constraints": {"ranking_authority": False, "campaign_authority": False},
        "cells": [{"cell_id": "cell-a", "model_id": "model", "effort": "high",
                   "scaffold": "direct_implement", "evaluation_sha256": hashlib.sha256(encoded).hexdigest(),
                   "device_claim_released": {"released_at": "now"}}],
    })

    result = server._scaffold_panel_summary(tmp_path)

    assert result["status"] == "complete"
    assert result["cells"][0]["average_speedup"] == 1.25
    assert result["cells"][0]["evaluation_hash_matches"] is True
    assert result["belief_measurement_count"] == 0
    assert result["ranking_authority"] is False


def test_rocm_diagnostics_preserve_belief_counts_and_shape_specificity(
        tmp_path: Path) -> None:
    _write(tmp_path / "campaigns/rvp/receipt.json", {
        "schema": "epyc.rvp_t0_1_saturation_probe.v1", "campaign_id": "rvp",
        "status": "complete", "workload": {"throughput_tflops": 41.8},
        "nominal_sclk_sample_fraction": .99, "max_power_w": 197, "power_cap_w": 300,
        "belief_measurements": [{}, {}, {}, {}],
    })
    _write(tmp_path / "campaigns/bh/receipt.json", {
        "schema": "epyc.ak_bh_1_gemm_baseline_compare.v1", "campaign_id": "bh",
        "status": "complete", "belief_measurements": [{}, {}],
        "comparisons": [{"hipblaslt_over_rocblas": .8},
                        {"hipblaslt_over_rocblas": 1.2}],
    })
    _write(tmp_path / "probes/profile/receipt.json", {
        "schema": "epyc.autokernel.rocprofv1_attribution.v1", "status": "passed",
    })

    result = server._rocm_diagnostics_summary(tmp_path)

    assert result["rvp"]["belief_measurement_count"] == 4
    assert result["baseline_honesty"]["hipblaslt_wins"] == 1
    assert result["baseline_honesty"]["ratio_min"] == .8
    assert result["baseline_honesty"]["ratio_max"] == 1.2
    assert result["profiles"][0]["belief_measurement_count"] == 0
    assert "do not rank" in result["note"]
