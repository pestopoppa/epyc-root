from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from scripts.graph_router import evaluate_offline_reward_pairwise_ranker as mod


def _pair_row(
    *,
    pair_id: str,
    group_key: str,
    preferred_action: str,
    rejected_action: str,
    source_family: str = "seeding_eval",
    suite: str = "math",
    answer_delta: float = 1.0,
    elapsed_delta: float = -0.5,
) -> dict:
    return {
        "schema_version": "offline_reward_pairwise_preference.v1",
        "contract_name": "within_task_pairwise_preference_v1",
        "pair_id": pair_id,
        "group_key": group_key,
        "question_id": group_key,
        "suite": suite,
        "source_path": "/tmp/source.jsonl",
        "source_record_offset": 0,
        "source_family": source_family,
        "prompt_sha256": "p",
        "expected_sha256": "e",
        "preferred_item_id": f"{pair_id}:preferred",
        "rejected_item_id": f"{pair_id}:rejected",
        "preferred_role_key": preferred_action,
        "rejected_role_key": rejected_action,
        "preferred_canonical_action": preferred_action,
        "rejected_canonical_action": rejected_action,
        "preferred_oracle_score": 0.9,
        "rejected_oracle_score": 0.1,
        "oracle_score_delta": 0.8,
        "label_source": "reference_token_coverage@0.86",
        "target_source": "answer_equivalence_final_label",
        "preferred_answer_chars": 20,
        "rejected_answer_chars": 10,
        "answer_chars_log_delta": answer_delta,
        "elapsed_log_delta": elapsed_delta,
        "preferred_error_present": False,
        "rejected_error_present": False,
    }


def test_build_symmetric_examples_flips_signed_features_only() -> None:
    rows = [
        _pair_row(
            pair_id="p1",
            group_key="g1",
            preferred_action="frontdoor",
            rejected_action="coder_escalation",
            source_family="three_way_eval",
            suite="debugbench",
        )
    ]
    encoders = mod.build_encoders(rows)

    x, y, metadata = mod.build_symmetric_examples(rows, encoders)

    assert x.shape == (2, len(encoders.feature_names))
    assert y.tolist() == [1.0, 0.0]
    action_width = len(encoders.actions)
    np.testing.assert_allclose(x[1, :action_width], -x[0, :action_width])
    np.testing.assert_allclose(x[1, -3:], -x[0, -3:])
    np.testing.assert_allclose(x[1, action_width:-3], x[0, action_width:-3])
    assert metadata[0]["preferred_canonical_action"] == "frontdoor"
    assert metadata[1]["preferred_canonical_action"] == "coder_escalation"
    assert metadata[1]["flipped"] is True


def test_interaction_feature_contract_flips_only_signed_features() -> None:
    rows = [
        _pair_row(
            pair_id="p1",
            group_key="g1",
            preferred_action="frontdoor",
            rejected_action="coder_escalation",
            source_family="three_way_eval",
            suite="debugbench",
        ),
        _pair_row(
            pair_id="p2",
            group_key="g2",
            preferred_action="architect_general",
            rejected_action="frontdoor",
            source_family="seeding_eval",
            suite="math",
        ),
    ]
    encoders = mod.build_encoders(rows, feature_contract=mod.INTERACTION_FEATURE_CONTRACT)

    x, y, metadata = mod.build_symmetric_examples(rows[:1], encoders)

    assert encoders.feature_contract == mod.INTERACTION_FEATURE_CONTRACT
    assert any(name.startswith("action_pair_direction[") for name in encoders.feature_names)
    assert any(name.startswith("source_action_delta[") for name in encoders.feature_names)
    assert y.tolist() == [1.0, 0.0]
    signed = set(encoders.signed_feature_indexes)
    for idx in range(x.shape[1]):
        if idx in signed:
            assert x[1, idx] == -x[0, idx]
        else:
            assert x[1, idx] == x[0, idx]
    assert metadata[1]["preferred_canonical_action"] == "coder_escalation"


