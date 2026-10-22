"""VB-YARN-AGG-1: yarn_gate decision records -> rows -> existing measurement ladder."""
import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402
from adapters import yarn_gate_agg as y  # noqa: E402

WHEN = "2026-10-22T10:00:00Z"
H = "a" * 40
S = "b" * 64
JUDGE = {"model": "mock-judge", "prompt_version": "yarn-qa-correctness/v1", "prompt_sha256": S,
         "temperature": 0.0, "seed": 0, "max_tokens": 64}


def cell(role="A1", mock=True, **kw):
    r = {"schema": y.DECISION_SCHEMA, "record_kind": "cell", "mock": mock, "comparison": "A0_vs_A1",
         "arm_role": role, "suite": "helmet", "task": "nq", "nominal_length": 245760,
         "model_pin": "q38-27b-gguf", "comparable_to_published": False,
         "prompt_n": {"source": "server_timings", "count": 10, "min": 229500, "median": 240000, "max": 245000},
         "bin": "229376-262144", "zone": "native",
         "source_pins": {"helmet_pin": H, "config_file": "nq_240k.yaml", "config_sha256": S, "max_test_samples": 10},
         "judged": True, "judge_pin": JUDGE,
         "judge_validation": {"n_compared": 50, "accuracy": 0.9, "cohen_kappa": 0.8, "sheet_sha256": S},
         "metric": "accuracy", "value": 0.7, "n_units": 10, "unit": "items", "n_unjudged": 0}
    r.update(kw)
    return r


def verdict(mock=True, **kw):
    r = cell(mock=mock, arm_role="A1_vs_A0", record_kind="verdict")
    for k in ("metric", "value", "n_units", "unit", "n_unjudged"):
        del r[k]
    r.update({"verdict": "INCONCLUSIVE", "rule_id": "net-paired-mcnemar/v1", "alpha": 0.05,
              "b_a0right_a1wrong": 1, "c_a0wrong_a1right": 2, "n_pairs": 10, "p_one_sided": 0.9,
              "mean_score_diff_a1_minus_a0": 0.1, "a0_record_sha256": S, "a1_record_sha256": S})
    r.update(kw)
    return r


def write(tmp_path, decisions, **kw):
    items = []
    for i, d in enumerate(decisions):
        f = tmp_path / f"rec{i}.json"
        f.write_text(json.dumps(d))
        items.append({"record_path": f, "decision": d})
    return y.write_belief_measurements(tmp_path, run_id="y1", producer="runner", records=items,
                                       emitted_at=WHEN, **kw)


def test_mock_cell_round_trips_with_judge_pin_and_zone(tmp_path):
    side = write(tmp_path, [cell("A0"), cell("A1"), verdict()], fixture=True)
    assert y.native_rows(side) == ()                      # real readers never see fixtures
    nats = y.native_rows(side, allow_fixture=True)
    assert len(nats) == 3
    tup = y.project(nats[0])
    d = tup.extra["decision"]
    assert d["judge_pin"]["model"] == "mock-judge" and d["zone"] == "native" and d["bin"] == "229376-262144"
    assert tup.extra["mock"] is True and tup.attestation_locator.startswith("fixture:")
    assert ct.grade(tup)[:2] == ("Judged", "Located")      # observation; no protocol
    cats = {y.project(n).category for n in nats}
    assert cats == {"BASELINE", "CANDIDATE"}
    v = [y.project(n) for n in nats if n["row"]["metric"] == y.VERDICT_METRIC][0]
    assert v.extra["decision"]["verdict"] == "INCONCLUSIVE" and v.reps == 10 and v.reps_basis == "pairs"


def test_frames_for_sidecar_fixture_gate(tmp_path):
    side = write(tmp_path, [cell()], fixture=True)
    assert y.frames_for_sidecar(side, as_of=WHEN) == []
    assert y.frames_for_sidecar(side, as_of=WHEN, allow_fixture=True)


def test_real_run_refuses_mock(tmp_path):
    with pytest.raises(y.CaptureError, match="mock"):
        write(tmp_path, [cell()])


def test_fixture_flag_refuses_non_mock(tmp_path):
    with pytest.raises(y.CaptureError, match="mock records only"):
        write(tmp_path, [cell(mock=False)], fixture=True)


def test_real_cell_with_protocol_is_witnessed(tmp_path):
    side = write(tmp_path, [cell(mock=False)], protocol_id="PROTO")
    (nat,) = y.native_rows(side)
    assert ct.grade(y.project(nat))[:2] == ("Witnessed", "Attested")


def test_unmeasured_or_nominal_zone_refused(tmp_path):
    for kw in ({"prompt_n": {"source": "nominal", "count": 1, "min": 5, "median": 5, "max": 5}},
               {"zone": "mixed"}, {"zone": "beyond-native"}, {"bin": "0-32768"}):
        with pytest.raises(y.CaptureError):
            write(tmp_path, [cell(mock=False, **kw)])
    d = cell(mock=False)
    del d["prompt_n"]
    with pytest.raises(y.CaptureError, match="prompt_n"):
        write(tmp_path, [d])


