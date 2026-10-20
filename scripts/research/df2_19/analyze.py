#!/usr/bin/env python3
"""DF2-19 step 3: coverage / hit-rate tables, strata, unions, step simulation, verdict.  See PROTOCOL.md.
usage: analyze.py [--no-b]   (reads feat_ac.pkl and feat_b.pkl)"""
import csv, gzip, hashlib, itertools, json, os, pickle, sys, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import df2lib as L

SCR = "/mnt/raid0/llm/tmp/df2-19-20261020/"
OUT = SCR + "out/"
SEEDS = list(range(16))
CAL, HOLD = "C2", "C4"
HMINS = [1, 2, 3, 4, 5]
SMINS = [0.0, .1, .2, .3, .4, .5, .6, .7, .8, .9]
TOTMINS = [1, 2, 3, 5]


def load_turns(use_b=True):
    runs = L.load_runs()
    fac = pickle.load(open(SCR + "feat/feat_ac.pkl", "rb"))
    fb = pickle.load(open(SCR + "feat/feat_b.pkl", "rb")) if use_b else None
    turns, const = [], []
    for r in runs:
        for t in r["turns"]:
            key = (r["run"], t["turn"])
            base = {"run": r["run"], "group": r["group"], "turn": t["turn"], "recovered": t["recovered"],
                    "qwen_pred": t["qwen_pred"] or 0, "draft_n": t["draft_n"] or 0, "draft_acc": t["draft_acc"] or 0}
            f = fac["turns"].get(key)
            if f is None:
                const.append(base)
                continue
            d = dict(base)
            d.update(f)
            if fb is not None:
                d.update(fb["turns"][key])
            d["cls"] = t["cls"][t["scored"]]
            d["N"] = len(d["actual"])
            d["steps_meas"] = d["draft_n"] / L.BLK
            d["eligible"] = (t["recovered"] == "full" and d["draft_n"] > 0)
            if d["eligible"]:
                d["m"] = d["N"] / d["steps_meas"]
                d["abar"] = L.solve_q(d["m"])
            turns.append(d)
            if not d["eligible"]:
                const.append(base)
    return turns, const, fac["meta"]


# ------------------------------------------------------------------ arm arrays
def arm_prop_hit(d, spec):
    kind = spec[0]
    act = d["actual"]
    if kind == "a":
        return d[f"a{spec[1]}_prop"], d[f"a{spec[1]}_hit"]
    if kind == "b":
        _, hmin, smin = spec
        prop = (d["b_order"] >= hmin + 1) & (d["b_p3"][:, 0] >= smin) & (d["b_t3"][:, 0] >= 0)
        return prop, prop & (d["b_t3"][:, 0] == act)
    if kind in ("c", "cg"):
        _, hmin, smin, totmin = spec
        prop = (d[f"{kind}_order"] >= hmin + 1) & (d[f"{kind}_p3"][:, 0] >= smin) & (d[f"{kind}_tot"] >= totmin) & (d[f"{kind}_t3"][:, 0] >= 0)
        return prop, prop & (d[f"{kind}_t3"][:, 0] == act)
    raise ValueError(spec)


def merged(d, specs):
    prop = np.zeros(d["N"], bool)
    hit = np.zeros(d["N"], bool)
    for sp in specs:  # priority order
        p, h = arm_prop_hit(d, sp)
        take = p & ~prop
        hit[take] = h[take]
        prop |= p
    return prop, hit


# ------------------------------------------------------------------ simulation
def fit_overlap(turns, H):
    """Token-weighted regression abar_t = q_unc + (q_cov - q_unc) * c_t over eligible turns."""
    x = np.array([H[i].mean() for i in range(len(turns))])
    y = np.array([t["abar"] for t in turns])
    w = np.array([t["N"] for t in turns], float)
    xm, ym = np.average(x, weights=w), np.average(y, weights=w)
    var = np.average((x - xm) ** 2, weights=w)
    beta = np.average((x - xm) * (y - ym), weights=w) / var if var > 0 else 0.0
    alpha = ym - beta * xm
    q_unc, q_cov = float(np.clip(alpha, 0.0, 1.0)), float(np.clip(alpha + beta, 0.0, 1.0))
    return q_unc, q_cov, float(alpha), float(beta)


