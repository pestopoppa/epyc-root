"""stage1_result: RESULT.json covers every resumed stint, rebuilt from results.jsonl (r8c bug: last stint only)."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "coordination"))
from taskflow import stage1_result as S  # noqa: E402


def _row(arm, key, verdict, fc=None, wall=100.0):
    return {"unit_id": f"{arm}:{key}", "arm": arm, "key": key, "np": 1, "thinking": arm.endswith("think") and "no" not in arm,
            "verdict": verdict, "reason": "reviewer-done" if verdict == "verified" else "x", "failure_class": fc,
            "wall_s": wall, "perf": {"requests": 2, "output_tokens": 100, "decode_slot_s": 10.0, "decode_tok_s_median": 10.0}}


def _stint_phase(arm, rows, pid):
    return {"arm": arm, "np": 1, "tasks": len(rows), "verified": sum(r["verdict"] == "verified" for r in rows),
            "load_s": 4.0, "server_stop": {"pid": pid}}


def test_three_stints_aggregate_all_units(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    nothink = [_row("canary-nothink", f"K{i}", "verified" if i < 3 else "rejected", None if i < 3 else "harness")
               for i in range(7)]
    think_a = [_row("canary-think", f"K{i}", "rejected", "model-limitation") for i in range(4)]
    think_b = [_row("canary-think", f"K{i}", "rejected", "harness") for i in range(4, 6)]
    think_c = [_row("canary-think", "K6", "error", "harness")]
    (out / "results.jsonl").write_text("".join(json.dumps(r) + "\n" for r in nothink + think_a + think_b + think_c))
    # stints 1 and 2 were finalized by their own job.py process; stint 3 is this one
    S.finalize(out, {"phases": [_stint_phase("canary-nothink", nothink, 1), _stint_phase("canary-think", think_a, 1)]})
    S.finalize(out, {"phases": [_stint_phase("canary-think", think_b, 2)]})
    summary = {"row": "r", "phases": [_stint_phase("canary-think", think_c, 3)]}
    S.finalize(out, summary, ["canary-nothink", "canary-think"])
    ph = {p["arm"]: p for p in summary["phases"]}
    assert ph["canary-nothink"]["tasks"] == 7 and ph["canary-nothink"]["verified"] == 3
    assert ph["canary-think"]["tasks"] == 7 and ph["canary-think"]["verified"] == 0
    assert ph["canary-think"]["failure_classes"] == {"harness": 3, "model-limitation": 4}
    assert ph["canary-think"]["stints"] == 3
    assert summary["total"] == {"tasks": 14, "verified": 3, "verified_rate": 0.21,
                                "failure_classes": {"harness": 7, "model-limitation": 4}}
    assert len(summary["stint_phases"]) == 4
    # idempotent: finalize twice (main() + finally) records no duplicate stint
    S.finalize(out, summary, ["canary-nothink", "canary-think"])
    assert len(S.read_rows(out / "stints.jsonl")) == 4 and summary["total"]["tasks"] == 14


def test_rerun_of_a_unit_replaces_earlier_row():
    rows = [_row("a", "K1", "error", "harness"), _row("a", "K1", "verified")]
    agg = S.rollup(rows)
    assert agg["total"]["tasks"] == 1 and agg["total"]["verified"] == 1


def test_cli_repairs_run_dir_and_keeps_last_stint_copy(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    rows = [_row("canary-nothink", "K1", "verified"), _row("canary-think", "K1", "error", "harness")]
    (out / "results.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    (out / "RESULT.json").write_text(json.dumps({"row": "r", "final": True,
                                                 "phases": [_stint_phase("canary-think", rows[1:], 9)]}))
    (tmp_path / "CONFIG.json").write_text(json.dumps({"arms": [{"name": "canary-nothink"}, {"name": "canary-think"}]}))
    assert S.main([str(tmp_path)]) == 0
    res = json.loads((out / "RESULT.json").read_text())
    assert [p["arm"] for p in res["phases"]] == ["canary-nothink", "canary-think"]
    assert res["total"]["tasks"] == 2 and res["final"] is True
    assert json.loads((out / "RESULT.last-stint.json").read_text())["phases"][0]["tasks"] == 1
