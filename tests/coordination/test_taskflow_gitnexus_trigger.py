"""dispatch.gitnexus_trigger: once-per-batch, tolerant, skipped on dry-run/test."""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/coordination"))
from taskflow import dispatch  # noqa: E402


def _fake(tmp_path, body):
    f = tmp_path / "fake_trigger.py"
    f.write_text(body)
    return f


def test_calls_trigger_with_batch_id(tmp_path, monkeypatch):
    monkeypatch.setattr(dispatch, "lane_root", lambda: tmp_path / "lanes")
    fake = _fake(tmp_path, "import sys,pathlib;pathlib.Path(sys.argv[0]+'.out').write_text(' '.join(sys.argv[1:]))\n")
    out = dispatch.gitnexus_trigger("B1", True, script=fake)
    assert out.startswith("rc=0")
    assert (tmp_path / "fake_trigger.py.out").read_text() == "trigger --batch-id B1"
    assert "gitnexus-trigger batch=B1" in (tmp_path / "lanes/sweep.log").read_text()


def test_skipped_on_dry_run_and_test(tmp_path, monkeypatch):
    monkeypatch.setattr(dispatch, "lane_root", lambda: tmp_path / "lanes")
    fake = _fake(tmp_path, "raise SystemExit(9)\n")
    assert dispatch.gitnexus_trigger("B", False, script=fake) == "skipped:dry-run"
    assert dispatch.gitnexus_trigger("B", True) == "skipped:test"   # real script never run under pytest


def test_failure_never_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(dispatch, "lane_root", lambda: tmp_path / "lanes")
    assert dispatch.gitnexus_trigger("B", True, script=_fake(tmp_path, "raise SystemExit(3)\n")).startswith("rc=3")

    def boom(*a, **k):
        raise subprocess.TimeoutExpired("x", 1)
    assert dispatch.gitnexus_trigger("B", True, script=tmp_path / "x.py", runner=boom).startswith("error:TimeoutExpired")
