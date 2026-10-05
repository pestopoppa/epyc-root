from __future__ import annotations

import json
from pathlib import Path

from scripts.graph_router import prepare_answer_equivalence_review as review


def test_prepare_review_writes_private_packet_and_redacted_manifest(tmp_path: Path) -> None:
    source = tmp_path / "source.json"
    source.write_text(
        json.dumps(
            {
                "results": [
                    {
                        "suite": "general",
                        "question_id": "q1",
                        "prompt": "private prompt",
                        "expected": "private reference",
                        "role_results": {
                            "frontdoor": {
                                "answer": "private response",
                                "passed": False,
                            }
                        },
                    }
                ]
            }
        )
    )
    disagreements = [
        {
            "item_id": "source:0:frontdoor",
            "source_path": str(source),
            "source_record_index": 0,
            "question_id": "q1",
            "suite": "general",
            "role_key": "frontdoor",
            "truth_label": 0,
            "equivalence_proxy_label": 1,
            "q_reward": -0.5,
            "binary_reward": 0.0,
            "oracle_score": None,
            "token_f1": 1.0,
        }
    ]

    summary = review.prepare_review(
        disagreements,
        private_review_jsonl=tmp_path / "private.jsonl",
        public_manifest_jsonl=tmp_path / "manifest.jsonl",
        summary_json=tmp_path / "summary.json",
        summary_md=tmp_path / "summary.md",
    )

    private_rows = [json.loads(line) for line in (tmp_path / "private.jsonl").read_text().splitlines()]
    public_rows = [json.loads(line) for line in (tmp_path / "manifest.jsonl").read_text().splitlines()]
    assert summary["review_rows"] == 1
    assert private_rows[0]["prompt"] == "private prompt"
    assert private_rows[0]["reference"] == "private reference"
    assert private_rows[0]["response"] == "private response"
    assert private_rows[0]["final_label"] is None
    assert private_rows[0]["source_passed"] is False
    assert private_rows[0]["label_status"] == "needs_semantic_judge"
    assert public_rows[0]["label_status"] == "needs_semantic_judge"
    assert public_rows[0]["disagreement_type"] == "current_negative_deterministically_equivalent"
    assert public_rows[0]["review_bucket"] == "current_negative_deterministically_equivalent"
    assert public_rows[0]["final_label"] is None
    assert "prompt" not in public_rows[0]
    assert "reference" not in public_rows[0]
    assert "response" not in public_rows[0]
    assert "answer" not in public_rows[0]
    assert "private prompt" not in (tmp_path / "summary.md").read_text()


def test_source_passed_positive_disagreement_gets_seeded_equivalent_label(tmp_path: Path) -> None:
    source = tmp_path / "source.json"
    source.write_text(
        json.dumps(
            {
                "results": [
                    {
                        "suite": "debugbench",
                        "question_id": "q1",
                        "prompt": "private prompt",
                        "expected": "private reference",
                        "role_results": {
                            "frontdoor": {
                                "answer": "different but passing implementation",
                                "passed": True,
                                "error_type": "none",
                            }
                        },
                    }
                ]
            }
        )
    )

    summary = review.prepare_review(
        [
            {
                "item_id": "source:0:frontdoor",
                "source_path": str(source),
                "source_record_index": 0,
                "question_id": "q1",
                "suite": "debugbench",
                "role_key": "frontdoor",
                "truth_label": 1,
                "equivalence_proxy_label": 0,
            }
        ],
        private_review_jsonl=tmp_path / "private.jsonl",
        public_manifest_jsonl=tmp_path / "manifest.jsonl",
        summary_json=tmp_path / "summary.json",
        summary_md=tmp_path / "summary.md",
    )

    row = json.loads((tmp_path / "manifest.jsonl").read_text())
    assert row["source_passed"] is True
    assert row["semantic_label"] == "equivalent"
    assert row["final_label"] == "equivalent"
    assert row["label_source"] == "source_passed_true"
    assert row["label_status"] == "seeded"
    assert summary["by_label_status"] == {"seeded": 1}
    assert summary["by_final_label"] == {"equivalent": 1}
    assert summary["status"] == "labeling_complete"


def test_agreed_negative_gets_seeded_not_equivalent_label(tmp_path: Path) -> None:
    source = tmp_path / "source.json"
    source.write_text(
        json.dumps(
            {
                "results": [
                    {
                        "suite": "simpleqa",
                        "question_id": "q1",
                        "prompt": "private prompt",
                        "expected": "private reference",
                        "role_results": {
                            "frontdoor": {
                                "answer": "wrong answer",
                                "passed": False,
                            }
                        },
                    }
                ]
            }
        )
    )

    summary = review.prepare_review(
        [
            {
                "item_id": "source:0:frontdoor",
                "source_path": str(source),
                "source_record_index": 0,
                "question_id": "q1",
                "suite": "simpleqa",
                "role_key": "frontdoor",
                "truth_label": 0,
                "equivalence_proxy_label": 0,
            }
        ],
        private_review_jsonl=tmp_path / "private.jsonl",
        public_manifest_jsonl=tmp_path / "manifest.jsonl",
        summary_json=tmp_path / "summary.json",
        summary_md=tmp_path / "summary.md",
    )

    row = json.loads((tmp_path / "manifest.jsonl").read_text())
    assert row["disagreement_type"] == "agreed_negative_not_equivalent"
    assert row["semantic_label"] == "not_equivalent"
    assert row["final_label"] == "not_equivalent"
    assert row["label_source"] == "target_proxy_agreed_negative"
    assert row["label_status"] == "seeded"
    assert summary["by_label_status"] == {"seeded": 1}
    assert summary["by_final_label"] == {"not_equivalent": 1}
    assert summary["status"] == "labeling_complete"


