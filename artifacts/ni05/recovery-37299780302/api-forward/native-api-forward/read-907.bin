"""VB-AP53-RATE: per-window re-proposal rate rows (write side).

Pins: the fold equals the planner fold; the first call arms and writes no window;
closed windows are written once, with stated denominators and self-hashes; a zero
denominator writes no row; backfill writes RETROSPECTIVE lines with zero belief rows
and never touches the prospective file; the hook never raises and never changes
the journal; the autopilot trial path calls the hook.
"""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "autopilot"))

rr = importlib.import_module("reproposal_rate")
rml = importlib.import_module("rejected_mutation_ledger")
ej = importlib.import_module("experiment_journal")

FLAG = {"type": "structural_experiment", "flags": {"user_modeling": True}, "description": "a"}
OTHER = {"type": "prompt_mutation", "target": "p.md", "description": "b"}
FAIL = "VIOLATIONS:\n  - Quality floor violation: 0.360 < 1.0 (tier 1)\n"


def _row(tid, action, **over):
    base = dict(
        trial_id=tid, config_snapshot=dict(action), failure_analysis="",
        deficiency_category="", outcome_status="ok", pareto_status="dominated",
        bug_corrupted_by="", keep_revert_decision="", eval_details={},
    )
    base.update(over)
    return SimpleNamespace(**base)


def _entry(tid, action, **over):
    kw = dict(trial_id=tid, timestamp=f"2026-09-16T00:{tid // 60:02d}:{tid % 60:02d}+00:00",
              species="test", action_type=action.get("type", ""), tier=1, quality=1.0,
              speed=1.0, cost=0.0, reliability=1.0, pareto_status="dominated",
              config_snapshot=dict(action))
    kw.update(over)
    return ej.JournalEntry(**kw)


def _history():
    return [
        _row(0, FLAG, failure_analysis=FAIL),              # rejects FLAG
        _row(1, FLAG),                                     # re-proposal (standing)
        _row(2, {"type": "seed_batch"}),                   # unkeyed
        _row(3, OTHER, outcome_status="invalid"),          # rejects OTHER
        _row(4, dict(OTHER, description="reworded")),      # re-proposal (narrative dropped)
        _row(5, FLAG, pareto_status="frontier"),           # re-proposal, then clears FLAG
        _row(6, FLAG),                                     # not a re-proposal
        _row(7, {"type": "numeric_trial", "params": {"a": 1}}),  # unkeyed
    ]


def test_fold_counts_and_matches_the_planner_fold():
    fold = rr.fold_windows(_history(), window=4)
    w0, w1 = fold["windows"][0], fold["windows"][4]
    assert (w0["all_trials"], w0["keyed_trials"], w0["reproposals"]) == (4, 3, 1)
    assert (w1["all_trials"], w1["keyed_trials"], w1["reproposals"]) == (4, 3, 2)
    assert w1["reproposals_by_action_type"] == {"prompt_mutation": 1, "structural_experiment": 1}
    assert w1["reproposals_by_standing_class"] == {"invalid": 1, "safety_gate": 1}
    planner = {r["config_fingerprint"]: r["last_reason"]
               for r in rml.rejected_configs_from_entries(_history())}
    assert fold["standing"] == planner


def test_ledger_window_counts_repeat_diffs_across_windows():
    recs = [{"trial_id": 1, "diff_sha256": "a", "rejecting_gate": "safety"},
            {"trial_id": 5, "diff_sha256": "a", "rejecting_gate": "safety"},
            {"trial_id": 6, "diff_sha256": "b", "rejecting_gate": "syntax"}]
    assert rr.ledger_window_counts(recs, 4, 8) == {
        "records": 2, "diff_repeats": 1, "by_rejecting_gate": {"safety": 1, "syntax": 1}}


def _journal(tmp_path, n, per_trial=None):
    per_trial = per_trial or {}
    j = ej.ExperimentJournal(tmp_path, segment_snapshots=False)
    for tid in range(n):
        action = FLAG if tid % 2 == 0 else OTHER
        over = per_trial.get(tid, {})
        j.record(_entry(tid, action, **over))
    return j


def test_first_call_arms_and_writes_no_window(tmp_path):
    j = _journal(tmp_path, 3)
    assert rr.record_closed_windows(j, window=4) == []
    lines = rr.read_lines(rr.rate_path(tmp_path))
    assert [(l["record"], l["armed_from_trial"]) for l in lines] == [("armed", 4)]


