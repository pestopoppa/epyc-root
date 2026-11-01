#!/usr/bin/env python3
"""PB-QCOST-1 confirm + q-axis: MECHANICAL verdict per PREDECLARATION.md as amended by AMENDMENT-confirm-R.md (2026-10-24).
Reads <run dir>/pb_qcost_1.jsonl (all phases), keeps completed phases only, applies the predeclared rules, writes VERDICT.json.
Nothing here is tunable at read time.
  python3 -B verdict_q.py --out RUNDIR [--sibling-dir DIR] [--predeclaration PREDECLARATION.md] [--amendment AMENDMENT.md] [--write VERDICT.json]
Amendment A1 (path fix): job.sh passes --out <job>/out/run, but sibling_sampler.py writes <job>/out/sibling_summary.json and
  <job>/out/sibling_load.csv, i.e. into the PARENT of --out.  The 2026-10-23 verdict looked in --out itself, read null and could
  only grade INDICATIVE.  The sibling dir now defaults to --out's parent (override with --sibling-dir).
Amendment A2 (per-phase contention grade): the existing 5 % / 5 % bars on CPUs 88-95 are applied to each completed ub phase's own
  window as well as run-wide; the run is UNCONTENDED only if the run-wide bar AND every completed phase's bar AND every proof pass.
"""
import argparse, hashlib, json, statistics, sys
from datetime import datetime, timezone
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pb_qcost_1_q as P  # noqa: E402

TOL = "noise floor = train rmse of the NEW ub-512 interval refit, ms per server iteration"


def confirm(a: dict) -> dict:
    res = {}
    for n in P.NS:
        pn = a["per_n"][n]
        il, rl = pn["interval_level"], pn["request_level"]
        old, noise = P.OLD21[n], il["noise_floor_train_rmse_ms_per_iter"]
        r = {"all_lengths_have_3_reps": pn["all_lengths_have_3_reps"], "refit_request_heldout_mape_pct": rl["refit_heldout"].get("mape_pct"),
             "frozen_request_heldout_mape_pct": rl["frozen_heldout"].get("mape_pct"),
             "A_new": il["refit_intercept_ms_at_c0"], "A_old": old["A"], "B_new": il["refit_slope_ms_per_cached_token"], "B_old": old["B"],
             "noise_floor_ms_per_iter": noise, "refit_heldout_p99_abs_ms_per_iter": il["refit_model_heldout"].get("p99_abs"),
             "refit_heldout_p99_under_ms_per_iter": il["refit_model_heldout"].get("p99_under_prediction")}
        if not r["all_lengths_have_3_reps"] or r["refit_request_heldout_mape_pct"] is None or r["A_new"] is None:
            r["verdict"] = "INCOMPLETE"
        else:
            r["dA_ms"] = round(r["A_new"] - old["A"], 2)
            r["dB_times_Cref_ms"] = round((r["B_new"] - old["B"]) * P.C_REF, 2)
            r["mape_ok"] = r["refit_request_heldout_mape_pct"] <= P.PASS_MAPE
            r["coef_agree"] = abs(r["dA_ms"]) <= noise and abs(r["dB_times_Cref_ms"]) <= noise
            r["verdict"] = ("CONFIRMED" if r["mape_ok"] and r["coef_agree"] else
                            "REFIT_FROM_UNCONTENDED" if r["mape_ok"] else "FAIL_MAPE")
        res[n] = r
    v = [res[n]["verdict"] for n in P.NS]
    res["overall"] = ("CONFIRMED" if all(x == "CONFIRMED" for x in v) else "INCOMPLETE" if "INCOMPLETE" in v
                      else "FAIL_MAPE" if "FAIL_MAPE" in v else "REFIT_FROM_UNCONTENDED")
    return res


def proofs(out: Path, rows: list) -> dict:
    done_ubs = sorted({r["ub"] for r in rows if r.get("kind") == "phase_done"})
    res, ok = {}, True
    for ub in done_ubs:
        f = out / f"graphs_proof_ub{ub}.json"
        d = json.loads(f.read_text()) if f.exists() else {}
        good = (d.get("graphs") == "ON" and (d.get("own_pid_kfd_vram_mib_at_ready") or 0) > 0
                and d.get("HSA_OVERRIDE_CPU_AFFINITY_DEBUG_in_environ") == ["HSA_OVERRIDE_CPU_AFFINITY_DEBUG=0"])
        res[ub] = {"graphs": d.get("graphs"), "own_pid_vram_mib_ready": d.get("own_pid_kfd_vram_mib_at_ready"),
                   "hsa": d.get("HSA_OVERRIDE_CPU_AFFINITY_DEBUG_in_environ"), "ok": good}
        ok &= good
    return {"per_ub": res, "all_ok": bool(done_ubs) and ok}


