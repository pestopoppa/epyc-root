"""Independent reader controls over a synthetic producer-written native fixture."""

import hashlib
import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/vidya"))
import claim_tuple as ct
from adapters import autokernel_aux_receipt as aux


@pytest.fixture
def fixture(tmp_path, monkeypatch):
    origin = Path(__file__).parent / "fixtures/nemo-native-MOCK_ONLY"
    target = tmp_path / "capture"
    shutil.copytree(origin, target)
    capture = json.loads((target / "capture.json").read_text())
    old_root = str(
        Path(capture["capture_contract"]["artifacts"]["model"]["path"]).parent
    )
    # Rebind only the synthetic external artifact authority into this temp tree.
    # Production has no MOCK_ONLY branch or authority override.
    for name in ("capture.json", "run.json", "final.json", "MOCK_ONLY_module_closure"):
        path = target / name
        path.write_text(path.read_text().replace(old_root, str(target)))
    capture = json.loads((target / "capture.json").read_text())
    run = json.loads((target / "run.json").read_text())
    contract = capture["capture_contract"]
    for name, item in contract["analysis_artifacts"].items():
        item["path"] = str(target / ("analysis-" + name))
    contract["artifacts"]["contract_module"] = contract["analysis_artifacts"][
        "nemo_native_join.py"
    ]
    item = contract["artifacts"]["module_closure"]
    item["sha256"] = hashlib.sha256(Path(item["path"]).read_bytes()).hexdigest()
    item["size"] = Path(item["path"]).stat().st_size
    run["source_time_artifacts"] = contract["artifacts"]
    run["capture_contract_sha256"] = aux._canonical_sha256(contract)
    for mark in run["marks"]:
        mark["capture_contract_sha256"] = run["capture_contract_sha256"]
    (target / "run.json").write_text(json.dumps(run))
    capture["files"]["run"]["sha256"] = hashlib.sha256(
        (target / "run.json").read_bytes()
    ).hexdigest()
    (target / "capture.json").write_text(json.dumps(capture))
    monkeypatch.setattr(
        aux,
        "_NEMO_NATIVE_AUTHORITY",
        {
            role: contract["artifacts"][role]["sha256"]
            for role in aux._NEMO_NATIVE_AUTHORITY
        },
    )
    monkeypatch.setattr(aux, "_NEMO_BOLT_MODEL", contract["artifacts"]["model"]["path"])
    receipt = json.loads((target / "final.json").read_text())
    receipt["source_receipt"]["sha256"] = hashlib.sha256(
        (target / "capture.json").read_bytes()
    ).hexdigest()
    receipt["native_join"]["raw_readset"] = {
        k: v["sha256"] for k, v in capture["files"].items()
    }
    receipt["native_join"]["source_run_hash"] = aux._canonical_sha256(run)
    for row in receipt["belief_measurements"]:
        row["extra"]["raw_readset"] = receipt["native_join"]["raw_readset"]
        row["extra"]["native_join_sha256"] = aux._canonical_sha256(
            receipt["native_join"]
        )

    receipt["source_receipt"]["locator"] = str(target / "capture.json")
    rehash(receipt)
    return target, receipt


def rehash(receipt):
    for row in receipt["belief_measurements"]:
        row["measurement_sha256"] = aux._canonical_sha256(
            {k: v for k, v in row.items() if k != "measurement_sha256"}
        )
    receipt["receipt_sha256"] = aux._canonical_sha256(
        {k: v for k, v in receipt.items() if k != "receipt_sha256"}
    )


def test_producer_fixture_reopens_raw_files_and_keeps_original_unratified_scope(
    fixture,
):
    root, receipt = fixture
    rows = aux.native_rows(receipt, receipt_locator=str(root / "final.json"))
    assert len(rows) == 1
    value = aux.project(rows[0])
    assert value.protocol_id == "" and value.reps == 1
    assert value.metric == "bolt_decode_step_busy_ms"
    assert ct.grade(value)[0] != "Ratified"


@pytest.mark.parametrize(
    "mutation",
    [
        "value",
        "claim",
        "metric_id",
        "category",
        "direction",
        "reps",
        "token",
        "context",
        "dispatch",
        "ownership",
        "readset",
        "agent",
        "device_claim",
    ],
)
def test_rehashed_finalized_tamper_still_refuses(fixture, mutation):
    root, receipt = fixture
    row = receipt["belief_measurements"][0]
    if mutation == "value":
        row["value"] *= 2
    elif mutation == "claim":
        row["claim"] = "Ratified optimization improvement"
    elif mutation == "metric_id":
        row["measurement_id"] = "another metric"
    elif mutation == "category":
        row["category"] = "CANDIDATE"
    elif mutation == "direction":
        row["metric_direction"] = "higher_better"
    elif mutation == "reps":
        row["reps"] = 31
    elif mutation == "token":
        receipt["native_join"]["requests"][-1]["tokens"][0]["token"] = 999
    elif mutation == "context":
        receipt["native_join"]["calls"][1]["begin"]["ctx"] = "0xDEAD"
    elif mutation == "dispatch":
        receipt["native_join"]["calls"][1]["dispatches"][0]["End_Timestamp"] = "999999"
    elif mutation == "ownership":
        receipt["native_join"]["calls"][1]["hip_rows"] = []
    elif mutation == "readset":
        row["extra"]["raw_readset"]["hip"] = "0" * 64
    elif mutation == "agent":
        receipt["native_join"]["calls"][1]["dispatches"][0]["Agent_Id"] = "999"
    else:
        receipt["device_claim"]["opened"]["device_id"] = "other"
    for item in receipt["belief_measurements"]:
        item["extra"]["native_join_sha256"] = aux._canonical_sha256(
            receipt["native_join"]
        )
    rehash(receipt)
    with pytest.raises(ct.ProjectionError):
        aux.native_rows(receipt, receipt_locator=str(root / "final.json"))


