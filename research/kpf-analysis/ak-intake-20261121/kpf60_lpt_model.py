#!/usr/bin/env python3
"""KPF-60-LPT-MODEL: model-free LPT cost model for HyPIC-style segment-parallel cold prefill.

Stdlib only. Run: python3 -I kpf60_lpt_model.py [--out KPF-60-LPT-MODEL.md]
Zero inference: every rate is read from the constants below; a rate that the KPF-60 P0 did not
measure is None and that (role, device) pair is EXCLUDED, never filled in.

Model (per role, prompt length L, k equal segments, seam window w, overhead multiplier m):
  baseline  T0 = L / r_home                       (single device = the role's served home device)
  parallel  segments (L/k each) are LPT-scheduled on uniform machines (device speeds = rates);
            T_par = makespan
                  + remote_transfer  (state of every segment not computed on the home device, serial, conservative)
                  + compose          (c_compose per segment, on the home device)
                  + seam recompute   ((k-1) * w tokens at the home device rate; HyPIC repairs the seams
                                      with the TRUE composed state, so this is on the critical path)
  cut = 1 - T_par / T0  (positive = faster).  Overheads (transfer+compose) are multiplied by m for sensitivity.
Helper-device rate is either measured (None => excluded) or swept parametrically as rho = r_helper_total / r_home
to give the BREAK-EVEN rho for a >= 20% cut. The parametric sweep is a requirement table, not a prediction.
"""
import argparse
import itertools

# ---------------- measured / sourced inputs ----------------
# KPF-60 P0 GPU harvest (kv-cache-program.md KPF-60 2026-10-27 harvest; artifacts/engineering/kpf60-gpu-crossover-20261102):
# Qwen3.8-27B Q8_0 on MI210, build gpu-20261020-dd3d9721c, llama-bench pp tok/s, f16 KV.
RATES = {
    # role -> device -> {prompt_len_bucket: tok/s} or None (UNMEASURED)
    "27B  (architect_critic / coder_escalation / ingest; MI210 :8083)": {
        "home": "mi210",
        "mi210": {"ub512": {2048: 839.42, 8192: 788.12}, "ub2048": {2048: 919.44, 8192: 867.36}},
        "cpu": None,   # P0 'INCLUDE_27B_CPU' reference stage not run
    },
    "35B-A3B  (frontdoor / worker_general; CPU 0-95 :8070 + halves)": {
        "home": "cpu",
        "cpu": None,   # P0 cpu_pp stage NOT harvested (kv-cache-program.md L1709: still needs the quiet slot)
        "mi210": None,  # P0 INCLUDE_35B_GPU optional stage not run; also does not fit beside the resident 27B
    },
    "Flash-Next UD-IQ4_XS  (architect_general; CPU 0-95 :8074)": {
        "home": "cpu",
        "cpu": None,   # cpu_pp not harvested
        "mi210": None,
    },
}
# Transfer sizes. 27B attn KV 65,536 B/token f16 is derived from pinned GGUF metadata (artifacts/engineering/kpf60-gpu-crossover-20261102).
# DN (A,B) per-chunk bytes and the other roles' bytes/token are DESIGN.md 2.2 estimates (27B ~100 MB/chunk, 35B ~38.5 MB, Flash-Next ~76 MB).
XFER = {
    "27B": dict(attn_per_tok=65536, dn_per_seg=100e6),
    "35B": dict(attn_per_tok=20500, dn_per_seg=38.5e6),
    "FN": dict(attn_per_tok=24600, dn_per_seg=76e6),
}
PCIE = 28.9e9                      # P0 measured H2D bytes/s (pinned == pageable within 0.2%)
C_COMPOSE = {"gpu": 1e-3, "cpu": 10e-3}   # DESIGN.md 2.2 upper bounds per placement, seconds
LENGTHS = [2048, 8192, 32768]      # >8192 is an EXTRAPOLATION of the pp8192 rate (attention cost grows; flagged in the note)
SEGS = [2, 3, 4, 8]
WS = [8, 64, 128]                  # seam window sweep (HyPIC default 8, in-house W=64, HyPIC's too-large 128)
MULTS = [1.0, 3.0, 10.0]           # overhead (transfer+compose) sensitivity multipliers
NCPU_WORKERS = 2                   # current production halves 2x48t; split of the whole-CPU rate is equal
THRESH = 0.20


def lpt_makespan(seg_len, speeds):
    """LPT on uniform machines: segments sorted desc, each to the machine with the earliest finish."""
    load = [0.0] * len(speeds)
    assign = [[] for _ in speeds]
    for s in sorted(seg_len, reverse=True):
        j = min(range(len(speeds)), key=lambda i: load[i] + s / speeds[i])
        load[j] += s / speeds[j]
        assign[j].append(s)
    return max(load), assign


def t_parallel(L, k, w, m, r_home, helpers, home, xk):
    """helpers: list of helper-device rates (tok/s). Home device is machine 0."""
    seg = [L / k] * k
    speeds = [r_home] + list(helpers)
    mk, assign = lpt_makespan(seg, speeds)
    remote = sum(len(a) for a in assign[1:])
    remote_tokens = sum(sum(a) for a in assign[1:])
    x = XFER[xk]
    xfer = (remote_tokens * x["attn_per_tok"] + remote * x["dn_per_seg"]) / PCIE
    comp = k * C_COMPOSE["gpu" if home == "mi210" else "cpu"]
    seam = (k - 1) * w / r_home
    return mk + m * (xfer + comp) + seam, remote


