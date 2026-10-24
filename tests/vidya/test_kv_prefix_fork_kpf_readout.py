"""VB-KVU-PF.3 / .4: the 2026-10-23 KPF read-out sidecars (aggregates only; the per-request rows files are NOT shipped,
so attestation is carried as absent, never skipped) project through claim_tuple.grade() -- or are refused for a reason."""
import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "vidya"))
import claim_tuple as ct  # noqa: E402
from adapters import kv_prefix_fork as kpf  # noqa: E402

FX = Path(__file__).parent / "fixtures"


def _copy(tmp_path, name):
    shutil.copytree(FX / name, tmp_path / name)
    return tmp_path / name / "belief_measurements.jsonl"


def _lines(path):
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]


def test_kpf18_item_185_projects_11_of_14_hsf_declined(tmp_path):
    sc = _copy(tmp_path, "kpf18_s1r")
    rows = _lines(sc)
    assert len(rows) == 14 and {r["kpf18_item"] for r in rows} == {185}
    assert all(kpf.validate_row(r) == [] for r in rows)
    natives = kpf.native_rows(sc)
    # VB-KVU-PF.6: the 3 hsf_L<L> records validate (they never void the file) but project nothing: their only
    # projectable number was a hit count of 0.
    assert len(natives) == 11 and not any(n["row"]["arm"].startswith("hsf_L") for n in natives)
    tuples = [kpf.project(n) for n in natives]
    assert len({t.measurement_id for t in tuples}) == 11
    assert all(t.extra["kpf18_item"] == 185 and t.extra["kpf18_arm"] == t.extra["arm"] for t in tuples)
    assert all(ct.grade(t)[0] for t in tuples)                       # the shared ladder grades each (rows may be absent)


def test_185_arm_vocabulary_and_undeclared_sub_arm_still_voids(tmp_path):
    for arm in ("A_tailonly_tail512", "item2_pcache_g3s2", "long_teacher_forced", "kpf191a_flagoff_g1", "hsf_L32000"):
        assert kpf.is_sub_arm(arm, 185)
    assert not kpf.is_sub_arm("hsf_Lx", 185) and not kpf.is_sub_arm("hsf_L8000", 184)
    sc = _copy(tmp_path, "kpf18_s1r")
    rows = _lines(sc)
    rows[3]["kpf18_arm"] = rows[3]["arm"] = "invented_arm"
    sc.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    assert kpf.native_rows(sc) == ()                                 # an undeclared arm voids the whole file


def test_kpf13_projects_2_of_2_zero_cell_attempt_kept(tmp_path):
    sc = _copy(tmp_path, "kpf13_restore")
    natives = kpf.native_rows(sc)
    assert len(natives) == 2
    aborted, full = [kpf.project(n) for n in natives]
    assert aborted.metric == "kpf_conformance_cells_scored" and aborted.value == 0
    assert aborted.attestation_sha256 == "" and "attested-absent" in aborted.extra["attestation_absent"]
    assert full.metric == "kpf_conformance_cell_pass_fraction" and full.reps == 24
    assert full.value == round(20 / 24, 6) and full.extra["counts"]["pass"] == 20 and full.extra["counts"]["fail"] == 4
    assert full.extra["decisions"]["decision_grade"] is True            # producer's word carried verbatim
    assert aborted.extra["decisions"]["decision_grade"] is False
    for t in (aborted, full):
        assert ct.grade(t)[0]                                           # the shared ladder decides


def test_kpf13_cells_without_own_counts_are_refused(tmp_path):
    sc = _copy(tmp_path, "kpf13_restore")
    rows = _lines(sc)
    rows[1]["equivalence"]["configs"]["A"] = None                     # counts must come from the record itself
    assert any("cannot be invented" in p for p in kpf.validate_row(rows[1]))


def test_kpf174_refused_for_writer_hash_defect_not_for_missing_equivalence(tmp_path):
    sc = _copy(tmp_path, "kpf174_swa")
    rows = _lines(sc)
    assert len(rows) == 5 and {r["arm"] for r in rows} == {
        "kpf174_191a_flag_off", "kpf174_mut_dft_partial_noop", "kpf191a_flag_on", "kpf191a_mut_dft_no_transfer"}
    for r in rows:
        problems = kpf.validate_row(r)
        assert len(problems) == 1 and "WRITE-SIDE defect" in problems[0]   # arm + missing equivalence now accepted
    assert kpf.native_rows(sc) == ()


def test_kpf174_would_project_once_writer_hash_is_sound(tmp_path):
    """The projection itself works: re-seal the stored bodies the way the writer should have (str keys) and 5/5 project."""
    rows = _lines(_copy(tmp_path, "kpf174_swa"))
    for r in rows:
        r["record_sha256"] = kpf._digest({k: v for k, v in r.items() if k != "record_sha256"})
    sc = tmp_path / "resealed.jsonl"
    sc.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    natives = kpf.native_rows(sc)
    assert len(natives) == 5
    by_arm = {}
    for n in natives:
        t = kpf.project(n)
        by_arm.setdefault(t.extra["arm"], []).append(t)
    assert [t.metric for t in by_arm["kpf174_191a_flag_off"]] == ["kpf_conformance_cells_scored",
                                                                   "kpf_conformance_cell_pass_fraction"]
    assert by_arm["kpf174_191a_flag_off"][1].value == round(4 / 6, 6)
    mut = by_arm["kpf174_mut_dft_partial_noop"][0]
    assert mut.metric == "kpf_mutant_detected_fraction" and mut.value == 1.0 and mut.reps == 2
    assert by_arm["kpf191a_mut_dft_no_transfer"][0].value == 1.0
    assert by_arm["kpf191a_flag_on"][0].value == round(2 / 3, 6)


