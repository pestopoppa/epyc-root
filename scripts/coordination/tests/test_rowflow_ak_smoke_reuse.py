import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "rowflow"))
import publish_row as pr


def test_three_consecutive_failures_park_and_unpark(tmp_path, monkeypatch, capsys):
    flags, rid = str(tmp_path), "row-test"
    monkeypatch.setattr(pr.rf, "dryrun_run", lambda *a, **k: ("FAIL", "broken"))
    for _ in range(3):
        assert pr.run_smoke(flags, rid, "0-3", 60)[0] == "FAIL"
    assert "PARKED-3STRIKE" in capsys.readouterr().out
    with pytest.raises(pr.rf.Refused, match="PARKED-3STRIKE"):
        pr.publish_smoked({"id": rid}, flags, "src")
    pr.rf.unpark(flags, rid, by="owner", note="fixed")
    assert pr.smoke_strikes(flags, rid) == {}
    monkeypatch.setattr(pr.rf, "dryrun_run", lambda *a, **k: ("PASS", "ok"))
    assert pr.run_smoke(flags, rid, "0-3", 60)[0] == "PASS"
    assert pr.smoke_strikes(flags, rid)["count"] == 0


def test_wait_does_not_count_as_failure(tmp_path, monkeypatch):
    monkeypatch.setattr(pr.rf, "dryrun_run", lambda *a, **k: ("WAIT", "busy"))
    assert pr.run_smoke(str(tmp_path), "row-test", "0-3", 60)[0] == "WAIT"
    assert pr.smoke_strikes(str(tmp_path), "row-test") == {}


def test_pass_reused_only_for_same_spec_and_code(tmp_path, monkeypatch):
    flags, rid = str(tmp_path), "row-test"
    launcher = tmp_path / "launch.sh"
    launcher.write_text("first")
    spec = {"id": rid, "launcher": str(launcher), "lane": "cpu"}
    row = {"id": rid, "launcher": {"path": str(launcher)}}
    monkeypatch.setattr(pr.rf, "job_sha", lambda path: pr.rf.sha256(path))
    def publish(s, f, source=None):
        pr.rf.atomic_json(pr.rf.ready_path(f, rid), row)
        return dict(row)
    monkeypatch.setattr(pr.rf, "publish", publish)
    monkeypatch.setattr(pr, "supersede_prior_attempts", lambda *a: None)
    monkeypatch.setattr(pr.rf, "supersede", lambda *a: None)
    monkeypatch.setattr(pr, "file_if_complete", lambda *a: False)
    passed = {"smoke_identity": pr.smoke_identity(spec, row), "smoke_measure": "/measured"}
    pr.rf.atomic_json(pr.rf.pass_path(flags, rid), passed)
    assert pr.publish_smoked(spec, flags, "src", queue_cpu=True)["id"] == rid
    assert not Path(pr.rf.smoke_queued_path(flags, rid)).exists()
    launcher.write_text("changed")
    assert pr.publish_smoked(spec, flags, "src", queue_cpu=True) is None
    assert Path(pr.rf.smoke_queued_path(flags, rid)).exists()


def test_queue_order_prefers_lower_rank(tmp_path):
    flags = str(tmp_path)
    paths = []
    for rid, rank in (("low", 50), ("high", 2)):
        q = pr.queued_path(flags, rid)
        pr.rf.atomic_json(q, {"spec": {"priority_rank": rank}, "queued_at": "same"})
        paths.append(q)
    assert min(paths, key=lambda q: pr.queue_order_key(flags, q)) == paths[1]


def test_same_recorded_failure_is_not_counted_twice(tmp_path):
    flags, rid = str(tmp_path), "row-test"
    fail = Path(pr.rf.dry_dir(flags, rid)) / "FAIL-1.json"
    pr.rf.atomic_json(str(fail), {"reason": "broken"})
    pr.record_smoke_outcome(flags, rid, "FAIL", "broken")
    pr.record_smoke_outcome(flags, rid, "FAIL", "broken")
    assert pr.smoke_strikes(flags, rid)["count"] == 1
    pr.rf.atomic_json(str(fail.with_name("FAIL-2.json")), {"reason": "broken"})
    pr.record_smoke_outcome(flags, rid, "FAIL", "broken")
    assert pr.smoke_strikes(flags, rid)["count"] == 2


