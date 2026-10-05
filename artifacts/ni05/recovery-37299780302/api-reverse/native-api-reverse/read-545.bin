from __future__ import annotations

import json
from pathlib import Path

from scripts.graph_router import build_offline_reward_pairwise_contract as mod


def _manifest_row(
    *,
    item_id: str,
    role_key: str,
    label: int,
    score: float,
    source_path: str = "/tmp/source.json",
    offset: int = 0,
    question_id: str = "q1",
    suite: str = "math",
    answer_chars: int = 10,
    elapsed: float = 1.0,
) -> dict:
    return {
        "schema_version": "offline_reward_feature_input.v1",
        "item_id": item_id,
        "join_key": f"{source_path}:{offset}:{role_key}:{item_id}",
        "question_id": question_id,
        "suite": suite,
        "role_key": role_key,
        "source_path": source_path,
        "source_record_index": offset + 1,
        "source_record_offset": offset,
        "source_record_index_base": "one_based",
        "source_record_count": 1,
        "source_role": role_key,
        "source_passed": bool(label),
        "source_elapsed_seconds": elapsed,
        "source_error_present": False,
        "prompt_sha256": "prompt-hash",
        "expected_sha256": "expected-hash",
        "answer_sha256": f"answer-{item_id}",
        "prompt_chars": 100,
        "expected_chars": 5,
        "answer_chars": answer_chars,
        "feature_context": {
            "task_type": "general",
            "task_type_onehot": [0.0, 0.0, 0.0, 0.0, 1.0],
            "source_family": "seeding_eval",
            "source_family_onehot": [0.0, 1.0, 0.0, 0.0],
            "context_length_chars": 100,
            "has_images": False,
            "expected_classifier_feature_dim_without_embedding": 11,
        },
        "oracle_binary_label": label,
        "oracle_score": score,
        "oracle_threshold": 0.86,
        "oracle_score_source": "reference_token_coverage",
        "target_binary_label": label,
        "target_source": "answer_equivalence_final_label",
        "label_source": "reference_token_coverage@0.86",
        "label_status": "oracle_labeled",
    }


def test_pairwise_contract_builds_within_task_preferences() -> None:
    rows = [
        _manifest_row(item_id="pos", role_key="frontdoor", label=1, score=0.9),
        _manifest_row(item_id="neg", role_key="coder_primary", label=0, score=0.2),
    ]

    pairs, summary = mod.build_pairwise_contract(
        rows,
        min_pairs=1,
        min_cross_action_pairs=1,
        generated_at="2026-06-21T00:00:00+00:00",
    )

    assert summary["schema_version"] == mod.SUMMARY_SCHEMA_VERSION
    assert summary["decision"]["status"] == "contract_ready"
    assert summary["decision"]["runtime_gate_change_allowed"] is False
    assert summary["coverage"]["pair_rows"] == 1
    assert summary["coverage"]["cross_action_pair_rows"] == 1
    assert summary["coverage"]["same_action_pair_rows"] == 0
    assert summary["coverage"]["action_pair_counts"] == {"frontdoor>coder_escalation": 1}
    assert pairs[0]["schema_version"] == mod.PAIRWISE_ROW_SCHEMA_VERSION
    assert pairs[0]["preferred_item_id"] == "pos"
    assert pairs[0]["rejected_item_id"] == "neg"
    assert pairs[0]["preferred_canonical_action"] == "frontdoor"
    assert pairs[0]["rejected_canonical_action"] == "coder_escalation"
    assert "prompt" not in pairs[0]
    assert "answer" not in pairs[0]
    assert "expected" not in pairs[0]


def test_pairwise_contract_remaps_legacy_architect_alias() -> None:
    rows = [
        _manifest_row(
            item_id="pos",
            role_key="architect_coding:delegated",  # stack-change-guard: allow retired-role remap fixture
            label=1,
            score=0.95,
        ),
        _manifest_row(item_id="neg", role_key="frontdoor:direct", label=0, score=0.1),
    ]

    pairs, summary = mod.build_pairwise_contract(
        rows,
        min_pairs=1,
        min_cross_action_pairs=1,
    )

    assert summary["coverage"]["action_pair_counts"] == {"architect_general>frontdoor": 1}
    assert pairs[0]["preferred_canonical_action"] == "architect_general"
    assert pairs[0]["rejected_canonical_action"] == "frontdoor"


def test_pairwise_contract_skips_groups_without_label_contrast() -> None:
    rows = [
        _manifest_row(item_id="pos-a", role_key="frontdoor", label=1, score=0.9),
        _manifest_row(item_id="pos-b", role_key="coder_escalation", label=1, score=0.8),
    ]

    pairs, summary = mod.build_pairwise_contract(rows, min_pairs=1)

    assert pairs == []
    assert summary["decision"]["status"] == "insufficient_contrast"
    assert summary["coverage"]["skipped_no_contrast_groups"] == 1


