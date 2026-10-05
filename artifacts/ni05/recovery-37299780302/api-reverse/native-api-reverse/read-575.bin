from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from scripts.autopilot import paired_stats


def _row(
    trial_id: int,
    fingerprint: str,
    outcomes: list[tuple[str, bool]],
) -> dict:
    return {
        "trial_id": trial_id,
        "config_snapshot": {"config_fingerprint": fingerprint},
        "eval_details": {
            "question_results": [
                {"qid": qid, "suite": "suite", "correct": correct} for qid, correct in outcomes
            ]
        },
    }


def test_mcnemar_from_vectors_counts_discordant_pairs() -> None:
    rows = [
        _row(1, "a", [("q1", True), ("q2", True), ("q3", False), ("q4", False)]),
        _row(2, "b", [("q1", True), ("q2", False), ("q3", True), ("q4", False)]),
    ]
    vectors = paired_stats.trial_vectors(rows)

    result = paired_stats.mcnemar_from_vectors(vectors[1], vectors[2], "1", "2")

    assert result.shared_qids == 4
    assert result.same_correct == 1
    assert result.same_wrong == 1
    assert result.a_correct_b_wrong == 1
    assert result.a_wrong_b_correct == 1
    assert result.p_value_two_sided == 1.0
    assert result.delta_b_minus_a == 0.0


def test_compare_fingerprints_uses_majority_per_qid() -> None:
    rows = [
        _row(1, "base", [("q1", True), ("q2", False), ("q3", False)]),
        _row(2, "base", [("q1", True), ("q2", False), ("q3", True)]),
        _row(3, "cand", [("q1", True), ("q2", True), ("q3", True)]),
        _row(4, "cand", [("q1", True), ("q2", True), ("q3", False)]),
    ]

    result = paired_stats.compare_fingerprints(rows, "cand", "base")

    assert result["shared_qids"] == 2  # q3 ties in both groups and is dropped
    assert result["a_correct_b_wrong"] == 0
    assert result["a_wrong_b_correct"] == 1
    assert result["delta_b_minus_a"] == 0.5
    assert result["candidate_trials"] == [3, 4]
    assert result["baseline_trials"] == [1, 2]


def test_summary_reports_no_vectors_for_current_style_rows(tmp_path: Path) -> None:
    journal = tmp_path / "autopilot_journal.jsonl"
    journal.write_text(
        json.dumps(
            {
                "trial_id": 10,
                "config_snapshot": {"type": "seed_batch"},
                "eval_details": {"details": {"correct": 2, "total": 3}},
            }
        )
        + "\n"
    )

    summary = paired_stats.summarize(tmp_path)

    assert summary["rows"] == 1
    assert summary["vector_trials"] == 0
    assert summary["fingerprints_with_vectors"] == {}


def test_iter_journal_rows_folds_supersession_events(tmp_path: Path) -> None:
    journal = tmp_path / "autopilot_journal.jsonl"
    rows = [
        _row(1, "base", [("q1", True)]),
        _row(2, "cand", [("q1", False)]),
        {
            "type": "supersession",
            "target_trial_ids": [2],
            "fields": {"bug_corrupted_by": "resource_contention"},
        },
    ]
    journal.write_text("\n".join(json.dumps(row) for row in rows) + "\n")

    loaded = list(paired_stats.iter_journal_rows(journal))

    assert [row["trial_id"] for row in loaded] == [1, 2]
    assert loaded[1]["bug_corrupted_by"] == "resource_contention"
    assert "type" not in loaded[1]


# ── McNemar VERDICT surface (mcnemar_verdict / verdict_from_result) ───────────
# The verdict promotes raw discordant counts (b = a_correct_b_wrong,
# c = a_wrong_b_correct) into an explicit gating verdict. Exact two-sided
# binomial sign test at/below MCNEMAR_EXACT_MAX_DISCORDANT discordant pairs;
# continuity-corrected normal approximation above it.


def test_verdict_threshold_selects_method_at_boundary() -> None:
    thr = paired_stats.MCNEMAR_EXACT_MAX_DISCORDANT
    assert thr == 25
    # n_discordant == threshold -> exact; threshold + 1 -> normal.
    at = paired_stats.mcnemar_verdict(12, 13)  # b+c = 25
    above = paired_stats.mcnemar_verdict(13, 13)  # b+c = 26
    assert at["n_discordant"] == 25
    assert at["approximation"] == "exact_binomial"
    assert at["z"] is None
    assert above["n_discordant"] == 26
    assert above["approximation"] == "normal_approx"
    assert above["z"] is not None


