"""Fixture tests for the LB-1 offline shadow-overhead attribution runner.

Pure offline logic only — parsing two synthetic paired-arm artifacts, resolving the
pairing + profile gate, and the attribution arithmetic (median/aggregate t/s, eval-wall
+ token deltas, Wilson + paired-difference CIs). NO inference, NO server, NO /chat.

The synthetic arms are constructed so every headline number is a clean closed form:

    shadow-OFF  per-question (tokens / eval_wall_s -> t/s):
        q1 100/1.00 = 100   q2 200/2.00 = 100   q3 200/4.00 = 50   q4 50/1.00 = 50
        totals: 550 tokens / 8.0 s -> aggregate 68.75 t/s ; median t/s 75.0
    shadow-ON  (25% slower wall, same tokens):
        q1 100/1.25 =  80   q2 200/2.50 =  80   q3 200/5.00 = 40   q4 50/1.25 = 40
        totals: 550 tokens / 10.0 s -> aggregate 55.0 t/s ; median t/s 60.0

    aggregate-t/s overhead = (68.75 - 55.0) / 68.75 = 0.20 exactly
    eval-wall total delta   = 10.0 - 8.0 = 2.0 s ; per-question mean delta = 0.5 s
    token total delta       = 0
    median-t/s delta        = 60.0 - 75.0 = -15.0
"""

from __future__ import annotations

import json

import pytest

from scripts.analysis import lb1_shadow_overhead_attribution as lb1


# --------------------------------------------------------------------------- #
# Synthetic paired-arm fixtures (same 4 questions/seed; differ only in shadow)
# --------------------------------------------------------------------------- #

_DATASET_SHA = "sha256:deadbeef"


def _off_payload() -> dict:
    return {
        "shadow": "off",
        "model": "gemma4-26B-A4B",
        "quant": "Q4_K_M",
        "seed": 42,
        "dataset_sha256": _DATASET_SHA,
        "records": [
            {"qid": "q1", "suite": "math", "eval_wall_s": 1.00, "tokens": 100, "correct": True},
            {"qid": "q2", "suite": "math", "eval_wall_s": 2.00, "tokens": 200, "correct": True},
            {"qid": "q3", "suite": "code", "eval_wall_s": 4.00, "tokens": 200, "correct": False},
            {"qid": "q4", "suite": "code", "eval_wall_s": 1.00, "tokens": 50, "correct": True},
        ],
    }


def _on_payload() -> dict:
    return {
        "shadow": "on",
        "model": "gemma4-26B-A4B",
        "quant": "Q4_K_M",
        "seed": 42,
        "dataset_sha256": _DATASET_SHA,
        "records": [
            {"qid": "q1", "suite": "math", "eval_wall_s": 1.25, "tokens": 100, "correct": True},
            {"qid": "q2", "suite": "math", "eval_wall_s": 2.50, "tokens": 200, "correct": True},
            {"qid": "q3", "suite": "code", "eval_wall_s": 5.00, "tokens": 200, "correct": False},
            {"qid": "q4", "suite": "code", "eval_wall_s": 1.25, "tokens": 50, "correct": True},
        ],
    }


def _attribution() -> dict:
    off = lb1.load_arm_artifact(_off_payload())
    on = lb1.load_arm_artifact(_on_payload())
    off, on = lb1.resolve_arms(off, on)
    return lb1.compute_attribution(off, on)


# --------------------------------------------------------------------------- #
# Parsing
# --------------------------------------------------------------------------- #


def test_load_arm_artifact_parses_metadata_and_derives_tps() -> None:
    off = lb1.load_arm_artifact(_off_payload())
    assert off.shadow_enabled is False
    assert off.label == "shadow_off"
    assert off.model == "gemma4-26B-A4B"
    assert off.quant == "Q4_K_M"
    assert off.seed == 42
    assert off.dataset_sha256 == _DATASET_SHA
    assert sorted(off.records) == ["q1", "q2", "q3", "q4"]

    # t/s is DERIVED from tokens / eval_wall_s when absent (the RCP-W2 identity).
    assert off.records["q1"].tps == pytest.approx(100.0)
    assert off.records["q3"].tps == pytest.approx(50.0)
    assert off.records["q1"].tokens == 100
    assert off.records["q3"].suite == "code"
    assert off.records["q3"].correct is False


def test_load_arm_artifact_reads_explicit_tps_and_aliases() -> None:
    payload = {
        "shadow_enabled": True,
        "records": [
            # alias-heavy row: question_id/tokens_generated/t_per_s/is_correct
            {"question_id": "z9", "domain": "sci", "eval_wall": 2.0, "tokens_generated": 30, "t_per_s": 40.0, "is_correct": 1},
        ],
    }
    arm = lb1.load_arm_artifact(payload)
    rec = arm.records["z9"]
    assert arm.shadow_enabled is True
    assert rec.tps == pytest.approx(40.0)  # explicit t/s wins over tokens/wall (=15.0)
    assert rec.tokens == 30
    assert rec.suite == "sci"
    assert rec.correct is True
    # dataset_sha256 is synthesized deterministically when the artifact omits it.
    assert arm.dataset_sha256.startswith("sha256:")


