"""Tests for Internal Interaction bake counter reporting."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from scripts.analysis import internal_interaction_bake_report as report_mod


def _write_progress(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _completed(ts: str, *, lookups: int, hits: int, misses: int) -> dict:
    return {
        "event_type": "task_completed",
        "task_id": f"task-{ts}",
        "timestamp": ts,
        "data": {
            "delegation_cache_lookups": lookups,
            "delegation_cache_hits": hits,
            "delegation_cache_misses": misses,
            "delegation_cache_hit_rate": hits / lookups if lookups else None,
        },
    }


def _contention(ts: str) -> dict:
    return {
        "event_type": "routing_fallback",
        "task_id": f"contended-{ts}",
        "timestamp": ts,
        "data": {"kind": "contention_denied", "retry_after_s": 5},
    }


def test_build_report_accepts_clean_observable_window(tmp_path: Path) -> None:
    _write_progress(
        tmp_path / "2026-07-03.jsonl",
        [
            _completed("2026-07-03T00:05:00+00:00", lookups=10, hits=9, misses=1),
            _completed("2026-07-03T01:05:00+00:00", lookups=10, hits=10, misses=0),
        ],
    )

    report = report_mod.build_report(
        progress_dir=tmp_path,
        since=datetime(2026, 7, 3, 0, 0, tzinfo=timezone.utc),
        until=datetime(2026, 7, 3, 2, 0, tzinfo=timezone.utc),
        min_hours=2,
        min_delegation_lookups=1,
    )

    assert report["gate_ready"] is True
    assert report["blockers"] == []
    assert report["full_window"]["delegation_cache_lookups"] == 20
    assert report["full_window"]["delegation_cache_misses"] == 1
    assert report["rise_checks"]["delegation_cache_miss_rate_rose"] is False


def test_build_report_blocks_on_second_half_rate_rise(tmp_path: Path) -> None:
    _write_progress(
        tmp_path / "2026-07-03.jsonl",
        [
            _completed("2026-07-03T00:05:00+00:00", lookups=10, hits=10, misses=0),
            _completed("2026-07-03T01:05:00+00:00", lookups=10, hits=5, misses=5),
            _contention("2026-07-03T01:10:00+00:00"),
        ],
    )

    report = report_mod.build_report(
        progress_dir=tmp_path,
        since=datetime(2026, 7, 3, 0, 0, tzinfo=timezone.utc),
        until=datetime(2026, 7, 3, 2, 0, tzinfo=timezone.utc),
        min_hours=2,
        min_delegation_lookups=1,
    )

    assert report["gate_ready"] is False
    assert report["rise_checks"]["delegation_cache_miss_rate_rose"] is True
    assert report["rise_checks"]["contention_denied_rate_rose"] is True
    assert any(b.startswith("delegation_cache_miss_rate_rose") for b in report["blockers"])
    assert any(b.startswith("contention_denied_rate_rose") for b in report["blockers"])
    assert "contention denied per hour" in report_mod.render_markdown(report)


def test_main_strict_returns_nonzero_when_window_is_blocked(tmp_path: Path) -> None:
    _write_progress(
        tmp_path / "2026-07-03.jsonl",
        [_completed("2026-07-03T00:05:00+00:00", lookups=1, hits=1, misses=0)],
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/analysis/internal_interaction_bake_report.py",
            "--progress-dir",
            str(tmp_path),
            "--since",
            "2026-07-03T00:00:00Z",
            "--until",
            "2026-07-03T01:00:00Z",
            "--min-hours",
            "2",
            "--strict",
            "--json",
        ],
        cwd=Path(__file__).resolve().parents[2],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert "window_too_short" in result.stdout
