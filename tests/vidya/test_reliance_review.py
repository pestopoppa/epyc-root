"""VB-AK-RELIANCE-REVIEW: a synthetic retraction flags exactly the experiments rows whose
`relies_on_claims` carried it, and no others. Real write path -> real fold."""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "vidya"))
sys.path.insert(0, str(REPO / "tests" / "vidya"))

import reliance_review as rr  # noqa: E402
from test_loop_beliefs import _claim_id, _ledger, _retract, _scoped  # noqa: E402

AS_OF = "2026-09-24T12:00:00+00:00"


def _row(attempt_id, payload):
    return {"attempt_id": attempt_id, "mechanism_id": "m-" + attempt_id, "status": "kept",
            "payload": json.dumps(payload) if payload is not None else "{not json"}


def test_synthetic_retraction_flags_exactly_the_carrying_rows(tmp_path):
    keep, gone, other = _scoped("keep"), _scoped("gone"), _scoped("other")
    path = _ledger(tmp_path, [keep, gone, other])
    _retract(path, gone)
    k, g, o = _claim_id(keep), _claim_id(gone), _claim_id(other)
    rows = [
        _row("a-carries", {"relies_on_claims": [k, g]}),
        _row("a-nested", {"hypothesis": {"relies_on_claims": [g]}}),
        _row("a-other", {"relies_on_claims": [k, o]}),
        _row("a-none", {"statement": "no reliance"}),
        _row("a-empty", {"relies_on_claims": []}),
        _row("a-prose", {"statement": f"mentions {g} only in prose"}),
        _row("a-bad", None),
    ]
    out = rr.review_ledger(rows, path, as_of=AS_OF)
    assert out["flagged_attempt_ids"] == ["a-carries", "a-nested"]
    assert out["flagged"][0]["flagged_claims"] == [
        {"claim_id": g, "canonical_id": g, "status": "retracted"}]
    assert out["undecodable"] == ["a-bad"] and out["scanned"] == 7


def test_nothing_retracted_flags_nothing(tmp_path):
    a = _scoped("a")
    path = _ledger(tmp_path, [a])
    out = rr.review_ledger([_row("r", {"relies_on_claims": [_claim_id(a)]})], path, as_of=AS_OF)
    assert out["flagged"] == []


def test_alias_and_correction_flags_without_a_ledger():
    rows = [_row("via-alias", {"relies_on_claims": ["clm_old"]}),
            _row("corr", {"relies_on_claims": ["clm_c"]}),
            _row("clean", {"relies_on_claims": ["clm_ok"]})]
    out = rr.review(rows, {"clm_new": "retracted", "clm_c": "corrected"}, {"clm_old": "clm_new"})
    assert out["flagged_attempt_ids"] == ["via-alias", "corr"]


def test_reads_a_real_experiments_table_read_only(tmp_path):
    db = tmp_path / "experiments.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE experiments (attempt_id TEXT, recorded_at TEXT, mechanism_id TEXT,"
                 " status TEXT, payload TEXT)")
    conn.execute("INSERT INTO experiments VALUES ('x','t','m','kept',?)",
                 (json.dumps({"relies_on_claims": ["clm_z"]}),))
    conn.commit(); conn.close()
    rows = rr.read_experiments(db)
    assert rr.review(rows, {"clm_z": "retracted"})["flagged_attempt_ids"] == ["x"]
