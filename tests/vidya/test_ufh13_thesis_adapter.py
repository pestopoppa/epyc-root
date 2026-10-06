"""Synthetic source-contract controls for the UFH-13 thesis measurement adapter."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402
import cli  # noqa: E402
import ingest_sources  # noqa: E402
from adapters import ufh13_thesis as adapter  # noqa: E402
from claim_tuple import ProjectionError  # noqa: E402


def _fixtures():
    path = HERE / "ufh13_thesis_fixtures.py"
    spec = importlib.util.spec_from_file_location("_ufh13_thesis_fixtures", path)
    if spec is None or spec.loader is None:
        raise AssertionError("UFH-13 synthetic fixture module is not loadable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run(tmp_path: Path, **kwargs):
    run = _fixtures().write_run(tmp_path, **kwargs)
    return run, run / "belief_measurements.jsonl"


def _rewrite_sidecar(path: Path, mutate) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    rows = [json.loads(line) for line in lines if line.strip()]
    mutate(rows)
    path.write_text("".join(json.dumps(row, sort_keys=True, allow_nan=True) + "\n"
                                    for row in rows), encoding="utf-8")


def test_actual_producer_rows_project_through_shared_measurement_grade(tmp_path):
    fixtures = _fixtures()
    run, sidecar = _run(tmp_path)
    natives = adapter.native_rows(sidecar)
    tuples = [adapter.project(native) for native in natives]
    assert len(tuples) == len(natives) == 9
    assert len({t.measurement_id for t in tuples}) == 9
    assert {t.category for t in tuples} == {"BASELINE", "CANDIDATE"}
    assert all(t.reps == 3 and t.reps_basis == "scored" for t in tuples)
    assert all(t.protocol_id == "" for t in tuples)
    assert all(t.extra["research_commit"] == fixtures.SYNTHETIC_RESEARCH_COMMIT
               for t in tuples)
    assert all(t.source_kind == "ufh13-thesis-measurement" for t in tuples)
    assert all(ct.grade(t)[:2] == ("Judged", "Located") for t in tuples)
    assert {t.metric_direction for t in tuples} == {"higher_better", "lower_better"}
    assert all(t.attestation_verified is True and t.attestation_present is True
               for t in tuples)

    rows_as_json = json.dumps(natives, sort_keys=True)
    tuples_as_json = json.dumps([t.extra for t in tuples], sort_keys=True)
    frames = [frame for t in tuples for frame in ct.to_frames(
        t, as_of="2026-10-06T00:00:00Z", adapter_id=adapter.ADAPTER_ID,
        authority=adapter.AUTHORITY)]
    frames_as_json = json.dumps(frames, sort_keys=True)
    assert fixtures.SYNTHETIC_SECRET not in rows_as_json
    assert fixtures.SYNTHETIC_SECRET not in tuples_as_json
    assert fixtures.SYNTHETIC_SECRET not in frames_as_json
    assert all(t.extra["instrument_class"] == "serving" for t in tuples)
    assert all("instrument_class" not in native["row"] for native in natives)
    assert (run / "records.jsonl").read_text().find(fixtures.SYNTHETIC_SECRET) >= 0


def test_none_native_metric_stays_omitted(tmp_path):
    result = _fixtures().synthetic_result()
    result["d"] = None
    _, sidecar = _run(tmp_path, result=result)
    natives = adapter.native_rows(sidecar)
    assert len(natives) == 8
    assert "ufh13.consultant_cost_fraction_d" not in {
        native["row"]["metric"] for native in natives
    }


def test_source_is_defaultless_and_registered_once_in_existing_cli(tmp_path):
    source = ingest_sources.SOURCES["ufh13-thesis-measurement"]
    assert source.default is None
    assert source.module == "ufh13_thesis"
    assert "ufh13-thesis-measurement" in cli._FILE_SOURCES
    assert cli._FILE_SOURCES.count("ufh13-thesis-measurement") == 1
    assert callable(source.load().project)
    run, _ = _run(tmp_path)
    assert source.units(run) == [run / "belief_measurements.jsonl"]


def test_pilot_manifest_is_refused(tmp_path):
    _, sidecar = _run(tmp_path, pilot=True)
    with pytest.raises(ProjectionError, match="pilot manifests"):
        adapter.native_rows(sidecar)


@pytest.mark.parametrize("commit", ["", "a" * 39, "A" * 40, "not-a-commit"])
def test_missing_or_malformed_manifest_source_pin_is_refused(tmp_path, commit):
    run, sidecar = _run(tmp_path)
    manifest_path = run / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    if commit:
        manifest["research_commit"] = commit
    else:
        del manifest["research_commit"]
    manifest_path.write_text(json.dumps(manifest, sort_keys=True) + "\n")
    with pytest.raises(ProjectionError, match="research_commit"):
        adapter.native_rows(sidecar)


@pytest.mark.parametrize("change", ["date", "naive-date", "reps"])
def test_sidecar_requires_native_iso_date_and_shared_scored_reps(tmp_path, change):
    _, sidecar = _run(tmp_path)

    def mutate(rows):
        if change == "date":
            rows[1]["date"] = "2026-10-07T00:00:00+00:00"
        elif change == "naive-date":
            rows[0]["date"] = "2026-10-06T00:00:00"
        elif change == "reps":
            rows[1]["reps"] = 4

    _rewrite_sidecar(sidecar, mutate)
    with pytest.raises(ProjectionError):
        adapter.native_rows(sidecar)


@pytest.mark.parametrize("change", ["verdict", "rule", "prereg"])
def test_sidecar_requires_shared_native_verdict_rule_and_prereg(tmp_path, change):
    _, sidecar = _run(tmp_path)

    def mutate(rows):
        if change == "verdict":
            rows[1]["extra"]["verdict"] = "OTHER_NATIVE_VERDICT"
        elif change == "rule":
            rows[1]["extra"]["rule"]["X"] = 0.5
        elif change == "prereg":
            rows[1]["extra"]["preregistration_sha256"] = "f" * 64

    _rewrite_sidecar(sidecar, mutate)
    with pytest.raises(ProjectionError, match="run-level identity"):
        adapter.native_rows(sidecar)


def test_manifest_preregistration_is_preserved_and_must_match_rows(tmp_path):
    prereg = "a" * 64
    _, sidecar = _run(tmp_path, preregistration_sha256=prereg)
    assert all(native["row"]["extra"]["preregistration_sha256"] == prereg
               for native in adapter.native_rows(sidecar))

    _rewrite_sidecar(sidecar, lambda rows: rows[0]["extra"].update(
        preregistration_sha256="b" * 64))
    with pytest.raises(ProjectionError, match="differs from its manifest"):
        adapter.native_rows(sidecar)


def test_duplicate_json_member_and_nonfinite_value_are_refused(tmp_path):
    _, sidecar = _run(tmp_path)
    lines = sidecar.read_text().splitlines()
    first = lines[0]
    needle = '"schema": "ufh13-thesis-belief/v1"'
    assert needle in first
    lines[0] = first.replace(needle, needle + ', "schema": "ufh13-thesis-belief/v1"', 1)
    sidecar.write_text("\n".join(lines) + "\n")
    with pytest.raises(ProjectionError, match="duplicate JSON member"):
        adapter.native_rows(sidecar)

    _, sidecar = _run(tmp_path / "second")
    _rewrite_sidecar(sidecar, lambda rows: rows[0].update(value=float("nan")))
    with pytest.raises(ProjectionError, match="strict JSON"):
        adapter.native_rows(sidecar)


@pytest.mark.parametrize("change", ["duplicate-id", "mixed-run", "mixed-suite", "wrong-category",
                                     "wrong-reps-basis", "wrong-locator", "wrong-record-path"])
def test_mixed_or_non_native_sidecar_unit_is_refused(tmp_path, change):
    run, sidecar = _run(tmp_path)

    def mutate(rows):
        if change == "duplicate-id":
            rows[1]["measurement_id"] = rows[0]["measurement_id"]
        elif change == "mixed-run":
            rows[1]["extra"]["run_id"] = "another-run"
        elif change == "mixed-suite":
            rows[1]["extra"]["suite_sha256"] = "e" * 64
        elif change == "wrong-category":
            rows[0]["category"] = "CANDIDATE"
        elif change == "wrong-reps-basis":
            rows[0]["reps_basis"] = "attempted"
        elif change == "wrong-locator":
            rows[1]["attestation_locator"] = "another-run"
        elif change == "wrong-record-path":
            rows[0]["attestation_path"] = str(run / "other-records.jsonl")

    _rewrite_sidecar(sidecar, mutate)
    with pytest.raises(ProjectionError):
        adapter.native_rows(sidecar)


def test_duplicate_measurement_id_is_refused(tmp_path):
    _, sidecar = _run(tmp_path)
    first_line = sidecar.read_text().splitlines()[0]
    with sidecar.open("a", encoding="utf-8") as stream:
        stream.write(first_line + "\n")
    with pytest.raises(ProjectionError, match="repeats a measurement_id"):
        adapter.native_rows(sidecar)


def test_records_digest_mismatch_and_symlink_are_refused(tmp_path):
    run, sidecar = _run(tmp_path)
    records = run / "records.jsonl"
    records.write_bytes(records.read_bytes() + b"{}\n")
    with pytest.raises(ProjectionError, match="do not match"):
        adapter.native_rows(sidecar)

    records.unlink()
    target = tmp_path / "external-records.jsonl"
    target.write_text("synthetic-only\n")
    records.symlink_to(target)
    with pytest.raises(ProjectionError, match="regular single-link"):
        adapter.native_rows(sidecar)


def test_records_change_during_hash_read_is_refused(tmp_path, monkeypatch):
    run, sidecar = _run(tmp_path)
    records = run / "records.jsonl"
    original_read = adapter.os.read
    calls = 0

    def mutate_during_read(fd, size):
        nonlocal calls
        calls += 1
        chunk = original_read(fd, size)
        # sidecar and manifest each consume a data read and EOF read; mutate during the
        # third file's first read, which is the attested sibling records.jsonl.
        if calls == 5:
            with records.open("ab") as stream:
                stream.write(b"changed-during-read\n")
        return chunk

    monkeypatch.setattr(adapter.os, "read", mutate_during_read)
    with pytest.raises(ProjectionError, match="changed during its read"):
        adapter.native_rows(sidecar)
