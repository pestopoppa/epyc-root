from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.analysis import ri10_canary_request_plan as plan


def _write_config(path: Path, *, mode: str = "canary") -> None:
    path.write_text(
        f"""
factual_risk:
  mode: {mode}
  canary_ratio: 0.25
  canary_roles: [frontdoor, worker_general]
  threshold_low: 0.3
  threshold_high: 0.7
  role_adjustments:
    tier_1: 0.727978
    tier_2: 0.824178
    tier_3: 1.0
  feature_weights:
    has_date_question: 0.15
    has_entity_question: 0.15
    has_citation_request: 0.10
    claim_density: 0.25
    factual_keyword_ratio: 0.20
    uncertainty_markers: 0.15
""",
        encoding="utf-8",
    )


def _write_dataset(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n",
        encoding="utf-8",
    )


def test_build_plan_balances_expected_canary_arms(tmp_path: Path) -> None:
    config = tmp_path / "classifier_config.yaml"
    _write_config(config)

    out = plan.build_plan(
        config_path=config,
        roles=["frontdoor"],
        per_role_per_arm=2,
        max_candidates=10_000,
    )

    assert out["request_count"] == 4
    assert out["selected_roles"] == ["frontdoor"]
    assert out["prompt_risk"]["frontdoor"]["risk_band"] == "high"
    assert [item["expected_factual_risk_mode"] for item in out["requests"]].count("enforce") == 2
    assert [item["expected_factual_risk_mode"] for item in out["requests"]].count("shadow") == 2

    for item in out["requests"]:
        payload = item["payload"]
        assert payload["force_role"] == "frontdoor"
        assert payload["force_mode"] == "direct"
        assert payload["request_id"] == item["request_id"]
        assert payload["request_priority"] == "background"
        assert payload["workload_class"] == "campaign"
        assert (
            plan.get_mode(
                plan.load_factual_risk_config(config),
                role="frontdoor",
                sample_key=item["request_id"],
            )
            == item["expected_factual_risk_mode"]
        )


def test_build_plan_uses_scored_dataset_without_leaking_answers_to_payload(
    tmp_path: Path,
) -> None:
    config = tmp_path / "classifier_config.yaml"
    _write_config(config)
    dataset = tmp_path / "scored.jsonl"
    _write_dataset(
        dataset,
        [
            {
                "prompt": "Which exact package name did PEP 371 introduce?",
                "expected_answer": "multiprocessing",
                "domain": "Software Engineering",
                "label_source": "aa_omniscience",
                "label_4class": "NOT_ATTEMPTED",
                "prompt_hash": "pep371",
                "risk_band_v1": "high",
                "risk_score_computed": 0.15,
            }
        ],
    )

    out = plan.build_plan(
        config_path=config,
        roles=["worker_general"],
        per_role_per_arm=2,
        scored_dataset_path=dataset,
        max_candidates=10_000,
    )

    assert out["request_count"] == 4
    assert out["scored_dataset"]["selected_high_risk_rows_by_role"] == {
        "worker_general": 1
    }
    for item in out["requests"]:
        assert item["scored_factuality"]["expected_answer"] == "multiprocessing"
        assert item["scored_factuality"]["prompt_hash"] == "pep371"
        assert "multiprocessing" not in item["payload"]["prompt"]

    payload_rows = [
        json.loads(line) for line in plan._render_jsonl(out).splitlines() if line
    ]
    assert payload_rows
    assert all("multiprocessing" not in json.dumps(row) for row in payload_rows)

    answer_key_rows = [
        json.loads(line)
        for line in plan._render_answer_key_jsonl(out).splitlines()
        if line
    ]
    assert {row["expected_answer"] for row in answer_key_rows} == {"multiprocessing"}
    assert {row["expected_factual_risk_mode"] for row in answer_key_rows} == {
        "enforce",
        "shadow",
    }


def test_build_plan_rejects_scored_dataset_without_high_risk_rows(
    tmp_path: Path,
) -> None:
    config = tmp_path / "classifier_config.yaml"
    _write_config(config)
    dataset = tmp_path / "scored.jsonl"
    _write_dataset(
        dataset,
        [
            {
                "prompt": "hello",
                "expected_answer": "world",
                "prompt_hash": "low",
            }
        ],
    )

    with pytest.raises(ValueError, match="no high-risk rows"):
        plan.build_plan(
            config_path=config,
            roles=["worker_general"],
            scored_dataset_path=dataset,
            scored_prompt_template="{prompt}",
        )


def test_build_plan_filters_scored_rows_that_include_expected_answer(
    tmp_path: Path,
) -> None:
    config = tmp_path / "classifier_config.yaml"
    _write_config(config)
    dataset = tmp_path / "scored.jsonl"
    _write_dataset(
        dataset,
        [
            {
                "prompt": "Which exact package name did PEP 371 introduce? Answer: multiprocessing",
                "expected_answer": "multiprocessing",
                "prompt_hash": "leaky",
            }
        ],
    )

    with pytest.raises(ValueError, match="had no rows with expected_answer"):
        plan.build_plan(
            config_path=config,
            roles=["worker_general"],
            scored_dataset_path=dataset,
        )


def test_build_plan_rejects_scored_template_without_prompt_placeholder(
    tmp_path: Path,
) -> None:
    config = tmp_path / "classifier_config.yaml"
    _write_config(config)
    dataset = tmp_path / "scored.jsonl"
    _write_dataset(dataset, [{"prompt": "Question?", "expected_answer": "Answer"}])

    with pytest.raises(ValueError, match="must contain"):
        plan.build_plan(
            config_path=config,
            roles=["worker_general"],
            scored_dataset_path=dataset,
            scored_prompt_template="missing placeholder",
        )


def test_build_plan_rejects_non_canary_config(tmp_path: Path) -> None:
    config = tmp_path / "classifier_config.yaml"
    _write_config(config, mode="shadow")

    with pytest.raises(ValueError, match="must be canary"):
        plan.build_plan(config_path=config, roles=["frontdoor"])


def test_build_plan_rejects_non_high_prompt(tmp_path: Path) -> None:
    config = tmp_path / "classifier_config.yaml"
    _write_config(config)

    with pytest.raises(ValueError, match="not high factual-risk"):
        plan.build_plan(
            config_path=config,
            roles=["frontdoor"],
            prompt="hello",
        )
