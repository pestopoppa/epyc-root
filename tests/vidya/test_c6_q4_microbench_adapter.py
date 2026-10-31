"""Strict C6 Q4 reader regressions over the actual R2 native bundle."""
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

import pytest

VIDYA = Path(__file__).resolve().parents[2] / "scripts/vidya"
sys.path.insert(0, str(VIDYA))
import claim_tuple as ct  # noqa: E402
import ingest_sources  # noqa: E402
from adapters import c6_q4_microbench as reader  # noqa: E402

PACKAGE = Path("/mnt/raid0/llm/tmp/c6-35186-q4-microbench-r2-20261031")
RUN = PACKAGE / "runs/20261031T024056.425184Z-2158835"

def _external_fixture_available():
    if os.environ.get("EPYC_C6_Q4_SKIP_EXTERNAL") == "1":
        return False
    required_capture = [
        PACKAGE / "PACKAGE-SHA256SUMS", PACKAGE / "calendar.sh",
        PACKAGE / "Q4-K-27B-EXACT.testfile", RUN / "PRE-RUN.json",
        RUN / "RESULT.json", RUN / "SHA256SUMS.txt",
        Path(__file__).resolve().parents[2] / "artifacts/compute/c6-q4-microbench-r2-20261031/outer-custody/CUSTODY-MANIFEST.json",
    ]
    if not all(path.is_file() for path in required_capture):
        return False
    try:
        pre = json.loads((RUN / "PRE-RUN.json").read_text())
        for name in ("candidate", "control"):
            root = Path(pre["images"][name]["root"])
            if not all((root / rel).is_file() for rel in (
                "BUILD-IDENTITY.json", "build-result.json", "SHA256SUMS", "bin/test-backend-ops")):
                return False
        return True
    except (OSError, KeyError, TypeError, ValueError):
        return False

HAS_EXTERNAL_FIXTURE = _external_fixture_available()


def _sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _write_seal(directory, name):
    files = sorted(p for p in directory.iterdir() if p.is_file() and p.name != name)
    (directory / name).write_text("".join(f"{_sha(p)}  {p.name}\n" for p in files))


def _copy_bundle(tmp_path):
    package = tmp_path / "pkg"
    package.mkdir()
    for line in (PACKAGE / "PACKAGE-SHA256SUMS").read_text().splitlines():
        _, rel = line.split(None, 1)
        src = PACKAGE / rel.strip()
        dest = package / rel.strip()
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
    shutil.copy2(PACKAGE / "PACKAGE-SHA256SUMS", package / "PACKAGE-SHA256SUMS")
    run = package / "runs" / RUN.name
    run.parent.mkdir(parents=True)
    shutil.copytree(RUN, run)
    return package, run


def _rewrite_top(run):
    _write_seal(run, "SHA256SUMS.txt")


@pytest.mark.skipif(not HAS_EXTERNAL_FIXTURE, reason="external R2 capture and signed stores are not installed")
def test_actual_full_r2_projects_22_scoped_observations():
    rows = reader.native_rows(RUN)
    assert len(rows) == 22
    tuples = [reader.project(row) for row in rows]
    assert len({t.measurement_id for t in tuples}) == 22
    assert sum(t.category == "CANDIDATE" for t in tuples) == 11
    assert sum(t.category == "BASELINE" for t in tuples) == 11
    assert all(t.metric_direction == "lower_better" and t.unit == "us" and t.protocol_id == "" for t in tuples)
    assert all(t.attestation_verified is True and t.reps == 1 and t.reps_basis.startswith("one process-level observation") for t in tuples)
    q4 = next(t for t in tuples if t.category == "CANDIDATE" and t.extra["cohort"] == "27b")
    assert q4.extra["internal_reps"] > 1 and q4.reps == 1
    assert all(t.extra["native_input_byte_identity"] == "UNKNOWN" and t.extra["co_tenancy"] == "UNKNOWN" for t in tuples)
    assert all(ct.grade(t)[:2] == ("Judged", "Located") for t in tuples)
    assert reader.frames_for_path(RUN, as_of="2026-10-31T05:00:00Z")
    source = ingest_sources.SOURCES["c6-q4-microbench"]
    assert source.task == "VB-C6-Q4-MICROBENCH-WIRE" and source.units(RUN) == [RUN]


