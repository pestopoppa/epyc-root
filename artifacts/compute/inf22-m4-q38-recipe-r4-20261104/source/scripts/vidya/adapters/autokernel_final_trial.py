"""Closed readback of parent-final provenance; no scientific evaluator or grader.

This projects a parent-issued record. It never reconstructs a live grant or the
original in-memory issuer. Research owns the T0 reducer and pre-append replay.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

from . import autokernel_unified_arm as arm

TRIAL_SCHEMA = "epyc.autokernel.parent_final_trial.v1"
REFERENCE_SCHEMA = "epyc.autokernel.parent_final_trial_reference.v1"
PAIR_SCHEMA = "epyc.autokernel.parent_server_t0_pair.v1"
PAIR_REFERENCE_SCHEMA = "epyc.autokernel.parent_server_t0_pair_reference.v1"
EVIDENCE_SCHEMA = "epyc.autokernel.parent_server_t0_witness.v1"
INPUT_SCHEMA = "epyc.autokernel.parent_server_t0_inputs.v1"
ADAPTER_ID = "epyc.autokernel.native_server_t0_witness.v1"
COVERAGE = "original_server_content_bytes_and_owning_t0_reducer_replay"
MAX_ARTIFACTS = 8192
MAX_CANONICAL_BYTES = 256 * 1024 * 1024
MAX_NODES = 2_000_000
TRIAL_FIELDS = {"schema", "plan", "plan_digest", "prepared_digest", "result_reference",
    "worker_start", "accepted_terminal", "result_fence", "original_arm_captures",
    "original_unit_receipts", "scientific_pair_reference", "control_reference",
    "calibration_reference", "original_raw_units", "original_admissible_view",
    "final_rows", "final_admissible_view", "source_identity"}
PAIR_FIELDS = {"schema", "plan_digest", "plan", "instrument_reference",
    "adapter_source_identity", "original_issuer_source", "ordered_units", "coverage"}
PAIR_UNIT_FIELDS = {"unit_id", "arm", "process_generation_id", "pair_id", "order_index",
    "original_frame", "parent_unit_receipt", "parent_unit_receipt_digest",
    "original_unit_scientific_receipt", "original_unit_status", "original_inputs",
    "original_owning_t0", "original_model_preparation", "selected_anchor_unit_id", "final_evidence"}
EVIDENCE_FIELDS = {"schema", "witness", "adapter_id", "frame", "native_observation",
    "lifecycle_reference", "runtime_readbacks", "original_owning_inputs",
    "original_anchor_native", "source", "report", "scope_defects", "status", "replay_coverage"}
INPUT_FIELDS = {"schema", "frame", "original_frame", "original_t0", "original_t0_digest",
    "original_identity", "request_by_slot", "policy", "anchor_unit_id", "source"}
T0_GATE_IDS = (
    "t0.source_integrity.symbol_and_registration_preservation",
    "t0.source_integrity.clean_build_from_snapshot", "t0.source_integrity.semantic_diff_conformance",
    "t0.schema_and_diff_policy", "t0.static_and_compile_checks", "t0.sanitizer.asan", "t0.sanitizer.ubsan",
    "t0.backend_op_units", "t0.exact_reference_comparison", "t0.unseen_boundary_shapes",
    "t0.affected_surface_reconciliation", "t0.no_fallback_dispatch_proof",
    "t0.state_rollback_teardown_race", "t0.output_coherence_vs_anchor", "t0.determinism_class",
    "t0.binary_and_linkage_identity", "t0.anti_reward_hacking")


def _same(actual, expected, label):
    if arm._canonical(actual) != arm._canonical(expected):
        raise arm.ProjectionError(f"parent final {label} differs")


def _digest(value, field, label):
    body = dict(value)
    declared = body.pop(field, None)
    if not isinstance(declared, str) or not arm._SHA.fullmatch(declared) or arm._hash(body) != declared:
        raise arm.ProjectionError(f"parent final {label} digest mismatch")
    return declared


class _Reader:
    def __init__(self, root):
        if root is None:
            raise arm.ProjectionError("parent final requires an allowlisted corpus root")
        self.root = Path(root)
        self.records = {}
        self.canonical_bytes = 0

    def artifact(self, reference, *, namespace=None):
        ref = arm._artifact_ref(reference, "parent final artifact")
        key = (ref["locator"], ref["sha256"])
        if key not in self.records:
            if len(self.records) >= MAX_ARTIFACTS:
                raise arm.ProjectionError("parent final artifact count exceeds readback bound")
            body = arm._artifact_bytes(self.root, *key)
            self.canonical_bytes += len(arm._canonical(body))
            if self.canonical_bytes > MAX_CANONICAL_BYTES:
                raise arm.ProjectionError("parent final aggregate readback exceeds bound")
            self.records[key] = body
        body = self.records[key]
        if namespace is not None:
            name = f"{hashlib.sha256(namespace.encode()).hexdigest()}-{arm._hash(body)}.json"
            _same(ref["locator"], name, "artifact namespace")
        return body

    def reference(self, value, schema, namespace):
        ref = arm._exact(value, {"schema", "artifact", "digest"}, "parent final reference")
        _same(ref["schema"], schema, "reference schema")
        body = self.artifact(ref["artifact"], namespace=f"{namespace}:{ref['digest']}")
        _same(arm._hash(body), ref["digest"], "referenced canonical content")
        return body

    def all_references(self, body):
        """Reopen every byte-bound StoredArtifact, without opening source/model paths."""
        pending, visited, count = [(body, 0)], set(), 0
        while pending:
            value, depth = pending.pop()
            count += 1
            if count > MAX_NODES or depth > 128:
                raise arm.ProjectionError("parent final nested reference budget exceeded")
            if isinstance(value, dict):
                if {"locator", "sha256", "verified"} <= set(value):
                    ref = arm._artifact_ref(value, "nested parent final artifact")
                    key = (ref["locator"], ref["sha256"])
                    if key not in visited:
                        visited.add(key)
                        pending.append((self.artifact(ref), depth + 1))
                else:
                    pending.extend((item, depth + 1) for item in value.values())
            elif isinstance(value, list):
                pending.extend((item, depth + 1) for item in value)


def _source(value):
    """Require complete recorded loaded identities; never repin today's files."""
    pending, count = [value], 0
    while pending:
        row = pending.pop()
        if isinstance(row, dict):
            if "implementation_status" in row or "configuration_status" in row:
                arm._exact(row, arm._CALLABLE_FIELDS, "parent final loaded source")
                for key in ("implementation", "configuration"):
                    if row[f"{key}_status"] != "pinned" or not isinstance(row[f"{key}_sha256"], str) \
                            or not arm._SHA.fullmatch(row[f"{key}_sha256"]):
                        raise arm.ProjectionError("parent final source identity is incomplete")
                count += 1
            else:
                pending.extend(row.values())
        elif isinstance(row, list):
            pending.extend(row)
    if not count:
        raise arm.ProjectionError("parent final has no loaded source identities")


