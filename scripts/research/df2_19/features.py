#!/usr/bin/env python3
"""DF2-19 step 2: per-position arm outputs.  usage: features.py {ac|b}
ac: arm (a) request-local (k=6,8,12) and arm (c) leave-prompt-group-out domain table (all / gen-only).
b : arm (b) 17 GB COUNT table, longest stored history, top-3.
Writes /mnt/raid0/llm/tmp/df2-19-20261020/feat/feat_<arm>.pkl  (single thread, no inference)."""
import hashlib, os, pickle, sys, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import df2lib as L

OUT = "/mnt/raid0/llm/tmp/df2-19-20261020/feat/"


def turn_ctx(t):
    ctx = np.concatenate([t["prompt"], t["gen"]]).astype(np.int32)
    s = len(t["prompt"])
    pos = s + np.flatnonzero(t["scored"])
    return ctx, s, pos


def corpus(runs, genonly):
    seen, parts = set(), []
    for r in runs:
        for toks, scored, cls in r["pieces"]:
            if genonly and not scored:
                continue
            h = hashlib.md5(toks.tobytes()).digest()
            if h in seen or len(toks) == 0:
                continue
            seen.add(h)
            parts.append(toks.astype(np.int64))
            parts.append(np.array([L.BOUND], np.int64))
    return np.concatenate(parts)


def main():
    arm = sys.argv[1]
    os.makedirs(OUT, exist_ok=True)
    runs = L.load_runs()
    res = {"arm": arm, "turns": {}, "meta": {}}
    t0 = time.time()
    if arm == "ac":
        groups = sorted({r["group"] for r in runs})
        tables = {}
        for g in groups:
            other = [r for r in runs if r["group"] != g]
            for go in (False, True):
                corp = corpus(other, go)
                tables[(g, go)] = L.DomainTable(corp)
                res["meta"][f"corpus_{g}_{'gen' if go else 'all'}_tokens"] = int(len(corp))
                print("built", g, go, len(corp), time.time() - t0, flush=True)
        for r in runs:
            g = r["group"]
            for t in r["turns"]:
                key = (r["run"], t["turn"])
                if len(t["gen"]) == 0 or not t["scored"].any():
                    continue
                ctx, s, pos = turn_ctx(t)
                d = {"actual": ctx[pos], "pos": pos - s}
                for k in (6, 8, 12):
                    prop, tok = L.local_lookup(ctx, s, k)
                    pp, tt = prop[pos - s], tok[pos - s]
                    d[f"a{k}_prop"] = pp
                    d[f"a{k}_hit"] = pp & (tt == d["actual"])
                hist, lens = L.windows(ctx, pos, 5)
                for go, nm in ((False, "c"), (True, "cg")):
                    order, t3, p3, tot = tables[(g, go)].query(hist, lens)
                    d[f"{nm}_order"], d[f"{nm}_t3"], d[f"{nm}_p3"], d[f"{nm}_tot"] = order, t3, p3, tot
                res["turns"][key] = d
            print(r["run"], "done", time.time() - t0, flush=True)
    else:
        tb = L.TableB()
        res["meta"]["orders"] = tb.orders
        for r in runs:
            for t in r["turns"]:
                if len(t["gen"]) == 0 or not t["scored"].any():
                    continue
                ctx, s, pos = turn_ctx(t)
                hist, lens = L.windows(ctx, pos, 5)
                order, t3, p3 = tb.query(hist, lens)
                res["turns"][(r["run"], t["turn"])] = {"b_order": order, "b_t3": t3, "b_p3": p3}
            print(r["run"], "done", time.time() - t0, flush=True)
    pickle.dump(res, open(OUT + f"feat_{arm}.pkl", "wb"), protocol=4)
    print("wrote", OUT + f"feat_{arm}.pkl")


if __name__ == "__main__":
    main()
