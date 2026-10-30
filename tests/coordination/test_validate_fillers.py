"""Tests for scripts/coordination/validate_fillers.py -- temp tables only."""
import contextlib
import io
import os
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
    v = dict(id="r1", owner="o", launcher="`/x/launch.sh` pid=4242", res="q1", minw="20 m", ram="40 GiB", stop="/s/STOP",
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


class R:
    def __init__(self, returncode, stdout):
        self.returncode, self.stdout = returncode, stdout


def cli(*a):
    """In-process run (so the liveness probe can be patched); see test_script_smoke for a subprocess."""
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
        rc = vf.run(list(a))
    return R(rc, out.getvalue())


@pytest.fixture(autouse=True)
def _alive(monkeypatch):
    monkeypatch.setattr(vf, "pid_alive", lambda pid, tokens: pid != 666)


def test_script_smoke_subprocess(tmp_path):
    r = subprocess.run([sys.executable, str(SCRIPT), "--file", str(tmp_path / "nope.md")],
                       capture_output=True, text=True)
    assert r.returncode == 3


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


@pytest.mark.parametrize("eff", ["n/a (build)", "n/a (noise unit)", "exact identity", "gates pass exactly", "+/-5 pp at n=20", "tg 2.00%"])
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


# ---- queue semantics: QUEUED implies a live launcher, everything else is BACKLOG ----
def backlog(**kw):
    d = dict(status="BACKLOG", ready="n", launcher="none yet", notes="blocker=missing launcher: no driver")
    d.update(kw)
    return row(**d)


def msgs(tmp_path, *rows, rid="r1"):
    return cli("--file", table(tmp_path, *rows), "--row", rid, "--for-grant")


def test_queued_row_with_live_pid_is_clean(tmp_path):
    assert msgs(tmp_path, row()).returncode == 0


def test_ready_y_without_pid_refused(tmp_path):
    r = msgs(tmp_path, row(launcher="`/x/launch.sh`"))
    assert r.returncode == 2 and "no launcher PID" in r.stdout


def test_ready_y_dead_pid_refused(tmp_path):
    r = msgs(tmp_path, row(launcher="`/x/launch.sh` pid=666"))
    assert r.returncode == 2 and "pid=666 is dead" in r.stdout


def test_pid_in_notes_and_legacy_spelling(tmp_path):
    assert msgs(tmp_path, row(launcher="`/x/launch.sh`", notes="armed pid=4242")).returncode == 0
    assert msgs(tmp_path, row(launcher="`/x/launch.sh`, PID 4242")).returncode == 0


def test_probe_receives_row_id_grant_and_launcher_path(tmp_path, monkeypatch):
    seen = {}
    monkeypatch.setattr(vf, "pid_alive", lambda pid, toks: seen.update(pid=pid, toks=toks) or True)
    msgs(tmp_path, row(launcher="`/x/launch.sh` pid=77; polls grants/f8-night.grant"))
    assert seen["pid"] == 77 and {"r1", "/x/launch.sh", "f8-night"} <= set(seen["toks"])


def test_check_row_accepts_injected_probe(tmp_path):
    t = vf.parse_table(Path(table(tmp_path, row())).read_text())
    col, rows, _ = t
    cells = rows[0][1]
    assert vf.check_row(cells, col, set(), pid_alive=lambda p, t: True) == []
    assert any("dead" in m for m in vf.check_row(cells, col, set(), pid_alive=lambda p, t: False))


def test_real_proc_probe(tmp_path):
    me = open(f"/proc/{os.getpid()}/cmdline", "rb").read().replace(b"\0", b" ").decode()
    tok = me.split()[0]
    assert vf.proc_pid_alive(os.getpid(), [tok])
    assert not vf.proc_pid_alive(os.getpid(), ["zz-no-such-token-zz"])
    assert not vf.proc_pid_alive(2 ** 22 + 12345, [tok])


def test_registered_not_ready_is_error_naming_backlog(tmp_path):
    r = msgs(tmp_path, backlog(status="REGISTERED"))
    assert r.returncode == 2 and "convert it to BACKLOG" in r.stdout


def test_other_non_ready_status_must_be_backlog(tmp_path):
    r = msgs(tmp_path, backlog(status="NOT-ARMED"))
    assert "must be BACKLOG" in r.stdout


@pytest.mark.parametrize("kind", ["missing launcher", "harness fix", "build", "operator decision"])
def test_backlog_with_blocker_and_owner_clean(tmp_path, kind):
    r = cli("--file", table(tmp_path, backlog(notes=f"blocker={kind}: text")), "--row", "r1")
    assert "WARN" not in r.stdout, r.stdout


def test_backlog_needs_blocker_from_set_and_owner(tmp_path):
    for notes in ("", "blocker=waiting for Godot", "blocked on build"):
        r = cli("--file", table(tmp_path, backlog(notes=notes)), "--row", "r1")
        assert "needs `blocker=" in r.stdout
    r = cli("--file", table(tmp_path, backlog(owner="-")), "--row", "r1")
    assert "needs an owner" in r.stdout


def test_ready_y_must_be_armed_and_terminal_rows_exempt(tmp_path):
    r = msgs(tmp_path, row(status="REGISTERED"))
    assert "a queued row is ARMED" in r.stdout
    for st in ("COMPLETE", "CANCELLED"):
        r = cli("--file", table(tmp_path, row(status=st, launcher="none", ready="y")), "--row", "r1")
        assert "WARN" not in r.stdout


@pytest.mark.parametrize("eff", ["n/a", "n/a ()", "n/a ( )"])
def test_bare_or_empty_na_effect_refused(tmp_path, eff):
    assert cli("--file", table(tmp_path, row(eff=eff)), "--row", "r1", "--for-grant").returncode == 2


@pytest.mark.parametrize("status", ["CANCELLED", "COMPLETE"])
def test_terminal_rows_skip_field_checks(tmp_path, status):
    bad = row(status=status, ready="n", ram="lots", prior="-", dec="-", eff="-", sub="?", cls="?",
              launcher="none")
    r = msgs(tmp_path, bad)
    assert r.returncode == 0 and "r1" not in r.stdout.replace("OK", "")


# ---- CTC-Q-C: booking class derived from the decision -------------------------------------------
def _derive(tmp_path, **kw):
    f = table(tmp_path, row(**kw))
    return cli("--file", f, "--print-class", "r1")


@pytest.mark.parametrize("kw,want", [
    (dict(cls="block-timing-quiet", dec="keep candidate vs champion baseline",
          notes="floor /x/serving-floor.q27b.json"), "block-timing-quiet"),
    (dict(cls="block-correctness", dec="candidate B vs baseline C: keep gate",
          prior="/a/b/serving-floor.q.json"), "block-timing-quiet"),
    (dict(cls="block-correctness", dec="keep gate on the registry floor for Q38FN decode"),
     "block-timing-quiet"),
    # baseline named but no floor file: not quiet; timing words make it pairable
    (dict(cls="block-timing-quiet", dec="candidate vs champion baseline", eff="tg 2.00%"),
     "block-timing-pairable"),
    (dict(cls="block-timing-pairable", dec="indicative: does the cache help prefill", eff="5% tok/s"),
     "block-timing-pairable"),
    (dict(cls="block-timing-quiet", dec="are the 12 failures pre-existing on baseline C", eff="exact"),
     "block-correctness"),
    (dict(cls="block-correctness", dec="is the output identical across arms", eff="exact identity"),
     "block-correctness"),
    (dict(cls="filler", dec="is the output identical across arms"), "filler"),
])
def test_derive_booking_class(tmp_path, kw, want):
    r = _derive(tmp_path, **kw)
    assert r.returncode == 0 and r.stdout.strip() == want


def test_print_class_unknown_row_exit_3(tmp_path):
    assert cli("--file", table(tmp_path, row()), "--print-class", "nope").returncode == 3


def test_declared_stricter_than_derived_refuses_for_grant_warns_otherwise(tmp_path):
    f = table(tmp_path, row(cls="block-timing-quiet", dec="are the 12 failures pre-existing on a base",
                            eff="exact", notes="serving-floor.x.json"))
    g = cli("--file", f, "--row", "r1", "--for-grant")
    assert g.returncode == 2 and "stricter than derived block-correctness" in g.stdout
    w = cli("--file", f)
    assert w.returncode == 0 and "WARN" in w.stdout and "stricter than derived" in w.stdout


def test_declared_laxer_than_derived_is_fine(tmp_path):
    f = table(tmp_path, row(cls="block-correctness", dec="candidate vs champion baseline",
                            notes="serving-floor.x.json"))
    assert cli("--file", f, "--row", "r1", "--for-grant").returncode == 0


def test_floor_measuring_row_derives_quiet(tmp_path):
    """c2-q38fn-aa-floor's real text: it produces a floor, so it cannot cite one."""
    kw = dict(cls="block-timing-quiet", eff="n/a (noise unit)",
              dec="C2 CAS: noise unit for the dd3d9721c Q38FN recipe on the current host state; "
                  "contextualises c2-q38fn-b-rerun and later 7b ABAs",
              prior="stored 24-pair Q38FN floors 0.65-8.4% for other recipes/builds: "
                    "`/mnt/raid0/llm/autokernel/campaigns/x/runtime-source-floors/`",
              notes="Optional, same grant as c2-q38fn-b-rerun. Output is per-pair spread")
    assert _derive(tmp_path, **kw).stdout.strip() == "block-timing-quiet"
    # no build reference -> not a baseline measurement
    kw["dec"] = "noise unit for the thing"
    assert _derive(tmp_path, **kw).stdout.strip() != "block-timing-quiet"


@pytest.mark.parametrize("text", [
    "Indicative correctness, no throughput claim",
    "not a timing run",
    "no speed claim, exactness only; without timing",
    "non-timing smoke",
])
def test_negated_timing_mentions_are_not_timing_signals(text):
    assert not vf.has_timing_signal(text)


@pytest.mark.parametrize("text", [
    "throughput A/B vs champion",
    "timing decision",
    "indicative timing, 3 pairs",
    "no warmup; tok/s is the metric",
    "gate: no throughput regression vs champion",
    "no tg loss > 1%",
    "no regression in throughput",
    "not a correctness-only check: latency A/B",
])
def test_real_timing_mentions_still_timing_signals(text):
    assert vf.has_timing_signal(text)



@pytest.mark.parametrize("dec,eff", [
    ("C2 CAS: noise unit for the dd3d9721c Q38FN recipe on the current host state", "n/a (noise unit)"),
    ("Measure candidate build ffc1bac82 baseline CPU A/A floor characterization", "n/a (uncertified raw characterization)"),
])
def test_build_floor_measurement_admits_without_existing_floor(tmp_path, dec, eff):
    record = row(cls="block-timing-quiet", dec=dec, eff=eff)
    f = table(tmp_path, record)
    assert _derive(tmp_path, cls="block-timing-quiet", dec=dec, eff=eff).stdout.strip() == "block-timing-quiet"
    checked = cli("--file", f, "--row", "r1", "--for-grant")
    assert checked.returncode == 0, checked.stdout


@pytest.mark.parametrize("dec,eff", [
    ("noise unit for the thing", "n/a (noise unit)"),
    ("A/A floor characterization", "n/a (raw observations)"),
    ("candidate throughput comparison, stddev retained", "+2% tok/s"),
    ("candidate versus baseline speed comparison", "n/a (noise observed)"),
    ("recipe only; no floor-producing operation", "n/a (stddev recorded)"),
    ("noise unit without declared identity", "n/a (spread)"),
])
def test_nonmeasurement_quiet_keeps_existing_floor_requirement(tmp_path, dec, eff):
    f = table(tmp_path, row(cls="block-timing-quiet", dec=dec, eff=eff))
    checked = cli("--file", f, "--row", "r1", "--for-grant")
    assert checked.returncode == 2, checked.stdout
    assert "must cite a floor file" in checked.stdout
    assert _derive(tmp_path, cls="block-timing-quiet", dec=dec, eff=eff).stdout.strip() != "block-timing-quiet"


def test_comparative_quiet_real_floor_contract_unchanged(tmp_path):
    floor = tmp_path / "serving-floor.q.json"
    floor.write_text('{"fixture_only": true}\n')
    f = table(tmp_path, row(cls="block-timing-quiet", dec="candidate versus baseline throughput", notes=str(floor)))
    checked = cli("--file", f, "--row", "r1", "--for-grant")
    assert checked.returncode == 0, checked.stdout