def acc_array(t, H, scenario, q_cov):
    if scenario == "indep":
        return np.full(t["N"], t["abar"])
    c = H.mean()
    qu = (t["abar"] - c * q_cov) / (1 - c) if c < 1 else t["abar"]
    qu = float(np.clip(qu, 0.0, 1.0))
    return np.where(H, q_cov, qu)


def sim_steps(turns, props, hits, accs, oracle, seeds=SEEDS):
    out = np.zeros(len(turns))
    for i, t in enumerate(turns):
        tk = int(hashlib.md5(f'{t["run"]}/{t["turn"]}'.encode()).hexdigest()[:6], 16)
        s = 0.0
        for sd in seeds:
            s += L.sim_turn(props[i], hits[i], accs[i], sd, tk, oracle)[1]
        out[i] = s / len(seeds)
    return out


def compare(turns, const, base_specs, cand_specs, scenario, oracle, q_fit_turns=None, fit=None, seeds=SEEDS, with_df=True):
    """Steps for baseline and candidate on `turns`.  H = union hit set of both.  Fit from q_fit_turns (calibration) if given."""
    n = len(turns)
    pb = [merged(t, base_specs) for t in turns]
    pc = [merged(t, cand_specs) for t in turns]
    H = [b[1] | c[1] for b, c in zip(pb, pc)]
    if fit is None:
        if scenario == "fit":
            fit = fit_overlap(turns if q_fit_turns is None else q_fit_turns,
                              H if q_fit_turns is None else [merged(t, base_specs)[1] | merged(t, cand_specs)[1] for t in q_fit_turns])
        else:
            fit = (None, None, None, None)
    q_cov = fit[1]
    accs = [acc_array(t, H[i], scenario, q_cov) for i, t in enumerate(turns)]
    s_base = sim_steps(turns, [p[0] for p in pb], [p[1] for p in pb], accs, oracle, seeds)
    s_cand = sim_steps(turns, [p[0] for p in pc], [p[1] for p in pc], accs, oracle, seeds)
    s_df = sim_steps(turns, [np.zeros(t["N"], bool) for t in turns], [np.zeros(t["N"], bool) for t in turns], accs, oracle, seeds) if with_df else None
    return s_base, s_cand, s_df, fit


def gains(turns, const_group, s_base, s_cand):
    U_steps = sum(c["draft_n"] / L.BLK for c in const_group)
    tot_base, tot_cand = s_base.sum(), s_cand.sum()
    return {"gain_diluted": (tot_base + U_steps) / (tot_cand + U_steps) - 1,
            "gain_undiluted": tot_base / tot_cand - 1,
            "tps_base": sum(t["N"] for t in turns) / tot_base, "tps_cand": sum(t["N"] for t in turns) / tot_cand}


def boot(turns, const_group, s_base, s_cand, nb=2000, seed=7):
    rng = np.random.default_rng(seed)
    U = sum(c["draft_n"] / L.BLK for c in const_group)
    n = len(turns)
    g = []
    for _ in range(nb):
        i = rng.integers(0, n, n)
        g.append((s_base[i].sum() + U) / (s_cand[i].sum() + U) - 1)
    return [float(np.percentile(g, 2.5)), float(np.percentile(g, 97.5))]


def choose_k(turns_cal):
    best = None
    for k in (6, 8, 12):
        specs = [("a", k)]
        pr = [merged(t, specs) for t in turns_cal]
        accs = [np.full(t["N"], t["abar"]) for t in turns_cal]
        s = sim_steps(turns_cal, [p[0] for p in pr], [p[1] for p in pr], accs, False, seeds=SEEDS[:8]).sum()
        if best is None or s < best[1]:
            best = (k, s)
    return best[0]