@pytest.mark.skipif(not HAS_EXTERNAL_FIXTURE, reason="external R2 capture and signed stores are not installed")
def test_sealed_raw_tamper_is_refused(tmp_path):
    _, run = _copy_bundle(tmp_path)
    raw = run / "27b-candidate/perf.sql"
    raw.write_text(raw.read_text() + "\n-- tampered\n")
    with pytest.raises(ct.ProjectionError, match="sealed file changed or missing"):
        reader.native_rows(run)


@pytest.mark.skipif(not HAS_EXTERNAL_FIXTURE, reason="external R2 capture and signed stores are not installed")
def test_missing_native_component_file_is_refused(tmp_path):
    _, run = _copy_bundle(tmp_path)
    (run / "ds41-candidate/down.jsonl").unlink()
    with pytest.raises(ct.ProjectionError, match="sealed file changed or missing"):
        reader.native_rows(run)


@pytest.mark.skipif(not HAS_EXTERNAL_FIXTURE, reason="external R2 capture and signed stores are not installed")
def test_smoke_or_unqualified_body_does_not_project(tmp_path):
    _, run = _copy_bundle(tmp_path)
    pre_path, result_path = run / "PRE-RUN.json", run / "RESULT.json"
    pre = json.loads(pre_path.read_text())
    pre["mode"] = "--smoke"
    pre_path.write_text(json.dumps(pre, indent=2, sort_keys=True) + "\n")
    result = json.loads(result_path.read_text())
    result["pre_run_sha256"] = _sha(pre_path)
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    _rewrite_top(run)
    with pytest.raises(ct.ProjectionError, match="not a full native run"):
        reader.native_rows(run)


@pytest.mark.skipif(not HAS_EXTERNAL_FIXTURE, reason="external R2 capture and signed stores are not installed")
def test_mismatched_case_identity_is_refused_after_seals_are_recomputed(tmp_path):
    _, run = _copy_bundle(tmp_path)
    sub = run / "27b-candidate"
    result_path = sub / "result-summary.json"
    result = json.loads(result_path.read_text())
    result["case_names"][0] = "unrelated_case"
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    _write_seal(sub, "SHA256SUMS.txt")
    top_path = run / "RESULT.json"
    top = json.loads(top_path.read_text())
    item = next(x for x in top["results"] if x["cohort"] == "27b" and x["image"] == "candidate")
    item["result_sha256"] = _sha(result_path)
    item["component_seal_sha256"] = _sha(sub / "SHA256SUMS.txt")
    top_path.write_text(json.dumps(top, indent=2, sort_keys=True) + "\n")
    _rewrite_top(run)
    with pytest.raises(ct.ProjectionError, match="case result identities/count mismatch"):
        reader.native_rows(run)


@pytest.mark.skipif(not HAS_EXTERNAL_FIXTURE, reason="external R2 capture and signed stores are not installed")
def test_incomplete_terminal_status_is_refused(tmp_path):
    _, run = _copy_bundle(tmp_path)
    result_path = run / "RESULT.json"
    result = json.loads(result_path.read_text())
    result["status"] = "INCOMPLETE_MICROBENCH_ONLY"
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    _rewrite_top(run)
    with pytest.raises(ct.ProjectionError, match="no complete microbench-only terminal result"):
        reader.native_rows(run)


@pytest.mark.skipif(not HAS_EXTERNAL_FIXTURE, reason="external R2 capture and signed stores are not installed")
def test_archived_outer_evidence_survives_live_scheduler_paths_moving(tmp_path, monkeypatch):
    source = Path(__file__).resolve().parents[2] / "artifacts/compute/c6-q4-microbench-r2-20261031/outer-custody"
    archive = tmp_path / "outer-custody"
    shutil.copytree(source, archive)
    monkeypatch.setattr(reader, "OUTER_CAPTURE_DIR", archive)
    live_paths = {original for original, _ in reader.OUTER_CAPTURE_EXPECTED.values()}
    original_read, original_sha = reader._read, reader._sha

    def no_live_read(path, *args, **kwargs):
        assert str(path) not in live_paths, "reader reached a mutable scheduler path"
        return original_read(path, *args, **kwargs)

    def no_live_hash(path):
        assert str(path) not in live_paths, "reader rehashed a mutable scheduler path"
        return original_sha(path)

    monkeypatch.setattr(reader, "_read", no_live_read)
    monkeypatch.setattr(reader, "_sha", no_live_hash)
    assert len(reader.native_rows(RUN)) == 22


