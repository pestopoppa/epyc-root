"""VB-M4-PBHOL-WIRE: the M4.2 PB-HOL-1-on-candidate phase dirs project through `pb_hol` (one claim per phase unit).

Fixture: `fixtures/belief_p1/pb_hol_m4/` -- the launcher's PREDECLARATION.md, RUN_RECORD.json and VERDICT.json copied
verbatim, the six phase dirs trimmed (see its PROVENANCE.json; completion token ids are SYNTHETIC with the real
equality pattern).
"""
import hashlib
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
from ledger import Ledger  # noqa: E402

FX = Path(__file__).parent / "fixtures" / "belief_p1" / "pb_hol_m4"
AS_OF = "2026-10-23T22:00:00Z"
PHASES = ["comp-champion", "comp-m4off", "off512", "srpf2048", "srpf2048cap0", "srpf512"]


@pytest.fixture()
def launcher(tmp_path):
    shutil.copytree(FX, tmp_path / "m4-srpf-pbhol")
    return tmp_path / "m4-srpf-pbhol"


def _tuples(launcher) -> dict:
    out = {}
    for phase in PHASES:
        natives = pb_hol.native_rows(launcher / "out" / phase)
        assert len(natives) == 1, phase
        out[phase] = pb_hol.project(natives[0])
    return out


def _load(path):
    return json.loads(path.read_text())


def _dump(path, doc):
    path.write_text(json.dumps(doc, indent=1) + "\n")


def _rows(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _write_rows(path, rows):
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))


def test_whole_out_dir_is_six_units_six_claims_with_distinct_ids(launcher):
    units = ingest_sources.SOURCES["pb-hol"].units(launcher / "out")
    assert [u.name for u in units] == PHASES
    ts = _tuples(launcher)
    ids = {t.measurement_id for t in ts.values()}
    assert len(ids) == 6 and all(i.startswith("pbhol-m4:v1:m4-srpf-pbhol-20261023T2028Z:") for i in ids)
    for t in ts.values():
        # the run is INCOMPLETE (C2 NOT_MEASURED) and its predeclaration is harness-local: empty protocol_id, every
        # claim an OBSERVATION; no normalised outcome anywhere
        assert t.protocol_id == "" and ct.grade(t)[:2] == ("Judged", "Located")
        assert "outcome" not in t.observation
        assert t.extra["run_verdict"] == "INCOMPLETE" and t.extra["claim_class"] == "INDICATIVE"
        assert t.extra["predeclaration_sha256"].startswith("c97394d2")
        assert t.source_kind == pb_hol.SOURCE_KIND and t.attestation_verified is True


def test_c1_phase_claims_carry_valid_rep_medians_and_the_verbatim_condition_word(launcher):
    ts = _tuples(launcher)
    t = ts["srpf512"]
    assert (t.metric, t.unit, t.metric_direction, t.value, t.reps) == (pb_hol.METRIC, "ms", "lower_better", 3365.6, 3)
    obs = t.observation
    assert obs["anchor_value"] == 3376.2 and obs["n_pairs"] == 3 and obs["retrofit"] is True
    assert obs["effect_rel"] == pytest.approx(3365.6 / 3376.2 - 1)
    assert obs["outcome_native"] == "PASS" and "C1_srpf512" in obs["outcome_reason"]
    assert "0.997x" in t.claim and "INCOMPLETE" in t.claim and t.extra["invalid_runs"] == []
    t2 = ts["srpf2048"]
    assert t2.value == 6353.4 and t2.observation["anchor_value"] == 6392.5 and t2.extra["ratio"] == 0.994
    cap0 = ts["srpf2048cap0"]
    assert cap0.value == 12578.3 and "outcome_native" not in cap0.observation and "never gating" in cap0.claim


def test_scope_is_read_from_each_phase_servers_argv(launcher):
    ts = _tuples(launcher)
    a = ts["srpf2048cap0"].applicability
    assert a["model_file"].endswith("Qwen3.8-27B-Q8_0.gguf") and a["backend"] == "gpu" and a["np"] == 3
    assert a["knob_family"] == "slot_serving" and a["varied"] == ["short_slot_index_order"]
    k = a["knobs"]
    assert (k["b"], k["ub"], k["prefill_order"], k["prefill_contend_cap"], k["dflash2"]) == (2048, 2048, "srpf", 0, True)
    assert a["build_sha"] == "c6ca031ac"
    off = ts["off512"].applicability["knobs"]
    assert off["b"] == 512 and "prefill_order" not in off
    champ = ts["comp-champion"].applicability
    assert champ["build_sha"] == "141e4bcf5" and "gpu-20261023-141e4bcf5-lbh" in champ["kernel"]["build_path"]
    assert ts["comp-m4off"].applicability["kernel"]["execution_digest"] == _load(
        launcher / "RUN_RECORD.json")["m4_llama_server_sha256"]


