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


def kpf62_write(tmp_path, measurements=None):
    """Explicit synthetic payloads; these are reader fixtures, never model-run evidence."""
    res = tmp_path / "kpf62_synthetic_results.json"
    res.write_text('{"fixture_scope":"synthetic adapter unit data; not a model run"}')
    g1_rows = [
        {"schema": chunk_kv.G1_POSITION_SCHEMA, "delta": 17, "position": 0, "component": "k", "comparison": "inject_vs_seq_add",
         "sum_sq_error": 0.0, "reference_sq_norm": 2.0, "element_count": 2, "mismatch_count": 0},
        {"schema": chunk_kv.G1_POSITION_SCHEMA, "delta": 17, "position": 1, "component": "k", "comparison": "inject_vs_seq_add",
         "sum_sq_error": 0.0, "reference_sq_norm": 1.0, "element_count": 1, "mismatch_count": 0},
    ]
    ref_rows = [
        {"schema": chunk_kv.G1_POSITION_SCHEMA, "delta": 17, "position": 0, "component": "k", "comparison": "inject_vs_in_place_ref",
         "sum_sq_error": 0.25, "reference_sq_norm": 0.0, "element_count": 2, "mismatch_count": 1},
    ]
    requests = []
    positions = []
    kl = {"head": [0.01, 0.03, 0.05, 0.07], "none": [0.2, 0.3, 0.4, 0.5], "all-inject": [0.0] * 4}
    for rid in ("synthetic-a", "synthetic-b"):
        for mode in ("head", "none", "all-inject"):
            request = {"id": rid, "mode": mode, "n_tokens": 2048, "n_chunks": 3, "r": 0.2}
            if mode == "all-inject":
                request["bit_identical_to_ref"] = True
            requests.append(request)
            for row, kval in enumerate(kl[mode]):
                positions.append({"id": rid, "mode": mode, "row": row, "pos": 100 + row,
                                  "kl": kval, "top1": int(mode == "all-inject" or row != 0),
                                  "nmse": 0.1 * row if mode == "head" else 0.01 * row})
    base = {"source_program": "KPF-62", "subject": "synthetic-attention-case",
            "served_pin": PIN, "window": WIN}
    ms = [
        {**base, "kind": "shift_exactness", "measure": "k_nmse", "component": "k",
         "comparison": "inject_vs_seq_add", "delta": 17, "position_rows": g1_rows},
        {**base, "kind": "shift_exactness", "measure": "mismatch_fraction", "component": "k",
         "comparison": "inject_vs_seq_add", "delta": 17, "position_rows": g1_rows},
        {**base, "kind": "shift_exactness", "measure": "k_nmse", "component": "k",
         "comparison": "inject_vs_in_place_ref", "delta": 17, "position_rows": ref_rows},
        {**base, "kind": "approx_gate", "measure": "mean_kl", "selector_mode": "head", "naive_mode": "none",
         "request_rows": requests, "position_rows": positions},
        {**base, "kind": "approx_gate", "measure": "naive_ratio", "selector_mode": "head", "naive_mode": "none",
         "request_rows": requests, "position_rows": positions},
        {**base, "kind": "approx_gate", "measure": "top1", "selector_mode": "head", "naive_mode": "none",
         "request_rows": requests, "position_rows": positions},
    ]
    return chunk_kv.write_belief_measurements(tmp_path, run_id="kpf62-synthetic", producer="synthetic-unit-fixture",
                                              results_path=res, measurements=measurements or ms, emitted_at=WHEN)


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


