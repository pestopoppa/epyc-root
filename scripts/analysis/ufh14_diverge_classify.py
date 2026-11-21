#!/usr/bin/env python3
"""FR-UFH14-DIVERGE: classify divergent follow-on turns by first-divergence position.

Input: the F12 calls (wire.jsonl + server-8083-window.log under results/C{2,4}/cxf{1,12}/r{1,2}).
Divergent turn: cache_n == previous prompt - 4 (restore of the prompt-end-minus-4 checkpoint).
LCP (first-divergence position) = f_keep * slot_n_tokens (previous release of the chosen slot);
cross-checked against sim_best * new_prompt_len (the two must agree within the rounding of the
3-decimal ratios, else the pair is `unaligned` and excluded from the position table).
Resolution: +-0.0005 * denominator tokens, i.e. ~+-35 tokens at 70k. Reported, never hidden.
"""
import json, re, sys, pathlib

RESULTS = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "/mnt/raid0/llm/tmp/ds41-c95/results")
CALLS = [f"C{c}/{a}/r{r}" for c in (2, 4) for a in ("cxf1", "cxf12") for r in (1, 2)]
TAIL = 64  # tokens: tail bucket = divergence within the last TAIL tokens of the previous output (template boundary zone)
SEL = re.compile(r"slot get_availabl: id\s+(\d+) \| task -1 \| selected slot by LCP similarity, sim_best = ([\d.]+) .*f_keep = ([\d.]+)")
REL = re.compile(r"slot\s+release: id\s+(\d+) \| task \d+ \| stop processing: n_tokens = (\d+)")


def call_turns(d):
    wire = [json.loads(l) for l in open(d / "wire/wire.jsonl")]
    events = []  # ordered log events: ('rel', slot, n) | ('sel', slot, sim, fkeep)
    for line in open(d / "server-8083-window.log", errors="replace"):
        m = SEL.search(line)
        if m:
            events.append(("sel", int(m[1]), float(m[2]), float(m[3])))
            continue
        m = REL.search(line)
        if m:
            events.append(("rel", int(m[1]), int(m[2])))
    last_rel, sels = {}, []
    for e in events:
        if e[0] == "rel":
            last_rel[e[1]] = e[2]
        else:
            sels.append((e[1], e[2], e[3], last_rel.get(e[1])))
    return wire, sels


def main():
    rows, note = [], []
    for c in CALLS:
        wire, sels = call_turns(RESULTS / c)
        main_reqs = [w for w in wire if w.get("timings")]
        if len(sels) != len(main_reqs):
            note.append(f"{c}: {len(sels)} LCP selections vs {len(main_reqs)} requests (alignment by order may be off)")
        prev, j = None, 0
        for i, w in enumerate(main_reqs):
            t = w["timings"]
            P = t["cache_n"] + t["prompt_n"]
            if prev is not None:
                pP, pO, pN = prev
                div = t["cache_n"] == pP - 4
                sel = None
                # greedy alignment: take the next LCP selection only if its two LCP estimates agree for this request
                for k in range(j, min(j + 4, len(sels))):  # look-ahead 4: side requests add LCP lines
                    cand = sels[k]
                    if cand[3] and abs(cand[2] * cand[3] - cand[1] * P) <= 0.0006 * max(cand[3], P) + 2:
                        sel, j = cand, k + 1
                        break
                r = {"call": c, "turn": i + 1, "prompt": P, "cache_n": t["cache_n"], "prev_prompt": pP,
                     "prev_out_usage": pO, "prev_slot_n": pN, "divergent": div, "reprefill": t["prompt_n"]}
                if sel and sel[3]:
                    sl, sim, fk, slot_n = sel
                    lcp_f, lcp_s = fk * slot_n, sim * P
                    tol = 0.0006 * max(slot_n, P) + 2
                    r.update(lcp=round(lcp_f), aligned=abs(lcp_f - lcp_s) <= tol, lcp_tol=round(tol),
                             slot_n_at_sel=slot_n, ckpt_past_kept=(pN > pP + pO))
                rows.append(r)
            prev = (P, w["usage"]["output_tokens"], t["cache_n"] + t["prompt_n"] + t["predicted_n"])
    div = [r for r in rows if r["divergent"]]
    out = {"follow_on_turns": len(rows), "divergent": len(div), "notes": note}
    buckets = {"earlier_than_prev_output (in prior prompt)": [], "template_boundary_head (first 64 tokens of previous output / assistant header)": [], "inside_prev_output": [], "template_boundary_tail": [], "unlocated (no LCP selection line, LRU slot, or ratios disagree)": []}
    for r in div:
        if "lcp" not in r or not r["aligned"]:
            buckets["unlocated (no LCP selection line, LRU slot, or ratios disagree)"].append(r); continue
        D, P0, O = r["lcp"], r["prev_prompt"], r["prev_out_usage"]
        end = P0 + O
        if D < P0 - r["lcp_tol"]:
            buckets["earlier_than_prev_output (in prior prompt)"].append(r)
        elif D < P0 + max(TAIL, r["lcp_tol"]):
            buckets["template_boundary_head (first 64 tokens of previous output / assistant header)"].append(r)
        elif D >= end - max(TAIL, r["lcp_tol"]):
            buckets["template_boundary_tail"].append(r)
        else:
            buckets["inside_prev_output"].append(r)
    # replay saving of periodic generation-time checkpoints every N tokens counted from the previous prompt end
    sav = {}
    for N in (1024, 2048):
        tot = 0
        for r in div:
            if "lcp" in r and r["aligned"]:
                D, P0 = r["lcp"], r["prev_prompt"]
                tot += max(0, ((D - P0) // N) * N) if D > P0 else 0
        sav[str(N)] = tot
    out["periodic_ckpt_tokens_saved_located"] = sav
    out["reprefill_tokens_located"] = sum(r["reprefill"] for r in div if "lcp" in r and r["aligned"])
    out["buckets"] = {k: {"n": len(v), "reprefill_tokens": sum(x["reprefill"] for x in v)} for k, v in buckets.items()}
    # PFXC-A1 coverage: its end-of-generation checkpoint sits at slot_n (previous release). It restores a turn only if
    # LCP >= that position. Every divergent turn has LCP < slot_n by definition, so served = 0 unless unlocated.
    # served == 0 by construction for located turns (LCP < slot_n); the tail turns are within the LCP resolution of it.
    out["pfxc_a1_eog_serves_located"] = 0
    out["ckpt_past_kept_text"] = sum(1 for r in div if r.get("ckpt_past_kept"))
    out["inside_position_fraction_quartiles"] = None
    ins = [(r["lcp"] - r["prev_prompt"]) / max(1, r["prev_out_usage"]) for r in buckets["inside_prev_output"]]
    if ins:
        ins.sort(); n = len(ins)
        out["inside_position_fraction_quartiles"] = [round(ins[int(q * (n - 1))], 3) for q in (0, .25, .5, .75, 1)]
    json.dump({"summary": out, "divergent_rows": div}, open(sys.argv[2] if len(sys.argv) > 2 else "/dev/stdout", "w"), indent=1)


main()