def _report_status(evidence, expected_prompts, requests, owning_original):
    """Check the owning report's recorded terminal summaries, not its gate policy."""
    report = arm._exact(evidence["report"], {"slots", "gate_ids", "coverage"}, "server T0 reports")
    _same(report["coverage"], COVERAGE, "report coverage")
    gate_ids = arm._strings(report["gate_ids"], "complete owning T0 gate IDs")
    _same(gate_ids, T0_GATE_IDS, "canonical owning gate membership")
    _same([gate["gate_id"] for gate in owning_original["report"]["gates"]], gate_ids,
          "original captured owning gate membership")
    if len(report["slots"]) != len(expected_prompts) or len(requests) != len(expected_prompts):
        raise arm.ProjectionError("parent final full T0/slot report membership differs")
    failed, unknown = False, False
    for index, slot in enumerate(report["slots"]):
        arm._exact(slot, {"slot_index", "prompt_id", "generation", "anchor_generation",
            "request", "evidence", "static_bundle", "report"}, "server T0 report slot")
        _same((slot["slot_index"], slot["prompt_id"]), (index, expected_prompts[index]), "T0 slot order")
        _same(slot["request"], requests[index], "original per-slot owning request")
        owning = slot["report"]
        if not isinstance(owning, dict) or owning.get("tier") != "T0":
            raise arm.ProjectionError("parent final report is not owning T0")
        gates = owning.get("gates")
        if not isinstance(gates, list) or [gate.get("gate_id") for gate in gates] != gate_ids:
            raise arm.ProjectionError("parent final complete owning gate order differs")
        for gate in gates:
            arm._exact(gate, {"gate_id", "gate_class", "outcome", "reasons", "evidence_ref",
                "requires_anchor", "notes"}, "owning T0 gate")
            if gate["outcome"] not in {"PASS", "FAIL", "COULD_NOT_CHECK"}:
                raise arm.ProjectionError("parent final unsupported owning gate outcome")
        _same(owning.get("failed"), [gate["gate_id"] for gate in gates if gate["outcome"] == "FAIL"], "failed gate summary")
        _same(owning.get("unevaluated"), [gate["gate_id"] for gate in gates if gate["outcome"] == "COULD_NOT_CHECK"], "unknown gate summary")
        if type(owning.get("anchor_bound")) is not bool or not isinstance(owning.get("demoted_gates"), list):
            raise arm.ProjectionError("parent final owning anchor/demotion state malformed")
        failed |= bool(owning["failed"])
        unknown |= bool(owning["unevaluated"] or owning["demoted_gates"] or not owning["anchor_bound"])
        fields = slot["generation"].get("fields", {})
        if fields.get("seed") is not None:
            raise arm.ProjectionError("v1 server generation invents a seed")
        coherence = owning.get("coherence")
        if isinstance(coherence, dict) and coherence.get("token_agreement_ratio") is not None:
            raise arm.ProjectionError("v1 server byte coherence invents token agreement")
    defects = evidence["scope_defects"]
    if not isinstance(defects, list):
        raise arm.ProjectionError("parent final scope defects must remain recorded")
    status = "fail" if failed or defects else "unknown" if unknown else "pass"
    _same(evidence["status"], status, "full owning report status")
    return status


