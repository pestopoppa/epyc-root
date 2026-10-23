"""U4-NOISE-1 sessions -> strict reader -> shared grade (VB-GPU-CPU-NOISE-WIRE). No inference.

The real sessions under /mnt/raid0/llm/tmp/gpu-cpu-noise-20261021/runs are read only; tamper tests run
on a tmp copy. Hermetic tests cover the decline/refuse paths that need no analysis.
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
from adapters import gpu_cpu_noise as reader  # noqa: E402

RUNS = Path("/mnt/raid0/llm/tmp/gpu-cpu-noise-20261021/runs")
W1, W2, ABORTED = RUNS / "20261022T170902Z", RUNS / "20261023T111836Z", RUNS / "20261022T164830Z"
needs_real = pytest.mark.skipif(not (W1 / "ANALYSIS.json").is_file() or not (W2 / "ANALYSIS.json").is_file(),
                                reason="real U4-NOISE-1 sessions not on this host")


def _rehash(row: dict) -> dict:
    body = json.dumps({k: v for k, v in row.items() if k != "content_sha256"}, sort_keys=True).encode()
    return dict(row, content_sha256=hashlib.sha256(body).hexdigest())


def _copy(src: Path, tmp_path: Path) -> Path:
    dst = tmp_path / src.name
    dst.mkdir()
    for name in ("RUN_RECORD.json", "schedule.json", "reps.jsonl", "END.json", "ANALYSIS.json"):
        shutil.copy2(src / name, dst / name)
    return dst


def _rewrite_json(path: Path, **changes) -> None:
    data = json.loads(path.read_text())
    data.update(changes)
    path.write_text(json.dumps(data, indent=1))


# ------------------------------------------------------------------ real sessions

@needs_real
def test_real_sessions_project_every_estimable_quantity_with_unique_ids():
    w1, w2 = reader.native_rows(W1), reader.native_rows(W2)
    # W1: A/A x 2 metrics + 5 conds x 2 metrics x 4 quantities; W2: A/A x 2 + G2 x (4 tg + 3 pp)
    assert (len(w1), len(w2)) == (42, 9)
    tuples = [reader.project(n) for n in w1 + w2]
    assert len({t.measurement_id for t in tuples}) == len(tuples)
    for t in tuples:
        assert ct.grade(t)[:2] == ("Judged", "Located")      # empty protocol_id: an OBSERVATION
        assert t.protocol_id == "" and t.attestation_verified is True
        assert t.applicability["backend"] == "cpu" and t.applicability["scope_basis"] == "native"
    g2 = {t.measurement_id: t for t in tuples}
    tg = g2["u4-noise-1:w1:20261022T170902Z:G2:tg:bias_pct"]
    assert round(tg.value, 2) == -0.73 and tg.reps == 10 and "not a serving speed number" in tg.claim
    assert "540bc18dd6b20a61" in tg.claim and tg.applicability["build_sha"] == "ffc1bac82"
    w2tg = g2["u4-noise-1:w2-q38fn:20261023T111836Z:G2:tg:vr_process"]
    assert "CO-RUN=CO-RUN-OK(labelled correction)" in w2tg.claim and "dbfd2a864b46bac9" in w2tg.claim
    assert w2tg.applicability["quant"] == "UD-IQ4_XS"


@needs_real
def test_absence_is_not_back_filled():
    ids = {reader.project(n).measurement_id for n in reader.native_rows(W2)}
    # W2 prefill has ONE sample per rep: no arm-unit variance exists, so no tuple claims one.
    assert "u4-noise-1:w2-q38fn:20261023T111836Z:G2:pp:vr_arm" not in ids
    assert reader.native_rows(ABORTED) == ()                 # END rc=5 gpu-warmup-failed: zero rows
    for dry in RUNS.glob("dry-*"):
        assert reader.native_rows(dry) == ()


@needs_real
def test_a_rep_value_that_was_re_hashed_still_does_not_re_derive(tmp_path):
    d = _copy(W2, tmp_path)
    rows = [json.loads(x) for x in (d / "reps.jsonl").read_text().splitlines()]
    i = next(i for i, r in enumerate(rows) if r["phase"] == "measure" and r["cond"] == "G2" and r["valid"])
    rows[i]["tg"]["samples_ts"] = [x * 0.9 for x in rows[i]["tg"]["samples_ts"]]
    rows[i] = _rehash(rows[i])
    (d / "reps.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    with pytest.raises(ct.ProjectionError, match="does not re-derive"):
        reader.native_rows(d)


@needs_real
def test_a_tampered_row_is_counted_hash_bad_and_refused(tmp_path):
    d = _copy(W2, tmp_path)
    lines = (d / "reps.jsonl").read_text().splitlines()
    row = json.loads(lines[5])
    row["wall_s"] = 1.0                                       # no re-hash
    lines[5] = json.dumps(row)
    (d / "reps.jsonl").write_text("\n".join(lines) + "\n")
    with pytest.raises(ct.ProjectionError, match="n_hash_bad"):
        reader.native_rows(d)


@needs_real
def test_prereg_bytes_must_match_the_sha_recorded_before_the_first_rep(tmp_path):
    d = _copy(W2, tmp_path)
    fake = tmp_path / "PREREG.md"
    fake.write_text("edited after the session")
    _rewrite_json(d / "RUN_RECORD.json", prereg=str(fake))
    with pytest.raises(ct.ProjectionError, match="pre-registration bytes differ"):
        reader.native_rows(d)


@needs_real
def test_analyzer_identity_binds_the_input_bytes(tmp_path):
    d = _copy(W2, tmp_path)
    reps = hashlib.sha256((d / "reps.jsonl").read_bytes()).hexdigest()
    rr = hashlib.sha256((d / "RUN_RECORD.json").read_bytes()).hexdigest()
    _rewrite_json(d / "ANALYSIS.json", analyzer={"sha256": "a" * 64, "reps_jsonl_sha256": reps,
                                                 "run_record_sha256": rr})
    natives = reader.native_rows(d)
    assert natives and natives[0]["analyzer_identity"]["reps_jsonl_sha256"] == reps
    _rewrite_json(d / "ANALYSIS.json", analyzer={"reps_jsonl_sha256": "b" * 64, "run_record_sha256": rr})
    with pytest.raises(ct.ProjectionError, match="different reps.jsonl"):
        reader.native_rows(d)


@needs_real
def test_sensitivity_analysis_is_not_the_primary(tmp_path):
    d = _copy(W2, tmp_path)
    _rewrite_json(d / "ANALYSIS.json", include_invalid=True)
    with pytest.raises(ct.ProjectionError, match="primary analysis"):
        reader.native_rows(d)


@needs_real
def test_cli_source_dispatch_counts_projected_and_declined(tmp_path):
    from ledger import Ledger

    report = ingest_sources.ingest(Ledger(tmp_path / "l.jsonl"), "gpu-cpu-noise", [RUNS],
                                   as_of="2026-10-23T16:00:00Z", dry_run=True)
    assert report["units_projected"] == 2 and report["rows_projected"] == 51
    assert report["frames_emitted"] == 153 and not report["refused"]
    assert str(ABORTED) in report["declined"]


# ------------------------------------------------------------------ hermetic

def _session(tmp_path: Path, end: dict | None, mode: str = "run") -> Path:
    d = tmp_path / "20261101T000000Z"
    d.mkdir(parents=True)
    prereg = tmp_path / "PREREG.md"
    prereg.write_text("pre-registered")
    (d / "RUN_RECORD.json").write_text(json.dumps({
        "schema": reader.RUN_SCHEMA, "session": d.name, "mode": mode, "blocks_min": 2,
        "prereg": str(prereg), "prereg_sha256": "0" * 64, "schedule_sha256": "0" * 64}))
    if end is not None:
        (d / "END.json").write_text(json.dumps({"session": d.name, **end}))
    (d / "ANALYSIS.json").write_text("{}")
    return d


def test_aborted_dry_and_unended_sessions_project_nothing(tmp_path):
    assert reader.native_rows(_session(tmp_path / "a", {"rc": 5, "reason": "gpu-warmup-failed",
                                                        "blocks_done": 0})) == ()
    assert reader.native_rows(_session(tmp_path / "b", None)) == ()
    assert reader.native_rows(_session(tmp_path / "c", {"rc": 0, "reason": "complete", "blocks_done": 9},
                                       mode="dry-run")) == ()


def test_complete_session_with_unmatched_prereg_is_refused(tmp_path):
    d = _session(tmp_path, {"rc": 0, "reason": "complete", "blocks_done": 5})
    with pytest.raises(ct.ProjectionError, match="pre-registration bytes differ"):
        reader.native_rows(d)


def test_end_claiming_complete_below_blocks_min_is_refused(tmp_path):
    d = _session(tmp_path, {"rc": 0, "reason": "complete", "blocks_done": 1})
    with pytest.raises(ct.ProjectionError, match="fewer than blocks_min"):
        reader.native_rows(d)


def test_adapter_registers_a_projection_and_no_ladder():
    assert reader.SOURCE_KIND in ct.registered()
    assert ct.source_classes()[reader.SOURCE_KIND] == ct.MEASUREMENT_CLASS
    assert reader.SOURCE_KIND not in ct.ladders()
    assert all("gpu_cpu_noise" not in module for module, _ in ct.ladders().values())
