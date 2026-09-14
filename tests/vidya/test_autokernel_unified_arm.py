"""Strict read-side tests for prospective unified per-arm captures."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "vidya"))
from adapters import autokernel_corpus as corpus
from adapters import autokernel_unified_arm as arm
from claim_tuple import ProjectionError, grade


def _hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False).encode()).hexdigest()


def _write(root, name, value):
    path = root / name
    path.write_text(json.dumps(value, indent=2, sort_keys=True))
    path.chmod(0o600)
    return {"locator": name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "verified": True}


def _reseal_raw(root, carrier):
    native_entry, attempt_entry = carrier["raw_artifacts"]
    native = native_entry["document"]
    old_native_digest = native["artifact_digest"]
    native_body = dict(native)
    native_body.pop("artifact_digest")
    native["artifact_digest"] = _hash(native_body)
    native_entry["stored"] = _write(root, native_entry["stored"]["locator"], native)

    attempt = attempt_entry["document"]
    if attempt["native_observation_digest"] == old_native_digest:
        attempt["native_observation_digest"] = native["artifact_digest"]
    attempt_body = dict(attempt)
    attempt_body.pop("artifact_digest")
    attempt["artifact_digest"] = _hash(attempt_body)
    attempt_entry["stored"] = _write(root, attempt_entry["stored"]["locator"], attempt)
    row = next(item for item in carrier["admissible_view"]["selected_rows"]
               if item["unit_id"] == attempt["unit_id"])
    row["artifact_digest"] = attempt["artifact_digest"]
    view_body = dict(carrier["admissible_view"])
    view_body.pop("view_digest")
    carrier["admissible_view"]["view_digest"] = _hash(view_body)
    body = dict(carrier)
    body.pop("carrier_digest")
    carrier["carrier_digest"] = _hash(body)
    return carrier


def carrier_fixture(root: Path, *, status="measurement"):
    """Exact parity fixture for measurement_capture v1; cross-repo test guards drift."""
    prompt_body = {"prompt": "exact", "n_predict": 8, "temperature": 0.0,
                   "top_p": 1.0, "top_k": 0, "cache_prompt": False}
    request_sha = hashlib.sha256(json.dumps(prompt_body, sort_keys=True,
                                            separators=(",", ":")).encode()).hexdigest()
    prompt = {"prompt_id": "p1", **prompt_body, "request_digest": request_sha}
    manifest_body = {"schema": "epyc.autokernel.frozen_prompt_manifest.v1",
                     "version": "v1", "prompts": [prompt]}
    manifest = {**manifest_body, "digest": _hash(manifest_body)}
    identity = {"backend": "cpu", "template_hash": "1" * 64,
                "resolved_execution_digest": "2" * 64,
                "resolved_snapshot_digest": "3" * 64, "workload_digest": "4" * 64,
                "model_digest": "5" * 64, "drafter_digest": None,
                "executable_digest": "6" * 64, "dso_set_digest": "7" * 64}
    identities = {"anchor": identity, "candidate": dict(identity, template_hash="8" * 64)}
    units = [{"unit_id": "a1", "arm": "anchor", "process_id": "proc-a",
              "expected_prompt_ids": ["p1"], "order_index": 0, "pair_id": None},
             {"unit_id": "c1", "arm": "candidate", "process_id": "proc-c",
              "expected_prompt_ids": ["p1"], "order_index": 1, "pair_id": None}]
    plan = {"schema": "epyc.autokernel.experiment_plan.v1", "plan_id": "plan-1",
            "campaign_id": "campaign-1", "category": "CANDIDATE", "phase": "discovery",
            "target_revision": "revision-1", "epoch": "epoch-1",
            "instrument_class": "serving", "comparison_kind": "mechanism",
            "estimand": "level", "changed_factors": ["factor-a"],
            "record_class": "discovery_screen", "intended_use": "explore",
            "protocol_ref": "P-test", "protocol_status": "ratified",
            "metric": "aggregate_tok_s", "metric_direction": "higher",
            "estimator_id": "median.v1", "unit": "process",
            "stopping": {"kind": "fixed_n", "n_per_arm": 1, "paired": False},
            "expected_units": units, "anchor_identity": identities["anchor"],
            "candidate_identity": identities["candidate"],
            "required_witnesses": ["identity", "teardown"], "calibration_ref": None,
            "policy_snapshot": {"reference": "MEASUREMENT.md@FLOOR-UNIT-1",
                                "digest": "9" * 64},
            "continuation_allowed": False}
    plan_digest = _hash(plan)
    worker = {"supervisor_id": "supervisor-1", "supervisor_incarnation": 2,
              "config_generation": 3, "worker_id": "worker-1", "worker_incarnation": 4}
    request = {"phase": "measurement", "slot_index": 0, "prompt_id": "p1",
               "request_sha256": request_sha, "predicted_n": 8,
               "predicted_per_second": 10.0, "terminal": True, "error": None}
    observation = {"schema": "epyc.autokernel.serving_observation.v1",
                   "process_pid": 123, "requests": [request],
                   "residency": {"status": "not_applicable"},
                   "teardown": "terminated", "failure": None}
    native_body = {"schema": "epyc.autokernel.planned_serving_artifact.v1",
                   "kind": "native_observation", "plan_digest": plan_digest,
                   "unit_id": "a1", "arm": "anchor", "process_generation_id": "proc-a",
                   "lineage_id": "lineage-1", "fence_id": "f-a1",
                   "comparison_identities": identities,
                   "grant_id": "grant-1", "container_id": "container-1",
                   "worker_identity": worker,
                   "observed_started_at": "2026-09-09T00:00:00Z",
                   "observed_ended_at": "2026-09-09T00:00:01Z",
                   "prompt_manifest_digest": manifest["digest"],
                   "observations": [observation], "selected_observation": observation,
                   "value": 10.0, "error": None}
    native = {**native_body, "artifact_digest": _hash(native_body)}
    witnesses = {name: {"status": "pass", "ref": f"{name}:a1"}
                 for name in ("identity", "teardown", "contention", "placement")}
    attempt_body = {"schema": "epyc.autokernel.planned_serving_artifact.v1",
                    "kind": "completed_attempt", "plan_digest": plan_digest,
                    "unit_id": "a1", "arm": "anchor", "process_generation_id": "proc-a",
                    "lineage_id": "lineage-1", "fence_id": "f-a1",
                    "comparison_identities": identities,
                    "grant_id": "grant-1", "container_id": "container-1",
                    "worker_identity": worker,
                    "observed_started_at": "2026-09-09T00:00:00Z",
                    "observed_ended_at": "2026-09-09T00:00:01Z",
                    "prompt_manifest_digest": manifest["digest"], "prompt_ids": ["p1"],
                    "native_observation_digest": native["artifact_digest"],
                    "stage_witnesses": witnesses, "terminal": True, "value": 10.0,
                    "provider_recorded_screen": "clean", "recorded_screen": "clean",
                    "reason": None}
    attempt = {**attempt_body, "artifact_digest": _hash(attempt_body)}
    stored_native = _write(root, "raw-native.json", native)
    stored_attempt = _write(root, "raw-attempt.json", attempt)
    selected = {"schema": "epyc.autokernel.raw_unit.v1", "plan_digest": plan_digest,
                "unit_id": "a1", "arm": "anchor", "process_id": "proc-a",
                "prompt_ids": ["p1"], "value": 10.0, "observed_order_index": 0,
                "terminal": True, "recorded_screen": "clean", "reason": None,
                "witnesses": witnesses, "artifact_digest": attempt["artifact_digest"]}
    peer = {"schema": "epyc.autokernel.raw_unit.v1", "plan_digest": plan_digest,
            "unit_id": "c1", "arm": "candidate", "process_id": "proc-c",
            "prompt_ids": ["p1"], "value": 10.0, "observed_order_index": 1,
            "terminal": True, "recorded_screen": "clean", "reason": None,
            "witnesses": {name: {"status": "pass", "ref": f"{name}:c1"}
                          for name in ("identity", "teardown", "contention", "placement")},
            "artifact_digest": "0" * 64}
    view_body = {"schema": "epyc.autokernel.admissible_unit_view.v1",
                 "plan_digest": plan_digest, "selected_rows": [selected, peer],
                 "independent_n": {"anchor": 1, "candidate": 1}, "complete": True,
                 "missing_expected_units": [], "rejection_reasons": {}}
    view = {**view_body, "view_digest": _hash(view_body)}
    measurement_id = _hash({"producer": arm.PRODUCER_ID, "plan_digest": plan_digest,
                            "lineage_id": "lineage-1", "arm": "anchor"})
    body = {"schema": arm.CAPTURE_SCHEMA, "producer": arm.PRODUCER_ID,
            "measurement_id": measurement_id, "arm": "anchor",
            "arm_locator": f"planned-serving:{plan_digest}:lineage-1:anchor",
            "plan": plan, "prompt_manifest": manifest,
            "prompt_manifest_digest": manifest["digest"], "lineage_id": "lineage-1",
            "comparison_identities": identities,
            "source_identity": {"source_revision": "a" * 40,
                                "model_sha256": "5" * 64, "build_sha256": "6" * 64,
                                "recipe_hash": "1" * 64},
            "capture_context": {"campaign_id": "campaign-1", "config_digest": "a" * 64,
                                "supervisor_id": "supervisor-1",
                                "supervisor_incarnation": 2, "config_generation": 3,
                                "worker_id": "worker-1", "worker_incarnation": 4,
                                "grant_id": "grant-1", "container_id": "container-1",
                                "lineage_id": "lineage-1",
                                "instrument_id": "planned-serving/v1",
                                "protocol_id": "P-test", "protocol_status": "ratified",
                                "source_identities": {
                                    "anchor": {"source_revision": "a" * 40,
                                               "model_sha256": "5" * 64,
                                               "build_sha256": "6" * 64,
                                               "recipe_hash": "1" * 64},
                                    "candidate": {"source_revision": "b" * 40,
                                                  "model_sha256": "5" * 64,
                                                  "build_sha256": "6" * 64,
                                                  "recipe_hash": "8" * 64}}},
            "admissible_view": view,
            "raw_artifacts": [{"document": native, "stored": stored_native},
                              {"document": attempt, "stored": stored_attempt}],
            "environment_verdicts": [{"unit_id": "a1",
                "contention": {"verdict": "clean", "ref": "contention:a1"},
                "placement": {"verdict": "proven", "ref": "placement:a1"},
                "residency": {"verdict": "not_applicable", "ref": None}}],
            "status": status, "diagnostic_reason": None if status == "measurement" else "x",
            "measurement": ({"metric": "aggregate_tok_s", "value": 10.0,
                             "unit": "t/s", "independent_unit": "process",
                             "direction": "higher", "independent_n": 1,
                             "reps_basis": "scored independent process launches",
                             "per_launch_values": [10.0]} if status == "measurement" else None),
            "claim": "anchor aggregate_tok_s for frozen plan plan-1",
            "category": "CANDIDATE", "phase": "discovery",
            "record_class": "discovery_screen", "intended_use": "explore",
            "protocol_id": "P-test", "protocol_status": "ratified",
            "instrument_id": "planned-serving/v1",
            "interval": {"start": "2026-09-09T00:00:00Z",
                         "end": "2026-09-09T00:00:01Z"}}
    return {**body, "carrier_digest": _hash(body)}


def v2_carrier_fixture(root: Path, *, instrument_extra: bool = False,
                       observation_extra: bool = False):
    """Closed synthetic v2 bytes, independent of the not-yet-published bridge."""
    carrier = carrier_fixture(root)
    callable_identity = {"module": "fixture", "qualname": "fixture", "kind": "python",
                         "implementation_status": "pinned",
                         "implementation_sha256": "a" * 64,
                         "configuration_status": "pinned",
                         "configuration_sha256": "b" * 64}
    instrument_body = {
        "schema": "epyc.autokernel.loaded_serving_instrument.v1",
        "scope": "fixture", "identity_basis": "fixture",
        "measurement_callable": callable_identity,
        "clock_callable": dict(callable_identity, qualname="clock"),
        "supporting_callables": [], "used_constants": {},
        "dependency_versions": {"python": "fixture"}, "configuration_complete": True,
    }
    if instrument_extra:
        instrument_body["unexpected"] = True
    instrument = {**instrument_body, "sha256": _hash(instrument_body)}
    instrument_ref_body = {
        "schema": "epyc.autokernel.loaded_serving_instrument_reference.v1",
        "identity_sha256": instrument["sha256"], "configuration_complete": True,
        "artifact": _write(root, "loaded-instrument.json", instrument),
    }
    instrument_ref = {**instrument_ref_body,
                      "reference_digest": _hash(instrument_ref_body)}

    carrier["schema"] = arm.CAPTURE_SCHEMA_V2
    carrier["producer"] = arm.PRODUCER_ID_V2
    plan = carrier["plan"]
    plan["schema"] = "epyc.autokernel.experiment_plan.v2"
    plan["loaded_instrument"] = instrument_ref
    for identity in (plan["anchor_identity"], plan["candidate_identity"]):
        identity.update({"schema": "epyc.autokernel.serving_arm_identity.v2",
                         "instrument_identity_sha256": instrument["sha256"],
                         "instrument_configuration_complete": True})
    plan_digest = _hash(plan)
    carrier["loaded_instrument"] = instrument_ref
    carrier["comparison_identities"] = {
        "anchor": plan["anchor_identity"], "candidate": plan["candidate_identity"]}
    carrier["capture_context"]["instrument_id"] = instrument["sha256"]
    carrier["instrument_id"] = instrument["sha256"]

    native = carrier["raw_artifacts"][0]["document"]
    attempt = carrier["raw_artifacts"][1]["document"]
    worker_binding = {"worker_id": "worker-1", "worker_incarnation": 4,
                      "grant_id": "grant-1", "grant_generation": 5,
                      "container_identity": {"path": "/fixture", "dev": 1, "ino": 2,
                                             "uid": 3, "nlink": 1, "mode": 16832}}
    observation_body = {
        "schema": "epyc.autokernel.lifecycle_observation.v1",
        "detector_version": "autokernel-lifecycle-observer-2",
        "observation_id": "obs-a1", "backend": "cpu",
        "instrument_identity_digest": instrument["sha256"],
        "recipe_identity_digest": "c" * 64, "clock_domain": "boot-1",
        "cadence_s": 0.1, "gap_limit_s": 1.0,
        "started_monotonic_s": 1.0, "ended_monotonic_s": 2.0,
        "started_at": "2026-09-09T00:00:00Z", "ended_at": "2026-09-09T00:00:01Z",
        "boot_id": "boot-1", "worker_binding": worker_binding,
        "held_claim": {"logical_cpus": [0], "gpu_devices": [], "physical_cpus": [0]},
        "requested_effective_state": {"logical_cpus": [0], "numa_nodes": [0],
                                      "thp_mode": "never"},
        "budgets": {}, "topology": None,
        "target_binding": {"pid": 123, "start_ticks": 456, "boot_id": "boot-1",
                           "worker_binding": worker_binding, "binding_ref": "descendant-a1"},
        "phase_boundaries": [], "load_window": {"start": None, "end": None,
                                                   "status": "unknown"},
        "samples": [], "intervals": [], "observer_cost": {},
        "shutdown": {"status": "resolved", "successor_permitted": True,
                     "late_writes_accepted": False},
        "completeness": "unknown", "issues": [], "residency": {},
        "verdict": {"status": "not_evaluated", "reason": None},
    }
    if observation_extra:
        observation_body["unexpected"] = True
    observation = {**observation_body, "content_sha256": _hash(observation_body)}
    reference_body = {
        "schema": "epyc.autokernel.lifecycle_observation_reference.v1",
        "observation_id": "obs-a1", "unit_id": "a1",
        "process_generation_id": "proc-a", "fence_id": "f-a1",
        "active_claim_ref": "claim-a1", "target_pid": 123,
        "target_start_ticks": 456, "descendant_binding_ref": "descendant-a1",
        "worker_id": "worker-1", "worker_generation": 4,
        "grant_id": "grant-1", "grant_generation": 5,
        "container_id": "container-1",
        "instrument_identity_sha256": instrument["sha256"],
        "observation_content_sha256": observation["content_sha256"],
        "shutdown_status": "resolved", "successor_permitted": True,
        "artifact": _write(root, "lifecycle-observation.json", observation),
    }
    reference = {**reference_body, "reference_digest": _hash(reference_body)}
    carrier["lifecycle_observations"] = [reference]
    for document in (native, attempt):
        document["schema"] = "epyc.autokernel.planned_serving_artifact.v2"
        document["plan_digest"] = plan_digest
        document["comparison_identities"] = carrier["comparison_identities"]
    native["lifecycle_observation"] = reference
    attempt["lifecycle_observation_content_sha256"] = observation["content_sha256"]
    carrier["admissible_view"]["plan_digest"] = plan_digest
    for row in carrier["admissible_view"]["selected_rows"]:
        row["plan_digest"] = plan_digest
    _reseal_raw(root, carrier)
    carrier["measurement_id"] = _hash({
        "producer": arm.PRODUCER_ID_V2, "plan_digest": plan_digest,
        "lineage_id": carrier["lineage_id"], "arm": carrier["arm"],
        "capture_schema": arm.CAPTURE_SCHEMA_V2,
        "instrument_identity_sha256": instrument["sha256"],
    })
    carrier["arm_locator"] = f"planned-serving:{plan_digest}:lineage-1:anchor"
    body = dict(carrier)
    body.pop("carrier_digest")
    carrier["carrier_digest"] = _hash(body)
    return carrier


def test_exact_carrier_projects_one_tuple_and_shared_ladder(tmp_path):
    carrier = carrier_fixture(tmp_path)
    path = tmp_path / "carrier.json"
    path.write_text(json.dumps(carrier, indent=2, sort_keys=True))
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    native = arm.native_rows(carrier, receipt_locator=f"autokernel:{path}",
                             receipt_sha256=digest, attestation_present=True,
                             corpus_root=tmp_path)[0]
    projected = arm.project(native)
    assert projected.value == 10.0 and projected.reps == 1
    assert projected.unit == "t/s" and projected.extra["independent_unit"] == "process"
    assert projected.extra["applicability"] == "observation_only"
    assert grade(projected)[0] in {"Witnessed", "Verified", "Judged"}


def test_v1_fixture_bytes_and_measurement_identity_are_frozen(tmp_path):
    carrier = carrier_fixture(tmp_path)
    assert _hash(carrier) == "aa57cd56f0330f9546cdb6fbedf32e6338dad9f38cc52172efec4f0e4446b7b1"
    assert carrier["measurement_id"] == \
        "9f9d6721e2396137eec3eac98cdf9da9721cdac7dca3e6806a216ce53f46b872"


def test_closed_v2_carrier_projects_without_effect_or_nomination_authority(tmp_path):
    carrier = v2_carrier_fixture(tmp_path)
    native = arm.native_rows(carrier, receipt_locator="v2:carrier",
                             receipt_sha256="a" * 64, attestation_present=True,
                             corpus_root=tmp_path)[0]
    projected = arm.project(native)
    assert projected.value == 10.0
    assert projected.extra["capture_schema"] == arm.CAPTURE_SCHEMA_V2
    assert projected.extra["instrument_identity_sha256"] == \
        carrier["loaded_instrument"]["identity_sha256"]
    assert projected.extra["lifecycle_observation_references"] == \
        carrier["lifecycle_observations"]
    assert projected.extra["applicability"] == "observation_only"
    assert "effect" not in projected.extra and "nomination" not in projected.extra


@pytest.mark.parametrize("fixture_kwargs,label", [
    ({"instrument_extra": True}, "loaded instrument identity"),
    ({"observation_extra": True}, "lifecycle observation"),
])
def test_v2_reopened_artifacts_are_closed_even_when_rehashed(tmp_path, fixture_kwargs, label):
    carrier = v2_carrier_fixture(tmp_path, **fixture_kwargs)
    with pytest.raises(ProjectionError, match=label):
        arm.native_rows(carrier, receipt_locator="v2:carrier",
                        receipt_sha256="a" * 64, corpus_root=tmp_path)


def test_v2_selected_serving_pid_must_equal_lifecycle_target_pid(tmp_path):
    carrier = v2_carrier_fixture(tmp_path)
    native = carrier["raw_artifacts"][0]["document"]
    native["selected_observation"]["process_pid"] = 124
    # The selected row is also the terminal member of observations; resealing
    # proves refusal comes from the cross-artifact PID binding, not a stale hash.
    assert native["observations"][-1]["process_pid"] == 124
    _reseal_raw(tmp_path, carrier)
    with pytest.raises(ProjectionError, match="serving PID differs"):
        arm.native_rows(carrier, receipt_locator="v2:carrier",
                        receipt_sha256="a" * 64, corpus_root=tmp_path)


@pytest.mark.parametrize("mutation", ["container", "target_worker", "target_boot"])
def test_v2_lifecycle_artifact_binds_container_worker_and_boot(tmp_path, mutation):
    carrier = v2_carrier_fixture(tmp_path)
    reference = carrier["lifecycle_observations"][0]
    path = tmp_path / reference["artifact"]["locator"]
    observation = json.loads(path.read_text())
    if mutation == "container":
        observation["worker_binding"]["container_identity"]["ino"] += 1
    elif mutation == "target_worker":
        observation["target_binding"]["worker_binding"]["worker_id"] = "other"
    else:
        observation["target_binding"]["boot_id"] = "other-boot"
    observation_body = dict(observation)
    observation_body.pop("content_sha256")
    observation["content_sha256"] = _hash(observation_body)
    path.write_text(json.dumps(observation, indent=2, sort_keys=True))
    reference["artifact"]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    reference["observation_content_sha256"] = observation["content_sha256"]
    reference_body = dict(reference)
    reference_body.pop("reference_digest")
    reference["reference_digest"] = _hash(reference_body)
    carrier["raw_artifacts"][0]["document"]["lifecycle_observation"] = reference
    carrier["raw_artifacts"][1]["document"][
        "lifecycle_observation_content_sha256"] = observation["content_sha256"]
    _reseal_raw(tmp_path, carrier)

    with pytest.raises(ProjectionError, match="ownership mismatch"):
        arm.native_rows(carrier, receipt_locator="v2:carrier",
                        receipt_sha256="a" * 64, corpus_root=tmp_path)


@pytest.mark.parametrize("mutation", ["identity_metadata", "instrument_reference",
                                       "lifecycle_reference", "lifecycle_content",
                                       "attempt_link", "unknown_carrier_field"])
def test_v2_closed_bindings_refuse_mutation(tmp_path, mutation):
    carrier = v2_carrier_fixture(tmp_path)
    if mutation == "identity_metadata":
        carrier["comparison_identities"]["anchor"][
            "instrument_configuration_complete"] = False
    elif mutation == "instrument_reference":
        carrier["loaded_instrument"]["identity_sha256"] = "0" * 64
    elif mutation == "lifecycle_reference":
        carrier["lifecycle_observations"][0]["fence_id"] = "other"
    elif mutation == "lifecycle_content":
        carrier["lifecycle_observations"][0]["observation_content_sha256"] = "0" * 64
    elif mutation == "attempt_link":
        carrier["raw_artifacts"][1]["document"][
            "lifecycle_observation_content_sha256"] = "0" * 64
        _reseal_raw(tmp_path, carrier)
    else:
        carrier["unexpected"] = True
    if mutation != "attempt_link":
        body = dict(carrier)
        body.pop("carrier_digest")
        carrier["carrier_digest"] = _hash(body)
    with pytest.raises(ProjectionError):
        arm.native_rows(carrier, receipt_locator="v2:carrier",
                        receipt_sha256="a" * 64, corpus_root=tmp_path)


def test_v2_journal_envelope_uses_same_closed_dispatch(tmp_path):
    carrier = v2_carrier_fixture(tmp_path)
    stored = _write(tmp_path, "sealed-v2-carrier.json", carrier)
    envelope = {"journal_schema": arm.JOURNAL_SCHEMA, "event_id": "event-v2",
                "kind": arm.JOURNAL_KIND, "seq": 1, "campaign_id": "campaign-1",
                "record_id": carrier["measurement_id"],
                "written_at": "2026-09-09T00:00:02Z",
                "payload": {"schema": arm.CAPTURE_SCHEMA_V2,
                            "measurement_id": carrier["measurement_id"],
                            "carrier": carrier, "artifact": stored}}
    projected = arm.project_journal_event(envelope, corpus_root=tmp_path)
    assert projected is not None and projected.attestation_verified is True
    raw = json.dumps(envelope, sort_keys=True).encode()
    rows = corpus.rows_for_document(tmp_path / "events.jsonl#L1", envelope,
                                   hashlib.sha256(raw).hexdigest(), corpus_root=tmp_path)
    assert len(rows) == 1 and arm.project(rows[0]).measurement_id == projected.measurement_id


def test_journal_envelope_dispatches_through_real_corpus_path(tmp_path):
    carrier = carrier_fixture(tmp_path)
    stored = _write(tmp_path, "sealed-carrier.json", carrier)
    envelope = {"journal_schema": arm.JOURNAL_SCHEMA, "kind": arm.JOURNAL_KIND,
                "seq": 1, "record_id": carrier["measurement_id"],
                "payload": {"schema": arm.CAPTURE_SCHEMA,
                            "measurement_id": carrier["measurement_id"],
                            "carrier": carrier, "artifact": stored}}
    raw = json.dumps(envelope, sort_keys=True).encode()
    rows = corpus.rows_for_document(
        tmp_path / "journal.jsonl#L1", envelope, hashlib.sha256(raw).hexdigest(),
        corpus_root=tmp_path)
    assert len(rows) == 1
    projected = arm.project(rows[0])
    assert projected.measurement_id.startswith("akarm_")


def test_incremental_journal_projection_rederives_attestation_bytes(tmp_path):
    carrier = carrier_fixture(tmp_path)
    stored = _write(tmp_path, "sealed-carrier.json", carrier)
    envelope = {"journal_schema": arm.JOURNAL_SCHEMA, "event_id": "event-1",
                "kind": arm.JOURNAL_KIND, "seq": 1, "campaign_id": "campaign-1",
                "record_id": carrier["measurement_id"],
                "written_at": "2026-09-09T00:00:02Z",
                "payload": {"schema": arm.CAPTURE_SCHEMA,
                            "measurement_id": carrier["measurement_id"],
                            "carrier": carrier, "artifact": stored}}
    projected = arm.project_journal_event(envelope, corpus_root=tmp_path)
    assert projected is not None
    assert projected.attestation_verified is True
    assert grade(projected)[:2] == ("Witnessed", "Attested")

    (tmp_path / "sealed-carrier.json").write_text("{}")
    with pytest.raises(ProjectionError, match="digest mismatch"):
        arm.project_journal_event(envelope, corpus_root=tmp_path)


def test_incremental_journal_projection_requires_outer_carrier_equality(tmp_path):
    carrier = carrier_fixture(tmp_path)
    other = json.loads(json.dumps(carrier))
    other["capture_context"]["config_digest"] = "b" * 64
    body = dict(other)
    body.pop("carrier_digest")
    other["carrier_digest"] = _hash(body)
    stored = _write(tmp_path, "other-carrier.json", other)
    envelope = {"journal_schema": arm.JOURNAL_SCHEMA, "event_id": "event-1",
                "kind": arm.JOURNAL_KIND, "seq": 1, "campaign_id": "campaign-1",
                "record_id": carrier["measurement_id"],
                "written_at": "2026-09-09T00:00:02Z",
                "payload": {"schema": arm.CAPTURE_SCHEMA,
                            "measurement_id": carrier["measurement_id"],
                            "carrier": carrier, "artifact": stored}}
    with pytest.raises(ProjectionError, match="exact carrier"):
        arm.project_journal_event(envelope, corpus_root=tmp_path)


@pytest.mark.parametrize("mode", ["escape", "symlink"])
def test_incremental_journal_projection_refuses_outer_artifact_path_tricks(tmp_path, mode):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    carrier = carrier_fixture(corpus)
    outside = tmp_path / "outside-carrier.json"
    outside.write_text(json.dumps(carrier, sort_keys=True))
    if mode == "escape":
        locator = "../outside-carrier.json"
    else:
        (corpus / "carrier-link.json").symlink_to(outside)
        locator = "carrier-link.json"
    stored = {"locator": locator,
              "sha256": hashlib.sha256(outside.read_bytes()).hexdigest(),
              "verified": True}
    envelope = {"journal_schema": arm.JOURNAL_SCHEMA, "event_id": "event-1",
                "kind": arm.JOURNAL_KIND, "seq": 1, "campaign_id": "campaign-1",
                "record_id": carrier["measurement_id"],
                "written_at": "2026-09-09T00:00:02Z",
                "payload": {"schema": arm.CAPTURE_SCHEMA,
                            "measurement_id": carrier["measurement_id"],
                            "carrier": carrier, "artifact": stored}}
    with pytest.raises(ProjectionError, match="escapes"):
        arm.project_journal_event(envelope, corpus_root=corpus)


def test_corpus_deduplicates_standalone_carrier_and_journal_event(tmp_path):
    carrier = carrier_fixture(tmp_path)
    stored = _write(tmp_path, "sealed-carrier.json", carrier)
    envelope = {"journal_schema": arm.JOURNAL_SCHEMA, "kind": arm.JOURNAL_KIND,
                "seq": 1, "record_id": carrier["measurement_id"],
                "payload": {"schema": arm.CAPTURE_SCHEMA,
                            "measurement_id": carrier["measurement_id"],
                            "carrier": carrier, "artifact": stored}}
    (tmp_path / "events.jsonl").write_text(json.dumps(envelope) + "\n")

    class Ledger:
        def __init__(self):
            self.frames = []

        def append(self, frame):
            self.frames.append(frame)

    report = corpus.ingest_corpus(
        Ledger(), root=tmp_path, as_of="2026-09-09T00:00:02Z")
    assert report["rows_projected"] == 1
    assert report["duplicate_measurements"] == 1


def test_corpus_quarantines_same_native_id_with_conflicting_carrier_bytes(tmp_path):
    first = carrier_fixture(tmp_path)
    second = json.loads(json.dumps(first))
    second["capture_context"]["config_digest"] = "b" * 64
    body = dict(second)
    body.pop("carrier_digest")
    second["carrier_digest"] = _hash(body)
    (tmp_path / "carrier-a.json").write_text(json.dumps(first, sort_keys=True))
    (tmp_path / "carrier-b.json").write_text(json.dumps(second, sort_keys=True))

    class Ledger:
        def __init__(self):
            self.frames = []

        def append(self, frame):
            self.frames.append(frame)

    ledger = Ledger()
    report = corpus.ingest_corpus(
        ledger, root=tmp_path, as_of="2026-09-09T00:00:02Z")
    assert report["rows_projected"] == 0 and report["refused"] == 2
    assert ledger.frames == []
    assert all("conflicting unified carriers" in item["reason"]
               for item in report["refusal_sample"])


def test_corpus_carries_actual_receipt_byte_verification(tmp_path):
    carrier = carrier_fixture(tmp_path)
    (tmp_path / "carrier.json").write_text(json.dumps(carrier, indent=2, sort_keys=True))

    class Ledger:
        def __init__(self):
            self.frames = []

        def append(self, frame):
            self.frames.append(frame)

    ledger = Ledger()
    corpus.ingest_corpus(ledger, root=tmp_path, as_of="2026-09-09T00:00:02Z")
    evidence = next(frame for frame in ledger.frames
                    if frame["frame_type"].endswith("evidence_supports_claim/v1"))
    assert evidence["assertion"]["grade"]["T"] == "Attested"


@pytest.mark.parametrize("mutation", ["carrier_digest", "recipe", "model", "np", "metric",
                                       "count", "time", "phase", "use", "protocol", "witness",
                                       "process", "request", "attempt_terminal", "outer_time",
                                       "near_value", "scalar_unit", "independent_unit",
                                       "native_time", "screen"])
def test_identity_count_label_and_witness_conflicts_refuse(tmp_path, mutation):
    carrier = carrier_fixture(tmp_path)
    if mutation == "carrier_digest": carrier["carrier_digest"] = "0" * 64
    elif mutation == "recipe": carrier["source_identity"]["recipe_hash"] = "0" * 64
    elif mutation == "model": carrier["source_identity"]["model_sha256"] = "0" * 64
    elif mutation == "np": carrier["measurement"]["independent_n"] = 2
    elif mutation == "metric": carrier["measurement"]["metric"] = "wall_throughput"
    elif mutation == "count": carrier["admissible_view"]["independent_n"]["anchor"] = 2
    elif mutation == "time": carrier["interval"]["end"] = "2026-09-08T00:00:00Z"
    elif mutation == "phase": carrier["phase"] = "release"
    elif mutation == "use": carrier["intended_use"] = "release"
    elif mutation == "protocol": carrier["protocol_id"] = "P-other"
    elif mutation == "witness": carrier["raw_artifacts"][1]["document"][
        "stage_witnesses"]["contention"] = {"status": "unknown", "ref": None}
    elif mutation == "process":
        carrier["raw_artifacts"][0]["document"]["process_generation_id"] = "wrong"
    elif mutation == "request":
        carrier["raw_artifacts"][0]["document"]["selected_observation"]["requests"][0][
            "prompt_id"] = "wrong"
    elif mutation == "attempt_terminal":
        carrier["raw_artifacts"][1]["document"]["terminal"] = False
    elif mutation == "outer_time":
        carrier["interval"]["start"] = "2026-09-08T00:00:00Z"
    elif mutation == "near_value":
        carrier["measurement"]["value"] += 5e-13
    elif mutation == "scalar_unit":
        carrier["measurement"]["unit"] = "process"
    elif mutation == "independent_unit":
        carrier["measurement"]["independent_unit"] = "session"
    elif mutation == "native_time":
        carrier["raw_artifacts"][0]["document"]["observed_ended_at"] = None
    elif mutation == "screen":
        carrier["raw_artifacts"][1]["document"]["provider_recorded_screen"] = "invented"
    if mutation in {"witness", "process", "request", "attempt_terminal", "native_time",
                    "screen"}:
        _reseal_raw(tmp_path, carrier)
    elif mutation != "carrier_digest":
        body = dict(carrier); body.pop("carrier_digest")
        carrier["carrier_digest"] = _hash(body)
    with pytest.raises(ProjectionError):
        arm.native_rows(carrier, receipt_locator="x", receipt_sha256="a" * 64,
                        corpus_root=tmp_path)


def test_diagnostic_and_unknown_schema_are_named_zero_projection(tmp_path):
    diagnostic = carrier_fixture(tmp_path, status="diagnostic")
    assert arm.native_rows(diagnostic, receipt_locator="x", receipt_sha256="a" * 64,
                           corpus_root=tmp_path) == ()
    assert arm.diagnostic_reason(diagnostic).startswith("diagnostic:")
    assert arm.diagnostic_reason({"schema": "epyc.unknown"}).startswith("refused:")
    assert arm.diagnostic_reason({"schema": arm.CAPTURE_SCHEMA,
                                  "producer": arm.PRODUCER_ID,
                                  "measurement_id": "a" * 64, "arm": [],
                                  "carrier_digest": "a" * 64}).startswith("refused:")


def test_another_valid_manifest_prompt_cannot_replace_unit_prompt(tmp_path):
    carrier = carrier_fixture(tmp_path)
    another = json.loads(json.dumps(carrier["prompt_manifest"]["prompts"][0]))
    another["prompt_id"] = "p2"
    carrier["prompt_manifest"]["prompts"].append(another)
    manifest_body = dict(carrier["prompt_manifest"])
    manifest_body.pop("digest")
    carrier["prompt_manifest"]["digest"] = _hash(manifest_body)
    carrier["prompt_manifest_digest"] = carrier["prompt_manifest"]["digest"]
    native = carrier["raw_artifacts"][0]["document"]
    native["prompt_manifest_digest"] = carrier["prompt_manifest_digest"]
    native["selected_observation"]["requests"][0]["prompt_id"] = "p2"
    attempt = carrier["raw_artifacts"][1]["document"]
    attempt["prompt_manifest_digest"] = carrier["prompt_manifest_digest"]
    _reseal_raw(tmp_path, carrier)
    with pytest.raises(ProjectionError, match="request order"):
        arm.native_rows(carrier, receipt_locator="x", receipt_sha256="a" * 64,
                        corpus_root=tmp_path)


def test_duplicate_prompt_manifest_ids_are_refused(tmp_path):
    carrier = carrier_fixture(tmp_path)
    carrier["prompt_manifest"]["prompts"].append(
        json.loads(json.dumps(carrier["prompt_manifest"]["prompts"][0])))
    manifest_body = dict(carrier["prompt_manifest"])
    manifest_body.pop("digest")
    carrier["prompt_manifest"]["digest"] = _hash(manifest_body)
    body = dict(carrier)
    body.pop("carrier_digest")
    carrier["carrier_digest"] = _hash(body)
    with pytest.raises(ProjectionError, match="duplicate prompt IDs"):
        arm.native_rows(carrier, receipt_locator="x", receipt_sha256="a" * 64,
                        corpus_root=tmp_path)


@pytest.mark.parametrize("bad", [float("nan"), float("inf")])
def test_nonfinite_nested_data_is_a_typed_refusal(tmp_path, bad):
    carrier = carrier_fixture(tmp_path)
    carrier["measurement"]["value"] = bad
    carrier["carrier_digest"] = "a" * 64
    with pytest.raises(ProjectionError, match="canonical JSON"):
        arm.native_rows(carrier, receipt_locator="x", receipt_sha256="a" * 64,
                        corpus_root=tmp_path)
    assert arm.diagnostic_reason(carrier).startswith("refused:")


def test_artifact_reader_bounds_bytes_and_refuses_invalid_utf8(tmp_path):
    carrier = carrier_fixture(tmp_path)
    stored = carrier["raw_artifacts"][0]["stored"]
    path = tmp_path / stored["locator"]
    path.write_bytes(b"\xff")
    stored["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    body = dict(carrier)
    body.pop("carrier_digest")
    carrier["carrier_digest"] = _hash(body)
    with pytest.raises(ProjectionError, match="not JSON"):
        arm.native_rows(carrier, receipt_locator="x", receipt_sha256="a" * 64,
                        corpus_root=tmp_path)


def test_artifact_reader_refuses_fifo_without_blocking(tmp_path):
    os.mkfifo(tmp_path / "fifo")
    code = (
        "from pathlib import Path; "
        "from adapters import autokernel_unified_arm as arm; "
        "from claim_tuple import ProjectionError; "
        "\ntry: arm._artifact_bytes(Path(r'%s'), 'fifo', '0' * 64)"
        "\nexcept ProjectionError: pass"
        "\nelse: raise SystemExit('FIFO was accepted')" % tmp_path)
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "scripts" / "vidya")
    subprocess.run(
        [sys.executable, "-c", code], env=env, check=True, timeout=1,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    carrier = carrier_fixture(tmp_path)
    stored = carrier["raw_artifacts"][0]["stored"]
    path = tmp_path / stored["locator"]
    with path.open("wb") as stream:
        stream.truncate(64 * 1024 * 1024 + 1)
    stored["sha256"] = "b" * 64
    body = dict(carrier)
    body.pop("carrier_digest")
    carrier["carrier_digest"] = _hash(body)
    with pytest.raises(ProjectionError, match="bounded"):
        arm.native_rows(carrier, receipt_locator="x", receipt_sha256="a" * 64,
                        corpus_root=tmp_path)


def test_project_is_total_for_malformed_native_wrapper():
    with pytest.raises(ProjectionError):
        arm.project({"source": {}, "corpus_root": []})


@pytest.mark.parametrize("link_kind", ["hardlink", "symlink"])
def test_external_raw_artifact_links_are_refused(tmp_path, link_kind):
    carrier = carrier_fixture(tmp_path)
    raw_path = tmp_path / carrier["raw_artifacts"][0]["stored"]["locator"]
    outside = tmp_path / "outside"
    outside.write_bytes(raw_path.read_bytes())
    raw_path.unlink()
    if link_kind == "hardlink":
        os.link(outside, raw_path)
    else:
        raw_path.symlink_to(outside)
    with pytest.raises(ProjectionError):
        arm.native_rows(carrier, receipt_locator="x", receipt_sha256="a" * 64,
                        corpus_root=tmp_path)


@pytest.mark.parametrize("path,value", [
    (("measurement", "per_launch_values"), None),
    (("admissible_view", "selected_rows"), [None]),
    (("plan", "expected_units"), [None]),
    (("raw_artifacts",), [None]),
    (("interval",), {"start": None, "end": []}),
])
def test_malformed_nested_values_are_typed_refusals(tmp_path, path, value):
    carrier = carrier_fixture(tmp_path)
    target = carrier
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    body = dict(carrier); body.pop("carrier_digest")
    carrier["carrier_digest"] = _hash(body)
    with pytest.raises(ProjectionError):
        arm.native_rows(carrier, receipt_locator="x", receipt_sha256="a" * 64,
                        corpus_root=tmp_path)


def test_real_research_producer_artifact_projects_cross_repo(tmp_path):
    configured = os.environ.get("EPYC_RESEARCH_ROOT")
    candidates = [Path(configured)] if configured else []
    research = next((item for item in candidates
                     if (item / "scripts/kernel_rnd/autokernel/loop/measurement_capture.py").is_file()),
                    None)
    if research is None:
        pytest.skip("set EPYC_RESEARCH_ROOT for the cross-repo producer conformance test")
    sys.path.insert(0, str(research / "scripts" / "kernel_rnd"))
    from autokernel.loop.test_measurement_capture import _run

    producer_root = tmp_path / "producer"
    producer_root.mkdir()
    result, _, _ = _run(producer_root)
    receipt = dict(result.capture_receipts[0]["artifact"])
    artifact_root = tmp_path / "producer" / "artifacts"
    carrier = json.loads((artifact_root / receipt["locator"]).read_text())
    native = arm.native_rows(carrier, receipt_locator="cross-repo:carrier",
                             receipt_sha256=receipt["sha256"], attestation_present=True,
                             corpus_root=artifact_root)
    assert len(native) == 1 and arm.project(native[0]).value == 20.0
