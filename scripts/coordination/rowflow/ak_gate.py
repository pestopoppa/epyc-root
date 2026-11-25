#!/usr/bin/env python3
"""ak_gate.py - the ONE tested gate harness for AK (autokernel) knob gate rows. Vendored into the row dir beside
ak_row_harness.py by `mk_ak_row.py gate new` and sealed in SOURCE.sha256; the row's job.py is a thin declaration:

    SPEC = {...knobs, arms, expect, server argv, workload, metric, keep rule, [correctness], [inputs]...}
    sys.exit(G.selftest(SPEC, D) if "--selftest" in sys.argv[1:] else G.main(SPEC, D, sys.argv[1:]))

Why (pipeline-mgmt 2026-11-25, AutoKernel top priority): the 2026-11-24/25 smoke failures came from per-row hand-rolled
witness / arm / smoke / identity logic: witness parsers that missed real lines, inverted per-arm expectations or ANDed
every knob together (ak-27b-tail-fuse2 r1/r2: one missing G5 marker reported all six knobs False); `-lv 4` missing on a
non-server argv (ak-c22-q8mc: llama-perplexity printed no INFO marker); resident-server arm bias; missing dirs/inputs
(out/kv_slots, inputs/kld_text.txt); in-process identity checks that flag drafter near-tie nondeterminism
(ak-c22-df2-devhandoff r3-r6). The harness owns all of it once:

  1. a FRESH server per arm visit (warm-up requests discarded), `-lv >= max(knob level, 4)` forced onto EVERY llama
     binary argv (server, perplexity, bench, cli, test-dflash*), balanced ABBA arm order (rotation + reversal: with
     2k scored blocks every arm sits at every position exactly twice);
  2. per-knob, per-arm witness parsing against an EXPLICIT expect table ({arm: {knob: present|absent}}); never an AND
     over knobs; a mismatch names knob, arm, expected, observed, log file, lines scanned and the argv / log -lv;
  3. the correctness unit FIRST (tbo | kld | identity); a failure stops with FAIL_CORRECTNESS. Identity runs every
     (arm, prompt) in its OWN process; the gate is outputs + accepted tokens, drafts are diagnostic unless
     `strict_drafts`; a baseline A/A identity difference is FUTILITY_HARNESS_NONDET (not the knob's fault);
  4. the OFF/OFF2 A/A guard: |exp(mean ln(OFF2/OFF)) - 1| > aa_max -> FUTILITY_HARNESS_AA (knob not judged);
  5. a fast smoke (budget ~5 min) on the smoke arm only: makes every dir, checks every declared input, one fresh
     server, one warm-up, one request long enough to reach the knob, witness check, TERMINAL-smoke.json +
     out-smoke/smoke_measure.json;
  6. resume: every unit is appended (fsync) to out/results.jsonl; a rerun skips completed unit ids;
  7. replay: `job.py --replay <prior out dir>` runs the WHOLE decision path offline (log re-parse -> witness, A/A,
     metric, KEEP rule, verdict) on a previous run's real logs/results and writes out/REPLAY-RECEIPT.json;
     `--decide-from <dir>` does the same and only prints `DECIDE {json}` (preflight R4 replay smoke, no writes);
  8. a standard out/RESULT.json: complete, verdict, polar, per_arm stats, witness table, A/A, correctness.

Process management: only processes this module started (captured Popen handles) are ever signalled, via
ak_row_harness.kill_tree. No quiet-host guard here (GPU gate rows); a CPU timing gate declares requires_quiet_host.
"""
import hashlib
import json
import math
import os
import re
import signal
import subprocess
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import ak_row_harness as H  # noqa: E402

GATE_VERSION = "1"
# Evidence a FAIL_* / FUTILITY_* row must keep so it can be diagnosed and REPLAYED (AutoKernel 2026-11-25): declared in
# spec.json keep + evidence by mk_ak_row gate new and in RESULT.json. ak_gate never deletes anything under these.
EVIDENCE_PATHS = ("out/logs", "out/prof", "out/servers/*.log", "out/results.jsonl", "out/RESULT.json",
                  "out/TERMINAL-smoke.json", "out-smoke")
EVIDENCE_VERDICTS = ("FAIL_*", "FUTILITY_*")
RECEIPT = "REPLAY-RECEIPT.json"
RECEIPT_SCHEMA = "epyc.ak_gate.replay_receipt.v1"
RESULT_SCHEMA = "epyc.ak_gate.result.v1"
MIN_LV = 4
LV_BIN_RX = re.compile(r"^(?:llama-(?:server|perplexity|bench|cli|batched-bench|completion|imatrix)|test-dflash[\w.-]*)$")
LV_FLAG_NAMES = ("-lv", "--verbosity", "--log-verbosity")
LOG_VERBOSITY_RX = re.compile(r"verbosity\s*=\s*(\d+)")
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
ENV_KNOB_RX = re.compile(r"^[A-Z][A-Z0-9_]{2,}$")
EXPECT_VALUES = ("present", "absent")
T975 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228,
        11: 2.201, 12: 2.179, 13: 2.160, 14: 2.145, 15: 2.131, 16: 2.120, 20: 2.086, 25: 2.060, 30: 2.042}
TIMING_FIELDS = ("prompt_n", "prompt_ms", "predicted_n", "predicted_ms", "draft_n", "draft_n_accepted")
KLD_RX = re.compile(r"Mean\s+KLD:\s+([-\d.eE+]+)")
SAME_TOP_RX = re.compile(r"Same top p:\s+([\d.]+)")
IDENTITY_RX = {"output": r"^\s*single-output:\s*(.*?)\s*$", "accepted": r"^\s*single-accepted:\s*(.*?)\s*$",
               "draft": r"^\s*single-draft:\s*(.*?)\s*$"}


def _t(df):
    if df in T975:
        return T975[df]
    return T975[max(k for k in T975 if k <= df)] if df > 1 else T975[1]


# ---------------------------------------------------------------------------------------------------- metrics
def _sum(reqs, k):
    return float(sum(float(r.get(k) or 0) for r in reqs))


def m_tok_s(reqs):
    ms = _sum(reqs, "predicted_ms")
    return _sum(reqs, "predicted_n") / ms * 1000.0 if ms > 0 else None


def m_pp_tok_s(reqs):
    ms = _sum(reqs, "prompt_ms")
    return _sum(reqs, "prompt_n") / ms * 1000.0 if ms > 0 else None


def m_ms_per_token(reqs):
    n = _sum(reqs, "predicted_n")
    return _sum(reqs, "predicted_ms") / n if n > 0 else None


def m_ms_per_round(reqs):
    """DFlash/spec decode: one verify round emits draft_n_accepted + 1 tokens."""
    rounds = _sum(reqs, "predicted_n") - _sum(reqs, "draft_n_accepted")
    return _sum(reqs, "predicted_ms") / rounds if rounds > 0 else None


def m_wall_s(reqs):
    w = _sum(reqs, "wall_s")
    return w if w > 0 else None


# name -> (function over the measured request records, higher_is_better). The declared direction must agree.
METRICS = {"tok_s": (m_tok_s, True), "pp_tok_s": (m_pp_tok_s, True), "ms_per_token": (m_ms_per_token, False),
           "ms_per_round": (m_ms_per_round, False), "wall_s": (m_wall_s, False)}


# ---------------------------------------------------------------------------------------------------- spec
class SpecError(ValueError):
    pass


def baseline_arms(spec):
    return list(spec.get("baseline") or [])


def candidate_arms(spec):
    c = spec.get("candidates")
    if c:
        return list(c)
    b = set(baseline_arms(spec))
    return [a for a in spec.get("arms", {}) if a not in b]


def arm_list(spec):
    """Base arm order for ABBA: baseline[0], candidates, baseline[1:] (the A/A pair is split across the block)."""
    b = baseline_arms(spec)
    return b[:1] + candidate_arms(spec) + b[1:]


def keep_cfg(spec):
    k = dict({"threshold": 1.0, "n_blocks": 8, "look_blocks": None, "aa_max": 0.02, "dummy_block": True},
             **(spec.get("keep") or {}))
    if k["look_blocks"] is None:
        k["look_blocks"] = k["n_blocks"] // 2
    return k


def visits_per_arm(spec):
    k = keep_cfg(spec)
    return k["n_blocks"] + (1 if k["dummy_block"] else 0)


def required_lv(spec):
    return max([MIN_LV] + [int(v.get("level") or MIN_LV) for v in (spec.get("knobs") or {}).values()])