@pytest.mark.skipif(not HAS_EXTERNAL_FIXTURE, reason="external R2 capture and signed stores are not installed")
def test_tampered_archived_outer_evidence_is_refused(tmp_path, monkeypatch):
    source = Path(__file__).resolve().parents[2] / "artifacts/compute/c6-q4-microbench-r2-20261031/outer-custody"
    archive = tmp_path / "outer-custody"
    shutil.copytree(source, archive)
    log = archive / "keeper-launcher.out"
    log.write_text(log.read_text() + "\nchanged after archival\n")
    monkeypatch.setattr(reader, "OUTER_CAPTURE_DIR", archive)
    with pytest.raises(ct.ProjectionError, match="sealed file changed or missing"):
        reader.native_rows(RUN)


def test_raw_sql_cannot_attach_or_detach_external_database(tmp_path):
    external = tmp_path / "must-not-be-created.sqlite"
    db = __import__("sqlite3").connect(":memory:")
    import sqlite3
    def deny_external_database(action, arg1, arg2, database, trigger):
        if action in (sqlite3.SQLITE_ATTACH, sqlite3.SQLITE_DETACH):
            return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK
    db.set_authorizer(deny_external_database)
    with pytest.raises(sqlite3.DatabaseError, match="not authorized"):
        db.executescript(f"ATTACH DATABASE '{external}' AS outside; DETACH DATABASE outside;")
    assert not external.exists()
    db.close()


# Small self-contained controls exercise the same production helpers without copying
# large native stores or depending on the capture host's /mnt/raid0 paths.
def test_small_raw_seal_valid_tampered_missing_and_unsafe_paths(tmp_path):
    (tmp_path / "payload.bin").write_bytes(b"small fixture")
    seal = tmp_path / "SHA256SUMS.txt"
    seal.write_text(f"{_sha(tmp_path / 'payload.bin')}  payload.bin\n")
    assert reader._seal(tmp_path, seal) == {"payload.bin": _sha(tmp_path / "payload.bin")}
    (tmp_path / "payload.bin").write_bytes(b"changed")
    with pytest.raises(ct.ProjectionError, match="sealed file changed or missing"):
        reader._seal(tmp_path, seal)
    seal.write_text("0" * 64 + "  absent.bin\n")
    with pytest.raises(ct.ProjectionError, match="sealed file changed or missing"):
        reader._seal(tmp_path, seal)
    seal.write_text("0" * 64 + "  ../outside.bin\n")
    with pytest.raises(ct.ProjectionError, match="unsafe/duplicate sealed path"):
        reader._seal(tmp_path, seal)


def _small_27b_component(tmp_path, *, sql_override=None, reported_us=123.5):
    package = tmp_path / "package"
    run = tmp_path / "runs" / reader.CANONICAL_RUN_ID
    sub = run / "27b-candidate"
    sub.mkdir(parents=True)
    package.mkdir(exist_ok=True)
    names = [
        "served_q4km_27b_blk_3_ffn_gate_weight_n1", "served_q4km_27b_blk_3_ffn_gate_weight_n8",
        "served_q4km_27b_blk_3_ffn_gate_weight_n16", "served_q4km_27b_blk_3_ffn_up_weight_n1",
        "served_q4km_27b_blk_3_ffn_up_weight_n8", "served_q4km_27b_blk_3_ffn_up_weight_n16",
        "served_q4km_27b_blk_4_ffn_down_weight_n1", "served_q4km_27b_blk_4_ffn_down_weight_n8",
        "served_q4km_27b_blk_4_ffn_down_weight_n16",
    ]
    (package / "Q4-K-27B-EXACT.testfile").write_text("".join(f"MUL_MAT 1 {name}\n" for name in names))
    result_rows = []
    insert_rows = []
    for i, name in enumerate(names):
        value = reported_us + i
        result_rows.append({"backend_name": "CPU", "time_us": value, "n_runs": 1000})
        insert_rows.append(f"('MUL_MAT','name={name}','perf',1,0,'',{value},1000,'CPU')")
    sql = sql_override or ("CREATE TABLE test_backend_ops (op_name TEXT, op_params TEXT, test_mode TEXT, supported INT, hard_failure INT, error_message TEXT, time_us REAL, n_runs INT, backend_name TEXT);\n" +
          "INSERT INTO test_backend_ops VALUES " + ",".join(insert_rows) + ";\n")
    (sub / "perf.sql").write_text(sql)
    (sub / "input.testfile").write_bytes((package / "Q4-K-27B-EXACT.testfile").read_bytes())
    (sub / "result-summary.json").write_text(json.dumps({"schema": "c6.35186.q4_cpu_perf_rows.v1", "case_count": 9,
        "case_names": names, "results": dict(zip(names, result_rows))}, sort_keys=True) + "\n")
    for filename, body in {"end.utc":"end\n", "image.txt":"candidate\n", "thread-config.txt":"threads=24\n",
                           "scope.txt":"normal\n", "exit.rc":"0\n", "perf.stderr":"", "start.utc":"start\n"}.items():
        (sub / filename).write_text(body)
    _write_seal(sub, "SHA256SUMS.txt")
    outer = run / "27b-candidate.outer.log"
    outer.write_text("fixture\n")
    top = {"result_sha256": _sha(sub / "result-summary.json"),
           "component_seal_sha256": _sha(sub / "SHA256SUMS.txt"),
           "outer_log_sha256": _sha(outer)}
    return run, package, names, top, reported_us


