"""Tests for scripts/coordination/validate_fillers.py -- temp tables only."""
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.coordination import validate_fillers as vf

SCRIPT = Path(__file__).parents[2] / "scripts/coordination/validate_fillers.py"
HEADER = ("| filler-id | owner | launcher + PID | resources | min useful window | max private RAM | "
          "STOP file | status | class | duration | min window | DS41-class y/n | ready y/n | prior | "
          "decision | min_effect | substrate | notes |")
SEP = "|" + "---|" * 18


def row(**kw):
    v = dict(id="r1", owner="o", launcher="l", res="q1", minw="20 m", ram="40 GiB", stop="/s/STOP",
             status="ARMED", cls="filler", dur="1 h", mw="20 m", ds="n", ready="y",
             prior="none found (f8, 2026-10-22)", dec="does X beat Y on the champion baseline",
             eff="+2.0% tok/s", sub="cpu", notes="")
    v.update(kw)
    return "| " + " | ".join(str(v[k]) for k in ["id", "owner", "launcher", "res", "minw", "ram",
                                                   "stop", "status", "cls", "dur", "mw", "ds",
                                                   "ready", "prior", "dec", "eff", "sub",
                                                   "notes"]) + " |"


def table(tmp_path, *rows):
    p = tmp_path / "FILLERS.md"
    p.write_text("# q\n\n## Queue\ntext\n\n" + "\n".join([HEADER, SEP, *rows]) + "\n\n## After\n")
    return str(p)


def cli(*a):
    return subprocess.run([sys.executable, str(SCRIPT), *a], capture_output=True, text=True)


def test_clean_row_passes_for_grant(tmp_path):
    f = table(tmp_path, row())
    r = cli("--file", f, "--row", "r1", "--for-grant")
    assert r.returncode == 0, r.stdout
    assert r.stdout.startswith("OK")


@pytest.mark.parametrize("field,val,needle", [
    ("status", "NOT-ARMED (S5 bundle sub-row)", "carries text"),
    ("status", "DONE", "first token"),
    ("cls", "quiet", "class"),
    ("ds", "yes", "ds41-class"),
    ("ready", "after build", "ready"),
    ("sub", "both", "substrate"),
    ("prior", "-", "prior unfilled"),
    ("prior", "none checked (owner)", "neither a path"),
    ("dec", "-", "decision"),
    ("eff", "-", "min_effect unfilled"),
    ("eff", "big gain", "min_effect"),
    ("ram", "-", "peak host RAM"),
    ("ram", "~48 GB VRAM", "peak host RAM"),
    ("ram", "45-60 GiB", "peak host RAM"),
])
def test_each_rule_refuses_for_grant_but_only_warns_otherwise(tmp_path, field, val, needle):
    f = table(tmp_path, row(**{field: val}))
    g = cli("--file", f, "--row", "r1", "--for-grant")
    assert g.returncode == 2 and needle in g.stdout
    w = cli("--file", f)
    assert w.returncode == 0 and "WARN" in w.stdout and needle in w.stdout


@pytest.mark.parametrize("prior", [
    "/mnt/raid0/llm/tmp/x/summary.json",
    "`/mnt/raid0/llm/tmp/x/summary.json` (n=1)",
    "none found (workspace-f8, 2026-10-22)",
    "none (checked 2026-10-22T05:00:00Z)",
])
def test_prior_forms_accepted(tmp_path, prior):
    assert cli("--file", table(tmp_path, row(prior=prior)), "--row", "r1", "--for-grant").returncode == 0


@pytest.mark.parametrize("eff", ["n/a (build)", "exact identity", "gates pass exactly", "+/-5 pp at n=20", "tg 2.00%"])
def test_effect_forms_accepted(tmp_path, eff):
    assert cli("--file", table(tmp_path, row(eff=eff)), "--row", "r1", "--for-grant").returncode == 0


def test_quiet_needs_baseline_and_floor_file(tmp_path):
    base = dict(cls="block-timing-quiet")
    ok = row(**base, dec="keep candidate vs champion baseline",
             notes="floor /mnt/raid0/llm/x/serving-floor.q27b.json")
    assert cli("--file", table(tmp_path, ok), "--row", "r1", "--for-grant").returncode == 0
    no_floor = row(**base, dec="keep candidate vs champion baseline", notes="")
    r = cli("--file", table(tmp_path, no_floor), "--row", "r1", "--for-grant")
    assert r.returncode == 2 and "floor file" in r.stdout
    no_base = row(**base, dec="does the thing help at all", notes="serving-floor.x.json")
    r = cli("--file", table(tmp_path, no_base), "--row", "r1", "--for-grant")
    assert r.returncode == 2 and "baseline" in r.stdout
    in_prior = row(**base, dec="candidate vs baseline", prior="/a/b/serving-floor.q.json")
    assert cli("--file", table(tmp_path, in_prior), "--row", "r1", "--for-grant").returncode == 0


def test_other_rows_do_not_block_a_clean_grant(tmp_path):
    f = table(tmp_path, row(id="bad", prior="-", dec="-", eff="-", sub="-"), row(id="good"))
    assert cli("--file", f, "--row", "good", "--for-grant").returncode == 0
    assert cli("--file", f, "--row", "bad", "--for-grant").returncode == 2


def test_duplicate_id_flagged(tmp_path):
    f = table(tmp_path, row(), row())
    assert "duplicate" in cli("--file", f).stdout


def test_cell_count_malformed(tmp_path):
    bad = row() + " extra |"
    f = table(tmp_path, bad.replace("r1", "r9"), row())
    full = cli("--file", f)
    assert full.returncode == 0 and "malformed row" in full.stdout
    assert cli("--file", f, "--row", "r9").returncode == 3
    assert cli("--file", f, "--row", "r1", "--for-grant").returncode == 0


def test_malformed_inputs_exit_3(tmp_path):
    assert cli("--file", str(tmp_path / "nope.md")).returncode == 3
    p = tmp_path / "x.md"
    p.write_text("no table here\n")
    assert cli("--file", str(p)).returncode == 3
    f = table(tmp_path, row())
    assert cli("--file", f, "--row", "absent").returncode == 3
    assert cli("--file", f, "--for-grant").returncode == 3


def test_header_with_wrong_columns_is_malformed(tmp_path):
    p = tmp_path / "x.md"
    p.write_text(HEADER.replace("| notes |", "|") + "\n" + SEP + "\n")
    assert cli("--file", str(p)).returncode == 3


def test_blank_line_inside_table_is_tolerated_and_reported(tmp_path):
    p = tmp_path / "x.md"
    p.write_text("\n".join([HEADER, SEP, row(id="a"), "", row(id="b"), "", "## After"]) + "\n")
    r = cli("--file", str(p), "--row", "b", "--for-grant")
    assert r.returncode == 0
    assert "blank line inside the table" in r.stdout


@pytest.mark.parametrize("ram", ["48", "48 GiB", "~48 GiB", "519.5 GiB"])
def test_ram_forms_accepted(tmp_path, ram):
    assert cli("--file", table(tmp_path, row(ram=ram)), "--row", "r1", "--for-grant").returncode == 0


def test_renamed_ram_header_is_accepted(tmp_path):
    p = tmp_path / "x.md"
    p.write_text("\n".join([HEADER.replace("max private RAM", "peak host RAM GiB"), SEP, row()]) + "\n")
    assert cli("--file", str(p), "--row", "r1", "--for-grant").returncode == 0
