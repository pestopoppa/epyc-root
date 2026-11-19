"""Synthetic producer -> existing adapter -> isolated planning context, no inference."""
import datetime
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/vidya"))
import claim_tuple
import ingest_sources
import loop_beliefs
from ledger import Ledger
from adapters import np_ctx_kvu


def synthetic_carrier(tmp_path):
    driver = os.environ.get("KVU126_RESEARCH_DRIVER")
    if not driver:
        pytest.skip("set KVU126_RESEARCH_DRIVER to the matching research producer checkout")
    sys.path.insert(0, driver)
    import kvu126_compare as producer
    import kvu126_finalize
    from test_kvu126_compare import ComparisonTest
    fixture = ComparisonTest()
    fixture.root = tmp_path
    fixture.plan = {"arms": {}}
    fixture.row("np8_48k", 8, 49152, 390000)
    fixture.row("np4_96k", 4, 98304, 391000)
    plan, records = fixture.prospective()
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(plan, sort_keys=True))
    plan_sha = hashlib.sha256(plan_path.read_bytes()).hexdigest()
    for name, entries in records["arms"].items():
        for item in entries:
            ref = item["runtime_receipt"]
            receipt = json.loads((tmp_path / ref["path"]).read_bytes())
            receipt["plan_sha256"] = plan_sha
            item["runtime_receipt"] = fixture.write_json(ref["path"], receipt)
            # Materialize the actual driver's original-output layout; the
            # producer finalizer must discover these files without inventing rows.
            cell = tmp_path / name / "cell"
            cell.mkdir(parents=True)
            shutil.copyfile(tmp_path / item["wave_file"]["path"], cell / "waves_capture.jsonl")
            occ_src = tmp_path / item["occupancy_file"]["path"]
            occ = json.loads(occ_src.read_bytes())
            shutil.copyfile(occ_src, cell / "wave-1-occupancy.json")
            shutil.copyfile(tmp_path / occ["native_source"], cell / occ["native_source"])
            shutil.copyfile(tmp_path / item["runtime_receipt"]["path"], cell / "wave-1-runtime.json")
    records_path = kvu126_finalize.write_index(tmp_path, tmp_path / "build.json")
    records = json.loads(records_path.read_bytes())
    sidecar = tmp_path / "belief_measurements.jsonl"
    producer.write_belief_measurements(sidecar, plan_path, records_path)
    return sidecar, records


def test_synthetic_original_capture_projects_and_reaches_planner(tmp_path):
    sidecar, _records = synthetic_carrier(tmp_path)
    ledger = Ledger(tmp_path / "ledger.jsonl")
    asof = datetime.datetime.now(datetime.timezone.utc).isoformat()
    report = ingest_sources.ingest(ledger, "np-ctx-kvu-measurement", [sidecar], as_of=asof)
    assert not report["refused"], str(report["refused"])
    assert report["rows_projected"] == 1
    frames = [record.frame for record in ledger.read_all()]
    evidence = next(f for f in frames if f["frame_type"].endswith("evidence_supports_claim/v1"))
    assert evidence["assertion"]["grade"] == {"Q": "Judged", "T": "Located"}
    assert evidence["assertion"]["protocol_id"] == ""
    class Sync:
        def status(self, *args, **kwargs):
            return {"fresh": True, "lag_entries": 0, "index_max_id": 0, "synced_max_id": 0, "last_sync": asof}
    cfg = tmp_path / "alarm.yaml"
    cfg.write_text("backend: file\nfile:\n  path: " + str(tmp_path / "alarms.jsonl") + "\n")
    context = loop_beliefs.prepare("rtg57.kvu126.synthetic", {"model_file": "fake-model", "backend": "cpu"},
                                   ledger=ledger.path, index_path=tmp_path / "index", as_of=asof,
                                   sync_module=Sync(), known_good=tmp_path / "known.json",
                                   alarm_state=tmp_path / "alarm.json", alarm_config=cfg,
                                   read_log=tmp_path / "reads.jsonl")
    assert context["status"] == "ready" and len(context["evidence"]["claim_ids"]) == 1
    other = loop_beliefs.prepare("rtg57.kvu126.other", {"model_file": "unrelated-model.gguf", "backend": "cpu"},
                                 ledger=ledger.path, index_path=tmp_path / "index", as_of=asof,
                                 sync_module=Sync(), known_good=tmp_path / "other-known.json",
                                 alarm_state=tmp_path / "other-alarm.json", alarm_config=cfg,
                                 read_log=tmp_path / "other-reads.jsonl")
    assert not other.get("evidence", {}).get("claim_ids", [])