def test_manual_label_overlay_sets_final_label_without_public_private_text(tmp_path: Path) -> None:
    source = tmp_path / "source.json"
    source.write_text(
        json.dumps(
            {
                "results": [
                    {
                        "suite": "instruction_precision",
                        "question_id": "q1",
                        "prompt": "private prompt",
                        "expected": "private reference",
                        "role_results": {
                            "frontdoor": {
                                "answer": "private response",
                                "passed": False,
                            }
                        },
                    }
                ]
            }
        )
    )
    manual_labels = review.load_manual_labels(
        _write_jsonl(
            tmp_path / "manual.jsonl",
            [
                {
                    "schema_version": review.MANUAL_LABEL_SCHEMA,
                    "item_id": "source:0:frontdoor",
                    "manual_label": "not_equivalent",
                    "label_source": "manual_codex_review_20260621",
                    "label_status": "manual_reviewed",
                    "review_note_code": "extra_disallowed_content_and_code",
                }
            ],
        )
    )

    summary = review.prepare_review(
        [
            {
                "item_id": "source:0:frontdoor",
                "source_path": str(source),
                "source_record_index": 0,
                "question_id": "q1",
                "suite": "instruction_precision",
                "role_key": "frontdoor",
                "truth_label": 0,
                "equivalence_proxy_label": 1,
            }
        ],
        private_review_jsonl=tmp_path / "private.jsonl",
        public_manifest_jsonl=tmp_path / "manifest.jsonl",
        summary_json=tmp_path / "summary.json",
        summary_md=tmp_path / "summary.md",
        manual_labels=manual_labels,
    )

    private_row = json.loads((tmp_path / "private.jsonl").read_text())
    public_row = json.loads((tmp_path / "manifest.jsonl").read_text())
    assert private_row["manual_label"] == "not_equivalent"
    assert public_row["manual_label"] == "not_equivalent"
    assert public_row["semantic_label"] == "not_equivalent"
    assert public_row["final_label"] == "not_equivalent"
    assert public_row["label_source"] == "manual_codex_review_20260621"
    assert public_row["label_status"] == "manual_reviewed"
    assert public_row["review_note_code"] == "extra_disallowed_content_and_code"
    assert "prompt" not in public_row
    assert "reference" not in public_row
    assert "response" not in public_row
    assert "answer" not in public_row
    assert "private prompt" not in (tmp_path / "summary.md").read_text()
    assert summary["status"] == "labeling_complete"
    assert summary["manual_label_rows"] == 1
    assert summary["by_label_status"] == {"manual_reviewed": 1}
    assert summary["by_final_label"] == {"not_equivalent": 1}


def test_manual_label_overlay_rejects_private_fields(tmp_path: Path) -> None:
    manual_path = _write_jsonl(
        tmp_path / "manual.jsonl",
        [
            {
                "schema_version": review.MANUAL_LABEL_SCHEMA,
                "item_id": "source:0:frontdoor",
                "manual_label": "equivalent",
                "response": "private response must not be committed",
            }
        ],
    )

    try:
        review.load_manual_labels(manual_path)
    except SystemExit as exc:
        assert "private field response" in str(exc)
    else:
        raise AssertionError("expected private-field manual label rejection")


def test_role_key_with_colon_matches_exact_role_result(tmp_path: Path) -> None:
    source = tmp_path / "source.jsonl"
    source.write_text(
        json.dumps(
            {
                "suite": "debugbench",
                "question_id": "q2",
                "prompt": "p",
                "expected": "e",
                "role_results": {"frontdoor:direct": {"answer": "a"}},
            }
        )
        + "\n"
    )

    row = review._private_review_row(
        {
            "item_id": "source:0:frontdoor_direct",
            "source_path": str(source),
            "source_record_index": 0,
            "role_key": "frontdoor:direct",
            "truth_label": 1,
            "equivalence_proxy_label": 0,
        }
    )

    assert row["role_key"] == "frontdoor:direct"
    assert row["response"] == "a"


def test_source_record_index_can_be_one_based_when_question_id_matches(tmp_path: Path) -> None:
    source = tmp_path / "source.json"
    source.write_text(
        json.dumps(
            {
                "results": [
                    {
                        "suite": "debugbench",
                        "question_id": "q1",
                        "prompt": "p1",
                        "expected": "e1",
                        "role_results": {"frontdoor": {"answer": "a1"}},
                    },
                    {
                        "suite": "debugbench",
                        "question_id": "q2",
                        "prompt": "p2",
                        "expected": "e2",
                        "role_results": {"frontdoor": {"answer": "a2"}},
                    },
                ]
            }
        )
    )

    row = review._private_review_row(
        {
            "item_id": "source:2:frontdoor",
            "source_path": str(source),
            "source_record_index": 2,
            "question_id": "q2",
            "role_key": "frontdoor",
            "truth_label": 1,
            "equivalence_proxy_label": 0,
        }
    )

    assert row["prompt"] == "p2"
    assert row["reference"] == "e2"
    assert row["response"] == "a2"


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> Path:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    return path
