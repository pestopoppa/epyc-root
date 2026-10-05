from __future__ import annotations

import json
from pathlib import Path
import datetime as dt

from scripts.autopilot import audit_block_report


def _trial(
    trial_id: int,
    core_correct: int,
    core_total: int,
    audit_correct: int,
    audit_total: int,
    *,
    missing_partition_core: int = 0,
    corrupt: str = "",
    outcome_status: str = "ok",
    tier: int = 1,
    timestamp: str | None = None,
    candidate: str | None = None,
) -> dict:
    question_results = []
    for idx in range(core_total):
        question_results.append(
            {
                "qid": f"core-{trial_id}-{idx}",
                "correct": idx < core_correct,
                "partition": "core" if idx >= missing_partition_core else None,
            }
        )
    for idx in range(audit_total):
        question_results.append(
            {
                "qid": f"audit-{trial_id}-{idx}",
                "correct": idx < audit_correct,
                "partition": "audit",
            }
        )
    row = {
        "trial_id": trial_id,
        "tier": tier,
        "outcome_status": outcome_status,
        "eval_details": {"question_results": question_results},
    }
    if timestamp is not None:
        row["timestamp"] = timestamp
    if corrupt:
        row["bug_corrupted_by"] = corrupt
    if candidate:
        row["seq"] = {"candidate": candidate}
    return row