def test_c2_not_measured_is_an_attested_row_with_no_value_and_its_invalid_runs(launcher):
    t = _tuples(launcher)["off512"]
    assert t.value is None and t.reps is None and t.observation == {}
    assert t.extra["condition_word"] == "NOT_MEASURED" and "NOT MEASURED" in t.claim
    inv = t.extra["invalid_runs"]
    assert [(i["arm"], i["rep"]) for i in inv] == [("B-off512", 1), ("B-off512", 2), ("B-off512", 3)]
    assert all(i["why"] == "long finished before the short was answered" for i in inv)
    assert t.extra["valid_A"] == [3372.6, 3381.1, 3383.2] and t.extra["valid_B"] == []
    assert t.extra["observation_withheld"]["anchor_value"] == 3381.1
    _, _, evidence = ct.to_frames(t, as_of=AS_OF, adapter_id=pb_hol.ADAPTER_ID, authority=pb_hol.AUTHORITY)
    assert "value" not in evidence["assertion"] and evidence["assertion"]["reps"] is None


def test_c3_rides_the_candidate_comp_phase_once_and_the_champion_control_its_own(launcher):
    ts = _tuples(launcher)
    c3 = ts["comp-m4off"]
    assert c3.metric == pb_hol.M4_METRIC_IDENTICAL and (c3.value, c3.reps) == (5, 5)
    assert c3.observation["outcome_native"] == "PASS" and c3.observation["anchor_value"] == 5
    assert c3.extra["mismatches"] == [] and c3.extra["excluded_champion_nondeterministic"] == ["pair4k.0", "pair4k.1"]
    ctl = ts["comp-champion"]
    assert ctl.metric == pb_hol.M4_METRIC_DETERMINISTIC and (ctl.value, ctl.reps) == (5, 7)
    assert "outcome_native" not in ctl.observation
    assert sum(1 for t in ts.values() if t.extra.get("condition") == pb_hol.M4_C3_KEY) == 1


def test_observation_and_scope_never_move_the_grade(launcher):
    for t in _tuples(launcher).values():
        assert ct.grade(t) == ct.grade(replace(t, observation={}, applicability={}))


def test_a_pass_run_maps_through_the_predeclared_reading_only(launcher):
    """SYNTHETIC verdict words (test data): the overall PASS / FAIL gate the normalised outcome."""
    for name in ("VERDICT.json", "RUN_RECORD.json"):
        doc = _load(launcher / name)
        doc["verdict"] = "PASS"
        _dump(launcher / name, doc)
    ts = _tuples(launcher)
    assert ts["srpf512"].observation["outcome"] == "null" and ts["comp-m4off"].observation["outcome"] == "null"
    assert "outcome" not in ts["srpf2048cap0"].observation and ts["off512"].observation == {}
    for name in ("VERDICT.json", "RUN_RECORD.json"):
        doc = _load(launcher / name)
        doc["verdict"] = "FAIL"
        if name == "VERDICT.json":
            doc["conditions"]["C1_srpf512"] = "FAIL"
        _dump(launcher / name, doc)
    t = pb_hol.project(pb_hol.native_rows(launcher / "out" / "srpf512")[0])
    assert t.observation["outcome_native"] == "FAIL" and t.observation["outcome"] == "regressed"
    assert ct.grade(t)[:2] == ("Judged", "Located")


def test_a_predeclaration_that_does_not_rehash_is_refused(launcher):
    p = launcher / "PREDECLARATION.md"
    p.write_text(p.read_text() + "\nedited after the run\n")
    with pytest.raises(ct.ProjectionError, match="PREDECLARATION"):
        pb_hol.native_rows(launcher / "out" / "srpf512")
    rec = _load(launcher / "RUN_RECORD.json")
    del rec["predeclaration_sha256"]
    _dump(launcher / "RUN_RECORD.json", rec)
    with pytest.raises(ct.ProjectionError, match="unbound"):
        pb_hol.native_rows(launcher / "out" / "srpf512")


