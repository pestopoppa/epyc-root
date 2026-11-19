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


# --- AKU-07o ROOT consumption: per-witness statuses, registry v3, 7-module pin set -------------
# Structural readback only. Hermetic synthetic records shaped like research 74e09ab48 / 2a208a221;
# they prove the ROOT reader's closed grammar, never a host or hardware claim. No grading here:
# the adapter projects, claim_tuple.grade() decides.
V2_REGISTRY = "epyc.autokernel.parent_scientific_witness_adapters.v2"


def _obs_source(name):
    return {"adapter_id": final.OBSERVATION_ADAPTERS[name], "witness": name, "callables": [],
            "helpers": [], "owning_protocols": []}


def _registry(schema=final.REGISTRY_V3, **slots):
    base = {"schema": schema, "correctness": {"adapter_id": final.ADAPTER_ID}, "purpose": None,
            "contention": None, "residency": None}
    return {**base, **slots}


def test_registry_v2_and_v3_are_closed_and_report_configured_observation_slots():
    assert final._registry(_registry(V2_REGISTRY)) == {}
    v3 = _registry(contention=_obs_source("contention"), residency=_obs_source("residency"))
    assert set(final._registry(v3)) == {"contention", "residency"}
    assert final._registry(_registry(contention=_obs_source("contention"))).keys() == {"contention"}


@pytest.mark.parametrize("mutate", [
    lambda r: r.update(schema="epyc.autokernel.parent_scientific_witness_adapters.v9"),
    lambda r: r.update(purpose=_obs_source("contention")),
    lambda r: r.update(schema=V2_REGISTRY, contention=_obs_source("contention")),
    lambda r: r.update(residency=_obs_source("contention")),
    lambda r: r.update(correctness=None),
    lambda r: r.update(extra=1),
    lambda r: r.update(contention={**_obs_source("contention"), "adapter_id": "foreign"}),
    lambda r: r.update(contention={**_obs_source("contention"), "unknown": 1}),
])
def test_registry_refuses_unsupported_grammar(mutate):
    registry = _registry()
    mutate(registry)
    with pytest.raises(ProjectionError):
        final._registry(registry)


def _selected(count, last="native_server_token_evidence.py"):
    modules = [{"path": f"/x/module_{index}.py"} for index in range(count)]
    if count == final.CURRENT_MODULE_COUNT:
        modules[-1] = {"path": f"/x/{last}"}
    return {"owning_source_pins": {"modules": modules}}


def test_pin_sets_accept_historical_six_and_current_seven_modules_only():
    assert final._pins(_selected(6)) is False
    assert final._pins(_selected(7)) is True
    for count in (0, 5, 8):
        with pytest.raises(ProjectionError):
            final._pins(_selected(count))
    with pytest.raises(ProjectionError, match="token-evidence"):
        final._pins(_selected(7, last="foreign.py"))


def _row(prompt, phase, slot, tokens, *, seed=7, v1=False):
    base = {"schema": final.TOKEN_ROW_SCHEMA, "prompt_id": prompt, "phase": phase,
            "slot_index": slot, "request_sha256": "a" * 64, "response_sha256": "b" * 64}
    if v1:
        return {**base, "basis": "v1_request_no_seed_token_request", "seed": None,
                "ignore_eos": None, "token_output_requested": None, "tokens": None}
    return {**base, "basis": "v2_explicit_seed_token_request", "seed": seed, "ignore_eos": True,
            "token_output_requested": True, "tokens": tokens}


def _token(overall, verdict, tokens=([1, 2], [1, 2]), unknown=None):
    rows = [_row("p0", "measurement", 0, list(tokens[0])), _row("p0", "measurement", 1, list(tokens[1]))]
    group = {"prompt_id": "p0", "seed": 7, "requests": 2, "slots": [["measurement", 0], ["measurement", 1]],
             "verdict": verdict, "first_divergence_index": None, "agreement_prefix_ratio": 1.0}
    return {"schema": final.TOKEN_WITNESS_SCHEMA, "evidence_class": "same_server_repeat_token_equality",
            "overall": overall, "groups": [group], "unknown_prompts": unknown or {},
            "is_t0_pass": False, "rows": rows}


def test_token_witness_identical_and_diverged_rederive_from_their_rows():
    final._token_witness(_token("identical", "identical"), {"status": "pass", "scope_defects": []}, pinned=True)
    diverged = _token("diverged", "diverged", tokens=([1, 2], [1, 3]))
    final._token_witness(diverged, {"status": "fail", "scope_defects": [final.TOKEN_DEFECT]}, pinned=True)


@pytest.mark.parametrize("mutate,evidence", [
    (lambda t: t.update(is_t0_pass=True), {"status": "pass", "scope_defects": []}),
    (lambda t: t.update(overall="bogus"), {"status": "pass", "scope_defects": []}),
    (lambda t: t.update(overall="diverged"), {"status": "fail", "scope_defects": [final.TOKEN_DEFECT]}),
    (lambda t: t["groups"][0].update(verdict="diverged"), {"status": "fail", "scope_defects": [final.TOKEN_DEFECT]}),
    (lambda t: t["rows"].__setitem__(0, _row("p0", "measurement", 0, [9, 9])), {"status": "pass", "scope_defects": []}),
    (lambda t: t.update(rows=[_row("p0", "measurement", 0, None, v1=True)]), {"status": "pass", "scope_defects": []}),
    (lambda t: t["rows"][0].update(basis="v1_request_no_seed_token_request"), {"status": "pass", "scope_defects": []}),
    (lambda t: t.update(extra=1), {"status": "pass", "scope_defects": []}),
])
def test_token_witness_refuses_tamper_and_never_confers_a_pass(mutate, evidence):
    token = _token("identical", "identical")
    mutate(token)
    with pytest.raises(ProjectionError):
        final._token_witness(token, evidence, pinned=True)