def validate_spec(spec):
    """Raise SpecError naming every defect of the declaration (selftest and every entry point call this first)."""
    errs = []
    knobs = spec.get("knobs") or {}
    arms = spec.get("arms") or {}
    expect = spec.get("expect") or {}
    if not spec.get("row_id"):
        errs.append("row_id missing")
    if not knobs:
        errs.append("no knobs declared (a gate row declares >= 1 knob with its witness marker)")
    for k, v in knobs.items():
        kind = v.get("kind") or ("flag" if k.startswith("-") else "env")
        if kind not in ("env", "flag", "observe"):
            errs.append(f"knob {k}: kind {kind!r} not env|flag|observe")
        if kind == "env" and not ENV_KNOB_RX.match(k):
            errs.append(f"knob {k}: env knob name must be UPPER_SNAKE")
        if kind == "flag" and not k.startswith("-"):
            errs.append(f"knob {k}: flag knob must start with '-'")
        if not str(v.get("marker") or "").strip():
            errs.append(f"knob {k}: empty witness marker")
        if v.get("marker", "").startswith("re:"):
            try:
                re.compile(v["marker"][3:])
            except re.error as e:
                errs.append(f"knob {k}: bad marker regex: {e}")
    if len(arms) < 2:
        errs.append("need >= 2 arms")
    for a, setting in arms.items():
        for k in (setting or {}):
            if k not in knobs:
                errs.append(f"arm {a} sets undeclared knob {k}")
            elif (knobs[k].get("kind") or "") == "observe":
                errs.append(f"arm {a} sets observe-only knob {k}")
    for a in arms:
        for k in knobs:
            e = (expect.get(a) or {}).get(k)
            if e not in EXPECT_VALUES:
                errs.append(f"expect[{a}][{k}] = {e!r}: every arm x knob needs an explicit present|absent")
    for a in expect:
        if a not in arms:
            errs.append(f"expect names unknown arm {a}")
    b = baseline_arms(spec)
    if not b or any(x not in arms for x in b):
        errs.append(f"baseline {b} must name declared arms")
    if not candidate_arms(spec) or any(x not in arms for x in candidate_arms(spec)):
        errs.append("no candidate arm (arms that are not baseline)")
    kc = keep_cfg(spec)
    if kc.get("aa_max") is not None and len(b) < 2:
        errs.append("the A/A guard needs two baseline arms (OFF, OFF2); set keep.aa_max null to opt out explicitly")
    if not (isinstance(kc["n_blocks"], int) and kc["n_blocks"] >= 2):
        errs.append("keep.n_blocks must be an int >= 2")
    if not (isinstance(kc["look_blocks"], int) and 0 <= kc["look_blocks"] <= kc["n_blocks"]):
        errs.append("keep.look_blocks must be 0..n_blocks")
    m = spec.get("metric") or {}
    if m.get("name") not in METRICS:
        errs.append(f"metric.name {m.get('name')!r} not one of {sorted(METRICS)}")
    elif m.get("higher_is_better") is not METRICS[m["name"]][1]:
        errs.append(f"metric {m['name']}: higher_is_better must be {METRICS[m['name']][1]} (declared "
                    f"{m.get('higher_is_better')!r}); confirm the metric direction")
    srv = spec.get("server") or {}
    argv = srv.get("argv") or []
    if not argv or "{PORT}" not in [str(x) for x in argv]:
        errs.append("server.argv must be the production argv with a '{PORT}' placeholder")
    for k, v in knobs.items():
        if (v.get("kind") or ("flag" if k.startswith("-") else "env")) == "flag" and k in [str(x) for x in argv]:
            errs.append(f"flag knob {k} already in the base server argv (arms add it)")
    cap = spec.get("fresh_server_starts")
    if cap is not None and int(cap) < visits_per_arm(spec):
        errs.append(f"fresh_server_starts {cap} < {visits_per_arm(spec)} visits per arm")
    for rel in (spec.get("inputs") or {}):
        if rel.startswith("/") or ".." in rel.split("/"):
            errs.append(f"input {rel}: must be relative to the row dir")
    c = spec.get("correctness")
    if c:
        if c.get("kind") not in ("tbo", "kld", "identity"):
            errs.append(f"correctness.kind {c.get('kind')!r} not tbo|kld|identity")
        if c.get("kind") in ("tbo", "kld") and not c.get("argv"):
            errs.append(f"correctness {c.get('kind')}: argv required")
        if c.get("kind") == "identity" and c.get("mode", "server") == "cmd" and not c.get("argv"):
            errs.append("correctness identity mode cmd: argv required")
        for a in c.get("arms") or []:
            if a not in arms:
                errs.append(f"correctness arm {a} not declared")
    w = spec.get("workload") or {}
    if not (w.get("prompts") or w.get("input")):
        errs.append("workload needs prompts or an input file")
    if errs:
        raise SpecError("; ".join(errs))
    return True


# ---------------------------------------------------------------------------------------------------- argv / env
def argv_lv(argv):
    """The -lv level an argv runs with (None = unset; --log-verbose = 99)."""
    a = [str(x) for x in argv]
    lv = None
    for i, t in enumerate(a):
        if t == "--log-verbose":
            return 99
        if t.startswith("--verbosity=") or t.startswith("--log-verbosity="):
            v = t.split("=", 1)[1]
            lv = max(lv or 0, int(v)) if v.isdigit() else lv
        elif t in LV_FLAG_NAMES and i + 1 < len(a) and a[i + 1].isdigit():
            lv = max(lv or 0, int(a[i + 1]))
    return lv


def llama_index(argv):
    for i, t in enumerate(argv):
        if LV_BIN_RX.match(os.path.basename(str(t))):
            return i
    return None


def ensure_lv(argv, level=MIN_LV, force=False):
    """argv with -lv >= level when it runs a llama binary (or force). An existing lower level is raised in place."""
    a = [str(x) for x in argv]
    if llama_index(a) is None and not force:
        return a
    have = argv_lv(a)
    if have is not None and have >= level:
        return a
    for i, t in enumerate(a):
        if t in LV_FLAG_NAMES and i + 1 < len(a):
            a[i + 1] = str(level)
            return a
        if t.startswith("--verbosity=") or t.startswith("--log-verbosity="):
            a[i] = t.split("=", 1)[0] + "=" + str(level)
            return a
    return a + ["-lv", str(level)]


def knob_kind(spec, k):
    v = (spec.get("knobs") or {}).get(k) or {}
    return v.get("kind") or ("flag" if k.startswith("-") else "env")


def arm_env_knobs(spec, arm):
    return {k: str(v) for k, v in ((spec.get("arms") or {}).get(arm) or {}).items()
            if knob_kind(spec, k) == "env" and v is not None and v is not False}


def arm_flags(spec, arm):
    out = []
    for k, v in ((spec.get("arms") or {}).get(arm) or {}).items():
        if knob_kind(spec, k) != "flag" or v is None or v is False:
            continue
        out += [k] if v is True else [k, str(v)]
    return out


# ---------------------------------------------------------------------------------------------------- witness
def read_log(path):
    try:
        with open(path, "rb") as f:
            return ANSI.sub("", f.read().decode(errors="replace"))
    except OSError:
        return None


def marker_hit(marker, lines):
    """1-based line number of the first line holding the marker (substring, or regex with 're:'), else None."""
    rx = re.compile(marker[3:]) if marker.startswith("re:") else None
    for i, ln in enumerate(lines, 1):
        if (rx.search(ln) if rx else marker in ln):
            return i
    return None


def witness_for(spec, arm, text, argv=None, log=None):
    """{knob: {expected, observed, ok, line, lines_scanned, log, argv_lv, log_lv, lv_required, note}} - one entry per knob,
    each judged ALONE against expect[arm][knob]. Never an AND over knobs."""
    lines = (text or "").splitlines()
    out = {}
    m = LOG_VERBOSITY_RX.findall(text or "")
    log_lv = int(m[0]) if m else None
    alv = argv_lv(argv) if argv else None
    for k, v in (spec.get("knobs") or {}).items():
        exp = ((spec.get("expect") or {}).get(arm) or {}).get(k)
        ln = marker_hit(str(v["marker"]), lines) if text is not None else None
        obs = "present" if ln else "absent"
        need = int(v.get("level") or MIN_LV)
        note = ""
        if text is None:
            obs, note = "no-log", "log file missing or unreadable"
        elif exp == "present" and obs == "absent":
            eff = alv if alv is not None else log_lv
            if argv is not None and (alv is None or alv < need):
                note = f"argv log level {'none' if alv is None else alv} < required {need}: INFO witness lines never print"
            elif eff is not None and eff < need:
                note = f"log verbosity {eff} < required {need}"
            elif eff is None:
                note = (f"no 'verbosity = N' banner in the log: the binary most likely ran below -lv {need}, so INFO "
                        "witness lines never print")
        out[k] = {"expected": exp, "observed": obs, "ok": obs == exp, "line": ln, "lines_scanned": len(lines),
                  "log": log, "argv_lv": alv, "log_lv": log_lv, "lv_required": need, "note": note}
    return out


