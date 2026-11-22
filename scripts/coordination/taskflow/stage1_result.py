#!/usr/bin/env python3
"""Stage 1 canary RESULT.json aggregation across resumed stints.

A canary job (row dir job.py) can be stopped with rc=75 to yield its quarter and resumed later. Each stint starts
a fresh summary and appends a phase covering only the units that stint ran, so the final RESULT.json described the
last stint alone (r8c: "canary-think verified 0/1" over 14 task-runs). results.jsonl is append-only and holds every
unit, so it is the source of truth: `rollup()` rebuilds one phase per arm from it and keeps the per-stint phase
records under `stints`.

Use from job.py at the end of main() (and in its finally):
    from taskflow import stage1_result
    stage1_result.finalize(OUT, summary)
Repair an existing run dir:
    python3 scripts/coordination/taskflow/stage1_result.py <run_dir> [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

SUM_PERF = ("requests", "prompt_tokens_computed", "cached_tokens", "output_tokens", "reviewer_or_title_requests",
            "degenerate_aborts", "bad_tool_args_seen", "server_error_retries")
MEDIAN_PERF = ("decode_tok_s_median", "prefill_tok_s_median", "ttft_s_median", "draft_acceptance", "prefix_hit",
               "draft_acceptance_per_request_median")


def _pct(xs, q):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return None
    return round(xs[min(len(xs) - 1, int(q * len(xs)))], 1)


def read_rows(path: Path) -> list[dict]:
    rows = []
    if path.exists():
        for ln in path.read_text().splitlines():
            try:
                rows.append(json.loads(ln))
            except ValueError:
                continue
    return rows


def dedupe(rows: list[dict]) -> list[dict]:
    """One row per unit_id; a later row for the same unit (a re-run) replaces the earlier one."""
    by = {}
    for r in rows:
        by[r.get("unit_id") or f"{r.get('arm')}:{r.get('key')}"] = r
    return list(by.values())


def perf_rollup(rows: list[dict]) -> dict:
    perfs = [r.get("perf") or {} for r in rows]
    out = {k: sum(p.get(k) or 0 for p in perfs) for k in SUM_PERF}
    for k in MEDIAN_PERF:                         # median of per-task values (request-level detail is per stint)
        vals = [p.get(k) for p in perfs if p.get(k) is not None]
        out[k] = round(statistics.median(vals), 3) if vals else None
    dec_s = sum(p.get("decode_slot_s") or 0 for p in perfs)
    out["decode_slot_s"] = round(dec_s, 1)
    out["decode_only_aggregate_tok_s"] = round(out["output_tokens"] / dec_s, 1) if dec_s else None
    return out


def arm_phase(arm: str, rows: list[dict], stints: list[dict]) -> dict:
    ver = sum(r.get("verdict") == "verified" for r in rows)
    fails = [r.get("failure_class") for r in rows if r.get("verdict") != "verified"]
    reasons = [r.get("reason") for r in rows if r.get("verdict") != "verified"]
    walls = [r.get("wall_s") for r in rows]
    first = rows[0] if rows else {}
    return {
        "arm": arm, "np": first.get("np"), "thinking": first.get("thinking"),
        "tasks": len(rows), "verified": ver,
        "verified_rate": round(ver / len(rows), 2) if rows else None,
        "failure_classes": {k: fails.count(k) for k in sorted(set(fails), key=str)},
        "failure_reasons": {k: reasons.count(k) for k in sorted(set(reasons), key=str)},
        "task_wall_s_median": _pct(walls, .5), "task_wall_s_p90": _pct(walls, .9),
        "task_wall_s_sum": round(sum(w or 0 for w in walls), 1),
        "perf": perf_rollup(rows),
        "stints": len(stints), "source": "results.jsonl",
    }


def rollup(rows: list[dict], stint_phases: list[dict] | None = None, arm_order: list[str] | None = None) -> dict:
    rows = dedupe(rows)
    stint_phases = stint_phases or []
    arms = list(arm_order or [])
    for r in rows:
        if r.get("arm") not in arms:
            arms.append(r.get("arm"))
    phases = []
    for a in arms:
        ar = [r for r in rows if r.get("arm") == a]
        if ar:
            phases.append(arm_phase(a, ar, [p for p in stint_phases if p.get("arm") == a]))
    ver = sum(p["verified"] for p in phases)
    tot = sum(p["tasks"] for p in phases)
    fc: dict = {}
    for p in phases:
        for k, v in p["failure_classes"].items():
            fc[k] = fc.get(k, 0) + v
    return {"phases": phases, "stint_phases": stint_phases,
            "total": {"tasks": tot, "verified": ver, "verified_rate": round(ver / tot, 2) if tot else None,
                      "failure_classes": fc}}


NO_MODEL_WORK_REASONS = ("harness", "lane")


def no_model_work(r: dict) -> bool:
    """A unit that never reached the model (r8d: lane cap refusal, reason=lane, 0 requests)."""
    return r.get("reason") in NO_MODEL_WORK_REASONS


def harness_futility(stint_rows: list[dict]) -> bool:
    """r8d: a stint whose EVERY unit is harness/lane did no model work; its rows must not count as final results."""
    return bool(stint_rows) and all(no_model_work(r) for r in stint_rows)


def quarantine_stint(out_dir: Path, stint_rows: list[dict]) -> int:
    """Move this stint's no-model-work rows out of results.jsonl into harness-futility.jsonl so the units stay
    un-done (resumable) and check_complete cannot count them. Returns the number of rows moved."""
    out_dir = Path(out_dir)
    rp = out_dir / "results.jsonl"
    ids = {r.get("unit_id") for r in stint_rows if no_model_work(r)}
    if not ids or not rp.exists():
        return 0
    keep, moved = [], []
    for ln in rp.read_text().splitlines():
        try:
            r = json.loads(ln)
        except ValueError:
            keep.append(ln)
            continue
        (moved if r.get("unit_id") in ids and no_model_work(r) else keep).append(ln)
    with (out_dir / "harness-futility.jsonl").open("a") as f:
        for ln in moved:
            f.write(ln + "\n")
    tmp = rp.with_suffix(".jsonl.tmp")
    tmp.write_text("".join(ln + "\n" for ln in keep))
    tmp.replace(rp)
    return len(moved)


def units_done(rows: list[dict]) -> set[str]:
    """Units with a real (model-work) result; harness/lane refusals never count toward completion."""
    return {r.get("unit_id") for r in rows if r.get("unit_id") and not no_model_work(r)}


def finalize(out_dir: Path, summary: dict, arm_order: list[str] | None = None) -> dict:
    """Merge this stint's phases with earlier stints' (persisted in stints.jsonl) and rebuild summary from
    results.jsonl. Idempotent: a phase already recorded (same arm + server pid) is not appended twice."""
    out_dir = Path(out_dir)
    sp = out_dir / "stints.jsonl"
    prior = read_rows(sp)
    seen = {(p.get("arm"), (p.get("server_stop") or {}).get("pid"), p.get("load_s")) for p in prior}
    new = [p for p in summary.get("phases_this_stint", summary.get("phases", []))
           if p.get("source") != "results.jsonl"
           and (p.get("arm"), (p.get("server_stop") or {}).get("pid"), p.get("load_s")) not in seen]
    if new:
        with sp.open("a") as f:
            for p in new:
                f.write(json.dumps(p) + "\n")
    stints = prior + new
    agg = rollup(read_rows(out_dir / "results.jsonl"), stints, arm_order)
    summary["phases_this_stint"] = [p for p in summary.get("phases_this_stint", summary.get("phases", []))
                                    if p.get("source") != "results.jsonl"]
    summary.update(phases=agg["phases"], stint_phases=agg["stint_phases"], total=agg["total"],
                   aggregated_from="results.jsonl")
    return summary


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("run_dir", type=Path)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    out = a.run_dir / "out"
    rp = out / "RESULT.json"
    summary = json.loads(rp.read_text()) if rp.exists() else {}
    arm_order = None
    cfg = a.run_dir / "CONFIG.json"
    if cfg.exists():
        arm_order = [x["name"] for x in json.loads(cfg.read_text()).get("arms", [])]
    if not a.dry_run and rp.exists() and not (out / "RESULT.last-stint.json").exists():
        (out / "RESULT.last-stint.json").write_text(rp.read_text())
    if a.dry_run:
        summary = dict(summary)
        agg = rollup(read_rows(out / "results.jsonl"), summary.get("phases"), arm_order)
        print(json.dumps({"phases": [{k: p[k] for k in ("arm", "tasks", "verified", "failure_classes")}
                                     for p in agg["phases"]], "total": agg["total"]}, indent=1))
        return 0
    finalize(out, summary, arm_order)
    rp.write_text(json.dumps(summary, indent=1) + "\n")
    print(json.dumps(summary["total"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
