#!/usr/bin/env python3
"""AK parallel loop P0: estimate-from-history (scripts/coordination/rowflow/estimate_history.py)."""
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "rowflow"))
import estimate_history as eh  # noqa: E402


def _row(flags, rid, wall_s, *, rc="0", reason="complete", est=None, started=True, units=None,
         filed=None):
    g = flags / "grants"
    g.mkdir(parents=True, exist_ok=True)
    (flags / "ready").mkdir(exist_ok=True)
    (flags / "filing-done").mkdir(exist_ok=True)
    start_m, end_s = 0, wall_s
    end = f"2026-11-20T{10 + end_s // 3600:02d}:{(end_s // 60) % 60:02d}:{end_s % 60:02d}Z"
    lines = [f"rc={rc} time={end} reason={reason}", f"job_id={rid}"]
    if started:
        lines.append(f"started=2026-11-20T10:00:0{start_m}Z")
    else:
        (g / f"{rid}.grant").write_text("regions=q0 start=2026-11-20T10:00Z end=2026-11-20T23:00Z")
    if est:
        lines.append(f"estimated_wall_s={est}")
    (g / f"{rid}.ended").write_text("\n".join(lines) + "\n")
    man = {"id": rid}
    if units:
        res = flags / f"{rid}.jsonl"
        res.write_text("".join(json.dumps({"unit_id": f"u{i}"}) + "\n" for i in range(units))
                       + json.dumps({"unit_id": "smoke-1", "mode": "smoke"}) + "\n")
        man.update(unit_key="unit_id", result_path=str(res))
    (flags / "ready" / f"{rid}.json").write_text(json.dumps(man))
    if filed:
        (flags / "filing-done" / f"{rid}.verdict.json").write_text(json.dumps(filed))


def test_family_strips_date_and_revision():
    assert eh.family_of("ak-dtree-build-gpu-20261120-r2") == "ak-dtree-build-gpu"
    assert eh.family_of("c15-fold-cpu-20261119T0300Z") == "c15-fold-cpu"
    assert eh.family_of("x-20261120", {"family": "fam"}) == "fam"


def test_percentile_is_nearest_rank():
    assert eh.percentile([1, 2, 3, 4], 0.75) == 3
    assert eh.percentile([10], 0.75) == 10
    assert eh.percentile([], 0.5) is None


def test_suggestion_is_p75_times_margin_and_excludes_failed_and_dry_runs(tmp_path):
    for i, w in enumerate((100, 200, 300, 400)):
        _row(tmp_path, f"fam-a-2026112{i}", w)
    _row(tmp_path, "fam-a-20261125", 9000, rc="75", reason="stopped")             # not complete
    _row(tmp_path, "fam-a-20261126", 9000, filed={"dry_run": True})              # dry run
    _row(tmp_path, "fam-a-20261127", 9000, filed={"compute_burned": False})      # nothing burned
    s = eh.suggest("fam-a-20261130", flags=str(tmp_path))
    assert s["n"] == 4 and s["p75_s"] == 300 and s["estimate_s"] == 375
    assert s["overrun_threshold_s"] == 563
    assert "300.0 s x 1.25" in s["estimate_justification"]


def test_too_little_history_returns_none(tmp_path):
    _row(tmp_path, "fam-b-20261120", 100)
    _row(tmp_path, "fam-b-20261121", 100)
    assert eh.suggest("fam-b-20261122", flags=str(tmp_path)) is None


def test_grant_start_fallback_and_overrun_flag(tmp_path):
    _row(tmp_path, "fam-c-20261120", 600, started=False, est=100)
    rec = [r for r in eh.samples(str(tmp_path)) if r["row"] == "fam-c-20261120"][0]
    assert rec["wall_s"] == 600 and rec["overrun"] is True and rec["usable"]


def test_per_unit_scaling_when_units_given(tmp_path):
    for i, (w, u) in enumerate(((100, 10), (200, 10), (300, 10))):
        _row(tmp_path, f"fam-d-2026112{i}", w, units=u)
    t = eh.table(eh.samples(str(tmp_path)))["fam-d"]
    assert t["per_unit_n"] == 3 and t["per_unit_p75_s"] == 30.0   # smoke record not counted
    s = eh.suggest("fam-d-20261129", units=4, flags=str(tmp_path))
    assert s["estimate_s"] == 150 and "4 units x 30.0 s/unit" in s["estimate_justification"]


def test_cli_no_history_exit_3(tmp_path, capsys):
    (tmp_path / "grants").mkdir()
    assert eh.main(["--flags", str(tmp_path), "--row", "nothing-20261120"]) == 3
    assert "NO-HISTORY" in capsys.readouterr().out
