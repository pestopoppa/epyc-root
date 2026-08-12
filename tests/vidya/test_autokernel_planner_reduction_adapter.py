from __future__ import annotations

import copy
import hashlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402
from adapters import autokernel_planner_reduction as planner  # noqa: E402


def _resign(value: dict, field: str) -> dict:
    unsigned = dict(value)
    unsigned.pop(field, None)
    value[field] = planner._canonical_sha(unsigned)
    return value


def _hypothesis(name: str) -> dict:
    return {
        "mechanism": f"Mechanism {name}",
        "target_surface": "gfx90a Q4_K",
        "falsifiable_counter": f"Counter {name}",
        "predicted_direction": "decode time decreases",
    }


def fixture() -> tuple[dict, dict, dict, dict]:
    arms = [
        {"cell_id": "plan-model-high-control", "model_id": "model-a",
         "quant_id": "provider-native", "effort": "high",
         "target_context_mode": "absent"},
        {"cell_id": "plan-model-xhigh-target", "model_id": "model-a",
         "quant_id": "provider-native", "effort": "xhigh",
         "target_context_mode": "rendered_context_line"},
    ]
    contract = {
        "schema": planner.CONTRACT_SCHEMA, "authority": planner.RUNNER_AUTHORITY,
        "experiment_id": "ak-le-planner-fixture",
        "fixed": {"retrieval_context_sha256": "1" * 64},
        "planner_arms": arms,
        "direction_predictions": [{
            "model_id": "model-a", "quant_id": "provider-native",
            "direction": "higher_effort_increases_search_persistence",
            "rationale": "fixture predeclaration",
        }],
        "scaffold_arms": [], "prior_hypothesis_sha256": [],
        "prefilter": {"ref": "/fixture/prefilter.json", "sha256": ""},
        "constraints": {
            "campaign_1_authority": False, "champion_authority": False,
            "model_or_kernel_invoked_by_contract": False,
            "ranking_authority": False, "release_authority": False,
            "target_value_is_manifest_field": False,
        },
    }
    prefilter = {
        "schema": planner.PREFILTER_SCHEMA, "authority": planner.AUTHORITY,
        "algorithm": planner.ALGORITHM,
        "producer": {"ref": planner.PREFILTER_PRODUCER_REF, "sha256": "2" * 64},
        "prior_hypothesis_sha256": [],
        "semantics": copy.deepcopy(planner._PREFILTER_SEMANTICS),
        "constraints": {
            "model_label_requested": False, "operator_label_requested": False,
            "campaign_1_authority": False, "ranking_authority": False,
            "champion_authority": False, "release_authority": False,
        },
    }
    _resign(prefilter, "contract_sha256")
    contract["prefilter"]["sha256"] = planner._canonical_sha(prefilter)
    _resign(contract, "contract_sha256")
    cells = []
    for arm in arms:
        prompt = f"prompt for {arm['cell_id']}"
        cells.append({
            **arm, "provider": "fixture", "prompt": prompt,
            "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
            "cli": {}, "argv_template": [], "timeout_seconds": 60.0,
        })
    manifest = {
        "schema": planner.MANIFEST_SCHEMA, "authority": planner.AUTHORITY,
        "scope": "ak-le-1-2-planner-only", "experiment_id": contract["experiment_id"],
        "experiment_contract_sha256": contract["contract_sha256"],
        "experiment_contract": contract,
        "retrieval_context_sha256": contract["fixed"]["retrieval_context_sha256"],
        "prefilter": copy.deepcopy(contract["prefilter"]), "cells": cells,
        "constraints": {
            "planner_workspace_write_access": False,
            "scaffold_execution_supported": False, "campaign_1_authority": False,
            "ranking_authority": False, "champion_authority": False,
            "release_authority": False, "model_or_kernel_invoked_by_compiler": False,
        },
        "scaffold_gap": "fixture",
    }
    _resign(manifest, "manifest_sha256")
    observations = []
    for ordinal, cell in enumerate(cells, 1):
        hypotheses = [_hypothesis(f"{ordinal}-novel"), _hypothesis(f"{ordinal}-novel")]
        raw = {
            "schema": planner.RAW_SCHEMA, "cell_id": cell["cell_id"],
            "termination": "search_exhausted", "hypotheses": hypotheses,
        }
        observations.append({
            "argv": ["fixture"], "cell_id": cell["cell_id"],
            "cli_executable_sha256": "3" * 64, "effort": cell["effort"],
            "elapsed_wall_seconds": 10.0 + ordinal,
            "finished_at": f"2026-08-12T00:00:0{ordinal}+00:00",
            "model_id": cell["model_id"], "observation": raw,
            "observation_sha256": str(ordinal) * 64,
            "prompt_sha256": cell["prompt_sha256"], "provider": "fixture",
            "quant_id": cell["quant_id"], "result_sha256": "4" * 64,
            "returncode": 0, "started_at": "2026-08-12T00:00:00+00:00",
            "status": "parsed", "stderr_sha256": "5" * 64,
            "stdout_sha256": "6" * 64, "timed_out": False,
        })
    panel = {
        "schema": planner.PANEL_SCHEMA, "status": "complete",
        "authority": planner.AUTHORITY, "experiment_id": manifest["experiment_id"],
        "experiment_contract_sha256": manifest["experiment_contract_sha256"],
        "manifest_sha256": manifest["manifest_sha256"],
        "capture_mode": "measured_model_output", "observations": observations,
        "constraints": {
            "external_prefilter_applied": False,
            "scaffold_observations_present": False, "campaign_1_authority": False,
            "ranking_authority": False, "champion_authority": False,
            "release_authority": False,
        },
        "next_required_step": "fixture",
    }
    _resign(panel, "panel_sha256")
    evidence, receipt = planner._replay(
        manifest=manifest, panel=panel, prefilter=prefilter)
    reduction = {
        "schema": planner.SOURCE_SCHEMA, "authority": planner.AUTHORITY,
        "manifest_sha256": manifest["manifest_sha256"],
        "panel_sha256": panel["panel_sha256"],
        "prefilter_contract_sha256": prefilter["contract_sha256"],
        "prefilter_evidence": evidence, "planner_receipt": receipt,
        "constraints": {
            "raw_panel_mutated": False, "scaffold_observations_fabricated": False,
            "campaign_1_authority": False, "ranking_authority": False,
            "champion_authority": False, "release_authority": False,
        },
    }
    producer = {
        "producer_id": planner.PRODUCER_ID, "ref": planner.PRODUCER_REF,
        "sha256": "7" * 64,
    }
    reduction["belief_measurements"] = planner._expected_rows(
        reduction=reduction, manifest=manifest, prefilter=prefilter,
        producer=producer)
    _resign(reduction, "reduction_sha256")
    return reduction, manifest, panel, prefilter