def test_load_jsonl_rejects_private_text_fields(tmp_path: Path) -> None:
    path = tmp_path / "pairs.jsonl"
    row = {
        **_pair_row(
            pair_id="p1",
            group_key="g1",
            preferred_action="frontdoor",
            rejected_action="coder_escalation",
        ),
        "prompt": "private text",
    }
    path.write_text(json.dumps(row) + "\n", encoding="utf-8")

    try:
        mod.load_jsonl(path)
    except mod.PairwiseRankerError as exc:
        assert "private fields present: prompt" in str(exc)
    else:
        raise AssertionError("expected PairwiseRankerError")


def test_cli_writes_pairwise_ranker_summary(tmp_path: Path) -> None:
    pairwise_path = tmp_path / "pairs.jsonl"
    rows = [
        _pair_row(
            pair_id=f"frontdoor-{idx}",
            group_key=f"g{idx}",
            preferred_action="frontdoor",
            rejected_action="coder_escalation",
            source_family="seeding_eval" if idx % 2 else "three_way_eval",
            suite="math" if idx % 2 else "debugbench",
            answer_delta=1.0 + idx / 10.0,
        )
        for idx in range(8)
    ]
    pairwise_path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )
    summary_json = tmp_path / "summary.json"
    summary_md = tmp_path / "summary.md"

    assert mod.main(
        [
            "--pairwise-jsonl",
            str(pairwise_path),
            "--summary-json",
            str(summary_json),
            "--summary-md",
            str(summary_md),
            "--families",
            "logistic_l2",
            "--seeds",
            "42,7",
            "--test-split",
            "0.25",
        ]
    ) == 0

    summary = json.loads(summary_json.read_text(encoding="utf-8"))
    assert summary["schema_version"] == mod.SUMMARY_SCHEMA_VERSION
    assert summary["leakage_policy"]["runtime_gate_change_allowed"] is False
    assert summary["leakage_policy"]["uses_prompt_answer_expected_text"] is False
    assert "oracle_score_delta" in summary["leakage_policy"]["target_fields_excluded_from_features"]
    assert summary["input"]["pair_rows"] == 8
    assert summary["input"]["cross_action_pair_rows"] == 8
    assert summary["input"]["pairing_mode_counts"] == {"unknown": 8}
    assert summary["feature_contract"]["symmetric_augmentation"] is True
    assert summary["runs"][0]["train_groups"] >= 1
    assert "# Offline Reward Pairwise Ranker Eval" in summary_md.read_text(encoding="utf-8")


def test_cli_accepts_interaction_feature_contract(tmp_path: Path) -> None:
    pairwise_path = tmp_path / "pairs.jsonl"
    rows = [
        _pair_row(
            pair_id=f"pair-{idx}",
            group_key=f"g{idx}",
            preferred_action="frontdoor" if idx % 2 else "architect_general",
            rejected_action="coder_escalation",
            source_family="seeding_eval" if idx % 2 else "three_way_eval",
            suite="math" if idx % 2 else "debugbench",
            answer_delta=1.0 + idx / 10.0,
        )
        for idx in range(8)
    ]
    pairwise_path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )
    summary_json = tmp_path / "summary.json"
    summary_md = tmp_path / "summary.md"

    assert mod.main(
        [
            "--pairwise-jsonl",
            str(pairwise_path),
            "--summary-json",
            str(summary_json),
            "--summary-md",
            str(summary_md),
            "--families",
            "logistic_l2",
            "--seeds",
            "42",
            "--test-split",
            "0.25",
            "--feature-contract",
            mod.INTERACTION_FEATURE_CONTRACT,
        ]
    ) == 0

    summary = json.loads(summary_json.read_text(encoding="utf-8"))
    assert summary["feature_contract"]["name"] == mod.INTERACTION_FEATURE_CONTRACT
    names = summary["feature_contract"]["feature_names"]
    assert any(name.startswith("action_pair_direction[") for name in names)
    assert any(name.startswith("source_suite[") for name in names)
    assert summary["leakage_policy"]["runtime_gate_change_allowed"] is False