def mismatches(units):
    """Every (unit, knob) whose observation disagrees with its arm's expectation, as readable dicts."""
    out = []
    for u in units:
        for k, w in (u.get("witness") or {}).items():
            if not w.get("ok"):
                out.append({"unit": u.get("unit_id"), "arm": u.get("arm"), "knob": k, "expected": w.get("expected"),
                            "observed": w.get("observed"), "log": w.get("log"), "lines_scanned": w.get("lines_scanned"),
                            "argv_lv": w.get("argv_lv"), "note": w.get("note")})
    return out


def mismatch_text(m):
    s = (f"knob {m['knob']} arm {m['arm']} unit {m['unit']}: expected {m['expected']}, observed {m['observed']} "
         f"(log {m['log']}, {m['lines_scanned']} lines scanned, argv -lv {m['argv_lv'] if m['argv_lv'] is not None else 'none'})")
    return s + (f" - {m['note']}" if m.get("note") else "")


def witness_table(spec, units):
    """{knob: {arm: {expected, observed: {present: n, absent: n}, mismatch_units: [...]}}} over every witnessed unit."""
    tab = {k: {} for k in (spec.get("knobs") or {})}
    for u in units:
        for k, w in (u.get("witness") or {}).items():
            if k not in tab:
                continue
            e = tab[k].setdefault(u.get("arm"), {"expected": w.get("expected"), "observed": {}, "mismatch_units": []})
            e["observed"][w.get("observed")] = e["observed"].get(w.get("observed"), 0) + 1
            if not w.get("ok"):
                e["mismatch_units"].append(u.get("unit_id"))
    return tab