def test_replays_prefilter_and_projects_four_rows_per_cell() -> None:
    reduction, manifest, panel, prefilter = fixture()
    rows = planner.native_rows(
        reduction, manifest=manifest, panel=panel, prefilter_contract=prefilter,
        reduction_locator="campaign:fixture/planner-reduction.json",
        reduction_file_sha256="8" * 64, attestation_present=True)
    tuples = [planner.project(row) for row in rows]
    assert len(tuples) == len({row.measurement_id for row in tuples}) == 8
    assert {row.extra["native_field"] for row in tuples} == {
        "novel_nonduplicate_count", "prefilter_survival_count",
        "already_optimized_termination_count", "elapsed_wall_seconds",
    }
    assert {row.value for row in tuples if row.metric.endswith("survival_count")} == {1}
    assert all(row.date.startswith("2026-08-12T") for row in tuples)
    assert all(row.extra["observation_only"] is True for row in tuples)
    assert all(row.extra["ranking_authority"] is False for row in tuples)
    assert all(ct.grade(row)[:2] == ("Witnessed", "Attested") for row in tuples)


def test_r1_refusal_and_r2_failed_panel_project_zero() -> None:
    assert planner.native_rows({
        "schema": planner.REFUSAL_SCHEMA, "status": "refused"}) == ()
    assert planner.native_rows({
        "schema": planner.PANEL_SCHEMA, "status": "failed"}) == ()


def test_exact_source_bundle_is_required() -> None:
    reduction, _, _, _ = fixture()
    with pytest.raises(ct.ProjectionError, match="exact manifest"):
        planner.native_rows(reduction)


@pytest.mark.parametrize("defect", [
    "row_value", "evidence", "raw_hypothesis", "authority", "producer",
])
def test_rehashed_semantic_tampering_fails_closed(defect: str) -> None:
    reduction, manifest, panel, prefilter = fixture()
    if defect == "row_value":
        reduction["belief_measurements"][0]["value"] = 99
        _resign(reduction["belief_measurements"][0], "measurement_sha256")
        _resign(reduction, "reduction_sha256")
    elif defect == "evidence":
        reduction["prefilter_evidence"][0]["decisions"][0]["survived_prefilter"] = False
        _resign(reduction["prefilter_evidence"][0], "evidence_sha256")
        _resign(reduction, "reduction_sha256")
    elif defect == "raw_hypothesis":
        panel["observations"][0]["observation"]["hypotheses"][0]["mechanism"] = "drift"
        _resign(panel, "panel_sha256")
    elif defect == "authority":
        reduction["constraints"]["ranking_authority"] = True
        _resign(reduction, "reduction_sha256")
    else:
        reduction["belief_measurements"][0]["extra"]["projection_producer"][
            "producer_id"] = "another-producer"
        _resign(reduction["belief_measurements"][0], "measurement_sha256")
        _resign(reduction, "reduction_sha256")
    with pytest.raises(ct.ProjectionError):
        planner.native_rows(
            reduction, manifest=manifest, panel=panel,
            prefilter_contract=prefilter)