def test_load_arm_artifact_rejects_duplicate_qids() -> None:
    payload = {
        "shadow": "off",
        "records": [
            {"qid": "dup", "eval_wall_s": 1.0, "tokens": 10},
            {"qid": "dup", "eval_wall_s": 1.0, "tokens": 10},
        ],
    }
    with pytest.raises(ValueError, match="duplicate qid"):
        lb1.load_arm_artifact(payload)


# --------------------------------------------------------------------------- #
# Pairing + profile gate
# --------------------------------------------------------------------------- #


def test_resolve_arms_orders_off_then_on_regardless_of_input_order() -> None:
    off_first = lb1.load_arm_artifact(_off_payload())
    on_first = lb1.load_arm_artifact(_on_payload())
    # Pass ON first, OFF second — resolve must still return (off, on).
    off, on = lb1.resolve_arms(on_first, off_first)
    assert off.shadow_enabled is False
    assert on.shadow_enabled is True


def test_resolve_arms_requires_one_off_and_one_on() -> None:
    a = lb1.load_arm_artifact(_off_payload())
    b = lb1.load_arm_artifact(_off_payload())
    with pytest.raises(ValueError, match="one shadow-OFF and one shadow-ON"):
        lb1.resolve_arms(a, b)


def test_resolve_arms_refuses_mismatched_dataset() -> None:
    from scripts.autopilot.paired_stats import PairedComparisonMismatchError

    off = lb1.load_arm_artifact(_off_payload())
    bad_on = _on_payload()
    bad_on["dataset_sha256"] = "sha256:different"
    on = lb1.load_arm_artifact(bad_on)
    with pytest.raises(PairedComparisonMismatchError):
        lb1.resolve_arms(off, on)


def test_paired_qids_intersection() -> None:
    off = lb1.load_arm_artifact(_off_payload())
    on = lb1.load_arm_artifact(_on_payload())
    off, on = lb1.resolve_arms(off, on)
    assert lb1.paired_qids(off, on) == ["q1", "q2", "q3", "q4"]


# --------------------------------------------------------------------------- #
# Attribution arithmetic (the pure core) — exact expected values
# --------------------------------------------------------------------------- #


def test_attribution_arm_aggregates_exact() -> None:
    res = _attribution()
    assert res["paired_qids"] == 4
    off_arm = res["arms"]["shadow_off"]
    on_arm = res["arms"]["shadow_on"]

    assert off_arm["total_tokens"] == 550
    assert off_arm["total_wall_s"] == 8.0
    assert off_arm["aggregate_tps"] == 68.75
    assert off_arm["median_tps"] == 75.0

    assert on_arm["total_tokens"] == 550
    assert on_arm["total_wall_s"] == 10.0
    assert on_arm["aggregate_tps"] == 55.0
    assert on_arm["median_tps"] == 60.0


def test_attribution_deltas_exact() -> None:
    res = _attribution()
    delta = res["delta_on_minus_off"]
    assert delta["aggregate_tps"] == -13.75
    assert delta["median_tps"] == -15.0
    assert delta["eval_wall_total_s"] == 2.0
    assert delta["eval_wall_mean_s"] == 0.5
    assert delta["tokens_total"] == 0
    # (68.75 - 55.0) / 68.75 == 0.20 exactly.
    assert res["overhead_fraction_tps"] == 0.2


def test_attribution_paired_cis_exact() -> None:
    res = _attribution()
    wall_ci = res["paired_ci"]["eval_wall_delta_s"]
    tps_ci = res["paired_ci"]["tps_delta"]

    # eval-wall per-question deltas: [0.25, 0.5, 1.0, 0.25]; mean 0.5, sd 0.353553.
    assert wall_ci["n"] == 4
    assert wall_ci["mean"] == 0.5
    assert wall_ci["sd"] == pytest.approx(0.353553, abs=1e-6)
    assert wall_ci["se"] == pytest.approx(0.176777, abs=1e-6)
    assert wall_ci["ci95"][0] == pytest.approx(0.153524, abs=1e-6)
    assert wall_ci["ci95"][1] == pytest.approx(0.846476, abs=1e-6)

    # t/s per-question deltas: [-20, -20, -10, -10]; mean -15.0, sd 5.773503.
    assert tps_ci["mean"] == -15.0
    assert tps_ci["sd"] == pytest.approx(5.773503, abs=1e-6)
    assert tps_ci["se"] == pytest.approx(2.886751, abs=1e-6)
    assert tps_ci["ci95"][0] == pytest.approx(-20.657929, abs=1e-6)
    assert tps_ci["ci95"][1] == pytest.approx(-9.342071, abs=1e-6)


