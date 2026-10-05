"""Tests for autopilot item analytics."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from scripts.autopilot.item_analytics import analyze_rows, load_journal, render_markdown


def test_suite_level_report_flags_pinned_zero_without_per_qid() -> None:
    rows = []
    for trial_id in range(1, 7):
        rows.append(
            {
                "trial_id": trial_id,
                "timestamp": f"2026-06-{trial_id:02d}T00:00:00+00:00",
                "eval_details": {
                    "per_suite_quality": {"agentic": 0.0, "coder": 3.0},
                    "details": {
                        "per_suite_counts": {"agentic": 2, "coder": 2},
                        "errors": 0,
                    },
                },
            }
        )

    report = analyze_rows(
        rows,
        last_trials=100,
        days=7,
        min_observations=5,
        now=datetime(2026, 6, 7, tzinfo=timezone.utc),
    )

    window = report["windows"]["last_100_trials"]
    assert window["per_qid_available"] is False
    flagged = {row["suite"]: row for row in window["flagged_suites"]}
    assert "pinned_zero_or_broken" in flagged["agentic"]["flags"]
    assert "saturated" in flagged["coder"]["flags"]
    assert "N2 ledger" in window["per_qid_limitation"]


def test_future_per_question_results_get_discrimination_flags() -> None:
    rows = [
        {
            "trial_id": 1,
            "timestamp": "2026-06-01T00:00:00+00:00",
            "keep_revert_decision": "keep",
            "eval_details": {
                "question_results": [
                    {"question_id": "q1", "suite": "agentic", "correct": False},
                    {"question_id": "q2", "suite": "coder", "correct": True},
                ],
                "per_suite_quality": {"agentic": 0.0, "coder": 3.0},
                "details": {"per_suite_counts": {"agentic": 1, "coder": 1}},
            },
        },
        {
            "trial_id": 2,
            "timestamp": "2026-06-02T00:00:00+00:00",
            "keep_revert_decision": "revert",
            "eval_details": {
                "question_results": [
                    {"question_id": "q1", "suite": "agentic", "correct": True},
                    {"question_id": "q2", "suite": "coder", "correct": True},
                ],
                "per_suite_quality": {"agentic": 3.0, "coder": 3.0},
                "details": {"per_suite_counts": {"agentic": 1, "coder": 1}},
            },
        },
    ]

    report = analyze_rows(rows, last_trials=2, days=7, min_observations=2)
    window = report["windows"]["last_2_trials"]

    assert window["per_qid_available"] is True
    questions = {row["question_id"]: row for row in window["question_summary"]}
    assert questions["q1"]["discrimination"] == -1.0
    assert "negative_discrimination" in questions["q1"]["flags"]


def test_watchlist_verdicts_separate_artifact_from_hard_candidate() -> None:
    rows = []
    for trial_id in range(1, 7):
        rows.append(
            {
                "trial_id": trial_id,
                "timestamp": f"2026-06-{trial_id:02d}T00:00:00+00:00",
                "eval_details": {
                    "per_suite_quality": {"usaco": 0.0, "mode_advantage_hard": 0.0},
                    "details": {"per_suite_counts": {"usaco": 2, "mode_advantage_hard": 2}},
                },
            }
        )

    report = analyze_rows(rows, last_trials=100, days=0, min_observations=5)
    window = report["windows"]["last_100_trials"]
    verdicts = {row["suite"]: row for row in window["watchlist_verdicts"]}

    assert verdicts["usaco"]["artifact_verdict"] == "artifact"
    assert verdicts["mode_advantage_hard"]["artifact_verdict"] == "genuinely_hard_candidate"


def test_markdown_reports_unavailable_per_qid() -> None:
    report = analyze_rows(
        [
            {
                "trial_id": 1,
                "timestamp": "2026-06-01T00:00:00+00:00",
                "eval_details": {
                    "per_suite_quality": {"agentic": 0.0},
                    "details": {"per_suite_counts": {"agentic": 2}},
                },
            }
        ],
        last_trials=1,
        days=0,
        min_observations=1,
    )

    md = render_markdown(report)

    assert "Per-qid analytics: **unavailable**" in md
    assert "agentic" in md


def test_load_journal_folds_supersession_events(tmp_path) -> None:
    journal = tmp_path / "autopilot_journal.jsonl"
    rows = [
        {
            "trial_id": 1,
            "timestamp": "2026-06-01T00:00:00+00:00",
            "eval_details": {"per_suite_quality": {"agentic": 1.0}},
        },
        {
            "trial_id": 2,
            "timestamp": "2026-06-02T00:00:00+00:00",
            "eval_details": {"per_suite_quality": {"agentic": 0.0}},
        },
        {
            "type": "supersession",
            "target_trial_ids": [2],
            "fields": {"bug_corrupted_by": "resource_contention"},
        },
    ]
    journal.write_text("\n".join(json.dumps(row) for row in rows) + "\n")

    loaded = load_journal(journal)

    assert [row["trial_id"] for row in loaded] == [1, 2]
    assert loaded[1]["bug_corrupted_by"] == "resource_contention"
