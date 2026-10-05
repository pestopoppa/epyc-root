from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "autopilot"))

coverage_report = importlib.import_module("eval_task_coverage_report")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def test_build_report_counts_repeated_questions_against_pool(tmp_path: Path) -> None:
    pool = tmp_path / "question_pool.jsonl"
    math_prompt = "What is two plus two?"
    code_prompt = "Write a Python add function."
    other_prompt = "Summarize the contract."
    math_qid = coverage_report._stable_question_qid("math", math_prompt)
    code_qid = coverage_report._stable_question_qid("coder", code_prompt)
    _write_jsonl(
        pool,
        [
            {"__pool_metadata__": True, "total_questions": 3},
            {"id": "m1", "suite": "math", "tier": 1, "prompt": math_prompt},
            {"id": "c1", "suite": "coder", "tier": 1, "prompt": code_prompt},
            {"id": "g1", "suite": "general", "tier": 2, "prompt": other_prompt},
        ],
    )
    journal = tmp_path / "autopilot_journal.jsonl"
    _write_jsonl(
        journal,
        [
            {
                "trial_id": 1,
                "action_type": "numeric_trial",
                "hypothesis": "try fast setting",
                "config_snapshot": {"type": "numeric_trial", "temperature": 0.2},
                "tier": 1,
                "eval_details": {
                    "core_id": "legacy_pool_seed_42_n50",
                    "question_results": [
                        {"suite": "math", "qid": math_qid, "correct": True},
                        {"suite": "coder", "qid": code_qid, "correct": False},
                    ],
                },
            },
            {
                "trial_id": 2,
                "action_type": "numeric_trial",
                "hypothesis": "try fast setting",
                "config_snapshot": {"type": "numeric_trial", "temperature": 0.4},
                "tier": 2,
                "eval_details": {
                    "core_id": "legacy_pool_seed_42_n50",
                    "question_results": [
                        {"suite": "math", "qid": math_qid, "correct": True},
                        {
                            "suite": "math",
                            "qid": math_qid,
                            "partition": "audit",
                            "correct": True,
                        },
                    ],
                },
            },
        ],
    )

    report = coverage_report.build_report(
        journal_paths=[journal], pool_path=pool, fold_supersessions=False
    )

    assert report["coverage"]["question_result_rows"] == 4
    assert report["coverage"]["distinct_journal_question_keys"] == 2
    assert report["coverage"]["pool_stable_question_keys"] == 3
    assert report["coverage"]["matched_pool_stable_question_keys"] == 2
    assert report["coverage"]["distinct_vs_pool_stable_upper_bound_pct"] == 66.6667
    assert report["coverage"]["repeat_factor"] == 2.0
    assert report["questions"]["partition_attempt_counts"] == {"audit": 1, "core": 3}
    assert report["questions"]["tier_question_counts"] == {"1": 2, "2": 2}
    assert report["questions"]["tier_distinct_question_counts"] == {"1": 2, "2": 1}
    assert report["questions"]["tier_coverage"]["1"] == {
        "distinct_journal_question_keys": 2,
        "distinct_vs_pool_pct": 100.0,
        "eval_bearing_trials": 1,
        "pool_question_keys": 2,
        "question_result_rows": 2,
    }
    assert report["questions"]["tier_coverage"]["2"] == {
        "distinct_journal_question_keys": 1,
        "distinct_vs_pool_pct": 100.0,
        "eval_bearing_trials": 1,
        "pool_question_keys": 1,
        "question_result_rows": 2,
    }
    assert report["pool"]["tier_counts"] == {"1": 2, "2": 1}
    assert report["planner_diversity"]["unique_action_types"] == 1
    assert report["planner_diversity"]["unique_config_fingerprints"] == 2
    assert report["planner_diversity"]["unique_hypotheses"] == 1


def test_markdown_renders_lane_split_guidance(tmp_path: Path) -> None:
    pool = tmp_path / "question_pool.jsonl"
    prompt = "2+2?"
    qid = coverage_report._stable_question_qid("math", prompt)
    _write_jsonl(
        pool,
        [
            {"__pool_metadata__": True, "total_questions": 1},
            {"id": "m1", "suite": "math", "tier": 1, "prompt": prompt},
        ],
    )
    journal = tmp_path / "autopilot_journal.jsonl"
    _write_jsonl(
        journal,
        [
            {
                "trial_id": 7,
                "eval_details": {
                    "question_results": [{"suite": "math", "qid": qid, "correct": True}]
                },
            }
        ],
    )

    markdown = coverage_report.render_markdown(
        coverage_report.build_report(
            journal_paths=[journal], pool_path=pool, fold_supersessions=False
        )
    )

    assert "AutoPilot Eval Task Coverage" in markdown
    assert "Tier Coverage" in markdown
    assert "Least-Covered Non-Sentinel Suites" in markdown
    assert "authority_core" in markdown
    assert "exploration_coverage" in markdown


def test_report_summarizes_surrogate_verifier_feedback(tmp_path: Path) -> None:
    pool = tmp_path / "question_pool.jsonl"
    prompt = "2+2?"
    qid = coverage_report._stable_question_qid("math", prompt)
    _write_jsonl(
        pool,
        [
            {"__pool_metadata__": True, "total_questions": 1},
            {"id": "m1", "suite": "math", "tier": 1, "prompt": prompt},
        ],
    )
    journal = tmp_path / "autopilot_journal.jsonl"
    question_results = [{"suite": "math", "qid": qid, "correct": True}]
    _write_jsonl(
        journal,
        [
            {
                "trial_id": 10,
                "eval_details": {
                    "question_results": question_results,
                    "details": {
                        "surrogate_feedback": {
                            "proxy_reward": 0.5,
                            "dense_feedback": True,
                            "opaque_only": False,
                            "accepted": False,
                        }
                    },
                },
            },
            {
                "trial_id": 11,
                "eval_details": {
                    "question_results": question_results,
                    "details": {
                        "surrogate_feedback": {
                            "proxy_reward": 1.0,
                            "dense_feedback": False,
                            "opaque_only": False,
                            "accepted": True,
                        }
                    },
                },
            },
            {
                "trial_id": 12,
                "eval_details": {
                    "question_results": question_results,
                    "surrogate_feedback": {
                        "proxy_reward": 1.0,
                        "dense_feedback": False,
                        "opaque_only": True,
                        "accepted": False,
                    },
                },
            },
        ],
    )

    report = coverage_report.build_report(
        journal_paths=[journal], pool_path=pool, fold_supersessions=False
    )
    surrogate = report["surrogate_verifier"]

    assert surrogate["rows"] == 3
    assert surrogate["accepted"] == 1
    assert surrogate["dense_feedback"] == 1
    assert surrogate["opaque_only"] == 1
    assert surrogate["proxy_reward_rows"] == 3
    assert surrogate["avg_proxy_reward"] == 0.8333
    assert surrogate["trial_id_min"] == 10
    assert surrogate["trial_id_max"] == 12
    assert surrogate["status"] == "oracle_conflict"

    markdown = coverage_report.render_markdown(report)
    assert "Surrogate Verifier Feedback" in markdown
    assert "Opaque-only oracle conflicts: `1`" in markdown
