"""Tests for tool-compression top-up telemetry summaries."""

from __future__ import annotations

import json

from scripts.analysis import tool_compression_topups as mod


def test_load_records_filters_tool_and_bad_json(tmp_path) -> None:
    path = tmp_path / "telemetry.jsonl"
    path.write_text(
        "\n".join(
            [
                "{bad json",
                json.dumps({"tool": "other", "command": "git status"}),
                json.dumps({"tool": "run_bash_compressed", "command": "git status"}),
                "",
            ]
        )
    )

    records = mod.load_records(path)

    assert records == [{"tool": "run_bash_compressed", "command": "git status"}]


def test_summarize_reports_top_up_rate_and_gate() -> None:
    summary = mod.summarize(
        [
            {
                "tool": "run_bash_compressed",
                "command": "ls src",
                "compressor_strategy": "ls_summary",
            },
            {
                "tool": "run_bash_compressed",
                "command": "head -20 src/file.py",
                "compressor_strategy": "raw_passthrough",
                "top_up_candidate": True,
                "followup_reason": "file_view_after_listing",
            },
        ],
        min_compressed_calls=2,
    )

    assert summary["compressed_calls"] == 2
    assert summary["min_compressed_calls"] == 2
    assert summary["has_enough_observations"] is True
    assert summary["followups"] == 1
    assert summary["top_up_rate"] == 0.5
    assert summary["passes_threshold"] is False
    assert summary["ready_for_rollout_decision"] is True
    assert summary["rollout_decision"] == "keep_optional_or_drop_candidate"
    assert summary["followup_reasons"] == {"file_view_after_listing": 1}
    assert summary["compressor_strategies"] == {"ls_summary": 1, "raw_passthrough": 1}


def test_summarize_distinguishes_empty_observation_window() -> None:
    summary = mod.summarize([])

    assert summary["compressed_calls"] == 0
    assert summary["has_enough_observations"] is False
    assert summary["passes_threshold"] is None
    assert summary["ready_for_rollout_decision"] is False
    assert summary["rollout_decision"] == "awaiting_compressed_calls"


def test_summarize_requires_minimum_observations_before_rollout_decision() -> None:
    summary = mod.summarize(
        [
            {
                "tool": "run_bash_compressed",
                "command": "git status",
                "compressor_strategy": "git_status",
            }
        ],
        min_compressed_calls=2,
    )

    assert summary["compressed_calls"] == 1
    assert summary["has_enough_observations"] is False
    assert summary["passes_threshold"] is True
    assert summary["ready_for_rollout_decision"] is False
    assert summary["rollout_decision"] == "awaiting_minimum_observations"