def test_kpf174b_rules_v2_arms_project_pass_fraction(tmp_path):
    """17.4b (rules v2): the spec-off C1 and junction-sweep launches are declared honest arms -> pass fraction."""
    sc = _copy(tmp_path, "kpf174b_rules_v2")
    rows = _lines(sc)
    assert {r["arm"] for r in rows} == {"kpf174b_c1_spec_off", "kpf174b_junction_sweep"}
    assert all(kpf.is_conformance(r) and kpf.validate_row(r) == [] for r in rows)
    natives = kpf.native_rows(sc)
    assert len(natives) == 2
    by_arm = {t.extra["arm"]: t for t in (kpf.project(n) for n in natives)}
    spec_off, sweep = by_arm["kpf174b_c1_spec_off"], by_arm["kpf174b_junction_sweep"]
    for t in (spec_off, sweep):
        assert t.metric == "kpf_conformance_cell_pass_fraction" and not t.extra["mutant_arm"]
        assert ct.grade(t)[0]                                           # the shared ladder decides
    assert spec_off.value == round(1 / 2, 6) and spec_off.reps == 2
    assert sweep.value == round(4 / 10, 6) and sweep.reps == 10
    assert sweep.extra["counts"]["fail"] == 6 and spec_off.extra["counts"]["verdict"] == "FAIL"  # verbatim


def test_kpf174b_unknown_arm_still_declined(tmp_path):
    sc = _copy(tmp_path, "kpf174b_rules_v2")
    rows = _lines(sc)
    rows[1]["arm"] = "kpf174b_junction_sweep_v3"                         # not a declared arm of KPF-17.4+17.4a+19.1a
    rows[1]["record_sha256"] = kpf._digest({k: v for k, v in rows[1].items() if k != "record_sha256"})
    assert not kpf.is_conformance(rows[1]) and kpf.validate_row(rows[1])
    sc.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    assert kpf.native_rows(sc) == ()                                     # an undeclared arm voids the whole file


# ------------------------------------------------------------------ VB-KVU-PF.6
# Fixtures are the two 2026-10-24 read-out sidecars, TRIMMED (item3v2 token streams, s1r per-cell detail and
# counters dropped) and RESEALED with the adapter's own digest; their per-request rows files are not shipped.


def test_item3v2_sameshape_projects_4_of_4_with_partial_load_kept(tmp_path):
    sc = _copy(tmp_path, "kpf18_item3v2")
    rows = _lines(sc)
    assert [r["arm"] for r in rows] == ["item3v2_load0", "item3v2_load1", "item3v2_load2", "item3v2_load2"]
    assert all("kpf18_arm" not in r for r in rows) and all(kpf.validate_row(r) == [] for r in rows)
    tuples = [kpf.project(n) for n in kpf.native_rows(sc)]
    assert len(tuples) == 4 and len({t.measurement_id for t in tuples}) == 4
    full = [t for t in tuples if t.metric == "kpf18_item3v2_judged_pairs_fork_effect_candidate"]
    partial = [t for t in tuples if t.metric == "kpf18_item3v2_judged_pairs_scored"]
    assert len(full) == 3 and len(partial) == 1
    for t in full:
        # A_child is the one judged fork_effect_candidate; B_child_recorded is recorded, not judged.
        assert (t.value, t.reps, t.metric_direction) == (1, 3, "lower_better")
        assert t.extra["classes"]["A_child"] == "fork_effect_candidate"
        assert t.extra["classes"]["B_child_recorded"] == "fork_effect_candidate"
        assert t.extra["predeclaration_sha256"].startswith("417310869f16")
        assert "FORK_EFFECT" not in t.claim                            # the run verdict is not re-derived on read
    assert sorted(t.extra["load"] for t in full) == [0, 1, 2]
    p = partial[0]
    assert (p.value, p.reps, p.extra["partial"], p.extra["valid"]) == (0, 1, True, False)
    assert p.observation["outcome_native"] == "partial (budget-aborted) load"
    for t in tuples:
        assert t.protocol_id == "" and ct.grade(t)[0] == "Judged"     # shared ladder decides: an OBSERVATION


