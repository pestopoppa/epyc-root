"""VB-AP53-RATE: AutoPilot per-window re-proposal rate -> ClaimTuple.

Pinned:
* fixtures are REAL writer output (fixtures/vb_writers/generate.py);
* the shared ladder grades every tuple (an observation: Judged/Located), no ladder here;
* locator and identity are the window;
* the retrospective backfill projects ZERO rows (spec section 4.7) and is declined, not refused;
* pre-hook windows, edited lines/rows, dropped rates and incoherent counts void the file;
* end to end: the real orchestrator hook writes the file and ``cli.py ingest`` reads it
  (skipped when no orchestrator checkout carrying the writer is available).
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402
import cli  # noqa: E402
from adapters import autopilot_reproposal_rate as adapter  # noqa: E402
from ledger import Ledger  # noqa: E402

FIX = HERE / "fixtures" / "vb_writers"
RATES = FIX / "autopilot_reproposal_rates.jsonl"
RETRO = FIX / "autopilot_reproposal_rates.retrospective.jsonl"
AS_OF = "2026-09-16T09:00:00Z"
SUPPORT = "epyc.vidya/frame/evidence_supports_claim/v1"


def _canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str, allow_nan=False)


def lines(path=RATES):
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]


def write_lines(path: Path, rows, *, rehash=False) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    out = []
    for line in rows:
        if rehash and "line_sha256" in line:
            line = dict(line)
            line.pop("line_sha256")
            line["line_sha256"] = hashlib.sha256(_canon(line).encode()).hexdigest()
        out.append(_canon(line) + "\n")
    path.write_text("".join(out))
    return path


def write_fixture(tmp: Path) -> Path:
    """For test_ingest_sources: a directory holding the prospective and retrospective files."""
    tmp.mkdir(parents=True, exist_ok=True)
    shutil.copy(RATES, tmp / RATES.name)
    shutil.copy(RETRO, tmp / RETRO.name)
    return tmp


def test_fixture_rows_project_and_the_shared_ladder_grades_them():
    rows = adapter.native_rows(RATES)
    assert sorted((r["extra"]["window"]["start"], r["metric"]) for r in rows) == sorted([
        (4, adapter.METRIC_ALL), (4, adapter.METRIC_DIFF_REPEAT), (4, adapter.METRIC_KEYED),
        (8, adapter.METRIC_ALL), (8, adapter.METRIC_KEYED),
    ])
    for native in rows:
        tup = ct.registered()[adapter.PROJECTION_NAME](native)
        q, t, reasons = ct.grade(tup)
        assert (q, t) == ("Judged", "Located")
        assert any("OBSERVATION" in r for r in reasons)
        assert tup.reps == native["extra"]["denominator"]
        assert tup.attestation_locator.endswith(
            f"#window={native['extra']['window']['start']}-"
            f"{native['extra']['window']['end_exclusive']}")
    assert len({r["measurement_id"] for r in rows}) == len(rows)
    diff = next(r for r in rows if r["metric"] == adapter.METRIC_DIFF_REPEAT)
    assert (diff["extra"]["numerator"], diff["extra"]["denominator"]) == (1, 2)
    assert ct.source_classes()[adapter.PROJECTION_NAME] == "measurement"


def test_retrospective_backfill_projects_zero_rows():
    assert adapter.native_rows(RETRO) == ()
    [line] = lines(RETRO)
    assert line["retrospective"] is True and "4.7" in line["no_warrant_reason"]


def test_retrospective_line_with_rows_is_refused(tmp_path):
    [line] = lines(RETRO)
    line["belief_measurements"] = copy.deepcopy(lines()[1]["belief_measurements"])
    with pytest.raises(ct.ProjectionError, match="retrospective"):
        adapter.native_rows(write_lines(tmp_path / "r.jsonl", [line], rehash=True))


def test_pre_hook_window_and_unarmed_file_are_refused(tmp_path):
    armed, w4, w8 = lines()
    early = dict(armed, armed_from_trial=8)
    with pytest.raises(ct.ProjectionError, match="pre-hook"):
        adapter.native_rows(write_lines(tmp_path / "a.jsonl", [early, w4]))
    with pytest.raises(ct.ProjectionError, match="before any armed"):
        adapter.native_rows(write_lines(tmp_path / "b.jsonl", [w4, w8]))


def test_edited_line_or_row_voids_the_file(tmp_path):
    armed, w4, w8 = lines()
    bad = copy.deepcopy(w8)
    bad["counts"]["reproposals"] = 1
    with pytest.raises(ct.ProjectionError, match="line_sha256"):
        adapter.native_rows(write_lines(tmp_path / "a.jsonl", [armed, w4, bad]))
    # A consistently edited row (line re-hashed) still fails the row hash.
    bad = copy.deepcopy(w8)
    bad["belief_measurements"][0]["claim"] = "nothing was ever re-proposed"
    with pytest.raises(ct.ProjectionError, match="row_sha256"):
        rows = adapter.native_rows(write_lines(tmp_path / "b.jsonl", [armed, w4, bad], rehash=True))
        [adapter.project(r) for r in rows]


def test_dropped_rate_and_incoherent_counts_are_refused(tmp_path):
    armed, w4, w8 = lines()
    dropped = copy.deepcopy(w4)
    dropped["belief_measurements"] = [r for r in dropped["belief_measurements"]
                                      if r["metric"] != adapter.METRIC_DIFF_REPEAT]
    with pytest.raises(ct.ProjectionError, match="denominator but no row"):
        adapter.native_rows(write_lines(tmp_path / "a.jsonl", [armed, dropped], rehash=True))
    twice = [armed, w4, w4]
    with pytest.raises(ct.ProjectionError, match="twice"):
        adapter.native_rows(write_lines(tmp_path / "b.jsonl", twice))


def test_projection_refuses_what_the_producer_never_writes():
    native = adapter.native_rows(RATES)[0]
    for field, value, match in (
        ("protocol_id", "P-LOOP-1", "protocol"),
        ("metric_direction", "higher_better", "lower_better"),
        ("value", 0.99, "row_sha256"),
        ("attestation_sha256", "e" * 64, "whole-file"),
    ):
        bad = copy.deepcopy(native)
        bad[field] = value
        with pytest.raises(ct.ProjectionError, match=match):
            adapter.project(bad)


def test_torn_tail_is_skipped_but_a_torn_middle_voids(tmp_path):
    text = RATES.read_text()
    torn = tmp_path / "torn.jsonl"
    torn.write_text(text + '{"schema": "epyc.autopilot.repro')
    assert len(adapter.native_rows(torn)) == 5
    middle = tmp_path / "middle.jsonl"
    middle.write_text('{"schema": "epyc.autopilot.repro\n' + text)
    with pytest.raises(ct.ProjectionError, match="not JSON"):
        adapter.native_rows(middle)


def test_cli_ingest_dir_projects_prospective_and_declines_retrospective(tmp_path, capsys):
    root = write_fixture(tmp_path / "fx")
    ledger = tmp_path / "ledger.jsonl"
    rc = cli.main(["--ledger", str(ledger), "--json", "ingest", "autopilot-reproposal-rate",
                   "--path", str(root), "--as-of", AS_OF])
    assert rc == 0
    report = json.loads(capsys.readouterr().out)
    assert report["rows_projected"] == 5 and report["refused"] == []
    assert report["declined"] == [str(root / RETRO.name)]
    supports = [r.frame for r in Ledger(ledger).read_all() if r.frame["frame_type"] == SUPPORT]
    assert {f["assertion"]["grade"]["Q"] for f in supports} == {"Judged"}


# ── live end to end: the real orchestrator hook -> file -> cli ingest -> tuple ───────────────

def _orchestrator():
    root = Path(os.environ.get("EPYC_ORCHESTRATOR_ROOT", "/mnt/raid0/llm/epyc-orchestrator"))
    py = Path(os.environ.get("EPYC_ORCHESTRATOR_PYTHON",
                             "/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python"))
    if not (root / "scripts" / "autopilot" / "reproposal_rate.py").is_file() or not py.is_file():
        pytest.skip("no orchestrator checkout carrying scripts/autopilot/reproposal_rate.py")
    return root, py


LIVE = r"""
import sys
from pathlib import Path
root, jd = Path(sys.argv[1]), Path(sys.argv[2])
sys.path[:0] = [str(root), str(root / "scripts" / "autopilot")]
import experiment_journal as ej, reproposal_rate as rr
FLAG = {"type": "structural_experiment", "flags": {"x": True}}
def entry(t, **o):
    kw = dict(trial_id=t, timestamp="2026-09-16T00:00:00+00:00", species="s",
              action_type="structural_experiment", tier=1, quality=1.0, speed=1.0, cost=0.0,
              reliability=1.0, pareto_status="dominated", config_snapshot=dict(FLAG))
    kw.update(o)
    return ej.JournalEntry(**kw)