def _write_journal(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def test_partition_extraction_and_missing_partition_defaults_to_core(tmp_path: Path) -> None:
    journal = tmp_path / "autopilot_journal.jsonl"
    _write_journal(
        journal,
        [
            _trial(1, core_correct=1, core_total=2, audit_correct=1, audit_total=2, missing_partition_core=1),
        ],
    )

    report = audit_block_report.build_report(audit_block_report.load_journal_rows([journal]))

    assert report["trial_count"] == 1
    assert report["audited_trial_count"] == 1
    trial = report["trials"][0]
    assert trial["core_correct"] == 1
    assert trial["core_total"] == 2
    assert trial["audit_correct"] == 1
    assert trial["audit_total"] == 2
    assert trial["core_quality_0_3"] == 1.5
    assert trial["audit_quality_0_3"] == 1.5
    assert trial["delta_audit_minus_core"] == 0.0


def test_skip_rows_without_audit_block(tmp_path: Path) -> None:
    journal = tmp_path / "autopilot_journal.jsonl"
    _write_journal(
        journal,
        [
            _trial(1, core_correct=2, core_total=2, audit_correct=1, audit_total=2),
            {
                "trial_id": 2,
                "eval_details": {
                    "question_results": [
                        {"qid": "core-2-0", "correct": True},
                        {"qid": "core-2-1", "correct": False},
                    ]
                },
            },
            {"type": "ledger", "trial_id": 3, "eval_details": {"question_results": []}},
            {"type": "supersession", "target_trial_ids": [1]},
        ],
    )

    report = audit_block_report.build_report(audit_block_report.load_journal_rows([journal]))

    assert report["trial_count"] == 2
    assert report["audited_trial_count"] == 1
    assert [trial["trial_id"] for trial in report["trials"]] == [1]


def test_cli_writes_json_and_markdown(tmp_path: Path) -> None:
    journal = tmp_path / "autopilot_journal.jsonl"
    out_json = tmp_path / "report.json"
    out_md = tmp_path / "report.md"
    _write_journal(
        journal,
        [
            _trial(7, core_correct=1, core_total=2, audit_correct=2, audit_total=2),
        ],
    )

    exit_code = audit_block_report.main(
        ["--journal", str(journal), "--out-json", str(out_json), "--out-md", str(out_md)]
    )

    assert exit_code == 0
    report = json.loads(out_json.read_text(encoding="utf-8"))
    assert report["trials"][0]["trial_id"] == 7
    assert report["trials"][0]["audit_quality_0_3"] == 3.0
    assert report["gaming_alarm_window"] == 30
    assert report["transfer_diagnostic"]["alarm_window"] == 30
    markdown = out_md.read_text(encoding="utf-8")
    assert "# W6 Rotating Audit Block Report" in markdown
    assert "Gaming alarm window: last 30 audited trials" in markdown
    assert "| trial_id | core | audit | core_q | audit_q | delta_audit_minus_core |" in markdown
    assert "7 | 1/2 | 2/2 | 1.500 | 3.000 | +1.500" in markdown


def test_build_report_default_keeps_all_history_alarm_window_none(
    tmp_path: Path,
) -> None:
    journal = tmp_path / "autopilot_journal.jsonl"
    _write_journal(
        journal,
        [
            _trial(1, core_correct=1, core_total=2, audit_correct=1, audit_total=2),
        ],
    )

    report = audit_block_report.build_report(audit_block_report.load_journal_rows([journal]))

    assert report["gaming_alarm_window"] is None
    assert report["transfer_diagnostic"]["alarm_window"] is None


def test_transfer_diagnostic_counts_divergences(tmp_path: Path) -> None:
    journal = tmp_path / "autopilot_journal.jsonl"
    _write_journal(
        journal,
        [
            _trial(1, core_correct=1, core_total=4, audit_correct=3, audit_total=4),
            _trial(2, core_correct=3, core_total=4, audit_correct=1, audit_total=4),
            _trial(3, core_correct=3, core_total=4, audit_correct=3, audit_total=4),
        ],
    )

    report = audit_block_report.build_report(audit_block_report.load_journal_rows([journal]))

    diagnostic = report["transfer_diagnostic"]
    assert diagnostic["audited_trial_count"] == 3
    assert diagnostic["potential_overfit_divergences"] == 1
    assert diagnostic["events"] == [
        {
            "trial_id": 2,
            "previous_trial_id": 1,
            "core_delta": 1.5,
            "audit_delta": -1.5,
        }
    ]


def test_report_excludes_untrusted_rows_from_w6_audit_counts_and_alarm(
    tmp_path: Path,
) -> None:
    journal = tmp_path / "autopilot_journal.jsonl"
    _write_journal(
        journal,
        [
            _trial(1, core_correct=1, core_total=2, audit_correct=1, audit_total=2),
            _trial(2, core_correct=2, core_total=2, audit_correct=1, audit_total=2),
            _trial(
                3,
                core_correct=2,
                core_total=2,
                audit_correct=0,
                audit_total=2,
                corrupt="resource_contention",
            ),
            _trial(
                4,
                core_correct=2,
                core_total=2,
                audit_correct=0,
                audit_total=2,
                outcome_status="skipped",
            ),
            _trial(
                5,
                core_correct=2,
                core_total=2,
                audit_correct=0,
                audit_total=2,
                outcome_status="invalid",
            ),
            _trial(
                6,
                core_correct=2,
                core_total=2,
                audit_correct=0,
                audit_total=2,
                tier=0,
            ),
        ],
    )

    report = audit_block_report.build_report(audit_block_report.load_journal_rows([journal]))

    assert report["trial_count"] == 6
    assert report["raw_audited_trial_count"] == 6
    assert report["trusted_audited_trial_count"] == 2
    assert report["untrusted_audited_trial_count"] == 4
    assert report["untrusted_audited_trial_ids"] == [3, 4, 5, 6]
    assert report["audited_trial_count"] == 2
    assert [trial["trial_id"] for trial in report["trials"]] == [1, 2]
    assert report["gaming_alarm"] is False
    assert report["transfer_diagnostic"]["potential_overfit_divergences"] == 0


def test_report_excludes_pre_era_audited_rows_from_counts_and_alarm(
    tmp_path: Path,
) -> None:
    journal = tmp_path / "autopilot_journal.jsonl"
    cutoff = dt.datetime(2026, 6, 26, 22, 7, 11, tzinfo=dt.timezone.utc).timestamp()
    _write_journal(
        journal,
        [
            _trial(
                1,
                core_correct=1,
                core_total=2,
                audit_correct=1,
                audit_total=2,
                timestamp="2026-06-26T22:07:10+00:00",
            ),
            _trial(
                2,
                core_correct=2,
                core_total=2,
                audit_correct=1,
                audit_total=2,
                timestamp="2026-06-26T22:07:10.500000+00:00",
            ),
            _trial(
                3,
                core_correct=1,
                core_total=2,
                audit_correct=1,
                audit_total=2,
                timestamp="2026-06-26T22:07:11+00:00",
            ),
            _trial(
                4,
                core_correct=1,
                core_total=2,
                audit_correct=1,
                audit_total=2,
                timestamp="2026-06-27T00:00:00+00:00",
            ),
        ],
    )

    report = audit_block_report.build_report(
        audit_block_report.load_journal_rows([journal]),
        alarm_window=2,
        exclude_before_ts=cutoff,
    )

    assert report["all_raw_audited_trial_count"] == 4
    assert report["raw_audited_trial_count"] == 2
    assert report["era_exclude_before_ts"] == cutoff
    assert report["era_excluded_audited_trial_count"] == 2
    assert report["era_excluded_audited_trial_ids"] == [1, 2]
    assert report["trusted_audited_trial_count"] == 2
    assert [trial["trial_id"] for trial in report["trials"]] == [3, 4]
    assert report["gaming_alarm"] is False
    assert report["cumulative_gaming_alarm"] is False


def test_report_accounts_for_pre_era_excluded_gaming_events(tmp_path: Path) -> None:
    journal = tmp_path / "autopilot_journal.jsonl"
    cutoff = dt.datetime(2026, 6, 26, 22, 7, 11, tzinfo=dt.timezone.utc).timestamp()
    _write_journal(
        journal,
        [
            _trial(
                1,
                core_correct=1,
                core_total=4,
                audit_correct=3,
                audit_total=4,
                timestamp="2026-06-26T22:07:09+00:00",
            ),
            _trial(
                2,
                core_correct=3,
                core_total=4,
                audit_correct=1,
                audit_total=4,
                timestamp="2026-06-26T22:07:10+00:00",
            ),
            _trial(
                3,
                core_correct=1,
                core_total=4,
                audit_correct=1,
                audit_total=4,
                timestamp="2026-06-26T22:07:11+00:00",
            ),
            _trial(
                4,
                core_correct=1,
                core_total=4,
                audit_correct=1,
                audit_total=4,
                timestamp="2026-06-27T00:00:00+00:00",
            ),
        ],
    )

    report = audit_block_report.build_report(
        audit_block_report.load_journal_rows([journal]),
        alarm_window=2,
        exclude_before_ts=cutoff,
    )

    assert report["era_excluded_gaming_event_count"] == 1
    assert report["era_excluded_gaming_events"] == [
        {
            "trial_id": 2,
            "previous_trial_id": 1,
            "core_delta": 1.5,
            "audit_delta": -1.5,
        }
    ]
    assert report["gaming_alarm"] is False
    assert report["cumulative_gaming_alarm"] is False


def test_no_gaming_alarm_with_insufficient_audited_history(tmp_path: Path) -> None:
    journal = tmp_path / "autopilot_journal.jsonl"
    _write_journal(
        journal,
        [
            _trial(1, core_correct=1, core_total=2, audit_correct=1, audit_total=2),
            _trial(2, core_correct=2, core_total=2, audit_correct=1, audit_total=2),
        ],
    )

    report = audit_block_report.build_report(audit_block_report.load_journal_rows([journal]))

    assert report["gaming_alarm"] is False
    assert report["gaming_events"] == []
    assert report["transfer_diagnostic"]["potential_overfit_divergences"] == 0


def test_gaming_alarm_ignores_flat_audit_and_one_question_wobble(tmp_path: Path) -> None:
    journal = tmp_path / "autopilot_journal.jsonl"
    _write_journal(
        journal,
        [
            _trial(1, core_correct=33, core_total=50, audit_correct=7, audit_total=10),
            _trial(2, core_correct=34, core_total=50, audit_correct=7, audit_total=10),
            _trial(3, core_correct=36, core_total=50, audit_correct=6, audit_total=10),
        ],
    )

    report = audit_block_report.build_report(audit_block_report.load_journal_rows([journal]))

    assert report["gaming_alarm"] is False
    assert report["gaming_events"] == []
    assert report["cumulative_gaming_alarm"] is False
    assert report["cumulative_gaming_events"] == []
    assert report["gaming_alarm_clearance_clean_trials_required"] == 0
    assert report["transfer_diagnostic"]["clearance_clean_trials_required"] == 0


def test_core_inflation_warning_flags_core_up_audit_flat(tmp_path: Path) -> None:
    journal = tmp_path / "autopilot_journal.jsonl"
    _write_journal(
        journal,
        [
            _trial(1, core_correct=30, core_total=50, audit_correct=7, audit_total=10),
            _trial(2, core_correct=31, core_total=50, audit_correct=7, audit_total=10),
            _trial(3, core_correct=32, core_total=50, audit_correct=7, audit_total=10),
        ],
    )

    report = audit_block_report.build_report(
        audit_block_report.load_journal_rows([journal]),
        monotone_core_steps=2,
    )

    assert report["gaming_alarm"] is False
    assert report["core_inflation_warning"] is True
    assert report["core_inflation_events"] == [
        {
            "start_trial_id": 1,
            "end_trial_id": 3,
            "trial_count": 3,
            "core_delta": 0.12,
            "audit_delta": 0.0,
            "audit_span": 0.0,
            "core_step": 0.06,
            "audit_step": 0.3,
            "min_core_steps": 2,
            "core_steps_observed": 2.0,
        }
    ]
    assert report["transfer_diagnostic"]["core_inflation_warnings"] == 1


def test_core_inflation_warning_requires_audit_flat_below_resolution(
    tmp_path: Path,
) -> None:
    journal = tmp_path / "autopilot_journal.jsonl"
    _write_journal(
        journal,
        [
            _trial(1, core_correct=30, core_total=50, audit_correct=7, audit_total=10),
            _trial(2, core_correct=31, core_total=50, audit_correct=7, audit_total=10),
            _trial(3, core_correct=32, core_total=50, audit_correct=8, audit_total=10),
        ],
    )

    report = audit_block_report.build_report(
        audit_block_report.load_journal_rows([journal]),
        monotone_core_steps=2,
    )

    assert report["core_inflation_warning"] is False
    assert report["core_inflation_events"] == []


def test_gaming_alarm_detects_beyond_resolution_divergence(tmp_path: Path) -> None:
    journal = tmp_path / "autopilot_journal.jsonl"
    _write_journal(
        journal,
        [
            _trial(1, core_correct=1, core_total=4, audit_correct=3, audit_total=4),
            _trial(2, core_correct=3, core_total=4, audit_correct=1, audit_total=4),
            _trial(3, core_correct=3, core_total=4, audit_correct=3, audit_total=4),
        ],
    )

    report = audit_block_report.build_report(audit_block_report.load_journal_rows([journal]))

    assert report["gaming_alarm"] is True
    assert report["gaming_events"] == [
        {
            "trial_id": 2,
            "previous_trial_id": 1,
            "core_delta": 1.5,
            "audit_delta": -1.5,
        }
    ]
    assert report["cumulative_gaming_alarm"] is True
    assert report["cumulative_gaming_events"] == report["gaming_events"]
    assert report["gaming_alarm_clearance_clean_trials_required"] is None
    assert report["transfer_diagnostic"]["clearance_clean_trials_required"] is None


def test_gaming_alarm_ignores_cross_candidate_divergence(tmp_path: Path) -> None:
    journal = tmp_path / "autopilot_journal.jsonl"
    _write_journal(
        journal,
        [
            _trial(
                1,
                core_correct=1,
                core_total=4,
                audit_correct=3,
                audit_total=4,
                candidate="candidate-a",
            ),
            _trial(
                2,
                core_correct=3,
                core_total=4,
                audit_correct=1,
                audit_total=4,
                candidate="candidate-b",
            ),
            _trial(
                3,
                core_correct=3,
                core_total=4,
                audit_correct=3,
                audit_total=4,
                candidate="candidate-b",
            ),
        ],
    )

    report = audit_block_report.build_report(audit_block_report.load_journal_rows([journal]))

    assert report["gaming_alarm"] is False
    assert report["gaming_events"] == []
    assert report["cumulative_gaming_alarm"] is False
    assert report["transfer_diagnostic"]["potential_overfit_divergences"] == 0
    assert [trial["candidate_key"] for trial in report["trials"]] == [
        "seq:candidate:candidate-a",
        "seq:candidate:candidate-b",
        "seq:candidate:candidate-b",
    ]


def test_gaming_alarm_keeps_same_candidate_divergence(tmp_path: Path) -> None:
    journal = tmp_path / "autopilot_journal.jsonl"
    _write_journal(
        journal,
        [
            _trial(
                1,
                core_correct=1,
                core_total=4,
                audit_correct=3,
                audit_total=4,
                candidate="candidate-a",
            ),
            _trial(
                2,
                core_correct=3,
                core_total=4,
                audit_correct=1,
                audit_total=4,
                candidate="candidate-a",
            ),
            _trial(
                3,
                core_correct=3,
                core_total=4,
                audit_correct=3,
                audit_total=4,
                candidate="candidate-a",
            ),
        ],
    )

    report = audit_block_report.build_report(audit_block_report.load_journal_rows([journal]))

    assert report["gaming_alarm"] is True
    assert report["gaming_events"] == [
        {
            "trial_id": 2,
            "previous_trial_id": 1,
            "core_delta": 1.5,
            "audit_delta": -1.5,
            "candidate_key": "seq:candidate:candidate-a",
        }
    ]


def test_alarm_window_can_clear_after_historical_divergence(tmp_path: Path) -> None:
    journal = tmp_path / "autopilot_journal.jsonl"
    _write_journal(
        journal,
        [
            _trial(1, core_correct=1, core_total=4, audit_correct=3, audit_total=4),
            _trial(2, core_correct=3, core_total=4, audit_correct=1, audit_total=4),
            _trial(3, core_correct=1, core_total=4, audit_correct=1, audit_total=4),
            _trial(4, core_correct=1, core_total=4, audit_correct=1, audit_total=4),
            _trial(5, core_correct=1, core_total=4, audit_correct=1, audit_total=4),
        ],
    )

    report = audit_block_report.build_report(
        audit_block_report.load_journal_rows([journal]),
        alarm_window=3,
    )

    assert report["gaming_alarm"] is False
    assert report["gaming_events"] == []
    assert report["gaming_alarm_clearance_clean_trials_required"] == 0
    assert report["gaming_alarm_window"] == 3
    assert report["gaming_alarm_window_trial_count"] == 3
    assert report["transfer_diagnostic"]["potential_overfit_divergences"] == 0
    assert report["cumulative_gaming_alarm"] is True
    assert report["transfer_diagnostic"]["cumulative_potential_overfit_divergences"] == 1


def test_alarm_window_reports_clean_rows_needed_to_clear_active_event(
    tmp_path: Path,
) -> None:
    journal = tmp_path / "autopilot_journal.jsonl"
    _write_journal(
        journal,
        [
            _trial(1, core_correct=1, core_total=4, audit_correct=1, audit_total=4),
            _trial(2, core_correct=1, core_total=4, audit_correct=1, audit_total=4),
            _trial(3, core_correct=1, core_total=4, audit_correct=3, audit_total=4),
            _trial(4, core_correct=3, core_total=4, audit_correct=1, audit_total=4),
            _trial(5, core_correct=3, core_total=4, audit_correct=3, audit_total=4),
        ],
    )

    report = audit_block_report.build_report(
        audit_block_report.load_journal_rows([journal]),
        alarm_window=3,
    )

    assert report["gaming_alarm"] is True
    assert report["gaming_events"] == [
        {
            "trial_id": 4,
            "previous_trial_id": 3,
            "core_delta": 1.5,
            "audit_delta": -1.5,
        }
    ]
    assert report["gaming_alarm_clearance_clean_trials_required"] == 1
    assert report["transfer_diagnostic"]["clearance_clean_trials_required"] == 1


def test_alarm_window_reports_clearance_before_window_is_full(tmp_path: Path) -> None:
    journal = tmp_path / "autopilot_journal.jsonl"
    _write_journal(
        journal,
        [
            _trial(1, core_correct=1, core_total=4, audit_correct=3, audit_total=4),
            _trial(2, core_correct=3, core_total=4, audit_correct=1, audit_total=4),
            _trial(3, core_correct=3, core_total=4, audit_correct=3, audit_total=4),
        ],
    )

    report = audit_block_report.build_report(
        audit_block_report.load_journal_rows([journal]),
        alarm_window=5,
    )

    assert report["gaming_alarm"] is True
    assert report["gaming_alarm_window"] == 5
    assert report["gaming_alarm_window_trial_count"] == 3
    assert report["gaming_alarm_clearance_clean_trials_required"] == 3
    assert report["transfer_diagnostic"]["clearance_clean_trials_required"] == 3


def test_markdown_distinguishes_current_window_from_cumulative_history(tmp_path: Path) -> None:
    journal = tmp_path / "autopilot_journal.jsonl"
    _write_journal(
        journal,
        [
            _trial(1, core_correct=1, core_total=4, audit_correct=3, audit_total=4),
            _trial(2, core_correct=3, core_total=4, audit_correct=1, audit_total=4),
            _trial(3, core_correct=1, core_total=4, audit_correct=1, audit_total=4),
            _trial(4, core_correct=1, core_total=4, audit_correct=1, audit_total=4),
            _trial(5, core_correct=1, core_total=4, audit_correct=1, audit_total=4),
        ],
    )

    markdown = audit_block_report.render_markdown(
        audit_block_report.build_report(
            audit_block_report.load_journal_rows([journal]),
            alarm_window=3,
        )
    )

    assert "Gaming alarm window: last 3 audited trials" in markdown
    assert "No suspicious gaming trend detected in the current window." in markdown
    assert "Historical divergences remain in cumulative evidence: 1 event." in markdown


def test_markdown_includes_gaming_alarm(tmp_path: Path) -> None:
    journal = tmp_path / "autopilot_journal.jsonl"
    _write_journal(
        journal,
        [
            _trial(1, core_correct=1, core_total=4, audit_correct=3, audit_total=4),
            _trial(2, core_correct=3, core_total=4, audit_correct=1, audit_total=4),
            _trial(3, core_correct=3, core_total=4, audit_correct=3, audit_total=4),
        ],
    )

    markdown = audit_block_report.render_markdown(
        audit_block_report.build_report(audit_block_report.load_journal_rows([journal]))
    )

    assert "## Audit Gaming Alarm" in markdown
    assert "triggered" in markdown
    assert "trial 2 vs 1" in markdown
