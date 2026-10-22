"""VB-EV19-GOLD-SELFCHECK-WIRE: scorer/pool self-check -> measurement tuples, graded by the shared ladder."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402
from adapters import _native_sidecar as ns  # noqa: E402
from adapters import ev19_gold_selfcheck as gs  # noqa: E402

WHEN = "2026-10-22T10:00:00Z"
ERA = "E20-eval-corpus-ev19-quality"


def suite(checkable=40, wrong=0, err=0, nc=4):
    ok = checkable - wrong - err
    return {"n": checkable + nc, "checkable": checkable, "ok_bare": max(ok - 2, 0), "ok_wrapped": min(2, ok),
            "ok_bare_rendered_gold": 0, "wrong": wrong, "scorer_error": err, "not_checkable": nc,
            "rate": ((wrong + err) / checkable) if checkable else None, "bare_wrong_rate": 0.0, "top_reasons": {}}


def setup(tmp_path, max_per_suite=0, suites=None):
    pool = tmp_path / "pool.jsonl"
    pool.write_text('{"suite":"a"}\n')
    rep = {"self_check_version": 2, "flagged": [], "method": "stride sample, bare gold then 8 wrappers",
           "pool": str(pool), "pool_size_bytes": pool.stat().st_size, "max_per_suite": max_per_suite,
           "suites": suites or {"agentic": suite(), "math": suite(100, wrong=1),
                                "empty": suite(0, nc=3)}}
    r = tmp_path / "gold_self_check.json"
    r.write_text(json.dumps(rep))
    return r, pool


def write(tmp_path, report, pool, **kw):
    kw.setdefault("pool_id", "corpus-ev19b-20261021")
    return gs.write_belief_measurements(tmp_path, run_id="ev19-t", producer="gold_self_check.py",
                                        report_path=report, pool_path=pool, eval_era_row=ERA,
                                        emitted_at=WHEN, **kw)


def rewrite(side, fn):
    rows = [json.loads(x) for x in side.read_text().splitlines()]
    fn(rows[0])
    side.write_text("\n".join(json.dumps(r) for r in rows) + "\n")


def test_full_pool_round_trip_and_grade(tmp_path):
    rep, pool = setup(tmp_path)
    side = write(tmp_path, rep, pool)
    natives = gs.native_rows(side)
    assert sorted(n["row"]["extra"]["suite_id"] for n in natives) == ["agentic", "math"]  # empty skipped
    for n in natives:
        tup = gs.project(n)
        assert tup.extra["sample_mode"] == "full_pool" and tup.extra["eval_era_row"] == ERA
        assert "not a model claim" in tup.claim and tup.metric_direction == "lower_better"
        q, t, _ = ct.grade(tup)
        assert (q, t) == ("Judged", "Located")  # no ratified protocol cited -> OBSERVATION by the ladder
    math = [n for n in natives if n["row"]["extra"]["suite_id"] == "math"][0]
    assert math["row"]["value"] == pytest.approx(0.01) and math["row"]["reps"] == 100
    assert gs.frames_for_sidecar(side, as_of=WHEN)


def test_full_pool_with_protocol_follows_the_shared_ladder(tmp_path):
    rep, pool = setup(tmp_path)
    side = write(tmp_path, rep, pool, protocol_id="P-QUAL-T1")
    tup = gs.project(gs.native_rows(side)[0])
    assert ct.grade(tup)[0] == "Witnessed"  # whatever grade() says; the adapter decides nothing


def test_sampled_run_is_non_gating_and_cannot_cite_protocol(tmp_path):
    rep, pool = setup(tmp_path, max_per_suite=300)
    with pytest.raises(gs.CaptureError, match="sampled"):
        write(tmp_path, rep, pool, protocol_id="P-QUAL-T1")
    side = write(tmp_path, rep, pool)
    tup = gs.project(gs.native_rows(side)[0])
    assert tup.extra["sample_mode"] == "sampled" and tup.extra["max_per_suite"] == 300
    assert tup.protocol_id == "" and ct.grade(tup)[:2] == ("Judged", "Located")


def test_sampled_row_with_forged_protocol_is_void(tmp_path):
    rep, pool = setup(tmp_path, max_per_suite=300)
    side = write(tmp_path, rep, pool)
    def mut(r):
        r["protocol_id"] = "P-QUAL-T1"
        ns.seal(r)
    rewrite(side, mut)
    assert gs.native_rows(side) == ()


def test_sample_mode_relabel_is_void(tmp_path):
    rep, pool = setup(tmp_path, max_per_suite=300)
    side = write(tmp_path, rep, pool)
    def mut(r):
        r["extra"]["sample_mode"] = "full_pool"
        ns.seal(r)
    rewrite(side, mut)
    assert gs.native_rows(side) == ()


def test_tampered_row_and_decayed_attestation(tmp_path):
    rep, pool = setup(tmp_path)
    side = write(tmp_path, rep, pool)
    rewrite(side, lambda r: r.update(value=0.5))
    assert gs.native_rows(side) == ()
    side = write(tmp_path, rep, pool)
    rep.write_text(rep.read_text().replace('"n": 44', '"n": 45'))
    assert gs.native_rows(side)[0]["attestation_present"] is False


def test_wrong_rate_must_recompute_from_counts(tmp_path):
    rep, pool = setup(tmp_path)
    side = write(tmp_path, rep, pool)
    def mut(r):
        r["extra"]["suite"]["wrong"] += 1
        r["extra"]["suite"]["ok_bare"] -= 1
        ns.seal(r)
    rewrite(side, mut)
    assert gs.native_rows(side) == ()


def test_writer_refuses_pool_mismatch(tmp_path):
    rep, pool = setup(tmp_path)
    with pytest.raises(gs.CaptureError, match="expected digest"):
        write(tmp_path, rep, pool, expected_pool_sha256="0" * 64)
    other = tmp_path / "other.jsonl"
    other.write_text("x")
    with pytest.raises(gs.CaptureError, match="scored pool"):
        write(tmp_path, rep, other)
    pool.write_text('{"suite":"a"}\n{"suite":"b"}\n')  # pool grew after the run
    with pytest.raises(gs.CaptureError, match="byte size"):
        write(tmp_path, rep, pool)
    with pytest.raises(gs.CaptureError, match="pool file missing"):
        write(tmp_path, rep, tmp_path / "gone.jsonl")


def test_writer_refuses_missing_and_inconsistent_fields(tmp_path):
    rep, pool = setup(tmp_path)
    d = json.loads(rep.read_text())
    del d["max_per_suite"]
    rep.write_text(json.dumps(d))
    with pytest.raises(gs.CaptureError, match="max_per_suite"):
        write(tmp_path, rep, pool)
    rep, pool = setup(tmp_path, suites={"a": {**suite(), "wrong": 3}})  # counts no longer sum
    with pytest.raises(gs.CaptureError, match="malformed"):
        write(tmp_path, rep, pool)
    rep, pool = setup(tmp_path, suites={"a": suite(0, nc=2)})
    with pytest.raises(gs.CaptureError, match="no suite"):
        write(tmp_path, rep, pool)


def test_project_refuses_invalid_native(tmp_path):
    rep, pool = setup(tmp_path)
    row = dict(gs.native_rows(write(tmp_path, rep, pool))[0]["row"], value=0.9)
    with pytest.raises(ct.ProjectionError):
        gs.project({"row": row})
    with pytest.raises(ct.ProjectionError):
        gs.project(None)
