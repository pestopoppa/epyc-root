"""Campaign-shaped prospective evaluation-event fixtures shared by the SC10/SC18 tests."""

from __future__ import annotations

import copy
import hashlib
import json
from statistics import median


def sha(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def event(*, prospective: bool = True, properties: bool = True, estimate: float | None = None):
    raw = [
        [0, "decode/seed-1", "selection", "anchor_first", "base", None,
         "2026-08-12T10:00:00Z", [50.0, 50.2], [52.0, 52.2]],
        [1, "decode/seed-2", "selection", "candidate_first", "base", None,
         "2026-08-12T10:01:00Z", [49.8, 50.0], [51.8, 52.0]],
    ]
    derived = estimate
    if derived is None:
        effects = [
            (median(block[8]) - median(block[7])) / median(block[7]) for block in raw
        ]
        derived = median(effects)
    discipline = {"suite_seed": 4711}
    if prospective:
        discipline["belief_capture"] = {
            "schema": "epyc.vidya.autokernel_evaluation_event_capture.v1",
            "effect_scale": "relative",
            "model_id": "Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf",
            "model_sha256": sha("model"),
            "source_sha256": sha("candidate-source"),
            "binary_sha256": sha("candidate-binary"),
            "resource_claim_receipt": "rcpt-cpu-claim-0042",
            "producer_sha256": sha("autokernel-evaluation-producer"),
            "raw_samples_sha256": sha("placeholder"),
        }
    gate = {
        "outcome": "PASS", "reasons": ["all property units passed"],
        "requires_anchor": False, "evidence_ref": "akcap:backend-ops-001",
    }
    if properties:
        gate["measurements"] = [{
            "schema": "epyc.autokernel.property_measurement.v1",
            "shape_id": "SOFT_MAX(type=f32,ne=[83,2,1,1])#0",
            "op": "SOFT_MAX", "backend": "CPU",
            "metric_id": "softmax_invariants/v1",
            "residual": 2.5e-08, "tolerance": 1e-4,
            "suite_seed": 4711, "input_transform": "identity", "passed": True,
        }]
    record = {
        "schema": "epyc.autokernel.evaluation_event.v5",
        "event_id": "ake-20260812-0001", "campaign_id": "ak-20260812-0001",
        "candidate_id": "akc-20260812-0001", "tier": "T1",
        "backend": "llama_cpu", "device_state": None, "change_class": "parameter",
        "anchor_tier": "T1", "transfer_ratio_to": [],
        "claim_grammar": {
            "category": "CANDIDATE", "protocol_id": "P-AK-SEARCH-1/v1",
            "metric": "decode_tokens_per_s", "metric_direction": "higher_better",
            "reps": 2, "attestation_ref": "akcap:campaign-20260812-0001",
        },
        "evaluator": {
            "id": "P-AK-SEARCH-1/v1", "bundle_sha256": sha("evaluator-bundle"),
        },
        "artifact": {
            "source_sha256": sha("candidate-source"),
            "binary_sha256": sha("candidate-binary"),
            "linkage_sha256": sha("candidate-linkage"),
        },
        "anchor": {
            "source_commit": "0db32c06e3e550065b78311a6031ef3dd2c4f27c",
            "binary_sha256": sha("anchor-binary"),
            "linkage_sha256": sha("anchor-linkage"),
            "measurement_event_ids": ["ake-20260811-anchor"],
        },
        "scope_manifest_sha256": sha("cpu-scope"),
        "host_receipt": "rcpt-host-20260812", "resource_claim_receipt": "rcpt-cpu-claim-0042",
        "co_residency": "single", "correctness": {"t0.backend_op_units": gate},
        "quality": {}, "stability": {}, "mechanism": {},
        "scope_denominator": {
            "machine_subset": "full", "numa_nodes": [], "devices": [], "cores": 192,
        },
        "determinism": {"class": "bitwise_stable", "same_seed_repeat_runs": 2},
        "performance": {
            "raw_samples": raw, "raw_samples_ref": "", "paired_blocks": len(raw),
            "estimate": derived, "uncertainty": {"e_value": 8.0, "threshold": 5.0},
            "search_discipline": discipline,
        },
        "integrity_flags": [], "status": "pass", "supersedes": [],
        "created_at": "2026-08-12T10:02:00Z",
    }
    raw_json = json.dumps(raw, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    raw_digest = hashlib.sha256(raw_json.encode("utf-8")).hexdigest()
    record["performance"]["raw_samples_ref"] = f"sha256:{raw_digest}"
    if prospective:
        discipline["belief_capture"]["raw_samples_sha256"] = raw_digest
        capture = discipline["belief_capture"]
        binding = {
            "schema": capture["schema"], "event_id": record["event_id"],
            "campaign_id": record["campaign_id"], "candidate_id": record["candidate_id"],
            "category": record["claim_grammar"]["category"],
            "protocol_id": record["claim_grammar"]["protocol_id"],
            "metric": record["claim_grammar"]["metric"],
            "metric_direction": record["claim_grammar"]["metric_direction"],
            "reps": record["claim_grammar"]["reps"],
            "effect_scale": capture["effect_scale"], "model_id": capture["model_id"],
            "model_sha256": capture["model_sha256"],
            "source_sha256": capture["source_sha256"],
            "binary_sha256": capture["binary_sha256"],
            "resource_claim_receipt": capture["resource_claim_receipt"],
            "producer_sha256": capture["producer_sha256"],
            "raw_samples_sha256": capture["raw_samples_sha256"],
        }
        capture["identity_binding_sha256"] = hashlib.sha256(
            json.dumps(binding, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=False).encode("utf-8")).hexdigest()
    return record


def envelope(**event_options):
    record = event(**event_options)
    return {
        "journal_schema": "epyc.autokernel.journal_entry.v1",
        "event_id": "evt-journal-000042", "seq": 42, "kind": "EVALUATION_EVENT",
        "campaign_id": record["campaign_id"], "record_id": record["event_id"],
        "written_at": "2026-08-12T10:02:01Z", "payload": record,
    }


def mutated(source, path, value):
    copy_source = copy.deepcopy(source)
    cursor = copy_source
    for key in path[:-1]:
        cursor = cursor[key]
    cursor[path[-1]] = value
    return copy_source