def test_kpf62_synthetic_rows_rederive_and_use_shared_ladder(tmp_path):
    natives = chunk_kv.native_rows(kpf62_write(tmp_path))
    rows = {(n["row"]["extra"]["kind"], n["row"]["extra"].get("measure"),
             n["row"]["extra"].get("comparison")): n["row"] for n in natives}
    g1 = rows[("shift_exactness", "k_nmse", "inject_vs_seq_add")]
    assert g1["value"] == 0.0
    assert g1["metric_direction"] == "lower_better"
    assert rows[("shift_exactness", "mismatch_fraction", "inject_vs_seq_add")]["value"] == 0.0
    ref = rows[("shift_exactness", "k_nmse", "inject_vs_in_place_ref")]
    assert ref["value"] == 0.25  # zero reference energy uses squared error, as test-chunk-kv does
    assert "informational" in ref["claim"] and "not a G1a gate" in ref["claim"]
    assert rows[("approx_gate", "mean_kl", None)]["value"] == pytest.approx(0.04)
    assert rows[("approx_gate", "naive_ratio", None)]["value"] == pytest.approx(8.75)
    assert rows[("approx_gate", "top1", None)]["value"] == pytest.approx(0.75)
    for native in natives:
        assert ct.grade(chunk_kv.project(native)) == ("Witnessed", "Attested", [])
    frames = chunk_kv.frames_for_sidecar(tmp_path / chunk_kv.SIDECAR_NAME, as_of="2026-10-21T11:00:00Z")
    natives_by_id = {native["row"]["measurement_id"]: native for native in natives}
    rows_by_id = {measurement_id: native["row"] for measurement_id, native in natives_by_id.items()}
    assert len(rows_by_id) == len(natives)
    assert len(frames) == 3 * len(natives)
    frame_types = {
        "epyc.vidya/frame/source_observed/v1": "source",
        "epyc.vidya/frame/claim_proposed/v1": "claim",
        "epyc.vidya/frame/evidence_supports_claim/v1": "evidence",
    }
    frames_by_id = {measurement_id: {kind: [] for kind in frame_types.values()}
                    for measurement_id in rows_by_id}
    for frame in frames:
        assertion = frame["assertion"]
        if frame["frame_type"] == "epyc.vidya/frame/source_observed/v1":
            frame_id = assertion["source_id"]
            prefix = "src_"
        elif frame["frame_type"] == "epyc.vidya/frame/claim_proposed/v1":
            frame_id = assertion["claim_id"]
            prefix = "clm_"
        else:
            assert frame["frame_type"] == "epyc.vidya/frame/evidence_supports_claim/v1"
            frame_id = assertion["evidence_id"]
            prefix = "evd_"
        assert frame_id.startswith(prefix)
        measurement_id = frame_id[len(prefix):]
        assert measurement_id in frames_by_id
        frames_by_id[measurement_id][frame_types[frame["frame_type"]]].append(frame)

    for measurement_id, row in rows_by_id.items():
        source_frames = frames_by_id[measurement_id]["source"]
        claim_frames = frames_by_id[measurement_id]["claim"]
        evidence_frames = frames_by_id[measurement_id]["evidence"]
        assert len(source_frames) == len(claim_frames) == len(evidence_frames) == 1
        source = source_frames[0]["assertion"]
        claim = claim_frames[0]["assertion"]
        evidence = evidence_frames[0]["assertion"]
        source_id = f"src_{measurement_id}"
        claim_id = f"clm_{measurement_id}"
        assert source["source_id"] == source_id
        assert source["source_kind"] == chunk_kv.SOURCE_KIND
        assert source["title"] == row["metric"]
        assert source["revision_observed"] == row["date"]
        assert source["locator"] == (
            f"chunk-kv:{row['run_id']}:{row['extra']['kind']}:{row['extra']['window']['window_id']}:"
            f"{row['results_path']}"
        )
        assert claim["claim_id"] == claim_id
        assert claim["source_id"] == source_id
        assert claim["display_text"] == row["claim"]
        assert evidence["evidence_id"] == f"evd_{measurement_id}"
        assert evidence["claim_id"] == claim_id
        assert evidence["source_id"] == source_id
        quality, truth, reasons = ct.grade(chunk_kv.project(natives_by_id[measurement_id]))
        assert evidence["grade"] == {"Q": quality, "T": truth}
        assert evidence["protocol_id"] == row["protocol_id"]
        assert evidence["reps"] == row["reps"]
        assert evidence["category"] == row["category"]
        assert evidence["metric_direction"] == row["metric_direction"]
        assert evidence_frames[0]["provenance"]["grade_reasons"] == reasons


