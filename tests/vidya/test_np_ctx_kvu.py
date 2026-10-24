"""VB-KVU-CPU: np x ctx x KV-mode capture rows project through the ONE `np-ctx-kvu-measurement` adapter.

Fixtures are verbatim trimmed copies of real records: the 2026-10-21 W2 Tier-0 cells s1b (OK) and s1c (ERRORS: the 4th
stream HTTP 400 in every decode wave) and three KVU-12.1 request rows (one HTTP 400).
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "vidya"))
import claim_tuple as ct  # noqa: E402
from adapters import np_ctx_kvu as N  # noqa: E402

FX = Path(__file__).parent / "fixtures" / "np_ctx_kvu"
S1B, S1C, REQ = FX / "s1b_unified_np4_L64k_depth", FX / "s1c_split_np4_L64k_depth_ABA2", FX / "kvu121" / "requests.jsonl"


def write(tmp_path: Path) -> Path:
    """For test_ingest_sources: a copy of the real trimmed W2 cell (s1c, ERRORS) as an ingestable unit."""
    dst = Path(tmp_path) / "w2"
    shutil.copytree(S1C, dst / S1C.name)
    return dst


def _tuples(unit):
    return [N.project(n) for n in N.native_rows(unit)]


def _by(ts):
    return {t.metric: t for t in ts}


def test_ok_cell_projects_medians_rederived_and_grades_located():
    ts = _by(_tuples(S1B))
    assert set(ts) == {"prefill_tps_median", "ttft_s_median", "decode_tps_sum_median", "decode_tps_per_stream_median",
                       "e2e_tps_median", "request_ok_fraction"}
    assert ts["decode_tps_sum_median"].value == 18.22 and ts["prefill_tps_median"].value == 112.2
    assert ts["request_ok_fraction"].value == 1.0 and ts["request_ok_fraction"].reps == 16
    for t in ts.values():
        assert ct.grade(t)[:2] == ("Judged", "Located")
        assert t.applicability["knobs"]["kv_unified"] is True and t.applicability["np"] == 4
        assert t.applicability["context_tokens"] == 262144


def test_error_cell_keeps_failed_requests_in_the_denominator():
    ts = _by(_tuples(S1C))
    f = ts["request_ok_fraction"]
    assert f.value == pytest.approx(13 / 16) and f.reps == 16
    assert "ERRORS" in f.observation["outcome_native"]
    assert ts["decode_tps_sum_median"].value == 18.5          # still projected, never dropped
    assert all(ct.grade(t)[:2] == ("Judged", "Located") for t in ts.values())
    assert ts["decode_tps_sum_median"].applicability["knobs"]["kv_unified"] is False


def test_request_rows_http_400_stays_a_row_with_no_timing_value():
    ts = _tuples(REQ)
    ok = [t for t in ts if t.metric == "request_ok"]
    assert sorted(t.value for t in ok) == [0, 1, 1]
    assert sum(t.metric == "ttft_s" for t in ts) == 2 and sum(t.metric == "prompt_n_tokens" for t in ts) == 2
    assert len({t.measurement_id for t in ts}) == len(ts)
    assert all(ct.grade(t)[:2] == ("Judged", "Located") for t in ts)
    assert all(t.extra.get("binary_not_kernel_store") for t in ts)      # the 12.1 arms ran a worktree build


def test_medians_that_do_not_rederive_are_refused(tmp_path):
    d = tmp_path / "s1b"
    shutil.copytree(S1B, d)
    rows = [json.loads(line) for line in (d / "summary.jsonl").read_text().splitlines()]
    rows[0]["decode_tps_sum_med"] = 99.0
    rows[0]["row_sha256"] = N.row_hash(rows[0])           # a valid hash over a wrong median: only re-derivation catches it
    (d / "summary.jsonl").write_text(json.dumps(rows[0]) + "\n")
    with pytest.raises(ct.ProjectionError, match="does not re-derive"):
        N.native_rows(d)


def test_tampered_row_and_prehook_row_are_refused(tmp_path):
    d = tmp_path / "s1b"
    shutil.copytree(S1B, d)
    rows = [json.loads(line) for line in (d / "summary.jsonl").read_text().splitlines()]
    rows[0]["np"] = 8
    (d / "summary.jsonl").write_text(json.dumps(rows[0]) + "\n")
    with pytest.raises(ct.ProjectionError, match="row_sha256"):
        N.native_rows(d)
    del rows[0]["schema"]
    (d / "summary.jsonl").write_text(json.dumps(rows[0]) + "\n")
    with pytest.raises(ct.ProjectionError, match="pre-hook"):
        N.native_rows(d)


def test_missing_wave_rows_refuse(tmp_path):
    d = tmp_path / "s1b"
    shutil.copytree(S1B, d)
    next(d.rglob("waves_capture.jsonl")).unlink()
    with pytest.raises(ct.ProjectionError, match="waves_capture"):
        N.native_rows(d)


def test_legacy_hash_only_with_empty_validation_problems(tmp_path):
    r = json.loads(REQ.read_text().splitlines()[0])
    assert r["row_sha256"] != N.row_hash(r) and N._legacy_hash_ok(r)    # recorded 12.1 convention
    r["validation_problems"] = ["x"]
    assert not N._legacy_hash_ok(r)
    p = tmp_path / "requests.jsonl"
    p.write_text(json.dumps(r) + "\n")
    with pytest.raises(ct.ProjectionError):
        N.native_rows(p)


def test_cli_dry_run_counts(tmp_path):
    cmd = [sys.executable, str(ROOT / "scripts/vidya/cli.py"), "--ledger", str(tmp_path / "l.jsonl"), "--json", "ingest",
           "np-ctx-kvu-measurement", "--path", str(FX), "--as-of", "2026-10-24T12:00:00Z", "--dry-run"]
    rep = json.loads(subprocess.run(cmd, capture_output=True, text=True, check=True).stdout)
    assert rep["refused"] == [] and rep["units_matched"] == 3 and rep["rows_projected"] == 12 + 7


def test_real_w2_and_kvu121_when_present():
    w2 = Path("/mnt/raid0/llm/worktrees/f8-kvu121-hash/artifacts/np_context_kvu_cpu_study_20261020/w2_20261021")
    req = Path("/mnt/raid0/llm/tmp/kvu121-arms/out/requests.jsonl")
    if w2.is_dir():
        assert sum(len(N.native_rows(u)) for u in sorted(w2.iterdir()) if (u / "summary.jsonl").is_file()) == 36
    if req.is_file():
        ts = _tuples(req)
        assert len(ts) == 200 and sum(t.metric == "request_ok" and t.value == 0 for t in ts) == 2
