from __future__ import annotations

import json
from pathlib import Path

from scripts.graph_router import reconstruct_answer_equivalence_targets as targets


def test_answer_equivalence_audit_counts_disagreements() -> None:
    rows = [
        {
            "item_id": "exact-positive",
            "suite": "simpleqa",
            "role_key": "frontdoor",
            "reference": "Paris",
            "response": "Paris",
            "binary_reward": 1.0,
        },
        {
            "item_id": "contained-positive-mislabeled",
            "suite": "simpleqa",
            "role_key": "frontdoor",
            "reference": "Paris",
            "response": "The answer is Paris.",
            "binary_reward": 0.0,
        },
        {
            "item_id": "wrong-negative",
            "suite": "simpleqa",
            "role_key": "frontdoor",
            "reference": "Paris",
            "response": "Lyon",
            "binary_reward": 0.0,
        },
    ]

    summary, disagreements = targets.audit_rows(rows)

    assert summary["counts"]["rows"] == 3
    assert summary["counts"]["agreement"] == 2
    assert summary["counts"]["disagreement"] == 1
    assert summary["disagreements"]["by_type"] == {
        "current_negative_deterministically_equivalent": 1
    }
    assert disagreements[0]["item_id"] == "contained-positive-mislabeled"
    assert disagreements[0]["equivalence_proxy_label"] == 1
    assert "reference" not in disagreements[0]
    assert "response" not in disagreements[0]


def test_answer_equivalence_audit_can_export_agreed_negative_candidates() -> None:
    rows = [
        {
            "item_id": "agreed-negative",
            "suite": "simpleqa",
            "role_key": "frontdoor",
            "reference": "Paris",
            "response": "Lyon",
            "binary_reward": 0.0,
        },
        {
            "item_id": "agreed-positive",
            "suite": "simpleqa",
            "role_key": "frontdoor",
            "reference": "Paris",
            "response": "Paris",
            "binary_reward": 1.0,
        },
    ]

    default_summary, default_candidates = targets.audit_rows(rows)
    expanded_summary, expanded_candidates = targets.audit_rows(rows, include_agreed_negatives=True)

    assert default_summary["counts"]["agreement"] == 2
    assert default_candidates == []
    assert expanded_summary["review_candidates"]["included_agreed_negative"] == 1
    assert expanded_summary["review_candidates"]["by_type"] == {
        "agreed_negative_not_equivalent": 1
    }
    assert expanded_candidates[0]["item_id"] == "agreed-negative"
    assert expanded_candidates[0]["truth_label"] == 0
    assert expanded_candidates[0]["equivalence_proxy_label"] == 0
    assert "reference" not in expanded_candidates[0]
    assert "response" not in expanded_candidates[0]


def test_negative_marker_exact_is_recoverable_positive() -> None:
    features = targets.equivalence_features("NONE", "none")

    assert features["normalized_exact"] is True
    assert features["negative_marker_exact"] is True
    assert targets.proxy_label(features, f1_threshold=0.8) == 1


def test_cli_writes_prompt_free_outputs(tmp_path: Path) -> None:
    input_path = tmp_path / "rows.jsonl"
    rows = [
        {
            "item_id": "a",
            "suite": "math",
            "role_key": "worker",
            "reference": "42",
            "response": "42",
            "binary_reward": 1.0,
        },
        {
            "item_id": "b",
            "suite": "math",
            "role_key": "worker",
            "reference": "42",
            "response": "43",
            "binary_reward": 1.0,
        },
    ]
    input_path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    summary_json = tmp_path / "summary.json"
    summary_md = tmp_path / "summary.md"
    disagreements = tmp_path / "disagreements.jsonl"

    assert targets.main(
        [
            "--input-jsonl",
            str(input_path),
            "--summary-json",
            str(summary_json),
            "--summary-md",
            str(summary_md),
            "--disagreements-jsonl",
            str(disagreements),
        ]
    ) == 0

    summary = json.loads(summary_json.read_text())
    out_rows = [json.loads(line) for line in disagreements.read_text().splitlines()]
    assert summary["schema_version"] == "answer_equivalence_target_audit.v1"
    assert len(out_rows) == 1
    assert "reference" not in out_rows[0]
    assert "response" not in out_rows[0]
    assert "Answer-Equivalence Target Audit" in summary_md.read_text()
