#!/usr/bin/env python3
"""CS-11 analysis. Reads raw/arms.jsonl, writes results.json + RESULTS.md. Rules are in PREDECLARED.md (authoritative).
Optional, once CS-9 exists:  analyze.py --cs9-loss 0.12 --cs9-speech-ok yes|no   (fraction of per-slot tok/s lost by the GPU LLM tenant, p95)."""
import argparse, json, os, statistics as S, sys
D = os.environ.get("CS11_DIR", "/mnt/raid0/llm/tmp/cs11-20261022")
KVU = {"architect_general": {"F": [31.11, 31.3], "P": [22.99, 24.47]}, "frontdoor": {"F": [36.79], "P": None}}  # KVU-11b, tok/s
ap = argparse.ArgumentParser(); ap.add_argument("--cs9-loss", type=float); ap.add_argument("--cs9-speech-ok", choices=["yes", "no"])
a = ap.parse_args()
arms = [json.loads(l) for l in open(f"{D}/raw/arms.jsonl") if l.strip()]
arms = [x for x in arms if x.get("kind") == "arm"]
res = {"protocol_id": "cs11-cpu-partition-v1", "metric_direction": "higher_is_better (tok/s); loss positive = partition slower", "unit": "percent of the arm-mean decode tok/s (arm = mean of K=4 requests of 500 tokens); loss = 1 - P/F, positive = partition slower", "roles": {}}
for role in ("frontdoor", "architect_general"):
    rows = {x["idx"]: x for x in arms if x["role"] == role}
    def v(i):
        x = rows.get(i)
        return x["arm_mean_tok_s"] if x and not x.get("error") and (x.get("n_good") or 0) >= 3 else None
    F = {i: v(i) for i in (1, 3, 5, 7)}; P = {i: v(i) for i in (2, 4, 6)}
    Fv = [x for x in F.values() if x]; r = {"F_tok_s": F, "P_tok_s": P}
    if len(Fv) >= 2:
        r["noise_floor_pct"] = round(100 * (max(Fv) - min(Fv)) / S.mean(Fv), 2)  # F-arm range / mean, unit: % of arm-mean tok/s
        r["F_mean"] = round(S.mean(Fv), 3)
    losses = {}
    for i, p in P.items():
        nb = [F.get(i - 1), F.get(i + 1)]
        if p and all(nb): losses[i] = round(1 - p / S.mean(nb), 4)
    r["pair_loss"] = losses
    cv = [100 * S.pstdev([q["tok_s"] for q in rows[i]["reqs"] if q.get("tok_s")]) / S.mean([q["tok_s"] for q in rows[i]["reqs"] if q.get("tok_s")])
          for i in rows if rows[i].get("reqs") and len([q for q in rows[i]["reqs"] if q.get("tok_s")]) >= 2]
    r["within_arm_cv_pct_median"] = round(S.median(cv), 2) if cv else None
    r["draft_acc_rate"] = {i: rows[i].get("arm_draft_acc_rate") for i in sorted(rows)}
    r["flags"] = {i: [k for k in ("pre_busy_flag", "error") if rows[i].get(k)] for i in rows if any(rows[i].get(k) for k in ("pre_busy_flag", "error"))}
    if losses and "noise_floor_pct" in r:
        nf = r["noise_floor_pct"] / 100; med = S.median(losses.values())
        r["median_loss"] = round(med, 4)
        r["resolved"] = bool(len(losses) >= 3 and all(l > nf for l in losses.values()) and med >= 2 * nf)
        r["pair_sign_agree"] = all(l > 0 for l in losses.values()) or all(l < 0 for l in losses.values())
    if "F_mean" in r and KVU[role]["F"]:
        r["F_vs_KVU11b_pct"] = round(100 * (r["F_mean"] / S.mean(KVU[role]["F"]) - 1), 1)
    res["roles"][role] = r
ls = [r["median_loss"] for r in res["roles"].values() if "median_loss" in r]
if len(ls) == 2:
    res["C_cpu_combined"] = round(S.mean(ls), 4); res["C_cpu_max"] = round(max(ls), 4)
    res["margin_m"] = round(max(r["noise_floor_pct"] for r in res["roles"].values()) / 100, 4)
    res["both_resolved"] = all(r.get("resolved") for r in res["roles"].values())
    if a.cs9_loss is not None:
        G, C, m = a.cs9_loss, res["C_cpu_combined"], res["margin_m"]
        if a.cs9_speech_ok == "no": res["verdict"] = "GPU co-residency fails the speech SLO in CS-9: the cost comparison is not applicable; operator decision with both numbers."
        elif G + m <= C: res["verdict"] = "R1: GPU co-residency is cheaper than the CPU partition; no speech component needs CPU placement."
        elif C + m <= G and res["both_resolved"]: res["verdict"] = "R2: CPU partition is cheaper on LLM cost, but TTS acceptance is unmet in KVU-11b; escalate with a speech co-load re-measure before any CPU placement."
        else: res["verdict"] = "R3: within margin; default GPU. Report both numbers."
json.dump(res, open(f"{D}/results.json", "w"), indent=1)
md = ["# CS-11 results (auto-generated; see PREDECLARED.md)", "", res["unit"], ""]
for role, r in res["roles"].items():
    md += [f"## {role}", f"- F tok/s: {r['F_tok_s']}  P tok/s: {r['P_tok_s']}", f"- noise floor: {r.get('noise_floor_pct')} % of arm-mean tok/s; within-arm CV median {r.get('within_arm_cv_pct_median')} %",
           f"- pair loss: {r['pair_loss']}  median {r.get('median_loss')}  resolved={r.get('resolved')}  sign-agree={r.get('pair_sign_agree')}",
           f"- F vs KVU-11b full-host: {r.get('F_vs_KVU11b_pct')} %   draft acceptance by arm: {r['draft_acc_rate']}   flags: {r['flags']}", ""]
md += [f"C_cpu_combined={res.get('C_cpu_combined')} C_cpu_max={res.get('C_cpu_max')} margin={res.get('margin_m')} both_resolved={res.get('both_resolved')}", f"verdict: {res.get('verdict', 'pending CS-9 (rerun with --cs9-loss)')}"]
open(f"{D}/RESULTS.md", "w").write("\n".join(md) + "\n")
print("\n".join(md))