def test_old_pass_without_measure_is_not_reused(tmp_path, monkeypatch):
    flags, rid = str(tmp_path), "row-old"
    launcher = tmp_path / "launch.sh"
    launcher.write_text("code")
    spec = {"id": rid, "launcher": str(launcher), "lane": "cpu"}
    row = {"id": rid, "launcher": {"path": str(launcher)}}
    monkeypatch.setattr(pr.rf, "job_sha", lambda p: pr.rf.sha256(p))
    def publish(s, f, source=None):
        pr.rf.atomic_json(pr.rf.ready_path(f, rid), row)
        return dict(row)
    monkeypatch.setattr(pr.rf, "publish", publish)
    monkeypatch.setattr(pr, "supersede_prior_attempts", lambda *a: None)
    pr.rf.atomic_json(pr.rf.pass_path(flags, rid), {"smoke_identity": pr.smoke_identity(spec, row)})
    assert pr.publish_smoked(spec, flags, "src", queue_cpu=True) is None
    assert Path(pr.rf.smoke_queued_path(flags, rid)).exists()


def test_gpu_reuse_needs_residency_proof(tmp_path, monkeypatch):
    flags, rid = str(tmp_path), "row-gpu"
    launcher = tmp_path / "launch.sh"
    launcher.write_text("code")
    spec = {"id": rid, "launcher": str(launcher), "lane": "gpu"}
    row = {"id": rid, "launcher": {"path": str(launcher)}}
    monkeypatch.setattr(pr.rf, "job_sha", lambda p: pr.rf.sha256(p))
    def publish(s, f, source=None):
        pr.rf.atomic_json(pr.rf.ready_path(f, rid), row)
        return dict(row)
    monkeypatch.setattr(pr.rf, "publish", publish)
    monkeypatch.setattr(pr, "supersede_prior_attempts", lambda *a: None)
    monkeypatch.setattr(pr, "gpu_busy", lambda flags: True)
    pr.rf.atomic_json(pr.rf.pass_path(flags, rid), {"smoke_identity": pr.smoke_identity(spec, row),
                                                  "smoke_measure": "/measured", "residency_evidence": {"kfd_pids": []}})
    assert pr.publish_smoked(spec, flags, "src") is None
    assert Path(pr.queued_path(flags, rid)).exists()


def test_old_pass_hidden_while_new_manifest_is_published(tmp_path, monkeypatch):
    flags, rid = str(tmp_path), "row-race"
    launcher = tmp_path / "launch.sh"
    launcher.write_text("code")
    spec = {"id": rid, "launcher": str(launcher), "lane": "cpu"}
    row = {"id": rid, "launcher": {"path": str(launcher)}}
    monkeypatch.setattr(pr.rf, "job_sha", lambda p: pr.rf.sha256(p))
    pr.rf.atomic_json(pr.rf.pass_path(flags, rid), {"smoke_identity": {"spec_sha256": "old"}, "smoke_measure": "old"})
    def publish(s, f, source=None):
        assert not Path(pr.rf.pass_path(f, rid)).exists()
        pr.rf.atomic_json(pr.rf.ready_path(f, rid), row)
        return dict(row)
    monkeypatch.setattr(pr.rf, "publish", publish)
    monkeypatch.setattr(pr, "supersede_prior_attempts", lambda *a: None)
    assert pr.publish_smoked(spec, flags, "src", queue_cpu=True) is None
    assert not Path(pr.rf.pass_path(flags, rid)).exists()
    assert list((Path(pr.rf.dry_dir(flags, rid)) / "superseded").glob("*/PASS.json"))


def test_publish_refusal_restores_prior_pass(tmp_path, monkeypatch):
    flags, rid = str(tmp_path), "row-race"
    old = {"passed_at": "before"}
    pr.rf.atomic_json(pr.rf.pass_path(flags, rid), old)
    def refuse(*a, **kw):
        assert not Path(pr.rf.pass_path(flags, rid)).exists()
        raise pr.rf.Refused("bad spec")
    monkeypatch.setattr(pr.rf, "publish", refuse)
    with pytest.raises(pr.rf.Refused, match="bad spec"):
        pr.publish_smoked({"id": rid}, flags, "src")
    assert pr.rf.load_json(pr.rf.pass_path(flags, rid)) == old


def test_publish_failure_after_ready_write_withdraws_new_manifest(tmp_path, monkeypatch):
    flags, rid = str(tmp_path), "row-race"
    old = {"passed_at": "before"}
    pr.rf.atomic_json(pr.rf.pass_path(flags, rid), old)
    pr.rf.atomic_json(pr.rf.ready_path(flags, rid), {"id": rid, "revision": "old"})
    def refuse(s, f, source=None):
        pr.rf.atomic_json(pr.rf.ready_path(f, rid), {"id": rid, "revision": "new"})
        raise pr.rf.Refused("late failure")
    monkeypatch.setattr(pr.rf, "publish", refuse)
    with pytest.raises(pr.rf.Refused, match="late failure"):
        pr.publish_smoked({"id": rid}, flags, "src")
    assert not Path(pr.rf.ready_path(flags, rid)).exists()
    assert pr.rf.load_json(pr.rf.pass_path(flags, rid)) == old
