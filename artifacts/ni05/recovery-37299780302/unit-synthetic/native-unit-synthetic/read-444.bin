"""A5: journal_snapshot_create --append refuses to write while autopilot runs.

--append embeds a point-in-time journal view and writes a large ledger event to
the LIVE shard, so it must refuse when autopilot may be appending trials —
unless --force-while-autopilot-alive is passed. The guard is exercised by
monkeypatching _autopilot_running_pids. All fixtures use tmp_path.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "autopilot"))

import journal_snapshot_create as jsc  # noqa: E402
from experiment_journal import ExperimentJournal, JournalEntry  # noqa: E402


def _entry(trial_id: int) -> JournalEntry:
    return JournalEntry(
        trial_id=trial_id,
        timestamp=f"2026-06-14T00:00:0{trial_id}Z",
        species="unit",
        action_type="seed_batch",
        tier=1,
        quality=1.0,
        speed=40.0,
        cost=0.2,
        reliability=0.9,
        pareto_status="frontier",
    )


def _seed_journal(tmp_path: Path) -> None:
    ExperimentJournal(journal_dir=tmp_path).record(_entry(1))


def _argv(journal_dir: Path, *extra: str) -> list[str]:
    return [
        "journal_snapshot_create.py",
        "--journal-dir",
        str(journal_dir),
        "--append",
        *extra,
    ]


def test_append_refuses_while_autopilot_alive(tmp_path, monkeypatch) -> None:
    _seed_journal(tmp_path)
    monkeypatch.setattr(jsc, "_autopilot_running_pids", lambda: [12345])
    monkeypatch.setattr(sys, "argv", _argv(tmp_path))

    assert jsc.main() == 3

    # Guard fired before the append: no snapshot event was written.
    reloaded = ExperimentJournal(journal_dir=tmp_path)
    assert reloaded.journal_snapshot_events() == []


def test_force_flag_bypasses_the_live_guard(tmp_path, monkeypatch) -> None:
    _seed_journal(tmp_path)
    monkeypatch.setattr(jsc, "_autopilot_running_pids", lambda: [12345])
    monkeypatch.setattr(sys, "argv", _argv(tmp_path, "--force-while-autopilot-alive"))

    rc = jsc.main()

    # The guard is bypassed: rc is NOT the guard's 3. With a single valid trial
    # the snapshot builds and appends, so an event lands too.
    assert rc != 3
    reloaded = ExperimentJournal(journal_dir=tmp_path)
    assert len(reloaded.journal_snapshot_events()) == 1


def test_append_proceeds_when_no_live_pids(tmp_path, monkeypatch) -> None:
    _seed_journal(tmp_path)
    monkeypatch.setattr(jsc, "_autopilot_running_pids", lambda: [])
    monkeypatch.setattr(sys, "argv", _argv(tmp_path))

    rc = jsc.main()

    assert rc != 3
    reloaded = ExperimentJournal(journal_dir=tmp_path)
    assert len(reloaded.journal_snapshot_events()) == 1