def test_closed_windows_are_written_once_with_stated_denominators(tmp_path):
    j = _journal(tmp_path, 1)
    rr.record_closed_windows(j, window=4)          # arms at 4 (trial 0 was pre-hook)
    fail = {"failure_analysis": FAIL}
    for tid in range(1, 12):
        over = fail if tid == 4 else {}
        j.record(_entry(tid, FLAG if tid % 2 == 0 else OTHER, **over))
        rr.record_closed_windows(j, window=4)
    lines = [l for l in rr.read_lines(rr.rate_path(tmp_path)) if l["record"] == "window"]
    assert [l["window"]["start"] for l in lines] == [4, 8]
    assert rr.record_closed_windows(j, window=4) == []   # idempotent
    w8 = lines[1]
    assert w8["retrospective"] is False and w8["armed_from_trial"] == 4
    assert w8["counts"]["reproposals"] == 2          # trials 8 and 10 re-propose FLAG
    rows = {r["metric"]: r for r in w8["belief_measurements"]}
    assert set(rows) == {rr.METRIC_ALL, rr.METRIC_KEYED}   # no ledger records -> no diff row
    row = rows[rr.METRIC_ALL]
    assert row["value"] == 2 / 4 and row["reps"] == 4 == row["extra"]["denominator"]
    assert row["extra"]["numerator"] == 2 and row["protocol_id"] == ""
    assert row["metric_direction"] == "lower_better"
    assert row["extra"]["row_sha256"] == rr.row_digest(row)
    assert row["extra"]["definition_sha256"] == rr.definition_sha256()
    shards = w8["sources"]["journal_shards"]
    assert shards and all(len(s["prefix_sha256"]) == 64 for s in shards)
    body = dict(w8)
    digest = body.pop("line_sha256")
    assert digest == rr._sha(rr._canon(body))
    assert not list(tmp_path.glob("*.rewound-*"))   # append-only growth never rotates


def test_ledger_records_add_the_diff_repeat_rate(tmp_path):
    j = _journal(tmp_path, 1)
    rr.record_closed_windows(j, window=4)
    for tid in (5, 6):
        rml.append_record(tmp_path, rml.build_record(
            target="p.md", mutation_type="m", artifact_kind="prompt",
            rejecting_gate="safety", diff_text="same diff", trial_id=tid))
    for tid in range(1, 8):
        j.record(_entry(tid, OTHER))
    assert rr.record_closed_windows(j, window=4) == [4]
    line = [l for l in rr.read_lines(rr.rate_path(tmp_path)) if l["record"] == "window"][0]
    row = {r["metric"]: r for r in line["belief_measurements"]}[rr.METRIC_DIFF_REPEAT]
    assert (row["extra"]["numerator"], row["extra"]["denominator"]) == (1, 2)


def test_zero_keyed_window_writes_no_keyed_row(tmp_path):
    j = ej.ExperimentJournal(tmp_path, segment_snapshots=False)
    rr.record_closed_windows(j, window=2)            # empty journal arms at 0
    for tid in range(2):
        j.record(_entry(tid, {"type": "seed_batch"}))
    assert rr.record_closed_windows(j, window=2) == [0]
    line = [l for l in rr.read_lines(rr.rate_path(tmp_path)) if l["record"] == "window"][0]
    assert [r["metric"] for r in line["belief_measurements"]] == [rr.METRIC_ALL]


def test_hook_never_raises_and_never_touches_the_journal(tmp_path, monkeypatch):
    j = _journal(tmp_path, 3)
    before = sorted((p.name, p.read_bytes()) for p in tmp_path.glob("autopilot_journal*"))

    def boom(*a, **k):
        raise OSError("disk full")

    monkeypatch.setattr(rr, "_append", boom)
    assert rr.record_closed_windows(j, window=2) == []
    assert rr.record_closed_windows(SimpleNamespace(), window=2) == []
    assert sorted((p.name, p.read_bytes()) for p in tmp_path.glob("autopilot_journal*")) == before


def test_env_switch_disables_the_hook(tmp_path, monkeypatch):
    j = _journal(tmp_path, 3)
    monkeypatch.setenv(rr.ENV_DISABLE, "0")
    assert rr.record_closed_windows(j, window=2) == []
    assert not rr.rate_path(tmp_path).exists()


