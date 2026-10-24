"""HSF-5.P microbench sidecar -> strict reader -> shared grade (VB-HSF5P-WRITE). No process is touched.

The fixture under ``fixtures/hsf5p/`` was written by the item's real analyzer
(``/mnt/raid0/llm/tmp/f8-launchers-20261024/hsf-5p/gpu/analyze.py``) from synthetic inputs, so the reader is
tested against the producer's actual output, not a hand-written imitation.
"""
import hashlib
import json
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402
import ingest_sources  # noqa: E402
from adapters import hsf5p_microbench as reader  # noqa: E402

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "hsf5p"


@pytest.fixture()
def item(tmp_path):
    shutil.copytree(FIXTURE, tmp_path / "hsf5p")
    return tmp_path / "hsf5p" / "gpu"


def _rows(item):
    return [json.loads(x) for x in (item / reader.SIDECAR).read_text().splitlines() if x.strip()]


def _rewrite(item, rows, reseal=True):
    for r in rows:
        if reseal:
            r["content_sha256"] = reader.body_sha256(r)
    (item / reader.SIDECAR).write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows))


def test_fixture_projects_every_row_and_grades_as_observation(item):
    natives = reader.native_rows(item)
    assert len(natives) == 7
    tuples = [reader.project(n) for n in natives]
    by_key = {t.extra["key"]: t for t in tuples}
    assert set(by_key) >= {"G1_decode", "G2_graphs_reused", "G3_restore", "G4_mirror_engaged"}
    g1 = by_key["G1_decode"]
    assert g1.metric == "hsf5p_decode_delta_pct" and g1.metric_direction == "lower_better" and g1.reps == 6
    assert g1.protocol_id == "" and g1.category == "CANDIDATE" and g1.attestation_verified is True
    assert by_key["G3_restore"].value == 0 and by_key["G3_restore"].reps == 2
    assert by_key["G4_mirror_engaged"].value == 4 and "bound k=6" in by_key["G4_mirror_engaged"].claim
    copy = by_key["1b:tail_128frags:d2h:auto"]
    assert copy.value == 61.0 and copy.reps == 3 and copy.unit == "us"
    assert copy.applicability["build_sha"] == "14d0f7fa2"
    assert len({t.measurement_id for t in tuples}) == 7
    for t in tuples:
        assert ct.grade(t)[:2] == ("Judged", "Located")   # no protocol: OBSERVATION, attested and located
    assert reader.frames_for_path(item, as_of="2026-10-24T12:00:00Z")


def test_units_find_the_sidecar_from_the_item_or_its_parent(item):
    assert reader.units(item) == [item / reader.SIDECAR]
    assert reader.units(item.parent) == [item / reader.SIDECAR]
    assert reader.units(item / "VERDICT.json") == []


def test_undecided_run_has_no_rows_and_projects_nothing(item):
    (item / reader.SIDECAR).write_text("")
    assert reader.native_rows(item) == ()


@pytest.mark.parametrize("mutate,match", [
    (lambda rows: rows[0].update(value=rows[0]["value"] + 1), "content_sha256"),
    (lambda rows: [r.update(value=0.0) for r in rows if r["key"] == "G1_decode"], "do not re-derive"),
    (lambda rows: [r.update(reps=5) for r in rows if r["key"] == "G1_decode"], "do not re-derive"),
    (lambda rows: rows[0].update(extra_field=1), "field set"),
    (lambda rows: [r.update(verdict="INCONCLUSIVE") for r in rows], "undecided run"),
    (lambda rows: [r.update(metric="hsf5p_other") for r in rows if r["key"] == "G2_graphs_reused"], "metric"),
    (lambda rows: [r.update(predeclaration_sha256="0" * 64) for r in rows], "predeclaration digest"),
    (lambda rows: rows[-1].update(run_id="hsf5p:other"), "more than one run"),
])
def test_rows_that_do_not_re_derive_are_refused(item, mutate, match):
    rows = _rows(item)
    mutate(rows)
    _rewrite(item, rows, reseal=match != "content_sha256")
    with pytest.raises(ct.ProjectionError, match=match):
        reader.native_rows(item)


def test_edited_input_is_refused(item):
    log = item / "out" / "server.B.log"
    log.write_text(log.read_text().replace("replay_steps=4", "replay_steps=5"))
    with pytest.raises(ct.ProjectionError, match="does not re-hash"):
        reader.native_rows(item)


def test_rehashed_but_inconsistent_input_is_refused(item):
    # a forger who re-hashes the edited input still cannot make the value follow from it
    log = item / "out" / "server.B.log"
    log.write_text(log.read_text().replace("replay_steps=4", "replay_steps=5"))
    rows = _rows(item)
    digest = hashlib.sha256(log.read_bytes()).hexdigest()
    for r in rows:
        r["inputs"]["out/server.B.log"] = digest
    _rewrite(item, rows)
    with pytest.raises(ct.ProjectionError, match="G4_mirror_engaged value/reps"):
        reader.native_rows(item)


def test_unverified_copy_in_bench_refuses_copy_rows(item):
    bench = item / "out" / "bench12.jsonl"
    lines = bench.read_text().splitlines()
    lines[1] = lines[1].replace('"ok": true', '"ok": false')
    bench.write_text("\n".join(lines) + "\n")
    rows = _rows(item)
    digest = hashlib.sha256(bench.read_bytes()).hexdigest()
    for r in rows:
        r["inputs"]["out/bench12.jsonl"] = digest
    _rewrite(item, rows)
    with pytest.raises(ct.ProjectionError, match="unverified copy"):
        reader.native_rows(item)


def test_source_is_registered_for_cli_ingest():
    src = ingest_sources.SOURCES["hsf5p-microbench"]
    assert src.module == "hsf5p_microbench" and src.task == "VB-HSF5P-WRITE"
    assert src.load().SOURCE_KIND == "hsf5p-microbench"