# --- Amendment A2: per-phase sibling-load grade (same bars as PREDECLARATION section 2, applied per phase) -------------------
MEDIAN_BAR, GT25_FRAC_BAR, GT25 = 0.05, 0.05, 0.25
SAMPLE_S, WIN_SAMPLES, GAP_S = 5, 6, 15     # sibling_sampler.py: one sample per 5 s, 6 samples = one 30-s window


def sampler_windows(csv: Path) -> list:
    """Rebuild sibling_sampler.py's 30-s windows from its append-only CSV (epoch_s,busy_frac).  A gap > 15 s starts a new
    sampler run (one per grant, the CSV is appended); within a run, consecutive groups of 6 samples are one window (the sampler's
    own grouping; a trailing partial group is dropped, as the sampler drops it).  Window = (start_s, end_s, mean_busy_frac)."""
    if not csv.exists():
        return []
    pts = []
    for ln in csv.read_text().splitlines():
        a, _, b = ln.strip().partition(",")
        try:
            pts.append((float(a), float(b)))
        except ValueError:
            continue
    runs, cur = [], []
    for t, f in pts:
        if cur and t - cur[-1][0] > GAP_S:
            runs.append(cur); cur = []
        cur.append((t, f))
    if cur:
        runs.append(cur)
    wins = []
    for r in runs:
        for i in range(0, len(r) - WIN_SAMPLES + 1, WIN_SAMPLES):
            g = r[i:i + WIN_SAMPLES]
            wins.append((g[0][0] - SAMPLE_S, g[-1][0], statistics.fmean(x[1] for x in g)))
    return wins


def grade_windows(ws: list) -> dict:
    if not ws:
        return {"windows": 0, "median_busy_frac": None, "frac_windows_gt_25pct": None, "n_windows_gt_5pct": None,
                "max_busy_frac": None, "grade": "INDICATIVE", "why": "no sampler windows in this phase (fail-closed)"}
    v = [w[2] for w in ws]
    med, gt25 = statistics.median(v), sum(x > GT25 for x in v) / len(v)
    ok = med <= MEDIAN_BAR and gt25 <= GT25_FRAC_BAR
    return {"windows": len(v), "median_busy_frac": round(med, 4), "frac_windows_gt_25pct": round(gt25, 4),
            "n_windows_gt_5pct": sum(x > 0.05 for x in v), "max_busy_frac": round(max(v), 4),
            "grade": "UNCONTENDED" if ok else "INDICATIVE"}


