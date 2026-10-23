"""KPF-26.1f: the VB-KVU-PF write side for KPF-26.1 task-outcome windows (per window: manifest digest, seed, per-arm
pass counts, spread, drop, verdict). One tuple per record through ``claim_tuple.grade()``; no new ladder."""
import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "vidya"))
import claim_tuple as ct  # noqa: E402
from adapters import kv_prefix_fork as kpf  # noqa: E402

REAL = Path("/mnt/raid0/llm/tmp/kpf261-outcome-out-v2")
RULE = "spread=|rate(A)-rate(A2)|; drop=rate(A)-rate(B)."


def _window(tmp_path, *, a=(1, 1, 1, 0), b=(1, 1, 1, 1), a2=(1, 1, 0, 0), verdict="WITHIN_SPREAD", seed=261):
    """A synthetic window dir + summary whose counts are what the real runner would write (4 cases x 1 rep)."""
    win = tmp_path / "win1"
    win.mkdir()
    steps = [("w0", "s0"), ("w0", "s1"), ("w1", "s0"), ("w1", "s1")]
    cases = [{"rep": 0, "arm": arm, "wave": w, "step": s, "pass": bool(p), "error": None, "answer": "x"}
             for arm, vec in (("A", a), ("B", b), ("A2", a2)) for (w, s), p in zip(steps, vec)]
    (win / "cases.jsonl").write_text("".join(json.dumps(c) + "\n" for c in cases))
    digest = hashlib.sha256(f"manifest-{seed}".encode()).hexdigest()
    (win / "manifest.json").write_text(json.dumps({"seed": seed, "n_tasks": 4, "digest": digest, "tasks": []}))
    (win / "treatment.json").write_text(json.dumps({"applied": True}))
    rate = {k: sum(v) / 4 for k, v in (("A", a), ("B", b), ("A2", a2))}
    pairs = list(zip(a, b, a2))
    summary = {
        "verdict": verdict, "reorder_decision": "KEEP_ON_ELIGIBLE", "gates": {"treatment_applied": True},
        "n_cases": 4, "regress": sum(1 for x, y, _ in pairs if x and not y),
        "improve": sum(1 for x, y, _ in pairs if not x and y), "ctrl_regress": sum(1 for x, _, z in pairs if x and not z),
        "ctrl_improve": sum(1 for x, _, z in pairs if not x and z),
        "pass_rate": {k: round(v, 4) for k, v in rate.items()}, "spread": round(abs(rate["A"] - rate["A2"]), 4),
        "drop": round(rate["A"] - rate["B"], 4), "sign_test_p_regress": 0.5, "rule": RULE,
        "manifest_digest": digest, "seed": seed, "complete": True, "stopped": None, "reps": 1,
        "finished_utc": "2026-10-22T22:20:34Z", "baseline_transport_errors": 0, "B_transport_errors": 0,
        "incomplete_cases": 0}
    sp = tmp_path / "summary.win1.json"
    sp.write_text(json.dumps(summary))
    binary = tmp_path / "llama-server"
    binary.write_bytes(b"bin")
    return win, sp, binary


def _row(tmp_path, **kw):
    win, sp, binary = _window(tmp_path, **kw)
    return kpf.outcome_record(win, sp, binary=binary, model="/m/Qwen3.6-35B-A3B-MTP-Q8_0.gguf", n_slots=4,
                              host="h"), win, sp


def test_outcome_record_projects_one_tuple_graded_by_the_shared_ladder(tmp_path):
    row, win, _ = _row(tmp_path)
    assert kpf.validate_row(row) == [] and row["arm"] == kpf.OUTCOME_ARM
    sidecar = tmp_path / "belief_measurements.jsonl"
    assert kpf.write_outcome_sidecar(sidecar, row) is True and kpf.write_outcome_sidecar(sidecar, row) is False
    natives = kpf.native_rows(sidecar)
    assert len(natives) == 1
    t = kpf.project(natives[0])
    assert t.metric == "kpf261_flag_on_task_pass_rate" and t.value == 1.0 and t.reps == 4
    assert t.observation["anchor_value"] == 0.75 and t.observation["outcome"] == "null"
    assert t.observation["outcome_native"] == "WITHIN_SPREAD" and t.observation["decisive"] is False
    assert t.observation["n_pairs"] == 4 and t.observation["noise_floor_rel"] == pytest.approx(0.25 / 0.75)
    assert t.extra["per_arm"]["A"] == {"pass": 3, "n": 4} and t.extra["seed"] == 261
    assert t.extra["manifest_digest"] == json.loads((win / "manifest.json").read_text())["digest"]
    assert t.attestation_present is True and t.attestation_verified is True and t.protocol_id == ""
    assert t.attestation_sha256 == hashlib.sha256((win / "cases.jsonl").read_bytes()).hexdigest()
    assert t.applicability["model_file"].endswith("Q8_0.gguf") and t.applicability["np"] == 4
    assert t.applicability["varied"] == ["ORCHESTRATOR_PREFIX_INDEX+ORCHESTRATOR_PREFIX_INDEX_FORK"]
    assert ct.grade(t)[:2] == ("Judged", "Located")  # n/one window/no protocol: the ladder's cap, not ours
    frames = kpf.frames_for_sidecar(sidecar, as_of="2026-10-23T12:00:00Z")
    assert frames and all(isinstance(f, dict) for f in frames)


