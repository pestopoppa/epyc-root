#!/usr/bin/env python3
"""M4.2b mechanical verdict, PAIRED design (AMENDMENT-M4.2b-paired.md, operator decision 2026-10-24 "Pair within one load").
Pure stdlib. Supersedes the 05fa4ef9... verdict.py of PREDECLARATION.md for load validity clause 5 and the C2 rule.

  verdict.py --out DIR [--prior FILE] [--write FILE]   reads DIR/loads.jsonl (one line per load, written by job.sh) and each
                                                        load's DIR/<load>/pb_hol_1.jsonl; C1/C3 copied from the pinned M4.2 VERDICT.json
  verdict.py --out DIR --check-load N                  job.sh: 'VALID', 'VALID FLAG: <why>' or 'INVALID: <reasons>' for load N
  verdict.py --selftest                                synthetic windows; rc 0 only if every case classifies as predeclared

C2 (AMENDMENT section 3):
  per VALID load L: C2_L = median(valid B short TTFT) / median(valid A short TTFT)   (the M4.2a quantity, unrounded here);
  adjacent pairs = consecutive VALID loads in execution order whose roles differ (ABAB -> 3 pairs: CH1-M4a, M4a-CH2, CH2-M4b);
  per pair p = C2_candidate / C2_champion; pooled paired ratio P = geometric mean of the p over every adjacent pair;
  C2_paired = round(22.05 x P, 3), judged against the UNCHANGED band with the M4.2a comparison code:
      22.05 x 0.9 <= C2_paired <= 22.05 x 1.1      (identically: 0.9 <= P <= 1.1)
  inside -> PASS (window clean) or PASS_WINDOW_DRIFT (any pair drift-flagged, or the champion's own pooled C2 outside the band);
  below -> FAIL_LOW, above -> FAIL_HIGH; NOT_MEASURED with < 2 valid loads of either binary or < 2 adjacent pairs.
Load validity (PREDECLARATION section 3 clauses 1-4 and 6, unchanged): harness complete; proofs (own port, graphs ON + HSA knob from
environ, residency >= 40 GiB own-pid, binary sha = the role's store sha); own-pid VRAM peak from the job watcher NON-NULL and <= the
60 GiB guard, no trip; >= 2 valid A and >= 2 valid B reps (M4.2a clause-3 predicate, unchanged); one window id for every load.
Clause 5 (C-solo drift, median(end 3) - median(start 3) > 2.8 ms, or C-solo not measurable) is a per-load FLAG that marks every
pair the load is in; it never voids a load or a pair.
"""
import argparse, hashlib, json, math, statistics, sys, tempfile
from pathlib import Path

MIN_VALID = 2                      # valid A and valid B reps per load
MIN_LOADS = 2                      # valid loads per binary
MIN_PAIRS = 2                      # adjacent champion/candidate pairs
MIN_COLLIDE_FRAC = 0.40
C_REPS = 3                         # solo shorts at each end of a load
PBHOL1_C = (278.4, 281.2)          # PB-HOL-1 C-solo (runs/20261021T160010Z), the ONLY C-solo values PB-HOL-1 has
DRIFT_BAR_MS = round(max(PBHOL1_C) - min(PBHOL1_C), 3)   # 2.8 ms (task text: "the C-solo spread of PB-HOL-1"): a FLAG now
VRAM_GUARD_MIB = 61440
RES_MIN_GIB = 40.0
ROLE_SHA = {"champion": "f0fe65c83f397dae0f40cb2bbf15223bef9be3df455f338409d5037699093882",    # gpu-20261023-141e4bcf5-lbh
            "candidate": "901743a0fc26bc2b4e9cfcabe3c3f8d46c9cbd7d6249e088f41ba2af417e3d90"}   # gpu-20261023-c6ca031ac-m4 (= M4.1)
