"""VB-UFH12-PLACEMENT: producer-written placement-gate sidecars, whole-file refusal, ingest.

Rows are written by the orchestrator's own capture module (pinned by sha256), never hand-built.
Until the orchestrator lane lands on main, point ``EPYC_EMBPL_CAPTURE`` at the lane's
``scripts/server/embedder_placement_capture.py``; the sha256 pin still applies.
"""

import json
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts/vidya"))
import claim_tuple as ct  # noqa: E402
from adapters import embedder_placement_gate as reader  # noqa: E402
from ingest_sources import SOURCES, ingest  # noqa: E402
from ledger import Ledger  # noqa: E402

T0 = datetime(2026, 9, 27, 10, 0, tzinfo=UTC)
#: the ledger refuses future-stamped frames, so ingest at the wall clock
AS_OF = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
POOL = [8090, 8091, 8092, 8093, 8094, 8095]
FD = [8070, 8080, 8180]


@pytest.fixture()
def producer(monkeypatch):
    override = os.environ.get("EPYC_EMBPL_CAPTURE")
    if override:
        monkeypatch.setattr(reader, "PRODUCER_PATH", Path(override))
    try:
        return reader._producer()
    except ct.ProjectionError as exc:
        pytest.skip(f"placement-gate capture module not landed here: {exc}")


def _iso(dt):
    return dt.isoformat()


def _snap(process_ports, props_ports):
    def proc(port):
        argv = ["/mnt/raid0/llm/kernels/production/cpu/bin/llama-server", "--port", str(port)]
        return {"pid": 1000 + port, "argv": argv, "argv_sha256": None, "cpus_allowed_list": "0-3",
                "exe": argv[0], "exe_sha256": "a" * 64, "ld_library_path": None,
                "ggml_libs": ["/mnt/raid0/llm/kernels/production/cpu/bin/libggml-cpu.so"]}
    return {"processes": {str(p): proc(p) for p in process_ports},
            "frontdoor_props": {str(p): {"build_info": "b10303-ffc1bac82", "model_path": "/m.gguf"}
                                for p in props_ports},
            "topology_hash": "4893e37e5d603c80"}


def _window(producer, process_ports, props_ports):
    def snap(pp, fp):
        out = _snap(pp, fp)
        for facts in out["processes"].values():
            facts["argv_sha256"] = producer.content_hash(facts["argv"])
        return out
    window = producer.CaptureWindow(process_ports, props_ports, snapshot_fn=snap)
    window.begin()
    window.mark("g2", _iso(T0), _iso(T0 + timedelta(minutes=2)))
    window.mark("g1", _iso(T0 + timedelta(minutes=2)), _iso(T0 + timedelta(minutes=20)))
    window.finish()
    return window


def _gate_record(label="post-cap"):
    g1 = {}
    for i, port in enumerate(FD):
        q = [50.0 + i, 50.5 + i, 49.8 + i, 50.2 + i]
        s = [47.0, 47.5, 46.9]
        g1[str(port)] = {"q_samples": q, "s_samples": s,
                         "aa_noise_floor_rel_median": sorted(abs(b - a) / a for a, b in zip(q, q[1:]))[1],
                         "s_embedding_load": [{"texts_per_s": v, "counters_delta": {"granted": 9}}
                                              for v in (30.0, 31.0, 29.0)]}
    return {"schema": "epyc.embedder_placement_gate.v1", "label": label, "load_mode": "scheduler",
            "started_at": _iso(T0), "finished_at": _iso(T0 + timedelta(minutes=20)),
            "params": {"fd_ports": FD, "pool_ports": POOL, "per_port_in_flight": 4, "pairs": 3,
                       "n_predict": 256, "g2_window_s": 60.0, "load_warmup_s": 3.0},
            "g2_pool_scaling": {"one_port": {"texts": 551, "seconds": 60.0},
                                "whole_pool": {"texts": 2734, "seconds": 60.0}},
            "g1_frontdoor_decode": g1}


def write_capture(tmp_path, producer, record=None, name="post-cap-20260927.json"):
    record = record or _gate_record()
    out = tmp_path / name
    out.write_text(json.dumps(record, indent=2))
    if record.get("gate") == "G3":
        window = _window(producer, POOL + [9000, 9002], [])
    else:
        window = _window(producer, POOL + FD, FD)
    sidecar = producer.write_belief_measurements(
        out, record, window=window, producer="test", gate_path=reader.PRODUCER_PATH,
        emitted_at=_iso(T0 + timedelta(minutes=25)))
    rows = [json.loads(line) for line in sidecar.read_text().splitlines()]
    return sidecar, rows, out