def validate_final(carrier, *, corpus_root):
    """Return validated original row witnesses for the shared native fact checks."""
    reader = _Reader(corpus_root)
    final = reader.reference(carrier["parent_final_trial"], REFERENCE_SCHEMA, "parent-final-trial")
    arm._exact(final, TRIAL_FIELDS, "parent final trial")
    _same(final["schema"], TRIAL_SCHEMA, "trial schema")
    plan = carrier["plan"]
    plan_digest = arm._hash(plan)
    _same((final["plan"], final["plan_digest"]), (plan, plan_digest), "original plan")
    _same((final["control_reference"], final["calibration_reference"]), (None, None),
          "supported qualified preparation slots")
    for label in ("original_admissible_view", "final_admissible_view"):
        view = arm._exact(final[label], arm._VIEW_FIELDS, label)
        _digest(view, "view_digest", label)
        _same(view["plan_digest"], plan_digest, "view original plan")
    expected = sorted(plan["expected_units"], key=lambda item: item["order_index"])
    ids = [item["unit_id"] for item in expected]
    if not ids or len(ids) > 1024:
        raise arm.ProjectionError("parent final plan membership exceeds supported bound")
    pair = reader.reference(final["scientific_pair_reference"], PAIR_REFERENCE_SCHEMA, "parent-server-t0-pair")
    arm._exact(pair, PAIR_FIELDS, "parent server T0 pair")
    _same((pair["schema"], pair["plan"], pair["plan_digest"], pair["instrument_reference"], pair["coverage"]),
          (PAIR_SCHEMA, plan, plan_digest, carrier["loaded_instrument"], COVERAGE), "scientific pair plan/source scope")
    original_refs = arm._exact(final["original_arm_captures"], {"anchor", "candidate"}, "original arm set")
    original_rows = final["original_raw_units"]
    final_rows = final["final_rows"]
    parent_rows = final["original_unit_receipts"]
    pair_rows = pair["ordered_units"]
    for rows, field in ((original_rows, "unit_id"), (parent_rows, "unit_id"), (pair_rows, "unit_id")):
        if not isinstance(rows, list) or [row.get(field) for row in rows] != ids:
            raise arm.ProjectionError("parent final full ordered original membership differs")
    if not isinstance(final_rows, list) or [row.get("row", {}).get("unit_id") for row in final_rows] != ids:
        raise arm.ProjectionError("parent final derived membership differs")
    native, attempts, originals = {}, {}, {}
    for name, ref in original_refs.items():
        arm._exact(ref, {"measurement_id", "carrier_digest", "artifact"}, "original capture reference")
        old = reader.artifact(ref["artifact"], namespace=f"carrier:{ref['measurement_id']}")
        _same((old["schema"], old["arm"], old["plan"], old["measurement_id"], old["carrier_digest"]),
              (arm.CAPTURE_SCHEMA_V2, name, plan, ref["measurement_id"], ref["carrier_digest"]), "original v2 arm")
        # Check version before dispatch: an original v3 must never recursively
        # start a fresh final reader and reset its aggregate budgets.
        arm._validate(old, corpus_root=reader.root)
        _same(old["admissible_view"], final["original_admissible_view"], "original immutable view")
        for item in old["raw_artifacts"]:
            document = item["document"]
            table = native if document.get("kind") == "native_observation" else attempts
            if document.get("kind") not in {"native_observation", "completed_attempt"} or document["unit_id"] in table:
                raise arm.ProjectionError("parent final duplicate/unsupported original artifact")
            table[document["unit_id"]] = document
        originals[name] = old
    if set(native) != set(ids) or set(attempts) != set(ids):
        raise arm.ProjectionError("parent final incomplete original native membership")
    _same(carrier["original_arm_capture"], original_refs[carrier["arm"]], "selected original arm reference")
    allowed_delta = {"schema", "producer", "measurement_id", "arm_locator", "carrier_digest",
        "admissible_view", "status", "diagnostic_reason", "measurement", "original_arm_capture", "parent_final_trial"}
    old = originals[carrier["arm"]]
    _same({key: value for key, value in carrier.items() if key not in allowed_delta},
          {key: value for key, value in old.items() if key not in allowed_delta}, "unchanged original carrier facts")
    source = arm._exact(final["source_identity"], {"finalizer", "selected_scientific_adapter"}, "parent final source")
    instrument = reader.artifact(carrier["loaded_instrument"]["artifact"])
    closure = instrument["used_constants"]["producer_source_closure"]
    selected = closure["scientific_adapters"]["correctness"]
    _same(selected["adapter_id"], ADAPTER_ID, "selected concrete server adapter")
    _same(source["selected_scientific_adapter"], selected, "prospectively pinned selected adapter")
    _same(source["finalizer"], selected["owning_source_pins"]["final_trial_source"], "prospectively pinned finalizer")
    _same((pair["adapter_source_identity"], pair["original_issuer_source"]),
          (selected, selected["owning_issuer"]), "pair original source closure")
    _source(closure)
    _source(source)
    result = _validate_result(final, carrier, reader, ids, originals)
    witnesses = {}
    for index, (spec, original, derived, receipt, pair_unit) in enumerate(
            zip(expected, original_rows, final_rows, parent_rows, pair_rows)):
        arm._exact(original, arm._RAW_FIELDS, "original full raw row")
        arm._exact(derived, {"original_unit_digest", "original_parent_receipt", "final_scientific_reference", "row"}, "derived raw row")
        arm._exact(receipt, {"unit_id", "receipt", "digest"}, "original parent receipt")
        arm._exact(pair_unit, PAIR_UNIT_FIELDS, "original pair unit")
        unit_id = spec["unit_id"]
        _same((pair_unit["arm"], pair_unit["process_generation_id"], pair_unit["pair_id"], pair_unit["order_index"]),
              (spec["arm"], spec["process_id"], spec["pair_id"], spec["order_index"]), "pair frozen unit")
        parent = reader.artifact(receipt["receipt"])
        _same(arm._hash(parent), receipt["digest"], "parent receipt digest")
        _same((pair_unit["parent_unit_receipt"], pair_unit["parent_unit_receipt_digest"]),
              (receipt["receipt"], receipt["digest"]), "pair original parent receipt")
        _same((derived["original_unit_digest"], derived["original_parent_receipt"], derived["final_scientific_reference"]),
              (arm._hash(original), receipt["receipt"], final["scientific_pair_reference"]), "derived original provenance")
        evidence = arm._exact(pair_unit["final_evidence"], EVIDENCE_FIELDS, "final scientific evidence")
        inputs = reader.artifact(pair_unit["original_inputs"])
        arm._exact(inputs, INPUT_FIELDS, "original server T0 inputs")
        _same((inputs["schema"], inputs["frame"], inputs["source"], inputs["original_t0"]),
              (INPUT_SCHEMA, pair_unit["original_frame"], selected, pair_unit["original_owning_t0"]), "original input issuance")
        owning = reader.artifact(inputs["original_t0"])
        _same(arm._hash(owning), inputs["original_t0_digest"], "original owning T0 content")
        _same(owning["source_pins"], selected["owning_issuer"]["owning_source_pins"],
              "original captured owning evaluator source")
        _same((owning["policy"], owning["frame"]), (inputs["policy"], inputs["original_frame"]),
              "original owning policy/frame")
        _same((evidence["schema"], evidence["witness"], evidence["adapter_id"], evidence["source"], evidence["replay_coverage"]),
              (EVIDENCE_SCHEMA, "correctness", ADAPTER_ID, selected, COVERAGE), "final owning evidence identity")
        _same((evidence["frame"], evidence["original_owning_inputs"]),
              (inputs["frame"], pair_unit["original_inputs"]), "final owning input frame")
        frame = inputs["frame"]
        _same((frame["identity"], frame["parent_descendant_event"], frame["active_claim"]),
              (parent["identity"], parent["parent_descendant_event"], parent["parent_active_claim"]),
              "original issued parent identity/descendant/claim")
        _same((frame["identity"]["unit_id"], frame["identity"]["plan_digest"],
               frame["identity"]["recipe_digest"], frame["arm"], frame["process_generation_id"],
               frame["expected_prompt_ids"]),
              (unit_id, final["plan_digest"], plan[f"{spec['arm']}_identity"]["resolved_execution_digest"],
               spec["arm"], spec["process_id"], spec["expected_prompt_ids"]), "full original unit frame")
        _same(frame["prompts"], carrier["prompt_manifest"], "original exact prompt manifest")
        start = final["worker_start"]
        for key in ("worker_id", "worker_generation", "grant_id", "grant_generation", "container_id",
                    "lineage_id", "config_digest", "config_generation", "supervisor_id", "supervisor_incarnation"):
            _same(frame["parent_descendant_event"][key], start[key], f"original parent descendant {key}")
        _same(reader.artifact(evidence["native_observation"]), native[unit_id], "final original native bytes")
        _same((parent["native_observation"], parent["lifecycle_observation"], parent["runtime_readbacks"]),
              (evidence["native_observation"], evidence["lifecycle_reference"], evidence["runtime_readbacks"]), "original parent lifecycle/native/readbacks")
        _same(native[unit_id]["lifecycle_observation"], evidence["lifecycle_reference"], "exact lifecycle membership")
        _same(result["lifecycle_observation_references"][index], evidence["lifecycle_reference"],
              "result exact original lifecycle reference")
        arm._validate_lifecycle_reference(evidence["lifecycle_reference"], reader.root)
        old_ref = pair_unit["original_unit_scientific_receipt"]
        old_evidence = reader.artifact(old_ref["artifact"])
        _same(arm._hash(old_evidence), old_ref["digest"], "original scientific receipt")
        _same(parent["findings"]["correctness"]["facts"]["receipt"], old_ref, "original parent scientific receipt")
        _same(old_evidence["status"], pair_unit["original_unit_status"], "immutable original scientific status")
        status = _report_status(evidence, spec["expected_prompt_ids"], inputs["request_by_slot"], owning)
        projected = dict(original)
        projected["witnesses"] = dict(original["witnesses"])
        prior = original["witnesses"].get("correctness")
        if prior is None or prior["status"] == "unknown" or status == "fail" and prior["status"] != "fail":
            projected["witnesses"]["correctness"] = {"status": status, "ref": None if status == "unknown" else
                f"parent-server-t0-pair:{final['scientific_pair_reference']['digest']}#{unit_id}"}
        _same(derived["row"], projected, "narrow derived correctness delta")
        _same(original["witnesses"], attempts[unit_id]["stage_witnesses"], "original attempt witnesses")
        witnesses[unit_id] = original["witnesses"]
    _same(carrier["admissible_view"], final["final_admissible_view"], "final view")
    # A structural reader retains the complete original closure. It does not
    # open today's source files, model inventory or execute any owning checker.
    reader.all_references(final)
    return witnesses