ROLE_PHASE = {"champion": "off512ch", "candidate": "off512"}
REF_RATIO, REF_TOL = 22.05, 0.10   # PB-HOL-1 band, UNCHANGED (operator 2026-10-24): applied to C2_paired = 22.05 x P
SENS_REL_BARS = (0.05, 0.10)       # NON-GATING: relative drift bars, and P over unflagged pairs only
PRIOR_VERDICT = Path("/mnt/raid0/llm/tmp/f8-launchers-20261023/m4-srpf-pbhol/VERDICT.json")
PRIOR_VERDICT_SHA = "4b47d4b766fbb194a7ca69d04b72c8668a9a20b5982305f52c8bd79f580c2078"
DECIDED = ["C1_srpf_B_over_A_lt_2", "C1_srpf512", "C1_srpf2048", "C3_off_completions_byte_identical"]
OUTCOME = {"PASS": "PASS", "PASS_WINDOW_DRIFT": "WINDOW_DRIFT_ONLY", "FAIL_LOW": "FAIL_CANDIDATE", "FAIL_HIGH": "FAIL_CANDIDATE",
           "NOT_MEASURED": "INCOMPLETE"}


def in_band(x: float) -> bool:
    """The M4.2a comparison code, unchanged."""
    return REF_RATIO * (1 - REF_TOL) <= x <= REF_RATIO * (1 + REF_TOL)


def valid_run(r: dict) -> tuple:
    """M4.2a AMENDMENT section 2 predicate, unchanged (byte-for-byte logic of ../m4-srpf-pbhol-2a/verdict.py valid_run)."""
    if r.get("skipped"):
        return False, "skipped: " + str(r["skipped"])
    if r.get("short_http") != 200 or r.get("short_error") or r.get("short_ttft_ms") is None:
        return False, f"short failed (http {r.get('short_http')}, {str(r.get('short_error'))[:60]})"
    p = r.get("long_progress_at_send")
    if not p or p[1] < MIN_COLLIDE_FRAC:
        return False, f"no collision: long progress at send {p}"
    if r.get("long_error"):
        return False, f"no collision: long errored ({str(r.get('long_error'))[:60]})"
    lt, ls, ss = r.get("long_ttft_ms"), r.get("long_t_send"), r.get("short_t_send")
    if lt is not None:
        if ls is None or ss is None:
            return False, "no collision proof: long_t_send/short_t_send missing"
        if ls + lt / 1000.0 <= ss:
            return False, f"no collision: long first token {ls + lt / 1000.0 - ss:+.2f} s vs short send (not after it)"
    return True, ""


