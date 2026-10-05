"""Tests for the offline reward-oracle evaluation harness."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.graph_router.evaluate_offline_reward_oracle import (
    evaluate,
    load_jsonl,
    main,
)


def _write_jsonl(path: Path, rows: list[dict]) -> Path:
    path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )
    return path


def test_evaluate_oracle_scores_against_binary_rewards_and_stress_rows(
    tmp_path: Path,
) -> None:
    data = _write_jsonl(
        tmp_path / "oracle_rows.jsonl",
        [
            {
                "item_id": "a-base",
                "reference": "Paris",
                "response": "Paris",
                "oracle_score": 0.95,
                "binary_reward": 1.0,
                "role_key": "frontdoor",
                "suite": "general",
                "target_source": "answer_equivalence_final_label",
                "variant_group": "a",
                "variant_type": "base",
            },
            {
                "item_id": "a-para",
                "reference": "Paris",
                "response": "The French capital is Paris.",
                "oracle_score": 0.9,
                "binary_reward": 1.0,
                "role_key": "frontdoor",
                "suite": "general",
                "target_source": "answer_equivalence_final_label",
                "variant_group": "a",
                "variant_type": "paraphrase",
            },
            {
                "item_id": "a-confound",
                "reference": "Paris",
                "response": "Lyon",
                "oracle_score": 0.2,
                "binary_reward": 0.0,
                "role_key": "frontdoor",
                "suite": "general",
                "target_source": "answer_equivalence_final_label",
                "variant_group": "a",
                "variant_type": "confound",
            },
            {
                "item_id": "b-base",
                "reference": "2",
                "response": "2",
                "oracle_score": 0.8,
                "q_reward": 1.0,
                "role_key": "worker",
                "suite": "math",
                "target_source": "original_binary_reward",
                "variant_group": "b",
                "variant_type": "base",
            },
            {
                "item_id": "b-synonym",
                "reference": "2",
                "response": "two",
                "oracle_score": 0.3,
                "q_reward": 1.0,
                "role_key": "worker",
                "suite": "math",
                "target_source": "original_binary_reward",
                "variant_group": "b",
                "variant_type": "synonym",
            },
            {
                "item_id": "b-wrong",
                "reference": "2",
                "response": "3",
                "oracle_score": 0.1,
                "q_reward": 0.0,
                "role_key": "worker",
                "suite": "math",
                "target_source": "original_binary_reward",
                "variant_group": "b",
                "variant_type": "confound",
            },
        ],
    )

    rows = load_jsonl(data, target_threshold=0.5)
    summary = evaluate(rows, oracle_threshold=0.5)

    assert summary["n"] == 6
    assert summary["target_positive"] == 4
    assert summary["target_negative"] == 2
    assert summary["score"]["spearman"] is not None
    assert summary["score"]["spearman"] > 0.5
    assert summary["score"]["agreement_at_threshold"] == 5 / 6
    assert summary["score"]["confusion"] == {"tp": 3, "fp": 0, "fn": 1, "tn": 2}
    assert summary["decision_gate"]["schema_version"] == (
        "offline_reward_oracle_decision_gate.v1"
    )
    assert summary["decision_gate"]["status"] == "blocked"
    assert "too_few_rows" in summary["decision_gate"]["blockers"]
    assert (
        "answer_equivalence_final_label:too_few_negatives"
        in summary["decision_gate"]["blockers"]
    )
    assert summary["calibration"]["schema_version"] == (
        "offline_reward_oracle_calibration.v1"
    )
    assert summary["calibration"]["threshold_count"] == 101
    assert summary["calibration"]["best"]["f1"]["threshold"] == 0.21
    assert summary["calibration"]["best"]["f1"]["confusion"] == {
        "tp": 4,
        "fp": 0,
        "fn": 0,
        "tn": 2,
    }
    assert summary["calibration"]["best"]["no_false_positive"]["threshold"] == 0.21
    assert summary["calibration"]["best"]["no_false_positive"]["confusion"] == {
        "tp": 4,
        "fp": 0,
        "fn": 0,
        "tn": 2,
    }
    assert summary["stress"]["groups_evaluated"] == 2
    assert summary["stress"]["paraphrase_total"] == 2
    assert summary["stress"]["paraphrase_penalized"] == 1
    assert summary["stress"]["confound_fooled"] == 0
    assert summary["slices"]["target_source"]["answer_equivalence_final_label"][
        "confusion"
    ] == {"tp": 2, "fp": 0, "fn": 0, "tn": 1}
    assert summary["slices"]["target_source"]["original_binary_reward"][
        "confusion"
    ] == {"tp": 1, "fp": 0, "fn": 1, "tn": 1}
    assert summary["slices"]["suite"]["general"]["n"] == 3
    assert summary["slices"]["role_key"]["worker"]["target_positive"] == 2


def test_target_score_overrides_legacy_binary_reward(tmp_path: Path) -> None:
    data = _write_jsonl(
        tmp_path / "oracle_rows.jsonl",
        [
            {
                "item_id": "manual-positive",
                "reference": "Paris",
                "response": "Paris",
                "oracle_score": 0.9,
                "binary_reward": 0.0,
                "target_score": 1.0,
            },
            {
                "item_id": "manual-negative",
                "reference": "Paris",
                "response": "Lyon",
                "oracle_score": 0.1,
                "binary_reward": 1.0,
                "target_score": 0.0,
            },
        ],
    )

    rows = load_jsonl(data, target_threshold=0.5)

    assert [row.target_score for row in rows] == [1.0, 0.0]
    assert [row.binary_target for row in rows] == [1, 0]


def test_cli_writes_json_and_markdown(tmp_path: Path) -> None:
    data = _write_jsonl(
        tmp_path / "oracle_rows.jsonl",
        [
            {
                "reference": "yes",
                "response": "yes",
                "oracle_score": 0.9,
                "outcome": "success",
            },
            {
                "reference": "yes",
                "response": "no",
                "oracle_score": 0.2,
                "outcome": "failure",
            },
        ],
    )
    out_json = tmp_path / "summary.json"
    out_md = tmp_path / "summary.md"

    assert main(
        [
            "--input",
            str(data),
            "--output-json",
            str(out_json),
            "--output-md",
            str(out_md),
        ]
    ) == 0

    summary = json.loads(out_json.read_text(encoding="utf-8"))
    assert summary["schema_version"] == "offline_reward_oracle_eval.v1"
    assert summary["score"]["agreement_at_threshold"] == 1.0
    assert summary["slices"]["target_source"]["unspecified"]["n"] == 2
    assert summary["decision_gate"]["status"] == "blocked"
    assert summary["calibration"]["best"]["f1"]["threshold"] == 0.21
    assert "Offline Reward-Oracle Evaluation" in out_md.read_text(encoding="utf-8")
    assert "Decision Gate" in out_md.read_text(encoding="utf-8")
    assert "Best no-false-positive recall" in out_md.read_text(encoding="utf-8")
    assert "### Target source" in out_md.read_text(encoding="utf-8")


def test_decision_gate_passes_only_with_required_slice_and_stress_rows(
    tmp_path: Path,
) -> None:
    rows: list[dict] = []
    for index in range(34):
        group = f"ae-{index}"
        rows.extend(
            [
                {
                    "item_id": f"ae-base-{index}",
                    "reference": "correct",
                    "response": "correct",
                    "oracle_score": 0.95,
                    "binary_reward": 1.0,
                    "target_source": "answer_equivalence_final_label",
                    "suite": "general",
                    "role_key": "frontdoor",
                    "variant_group": group,
                    "variant_type": "base",
                },
                {
                    "item_id": f"ae-para-{index}",
                    "reference": "correct",
                    "response": "also correct",
                    "oracle_score": 0.9,
                    "binary_reward": 1.0,
                    "target_source": "answer_equivalence_final_label",
                    "suite": "general",
                    "role_key": "frontdoor",
                    "variant_group": group,
                    "variant_type": "paraphrase",
                },
                {
                    "item_id": f"ae-confound-{index}",
                    "reference": "correct",
                    "response": "wrong",
                    "oracle_score": 0.05,
                    "binary_reward": 0.0,
                    "target_source": "answer_equivalence_final_label",
                    "suite": "general",
                    "role_key": "frontdoor",
                    "variant_group": group,
                    "variant_type": "confound",
                },
            ]
        )
    rows.extend(
        [
            {
                "item_id": "original-pos-1",
                "reference": "2",
                "response": "2",
                "oracle_score": 0.9,
                "q_reward": 1.0,
                "target_source": "original_binary_reward",
                "suite": "math",
                "role_key": "worker",
            },
            {
                "item_id": "original-pos-2",
                "reference": "2",
                "response": "two",
                "oracle_score": 0.85,
                "q_reward": 1.0,
                "target_source": "original_binary_reward",
                "suite": "math",
                "role_key": "worker",
            },
            {
                "item_id": "original-neg-1",
                "reference": "2",
                "response": "3",
                "oracle_score": 0.1,
                "q_reward": 0.0,
                "target_source": "original_binary_reward",
                "suite": "math",
                "role_key": "worker",
            },
            {
                "item_id": "original-neg-2",
                "reference": "2",
                "response": "4",
                "oracle_score": 0.05,
                "q_reward": 0.0,
                "target_source": "original_binary_reward",
                "suite": "math",
                "role_key": "worker",
            },
        ]
    )
    data = _write_jsonl(tmp_path / "oracle_rows.jsonl", rows)

    summary = evaluate(load_jsonl(data, target_threshold=0.5), oracle_threshold=0.5)

    assert summary["n"] == 106
    assert summary["decision_gate"]["status"] == "decision_grade"
    assert summary["decision_gate"]["blockers"] == []
    assert summary["decision_gate"]["slice_checks"][
        "answer_equivalence_final_label"
    ]["target_negative"]["passed"] is True