def test_attribution_accuracy_wilson_and_mcnemar_exact() -> None:
    res = _attribution()
    acc = res["accuracy"]
    assert acc["available"] is True
    assert acc["off_correct"] == 3
    assert acc["on_correct"] == 3
    assert acc["off_accuracy"] == 0.75
    assert acc["on_accuracy"] == 0.75
    assert acc["accuracy_delta_on_minus_off"] == 0.0

    # Wilson 95% score interval for 3/4 (z = 1.959964), matched by both arms.
    assert acc["off_wilson95"][0] == pytest.approx(0.300642, abs=1e-6)
    assert acc["off_wilson95"][1] == pytest.approx(0.954413, abs=1e-6)
    assert acc["on_wilson95"] == acc["off_wilson95"]

    # Identical correctness vectors -> zero discordant pairs -> McNemar p == 1.0.
    assert acc["mcnemar_p_value_two_sided"] == 1.0
    assert acc["mcnemar"]["a_correct_b_wrong"] == 0
    assert acc["mcnemar"]["a_wrong_b_correct"] == 0


def test_attribution_is_model_quant_indexed_never_role() -> None:
    res = _attribution()
    assert res["indexed_by"] == "model_quant"
    assert res["model_quant_key"] == "gemma4-26B-A4B/Q4_K_M"
    assert res["observation_only"] is True
    # No role indexing anywhere in the emitted result.
    assert "role" not in json.dumps(res).lower().replace("payload", "")


def test_paired_delta_ci_single_point_has_zero_width() -> None:
    ci = lb1._paired_delta_ci([2.5], lb1.DEFAULT_Z)
    assert ci["n"] == 1
    assert ci["mean"] == 2.5
    assert ci["sd"] is None
    assert ci["ci95"] == [2.5, 2.5]


# --------------------------------------------------------------------------- #
# Planning (default dry-run CLI path) — no inference
# --------------------------------------------------------------------------- #


def _write_fixture_arms(tmp_path):
    off_path = tmp_path / "shadow_off.json"
    on_path = tmp_path / "shadow_on.json"
    off_path.write_text(json.dumps(_off_payload()), encoding="utf-8")
    on_path.write_text(json.dumps(_on_payload()), encoding="utf-8")
    return off_path, on_path


def test_default_cli_is_dry_run_plan_with_embedded_attribution(tmp_path, capsys) -> None:
    off_path, on_path = _write_fixture_arms(tmp_path)
    out_path = tmp_path / "attribution.json"

    rc = lb1.main(
        [
            "--off-artifact", str(off_path),
            "--on-artifact", str(on_path),
            "--output", str(out_path),
        ]
    )
    assert rc == 0

    plan = json.loads(capsys.readouterr().out)
    assert plan["kind"] == "lb1_shadow_overhead_plan"
    assert plan["mode"] == "dry_run"
    assert plan["inference_ran"] is False
    assert plan["indexed_by"] == "model_quant"
    assert plan["model_quant_key"] == "gemma4-26B-A4B/Q4_K_M"
    assert plan["paired_qids"] == 4

    # Transport rides the placement queue as an eval_batch, NEVER /chat.
    transport = plan["transport"]
    assert transport["transport"] == "placement_queue"
    assert transport["request_priority"] == "background"
    assert transport["workload_class"] == "eval_batch"
    assert transport["uses_chat_endpoint"] is False

    # The offline attribution is embedded in the plan and matches the pure computation.
    assert plan["attribution"]["delta_on_minus_off"]["eval_wall_total_s"] == 2.0
    assert plan["attribution"]["overhead_fraction_tps"] == 0.2

    # --output was written with the standalone attribution report.
    written = json.loads(out_path.read_text())
    assert written["kind"] == "lb1_shadow_overhead_attribution"
    assert written["paired_qids"] == 4


def test_execute_without_env_flag_falls_back_to_dry_run(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.delenv(lb1.LB1_INFERENCE_ENV, raising=False)
    off_path, on_path = _write_fixture_arms(tmp_path)

    rc = lb1.main(
        [
            "--off-artifact", str(off_path),
            "--on-artifact", str(on_path),
            "--execute",  # requested, but env flag is unset -> dry-run
        ]
    )
    assert rc == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan["mode"] == "dry_run"
    assert plan["inference_ran"] is False
    assert any(lb1.LB1_INFERENCE_ENV in note and "falling back" in note for note in plan["notes"])