# ---------------------------------------------------------------------------------------------------- ABBA order
def block_order(spec, block):
    """Arms of `block` in visit order. Scored block b (1-based) uses index i = b - 1, the dummy (block 0) uses index 0:
    rotation r = (i // 2) % k of the base list, reversed on odd i. Over 2k scored blocks every arm sits at every
    position exactly twice (AB BA BA AB for two arms)."""
    base = arm_list(spec)
    k = len(base)
    i = max(block - 1, 0)
    r = (i // 2) % k
    rot = base[r:] + base[:r]
    return rot[::-1] if i % 2 else rot


def blocks(spec):
    kc = keep_cfg(spec)
    return list(range(0 if kc["dummy_block"] else 1, kc["n_blocks"] + 1))


# ---------------------------------------------------------------------------------------------------- statistics
def metric_of(spec, reqs):
    if not reqs:
        return None
    fn = METRICS[spec["metric"]["name"]][0]
    return fn(reqs)


def _speed(spec, x, base):
    """Ratio > 1 means the candidate is better, whatever the metric direction."""
    hib = METRICS[spec["metric"]["name"]][1]
    return x / base if hib else base / x


def block_values(spec, units):
    """{block: {arm: metric}} over scored timing units with a metric."""
    out = {}
    for u in units:
        if u.get("kind") != "visit" or not u.get("block") or u.get("metric") is None:
            continue
        out.setdefault(u["block"], {})[u["arm"]] = u["metric"]
    return out


def full_blocks(spec, units):
    arms = set(arm_list(spec))
    bv = block_values(spec, units)
    return {b: v for b, v in bv.items() if arms <= set(v)}


def log_ratios(spec, units, arm):
    b = baseline_arms(spec)
    out = []
    for blk, v in sorted(full_blocks(spec, units).items()):
        base = sum(v[x] for x in b) / len(b)
        if base > 0 and v[arm] > 0:
            out.append(math.log(_speed(spec, v[arm], base)))
    return out


def ci(lr):
    n = len(lr)
    if n == 0:
        return None, None, None
    m = sum(lr) / n
    if n < 2:
        return math.exp(m), None, None
    sd = math.sqrt(sum((x - m) ** 2 for x in lr) / (n - 1))
    h = _t(n - 1) * sd / math.sqrt(n)
    return math.exp(m), math.exp(m - h), math.exp(m + h)


def aa_ratio(spec, units):
    """exp(mean ln(OFF2 / OFF)) direction-normalised (> 1: OFF2 better), over full scored blocks."""
    b = baseline_arms(spec)
    if len(b) < 2:
        return None
    lr = [math.log(_speed(spec, v[b[1]], v[b[0]])) for _blk, v in sorted(full_blocks(spec, units).items())
          if v[b[0]] > 0 and v[b[1]] > 0]
    return math.exp(sum(lr) / len(lr)) if lr else None


def per_arm_stats(spec, units):
    out = {}
    for a in arm_list(spec):
        vals = [u["metric"] for u in units if u.get("kind") == "visit" and u.get("arm") == a and u.get("block")
                and u.get("metric") is not None]
        st = {"n": len(vals), "mean_metric": (sum(vals) / len(vals)) if vals else None, "metric": spec["metric"]["name"]}
        if a in candidate_arms(spec):
            lr = log_ratios(spec, units, a)
            u_, lo, hi = ci(lr)
            st.update(speedup=u_, ci95=[lo, hi], block_log_ratios=lr)
        out[a] = st
    return out


# ---------------------------------------------------------------------------------------------------- correctness
def identity_fields(c):
    f = ["output"] + (["accepted"] if c.get("gate_accepted", True) else []) + (["draft"] if c.get("strict_drafts") else [])
    return f


def correctness_units(units):
    return [u for u in units if str(u.get("kind") or "").startswith("c-")]


def plan_correctness(spec):
    """[(unit_id, kind, arm, extra)] of the declared correctness unit, in run order."""
    c = spec.get("correctness") or {}
    kind = c.get("kind")
    if not kind:
        return []
    b, cand = baseline_arms(spec), candidate_arms(spec)
    if kind == "tbo":
        return [(f"c-tbo-{a}", "c-tbo", a, {}) for a in (c.get("arms") or b[:1] + cand)]
    if kind == "kld":
        base = c.get("base_arm") or b[0]
        arms = c.get("arms") or [x for x in b if x != base] + cand
        return [(f"c-kld-base-{base}", "c-kld", base, {"mode": "base"})] + [(f"c-kld-{a}", "c-kld", a, {"mode": "kld"})
                                                                             for a in arms]
    n = int(c.get("n_prompts") or len(identity_prompts(spec, None)) or 1)
    arms = c.get("arms") or b + cand
    return [(f"c-id-{a}-p{i}", "c-id", a, {"prompt": i}) for i in range(n) for a in arms]


def decide_correctness(spec, units):
    """(verdict or None, detail, complete). None + complete = passed."""
    c = spec.get("correctness") or {}
    if not c:
        return None, {"kind": None}, True
    plan = plan_correctness(spec)
    by = {u.get("unit_id"): u for u in correctness_units(units)}
    if any(uid not in by for uid, *_ in plan):
        return None, {"kind": c["kind"], "missing": [uid for uid, *_ in plan if uid not in by]}, False
    us = [by[uid] for uid, *_ in plan]
    err = [u for u in us if u.get("error")]
    if err:
        return f"FUTILITY_HARNESS_{err[0].get('error_class') or 'UNIT'}", {"kind": c["kind"], "error": err[0].get("error"),
                                                                          "unit": err[0].get("unit_id")}, True
    mm = mismatches([u for u in us if u.get("witness")])
    if mm:
        return "FUTILITY_HARNESS_WITNESS", {"kind": c["kind"], "witness_mismatches": mm}, True
    kind = c["kind"]
    if kind == "tbo":
        bad = [u for u in us if not u.get("pass")]
        det = {"kind": kind, "per_arm": {u["arm"]: {k: u.get(k) for k in ("n_cases", "n_ok", "rc", "fails")} for u in us}}
        return ("FAIL_CORRECTNESS", dict(det, failed=[u["unit_id"] for u in bad]), True) if bad else (None, det, True)
    if kind == "kld":
        mx = float(c.get("max_kld", 0.003))
        kl = {u["arm"]: u.get("mean_kld") for u in us if u.get("mode") == "kld"}
        det = {"kind": kind, "mean_kld": kl, "max_kld": mx}
        if any(v is None for v in kl.values()):
            return "FUTILITY_HARNESS_MISSING_OUTPUT", dict(det, why="no 'Mean KLD' in a perplexity log"), True
        bad = [a for a in candidate_arms(spec) if a in kl and kl[a] > mx]
        return ("FAIL_CORRECTNESS", dict(det, failed=bad), True) if bad else (None, det, True)
    fields = identity_fields(c)
    ref, others = baseline_arms(spec)[0], baseline_arms(spec)[1:]
    det = {"kind": kind, "gated_fields": fields, "per_prompt": [], "draft_diff_prompts": 0}
    nondet, fail = [], []
    byp = {}
    for u in us:
        byp.setdefault(u["prompt"], {})[u["arm"]] = u
    for p, arms in sorted(byp.items()):
        r = arms.get(ref)
        row = {"prompt": p}
        for a, u in arms.items():
            if a == ref:
                continue
            eq = {f: (u.get(f + "_sha") == r.get(f + "_sha")) for f in ("output", "accepted", "draft")}
            row[a] = eq
            if not eq["draft"]:
                det["draft_diff_prompts"] += 1
            bad = [f for f in fields if not eq[f]]
            if bad and a in others:
                nondet.append(f"prompt {p} {a} vs {ref}: {','.join(bad)} differ")
            elif bad:
                fail.append(f"prompt {p} {a} vs {ref}: {','.join(bad)} differ")
        det["per_prompt"].append(row)
    if nondet:
        return "FUTILITY_HARNESS_NONDET", dict(det, nondet=nondet), True
    if fail:
        return "FAIL_CORRECTNESS", dict(det, failed=fail), True
    return None, det, True


# ---------------------------------------------------------------------------------------------------- decide
def polar(verdict):
    v = str(verdict or "")
    if v.startswith("KEEP") or v == "SMOKE_PASS":
        return "PASS"
    if v.startswith(("FAIL", "NO_KEEP", "FUTILITY_CANDIDATE")):
        return "FAIL"
    return None


def decide(spec, units):
    """The pre-registered rule, first match wins. Returns {verdict, polar, terminal, reason, ...}; terminal False =
    keep running (or, in a replay, the prior run did not get far enough)."""
    kc = keep_cfg(spec)
    cv, cdet, cdone = decide_correctness(spec, units)
    res = {"correctness": cdet}
    if not cdone:
        return dict(res, verdict="INCOMPLETE_CORRECTNESS", polar=None, terminal=False, reason="correctness unit pending")
    if cv:
        r = (f"{cdet.get('kind')}: " + "; ".join(mismatch_text(m) for m in cdet.get("witness_mismatches", []))
             if cdet.get("witness_mismatches") else json.dumps({k: cdet.get(k) for k in ("failed", "nondet", "why", "error")
                                                                 if cdet.get(k)})[:600])
        return dict(res, verdict=cv, polar=polar(cv), terminal=True, reason=r)
    tus = [u for u in units if u.get("kind") == "visit"]
    err = [u for u in tus if u.get("error")]
    if err:
        v = f"FUTILITY_HARNESS_{err[0].get('error_class') or 'SERVER'}"
        return dict(res, verdict=v, polar=None, terminal=True, reason=f"{err[0].get('unit_id')}: {err[0].get('error')}")
    mm = mismatches(tus)
    if mm:
        return dict(res, verdict="FUTILITY_HARNESS_WITNESS", polar=None, terminal=True, witness_mismatches=mm,
                    reason="; ".join(mismatch_text(m) for m in mm[:6]))
    nometric = [u for u in tus if u.get("block") and u.get("metric") is None]
    if nometric:
        return dict(res, verdict="FUTILITY_HARNESS_MISSING_OUTPUT", polar=None, terminal=True,
                    reason=f"{nometric[0].get('unit_id')}: no {spec['metric']['name']} from the server timings")
    nb = len(full_blocks(spec, units))
    res.update(blocks_scored=nb, aa_ratio=aa_ratio(spec, units))
    live = candidate_arms(spec)
    if nb >= max(kc["look_blocks"], 2) and kc["aa_max"] is not None and res["aa_ratio"] is not None \
            and abs(res["aa_ratio"] - 1.0) > float(kc["aa_max"]):
        return dict(res, verdict="FUTILITY_HARNESS_AA", polar=None, terminal=True,
                    reason=f"A/A {baseline_arms(spec)[1]}/{baseline_arms(spec)[0]} = {res['aa_ratio']:.4f}, "
                           f"|aa-1| > {kc['aa_max']}: the instrument is noisier than the effect; knob not judged")
    thr = float(kc["threshold"])
    if 2 <= kc["look_blocks"] <= nb < kc["n_blocks"] and all((ci(log_ratios(spec, units, a))[2] or 0) < thr for a in live):
        return dict(res, verdict="FUTILITY_CANDIDATE_BELOW_FLOOR", polar="FAIL", terminal=True,
                    reason=f"look at {nb} blocks: every candidate CI upper < {thr}")
    if nb < kc["n_blocks"]:
        return dict(res, verdict="INCOMPLETE", polar=None, terminal=False, reason=f"{nb}/{kc['n_blocks']} blocks scored")
    keep = [a for a in live if (ci(log_ratios(spec, units, a))[1] or 0) > thr]
    v = "KEEP_" + "+".join(keep) if keep else "NO_KEEP"
    return dict(res, verdict=v, polar=polar(v), terminal=True,
                reason=f"{nb} blocks; KEEP iff CI lower > {thr}: " +
                       ", ".join(f"{a} {ci(log_ratios(spec, units, a))}" for a in live))


def decide_smoke(spec, units):
    """The smoke rule over the smoke arm's unit(s): server answered, metric present, every knob as expected."""
    us = [u for u in units if u.get("kind") in ("smoke", "log")]
    if not us:
        return {"verdict": "SMOKE_NO_UNIT", "polar": None, "terminal": True, "reason": "no smoke unit / log found"}
    err = [u for u in us if u.get("error")]
    if err:
        return {"verdict": f"FUTILITY_HARNESS_{err[0].get('error_class') or 'SERVER'}", "polar": None, "terminal": True,
                "reason": f"{err[0].get('unit_id')}: {err[0].get('error')}"}
    mm = mismatches(us)
    if mm:
        return {"verdict": "FUTILITY_HARNESS_WITNESS", "polar": None, "terminal": True, "witness_mismatches": mm,
                "reason": "; ".join(mismatch_text(m) for m in mm[:6])}
    if any(u.get("kind") == "smoke" and u.get("metric") is None for u in us):
        return {"verdict": "FUTILITY_HARNESS_MISSING_OUTPUT", "polar": None, "terminal": True,
                "reason": f"smoke request returned no {spec['metric']['name']}"}
    return {"verdict": "SMOKE_PASS", "polar": "PASS", "terminal": True,
            "reason": f"{len(us)} unit(s); every knob witnessed as expected"}


# ---------------------------------------------------------------------------------------------------- io helpers
def load_units(out_dir, name=H.RESULTS_JSONL):
    """Unit records of a results.jsonl; the LAST record of a unit id wins (a resumed run may re-append)."""
    by, order = {}, []
    try:
        with open(os.path.join(out_dir, name)) as f:
            for ln in f:
                try:
                    u = json.loads(ln)
                except ValueError:
                    continue
                if not isinstance(u, dict) or not u.get("unit_id"):
                    continue
                if u["unit_id"] not in by:
                    order.append(u["unit_id"])
                by[u["unit_id"]] = u
    except OSError:
        pass
    return [by[k] for k in order]


def _sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def sha_bytes(b):
    return hashlib.sha256(b if isinstance(b, bytes) else str(b).encode()).hexdigest()


def logs_sha256(row_or_out):
    """One sha over every file a replay reads: out/logs/**, out/results.jsonl, out-smoke/results.jsonl (path + sha)."""
    out_dir, row = resolve_prior(row_or_out)
    files = []
    for root in (os.path.join(out_dir, "logs"),):
        for r, _d, fs in os.walk(root):
            files += [os.path.join(r, f) for f in fs]
    for p in (os.path.join(out_dir, H.RESULTS_JSONL), os.path.join(row, "out-smoke", H.RESULTS_JSONL),
              os.path.join(out_dir, H.TERMINAL_SMOKE)):
        if os.path.isfile(p):
            files.append(p)
    h = hashlib.sha256()
    for p in sorted(files):
        h.update(f"{os.path.relpath(p, row)}\0{_sha_file(p)}\n".encode())
    return h.hexdigest(), len(files)


def resolve_prior(path):
    """(out_dir, row_dir) for a prior run given its row dir or its out dir."""
    p = os.path.abspath(path)
    if os.path.isdir(os.path.join(p, "out")):
        return os.path.join(p, "out"), p
    return p, os.path.dirname(p)


def atomic_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f, indent=1, default=str)
    os.replace(tmp, path)


# ---------------------------------------------------------------------------------------------------- workload
def identity_prompts(spec, row_dir):
    c = spec.get("correctness") or {}
    if c.get("prompts"):
        return list(c["prompts"])
    ps = workload_prompts(spec, row_dir) if row_dir else list((spec.get("workload") or {}).get("prompts") or [])
    n = c.get("n_prompts")
    return ps[:n] if n else ps


