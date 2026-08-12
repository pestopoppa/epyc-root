"""SC27 governed receipts are re-derived, projected, and never back-filled."""

import copy
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "vidya"))

import claim_tuple as ct
from adapters import autokernel_governed_receipt as governed


def sign(value):
    unsigned = copy.deepcopy(value)
    unsigned.pop("receipt_sha256", None)
    unsigned["receipt_sha256"] = governed._canonical_sha256(unsigned)
    return unsigned


def row_sign(row):
    unsigned = copy.deepcopy(row)
    unsigned.pop("measurement_sha256", None)
    unsigned["measurement_sha256"] = governed._canonical_sha256(unsigned)
    return unsigned


def replay_receipt():
    arm_values = ((100.0, 104.0), (101.0, 105.04))
    paired = [{"block": block, "anchor": anchor, "candidate": candidate,
               "relative_delta": candidate / anchor - 1.0}
              for block, (anchor, candidate) in enumerate(arm_values)]
    median_delta = sum(row["relative_delta"] for row in paired) / 2
    source = {
        "source_root": "/source", "source_branch": "production-consolidated-v9",
        "source_commit": "0" * 39 + "1", "binary": "/bin/llama-bench",
        "binary_sha256": "a" * 64, "linkage_sha256": "b" * 64,
        "model": "/models/q8.gguf", "model_sha256": "c" * 64,
    }
    opened = {"claim_id": "akd-1", "device_id": "mi210_0",
              "acquired_at": "2026-08-12T02:00:00Z"}
    released = {**opened, "released_at": "2026-08-12T02:10:00Z"}
    source_sha = governed._canonical_sha256(source)
    claim_sha = governed._canonical_sha256({"opened": opened, "released": released})
    producer_sha = "d" * 64
    evidence = {
        "paired_blocks": paired,
        "aggregation": "median(candidate_tokens_per_s/anchor_tokens_per_s-1)",
        "scored_blocks": 2, "samples_per_arm_per_block": 3,
        "contribution_floor": 0.03, "all_blocks_positive": True,
        "native_verdict": "REPRODUCED_KNOWN_WIN",
        "orders": [["anchor", "candidate"], ["candidate", "anchor"]],
        "order_seed": 17, "source_identity_sha256": source_sha,
        "claim_identity_sha256": claim_sha, "producer_sha256": producer_sha,
    }
    row = row_sign({
        "measurement_id": "async_prefetch_median_relative_delta",
        "metric": "async_prefetch_paired_median_relative_throughput_delta",
        "value": median_delta, "unit": "fraction", "metric_direction": "higher_better",
        "category": "BASELINE", "protocol_id": governed.REPLAY_SCHEMA,
        "reps": 2, "reps_basis": "scored:balanced paired replay blocks",
        "claim": "fixture governed replay", "native_verdict": "REPRODUCED_KNOWN_WIN",
        "extra": {
            "candidate_parameter": {"GGML_CUDA_Q8_PREFETCH": "1"},
            "anchor_parameter": {"GGML_CUDA_Q8_PREFETCH": "0"},
            "source_identity": source, "source_identity_sha256": source_sha,
            "binary_sha256": source["binary_sha256"],
            "model_sha256": source["model_sha256"],
            "device_claim_id": opened["claim_id"],
            "claim_identity_sha256": claim_sha,
            "producer_id": governed.REPLAY_PRODUCER,
            "producer_sha256": producer_sha,
            "evidence_basis": evidence,
            "evidence_sha256": governed._canonical_sha256(evidence),
        },
    })
    return sign({
        "schema": governed.REPLAY_SCHEMA, "status": "complete",
        "campaign_id": "ak-prefetch-successor", "ended_at": "2026-08-12T02:10:00Z",
        **source, "blocks": 2, "cell": {"repetitions": 3},
        "orders": evidence["orders"], "order_seed": 17,
        "source_identity_sha256": source_sha, "claim_identity_sha256": claim_sha,
        "producer": {"producer_id": governed.REPLAY_PRODUCER,
                     "path": governed.REPLAY_PRODUCER_PATH, "sha256": producer_sha},
        "device_claim_open": opened, "device_claim_released": released,
        "result": {"paired_blocks": paired,
                   "minimum_relative_delta": min(row["relative_delta"] for row in paired),
                   "median_relative_delta": median_delta, "contribution_floor": 0.03,
                   "all_blocks_positive": True,
                   "verdict": "REPRODUCED_KNOWN_WIN"},
        "belief_measurements": [row],
    })


