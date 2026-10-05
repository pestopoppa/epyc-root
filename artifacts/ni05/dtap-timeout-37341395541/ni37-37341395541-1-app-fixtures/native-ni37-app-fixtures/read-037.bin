"""Project prospective AK-LE-3 same-model scaffold panels into ClaimTuples.

The completed 2026-08-12 r1 panel predates the producer hook and therefore emits
zero rows.  Successor panels carry four cell estimates and two within-model
scaffold-effect ratios.  This reader re-derives those values from the native
evaluations and refuses fixture, incomplete, authority-bearing, unmatched, or
digest-mutated panels.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Any, Mapping

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_tuple import ClaimTuple, ProjectionError, register  # noqa: E402

ADAPTER_ID = "vidya.adapters.autokernel_scaffold_panel/v1"
SOURCE_SCHEMA = "epyc.autokernel.ak_le_3_scaffold_panel.v1"
EVALUATION_SCHEMA = "epyc.autokernel.ak_le_3_arena_evaluation.v1"
AUTHORITY = "diagnostic_scaffold_observation_only"
PRODUCER_ID = "autokernel.controller.loop_scaffold_runner/ak_le_3_beliefs_v1"
PRODUCER_PATH = "scripts/kernel_rnd/autokernel/controller/loop_scaffold_runner.py"
DIRECT = "direct_implement"
SPLIT = "implement_then_exploit"
_SHA = re.compile(r"[0-9a-f]{64}")


def _canonical_sha(value: Any) -> str:
    try:
        raw = json.dumps(value, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False, allow_nan=False).encode()
    except (TypeError, ValueError) as exc:
        raise ProjectionError(f"scaffold panel is not canonical JSON: {exc}") from exc
    return hashlib.sha256(raw).hexdigest()


def _pretty_sha(value: Mapping[str, Any]) -> str:
    raw = (json.dumps(dict(value), indent=2, sort_keys=True) + "\n").encode()
    return hashlib.sha256(raw).hexdigest()


def _sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _SHA.fullmatch(value):
        raise ProjectionError(f"{label} must be a lowercase SHA-256")
    return value


def _mapping(value: Any, label: str) -> dict:
    if not isinstance(value, dict):
        raise ProjectionError(f"{label} must be an object")
    return value


def _positive_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ProjectionError(f"{label} must be a positive integer")
    return value


def _positive(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) \
            or not math.isfinite(value) or value <= 0:
        raise ProjectionError(f"{label} must be a positive finite number")
    return float(value)


def _claim_identity(cell: dict) -> tuple[dict, str]:
    opened = _mapping(cell.get("device_claim_open"), "device_claim_open")
    released = _mapping(cell.get("device_claim_released"), "device_claim_released")
    for key in ("claim_id", "device_id", "campaign_id", "acquired_at"):
        if not opened.get(key) or released.get(key) != opened[key]:
            raise ProjectionError(f"device claim {key} changed across release")
    if not released.get("released_at"):
        raise ProjectionError("device claim has no durable release")
    identity = {"opened": opened, "released": released}
    return identity, _canonical_sha(identity)


def _cell(cell: Any) -> dict:
    cell = _mapping(cell, "cell")
    receipt_sha = _sha(cell.get("cell_receipt_sha256"), "cell_receipt_sha256")
    unsigned = dict(cell)
    unsigned.pop("cell_receipt_sha256", None)
    if _canonical_sha(unsigned) != receipt_sha:
        raise ProjectionError("cell_receipt_sha256 does not bind the cell")
    evaluation = _mapping(cell.get("evaluation"), "cell.evaluation")
    if evaluation.get("schema") != EVALUATION_SCHEMA \
            or evaluation.get("authority") != AUTHORITY \
            or evaluation.get("cell_id") != cell.get("cell_id"):
        raise ProjectionError("cell evaluation identity drifted")
    if _pretty_sha(evaluation) != _sha(
            cell.get("evaluation_sha256"), "evaluation_sha256"):
        raise ProjectionError("evaluation_sha256 does not bind the native evaluation")
    if evaluation.get("pass_compilation") is not True \
            or evaluation.get("pass_correctness") is not True:
        raise ProjectionError("incorrect scaffold cells are not measurements")
    if any(evaluation.get(key) is not False for key in (
            "campaign_authority", "ranking_authority", "champion_authority",
            "release_authority")):
        raise ProjectionError("cell evaluation sought forbidden authority")
    baseline = _positive_int(evaluation.get("valid_baseline_cases"), "baseline cases")
    optimized = _positive_int(evaluation.get("valid_optimized_cases"), "optimized cases")
    if baseline != optimized:
        raise ProjectionError("cell evaluation is not case matched")
    _positive(evaluation.get("average_speedup"), "average_speedup")
    _claim_identity(cell)
    return cell


def _measurement(*, measurement_id: str, metric: str, value: float, category: str,
                 reps: int, basis: str, date: str, claim: str, extra: dict) -> dict:
    row = {
        "measurement_id": measurement_id, "metric": metric, "value": value,
        "unit": "ratio", "metric_direction": "higher_better", "category": category,
        "protocol_id": SOURCE_SCHEMA, "reps": reps, "reps_basis": basis,
        "date": date, "claim": claim, "extra": extra,
    }
    row["measurement_sha256"] = _canonical_sha(row)
    return row


def _expected(panel: dict) -> list[dict]:
    producer = _mapping(panel.get("producer"), "producer")
    if producer.get("producer_id") != PRODUCER_ID or producer.get("path") != PRODUCER_PATH:
        raise ProjectionError("scaffold panel names another producer")
    _sha(producer.get("sha256"), "producer.sha256")
    source = _mapping(panel.get("source_identity"), "source_identity")
    evaluator = _mapping(panel.get("evaluator_identity"), "evaluator_identity")
    _sha(source.get("base_tree_sha256"), "source.base_tree_sha256")
    _sha(evaluator.get("evaluator_sha256"), "evaluator.evaluator_sha256")
    cells = [_cell(value) for value in panel.get("cells", ())]
    if len(cells) != 4 or len({cell.get("cell_id") for cell in cells}) != 4:
        raise ProjectionError("scaffold panel must contain four unique cells")
    by_model: dict[str, dict[str, dict]] = {}
    rows: list[dict] = []
    authority = {
        "diagnostic_only": True, "campaign_authority": False,
        "ranking_authority": False, "champion_authority": False,
        "release_authority": False,
    }
    for cell in cells:
        evaluation = cell["evaluation"]
        model, scaffold = cell.get("model_id"), cell.get("scaffold")
        if not isinstance(model, str) or scaffold not in {DIRECT, SPLIT}:
            raise ProjectionError("cell model/scaffold identity is invalid")
        if scaffold in by_model.setdefault(model, {}):
            raise ProjectionError("duplicate model/scaffold cell")
        by_model[model][scaffold] = cell
        claim_identity, claim_sha = _claim_identity(cell)
        speedup = _positive(evaluation["average_speedup"], "average_speedup")
        row_id = f"ak_le_3_{model.replace('.', '_').replace('-', '_')}_{scaffold}_average_speedup"
        evidence = {
            "cell_id": cell["cell_id"], "model_id": model,
            "quant_id": cell["quant_id"], "effort": cell["effort"],
            "scaffold": scaffold, "planned_wall_seconds": cell["planned_wall_seconds"],
            "evaluation": evaluation, "evaluation_sha256": cell["evaluation_sha256"],
            "cell_receipt_sha256": cell["cell_receipt_sha256"],
            "device_claim_identity_sha256": claim_sha,
            "manifest_sha256": panel["manifest_sha256"],
            "source": source, "evaluator": evaluator,
            "producer_sha256": producer["sha256"],
        }
        rows.append(_measurement(
            measurement_id=row_id,
            metric="agentkernelarena_candidate_over_baseline_average_speedup",
            value=speedup, category="BASELINE" if scaffold == DIRECT else "CANDIDATE",
            reps=evaluation["valid_baseline_cases"],
            basis="scored:matched AgentKernelArena baseline/candidate cases",
            date=cell["evaluation_process"]["finished_at"],
            claim=f"AK-LE-3 {model} {scaffold} observed AgentKernelArena average speedup {speedup:.9g}x",
            extra={**authority, "experiment_id": panel["experiment_id"],
                   "source": source, "evaluator": evaluator, "producer": producer,
                   "device_claim_identity": claim_identity,
                   "device_claim_identity_sha256": claim_sha,
                   "evidence_basis": evidence, "evidence_sha256": _canonical_sha(evidence)}))
    if len(by_model) != 2:
        raise ProjectionError("scaffold panel must contain exactly two models")
    for model, arms in sorted(by_model.items()):
        if set(arms) != {DIRECT, SPLIT}:
            raise ProjectionError("each model must contain both scaffold arms")
        direct, split = arms[DIRECT], arms[SPLIT]
        de, se = direct["evaluation"], split["evaluation"]
        if (de["valid_baseline_cases"], de["valid_optimized_cases"]) != \
                (se["valid_baseline_cases"], se["valid_optimized_cases"]):
            raise ProjectionError("same-model scaffold arms have different case bases")
        direct_claim, direct_sha = _claim_identity(direct)
        split_claim, split_sha = _claim_identity(split)
        ratio = _positive(se["average_speedup"], "split speedup") / _positive(
            de["average_speedup"], "direct speedup")
        evidence = {
            "model_id": model, "direct_cell_id": direct["cell_id"],
            "split_cell_id": split["cell_id"], "direct_evaluation": de,
            "split_evaluation": se,
            "direct_cell_receipt_sha256": direct["cell_receipt_sha256"],
            "split_cell_receipt_sha256": split["cell_receipt_sha256"],
            "direct_device_claim_identity_sha256": direct_sha,
            "split_device_claim_identity_sha256": split_sha,
            "manifest_sha256": panel["manifest_sha256"],
            "source": source, "evaluator": evaluator,
            "producer_sha256": producer["sha256"],
        }
        rows.append(_measurement(
            measurement_id=f"ak_le_3_{model.replace('.', '_').replace('-', '_')}_split_over_direct_scaffold_effect",
            metric="implement_then_exploit_over_direct_average_speedup_ratio",
            value=ratio, category="CANDIDATE", reps=de["valid_baseline_cases"],
            basis="scored:same-model matched AgentKernelArena cases per scaffold arm",
            date=max(direct["evaluation_process"]["finished_at"],
                     split["evaluation_process"]["finished_at"]),
            claim=(f"AK-LE-3 {model} implement-then-exploit/direct matched scaffold "
                   f"effect was {ratio:.9g}x"),
            extra={**authority, "experiment_id": panel["experiment_id"], "model_id": model,
                   "source": source, "evaluator": evaluator, "producer": producer,
                   "device_claim_identities": {"direct": direct_claim, "split": split_claim},
                   "evidence_basis": evidence, "evidence_sha256": _canonical_sha(evidence)}))
    return rows


def native_rows(panel: dict, *, panel_locator: str = "", panel_file_sha256: str = "",
                attestation_present: bool | None = None) -> tuple[dict, ...]:
    if not isinstance(panel, dict) or panel.get("schema") != SOURCE_SCHEMA:
        raise ProjectionError("unsupported AutoKernel scaffold panel schema")
    if panel.get("belief_measurements") is None:
        return ()
    if (panel.get("status") != "complete" or panel.get("capture_mode") != "measured"
            or panel.get("authority") != AUTHORITY):
        raise ProjectionError("only terminal measured diagnostic scaffold panels project")
    constraints = _mapping(panel.get("constraints"), "constraints")
    if constraints.get("empirical_observation") is not True or any(
            constraints.get(key) is not False for key in (
                "campaign_authority", "ranking_authority", "champion_authority",
                "release_authority")):
        raise ProjectionError("scaffold panel authority boundary drifted")
    unsigned = dict(panel)
    panel_sha = _sha(unsigned.pop("panel_sha256", None), "panel_sha256")
    if _canonical_sha(unsigned) != panel_sha:
        raise ProjectionError("panel_sha256 does not bind the terminal panel")
    if panel_file_sha256:
        _sha(panel_file_sha256, "panel_file_sha256")
    expected = _expected(panel)
    native = panel["belief_measurements"]
    if not isinstance(native, list) or native != expected:
        raise ProjectionError("producer-written scaffold beliefs do not re-derive")
    result = []
    for row in native:
        value = dict(row)
        value["_panel_locator"] = panel_locator
        value["_panel_file_sha256"] = panel_file_sha256
        value["_attestation_present"] = attestation_present
        result.append(value)
    return tuple(result)


@register("autokernel_scaffold_panel")
def project(native: Mapping[str, Any]) -> ClaimTuple:
    if not isinstance(native, Mapping):
        raise ProjectionError("scaffold native row must be an object")
    return ClaimTuple(
        measurement_id=str(native["measurement_id"]), metric=str(native["metric"]),
        value=native["value"], date=str(native["date"]), category=str(native["category"]),
        claim=str(native["claim"]), metric_direction=str(native["metric_direction"]),
        protocol_id=str(native["protocol_id"]), reps=int(native["reps"]),
        reps_basis=str(native["reps_basis"]), unit=str(native["unit"]),
        attestation_locator=str(native.get("_panel_locator", "")),
        attestation_sha256=str(native.get("_panel_file_sha256", "")),
        attestation_present=native.get("_attestation_present"),
        extra=dict(native["extra"]),
    )


__all__ = ["ADAPTER_ID", "SOURCE_SCHEMA", "native_rows", "project"]
