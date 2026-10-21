"""VB-IBENCH-WRITE and VB-KVCHUNK-WRITE: round trip graded by the one shared ladder, plus refusals."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "vidya"))

import claim_tuple as ct  # noqa: E402
from adapters import chunk_kv, injection_fixture  # noqa: E402

WHEN = "2026-10-21T10:00:00Z"
FX = "f" * 64
PIN = {"role": "worker_general", "model": "gemma4-26B", "kernel_ref": "production-consolidated-v10"}
WIN = {"window_id": "w-test", "region_lock_claim": "claim-1",
       "start_utc": "2026-10-21T10:00:00Z", "end_utc": "2026-10-21T10:30:00Z"}


def inj_write(tmp_path, **kw):
    res = tmp_path / "ct18_results.json"
    res.write_text("{}")
    atk = lambda hits: [{"fixture_id": f"a{i}", "attack_success": i < hits} for i in range(5)]
    arms = {"no-sentence": {"thinking_setting": "off", "served_pin": PIN, "is_control": True,
                            "attacks": atk(2)},
            "boundary+datamark": {"thinking_setting": "on", "served_pin": PIN, "is_control": False,
                                  "attacks": atk(1)}}
    arms.update(kw)
    return injection_fixture.write_belief_measurements(
        tmp_path, run_id="ct18", producer="ct18-runner", results_path=res,
        fixture_set_id="IB2+SP1", fixture_sha256=FX, arms=arms, emitted_at=WHEN)


def kv_write(tmp_path, extra=None):
    res = tmp_path / "kpf_results.json"
    res.write_text("{}")
    ms = [{"kind": "prefill_rate", "source_program": "KPF-60", "subject": "role=frontdoor",
           "served_pin": PIN, "window": WIN, "samples": [100.0, 110.0, 105.0]},
          {"kind": "inject_latency", "source_program": "KPF-60", "subject": "chunk=doc",
           "served_pin": PIN, "window": WIN, "samples": [12.0, 14.0]},
          {"kind": "drift_curve", "source_program": "KPF-60", "subject": "chunk=doc",
           "served_pin": PIN, "window": WIN, "drift_unit": "nmse",
           "points": [{"position": 0, "drift": 0.0}, {"position": 512, "drift": 0.02}]},
          {"kind": "prefix_hit_share", "source_program": "KPF-64", "subject": "role=frontdoor",
           "served_pin": PIN, "window": WIN, "realised_tokens": 900, "ideal_tokens": 1000}]
    ms += extra or []
    return chunk_kv.write_belief_measurements(tmp_path, run_id="kv1", producer="kpf-runner",
                                              results_path=res, measurements=ms, emitted_at=WHEN)


CARRIERS = {"inj": (injection_fixture, inj_write, 2), "kv": (chunk_kv, kv_write, 4)}


@pytest.fixture(params=sorted(CARRIERS))
def carrier(request):
    return CARRIERS[request.param]


def test_round_trip_is_graded_by_the_shared_ladder(carrier, tmp_path):
    mod, write, n = carrier
    natives = mod.native_rows(write(tmp_path))
    assert len(natives) == n
    for nat in natives:
        q, t, reasons = ct.grade(mod.project(nat))
        assert (q, t, reasons) == ("Witnessed", "Attested", [])


def test_no_sidecar_zero_rows_and_tamper_voids(carrier, tmp_path):
    mod, write, _ = carrier
    assert mod.rows_for_run(tmp_path) == ()
    sc = write(tmp_path)
    lines = sc.read_text().splitlines()
    row = json.loads(lines[0]); row["claim"] += " (edited)"; lines[0] = json.dumps(row, sort_keys=True)
    sc.write_text("\n".join(lines) + "\n")
    assert mod.native_rows(sc) == ()


def test_mutated_attestation_grades_down(carrier, tmp_path):
    mod, write, n = carrier
    sc = write(tmp_path)
    Path(json.loads(sc.read_text().splitlines()[0])["results_path"]).write_text("tamper")
    nat = mod.native_rows(sc)
    assert len(nat) == n and ct.grade(mod.project(nat[0]))[:2] != ("Witnessed", "Attested")


def test_foreign_row_refused(carrier):
    with pytest.raises(ct.ProjectionError):
        carrier[0].project({"row": {"schema": "other"}})


def test_injection_claim_is_static_attack_asr_never_robustness(tmp_path):
    rows = {n["row"]["extra"]["arm_label"]: n["row"] for n in injection_fixture.native_rows(inj_write(tmp_path))}
    assert rows["no-sentence"]["claim"].startswith(injection_fixture.CLAIM_PREFIX)
    assert "not a robustness claim" in rows["no-sentence"]["claim"]
    assert rows["no-sentence"]["value"] == pytest.approx(0.4) and rows["no-sentence"]["category"] == "BASELINE"
    sc = tmp_path / injection_fixture.SIDECAR_NAME
    row = json.loads(sc.read_text().splitlines()[0])
    row["claim"] = "arm is robust to injection"
    row = injection_fixture.ns.seal(row)
    assert any("fixed" in p for p in injection_fixture.validate_row(row))


def test_injection_refuses_missing_pin_bad_thinking_and_duplicates(tmp_path):
    ok = {"thinking_setting": "on", "served_pin": PIN, "is_control": False,
          "attacks": [{"fixture_id": "a", "attack_success": False}]}
    for bad in ({**ok, "served_pin": {"role": "x"}}, {**ok, "thinking_setting": "maybe"},
                {**ok, "attacks": [{"fixture_id": "a", "attack_success": 1}]},
                {**ok, "attacks": [{"fixture_id": "a", "attack_success": True}] * 2}):
        with pytest.raises(injection_fixture.CaptureError):
            inj_write(tmp_path, bad=bad)


def test_kv_rederives_values(tmp_path):
    by = {n["row"]["extra"]["kind"]: n["row"] for n in chunk_kv.native_rows(kv_write(tmp_path))}
    assert by["prefill_rate"]["value"] == 105.0 and by["inject_latency"]["value"] == 13.0
    assert by["drift_curve"]["value"] == 0.02 and by["prefix_hit_share"]["value"] == 0.9
    row = json.loads((tmp_path / chunk_kv.SIDECAR_NAME).read_text().splitlines()[0])
    row["value"] = 999.0
    assert any("re-derive" in p for p in chunk_kv.validate_row(chunk_kv.ns.seal(row)))


def test_kv_requires_pin_window_and_known_program(tmp_path):
    base = {"kind": "prefill_rate", "source_program": "KPF-60", "subject": "s",
            "served_pin": PIN, "window": WIN, "samples": [1.0]}
    for bad in ({**base, "served_pin": {"role": "x"}}, {**base, "window": {"window_id": "w"}},
                {**base, "source_program": "OTHER"}, {**base, "samples": []},
                {**base, "kind": "prefix_hit_share", "realised_tokens": 1, "ideal_tokens": 0}):
        with pytest.raises(chunk_kv.CaptureError):
            res = tmp_path / "r.json"; res.write_text("{}")
            chunk_kv.write_belief_measurements(tmp_path, run_id="x", producer="p", results_path=res,
                                               measurements=[bad], emitted_at=WHEN)


def test_frames_emit(carrier, tmp_path):
    mod, write, n = carrier
    assert len(mod.frames_for_sidecar(write(tmp_path), as_of="2026-10-21T11:00:00Z")) >= n
