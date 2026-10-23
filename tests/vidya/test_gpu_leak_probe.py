"""VB-GPU-LEAK-WRITE: GPU-LEAK-1/1d VRAM-slope probes -> OBSERVATION tuples graded by the one shared ladder."""
import glob
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402
from adapters import _native_sidecar as ns  # noqa: E402
from adapters import gpu_leak_probe as gl  # noqa: E402

WHEN = "2026-10-23T14:00:00Z"
REAL = [Path("/mnt/raid0/llm/tmp/gpu-leak-1-probe-20261023"), Path("/mnt/raid0/llm/tmp/gpu-leak-1d-probe")]


def _series(slope, n=12, base=1000.0):
    return [[i, round(base + slope * i, 1)] for i in range(n + 1)]


def _result(tmp_path, with_1d=False):
    gs, ns_ = _series(100.0), _series(0.0)
    r = {"item": "GPU-LEAK-1 probe", "date": "2026-10-23T13:18:13Z", "verdict": "graphs implicated",
         "slope_G_mib_per_req": round(gl.fit_slope(gs, 5, None)[0], 2),
         "slope_N_mib_per_req": round(gl.fit_slope(ns_, 5, None)[0], 2), "n_done_G": 12, "n_done_N": 12,
         "fit": "linear least squares over requests 5..n_done", "series_G": gs, "series_N": ns_,
         "errors_G": [], "errors_N": []}
    if with_1d:
        r.update({"item": "GPU-LEAK-1d probe", "slope_G_mib_per_req": r.pop("slope_G_mib_per_req")})
        r["segments_G"] = {"fixed_4096_tok_3_to_10": round(gl.fit_slope(gs, 3, 10)[0], 2),
                           "varied_10_to_n": round(gl.fit_slope(gs, 10, None)[0], 2)}
    path = tmp_path / "RESULT.json"
    path.write_text(json.dumps(r))
    return path


def write(tmp_path, **kw):
    return gl.write_belief_measurements(tmp_path, run_id="gpuleak-t", producer="t", results_path=_result(tmp_path, **kw),
                                        emitted_at=WHEN)


def test_round_trip_two_arms_observation_with_contrast(tmp_path):
    side = write(tmp_path)
    natives = gl.native_rows(side)
    assert [n["row"]["extra"]["arm"] for n in natives] == ["G", "N"]
    tg, tn = (gl.project(n) for n in natives)
    assert tg.value == 100.0 and tn.value == 0.0 and tg.reps == tn.reps == 8  # series points 5..12
    assert tn.observation == {"outcome_native": "graphs implicated", "anchor_value": 100.0, "effect_rel": -1.0}
    assert "anchor_value" not in tg.observation
    for t in (tg, tn):
        assert t.protocol_id == "" and t.metric_direction == "lower_better"
        assert t.attestation_present is True and t.attestation_verified is True
        assert ct.grade(t)[:2] == ("Judged", "Located")
    assert gl.frames_for_sidecar(side, as_of=WHEN)


def test_segment_rows_for_1d(tmp_path):
    side = write(tmp_path, with_1d=True)
    metrics = sorted(n["row"]["metric"] for n in gl.native_rows(side) if n["row"]["extra"]["arm"] == "G")
    assert metrics == sorted(gl.METRICS)


def test_a_slope_that_does_not_follow_from_its_series_is_refused(tmp_path):
    side = write(tmp_path)
    rows = [json.loads(x) for x in side.read_text().splitlines()]
    rows[0]["value"] = 5.0
    rows[0]["row_sha256"] = ns.row_digest(rows[0])
    side.write_text("".join(json.dumps(r) + "\n" for r in rows))
    assert gl.native_rows(side) == ()  # an invalid line voids the whole file
    assert any("does not follow from its series" in p for p in gl.row_problems(rows[0]))


def test_tampered_results_file_grades_down_instead_of_vanishing(tmp_path):
    side = write(tmp_path)
    (tmp_path / "RESULT.json").write_text((tmp_path / "RESULT.json").read_text() + " ")
    for n in gl.native_rows(side):
        t = gl.project(n)
        assert t.attestation_present is False and t.attestation_verified is None
        assert ct.grade(t)[:2] == ("Judged", "Located")


def test_writer_refuses_malformed_results(tmp_path):
    bad = tmp_path / "RESULT.json"
    bad.write_text(json.dumps({"item": "x", "verdict": "v", "slope_G_mib_per_req": 1.0, "series_G": [[0, 1.0]]}))
    with pytest.raises(gl.CaptureError, match="series_G"):
        gl.write_belief_measurements(tmp_path, run_id="r", producer="p", results_path=bad)
    bad.write_text(json.dumps({"item": "x", "verdict": "v"}))
    with pytest.raises(gl.CaptureError, match="slope_"):
        gl.write_belief_measurements(tmp_path, run_id="r", producer="p", results_path=bad)


def test_non_empty_protocol_is_refused(tmp_path):
    row = json.loads(write(tmp_path).read_text().splitlines()[0])
    row["protocol_id"] = "ratified:x"
    assert any("protocol_id must be empty" in p for p in gl.row_problems(row))


@pytest.mark.skipif(not all((d / "RESULT.json").is_file() for d in REAL), reason="real probe dirs not on this host")
def test_real_probe_results_rederive_and_project(tmp_path):
    expected = {"gpu-leak-1-probe-20261023": {("G", 290.26), ("N", 0.0)}, "gpu-leak-1d-probe": {("P", 1.7), ("PN", 1.7)}}
    for d in REAL:
        runs = glob.glob(str(d / "run-*"))
        out = tmp_path / d.name
        out.mkdir()
        side = gl.write_belief_measurements(out, run_id=d.name, producer="t", results_path=d / "RESULT.json",
                                            run_dir=runs[0] if runs else None, emitted_at=WHEN)
        tuples = [gl.project(n) for n in gl.native_rows(side)]
        got = {(t.extra["arm"], t.value) for t in tuples if t.metric == "gpu_leak_vram_slope_mib_per_req"}
        assert got == expected[d.name]
        assert all(ct.grade(t)[:2] == ("Judged", "Located") for t in tuples)
