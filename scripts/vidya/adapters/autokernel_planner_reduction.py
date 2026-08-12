"""Project prospective AK-LE planner reductions into canonical ClaimTuples.

The reader consumes the finalized reduction together with its exact execution
manifest, raw panel, and structural-prefilter contract.  It independently
replays the deterministic prefilter, reconstructs the planner receipt and the
producer's four rows per cell, and refuses any rehashed semantic drift.  The
under-specified r1 refusal and failed r2 panel have no producer-written rows and
therefore project nothing; historical tuples are never reconstructed.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Any, Mapping

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_tuple import ClaimTuple, ProjectionError, register  # noqa: E402

ADAPTER_ID = "vidya.adapters.autokernel_planner_reduction/v1"
SOURCE_SCHEMA = "epyc.autokernel.loop_experiment_planner_reduction.v1"
REFUSAL_SCHEMA = "epyc.autokernel.loop_experiment_planner_reduction_refusal.v1"
PANEL_SCHEMA = "epyc.autokernel.loop_experiment_planner_panel.v1"
MANIFEST_SCHEMA = "epyc.autokernel.loop_experiment_execution_manifest.v1"
CONTRACT_SCHEMA = "epyc.autokernel.loop_engineering_experiment.v1"
PLANNER_RECEIPT_SCHEMA = "epyc.autokernel.loop_engineering_planner_receipt.v1"
PREFILTER_SCHEMA = "epyc.autokernel.planner_structural_prefilter_contract.v1"
EVIDENCE_SCHEMA = "epyc.autokernel.planner_structural_prefilter_evidence.v1"
RAW_SCHEMA = "epyc.autokernel.loop_experiment_raw_planner.v1"
RUNNER_AUTHORITY = "observe_only_no_campaign_ranking_or_release_authority"
AUTHORITY = "observe_only_no_campaign_ranking_champion_or_release_authority"
ALGORITHM = "normalized_fingerprint_prior_and_per_cell_first_occurrence.v1"
PRODUCER_ID = "autokernel.controller.loop_experiment_beliefs/v1"
PRODUCER_REF = (
    "git://epyc-inference-research/scripts/kernel_rnd/autokernel/controller/"
    "loop_experiment_beliefs.py"
)
PREFILTER_PRODUCER_REF = (
    "git://epyc-inference-research/scripts/kernel_rnd/autokernel/controller/"
    "loop_experiment_prefilter.py"
)
REPS_BASIS = "scored:one complete hash-bound AK-LE planner cell"
_SHA = re.compile(r"[0-9a-f]{64}")
_TERMINATIONS = frozenset({"already_optimized", "budget_exhausted", "search_exhausted"})
_HYPOTHESIS_FIELDS = {
    "mechanism", "target_surface", "falsifiable_counter", "predicted_direction"
}
_METRICS = (
    ("novel_nonduplicate_count", "ak_le_planner_novel_nonduplicate_count",
     "count", "higher_better"),
    ("prefilter_survival_count", "ak_le_planner_prefilter_survival_count",
     "count", "higher_better"),
    ("already_optimized_termination_count",
     "ak_le_planner_already_optimized_termination", "indicator", "lower_better"),
    ("elapsed_wall_seconds", "ak_le_planner_elapsed_wall_seconds",
     "seconds", "lower_better"),
)
_PREFILTER_SEMANTICS = {
    "fingerprint": (
        "sha256(canonical JSON of casefolded whitespace-normalized "
        "mechanism,target_surface,falsifiable_counter,predicted_direction)"),
    "admissibility": "runner-v1 strict four-field non-empty structural observation",
    "prior_match": "exact fingerprint equality",
    "duplicate_scope": "within_cell",
    "duplicate_policy": "first_occurrence_survives",
    "cross_cell_duplicates": "retained_for_matched_arm_independence",
    "semantic_quality_label": "not_performed",
    "campaign_do_not_repeat_gate": "not_replaced_or_invoked",
}


def _canonical_sha(value: Any) -> str:
    try:
        raw = json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
            allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ProjectionError(f"planner reduction is not canonical JSON: {exc}") from exc
    return hashlib.sha256(raw).hexdigest()


def _sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _SHA.fullmatch(value):
        raise ProjectionError(f"{label} must be a lowercase SHA-256")
    return value


def _mapping(value: Any, label: str) -> dict:
    if not isinstance(value, dict):
        raise ProjectionError(f"{label} must be an object")
    return value


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or "\0" in value:
        raise ProjectionError(f"{label} must be non-empty text without NUL")
    return value


def _self_hashed(value: Mapping[str, Any], field: str, label: str) -> dict:
    payload = dict(value)
    claimed = _sha(payload.pop(field, None), field)
    if _canonical_sha(payload) != claimed:
        raise ProjectionError(f"{label} {field} does not verify")
    payload[field] = claimed
    return payload


def _authority_false(value: Any, names: tuple[str, ...], label: str) -> dict:
    constraints = _mapping(value, label)
    if set(constraints) != set(names):
        raise ProjectionError(f"{label} has unknown or missing fields")
    if any(constraints.get(name) is not False for name in names):
        raise ProjectionError(f"{label} requests forbidden authority")
    return constraints


def _manifest(value: Mapping[str, Any]) -> dict:
    manifest = _self_hashed(value, "manifest_sha256", "manifest")
    if set(manifest) != {
            "schema", "authority", "scope", "experiment_id",
            "experiment_contract_sha256", "experiment_contract",
            "retrieval_context_sha256", "prefilter", "cells", "constraints",
            "scaffold_gap", "manifest_sha256"}:
        raise ProjectionError("execution manifest has unknown or missing fields")
    if (manifest.get("schema") != MANIFEST_SCHEMA
            or manifest.get("authority") != AUTHORITY
            or manifest.get("scope") != "ak-le-1-2-planner-only"):
        raise ProjectionError("execution manifest schema, scope, or authority drifted")
    _authority_false(manifest.get("constraints"), (
        "planner_workspace_write_access", "scaffold_execution_supported",
        "campaign_1_authority", "ranking_authority", "champion_authority",
        "release_authority", "model_or_kernel_invoked_by_compiler",
    ), "manifest.constraints")
    contract = _self_hashed(
        _mapping(manifest.get("experiment_contract"), "experiment_contract"),
        "contract_sha256", "experiment contract")
    if set(contract) != {
            "schema", "experiment_id", "fixed", "planner_arms",
            "direction_predictions", "scaffold_arms", "prior_hypothesis_sha256",
            "prefilter", "authority", "constraints", "contract_sha256"}:
        raise ProjectionError("experiment contract has unknown or missing fields")
    if (contract.get("schema") != CONTRACT_SCHEMA
            or contract.get("authority") != RUNNER_AUTHORITY
            or contract.get("contract_sha256") != manifest.get(
                "experiment_contract_sha256")
            or contract.get("experiment_id") != manifest.get("experiment_id")
            or contract.get("prefilter") != manifest.get("prefilter")):
        raise ProjectionError("embedded experiment contract identity drifted")
    _authority_false(contract.get("constraints"), (
        "campaign_1_authority", "champion_authority",
        "model_or_kernel_invoked_by_contract", "ranking_authority",
        "release_authority", "target_value_is_manifest_field",
    ), "experiment_contract.constraints")
    fixed = _mapping(contract.get("fixed"), "experiment_contract.fixed")
    if fixed.get("retrieval_context_sha256") != manifest.get("retrieval_context_sha256"):
        raise ProjectionError("manifest retrieval context identity drifted")
    prior = contract.get("prior_hypothesis_sha256")
    if (not isinstance(prior, list) or tuple(prior) != tuple(sorted(set(prior)))
            or any(not isinstance(item, str) or not _SHA.fullmatch(item) for item in prior)):
        raise ProjectionError("experiment prior-hypothesis set is malformed")
    arms, cells = contract.get("planner_arms"), manifest.get("cells")
    if not isinstance(arms, list) or not arms or not isinstance(cells, list):
        raise ProjectionError("manifest lacks planner cells")
    projected = []
    seen = set()
    for cell in cells:
        cell = _mapping(cell, "manifest cell")
        identity = {name: cell.get(name) for name in (
            "cell_id", "model_id", "quant_id", "effort", "target_context_mode")}
        if any(not isinstance(item, str) or not item for item in identity.values()):
            raise ProjectionError("manifest planner arm identity is incomplete")
        if identity["cell_id"] in seen:
            raise ProjectionError("manifest planner cell is duplicated")
        seen.add(identity["cell_id"])
        prompt = _text(cell.get("prompt"), "manifest cell prompt")
        if hashlib.sha256(prompt.encode("utf-8")).hexdigest() != cell.get("prompt_sha256"):
            raise ProjectionError("manifest planner prompt hash drifted")
        projected.append(identity)
    if projected != arms:
        raise ProjectionError("manifest cells differ from predeclared planner arms")
    predictions = contract.get("direction_predictions")
    if not isinstance(predictions, list):
        raise ProjectionError("experiment direction predictions are missing")
    prediction_keys = []
    for row in predictions:
        if not isinstance(row, dict) or set(row) != {
                "model_id", "quant_id", "direction", "rationale"}:
            raise ProjectionError("direction prediction is malformed")
        prediction_keys.append((row["model_id"], row["quant_id"]))
    if len(prediction_keys) != len(set(prediction_keys)):
        raise ProjectionError("direction prediction is duplicated")
    return manifest


def _prefilter(value: Mapping[str, Any], *, manifest: dict) -> dict:
    contract = _self_hashed(value, "contract_sha256", "prefilter contract")
    if set(contract) != {
            "schema", "authority", "algorithm", "producer",
            "prior_hypothesis_sha256", "semantics", "constraints",
            "contract_sha256"}:
        raise ProjectionError("prefilter contract has unknown or missing fields")
    if (contract.get("schema") != PREFILTER_SCHEMA
            or contract.get("authority") != AUTHORITY
            or contract.get("algorithm") != ALGORITHM
            or contract.get("semantics") != _PREFILTER_SEMANTICS):
        raise ProjectionError("prefilter contract semantics drifted")
    producer = _mapping(contract.get("producer"), "prefilter producer")
    if set(producer) != {"ref", "sha256"} \
            or producer.get("ref") != PREFILTER_PRODUCER_REF:
        raise ProjectionError("prefilter producer identity drifted")
    _sha(producer.get("sha256"), "prefilter producer SHA-256")
    _authority_false(contract.get("constraints"), (
        "model_label_requested", "operator_label_requested", "campaign_1_authority",
        "ranking_authority", "champion_authority", "release_authority",
    ), "prefilter.constraints")
    embedded = manifest["experiment_contract"]
    if contract.get("prior_hypothesis_sha256") != embedded.get("prior_hypothesis_sha256"):
        raise ProjectionError("prefilter prior set differs from the experiment contract")
    manifest_pin = _mapping(manifest.get("prefilter"), "manifest prefilter pin")
    if manifest_pin != {
            "ref": manifest_pin.get("ref"),
            "sha256": _canonical_sha(contract)}:
        raise ProjectionError("manifest does not pin this prefilter contract")
    return contract


def _panel(value: Mapping[str, Any], *, manifest: dict) -> dict:
    panel = _self_hashed(value, "panel_sha256", "panel")
    if set(panel) != {
            "schema", "status", "authority", "experiment_id",
            "experiment_contract_sha256", "manifest_sha256", "capture_mode",
            "observations", "constraints", "next_required_step", "panel_sha256"}:
        raise ProjectionError("panel has unknown or missing fields")
    if (panel.get("schema") != PANEL_SCHEMA or panel.get("status") != "complete"
            or panel.get("authority") != AUTHORITY
            or panel.get("capture_mode") != "measured_model_output"):
        raise ProjectionError("panel is not a complete measured planner panel")
    for name in ("experiment_id", "experiment_contract_sha256", "manifest_sha256"):
        if panel.get(name) != manifest.get(name):
            raise ProjectionError(f"panel {name} differs from its manifest")
    _authority_false(panel.get("constraints"), (
        "external_prefilter_applied", "scaffold_observations_present",
        "campaign_1_authority", "ranking_authority", "champion_authority",
        "release_authority",
    ), "panel.constraints")
    rows = panel.get("observations")
    if not isinstance(rows, list) or len(rows) != len(manifest["cells"]):
        raise ProjectionError("panel does not cover every planner cell")
    for cell, row in zip(manifest["cells"], rows):
        row = _mapping(row, "panel observation")
        if set(row) != {
                "argv", "cell_id", "cli_executable_sha256", "effort",
                "elapsed_wall_seconds", "finished_at", "model_id", "observation",
                "observation_sha256", "prompt_sha256", "provider", "quant_id",
                "result_sha256", "returncode", "started_at", "status",
                "stderr_sha256", "stdout_sha256", "timed_out"}:
            raise ProjectionError("panel observation has unknown or missing fields")
        if any(row.get(name) != cell.get(name) for name in (
                "cell_id", "provider", "model_id", "quant_id", "effort")):
            raise ProjectionError("panel observation cell identity drifted")
        if (row.get("status") != "parsed" or row.get("returncode") != 0
                or row.get("timed_out") is not False):
            raise ProjectionError("panel observation is not a successful parsed capture")
        elapsed = row.get("elapsed_wall_seconds")
        if (isinstance(elapsed, bool) or not isinstance(elapsed, (int, float))
                or not math.isfinite(elapsed) or elapsed <= 0):
            raise ProjectionError("panel elapsed wall time is invalid")
        _text(row.get("finished_at"), "panel finished_at")
        raw = _mapping(row.get("observation"), "raw planner observation")
        if (set(raw) != {"schema", "cell_id", "termination", "hypotheses"}
                or raw.get("schema") != RAW_SCHEMA
                or raw.get("cell_id") != row.get("cell_id")
                or raw.get("termination") not in _TERMINATIONS
                or not isinstance(raw.get("hypotheses"), list)):
            raise ProjectionError("raw planner observation is structurally invalid")
        for hypothesis in raw["hypotheses"]:
            if not isinstance(hypothesis, dict) or set(hypothesis) != _HYPOTHESIS_FIELDS:
                raise ProjectionError("raw hypothesis is structurally invalid")
            for field in _HYPOTHESIS_FIELDS:
                _text(hypothesis.get(field), f"raw hypothesis {field}")
        for name in ("observation_sha256", "prompt_sha256", "result_sha256",
                     "stderr_sha256", "stdout_sha256", "cli_executable_sha256"):
            _sha(row.get(name), f"panel {name}")
    return panel


def _fingerprint(hypothesis: dict) -> str:
    normalized = {
        name: " ".join(_text(hypothesis[name], name).casefold().split())
        for name in ("mechanism", "target_surface", "falsifiable_counter",
                     "predicted_direction")
    }
    return _canonical_sha(normalized)


def _replay(*, manifest: dict, panel: dict, prefilter: dict) -> tuple[list[dict], dict]:
    prior = frozenset(prefilter["prior_hypothesis_sha256"])
    evidence_rows = []
    search_rows = []
    arm_by_id = {row["cell_id"]: row for row in manifest["experiment_contract"]["planner_arms"]}
    for row in panel["observations"]:
        seen: set[str] = set()
        decisions = []
        fingerprints = []
        for ordinal, hypothesis in enumerate(row["observation"]["hypotheses"]):
            fingerprint = _fingerprint(hypothesis)
            fingerprints.append(fingerprint)
            if fingerprint in prior:
                decision, passed = "rejected_exact_prior", False
            elif fingerprint in seen:
                decision, passed = "rejected_duplicate_in_cell", False
            else:
                decision, passed = "survived_structural_prefilter", True
            decision_row = {
                "hypothesis_ordinal": ordinal,
                "hypothesis_fingerprint_sha256": fingerprint,
                "decision": decision,
                "survived_prefilter": passed,
            }
            decision_row["decision_sha256"] = _canonical_sha({
                "cell_id": row["cell_id"],
                "raw_observation_sha256": row["observation_sha256"],
                **decision_row,
            })
            decisions.append(decision_row)
            seen.add(fingerprint)
        evidence = {
            "schema": EVIDENCE_SCHEMA, "algorithm": ALGORITHM,
            "prefilter_contract_sha256": prefilter["contract_sha256"],
            "cell_id": row["cell_id"],
            "raw_observation_sha256": row["observation_sha256"],
            "decisions": decisions,
        }
        evidence["evidence_sha256"] = _canonical_sha(evidence)
        evidence_rows.append(evidence)
        arm = arm_by_id[row["cell_id"]]
        search_rows.append({
            **arm,
            "hypotheses_total": len(fingerprints),
            "hypotheses_unique": len(set(fingerprints)),
            "duplicate_count": len(fingerprints) - len(set(fingerprints)),
            "novel_nonduplicate_count": len(set(fingerprints) - prior),
            "already_optimized_termination_count": int(
                row["observation"]["termination"] == "already_optimized"),
            "prefilter_survival_count": sum(
                decision["survived_prefilter"] for decision in decisions),
            "termination": row["observation"]["termination"],
            "elapsed_wall_seconds": row["elapsed_wall_seconds"],
            "evidence_sha256": evidence["evidence_sha256"],
        })
    contract = manifest["experiment_contract"]
    receipt = {
        "schema": PLANNER_RECEIPT_SCHEMA,
        "experiment_id": contract["experiment_id"],
        "contract_sha256": contract["contract_sha256"],
        "capture_mode": "measured",
        "authority": RUNNER_AUTHORITY,
        "scope": "ak-le-1-2-planner-only",
        "search_persistence_observations": search_rows,
        "scaffold_throughput_observations": "absent_not_fabricated",
        "objective": {
            "metrics": [
                "hypotheses_unique", "novel_nonduplicate_count",
                "prefilter_survival_count", "already_optimized_termination_count",
                "elapsed_wall_seconds",
            ],
            "matched_planner_factorial": True,
            "scaffold_factorial_measured": False,
        },
        "constraints": {
            "empirical_claim": True, "partial_receipt": True,
            "campaign_1_authority": False, "ranking_authority": False,
            "champion_authority": False, "release_authority": False,
            "controller_ab_authority": False,
        },
    }
    receipt["receipt_sha256"] = _canonical_sha(receipt)
    return evidence_rows, receipt


def _expected_rows(*, reduction: dict, manifest: dict, prefilter: dict,
                   producer: dict) -> list[dict]:
    predictions = {
        (row["model_id"], row["quant_id"]): row
        for row in manifest["experiment_contract"]["direction_predictions"]
    }
    by_cell = {row["cell_id"]: row for row in reduction["prefilter_evidence"]}
    rows = []
    for search in reduction["planner_receipt"]["search_persistence_observations"]:
        evidence = by_cell[search["cell_id"]]
        arm = {name: search[name] for name in (
            "cell_id", "model_id", "quant_id", "effort", "target_context_mode")}
        prediction = predictions.get((arm["model_id"], arm["quant_id"]))
        if prediction is None:
            raise ProjectionError("planner arm lacks its predeclared direction")
        search_sha = _canonical_sha(search)
        for native_field, metric, unit, direction in _METRICS:
            value = search[native_field]
            row = {
                "measurement_id": f"ak_le_{search['cell_id']}_{native_field}",
                "metric": metric, "value": value, "unit": unit,
                "metric_direction": direction, "category": "BASELINE", "reps": 1,
                "reps_basis": REPS_BASIS,
                "claim": (
                    f"AK-LE planner cell {search['cell_id']} observed "
                    f"{native_field}={value}"
                ),
                "extra": {
                    "measurement_role": "search_persistence_observation",
                    "native_field": native_field,
                    "metric_interpretation": (
                        "observed_cost_lower_is_better; not evidence that shorter search "
                        "is more persistent"
                        if native_field == "elapsed_wall_seconds"
                        else "predeclared search-persistence outcome"),
                    **arm,
                    "predeclared_direction": prediction["direction"],
                    "predeclared_direction_rationale": prediction["rationale"],
                    "scored_cell_basis": {
                        "reduction_schema": SOURCE_SCHEMA,
                        "planner_receipt_schema": PLANNER_RECEIPT_SCHEMA,
                        "planner_receipt_sha256": reduction["planner_receipt"][
                            "receipt_sha256"],
                        "search_persistence_observation_sha256": search_sha,
                    },
                    "manifest_sha256": reduction["manifest_sha256"],
                    "panel_sha256": reduction["panel_sha256"],
                    "prefilter_contract_sha256": reduction[
                        "prefilter_contract_sha256"],
                    "prefilter_evidence_sha256": evidence["evidence_sha256"],
                    "raw_observation_sha256": evidence["raw_observation_sha256"],
                    "projection_producer": dict(producer),
                    "prefilter_reducer_producer": dict(prefilter["producer"]),
                    "authority": AUTHORITY, "observation_only": True,
                    "campaign_1_authority": False, "ranking_authority": False,
                    "champion_authority": False, "release_authority": False,
                },
            }
            row["measurement_sha256"] = _canonical_sha(row)
            rows.append(row)
    return rows


def native_rows(
    reduction: Mapping[str, Any], *, manifest: Mapping[str, Any] | None = None,
    panel: Mapping[str, Any] | None = None,
    prefilter_contract: Mapping[str, Any] | None = None,
    reduction_locator: str = "", reduction_file_sha256: str = "",
    attestation_present: bool | None = None,
) -> tuple[dict, ...]:
    """Verify a finalized prospective reduction and return its native rows."""
    if not isinstance(reduction, Mapping):
        raise ProjectionError("planner reduction must be an object")
    # The r1 refusal and r2 failed panel are durable non-measurements.  Their
    # known schemas can be passed through discovery code without becoming an
    # excuse to synthesize historical rows.
    if reduction.get("schema") in {REFUSAL_SCHEMA, PANEL_SCHEMA} \
            and reduction.get("belief_measurements") is None:
        return ()
    if reduction.get("schema") != SOURCE_SCHEMA:
        raise ProjectionError("unsupported AutoKernel planner reduction schema")
    if reduction.get("belief_measurements") is None:
        return ()
    if manifest is None or panel is None or prefilter_contract is None:
        raise ProjectionError(
            "planner beliefs require the exact manifest, panel, and prefilter contract")
    native = _self_hashed(reduction, "reduction_sha256", "reduction")
    if set(native) != {
            "schema", "authority", "manifest_sha256", "panel_sha256",
            "prefilter_contract_sha256", "prefilter_evidence", "planner_receipt",
            "constraints", "belief_measurements", "reduction_sha256"}:
        raise ProjectionError("planner reduction has unknown or missing fields")
    trusted_manifest = _manifest(manifest)
    trusted_prefilter = _prefilter(prefilter_contract, manifest=trusted_manifest)
    trusted_panel = _panel(panel, manifest=trusted_manifest)
    evidence, receipt = _replay(
        manifest=trusted_manifest, panel=trusted_panel, prefilter=trusted_prefilter)
    expected_base = {
        "schema": SOURCE_SCHEMA, "authority": AUTHORITY,
        "manifest_sha256": trusted_manifest["manifest_sha256"],
        "panel_sha256": trusted_panel["panel_sha256"],
        "prefilter_contract_sha256": trusted_prefilter["contract_sha256"],
        "prefilter_evidence": evidence, "planner_receipt": receipt,
        "constraints": {
            "raw_panel_mutated": False, "scaffold_observations_fabricated": False,
            "campaign_1_authority": False, "ranking_authority": False,
            "champion_authority": False, "release_authority": False,
        },
    }
    observed_base = {key: native.get(key) for key in expected_base}
    if observed_base != expected_base:
        raise ProjectionError("planner reduction does not independently rederive")
    rows = native.get("belief_measurements")
    if not isinstance(rows, list) or not rows:
        raise ProjectionError("prospective planner reduction has no measurement rows")
    first_extra = _mapping(_mapping(rows[0], "belief row").get("extra"), "belief extra")
    producer = _mapping(first_extra.get("projection_producer"), "projection producer")
    if (set(producer) != {"producer_id", "ref", "sha256"}
            or producer.get("producer_id") != PRODUCER_ID
            or producer.get("ref") != PRODUCER_REF):
        raise ProjectionError("planner belief producer identity drifted")
    _sha(producer.get("sha256"), "projection producer SHA-256")
    expected_rows = _expected_rows(
        reduction=expected_base, manifest=trusted_manifest,
        prefilter=trusted_prefilter, producer=producer)
    if rows != expected_rows:
        raise ProjectionError("producer-written planner beliefs do not rederive")
    if reduction_file_sha256:
        _sha(reduction_file_sha256, "reduction_file_sha256")
    dates = {row["cell_id"]: row["finished_at"] for row in trusted_panel["observations"]}
    result = []
    for row in rows:
        value = copy.deepcopy(row)
        value["date"] = dates[value["extra"]["cell_id"]]
        value["_reduction_locator"] = reduction_locator
        value["_reduction_file_sha256"] = reduction_file_sha256
        value["_attestation_present"] = attestation_present
        result.append(value)
    return tuple(result)


@register("autokernel_planner_reduction")
def project(native: Mapping[str, Any]) -> ClaimTuple:
    if not isinstance(native, Mapping):
        raise ProjectionError("planner native row must be an object")
    return ClaimTuple(
        measurement_id=str(native["measurement_id"]), metric=str(native["metric"]),
        value=native["value"], date=str(native.get("date", "")),
        category=str(native["category"]), claim=str(native["claim"]),
        metric_direction=str(native["metric_direction"]), protocol_id=SOURCE_SCHEMA,
        reps=int(native["reps"]), reps_basis=str(native["reps_basis"]),
        unit=str(native["unit"]),
        attestation_locator=str(native.get("_reduction_locator", "")),
        attestation_sha256=str(native.get("_reduction_file_sha256", "")),
        attestation_present=native.get("_attestation_present"),
        extra=dict(native["extra"]),
    )


__all__ = ["ADAPTER_ID", "SOURCE_SCHEMA", "native_rows", "project"]