def test_mutated_cases_file_grades_down_instead_of_being_skipped(tmp_path):
    row, win, _ = _row(tmp_path)
    sidecar = tmp_path / "belief_measurements.jsonl"
    kpf.write_outcome_sidecar(sidecar, row)
    (win / "cases.jsonl").write_text((win / "cases.jsonl").read_text() + "\n")
    (n,) = kpf.native_rows(sidecar)
    t = kpf.project(n)
    assert t.attestation_present is False and t.attestation_verified is None
    assert ct.grade(t)[:2] == ("Judged", "Located")


@pytest.mark.parametrize("verdict,outcome,decisive", [("UNCHANGED", "null", False), ("CHANGED", "regressed", True),
                                                      ("INVALID", "refused_scope", False)])
def test_producer_verdict_is_normalised_never_rederived(tmp_path, verdict, outcome, decisive):
    row, *_ = _row(tmp_path, verdict=verdict)
    t = kpf.project({"row": row, "sidecar_path": str(tmp_path / "x.jsonl"), "attestation_present": True})
    assert t.observation["outcome"] == outcome and t.observation["decisive"] is decisive
    assert t.observation["outcome_native"] == verdict and t.extra["verdict"] == verdict


def test_writer_refuses_a_window_whose_files_disagree_with_the_summary(tmp_path):
    win, sp, binary = _window(tmp_path)
    s = json.loads(sp.read_text())
    for patch, why in ((dict(regress=9), "regress"), (dict(complete=False, stopped="deadline"), "not complete"),
                       (dict(manifest_digest="0" * 64), "manifest"), (dict(drop=0.5), "drop"),
                       (dict(pass_rate={"A": 0.5, "B": 1.0, "A2": 0.5}), "pass_rate")):
        sp.write_text(json.dumps({**s, **patch}))
        with pytest.raises(ct.ProjectionError, match=why):
            kpf.outcome_record(win, sp, binary=binary, model="/m/x-Q8_0.gguf", n_slots=4)


def test_tampered_outcome_record_voids_file_and_per_arm_counts_are_validated(tmp_path):
    row, *_ = _row(tmp_path)
    assert kpf.validate_row({**row, "host": "other"}) == ["record_sha256 does not re-derive"]
    bad = json.loads(json.dumps(row))
    bad["kpf_outcome"]["per_arm"]["B"]["pass"] = 99
    assert any("per_arm.B" in p for p in kpf.validate_row(bad))
    bad = json.loads(json.dumps(row))
    del bad["kpf_outcome"]["per_arm"]["A2"]
    assert any("per_arm" in p for p in kpf.validate_row(bad))
    assert any("rows_sha256" in p for p in kpf.validate_row({k: v for k, v in row.items() if k != "rows_sha256"}))


def test_cli_write_outcome_is_idempotent(tmp_path, capsys):
    win, sp, binary = _window(tmp_path)
    args = ["write-outcome", "--win-dir", str(win), "--summary", str(sp), "--sidecar", str(tmp_path / "bm.jsonl"),
            "--binary", str(binary), "--model", "/m/x-Q8_0.gguf", "--n-slots", "4"]
    assert kpf.main(args) == 0 and json.loads(capsys.readouterr().out)["written"] is True
    assert kpf.main(args) == 0 and json.loads(capsys.readouterr().out)["written"] is False
    assert len((tmp_path / "bm.jsonl").read_text().splitlines()) == 1


def test_fork_records_unaffected_by_outcome_arm():
    assert kpf.OUTCOME_ARM not in kpf.ARMS
    assert any("arm" in p for p in kpf.validate_row({"schema": kpf.SCHEMA, "arm": "kpf261_outcome_x"}))


@pytest.mark.skipif(not (REAL / "summary.win1.json").is_file(), reason="real KPF-26.1 windows not on this host")
def test_real_windows_rederive_from_cases_and_project(tmp_path):
    binary = Path("/mnt/raid0/llm/kernels/production/cpu/llama-server")
    if not binary.is_file():
        pytest.skip("production cpu binary not present")
    side = tmp_path / "belief_measurements.jsonl"
    for w in (1, 2):
        row = kpf.outcome_record(REAL / f"win{w}", REAL / f"summary.win{w}.json", binary=binary,
                                 model="/mnt/raid0/llm/models/Qwen3.6-35B-A3B-MTP-Q8_0.gguf", n_slots=4,
                                 run_id=f"kpf261-v2-win{w}")
        assert kpf.write_outcome_sidecar(side, row)
    tuples = [kpf.project(n) for n in kpf.native_rows(side)]
    assert [t.extra["verdict"] for t in tuples] == ["WITHIN_SPREAD", "WITHIN_SPREAD"]
    assert [t.extra["per_arm"]["A"]["pass"] for t in tuples] == [137, 137]
    assert [t.extra["per_arm"]["B"]["pass"] for t in tuples] == [141, 138]
    assert all(ct.grade(t)[:2] == ("Judged", "Located") for t in tuples)
