"""P1-L: PB-HOL-1 run directories project to scoped, value-bearing arm-comparison claims."""
import copy
import json
import shutil
import sys
from dataclasses import replace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "vidya"))
import claim_tuple as ct  # noqa: E402
import ingest_sources  # noqa: E402
from adapters import pb_hol  # noqa: E402

FX = Path(__file__).parent / "fixtures" / "belief_p1" / "pb_hol" / "20261021T160010Z"
AS_OF = "2026-10-21T18:00:00Z"


@pytest.fixture()
def run(tmp_path):
    shutil.copytree(FX, tmp_path / "run")
    return tmp_path / "run"


def _summary(run):
    return json.loads((run / "summary.json").read_text())


def _write(run, summary, *, rows=None):
    (run / "summary.json").write_text(json.dumps(summary))
    if rows is not None:
        (run / "pb_hol_1.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))


def _rows(run):
    return [json.loads(line) for line in (run / "pb_hol_1.jsonl").read_text().splitlines()]


def test_off_arms_project_one_claim_with_the_verbatim_verdict(run):
    natives = pb_hol.native_rows(run)
    assert [n["comparison"] for n in natives] == ["A-off_vs_B-off"]  # the budget-on arms are empty today
    t = pb_hol.project(natives[0])
    assert (t.metric, t.unit, t.metric_direction, t.reps) == (pb_hol.METRIC, "ms", "lower_better", 3)
    assert t.value == 70932.2
    obs = t.observation
    assert obs["anchor_value"] == 3217.5 and obs["n_pairs"] == 3 and obs["retrofit"] is True
    assert obs["effect_rel"] == pytest.approx(70932.2 / 3217.5 - 1)
    assert obs["outcome_native"] == "CONFIRMED" and obs["outcome"] == "regressed"
    assert obs["outcome_reason"] == _summary(run)["rule"]
    assert "22.05x" in t.claim and "CONFIRMED" in t.claim
    assert ct.grade(t)[:2] == ("Judged", "Located")  # n=3, no codified protocol: the shared ladder decides


def test_scope_is_the_27b_gpu_np3_dflash2_shape_from_the_servers_argv(run):
    a = pb_hol.project(pb_hol.native_rows(run)[0]).applicability
    assert a["model_file"] == "/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf"
    assert a["quant"] == "Q8_0" and a["backend"] == "gpu" and a["np"] == 3
    assert a["knob_family"] == "slot_serving" and a["varied"] == ["short_slot_index_order"]
    assert a["build_sha"] == "dd3d9721c" and a["scope_basis"] == "native"
    assert a["kernel"]["execution_digest"] == _summary(run)["binary_sha256"]
    k = a["knobs"]
    assert (k["b"], k["ub"], k["kv_unified"], k["dflash2"], k["spec_draft_n_max"]) == (512, 512, True, True, 7)
    assert "prefill_budget_decoding" not in k and "device" not in a


def test_observation_and_scope_never_move_the_grade_and_ride_the_frames(run):
    t = pb_hol.project(pb_hol.native_rows(run)[0])
    assert ct.grade(t) == ct.grade(replace(t, observation={}, applicability={}))
    source, _, evidence = ct.to_frames(t, as_of=AS_OF, adapter_id=pb_hol.ADAPTER_ID, authority=pb_hol.AUTHORITY)
    assert source["assertion"]["applicability"]["np"] == 3
    assert evidence["assertion"]["observation"]["outcome_native"] == "CONFIRMED"
    assert source["provenance"]["retrofit"] is True


def _with_on_arms(run):
    """SYNTHETIC on-arm samples (test data, not a measurement) plus the on-server's argv shape."""
    s = _summary(run)
    rows = _rows(run)
    on = {"A-on": [3000.0, 3100.0], "B-on": [9000.0, 9200.0], "B-on-nodec": [4000.0, 4200.0]}
    for arm, values in on.items():
        s["budget_on_arms"][arm] = {"median_ms": sum(values) / 2, "ttft_ms": values}
        rows += [{"kind": "run", "phase": "on", "budget": True, "arm": arm, "rep": i, "short_ttft_ms": v}
                 for i, v in enumerate(values, 1)]
    argv = copy.deepcopy(s["servers"][0]["readback"]["proc_cmdline"])
    argv[argv.index("-b") + 1] = argv[argv.index("-ub") + 1] = "2048"
    argv += ["--prefill-budget-decoding", "512"]
    server = copy.deepcopy(s["servers"][0])
    server["label"] = server["label"].replace("-off-", "-on-")
    server["readback"]["proc_cmdline"] = argv
    s["servers"].append(server)
    _write(run, s, rows=rows)
    return run


def test_budget_on_arms_project_when_present_without_a_verdict(run):
    natives = pb_hol.native_rows(_with_on_arms(run))
    assert [n["comparison"] for n in natives] == ["A-off_vs_B-off", "A-on_vs_B-on", "B-on-nodec_vs_B-on"]
    on = pb_hol.project(natives[1])
    assert on.value == 9100.0 and on.observation["anchor_value"] == 3050.0
    assert "outcome" not in on.observation and "outcome_native" not in on.observation
    assert "confound" in on.claim and "no predeclared rule" in on.claim
    k = on.applicability["knobs"]
    assert (k["b"], k["ub"], k["prefill_budget_decoding"]) == (2048, 2048, 512)
    feeder = pb_hol.project(natives[2])
    assert feeder.applicability["varied"] == ["decode_feeder"] and feeder.observation["anchor_value"] == 4100.0
    ids = {pb_hol.project(n).measurement_id for n in natives}
    assert len(ids) == 3  # one claim per comparison, ids distinct


def test_a_run_with_no_samples_on_either_side_declines(run):
    s = _summary(run)
    s["A_off_ttft_ms"] = s["B_off_ttft_ms"] = []
    s["A_off_median"] = s["B_off_median"] = s["B_over_A_off"] = None
    s["verdict"] = "INCOMPLETE"
    _write(run, s, rows=[{"kind": "run", "phase": "off", "arm": "C", "rep": 1, "short_ttft_ms": 280.0}])
    assert pb_hol.native_rows(run) == []


def test_incomplete_verdict_carries_no_normalised_outcome(run):
    s = _summary(run)
    s["verdict"] = "INCOMPLETE"
    _write(run, s)
    obs = pb_hol.project(pb_hol.native_rows(run)[0]).observation
    assert obs["outcome_native"] == "INCOMPLETE" and "outcome" not in obs


def test_summary_that_does_not_rederive_from_its_rows_is_refused(run):
    rows = _rows(run)
    for r in rows:
        if r["arm"] == "B-off":
            r["short_ttft_ms"] += 1.0
            break
    _write(run, _summary(run), rows=rows)
    with pytest.raises(ct.ProjectionError, match="re-derive"):
        pb_hol.native_rows(run)


def test_a_wrong_stated_median_or_ratio_is_refused(run):
    s = _summary(run)
    s["B_off_median"] = 1.0
    _write(run, s)
    with pytest.raises(ct.ProjectionError, match="median"):
        pb_hol.native_rows(run)
    s = _summary(run)
    s["B_off_median"] = 70932.2
    s["B_over_A_off"] = 5.0
    _write(run, s)
    with pytest.raises(ct.ProjectionError, match="B_over_A_off"):
        pb_hol.project(pb_hol.native_rows(run)[0])


def test_foreign_or_missing_documents_decline(run, tmp_path):
    s = _summary(run)
    s["schema"] = "other"
    _write(run, s)
    assert pb_hol.native_rows(run) == []
    assert pb_hol.native_rows(tmp_path / "nowhere") == []


def test_a_disagreeing_readback_scopes_nothing(run):
    s = _summary(run)
    s["servers"][0]["readback"]["exe_matches_binary"] = False
    _write(run, s)
    assert pb_hol.project(pb_hol.native_rows(run)[0]).applicability == {}


def test_registered_single_ladder_and_cli_source(run):
    assert pb_hol.SOURCE_KIND in ct.registered()
    assert ct.source_classes()[pb_hol.SOURCE_KIND] == "measurement"
    parent = run.parent
    units = ingest_sources.SOURCES["pb-hol"].units(parent)
    assert units == [run]
