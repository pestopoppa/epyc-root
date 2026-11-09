"""parser_quality_common: one failed document must never lose scoring (parser-odl-hybrid-200pdf-20261109: doc 141 failed once,
the loop moved on with attempts=1 < MAX_ATTEMPTS, ok+failed_final was 199 != 200, nothing was scored, row ended rc=75)."""
import filecmp
import json
import os
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "scripts" / "row_jobs"))
os.environ.setdefault("FILLER_CPUS", "0")
import parser_quality_common as pq  # noqa: E402


def _job(tmp_path, monkeypatch, outcomes):
    """outcomes: stem -> list of (ok, value) consumed per attempt; missing stems always succeed."""
    pdfs = tmp_path / "pdfs"
    pdfs.mkdir()
    for i in range(200):
        (pdfs / f"d{i:03d}.pdf").write_text("x")
    monkeypatch.setattr(pq, "PDFS", pdfs)
    monkeypatch.setattr(pq, "DEADLINE", None)
    monkeypatch.setattr(pq, "STOPFILE", "")
    j = pq.Job("odl_hybrid", tmp_path / "row", 1)
    calls = {}
    scored = []
    j.prove_identity = lambda: {}
    j.start = lambda: None
    j.close = lambda: None

    def run_one(stem):
        calls[stem] = calls.get(stem, 0) + 1
        seq = outcomes.get(stem)
        return seq[min(calls[stem], len(seq)) - 1] if seq else (True, "# md " + stem)
    j.run_one = run_one
    j.score = lambda tag: scored.append(tag) or {"docs_scored": j.counts()["ok"]}
    return j, calls, scored


def test_transient_failure_is_retried_in_run_and_scored(tmp_path, monkeypatch):
    j, calls, scored = _job(tmp_path, monkeypatch, {"d141": [(True, ""), (True, "# ok")]})
    assert j.main() == 0
    assert calls["d141"] == 2
    assert j.counts() == {"ok": 200, "failed_final": 0, "untouched": 0}
    assert scored == ["final"] and (j.OUT / "COMPLETE").exists()


def test_permanently_failing_doc_is_censored_and_scoring_still_runs(tmp_path, monkeypatch):
    j, calls, scored = _job(tmp_path, monkeypatch, {"d141": [(True, "")]})
    assert j.main() == 0
    assert calls["d141"] == pq.MAX_ATTEMPTS
    assert j.counts() == {"ok": 199, "failed_final": 1, "untouched": 0}
    assert scored == ["final"] and (j.OUT / "COMPLETE").exists()
    recs = [json.loads(l) for l in (j.OUT / "results.jsonl").read_text().splitlines()]
    assert [r for r in recs if r.get("kind") == "final"][0]["coverage"]["failed_final"] == 1


def test_resume_finishes_doc_left_at_one_attempt(tmp_path, monkeypatch):
    j, calls, scored = _job(tmp_path, monkeypatch, {})
    for d in (j.OUT, j.STATE, j.PRED):
        d.mkdir(parents=True, exist_ok=True)
    j.sfile("d141").write_text(json.dumps({"status": "fail", "attempts": 1, "elapsed_s": 3.0, "error": "empty prediction"}))
    assert j.main() == 0
    assert calls["d141"] == 1 and j.counts()["ok"] == 200 and scored == ["final"]


DEPLOYED = Path("/mnt/raid0/llm/tmp/parser-quality-common-20261109-r2/common.py")


@pytest.mark.skipif(not DEPLOYED.exists(), reason="deployed copy not on this host")
def test_tracked_copy_matches_deployed_copy():
    assert filecmp.cmp(HERE.parents[1] / "scripts" / "row_jobs" / "parser_quality_common.py", DEPLOYED, shallow=False)
