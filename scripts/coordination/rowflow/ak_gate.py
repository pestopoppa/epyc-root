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
  5. a time-bounded smoke: checks inputs, visits each arm, runs a reduced correctness plan and writes
     TERMINAL-smoke.json +
     out-smoke/smoke_measure.json;
  6. resume: every unit is appended (fsync) to out/results.jsonl; a rerun skips completed unit ids;
  7. replay: `job.py --replay <prior out dir>` runs the WHOLE decision path offline (log re-parse -> witness, A/A,
     metric, KEEP rule, verdict) on a previous run's real logs/results and prints the verdict (the fix loop);
     `--decide-from <dir>` prints it as `DECIDE {json}` for the preflight R4 replay (= the R1 receipt). No writes;
  8. a standard out/RESULT.json: complete, verdict, polar, per_arm stats, witness table, A/A, correctness.

Process management: only processes this module started (captured Popen handles) are ever signalled, via
ak_row_harness.kill_tree. No quiet-host guard here (GPU gate rows); a CPU timing gate declares requires_quiet_host.
"""
import hashlib
import copy
import concurrent.futures
import json
import math
import os
import re
import signal
import shutil
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
EVIDENCE_PATHS = ("out/logs", "out/results.jsonl", "out/RESULT.json", "out/TERMINAL-smoke.json", "out-smoke")
RESULT_SCHEMA = "epyc.ak_gate.result.v1"
MIN_LV = 4
LV_BIN_RX = re.compile(r"^(?:llama-(?:server|perplexity|bench|cli|batched-bench|completion|imatrix)|test-dflash[\w.-]*)$")
LV_FLAG_NAMES = ("-lv", "--verbosity", "--log-verbosity")
LOG_VERBOSITY_RX = re.compile(r"verbosity\s*=\s*(\d+)")
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
ENV_KNOB_RX = re.compile(r"^[A-Z][A-Z0-9_]{2,}$")
ENV_NAME_RX = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")   # per-unit / per-arm env (arm_env, correctness env)
EXPECT_VALUES = ("present", "absent")
T975 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228,
        11: 2.201, 12: 2.179, 13: 2.160, 14: 2.145, 15: 2.131, 16: 2.120, 20: 2.086, 25: 2.060, 30: 2.042}
TIMING_FIELDS = ("prompt_n", "prompt_ms", "predicted_n", "predicted_ms", "draft_n", "draft_n_accepted")
KLD_RX = re.compile(r"Mean\s+KLD:\s+([-\d.eE+]+)")
SAME_TOP_RX = re.compile(r"Same top p:\s+([\d.]+)")
CORRECTNESS_KEYS = {
    "common": {"kind", "argv", "arms", "timeout_s", "apply_flags", "witness", "lv", "env"},
    "tbo": {"min_cases", "require_rc0", "ops"},
    "kld": {"base_arm", "max_kld", "max_kld_noise_k", "noise_arm", "witness_base"},
    "identity": {"mode", "prompts", "n_prompts", "n_predict", "rx", "gate_accepted", "strict_drafts"},
    "selftest_bin": {"runs", "mismatch_rx", "max_mismatch"}}
UNIT_KIND = {"c-tbo": "tbo", "c-kld": "kld", "c-id": "identity", "c-st": "selftest_bin"}
UNIT_TYPE = dict({"visit": "served", "smoke": "served", "log": "served"}, **UNIT_KIND)   # expect_by_unit scopes
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


def corr_list(spec):
    """The declared correctness units: one dict or a list of them (all must pass, run in order)."""
    c = spec.get("correctness")
    return [x for x in (c if isinstance(c, list) else [c]) if x]


def corr_of(spec, unit_kind):
    return next((c for c in corr_list(spec) if c.get("kind") == UNIT_KIND.get(unit_kind)), {})


def per_arm(v, arm, default):
    """A per-arm setting: a scalar for every arm, or {ARM: value} (arms not named get `default`)."""
    return v.get(arm, default) if isinstance(v, dict) else (default if v is None else v)


def baseline_arms(spec):
    return list(spec.get("baseline") or [])


def noise_arms(spec):
    return {c["noise_arm"] for c in corr_list(spec) if c.get("kind") == "kld" and isinstance(c.get("noise_arm"), str) and c.get("noise_arm")}


def candidate_arms(spec):
    c = spec.get("candidates")
    if c:
        return [a for a in c if a not in noise_arms(spec)]
    b = set(baseline_arms(spec)) | noise_arms(spec)
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


def marker_colon_refusal(name, marker):
    if re.search(r":\d+$", str(marker or "")):
        return (f"REFUSED: knob {name} marker ends in ':<n>' - the level separator is '::'. "
                f"FIX: --knob '{name}:<marker>::<n>'")
    return None


def command_binary(argv):
    """Find the command behind supported placement and environment wrappers."""
    if not isinstance(argv, (list, tuple)) or not argv:
        return "<missing>"
    args = list(argv)
    while args and isinstance(args[0], str) and os.path.basename(args[0]) in ("env", "taskset", "numactl"):
        wrapper = os.path.basename(args.pop(0))
        valued = {"env": {"-u", "--unset", "-C", "--chdir"},
                  "taskset": {"-c", "--cpu-list"},
                  "numactl": {"-m", "--membind", "-N", "--cpunodebind", "-C", "--physcpubind",
                              "-i", "--interleave", "-p", "--preferred", "--preferred-many"}}[wrapper]
        taskset_cpu = False
        while args and isinstance(args[0], str):
            token = args[0]
            if token == "--":
                args.pop(0)
                break
            if wrapper == "env" and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", token):
                args.pop(0)
            elif token in valued:
                taskset_cpu = wrapper == "taskset"
                args = args[2:]
            elif token.startswith("-"):
                if wrapper == "taskset" and (token.startswith("--cpu-list=") or token.startswith("-c")):
                    taskset_cpu = True
                args.pop(0)
            elif wrapper == "taskset" and not taskset_cpu:
                args.pop(0)  # positional CPU mask
                break
            else:
                break
    return str(args[0]) if args else "<missing>"


def executable_error(argv, unit):
    binary = command_binary(argv)
    path = shutil.which(binary) if os.path.dirname(binary) == "" else binary
    if not path or not os.path.isfile(path) or not os.access(path, os.X_OK):
        return f"{unit}: argv[0] {binary!r}: FIX: point argv[0] at an existing binary in the store"
    return None


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
        colon_refusal = marker_colon_refusal(k, v.get("marker"))
        if colon_refusal:
            errs.append(colon_refusal)
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
    for what, envd in [("arm_env[%s]" % a, e) for a, e in (spec.get("arm_env") or {}).items()] + \
            [("correctness %s env" % c.get("kind"), c.get("env")) for c in corr_list(spec) if c.get("env") is not None]:
        if not isinstance(envd, dict) or not all(isinstance(k, str) and ENV_NAME_RX.match(k) for k in envd):
            errs.append(f"{what}: want a {{ENV_NAME: value}} dict")
            continue
        for k in envd:
            if k in knobs:
                errs.append(f"{what}: {k} is a declared knob (only an arm sets a knob; use --arm)")
    for a in (spec.get("arm_env") or {}):
        if a not in arms:
            errs.append(f"arm_env names unknown arm {a}")
    srv = spec.get("server") or {}
    argv = srv.get("argv") or []
    if error := executable_error(argv, "server"):
        errs.append(error)
    if not argv or "{PORT}" not in [str(x) for x in argv]:
        errs.append("server.argv must be the production argv with a '{PORT}' placeholder")
    for k, v in knobs.items():
        if (v.get("kind") or ("flag" if k.startswith("-") else "env")) == "flag" and k in [str(x) for x in argv]:
            errs.append(f"flag knob {k} already in the base server argv (arms add it)")
    for rel in (spec.get("inputs") or {}):
        if rel.startswith("/") or ".." in rel.split("/"):
            errs.append(f"input {rel}: must be relative to the row dir")
    kinds = [c.get("kind") for c in corr_list(spec)]
    if len(kinds) != len(set(kinds)):
        errs.append(f"correctness: one unit per kind (got {kinds})")
    for c in corr_list(spec):
        if c.get("argv") and (error := executable_error(c["argv"], f"correctness {c.get('kind')}")):
            errs.append(error)
        if c.get("kind") in ("identity", "kld", "tbo", "selftest_bin") and c.get("arms"):
            for baseline in b:
                if baseline not in c["arms"]:
                    errs.append(f"correctness {c['kind']}: FIX: add {baseline} to the unit's arms")
        if c.get("kind") == "tbo" and "require_rc0" in c and not isinstance(c["require_rc0"], bool):
            errs.append("correctness tbo: require_rc0 must be a boolean")
        if c.get("kind") not in ("tbo", "kld", "identity", "selftest_bin"):
            errs.append(f"correctness.kind {c.get('kind')!r} not tbo|kld|identity|selftest_bin")
        else:
            bad = sorted(set(c) - CORRECTNESS_KEYS["common"] - CORRECTNESS_KEYS[c["kind"]])
            if bad:
                errs.append(f"correctness ({c['kind']}): unknown key(s) {bad}; allowed "
                            f"{sorted(CORRECTNESS_KEYS['common'] | CORRECTNESS_KEYS[c['kind']])}")
        if c.get("kind") == "identity" and c.get("n_prompts") is not None:
            n = c["n_prompts"]
            if type(n) is not int or n < 1:
                errs.append("correctness identity: n_prompts must be a positive integer")
            else:
                available = identity_prompt_count(spec, c)
                if n > available:
                    errs.append(identity_prompt_error(n, available))
        if c.get("kind") == "selftest_bin":
            try:
                if re.compile(str(c.get("mismatch_rx") or "")).groups < 1:
                    errs.append("correctness selftest_bin: mismatch_rx needs one capture group (the mismatch count)")
            except re.error as e:
                errs.append(f"correctness selftest_bin: bad mismatch_rx: {e}")
            mx = c.get("max_mismatch")
            if not isinstance(mx, dict) or not mx or any(a not in arms for a in mx):
                errs.append("correctness selftest_bin: max_mismatch {arm: N} must gate >= 1 declared arm")
        if c.get("kind") in ("tbo", "kld", "selftest_bin") and not c.get("argv"):
            errs.append(f"correctness {c.get('kind')}: argv required")
        if c.get("kind") == "identity" and c.get("mode", "server") == "cmd" and not c.get("argv"):
            errs.append("correctness identity mode cmd: argv required")
        for a in list(c.get("arms") or []) + [a for x in ("ops", "min_cases", "max_mismatch")
                                               if isinstance(c.get(x), dict) for a in c[x]]:
            if a not in arms:
                errs.append(f"correctness {c.get('kind')}: arm {a} not declared")
        noise = c.get("noise_arm") if c.get("kind") == "kld" else None
        if noise is not None and (not isinstance(noise, str) or noise not in arms or noise in b or noise == c.get("base_arm")):
            errs.append("correctness kld: noise_arm must be a declared arm distinct from the baseline")
        if c.get("max_kld_noise_k") is not None and not noise and len(baseline_arms(spec)) < 2:
            errs.append("correctness kld: max_kld_noise_k needs the OFF2 arm (KLD(OFF2 vs OFF) is the noise floor)")
    for ut, by_arm in (spec.get("expect_by_unit") or {}).items():
        if ut not in set(UNIT_TYPE.values()):
            errs.append(f"expect_by_unit {ut!r}: not one of {sorted(set(UNIT_TYPE.values()))}")
            continue
        for a, cells in (by_arm or {}).items():
            for k, e in (cells or {}).items():
                if a not in arms or k not in knobs or e not in EXPECT_VALUES + ("ignore",):
                    errs.append(f"expect_by_unit[{ut}][{a}][{k}] = {e!r}: want a declared arm/knob and present|absent|ignore")
    for side, m in (spec.get("verdict_map") or {}).items():
        if side not in ("PASS", "FAIL") or not isinstance(m, dict):
            errs.append(f"verdict_map side {side!r}: want {{PASS|FAIL: {{native verdict (prefix): name}}}}")
    def check_sampler(value, label):
        if not isinstance(value, dict):
            errs.append(f"{label}: sampler must be a dict")
            return
        for key, val in value.items():
            if key not in ("temperature", "top_k", "top_p", "min_p") or isinstance(val, bool) or not isinstance(val, (int, float)) or not math.isfinite(val) or val < 0 or (key in ("top_p", "min_p") and val > 1) or (key == "top_k" and not isinstance(val, int)):
                errs.append(f"{label}: invalid sampler {key}={val!r}")
    samplers = spec.get("sampler", {})
    for sm in (samplers if isinstance(samplers, list) else [samplers]):
        check_sampler(sm, "spec")
    if isinstance(samplers, list) and not samplers:
        errs.append("spec sampler list must not be empty")
    if "seed_base" in spec and (isinstance(spec["seed_base"], bool) or not isinstance(spec["seed_base"], int) or not 0 <= spec["seed_base"] <= 2147483647):
        errs.append("seed_base must be an integer in 0..2147483647")
    declared_units = spec.get("units", [])
    if not isinstance(declared_units, list):
        errs.append("units must be a list")
        declared_units = []
    for u in declared_units:
        if not isinstance(u, dict) or u.get("kind") != "load":
            errs.append("units: only kind load is supported")
            continue
        if u.get("argv") and (error := executable_error(u["argv"], "load unit server")):
            errs.append(error)
        if "sampler" in u:
            check_sampler(u["sampler"], "load unit")
        if not u.get("arms") or any(a not in arms for a in u["arms"]):
            errs.append("load unit arms must name declared arms")
        for key in ("blocks", "concurrency"):
            if key in u and (type(u[key]) is not int or u[key] < 1):
                errs.append(f"load unit {key} must be a positive integer")
        if u.get("metric", "ms_per_round") not in METRICS:
            errs.append("load unit metric must name a supported metric")
        if "argv" in u and (not isinstance(u["argv"], list) or "{PORT}" not in u["argv"]):
            errs.append("load unit argv must be a list containing {PORT}")
    w = spec.get("workload") or {}
    if not (w.get("prompts") or w.get("input")):
        errs.append("workload needs prompts or an input file")
    errs += witness_scope_errors(spec) + server_env_knob_errors(spec)
    if errs:
        raise SpecError("; ".join(errs))
    for c in corr_list(spec):
        if c.get("kind") == "tbo" and c.get("require_rc0") is False:
            print(f"WARNING ak_gate {spec['row_id']}: tbo require_rc0=false; nonzero exit codes are accepted",
                  file=sys.stderr, flush=True)
    return True


def server_env_knob_errors(spec):
    """q8wt-r3 (2026-11-25): proc_env strips a server.env key that is a declared knob, so a knob set in --server-env
    never reaches ANY arm (OFF/OFF2 silently ran the stock path). Refused: set it per arm instead."""
    knobs = spec.get("knobs") or {}
    return [f"server-env knob: server.env sets {k}={v}, but {k} is a declared knob and ak_gate strips it from every arm; "
            f"set it per arm: --arm OFF:{k}={v} (and on every arm that should carry it)"
            for k, v in ((spec.get("server") or {}).get("env") or {}).items() if k in knobs]


NO_LV_BINARIES = ("test-backend-ops",)   # takes no -lv: prints no INFO witness line, ever


def witness_scope_errors(spec):
    """Witness scope per unit (gate rehearsal 2026-11-25): every (arm, knob) a correctness unit is JUDGED on with an
    effective expectation `present` must be one that unit's binary can print. Refused: a witnessed tbo unit (or any unit
    whose binary is test-backend-ops) expecting a marker (no -lv, no INFO line); a non-served unit expecting a FLAG
    knob it does not get (no apply_flags: the flag is only on the server argv). FIX: expect_by_unit[<unit>][<arm>]
    [<knob>] = "ignore"."""
    errs = []
    knobs = spec.get("knobs") or {}
    arms = spec.get("arms") or {}
    for c in corr_list(spec):
        ut = c.get("kind")
        if ut not in ("tbo", "kld", "identity", "selftest_bin"):
            continue
        if ut == "tbo" and not c.get("witness"):
            continue   # an unwitnessed tbo unit is never judged
        if witness_exempt(spec, ut):
            continue
        argv = [str(x) for x in (c.get("argv") or [])]
        binary = os.path.basename(argv[0]) if argv and not str(argv[0]).startswith("@@") else ""
        no_lv = ut == "tbo" or binary in NO_LV_BINARIES
        for a in (c.get("arms") or list(arms)):
            for k, v in knobs.items():
                if expect_of(spec, a, k, ut) != "present":
                    continue
                kind = v.get("kind") or ("flag" if k.startswith("-") else "env")
                if no_lv:
                    errs.append(f"witness scope: {ut} unit ({binary or 'test-backend-ops'}) is judged on {k} = present for "
                                f"arm {a}, but test-backend-ops takes no -lv and never prints a witness line; set "
                                f"expect_by_unit.{ut}.{a}.{k} = \"ignore\" (or drop witness:true)")
                elif kind == "flag" and not c.get("apply_flags"):
                    errs.append(f"witness scope: {ut} unit is judged on flag knob {k} = present for arm {a}, but the flag "
                                f"is only on the server argv (no apply_flags); set expect_by_unit.{ut}.{a}.{k} = "
                                f"\"ignore\" or apply_flags: true")
    return errs


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


def expect_of(spec, arm, knob, unit_type="served"):
    """expect_by_unit[unit_type][arm][knob] (present|absent|ignore) when declared, else expect[arm][knob]."""
    e = ((spec.get("expect") or {}).get(arm) or {}).get(knob)
    return (((spec.get("expect_by_unit") or {}).get(unit_type) or {}).get(arm) or {}).get(knob, e)


# test-backend-ops takes no -lv, so it can never print the INFO witness lines: exempt from witness expectations unless
# the row lists "tbo" in expect_by_unit. kld / identity / selftest_bin run llama binaries at -lv and stay witnessed.
WITNESS_EXEMPT_UNIT_TYPES = ("tbo",)


def witness_exempt(spec, unit_type):
    return unit_type in WITNESS_EXEMPT_UNIT_TYPES and unit_type not in (spec.get("expect_by_unit") or {})


def witness_for(spec, arm, text, argv=None, log=None, unit_type="served"):
    """{knob: {expected, observed, ok, line, lines_scanned, log, argv_lv, log_lv, lv_required, note}} - one entry per knob,
    each judged ALONE against expect[arm][knob]. Never an AND over knobs."""
    if witness_exempt(spec, unit_type):
        return {}
    lines = (text or "").splitlines()
    out = {}
    m = LOG_VERBOSITY_RX.findall(text or "")
    log_lv = int(m[0]) if m else None
    alv = argv_lv(argv) if argv else None
    for k, v in (spec.get("knobs") or {}).items():
        exp = expect_of(spec, arm, k, unit_type)
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
        out[k] = {"expected": exp, "observed": obs, "ok": obs == exp or exp == "ignore", "line": ln, "lines_scanned": len(lines),
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
    """[(unit_id, kind, arm, extra)] of every declared correctness unit, in run order."""
    return [p for c in corr_list(spec) for p in _plan_one(spec, c)]


def _plan_one(spec, c):
    kind = c.get("kind")
    if not kind:
        return []
    b, cand = baseline_arms(spec), candidate_arms(spec)
    if kind == "tbo":
        return [(f"c-tbo-{a}", "c-tbo", a, {}) for a in (c.get("arms") or b + cand)]
    if kind == "selftest_bin":   # N fresh processes per arm, interleaved run by run
        arms = c.get("arms") or b + cand
        return [(f"c-st-{a}-r{r}", "c-st", a, {"run": r}) for r in range(1, int(c.get("runs") or 1) + 1) for a in arms]
    if kind == "kld":
        base = c.get("base_arm") or b[0]
        arms = list(c.get("arms") or [x for x in b if x != base] + cand)
        if c.get("noise_arm") and c["noise_arm"] not in arms:
            arms.append(c["noise_arm"])
        return [(f"c-kld-base-{base}", "c-kld", base, {"mode": "base"})] + [(f"c-kld-{a}", "c-kld", a, {"mode": "kld"})
                                                                             for a in arms]
    n = int(c.get("n_prompts") or len(identity_prompts(spec, None)) or 1)
    arms = [a for a in (c.get("arms") or b + cand) if a not in noise_arms(spec)]
    return [(f"c-id-{a}-p{i}", "c-id", a, {"prompt": i}) for i in range(n) for a in arms]


def smoke_spec(spec):
    """Reduce repetitions while retaining each declared correctness arm and the full judge."""
    reduced = copy.deepcopy(spec)
    for c in corr_list(reduced):
        if c["kind"] == "identity":
            c["n_prompts"] = 1
            c["n_predict"] = min(int(c.get("n_predict") or 64), int((spec.get("smoke") or {}).get("n_predict", 32)))
            arms = list(c.get("arms") or baseline_arms(spec) + candidate_arms(spec))
            c["arms"] = list(dict.fromkeys(baseline_arms(spec)[:2] + arms))
        elif c["kind"] == "selftest_bin":
            c["runs"] = 1
        elif c["kind"] == "tbo":
            ops = c.get("ops")
            if isinstance(ops, dict):
                c["ops"] = {a: str(v).split(",")[0] for a, v in ops.items()}
            elif ops:
                c["ops"] = str(ops).split(",")[0]
            c["min_cases"] = 1
    return reduced


def tbo_pass(c, u):
    """rc 0, zero explicit FAIL cases, every case that ran OK, and at least the arm's min_cases ran (a crash or a too-short
    -o list is not a pass). "not supported" cases are skipped (n_skipped), never failures; n_cases counts cases that ran."""
    return (int(u.get("n_cases") or 0) >= int(per_arm(c.get("min_cases"), u["arm"], 1)) and u.get("n_ok") == u.get("n_cases")
            and not u.get("n_fail") and (u.get("rc") == 0 or c.get("require_rc0") is False))


def tbo_counts(cases):
    ran = [x for x in cases if not x.get("skipped")]
    return dict(n_cases=len(ran), n_ok=sum(1 for x in ran if x["ok"]), n_fail=sum(1 for x in ran if x["ok"] is False),
                n_skipped=len(cases) - len(ran),
                fails=[(x["op"] + "(" + x["args"] + ")")[:160] for x in ran if x["ok"] is not True][:20])


def decide_correctness(spec, units):
    """(verdict or None, detail, complete) over every declared correctness unit: the first failing one decides; all
    must pass. None + complete = passed."""
    cs = corr_list(spec)
    if not cs:
        return None, {"kind": None}, True
    dets = []
    for c in cs:
        v, det, done = _decide_one(spec, c, units)
        if not done or v:
            return v, det, done
        dets.append(det)
    return None, (dets[0] if len(dets) == 1 else {"kind": "+".join(c["kind"] for c in cs), "parts": dets}), True


def _decide_one(spec, c, units):
    try:
        return _decide_one_impl(spec, c, units)
    except Exception as e:
        return "FUTILITY_HARNESS_DECIDE", {"kind": c.get("kind"), "why":
                f"{type(e).__name__}: {e}; unit {c.get('kind')} arms {c.get('arms') or list(spec.get('arms') or {})}"}, True


def _decide_one_impl(spec, c, units):
    plan = _plan_one(spec, c)
    by = {u.get("unit_id"): u for u in correctness_units(units)}
    missing = [(uid, arm) for uid, _kind, arm, _extra in plan if not isinstance(by.get(uid), dict)]
    if missing:
        uid, arm = next(((uid, arm) for uid, arm in missing if arm in baseline_arms(spec)), missing[0])
        verdict = "FUTILITY_HARNESS_NO_BASELINE" if arm in baseline_arms(spec) else "FUTILITY_HARNESS_DECIDE"
        return verdict, {"kind": c["kind"], "why": f"MissingRecord: missing unit {uid} arm {arm}"}, True
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
        bad = [u for u in us if not tbo_pass(c, u)]
        det = {"kind": kind, "per_arm": {u["arm"]: dict({k: u.get(k) for k in ("n_cases", "n_ok", "n_fail", "n_skipped", "rc", "fails")},
                                                       min_cases=int(per_arm(c.get("min_cases"), u["arm"], 1)))
                                         for u in us}}
        if any(u["arm"] in baseline_arms(spec) for u in bad):   # the reference itself fails: harness/baseline broken, not the knob
            return "FUTILITY_HARNESS_BASELINE", dict(det, failed=[u["unit_id"] for u in bad],
                                                     why="baseline arm fails the tbo unit; a candidate is judged only when OFF passes"), True
        return ("FAIL_CORRECTNESS", dict(det, failed=[u["unit_id"] for u in bad]), True) if bad else (None, det, True)
    if kind == "kld":
        mx = float(c.get("max_kld", 0.003))
        kl = {u["arm"]: u.get("mean_kld") for u in us if u.get("mode") == "kld"}
        det = {"kind": kind, "mean_kld": kl, "max_kld_abs": mx}
        if any(v is None for v in kl.values()):
            return "FUTILITY_HARNESS_MISSING_OUTPUT", dict(det, why="no 'Mean KLD' in a perplexity log"), True
        k = c.get("max_kld_noise_k")
        noise_arm = c.get("noise_arm") or next(iter(baseline_arms(spec)[1:2]), None)
        det["kld_floor_source"] = noise_arm if k is not None else None
        det["noise_kld"] = kl.get(noise_arm) if noise_arm else None
        if k is not None:
            if not noise_arm or kl.get(noise_arm) is None:
                return "FUTILITY_HARNESS_MISSING_OUTPUT", dict(det, why=f"no {noise_arm or 'OFF2'} KLD for the noise-floor bound"), True
            mx = max(mx, float(k) * kl[noise_arm])
        det["max_kld"] = mx
        bad = [a for a in candidate_arms(spec) if a in kl and kl[a] > mx]
        return ("FAIL_CORRECTNESS", dict(det, failed=bad), True) if bad else (None, det, True)
    if kind == "selftest_bin":
        tot = {}
        for u in us:
            tot[u["arm"]] = tot.get(u["arm"], 0) + int(u.get("mismatches") or 0)
        det = {"kind": kind, "mismatches": tot, "max_mismatch": c["max_mismatch"], "runs": int(c.get("runs") or 1)}
        bad = [a for a, mx in c["max_mismatch"].items() if tot.get(a, 0) > int(mx)]
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
        if not isinstance(r, dict):
            return "FUTILITY_HARNESS_NO_BASELINE", dict(det, why=f"missing baseline record: unit {kind} prompt {p} arm {ref}"), True
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
    try:
        return _decide_public(spec, units)
    except Exception as e:
        return decide_error(e, "decision", "unknown")


def decide_error(e, unit, arm):
    return {"verdict": "FUTILITY_HARNESS_DECIDE", "polar": None, "terminal": True,
            "reason": f"{type(e).__name__}: {e}; unit {unit} arm {arm}"}


def _decide_public(spec, units):
    """_decide() with the row's declared verdict names (spec.verdict_map {PASS|FAIL: {native verdict or prefix: name}}):
    a mapped verdict takes its side as `polar` and keeps the native one in native_verdict."""
    units = [u for u in units if u.get("kind") != "load" and not u.get("report_only")]
    points = spec.get("sampler")
    if isinstance(points, list) and len(points) > 1:
        ds = [_decide(spec, [u for u in units if u.get("kind") != "visit" or u.get("sampler_index") == i])
              for i in range(len(points))]
        failures = [d for d in ds if d["terminal"] and d["verdict"].startswith(("FUTILITY_HARNESS", "FAIL_CORRECTNESS"))]
        if failures:
            d = failures[0]
        elif not all(x["terminal"] for x in ds):
            d = dict(ds[0], verdict="INCOMPLETE", polar=None, terminal=False, reason="sampler points pending")
        else:
            d = next((x for x in ds if x.get("polar") == "PASS"), ds[-1])
        d = dict(d, sampler_decisions=ds)
    else:
        d = _decide(spec, units)
    v = str(d.get("verdict") or "")
    for side, m in (spec.get("verdict_map") or {}).items():
        for native, name in m.items():
            if d.get("terminal") and (v == native or v.startswith(native + "_")):
                return dict(d, verdict=name, polar=side, native_verdict=v)
    return d


def _decide(spec, units):
    try:
        return _decide_impl(spec, units)
    except Exception as e:
        return decide_error(e, "keep rule", "unknown")


def _decide_impl(spec, units):
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
def identity_prompt_count(spec, c):
    if c.get("prompts"):
        return len(c["prompts"])
    w = spec.get("workload") or {}
    if w.get("prompts"):
        return len(w["prompts"])
    return len(w.get("offsets") or [0]) if w.get("input") else 0


def identity_prompt_error(n, available):
    return (f"correctness identity: n_prompts={n} exceeds available prompts ({available}); "
            f"FIX: set n_prompts <= {available}")


def identity_prompts(spec, row_dir):
    c = corr_of(spec, "c-id")
    n = c.get("n_prompts")
    available = identity_prompt_count(spec, c)
    if n is not None and type(n) is int and n > available:
        raise SpecError(identity_prompt_error(n, available))
    if c.get("prompts"):
        return list(c["prompts"])
    ps = workload_prompts(spec, row_dir) if row_dir else list((spec.get("workload") or {}).get("prompts") or [])
    return ps[:n] if n else ps


def workload_prompts(spec, row_dir):
    w = spec.get("workload") or {}
    if w.get("prompts"):
        return list(w["prompts"])
    t = open(os.path.join(row_dir, w["input"]), encoding="utf-8", errors="replace").read()
    win = int(w.get("win_chars") or 6000)
    offs = w.get("offsets") or [0]
    return [t[o:o + win] + str(w.get("suffix") or "") for o in offs]


def request_body(spec, prompt, n_predict, sampler=None, prompt_index=0):
    body = {"prompt": prompt, "n_predict": int(n_predict), "temperature": 0.0, "top_k": 1, "seed": 0, "ignore_eos": True,
            "return_tokens": True}
    body.update((spec.get("workload") or {}).get("body") or {})
    row_sampler = spec.get("sampler", {})
    if isinstance(row_sampler, list):
        row_sampler = row_sampler[0]
    body.update(row_sampler)
    body.update(sampler or {})
    body["seed"] = (spec.get("seed_base", 0) + prompt_index) % 2147483648
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

    def proc_env(self, arm, binary=None, unit_env=None):
        e = {"PATH": "/usr/bin:/bin", "HOME": self.env.get("HOME", "/tmp"),
             "FILLER_ID": self.env.get("FILLER_ID", self.spec["row_id"])}
        e.update({k: str(v) for k, v in ((self.spec.get("server") or {}).get("env") or {}).items()})
        if binary and "LD_LIBRARY_PATH" not in ((self.spec.get("server") or {}).get("env") or {}):
            e["LD_LIBRARY_PATH"] = os.path.dirname(os.path.realpath(binary))   # this kernel's own ggml, never inherited
        e.update({k: str(v) for k, v in (unit_env or {}).items()})                          # this unit's own env
        e.update({k: str(v) for k, v in ((self.spec.get("arm_env") or {}).get(arm) or {}).items()})   # this arm's env
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
        if getattr(self, "smoke_deadline", None):
            timeout = min(timeout, max(0.001, self.smoke_deadline - t0))
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
        cfg = getattr(self, "current_unit", {})
        argv = self.llama_argv(cfg.get("argv", srv["argv"]), arm, port)
        log = os.path.join(self.logs, f"{uid}.log")
        if os.path.exists(log):
            os.replace(log, log + f".prev-{int(time.time())}")
        t0 = time.time()
        uenv = (corr_of(self.spec, kind) or {}).get("env") if kind in UNIT_KIND else None
        p = self.start_server(self.pin(argv), self.proc_env(arm, argv[llama_index(argv) or 0], uenv), log)
        u = {"unit_id": uid, "kind": kind, "arm": arm, "argv": argv, "log": os.path.relpath(log, self.out), "port": port}
        try:
            why = self.wait_ready(port, p, ready_timeout)
            u["load_s"] = round(time.time() - t0, 2)
            if why:
                return dict(u, error=why, error_class="STOPPED" if why == "stopped" else "SERVER")
            to = float(srv.get("request_timeout_s") or 1800)
            if getattr(self, "smoke_deadline", None):
                to = min(to, max(0.001, self.smoke_deadline - time.time()))
            def request_timeout():
                if getattr(self, "smoke_deadline", None):
                    remaining = self.smoke_deadline - time.time()
                    if remaining <= 0:
                        raise TimeoutError("smoke.budget_s exhausted")
                    return min(to, remaining)
                return to
            for _ in range(int(warmup)):
                self.request(port, request_body(self.spec, "Hello", 16), request_timeout())
            def one(item):
                i, pr = item
                return self.request(port, request_body(self.spec, pr, n_predict, cfg.get("sampler"), i + cfg.get("prompt_index", 0)), request_timeout())[0]
            concurrency = cfg.get("concurrency", 1)
            if concurrency > 1:
                with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
                    reqs = list(pool.map(one, enumerate(prompts)))
            else:
                reqs = [one(item) for item in enumerate(prompts)]
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
                u.update(error=f"KFD VRAM {u['vram_b']} B < server.kfd_min_vram_gib {mv} GiB; verify GPU residency and lower server.kfd_min_vram_gib to the measured footprint",
                         error_class="RESIDENCY")
        u["gate_unit"] = True
        return u

    # ------------------------------------------------------------------ correctness
    def run_correctness_unit(self, uid, kind, arm, extra):
        c = corr_of(self.spec, kind)
        to = float(c.get("timeout_s") or 3600)
        log = os.path.join(self.logs, f"{uid}.log")
        if kind == "c-id" and c.get("mode", "server") == "server":
            prompts = identity_prompts(self.spec, self.d)
            if not 0 <= extra["prompt"] < len(prompts):
                return {"unit_id": uid, "kind": kind, "arm": arm, "gate_unit": True,
                        "error_class": "DECIDE", "error": f"IndexError: prompt {extra['prompt']} unavailable; unit {uid} arm {arm}"}
            pr = prompts[extra["prompt"]]
            self.current_unit = {"sampler": {"temperature": 0.0, "top_k": 1}, "prompt_index": extra["prompt"]}
            u = self.visit_fn(uid, arm, [pr], int(c.get("n_predict") or 64), 0,
                              float(self.spec["server"].get("ready_timeout_s") or 900), kind="c-id")
            u["prompt"] = extra["prompt"]
            if not u.get("error"):
                r = (u.get("req") or [None])[0] or {}
                u["output_sha"] = r.get("tokens_sha") or r.get("content_sha")
                u["accepted_sha"] = sha_bytes(str(r.get("draft_n_accepted")))[:16]
                u["draft_sha"] = sha_bytes(str(r.get("draft_n")))[:16]
            return self.finish_correctness(u)
        if kind == "c-kld":
            base = os.path.join(self.out, "kld-base.bin")
            ex = ["--kl-divergence-base", base] + (["--kl-divergence"] if extra.get("mode") == "kld" else [])
            argv = self.llama_argv(list(c["argv"]) + ex, arm, flags=bool(c.get("apply_flags")))
        elif kind == "c-tbo":
            ops = per_arm(c.get("ops"), arm, None)
            argv = self.subst(list(c["argv"]) + (["-o", str(ops)] if ops else []))
            if c.get("lv"):
                argv = ensure_lv(argv, self.lv, force=True)
        elif kind == "c-st":    # a declared A/A self-test binary, one fresh process per run
            argv = self.llama_argv(c["argv"], arm, flags=bool(c.get("apply_flags")), force_lv=c.get("lv", True))
        else:   # identity, cmd mode: every (arm, prompt) in its OWN process
            argv = self.llama_argv(c["argv"], arm, flags=bool(c.get("apply_flags")),
                                   extra={"{PROMPT_INDEX}": str(extra["prompt"])}, force_lv=c.get("lv", True))
        try:
            r = self.run_fn(self.pin(argv), self.proc_env(arm, argv[llama_index(argv) or 0], c.get("env")), log, to)
        except OSError as e:
            r = {"rc": None, "error": f"{type(e).__name__}: {e}"}
        u = {"unit_id": uid, "kind": kind, "arm": arm, "argv": argv, "log": os.path.relpath(log, self.out),
             "rc": r.get("rc"), "secs": r.get("secs"), **extra}
        if r.get("error"):
            u.update(error=r["error"], error_class="STOPPED" if r["error"] == "stopped" else ("MISSING_OUTPUT" if r["error"].startswith(("FileNotFoundError", "PermissionError")) else "TIMEOUT"))
        return self.finish_correctness(u)

    def finish_correctness(self, u):
        c = corr_of(self.spec, u["kind"])
        txt = read_log(os.path.join(self.out, u["log"])) if u.get("log") else None
        if u.get("error"):
            u["gate_unit"] = True
            return u
        if c.get("witness", c["kind"] != "tbo") and not (u["kind"] == "c-kld" and u.get("mode") == "base"
                                                          and c.get("witness_base") is False):
            u["witness"] = witness_for(self.spec, u["arm"], txt, u.get("argv") if c["kind"] != "tbo" else None, u["log"],
                                       UNIT_TYPE[u["kind"]])
        if u["kind"] == "c-tbo":
            cases = H.tbo_cases(txt or "")
            u.update(tbo_counts(cases))
            u["pass"] = tbo_pass(c, u)
        elif u["kind"] == "c-kld":
            m = KLD_RX.findall(txt or "")
            s = SAME_TOP_RX.findall(txt or "")
            u.update(mean_kld=float(m[-1]) if m else None, same_top_p_pct=float(s[-1]) if s else None)
            if u.get("mode") == "base" and u.get("rc") not in (0, None):
                u.update(error=f"kld base run rc {u.get('rc')}", error_class="MISSING_OUTPUT")
        elif u["kind"] == "c-st":
            u.update(selftest_parse(c, txt))
            if u["mismatches"] is None:
                u.update(error=f"no mismatch_rx match in the self-test log (rc {u.get('rc')})", error_class="MISSING_OUTPUT")
        elif u["kind"] == "c-id" and c.get("mode", "server") == "cmd":
            got = identity_parse(c, txt)
            if got["output"] is None:
                u.update(error="no output line in the identity log", error_class="MISSING_OUTPUT")
            for f in ("output", "accepted", "draft"):
                u[f + "_sha"] = sha_bytes(json.dumps(got[f]))[:16] if got[f] is not None else None
            u["n_draft_lines"] = len(got["draft"] or [])
        u["gate_unit"] = True
        return u

    def unit_key(self, uid, kind, arm, extra):
        """Fail closed when any input needed to identify a unit cannot be read."""
        try:
            c = corr_of(self.spec, kind) if kind in UNIT_KIND else {}
            server = self.spec["server"]
            binaries = [server["argv"][0]]
            if c.get("argv"):
                binaries.append(c["argv"][0])
            inputs = {p: _sha_file(os.path.join(self.d, p)) for p in (self.spec.get("inputs") or {})}
            w = self.spec.get("workload") or {}
            if w.get("input"):
                inputs[w["input"]] = _sha_file(os.path.join(self.d, w["input"]))
            prompts = workload_prompts(self.spec, self.d)
            if kind == "c-id":
                prompts = identity_prompts(self.spec, self.d)
            base_sha = _sha_file(os.path.join(self.out, "kld-base.bin")) if kind == "c-kld" and extra.get("mode") == "kld" else None
            key = {"kld_base_sha": base_sha, "unit_id": uid, "kind": kind, "arm": arm, "extra": extra,
                   "binaries": [(p, _sha_file(p)) for p in binaries],
                   "harness": {p: _sha_file(os.path.join(self.d, p)) for p in ("ak_gate.py", "ak_row_harness.py")},
                   "server": server, "knobs": self.spec.get("knobs"), "arms": self.spec.get("arms"),
                   "arm_env": self.spec.get("arm_env"), "expect": self.spec.get("expect"),
                   "expect_by_unit": self.spec.get("expect_by_unit"), "correctness": c,
                   "workload": w, "prompts_sha": sha_bytes(json.dumps(prompts, ensure_ascii=False)),
                   "inputs": inputs, "sampler": self.spec.get("sampler"), "seed_base": self.spec.get("seed_base"),
                   "smoke": self.spec.get("smoke") if kind == "smoke" else None,
                   "metric": self.spec.get("metric") if kind == "smoke" else None}
            return sha_bytes(json.dumps(key, sort_keys=True, ensure_ascii=False))
        except (OSError, ValueError, KeyError, TypeError):
            return None

    def mark_reusable(self, u, extra):
        kind = u.get("kind")
        if kind not in UNIT_KIND and kind != "smoke":
            return u
        key = self.unit_key(u["unit_id"], kind, u["arm"], extra)
        if not key or u.get("error") or ("rc" in u and u["rc"] != 0):
            return u
        if kind == "c-tbo":
            verdict = ("PASS" if u["pass"] else "FAIL") if isinstance(u.get("pass"), bool) and u.get("n_cases", 0) > 0 else None
        elif kind == "c-kld":
            verdict = "RECORDED" if (extra.get("mode") == "base" and os.path.isfile(os.path.join(self.out, "kld-base.bin"))) or u.get("mean_kld") is not None else None
        elif kind == "c-st":
            verdict = "RECORDED" if u.get("mismatches") is not None else None
        elif kind == "c-id":
            verdict = "RECORDED" if u.get("output_sha") and u.get("accepted_sha") else None
        else:
            verdict = decide_smoke(self.spec, [u])["verdict"] if u.get("req") and u.get("metric") is not None else None
        if verdict:
            u.update(reuse_key=key, unit_verdict=verdict)
            if kind == "c-kld" and extra.get("mode") == "base":
                u["base_sha256"] = _sha_file(os.path.join(self.out, "kld-base.bin"))
        return u

    def reuse_unit(self, uid, kind, arm, extra):
        if kind not in UNIT_KIND and kind != "smoke":
            return None
        key = self.unit_key(uid, kind, arm, extra)
        if not key:
            return None
        try:
            with open(os.path.join(self.d, "spec.json")) as f:
                pred = json.load(f).get("supersedes") or []
        except (OSError, ValueError):
            return None
        for pid in [pred] if isinstance(pred, str) else pred:
            if not isinstance(pid, str) or not pid or os.path.basename(pid) != pid or pid in (".", ".."):
                continue
            prior = os.path.join(os.path.dirname(self.d), pid, "out")
            for u in load_units(prior):
                if (u.get("unit_id") != uid or u.get("kind") != kind or u.get("arm") != arm
                        or u.get("reuse_key") != key or not u.get("unit_verdict") or u.get("error")
                        or ("rc" in u and u["rc"] != 0)):
                    continue
                try:
                    if u.get("log"):
                        rel = u["log"]
                        if os.path.isabs(rel) or os.path.commonpath([prior, os.path.abspath(os.path.join(prior, rel))]) != prior:
                            continue
                        shutil.copyfile(os.path.join(prior, rel), os.path.join(self.out, rel))
                    if kind == "c-kld" and extra.get("mode") == "base":
                        base = os.path.join(prior, "kld-base.bin")
                        if not u.get("base_sha256") or _sha_file(base) != u["base_sha256"]:
                            continue
                        shutil.copyfile(base, os.path.join(self.out, "kld-base.bin"))
                except (OSError, ValueError):
                    continue
                u = dict(u, reused_from=pid)
                H.append_unit(u, self.out)
                self.log(f"UNIT-REUSED {uid} from {pid}")
                return u
        return None

    # ------------------------------------------------------------------ modes
    def smoke(self):
        """Visit every arm and run one reduced correctness plan within the smoke budget."""
        sm = dict({"arm": candidate_arms(self.spec)[0], "prompt_chars": 2000, "n_predict": 32, "budget_s": 300},
                  **(self.spec.get("smoke") or {}))
        t0 = time.time()
        self.smoke_deadline = t0 + float(sm["budget_s"])
        try:
            bad = self.prepare()
            if bad:
                return H.end_smoke("FAIL", 3, "inputs: " + "; ".join(bad), self.out)
            prompt = (workload_prompts(self.spec, self.d) or ["Hello"])[0][:int(sm["prompt_chars"])]
            units = []
            u0 = time.time()
            for arm in self.spec["arms"]:
                remaining = float(sm["budget_s"]) - (time.time() - t0)
                if remaining <= 0:
                    return H.end_smoke("FAIL", 3, "smoke budget exceeded; adjust smoke.budget_s", self.out)
                ready = min(float(self.spec["server"].get("ready_timeout_s") or 900), remaining)
                uid = f"smoke-{arm}"
                u = self.finish_unit(self.visit_fn(uid, arm, [prompt], int(sm["n_predict"]), 1,
                                                   ready, kind="smoke"))
                H.append_unit(u, self.out)
                units.append(u)
                H.append_unit(dict(u, smoke=True), self.out_smoke)
                d = decide_smoke(self.spec, units)
                if d["verdict"] != "SMOKE_PASS":
                    fix = ("Verify GPU residency and adjust server.kfd_min_vram_gib to the measured footprint"
                           if d["verdict"] == "FUTILITY_HARNESS_RESIDENCY" else
                           "Check expect.<arm>.<knob>, expect_by_unit.served, knobs.<knob>.marker and server.argv")
                    if d.get("witness_mismatches"):
                        mismatch = d["witness_mismatches"][0]
                        fix = f"Check expect.{mismatch['arm']}.{mismatch['knob']}, expect_by_unit.served.{mismatch['arm']}.{mismatch['knob']}, knobs.{mismatch['knob']}.marker and server.argv"
                    return H.end_smoke("FAIL", 3, f"{d['verdict']}: {d['reason']}", self.out,
                                       extra={"verdict": d["verdict"], "fix": fix, "failclass": {"side": "harness"}})
            # Run the same correctness units and judge as the full run, against a reduced plan.
            original_spec = self.spec
            self.spec = smoke_spec(original_spec)
            correctness = []
            try:
                for uid, kind, arm, extra in plan_correctness(self.spec):
                    remaining = self.smoke_deadline - time.time()
                    if remaining <= 0:
                        return H.end_smoke("FAIL", 3, "smoke budget exceeded; adjust smoke.budget_s", self.out)
                    c = corr_of(self.spec, kind)
                    c["timeout_s"] = min(float(c.get("timeout_s") or 3600), remaining)
                    self.spec["server"]["ready_timeout_s"] = min(float(self.spec["server"].get("ready_timeout_s") or 900), remaining)
                    u = self.run_correctness_unit(uid, kind, arm, extra)
                    correctness.append(u)
                    H.append_unit(dict(u, smoke=True), self.out_smoke)
                verdict, detail, _ = decide_correctness(self.spec, correctness)
                if verdict:
                    reason = json.dumps(detail, sort_keys=True)[:1200]
                    kind = detail.get("kind", "unknown")
                    fix = {"FUTILITY_HARNESS_WITNESS": f"Check correctness[{kind}].argv and expect_by_unit.{kind} for the named arm and knob",
                           "FUTILITY_HARNESS_NONDET": "Fix correctness[identity].argv or server.argv and baseline arm settings to make A/A deterministic",
                           "FUTILITY_HARNESS_MISSING_OUTPUT": f"Fix correctness[{kind}].argv executable path and output flags"}.get(
                               verdict, f"Check correctness[{kind}].argv and unit logs")
                    if detail.get("witness_mismatches"):
                        mismatch = detail["witness_mismatches"][0]
                        fix = f"Check expect_by_unit.{kind}.{mismatch['arm']}.{mismatch['knob']}, knobs.{mismatch['knob']}.marker and correctness[{kind}].argv"
                    extra = {"verdict": verdict, "fix": fix}
                    if verdict.startswith("FUTILITY_HARNESS_"):
                        extra["failclass"] = {"side": "harness"}
                    return H.end_smoke("FAIL", 3, f"{verdict}: {reason}", self.out, extra=extra)
            finally:
                self.spec = original_spec
                self.current_unit = {}
            unit_s = max((time.time() - u0) / len(units), 0.001)
            H.write_smoke_measure(self.out_smoke, unit_s, len(units), u0 - t0,
                                  unit_name="arm visit", extra={"gate": "ak_gate"})
            result_path = os.path.join(self.out, "RESULT.json")

            if time.time() - t0 > float(sm["budget_s"]):
                return H.end_smoke("FAIL", 3, f"smoke took {time.time() - t0:.0f} s > budget {sm['budget_s']} s "
                                              f"(shorten smoke.prompt_chars / n_predict)", self.out)
            return H.end_smoke("PASS", 0, f"{len(units)} arms: {d['reason']}; {time.time() - t0:.1f} s", self.out)
        except Exception as e:  # noqa: BLE001 - the smoke always says why it failed
            return H.end_smoke("FAIL", 3, f"FUTILITY_HARNESS_SERVER: {e.__class__.__name__}: {e}", self.out,
                               extra={"verdict": "FUTILITY_HARNESS_SERVER", "fix": "Check server.argv and smoke.budget_s",
                                      "failclass": {"side": "harness"}})
        finally:
            self.smoke_deadline = None
            self.kill_all()

    def run(self):
        try:
            return self._run()
        except Exception as e:
            try:
                units = load_units(self.out)
            except Exception:
                units = []
            return self.finish(units, decide_error(e, getattr(self, "decision_unit", "run"),
                                                   getattr(self, "decision_arm", "unknown")))

    def _run(self):
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
            self.decision_unit, self.decision_arm = uid, arm
            u = self.reuse_unit(uid, kind, arm, extra)
            if u is None:
                u = self.run_correctness_unit(uid, kind, arm, extra)
                if u.get("error_class") == "STOPPED":
                    return 75
                self.mark_reusable(u, extra)
                H.append_unit(u, self.out)
            units.append(u)
        d = decide(self.spec, units)
        if d["terminal"]:
            return self.finish(units, d)
        srv = self.spec["server"]
        w = self.spec.get("workload") or {}
        prompts = workload_prompts(self.spec, self.d)
        kc = keep_cfg(self.spec)
        for j, cfg in enumerate(self.spec.get("units", [])):
            for b in range(1, cfg.get("blocks", 1) + 1):
                for arm in cfg["arms"]:
                    uid = f"load{j}-b{b}-{arm}"
                    if uid in done:
                        continue
                    if self.should_stop():
                        return 75
                    self.current_unit = cfg
                    u = self.visit_fn(uid, arm, prompts, int(cfg.get("n_predict", w.get("n_predict") or 256)),
                                      int(srv.get("warmup", 1)), float(srv.get("ready_timeout_s") or 900), kind="load")
                    if u.get("error_class") == "STOPPED":
                        return 75
                    u = self.finish_unit(dict(u, kind="load", block=b, report_only=True))
                    u["metric"] = METRICS[cfg.get("metric", "ms_per_round")][0](u.get("req") or [])
                    H.append_unit(u, self.out)
                    units.append(u)
        points = self.spec.get("sampler", {})
        points = points if isinstance(points, list) else [points]
        for b in blocks(self.spec):
          for si, sampler in enumerate(points):
            self.current_unit = {"sampler": sampler}
            if len(points) > 1 and _decide(self.spec, [u for u in units if u.get("kind") != "visit" or u.get("sampler_index") == si])["terminal"]:
                continue
            for arm in block_order(self.spec, b):
                uid = f"b{b}-{arm}" if len(points) == 1 else f"s{si}-b{b}-{arm}"
                if uid in done:
                    continue
                if self.should_stop():
                    return 75
                u = self.visit_fn(uid, arm, prompts, int(w.get("n_predict") or 256), int(srv.get("warmup", 1)),
                                  float(srv.get("ready_timeout_s") or 900))
                if u.get("error_class") == "STOPPED":
                    return 75
                u = self.finish_unit(dict(u, block=b, sampler_index=si, sampler=sampler))
                H.append_unit(u, self.out)
                units.append(u)
                d = decide(self.spec, units)
                if d["terminal"]:
                    return self.finish(units, d)
            if b == kc["look_blocks"]:
                self.log(f"look at block {b}: {decide(self.spec, units)['verdict']}")
        return self.finish(units, decide(self.spec, units))

    def finish(self, units, d):
        try:
            res = result_doc(self.spec, units, d)
        except Exception as e:
            d = decide_error(e, "result", "unknown")
            res = {"schema": RESULT_SCHEMA, "complete": True, "row": self.spec.get("row_id"), **d}
        atomic_json(os.path.join(self.out, "RESULT.json"), res)
        self.log(f"RESULT {res['verdict']} (polar {res['polar']}): {res.get('reason', '')[:300]}")
        return 0


def selftest_parse(c, txt):
    m = re.findall(str(c["mismatch_rx"]), txt or "", re.M)
    v = m[-1] if m else None
    return {"mismatches": int(v[0] if isinstance(v, tuple) else v) if v is not None else None}


def identity_parse(c, txt):
    rx = {k: re.compile((c.get("rx") or {}).get(k) or v, re.M) for k, v in IDENTITY_RX.items()}
    t = txt or ""
    out = rx["output"].findall(t)
    acc = rx["accepted"].findall(t)
    return {"output": out[-1] if out else None, "accepted": acc[-1] if acc else None, "draft": rx["draft"].findall(t)}


def result_doc(spec, units, d):
    tus = [u for u in units if u.get("kind") == "visit" and not u.get("report_only")]
    gate_units = [u for u in units if u.get("kind") != "load" and not u.get("report_only")]
    res = {"schema": RESULT_SCHEMA, "complete": bool(d.get("terminal")), "verdict": d["verdict"], "polar": d.get("polar"),
           "native_verdict": d.get("native_verdict", d["verdict"]), "reason": d.get("reason", ""), "row": spec["row_id"], "task": spec.get("task"), "utc": H.now(),
           "metric": spec["metric"], "keep": keep_cfg(spec), "per_arm": per_arm_stats(spec, gate_units),
           "witness": witness_table(spec, gate_units), "witness_mismatches": mismatches(gate_units),
           "aa": {"ratio": aa_ratio(spec, gate_units), "max": keep_cfg(spec)["aa_max"],
                  "arms": baseline_arms(spec)[:2]},
           "correctness": d.get("correctness"), "blocks_scored": len(full_blocks(spec, gate_units)),
           "n_units": len(units), "n_visits": len(tus),
           "units": units,
           "gate": {"module": "ak_gate.py", "version": GATE_VERSION, "sha256": _sha_file(os.path.abspath(__file__))}}
    if spec.get("units") or any(u.get("kind") == "load" or u.get("report_only") for u in units):
        res["report_only"] = [u for u in units if u.get("kind") == "load" or u.get("report_only")]
    if d.get("sampler_decisions") is not None:
        res["sampler_decisions"] = d["sampler_decisions"]
        res["sampler_results"] = [{"sampler": point, "per_arm": per_arm_stats(spec, [u for u in gate_units if u.get("sampler_index") == i]),
                                   "aa_ratio": aa_ratio(spec, [u for u in gate_units if u.get("sampler_index") == i])}
                                  for i, point in enumerate(spec["sampler"])]
    if str(d["verdict"]).startswith(("FAIL", "FUTILITY")):
        res["evidence"] = list(EVIDENCE_PATHS)   # spec.keep: the replay input of a failed gate
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
    recorded = [u for u in load_units(out_dir) if u.get("gate_unit")]
    units = [u for u in recorded if u.get("kind") != "load" and not u.get("report_only")]
    mode = "smoke" if units and all(u.get("kind") == "smoke" for u in units) else "units"
    if not units and not recorded:
        units = [u for u in load_units(os.path.join(row_dir, "out-smoke")) if u.get("gate_unit")]
        mode = "smoke"
    skipped = []
    if not units and not recorded:
        units, skipped = logs_only_units(spec, out_dir)
        mode = "logs-only"
    out = []
    for u in units:
        u = dict(u)
        c = corr_of(spec, u.get("kind"))
        txt = read_log(os.path.join(out_dir, u["log"])) if u.get("log") else None
        if u.get("error"):
            out.append(u)
            continue
        witnessed = u["kind"] in ("visit", "smoke", "log", "c-id", "c-kld", "c-st") or \
            (u["kind"] == "c-tbo" and c.get("witness"))
        if witnessed and u.get("arm") not in (spec.get("arms") or {}):
            # a prior arm the new declaration does not declare cannot be judged: a mismatch, never "unwitnessed"
            u["witness"] = {"(arm)": {"expected": "a declared arm", "observed": "no-arm", "ok": False, "line": None,
                                      "lines_scanned": 0, "log": u.get("log"), "argv_lv": None, "log_lv": None,
                                      "lv_required": MIN_LV, "note": f"prior arm {u.get('arm')!r} is not declared"}}
        elif witnessed:
            u["witness"] = witness_for(spec, u["arm"], txt, u.get("argv") if u["kind"] != "c-tbo" else None, u.get("log"),
                                       UNIT_TYPE.get(u["kind"], "served"))
        if u.get("req") is not None:
            u["metric"] = metric_of(spec, u["req"])
        if u["kind"] == "c-kld" and txt is not None:
            m = KLD_RX.findall(txt)
            u["mean_kld"] = float(m[-1]) if m else None
        if u["kind"] == "c-tbo" and txt is not None:
            cases = H.tbo_cases(txt)
            u.update(tbo_counts(cases))
            u["pass"] = tbo_pass(c, u)
        if u["kind"] == "c-st" and txt is not None:
            u.update(selftest_parse(c, txt))
        if u["kind"] == "c-id" and c.get("mode", "server") == "cmd" and txt is not None:
            got = identity_parse(c, txt)
            for f in ("output", "accepted", "draft"):
                u[f + "_sha"] = sha_bytes(json.dumps(got[f]))[:16] if got[f] is not None else None
        out.append(u)
    return out, mode, skipped


def replay(spec, row_dir, prior, stream=None):
    """The WHOLE decision path offline over a previous run's real logs + results (no server, no GPU, no network, no
    writes). Returns {prev_id, mode, n_units, n_witnessed, skipped_logs, observed, verdict, witness_mismatches,
    mismatch_pairs, correctness_kind}: what `--decide-from` prints for the preflight R4 replay (which is the R1 receipt)."""
    validate_spec(spec)
    t0 = time.time()
    out_dir, prow = resolve_prior(prior)
    units, mode, skipped = replay_units(spec, out_dir, prow)
    d = decide(spec, units) if mode == "units" else decide_smoke(spec, units)
    if mode == "units" and not d["terminal"] and not [u for u in units if u.get("kind") == "visit"] and \
            any(u.get("kind") == "smoke" for u in units):
        d = decide_smoke(spec, units)
    prev_id = os.path.basename(prow)
    for meta in (os.path.join(prow, "spec.json"), os.path.join(out_dir, "RESULT.json")):
        try:
            m = json.load(open(meta))
            prev_id = str(m.get("id") or m.get("row") or prev_id)
            break
        except (OSError, ValueError, AttributeError):
            continue
    mm = mismatches(units)
    rec = {"prev_id": prev_id, "prior_out": out_dir, "mode": mode, "n_units": len(units),
           "n_witnessed": sum(1 for u in units if u.get("witness")), "skipped_logs": skipped[:40],
           "observed": {"verdict": d["verdict"], "native_verdict": d.get("native_verdict", d["verdict"]),
                        "polar": d.get("polar"), "terminal": d.get("terminal"),
                        "reason": str(d.get("reason") or "")[:1200], "n_units": len(units)},
           "verdict": d["verdict"], "witness_mismatches": mm[:40],
           "mismatch_pairs": sorted({(m["knob"], m["arm"]) for m in mm}),
           "correctness_kind": "+".join(c["kind"] for c in corr_list(spec)) or None, "elapsed_s": round(time.time() - t0, 3)}
    print(f"REPLAY {prev_id} mode={mode} units={len(units)} witnessed={rec['n_witnessed']} -> {d['verdict']} "
          f"(polar {d.get('polar')}): {str(d.get('reason') or '')[:400]}", file=stream or sys.stdout, flush=True)
    return rec


# ---------------------------------------------------------------------------------------------------- selftest
def _synthetic_log(spec, arm, lv=MIN_LV):
    lines = [f"0.00.040.649 I cmn  common_param: verbosity = {lv} (adjust with the `-lv N` CLI arg)", "noise line"]
    for k, v in spec["knobs"].items():
        if expect_of(spec, arm, k) == "present":
            m = v["marker"]
            lines.append("0.01.000.000 I " + (re.sub(r"[\\^$.*+?()\[\]{}|]", "", m[3:]) if m.startswith("re:") else m))
    return "\n".join(lines) + "\n"


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
    k0 = next((k for k in spec["knobs"] if expect_of(spec, cand, k) == "present"), None)
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
    sp = dict(spec, correctness=None, candidates=candidate_arms(spec), inputs={}, workload={"prompts": ["p"]}, dirs=[])
    quiet = open(os.devnull, "w")
    verdicts = {}
    with tempfile.TemporaryDirectory() as t:
        def gate(name, speed):
            g = Gate(sp, os.path.join(t, name), env={"FILLER_PORTS": "1"}, stream=quiet)
            g.visit_fn = stub_visit(sp, g.out, speed)
            return g
        fast = max(1.10, float(keep_cfg(sp)["threshold"]) * 1.05)
        for name, speed in (("keep", {a: fast for a in candidate_arms(sp)}), ("nokeep", {})):
            g = gate(name, speed)
            assert g.run() == 0
            res = json.load(open(os.path.join(g.out, "RESULT.json")))
            verdicts[name] = res["verdict"]
            if name == "keep":
                assert res["native_verdict"].startswith("KEEP") and res["polar"] == "PASS", res["verdict"]
            elif float(keep_cfg(sp)["threshold"]) >= 1.0:
                assert res["native_verdict"] in ("NO_KEEP", "FUTILITY_CANDIDATE_BELOW_FLOOR"), res["verdict"]
            r = replay(sp, g.d, g.out, stream=quiet)
            assert r["verdict"] == res["verdict"], (r["verdict"], res["verdict"])
        if keep_cfg(sp)["aa_max"] is not None:
            g = gate("aa", {baseline_arms(sp)[1]: 1.0 + 3 * float(keep_cfg(sp)["aa_max"])})
            g.run()
            verdicts["aa"] = json.load(open(os.path.join(g.out, "RESULT.json")))["native_verdict"]
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
        try:   # --replay: the developer fix loop (REPLAY line on stdout); --decide-from: preflight R4 (DECIDE json)
            rec = replay(spec, row_dir, argv[i + 1], stream=sys.stdout if flag == "--replay" else sys.stderr)
        except Exception as e:  # noqa: BLE001 - a crashed decide is the R4 finding itself: say so, rc 3
            print("DECIDE " + json.dumps({"error": f"{e.__class__.__name__}: {e}"}), flush=True)
            return 3
        if flag == "--decide-from":
            print("DECIDE " + json.dumps(rec), flush=True)
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
