"""VB-AK-BW-CENSUS-WIRE: AutoKernel bandwidth census records project as BASELINE observations,
graded by the one shared ladder.

Fixture: `fixtures/bw_census_fixture.json` -- 14 real records of the live
`mi210_bandwidth_census.json` (3 q8wv GPU, 2 mmid GPU, 2 rka-ipb GPU, the 6 a3b CPU records whose
`measured_at` is empty, and the q38fn CPU record whose `result_sha256` is null), with the census's
`applied` ledger. Everything here uses a temp ledger; the live ledger is never touched.
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
from adapters import autokernel_bw_census as bw  # noqa: E402
from claim_tuple import ProjectionError, grade, to_frames  # noqa: E402
from ledger import Ledger  # noqa: E402

FIXTURE = HERE / "fixtures" / "bw_census_fixture.json"
AS_OF = "2026-11-24T12:00:00Z"
SUPPORT = "epyc.vidya/frame/evidence_supports_claim/v1"
Q8 = "27b-q8_0|attn_q_v5i|12288x5120|n1"
CPU_A3B = "cpu|a3b-q8_0-cpu|MUL_MAT:lm_head|quarter-24t|n1"


def _doc() -> dict:
    return json.loads(FIXTURE.read_text())


def _write(tmp: Path, doc: dict, name: str = "mi210_bandwidth_census.json") -> Path:
    path = tmp / name
    path.write_text(json.dumps(doc))
    return path


def _row(doc: dict, key: str) -> dict:
    got = bw.classify(doc, locator=f"{bw.LOCATOR_PREFIX}/t/c.json", sha256="0" * 64)
    (row,) = [r for r in got["rows"] if r["key"] == key]
    return row


def test_fixture_is_small():
    assert FIXTURE.stat().st_size <= 30 * 1024


def test_real_gpu_record_projects_one_baseline_observation():
    row = _row(_doc(), Q8)
    tup = bw.project(row)
    rec = row["record"]
    assert tup.category == "BASELINE" and tup.metric == bw.METRIC and tup.unit == "GB/s"
    assert tup.metric_direction == "higher_better" and tup.value == rec["gbps"] == 1098.9
    assert tup.date == rec["measured_at"] == "2026-11-22T13:07:57Z"
    assert tup.protocol_id == ""
    assert tup.attestation_sha256 == rec["result_sha256"]
    assert tup.attestation_locator == f"{bw.LOCATOR_PREFIX}{Q8}@{rec['result_sha256']}"
    assert tup.extra["source_row"] == rec["source_row"]
    assert tup.source_kind == bw.SOURCE_KIND == "autokernel-bw-census"
    assert tup.observation == {"retrofit": True}
    assert tup.measurement_id.startswith(bw.MEASUREMENT_PREFIX)
    assert tup.measurement_id.endswith(rec["result_sha256"][:16])
    assert tup.applicability["device"] == "mi210" and tup.applicability["kernel"] == "attn_q_v5i"
    assert tup.applicability["shape"] == "12288x5120"
    assert "model=27b-q8_0" in tup.applicability["config_key"] and "n=1" in tup.applicability["config_key"]
    assert tup.extra["device_basis"] == "file_default" and tup.extra["applied_bound"] is True


def test_grade_is_the_shared_ladder_and_an_observation():
    tup = bw.project(_row(_doc(), Q8))
    # No protocol: Judged/Located -- an observation, never decision-gating. The adapter grades nothing.
    assert grade(tup)[:2] == ("Judged", "Located")
    assert any("no protocol" in r for r in grade(tup)[2])
    assert grade(tup) == grade(dataclasses.replace(tup, observation={}))  # observation is inert to grading
    # Same tuple, same grade as the one ladder says; nothing census-specific moves it.
    assert grade(dataclasses.replace(tup, protocol_id="")) == grade(tup)


def test_batch_width_n_is_not_a_repetition_count():
    tup = bw.project(_row(_doc(), "27b-q8_0|attn_q_v5i|12288x5120|n16"))
    assert tup.extra["batch_n"] == 16 and tup.reps is None
    assert tup.reps_basis.startswith("unknown")
    assert "n=16" in tup.applicability["config_key"]


def test_missing_warrant_records_are_dropped_as_unknown_never_filled(tmp_path):
    doc = _doc()
    got = bw.classify(doc, locator=f"{bw.LOCATOR_PREFIX}/t/c.json", sha256="0" * 64)
    keys = {r["key"] for r in got["rows"]}
    unknown = {u["key"]: u["missing"] for u in got["unknown"]}
    assert len(keys) == 7 and got["refused"] == []
    # the 6 a3b CPU records: empty measured_at; the q38fn record: null result_sha256
    assert sum(1 for k in unknown if k.startswith("cpu|a3b-q8_0-cpu")) == 6
    assert all(v == ["measured_at"] for k, v in unknown.items() if "a3b" in k)
    assert unknown["cpu|q38fn-ud-iq4xs-cpu|forward_m1_dense|quarter-24t|n1"] == ["result_sha256"]
    assert keys.isdisjoint(unknown)
    # the file reader agrees and reports the same drops
    path = _write(tmp_path, doc)
    assert len(bw.native_rows(path)) == 7
    assert {u["key"] for u in bw.dropped(path)["unknown"]} == set(unknown)


@pytest.mark.parametrize("field", ["source_row", "result_sha256", "measured_at"])
@pytest.mark.parametrize("blank", [None, "", "   "])
def test_each_warrant_field_missing_drops_the_record(field, blank):
    doc = _doc()
    doc["records"][Q8][field] = blank
    got = bw.classify(doc, locator=f"{bw.LOCATOR_PREFIX}/t/c.json", sha256="0" * 64)
    assert Q8 not in {r["key"] for r in got["rows"]}
    assert {"key": Q8, "missing": [field]} in got["unknown"]
    doc2 = _doc()
    del doc2["records"][Q8][field]
    got2 = bw.classify(doc2, locator=f"{bw.LOCATOR_PREFIX}/t/c.json", sha256="0" * 64)
    assert {"key": Q8, "missing": [field]} in got2["unknown"]


def test_project_itself_refuses_a_row_without_warrant():
    row = _row(_doc(), Q8)
    for field in ("source_row", "result_sha256", "measured_at"):
        bad = copy.deepcopy(row)
        bad["record"][field] = ""
        with pytest.raises(ProjectionError, match="UNKNOWN warrant"):
            bw.project(bad)


def test_record_that_does_not_rederive_is_refused_by_name_never_repaired():
    doc = _doc()
    doc["records"][Q8]["gbps"] = 1300.0
    got = bw.classify(doc, locator=f"{bw.LOCATOR_PREFIX}/t/c.json", sha256="0" * 64)
    assert Q8 not in {r["key"] for r in got["rows"]}
    (refused,) = got["refused"]
    assert refused["key"] == Q8 and "does not re-derive" in refused["reason"]
    # one bad record never costs the file its good ones
    assert len(got["rows"]) == 6


def test_result_sha_disagreeing_with_the_census_applied_ledger_is_refused():
    doc = _doc()
    doc["records"][Q8]["result_sha256"] = "ab" * 32
    got = bw.classify(doc, locator=f"{bw.LOCATOR_PREFIX}/t/c.json", sha256="0" * 64)
    (refused,) = got["refused"]
    assert "applied" in refused["reason"]


@pytest.mark.parametrize("field,value", [("result_sha256", "xyz"), ("measured_at", "yesterday"),
                                         ("gbps", float("nan")), ("gbps", -1.0), ("n", True),
                                         ("device", "tpu")])
def test_malformed_present_values_are_refused(field, value):
    doc = _doc()
    doc["records"][Q8][field] = value
    got = bw.classify(doc, locator=f"{bw.LOCATOR_PREFIX}/t/c.json", sha256="0" * 64)
    assert Q8 not in {r["key"] for r in got["rows"]}
    assert [r["key"] for r in got["refused"]] == [Q8]


def test_projectable_cpu_record_keeps_its_own_device_and_config():
    doc = _doc()
    doc["records"][CPU_A3B]["measured_at"] = "2026-11-21"  # a date-only warrant is still a warrant
    tup = bw.project(_row(doc, CPU_A3B))
    assert tup.applicability["device"] == "cpu" and tup.extra["device_basis"] == "record"
    assert tup.date == "2026-11-21" and "config=quarter-24t" in tup.applicability["config_key"]
    assert grade(tup)[:2] == ("Judged", "Located")


def test_device_gpu_is_an_alias_of_mi210_and_says_so():
    # N8: the census producer writes device "gpu" on its MI210 records
    doc = _doc()
    doc["records"][Q8]["device"] = "gpu"
    tup = bw.project(_row(doc, Q8))
    assert tup.applicability["device"] == "mi210" and tup.extra["device_basis"] == "record_alias:gpu"
    # identity is keyed on the census key + result sha, so the alias does not fork the measurement
    assert tup.measurement_id == bw.project(_row(_doc(), Q8)).measurement_id


def test_unknown_device_word_is_still_refused_by_name():
    doc = _doc()
    doc["records"][Q8]["device"] = "tpu"
    got = bw.classify(doc, locator=f"{bw.LOCATOR_PREFIX}/t/c.json", sha256="0" * 64)
    (refused,) = got["refused"]
    assert "'tpu'" in refused["reason"] and "gpu" in refused["reason"]


def test_identity_is_stable_and_distinguishes_key_and_result():
    a = bw.project(_row(_doc(), Q8))
    assert a.measurement_id == bw.project(_row(_doc(), Q8)).measurement_id
    other = bw.project(_row(_doc(), "27b-q8_0|attn_q_v5i|12288x5120|n16"))
    assert other.measurement_id != a.measurement_id
    doc = _doc()
    doc["applied"][0]["sha256"] = doc["records"][Q8]["result_sha256"] = "cd" * 32
    assert bw.project(_row(doc, Q8)).measurement_id != a.measurement_id  # a re-measurement is a new claim


def test_non_census_documents_project_nothing():
    for doc in ({"schema": "something.else", "records": {}}, [], {"records": {}}):
        assert bw.classify(doc, locator=f"{bw.LOCATOR_PREFIX}/x", sha256="0" * 64)["rows"] == []


def test_symlink_and_non_json_are_refused(tmp_path):
    real = _write(tmp_path, _doc())
    link = tmp_path / "link.json"
    link.symlink_to(real)
    with pytest.raises(ProjectionError):
        bw.read_census(link)
    junk = tmp_path / "junk.json"
    junk.write_text("{not json")
    with pytest.raises(ProjectionError, match="not JSON"):
        bw.read_census(junk)


def test_registered_projection_is_ours():
    assert bw.SOURCE_KIND in ct.registered()
    assert ct.registered()[bw.SOURCE_KIND].__module__ == bw.__name__


def test_ingest_dispatch_appends_to_a_temp_ledger_only(tmp_path):
    assert "ak-bw-census" in ingest_sources.SOURCES
    assert ingest_sources.SOURCES["ak-bw-census"].default == bw.LIVE_CENSUS  # read-only default
    path = _write(tmp_path, _doc())
    ledger = Ledger(tmp_path / "ledger.jsonl")
    report = ingest_sources.ingest(ledger, "ak-bw-census", [path], as_of=AS_OF)
    assert report["units_projected"] == 1 and report["rows_projected"] == 7
    assert report["refused"] == [] and report["declined"] == []
    frames = [r.frame for r in ledger.read_all()]
    support = [f for f in frames if f["frame_type"] == SUPPORT]
    assert len(support) == 7 and ledger.verify() == []
    expected = {(g[0], g[1]) for g in (grade(bw.project(n))[:2] for n in bw.native_rows(path))}
    assert {(f["assertion"]["grade"]["Q"], f["assertion"]["grade"]["T"]) for f in support} == expected
    assert expected == {("Judged", "Located")}  # the dispatcher adds no ladder
    assert all(f["provenance"].get("retrofit") is True for f in frames
               if f["frame_type"].endswith("source_observed/v1"))
    # idempotent: same census read again adds nothing new under --only-new
    again = ingest_sources.ingest(ledger, "ak-bw-census", [path], as_of=AS_OF, only_new=True)
    assert again["frames_emitted"] == 0


def test_ingest_report_counts_dropped_unknown_and_refused_records(tmp_path):
    doc = _doc()
    doc["records"][Q8]["device"] = "tpu"  # one refused record
    path = _write(tmp_path, doc)
    ledger = Ledger(tmp_path / "ledger.jsonl")
    report = ingest_sources.ingest(ledger, "ak-bw-census", [path], as_of=AS_OF, dry_run=True)
    dropped = report["dropped_records"]
    assert dropped["unknown"] == 7 and dropped["refused"] == 1 and dropped["errors"] == []
    assert {e["key"] for e in dropped["examples"] if e["kind"] == "refused"} == {Q8}
    text = ingest_sources.human(report)
    assert "unknown-warrant=7" in text and "refused=1" in text


def test_ingest_report_has_no_dropped_block_for_sources_without_the_hook(tmp_path):
    assert ingest_sources.SOURCES["ak-bw-census"].dropped == "dropped"
    # the census's second projection (AK-BNSIG signatures) reports drops the same way
    assert all(s.dropped == "" for n, s in ingest_sources.SOURCES.items()
               if n not in ("ak-bw-census", "ak-bottleneck-signature"))


def test_ingest_dry_run_appends_nothing_and_missing_path_is_reported(tmp_path):
    path = _write(tmp_path, _doc())
    ledger = Ledger(tmp_path / "ledger.jsonl")
    report = ingest_sources.ingest(ledger, "ak-bw-census", [path, tmp_path / "absent.json"],
                                   as_of=AS_OF, dry_run=True)
    assert report["rows_projected"] == 7 and report["missing"] == [str(tmp_path / "absent.json")]
    assert report["dry_run"] is True and report["frames_emitted"] > 0
    assert not (tmp_path / "ledger.jsonl").exists() or ledger.read_all() == []


def test_to_frames_roundtrip_matches_the_shared_carrier():
    tup = bw.project(_row(_doc(), Q8))
    frames = to_frames(tup, as_of=AS_OF, adapter_id=bw.ADAPTER_ID, authority=bw.AUTHORITY)
    ev = [f for f in frames if f["frame_type"] == SUPPORT][0]["assertion"]
    assert ev["grade"] == {"Q": "Judged", "T": "Located"} and ev["category"] == "BASELINE"
    assert ev["metric"] == bw.METRIC and ev["value"] == ct.frame_scalar(1098.9) and ev["unit"] == "GB/s"
