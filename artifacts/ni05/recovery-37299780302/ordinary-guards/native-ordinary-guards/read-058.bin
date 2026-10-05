"""Tests for the read-only AutoPilot archive authority report."""

from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "autopilot"))

from archive_authority_report import (  # noqa: E402
    build_archive_authority_report,
    main,
    render_markdown,
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


def _empty_frontier_state() -> dict[str, Any]:
    boundary = 1781481600.0
    return {
        "trial_counter": 2,
        "pareto_objective_policy": "legacy_4d_v1",
        "eval_execution_instrument_id": "resource-lanes-test",
        "eval_scoring_schedule_id": "judge-tail-test",
        "pareto_epoch_ts": boundary,
        "pareto_exclude_before_ts": boundary,
        "quality_exclude_before_ts": boundary,
        "_allow_empty_frontier_rebase": True,
        "_allow_empty_frontier_rebase_note": "Operator-ratified test boundary.",
        "eval_instrument_empty_frontier_bootstrap": {
            "status": "pending",
            "opened_at": "2026-06-15T00:00:00Z",
            "objective_policy": "legacy_4d_v1",
            "execution_instrument_id": "resource-lanes-test",
            "scoring_schedule_id": "judge-tail-test",
            "completion_condition": "first post-boundary Pareto point",
        },
    }


def test_report_marks_aligned_archive_ok() -> None:
    rows = [_row(1, quality=1.2)]
    report = build_archive_authority_report(
        {"trial_counter": 2, "pareto_archive": _archive(rows)},
        rows,
    )

    assert report["ok"] is True
    assert report["state_archive_present"] is True
    assert report["diagnostic"]["status"] == "match"
    assert report["entry_id_delta"]["state_only_count"] == 0
    assert report["entry_id_delta"]["journal_only_count"] == 0
    assert report["frontier_id_delta"]["state_only_count"] == 0
    assert report["frontier_id_delta"]["journal_only_count"] == 0
    assert report["entry_mismatches"]["count"] == 0


def test_report_accepts_absent_state_cache_as_journal_authoritative() -> None:
    rows = [_row(1, quality=1.2)]
    report = build_archive_authority_report({"trial_counter": 2}, rows)

    assert report["ok"] is True
    assert report["state_archive_present"] is False
    assert report["diagnostic"]["status"] == "match"
    assert report["entry_id_delta"]["journal_only_count"] == 0
    rendered = render_markdown(report)
    assert "- State archive cache: absent (journal-authoritative)" in rendered


def test_report_replays_with_state_epoch_exclusion() -> None:
    rows = [
        _row_at(1, "2026-06-14T00:00:01Z", quality=2.0),
        _row_at(2, "2026-06-15T00:00:01Z", quality=1.2),
    ]
    report = build_archive_authority_report(
        {
            "trial_counter": 3,
            "pareto_exclude_before_ts": 1781481600.0,
        },
        rows,
    )

    assert report["ok"] is True
    assert report["diagnostic"]["journal_entry_count"] == 1
    assert report["diagnostic"]["journal_frontier_count"] == 1
    assert report["diagnostic"]["replay_kwargs"] == {
        "exclude_before_ts": 1781481600.0
    }


def test_report_accepts_ratified_empty_current_era() -> None:
    rows = [_row_at(1, "2026-06-14T00:00:01Z")]

    report = build_archive_authority_report(_empty_frontier_state(), rows)

    assert report["ok"] is True
    assert report["state_archive_present"] is False
    assert report["diagnostic"]["status"] == "match"
    assert report["diagnostic"]["authority_mode"] == "authorized_empty_current_era"
    assert report["diagnostic"]["empty_frontier_bootstrap"]["authorized"] is True


def test_report_summarizes_id_and_value_drift() -> None:
    rows = [_row(1, quality=1.2), _row(2, quality=1.1)]
    archive = json.loads(json.dumps(_archive([rows[0], _row(3, quality=1.3)])))
    archive["all_entries"][0]["objectives"][0] = 0.5
    report = build_archive_authority_report(
        {"trial_counter": 4, "pareto_archive": archive},
        rows,
        max_examples=5,
    )

    assert report["ok"] is False
    assert report["diagnostic"]["status"] == "drift"
    assert report["entry_id_delta"]["state_only_examples"] == [3]
    assert report["entry_id_delta"]["journal_only_examples"] == [2]
    assert report["entry_mismatches"]["count"] == 1
    assert report["entry_mismatches"]["examples"][0]["trial_id"] == 1
    rendered = render_markdown(report)
    assert "State-only entries: 1 [3]" in rendered
    assert "Journal-only entries: 1 [2]" in rendered


def test_markdown_renders_structured_report_core_fields() -> None:
    rows = [_row(1, quality=1.2)]
    report = build_archive_authority_report(
        {"trial_counter": 2, "pareto_archive": _archive(rows)},
        rows,
    )

    rendered = render_markdown(report)

    assert f"- Status: {report['diagnostic']['status']}" in rendered
    assert f"- Recommendation: {report['recommendation']}" in rendered
    assert (
        "- State/journal trial bounds: "
        f"state_trial_counter={report['state_trial_counter']}, "
        f"journal_max_trial_id={report['journal_max_trial_id']}"
    ) in rendered
    assert (
        f"- Common-entry value mismatches: {report['entry_mismatches']['count']}"
        in rendered
    )
    assert (
        "- Snapshot tail: through_trial_id=None, tail_trials=0, "
        "tail_max_trial_id=None, journal_max_trial_id=None"
    ) in rendered


def test_cli_json_strict_returns_nonzero_on_drift(
    tmp_path: Path,
    capsys,
) -> None:
    rows = [_row(1), _row(2)]
    state_path = tmp_path / "autopilot_state.json"
    journal_path = tmp_path / "autopilot_journal.jsonl"
    state_path.write_text(
        json.dumps({"trial_counter": 3, "pareto_archive": _archive([rows[0]])}),
        encoding="utf-8",
    )
    journal_path.write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n",
        encoding="utf-8",
    )

    rc = main(
        [
            "--state",
            str(state_path),
            "--journal",
            str(journal_path),
            "--json",
            "--strict",
        ]
    )
    out = json.loads(capsys.readouterr().out)

    assert rc == 1
    assert out["ok"] is False
    assert out["entry_id_delta"]["journal_only_examples"] == [2]


def test_cli_returns_two_for_invalid_state_json(
    tmp_path: Path,
    capsys,
) -> None:
    state_path = tmp_path / "autopilot_state.json"
    journal_path = tmp_path / "autopilot_journal.jsonl"
    state_path.write_text("{not-json", encoding="utf-8")
    journal_path.write_text("", encoding="utf-8")

    rc = main(["--state", str(state_path), "--journal", str(journal_path)])

    assert rc == 2
    assert "state file is not valid JSON" in capsys.readouterr().err