j = ej.ExperimentJournal(jd, segment_snapshots=False)
j.record(entry(0))
rr.record_closed_windows(j, window=3)
for t in range(1, 7):
    j.record(entry(t, failure_analysis="VIOLATIONS:\n - x\n" if t == 3 else ""))
    rr.record_closed_windows(j, window=3)
"""


def test_live_writer_to_cli_ingest_end_to_end(tmp_path, capsys):
    root, py = _orchestrator()
    jd = tmp_path / "journal"
    subprocess.run([str(py), "-c", LIVE, str(root), str(jd)], check=True, timeout=120,
                   capture_output=True)
    path = jd / "autopilot_reproposal_rates.jsonl"
    ledger = tmp_path / "ledger.jsonl"
    rc = cli.main(["--ledger", str(ledger), "--json", "ingest", "autopilot-reproposal-rate",
                   "--path", str(path), "--as-of", AS_OF])
    assert rc == 0
    report = json.loads(capsys.readouterr().out)
    assert report["refused"] == [] and report["rows_projected"] == 2   # window 3..5: all + keyed
    [native] = [r for r in adapter.native_rows(path) if r["metric"] == adapter.METRIC_ALL]
    assert (native["extra"]["numerator"], native["extra"]["denominator"]) == (2, 3)
    tup = adapter.project(native)
    supports = [r.frame for r in Ledger(ledger).read_all() if r.frame["frame_type"] == SUPPORT]
    got = {f["assertion"]["claim_id"]: f["assertion"]["grade"] for f in supports}
    q, t, _ = ct.grade(tup)
    assert got[f"clm_{tup.measurement_id}"] == {"Q": q, "T": t}