def test_small_27b_sql_rows_rederive_case_and_value(tmp_path):
    run, package, names, top, base_us = _small_27b_component(tmp_path)
    got = reader._verified_component(run, package, "27b", "candidate", top, {})
    assert list(got) == names
    assert got[names[0]]["value"] == base_us
    assert got[names[0]]["internal_reps"] == 1000


def test_small_27b_sql_case_identity_mismatch_is_refused(tmp_path):
    run, package, names, top, _ = _small_27b_component(tmp_path)
    result_path = run / "27b-candidate" / "result-summary.json"
    result = json.loads(result_path.read_text())
    result["case_names"][0] = "not_a_pinned_case"
    result_path.write_text(json.dumps(result, sort_keys=True) + "\n")
    _write_seal(run / "27b-candidate", "SHA256SUMS.txt")
    top["result_sha256"] = _sha(result_path)
    top["component_seal_sha256"] = _sha(run / "27b-candidate" / "SHA256SUMS.txt")
    with pytest.raises(ct.ProjectionError, match="case result identities/count mismatch"):
        reader._verified_component(run, package, "27b", "candidate", top, {})


def test_small_27b_sql_value_mismatch_is_refused(tmp_path):
    run, package, names, top, _ = _small_27b_component(tmp_path, reported_us=900.0)
    result_path = run / "27b-candidate" / "result-summary.json"
    result = json.loads(result_path.read_text())
    result["results"][names[0]]["time_us"] = 1.0
    result_path.write_text(json.dumps(result, sort_keys=True) + "\n")
    _write_seal(run / "27b-candidate", "SHA256SUMS.txt")
    top["result_sha256"] = _sha(result_path)
    top["component_seal_sha256"] = _sha(run / "27b-candidate" / "SHA256SUMS.txt")
    with pytest.raises(ct.ProjectionError, match="displayed values do not rederive"):
        reader._verified_component(run, package, "27b", "candidate", top, {})


def test_small_27b_sql_cannot_attach_external_database(tmp_path):
    external = tmp_path / "outside.sqlite"
    sql = f"ATTACH DATABASE '{external}' AS outside;"
    run, package, _, top, _ = _small_27b_component(tmp_path, sql_override=sql)
    with pytest.raises(ct.ProjectionError, match="raw perf SQL invalid"):
        reader._verified_component(run, package, "27b", "candidate", top, {})
    assert not external.exists()


def test_projection_keeps_thousand_internal_runs_at_one_process_observation(tmp_path):
    att = tmp_path / "runs" / reader.CANONICAL_RUN_ID / "RESULT.json"
    att.parent.mkdir(parents=True)
    att.write_text("{}\n")
    digest = _sha(att)
    row = {"schema": reader.SOURCE_KIND, "run_id": reader.CANONICAL_RUN_ID, "cohort": "27b",
           "image": "candidate", "case": "served_q4km_27b_blk_3_ffn_gate_weight_n1",
           "metric": "q4k_27b_matmul_latency_us", "value": 123.5, "unit": "us",
           "metric_direction": "lower_better", "internal_reps": 1000, "date": "2026-10-31",
           "source_sha": reader._IMAGE_SOURCE["candidate"][0], "source_tree": reader._IMAGE_SOURCE["candidate"][1],
           "purpose": "component timing only; no keep/serving grade", "native_input_byte_identity": "UNKNOWN",
           "co_tenancy": "UNKNOWN", "attestation_path": str(att), "attestation_sha256": digest,
           "attestation_locator": "unit-test", "attestation_verified": True,
           "native_detail": {"time_us": 123.5, "n_runs": 1000}}
    claim = reader.project(row)
    assert claim.reps == 1
    assert "internal repetitions=1000" in claim.reps_basis
    assert claim.extra["internal_reps"] == 1000
