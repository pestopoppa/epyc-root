from __future__ import annotations

import json
from pathlib import Path

from scripts.graph_router import build_offline_reward_source_reward_diagnostic as mod


def _candidate(
    *,
    candidate_id: str,
    role_key: str,
    q_reward: float,
    offset: int = 0,
    question_id: str = "q1",
) -> dict:
    return {
        "schema_version": "offline_reward_verifier_expansion_candidate.v1",
        "candidate_id": candidate_id,
        "source_path": "/tmp/source.jsonl",
        "source_record_index": offset + 1,
        "source_record_index_base": "one_based",
        "source_record_offset": offset,
        "question_id": question_id,
        "suite": "math",
        "role_key": role_key,
        "source_family": "seeding_eval",
        "source_passed": q_reward >= 0.5,
        "source_elapsed_seconds": 1.5,
        "source_error_present": False,
        "prompt_sha256": f"prompt-{question_id}",
        "expected_sha256": f"expected-{question_id}",
        "response_sha256": f"response-{candidate_id}",
        "prompt_chars": 100,
        "reference_chars": 2,
        "response_chars": 40,
        "q_reward": q_reward,
    }


def test_source_reward_diagnostic_builds_score_ordered_contract() -> None:
    pair_rows, summary = mod.build_source_reward_diagnostic(
        [
            _candidate(candidate_id="frontdoor", role_key="frontdoor:direct", q_reward=1.0),
            _candidate(
                candidate_id="coder",
                role_key="coder_escalation:direct",
                q_reward=0.0,
            ),
            _candidate(
                candidate_id="architect",
                role_key="architect_general:direct",
                q_reward=0.5,
            ),
        ],
        min_pairs=1,
        min_cross_action_pairs=1,
        generated_at="2026-07-04T00:00:00+00:00",
    )

    assert summary["schema_version"] == mod.SUMMARY_SCHEMA_VERSION
    assert summary["decision"]["status"] == "contract_ready"
    assert summary["decision"]["runtime_gate_change_allowed"] is False
    assert summary["diagnostic"]["independent_oracle"] is False
    assert summary["diagnostic"]["source_reward_passthrough"] is True
    assert summary["coverage"]["pair_rows"] == 3
    assert summary["coverage"]["cross_action_pair_rows"] == 3
    assert pair_rows[0]["pairing_mode"] == "score_ordered"
    assert all(
        row["preferred_oracle_score"] > row["rejected_oracle_score"]
        for row in pair_rows
    )
    assert "prompt" not in pair_rows[0]
    assert "answer" not in pair_rows[0]


def test_source_reward_diagnostic_rejects_private_candidate_text() -> None:
    try:
        mod.build_source_reward_diagnostic(
            [
                {
                    **_candidate(
                        candidate_id="frontdoor",
                        role_key="frontdoor:direct",
                        q_reward=1.0,
                    ),
                    "response": "private output text",
                }
            ],
            min_pairs=1,
        )
    except mod.SourceRewardDiagnosticError as exc:
        assert "private fields present: response" in str(exc)
    else:
        raise AssertionError("expected SourceRewardDiagnosticError")


def test_source_reward_diagnostic_cli_writes_outputs(tmp_path: Path) -> None:
    candidates = tmp_path / "candidates.jsonl"
    candidates.write_text(
        "\n".join(
            json.dumps(row, sort_keys=True)
            for row in [
                _candidate(
                    candidate_id="frontdoor",
                    role_key="frontdoor:direct",
                    q_reward=1.0,
                ),
                _candidate(
                    candidate_id="coder",
                    role_key="coder_escalation:direct",
                    q_reward=0.0,
                ),
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
            "--candidates-jsonl",
            str(candidates),
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
            "2026-07-04T00:00:00+00:00",
        ]
    ) == 0

    assert out_jsonl.exists()
    summary = json.loads(summary_json.read_text(encoding="utf-8"))
    assert summary["decision"]["status"] == "contract_ready"
    assert summary["outputs"]["pairwise_jsonl"] == str(out_jsonl)
    assert "Diagnostic only" in summary_md.read_text(encoding="utf-8")
