"""paired_loadgen / run_paired_serving_ab write side -> strict legacy-serving reader -> grade, no inference."""
import hashlib
import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/vidya"))

from adapters import autokernel_legacy_serving as reader
from claim_tuple import grade


@pytest.fixture
def loop(monkeypatch):
    research = os.environ.get("EPYC_RESEARCH_ROOT")
    if not research:
        pytest.skip("EPYC_RESEARCH_ROOT must select the paired_loadgen producer")
    monkeypatch.syspath_prepend(str(Path(research) / "scripts/kernel_rnd"))
    from autokernel.loop import paired_loadgen, run_paired_serving_ab
    return paired_loadgen, run_paired_serving_ab


def _natives(path):
    raw = path.read_bytes()
    return reader.native_rows(json.loads(raw), receipt_locator=f"autokernel:{path}",
                              receipt_sha256=hashlib.sha256(raw).hexdigest())


def _v2(path):
    raw = path.read_bytes()
    return reader.native_rows_v2(json.loads(raw), receipt_locator=f"autokernel:{path}",
                                 receipt_sha256=hashlib.sha256(raw).hexdigest())


def test_fixture_record_exports_reads_back_and_grades(loop, tmp_path):
    pl, _ = loop
    a = pl.Arm("A", lambda s: (100.0, None), np=2)
    b = pl.Arm("B", lambda s: (110.0, None), np=2)
    rec = pl.paired_record(a, b, pairs=3, base_seed=1, floor_pct=1.0, floor_unit="session",
                           belief={"model": "/m/x.gguf", "anchor_build": "/b/a", "candidate_build": "/b/b"})
    path = pl.export_belief(tmp_path, rec, campaign_id="c", epoch="e", recorded_at="2026-10-22T00:00:00Z")
    tuples = [reader.project(n) for n in _natives(path)]
    assert [t.value for t in tuples] == [100.0, 110.0]
    assert all(grade(t)[:2] == ("Judged", "Located") for t in tuples)
    (v2,) = _v2(path)
    assert "unit: session" in v2["claim"]["claim"] and "PIPELINE-ONLY" not in v2["claim"]["claim"]
    assert v2["applicability"]["model_file"] == "/m/x.gguf"


def test_record_without_capture_is_refused(loop, tmp_path):
    pl, _ = loop
    a = pl.Arm("A", lambda s: (100.0, None)); b = pl.Arm("B", lambda s: (101.0, None))
    rec = pl.paired_record(a, b, pairs=2, base_seed=1, floor_pct=1.0, floor_unit="session")
    with pytest.raises(ValueError, match="no belief_capture"):
        pl.export_belief(tmp_path, rec, campaign_id="c", epoch="e", recorded_at="2026-10-22T00:00:00Z")


def test_tampered_native_is_refused_by_reader(loop, tmp_path):
    pl, _ = loop
    a = pl.Arm("A", lambda s: (100.0, None), np=1); b = pl.Arm("B", lambda s: (101.0, None), np=1)
    rec = pl.paired_record(a, b, pairs=2, base_seed=1, floor_pct=1.0, floor_unit="session",
                           belief={"model": "/m/x.gguf", "anchor_build": "/b/a", "candidate_build": "/b/b"})
    path = pl.export_belief(tmp_path, rec, campaign_id="c", epoch="e", recorded_at="2026-10-22T00:00:00Z")
    src = path.parent / "sources" / path.name
    body = json.loads(src.read_text()); body["comparison"]["anchor_tok_s"] = 999.0
    src.write_text(json.dumps(body))
    with pytest.raises(Exception):
        _natives(path)


def test_toy_driver_record_grades_marked_pipeline_only(loop, tmp_path):
    _, drv = loop
    assert drv.main(["--toy", "--toy-rates", "100,100", "--out-dir", str(tmp_path), "--pairs", "3",
                     "--aa-pairs", "3", "--np", "2"]) == 0
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    path = Path(manifest["belief_receipt"])
    tuples = [reader.project(n) for n in _natives(path)]
    assert len(tuples) == 2 and all(grade(t)[:2] == ("Judged", "Located") for t in tuples)
    (v2,) = _v2(path)
    assert "PIPELINE-ONLY shakedown (toy endpoint)" in v2["claim"]["claim"]
    assert v2["applicability"]["np"] == 2
