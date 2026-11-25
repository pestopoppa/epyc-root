"""failclass: a connection drop with a crash marker in the row's server log is candidate_crash, not harness."""
import os
import sys

_T = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_T), "akloop"))
import failclass  # noqa: E402

DROP = "urllib.error.URLError: Remote end closed connection without response"
FAIL = {"id": "r1", "reason": "reason=job-rc-1"}


def _row(tmp_path, log_text):
    d = tmp_path / "out" / "logs"
    d.mkdir(parents=True)
    (d / "smoke-BOTH-server.log").write_text(log_text)
    return str(tmp_path)


def test_ggml_assert_is_candidate_crash(tmp_path):
    rd = _row(tmp_path, "load ok\n./common/sampling.cpp:164: GGML_ASSERT(logits != nullptr) failed\n")
    c = failclass.classify_fail(FAIL, DROP, rd)
    assert (c.side, c.klass, c.rule) == ("candidate", "candidate_crash", "server-log:GGML_ASSERT")
    assert "sampling.cpp:164" in c.evidence


def test_segfault_is_candidate_crash(tmp_path):
    rd = _row(tmp_path, "x\nSegmentation fault (core dumped)\n")
    c = failclass.classify_fail(FAIL, DROP, rd)
    assert (c.side, c.klass, c.rule) == ("candidate", "candidate_crash", "server-log:Segmentation fault")


def test_drop_without_marker_unchanged(tmp_path):
    rd = _row(tmp_path, "all fine\nslot released\n")
    c = failclass.classify_fail(FAIL, DROP, rd)
    assert (c.side, c.klass, c.rule) == ("harness", "job_script_error", "text:pipeline-env")


def test_no_row_dir_unchanged():
    c = failclass.classify_fail(FAIL, DROP)
    assert c.rule == "text:pipeline-env"


def test_row_dir_from_result_path():
    assert failclass.row_dir_from_result_path("/a/row/out/RESULT.json") == "/a/row"
    assert failclass.row_dir_from_result_path(None) is None