def live_receipt():
    producer_sha = "e" * 64
    source = {"production_source_commit": "1" * 40,
              "measurement_instrument_commit": "2" * 40,
              "runtime_source_sha256": "3" * 64}
    source_sha = governed._canonical_sha256(source)
    binary = {"path": "/evidence/llama-bench", "sha256": "4" * 64,
              "linkage_sha256": "5" * 64, "copy_exact": True}
    model = {"path": "/models/tiny.gguf", "sha256": "6" * 64}
    claim = {"schema": "epyc.autokernel.cpu_region_claim_receipt.v1",
             "claim_id": "akc-1", "campaign_id": "ak-controls-successor",
             "cpu_list": "0-95", "acquired_at": "2026-08-12T02:00:00Z",
             "released_at": "2026-08-12T02:10:00Z"}
    claim_sha = governed._canonical_sha256(claim)
    sweep_sha = "7" * 64
    raw = {control: {control: str(index) * 64}
           for index, control in enumerate(governed.LIVE_CONTROLS, 1)}
    rows = []
    for ordinal, control in enumerate(governed.LIVE_CONTROLS, 1):
        outcome = {"control_id": control, "ordinal": ordinal,
                   "outcome": "PASS", "disposition": "satisfied"}
        observation = {"control_id": control, "abs_effect_count": 15,
                       "effect_resolution": "improvement"}
        evidence = {"control_id": control, "outcome": outcome,
                    "observation": observation, "raw_vector_sha256": raw[control],
                    "control_sweep_sha256": sweep_sha,
                    "source_identity_sha256": source_sha,
                    "binary_sha256": binary["sha256"],
                    "model_sha256": model["sha256"],
                    "claim_identity_sha256": claim_sha,
                    "producer_sha256": producer_sha}
        rows.append(row_sign({
            "measurement_id": f"live_control_{control}_requirement_satisfied",
            "metric": "autokernel_control_requirement_satisfaction", "value": 1.0,
            "unit": "fraction", "metric_direction": "higher_better",
            "category": "BASELINE", "protocol_id": governed.LIVE_PROTOCOL,
            "reps": 15, "reps_basis": "scored:paired live-control blocks",
            "claim": f"fixture {control}", "native_verdict": "PASS",
            "extra": {"control_id": control, "native_disposition": "satisfied",
                      "native_effect_resolution": "improvement",
                      "source_identity": source, "source_identity_sha256": source_sha,
                      "binary_identity": binary, "model_identity": model,
                      "resource_claim_identity": claim,
                      "claim_identity_sha256": claim_sha,
                      "producer_id": governed.LIVE_PRODUCER,
                      "producer_sha256": producer_sha,
                      "evidence_basis": evidence,
                      "evidence_sha256": governed._canonical_sha256(evidence)},
        }))
    outcomes = [row["extra"]["evidence_basis"]["outcome"] for row in rows]
    observations = [row["extra"]["evidence_basis"]["observation"] for row in rows]
    native_verdict = {"marker": "5/5", "may_rank": True,
                      "halts_campaign": False, "voids_window": False}
    return sign({
        "schema": governed.LIVE_SCHEMA, "status": "complete",
        "campaign_id": claim["campaign_id"], "protocol_id": governed.LIVE_PROTOCOL,
        "created_at": "2026-08-12T02:10:00Z", "ended_at": "2026-08-12T02:10:00Z",
        "producer": {"producer_id": governed.LIVE_PRODUCER,
                     "path": governed.LIVE_PRODUCER_PATH, "sha256": producer_sha},
        "source_identity": source, "source_identity_sha256": source_sha,
        "binary_identity": binary, "model_identity": model,
        "resource_claim_identity": claim, "claim_identity_sha256": claim_sha,
        "control_sweep_sha256": sweep_sha, "raw_vector_sha256": raw,
        "control_panel": {**native_verdict, "outcomes": outcomes,
                          "observations": observations},
        "native_verdict": native_verdict,
        "belief_measurements": rows,
    })


def resign(value, *rows):
    for index in rows:
        value["belief_measurements"][index] = row_sign(value["belief_measurements"][index])
    return sign(value)


