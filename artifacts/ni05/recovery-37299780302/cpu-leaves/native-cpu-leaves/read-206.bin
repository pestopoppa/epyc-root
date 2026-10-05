from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "autopilot"))

core_v2_promotion_report = importlib.import_module("core_v2_promotion_report")


def _write_core(path: Path, *, core_id: str = "core_v2") -> None:
    selection_report = {
        "core_id": core_id,
        "generated_at": "2026-07-03T00:00:00Z",
        "selected_count": 1,
        "eligible_items": 3,
        "observed_items": 5,
        "source_rows": 5,
        "shortfall": 0,
        "unresolved_selected_count": 0,
        "parameters": {"source": "ledger", "target_size": 1, "min_attempts": 5},
        "source_provenance": {
            "trusted_rows": 5,
            "untrusted_rows": 0,
            "era_excluded_rows": 10,
            "exclude_before_ts": 1782511631.0,
        },
    }
    rows = [
        {
            "__core_metadata__": True,
            "core_id": core_id,
            "generated_at": "2026-07-03T00:00:00Z",
            "generator": "unit",
            "selected_count": 1,
            "selection_report": selection_report,
        },
        {
            "id": "q1",
            "suite": "math",
            "prompt": "2+2?",
            "expected": "4",
            "scoring_method": "exact_match",
        },
    ]
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")


def _write_eras(path: Path, *, core_id: str | None = None) -> None:
    lines = [
        "eras:",
        "  - id: E3b",
        '    from: "2000-01-01T00:00:00Z"',
        "    scope: autopilot_quality",
    ]
    if core_id is not None:
        lines.extend(
            [
                "  - id: E4-unit",
                '    from: "2000-01-01T00:00:00Z"',
                "    scope: autopilot_quality",
                f'    core_id: "{core_id}"',
                '    policy_version: "unit-test"',
            ]
        )
    path.write_text("\n".join(lines) + "\n")


def test_promotion_report_blocks_without_core_era(tmp_path) -> None:
    core_path = tmp_path / "core_v2.jsonl"
    eras_path = tmp_path / "instrument_eras.yaml"
    _write_core(core_path)
    _write_eras(eras_path)

    report = core_v2_promotion_report.build_core_v2_promotion_report(
        "core_v2",
        core_path=core_path,
        eras_path=eras_path,
    )

    assert report["promotion_ready"] is False
    assert report["core"]["ok"] is True
    assert report["selection"]["ok"] is True
    assert report["instrument_era_guard"]["status"] == "missing_core_era"
    assert any("instrument era" in blocker for blocker in report["blockers"])
    draft = report["operator_era_row_draft"]
    assert draft["status"] == "draft_only"
    assert draft["operator_must_review"] is True
    assert draft["append_under"] == "eras"
    assert draft["row"]["scope"] == "autopilot_quality"
    assert draft["row"]["core_id"] == "core_v2"
    assert draft["row"]["id"] == "E4-core-core-v2"
    rendered = core_v2_promotion_report.render_markdown(report)
    assert "## Operator Era Row Draft" in rendered
    assert "draft-only" in rendered
    assert 'core_id: "core_v2"' in rendered


def test_promotion_report_ready_with_matching_core_era(tmp_path) -> None:
    core_path = tmp_path / "core_v2.jsonl"
    eras_path = tmp_path / "instrument_eras.yaml"
    _write_core(core_path)
    _write_eras(eras_path, core_id="core_v2")

    report = core_v2_promotion_report.build_core_v2_promotion_report(
        "core_v2",
        core_path=core_path,
        eras_path=eras_path,
    )

    assert report["promotion_ready"] is True
    assert report["blockers"] == []
    assert report["instrument_era_guard"]["era"]["id"] == "E4-unit"
    assert report["operator_era_row_draft"]["status"] == "already_authorized"
    assert report["operator_era_row_draft"]["row"] is None
    assert "Status: ready" in core_v2_promotion_report.render_markdown(report)
