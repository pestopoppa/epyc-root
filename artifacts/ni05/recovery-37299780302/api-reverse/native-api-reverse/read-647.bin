from __future__ import annotations

import json
from pathlib import Path

from scripts.tasks import summarize_real_task_corpus as summary


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def test_build_summary_keeps_source_strata_and_privacy_counts(tmp_path: Path) -> None:
    live_manifest = tmp_path / "live" / "manifest.json"
    live_rows = tmp_path / "live" / "rows.jsonl"
    hist_manifest = tmp_path / "historical" / "manifest.json"
    hist_rows = tmp_path / "historical" / "rows.jsonl"
    _write_json(
        live_manifest,
        {
            "counts": {
                "written": 2,
                "by_class": {"code_change_implementation": 1, "benchmark_eval_measurement": 1},
                "by_outcome": {"success": 2},
            }
        },
    )
    _write_jsonl(
        live_rows,
        [
            {"task_id": "a", "class": "code_change_implementation", "outcome": "success", "wall_s": 1.0},
            {"task_id": "b", "class": "benchmark_eval_measurement", "outcome": "success", "wall_s": 2.0},
        ],
    )
    _write_json(
        hist_manifest,
        {
            "counts": {
                "written": 1,
                "by_class": {"research_intake_deep_dive": 1},
                "by_outcome": {"success": 1},
            }
        },
    )
    _write_jsonl(
        hist_rows,
        [
            {
                "task_id": "hist-a",
                "class": "research_intake_deep_dive",
                "outcome": "success",
                "wall_s": 3.0,
                "tokens": {"total": 10},
            }
        ],
    )

    built = summary.build_summary(
        [
            {
                "label": "live",
                "source_family": "live_progress",
                "evidence_role": "operator_progress",
                "weight": 1.0,
                "manifest": str(live_manifest),
                "rows": str(live_rows),
            },
            {
                "label": "historical",
                "source_family": "historical_operator_conversation",
                "evidence_role": "operator_demand_backfill",
                "weight": 1.0,
                "manifest": str(hist_manifest),
                "rows": str(hist_rows),
            },
        ],
        generated_at="2026-06-20T00:00:00+00:00",
    )

    assert built["totals"]["raw_records"] == 3
    assert built["totals"]["by_source_family_raw"] == {
        "historical_operator_conversation": 1,
        "live_progress": 2,
    }
    assert built["totals"]["by_class_raw"] == {
        "benchmark_eval_measurement": 1,
        "code_change_implementation": 1,
        "research_intake_deep_dive": 1,
    }
    assert built["totals"]["token_payloads"] == 1
    assert built["totals"]["prompt_text_rows"] == 0
    assert built["totals"]["dominant_source_family"] == "live_progress"
    assert built["totals"]["max_source_family_weighted_share"] == 0.666667
    assert built["gate_readout"]["class_outcome_count_gate"] is False
    assert built["gate_readout"]["multiple_source_families"] is True
    assert built["gate_readout"]["token_payload_coverage"] is True
    assert built["gate_readout"]["source_weight_dominance_ok"] is False
    assert built["gate_readout"]["privacy_prompt_text_free"] is True


def test_build_summary_sums_repeated_source_family_before_dominance_check(tmp_path: Path) -> None:
    live_a_manifest = tmp_path / "live-a" / "manifest.json"
    live_a_rows = tmp_path / "live-a" / "rows.jsonl"
    live_b_manifest = tmp_path / "live-b" / "manifest.json"
    live_b_rows = tmp_path / "live-b" / "rows.jsonl"
    hist_manifest = tmp_path / "historical" / "manifest.json"
    hist_rows = tmp_path / "historical" / "rows.jsonl"
    for manifest, rows, written, task_class in [
        (live_a_manifest, live_a_rows, 20, "code_change_implementation"),
        (live_b_manifest, live_b_rows, 10, "debug_root_cause"),
        (hist_manifest, hist_rows, 100, "research_intake_deep_dive"),
    ]:
        _write_json(
            manifest,
            {
                "counts": {
                    "written": written,
                    "by_class": {task_class: written},
                    "by_outcome": {"success": written},
                }
            },
        )
        _write_jsonl(
            rows,
            [
                {
                    "task_id": str(manifest),
                    "class": task_class,
                    "outcome": "success",
                    "wall_s": 1.0,
                }
            ],
        )

    built = summary.build_summary(
        [
            {
                "label": "live-a",
                "source_family": "live_progress",
                "evidence_role": "operator_progress",
                "weight": 1.0,
                "manifest": str(live_a_manifest),
                "rows": str(live_a_rows),
            },
            {
                "label": "live-b",
                "source_family": "live_progress",
                "evidence_role": "operator_progress",
                "weight": 1.0,
                "manifest": str(live_b_manifest),
                "rows": str(live_b_rows),
            },
            {
                "label": "historical",
                "source_family": "historical_operator_conversation",
                "evidence_role": "operator_demand_backfill",
                "weight": 0.4,
                "manifest": str(hist_manifest),
                "rows": str(hist_rows),
            },
        ],
        generated_at="2026-06-21T00:00:00+00:00",
    )

    assert built["totals"]["by_source_family_raw"] == {
        "historical_operator_conversation": 100,
        "live_progress": 30,
    }
    assert built["totals"]["by_source_family_weighted"] == {
        "historical_operator_conversation": 40.0,
        "live_progress": 30.0,
    }
    assert built["totals"]["by_evidence_role_raw"] == {
        "operator_demand_backfill": 100,
        "operator_progress": 30,
    }
    assert built["totals"]["by_source_family_weighted_share"] == {
        "historical_operator_conversation": 0.571429,
        "live_progress": 0.428571,
    }
    assert built["gate_readout"]["source_weight_dominance_ok"] is True


def test_parse_source_requires_complete_pipe_spec() -> None:
    parsed = summary.parse_source("live|live_progress|operator_progress|1.0|manifest.json|-")

    assert parsed == {
        "label": "live",
        "source_family": "live_progress",
        "evidence_role": "operator_progress",
        "weight": 1.0,
        "manifest": "manifest.json",
        "rows": None,
    }
