import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "loop_metrics", ROOT / "scripts/handoffs/loop_metrics.py"
)
sys.path.insert(0, str(ROOT / "scripts/handoffs"))
metrics = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(metrics)
DAY = "2026-10-31"


def blob(*rows):
    return b"".join(json.dumps(row).encode() + b"\n" for row in rows)


def ended(rid, reason, rc=1, stamp=DAY + "T12:00:00Z"):
    return {"id": rid, "end_line": f"rc={rc} time={stamp} reason={reason}"}


@pytest.mark.parametrize(
    "reason",
    [
        "t1-admission:DRYRUN_REFUSED",
        "build-missing:source",
        "refused:own-port-123-listening",
        "stop-file-before-start",
        "grant-expired-unrun",
        "window-12s-below-min-20",
    ],
)
def test_entry_reason_has_native_phase_evidence(reason):
    report = metrics.terminal_observations(blob(ended("r", reason)), DAY)
    assert report["confirmed_entry_failures"] == 1
    assert report["value"] is None


def test_rc_alone_never_classifies_entry_failure():
    report = metrics.terminal_observations(
        blob(
            ended("a", "launcher-signalled", 143),
            ended("b", "exited", 75),
            ended("c", "job-rc-75:exited", 75),
            ended("d", "complete", 0),
        ),
        DAY,
    )
    assert report["phase_unknown"] == 2
    assert report["confirmed_job_terminals"] == 2
    assert report["confirmed_entry_failures"] == 0
    assert report["value"] is None


def test_duplicate_terminals_are_not_extra_attempts_and_conflicts_visible():
    a = ended("a", "t1-admission:no")
    report = metrics.terminal_observations(blob(a, a, ended("a", "complete", 0)), DAY)
    assert report["observed_terminal_records"] == 1
    assert report["conflicting_records"] == 1
    assert report["value"] is None


def test_timezone_uses_event_date_not_watcher_seen_at():
    row = ended("a", "complete", 0, "2026-11-01T00:30:00+02:00")
    row["seen_at"] = "2026-11-02T00:00:00Z"
    assert (
        metrics.terminal_observations(blob(row), DAY)["observed_terminal_records"] == 1
    )
    assert (
        metrics.terminal_observations(blob(row), "2026-11-01")[
            "observed_terminal_records"
        ]
        == 0
    )


def test_partial_or_malformed_sources_never_become_zero_rate():
    data = blob(ended("a", "complete", 0)) + b"not-json\n" + b'{"id":"partial"}'
    report = metrics.terminal_observations(data, DAY)
    assert report["malformed_or_partial_records"] == 2
    assert report["confirmed_job_terminals"] == 1
    assert report["value"] is None


def test_idle_alerts_never_turn_gaps_or_two_samples_into_hours():
    a = {
        "kind": "idle",
        "ts": DAY + "T00:00:00Z",
        "regions": "q0 gpu-quiet",
        "checks": 2,
        "interval_s": 120,
    }
    b = dict(a, ts=DAY + "T23:59:00Z")
    report = metrics.idle_observations(blob(a, a, b), DAY)
    assert report["idle_alerts"] == 2
    assert report["region_alerts"] == {"q0": 2, "gpu-quiet": 2}
    assert report["value"] is None


def test_missing_sources_are_unknown_not_healthy_zero(tmp_path):
    report = metrics.report(DAY, None, tmp_path / "absent", tmp_path / "absent2")
    assert all(
        report[key]["value"] is None
        for key in (
            "decision_results",
            "idle_hours",
            "failed_at_entry_rate",
            "operator_messages",
        )
    )
    assert report["sources"]["filing_due"]["status"] == "unknown"


@pytest.mark.parametrize(
    "snapshot",
    [
        b"{",
        b"[]",
        b'{"series":{}}',
        blob(
            {"series": {DAY: {"rows": True, "handoff_ticks": 0, "progress_lines": 0}}}
        ),
    ],
)
def test_invalid_native_snapshot_cannot_fabricate_decision_counts(snapshot):
    assert metrics.decisions(snapshot, DAY)["value"] is None


