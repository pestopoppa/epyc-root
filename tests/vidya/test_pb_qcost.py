"""VB-PBQ-1: PB-QCOST-1 prefill-cost records (original and confirm layouts) project to scoped OBSERVATION beliefs.

The fixture is SYNTHETIC (test data, not a measurement): rows drawn from a known cost model with seeded jitter, and the
producer-shaped summary / VERDICT built from them with the adapter's copy of the producers' pure fit code. The real run
directories, when present on this host, are checked against the producers' own stated numbers.
"""
import copy
import hashlib
import json
import random
import shutil
import sys
from dataclasses import replace
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "vidya"))
import claim_tuple as ct  # noqa: E402
from adapters import pb_qcost as P  # noqa: E402

AS_OF = "2026-10-24T09:00:00Z"
BIN = "/mnt/raid0/llm/kernels/builds/gpu-20261020-dd3d9721c/bin/llama-server"
BIN_SHA = "49b124aa59a6ebfd3dfa993ee284ac5727d38f033a187fa086748204dbd5fad5"
LENGTHS = (4000, 8000, 16000, 32000, 64000)
REAL_ORIG = Path("/mnt/raid0/llm/tmp/pb-qcost-1/runs/20261021T212922Z")
REAL_CONF = Path("/mnt/raid0/llm/tmp/f8-launchers-20261023/pb-qcost-1-confirm")
PRE_TEXT = "# SYNTHETIC predeclaration (test fixture)\n"


def _argv(ub: int, out: Path) -> list[str]:
    return [BIN, "-m", "/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf", "-np", "5", "-c", "393216", "-b", str(ub),
            "-ub", str(ub), "--flash-attn", "on", "-ctk", "q8_0", "-ctv", "q8_0", "--kv-unified", "-md",
            "/mnt/raid0/llm/models/Qwen3.8-27B-DFlash2-Q8_0.gguf", "--spec-type", "draft-dflash",
            "--spec-draft-n-max", "7", "--device", "ROCm0", "--slot-save-path", str(out / f"ss{ub}"), "--port", "18391"]


