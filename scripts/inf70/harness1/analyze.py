#!/usr/bin/env python3
"""INF-70 HARNESS-1 analysis. Same token-weighted metric as champion3/analyze.py
(sum pred_n / sum pred_ms, pred_n>=16 floor) so the numbers are directly comparable."""
import glob, json, os, re, statistics as st, sys, itertools
R = os.environ.get("INF70_RUNS", "/mnt/raid0/llm/tmp/inf70/agents/harness1/runs")
FLOOR = 16

def load(l, root=R):
    p = f"{root}/{l}.rows.jsonl"
    return [json.loads(x) for x in open(p) if x.strip()] if os.path.exists(p) else None

def dec(rows): return [r for r in rows if (r.get("pred_n") or 0) >= FLOOR and r.get("pred_ms")]

def tw(rows, num="pred_n", den="pred_ms"):
    n = sum(r[num] for r in rows); d = sum(r[den] for r in rows)/1000.0
    return n/d if d else None

def summ(l, root=R):
    rows = load(l, root)
    if not rows: return None
    d = dec(rows)
    reasons = {}
    for r in rows: reasons[r.get("verdict","?")] = reasons.get(r.get("verdict","?"),0)+1
    pre = [r for r in rows if r.get("prompt_ms") and r.get("prompt_n")]
    return dict(label=l, n=len(rows), n_dec=len(d), tw_tps=round(tw(d),4),
                ms_per_tok=round(1000.0/tw(d),3),
                pp=round(tw(pre,"prompt_n","prompt_ms"),2) if pre else None, reasons=reasons)

def noise(labels, key="tw_tps", root=R):
    """Autokernel-style A/A floor: p95 of |a-b|/mean over every unordered pair."""
    vals = [(l, summ(l, root)) for l in labels]
    vals = [(l, s[key]) for l, s in vals if s]
    if len(vals) < 2: return None
    v = [x for _, x in vals]
    pairs = sorted(abs(a-b)/((a+b)/2)*100 for a, b in itertools.combinations(v, 2))
    idx = min(len(pairs)-1, int(round(0.95*(len(pairs)-1))))
    return dict(labels=[l for l, _ in vals], key=key, n=len(v),
                values=[round(x,4) for x in v],
                mean=round(st.mean(v),4), sd=round(st.pstdev(v),4),
                cv_pct=round(100*st.pstdev(v)/st.mean(v),3),
                spread_pct=round(100*(max(v)-min(v))/st.mean(v),3),
                n_pairs=len(pairs), pair_p95_pct=round(pairs[idx],3),
                pair_median_pct=round(st.median(pairs),3), pair_max_pct=round(max(pairs),3))

def sha_ident(a, b, roota=R, rootb=R):
    ra = {r["id"]: r.get("sha") for r in (load(a, roota) or [])}
    rb = {r["id"]: r.get("sha") for r in (load(b, rootb) or [])}
    ks = sorted(set(ra) & set(rb))
    return dict(a=a, b=b, n=len(ks), same=sum(1 for k in ks if ra[k]==rb[k]),
                diff=[k for k in ks if ra[k]!=rb[k]])

def timelines():
    out = []
    for p in sorted(glob.glob(f"{R}/*.timeline")):
        txt = open(p).read()
        for m in re.finditer(r"placement(?: GB n0\.\.n3| GB|.*?GB)[: ]+([\d. ]+)", txt):
            pass
        out.append((os.path.basename(p), txt))
    return out

if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "summ":
        for l in sys.argv[2:]:
            s = summ(l)
            if s: print(json.dumps(s))
    elif mode == "noise":
        print(json.dumps(noise(sys.argv[2:]), indent=1))
    elif mode == "sha":
        print(json.dumps(sha_ident(sys.argv[2], sys.argv[3])))
    elif mode == "sha_x":   # cross-directory: sha_x <labelA> <rootA> <labelB> <rootB>
        print(json.dumps(sha_ident(sys.argv[2], sys.argv[4], sys.argv[3], sys.argv[5])))

# --- contention conditioning (added after the A_OLD1 build-bypass finding) -----------------
def contention(label, root=R):
    """Per-arm foreign-load record, from the corrected sampler. `foreign_cpu_p50/max` are in
    units of one fully-busy core (100 = one core), summed across foreign processes per sample.
    A bench arm cannot detect a lock bypasser except by sampling, so this is the only handle
    on why two identical arms disagree."""
    import os, re
    p = f"{root}/{label}.coresidency"
    if not os.path.exists(p): return None
    samples, cur, heavy = [], None, {}
    for line in open(p, errors="replace"):
        if line.startswith("==="):
            if cur is not None: samples.append(cur)
            cur = 0.0; continue
        if "FOREIGN" not in line or cur is None: continue
        m = re.search(r"cpu=([0-9.]+)", line); n = re.search(r"comm=(\S+)", line)
        if not m: continue
        v = float(m.group(1)); cur += v
        if n and v >= 100: heavy[n.group(1)] = max(heavy.get(n.group(1), 0), v)
    if cur is not None: samples.append(cur)
    if not samples: return None
    samples.sort()
    return dict(label=label, n_samples=len(samples),
                foreign_cpu_p50=round(samples[len(samples)//2], 1),
                foreign_cpu_max=round(max(samples), 1),
                heavy=dict(sorted(heavy.items(), key=lambda kv: -kv[1])[:4]))

def conditioned(labels, root=R):
    out = []
    for l in labels:
        s = summ(l, root); c = contention(l, root)
        if not s: continue
        out.append(dict(label=l, tw_tps=s["tw_tps"], pp=s["pp"],
                        foreign_p50=(c or {}).get("foreign_cpu_p50"),
                        foreign_max=(c or {}).get("foreign_cpu_max"),
                        heavy=(c or {}).get("heavy")))
    return out