def test_pairwise_contract_score_ordered_expands_beyond_binary_contrast() -> None:
    rows = [
        _manifest_row(item_id="pos-a", role_key="frontdoor", label=1, score=0.95),
        _manifest_row(item_id="pos-b", role_key="architect_general", label=1, score=0.90),
        _manifest_row(item_id="neg-a", role_key="coder_escalation", label=0, score=0.20),
    ]

    binary_pairs, binary_summary = mod.build_pairwise_contract(
        rows,
        min_pairs=1,
        min_cross_action_pairs=1,
        pairing_mode="binary_label",
    )
    score_pairs, score_summary = mod.build_pairwise_contract(
        rows,
        min_pairs=1,
        min_cross_action_pairs=1,
        pairing_mode="score_ordered",
        min_score_delta=0.01,
    )

    assert len(binary_pairs) == 2
    assert len(score_pairs) == 3
    assert score_summary["contract"]["pairing_mode"] == "score_ordered"
    assert score_summary["contract"]["learning_target"] == "within_source_record_score_ordered_preference"
    assert score_summary["coverage"]["cross_action_pair_rows"] == 3
    assert score_pairs[0]["pairing_mode"] == "score_ordered"
    assert all(pair["preferred_oracle_score"] > pair["rejected_oracle_score"] for pair in score_pairs)


def test_pairwise_contract_score_ordered_skips_equal_score_ties() -> None:
    rows = [
        _manifest_row(item_id="a", role_key="frontdoor", label=1, score=0.5),
        _manifest_row(item_id="b", role_key="architect_general", label=0, score=0.5),
        _manifest_row(item_id="c", role_key="coder_escalation", label=0, score=0.5),
    ]

    pairs, summary = mod.build_pairwise_contract(
        rows,
        min_pairs=1,
        min_cross_action_pairs=1,
        pairing_mode="score_ordered",
        min_score_delta=0.0,
    )

    assert pairs == []
    assert summary["decision"]["status"] == "insufficient_contrast"
    assert summary["coverage"]["skipped_no_contrast_groups"] == 1


def test_pairwise_contract_rejects_private_text_fields() -> None:
    rows = [
        {
            **_manifest_row(item_id="pos", role_key="frontdoor", label=1, score=0.9),
            "prompt": "private text",
        },
        _manifest_row(item_id="neg", role_key="coder_escalation", label=0, score=0.1),
    ]

    try:
        mod.build_pairwise_contract(rows, min_pairs=1)
    except mod.PairwiseContractError as exc:
        assert "private fields present: prompt" in str(exc)
    else:
        raise AssertionError("expected PairwiseContractError")


def test_cli_writes_jsonl_summary_and_markdown(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.jsonl"
    manifest.write_text(
        "\n".join(
            json.dumps(row, sort_keys=True)
            for row in [
                _manifest_row(item_id="pos", role_key="frontdoor", label=1, score=0.9),
                _manifest_row(item_id="neg", role_key="coder_escalation", label=0, score=0.1),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    out_jsonl = tmp_path / "pairs.jsonl"
    summary_json = tmp_path / "summary.json"
    summary_md = tmp_path / "summary.md"

    assert mod.main(
        [
            "--manifest-jsonl",
            str(manifest),
            "--output-jsonl",
            str(out_jsonl),
            "--summary-json",
            str(summary_json),
            "--summary-md",
            str(summary_md),
            "--min-pairs",
            "1",
            "--min-cross-action-pairs",
            "1",
            "--generated-at",
            "2026-06-21T00:00:00+00:00",
        ]
    ) == 0

    assert len(out_jsonl.read_text(encoding="utf-8").strip().splitlines()) == 1
    assert json.loads(summary_json.read_text(encoding="utf-8"))["decision"]["status"] == "contract_ready"
    assert "# Offline Reward Pairwise Contract" in summary_md.read_text(encoding="utf-8")


def test_candidate_only_manifest_cannot_overwrite_broad_contract(tmp_path: Path) -> None:
    manifest = tmp_path / "offline_reward_feature_manifest_pairwise_holdout_expansion.jsonl"
    manifest.write_text(
        "\n".join(
            json.dumps(row, sort_keys=True)
            for row in [
                _manifest_row(item_id="pos", role_key="frontdoor", label=1, score=0.9),
                _manifest_row(item_id="neg", role_key="coder_escalation", label=0, score=0.1),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    assert (
        mod.main(
            [
                "--manifest-jsonl",
                str(manifest),
                "--output-jsonl",
                str(tmp_path / "offline_reward_pairwise_preference_contract_score_ordered.jsonl"),
                "--summary-json",
                str(tmp_path / "summary.json"),
                "--pairing-mode",
                "score_ordered",
            ]
        )
        == 2
    )


def test_candidate_only_scope_records_distinct_artifact_mode(tmp_path: Path) -> None:
    manifest = tmp_path / "offline_reward_feature_manifest_pairwise_expanded_gap.jsonl"
    manifest.write_text(
        "\n".join(
            json.dumps(row, sort_keys=True)
            for row in [
                _manifest_row(item_id="pos", role_key="frontdoor", label=1, score=0.9),
                _manifest_row(item_id="neg", role_key="coder_escalation", label=0, score=0.1),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    out_jsonl = tmp_path / "offline_reward_pairwise_preference_contract_candidate_only_expanded_gap.jsonl"
    summary_json = tmp_path / "summary.json"

    assert (
        mod.main(
            [
                "--manifest-jsonl",
                str(manifest),
                "--output-jsonl",
                str(out_jsonl),
                "--summary-json",
                str(summary_json),
                "--artifact-scope",
                "candidate_only",
                "--min-pairs",
                "1",
                "--min-cross-action-pairs",
                "1",
            ]
        )
        == 0
    )

    payload = json.loads(summary_json.read_text(encoding="utf-8"))
    assert payload["decision"]["status"] == "contract_ready"
    assert payload["artifact_scope"] == {
        "allow_protected_output_overwrite": False,
        "candidate_only_manifest": True,
        "mode": "candidate_only",
        "protected_broad_output": False,
    }