def load_stats(out: Path, rec: dict, window: str) -> dict:
    """One load: its numbers, its validity reasons (empty list = VALID) and its drift flag (never a validity reason)."""
    role = rec.get("role")
    st = {"load": rec.get("load"), "role": role, "kind": rec.get("kind"), "dir": rec.get("dir"), "why_invalid": [],
          "A": [], "B": [], "C_start": [], "C_end": [], "invalid_reps": [], "drift_flag": None}
    why = st["why_invalid"]
    if role not in ROLE_SHA:
        why.append(f"unknown role {role!r}")
        return st
    if rec.get("window_id") != window:
        why.append(f"window {rec.get('window_id')} != {window} (never pooled across windows)")
    if rec.get("harness_rc") != 0 or rec.get("status") != "complete":
        why.append(f"harness rc={rec.get('harness_rc')} status={rec.get('status')}")
    if rec.get("trip"):
        why.append(f"guard trip: {rec['trip']}")
    pk = rec.get("vram_peak_mib")
    st["vram_peak_mib"] = pk
    if pk is None:
        why.append("own-pid VRAM peak is null (no residency proof from the job watcher)")
    elif pk > VRAM_GUARD_MIB:
        why.append(f"own-pid VRAM peak {pk} MiB > guard {VRAM_GUARD_MIB}")
    f = out / str(rec.get("dir", "")) / "pb_hol_1.jsonl"
    rows = [json.loads(ln) for ln in f.read_text().splitlines() if ln.strip()] if f.is_file() else []
    if not rows:
        why.append(f"no rows in {f}")
        return st
    phase = ROLE_PHASE[role]
    po = [r for r in rows if r.get("kind") == "port_ownership"]
    if len(po) != 1 or not po[0].get("ok"):
        why.append(f"port ownership proof: {len(po)} rows, ok={[r.get('ok') for r in po]}")
    if po and po[0].get("binary_sha256") != ROLE_SHA[role]:
        why.append(f"binary sha {po[0].get('binary_sha256')} != the {role} store sha")
    if po and po[0].get("phase") != phase:
        why.append(f"phase {po[0].get('phase')} != {phase} for role {role}")
    gp = [r for r in rows if r.get("kind") == "graphs_proof"]
    if not gp or any(r.get("graphs") != "ON" or r.get("HSA_OVERRIDE_CPU_AFFINITY_DEBUG") != "0" for r in gp):
        why.append(f"graphs/HSA proof: {[(r.get('graphs'), r.get('HSA_OVERRIDE_CPU_AFFINITY_DEBUG')) for r in gp]}")
    rs = [r for r in rows if r.get("kind") == "residency"]
    st["own_vram_gib_at_ready"] = [r.get("own_vram_gib") for r in rs]
    if not rs or any(not r.get("ok") or (r.get("own_vram_gib") or 0) < RES_MIN_GIB for r in rs):
        why.append(f"residency: {st['own_vram_gib_at_ready']}")
    runs = [r for r in rows if r.get("kind") == "run"]
    cs = [r for r in runs if r.get("arm") == "C"]
    # clause 5, AMENDED: a FLAG, never a validity reason
    if len(cs) != 2 * C_REPS or any(r.get("short_ttft_ms") is None or r.get("short_error") or r.get("short_http") != 200 for r in cs):
        st["drift_flag"] = f"C-solo drift not measurable: {len(cs)} solo rows (want {2 * C_REPS}, all answered)"
    else:
        st["C_start"] = [r["short_ttft_ms"] for r in cs[:C_REPS]]
        st["C_end"] = [r["short_ttft_ms"] for r in cs[C_REPS:]]
        st["c_drift_ms"] = round(statistics.median(st["C_end"]) - statistics.median(st["C_start"]), 3)
        if st["c_drift_ms"] > DRIFT_BAR_MS:
            st["drift_flag"] = f"C-solo drift {st['c_drift_ms']:+.1f} ms > {DRIFT_BAR_MS} ms (PB-HOL-1 C-solo spread)"
    for r in runs:
        arm = str(r.get("arm", "")).split("-")[0]
        if arm not in ("A", "B"):
            continue
        ok, w = valid_run(r)
        if ok:
            st[arm].append(r["short_ttft_ms"])
        else:
            st["invalid_reps"].append({"arm": r.get("arm"), "rep": r.get("rep"), "why": w})
    if len(st["A"]) < MIN_VALID or len(st["B"]) < MIN_VALID:
        why.append(f"valid reps A={len(st['A'])} B={len(st['B'])} (< {MIN_VALID})")
    cal = [r.get("long_ttft_s") for r in rows if r.get("kind") == "calibration" and r.get("long_ttft_s")]
    st["solo_64k_s"] = cal[0] if cal else None
    if st["A"] and st["B"]:
        ma = statistics.median(st["A"])
        st["medA"], st["medB"] = ma, statistics.median(st["B"])
        st["c2_raw"] = st["medB"] / ma
        st["ratio"] = round(st["c2_raw"], 3)
        st["rep_ratios"] = [round(b / ma, 3) for b in st["B"]]
    return st


def _flag(s: dict, rel=None):
    """Gating flag (rel None: the 2.8 ms bar) or a NON-GATING relative bar."""
    if rel is None:
        return s.get("drift_flag")
    if "c_drift_ms" not in s or not s["C_start"]:
        return s.get("drift_flag")
    return "drift" if s["c_drift_ms"] > rel * statistics.median(s["C_start"]) else None


def adjacent_pairs(valid: list, rel=None) -> list:
    pairs = []
    for x, y in zip(valid, valid[1:]):
        if x["role"] == y["role"]:
            continue
        c, h = (x, y) if x["role"] == "candidate" else (y, x)
        fl = [f"L{s['load']}: {_flag(s, rel)}" for s in (x, y) if _flag(s, rel)]
        pairs.append({"loads": [x["load"], y["load"]], "order": f"{x['role']}->{y['role']}",
                      "candidate_c2": round(c["c2_raw"], 3), "champion_c2": round(h["c2_raw"], 3),
                      "p": c["c2_raw"] / h["c2_raw"], "drift_flag": fl or None})
    return pairs


