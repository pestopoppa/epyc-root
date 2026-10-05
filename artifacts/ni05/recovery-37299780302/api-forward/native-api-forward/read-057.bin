"""Tests for AutoPilot archive-authority state repair."""

from __future__ import annotations

import contextlib
import json
import os
from pathlib import Path
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "autopilot"))

import archive_authority_repair  # noqa: E402
from archive_authority_repair import (  # noqa: E402
    build_repaired_state,
    main,
    repair_state_file,
)
from src.autopilot_core.journal_reconstruction import (  # noqa: E402
    reconstruct_archive_from_journal_rows,
)


def _row(trial_id: int, *, quality: float = 1.0) -> dict[str, Any]:
    return {
        "trial_id": trial_id,
        "timestamp": f"2026-06-14T00:00:0{trial_id}Z",
        "species": "unit",
        "action_type": "seed_batch",
        "tier": 1,
        "quality": quality,
        "speed": 40.0,
        "cost": 0.2,
        "reliability": 0.9,
        "pareto_status": "frontier",
    }


def _row_at(trial_id: int, timestamp: str, *, quality: float = 1.0) -> dict[str, Any]:
    row = _row(trial_id, quality=quality)
    row["timestamp"] = timestamp
    return row


def _archive(rows: list[dict[str, Any]]) -> dict[str, Any]:
    archive = reconstruct_archive_from_journal_rows(rows, None, current_run_only=False)
    assert archive is not None
    return archive


def _write_state_and_journal(
    tmp_path: Path,
    *,
    state_rows: list[dict[str, Any]],
    journal_rows: list[dict[str, Any]],
) -> tuple[Path, Path]:
    state_path = tmp_path / "autopilot_state.json"
    journal_path = tmp_path / "autopilot_journal.jsonl"
    state_path.write_text(
        json.dumps({"trial_counter": 3, "pareto_archive": _archive(state_rows)}),
        encoding="utf-8",
    )
    journal_path.write_text(
        "\n".join(json.dumps(row) for row in journal_rows) + "\n",
        encoding="utf-8",
    )
    return state_path, journal_path


def test_build_repaired_state_removes_only_archive_cache() -> None:
    state = {
        "trial_counter": 3,
        "paused": True,
        "pareto_archive": _archive([_row(1)]),
    }
    rows = [_row(1), _row(2)]

    repaired, result = build_repaired_state(state, rows)

    assert result.status == "ready"
    assert result.before["ok"] is False
    assert result.after is not None
    assert result.after["ok"] is True
    assert repaired["trial_counter"] == 3
    assert repaired["paused"] is True
    assert "pareto_archive" not in repaired


def test_build_repaired_state_uses_epoch_exclusion() -> None:
    rows = [
        _row_at(1, "2026-06-14T00:00:01Z", quality=2.0),
        _row_at(2, "2026-06-15T00:00:01Z", quality=1.2),
    ]
    state = {
        "trial_counter": 3,
        "pareto_archive": _archive([rows[0]]),
        "pareto_exclude_before_ts": 1781481600.0,
    }

    repaired, result = build_repaired_state(state, rows)

    assert result.status == "ready"
    assert result.after is not None
    assert result.after["ok"] is True
    assert result.after["diagnostic"]["journal_entry_count"] == 1
    assert "pareto_archive" not in repaired


def test_repair_state_file_dry_run_does_not_write(tmp_path: Path) -> None:
    state_path, journal_path = _write_state_and_journal(
        tmp_path,
        state_rows=[_row(1)],
        journal_rows=[_row(1), _row(2)],
    )
    original = state_path.read_text(encoding="utf-8")

    result = repair_state_file(state_path, journal_path)

    assert result.status == "ready"
    assert state_path.read_text(encoding="utf-8") == original
    assert list(tmp_path.glob("*.bak-archive-repair-*")) == []


def test_repair_state_file_write_creates_backup_and_aligns(tmp_path: Path) -> None:
    state_path, journal_path = _write_state_and_journal(
        tmp_path,
        state_rows=[_row(1)],
        journal_rows=[_row(1), _row(2)],
    )

    result = repair_state_file(
        state_path,
        journal_path,
        write=True,
        expect_trial_counter=3,
    )
    loaded = json.loads(state_path.read_text(encoding="utf-8"))

    assert result.status == "written"
    assert result.after is not None
    assert result.after["ok"] is True
    assert result.backup_path
    assert Path(result.backup_path).exists()
    assert "pareto_archive" not in loaded


def test_repair_state_file_refuses_trial_counter_mismatch(tmp_path: Path) -> None:
    state_path, journal_path = _write_state_and_journal(
        tmp_path,
        state_rows=[_row(1)],
        journal_rows=[_row(1), _row(2)],
    )

    result = repair_state_file(
        state_path,
        journal_path,
        write=True,
        expect_trial_counter=99,
    )

    assert result.status == "trial_counter_mismatch"
    assert "expected trial_counter 99" in result.warning
    assert list(tmp_path.glob("*.bak-archive-repair-*")) == []


def test_repair_state_file_write_takes_state_lock(tmp_path: Path, monkeypatch) -> None:
    """H4: the archiver holds the cross-process write lock across its whole
    read->build->write when actually writing; dry-run inspection takes no lock."""
    state_path, journal_path = _write_state_and_journal(
        tmp_path,
        state_rows=[_row(1)],
        journal_rows=[_row(1), _row(2)],
    )

    acquisitions: list[Path] = []
    real = archive_authority_repair.state_write_lock

    @contextlib.contextmanager
    def spy(path, *args, **kwargs):
        acquisitions.append(Path(os.fspath(path)))
        with real(path, *args, **kwargs) as held:
            yield held

    monkeypatch.setattr(archive_authority_repair, "state_write_lock", spy)

    # Dry-run: no lock.
    repair_state_file(state_path, journal_path)
    assert acquisitions == []

    # Write: the read-modify-write is bracketed by exactly one lock acquisition.
    result = repair_state_file(state_path, journal_path, write=True, expect_trial_counter=3)
    assert result.status == "written"
    assert acquisitions == [state_path]


def test_cli_write_returns_zero_on_repair(tmp_path: Path) -> None:
    state_path, journal_path = _write_state_and_journal(
        tmp_path,
        state_rows=[_row(1)],
        journal_rows=[_row(1), _row(2)],
    )

    rc = main(
        [
            "--state",
            str(state_path),
            "--journal",
            str(journal_path),
            "--write",
            "--expect-trial-counter",
            "3",
        ]
    )

    assert rc == 0