@pytest.mark.parametrize(
    "name", ["native.jsonl", "hip.csv", "kernels.csv", "agents.csv"]
)
def test_raw_file_drift_refuses_before_projection(fixture, name):
    root, receipt = fixture
    with (root / name).open("ab") as f:
        f.write(b"\n")
    with pytest.raises(ct.ProjectionError):
        aux.native_rows(receipt)


def test_direct_project_cannot_substitute_a_different_row(fixture):
    _root, receipt = fixture
    native = dict(aux.native_rows(receipt)[0])
    native["measurement"] = {**native["measurement"], "value": 42}
    with pytest.raises(ct.ProjectionError):
        aux.project(native)


def test_rehashing_raw_token_and_report_does_not_hide_broken_native_input_chain(
    fixture,
):
    root, receipt = fixture
    path = root / "native.jsonl"
    native = [json.loads(x) for x in path.read_text().splitlines()]
    native[2]["token"] = 999
    path.write_text("\n".join(json.dumps(x) for x in native) + "\n")
    source = json.loads((root / "capture.json").read_text())
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    source["files"]["native"]["sha256"] = digest
    (root / "capture.json").write_text(json.dumps(source))
    receipt["source_receipt"]["sha256"] = hashlib.sha256(
        (root / "capture.json").read_bytes()
    ).hexdigest()
    receipt["native_join"]["raw_readset"]["native"] = digest
    receipt["native_join"]["requests"][-1]["tokens"][0]["token"] = 999
    receipt["native_join"]["calls"][0]["emitted"][0]["token"] = 999
    row = receipt["belief_measurements"][0]
    row["extra"]["raw_readset"]["native"] = digest
    row["extra"]["native_join_sha256"] = aux._canonical_sha256(receipt["native_join"])
    rehash(receipt)
    with pytest.raises(ct.ProjectionError, match="plain token identity"):
        aux.native_rows(receipt)


@pytest.mark.parametrize(
    "mutation",
    [
        "missing_contract",
        "model",
        "build",
        "template",
        "argv",
        "payload",
        "claim_window",
        "claim_holder",
        "module_bytes",
        "analysis_bytes",
        "canary_relabel",
    ],
)
def test_independent_reader_refuses_rehashed_prospective_identity_changes(
    fixture, mutation
):
    root, receipt = fixture
    capture = json.loads((root / "capture.json").read_text())
    run = json.loads((root / "run.json").read_text())
    contract = capture["capture_contract"]
    if mutation == "missing_contract":
        capture.pop("capture_contract")
    elif mutation == "model":
        contract["artifacts"]["model"] = dict(contract["artifacts"]["producer"])
    elif mutation == "build":
        contract["artifacts"]["server"] = dict(contract["artifacts"]["producer"])
    elif mutation == "template":
        contract["artifacts"]["template"] = dict(contract["artifacts"]["producer"])
    elif mutation == "argv":
        run["argv"] = ["different-wrapper", *run["argv"]]
        contract["argv"] = run["argv"]
    elif mutation == "payload":
        run["marks"][-1]["payload"]["max_tokens"] = 32
    elif mutation == "claim_window":
        capture["device_claim_released"]["released_at"] = "2026-10-30T01:00:20Z"
    elif mutation == "claim_holder":
        for phase in ("device_claim_open", "device_claim_released"):
            capture[phase]["holder_start_ticks"] += 1
    elif mutation == "module_bytes":
        Path(contract["artifacts"]["claim_module"]["path"]).write_text("changed module")
    elif mutation == "analysis_bytes":
        Path(contract["analysis_artifacts"]["nemo_native_join.py"]["path"]).write_text(
            "changed analysis"
        )
    else:
        contract["purpose"] = "R7_GPU_CANARY"
    if "capture_contract" in capture:
        run["source_time_artifacts"] = contract["artifacts"]
        run["capture_contract_sha256"] = aux._canonical_sha256(contract)
        for mark in run["marks"]:
            mark["capture_contract_sha256"] = run["capture_contract_sha256"]
    (root / "run.json").write_text(json.dumps(run))
    capture["files"]["run"]["sha256"] = hashlib.sha256(
        (root / "run.json").read_bytes()
    ).hexdigest()
    (root / "capture.json").write_text(json.dumps(capture))
    receipt["source_receipt"]["sha256"] = hashlib.sha256(
        (root / "capture.json").read_bytes()
    ).hexdigest()
    receipt["device_claim"] = {
        "opened": capture["device_claim_open"],
        "released": capture["device_claim_released"],
    }
    receipt["native_join"]["raw_readset"] = {
        k: v["sha256"] for k, v in capture["files"].items()
    }
    receipt["native_join"]["source_run_hash"] = aux._canonical_sha256(run)
    for row in receipt["belief_measurements"]:
        row["extra"]["raw_readset"] = receipt["native_join"]["raw_readset"]
        row["extra"]["native_join_sha256"] = aux._canonical_sha256(
            receipt["native_join"]
        )
    rehash(receipt)
    with pytest.raises(ct.ProjectionError):
        aux.native_rows(receipt, receipt_locator=str(root / "final.json"))