def best_cut(L, w, m, r_home, helpers, home, xk):
    best = (-9.9, None, 0)
    t0 = L / r_home
    for k in SEGS:
        t, rem = t_parallel(L, k, w, m, r_home, helpers, home, xk)
        c = 1 - t / t0
        if c > best[0]:
            best = (c, k, rem)
    return best


def breakeven_rho(L, w, m, home, xk, n_help):
    """Smallest rho = (total helper rate)/(home rate) for a >= THRESH cut, best k; None if > 64 or never."""
    lo, hi = 0.0, 64.0
    f = lambda rho: best_cut(L, w, m, 1.0 * 1000, [rho * 1000 / n_help] * n_help, home, xk)[0]
    if f(hi) < THRESH:
        return None
    for _ in range(60):
        mid = (lo + hi) / 2
        if f(mid) >= THRESH:
            hi = mid
        else:
            lo = mid
    return hi


def rate_for(entry, dev, L, shape="ub512"):
    d = entry.get(dev)
    if d is None:
        return None
    t = d[shape]
    return t[2048] if L <= 2048 else t[8192]   # nearest measured bucket; 32768 reuses pp8192 (extrapolated)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    out = []
    P = out.append

    P("## 1. Rates actually available (KPF-60 P0) and what each served role gets\n")
    P("| role | home device | home rate (tok/s) | other-device rate | status |")
    P("|---|---|---|---|---|")
    for role, e in RATES.items():
        home = e["home"]
        hr = rate_for(e, home, 2048)
        if hr is None:
            P(f"| {role} | {home} | **MISSING** | **MISSING** | EXCLUDED from the prediction table; break-even table only |")
        else:
            P(f"| {role} | {home} | {rate_for(e, home, 2048):.0f} (pp2048) / {rate_for(e, home, 8192):.0f} (pp8192), ub512 | CPU **MISSING** | home-only: no second device with a rate, predicted cut = none |")

    P("\n## 2. Predicted cold-TTFT change from the MEASURED rates only\n")
    P("A parallel schedule needs at least two devices with a measured rate for the same role. Per role:\n")
    P("| role | devices with measured rate | L | best k | T0 (s) | T_par (s) | predicted cut |")
    P("|---|---|---|---|---|---|---|")
    for role, e in RATES.items():
        home = e["home"]
        xk = "27B" if role.startswith("27B") else ("35B" if role.startswith("35B") else "FN")
        for L in LENGTHS:
            r = rate_for(e, home, L)
            if r is None:
                P(f"| {role} | none | {L} | - | - | - | **excluded (home rate missing)** |")
                continue
            helpers = [rate_for(e, d, L) for d in ("mi210", "cpu") if d != home and rate_for(e, d, L) is not None]
            if not helpers:
                # single device: segment-parallel on one device only adds seam + compose overhead
                t0 = L / r
                t, _ = t_parallel(L, 2, 64, 1.0, r, [], home, xk)
                P(f"| {role} | {home} only | {L}{'*' if L > 8192 else ''} | 1 (no helper) | {t0:.2f} | {t0:.2f} | **0% (no second measured device; k>1 on one device is {100*(1-t/t0):.1f}% at w=64)** |")
            else:
                c, k, rem = best_cut(L, 64, 1.0, r, helpers, home, xk)
                P(f"| {role} | {home}+helper | {L} | {k} | {L/r:.2f} | {L/r*(1-c):.2f} | {100*c:.1f}% |")
    P("\n`*` pp>8192 reuses the pp8192 rate (extrapolation; true rate is lower, which only raises the baseline).\n")

    P("## 3. Requirement table (parametric, NOT a prediction): helper rate needed for a >= 20% cut\n")
    P(f"rho = total helper rate / home-device rate; helpers = {NCPU_WORKERS} equal workers; best k in {SEGS}; ")
    P("overhead multiplier m scales transfer+compose. Cells: minimum rho (\"-\" = unreachable even at rho=64).\n")
    P("| home | L | w | m=1 | m=3 | m=10 |")
    P("|---|---|---|---|---|---|")
    for home, xk in (("mi210", "27B"), ("cpu", "35B")):
        for L, w in itertools.product(LENGTHS, WS):
            cells = []
            for m in MULTS:
                b = breakeven_rho(L, w, m, home, xk, NCPU_WORKERS)
                cells.append("-" if b is None else f"{b:.3f}")
            P(f"| {home} (xfer={xk}) | {L} | {w} | " + " | ".join(cells) + " |")
    P("")
    P("Reading: with ideal splitting and negligible overhead the cut is rho/(1+rho), so 20% needs rho >= 0.25 (helpers together at least 1/4 of the home device). ")
    P("Seam recompute (k-1)*w tokens at the home rate and compose/transfer overheads raise it; the table gives the figure per w and m.\n")

    P("## 4. Sensitivity of the measured 27B row to the seam/ubatch choice\n")
    P("Home-only baseline at ub2048 instead of ub512 changes T0 by about 9-10% (919 vs 839 tok/s at pp2048). Because no helper rate exists, the cut stays 0%.\n")

    txt = "\n".join(out)
    if a.out:
        with open(a.out, "w") as f:
            f.write(txt + "\n")
    print(txt)


if __name__ == "__main__":
    main()
