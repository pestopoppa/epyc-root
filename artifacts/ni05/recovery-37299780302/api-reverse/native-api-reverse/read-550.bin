"""Tests for offline verifier-data expansion planning."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import numpy as np

from scripts.graph_router import plan_offline_reward_verifier_expansion as mod


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def test_canonical_action_maps_historical_delegated_and_alias_roles(caplog) -> None:
    actions = {"frontdoor", "architect_general", "coder_escalation", "worker_vision"}
    legacy_architect_coding = "architect_coding:delegated"  # stack-change-guard: allow retired-role remap fixture

    caplog.set_level(logging.WARNING, logger="scripts.graph_router.action_space")
    assert mod._canonical_action("architect_general:delegated", actions) == "architect_general"
    assert mod._canonical_action(legacy_architect_coding, actions) == "architect_general"
    assert mod._canonical_action("coder_primary", actions) == "coder_escalation"
    assert mod._canonical_action("frontdoor:direct", actions) == "frontdoor"
    assert mod._canonical_action("worker_vision:direct", actions) == "worker_vision"
    assert mod._canonical_action("vision_escalation:direct", actions) is None
    assert "Unknown action" not in caplog.text


def test_build_plan_excludes_existing_rows_and_strips_private_text(tmp_path: Path) -> None:
    source = tmp_path / "results.jsonl"
    _write_jsonl(
        source,
        [
            {
                "question_id": "q1",
                "suite": "architecture",
                "prompt": "Design the thing",
                "expected": "Use a queue",
                "rewards": {
                    "architect_general:delegated": 1.0,
                    "coder_primary": 0.0,
                },
                "role_results": {
                    "architect_general:delegated": {
                        "answer": "Use a queue with backpressure",
                        "passed": True,
                    },
                    "coder_primary": {
                        "answer": "Use direct calls",
                        "passed": False,
                    },
                },
            }
        ],
    )
    existing_manifest = tmp_path / "existing.jsonl"
    _write_jsonl(
        existing_manifest,
        [
            {
                "source_path": str(source),
                "source_record_offset": 0,
                "role_key": "coder_primary",
            }
        ],
    )
    existing_summary = tmp_path / "summary.json"
    existing_summary.write_text(
        json.dumps(
            {
                "canonical_action_counts": {
                    "architect_general": 10,
                    "coder_escalation": 88,
                }
            }
        ),
        encoding="utf-8",
    )

    candidates, summary = mod.build_plan(
        argparse.Namespace(
            input=[source],
            existing_manifest=existing_manifest,
            existing_summary=existing_summary,
            target_actions="architect_general,coder_escalation",
            target_source_families="other",
            min_action_rows=30,
            min_source_family_action_rows=10,
            max_candidates_per_action=20,
        )
    )

    assert len(candidates) == 1
    assert candidates[0]["canonical_action"] == "architect_general"
    assert "prompt" not in candidates[0]
    assert "expected" not in candidates[0]
    assert "response" not in candidates[0]
    assert summary["candidate_action_counts"] == {"architect_general": 1}
    assert summary["candidate_source_family_counts"] == {"other": 1}
    assert summary["candidate_source_family_action_counts"] == {
        "other:architect_general": 1
    }
    assert summary["existing_rows_excluded"] == 1
    assert summary["recommended_sources"][0]["source_path"] == str(source)
    assert summary["recommended_sources"][0]["target_source_family_action_counts"] == {
        "other:architect_general": 1
    }


def test_build_plan_deduplicates_repeated_input_paths(tmp_path: Path) -> None:
    source = tmp_path / "results.jsonl"
    _write_jsonl(
        source,
        [
            {
                "question_id": "q1",
                "suite": "architecture",
                "prompt": "Design the thing",
                "expected": "Use a queue",
                "role_results": {
                    "architect_general:delegated": {
                        "answer": "Use a queue with backpressure",
                        "passed": True,
                    },
                },
            }
        ],
    )

    candidates, summary = mod.build_plan(
        argparse.Namespace(
            input=[source, source],
            existing_manifest=None,
            existing_summary=None,
            target_actions="architect_general",
            target_source_families="other",
            min_action_rows=30,
            min_source_family_action_rows=10,
            max_candidates_per_action=20,
        )
    )

    assert len(candidates) == 1
    assert summary["files_scanned"] == 2
    assert summary["candidate_action_counts"] == {"architect_general": 1}


def test_build_plan_filters_and_counts_target_source_families(tmp_path: Path) -> None:
    seeding_source = tmp_path / "seeding_20260305_203724.jsonl"
    three_way_source = tmp_path / "3way_20260303_025953.jsonl"
    other_source = tmp_path / "misc_results.jsonl"
    for source in (seeding_source, three_way_source, other_source):
        _write_jsonl(
            source,
            [
                {
                    "question_id": source.stem,
                    "suite": "architecture",
                    "prompt": f"Prompt for {source.stem}",
                    "expected": "Use a queue",
                    "role_results": {
                        "architect_general:delegated": {
                            "answer": "Use a queue with backpressure",
                            "passed": True,
                        },
                    },
                }
            ],
        )

    candidates, summary = mod.build_plan(
        argparse.Namespace(
            input=[seeding_source, three_way_source, other_source],
            existing_manifest=None,
            existing_summary=None,
            target_actions="architect_general",
            target_source_families="seeding_eval,three_way_eval",
            min_action_rows=30,
            min_source_family_action_rows=2,
            max_candidates_per_action=20,
        )
    )

    assert {row["source_family"] for row in candidates} == {
        "seeding_eval",
        "three_way_eval",
    }
    assert summary["candidate_source_family_counts"] == {
        "seeding_eval": 1,
        "three_way_eval": 1,
    }
    assert summary["candidate_source_family_action_counts"] == {
        "seeding_eval:architect_general": 1,
        "three_way_eval:architect_general": 1,
    }
    assert summary["stats"]["skipped_non_target_source_family_file"] == 1


def test_build_plan_can_use_retained_npz_counts_for_deficits(tmp_path: Path) -> None:
    source = tmp_path / "seeding_20260305_203724.jsonl"
    _write_jsonl(
        source,
        [
            {
                "question_id": "q1",
                "suite": "architecture",
                "prompt": "Design the thing",
                "expected": "Use a queue",
                "role_results": {
                    "architect_general:delegated": {
                        "answer": "Use a queue with backpressure",
                        "passed": True,
                    },
                },
            }
        ],
    )
    retained_npz = tmp_path / "retained.npz"
    np.savez(
        retained_npz,
        metadata=np.asarray(
            [
                {
                    "source_path": str(source),
                    "canonical_action": "frontdoor",
                }
            ],
            dtype=object,
        ),
    )

    candidates, summary = mod.build_plan(
        argparse.Namespace(
            input=[source],
            existing_manifest=None,
            existing_npz=retained_npz,
            existing_summary=None,
            target_actions="frontdoor,architect_general",
            target_source_families="seeding_eval",
            min_action_rows=30,
            min_source_family_action_rows=2,
            max_candidates_per_action=20,
        )
    )

    assert len(candidates) == 1
    assert summary["existing_action_counts"] == {"frontdoor": 1}
    assert summary["existing_source_family_action_counts"] == {
        "seeding_eval:frontdoor": 1
    }
    assert summary["recommended_sources"][0]["target_source_family_action_counts"] == {
        "seeding_eval:architect_general": 1
    }
