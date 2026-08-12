"""SC30: fault rehearsals remain run-keyed dependency evidence, never measurements."""

import copy
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402
from adapters import autokernel_fault_rehearsal as fault  # noqa: E402


def process_identity(pid: int) -> dict:
    argv = ["/usr/bin/python3", "-m", "autokernel.fault_rehearsal", "_fixture", "/tmp/cfg"]
    return {
        "pid": pid,
        "pgid": pid,
        "start_ticks": pid * 10,
        "boot_id": "fixture-boot",
        "argv": argv,
        "argv_sha256": fault._canonical_sha256(argv),
    }


def receipt(*, failed_leg: int | None = None) -> dict:
    campaign_id = "ak-fault-rehearsal-prospective-fixture"
    source = {"root": "/source", "branch": "candidate", "commit": "a" * 40}
    producer = {
        "path": "/source/scripts/kernel_rnd/autokernel/fault_rehearsal.py",
        "sha256": "b" * 64,
    }
    legs = [
        {
            "name": fault.EXPECTED_LEGS[0], "status": "PASS",
            "crash_process": process_identity(101),
            "restart_process": process_identity(102),
        },
        {
            "name": fault.EXPECTED_LEGS[1], "status": "PASS",
            "teardown": {"identity": process_identity(103)},
        },
        {"name": fault.EXPECTED_LEGS[2], "status": "PASS"},
    ]
    if failed_leg is not None:
        legs[failed_leg]["status"] = "FAIL"
    run_status = "PASS" if failed_leg is None else "FAIL"
    value = {
        "schema": fault.SOURCE_SCHEMA,
        "capture_mode": fault.CAPTURE_MODE,
        "campaign_id": campaign_id,
        "status": run_status,
        "environment": {
            "source_tree": source,
            "producer_path": producer["path"],
            "producer_sha256": producer["sha256"],
        },
        "authority": fault.AUTHORITY_BOUNDARY,
        "live_claim_root_touched": False,
        "legs": legs,
    }
    run_identity = {"receipt_schema": fault.SOURCE_SCHEMA, "campaign_id": campaign_id}
    support_key = "akfault_run_" + fault._canonical_sha256(run_identity)[:24]
    processes = [
        [
            {"role": "crash_process", "identity": legs[0]["crash_process"]},
            {"role": "restart_process", "identity": legs[0]["restart_process"]},
        ],
        [{"role": "claim_holder_process", "identity": legs[1]["teardown"]["identity"]}],
        [],
    ]
    rows = []
    for index, leg in enumerate(legs):
        row = {
            "schema": fault.EVIDENCE_SCHEMA,
            "evidence_id": "akfault_" + fault._canonical_sha256(
                [run_identity, leg["name"]]
            )[:24],
            "classification": fault.CLASSIFICATION,
            "support_scope": fault.SUPPORT_SCOPE,
            "support_key": support_key,
            "run_identity": run_identity,
            "run_status": run_status,
            "leg_name": leg["name"],
            "leg_status": leg["status"],
            "source_identity": source,
            "producer_identity": producer,
            "process_identities": processes[index],
            "performance_measurement": False,
            "corroborating_witness": False,
            "belief_measurement_emitted": False,
        }
        row["evidence_sha256"] = fault._canonical_sha256(row)
        rows.append(row)
    value["dependency_evidence"] = rows
    value["receipt_sha256"] = fault._canonical_sha256(value)
    return value


def test_valid_rows_retain_leg_identities_but_share_one_run_support_key():
    native = receipt()
    records = fault.classify_receipt(
        native, receipt_locator="rehearsals/run/receipt.json",
        receipt_sha256=native["receipt_sha256"],
    )
    assert len(records) == 3
    assert len({record.evidence_id for record in records}) == 3
    assert len({record.support_key for record in records}) == 1
    assert [len(record.process_identities) for record in records] == [2, 1, 0]
    assert {record.run_status for record in records} == {"PASS"}
    assert {record.support_scope for record in records} == {"rehearsal_run"}
    assert {record.receipt_sha256 for record in records} == {native["receipt_sha256"]}


def test_classification_never_grants_measurement_or_corroboration_authority():
    records = fault.classify_receipt(receipt())
    assert all(record.classification == "dependency_evidence_only" for record in records)
    assert all(record.performance_measurement is False for record in records)
    assert all(record.corroborating_witness is False for record in records)
    assert all(record.belief_measurement_emitted is False for record in records)
    assert fault.project not in ct.registered().values()
    with pytest.raises(ct.ProjectionError, match="dependency evidence only"):
        fault.project({"receipt": receipt()})


def test_one_failed_leg_marks_every_row_as_one_failed_run_not_two_supports():
    records = fault.classify_receipt(receipt(failed_leg=2))
    assert [record.leg_status for record in records] == ["PASS", "PASS", "FAIL"]
    assert {record.run_status for record in records} == {"FAIL"}
    assert len({record.support_key for record in records}) == 1


def test_receipt_without_producer_hook_is_not_backfilled():
    old = receipt()
    old.pop("dependency_evidence")
    old.pop("receipt_sha256")
    assert fault.classify_receipt(old) == ()


@pytest.mark.parametrize(
    "mutate, resign_outer, match",
    [
        (lambda value: value["dependency_evidence"][1].update(
            support_key="akfault_per_leg_forbidden"), True, "digest does not bind"),
        (lambda value: value["dependency_evidence"][0]["process_identities"][0][
            "identity"].update(pid=999), True, "digest does not bind"),
        (lambda value: value["environment"]["source_tree"].update(commit="c" * 40),
         False, "logical rehearsal receipt"),
        (lambda value: value["authority"].update(release=True), False, "all-false boundary"),
    ],
)
def test_mutated_dependency_identity_or_authority_fails_closed(mutate, resign_outer, match):
    value = copy.deepcopy(receipt())
    mutate(value)
    if resign_outer:
        value.pop("receipt_sha256")
        value["receipt_sha256"] = fault._canonical_sha256(value)
    with pytest.raises(ct.ProjectionError, match=match):
        fault.classify_receipt(value)


def test_external_receipt_digest_must_match_the_self_bound_receipt():
    with pytest.raises(ct.ProjectionError, match="external receipt digest"):
        fault.classify_receipt(receipt(), receipt_sha256="f" * 64)