def test_real_verdict_producer_to_cli_readonly(tmp_path):
    source_root = Path(os.environ.get("LOOP5_SOURCE_ROOT", str(ROOT)))
    producer = source_root / "scripts/handoffs/verdict_count.py"
    repo = tmp_path / "repo"
    active = repo / "handoffs/active"
    active.mkdir(parents=True)
    (repo / "progress/2026-10").mkdir(parents=True)
    (active / "backlog-priority.json").write_text(
        json.dumps(
            {
                "rows": {
                    "INF-99": {
                        "kind": "inference-prep",
                        "score": 1,
                        "basis": "test instrument",
                    }
                }
            }
        )
    )
    (active / "inference-index.md").write_text(
        "| INF-99 | T | [test](case.md) | step | - |\n"
    )
    (active / "case.md").write_text(
        "- [x] INF-99 verdict KEEP " + DAY + " [belief: cc]\n"
    )
    fillers = tmp_path / "FILLERS.md"
    cells = [
        "INF-99-run",
        "owner",
        "launcher",
        "any-cpu-quarter",
        "1",
        "1",
        "STOP",
        "COMPLETE",
        "block-correctness",
        "60",
        "1",
        "n",
        "n",
        "case.md",
        "predeclared adopt/reject",
        "1%",
        "cpu",
        "notes",
    ]
    fillers.write_text("| " + " | ".join(cells) + " |\n")
    grants = tmp_path / "grants"
    grants.mkdir()
    (grants / "INF-99-run.ended").write_text(
        "rc=0 time=" + DAY + "T10:00:00Z reason=complete\n"
    )
    snapshot = tmp_path / "native.json"
    subprocess.run(
        [
            sys.executable,
            str(producer),
            "--repo",
            str(repo),
            "--fillers",
            str(fillers),
            "--grants",
            str(grants),
            "--today",
            DAY,
            "--days",
            "1",
            "--json",
            str(snapshot),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    due, idle = tmp_path / "due.jsonl", tmp_path / "idle.jsonl"
    due.write_bytes(blob(ended("a", "t1-admission:refused")))
    idle.write_bytes(b"")
    watched = [p for p in tmp_path.rglob("*") if p.is_file()]
    before = {str(p): (p.read_bytes(), p.stat().st_mtime_ns) for p in watched}
    done = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/handoffs/loop_metrics.py"),
            "--date",
            DAY,
            "--verdict-snapshot",
            str(snapshot),
            "--filing-due",
            str(due),
            "--keeper-alerts",
            str(idle),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    report = json.loads(done.stdout)
    assert report["decision_results"]["value"] == 1
    assert (
        report["decision_results"]["basis"]
        == "unchanged verdict_count.py native series.rows"
    )
    assert report["failed_at_entry_rate"]["confirmed_entry_failures"] == 1
    assert report["operator_messages"]["value"] is None
    assert {str(p): (p.read_bytes(), p.stat().st_mtime_ns) for p in watched} == before
    assert sorted(str(p) for p in tmp_path.rglob("*") if p.is_file()) == sorted(before)


def test_prospective_partial_stream_does_not_claim_coverage():
    assert metrics.prospective(b'{"partial":true}')["value"] is None


def test_nonregular_or_symlink_metadata_refuses_without_reading(tmp_path):
    target = tmp_path / "target"
    target.write_text("private content must not be read")
    link = tmp_path / "alias"
    link.symlink_to(target)
    raw, meta = metrics.read_source(link)
    assert raw is None and meta["status"] == "unknown"
    fifo = tmp_path / "fifo"
    os.mkfifo(fifo)
    raw, meta = metrics.read_source(fifo)
    assert raw is None and meta["status"] == "unknown"