def workload_prompts(spec, row_dir):
    w = spec.get("workload") or {}
    if w.get("prompts"):
        return list(w["prompts"])
    t = open(os.path.join(row_dir, w["input"]), encoding="utf-8", errors="replace").read()
    win = int(w.get("win_chars") or 6000)
    offs = w.get("offsets") or [0]
    return [t[o:o + win] + str(w.get("suffix") or "") for o in offs]


def request_body(spec, prompt, n_predict):
    body = {"prompt": prompt, "n_predict": int(n_predict), "temperature": 0.0, "top_k": 1, "seed": 0, "ignore_eos": True,
            "return_tokens": True}
    body.update((spec.get("workload") or {}).get("body") or {})
    body["cache_prompt"] = False   # forced: no slot / prompt-cache state carries across requests
    return body


# ---------------------------------------------------------------------------------------------------- the runner
class Gate:
    """One run of a declared gate. `clock`, `visit_fn`, `run_fn` are injectable for tests."""

    def __init__(self, spec, row_dir, env=None, visit_fn=None, run_fn=None, stream=None):
        validate_spec(spec)
        self.spec, self.d = spec, os.path.abspath(row_dir)
        self.env = os.environ if env is None else env
        self.out = os.path.join(self.d, "out")
        self.out_smoke = os.path.join(self.d, "out-smoke")
        self.logs = os.path.join(self.out, "logs")
        self.procs = []
        self.visit_fn = visit_fn or self._visit
        self.run_fn = run_fn or self._run_proc
        self.stream = stream or sys.stderr
        self.lv = required_lv(spec)
        self.stop_file = self.env.get("FILLER_STOPFILE") or os.path.join(self.d, "STOP")

    # ------------------------------------------------------------------ housekeeping
    def log(self, msg):
        print(f"ak_gate {self.spec['row_id']}: {msg}", file=self.stream, flush=True)

    def kill_all(self, *_a):
        while self.procs:
            H.kill_tree(self.procs.pop())

    def install_traps(self):
        import atexit
        atexit.register(self.kill_all)

        def _term(signum, _frame):
            self.kill_all()
            sys.exit(128 + signum)
        signal.signal(signal.SIGTERM, _term)

    def should_stop(self):
        dl = self.env.get("FILLER_DEADLINE")
        return H.should_stop(self.stop_file, int(dl) if dl and dl.isdigit() else None)

    def prepare(self):
        """Make every dir the row needs and check every declared input. Returns [problems] (empty = ok)."""
        for p in [self.out, self.logs, self.out_smoke] + [os.path.join(self.d, x) for x in self.spec.get("dirs") or []]:
            os.makedirs(p, exist_ok=True)
        if any("{SLOTDIR}" == str(a) for a in self.spec["server"]["argv"]):
            os.makedirs(os.path.join(self.out, "kv_slots"), exist_ok=True)
        bad = []
        for rel, want in sorted((self.spec.get("inputs") or {}).items()):
            p = os.path.join(self.d, rel)
            if not os.path.isfile(p):
                bad.append(f"input {rel} missing")
            elif want and _sha_file(p) != want:
                bad.append(f"input {rel} sha256 {_sha_file(p)[:12]} != pinned {str(want)[:12]}")
        for b in self.spec.get("binaries") or []:
            if not os.path.exists(b):
                bad.append(f"binary {b} missing")
        return bad

    def port(self):
        env = [int(x) for x in str(self.env.get("FILLER_PORTS") or "").split(",") if x.strip().isdigit()]
        return env[0] if env else H.alloc_ports(self.spec["row_id"], 1)[0]

    def subst(self, argv, port=None, extra=None):
        m = {"{PORT}": str(port), "{SLOTDIR}": os.path.join(self.out, "kv_slots"), "{OUT}": self.out, "{ROW}": self.d}
        m.update(extra or {})
        out = []
        for a in argv:
            a = str(a)
            for k, v in m.items():
                if k in a and v is not None:
                    a = a.replace(k, str(v))
            out.append(a)
        return out

    def pin(self, argv):
        cpus = H.grant_cpus(self.env, default=[])
        pre = []
        mb = (self.spec.get("server") or {}).get("membind")
        if mb is not None:
            pre += ["/usr/bin/numactl", f"--membind={mb}", "--"]
        if cpus:
            pre += ["/usr/bin/taskset", "-c", H.cpu_str(cpus)]
        return pre + list(argv)

    def proc_env(self, arm, binary=None):
        e = {"PATH": "/usr/bin:/bin", "HOME": self.env.get("HOME", "/tmp"),
             "FILLER_ID": self.env.get("FILLER_ID", self.spec["row_id"])}
        e.update({k: str(v) for k, v in ((self.spec.get("server") or {}).get("env") or {}).items()})
        if binary and "LD_LIBRARY_PATH" not in ((self.spec.get("server") or {}).get("env") or {}):
            e["LD_LIBRARY_PATH"] = os.path.dirname(os.path.realpath(binary))   # this kernel's own ggml, never inherited
        for k in self.spec["knobs"]:
            if knob_kind(self.spec, k) == "env":
                e.pop(k, None)      # a knob is only ever set by its arm
        e.update(arm_env_knobs(self.spec, arm))
        return e

    def llama_argv(self, argv, arm, port=None, flags=True, extra=None, force_lv=False):
        a = self.subst(argv, port, extra)
        if flags:
            a = a + arm_flags(self.spec, arm)
        return ensure_lv(a, self.lv, force=force_lv)

    # ------------------------------------------------------------------ processes
    def _run_proc(self, argv, env, log, timeout):
        os.makedirs(os.path.dirname(log), exist_ok=True)
        t0 = time.time()
        with open(log, "wb") as lf:
            p = subprocess.Popen(argv, stdout=lf, stderr=subprocess.STDOUT, env=env, cwd=self.d)
            self.procs.append(p)
            try:
                while p.poll() is None:
                    if self.should_stop() or time.time() - t0 > timeout:
                        H.kill_tree(p)
                        return {"rc": None, "secs": round(time.time() - t0, 1),
                                "error": "stopped" if self.should_stop() else f"timeout {timeout} s"}
                    time.sleep(0.2)
            finally:
                if p in self.procs:
                    self.procs.remove(p)
        return {"rc": p.returncode, "secs": round(time.time() - t0, 1)}

    def start_server(self, argv, env, log):
        os.makedirs(os.path.dirname(log), exist_ok=True)
        lf = open(log, "ab")
        p = subprocess.Popen(argv, stdout=lf, stderr=subprocess.STDOUT, env=env, cwd=self.d)
        lf.close()
        self.procs.append(p)
        return p

    def stop_server(self, p):
        H.kill_tree(p)
        if p in self.procs:
            self.procs.remove(p)

    def wait_ready(self, port, p, timeout):
        import urllib.request
        t0 = time.time()
        while time.time() - t0 < timeout:
            if p.poll() is not None:
                return f"server exited rc {p.returncode} before /health"
            if self.should_stop():
                return "stopped"
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=5) as r:
                    if r.status == 200:
                        return None
            except OSError:
                pass
            time.sleep(0.5)
        return f"server not ready within {timeout} s"

    def request(self, port, body, timeout):
        import urllib.request
        req = urllib.request.Request(f"http://127.0.0.1:{port}/completion", data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        t0 = time.time()
        with urllib.request.urlopen(req, timeout=timeout) as r:
            res = json.load(r)
        tm = res.get("timings") or {}
        rec = {k: tm.get(k) for k in TIMING_FIELDS}
        rec["wall_s"] = round(time.time() - t0, 3)
        rec["content_sha"] = sha_bytes(str(res.get("content", "")))[:16]
        if isinstance(res.get("tokens"), list):
            rec["tokens_sha"] = sha_bytes(json.dumps(res["tokens"]))[:16]
        return rec, res

    @staticmethod
    def kfd_vram(pid):
        d = f"/sys/class/kfd/kfd/proc/{pid}"
        try:
            return sum(int(open(os.path.join(d, f)).read().strip() or 0) for f in os.listdir(d) if f.startswith("vram_"))
        except (OSError, ValueError):
            return 0

    def _visit(self, uid, arm, prompts, n_predict, warmup, ready_timeout, kind="visit"):
        """ONE fresh server for (uid, arm): start, /health, `warmup` discarded requests, the measured requests, stop.
        Returns the unit record (witness from the server's own log)."""
        srv = self.spec["server"]
        port = self.port()
        argv = self.llama_argv(srv["argv"], arm, port)
        log = os.path.join(self.logs, f"{uid}.log")
        if os.path.exists(log):
            os.replace(log, log + f".prev-{int(time.time())}")
        t0 = time.time()
        p = self.start_server(self.pin(argv), self.proc_env(arm, argv[llama_index(argv) or 0]), log)
        u = {"unit_id": uid, "kind": kind, "arm": arm, "argv": argv, "log": os.path.relpath(log, self.out), "port": port}
        try:
            why = self.wait_ready(port, p, ready_timeout)
            u["load_s"] = round(time.time() - t0, 2)
            if why:
                return dict(u, error=why, error_class="STOPPED" if why == "stopped" else "SERVER")
            to = float(srv.get("request_timeout_s") or 1800)
            for _ in range(int(warmup)):
                self.request(port, request_body(self.spec, "Hello", 16), to)
            reqs = []
            for pr in prompts:
                rec, _res = self.request(port, request_body(self.spec, pr, n_predict), to)
                reqs.append(rec)
            u["req"] = reqs
            u["warmup_discarded"] = int(warmup)
            if srv.get("kfd_min_vram_gib"):
                u["vram_b"] = self.kfd_vram(p.pid)
        except Exception as e:  # noqa: BLE001 - a visit always records why it failed
            u.update(error=f"{e.__class__.__name__}: {e}", error_class="SERVER")
        finally:
            self.stop_server(p)
        u["secs"] = round(time.time() - t0, 2)
        return u

    def finish_unit(self, u):
        """Witness + metric from the unit's own log / requests (the same code the replay runs)."""
        if not u.get("error"):
            txt = read_log(os.path.join(self.out, u["log"])) if u.get("log") else None
            u["witness"] = witness_for(self.spec, u["arm"], txt, u.get("argv"), u.get("log"))
            if u.get("req") is not None:
                u["metric"] = metric_of(self.spec, u["req"])
            mv = (self.spec.get("server") or {}).get("kfd_min_vram_gib")
            if mv and u.get("vram_b") is not None and u["vram_b"] < float(mv) * (1 << 30):
                u.update(error=f"VRAM {u['vram_b']} B < {mv} GiB: the server did not run on the GPU",
                         error_class="RESIDENCY")
        u["gate_unit"] = True
        return u

    # ------------------------------------------------------------------ correctness
    def run_correctness_unit(self, uid, kind, arm, extra):
        c = self.spec["correctness"]
        to = float(c.get("timeout_s") or 3600)
        log = os.path.join(self.logs, f"{uid}.log")
        if kind == "c-id" and c.get("mode", "server") == "server":
            pr = identity_prompts(self.spec, self.d)[extra["prompt"]]
            u = self.visit_fn(uid, arm, [pr], int(c.get("n_predict") or 64), 0,
                              float(self.spec["server"].get("ready_timeout_s") or 900), kind="c-id")
            u["prompt"] = extra["prompt"]
            if not u.get("error"):
                r = (u.get("req") or [{}])[0]
                u["output_sha"] = r.get("tokens_sha") or r.get("content_sha")
                u["accepted_sha"] = sha_bytes(str(r.get("draft_n_accepted")))[:16]
                u["draft_sha"] = sha_bytes(str(r.get("draft_n")))[:16]
            return self.finish_correctness(u)
        if kind == "c-kld":
            base = os.path.join(self.out, "kld-base.bin")
            ex = ["--kl-divergence-base", base] + (["--kl-divergence"] if extra.get("mode") == "kld" else [])
            argv = self.llama_argv(list(c["argv"]) + ex, arm, flags=bool(c.get("apply_flags")))
        elif kind == "c-tbo":
            argv = self.subst(c["argv"])
            if c.get("lv"):
                argv = ensure_lv(argv, self.lv, force=True)
        else:   # identity, cmd mode: every (arm, prompt) in its OWN process
            argv = self.llama_argv(c["argv"], arm, flags=bool(c.get("apply_flags")),
                                   extra={"{PROMPT_INDEX}": str(extra["prompt"])}, force_lv=c.get("lv", True))
        r = self.run_fn(self.pin(argv), self.proc_env(arm, argv[llama_index(argv) or 0]), log, to)
        u = {"unit_id": uid, "kind": kind, "arm": arm, "argv": argv, "log": os.path.relpath(log, self.out),
             "rc": r.get("rc"), "secs": r.get("secs"), **extra}
        if r.get("error"):
            u.update(error=r["error"], error_class="STOPPED" if r["error"] == "stopped" else "TIMEOUT")
        return self.finish_correctness(u)

    def finish_correctness(self, u):
        c = self.spec["correctness"]
        txt = read_log(os.path.join(self.out, u["log"])) if u.get("log") else None
        if u.get("error"):
            u["gate_unit"] = True
            return u
        if c.get("witness", c["kind"] != "tbo") and not (u["kind"] == "c-kld" and u.get("mode") == "base"
                                                          and c.get("witness_base") is False):
            u["witness"] = witness_for(self.spec, u["arm"], txt, u.get("argv") if c["kind"] != "tbo" else None, u["log"])
        if u["kind"] == "c-tbo":
            cases = H.tbo_cases(txt or "")
            u.update(n_cases=len(cases), n_ok=sum(1 for x in cases if x["ok"]),
                     fails=[(x["op"] + "(" + x["args"] + ")")[:160] for x in cases if x["ok"] is not True][:20])
            u["pass"] = (u["n_cases"] >= int(c.get("min_cases") or 1) and u["n_ok"] == u["n_cases"]
                         and (u.get("rc") == 0 or not c.get("require_rc0")))
        elif u["kind"] == "c-kld":
            m = KLD_RX.findall(txt or "")
            s = SAME_TOP_RX.findall(txt or "")
            u.update(mean_kld=float(m[-1]) if m else None, same_top_p_pct=float(s[-1]) if s else None)
            if u.get("mode") == "base" and u.get("rc") not in (0, None):
                u.update(error=f"kld base run rc {u.get('rc')}", error_class="MISSING_OUTPUT")
        elif u["kind"] == "c-id" and c.get("mode", "server") == "cmd":
            got = identity_parse(c, txt)
            if got["output"] is None:
                u.update(error="no output line in the identity log", error_class="MISSING_OUTPUT")
            for f in ("output", "accepted", "draft"):
                u[f + "_sha"] = sha_bytes(json.dumps(got[f]))[:16] if got[f] is not None else None
            u["n_draft_lines"] = len(got["draft"] or [])
        u["gate_unit"] = True
        return u

    # ------------------------------------------------------------------ modes
    def smoke(self):
        """ON-arm-only smoke under a ~5 min budget: dirs + inputs first, one fresh server, one warm-up, ONE request long
        enough to reach the knob, witness check, TERMINAL-smoke.json + out-smoke/smoke_measure.json."""
        sm = dict({"arm": candidate_arms(self.spec)[0], "prompt_chars": 2000, "n_predict": 32, "budget_s": 300},
                  **(self.spec.get("smoke") or {}))
        t0 = time.time()
        try:
            bad = self.prepare()
            if bad:
                return H.end_smoke("FAIL", 3, "inputs: " + "; ".join(bad), self.out)
            prompt = (workload_prompts(self.spec, self.d) or ["Hello"])[0][:int(sm["prompt_chars"])]
            ready = min(float(self.spec["server"].get("ready_timeout_s") or 900), float(sm["budget_s"]) - 30)
            u0 = time.time()
            u = self.finish_unit(self.visit_fn(f"smoke-{sm['arm']}", sm["arm"], [prompt], int(sm["n_predict"]), 1,
                                               ready, kind="smoke"))
            unit_s = max(time.time() - u0, 0.001)
            H.append_unit(dict(u, smoke=True), self.out_smoke)
            H.write_smoke_measure(self.out_smoke, unit_s, 1, float(u.get("load_s") or 0.0) + (u0 - t0),
                                  unit_name="arm visit", extra={"arm": sm["arm"], "gate": "ak_gate"})
            d = decide_smoke(self.spec, [u])
            if time.time() - t0 > float(sm["budget_s"]):
                return H.end_smoke("FAIL", 3, f"smoke took {time.time() - t0:.0f} s > budget {sm['budget_s']} s "
                                              f"(shorten smoke.prompt_chars / n_predict)", self.out)
            if d["verdict"] != "SMOKE_PASS":
                return H.end_smoke("FAIL", 3, f"{d['verdict']}: {d['reason']}", self.out)
            return H.end_smoke("PASS", 0, f"arm {sm['arm']}: witness ok for {len(self.spec['knobs'])} knob(s); "
                                          f"{self.spec['metric']['name']}={u.get('metric')}; {unit_s:.1f} s", self.out)
        except Exception as e:  # noqa: BLE001 - the smoke always says why it failed
            return H.end_smoke("FAIL", 3, f"{e.__class__.__name__}: {e}", self.out)
        finally:
            self.kill_all()

    def run(self):
        """The full gate: inputs -> correctness first -> ABBA blocks with fresh servers -> verdict. Resumable."""
        bad = self.prepare()
        if bad:
            return self.finish([], {"verdict": "FUTILITY_HARNESS_MISSING_INPUT", "polar": None, "terminal": True,
                                    "reason": "; ".join(bad)})
        units = load_units(self.out)
        done = {u["unit_id"] for u in units if u.get("gate_unit")}
        for uid, kind, arm, extra in plan_correctness(self.spec):
            if uid in done:
                continue
            if self.should_stop():
                return 75
            u = self.run_correctness_unit(uid, kind, arm, extra)
            if u.get("error_class") == "STOPPED":
                return 75
            H.append_unit(u, self.out)
            units.append(u)
        d = decide(self.spec, units)
        if d["terminal"]:
            return self.finish(units, d)
        srv = self.spec["server"]
        w = self.spec.get("workload") or {}
        prompts = workload_prompts(self.spec, self.d)
        kc = keep_cfg(self.spec)
        for b in blocks(self.spec):
            for arm in block_order(self.spec, b):
                uid = f"b{b}-{arm}"
                if uid in done:
                    continue
                if self.should_stop():
                    return 75
                u = self.visit_fn(uid, arm, prompts, int(w.get("n_predict") or 256), int(srv.get("warmup", 1)),
                                  float(srv.get("ready_timeout_s") or 900))
                if u.get("error_class") == "STOPPED":
                    return 75
                u = self.finish_unit(dict(u, block=b))
                H.append_unit(u, self.out)
                units.append(u)
                d = decide(self.spec, units)
                if d["terminal"]:
                    return self.finish(units, d)
            if b == kc["look_blocks"]:
                self.log(f"look at block {b}: {decide(self.spec, units)['verdict']}")
        return self.finish(units, decide(self.spec, units))

    def finish(self, units, d):
        res = result_doc(self.spec, units, d)
        atomic_json(os.path.join(self.out, "RESULT.json"), res)
        self.log(f"RESULT {res['verdict']} (polar {res['polar']}): {res.get('reason', '')[:300]}")
        return 0


def identity_parse(c, txt):
    rx = {k: re.compile((c.get("rx") or {}).get(k) or v, re.M) for k, v in IDENTITY_RX.items()}
    t = txt or ""
    out = rx["output"].findall(t)
    acc = rx["accepted"].findall(t)
    return {"output": out[-1] if out else None, "accepted": acc[-1] if acc else None, "draft": rx["draft"].findall(t)}


def result_doc(spec, units, d):
    tus = [u for u in units if u.get("kind") == "visit"]
    res = {"schema": RESULT_SCHEMA, "complete": bool(d.get("terminal")), "verdict": d["verdict"], "polar": d.get("polar"),
           "reason": d.get("reason", ""), "row": spec["row_id"], "task": spec.get("task"), "utc": H.now(),
           "metric": spec["metric"], "keep": keep_cfg(spec), "per_arm": per_arm_stats(spec, units),
           "witness": witness_table(spec, units), "witness_mismatches": mismatches(units),
           "aa": {"ratio": aa_ratio(spec, units), "max": keep_cfg(spec)["aa_max"],
                  "arms": baseline_arms(spec)[:2]},
           "correctness": d.get("correctness"), "blocks_scored": len(full_blocks(spec, units)),
           "n_units": len(units), "n_visits": len(tus),
           "gate": {"module": "ak_gate.py", "version": GATE_VERSION, "sha256": _sha_file(os.path.abspath(__file__))}}
    if str(d["verdict"]).startswith(("FAIL", "FUTILITY")):
        res["evidence"] = {"keep": list(EVIDENCE_PATHS), "why": "failed gate: logs + units are the replay input"}
    return res


# ---------------------------------------------------------------------------------------------------- replay
def logs_only_units(spec, out_dir):
    """A prior run that is not an ak_gate run (hand-rolled job): every *.log under out/logs becomes one unit whose arm is
    the filename token that names a declared arm (smoke-ALL-server.log -> ALL). Logs naming no arm are skipped."""
    arms = list(spec.get("arms") or {})
    us, skipped = [], []
    root = os.path.join(out_dir, "logs")
    for r, _d, fs in os.walk(root):
        for f in sorted(fs):
            if not f.endswith((".log", ".out", ".err")):
                continue
            toks = re.split(r"[-_.]", f)
            hit = [a for a in arms if a in toks]
            rel = os.path.relpath(os.path.join(r, f), out_dir)
            if len(hit) != 1:
                skipped.append(rel)
                continue
            us.append({"unit_id": rel, "kind": "log", "arm": hit[0], "log": rel, "argv": None})
    return us, skipped


def replay_units(spec, out_dir, row_dir):
    """(units, mode, skipped): the prior run's units with witness + metric RE-DERIVED from its logs / raw timings by the
    same functions the live run uses (recorded witness / metric fields are never trusted)."""
    units = [u for u in load_units(out_dir) if u.get("gate_unit")]
    mode = "units"
    if not units:
        units = [u for u in load_units(os.path.join(row_dir, "out-smoke")) if u.get("gate_unit")]
        mode = "smoke"
    skipped = []
    if not units:
        units, skipped = logs_only_units(spec, out_dir)
        mode = "logs-only"
    c = spec.get("correctness") or {}
    out = []
    for u in units:
        u = dict(u)
        txt = read_log(os.path.join(out_dir, u["log"])) if u.get("log") else None
        if u.get("error"):
            out.append(u)
            continue
        witnessed = u["kind"] in ("visit", "smoke", "log", "c-id", "c-kld") or (u["kind"] == "c-tbo" and c.get("witness"))
        if witnessed and u.get("arm") in (spec.get("arms") or {}):
            u["witness"] = witness_for(spec, u["arm"], txt, u.get("argv") if u["kind"] != "c-tbo" else None, u.get("log"))
        if u.get("req") is not None:
            u["metric"] = metric_of(spec, u["req"])
        if u["kind"] == "c-kld" and txt is not None:
            m = KLD_RX.findall(txt)
            u["mean_kld"] = float(m[-1]) if m else None
        if u["kind"] == "c-tbo" and txt is not None:
            cases = H.tbo_cases(txt)
            u.update(n_cases=len(cases), n_ok=sum(1 for x in cases if x["ok"]))
            u["pass"] = u["n_cases"] >= int(c.get("min_cases") or 1) and u["n_ok"] == u["n_cases"] and \
                (u.get("rc") == 0 or not c.get("require_rc0"))
        if u["kind"] == "c-id" and c.get("mode", "server") == "cmd" and txt is not None:
            got = identity_parse(c, txt)
            for f in ("output", "accepted", "draft"):
                u[f + "_sha"] = sha_bytes(json.dumps(got[f]))[:16] if got[f] is not None else None
        out.append(u)
    return out, mode, skipped


def replay(spec, row_dir, prior, write_receipt=True, flags=None, stream=None):
    """The WHOLE decision path offline over a previous run's real logs + results. Returns the receipt dict; writes
    <row>/out/REPLAY-RECEIPT.json when write_receipt. No server, no GPU, no network."""
    validate_spec(spec)
    t0 = time.time()
    out_dir, prow = resolve_prior(prior)
    units, mode, skipped = replay_units(spec, out_dir, prow)
    d = decide(spec, units) if mode == "units" else decide_smoke(spec, units)
    if mode == "units" and not d["terminal"] and not [u for u in units if u.get("kind") == "visit"] and \
            any(u.get("kind") == "smoke" for u in units):
        d = decide_smoke(spec, units)
    lsha, nfiles = logs_sha256(prior)
    prev_id = os.path.basename(prow)
    for meta in (os.path.join(prow, "spec.json"), os.path.join(out_dir, "RESULT.json")):
        try:
            m = json.load(open(meta))
            prev_id = str(m.get("id") or m.get("row") or prev_id)
            break
        except (OSError, ValueError, AttributeError):
            continue
    flags = flags or os.environ.get("ROWFLOW_FLAGS") or "/mnt/raid0/llm/tmp/compute-flags"
    dd = os.path.join(flags, "dryrun", prev_id)
    fails = sorted((p for p in (os.path.join(dd, f) for f in (os.listdir(dd) if os.path.isdir(dd) else []))
                    if re.match(r"FAIL-\d+\.json$", os.path.basename(p))), key=lambda p: os.path.getmtime(p))
    lo = os.path.join(dd, "launcher.out")
    job = os.path.join(os.path.abspath(row_dir), "job.py")
    try:
        cpus = H.cpu_str(sorted(os.sched_getaffinity(0)))
    except (AttributeError, OSError):
        cpus = ""
    rec = {"schema": RECEIPT_SCHEMA, "prev_id": prev_id, "prior_out": out_dir, "mode": mode,
           "logs_sha256": lsha, "n_files": nfiles, "n_units": len(units), "skipped_logs": skipped[:40],
           "observed": {"verdict": d["verdict"], "polar": d.get("polar"), "terminal": d.get("terminal"),
                        "reason": str(d.get("reason") or "")[:1200], "n_units": len(units)},
           "verdict": d["verdict"], "witness_mismatches": mismatches(units)[:40],
           "prev_fail": fails[-1] if fails else None, "prev_fail_sha256": _sha_file(fails[-1]) if fails else None,
           "prev_launcher_out_sha256": _sha_file(lo) if os.path.isfile(lo) else None,
           "job_sha256": _sha_file(job) if os.path.isfile(job) else None,
           "gate_sha256": _sha_file(os.path.abspath(__file__)),
           "decide_cmd": f"python3 -I -B {job} --replay {out_dir}", "replayed_at": H.now(), "host_cpus": cpus,
           "elapsed_s": round(time.time() - t0, 3)}
    prev_term = os.path.join(out_dir, H.TERMINAL_SMOKE)
    try:
        rec["prev_smoke"] = {k: v for k, v in json.load(open(prev_term)).items() if k in ("verdict", "rc", "reason")}
    except (OSError, ValueError):
        rec["prev_smoke"] = None
    if write_receipt:
        atomic_json(os.path.join(os.path.abspath(row_dir), "out", RECEIPT), rec)
    print(f"REPLAY {prev_id} mode={mode} units={len(units)} -> {d['verdict']} (polar {d.get('polar')}): "
          f"{str(d.get('reason') or '')[:400]}", file=stream or sys.stdout, flush=True)
    return rec


# ---------------------------------------------------------------------------------------------------- selftest
def _synthetic_log(spec, arm, lv=MIN_LV):
    lines = [f"0.00.040.649 I cmn  common_param: verbosity = {lv} (adjust with the `-lv N` CLI arg)", "noise line"]
    for k, v in spec["knobs"].items():
        if spec["expect"][arm][k] == "present":
            m = v["marker"]
            lines.append("0.01.000.000 I " + (re.sub(r"[\\^$.*+?()\[\]{}|]", "", m[3:]) if m.startswith("re:") else m))
    return "\n".join(lines) + "\n"


def cand_all(spec):
    return candidate_arms(spec)


def stub_visit(spec, out_dir, speed):
    """A process-free visit for selftests: writes a synthetic log holding exactly the arm's expected markers and
    returns timings whose metric is `speed[arm]` x better than 1.0 (direction-aware)."""
    def fn(uid, arm, prompts, n_predict, warmup, ready_timeout, kind="visit"):
        d = os.path.join(out_dir, "logs")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, f"{uid}.log"), "w") as f:
            f.write(_synthetic_log(spec, arm))
        ms = 1000.0 / float(speed.get(arm, 1.0))   # every metric here improves as ms falls
        req = [{"prompt_n": 100, "prompt_ms": ms / 4, "predicted_n": 100, "predicted_ms": ms, "draft_n": 50,
                "draft_n_accepted": 20, "wall_s": ms / 1000, "content_sha": "x", "tokens_sha": "y"}]
        return {"unit_id": uid, "kind": kind, "arm": arm, "argv": ["llama-server", "-lv", str(MIN_LV)],
                "log": os.path.join("logs", f"{uid}.log"), "req": req, "load_s": 0.1}
    return fn


