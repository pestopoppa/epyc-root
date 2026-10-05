from __future__ import annotations

import json
from pathlib import Path

from scripts.tasks import package_real_suite_eval as packager


def test_packager_writes_prompt_free_eval_report(tmp_path: Path) -> None:
    source = tmp_path / "eval.jsonl"
    out_dir = tmp_path / "report"
    row = {
        "event_type": "core_v2_calibration",
        "calibration_id": "real-suite",
        "core_id": "real_suite_v1",
        "trial_id": 910000,
        "requested_n": 2,
        "seed": 4242,
        "tier": 1,
        "quality": 1.5,
        "reliability": 1.0,
        "eval_wall_s": 12.0,
        "eval_concurrency": 1,
        "speed_metric_mode": "median_request_tps",
        "aggregate_speed": 3.0,
        "median_request_speed": 2.0,
        "eval_details": {
            "question_results": [
                {"qid": "a", "suite": "real_suite_v1", "correct": True, "latency_ms": 100},
                {
                    "qid": "b",
                    "suite": "real_suite_v1",
                    "real_task_class": "coding_change",
                    "correct": False,
                    "latency_ms": 200,
                    "route": "worker_general",
                    "error": True,
                    "error_detail": "connection refused",
                },
            ],
            "details": {"correct": 1},
        },
    }
    source.write_text(json.dumps(row) + "\n", encoding="utf-8")

    summary = packager.run(
        packager.build_parser().parse_args(
            ["--input", str(source), "--output-dir", str(out_dir), "--caveat", "unit caveat"]
        )
    )

    question_rows = [
        json.loads(line) for line in (out_dir / "question_results.jsonl").read_text().splitlines()
    ]
    assert summary["metrics"]["n_questions"] == 2
    assert summary["metrics"]["correct"] == 1
    assert summary["metrics"]["accuracy"] == 0.5
    assert summary["error_breakdown"] == {"connection refused": 1}
    assert summary["by_task_class"] == {
        "coding_change": {
            "count": 1,
            "correct": 0,
            "errors": 1,
            "accuracy": 0.0,
            "reliability": 0.0,
        },
        "unknown": {
            "count": 1,
            "correct": 1,
            "errors": 0,
            "accuracy": 1.0,
            "reliability": 1.0,
        },
    }
    assert summary["privacy"]["private_key_matches"] == []
    assert summary["question_ledger_path"] == str(out_dir / "question_ledger.jsonl")
    assert "prompt" not in question_rows[0]
    assert "answer" not in question_rows[0]
    assert (out_dir / "summary.md").exists()
    ledger_rows = [
        json.loads(line)
        for line in (out_dir / "question_ledger.jsonl").read_text().splitlines()
    ]
    assert len(ledger_rows) == 2
    assert ledger_rows[0]["schema_version"] == "real_suite_v1_eval_question_ledger_row.v1"
    assert ledger_rows[0]["qid"] == "a"
    assert ledger_rows[0]["calibration_id"] == "real-suite"
    assert ledger_rows[1]["real_task_class"] == "coding_change"
    assert "prompt" not in ledger_rows[0]
    assert "answer" not in ledger_rows[0]


def test_sanitize_question_results_drops_private_fields() -> None:
    rows = packager.sanitize_question_results(
        [
            {
                "qid": "a",
                "suite": "real_suite_v1",
                "real_task_class": "ops_dashboard",
                "correct": True,
                "prompt": "private",
                "expected": "private",
                "answer": "private",
                "error_detail": "safe",
            }
        ]
    )

    assert rows == [
        {
            "qid": "a",
            "suite": "real_suite_v1",
            "real_task_class": "ops_dashboard",
            "correct": True,
            "error_detail": "safe",
            "eval_rank": 1,
        }
    ]
