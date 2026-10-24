"""VB-LB7-STALL-WIRE: UFH14-LB7 launcher dirs project to re-derived, protocol-cited stall-attribution tuples."""
import copy
import hashlib
import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "vidya"))
import claim_tuple as ct  # noqa: E402
from adapters import ufh14_lb7_stall as lb7  # noqa: E402

FIXTURE = Path(__file__).parent / "fixtures" / "ufh14_lb7"
REAL = Path("/mnt/raid0/llm/tmp/f8-launchers-20261023/locals-ufh14-lb7-stall")


def write(tmp_path: Path) -> Path:
    run = Path(tmp_path) / "locals-ufh14-lb7-stall"
    shutil.copytree(FIXTURE, run)
    return run


@pytest.fixture()
def run(tmp_path):
    return write(tmp_path)


def _project(run):
    return [ct.registered()[lb7.SOURCE_KIND](n) for n in lb7.native_rows(run)]


def _edit(path: Path, fn):
    doc = json.loads(path.read_text())
    fn(doc)
    path.write_text(json.dumps(doc, indent=1) + "\n")


def _seal(run: Path):
    """Rewrite VERDICT.json / RUN_RECORD.json from the (edited) attribs, as the producer's aggregate would."""
    by = {}
    for p in sorted((run / "out").glob("*.attrib.json")):
        d = json.loads(p.read_text())
        by[d["label"]] = d
    v = lb7.rederive_verdict(by)
    (run / "VERDICT.json").write_text(json.dumps(v, indent=1) + "\n")
    _edit(run / "RUN_RECORD.json", lambda d: d.update(verdict=v["verdict"], sessions_ok=sum(1 for d in by.values() if d.get('status') == 'OK')))
    return v


def test_round_trip_projects_six_cited_tuples(run):
    tuples = _project(run)
    assert [t.metric for t in tuples] == [
        "ufh14_lb7_client_gap_delta", "ufh14_lb7_delta_neighbour_idle_save", "ufh14_lb7_delta_own_prompt_load",
        "ufh14_lb7_delta_other_prompt_load", "ufh14_lb7_delta_queue_and_loop_busy", "ufh14_lb7_on_copy_throughput"]
    pre = hashlib.sha256((run / "PREDECLARATION.md").read_bytes()).hexdigest()
    by_metric = {t.metric: t for t in tuples}
    assert by_metric["ufh14_lb7_client_gap_delta"].value == 38.973
    assert by_metric["ufh14_lb7_delta_other_prompt_load"].value == 19.907
    assert by_metric["ufh14_lb7_delta_queue_and_loop_busy"].value == -0.649
    for t in tuples:
        assert t.protocol_id == "" and t.extra["predeclaration_sha256"] == pre
        assert t.attestation_sha256 == hashlib.sha256((run / "VERDICT.json").read_bytes()).hexdigest()
        assert t.extra["verdict"] == "UNATTRIBUTED" and "UNATTRIBUTED" in t.claim
        assert t.observation["retrofit"] is True
        assert t.applicability["build_sha"] == "49550eda5"
        assert t.applicability["kernel"]["execution_digest"].startswith("51baea5e")
        assert t.applicability["varied"] == ["cache_idle_slots"]
        # the shared ladder decides; this module only supplies the inputs
        assert ct.grade(t) == ct.grade(t)
        assert ct.grade(t)[:2] == ("Judged", "Located")
    assert all(t.reps == 3 for t in tuples[:5]) and tuples[5].reps == 60


def test_no_ladder_registered_here():
    src = (ROOT / "scripts" / "vidya" / "adapters" / "ufh14_lb7_stall.py").read_text()
    assert "register_ladder" not in src and "def grade" not in src


def test_harness_local_predeclaration_is_not_a_protocol(run):
    """A ratified protocol id would lift the grade; the harness-local predeclaration must not."""
    t = _project(run)[0]
    from dataclasses import replace
    assert ct.grade(t)[:2] == ("Judged", "Located")
    assert ct.grade(replace(t, protocol_id="x"))[:2] != ("Judged", "Located")


@pytest.mark.skipif(not REAL.is_dir(), reason="real UFH14-LB7 run not present")
def test_real_run_rederives_and_matches():
    rows = lb7.native_rows(REAL)
    assert len(rows) == 6 and {r["verdict"] for r in rows} == {"UNATTRIBUTED"}


def test_tampered_per_turn_row_is_refused(run):
    _edit(run / "out" / "s1-ON.attrib.json", lambda d: d["per_turn"][3].__setitem__("gap_client_s", 99.0))
    with pytest.raises(ct.ProjectionError):
        lb7.native_rows(run)


def test_tampered_turn2plus_summary_is_refused(run):
    _edit(run / "out" / "s2-OFF.attrib.json", lambda d: d["turn2plus"].__setitem__("gap_client_mean_s", 5.0))
    with pytest.raises(ct.ProjectionError, match="turn2plus"):
        lb7.native_rows(run)