def test_verdict_small_exact_one_directional_is_significant_b_better() -> None:
    # 8 discordant flips, all A-wrong/B-right: exact two-sided p = 2*C(8,0)/2^8.
    v = paired_stats.mcnemar_verdict(0, 8)
    assert v["method"] == "mcnemar"
    assert v["approximation"] == "exact_binomial"
    assert v["n_discordant"] == 8
    assert v["p_value"] == pytest.approx(2.0 / 256.0)
    assert v["p_value"] == paired_stats._exact_two_sided_binomial_p(0, 8)
    assert v["verdict"] == "b_better"


def test_verdict_small_exact_a_better_direction() -> None:
    # Mirror image: all flips A-right/B-wrong -> a_better.
    v = paired_stats.mcnemar_verdict(8, 0)
    assert v["verdict"] == "a_better"
    assert v["p_value"] == pytest.approx(2.0 / 256.0)


def test_verdict_balanced_small_is_indistinguishable() -> None:
    # b == c: the sign test cannot reject; verdict is indistinguishable.
    v = paired_stats.mcnemar_verdict(2, 2)
    assert v["p_value"] == 1.0
    assert v["verdict"] == "indistinguishable"


def test_verdict_zero_discordant_is_indistinguishable() -> None:
    v = paired_stats.mcnemar_verdict(0, 0)
    assert v["n_discordant"] == 0
    assert v["approximation"] == "exact_binomial"
    assert v["p_value"] == 1.0
    assert v["z"] is None
    assert v["verdict"] == "indistinguishable"


def test_verdict_large_normal_significant_b_better_with_signed_z() -> None:
    # 65 discordant, heavily B-favouring -> normal approx, significant, z > 0.
    v = paired_stats.mcnemar_verdict(5, 60)
    assert v["approximation"] == "normal_approx"
    assert v["n_discordant"] == 65
    # Continuity-corrected z = (|b-c|-1)/sqrt(b+c), signed by (c - b) > 0.
    expected_z = (abs(5 - 60) - 1) / math.sqrt(65)
    assert v["z"] == pytest.approx(expected_z, abs=1e-5)
    assert v["z"] > 0
    assert v["p_value"] < 0.05
    assert v["verdict"] == "b_better"


def test_verdict_large_normal_a_better_has_negative_z() -> None:
    v = paired_stats.mcnemar_verdict(60, 5)
    assert v["approximation"] == "normal_approx"
    assert v["z"] < 0
    assert v["p_value"] < 0.05
    assert v["verdict"] == "a_better"


def test_verdict_large_normal_noise_band_is_indistinguishable() -> None:
    # E7c-shaped real counts: b=61, c=58 -> normal approx, clearly not significant.
    v = paired_stats.mcnemar_verdict(61, 58)
    assert v["approximation"] == "normal_approx"
    assert v["n_discordant"] == 119
    assert v["p_value"] > 0.5
    assert v["verdict"] == "indistinguishable"
    # Normal-approx p tracks the exact p closely in this regime (sanity, not spec).
    assert v["p_value"] == pytest.approx(
        paired_stats._exact_two_sided_binomial_p(61, 58), abs=2e-3
    )


def test_verdict_alpha_is_honoured() -> None:
    # p ~= 0.0078 for (0,8): significant at 0.05, NOT at 0.001.
    assert paired_stats.mcnemar_verdict(0, 8, alpha=0.05)["verdict"] == "b_better"
    assert (
        paired_stats.mcnemar_verdict(0, 8, alpha=0.001)["verdict"]
        == "indistinguishable"
    )


def test_verdict_exact_max_discordant_override_forces_normal() -> None:
    # Lowering the threshold forces the normal branch on a small discordant set.
    v = paired_stats.mcnemar_verdict(0, 8, exact_max_discordant=4)
    assert v["approximation"] == "normal_approx"
    assert v["z"] is not None
    assert v["exact_max_discordant"] == 4


def test_verdict_from_result_matches_direct_call() -> None:
    rows = [
        _row(1, "a", [(f"q{i}", i <= 4) for i in range(1, 13)]),
        _row(2, "b", [(f"q{i}", True) for i in range(1, 13)]),
    ]
    vectors = paired_stats.trial_vectors(rows)
    result = paired_stats.mcnemar_from_vectors(vectors[1], vectors[2], "1", "2")
    derived = paired_stats.verdict_from_result(result)
    direct = paired_stats.mcnemar_verdict(
        result.a_correct_b_wrong, result.a_wrong_b_correct
    )
    assert derived == direct
    assert derived["verdict"] == "b_better"


def test_verdict_is_json_serializable() -> None:
    v = paired_stats.mcnemar_verdict(3, 40)
    assert json.loads(json.dumps(v)) == v
