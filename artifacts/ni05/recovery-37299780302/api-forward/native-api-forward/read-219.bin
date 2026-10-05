from __future__ import annotations

import json

import pytest

from scripts.analysis.dar1_regret_analysis import compute_regret, parse_progress_logs


def _write_jsonl(path, rows):
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")


def test_parse_progress_logs_reads_top_level_outcomes_and_cheap_first(tmp_path):
    _write_jsonl(
        tmp_path / "2026-06-12.jsonl",
        [
            {
                "event_type": "routing_decision",
                "task_id": "task-1",
                "timestamp": "2026-06-12T00:00:00Z",
                "data": {
                    "routing": ["worker_math"],
                    "chosen_action": "worker_math",
                    "action_topk": ["frontdoor", "worker_math"],
                    "q_topk": [0.8, 0.7],
                    "selection_score_topk": [0.9, 0.6],
                    "decision_source": "rules",
                    "difficulty_band": "hard",
                    "task_class": "coding_change",
                },
            },
            {
                "event_type": "task_completed",
                "task_id": "task-1",
                "outcome": "success",
                "reward": 1.0,
                "data": {"task_record_v1": {"class": "coding_change"}},
            },
            {
                "event_type": "routing_fallback",
                "task_id": "task-1",
                "data": {
                    "kind": "try_cheap_first",
                    "cheap_first_attempted": True,
                    "cheap_first_passed": False,
                    "reason": "quality_issue",
                },
            },
            {
                "event_type": "routing_decision",
                "task_id": "task-2",
                "data": {
                    "routing": ["frontdoor"],
                    "q_topk": [0.5, 0.5],
                    "selection_score_topk": [0.5, 0.5],
                    "decision_source": "learned",
                    "difficulty_band": "easy",
                    "real_task_class": "governance_docs_handoff",
                },
            },
            {
                "event_type": "task_failed",
                "task_id": "task-2",
                "data": {},
            },
        ],
    )

    decisions, outcomes, cheap_first = parse_progress_logs(
        tmp_path,
        "2026-06-12",
        "2026-06-12",
    )
    report = compute_regret(decisions, outcomes, cheap_first)

    assert outcomes["task-1"].outcome == "success"
    assert outcomes["task-2"].outcome == "failure"
    assert report.outcome_matched == 2
    assert report.identifiable_regret_decisions == 2
    assert report.mean_decision_regret == pytest.approx(0.15)
    assert report.regret_gate_pct == pytest.approx(15.0)
    assert report.cheap_first_total == 1
    assert report.cheap_first_attempted == 1
    assert report.cheap_first_passed == 0
    assert report.cheap_first_reasons == {"quality_issue": 1}
    assert report.task_class_counts == {
        "coding_change": 1,
        "governance_docs_handoff": 1,
    }
    assert report.task_class_regret == {
        "coding_change": pytest.approx(0.0),
        "governance_docs_handoff": pytest.approx(0.0),
    }
    assert report.task_class_success_rate == {
        "coding_change": pytest.approx(100.0),
        "governance_docs_handoff": pytest.approx(0.0),
    }
