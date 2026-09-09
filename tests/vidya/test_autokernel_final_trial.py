"""Actual research issuance -> ROOT readback; no synthetic measurement positive."""
import copy
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/vidya"))
from adapters import autokernel_corpus as corpus
from adapters import autokernel_final_trial as final
from adapters import autokernel_unified_arm as arm
from claim_tuple import ProjectionError


@pytest.fixture(scope="module")
def actual(tmp_path_factory):
    configured = os.environ.get("EPYC_RESEARCH_ROOT")
    if not configured:
        pytest.skip("set EPYC_RESEARCH_ROOT for actual parent-final producer conformance")
    research = Path(configured).resolve()
    test = research / "scripts/kernel_rnd/autokernel/loop/test_native_final_trial.py"
    assert test.is_file(), "research dependency lacks the published original final-trial producer test"
    base = tmp_path_factory.mktemp("actual-final-source") / "pytest"
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(research / "scripts/kernel_rnd")
    completed = subprocess.run([sys.executable, "-m", "pytest", "-q", str(test),
        "-k", "actual_child_http_original_issuer_final_pair_capture_and_restart",
        "--basetemp", str(base)], cwd=research, env=environment,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=180, check=False)
    assert completed.returncode == 0, completed.stdout
    case = base / "test_actual_child_http_origina0" / "controller"
    rows = [json.loads(line) for line in (case / "journal/events.jsonl").read_text().splitlines()]
    events = [row for row in rows if row.get("payload", {}).get("schema") == arm.CAPTURE_SCHEMA_V3]
    assert len(events) == 2
    return case / "unified-native-artifacts", events


def _write(root, namespace, body):
    name = f"{hashlib.sha256(namespace.encode()).hexdigest()}-{arm._hash(body)}.json"
    raw = json.dumps(body, indent=2, sort_keys=True).encode()
    path = root / name
    if path.exists():
        assert path.read_bytes() == raw
    else:
        path.write_bytes(raw)
    return {"locator": name, "sha256": hashlib.sha256(raw).hexdigest(), "verified": True}


def _body(root, reference):
    return arm._artifact_bytes(root, reference["locator"], reference["sha256"])


def _reseal(event, root, body):
    """Reseal malicious test input, never append it or call it original issuance."""
    event = copy.deepcopy(event)
    payload = event["payload"]
    carrier = payload["carrier"]
    digest = arm._hash(body)
    carrier["parent_final_trial"] = {"schema": final.REFERENCE_SCHEMA, "digest": digest,
        "artifact": _write(root, f"parent-final-trial:{digest}", body)}
    identity = {"producer": arm.PRODUCER_ID_V3, "capture_schema": arm.CAPTURE_SCHEMA_V3,
        "plan_digest": arm._hash(carrier["plan"]), "lineage_id": carrier["lineage_id"], "arm": carrier["arm"],
        "instrument_identity_sha256": carrier["loaded_instrument"]["identity_sha256"],
        "parent_final_trial_digest": digest}
    measurement_id = arm._hash(identity)
    carrier["measurement_id"] = measurement_id
    carrier["arm_locator"] = f"parent-final-serving:{identity['plan_digest']}:{carrier['lineage_id']}:{carrier['arm']}:{digest}"
    carrier.pop("carrier_digest")
    carrier["carrier_digest"] = arm._hash(carrier)
    payload.update(measurement_id=measurement_id, artifact=_write(root, f"carrier:{measurement_id}", carrier))
    event["record_id"] = measurement_id
    return event


def test_actual_child_parent_pair_final_journal_remains_diagnostic(actual):
    root, events = actual
    for event in events:
        assert arm.project_journal_event(event, corpus_root=root) is None
        assert arm.diagnostic_reason(event, corpus_root=root).startswith("diagnostic:")
        assert corpus._dispatch_schema(event) == arm.CAPTURE_SCHEMA_V3
        assert corpus.rows_for_document(root / "events.jsonl", event, arm._hash(event), corpus_root=root) == []


@pytest.mark.parametrize("field", ["parent_final_trial", "original_arm_capture"])
@pytest.mark.parametrize("value", [None, [], 7, "not-a-reference"])
def test_public_corpus_rejects_nonobject_v3_references(actual, field, value):
    root, events = actual
    event = copy.deepcopy(events[0])
    event["payload"]["carrier"][field] = value
    with pytest.raises(ProjectionError):
        corpus.rows_for_document(root / "malicious.jsonl", event, arm._hash(event), corpus_root=root)


@pytest.mark.parametrize("mutation", ["unknown", "terminal", "start_unknown", "fence_unknown",
    "prefix", "original_unit_order", "final_value", "source", "wrong_original_arm"])
