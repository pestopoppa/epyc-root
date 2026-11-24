import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "rowflow"))
import rowflow as rf


def test_gpu_publish_requires_basis_before_launcher(tmp_path):
    spec = {"id": "gpu-row", "owner": "owner", "launcher": "/missing", "lane": "gpu",
            "result_path": "/tmp/result", "decision_rule": "score > 0", "estimate_s": 600,
            "handoff_task": "h.md:T"}
    with pytest.raises(rf.Refused, match="ESTIMATE-BASIS"):
        rf.publish(spec, str(tmp_path))


def test_rebook_uses_larger_measured_estimate_and_respects_cap(tmp_path):
    measure = tmp_path / "smoke_measure.json"
    measure.write_text(json.dumps({"unit_s": 20, "units_measured": 1, "loads_s": 10}))
    row = {"lane": "gpu", "estimate_s": 600, "min_window_s": 300, "window_s": 1020,
           "estimate_basis": {"units": 100}, "resumable": False}
    got = rf.rebook_gpu_smoke(dict(row), str(measure))
    assert got["estimate_s"] == 2513
    assert got["window_s"] >= got["estimate_s"]
    assert got["book_s"] >= 2513
    assert got["estimate_basis"]["smoke_measure"] == str(measure)
    with pytest.raises(rf.Refused, match="SMOKE-ESTIMATE"):
        rf.rebook_gpu_smoke(dict(row, max_window_s=1020), str(measure))


def test_measure_path_honors_provisional_rebook_path(tmp_path):
    path = tmp_path / "custom" / "smoke_measure.json"
    row = {"scratch_root": str(tmp_path), "estimate_basis": {"rebook_from": "custom/smoke_measure.json"}}
    before = {p: rf.smoke_measure_stamp(p) for p in rf.smoke_measure_paths(row, str(tmp_path / "dry"))}
    path.parent.mkdir()
    path.write_text('{"unit_s":1,"units_measured":1,"loads_s":0}')
    assert rf.fresh_smoke_measure(row, str(tmp_path / "dry"), before) == str(path)


def test_provisional_basis_is_accepted_before_smoke(tmp_path):
    spec = {"id": "gpu-row", "owner": "owner", "launcher": "/missing", "lane": "gpu",
            "result_path": "/tmp/result", "decision_rule": "score > 0", "estimate_s": 600,
            "scratch_root": str(tmp_path), "handoff_task": "h.md:T",
            "estimate_basis": {"provisional": True, "reason": "first smoke", "units": 10,
                               "rebook_from": "out-smoke/smoke_measure.json"}}
    with pytest.raises(rf.Refused, match="launcher .* missing"):
        rf.publish(spec, str(tmp_path))


def test_gpu_smoke_rebooks_from_fresh_measure_without_device(monkeypatch):
    from test_rowflow import Fixture
    fx = Fixture()
    try:
        rid = "gpu-rebook-test"
        d = Path(fx.job(rid))
        launcher = d / "launch.sh"
        launcher.write_text(launcher.read_text().replace("--class cpu", "--class gpu --gpu-quiet exclusive --claim-cpus 184-191"))
        spec = fx.spec(rid, str(d), lane="gpu", regions="mi210_0,184-191",
                       estimate_basis={"provisional": True, "reason": "first smoke", "units": 1000,
                                       "rebook_from": "out-smoke/smoke_measure.json"})
        row = rf.publish(spec, fx.flags)
        class Done:
            pid = 424242
            def poll(self): return 0
            def wait(self, timeout=None): return 0
        def launch(argv, **kw):
            dd = Path(kw["env"]["FILLER_DRYRUN_DIR"])
            (dd / "smoke_measure.json").write_text('{"unit_s":1,"units_measured":1,"loads_s":0}')
            Path(row["result_path"]).write_text('{"score": 1}\n')
            (dd / "ended").write_text("rc=0 time=x reason=exited\n")
            return Done()
        monkeypatch.setattr(rf.subprocess, "Popen", launch)
        monkeypatch.setattr(rf, "gpu_sample_window", lambda root, tracked, own, **kw: own.update({12345: 0}))
        monkeypatch.setattr(rf, "row_orphans", lambda rid: [])
        monkeypatch.setattr(rf, "reap_pids", lambda tracked: ([], []))
        monkeypatch.setattr(rf.time, "sleep", lambda _: None)
        verdict, message = rf.dryrun_run(fx.flags, rid, "mi210_0,184-191", True, smoke_s=60)
        assert verdict == "PASS", message
        row = rf.load_json(rf.ready_path(fx.flags, rid))
        assert row["estimate_s"] == 1250 and row["book_s"] >= 1250
        receipt = rf.load_json(rf.pass_path(fx.flags, rid))
        assert receipt["residency_evidence"]["kfd_pids"] == [12345]
    finally:
        fx.cleanup()