def test_judge_pin_required_when_judged_and_forbidden_otherwise(tmp_path):
    d = cell(mock=False)
    del d["judge_pin"]
    with pytest.raises(y.CaptureError, match="judge_pin"):
        write(tmp_path, [d])
    with pytest.raises(y.CaptureError, match="unjudged"):
        write(tmp_path, [cell(mock=False, judged=False)])
    d = cell(mock=False)
    del d["judge_validation"]
    with pytest.raises(y.CaptureError, match="judge_validation"):
        write(tmp_path, [d])
    d = cell(mock=False, judged=False, judge_pin=None, judge_validation=None, metric="exact_match")
    del d["judge_pin"], d["judge_validation"]
    write(tmp_path, [d])


def test_verdict_kept_verbatim_and_bad_verdict_refused(tmp_path):
    with pytest.raises(y.CaptureError, match="verdict"):
        write(tmp_path, [verdict(verdict="MAYBE")])
    with pytest.raises(y.CaptureError):
        write(tmp_path, [verdict(n_pairs=2)])
    (nat,) = y.native_rows(write(tmp_path, [verdict(mock=False, verdict="NOT-FAIL")]))
    assert y.project(nat).extra["decision"]["verdict"] == "NOT-FAIL"


def test_absent_pin_fields_refused(tmp_path):
    for k in ("helmet_pin", "config_sha256"):
        d = cell(mock=False)
        del d["source_pins"][k]
        with pytest.raises(y.CaptureError):
            write(tmp_path, [d])
    d = cell(mock=False, suite="oolong", unit="items", source_pins={"source_revision": "oolongbench/oolong-synth@" + H, "vendored_sha256": S})
    with pytest.raises(y.CaptureError, match="contexts"):
        write(tmp_path, [d])


def test_tampered_row_voids_file_and_attestation_grades_down(tmp_path):
    side = write(tmp_path, [cell(mock=False)], protocol_id="P")
    (tmp_path / "rec0.json").write_text("{}")
    (nat,) = y.native_rows(side)
    assert ct.grade(y.project(nat))[:2] != ("Witnessed", "Attested")
    row = json.loads(side.read_text())
    row["value"] = 0.1
    side.write_text(json.dumps(row) + "\n")
    assert y.native_rows(side) == ()


def test_no_sidecar_zero_rows_and_foreign_projection(tmp_path):
    assert y.native_rows(tmp_path / "none.jsonl") == ()
    with pytest.raises(ct.ProjectionError):
        y.project({"row": {}})


RULER_PINS = {"ruler_repo": "/mnt/raid0/llm/data/eval/ruler/repo", "ruler_pin": "ab17b78", "essay_sha256": S,
              "words_source": "essay_vocab_hyphen_pairs",
              "deviations": ["word_keys: hyphenated pairs from Paul Graham essay vocabulary",
                             "essay_source: local PaulGrahamEssays/*.txt"]}


def ruler_cell(role="A1", **kw):
    return cell(role, mock=False, suite="ruler", task="niah_multikey_2", nominal_length=32768,
                prompt_n={"source": "model_tokenizer_json", "count": 5, "min": 30000, "median": 31000, "max": 32000},
                bin="0-32768", zone="native", source_pins=dict(RULER_PINS), judged=False,
                judge_pin=None, judge_validation=None, metric="accuracy", n_units=5, **kw)


def _clean(r):
    return {k: v for k, v in r.items() if k not in ("judge_pin", "judge_validation")}


def test_ruler_final_fixture_projects_as_observation(tmp_path):
    recs = [_clean(ruler_cell("A0")), _clean(ruler_cell("A1"))]
    side = write(tmp_path, [dict(r, mock=True) for r in recs], fixture=True)
    nats = y.native_rows(side, allow_fixture=True)
    assert len(nats) == 2
    for n in nats:
        tup = y.project(n)
        d = tup.extra["decision"]
        assert d["suite"] == "ruler" and d["source_pins"]["words_source"] == "essay_vocab_hyphen_pairs"
        assert d["comparable_to_published"] is False and tup.protocol_id == ""
        assert ct.grade(tup)[:2] == ("Judged", "Located")
    # real (non-mock) ruler record projects too
    side2 = write(tmp_path, [_clean(ruler_cell("A1"))])
    assert len(y.native_rows(side2)) == 1


def test_ruler_interim_fixture_projects_nothing(tmp_path):
    # an INTERIM pass never calls the writer, so no sidecar exists and nothing projects
    assert y.native_rows(tmp_path / y.SIDECAR_NAME) == ()
    assert y.frames_for_sidecar(tmp_path / y.SIDECAR_NAME, as_of=WHEN) == []


def test_ruler_pins_required_and_published_comparison_refused():
    base = _clean(ruler_cell())
    assert y.record_problems(base) == []
    for k in ("ruler_pin", "essay_sha256", "words_source", "deviations"):
        bad = copy.deepcopy(base)
        del bad["source_pins"][k]
        assert y.record_problems(bad), k
    bad = copy.deepcopy(base)
    bad["source_pins"]["deviations"] = []
    assert y.record_problems(bad)
    bad = dict(base, comparable_to_published=True)
    assert y.record_problems(bad)
