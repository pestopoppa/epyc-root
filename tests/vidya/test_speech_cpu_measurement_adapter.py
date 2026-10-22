"""VB-SPEECH-CPU-1/1a: producer-shaped capture rows project; legacy, censored and tampered rows do not.

No server, no inference. The producer module is loaded by its pinned sha256 from the research repo
(override with SPEECH_CPU_TEST_RESEARCH_ROOT, e.g. a worktree, before the research push lands).
"""
import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/vidya"))
import claim_tuple as ct  # noqa: E402
from adapters import speech_cpu_measurement as reader  # noqa: E402
from ingest_sources import SOURCES, ingest  # noqa: E402
from ledger import Ledger  # noqa: E402
from datetime import UTC, datetime

AS_OF = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

RESEARCH = Path(os.environ.get("SPEECH_CPU_TEST_RESEARCH_ROOT", str(reader.RESEARCH_ROOT)))


@pytest.fixture
def producer(monkeypatch):
    path = RESEARCH / "artifacts/speech_cpu_realtime_20260924/speech_cpu_capture.py"
    if not path.is_file():
        pytest.skip(f"producer not present at {path}")
    monkeypatch.setattr(reader, "PRODUCER_PATH", path)
    return reader._producer()


def _rows(producer, tmp_path, native, **kw):
    b = tmp_path / "whisper-server"
    b.write_bytes(b"binary")
    t0, t1 = native["t_start_epoch"], native["t_end_epoch"]
    args = dict(harness="speech_cpu_bench", run_id="run1", row_index=kw.pop("row_index", 0),
                binaries={"stt": producer.binary_digest(str(b))}, cores="0-23", threads=24,
                shim_nprocs=None, cap_s=600.0, mode="solo", emitted_at="2026-10-22T12:00:00Z",
                cotenant={"port": 8070, "samples": [{"t": (t0 + t1) / 2, "resolved": True}],
                          "n_samples": 1, "generating": False, "generating_basis": {}})
    args.update(kw)
    return producer.make_rows(native, **args)


def _stt(**kw):
    d = {"kind": "stt", "rtf": 0.19, "status": 200, "t_start_epoch": 10.0, "t_end_epoch": 12.0}
    d.update(kw)
    return d


def _write(tmp_path, rows):
    p = tmp_path / "speech_cpu_capture.jsonl"
    p.write_text("".join(json.dumps(r) + "\n" for r in rows))
    return p


def test_pinned_sha_matches_producer(producer):
    assert reader._sha256(reader.PRODUCER_PATH) == reader.PRODUCER_SHA256


def test_stt_tts_and_llm_rows_project_and_grade(producer, tmp_path):
    tts = {"kind": "tts", "rtf": 0.6, "first_packet_s": 0.11, "status": 200,
           "t_start_epoch": 20.0, "t_end_epoch": 23.0}
    llm = {"kind": "llm", "tok_s": 41.0, "capped": False, "t_start_epoch": 30.0, "t_end_epoch": 39.0}
    rows = (_rows(producer, tmp_path, _stt())
            + _rows(producer, tmp_path, tts, row_index=1, cores="24-39", threads=16, shim_nprocs=32)
            + _rows(producer, tmp_path, llm, row_index=2, harness="live_llm_contention", cap_s=180.0))
    natives = reader.native_rows(_write(tmp_path, rows))
    assert [n["row"]["metric"] for n in natives] == [
        "stt_rtf", "tts_rtf", "tts_first_packet_s", "cotenant_llm_tok_s"]
    for n in natives:
        tup = reader.project(n)
        assert tup.source_kind == "speech-cpu-measurement"
        assert tup.attestation_verified is True and tup.applicability["knobs"]["cores"]
        assert len(tup.extra["cautions"]) == 3
        grade, _, _ = ct.grade(tup)  # the shared ladder decides; the adapter never grades
        assert grade
    assert natives[1]["row"]["placement"]["shim_nprocs"] == 32


def test_censored_rows_counted_not_projected(producer, tmp_path):
    ok = _rows(producer, tmp_path, _stt())
    capped = _rows(producer, tmp_path, _stt(rtf=None, timed_out_after_s=90.0), row_index=1)
    aborted = _rows(producer, tmp_path, _stt(), row_index=2, guard_aborted=True)
    natives = reader.native_rows(_write(tmp_path, ok + capped + aborted))
    assert len(natives) == 1 and natives[0]["n_censored_in_run"] == 2
    with pytest.raises(ct.ProjectionError, match="not a measurement"):
        reader.project({"row": capped[0]})


def test_legacy_retrospective_rows_yield_zero_tuples(producer, tmp_path):
    legacy = {"kind": "stt", "clip": "short_11s.wav", "rtf": 0.19, "status": 200, "tag": "main40"}
    with pytest.raises(ct.ProjectionError, match="refused"):
        reader.native_rows(_write(tmp_path, [legacy]))


def test_tampered_row_refused(producer, tmp_path):
    (row,) = _rows(producer, tmp_path, _stt())
    row["value"] = 0.01
    with pytest.raises(ct.ProjectionError, match="row_sha256"):
        reader.native_rows(_write(tmp_path, [row]))


def test_missing_layout_or_cotenant_refused(producer, tmp_path):
    (row,) = _rows(producer, tmp_path, _stt())
    for mutate in (lambda r: r["placement"].update(cores=""), lambda r: r.update(cotenant={})):
        bad = json.loads(json.dumps(row))
        mutate(bad)
        bad["row_sha256"] = producer.row_digest(bad)
        with pytest.raises(ct.ProjectionError):
            reader.project({"row": bad})


def test_producer_bytes_drift_refused(monkeypatch, tmp_path):
    fake = tmp_path / "speech_cpu_capture.py"
    fake.write_text("def validate_row(r):\n    return []\n")
    monkeypatch.setattr(reader, "PRODUCER_PATH", fake)
    with pytest.raises(ct.ProjectionError, match="reviewed sha256"):
        reader._producer()


def test_source_row_registered():
    src = SOURCES["speech-cpu-measurement"]
    assert src.module == "speech_cpu_measurement" and src.default is None
    assert "speech-cpu-measurement" in ct.registered()


def test_ingest_wires_the_source(producer, tmp_path):
    rows = _rows(producer, tmp_path, _stt()) + _rows(
        producer, tmp_path, _stt(rtf=None, timed_out_after_s=90.0), row_index=1)
    _write(tmp_path, rows)
    report = ingest(Ledger(tmp_path / "ledger.jsonl"), "speech-cpu-measurement", [tmp_path], as_of=AS_OF)
    assert report["rows_projected"] == 1  # the capped row is counted on the tuple, never projected