def choose_gate(turns_cal, const_cal, kind, ak, variant="c"):
    best, rows = None, []
    grid = [(h, s, 1) for h in HMINS for s in SMINS] if kind == "b" else [(h, s, tm) for h in HMINS for s in SMINS for tm in TOTMINS]
    for gcfg in grid:
        sp = (variant,) + gcfg if kind == "c" else ("b", gcfg[0], gcfg[1])
        s_base, s_cand, _, fit = compare(turns_cal, const_cal, [("a", ak)], [("a", ak), sp], "fit", False, seeds=SEEDS[:8], with_df=False)
        g = gains(turns_cal, const_cal, s_base, s_cand)["gain_diluted"]
        rows.append((gcfg, g))
        if best is None or g > best[1]:
            best = (gcfg, g)
    return best, rows


def evaluate(turns, const, cal, hold, use_b, log):
    T = {g: [t for t in turns if t["group"] == g and t["eligible"]] for g in (cal, hold)}
    C = {g: [c for c in const if c["group"] == g] for g in (cal, hold)}
    res = {"calibration_group": cal, "holdout_group": hold}
    ak = choose_k(T[cal])
    res["a_k_chosen_on_cal"] = ak
    arms = {"c": None, "cg": None}
    if use_b:
        arms["b"] = None
    out = {}
    for kind in (["b"] if use_b else []) + ["c", "cg"]:
        best, rows = choose_gate(T[cal], C[cal], kind if kind == "b" else "c", ak, variant=kind)
        gcfg = best[0]
        sp = ("b", gcfg[0], gcfg[1]) if kind == "b" else (kind,) + gcfg
        cell = {"gate_chosen_on_cal": list(gcfg), "cal_gain_diluted": best[1], "spec": list(map(str, sp)),
                "grid_top5": sorted(rows, key=lambda r: -r[1])[:5]}
        # fit from calibration, applied to holdout
        fit_cal = None
        s_b, s_c, _, fit_cal = compare(T[cal], C[cal], [("a", ak)], [("a", ak), sp], "fit", False, with_df=False)
        cell["fit_on_cal"] = {"q_unc": fit_cal[0], "q_cov": fit_cal[1], "alpha": fit_cal[2], "beta": fit_cal[3]}
        for scen in ("indep", "fit"):
            for oracle in (False, True):
                sb, sc, sdf, _ = compare(T[hold], C[hold], [("a", ak)], [("a", ak), sp], scen, oracle, fit=fit_cal if scen == "fit" else None)
                gg = gains(T[hold], C[hold], sb, sc)
                gg["ci95_diluted"] = boot(T[hold], C[hold], sb, sc)
                gg["dflash2_alone_tps_sim"] = sum(t["N"] for t in T[hold]) / sdf.sum()
                gg["dflash2_alone_tps_measured"] = sum(t["N"] for t in T[hold]) / sum(t["steps_meas"] for t in T[hold])
                gg["a_alone_vs_dflash2_alone"] = sdf.sum() / sb.sum() - 1
                cell[f"{scen}|{'oracle' if oracle else 'realistic'}"] = gg
                if scen == "fit" and not oracle:
                    per_run = {}
                    for rn in sorted({t["run"] for t in T[hold]}):
                        ix = [i for i, t in enumerate(T[hold]) if t["run"] == rn]
                        per_run[rn] = float(sb[ix].sum() / sc[ix].sum() - 1)
                    gg["per_run_undiluted"] = per_run
        # standalone X vs DFlash2-alone and vs a-alone (fit, realistic), plus union (a,c,b)
        out[kind] = cell
        log(f"[{cal}->{hold}] {kind} gate={gcfg} cal_gain={best[1]:+.4f} hold fit/realistic={cell['fit|realistic']['gain_diluted']:+.4f} indep/oracle={cell['indep|oracle']['gain_diluted']:+.4f}")
    res["arms"] = out
    return res


# ------------------------------------------------------------------ coverage tables
def pct(a, b):
    return float(a) / float(b) if b else None