def test_pre_hook_receipts_are_never_backfilled():
    assert governed.native_rows({
        "schema": governed.REPLAY_SCHEMA, "campaign_id": "historical",
    }) == ()


def test_replay_projects_one_attested_row_through_shared_ladder():
    rows = governed.native_rows(
        replay_receipt(), receipt_locator="probe:successor/receipt.json",
        receipt_sha256="f" * 64, attestation_present=True)
    projected = governed.project(rows[0])
    assert projected.reps == 2
    assert projected.metric_direction == "higher_better"
    assert projected.extra["native_verdict"] == "REPRODUCED_KNOWN_WIN"
    assert ct.grade(projected)[:2] == ("Witnessed", "Attested")


def test_live_projects_exactly_five_rows_with_unique_identity():
    rows = governed.native_rows(
        live_receipt(), receipt_locator="controls:successor/belief_receipt.json",
        receipt_sha256="f" * 64, attestation_present=True)
    projected = [governed.project(row) for row in rows]
    assert len(projected) == len({row.measurement_id for row in projected}) == 5
    assert all(row.protocol_id == governed.LIVE_PROTOCOL for row in projected)
    assert all(ct.grade(row)[:2] == ("Witnessed", "Attested") for row in projected)


@pytest.mark.parametrize("defect", [
    "receipt", "row", "source", "binary", "model", "claim", "evidence",
    "verdict", "delta", "reps",
])
def test_replay_binding_defects_fail_closed(defect):
    value = replay_receipt()
    if defect == "receipt":
        value["receipt_sha256"] = "0" * 64
    elif defect == "row":
        value["belief_measurements"][0]["measurement_sha256"] = "0" * 64
        value = sign(value)
    elif defect == "source":
        value["binary_sha256"] = "0" * 64
        value = sign(value)
    elif defect == "binary":
        value["belief_measurements"][0]["extra"]["binary_sha256"] = "0" * 64
        value = resign(value, 0)
    elif defect == "model":
        value["belief_measurements"][0]["extra"]["model_sha256"] = "0" * 64
        value = resign(value, 0)
    elif defect == "claim":
        value["claim_identity_sha256"] = "0" * 64
        value = sign(value)
    elif defect == "evidence":
        value["belief_measurements"][0]["extra"]["evidence_sha256"] = "0" * 64
        value = resign(value, 0)
    elif defect == "verdict":
        value["result"]["verdict"] = "NOT_REPRODUCED"
        value = sign(value)
    elif defect == "delta":
        value["result"]["paired_blocks"][0]["relative_delta"] = 0.03
        value = sign(value)
    else:
        value["belief_measurements"][0]["reps"] = 3
        value = resign(value, 0)
    with pytest.raises(ct.ProjectionError):
        governed.native_rows(value)


@pytest.mark.parametrize("defect", [
    "receipt", "row", "source", "binary", "model", "claim", "raw",
    "evidence", "verdict", "marker", "reps",
])
def test_live_binding_defects_fail_closed(defect):
    value = live_receipt()
    row = value["belief_measurements"][0]
    if defect == "receipt":
        value["receipt_sha256"] = "0" * 64
    elif defect == "row":
        row["measurement_sha256"] = "0" * 64
        value = sign(value)
    elif defect == "source":
        value["source_identity_sha256"] = "0" * 64
        value = sign(value)
    elif defect == "binary":
        row["extra"]["binary_identity"]["sha256"] = "0" * 64
        value = resign(value, 0)
    elif defect == "model":
        row["extra"]["model_identity"]["sha256"] = "0" * 64
        value = resign(value, 0)
    elif defect == "claim":
        row["extra"]["resource_claim_identity"]["claim_id"] = "other"
        value = resign(value, 0)
    elif defect == "raw":
        row["extra"]["evidence_basis"]["raw_vector_sha256"] = {"x": "0" * 64}
        value = resign(value, 0)
    elif defect == "evidence":
        row["extra"]["evidence_sha256"] = "0" * 64
        value = resign(value, 0)
    elif defect == "verdict":
        row["native_verdict"] = "FAIL"
        value = resign(value, 0)
    elif defect == "marker":
        value["native_verdict"]["marker"] = "4/5"
        value = sign(value)
    else:
        row["reps"] = 14
        value = resign(value, 0)
    with pytest.raises(ct.ProjectionError):
        governed.native_rows(value)