def test_kpf62_rederives_tampering_and_rejects_missing_or_unbound_metrics(tmp_path):
    sc = kpf62_write(tmp_path)
    lines = sc.read_text().splitlines()
    row = json.loads(lines[0])
    row["value"] = 12.0
    row = chunk_kv.ns.seal(row)
    assert any("re-derive" in problem for problem in chunk_kv.validate_row(row))

    res = tmp_path / "kpf62_bad.json"
    res.write_text("{}")
    base = {"source_program": "KPF-62", "subject": "synthetic", "served_pin": PIN, "window": WIN}
    g1 = {**base, "kind": "shift_exactness", "measure": "k_nmse", "component": "k",
          "comparison": "inject_vs_seq_add", "delta": 17,
          "position_rows": [{"schema": chunk_kv.G1_POSITION_SCHEMA, "delta": 17, "position": 0, "component": "k", "comparison": "inject_vs_seq_add",
                             "sum_sq_error": 0.0, "reference_sq_norm": 0.0, "element_count": 1,
                             "mismatch_count": 2}]}
    with pytest.raises(chunk_kv.CaptureError):
        chunk_kv.write_belief_measurements(tmp_path, run_id="bad", producer="synthetic", results_path=res,
                                           measurements=[g1], emitted_at=WHEN)

    wrong_program = {**g1, "source_program": "KPF-60"}
    with pytest.raises(chunk_kv.CaptureError):
        chunk_kv.write_belief_measurements(tmp_path, run_id="wrong-program", producer="synthetic", results_path=res,
                                           measurements=[wrong_program], emitted_at=WHEN)

    # G3 zero values are valid measurements; undefined baseline/selector 0/0 is explicitly refused.
    zero_requests = [{"id": "z", "mode": mode, **({"bit_identical_to_ref": True} if mode == "all-inject" else {})}
                     for mode in ("head", "none", "all-inject")]
    zero_positions = [{"id": "z", "mode": mode, "row": 0, "pos": 4, "kl": 0.0, "top1": 1, "nmse": 0.0}
                      for mode in ("head", "none", "all-inject")]
    zero = {**base, "kind": "approx_gate", "measure": "mean_kl", "selector_mode": "head", "naive_mode": "none",
            "request_rows": zero_requests, "position_rows": zero_positions}
    valid = chunk_kv.write_belief_measurements(tmp_path, run_id="zero", producer="synthetic", results_path=res,
                                                measurements=[zero], emitted_at=WHEN)
    assert chunk_kv.native_rows(valid)[0]["row"]["value"] == 0.0
    undefined = {**zero, "measure": "naive_ratio"}
    with pytest.raises(chunk_kv.CaptureError):
        chunk_kv.write_belief_measurements(tmp_path, run_id="undefined", producer="synthetic", results_path=res,
                                           measurements=[undefined], emitted_at=WHEN)
    unsupported = {**zero, "measure": "retention"}
    with pytest.raises(chunk_kv.CaptureError):
        chunk_kv.write_belief_measurements(tmp_path, run_id="retention", producer="synthetic", results_path=res,
                                           measurements=[unsupported], emitted_at=WHEN)

    # A naive ratio pools the same request IDs and positions as the selector; a single surviving
    # baseline row or shifted position cannot stand in for the missing coverage.
    sidecar = kpf62_write(tmp_path)
    ratio_extra = next(n["row"]["extra"] for n in chunk_kv.native_rows(sidecar)
                       if n["row"]["extra"].get("measure") == "naive_ratio")
    partial = {**ratio_extra, "position_rows": [p for p in ratio_extra["position_rows"]
                                                if not (p["id"] == "synthetic-b" and p["mode"] == "none")]}
    with pytest.raises(chunk_kv.CaptureError):
        chunk_kv.write_belief_measurements(tmp_path, run_id="partial-baseline", producer="synthetic",
                                           results_path=res, measurements=[partial], emitted_at=WHEN)
    misaligned_positions = [dict(p) for p in ratio_extra["position_rows"]]
    next(p for p in misaligned_positions if p["id"] == "synthetic-a" and p["mode"] == "none")["pos"] += 1
    misaligned = {**ratio_extra, "position_rows": misaligned_positions}
    with pytest.raises(chunk_kv.CaptureError):
        chunk_kv.write_belief_measurements(tmp_path, run_id="misaligned-baseline", producer="synthetic",
                                           results_path=res, measurements=[misaligned], emitted_at=WHEN)
