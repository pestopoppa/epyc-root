#!/usr/bin/env python3
"""row_disk_budget.py + template_lint manifest WARNs."""
import io
import json
import os
import sys
import time
from contextlib import redirect_stdout

import pytest

_C = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_C, "churn"))
sys.path.insert(0, os.path.join(_C, "job_templates"))
import row_disk_budget as rdb  # noqa: E402
import template_lint as tl  # noqa: E402

GIB = 1 << 30


def mkrow(tmp_path, rid="r1", budget=None, scratch=True, post=0, pre=0):
    flags = tmp_path / "flags"
    (flags / "ready").mkdir(parents=True, exist_ok=True)
    (flags / "grants").mkdir(exist_ok=True)
    sr = tmp_path / ("scratch-" + rid)
    sr.mkdir()
    m = {"id": rid}
    if scratch:
        m["scratch_root"] = str(sr)
    if budget is not None:
        m["budget_gib"] = budget
    (flags / "ready" / f"{rid}.json").write_text(json.dumps(m))
    g = flags / "grants" / f"{rid}.grant"
    g.write_text("x")
    old = time.time() - 1000
    if pre:
        f = sr / "input.bin"
        with open(f, "wb") as fh:
            fh.truncate(pre)
        os.utime(f, (old - 10, old - 10))
    os.utime(g, (old, old))
    if post:
        with open(sr / "out.bin", "wb") as fh:
            fh.truncate(post)
    return flags


def run(flags, *args):
    buf = io.StringIO()
    with redirect_stdout(buf):
        assert rdb.main(["--flags", str(flags), *args]) == 0
    return buf.getvalue()


def alerts(flags):
    p = flags / "rowflow-alerts.jsonl"
    return p.read_text().splitlines() if p.exists() else []


def test_ok_within_budget(tmp_path):
    f = mkrow(tmp_path, budget=1, post=GIB)
    assert "verdict=OK" in run(f)


def test_over(tmp_path):
    f = mkrow(tmp_path, budget=1, post=4 * GIB)
    out = run(f)
    assert "verdict=OVER" in out and "over=1" in out


def test_pre_grant_inputs_not_counted(tmp_path):
    f = mkrow(tmp_path, budget=1, pre=50 * GIB, post=1024)
    assert "verdict=OK" in run(f)


def test_undeclared_default(tmp_path):
    f = mkrow(tmp_path, post=4 * GIB)
    out = run(f)
    assert "declared=false" in out and "budget_gib=1.0" in out and "verdict=OVER" in out and "undeclared=1" in out


def test_no_scratch_root(tmp_path):
    f = mkrow(tmp_path, scratch=False)
    assert "verdict=NO-SCRATCH-ROOT" in run(f)


def test_ended_grant_skipped(tmp_path):
    f = mkrow(tmp_path, post=4 * GIB)
    (f / "grants" / "r1.ended").write_text("x")
    assert "live=0" in run(f)


def test_alert_dedupe(tmp_path):
    f = mkrow(tmp_path, budget=1, post=4 * GIB)
    run(f, "--alert")
    assert len(alerts(f)) == 1
    rec = json.loads(alerts(f)[0])
    assert rec["schema"] == "rowflow.alert.v1" and rec["row_id"] == "r1" and rec["kind"] == "disk-budget"
    run(f, "--alert")
    assert len(alerts(f)) == 1
    assert (f / "ws58-keeper-state" / "disk-budget.json").exists()


def test_no_alert_when_ok(tmp_path):
    f = mkrow(tmp_path, budget=1, post=10)
    run(f, "--alert")
    assert alerts(f) == []


def test_walk_cap_unverifiable_no_alert(tmp_path):
    f = mkrow(tmp_path, budget=1, post=4 * GIB)
    sr = tmp_path / "scratch-r1"
    for i in range(10):
        (sr / f"f{i}").write_text("a")
    out = run(f, "--alert", "--walk-cap", "3")
    assert "verdict=UNVERIFIABLE" in out and alerts(f) == []


def test_log_and_json(tmp_path):
    f = mkrow(tmp_path, budget=1, post=10)
    lg = tmp_path / "x.log"
    d = json.loads(run(f, "--json", "--log", str(lg)))
    assert d["live"] == 1 and "BUDGET SUMMARY" in lg.read_text()


def lint(tmp_path, manifest):
    (tmp_path / "row.json").write_text(json.dumps(manifest))
    return tl.lint_dir(tmp_path)


def test_lint_budget_missing(tmp_path):
    w = lint(tmp_path, {"schema": "epyc.row.v3", "id": "x", "raw": ["a"]})
    assert any(x.startswith("budget_gib missing") for x in w) and not any("raw declaration" in x for x in w)


def test_lint_raw_missing(tmp_path):
    w = lint(tmp_path, {"id": "x", "budget_gib": 3})
    assert any(x.startswith("raw declaration missing") for x in w) and not any("budget_gib" in x for x in w)


def test_lint_well_declared(tmp_path):
    assert lint(tmp_path, {"id": "x", "budget_gib": 3, "notes": "raw_globs=out/*.bin"}) == []
    assert lint(tmp_path, {"id": "x", "budget_gib": 3, "raw": ["out/*"]}) == []


def test_lint_launcher_path_and_exit0(tmp_path, capsys):
    (tmp_path / "row.json").write_text(json.dumps({"id": "x"}))
    (tmp_path / "launch.sh").write_text("echo hi\n")
    assert tl.main([str(tmp_path / "launch.sh")]) == 0
    assert "WARN budget_gib missing" in capsys.readouterr().out