def test_tampered_source_and_absent_original_refuse(tmp_path):
    sidecar, records = synthetic_carrier(tmp_path)
    item = records["arms"]["np8_48k"][0]
    (tmp_path / item["occupancy_file"]["path"]).write_text("{}")
    ledger = Ledger(tmp_path / "tamper-ledger.jsonl")
    report = ingest_sources.ingest(ledger, "np-ctx-kvu-measurement", [sidecar],
                                    as_of=datetime.datetime.now(datetime.timezone.utc).isoformat())
    assert report["refused"] and report["rows_projected"] == 0


def test_rehashed_forged_sample_still_refused_against_native_metric(tmp_path):
    sidecar, records = synthetic_carrier(tmp_path)
    item = records["arms"]["np8_48k"][0]
    occupancy_path = tmp_path / item["occupancy_file"]["path"]
    occ = json.loads(occupancy_path.read_bytes())
    occ["samples"][0]["unique_cells"] += 1
    raw_path = occupancy_path.parent / occ["native_source"]
    raw = json.loads(raw_path.read_bytes())
    raw["samples"] = occ["samples"]
    raw_path.write_text(json.dumps(raw))
    occ["native_source_sha256"] = hashlib.sha256(raw_path.read_bytes()).hexdigest()
    occupancy_path.write_text(json.dumps(occ))
    item["occupancy_file"]["sha256"] = hashlib.sha256(occupancy_path.read_bytes()).hexdigest()
    index_path = tmp_path / "kvu126-evidence-index.json"
    index_path.write_text(json.dumps(records, sort_keys=True))
    carrier = json.loads(sidecar.read_bytes())
    carrier["evidence_index_sha256"] = hashlib.sha256(index_path.read_bytes()).hexdigest()
    carrier["row_sha256"] = np_ctx_kvu.row_hash(carrier)
    sidecar.write_text(json.dumps(carrier) + "\n")
    report = ingest_sources.ingest(Ledger(tmp_path / "forged-ledger.jsonl"), "np-ctx-kvu-measurement", [sidecar],
                                    as_of=datetime.datetime.now(datetime.timezone.utc).isoformat())
    assert report["refused"] and report["rows_projected"] == 0
    assert "native metric response" in report["refused"][0]["reason"]


def test_rewritten_plan_cannot_retrofit_original_run_binding(tmp_path):
    sidecar, _records = synthetic_carrier(tmp_path)
    plan_path = tmp_path / "plan.json"
    plan = json.loads(plan_path.read_bytes())
    plan["noise_rule"] = "post-run rewrite"
    plan_path.write_text(json.dumps(plan, sort_keys=True))
    carrier = json.loads(sidecar.read_bytes())
    carrier["plan_sha256"] = hashlib.sha256(plan_path.read_bytes()).hexdigest()
    carrier["row_sha256"] = np_ctx_kvu.row_hash(carrier)
    sidecar.write_text(json.dumps(carrier) + "\n")
    report = ingest_sources.ingest(Ledger(tmp_path / "rewritten-plan-ledger.jsonl"), "np-ctx-kvu-measurement", [sidecar],
                                    as_of=datetime.datetime.now(datetime.timezone.utc).isoformat())
    assert report["refused"] and report["rows_projected"] == 0
    assert "runtime receipt" in report["refused"][0]["reason"]