def test_tampered_verdict_figure_is_refused(run):
    _edit(run / "VERDICT.json", lambda d: d["median_dGroups_s"].__setitem__("OTHER_PROMPT_LOAD", 25.0))
    with pytest.raises(ct.ProjectionError, match="VERDICT.json"):
        lb7.native_rows(run)


def test_tampered_verdict_word_is_refused(run):
    _edit(run / "VERDICT.json", lambda d: d.__setitem__("verdict", "OWNER=OTHER_PROMPT_LOAD"))
    with pytest.raises(ct.ProjectionError):
        lb7.native_rows(run)


def test_run_record_verdict_must_agree(run):
    _edit(run / "RUN_RECORD.json", lambda d: d.__setitem__("verdict", "NOT_REPRODUCED"))
    with pytest.raises(ct.ProjectionError, match="RUN_RECORD"):
        lb7.native_rows(run)


def test_group_partition_inconsistency_is_refused(run):
    _edit(run / "out" / "s4-ON.attrib.json",
          lambda d: d["per_turn"][5]["components_s"].__setitem__("other_load", 50.0))
    with pytest.raises(ct.ProjectionError):
        lb7.native_rows(run)


def test_incomplete_run_is_declined_with_reason(run):
    for label in ("s3-OFF", "s6-OFF"):
        (run / "out" / f"{label}.attrib.json").unlink()
    v = _seal(run)
    assert v["verdict"] == "INCOMPLETE" and v["n_valid_pairs"] == 1
    assert lb7.native_rows(run) == []
    assert "INCOMPLETE" in lb7.decline_reason(run)


def test_failed_session_makes_pair_invalid_and_run_incomplete(run):
    for label in ("s4-ON", "s5-ON"):
        _edit(run / "out" / f"{label}.attrib.json", lambda d: d.__setitem__("status", "FAIL"))
    v = _seal(run)
    assert v["verdict"] == "INCOMPLETE"
    assert lb7.native_rows(run) == []


def test_instrument_fail_is_declined():
    by = {}
    for p in sorted((FIXTURE / "out").glob("*.attrib.json")):
        d = json.loads(p.read_text())
        by[d["label"]] = d
    bad = copy.deepcopy(by)
    bad["s1-ON"]["align"]["lag_p95_s"] = 2.0   # alignment gate fails; the producer's rule says INSTRUMENT_FAIL
    assert lb7.rederive_verdict(bad)["verdict"] == "INSTRUMENT_FAIL"


def test_instrument_fail_unit_projects_nothing(run):
    _edit(run / "out" / "s1-ON.attrib.json", lambda d: d["align"].__setitem__("n_lag_below_0_2s", 18))
    _edit(run / "out" / "s1-ON.attrib.json", lambda d: d["align"].__setitem__("lag_p95_s", 0.0008))
    # make the pair's match gate fail honestly: 10 of 18 turns unmatched -> but per_turn rows would then differ
    _edit(run / "out" / "s1-ON.attrib.json", lambda d: d.update(n_matched=10, unmatched=[{"x": i} for i in range(8)]))
    v = _seal(run)
    assert v["verdict"] == "INSTRUMENT_FAIL"
    assert lb7.native_rows(run) == []
    assert "INSTRUMENT_FAIL" in lb7.decline_reason(run)


def test_not_reproduced_still_projects_with_null_outcome(run):
    def flatten(d):
        for t in d["per_turn"]:
            t["gap_client_s"] = 1.0
        d["turn2plus"]["gap_client_mean_s"] = 1.0
        d["turn2plus"]["gap_client_median_s"] = 1.0
    _edit(run / "out" / "s1-ON.attrib.json", flatten)
    v = _seal(run)
    assert v["verdict"] == "NOT_REPRODUCED"
    tuples = _project(run)
    assert tuples and all(t.observation.get("outcome") == "null" for t in tuples)


def test_foreign_verdict_is_declined(tmp_path):
    d = tmp_path / "other"
    d.mkdir()
    (d / "VERDICT.json").write_text(json.dumps({"verdict": "CARRY"}))
    assert lb7.native_rows(d) == []
    assert lb7.decline_reason(d) is None


def test_wrong_item_is_refused(run):
    _edit(run / "RUN_RECORD.json", lambda d: d.__setitem__("item", "something-else"))
    with pytest.raises(ct.ProjectionError, match="item"):
        lb7.native_rows(run)


def test_unproven_readback_drops_scope_not_the_tuple(run):
    _edit(run / "out" / "s1-ON" / "report.json", lambda d: d["preflight"].__setitem__("kfd", []))
    tuples = _project(run)
    assert len(tuples) == 6 and tuples[0].applicability == {}