def coverage_tables(turns, const, use_b):
    rows = {}
    for g in ("C2", "C4", "ALL"):
        ts = [t for t in turns if g == "ALL" or t["group"] == g]
        N = sum(t["N"] for t in ts)
        unrec = sum(c["qwen_pred"] for c in const if (g == "ALL" or c["group"] == g) and c["recovered"] in ("lost_compaction", "aborted", "none"))
        unrec_partial = sum(c["qwen_pred"] for c in const if (g == "ALL" or c["group"] == g) and c["recovered"] == "message_only")
        cat = lambda key: np.concatenate([t[key] for t in ts])
        act = cat("actual")
        cls = cat("cls")
        arms = {}
        for k in (6, 8, 12):
            arms[f"a{k}"] = {"prop": cat(f"a{k}_prop"), "hit1": cat(f"a{k}_hit"), "hit3": cat(f"a{k}_hit")}
        for nm in (["b"] if use_b else []) + ["c", "cg"]:
            t3 = np.concatenate([t[f"{nm}_t3"] for t in ts])
            order = cat(f"{nm}_order")
            arms[nm] = {"prop": (order > 0) & (t3[:, 0] >= 0), "hit1": t3[:, 0] == act, "hit3": (t3 == act[:, None]).any(axis=1), "order": order,
                        "p1": np.concatenate([t[f"{nm}_p3"] for t in ts])[:, 0]}
            if nm != "b":
                arms[nm]["tot"] = cat(f"{nm}_tot")
        # run>=3 coverage for a8
        def runs3(hit_by_turn):
            n3 = 0
            for h in hit_by_turn:
                if not h.any():
                    continue
                d = np.diff(np.concatenate([[0], h.astype(np.int8), [0]]))
                st, en = np.flatnonzero(d == 1), np.flatnonzero(d == -1)
                ln = en - st
                n3 += int(ln[ln >= 3].sum())
            return n3
        sec = {"scored_positions": int(N), "unrecovered_turn_qwen_tokens": int(unrec), "message_only_turn_qwen_tokens": int(unrec_partial)}
        for k in (6, 8, 12):
            sec[f"a{k}_runs3_coverage"] = pct(runs3([t[f"a{k}_hit"] for t in ts]), N)
        for nm, a in arms.items():
            sec[nm] = {"coverage": pct(a["prop"].sum(), N), "top1_hit_all": pct(a["hit1"].sum(), N), "top1_hit_given_cov": pct((a["hit1"] & a["prop"]).sum(), a["prop"].sum()),
                       "top3_hit_all": pct(a["hit3"].sum(), N)}
            by = {}
            for ci, cn in enumerate(L.CLS_NAMES):
                m = cls == ci
                by[cn] = {"n": int(m.sum()), "coverage": pct((a["prop"] & m).sum(), m.sum()), "top1_hit_all": pct((a["hit1"] & m).sum(), m.sum()),
                          "top3_hit_all": pct((a["hit3"] & m).sum(), m.sum())}
            sec[nm]["by_class"] = by
            if "order" in a:
                st = {}
                for o in range(2, 7):
                    m = a["order"] == o
                    st[f"order{o}"] = {"n": int(m.sum()), "top1_hit": pct((a["hit1"] & m).sum(), m.sum()), "top3_hit": pct((a["hit3"] & m).sum(), m.sum())}
                sec[nm]["by_order"] = st
                sb = {}
                for lo, hi in [(0, .2), (.2, .4), (.4, .6), (.6, .8), (.8, 1.01)]:
                    m = a["prop"] & (a["p1"] >= lo) & (a["p1"] < hi)
                    sb[f"p1[{lo},{min(hi,1.0)})"] = {"n": int(m.sum()), "top1_hit": pct((a["hit1"] & m).sum(), m.sum())}
                sec[nm]["by_top1_score"] = sb
            if "tot" in a:
                stt = {}
                for lo, hi in [(1, 2), (2, 3), (3, 5), (5, 10), (10, 25), (25, 10**12)]:
                    m = a["prop"] & (a["tot"] >= lo) & (a["tot"] < hi)
                    stt[f"count[{lo},{hi if hi<10**12 else 'inf'})"] = {"n": int(m.sum()), "top1_hit": pct((a["hit1"] & m).sum(), m.sum()), "top3_hit": pct((a["hit3"] & m).sum(), m.sum())}
                sec[nm]["by_history_count"] = stt
        # unions (any-correct, ungated; a at k=8)
        names = [n for n in ("a8", "b", "c") if n in arms]
        un = {}
        for r_ in range(2, len(names) + 1):
            for comb in itertools.combinations(names, r_):
                h1 = np.zeros(N, bool); h3 = np.zeros(N, bool)
                for nm in comb:
                    h1 |= arms[nm]["hit1"]; h3 |= arms[nm]["hit3"]
                un["+".join(comb)] = {"top1_any": pct(h1.sum(), N), "top3_any": pct(h3.sum(), N)}
        sec["unions_any_correct"] = un
        rows[g] = sec
    return rows