def pooled(pairs: list) -> float:
    return math.exp(statistics.fmean(math.log(q["p"]) for q in pairs))


def c2_from(loads: list) -> dict:
    valid = sorted([s for s in loads if not s["why_invalid"]], key=lambda s: s["load"])
    ch = [s for s in valid if s["role"] == "champion"]
    m4 = [s for s in valid if s["role"] == "candidate"]
    res = {"valid_champion_loads": [s["load"] for s in ch], "valid_candidate_loads": [s["load"] for s in m4],
           "band": [round(REF_RATIO * (1 - REF_TOL), 3), round(REF_RATIO * (1 + REF_TOL), 3)]}
    if len(ch) < MIN_LOADS or len(m4) < MIN_LOADS:
        res.update(cond="NOT_MEASURED", why=f"valid loads champion={len(ch)} candidate={len(m4)} (< {MIN_LOADS} of either)")
        return res
    pairs = adjacent_pairs(valid)
    res["pairs"] = [{**q, "p": round(q["p"], 4)} for q in pairs]
    if len(pairs) < MIN_PAIRS:
        res.update(cond="NOT_MEASURED", why=f"{len(pairs)} adjacent champion/candidate pair(s) among the valid loads (< {MIN_PAIRS})")
        return res
    P = pooled(pairs)
    C2p = round(REF_RATIO * P, 3)
    cha = [x for s in ch for x in s["A"]]
    chb = [x for s in ch for x in s["B"]]
    m4a = [x for s in m4 for x in s["A"]]
    m4b = [x for s in m4 for x in s["B"]]
    champ = round(statistics.median(chb) / statistics.median(cha), 3)
    cand = round(statistics.median(m4b) / statistics.median(m4a), 3)
    flagged = [q["loads"] for q in pairs if q["drift_flag"]]
    window_drift = []
    if flagged:
        window_drift.append(f"{len(flagged)}/{len(pairs)} pairs drift-flagged {flagged}")
    if not in_band(champ):
        window_drift.append(f"champion pooled C2 {champ} outside the band")
    if not in_band(C2p):
        cond = "FAIL_LOW" if C2p < REF_RATIO * (1 - REF_TOL) else "FAIL_HIGH"
    else:
        cond = "PASS_WINDOW_DRIFT" if window_drift else "PASS"
    res.update(cond=cond, pooled_paired_ratio=round(P, 4), C2_paired=C2p, n_pairs=len(pairs), flagged_pairs=flagged,
               window_drift=window_drift or None, champion_pooled_c2=champ, champion_pooled_c2_in_band=in_band(champ),
               candidate_pooled_c2_raw=cand, candidate_pooled_c2_raw_in_band=in_band(cand))
    return res


def load_prior(path: Path, want_sha) -> dict:
    raw = path.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    if want_sha and sha != want_sha:
        raise SystemExit(f"REFUSE: prior verdict {path} sha256 {sha} != pinned {want_sha}")
    conds = json.loads(raw)["conditions"]
    missing = [k for k in DECIDED if k not in conds]
    if missing:
        raise SystemExit(f"REFUSE: prior verdict lacks {missing}")
    return {"path": str(path), "sha256": sha, "conditions": {k: conds[k] for k in DECIDED}}


