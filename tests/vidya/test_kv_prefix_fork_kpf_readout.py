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


def test_kpf18_item_185_projects_14_of_14(tmp_path):
    sc = _copy(tmp_path, "kpf18_s1r")
    rows = _lines(sc)
    assert len(rows) == 14 and {r["kpf18_item"] for r in rows} == {185}
    assert all(kpf.validate_row(r) == [] for r in rows)
    natives = kpf.native_rows(sc)
    assert len(natives) == 14
    tuples = [kpf.project(n) for n in natives]
    assert len({t.measurement_id for t in tuples}) == 14
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
