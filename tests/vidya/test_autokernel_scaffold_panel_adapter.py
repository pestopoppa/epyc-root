from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "vidya"))
sys.path.insert(0, str(ROOT / "scripts" / "vidya" / "adapters"))

import claim_tuple as ct  # noqa: E402
import autokernel_scaffold_panel as scaffold  # noqa: E402


def _pretty_sha(value: dict) -> str:
    return scaffold._pretty_sha(value)


def _cell(model: str, arm: str, speedup: float, ordinal: int) -> dict:
    cell_id = f"scaffold-{ordinal}-{arm}"
    evaluation = {
        "schema": scaffold.EVALUATION_SCHEMA, "authority": scaffold.AUTHORITY,
        "cell_id": cell_id, "pass_compilation": True, "pass_correctness": True,
        "valid_baseline_cases": 4, "valid_optimized_cases": 4,
        "average_speedup": speedup, "baseline_commit": "a" * 40,
        "baseline_tree_sha256": "b" * 64, "candidate_diff_sha256": "c" * 64,
        "evaluator": {"evaluator_sha256": "d" * 64},
        "actor_reported_performance_admitted": False,
        "campaign_authority": False, "ranking_authority": False,
        "champion_authority": False, "release_authority": False,
    }
    common_claim = {
        "claim_id": f"claim-{ordinal}", "device_id": "mi210_0",
        "campaign_id": "ak-le-3-fixture", "acquired_at": "2026-08-12T00:00:00+00:00",
        "state": "held",
    }
    cell = {
        "cell_id": cell_id, "model_id": model, "quant_id": "provider-native",
        "effort": "high", "scaffold": arm, "capture_mode": "measured",
        "planned_wall_seconds": 600.0, "observed_actor_wall_seconds": 590.0,
        "checkpoints": [],
        "evaluation_process": {
            "finished_at": f"2026-08-12T00:00:0{ordinal}+00:00"},
        "evaluation_sha256": _pretty_sha(evaluation), "evaluation": evaluation,
        "device_claim_open": {**common_claim, "released_at": None},
        "device_claim_released": {
            **common_claim, "released_at": f"2026-08-12T00:00:0{ordinal}+00:00"},
        "authority": scaffold.AUTHORITY,
    }
    cell["cell_receipt_sha256"] = scaffold._canonical_sha(cell)
    return cell


def panel(*, prospective: bool = True) -> dict:
    cells = [
        _cell("gpt-5.6-sol", scaffold.DIRECT, 0.99, 1),
        _cell("gpt-5.6-sol", scaffold.SPLIT, 1.39, 2),
        _cell("gpt-5.6-terra", scaffold.DIRECT, 1.01, 3),
        _cell("gpt-5.6-terra", scaffold.SPLIT, 1.00, 4),
    ]
    value = {
        "schema": scaffold.SOURCE_SCHEMA, "status": "complete",
        "authority": scaffold.AUTHORITY, "capture_mode": "measured",
        "experiment_id": "ak-le-3-fixture", "manifest_sha256": "e" * 64,
        "cells": cells,
        "constraints": {
            "same_model_within_scaffold_pair": True,
            "wall_time_matched_by_plan": True,
            "centralized_agentkernelarena_evaluation": True,
            "empirical_observation": True, "campaign_authority": False,
            "ranking_authority": False, "champion_authority": False,
            "release_authority": False,
        },
    }
    if not prospective:
        value["panel_sha256"] = scaffold._canonical_sha(value)
        return value
    value["producer"] = {
        "producer_id": scaffold.PRODUCER_ID, "path": scaffold.PRODUCER_PATH,
        "sha256": "f" * 64,
    }
    value["source_identity"] = {
        "repository": "/source/agent-kernel-arena", "base_commit": "a" * 40,
        "base_tree_sha256": "b" * 64,
    }
    value["evaluator_identity"] = {"evaluator_sha256": "d" * 64}
    value["belief_measurements"] = scaffold._expected(value)
    value["panel_sha256"] = scaffold._canonical_sha(value)
    return value


def _resign_cell(value: dict, index: int) -> None:
    cell = value["cells"][index]
    unsigned = dict(cell)
    unsigned.pop("cell_receipt_sha256", None)
    cell["cell_receipt_sha256"] = scaffold._canonical_sha(unsigned)


def _resign(value: dict) -> dict:
    unsigned = dict(value)
    unsigned.pop("panel_sha256", None)
    value["panel_sha256"] = scaffold._canonical_sha(unsigned)
    return value


def test_pre_hook_terminal_r1_is_not_backfilled() -> None:
    assert scaffold.native_rows(panel(prospective=False)) == ()


def test_four_cells_and_two_same_model_effects_project_diagnostic_only() -> None:
    rows = scaffold.native_rows(
        panel(), panel_locator="campaign:ak-le-3/panel.json",
        panel_file_sha256="1" * 64, attestation_present=True)
    tuples = [scaffold.project(row) for row in rows]
    assert len(tuples) == len({row.measurement_id for row in tuples}) == 6
    effects = [row for row in tuples if row.metric.startswith("implement_then_exploit")]
    assert {round(row.value, 6) for row in effects} == {
        round(1.39 / 0.99, 6), round(1.00 / 1.01, 6)}
    assert all(row.extra["diagnostic_only"] is True for row in tuples)
    assert all(row.extra["ranking_authority"] is False for row in tuples)
    assert all(ct.grade(row)[:2] == ("Witnessed", "Attested") for row in tuples)


@pytest.mark.parametrize("defect", [
    "panel_hash", "cell_hash", "evaluation_hash", "speedup", "row",
    "claim_release", "authority", "case_basis", "missing_arm",
])
def test_tampering_and_unmatched_panels_fail_closed(defect: str) -> None:
    value = panel()
    if defect == "panel_hash":
        value["panel_sha256"] = "0" * 64
    elif defect == "cell_hash":
        value["cells"][0]["cell_receipt_sha256"] = "0" * 64
        _resign(value)
    elif defect == "evaluation_hash":
        value["cells"][0]["evaluation_sha256"] = "0" * 64
        _resign_cell(value, 0); _resign(value)
    elif defect == "speedup":
        value["cells"][0]["evaluation"]["average_speedup"] = 9.0
        value["cells"][0]["evaluation_sha256"] = _pretty_sha(
            value["cells"][0]["evaluation"])
        _resign_cell(value, 0); _resign(value)
    elif defect == "row":
        value["belief_measurements"][0]["value"] = 9.0
        _resign(value)
    elif defect == "claim_release":
        value["cells"][0]["device_claim_released"]["released_at"] = None
        _resign_cell(value, 0); _resign(value)
    elif defect == "authority":
        value["constraints"]["ranking_authority"] = True
        _resign(value)
    elif defect == "case_basis":
        value["cells"][1]["evaluation"]["valid_baseline_cases"] = 3
        value["cells"][1]["evaluation"]["valid_optimized_cases"] = 3
        value["cells"][1]["evaluation_sha256"] = _pretty_sha(
            value["cells"][1]["evaluation"])
        _resign_cell(value, 1); _resign(value)
    else:
        value["cells"].pop()
        _resign(value)
    with pytest.raises(ct.ProjectionError):
        scaffold.native_rows(value)