def test_cli_reports_independent_source_family_holdout(tmp_path: Path) -> None:
    pairwise_path = tmp_path / "pairs.jsonl"
    rows = []
    for idx in range(12):
        source_family = "heldout_family" if idx < 4 else "train_family"
        rows.append(
            _pair_row(
                pair_id=f"pair-{idx}",
                group_key=f"g{idx}",
                preferred_action="frontdoor",
                rejected_action="coder_escalation",
                source_family=source_family,
                suite="debugbench" if idx % 2 else "math",
                answer_delta=1.0 + idx / 10.0,
            )
        )
    pairwise_path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )
    summary_json = tmp_path / "summary.json"
    summary_md = tmp_path / "summary.md"

    assert mod.main(
        [
            "--pairwise-jsonl",
            str(pairwise_path),
            "--summary-json",
            str(summary_json),
            "--summary-md",
            str(summary_md),
            "--families",
            "logistic_l2",
            "--seeds",
            "42",
            "--test-split",
            "0.25",
            "--holdout-fields",
            "source_family",
            "--min-holdout-pair-rows",
            "4",
            "--min-train-pair-rows",
            "4",
        ]
    ) == 0

    summary = json.loads(summary_json.read_text(encoding="utf-8"))
    holdout = summary["independent_holdout"]["source_family"]
    assert holdout["eligible_holdout_values"] == ["heldout_family", "train_family"]
    assert holdout["results"]["heldout_family"]["test_pair_rows"] == 4
    assert holdout["results"]["heldout_family"]["train_pair_rows"] == 8
    assert holdout["results"]["heldout_family"]["aggregate"]["decision"]["runtime_gate_change_allowed"] is False
    assert summary["holdout_decision"]["eligible_holdouts"] == 2
    assert summary["holdout_decision"]["runtime_gate_change_allowed"] is False
    assert "Independent Holdout Summary" in summary_md.read_text(encoding="utf-8")


def test_split_group_kfolds_are_group_disjoint() -> None:
    rows = [
        _pair_row(
            pair_id=f"pair-{idx}",
            group_key=f"g{idx}",
            preferred_action="frontdoor",
            rejected_action="coder_escalation",
        )
        for idx in range(6)
    ]

    folds = mod.split_group_kfolds(rows, seed=42, folds=3)

    assert len(folds) == 3
    seen_test_groups = set()
    for train_groups, test_groups in folds:
        assert train_groups
        assert test_groups
        assert train_groups.isdisjoint(test_groups)
        seen_test_groups.update(test_groups)
    assert seen_test_groups == {f"g{idx}" for idx in range(6)}


def test_cli_can_emit_group_disjoint_cross_validation(tmp_path: Path) -> None:
    pairwise_path = tmp_path / "pairs.jsonl"
    rows = [
        _pair_row(
            pair_id=f"pair-{idx}",
            group_key=f"g{idx}",
            preferred_action="frontdoor",
            rejected_action="coder_escalation",
            source_family="seeding_eval" if idx % 2 else "three_way_eval",
            suite="math" if idx % 2 else "debugbench",
            answer_delta=1.0 + idx / 10.0,
        )
        for idx in range(9)
    ]
    pairwise_path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )
    summary_json = tmp_path / "summary.json"
    summary_md = tmp_path / "summary.md"

    assert mod.main(
        [
            "--pairwise-jsonl",
            str(pairwise_path),
            "--summary-json",
            str(summary_json),
            "--summary-md",
            str(summary_md),
            "--families",
            "logistic_l2",
            "--seeds",
            "42",
            "--test-split",
            "0.25",
            "--cv-folds",
            "3",
        ]
    ) == 0

    summary = json.loads(summary_json.read_text(encoding="utf-8"))
    cv = summary["cross_validation"]
    assert cv["folds"] == 3
    assert cv["group_disjoint"] is True
    assert cv["decision"]["runtime_gate_change_allowed"] is False
    assert len(cv["fold_summaries"]) == 3
    assert len(cv["runs"]) == 3
    assert {run["cv_fold"] for run in cv["runs"]} == {1, 2, 3}
    assert "Cross-Validation Summary" in summary_md.read_text(encoding="utf-8")