def _rows(out: Path, ubs: tuple[int, ...], phased: bool, seed: int = 7) -> list[dict]:
    """SYNTHETIC per-interval rows from t = a_n + b q + d q c (+ seeded jitter), q = ub - 8n."""
    rng = random.Random(seed)
    coef = {1: (190.0, 1.15, 2.2e-5), 4: (340.0, 1.03, 2.85e-5)}
    rows: list[dict] = []
    for ub in ubs:
        tag = {"ub": ub} if phased else {}
        argv = _argv(ub, out)
        rows.append({"kind": "port_ownership", **tag, "ok": True, "detail": "synthetic", "pid": 1, "argv": argv})
        if phased:
            rows.append({"kind": "proof", "ub": ub, "graphs": "ON", "exe_matches_binary": True})
        reps = 3 if ub == 512 else 1
        for n in P.NS:
            a, b, d = coef[n]
            q = ub - 8 * n
            for rep in range(1, reps + 1):
                for L in LENGTHS:
                    ivs = []
                    for c in range(q, L - q, max(q, L // 6)):
                        t = a + b * q + d * q * c + rng.uniform(-15, 15)
                        ivs.append({"c": c, "dn": q, "dt_s": round(t / 1000, 4), "t_ms": round(t, 2),
                                    "iter_ms": round(t * 512 / q, 2)})
                    if not phased:
                        for i in ivs:
                            i.pop("t_ms")
                    rows.append({"kind": "run", **tag, **({"phase_id": f"ub{ub}-syn"} if phased else {}),
                                 "n_gen": n, "rep": rep, "length": L, "http": 200,
                                 "ttft_ms": round(sum(i["dt_s"] for i in ivs) * 1000 + 50, 1), "intervals": ivs})
        if phased:
            rows.append({"kind": "phase_done", "ub": ub, "phase_id": f"ub{ub}-syn"})
    return rows


def _dump_rows(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))


def _itv(fit: dict) -> dict:
    return {"unit": "ms per server iteration (q = 512 tokens, interval = consecutive log lines)",
            "refit_intercept_ms_at_c0": fit["A"], "refit_slope_ms_per_cached_token": fit["B"],
            "noise_floor_train_rmse_ms_per_iter": fit["noise_rmse"], "noise_floor_n_intervals": fit["noise_n"],
            "refit_model_heldout": {"n": fit["held_n"], "p99_abs": fit["p99_abs"],
                                    "p99_under_prediction": fit["p99_under"]}}


def write_original(tmp_path: Path) -> Path:
    run = tmp_path / "orig" / "20261021T000000Z"
    run.mkdir(parents=True)
    rows = _rows(run, (512,), phased=False)
    _dump_rows(run / P.ROWS, rows)
    per_n = {str(n): {"interval_level": _itv(P._interval_fit(rows, n))} for n in P.NS}
    argv = rows[0]["argv"]
    summary = {"schema": P.SCHEMA, "status": "complete", "overall": "FAIL", "np": 5, "binary": BIN,
               "binary_sha256": BIN_SHA, "analysis": {"per_n": per_n}, "finished": "2026-10-21T22:01:02Z",
               "server": {"readback": {"proc_cmdline": argv, "proc_cmdline_matches_argv": True,
                                       "exe_matches_binary": True}}}
    (run / P.SUMMARY).write_text(json.dumps(summary))
    return run


def write_confirm(tmp_path: Path) -> Path:
    unit = tmp_path / "pb-qcost-1-confirm"
    run = unit / "out" / "run"
    run.mkdir(parents=True)
    ubs = (512, 256, 1024)
    rows = _rows(run, ubs, phased=True)
    _dump_rows(run / P.ROWS, rows)
    for ub in ubs:
        (run / f"graphs_proof_ub{ub}.json").write_text(json.dumps({
            "ub": ub, "graphs": "ON", "HSA_OVERRIDE_CPU_AFFINITY_DEBUG_in_environ": ["HSA_OVERRIDE_CPU_AFFINITY_DEBUG=0"],
            "own_pid_kfd_vram_mib_at_ready": 50000.0 + ub, "exe": BIN, "exe_matches_binary": True,
            "proc_cmdline": next(r["argv"] for r in rows if r.get("kind") == "port_ownership" and r["ub"] == ub)}))
    (unit / "out" / "sibling_summary.json").write_text(json.dumps({"cpus": "88-95", "median_busy_frac": 0.003}))
    (unit / P.PREDECLARATION).write_text(PRE_TEXT)
    pre_sha = hashlib.sha256(PRE_TEXT.encode()).hexdigest()
    old = {1: (766.85, 0.010794), 4: (871.40, 0.013798)}
    confirm, q_axis, summary_n, summary_q = {}, {}, {}, {}
    for n in P.NS:
        fit = P._interval_fit(rows, n)
        summary_n[str(n)] = {"interval_level": _itv(fit)}
        confirm[str(n)] = {"A_new": fit["A"], "A_old": old[n][0], "B_new": fit["B"], "B_old": old[n][1],
                           "noise_floor_ms_per_iter": fit["noise_rmse"],
                           "refit_heldout_p99_abs_ms_per_iter": fit["p99_abs"],
                           "refit_heldout_p99_under_ms_per_iter": fit["p99_under"],
                           "dA_ms": round(fit["A"] - old[n][0], 2),
                           "dB_times_Cref_ms": round((fit["B"] - old[n][1]) * P.C_REF, 2), "verdict": "CONFIRMED"}
        qf = P._q_fit(rows, n)
        q_axis[str(n)] = {"q_levels_by_ub": qf["levels"], "q_identified": True, "coef": qf["coef"],
                          "ci95_a": qf["ci95_a"], "ci95_b": qf["ci95_b"], "ci95_d": qf["ci95_d"],
                          "noise_floor_train_rmse_ms_per_iter": qf["noise_rmse"], "n_train_intervals": qf["noise_n"],
                          "heldout_interval": {"n": qf["held_n"], "p99_abs": qf["p99_abs"]},
                          "b_vs_assumed_0.9865": {"agrees_within_noise": False},
                          "d_vs_2026_10_21_refit": {"d_old": round(old[n][1] / 512, 9)}, "verdict": "PASS"}
        summary_q[str(n)] = {"coef": qf["coef"]}
    label = "PB-QCOST-1 confirm CONFIRMED; q axis PASS; grade INDICATIVE"
    verdict = {"phases_done": sorted(ubs), "confirm": {**confirm, "overall": "CONFIRMED"},
               "confirm_overall": "CONFIRMED", "q_axis": {"per_n": q_axis, "model": "t_ms = a_n + b*q + d*q*c",
                                                          "overall": "PASS"},
               "q_overall": "PASS", "proof": P._proofs(run, rows), "label": label, "grade": "INDICATIVE",
               "sibling_summary": None, "predeclaration_sha256": pre_sha, "tolerance_def": "synthetic"}
    (unit / P.VERDICT).write_text(json.dumps(verdict))
    (unit / P.RUN_RECORD).write_text(json.dumps({
        "label": label, "predeclaration_sha256": pre_sha, "binary": BIN, "binary_sha256": BIN_SHA,
        "window_id": "pb-qcost-1-confirm-syn", "time": "2026-10-23T20:17:03Z"}))
    (run / P.SUMMARY).write_text(json.dumps({
        "schema": P.SCHEMA, "status": "complete", "np": 5, "binary": BIN, "binary_sha256": BIN_SHA, "ubs": list(ubs),
        "analysis": {"per_n": summary_n}, "analysis_q": {"per_n": summary_q}, "finished": "2026-10-23T20:17:00Z"}))
    return unit


def write(tmp_path: Path) -> Path:
    """Both layouts under one root (the ingest dispatcher finds each unit as a child)."""
    root = tmp_path / "pbq"
    root.mkdir()
    shutil.move(str(write_original(tmp_path)), str(root / "20261021T000000Z"))
    shutil.move(str(write_confirm(tmp_path)), str(root / "pb-qcost-1-confirm"))
    return root


def _by(tuples):
    return {t.measurement_id.split(":", 4)[4]: t for t in tuples}


# --- original layout --------------------------------------------------------------------------------------------
def test_original_projects_four_metrics_per_n_as_located_observations(tmp_path):
    run = write_original(tmp_path)
    natives = P.native_rows(run)
    tuples = [P.project(n) for n in natives]
    assert len(tuples) == 8
    by = _by(tuples)
    assert set(by) == {f"ub512:n{n}:{k}" for n in P.NS for k in ("intercept", "c_slope", "noise_floor",
                                                                  "heldout_p99_abs")}
    summary = json.loads((run / P.SUMMARY).read_text())
    il = summary["analysis"]["per_n"]["4"]["interval_level"]
    assert by["ub512:n4:intercept"].value == il["refit_intercept_ms_at_c0"]
    assert by["ub512:n4:heldout_p99_abs"].value == il["refit_model_heldout"]["p99_abs"]
    for t in tuples:
        assert ct.grade(t)[:2] == ("Judged", "Located")
        assert t.protocol_id == "" and t.attestation_verified is True
        assert t.attestation_sha256 == hashlib.sha256((run / P.ROWS).read_bytes()).hexdigest()
        assert t.unit.startswith("ms per server iteration") and "token" not in t.unit.split("(")[0].replace(
            "per cached token", "")
        assert t.observation["retrofit"] is True
        a = t.applicability
        assert a["np"] == 5 and a["backend"] == "gpu" and a["kernel"]["execution_digest"] == BIN_SHA
        assert a["knobs"]["q_tokens_per_iteration"] in (504, 480) and a["knobs"]["b"] == 512
        assert "q coefficient is NOT measured" in a["recipe"]
        # a synthetic jsonl is not the pinned 21:29Z digest: no grade is invented for it
        assert "grade UNGRADED" in a["recipe"]


def test_original_grade_rides_in_applicability_when_the_digest_is_pinned(tmp_path, monkeypatch):
    run = write_original(tmp_path)
    digest = hashlib.sha256((run / P.ROWS).read_bytes()).hexdigest()
    monkeypatch.setitem(P.ORIGINAL_GRADES, digest, P.ORIGINAL_GRADES[next(iter(P.ORIGINAL_GRADES))])
    t = P.project(P.native_rows(run)[0])
    assert "grade INDICATIVE" in t.applicability["recipe"] and "KVU-12 np8 CPU timing" in t.applicability["recipe"]
    assert t.extra["grade"] == "INDICATIVE" and "PREDECLARATION.md" in t.extra["grade_source"]


def test_original_summary_that_does_not_rederive_is_refused(tmp_path):
    run = write_original(tmp_path)
    s = json.loads((run / P.SUMMARY).read_text())
    s["analysis"]["per_n"]["1"]["interval_level"]["refit_intercept_ms_at_c0"] += 0.1
    (run / P.SUMMARY).write_text(json.dumps(s))
    with pytest.raises(ct.ProjectionError, match="re-derive"):
        P.native_rows(run)


def test_original_tampered_row_is_refused(tmp_path):
    run = write_original(tmp_path)
    rows = [json.loads(x) for x in (run / P.ROWS).read_text().splitlines()]
    next(r for r in rows if r.get("kind") == "run" and r["length"] == 16000)["intervals"][0]["iter_ms"] += 40
    _dump_rows(run / P.ROWS, rows)
    with pytest.raises(ct.ProjectionError):
        P.native_rows(run)


def test_original_jsonl_changed_after_read_is_refused_at_projection(tmp_path):
    run = write_original(tmp_path)
    native = P.native_rows(run)[0]
    with (run / P.ROWS).open("a") as fh:
        fh.write("\n")
    with pytest.raises(ct.ProjectionError, match="changed"):
        P.project(native)


# --- confirm layout ---------------------------------------------------------------------------------------------
def test_confirm_projects_ub512_and_q_axis_with_cis_and_the_path_defect_cause(tmp_path):
    unit = write_confirm(tmp_path)
    tuples = [P.project(n) for n in P.native_rows(unit)]
    assert len(tuples) == 18
    by = _by(tuples)
    verdict = json.loads((unit / P.VERDICT).read_text())
    q4 = verdict["q_axis"]["per_n"]["4"]
    assert by["q_axis:n4:q_b"].value == q4["coef"]["b_ms_per_token"] and by["q_axis:n4:q_b"].unit == "ms per token"
    assert by["q_axis:n4:q_b"].extra["ci95"] == q4["ci95_b"]
    assert by["q_axis:n1:q_d"].unit == "ms per token x cached token"
    assert by["q_axis:n1:q_d"].extra["ci95"] == verdict["q_axis"]["per_n"]["1"]["ci95_d"]
    assert by["ub512:n1:intercept"].observation["anchor_value"] == 766.85
    assert by["ub512:n1:intercept"].observation["outcome_native"] == "CONFIRMED"
    assert "b" not in by["q_axis:n1:q_a"].applicability["knobs"]
    assert by["q_axis:n1:q_a"].applicability["varied"] == ["b", "ub"]
    for t in tuples:
        assert ct.grade(t)[:2] == ("Judged", "Located") and t.protocol_id == ""
        assert "grade INDICATIVE" in t.applicability["recipe"]
        assert "sibling-summary path defect" in t.applicability["recipe"]
        assert t.extra["proofs"]["all_ok"] is True and set(t.extra["proofs"]["per_ub"]) == {"256", "512", "1024"}
        assert t.extra["sibling_summary_unread"]["median_busy_frac"] == 0.003


def test_confirm_verdict_that_does_not_rederive_is_refused(tmp_path):
    unit = write_confirm(tmp_path)
    v = json.loads((unit / P.VERDICT).read_text())
    bad = copy.deepcopy(v)
    bad["q_axis"]["per_n"]["1"]["ci95_b"][0] += 1e-6
    (unit / P.VERDICT).write_text(json.dumps(bad))
    with pytest.raises(ct.ProjectionError, match="ci95_b"):
        P.native_rows(unit)
    bad = copy.deepcopy(v)
    bad["confirm"]["4"]["A_new"] += 1
    (unit / P.VERDICT).write_text(json.dumps(bad))
    with pytest.raises(ct.ProjectionError, match="A_new"):
        P.native_rows(unit)
    bad = copy.deepcopy(v)
    bad["proof"]["per_ub"]["256"]["ok"] = False
    (unit / P.VERDICT).write_text(json.dumps(bad))
    with pytest.raises(ct.ProjectionError, match="proof"):
        P.native_rows(unit)


def test_confirm_tampered_rows_or_predeclaration_are_refused(tmp_path):
    unit = write_confirm(tmp_path)
    (unit / P.PREDECLARATION).write_text(PRE_TEXT + "edited after launch\n")
    with pytest.raises(ct.ProjectionError, match="PREDECLARATION"):
        P.native_rows(unit)
    (unit / P.PREDECLARATION).write_text(PRE_TEXT)
    path = unit / "out" / "run" / P.ROWS
    rows = [json.loads(x) for x in path.read_text().splitlines()]
    next(r for r in rows if r.get("kind") == "run" and r["ub"] == 1024 and r["length"] == 4000)["intervals"][0][
        "t_ms"] += 30
    _dump_rows(path, rows)
    with pytest.raises(ct.ProjectionError):
        P.native_rows(unit)


def test_foreign_and_inner_dirs_are_declined(tmp_path):
    assert P.native_rows(tmp_path) == []
    (tmp_path / "VERDICT.json").write_text(json.dumps({"label": "spec-rng"}))
    assert P.native_rows(tmp_path) == []
    unit = write_confirm(tmp_path / "c")
    assert P.native_rows(unit / "out" / "run") == []  # the confirm's inner dir is not an original-layout run
    other = tmp_path / "other"
    other.mkdir()
    (other / P.ROWS).write_text("{}\n")
    (other / P.SUMMARY).write_text(json.dumps({"schema": "epyc.pbhol1.run.v1"}))
    assert P.native_rows(other) == []


def test_observation_and_scope_never_move_the_grade(tmp_path):
    for t in (P.project(n) for n in P.native_rows(write_confirm(tmp_path))):
        assert ct.grade(t) == ct.grade(replace(t, observation={}, applicability={}))
        frames = ct.to_frames(t, as_of=AS_OF, adapter_id=P.ADAPTER_ID, authority=P.AUTHORITY)
        assert len(frames) == 3


# --- the real records, when this host has them -------------------------------------------------------------------
@pytest.mark.skipif(not (REAL_ORIG / P.ROWS).is_file(), reason="2026-10-21 run dir not on this host")
def test_real_original_run_reproduces_the_summary_and_carries_its_grade():
    by = _by(P.project(n) for n in P.native_rows(REAL_ORIG))
    assert len(by) == 8
    t = by["ub512:n1:intercept"]
    assert t.attestation_sha256.startswith("a82cdf93")
    assert (t.value, by["ub512:n4:intercept"].value) == (766.8, 871.4)
    assert (by["ub512:n1:heldout_p99_abs"].value, by["ub512:n4:heldout_p99_abs"].value) == (72.292, 210.692)
    assert (by["ub512:n1:c_slope"].value, by["ub512:n4:noise_floor"].value) == (0.010794, 28.858)
    assert "grade INDICATIVE" in t.applicability["recipe"] and t.applicability["knobs"]["q_tokens_per_iteration"] == 504
    assert by["ub512:n4:intercept"].applicability["knobs"]["q_tokens_per_iteration"] == 480


@pytest.mark.skipif(not (REAL_CONF / P.VERDICT).is_file(), reason="confirm launcher dir not on this host")
def test_real_confirm_run_reproduces_the_verdict_including_bootstrap_cis():
    by = _by(P.project(n) for n in P.native_rows(REAL_CONF))
    assert len(by) == 18
    assert by["q_axis:n1:q_b"].value == 1.16553045 and by["q_axis:n1:q_b"].extra["ci95"] == [1.11140664, 1.20932548]
    assert by["q_axis:n4:q_d"].value == 2.848e-05 and by["q_axis:n4:q_d"].extra["ci95"] == [2.679e-05, 3.086e-05]
    assert by["ub512:n4:heldout_p99_abs"].value == 211.166 and by["ub512:n1:intercept"].value == 774.3
    t = by["ub512:n1:intercept"]
    assert t.extra["predeclaration_sha256"].startswith("f45aef1a") and t.extra["grade"] == "INDICATIVE"
    assert "sibling-summary path defect" in t.applicability["recipe"]