def verdict(out: Path, prior: dict) -> dict:
    lf = out / "loads.jsonl"
    recs = [json.loads(ln) for ln in lf.read_text().splitlines() if ln.strip()] if lf.is_file() else []
    meta = {}
    mf = out / "window.json"
    if mf.is_file():
        meta = json.loads(mf.read_text())
    window = meta.get("window_id")
    loads = [load_stats(out, r, window) for r in recs]
    c2 = c2_from(loads)
    pc = prior["conditions"]
    c2c = {"PASS": "PASS", "PASS_WINDOW_DRIFT": "PASS", "FAIL_LOW": "FAIL", "FAIL_HIGH": "FAIL"}.get(c2["cond"], "NOT_MEASURED")
    conds = {**pc, "C2_off_identity_paired": c2c}
    gate = [pc["C1_srpf_B_over_A_lt_2"], c2c, pc["C3_off_completions_byte_identical"]]
    overall = "FAIL" if "FAIL" in gate else ("PASS" if all(x == "PASS" for x in gate) else "INCOMPLETE")
    # NON-GATING: P over unflagged pairs only (what voiding would have decided), under the 2.8 ms bar and two relative bars;
    # P over the disjoint pairs only (CH1-M4a, CH2-M4b: the un-overlapped form); per-load numbers
    valid = sorted([s for s in loads if not s["why_invalid"]], key=lambda s: s["load"])
    sens = {}
    for name, rel in (("drift_bar_2.8ms", None),) + tuple((f"drift_bar_{int(r * 100)}pct", r) for r in SENS_REL_BARS):
        pr = adjacent_pairs(valid, rel) if c2.get("pairs") else []
        keep = [q for q in pr if not q["drift_flag"]]
        sens[name] = {"flagged_pairs": len(pr) - len(keep), "unflagged_pairs": len(keep),
                      "C2_paired_unflagged_only": round(REF_RATIO * pooled(keep), 3) if keep else None}
    pr = adjacent_pairs(valid) if c2.get("pairs") else []
    disjoint = pr[0::2]
    nong = {"C2_paired_disjoint_pairs_only": round(REF_RATIO * pooled(disjoint), 3) if disjoint else None,
            "per_load": [{k: s.get(k) for k in ("load", "role", "kind", "ratio", "rep_ratios", "c_drift_ms", "drift_flag", "C_start",
                                                "C_end", "solo_64k_s", "vram_peak_mib", "own_vram_gib_at_ready")} for s in loads],
            "sensitivity": sens}
    return {"verdict": overall, "outcome": OUTCOME.get(c2["cond"], "INCOMPLETE") if overall != "FAIL" or c2c == "FAIL" else "FAIL_PRIOR",
            "conditions": conds, "c2": c2, "window": meta,
            "loads": [{"load": s["load"], "role": s["role"], "kind": s["kind"], "valid": not s["why_invalid"],
                       "why_invalid": s["why_invalid"], "drift_flag": s["drift_flag"], "invalid_reps": s["invalid_reps"]} for s in loads],
            "NON_GATING": nong, "drift_bar_ms": DRIFT_BAR_MS, "drift_bar_role": "per-pair FLAG (operator 2026-10-24), never voiding",
            "min_valid_loads_per_binary": MIN_LOADS, "min_adjacent_pairs": MIN_PAIRS,
            "decided_from": {"path": prior["path"], "sha256": prior["sha256"], "note": "C1, C3 decided in M4.2; copied verbatim"},
            "rule": "AMENDMENT-M4.2b-paired.md (supersedes PREDECLARATION.md section 3 clause 5, sections 4-5 for C2)",
            "gating": "C1 AND C2 AND C3; C2 = 22.05 x geometric-mean(candidate C2 / champion C2 over adjacent pairs) within 22.05 x (1 +- 0.10); production gate is a separate step"}


# ---------------------------------------------------------------- selftest
def _run(arm, rep, ttft, t0, *, frac=0.5, long_first_after_send_s=None, long_error=None, http=200):
    ts = t0 + rep * 300
    long_send = ts - 60.0
    lt = None if long_first_after_send_s is None else (ts + long_first_after_send_s - long_send) * 1000.0
    return {"kind": "run", "arm": arm, "rep": rep, "short_ttft_ms": ttft, "short_http": http, "short_error": None,
            "short_t_send": ts, "long_t_send": long_send, "long_ttft_ms": lt, "long_error": long_error,
            "long_finished_before_abort": arm.startswith("B"), "long_progress_at_send": [int(64000 * frac), frac, ts]}