def _validate_result(final, carrier, reader, ids, originals):
    reference = arm._exact(final["result_reference"], {"schema", "nonce", "prepared_digest", "worker_id",
        "worker_generation", "result_digest", "result_locator", "result_sha256", "reference_digest"}, "result reference")
    _same(reference["schema"], "epyc.autokernel.planned_worker_result_reference.v2", "result reference schema")
    _digest(reference, "reference_digest", "result reference")
    result = reader.artifact({"locator": reference["result_locator"],
        "sha256": reference["result_sha256"], "verified": True})
    arm._exact(result, {"schema", "nonce", "prepared_digest", "plan_digest", "lineage_id", "stage_id",
        "worker_id", "worker_generation", "grant_id", "grant_generation", "container_id", "completed_unit_ids",
        "run", "captures", "result_digest", "lifecycle_observation_references"}, "original worker result")
    _same(result["schema"], "epyc.autokernel.planned_worker_result.v2", "result schema")
    _same(_digest(result, "result_digest", "worker result"), reference["result_digest"], "original result digest")
    start, terminal, fence = final["worker_start"], final["accepted_terminal"], final["result_fence"]
    arm._exact(start, {"schema", "nonce", "request_id", "prepared_digest", "plan_digest", "lineage_id", "stage_id",
        "campaign_id", "config_digest", "config_generation", "supervisor_id", "supervisor_incarnation", "worker_id",
        "worker_generation", "grant_id", "grant_generation", "container_id", "child_process", "cgroup_identity",
        "clock_domain", "provider_deadline", "sequence", "start_digest"}, "original worker start")
    _same((start["schema"], start["sequence"]), ("epyc.autokernel.planned_worker_start.v1", 0), "start schema/sequence")
    arm._exact(terminal, {"worker_id", "worker_generation", "request_id", "plan_digest", "lineage_id", "stage_id",
        "grant_id", "grant_generation", "container_id", "return_code", "result_digest", "accepted", "reason"}, "original terminal")
    arm._exact(fence, {"campaign_id", "config_digest", "supervisor_id", "supervisor_incarnation", "config_generation",
        "worker_id", "worker_incarnation", "grant_id", "container_id", "lineage_id", "current", "result_accepted"}, "original result fence")
    _digest(start, "start_digest", "worker start")
    if terminal.get("accepted") is not True or fence.get("current") is not True or fence.get("result_accepted") is not True:
        raise arm.ProjectionError("parent final original accepted fence is missing")
    _same(terminal["result_digest"], arm._hash(reference), "accepted terminal result")
    for row in (start, reference, result):
        _same(row["prepared_digest"], final["prepared_digest"], "original preparation")
    for key in ("worker_id", "worker_generation"):
        _same((result[key], reference[key], terminal[key]), (start[key],) * 3, f"original {key}")
    _same((result["nonce"], reference["nonce"]), (start["nonce"],) * 2, "original worker nonce")
    for key in ("plan_digest", "grant_id", "grant_generation", "container_id", "lineage_id", "request_id", "stage_id"):
        _same(terminal[key], start[key], f"original terminal {key}")
    _same(start["plan_digest"], final["plan_digest"], "worker plan")
    for key in ("campaign_id", "config_digest", "config_generation", "supervisor_id", "supervisor_incarnation",
                "worker_id", "grant_id", "container_id", "lineage_id"):
        _same((fence[key], carrier["capture_context"][key]), (start[key],) * 2, f"original context {key}")
    _same(fence["worker_incarnation"], start["worker_generation"], "original worker incarnation")
    _same(result["completed_unit_ids"], ids, "complete original result membership")
    _same([row["unit_id"] for row in result["lifecycle_observation_references"]], ids, "complete result lifecycle membership")
    _same(result["run"]["raw_units"], final["original_raw_units"], "original result raw rows")
    _same(result["run"]["admissible_view"], final["original_admissible_view"], "original result view")
    _same(result["run"]["lifecycle_observation_references"], result["lifecycle_observation_references"], "run exact lifecycle refs")
    captures = result["captures"]
    if not isinstance(captures, list) or len(captures) != 2:
        raise arm.ProjectionError("parent final original result requires both arm captures")
    for capture, name in zip(captures, ("anchor", "candidate")):
        arm._exact(capture, {"measurement_id", "payload", "payload_digest", "artifact"}, "original result capture")
        payload = arm._exact(capture["payload"], {"schema", "measurement_id", "carrier", "artifact"}, "original result payload")
        ref = final["original_arm_captures"][name]
        _same(payload, {"schema": arm.CAPTURE_SCHEMA_V2, "measurement_id": ref["measurement_id"],
            "carrier": originals[name], "artifact": ref["artifact"]}, "original result capture reference/bytes")
        _same((capture["measurement_id"], capture["payload_digest"]),
              (ref["measurement_id"], arm._hash(payload)), "original deferred capture digest")
        _same(capture["artifact"], ref["artifact"], "original deferred carrier reference")
        _same(reader.artifact(capture["artifact"]), payload["carrier"], "original deferred carrier artifact")
    return result