def test_backfill_is_retrospective_with_zero_belief_rows(tmp_path):
    _journal(tmp_path, 9, {0: {"failure_analysis": FAIL}})
    out = tmp_path / rr.RETROSPECTIVE_FILENAME
    report = rr.backfill(tmp_path, out, window=4)
    assert report["retrospective_lines"] == 2 and report["belief_rows"] == 0
    assert report["totals"] == {"all_trials": 8, "keyed_trials": 8, "reproposals": 3}
    lines = rr.read_lines(out)
    assert all(l["retrospective"] is True and l["record"] == "retrospective_window"
               and l["belief_measurements"] == [] and "4.7" in l["no_warrant_reason"]
               for l in lines)
    assert not rr.rate_path(tmp_path).exists()
    with pytest.raises(FileExistsError):
        rr.backfill(tmp_path, out, window=4)
    with pytest.raises(ValueError):
        rr.backfill(tmp_path, tmp_path / "x" / rr.RATE_FILENAME, window=4)


def test_backfill_stops_at_the_armed_boundary(tmp_path):
    j = _journal(tmp_path, 5)
    rr.record_closed_windows(j, window=2)            # max trial 4 -> armed_from 6
    for tid in range(5, 10):
        j.record(_entry(tid, FLAG))
    report = rr.backfill(tmp_path, tmp_path / "retro.jsonl", window=2)
    assert report["windows_before_trial"] == 6 and report["retrospective_lines"] == 3


def test_autopilot_trial_paths_call_the_hook():
    src = (ROOT / "scripts" / "autopilot" / "autopilot.py").read_text()
    assert src.count("_record_reproposal_rate_windows(journal)") == 2
    autopilot = importlib.import_module("autopilot")

    class Broken:
        journal_dir = None

        def all_entries(self):
            raise RuntimeError("boom")

    assert autopilot._record_reproposal_rate_windows(Broken()) is None


def test_cli_backfill(tmp_path, capsys):
    _journal(tmp_path, 4)
    out = tmp_path / "retro.jsonl"
    assert rr.main(["backfill", "--journal-dir", str(tmp_path), "--out", str(out),
                    "--window", "2"]) == 0
    assert json.loads(capsys.readouterr().out)["belief_rows"] == 0


def test_journal_rewind_rotates_the_rate_file_and_rearms(tmp_path, caplog):
    j = _journal(tmp_path, 1)
    rr.record_closed_windows(j, window=4)                 # arms at 4
    for tid in range(1, 10):
        j.record(_entry(tid, FLAG))
        rr.record_closed_windows(j, window=4)
    path = rr.rate_path(tmp_path)
    assert [l["window"]["start"] for l in rr.read_lines(path) if l["record"] == "window"] == [4]

    # Rewind: keep trials 0-2 only, then re-run ids 3.. with different content.
    shard = tmp_path / "autopilot_journal.jsonl"
    shard.write_text("".join(shard.read_text().splitlines(keepends=True)[:3]))
    rr._PREFIX_MEMO.clear()
    j2 = ej.ExperimentJournal(tmp_path, segment_snapshots=False)
    j2.record(_entry(3, OTHER))
    with caplog.at_level("WARNING", logger="autopilot"):
        assert rr.record_closed_windows(j2, window=4) == []
    [rotated] = list(tmp_path.glob(rr.RATE_FILENAME + ".rewound-*"))
    assert [l["window"]["start"] for l in rr.read_lines(rotated) if l["record"] == "window"] == [4]
    assert "rotated" in caplog.text
    fresh = rr.read_lines(path)
    assert [(l["record"], l["armed_from_trial"]) for l in fresh] == [("armed", 4)]

    for tid in range(4, 8):
        j2.record(_entry(tid, OTHER))
        rr.record_closed_windows(j2, window=4)
    windows = [l for l in rr.read_lines(path) if l["record"] == "window"]
    assert [w["window"]["start"] for w in windows] == [4]    # the re-run window is written
    old = [l for l in rr.read_lines(rotated) if l["record"] == "window"][0]
    assert windows[0]["counts"]["fold_sha256"] != old["counts"]["fold_sha256"]   # new trials
    assert len(list(tmp_path.glob(rr.RATE_FILENAME + ".rewound-*"))) == 1


def test_in_place_prefix_edit_is_detected_despite_the_memo(tmp_path):
    j = _journal(tmp_path, 1)
    rr.record_closed_windows(j, window=2)
    for tid in range(1, 4):
        j.record(_entry(tid, FLAG))
        rr.record_closed_windows(j, window=2)
    lines = rr.read_lines(rr.rate_path(tmp_path))
    assert rr.journal_mismatch(lines) == ""
    shard = tmp_path / "autopilot_journal.jsonl"
    data = bytearray(shard.read_bytes())
    data[10:11] = b"X" if data[10:11] != b"X" else b"Y"
    shard.write_bytes(bytes(data))       # same size, same inode, changed prefix
    rr._PREFIX_MEMO.clear()
    assert "prefix changed" in rr.journal_mismatch(lines)