def _rewrite(sidecar, rows):
    sidecar.write_text("".join(json.dumps(r) + "\n" for r in rows))


def test_rows_project_and_grade_through_the_shared_ladder(tmp_path, producer):
    sidecar, rows, record = write_capture(tmp_path, producer)
    natives = reader.native_rows(sidecar)
    assert len(natives) == len(rows) == 3 + 3 * len(FD)
    tuples = [reader.project(n) for n in natives]
    assert {t.extra["gate"] for t in tuples} == {"G1", "G2"}
    ratio = next(t for t in tuples if t.metric == "g1_s_over_q_median" and t.extra["port"] == 8070)
    assert ratio.attestation_verified is True and ratio.protocol_id == ""
    assert "A/A noise floor" in ratio.claim
    assert ratio.extra["topology_hash"] and ratio.extra["placement_digest"]
    assert ratio.extra["provenance"]["frontdoor_props"]["8070"]["build_info"]
    q_grade, _t, _reasons = ct.grade(ratio)
    assert q_grade == "Judged"  # no codified protocol: an observation, graded by the shared ladder
    record.write_text("changed")
    assert reader.project(natives[0]).attestation_verified is None


@pytest.mark.parametrize("mutation", ["value", "rehashed_value", "duplicate", "drop_g2",
                                      "drop_port_baseline", "mixed_run", "renamed"])
def test_any_bad_row_voids_the_whole_sidecar(tmp_path, producer, mutation):
    sidecar, rows, _ = write_capture(tmp_path, producer)
    if mutation == "value":
        rows[4]["value"] += 1
    elif mutation == "rehashed_value":
        rows[4]["value"] += 1
        rows[4]["row_sha256"] = producer.row_digest(rows[4])
    elif mutation == "duplicate":
        rows[5] = rows[4]
    elif mutation == "drop_g2":
        rows = [r for r in rows if r["metric"] != "g2_scaling_ratio"]
    elif mutation == "drop_port_baseline":
        rows = [r for r in rows if not (r["metric"] == "g1_q_decode_tps_median" and r["port"] == 8180)]
    elif mutation == "mixed_run":
        other, other_rows, _ = write_capture(tmp_path, producer, _gate_record(label="post"),
                                             name="post-20260927.json")
        rows[0] = other_rows[0]
    else:
        sidecar = sidecar.rename(tmp_path / "other.belief_measurements.jsonl")
    _rewrite(sidecar, rows)
    with pytest.raises(ct.ProjectionError):
        reader.native_rows(sidecar)


def test_g3_speech_is_its_own_claim_set(tmp_path, producer):
    record = {
        "schema": "epyc.embedder_placement_g3.v1", "gate": "G3", "label": "post-cap",
        "started_at": _iso(T0), "finished_at": _iso(T0 + timedelta(minutes=5)),
        "method": {"warmup_discarded": True, "reps": 3},
        "params": {"pool_ports": POOL, "per_port_in_flight": 4},
        "quiet": {"stt_rtf": [0.2, 0.19, 0.21], "stt_status": [200] * 3,
                  "tts_first_packet_s": [0.09, 0.08, 0.09], "tts_status": [200] * 3},
        "saturated": {"stt_rtf": [0.22, 0.24, 0.21], "stt_status": [200] * 3,
                      "tts_first_packet_s": [0.11, 0.12, 0.10], "tts_status": [200] * 3},
    }
    sidecar, rows, _ = write_capture(tmp_path, producer, record, name="g3-post-cap-20260927.json")
    tuples = [reader.project(n) for n in reader.native_rows(sidecar)]
    assert {t.extra["gate"] for t in tuples} == {"G3"} and len(tuples) == 4
    assert all(t.metric_direction == "lower_better" for t in tuples)


def test_ingest_wires_the_source(tmp_path, producer):
    sidecar, rows, _ = write_capture(tmp_path, producer)
    assert SOURCES["embedder-placement-gate"].task == "VB-UFH12-PLACEMENT"
    report = ingest(Ledger(tmp_path / "ledger.jsonl"), "embedder-placement-gate", [tmp_path],
                    as_of=AS_OF)
    assert report["rows_projected"] == len(rows)


def test_phase0_records_without_sidecars_yield_nothing(tmp_path, producer):
    """The 2026-09-26 Phase-0 JSON files carry no sidecar: zero claims, never backfilled."""
    (tmp_path / "post-20260926.json").write_text('{"schema": "epyc.embedder_placement_gate.v1"}')
    report = ingest(Ledger(tmp_path / "ledger.jsonl"), "embedder-placement-gate", [tmp_path],
                    as_of=AS_OF, dry_run=True)
    assert report["rows_projected"] == 0