def _load_rows(role, a, bs, c0=280.0, drift=1.0, *, sha=None, graphs="ON", res=46.6, frac=0.5, nc=C_REPS):
    ph = ROLE_PHASE[role]
    rows = [{"kind": "port_ownership", "phase": ph, "ok": True, "binary_sha256": sha or ROLE_SHA[role]},
            {"kind": "graphs_proof", "graphs": graphs, "HSA_OVERRIDE_CPU_AFFINITY_DEBUG": "0"},
            {"kind": "residency", "own_vram_gib": res, "ok": res >= RES_MIN_GIB},
            {"kind": "calibration", "long_ttft_s": 120.0}]
    rows += [{"kind": "run", "arm": "C", "rep": i + 1, "short_ttft_ms": c0 + i * 0.1, "short_http": 200} for i in range(nc)]
    for i, b in enumerate(bs):
        rows.append(_run(f"A-{ph}", i + 1, a + i, 1000.0))
        rows.append(_run(f"B-{ph}", i + 1, b, 1000.0, frac=frac, long_first_after_send_s=b / 1000.0 - 0.2))
    rows += [{"kind": "run", "arm": "C", "rep": nc + i + 1, "short_ttft_ms": c0 + drift + i * 0.1, "short_http": 200} for i in range(nc)]
    return rows


def L(role, c2, *, a=3250.0, spread=0.03, extra=None, **kw):
    """A synthetic load whose C2 (median B / median A) is exactly c2: A = a, a+1, a+2 (median a+1); B = c2 x (a+1) x (1-s, 1, 1+s)."""
    m = a + 1
    return (role, _load_rows(role, a, [c2 * m * (1 - spread), c2 * m, c2 * m * (1 + spread)], **kw), extra or {})