def selftest(spec, row_dir, stream=None):
    """No compute: the declaration validates; per-knob witness on synthetic logs (and a one-knob miss is named alone);
    ABBA balance; decide() reaches KEEP / NO_KEEP / A/A; the smoke and a replay run end to end against a stub visit in a
    tempdir. Nothing is written in the row dir."""
    import tempfile
    stream = stream or sys.stdout
    validate_spec(spec)
    for a in spec["arms"]:
        w = witness_for(spec, a, _synthetic_log(spec, a), ["llama-server", "-lv", "4"])
        assert all(x["ok"] for x in w.values()), (a, w)
    cand = candidate_arms(spec)[0]
    k0 = next(k for k in spec["knobs"] if spec["expect"][cand][k] == "present") if any(
        spec["expect"][cand][k] == "present" for k in spec["knobs"]) else None
    if k0:
        txt = "\n".join(ln for ln in _synthetic_log(spec, cand).splitlines()
                        if not marker_hit(spec["knobs"][k0]["marker"], [ln]))
        w = witness_for(spec, cand, txt, ["llama-server"])
        assert not w[k0]["ok"] and all(v["ok"] for k, v in w.items() if k != k0), w
        assert "argv log level none" in w[k0]["note"], w[k0]
    scored = [b for b in blocks(spec) if b >= 1]
    k = len(arm_list(spec))
    if len(scored) >= 2 * k:
        seen = {}
        for b in scored[:2 * k]:
            for pos, a in enumerate(block_order(spec, b)):
                seen.setdefault(a, []).append(pos)
        assert all(sorted(v) == sorted(list(range(k)) * 2) for v in seen.values()), seen
    sp = dict(spec, correctness=None, inputs={}, workload={"prompts": ["p"]}, dirs=[])
    quiet = open(os.devnull, "w")
    verdicts = {}
    with tempfile.TemporaryDirectory() as t:
        def gate(name, speed):
            g = Gate(sp, os.path.join(t, name), env={"FILLER_PORTS": "1"}, stream=quiet)
            g.visit_fn = stub_visit(sp, g.out, speed)
            return g
        fast = max(1.10, float(keep_cfg(sp)["threshold"]) * 1.05)
        for name, speed in (("keep", {a: fast for a in cand_all(sp)}), ("nokeep", {})):
            g = gate(name, speed)
            assert g.run() == 0
            res = json.load(open(os.path.join(g.out, "RESULT.json")))
            verdicts[name] = res["verdict"]
            if name == "keep":
                assert res["verdict"].startswith("KEEP") and res["polar"] == "PASS", res["verdict"]
            elif float(keep_cfg(sp)["threshold"]) >= 1.0:
                assert res["verdict"] in ("NO_KEEP", "FUTILITY_CANDIDATE_BELOW_FLOOR"), res["verdict"]
            r = replay(sp, g.d, g.out, write_receipt=False, flags=t, stream=quiet)
            assert r["verdict"] == res["verdict"], (r["verdict"], res["verdict"])
        if keep_cfg(sp)["aa_max"] is not None:
            g = gate("aa", {baseline_arms(sp)[1]: 1.0 + 3 * float(keep_cfg(sp)["aa_max"])})
            g.run()
            verdicts["aa"] = json.load(open(os.path.join(g.out, "RESULT.json")))["verdict"]
            assert verdicts["aa"] == "FUTILITY_HARNESS_AA", verdicts["aa"]
        g = gate("smoke", {})
        assert g.smoke() == 0, json.load(open(os.path.join(g.out, H.TERMINAL_SMOKE)))
        assert os.path.isfile(os.path.join(g.out_smoke, H.SMOKE_MEASURE))
    print(f"selftest ok ({len(spec['knobs'])} knobs x {len(spec['arms'])} arms; {verdicts})", file=stream)
    return 0


