import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "rowflow"))
import rowflow as rf


def test_flag_only_identical_filed_result_and_identity(tmp_path, monkeypatch):
    flags, rid = str(tmp_path), "row-test"
    launcher = tmp_path / "launch.sh"
    launcher.write_text("code")
    result = tmp_path / "RESULT.json"
    result.write_bytes(b'{"verdict":"DONE"}')
    ident = {"spec_sha256": "spec", "job_sha256": "code"}
    row = {"smoke_identity": ident, "launcher": {"path": str(launcher)}}
    passed = {"smoke_identity": ident}
    monkeypatch.setattr(rf, "job_sha", lambda p: "code")
    done = tmp_path / "filing-done"
    done.mkdir()
    (done / (rid + ".FILED")).write_text("filed")
    receipt = {"smoke_identity": ident, "result_path": str(result),
               "verdict": {"native_result_sha256": rf.sha256(str(result))}}
    rf.atomic_json(str(done / (rid + ".verdict.json")), receipt)
    assert "SAME-RESULT" in rf.same_filed_result_warning(flags, rid, row, passed)
    result.write_bytes(b'{"verdict":"NEW"}')
    assert rf.same_filed_result_warning(flags, rid, row, passed) is None
    result.write_bytes(b'{"verdict":"DONE"}')
    monkeypatch.setattr(rf, "job_sha", lambda p: "changed")
    assert rf.same_filed_result_warning(flags, rid, row, passed) is None
    monkeypatch.setattr(rf, "job_sha", lambda p: "code")
    assert rf.same_filed_result_warning(flags, rid, row, {"smoke_identity": {"spec_sha256": "other"}}) is None


def test_publish_warning_is_logged_for_matching_filed_result(tmp_path, monkeypatch, capsys):
    import publish_row as pr
    flags, rid = str(tmp_path), "row-publish"
    launcher = tmp_path / "launch.sh"
    launcher.write_text("code")
    result = tmp_path / "RESULT.json"
    result.write_text('{"verdict":"DONE"}')
    spec = {"id": rid, "launcher": str(launcher), "result_path": str(result)}
    monkeypatch.setattr(rf, "job_sha", lambda p: "code")
    ident = pr.smoke_identity(spec, {"launcher": {"path": str(launcher)}})
    done = tmp_path / "filing-done"
    done.mkdir()
    (done / (rid + ".FILED")).write_text("filed")
    rf.atomic_json(str(done / (rid + ".verdict.json")), {"smoke_identity": ident, "result_path": str(result),
                                                        "verdict": {"native_result_sha256": rf.sha256(str(result))}})
    pr.warn_filed_replay(spec, flags)
    assert "SAME-RESULT" in capsys.readouterr().out
    assert "SAME-RESULT" in (tmp_path / "ws58-calendar-keeper.log").read_text()