def _tag_epoch(phase_id: str):
    """'ub512-20261023T191256Z' -> epoch seconds of the phase start (the driver stamps it when the phase begins, before load)."""
    try:
        return datetime.strptime(phase_id.split("-", 1)[1], "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc).timestamp()
    except (IndexError, ValueError):
        return None


def phase_spans(rows: list) -> dict:
    """Completed phases only: {phase_id: (ub, start_s, end_s)}; start = phase_id stamp (or the earliest row time of the phase),
    end = the phase_done row's t."""
    spans = {}
    for r in rows:
        if r.get("kind") == "phase_done" and r.get("phase_id"):
            pid = r["phase_id"]
            ts = [x.get("t_send") for x in rows if x.get("phase_id") == pid and x.get("kind") == "run" and x.get("t_send")]
            st = _tag_epoch(pid)
            if st is None and ts:
                st = min(ts)
            spans[pid] = (r["ub"], st, r.get("t"))
    return spans


def per_phase_grade(rows: list, sib_dir: Path) -> dict:
    """A window counts toward a phase if it OVERLAPS the phase span (a boundary window counts toward both: fail-closed)."""
    wins = sampler_windows(sib_dir / "sibling_load.csv")
    res = {}
    for pid, (ub, st, en) in sorted(phase_spans(rows).items(), key=lambda kv: kv[1][1] or 0):
        if st is None or en is None:
            g = grade_windows([]); g["why"] = "phase span unknown (fail-closed)"
        else:
            g = grade_windows([w for w in wins if w[0] < en and w[1] > st])
        g.update({"ub": ub, "phase_id": pid,
                  "span_utc": [datetime.fromtimestamp(x, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if x else None for x in (st, en)]})
        res[pid] = g
    return {"rule": "AMENDMENT-confirm-R A2: per completed phase, median 30-s busy fraction of CPUs 88-95 <= 5 % AND <= 5 % of "
                    "windows > 25 %; windows overlapping the phase span", "csv": str(sib_dir / "sibling_load.csv"),
            "sampler_windows_total": len(wins), "per_phase": res,
            "all_uncontended": bool(res) and all(g["grade"] == "UNCONTENDED" for g in res.values())}


def verdict(rows: list, out: Path, pre_sha: str | None = None, sib_dir: Path | None = None, amend_sha: str | None = None) -> dict:
    u = P.usable(rows)
    done = sorted({r["ub"] for r in rows if r.get("kind") == "phase_done"})
    base = P.analyse(u)
    c = confirm(base)
    q = P.analyse_q(u)
    pr = proofs(out, rows)
    c_final = c["overall"] if pr["all_ok"] or c["overall"] == "INCOMPLETE" else "INVALID_PROOF"
    qv = q["overall"] if pr["all_ok"] or q["overall"] == "INCOMPLETE" else "INVALID_PROOF"
    sib_dir = out.parent if sib_dir is None else sib_dir          # A1: the sampler writes into --out's parent
    sf = sib_dir / "sibling_summary.json"
    sib = json.loads(sf.read_text()) if sf.exists() else None
    grade_run = ("UNCONTENDED" if (sib and pr["all_ok"] and sib.get("median_busy_frac") is not None and sib["median_busy_frac"] <= 0.05
                                   and sib.get("frac_windows_gt_25pct", 1) <= 0.05) else "INDICATIVE")
    pp = per_phase_grade(rows, sib_dir)                            # A2
    grade = "UNCONTENDED" if grade_run == "UNCONTENDED" and pp["all_uncontended"] else "INDICATIVE"
    label = ("PB-QCOST-1 confirm " + c_final + "; q axis " + qv + "; grade " + grade) if done else "NOT_RUN"
    rec = {"phases_done": done, "confirm": c, "confirm_overall": c_final, "q_axis": q, "q_overall": qv, "proof": pr,
           "label": label, "grade": grade, "grade_run_level": grade_run, "sibling_per_phase": pp, "sibling_summary": sib,
           "sibling_summary_path": str(sf), "predeclaration_sha256": pre_sha, "amendment_sha256": amend_sha, "tolerance_def": TOL,
           "handoff_text": {"b_ms_per_token": {n: q["per_n"][n].get("coef") for n in P.NS},
                            "use": "KVU-16g-2 takes target-ms margins from confirm.<n>.refit_heldout_p99_under_ms_per_iter (n=4 is the conservative one)"}}
    return rec


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--predeclaration", default=str(HERE / "PREDECLARATION.md"))
    ap.add_argument("--amendment", default=str(HERE / "AMENDMENT-confirm-R.md"))
    ap.add_argument("--sibling-dir", default=None, help="dir holding sibling_summary.json + sibling_load.csv (default: --out's parent)")
    ap.add_argument("--write", default=None)
    a = ap.parse_args()
    out = Path(a.out)
    f = out / "pb_qcost_1.jsonl"
    rows = [json.loads(x) for x in f.read_text().splitlines()] if f.exists() else []
    pre, am = Path(a.predeclaration), Path(a.amendment)
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None  # noqa: E731
    rec = verdict(rows, out, sha(pre), Path(a.sibling_dir) if a.sibling_dir else None, sha(am))
    txt = json.dumps(rec, indent=1, default=str)
    if a.write:
        Path(a.write).write_text(txt + "\n")
    brief = {k: rec[k] for k in ("phases_done", "confirm_overall", "q_overall", "grade", "grade_run_level", "label", "predeclaration_sha256",
                                 "amendment_sha256")}
    brief["per_phase"] = {g["ub"]: g["grade"] for g in rec["sibling_per_phase"]["per_phase"].values()}
    print(json.dumps(brief))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