def test_item3v2_load_must_match_its_own_block_and_partial_needs_the_flag(tmp_path):
    sc = _copy(tmp_path, "kpf18_item3v2")
    rows = _lines(sc)
    bad = dict(rows[0], arm="item3v2_load1")
    assert any("does not name load 1" in p for p in kpf.validate_row(bad))
    bare = {k: v for k, v in rows[2].items() if k != "partial"}
    assert any("neither an item3v2 block nor partial" in p for p in kpf.validate_row(bare))
    wrong_item = dict(rows[0], kpf18_item=184)
    assert any("not in" in p for p in kpf.validate_row(wrong_item))
    mismatched = dict(rows[0], kpf18_arm="item3v2_load9")            # a present locator must still match
    assert any("matching kpf18_arm" in p for p in kpf.validate_row(mismatched))


def test_step7_graphs_on_hsf_records_validate_but_project_nothing(tmp_path):
    sc = _copy(tmp_path, "kpf18_step7_graphs_on")
    rows = _lines(sc)
    assert [r["arm"] for r in rows] == ["hsf_L8000", "hsf_L16000", "hsf_L32000"]
    assert all(kpf.validate_row(r) == [] for r in rows)
    assert kpf.native_rows(sc) == ()                                  # declined, never a hit count of 0
    with pytest.raises(ct.ProjectionError, match="0 hit count"):
        kpf.project({"row": rows[0], "sidecar_path": str(sc)})


# ------------------------------------------------------------------ VB-KPF174C-ARM
# Fixture: one KPF-17.4c record written by research kpf174c_bisect.py @ 1157adc2f (its own main() and seal) against the
# driver tests' allocator-faithful LayoutFake: no server, no model (window_id fixture-layoutfake-20261024, small
# synthetic geometry). Aggregates only; the rows file is not shipped (attestation is absent wherever its declared path
# does not exist).


def test_kpf174c_bisect_projects_matched_pair_fraction_with_decision_words_verbatim(tmp_path):
    sc = _copy(tmp_path, "kpf174c_bisect")
    rows = _lines(sc)
    assert len(rows) == 1 and rows[0]["arm"] == "kpf174c_bisect_spec_off" and rows[0]["kpf_task"] == "KPF-17.4c"
    assert kpf.is_conformance(rows[0]) and kpf.validate_row(rows[0]) == []
    natives = kpf.native_rows(sc)
    assert len(natives) == 1
    t = kpf.project(natives[0])
    assert t.metric == "kpf174c_matched_pair_identical_fraction" and t.unit == "fraction"
    assert (t.value, t.reps) == (1.0, 12) and "layout-matched pairs" in t.reps_basis
    c = t.extra["counts"]
    assert (c["attempts"], c["pass"], c["fail"], c["invalid"], c["out_of_scope"]) == (12, 12, 0, 0, 0)
    assert c["verdict"] == "none_reproduced" and c["pairs_planned"] == 12 and c["cells_interrupted"] == 0
    # the predeclared decision words ride in extra exactly as the record states them (never re-derived on read)
    d = rows[0]["decisions"]
    assert (t.extra["locus"], t.extra["explains_174b"], t.extra["decision_grade"]) == (
        d["locus"], d["explains_174b"], d["decision_grade"])
    assert t.extra["locus"] == "none_reproduced" and t.extra["explains_174b"] == "control_layout_numerics"
    assert "none_reproduced" not in t.claim and "control_layout_numerics" not in t.claim
    assert t.extra["rules_sha256"].startswith("b871d9a0") and not t.extra["mutant_arm"]
    # the declared rows path may or may not exist on the reading host; either way the digest is the record's own
    assert isinstance(t.attestation_present, bool) and t.attestation_sha256 == rows[0]["rows_sha256"]
    assert t.applicability["varied"] == ["restore_path", "kv_layout"]
    assert ct.grade(t)[0]                                               # the shared ladder decides


def test_kpf174c_unknown_arm_still_declined(tmp_path):
    sc = _copy(tmp_path, "kpf174c_bisect")
    rows = _lines(sc)
    rows[0]["arm"] = "kpf174c_bisect_spec_on"                            # not a declared arm of KPF-17.4c
    rows[0]["record_sha256"] = kpf._digest({k: v for k, v in rows[0].items() if k != "record_sha256"})
    assert not kpf.is_conformance(rows[0]) and kpf.validate_row(rows[0])
    sc.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    assert kpf.native_rows(sc) == ()                                     # an undeclared arm voids the whole file


def test_kpf174c_counts_cannot_be_invented_or_overfull(tmp_path):
    rows = _lines(_copy(tmp_path, "kpf174c_bisect"))
    bare = {k: v for k, v in rows[0].items() if k != "launch_verdict"}
    bare["record_sha256"] = kpf._digest({k: v for k, v in bare.items() if k != "record_sha256"})
    assert any("cannot be invented" in p for p in kpf.validate_row(bare))
    over = json.loads(json.dumps(rows[0]))
    over["launch_verdict"]["invalid"] = 1                                # 12 + 0 + 1 > 12 attempts
    over["record_sha256"] = kpf._digest({k: v for k, v in over.items() if k != "record_sha256"})
    assert any("cannot be invented" in p for p in kpf.validate_row(over))
    tampered = dict(rows[0], window_id="elsewhere")                      # the seal still binds every field
    assert any("does not re-derive" in p for p in kpf.validate_row(tampered))