def test_token_witness_requires_pinned_module_and_recorded_failure_for_divergence():
    with pytest.raises(ProjectionError, match="pinned"):
        final._token_witness(_token("identical", "identical"), {"status": "pass", "scope_defects": []}, pinned=False)
    diverged = _token("diverged", "diverged", tokens=([1, 2], [1, 3]))
    with pytest.raises(ProjectionError, match="recorded failure"):
        final._token_witness(diverged, {"status": "pass", "scope_defects": []}, pinned=True)


def _receipt_case(tmp_path, name, status, *, backend_defects=()):
    source = _obs_source(name)
    lifecycle = {"artifact": {"locator": "l", "sha256": "c" * 64, "verified": True}}
    body = {"schema": final.WITNESS_SCHEMA, "witness": name, "adapter_id": final.OBSERVATION_ADAPTERS[name],
            "lifecycle_reference": lifecycle, "source": source, "status": status,
            "report": {"reason": "r", "facts": {}}, "scope_defects": list(backend_defects)}
    stored = _write(tmp_path, f"parent-scientific-witness:{arm._hash(body)}", body)
    reference = {"artifact": stored, "digest": arm._hash(body), "witness": name, "schema": final.WITNESS_SCHEMA}
    facts = {"receipt": reference, "report": body["report"], "scope_defects": body["scope_defects"],
             "adapter_source": source}
    digest = "d" * 64
    ref = f"parent-unit-evidence:{digest}#{name}" if status != "unknown" else None
    parent = {"findings": {name: {"status": status, "reason": "r", "facts": facts}}}
    return (parent, {"digest": digest}, {name: {"status": status, "ref": ref}},
            {"lifecycle_reference": lifecycle}, {name: source}, final._Reader(tmp_path), body)


@pytest.mark.parametrize("name", ["contention", "residency"])
@pytest.mark.parametrize("status", ["pass", "fail", "unknown"])
def test_observation_witness_receipt_reopens_per_witness(tmp_path, name, status):
    parent, receipt, witnesses, evidence, configured, reader, _ = _receipt_case(tmp_path, name, status)
    final._witness_receipts(parent, receipt, witnesses, evidence, configured, reader)


@pytest.mark.parametrize("mutation", ["finding_status", "witness_ref", "unconfigured_verdict", "receipt_status",
                                      "foreign_source", "pass_with_defect", "missing_receipt_verdict"])
def test_observation_witness_receipt_mutations_refuse(tmp_path, mutation):
    parent, receipt, witnesses, evidence, configured, reader, body = _receipt_case(tmp_path, "contention", "pass")
    finding = parent["findings"]["contention"]
    if mutation == "finding_status":
        finding["status"] = "fail"
    elif mutation == "witness_ref":
        witnesses["contention"]["ref"] = "parent-unit-evidence:" + "e" * 64 + "#contention"
    elif mutation == "unconfigured_verdict":
        configured = {}
    elif mutation == "receipt_status":
        body["status"] = "fail"
        finding["facts"]["receipt"]["artifact"] = _write(tmp_path, "x", body)
        finding["facts"]["receipt"]["digest"] = arm._hash(body)
    elif mutation == "foreign_source":
        configured = {"contention": {**configured["contention"], "adapter_id": "foreign"}}
    elif mutation == "pass_with_defect":
        body["scope_defects"] = ["d"]
        finding["facts"]["scope_defects"] = ["d"]
        finding["facts"]["receipt"]["artifact"] = _write(tmp_path, "y", body)
        finding["facts"]["receipt"]["digest"] = arm._hash(body)
    else:
        finding["facts"].pop("receipt")
    with pytest.raises(ProjectionError):
        final._witness_receipts(parent, receipt, witnesses, evidence, configured, reader)


def test_unconfigured_slot_may_only_be_unknown_without_a_receipt(tmp_path):
    parent = {"findings": {"residency": {"status": "unknown", "facts": {"backend": "gpu"}}}}
    final._witness_receipts(parent, {"digest": "d" * 64}, {"residency": {"status": "unknown", "ref": None}},
                            {}, {}, final._Reader(tmp_path))


def test_actual_producer_final_evidence_uses_current_pin_set_and_v1_bytes(actual):
    """Real research issuance: current 7-module pins accepted, no token key on a v1 trial."""
    root, events = actual
    body = _body(root, events[0]["payload"]["carrier"]["parent_final_trial"]["artifact"])
    pins = body["source_identity"]["selected_scientific_adapter"]["owning_source_pins"]["modules"]
    assert final._pins({"owning_source_pins": {"modules": pins}}) == (len(pins) == final.CURRENT_MODULE_COUNT)
    pair = _body(root, body["scientific_pair_reference"]["artifact"])
    assert all(final.TOKEN_WITNESS_KEY not in unit["final_evidence"] for unit in pair["ordered_units"])
