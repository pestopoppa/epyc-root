#!/usr/bin/env python3
"""EXP-01 planned look. look.py R A B -> one look unit (pair tg ratio, preliminary band, stop verdict).
look.py R SUMMARY SUMMARY WALL -> pilot outputs: duration, variance, capture completeness, consumer coverage."""
import json, statistics as st, sys

R = sys.argv[1]
rows = [json.loads(l) for l in open(R) if l.strip()]
speed = [r for r in rows if r.get("kind") == "speed" and r.get("rc") == 0 and "tg" in r]


def arm(a):
    return [r["tg"] for r in speed if r["arm"] == a]


def pair(a, b):
    xa, xb = arm(a), arm(b)
    d = {"pair": f"{b}/{a}", "n": [len(xa), len(xb)]}
    if len(xa) < 2 or len(xb) < 2:
        d["stop"] = "continue"; return d
    ma, mb, sa, sb = st.mean(xa), st.mean(xb), st.stdev(xa), st.stdev(xb)
    ratio = mb / ma
    half = 2 * ((sa ** 2 / len(xa) + sb ** 2 / len(xb)) ** 0.5) / ma
    lo, hi = ratio - half, ratio + half
    stop = "answer-above" if lo > 1.00 else ("futility" if hi < 0.95 else "continue")
    d.update(ratio=round(ratio, 4), band=[round(lo, 4), round(hi, 4)], sd=[round(sa, 3), round(sb, 3)],
             mean=[round(ma, 3), round(mb, 3)], rule=">=0.95 tg128 ratio (STEP3/T3; decided only by the full paired set)",
             stop="answer" if stop == "answer-above" else stop,
             label="operational pilot look (exploratory/decision-support), never a gate result")
    return d


a, b = sys.argv[2], sys.argv[3]
if a != "SUMMARY":
    d = pair(a, b); d["unit"] = f"look-{a}-{b}"; d["kind"] = "look"
    print(json.dumps(d)); sys.exit(0)

val = next((r for r in reversed(rows) if r.get("unit") == "validity"), {})
arms = ["Q4KM", "IQ4KT", "IQ2XXS", "IQ2KT"]
durs = {x: [r["duration_s"] for r in speed if r["arm"] == x] for x in arms}
var = {x: (round(st.stdev(arm(x)), 3) if len(arm(x)) > 1 else None) for x in arms}
fields = ("tg", "pp", "gguf", "build_commit", "duration_s")
complete = {x: (sum(all(k in r for k in fields) for r in speed if r["arm"] == x), int(__import__("os").environ.get("LAUNCHES", "3"))) for x in arms}
qual = [r for r in rows if r.get("kind") == "quality" and "correct" in r]
pairs = {p: pair(*p.split(":")) for p in ("Q4KM:IQ4KT", "IQ2XXS:IQ2KT")}
mech = any("KT" in str(r.get("type_k", "")).upper() for r in speed if r["arm"] in ("IQ4KT", "IQ2KT"))
cov = {
    "STEP2/T2 (report)": "partial: speed slice" if pairs["Q4KM:IQ4KT"].get("ratio") else "none",
    "STEP3/T3 (>=0.95 AND paired flips)": ("futility-indicated (operational, gate open)" if pairs["Q4KM:IQ4KT"].get("stop") == "futility"
                                          else "not answerable by pilot (needs full paired set + quality pass)"),
}
print(json.dumps({"wall_s": int(sys.argv[4]) if len(sys.argv) > 4 else None, "validity_ok": val.get("ok"), "why": val.get("why"),
                  "fixture": (val.get("instrument") or {}).get("fixture"), "duration_per_launch_s": durs, "variance_sd_tg": var,
                  "aa_spread_control_Q4KM": arm("Q4KM"), "capture_completeness": complete, "quality_items_scored": len(qual),
                  "mechanism_selected": mech, "looks": pairs, "consumer_coverage": cov,
                  "decision_hint": "REVISE" if not val.get("ok") or not mech else "owner review: EXPAND with n from observed sd"}, indent=1))