# ---------------------------------------------------------------------------------------------------- entry point
def main(spec, row_dir, argv=None, env=None):
    """job.py entry: --replay DIR [--no-receipt] | --decide-from DIR | (grant) smoke or full run."""
    argv = list(sys.argv[1:] if argv is None else argv)
    env = os.environ if env is None else env
    if "--replay" in argv or "--decide-from" in argv:
        flag = "--replay" if "--replay" in argv else "--decide-from"
        i = argv.index(flag)
        if i + 1 >= len(argv):
            print(f"usage: job.py {flag} <prior row dir | prior out dir>", file=sys.stderr)
            return 2
        try:
            rec = replay(spec, row_dir, argv[i + 1], write_receipt=(flag == "--replay" and "--no-receipt" not in argv),
                         stream=sys.stderr)
        except Exception as e:  # noqa: BLE001 - a crashed decide is the R4 finding itself: say so, rc 3
            print("DECIDE " + json.dumps({"error": f"{e.__class__.__name__}: {e}"}), flush=True)
            return 3
        print("DECIDE " + json.dumps({k: rec[k] for k in ("prev_id", "mode", "n_units", "observed", "logs_sha256",
                                                          "job_sha256", "gate_sha256")}), flush=True)
        return 0
    H.require_grant(env)   # no FILLER_ID/FILLER_DRYRUN -> exit 64: never run a row (or its smoke) by hand
    g = Gate(spec, row_dir, env=env)
    g.install_traps()
    try:
        if env.get("FILLER_SMOKE") == "1" or env.get("FILLER_DRYRUN") == "1":
            return g.smoke()
        return g.run()
    finally:
        g.kill_all()


if __name__ == "__main__":
    print("ak_gate.py is a library: the row's job.py declares SPEC and calls ak_gate.main(SPEC, D)", file=sys.stderr)
    sys.exit(2)
