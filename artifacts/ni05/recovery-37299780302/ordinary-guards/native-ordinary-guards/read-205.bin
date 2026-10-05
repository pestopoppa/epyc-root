from __future__ import annotations

import json
import os

from scripts.autopilot.core_v2_calibrate import (
    configure_tool_sentinels,
    default_output_path,
    restore_tool_sentinels,
    result_to_row,
    write_row,
)
from scripts.autopilot.safety_gate import EvalResult


def _result() -> EvalResult:
    return EvalResult(
        tier=1,
        quality=1.5,
        speed=42.0,
        cost=0.5,
        reliability=1.0,
        per_suite_quality={"math": 1.5},
        per_suite_counts={"math": 2},
        routing_distribution={"frontdoor": 1.0},
        n_questions=2,
        question_results=[
            {"qid": "math/a", "suite": "math", "correct": True, "partition": "core"},
            {"qid": "math/b", "suite": "math", "correct": False, "partition": "core"},
        ],
        core_id="legacy_pool_seed_4242_n300",
        details={"requested_n": 300},
        median_request_speed=7.0,
        aggregate_speed=42.0,
        eval_concurrency=3,
        eval_wall_s=12.5,
        speed_metric_mode="aggregate_batch_tps",
    )


def test_result_to_row_is_selector_compatible():
    row = result_to_row(
        result=_result(),
        calibration_id="cal-a",
        repeat_index=1,
        repeats=3,
        requested_n=300,
        seed=4242,
        trial_id=900001,
        started_at="2026-06-14T00:00:00Z",
    )

    assert row["event_type"] == "core_v2_calibration"
    assert row["calibration_id"] == "cal-a"
    assert row["repeat_index"] == 1
    assert row["eval_details"]["question_results"][0]["qid"] == "math/a"
    assert row["eval_details"]["details"]["requested_n"] == 300
    assert row["speed_metric_mode"] == "aggregate_batch_tps"


def test_write_row_appends_jsonl(tmp_path):
    path = tmp_path / "calibration.jsonl"
    row = result_to_row(
        result=_result(),
        calibration_id="cal-a",
        repeat_index=0,
        repeats=1,
        requested_n=300,
        seed=4242,
        trial_id=900000,
        started_at="2026-06-14T00:00:00Z",
    )

    write_row(path, row)
    write_row(path, row | {"repeat_index": 1})

    lines = [json.loads(line) for line in path.read_text().splitlines()]
    assert [line["repeat_index"] for line in lines] == [0, 1]


def test_tool_sentinel_env_is_restored(monkeypatch):
    monkeypatch.setenv("AUTOPILOT_TOOL_SENTINELS", "1")
    prior = configure_tool_sentinels(False)
    assert prior == "1"
    assert "AUTOPILOT_TOOL_SENTINELS" not in os.environ
    restore_tool_sentinels(prior)
    assert os.environ["AUTOPILOT_TOOL_SENTINELS"] == "1"


def test_default_output_path_uses_tmp_root():
    assert str(default_output_path("cal-a")).startswith("/mnt/raid0/llm/tmp/core_v2_calibration/")