def test_resealed_final_fact_mutations_refuse(actual, mutation):
    root, events = actual
    event = events[0]
    body = _body(root, event["payload"]["carrier"]["parent_final_trial"]["artifact"])
    if mutation == "unknown":
        body["unknown"] = True
    elif mutation == "terminal":
        body["accepted_terminal"]["accepted"] = False
    elif mutation == "start_unknown":
        body["worker_start"]["unknown"] = True
    elif mutation == "fence_unknown":
        body["result_fence"]["unknown"] = True
    elif mutation == "prefix":
        body["original_unit_receipts"].pop()
    elif mutation == "original_unit_order":
        body["original_raw_units"].reverse()
    elif mutation == "final_value":
        body["final_rows"][0]["row"]["value"] += 1.0
    elif mutation == "source":
        body["source_identity"]["finalizer"]["producer_id"] = "foreign"
    else:
        body["original_arm_captures"]["anchor"] = body["original_arm_captures"]["candidate"]
    with pytest.raises(ProjectionError):
        arm.project_journal_event(_reseal(event, root, body), corpus_root=root)


def test_nested_v3_original_refuses_before_recursive_dispatch(actual, monkeypatch):
    root, events = actual
    event = events[0]
    body = _body(root, event["payload"]["carrier"]["parent_final_trial"]["artifact"])
    original = body["original_arm_captures"]["anchor"]
    old = _body(root, original["artifact"])
    old["schema"] = arm.CAPTURE_SCHEMA_V3
    old.pop("carrier_digest")
    old["carrier_digest"] = arm._hash(old)
    original["carrier_digest"] = old["carrier_digest"]
    original["artifact"] = _write(root, f"carrier:{original['measurement_id']}", old)
    dispatch = arm._validate
    calls = []
    def checked(source, **kwargs):
        calls.append(source.get("schema"))
        assert len(calls) == 1, "original v3 recursively dispatched with a fresh budget"
        return dispatch(source, **kwargs)
    monkeypatch.setattr(arm, "_validate", checked)
    with pytest.raises(ProjectionError, match="original v2 arm"):
        arm.project_journal_event(_reseal(event, root, body), corpus_root=root)


def test_arbitrary_seventeen_gate_names_cannot_replace_original_membership(actual):
    root, events = actual
    body = _body(root, events[0]["payload"]["carrier"]["parent_final_trial"]["artifact"])
    pair = _body(root, body["scientific_pair_reference"]["artifact"])
    unit = pair["ordered_units"][0]
    inputs = _body(root, unit["original_inputs"])
    owning = _body(root, unit["original_owning_t0"])
    evidence = unit["final_evidence"]
    evidence["report"]["gate_ids"] = [f"fake-gate-{index}" for index in range(17)]
    with pytest.raises(ProjectionError, match="canonical owning gate membership"):
        final._report_status(evidence, unit["original_frame"]["expected_prompt_ids"], inputs["request_by_slot"], owning)


@pytest.mark.parametrize("mutation", ["same_ids_foreign_lifecycle", "foreign_capture_reference"])
def test_original_result_reference_exactness_not_only_membership(actual, mutation):
    root, events = actual
    event = events[0]
    body = _body(root, event["payload"]["carrier"]["parent_final_trial"]["artifact"])
    reference = body["result_reference"]
    result = arm._artifact_bytes(root, reference["result_locator"], reference["result_sha256"])
    if mutation == "same_ids_foreign_lifecycle":
        rows = result["lifecycle_observation_references"]
        original_ids = [row["unit_id"] for row in rows]
        rows[0]["artifact"] = copy.deepcopy(rows[1]["artifact"])
        rows[0].pop("reference_digest")
        rows[0]["reference_digest"] = arm._hash(rows[0])
        result["run"]["lifecycle_observation_references"] = copy.deepcopy(rows)
        assert [row["unit_id"] for row in rows] == original_ids
        reason = "result exact original lifecycle reference"
    else:
        capture = result["captures"][0]
        capture["artifact"] = copy.deepcopy(result["captures"][1]["artifact"])
        reason = "original deferred carrier reference"
    result.pop("result_digest")
    result["result_digest"] = arm._hash(result)
    stored = _write(root, f"planned-worker-result:{body['prepared_digest']}:{body['worker_start']['nonce']}", result)
    reference.update(result_locator=stored["locator"], result_sha256=stored["sha256"],
                     result_digest=result["result_digest"])
    reference.pop("reference_digest")
    reference["reference_digest"] = arm._hash(reference)
    body["accepted_terminal"]["result_digest"] = arm._hash(reference)
    with pytest.raises(ProjectionError, match=reason):
        arm.project_journal_event(_reseal(event, root, body), corpus_root=root)
