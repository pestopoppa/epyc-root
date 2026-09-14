"""Actual prospective research writer → existing governed ladder, no hardware."""
import copy
import importlib
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/vidya"))
import claim_tuple
from adapters import autokernel_governed_receipt as reader


def original_receipt(tmp_path, monkeypatch):
    research = os.environ.get("EPYC_RESEARCH_ROOT")
    if not research:
        pytest.skip("explicit matching research producer checkout required")
    sys.path.insert(0, str(Path(research) / "scripts/kernel_rnd"))
    producer = importlib.import_module("autokernel.loop.direct_gpu_control")
    fixtures = importlib.import_module("autokernel.loop.test_direct_gpu_control")
    fixtures.available(monkeypatch)
    def absent(**kwargs):
        raise producer.GpuControlRefused("synthetic original tool absent before calibration")
    monkeypatch.setattr(producer, "require_available", absent)
    from autokernel.loop.measurement_capture import ArtifactStore
    store = ArtifactStore(tmp_path / "store")
    try:
        with fixtures.claims(tmp_path) as claims:
            _, observations, reference = fixtures.invoke(store, claims)
        body = producer._read(store, producer.NAMESPACE, reference.to_dict())
        receipt = producer._read(store, "direct-gpu-control-beliefs", body["belief_receipt"])
        path = store.root / body["belief_receipt"]["locator"]
        return receipt, path, observations
    finally:
        store.close()


def test_actual_setup_writer_projects_no_protocol_or_scientific_failure(tmp_path, monkeypatch):
    receipt, path, observations = original_receipt(tmp_path, monkeypatch)
    rows = reader.native_rows(receipt, receipt_locator=str(path), attestation_present=True)
    assert len(rows) == 2 and all(not row.ran for row in observations.values())
    projected = [reader.project(row) for row in rows]
    assert all(row.protocol_id == "" and row.value == 0 and row.extra["native_verdict"] is None
               for row in projected)
    assert all(claim_tuple.grade(row)[:2] == ("Judged", "Located") for row in projected)
    # Existing corpus dispatcher discovers the new variant automatically.
    from adapters import autokernel_corpus
    assert autokernel_corpus._schema_map()[reader.DIRECT_GPU_SCHEMA] is reader


def test_pre_hook_absence_and_moved_native_source_refused(tmp_path, monkeypatch):
    receipt, path, _ = original_receipt(tmp_path, monkeypatch)
    old = copy.deepcopy(receipt)
    del old["belief_measurements"]
    assert reader.native_rows(old, receipt_locator=str(path)) == ()
    declaration = path.parent / receipt["native_basis"]["declaration"]["locator"]
    declaration.rename(declaration.with_suffix(".retained"))
    with pytest.raises(claim_tuple.ProjectionError, match="original source"):
        reader.native_rows(receipt, receipt_locator=str(path))


def test_receipt_self_hash_does_not_authorize_relabelled_setup_as_fail(tmp_path, monkeypatch):
    receipt, path, _ = original_receipt(tmp_path, monkeypatch)
    row = receipt["belief_measurements"][0]
    row["native_verdict"] = "FAIL"
    unsigned = {key: value for key, value in row.items() if key != "measurement_sha256"}
    row["measurement_sha256"] = reader._canonical_sha256(unsigned)
    receipt["receipt_sha256"] = reader._canonical_sha256({key: value for key, value in receipt.items()
                                                          if key != "receipt_sha256"})
    with pytest.raises(claim_tuple.ProjectionError, match="observation-only"):
        reader.native_rows(receipt, receipt_locator=str(path))
