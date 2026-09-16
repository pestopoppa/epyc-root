"""SC83: reviewer negative-control false-accept rate -> ClaimTuple.

Pinned:
* fixtures are REAL writer output (fixtures/vb_writers/generate.py);
* the shared ladder grades (observation: Judged/Located); a protocol is refused until RC-6a;
* locator = the scoring run; a run with no scored decoy projects nothing;
* a denominator that dropped decoys, a re-bound stale verdict and edited lines/rows are refused;
* input decay is carried as attestation_present=False, never repaired;
* end to end: the real orchestrator CLI writes the file and ``cli.py ingest reviewer-fa``
  reads it (skipped without an orchestrator checkout carrying the writer).
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402
import cli  # noqa: E402
from adapters import reviewer_false_accept as adapter  # noqa: E402
from ledger import Ledger  # noqa: E402

FIX = HERE / "fixtures" / "vb_writers"
RUNS = FIX / "false_accept_runs.jsonl"
AS_OF = "2026-09-16T09:00:00Z"
SUPPORT = "epyc.vidya/frame/evidence_supports_claim/v1"


def _canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str, allow_nan=False)


def lines():
    return [json.loads(x) for x in RUNS.read_text().splitlines() if x.strip()]


def rehash(line):
    line = dict(line)
    line.pop("line_sha256", None)
    line["line_sha256"] = hashlib.sha256(_canon(line).encode()).hexdigest()
    return line


def write_lines(path: Path, rows) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(_canon(x) + "\n" for x in rows))
    return path


def write_fixture(tmp: Path) -> Path:
    """For test_ingest_sources."""
    return write_lines(tmp / "false_accept_runs.jsonl", lines())


def test_fixture_projects_one_row_for_the_scored_run_only():
    rows = adapter.native_rows(RUNS)
    assert [r["extra"]["run_id"] for r in rows] == ["fixture-r1"]   # r2: every verdict stale
    [native] = rows
    tup = ct.registered()[adapter.PROJECTION_NAME](native)
    assert (tup.value, tup.reps) == (0.5, 2)
    assert tup.attestation_locator.endswith("#run=fixture-r1")
    q, t, reasons = ct.grade(tup)
    assert (q, t) == ("Judged", "Located")
    assert any("OBSERVATION" in r for r in reasons)
    assert native["extra"]["stale"] == ["d2"]
    assert ct.source_classes()[adapter.PROJECTION_NAME] == "measurement"
    r2 = lines()[1]
    assert r2["result"]["rate"] is None and r2["belief_measurements"] == []
    assert list(r2["stale"]) == ["d2"]


def test_denominator_that_dropped_decoys_is_refused(tmp_path):
    r1, r2 = lines()
    bad = copy.deepcopy(r1)
    bad["result"]["unscored"] = []           # d2 silently vanished from the accounting
    with pytest.raises(ct.ProjectionError, match="dropped decoys"):
        adapter.native_rows(write_lines(tmp_path / "a.jsonl", [rehash(bad)]))


def test_rebound_stale_verdict_is_refused(tmp_path):
    r1, _ = lines()
    bad = copy.deepcopy(r1)
    bad["result"]["unscored"] = ["d9"]       # still accounts, but stale d2 is no longer unscored
    with pytest.raises(ct.ProjectionError, match="re-bound"):
        adapter.native_rows(write_lines(tmp_path / "a.jsonl", [rehash(bad)]))


def test_edited_line_or_row_and_duplicate_run_are_refused(tmp_path):
    r1, r2 = lines()
    bad = copy.deepcopy(r1)
    bad["result"]["numerator"] = 0
    with pytest.raises(ct.ProjectionError, match="line_sha256"):
        adapter.native_rows(write_lines(tmp_path / "a.jsonl", [bad]))
    bad = copy.deepcopy(r1)
    bad["belief_measurements"][0]["claim"] = "the reviewer never accepts a decoy"
    rows = adapter.native_rows(write_lines(tmp_path / "b.jsonl", [rehash(bad)]))
    with pytest.raises(ct.ProjectionError, match="row_sha256"):
        adapter.project(rows[0])
    with pytest.raises(ct.ProjectionError, match="twice"):
        adapter.native_rows(write_lines(tmp_path / "c.jsonl", [r1, r1]))
    with pytest.raises(ct.ProjectionError, match="not a"):
        adapter.native_rows(write_lines(tmp_path / "d.jsonl", [{"schema": "other"}]))


def test_projection_refuses_a_protocol_and_projected_objections():
    native = adapter.native_rows(RUNS)[0]
    bad = copy.deepcopy(native)
    bad["protocol_id"] = "RC-6a"
    with pytest.raises(ct.ProjectionError, match="RC-6a"):
        adapter.project(bad)
    bad = copy.deepcopy(native)
    bad["reps"] = 5
    with pytest.raises(ct.ProjectionError, match="row_sha256"):
        adapter.project(bad)


def test_input_decay_is_carried_not_repaired(tmp_path):
    r1, _ = lines()
    corpus = tmp_path / "corpus.jsonl"
    corpus.write_text("edited after scoring\n")
    moved = copy.deepcopy(r1)
    moved["inputs"]["corpus"]["path"] = str(corpus)
    [native] = adapter.native_rows(write_lines(tmp_path / "a.jsonl", [rehash(moved)]))
    assert native["attestation_present"] is False
    tup = adapter.project(native)                 # reader key is outside the writer's row hash
    assert tup.attestation_present is False
    [fresh] = adapter.native_rows(RUNS)           # recorded inputs no longer on disk: not asserted
    assert "attestation_present" not in fresh


def test_cli_ingest_fixture(tmp_path, capsys):
    path = write_fixture(tmp_path / "fx")
    ledger = tmp_path / "ledger.jsonl"
    rc = cli.main(["--ledger", str(ledger), "--json", "ingest", "reviewer-fa",
                   "--path", str(path), "--as-of", AS_OF])
    assert rc == 0
    report = json.loads(capsys.readouterr().out)
    assert report["rows_projected"] == 1 and report["frames_emitted"] == 3
    assert report["refused"] == [] and report["declined"] == []


def test_cli_ingest_run_file_with_no_scored_run_is_declined(tmp_path, capsys):
    _, r2 = lines()
    path = write_lines(tmp_path / "false_accept_runs.jsonl", [r2])
    rc = cli.main(["--ledger", str(tmp_path / "l.jsonl"), "--json", "ingest", "reviewer-fa",
                   "--path", str(path), "--as-of", AS_OF])
    assert rc == 0
    report = json.loads(capsys.readouterr().out)
    assert report["rows_projected"] == 0 and report["declined"] == [str(path)]


# ── live end to end: the real orchestrator CLI -> file -> cli ingest -> tuple ────────────────

def _orchestrator():
    root = Path(os.environ.get("EPYC_ORCHESTRATOR_ROOT", "/mnt/raid0/llm/epyc-orchestrator"))
    py = Path(os.environ.get("EPYC_ORCHESTRATOR_PYTHON",
                             "/mnt/raid0/llm/epyc-orchestrator/.venv/bin/python"))
    if not (root / "scripts" / "review" / "score_false_accept.py").is_file() or not py.is_file():
        pytest.skip("no orchestrator checkout carrying scripts/review/score_false_accept.py")
    return root, py


def test_live_writer_to_cli_ingest_end_to_end(tmp_path, capsys):
    root, py = _orchestrator()
    gen = FIX / "generate.py"
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    prep = (
        "import sys, runpy; from pathlib import Path\n"
        f"g = runpy.run_path({str(gen)!r}, run_name='fixture_helpers')\n"
        "stale = g['_binding']('d2', source_version='v0', source_hash=g['rev'].content_hash('old'))\n"
        "g['write_fa_inputs'](Path(sys.argv[1]), [g['_verdict']('d0', True), "
        "g['_verdict']('d1', True), g['_verdict']('d2', False, stale)])\n"
    )
    env = dict(os.environ, EPYC_ORCHESTRATOR_ROOT=str(root))
    subprocess.run([str(py), "-c", prep, str(inputs)], check=True, timeout=120, env=env,
                   capture_output=True)
    out = tmp_path / "false_accept_runs.jsonl"
    subprocess.run([str(py), str(root / "scripts" / "review" / "score_false_accept.py"),
                    "--corpus", str(inputs / "corpus.jsonl"),
                    "--verdicts", str(inputs / "verdicts.jsonl"),
                    "--current-bindings", str(inputs / "bindings.json"),
                    "--run-id", "live-1", "--out", str(out)],
                   check=True, timeout=120, capture_output=True, cwd=root)
    ledger = tmp_path / "ledger.jsonl"
    rc = cli.main(["--ledger", str(ledger), "--json", "ingest", "reviewer-fa",
                   "--path", str(out), "--as-of", AS_OF])
    assert rc == 0
    report = json.loads(capsys.readouterr().out)
    assert report["refused"] == [] and report["rows_projected"] == 1
    [native] = adapter.native_rows(out)
    assert (native["extra"]["numerator"], native["extra"]["denominator"]) == (2, 2)
    assert "attestation_present" not in native          # live inputs still match
    tup = adapter.project(native)
    q, t, _ = ct.grade(tup)
    supports = [r.frame for r in Ledger(ledger).read_all() if r.frame["frame_type"] == SUPPORT]
    assert supports[0]["assertion"]["grade"] == {"Q": q, "T": t}
    assert supports[0]["assertion"]["claim_id"] == f"clm_{tup.measurement_id}"
    (inputs / "corpus.jsonl").write_text("changed\n")    # decay after scoring
    assert adapter.native_rows(out)[0]["attestation_present"] is False