def test_gpu_pass_reuse_restores_measured_booking(tmp_path, monkeypatch):
    import publish_row as pr
    flags, rid = str(tmp_path), "gpu-reuse"
    launcher = tmp_path / "launch.sh"
    launcher.write_text("code")
    measure = tmp_path / "smoke_measure.json"
    measure.write_text('{"unit_s":20,"units_measured":1,"loads_s":10}')
    spec = {"id": rid, "lane": "gpu", "launcher": str(launcher),
            "estimate_basis": {"provisional": True, "reason": "first smoke", "units": 100,
                               "rebook_from": str(measure)}}
    row = {"id": rid, "lane": "gpu", "launcher": {"path": str(launcher)}, "estimate_s": 600,
           "window_s": 1020, "min_window_s": 300, "resumable": False, "estimate_basis": spec["estimate_basis"]}
    monkeypatch.setattr(rf, "job_sha", lambda p: rf.sha256(p))
    def publish(s, f, source=None):
        rf.atomic_json(rf.ready_path(f, rid), row)
        return dict(row)
    monkeypatch.setattr(rf, "publish", publish)
    monkeypatch.setattr(pr, "supersede_prior_attempts", lambda *a: None)
    monkeypatch.setattr(rf, "supersede", lambda *a: None)
    monkeypatch.setattr(pr, "file_if_complete", lambda *a: False)
    rf.atomic_json(rf.pass_path(flags, rid), {"smoke_identity": pr.smoke_identity(spec, row),
                                             "smoke_measure": str(measure), "smoke_measure_sha256": rf.sha256(str(measure)),
                                             "residency_evidence": {"kfd_pids": [1]}})
    reused = pr.publish_smoked(spec, flags, "src")
    assert reused["estimate_s"] == 2513 and reused["book_s"] >= 2513
    assert rf.load_json(rf.ready_path(flags, rid))["estimate_s"] == 2513


def test_provisional_gpu_lint_remains_stable_after_smoke(tmp_path):
    import ak_row_harness as harness
    measure = tmp_path / "out-smoke" / "smoke_measure.json"
    spec = {"lane": "gpu", "estimate_s": 600, "scratch_root": str(tmp_path),
            "estimate_basis": {"provisional": True, "reason": "first smoke", "units": 1,
                               "rebook_from": str(measure)}}
    before = harness.check_spec_estimate(spec)
    measure.parent.mkdir()
    measure.write_text('{"unit_s":1,"units_measured":1,"loads_s":0}')
    assert harness.check_spec_estimate(spec) == before


def test_malformed_measured_basis_is_refused_cleanly(tmp_path):
    import ak_row_harness as harness
    measure = tmp_path / "measure.json"
    measure.write_text('[]')
    with pytest.raises(ValueError, match="JSON object"):
        harness.check_spec_estimate({"estimate_s": 600, "estimate_basis": {"smoke_measure": str(measure), "units": 1}})


def test_fresh_smoke_measure_is_warn_only_until_ak_confirms():
    # warn-only by agreement with AutoKernel (2026-11-23) until every queued AK row writes smoke_measure.json
    assert rf.SMOKE_MEASURE_ENFORCE is False
