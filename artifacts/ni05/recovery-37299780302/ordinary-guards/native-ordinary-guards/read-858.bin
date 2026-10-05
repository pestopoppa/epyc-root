from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_token_audit():
    path = Path(__file__).resolve().parents[2] / "scripts" / "analysis" / "token_audit.py"
    spec = importlib.util.spec_from_file_location("token_audit", path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_recent_ap16_observations_uses_runtime_rows(tmp_path: Path) -> None:
    token_audit = _load_token_audit()
    journal = tmp_path / "autopilot_journal.jsonl"
    rows = [
        {"trial_id": 1, "instruction_token_count": 0, "instruction_token_ratio": 0.0},
        {
            "trial_id": 2,
            "timestamp": "2026-06-28T00:00:00+00:00",
            "species": "numeric_swarm",
            "instruction_token_count": 3188,
            "instruction_token_ratio": 0.9183,
            "reliability": 0.98,
            "eval_details": {
                "routing_distribution": {"frontdoor": 0.76, "worker": 0.24},
                "question_results": [
                    {"route": "frontdoor"},
                    {"route": "worker_general"},
                ],
                "details": {
                    "partition_quality": {"core": 2.1},
                    "objective_speed_tps": 59.4,
                },
            },
        },
    ]
    journal.write_text("\n".join(json.dumps(row) for row in rows) + "\n")

    observations = token_audit.load_recent_ap16_observations([journal])

    assert [row["trial_id"] for row in observations] == [2]
    assert observations[0]["instruction_tokens"] == 3188
    assert observations[0]["observed_scaffold_tokens"] > 0
    assert observations[0]["unique_routes"] == ["frontdoor", "worker_general"]
    assert observations[0]["quality"] == 2.1
    assert observations[0]["routing_distribution"] == {"frontdoor": 0.76, "worker": 0.24}


def test_runtime_scaffold_breakdown_counts_active_roles_only() -> None:
    token_audit = _load_token_audit()

    frontdoor_worker = token_audit.runtime_scaffold_breakdown(("frontdoor", "worker"))
    with_architect = token_audit.runtime_scaffold_breakdown(("frontdoor", "worker", "architect"))

    assert frontdoor_worker["root_scaffold_tokens"] > 0
    assert frontdoor_worker["route_role_tokens"] > 0
    assert with_architect["total_tokens"] > frontdoor_worker["total_tokens"]
    assert {component["name"] for component in frontdoor_worker["role_components"]} == {
        "frontdoor",
        "worker_general",
    }


def test_role_overlay_report_label_preserves_retired_role_marker() -> None:
    token_audit = _load_token_audit()
    retired_role_file = "architect" "_coding.md"

    assert "stack-change-guard: allow historical retired-role note" in (
        token_audit.role_overlay_report_label(retired_role_file)
    )
    assert token_audit.role_overlay_report_label("frontdoor.md") == "frontdoor.md"