def write_csv(turns, use_b):
    p = OUT + "positions.csv.gz"
    with gzip.open(p, "wt", newline="") as f:
        w = csv.writer(f)
        hdr = ["run", "group", "turn", "pos", "class", "token", "a8_prop", "a8_hit", "c_order", "c_tot", "c_top1", "c_top2", "c_top3", "c_p1", "c_hit1", "c_hit3"]
        if use_b:
            hdr += ["b_order", "b_top1", "b_top2", "b_top3", "b_p1", "b_hit1", "b_hit3"]
        w.writerow(hdr)
        for t in turns:
            for i in range(t["N"]):
                row = [t["run"], t["group"], t["turn"], int(t["pos"][i]), L.CLS_NAMES[t["cls"][i]], int(t["actual"][i]), int(t["a8_prop"][i]), int(t["a8_hit"][i]),
                       int(t["c_order"][i]), int(t["c_tot"][i]), *map(int, t["c_t3"][i]), round(float(t["c_p3"][i][0]), 4), int(t["c_t3"][i][0] == t["actual"][i]), int((t["c_t3"][i] == t["actual"][i]).any())]
                if use_b:
                    row += [int(t["b_order"][i]), *map(int, t["b_t3"][i]), round(float(t["b_p3"][i][0]), 4), int(t["b_t3"][i][0] == t["actual"][i]), int((t["b_t3"][i] == t["actual"][i]).any())]
                w.writerow(row)
    return p


def main():
    use_b = "--no-b" not in sys.argv
    os.makedirs(OUT, exist_ok=True)
    t0 = time.time()
    logf = open(OUT + "analyze.log", "a")

    def log(s):
        s = f"{time.time()-t0:7.1f}s {s}"
        print(s, flush=True); logf.write(s + "\n"); logf.flush()

    turns, const, meta = load_turns(use_b)
    log(f"turns scored={len(turns)} eligible={sum(t['eligible'] for t in turns)} const(unrecovered/ineligible)={len(const)}")
    result = {"use_b": use_b, "meta": meta, "seeds": len(SEEDS)}
    result["coverage"] = coverage_tables(turns, const, use_b)
    log("coverage done")
    result["primary"] = evaluate(turns, const, CAL, HOLD, use_b, log)
    result["secondary_reverse"] = evaluate(turns, const, HOLD, CAL, use_b, log)
    # verdict (predeclared): primary, fit|realistic, diluted, point estimate >= +3.0% for (a+b) or (a+c)
    v = {}
    for kind in (["b"] if use_b else []) + ["c"]:
        v[kind] = result["primary"]["arms"][kind]["fit|realistic"]["gain_diluted"]
    result["verdict_inputs_fit_realistic_diluted"] = v
    result["verdict"] = "GO" if any(x >= 0.03 for x in v.values()) else "STOP"
    log(f"VERDICT {result['verdict']} {v}")
    json.dump(result, open(OUT + ("results.json" if use_b else "results_no_b.json"), "w"), indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o))
    if use_b:
        write_csv(turns, use_b)
    log("done")


if __name__ == "__main__":
    main()
