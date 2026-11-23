import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "rowflow"))
import rowflow as rf
from test_rowflow import Fixture


def test_measure_must_be_valid_and_new(tmp_path):
    root = tmp_path / "row"
    out = root / "out-smoke"
    out.mkdir(parents=True)
    path = out / "smoke_measure.json"
    path.write_text(json.dumps({"unit_s": 1, "units_measured": 1, "loads_s": 0}))
    start = {str(path): rf.smoke_measure_stamp(str(path))}
    assert rf.fresh_smoke_measure({"scratch_root": str(root)}, str(tmp_path / "dry"), start) is None
    path.write_text(json.dumps({"unit_s": "NaN", "units_measured": 1, "loads_s": 0}))
    assert rf.fresh_smoke_measure({"scratch_root": str(root)}, str(tmp_path / "dry"), start) is None
    time.sleep(0.01)  # filesystem timestamp granularity
    path.write_text(json.dumps({"unit_s": 1, "units_measured": 1, "loads_s": 0}))
    assert rf.fresh_smoke_measure({"scratch_root": str(root)}, str(tmp_path / "dry"), start) == str(path)


def test_zero_vram_owned_kfd_is_residency(monkeypatch):
    monkeypatch.setattr(rf, "harness_tree", lambda root, tracked: tracked)
    monkeypatch.setattr(rf, "gpu_occupancy", lambda: {"pids": {12: 0, 13: 123}})
    monkeypatch.setattr(rf, "pid_is_rows", lambda pid, rid, tracked: pid == 12)
    own = {}
    rf.sample_gpu_residency(1, {}, own, rid="row")
    assert own == {12: 0}


def test_smoke_without_fresh_measure_cannot_pass():
    fx = Fixture()
    try:
        rid = "measure-required"
        d = fx.job(rid, measure=False)
        rf.publish(fx.spec(rid, d), fx.flags)
        verdict, reason = rf.dryrun_run(fx.flags, rid, "0-3", True, smoke_s=60)
        assert verdict == "FAIL" and "SMOKE-NO-MEASURE" in reason
        assert not os.path.exists(rf.pass_path(fx.flags, rid))
    finally:
        fx.cleanup()