def test_a_verdict_disagreeing_with_the_run_record_is_refused(launcher):
    rec = _load(launcher / "RUN_RECORD.json")
    rec["verdict"] = "PASS"
    _dump(launcher / "RUN_RECORD.json", rec)
    with pytest.raises(ct.ProjectionError, match="verdict"):
        pb_hol.native_rows(launcher / "out" / "off512")


def test_rows_that_do_not_rederive_are_refused(launcher):
    rows_path = launcher / "out" / "srpf512" / "pb_hol_1.jsonl"
    rows = _rows(rows_path)
    for r in rows:
        if r.get("arm") == "B-srpf512":
            r["short_ttft_ms"] += 1.0
            break
    _write_rows(rows_path, rows)
    with pytest.raises(ct.ProjectionError, match="re-derive"):
        pb_hol.native_rows(launcher / "out" / "srpf512")


def test_a_verdict_partition_that_does_not_rederive_is_refused(launcher):
    v = _load(launcher / "VERDICT.json")
    v["phases"]["off512"]["invalid"] = []
    _dump(launcher / "VERDICT.json", v)
    with pytest.raises(ct.ProjectionError, match="partition"):
        pb_hol.native_rows(launcher / "out" / "off512")
    v["phases"]["off512"] = _load(FX / "VERDICT.json")["phases"]["off512"]
    v["phases"]["srpf512"]["ratio"] = 0.5
    _dump(launcher / "VERDICT.json", v)
    with pytest.raises(ct.ProjectionError, match="ratio"):
        pb_hol.native_rows(launcher / "out" / "srpf512")


def test_completion_digests_are_rehashed_and_the_c3_detail_rederived(launcher):
    rows_path = launcher / "out" / "comp-m4off" / "pb_hol_1.jsonl"
    original = _rows(rows_path)
    rows = [dict(r) for r in original]
    rows[0]["tokens"] = [999] + rows[0]["tokens"][1:]
    _write_rows(rows_path, rows)
    with pytest.raises(ct.ProjectionError, match="re-hash"):
        pb_hol.native_rows(launcher / "out" / "comp-m4off")
    # a consistently re-hashed but DIFFERENT candidate completion no longer matches the verdict's detail
    rows[0]["tokens_sha256"] = hashlib.sha256(json.dumps(rows[0]["tokens"]).encode()).hexdigest()
    _write_rows(rows_path, rows)
    for phase in ("comp-m4off", "comp-champion"):
        with pytest.raises(ct.ProjectionError, match="completions detail"):
            pb_hol.native_rows(launcher / "out" / phase)


def test_a_server_binary_other_than_the_recorded_one_is_refused(launcher):
    p = launcher / "out" / "srpf512" / "summary.json"
    s = _load(p)
    s["servers"][0]["binary_sha256"] = "0" * 64
    _dump(p, s)
    with pytest.raises(ct.ProjectionError, match="m4_llama_server_sha256"):
        pb_hol.native_rows(launcher / "out" / "srpf512")


def test_attempt_dirs_and_phase_dirs_without_their_launcher_decline(launcher, tmp_path):
    shutil.copytree(launcher / "out" / "srpf512", launcher / "out" / "srpf512.attempt-1")
    assert pb_hol.native_rows(launcher / "out" / "srpf512.attempt-1") == []
    lone = tmp_path / "lone" / "x" / "srpf512"
    shutil.copytree(launcher / "out" / "srpf512", lone)
    assert pb_hol.native_rows(lone) == []


def test_a_disagreeing_readback_scopes_nothing(launcher):
    p = launcher / "out" / "srpf2048" / "summary.json"
    s = _load(p)
    s["servers"][0]["readback"]["proc_cmdline_matches_argv"] = False
    _dump(p, s)
    assert pb_hol.project(pb_hol.native_rows(launcher / "out" / "srpf2048")[0]).applicability == {}


def test_ingest_dry_run_and_only_new_append_each_claim_once(launcher, tmp_path):
    ledger = Ledger(tmp_path / "ledger.jsonl")
    report = ingest_sources.ingest(ledger, "pb-hol", [launcher / "out"], as_of=AS_OF, dry_run=True)
    assert (report["units_matched"], report["units_projected"], report["rows_projected"]) == (6, 6, 6)
    assert report["declined"] == [] and report["refused"] == []
    report = ingest_sources.ingest(ledger, "pb-hol", [launcher / "out", launcher / "out" / "comp-m4off"],
                                   as_of=AS_OF, only_new=True)
    assert len(ledger) == 18 and ledger.verify() == []