def _window(td: Path, loads: list, window="w1") -> Path:
    (td / "window.json").write_text(json.dumps({"window_id": window}))
    recs = []
    for i, (role, rows, extra) in enumerate(loads, 1):
        d = f"L{i}-{role}"
        (td / d).mkdir(parents=True, exist_ok=True)
        (td / d / "pb_hol_1.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
        rec = {"load": i, "role": role, "kind": "planned", "dir": d, "window_id": window, "harness_rc": 0, "status": "complete",
               "trip": None, "vram_peak_mib": 48436}
        rec.update(extra)
        recs.append(rec)
    (td / "loads.jsonl").write_text("\n".join(json.dumps(r) for r in recs) + "\n")
    return td


def selftest() -> int:
    bad = 0
    ok_prior = {"path": "synthetic", "sha256": "-", "conditions": {k: "PASS" for k in DECIDED}}
    CH, M4 = "champion", "candidate"

    def abab(c2s, roles=(CH, M4, CH, M4), **kw):
        return [L(r, c, **kw) for r, c in zip(roles, c2s)]

    def drifting(base, step, shift=1.0, **kw):
        """Progressive window drift: load k (0-based) reads base x step**k, both binaries alike; the candidate x shift."""
        return [L(r, base * step ** k * (shift if r == M4 else 1.0), **kw) for k, r in enumerate((CH, M4, CH, M4))]

    def case(label, want, want_c2, loads, prior=ok_prior, want_pairs=None):
        nonlocal bad
        with tempfile.TemporaryDirectory() as td:
            v = verdict(_window(Path(td), loads), prior)
        c2 = v["c2"]
        ok = v["verdict"] == want and c2["cond"] == want_c2 and (want_pairs is None or c2.get("n_pairs") == want_pairs)
        bad += 0 if ok else 1
        print(f"  selftest {'ok ' if ok else 'BAD'} {label}: want {want}/{want_c2} got {v['verdict']}/{c2['cond']} ({v['outcome']}) "
              f"C2p={c2.get('C2_paired')} P={c2.get('pooled_paired_ratio')} pairs={c2.get('n_pairs')} champ={c2.get('champion_pooled_c2')} "
              f"cand_raw={c2.get('candidate_pooled_c2_raw')} invalid={[l['load'] for l in v['loads'] if not l['valid']]}")

    # --- the operator's two required cases
    case("drifting window, both arms slow equally inside every load (M4.2a: C-solo +603 ms, raw 25.2x) -> must NOT fail",
         "PASS", "PASS_WINDOW_DRIFT", abab([25.2, 25.2, 25.3, 25.2], drift=603.3), want_pairs=3)
    case("drifting window, progressive x1.15 per load on both binaries (raw 22 -> 33x) -> must NOT fail",
         "PASS", "PASS_WINDOW_DRIFT", drifting(22.05, 1.15, drift=40.0))
    case("drifting window, progressive x1.25 per load (stress: overlapping pairs leave drift^(1/3)) -> must NOT fail",
         "PASS", "PASS_WINDOW_DRIFT", drifting(22.05, 1.25))
    case("real candidate shift +20% in a quiet window -> must FAIL", "FAIL", "FAIL_HIGH", abab([22.05, 26.46, 22.0, 26.5]))
    case("real candidate shift -20% (HOL weaker) -> must FAIL", "FAIL", "FAIL_LOW", abab([22.05, 17.64, 22.1, 17.6]))
    case("real candidate shift +20% inside a x1.15 drifting window -> must FAIL", "FAIL", "FAIL_HIGH", drifting(22.05, 1.15, shift=1.20, drift=40.0))
    case("real candidate shift +20% with equal in-load drift flags -> FAIL (flags never rescue)", "FAIL", "FAIL_HIGH",
         abab([25.2, 30.24, 25.3, 30.3], drift=603.3))
    # --- band edges (the unchanged 22.05 x (1 +- 0.10), applied to 22.05 x P)
    case("quiet window, binaries identical", "PASS", "PASS", abab([22.05, 22.1, 22.0, 22.05]), want_pairs=3)
    case("candidate +8% (inside 10%)", "PASS", "PASS", abab([22.05, 23.814, 22.05, 23.814]))
    case("candidate +12% (outside 10%)", "FAIL", "FAIL_HIGH", abab([22.05, 24.696, 22.05, 24.696]))
    case("candidate -12%", "FAIL", "FAIL_LOW", abab([22.05, 19.404, 22.05, 19.404]))
    # --- window-drift classification
    case("quiet C-solo but champion itself reads 26x (window unlike PB-HOL-1), candidate equal", "PASS", "PASS_WINDOW_DRIFT",
         abab([26.0, 26.1, 26.0, 25.9]))
    case("one load +5 ms C-solo drift (was INVALID under PREDECLARATION 3.5) -> flag only", "PASS", "PASS_WINDOW_DRIFT",
         [L(CH, 22.05, drift=5.0), L(M4, 22.1), L(CH, 22.0), L(M4, 22.05)])
    case("drift exactly at the bar (2.8 ms) is not flagged", "PASS", "PASS", abab([22.05, 22.1, 22.0, 22.05], drift=2.8))
    case("missing end solo shorts -> drift unmeasurable = flag, not void", "PASS", "PASS_WINDOW_DRIFT",
         [L(CH, 22.05), L(M4, 22.1, nc=1), L(CH, 22.0), L(M4, 22.05)])
    # --- pairing / replacement
    case("INVALID load retried immediately keeps the alternation (CH, M4x, M4r, CH, M4) -> 3 pairs", "PASS", "PASS",
         [L(CH, 22.05), L(M4, 22.1, extra={"vram_peak_mib": None}), L(M4, 22.1, extra={"kind": "replacement"}), L(CH, 22.0), L(M4, 22.05)],
         want_pairs=3)
    case("valid loads not alternating (CH, CH, M4, M4) -> 1 adjacent pair -> NOT_MEASURED", "INCOMPLETE", "NOT_MEASURED",
         abab([22.05, 22.0, 22.1, 22.05], roles=(CH, CH, M4, M4)))
    # --- load validity (unchanged clauses): one invalid load leaves 1 valid candidate -> NOT_MEASURED
    q = [22.05, 22.1, 22.0]
    for label, bad_load in (("null own-pid VRAM peak", L(M4, 22.1, extra={"vram_peak_mib": None})),
                            ("VRAM guard trip", L(M4, 22.1, extra={"trip": "own VRAM 62000 MiB"})),
                            ("wrong binary sha", L(M4, 22.1, sha="0" * 64)),
                            ("graphs OFF", L(M4, 22.1, graphs="OFF")),
                            ("not resident (CPU fallback, 3 GiB)", L(M4, 22.1, res=3.0)),
                            ("no collision (short sent at 0.30)", L(M4, 22.1, frac=0.30)),
                            ("a load from another window is never pooled", L(M4, 22.1, extra={"window_id": "w0"})),
                            ("harness incomplete (deadline)", L(M4, 22.1, extra={"status": "abort: deadline", "harness_rc": 3}))):
        case(f"{label} invalidates the load", "INCOMPLETE", "NOT_MEASURED", [L(CH, q[0]), bad_load, L(CH, q[2]), L(M4, 22.05)])
    case("decided C1 FAIL propagates", "FAIL", "PASS", abab([22.05, 22.1, 22.0, 22.05]),
         prior={**ok_prior, "conditions": {**ok_prior["conditions"], "C1_srpf_B_over_A_lt_2": "FAIL"}})
    with tempfile.TemporaryDirectory() as td:
        v = verdict(Path(td), ok_prior)
        ok = v["verdict"] == "INCOMPLETE" and v["c2"]["cond"] == "NOT_MEASURED" and v["outcome"] == "INCOMPLETE"
        bad += 0 if ok else 1
        print(f"  selftest {'ok ' if ok else 'BAD'} empty output dir -> INCOMPLETE/NOT_MEASURED (never a vacuous pass)")
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "VERDICT.json"
        p.write_text(json.dumps({"conditions": {k: "PASS" for k in DECIDED}}))
        try:
            load_prior(p, PRIOR_VERDICT_SHA)
            ok = False
        except SystemExit:
            ok = True
        bad += 0 if ok else 1
        print(f"  selftest {'ok ' if ok else 'BAD'} prior VERDICT.json sha mismatch is refused")
    # the band is the M4.2a one, numerically
    ok = (round(REF_RATIO * (1 - REF_TOL), 3), round(REF_RATIO * (1 + REF_TOL), 3)) == (19.845, 24.255) and DRIFT_BAR_MS == 2.8
    bad += 0 if ok else 1
    print(f"  selftest {'ok ' if ok else 'BAD'} band 19.845-24.255 and drift bar 2.8 ms unchanged")
    print(f"selftest {'PASS' if not bad else 'FAIL'} ({bad} bad)")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    ap.add_argument("--prior", default=str(PRIOR_VERDICT))
    ap.add_argument("--write")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--check-load", type=int, metavar="N", help="job.sh: print 'VALID', 'VALID FLAG: <why>' or 'INVALID: <reasons>' for load N")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.out:
        ap.error("--out required")
    if a.check_load is not None:
        out = Path(a.out)
        recs = [json.loads(ln) for ln in (out / "loads.jsonl").read_text().splitlines() if ln.strip()]
        win = json.loads((out / "window.json").read_text()).get("window_id")
        rec = [r for r in recs if r.get("load") == a.check_load]
        if not rec:
            print(f"INVALID: load {a.check_load} not in loads.jsonl")
            return 0
        s = load_stats(out, rec[-1], win)
        if s["why_invalid"]:
            print("INVALID: " + "; ".join(s["why_invalid"]))
        else:
            print("VALID" + (f" FLAG: {s['drift_flag']}" if s["drift_flag"] else ""))
        return 0
    v = verdict(Path(a.out), load_prior(Path(a.prior), PRIOR_VERDICT_SHA))
    txt = json.dumps(v, indent=1)
    if a.write:
        Path(a.write).write_text(txt + "\n")
    print(txt)
    print(f"VERDICT {v['verdict']} OUTCOME {v['outcome']} C2={v['c2']['cond']} C2_paired={v['c2'].get('C2_paired')} "
          f"P={v['c2'].get('pooled_paired_ratio')} pairs={v['c2'].get('n_pairs')} champion_c2={v['c2'].get('champion_pooled_c2')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
