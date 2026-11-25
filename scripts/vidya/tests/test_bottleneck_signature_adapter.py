"""VB-AK-BNSIG-WIRE (AK-BNSIG-P3): census bottleneck signatures project as Judged/Located observations,
one tuple per (kernel record x build x fired class), graded by the one shared ladder.

Fixture `fixtures/bnsig_census_fixture.json`: one census record signed by research
`census_update.apply_signature` from the 2026-11-25 q8wt diag RESULT (V5I q8mf: issue_bound primary,
over_subscribed marginal, over_fetch + latency_bound ruled out). Temp ledgers only.
"""
from __future__ import annotations

import copy
import dataclasses
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import claim_tuple as ct  # noqa: E402
import ingest_sources  # noqa: E402
from adapters import autokernel_bottleneck_signature as bn  # noqa: E402
from claim_tuple import ProjectionError, grade  # noqa: E402

FIXTURE = HERE / "fixtures" / "bnsig_census_fixture.json"
RID = "27b-q8_0|gemv_q8mf|5120x17408|n8"
LOC = f"{bn.LOCATOR_PREFIX}/t/c.json"


def _doc() -> dict:
    return json.loads(FIXTURE.read_text())


def _rows(doc: dict) -> dict:
    return {r["class"]: r for r in bn.classify(doc, locator=LOC, sha256="0" * 64)["rows"]}


def test_projects_one_tuple_per_fired_class_judged_located():
    rows = _rows(_doc())
    assert set(rows) == {"issue_bound", "over_subscribed"}
    issue = bn.project(rows["issue_bound"])
    assert issue.category == "BASELINE" and issue.protocol_id == "" and issue.source_kind == bn.SOURCE_KIND
    assert issue.metric == "bottleneck_issue_bound_issue_busy" and issue.value == pytest.approx(0.4645)
    assert issue.metric_direction == "lower_better"
    assert grade(issue)[:2] == ("Judged", "Located")
    assert issue.observation == {"retrofit": False, "outcome_native": "issue_bound"}
    assert issue.extra["ruled_out"] == ["over_fetch", "latency_bound"]
    assert "build=unknown" in issue.applicability["config_key"] and issue.extra["build_basis"] == "unknown"
    oversub = bn.project(rows["over_subscribed"])
    assert oversub.value == pytest.approx(0.5274) and "(marginal)" in oversub.claim
    assert oversub.measurement_id != issue.measurement_id
    assert grade(oversub)[:2] == ("Judged", "Located")


def test_build_is_carried_when_recorded_and_forks_identity():
    doc = _doc()
    a = bn.project(_rows(doc)["issue_bound"])
    doc["records"][RID]["signature"]["build"] = "ffc1bac82"
    b = bn.project(_rows(doc)["issue_bound"])
    assert b.extra["build"] == "ffc1bac82" and "build=ffc1bac82" in b.applicability["config_key"]
    assert a.measurement_id != b.measurement_id


@pytest.mark.parametrize("field", ["source_row", "result_sha256", "measured_at"])
def test_missing_warrant_dropped(field):
    doc = _doc()
    doc["records"][RID]["signature"][field] = ""
    got = bn.classify(doc, locator=LOC, sha256="0" * 64)
    assert got["rows"] == [] and got["unknown"] == [{"key": RID, "missing": [field]}]


def test_refs_sha_mismatch_refused():
    doc = _doc()
    doc["signature_applied"][0]["sha256"] = "c" * 64
    got = bn.classify(doc, locator=LOC, sha256="0" * 64)
    assert got["rows"] == [] and "signature_applied" in got["refused"][0]["reason"]


def test_failed_reference_check_is_refused_not_projected():
    doc = _doc()
    sig = doc["records"][RID]["signature"]
    sig["reference_check"]["ok"] = False
    got = bn.classify(doc, locator=LOC, sha256="0" * 64)
    assert got["rows"] == [] and "states no limiter" in got["refused"][0]["reason"]
    doc = _doc()
    doc["records"][RID]["signature"].update({"class": "reference_incoherent", "classes": ["reference_incoherent"]})
    assert bn.classify(doc, locator=LOC, sha256="0" * 64)["rows"] == []


def test_ruled_out_class_never_projects_and_marginal_is_kept():
    doc = _doc()
    doc["records"][RID]["signature"]["ruled_out"].append("over_subscribed")  # contradictory record
    issue = bn.project(_rows(doc)["issue_bound"])
    assert "over_subscribed" not in issue.extra["ruled_out"]   # a fired (marginal) class is never ruled out


def test_unsigned_records_are_not_this_source():
    doc = _doc()
    doc["records"][RID].pop("signature")
    assert bn.classify(doc, locator=LOC, sha256="0" * 64) == {"rows": [], "unknown": [], "refused": []}


def test_file_reader_and_source_registration(tmp_path):
    path = tmp_path / "mi210_bandwidth_census.json"
    path.write_text(json.dumps(_doc()))
    assert len(bn.native_rows(path)) == 2 and bn.dropped(path) == {"unknown": [], "refused": []}
    src = ingest_sources.SOURCES["ak-bottleneck-signature"]
    assert src.module == "autokernel_bottleneck_signature" and src.task == "VB-AK-BNSIG-WIRE"


def test_no_new_ladder_registered():
    assert set(ct.ladders()) <= set(ct.SOURCE_CLASSES)
    module, fn = ct.ladders()["measurement"]
    assert fn is ct.grade and module == "scripts/vidya/claim_tuple.py"
    tup = bn.project(_rows(_doc())["issue_bound"])
    assert grade(tup) == grade(dataclasses.replace(tup, observation={}))   # observation inert to grading


def test_project_refuses_wrong_shape_and_unfired_class():
    row = _rows(_doc())["issue_bound"]
    with pytest.raises(ProjectionError):
        bn.project({k: v for k, v in row.items() if k != "class"})
    bad = copy.deepcopy(row)
    bad["class"] = "over_fetch"
    with pytest.raises(ProjectionError, match="did not fire"):
        bn.project(bad)


def test_temp_ledger_ingest_appends_two_observations(tmp_path):
    from ledger import Ledger
    path = tmp_path / "mi210_bandwidth_census.json"
    path.write_text(json.dumps(_doc()))
    ledger = Ledger(tmp_path / "ledger.jsonl")
    report = ingest_sources.ingest(ledger, "ak-bottleneck-signature", [path], as_of="2026-11-25T12:00:00Z")
    assert report["rows_projected"] == 2 and not report["refused"] and report["frames_emitted"] > 0
    again = ingest_sources.ingest(ledger, "ak-bottleneck-signature", [path], as_of="2026-11-25T12:00:00Z", dry_run=True)
    assert again["rows_projected"] == 2


def test_row_absent_from_signature_applied_is_refused():
    doc = _doc()
    doc["signature_applied"] = []
    got = bn.classify(doc, locator=LOC, sha256="0" * 64)
    assert got["rows"] == [] and "absent from the census `signature_applied`" in got["refused"][0]["reason"]
    row = _rows(_doc())["issue_bound"]
    with pytest.raises(ProjectionError, match="absent"):
        bn.project(dict(row, applied_sha256=None))


def test_applied_bound_is_recorded():
    assert bn.project(_rows(_doc())["issue_bound"]).extra["applied_bound"] is True
