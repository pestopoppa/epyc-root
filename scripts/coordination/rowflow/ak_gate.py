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
import statistics
import shutil
import subprocess
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import ak_row_harness as H  # noqa: E402
import rocprof_trace as RT  # noqa: E402

GATE_VERSION = "2"
# Bump when the way a correctness/smoke unit is EXECUTED or JUDGED changes.
UNIT_SEMANTICS_VERSION = 9
# Evidence a FAIL_* / FUTILITY_* row must keep so it can be diagnosed and REPLAYED (AutoKernel 2026-11-25): declared in
# spec.json keep + evidence by mk_ak_row gate new and in RESULT.json. ak_gate never deletes anything under these.
EVIDENCE_PATHS = ("out/logs", "out/results.jsonl", "out/RESULT.json", "out/TERMINAL-smoke.json", "out-smoke", "out/prof", "out/OP-GBPS.json")
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
    "tbo": {"min_cases", "require_rc0", "ops", "diagnostic_arms", "required_cases"},
    "kld": {"base_arm", "max_kld", "max_kld_noise_k", "noise_arm", "witness_base", "min_vram_gib", "library_root"},
    "identity": {"mode", "prompts", "n_prompts", "n_predict", "rx", "gate_accepted", "strict_drafts"},
    "selftest_bin": {"runs", "mismatch_rx", "max_mismatch"},
    "served_quality": {"input_kind", "input", "noise_arm", "gate", "n_predict", "n_probs", "k", "abs_floor_items", "test_timeout_s", "noise_argv_delta"}}
UNIT_KIND = {"c-tbo": "tbo", "c-kld": "kld", "c-id": "identity", "c-st": "selftest_bin", "c-sq": "served_quality"}
UNIT_TYPE = dict({"visit": "served", "smoke": "served", "log": "served", "op": "op"}, **UNIT_KIND)   # expect_by_unit scopes
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
           "ms_per_round": (m_ms_per_round, False), "wall_s": (m_wall_s, False), "op_gbps": (None, True)}


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
    return {c["noise_arm"] for c in corr_list(spec) if c.get("kind") in ("kld", "served_quality") and isinstance(c.get("noise_arm"), str) and c.get("noise_arm")}


def candidate_arms(spec):
    c = spec.get("candidates")
    if c:
        return [a for a in c if a not in noise_arms(spec)]
    b = set(baseline_arms(spec)) | noise_arms(spec)
    return [a for a in spec.get("arms", {}) if a not in b]


def arm_list(spec):
    """Base arm order for ABBA: baseline[0], candidates, baseline[1:] (the A/A pair is split across the block)."""
    b = baseline_arms(spec)
    if (spec.get("metric") or {}).get("name") == "op_gbps" and (spec.get("op_unit") or {}).get("arms"):
        return list(spec["op_unit"]["arms"])
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
    if not candidate_arms(spec) or any(x not in arms or x in b for x in candidate_arms(spec)):
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
    for a, store in (spec.get("arm_stores") or {}).items():
        if a not in arms or not isinstance(store, dict) or not all(store.get(k) for k in ("store", "bin", "lib", "sha256")):
            errs.append(f"arm_stores[{a}]: invalid store declaration")
    floor = spec.get("serving_floor")
    if floor and (floor.get("arm") not in b or not isinstance(floor.get("ratio"), (int, float)) or
                  not math.isfinite(floor["ratio"]) or floor["ratio"] <= 0 or m.get("name") == "op_gbps"):
        errs.append("serving_floor: needs a baseline arm and positive ratio on a serving metric")
    for a in (spec.get("arm_env") or {}):
        if a not in arms:
            errs.append(f"arm_env names unknown arm {a}")
    srv = spec.get("server") or {}
    argv = srv.get("argv") or []
    is_op = m.get("name") == "op_gbps"
    if not is_op and (error := executable_error(argv, "server")):
        errs.append(error)
    if not is_op and (not argv or "{PORT}" not in [str(x) for x in argv]):
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
    kld_chunks = (spec.get("smoke") or {}).get("kld_chunks")
    if kld_chunks is not None and (type(kld_chunks) is not int or kld_chunks < 1):
        errs.append("smoke.kld_chunks must be a positive integer")
    identity_limit = (spec.get("smoke") or {}).get("identity_n_predict")
    if identity_limit is not None and (type(identity_limit) is not int or identity_limit < 1):
        errs.append("smoke.identity_n_predict must be a positive integer")
    for c in corr_list(spec):
        if c.get("argv") and (error := executable_error(c["argv"], f"correctness {c.get('kind')}")):
            errs.append(error)
        if c.get("kind") in ("identity", "kld", "tbo", "selftest_bin", "served_quality") and c.get("arms"):
            for baseline in b:
                if baseline not in c["arms"]:
                    errs.append(f"correctness {c['kind']}: FIX: add {baseline} to the unit's arms")
        if c.get("kind") == "kld" and c.get("min_vram_gib") is not None:
            v = c["min_vram_gib"]
            if type(v) not in (int, float) or not math.isfinite(v) or v <= 0 or not os.path.isabs(str(c.get("library_root") or "")):
                errs.append("correctness kld: min_vram_gib requires a positive number and absolute library_root")
        if c.get("kind") == "tbo":
            for arm in c.get("diagnostic_arms") or []:
                if arm not in (c.get("arms") or []) or arm in b or arm in candidate_arms(spec):
                    errs.append(f"correctness tbo: diagnostic arm {arm} must be a declared non-gating arm")
            required = c.get("required_cases") or {}
            if not isinstance(required, dict):
                errs.append("correctness tbo: required_cases must map regexes to positive counts")
            else:
                for pattern, count in required.items():
                    try:
                        re.compile(pattern)
                        if type(count) is not int or count < 1:
                            raise ValueError("count must be positive")
                    except (TypeError, ValueError, re.error) as e:
                        errs.append(f"correctness tbo: invalid required_cases {pattern!r}: {e}")
        if c.get("kind") == "tbo" and "require_rc0" in c and not isinstance(c["require_rc0"], bool):
            errs.append("correctness tbo: require_rc0 must be a boolean")
        if c.get("kind") not in ("tbo", "kld", "identity", "selftest_bin", "served_quality"):
            errs.append(f"correctness.kind {c.get('kind')!r} not tbo|kld|identity|selftest_bin|served_quality")
        else:
            bad = sorted(set(c) - CORRECTNESS_KEYS["common"] - CORRECTNESS_KEYS[c["kind"]])
            if bad:
                errs.append(f"correctness ({c['kind']}): unknown key(s) {bad}; allowed "
                            f"{sorted(CORRECTNESS_KEYS['common'] | CORRECTNESS_KEYS[c['kind']])}")
        if c.get("kind") == "served_quality":
            path = c.get("input")
            if not isinstance(path, str) or path not in (spec.get("inputs") or {}) or not re.fullmatch(r"[0-9a-f]{64}", str((spec.get("inputs") or {}).get(path, ""))):
                errs.append("correctness served_quality: input must name a sha256-pinned spec.inputs entry")
            noise = c.get("noise_arm")
            promotion = c.get("input_kind") == "promotion_suites"
            if c.get("input_kind", "items") not in ("items", "promotion_suites"):
                errs.append("correctness served_quality: unknown input_kind")
            if promotion and c.get("gate") is not True:
                errs.append("correctness served_quality: promotion suites must gate")
            if promotion and (spec.get("inputs") or {}).get(path) != PROMOTION_SHA256:
                errs.append("correctness served_quality: promotion manifest hash mismatch")
            if not promotion and (noise not in arms or (b and noise == b[0])):
                errs.append("correctness served_quality: noise_arm must be declared and distinct from baseline")
            if c.get("arms") and b and not set([b[0]] + ([] if promotion else [noise]) + candidate_arms(spec)).issubset(c["arms"]):
                errs.append("correctness served_quality: arms must include baseline, noise and every candidate")
            delta = c.get("noise_argv_delta", {})
            if not isinstance(delta, dict) or any(k not in ("--threads", "--threads-batch") or type(v) is not int or v < 1 for k, v in (delta.items() if isinstance(delta, dict) else [])):
                errs.append("correctness served_quality: noise_argv_delta accepts positive --threads and --threads-batch values")
            if type(c.get("gate", False)) is not bool:
                errs.append("correctness served_quality: gate must be boolean")
            for name, default in (("n_predict", 512), ("n_probs", 5), ("test_timeout_s", 5)):
                v = c.get(name, default)
                if type(v) not in (int, float) or not math.isfinite(v) or v <= 0 or (name != "test_timeout_s" and type(v) is not int):
                    errs.append(f"correctness served_quality: {name} must be positive")
            for name, default in (("k", 3), ("abs_floor_items", 1)):
                v = c.get(name, default)
                if type(v) not in (int, float) or not math.isfinite(v) or v < 0:
                    errs.append(f"correctness served_quality: {name} must be nonnegative")
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
        if u.get("metric", "ms_per_round") not in METRICS or u.get("metric") == "op_gbps":
            errs.append("load unit metric must name a supported served metric")
        if "argv" in u and (not isinstance(u["argv"], list) or "{PORT}" not in u["argv"]):
            errs.append("load unit argv must be a list containing {PORT}")
    w = spec.get("workload") or {}
    if not is_op and not (w.get("prompts") or w.get("input")):
        errs.append("workload needs prompts or an input file")
    if is_op:
        op = spec.get("op_unit") or {}
        if type(op.get("witness_exactly_once", False)) is not bool:
            errs.append("op_unit.witness_exactly_once must be boolean")
        proof = op.get("proof")
        if proof is not None and (not isinstance(proof, dict) or not os.path.isabs(str(proof.get("store") or "")) or not re.fullmatch(r"[0-9a-f]{40}", str(proof.get("source_sha") or "")) or not re.fullmatch(r"[0-9a-f]{64}", str(proof.get("library_sha256") or ""))):
            errs.append("op_unit.proof requires absolute store, source_sha and library_sha256")
        if not isinstance(op.get("op"), str) or not op["op"]:
            errs.append("op_unit.op required")
        if error := executable_error(op.get("argv") or [], "op test-backend-ops"):
            errs.append(error)
        if type(op.get("reps")) is not int or op["reps"] < 2:
            errs.append("op_unit.reps must be an integer >= 2")
        shapes = op.get("shapes")
        if not isinstance(shapes, list) or not shapes or any(not isinstance(x, dict) or not isinstance(x.get("filter"), str) or not x["filter"] or type(x.get("bytes")) not in (int, float) or not math.isfinite(x["bytes"]) or x["bytes"] <= 0 or (type(x.get("gate", True)) is not bool or type(x.get("futility", x.get("gate", True))) is not bool) for x in shapes):
            errs.append("op_unit.shapes requires [{filter: str, bytes: positive number, gate: bool}]")
        elif len({x["filter"] for x in shapes}) != len(shapes) or not any(x.get("gate", True) for x in shapes) or not any(x.get("futility", x.get("gate", True)) for x in shapes):
            errs.append("op_unit.shapes must be unique and contain a gating shape")
        for key in ("kernel_regex", "merge_regex"):
            if key == "kernel_regex" or op.get(key):
                try:
                    if not isinstance(op.get(key), str) or not op[key]:
                        raise ValueError("required")
                    re.compile(op[key])
                except (ValueError, re.error) as e:
                    errs.append(f"op_unit.{key}: invalid regex: {e}")
        for arm, pattern in (op.get("attribution") or {}).items():
            try:
                if arm not in arms or not isinstance(pattern, str) or not pattern:
                    raise ValueError("requires a declared arm and nonempty regex")
                re.compile(pattern)
            except (ValueError, re.error) as e:
                errs.append(f"op_unit.attribution[{arm}]: {e}")
        for arm, av in (op.get("arm_argv") or {}).items():
            if arm not in arms:
                errs.append(f"op_unit.arm_argv: unknown arm {arm}")
            if error := executable_error(av, f"op arm {arm}"):
                errs.append(error)
        timing_arms = op.get("arms") or arm_list(spec)
        if not isinstance(timing_arms, list) or len(timing_arms) != len(set(timing_arms)) or not set(b + candidate_arms(spec)).issubset(timing_arms) or any(a not in arms for a in timing_arms):
            errs.append("op_unit.arms must uniquely include the baseline and every candidate")
        rule = spec.get("op_decide") or {"kind": "ci_lower"}
        if not isinstance(rule, dict):
            errs.append("op_decide must be an object")
            rule = {}
        if rule.get("kind") == "ratio_min" and (len(b) != 1 or len(candidate_arms(spec)) != 1):
            errs.append("ratio_min requires exactly one baseline and one candidate")
        if rule.get("kind") not in ("ci_lower", "ratio_min"):
            errs.append("op_decide.kind must be ci_lower or ratio_min")
        for key in (("threshold",) if rule.get("kind") == "ratio_min" else ()):
            if type(rule.get(key)) not in (int, float) or not math.isfinite(rule[key]) or rule[key] <= 0:
                errs.append(f"op_decide.{key} must be positive")
        f = rule.get("futility") or {}
        if not isinstance(f, dict):
            errs.append("op_decide.futility must be an object")
            f = {}
        if f and (type(f.get("first_rep_gmean_min")) not in (int, float) or not math.isfinite(f["first_rep_gmean_min"]) or f["first_rep_gmean_min"] <= 0):
            errs.append("op_decide.futility.first_rep_gmean_min must be positive")
        if op.get("reps") != kc["n_blocks"] or kc["dummy_block"]:
            errs.append("op_unit.reps must equal keep.n_blocks and dummy_block must be false")
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
        if ut not in ("tbo", "kld", "identity", "selftest_bin", "served_quality"):
            continue
        if ut == "served_quality":
            continue  # this unit uses the full served argv and arm flags
        if ut == "tbo" and not c.get("witness"):
            continue   # an unwitnessed tbo unit is never judged
        if witness_exempt(spec, ut):
            continue
        argv = [str(x) for x in (c.get("argv") or [])]
        binary = os.path.basename(argv[0]) if argv and not str(argv[0]).startswith("@@") else ""
        no_lv = (ut == "tbo" or binary in NO_LV_BINARIES) and (spec.get("metric") or {}).get("name") != "op_gbps"
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


# Served rows exempt test-backend-ops unless explicitly scoped. An op row may opt into its own TBO witness:
# the declaration is then responsible for choosing markers its backend actually emits.
WITNESS_EXEMPT_UNIT_TYPES = ("tbo",)


def witness_exempt(spec, unit_type):
    if unit_type == "tbo" and (spec.get("metric") or {}).get("name") == "op_gbps" and any(c.get("kind") == "tbo" and c.get("witness") for c in corr_list(spec)):
        return False
    return unit_type in WITNESS_EXEMPT_UNIT_TYPES and unit_type not in (spec.get("expect_by_unit") or {})


# Unit execution and judgment also depend on helpers such as witness parsing and metrics.
# Bump UNIT_SEMANTICS_VERSION when changing how correctness/smoke units execute or are judged.
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
        count = sum(marker_hit(str(v["marker"]), [line]) is not None for line in lines)
        exact = (spec.get("op_unit") or {}).get("witness_exactly_once", False) and unit_type in ("op", "tbo", "kld")
        ok = (obs == exp or exp == "ignore") and not (exact and exp == "present" and count != 1)
        if exact and exp == "present" and count > 1:
            note = f"witness appeared {count} times; expected exactly once"
        out[k] = {"expected": exp, "observed": obs, "ok": ok, "line": ln, "count": count, "lines_scanned": len(lines),
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


def serving_floor_results(spec, units):
    floor = spec.get("serving_floor")
    if not floor:
        return {}
    blocks = full_blocks(spec, units)
    incumbent = floor["arm"]
    result = {}
    for arm in candidate_arms(spec):
        pairs = [(v[arm], v[incumbent]) for v in blocks.values() if arm in v and incumbent in v]
        ref = sum(y for _, y in pairs) / len(pairs) if pairs else None
        value = sum(x for x, _ in pairs) / len(pairs) if pairs else None
        ratio = _speed(spec, value, ref) if ref is not None and ref > 0 and value > 0 else None
        result[arm] = {"incumbent": incumbent, "threshold": floor["ratio"], "ratio": ratio,
                       "pass": ratio >= floor["ratio"] if ratio is not None else None, "blocks": len(pairs)}
    return result


# ---------------------------------------------------------------------------------------------------- correctness
# Network isolation is installed before candidate code executes, inherited by descendants,
# and fails closed if libseccomp is unavailable. The scorer never inherits open fds.
QUALITY_SANDBOX = r'''
import ctypes, errno, json, resource, sys
try:
    lib = ctypes.CDLL("libseccomp.so.2", use_errno=True)
    lib.seccomp_init.argtypes = [ctypes.c_uint32]
    lib.seccomp_init.restype = ctypes.c_void_p
    lib.seccomp_rule_add.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int, ctypes.c_uint]
    lib.seccomp_load.argtypes = [ctypes.c_void_p]
    lib.seccomp_syscall_resolve_name.argtypes = [ctypes.c_char_p]
    ctx = lib.seccomp_init(0x7fff0000)
    if not ctx: raise RuntimeError("seccomp_init")
    for name in ("socket", "socketpair", "io_uring_setup", "ptrace", "process_vm_readv", "process_vm_writev", "pidfd_getfd", "pidfd_send_signal", "unshare", "setns", "kill", "tkill", "tgkill", "rt_sigqueueinfo", "rt_tgsigqueueinfo", "fork", "vfork", "clone", "clone3", "execve", "execveat", "openat2", "unlink", "unlinkat", "rename", "renameat", "renameat2", "link", "linkat", "symlink", "symlinkat", "mkdir", "mkdirat", "rmdir", "mknod", "mknodat", "truncate", "ftruncate", "chmod", "fchmod", "fchmodat", "chown", "fchown", "fchownat", "lchown"):
        nr = lib.seccomp_syscall_resolve_name(name.encode())
        if nr >= 0 and lib.seccomp_rule_add(ctx, 0x00050000 | errno.EPERM, nr, 0) != 0: raise RuntimeError(name)
    class ArgCmp(ctypes.Structure):
        _fields_ = [("arg", ctypes.c_uint), ("op", ctypes.c_int), ("datum_a", ctypes.c_uint64), ("datum_b", ctypes.c_uint64)]
    lib.seccomp_rule_add_array.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int, ctypes.c_uint, ctypes.POINTER(ArgCmp)]
    for name, arg in (("open", 1), ("openat", 2)):
        nr = lib.seccomp_syscall_resolve_name(name.encode())
        if nr >= 0:
            for flag in (1, 2, 64, 512, 1024, 0x400000):
                cmp = ArgCmp(arg, 7, flag, flag)  # SCMP_CMP_MASKED_EQ
                if lib.seccomp_rule_add_array(ctx, 0x00050000 | errno.EPERM, nr, 1, ctypes.byref(cmp)) != 0:
                    raise RuntimeError("seccomp open flags")
    if lib.seccomp_load(ctx) != 0: raise RuntimeError("seccomp_load")
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_FSIZE, (65536, 65536))
    resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
except BaseException as e:
    sys.stderr.write("sandbox setup failed: " + str(e))
    sys.exit(125)
program = json.load(sys.stdin)
sys.stdout.write("SANDBOX_READY\n"); sys.stdout.flush()
exec(compile(program, "<quality-test>", "exec"), {})
sys.stdout.write("\nSANDBOX_TESTS_PASSED\n"); sys.stdout.flush()
'''


PROMOTION_SHA256 = "1532906b4a754673937027e73e2023d8eee7ed5d08f084c207a60ac81460adb1"

def load_promotion_items(path):
    if _sha_file(path) != PROMOTION_SHA256:
        raise ValueError("promotion manifest hash mismatch")
    with open(path, encoding="utf-8") as f:
        suites = json.load(f)["suites"]
    items = [dict(row, suite=suite) for suite, n in (("mmlu_pro", 200), ("gpqa", 195))
             for row in suites[suite]]
    if [len(suites[x]) for x in ("mmlu_pro", "gpqa")] != [200, 195] or len({x["id"] for x in items}) != 395 or any(x.get("scoring_method") != "multiple_choice" for x in items):
        raise ValueError("invalid promotion suite")
    return items

def load_quality_items(path):
    with open(path, encoding="utf-8") as f:
        items = [json.loads(line) for line in f if line.strip()]
    if not items or len({x.get("id") for x in items}) != len(items):
        raise ValueError("empty or duplicate quality items")
    for x in items:
        if not isinstance(x.get("id"), str) or not isinstance(x.get("prompt"), str) or x.get("kind") not in ("math", "code"):
            raise ValueError("invalid quality item")
        if x["kind"] == "math" and not isinstance(x.get("answer"), str):
            raise ValueError("math item missing answer")
        if x["kind"] == "code" and (not isinstance(x.get("test"), str) or not re.fullmatch(r"[A-Za-z_]\w*", x.get("entry_point", ""))):
            raise ValueError("code item missing test or entry point")
    return items


def numeric_answer(text):
    from decimal import Decimal, InvalidOperation
    tags = re.findall(r"<answer>\s*(.*?)\s*</answer>", text, re.I | re.S)
    text = tags[-1] if tags else text
    matches = re.findall(r"(?<![\w.])[-+]?(?:(?:\d[\d,]*)(?:\.\d+)?|\.\d+)", text)
    if not matches:
        return None
    try:
        return Decimal(matches[-1].replace(",", ""))
    except InvalidOperation:
        return None


def score_quality(item, output, timeout):
    if item["kind"] == "math":
        expected, actual = numeric_answer(item["answer"]), numeric_answer(output)
        return expected is not None and actual is not None and expected == actual
    import tempfile
    code = output.strip("\n")
    fence = re.search(r"```(?:python)?\s*\n(.*?)```", code, re.S | re.I)
    if fence:
        code = fence.group(1)
    # HumanEval asks for a continuation; accept a complete function as well.
    source = code if re.search(r"^\s*def\s+" + re.escape(item["entry_point"]) + r"\s*\(", code, re.M) else item["prompt"] + code
    source = "from typing import *\n" + source
    source += "\n" + item["test"] + "\ncheck(" + item["entry_point"] + ")\n"
    try:
        with tempfile.TemporaryDirectory(prefix="ak-quality-") as tmp, tempfile.TemporaryFile(dir=tmp) as output_file:
            p = subprocess.run([sys.executable, "-I", "-c", QUALITY_SANDBOX], input=json.dumps(source),
                               text=True, stdout=output_file, stderr=subprocess.DEVNULL, cwd=tmp,
                               env={"PATH": "/usr/bin:/bin", "HOME": tmp}, timeout=float(timeout))
            output_file.seek(0)
            output = output_file.read().decode("utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        return False
    if not output.startswith("SANDBOX_READY\n"):
        raise RuntimeError("network-isolated code scorer could not initialize")
    return p.returncode == 0 and output.endswith("\nSANDBOX_TESTS_PASSED\n")


def mcnemar_bad_p(baseline, candidate):
    bad = sum(a and not b for a, b in zip(baseline, candidate))
    good = sum(not a and b for a, b in zip(baseline, candidate))
    n = bad + good
    return sum(math.comb(n, i) for i in range(bad, n + 1)) / (2 ** n), bad, good


def quality_noise_argv(argv, delta):
    # Replace thread settings (including their short aliases), preserving every other served flag.
    aliases = {"--threads": ("--threads", "-t"), "--threads-batch": ("--threads-batch", "-tb")}
    out = list(argv)
    for flag, value in delta.items():
        names = aliases[flag]
        cleaned, i = [], 0
        while i < len(out):
            token = out[i]
            if token in names:
                if i + 1 >= len(out):
                    raise ValueError(f"missing value for {token}")
                i += 2
            elif any(token.startswith(name + "=") for name in names):
                i += 1
            else:
                cleaned.append(token)
                i += 1
        out = cleaned + [flag, str(value)]
    return out


def quality_diagnostic(base, other):
    if base.get("diagnostics_unavailable") or other.get("diagnostics_unavailable"):
        return {"first_divergence_token_index": None, "top_k_overlap_before_divergence": [],
                "unavailable": base.get("diagnostics_unavailable") or other.get("diagnostics_unavailable")}
    a, b = base["tokens"], other["tokens"]
    divergence = next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), None)
    if divergence is None and len(a) != len(b):
        divergence = min(len(a), len(b))
    end = divergence if divergence is not None else min(len(a), len(b))
    overlaps = []
    for p, q in zip(base["completion_probabilities"][:end], other["completion_probabilities"][:end]):
        def choices(x):
            return {("id", v["id"]) if "id" in v else ("text", v.get("token", v.get("tok_str")))
                    for v in (x.get("top_logprobs") or x.get("top_probs") or x.get("probs") or [])
                    if isinstance(v, dict) and any(k in v for k in ("id", "token", "tok_str"))}
        x, y = choices(p), choices(q)
        overlaps.append(len(x & y) / max(len(x), len(y)) if x and y else None)
    return {"first_divergence_token_index": divergence, "top_k_overlap_before_divergence": overlaps}


def quality_decision(spec, c, units):
    by = {u["arm"]: u["req"] for u in units}
    if c.get("input_kind") == "promotion_suites":
        import v7_quality_gate_compare as compare
        base_arm = baseline_arms(spec)[0]
        ids = [(r["suite"], r["item_id"]) for r in by[base_arm]]
        if not ids or any([(r["suite"], r["item_id"]) for r in rows] != ids for rows in by.values()):
            raise ValueError("promotion item order differs between arms")
        expected_counts = [1, 1] if c.get("_smoke") else [200, 195]
        if [sum(suite == name for suite, _ in ids) for name in ("mmlu_pro", "gpqa")] != expected_counts:
            raise ValueError("promotion suite coverage incomplete")
        per_arm = {}
        for arm, rows in by.items():
            suites = []
            for suite in ("mmlu_pro", "gpqa"):
                subset = [r for r in rows if r["suite"] == suite]
                n = len(subset)
                suites.append({"suite": suite, "n": n, "accuracy": sum(r["correct"] for r in subset) / n if n else None,
                               "truncated": sum(r["truncated"] for r in subset), "errors": 0,
                               "accuracy_is_lower_bound": any(r["truncated"] for r in subset)})
            per_arm[arm] = {"suites": suites, "truncated": sum(r["truncated"] for r in rows), "errors": 0}
        failed = []
        for arm in candidate_arms(spec):
            rows, summary, verdict, verdict_text = compare.compare(per_arm[base_arm], per_arm[arm], 0.05)
            per_arm[arm]["compare"] = {"rows": rows, "summary": summary, "verdict": verdict, "verdict_text": verdict_text}
            if verdict != "pass" and not c.get("_smoke"): failed.append(arm)
        return {"base_arm": base_arm, "gate": True, "failed": failed, "per_arm": per_arm}
    base_arm, noise = baseline_arms(spec)[0], c["noise_arm"]
    base = by[base_arm]
    ids = [r["item_id"] for r in base]
    if not ids or any([r["item_id"] for r in rows] != ids for rows in by.values()):
        raise ValueError("quality item order differs between arms")
    truth = [r["correct"] for r in base]
    n = len(base)
    acc = sum(truth) / n
    noise_acc = sum(r["correct"] for r in by[noise]) / n
    allowed_items = max(float(c.get("abs_floor_items", 1)), float(c.get("k", 3)) * abs(sum(r["correct"] for r in by[noise]) - sum(truth)))
    bound = allowed_items / n
    details, failed = {}, []
    for arm, rows in by.items():
        values = [r["correct"] for r in rows]
        p, bad, good = mcnemar_bad_p(truth, values)
        accuracy = sum(values) / n
        passed = sum(truth) - sum(values) <= allowed_items and not (bad > good and p < 0.05)
        if arm in candidate_arms(spec) and not passed:
            failed.append(arm)
        details[arm] = {"accuracy": accuracy, "correct": sum(values), "mcnemar_p_bad": p,
                        "baseline_only_correct": bad, "arm_only_correct": good, "pass": passed,
                        "per_prompt": [{"item_id": r["item_id"], "correct": r["correct"], **quality_diagnostic(ref, r)} for ref, r in zip(base, rows)]}
    return {"n": n, "base_arm": base_arm, "noise_arm": noise, "noise_accuracy": noise_acc,
            "allowed_loss": bound, "gate": c.get("gate", False), "failed": failed, "per_arm": details}


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
    if kind == "served_quality":
        return [(f"c-sq-{a}", "c-sq", a, {}) for a in [b[0]] + ([] if c.get("input_kind") == "promotion_suites" else [c["noise_arm"]]) + cand]
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


def smoke_spec(spec, identity_count=None):
    """Reduce repetitions while retaining each declared correctness arm and the full judge."""
    reduced = copy.deepcopy(spec)
    for c in corr_list(reduced):
        if c["kind"] == "identity":
            if identity_count is not None:
                c["n_prompts"] = identity_count
            elif not c.get("n_prompts"):
                c["n_prompts"] = identity_prompt_count(spec, c) or 1
            sm = spec.get("smoke") or {}
            c["n_predict"] = min(int(c.get("n_predict") or 64), int(sm.get("identity_n_predict", sm.get("n_predict", 32))))
            c["arms"] = baseline_arms(spec)[:2]
        elif c["kind"] == "kld":
            c["argv"] = list(c.get("argv") or []) + ["--chunks", str((spec.get("smoke") or {}).get("kld_chunks", 2))]
        elif c["kind"] == "served_quality":
            c["_smoke"] = True  # one example of each type, while retaining the same scorer and token cap
        elif c["kind"] == "selftest_bin":
            c["runs"] = 1
        elif c["kind"] == "tbo":
            # An exact, small test-backend-ops case avoids running an entire operation suite.
            c["ops"] = "ADD"
            c["argv"] = list(c.get("argv") or []) + ["-p", r"^type=f16,ne=\[1,1,8,1\],nr=\[1,1,1,1\],nf=1(,perm1=0(,src_overlap=0)?)?$"]
            c["min_cases"] = 1
            c.pop("required_cases", None)
            if (spec.get("metric") or {}).get("name") == "op_gbps":
                c["witness"] = False
    return reduced


def tbo_pass(c, u):
    """rc 0, zero explicit FAIL cases, every case that ran OK, and at least the arm's min_cases ran (a crash or a too-short
    -o list is not a pass). "not supported" cases are skipped (n_skipped), never failures; n_cases counts cases that ran."""
    return (all((u.get("required_cases") or {}).get(rx, 0) >= count for rx, count in (c.get("required_cases") or {}).items())
            and int(u.get("n_cases") or 0) >= int(per_arm(c.get("min_cases"), u["arm"], 1)) and u.get("n_ok") == u.get("n_cases")
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
    result = dets[0] if len(dets) == 1 else {"kind": "+".join(c["kind"] for c in cs), "parts": dets}
    if len(dets) > 1:
        for det in dets:
            if "served_quality" in det:
                result["served_quality"] = det["served_quality"]
    return None, result, True


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
    if kind == "served_quality":
        det = quality_decision(spec, c, us)
        return ("FAIL_CORRECTNESS" if c.get("gate", False) and det["failed"] else None), {"kind": kind, "served_quality": det}, True
    if kind == "tbo":
        bad = [u for u in us if u["arm"] not in (c.get("diagnostic_arms") or []) and not tbo_pass(c, u)]
        det = {"kind": kind, "per_arm": {u["arm"]: dict({k: u.get(k) for k in ("n_cases", "n_ok", "n_fail", "n_skipped", "rc", "fails", "required_cases", "nmse_lines")},
                                                       min_cases=int(per_arm(c.get("min_cases"), u["arm"], 1)))
                                         for u in us}}
        if (spec.get("metric") or {}).get("name") != "op_gbps" and any(u["arm"] in baseline_arms(spec) for u in bad):   # the reference itself fails: harness/baseline broken, not the knob
            return "FUTILITY_HARNESS_BASELINE", dict(det, failed=[u["unit_id"] for u in bad],
                                                     why="baseline arm fails the tbo unit; a candidate is judged only when OFF passes"), True
        return ("FAIL_CORRECTNESS", dict(det, failed=[u["unit_id"] for u in bad]), True) if bad else (None, det, True)
    if kind == "kld":
        mx = float(c.get("max_kld", 0.003))
        kl = {u["arm"]: u.get("mean_kld") for u in us if u.get("mode") == "kld"}
        det = {"kind": kind, "mean_kld": kl, "max_kld_abs": mx}
        if any(v is None or not math.isfinite(v) for v in kl.values()):
            return "FUTILITY_HARNESS_MISSING_OUTPUT", dict(det, why="no finite 'Mean KLD' in a perplexity log"), True
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
        verdict = "FAIL_KLD" if (spec.get("metric") or {}).get("name") == "op_gbps" else "FAIL_CORRECTNESS"
        return (verdict, dict(det, failed=bad), True) if bad else (None, det, True)
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
    return map_verdict(spec, d)


def map_verdict(spec, d):
    if d.get("native_verdict") is not None:
        return d
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


def op_trace_metric(op, shape, arm, directory):
    """Recompute bandwidth from the saved rocprof trace; reject missing or invalid dispatches."""
    rows = RT.read_csvs(directory, "kernel_trace.csv")
    def duration(pattern, label):
        matches = [r for r in rows if re.search(pattern, r.get("Kernel_Name") or "")]
        if not matches:
            raise ValueError(f"{label} found no kernel in rocprofv3 trace")
        if any(int(r["End_Timestamp"]) <= int(r["Start_Timestamp"]) for r in matches):
            raise ValueError(f"{label} has a nonpositive kernel duration")
        return matches, RT.mean_duration_s(matches)
    main, elapsed = duration(op["kernel_regex"], "kernel_regex")
    if op.get("merge_regex"):
        _, merge = duration(op["merge_regex"], "merge_regex")
        elapsed += merge
    family = (op.get("attribution") or {}).get(arm)
    if family and any(not re.search(family, r.get("Kernel_Name") or "") for r in main):
        raise ValueError("kernel attribution mismatch")
    return shape["bytes"] / elapsed / 1e9


def decide_op(spec, units, res):
    """Judge each shape using the declared rule; incomplete matrices never pass."""
    op, rule = spec["op_unit"], spec.get("op_decide") or {"kind": "ci_lower"}
    us = [u for u in units if u.get("kind") == "op"]
    err = next((u for u in us if u.get("error") or type(u.get("metric")) not in (int, float) or not math.isfinite(u["metric"]) or u["metric"] <= 0), None)
    mm = mismatches(us)
    valid = [u for u in us if not u.get("error") and type(u.get("metric")) in (int, float)
             and math.isfinite(u["metric"]) and u["metric"] > 0]
    outcomes = {}
    base, candidates = baseline_arms(spec)[0], candidate_arms(spec)
    for shape in op["shapes"]:
        shape_us = [u for u in valid if u.get("shape") == shape["filter"]]
        row = {}
        for arm in candidates:
            vals = {a: [u["metric"] for u in shape_us if u.get("arm") == a and u.get("block")] for a in (base, arm)}
            ratio = statistics.median(vals[arm]) / statistics.median(vals[base]) if all(vals.values()) else None
            lr = log_ratios(spec, [dict(u, kind="visit") for u in shape_us], arm)
            estimate, lo, hi = ci(lr)
            passed = (ratio >= rule["threshold"] if ratio is not None else None) if rule["kind"] == "ratio_min" else (lo > keep_cfg(spec)["threshold"] if lo is not None else None)
            first = {u["arm"]: u["metric"] for u in shape_us if u.get("block") == 1}
            row[arm] = {"ratio": ratio, "first_ratio": first[arm] / first[base] if arm in first and base in first else None,
                        "ci": [estimate, lo, hi], "keep": passed}
        outcomes[shape["filter"]] = {"gate": shape.get("gate", True), "futility": shape.get("futility", shape.get("gate", True)), "arms": row}
        if rule["kind"] == "ci_lower":
            ci_spec = dict(spec, metric={"name": "tok_s", "higher_is_better": True}, correctness=None, candidates=candidate_arms(spec))
            cd = _decide_impl(ci_spec, [dict(u, kind="visit") for u in shape_us])
            outcomes[shape["filter"]]["decision"] = cd
    res.update(op_decide=rule, per_shape=outcomes)
    if err:
        return dict(res, verdict="FUTILITY_HARNESS_" + (err.get("error_class") or "MISSING_OUTPUT"), polar=None, terminal=True, reason=str(err.get("error") or "op metric missing"))
    if mm:
        return dict(res, verdict="FUTILITY_HARNESS_WITNESS", polar=None, terminal=True, witness_mismatches=mm, reason=mismatch_text(mm[0]))
    gated = [x for x in outcomes.values() if x["gate"]]
    f = (rule.get("futility") or {}).get("first_rep_gmean_min")
    if f is not None:
        first = [x["arms"][a]["first_ratio"] for x in outcomes.values() if x["futility"] for a in candidates]
        first_shapes = {shape["filter"] for shape in op["shapes"] if shape.get("futility", shape.get("gate", True))}
        first_complete = {(shape, 1, arm) for shape in first_shapes for arm in arm_list(spec)} <= {
            (u.get("shape"), u.get("block"), u.get("arm")) for u in us}
        if first_complete and all(x is not None for x in first):
            gm = math.exp(sum(math.log(x) for x in first) / len(first))
            res["first_rep_gmean"] = gm
            if gm < f:
                return dict(res, verdict="FUTILITY_OP_BELOW_FLOOR", polar="FAIL", terminal=True, reason=f"first-rep geometric mean {gm} < {f}")
    if rule["kind"] == "ci_lower":
        decisions = [x["decision"] for x in gated]
        failure = next((x for x in decisions if x["terminal"] and str(x["verdict"]).startswith("FUTILITY")), None)
        if failure:
            return dict(res, verdict=failure["verdict"], polar=failure["polar"], terminal=True, reason=failure["reason"])
    expected = {(shape["filter"], b, a) for shape in op["shapes"] for b in range(1, op["reps"] + 1) for a in arm_list(spec)}
    actual = {(u.get("shape"), u.get("block"), u.get("arm")) for u in us}
    if not expected <= actual:
        return dict(res, verdict="INCOMPLETE", polar=None, terminal=False, reason=f"{len(expected - actual)} op units pending")
    winners = [a for a in candidates if all(x["arms"][a]["keep"] for x in gated)]
    verdict = "KEEP_" + "+".join(winners) if winners else "NO_KEEP"
    return dict(res, verdict=verdict, polar=polar(verdict), terminal=True, reason="all qualifying shapes must pass")


def _decide_impl(spec, units):
    """The pre-registered rule, first match wins. Returns {verdict, polar, terminal, reason, ...}; terminal False =
    keep running (or, in a replay, the prior run did not get far enough)."""
    kc = keep_cfg(spec)
    cv, cdet, cdone = decide_correctness(spec, units)
    quality = next((c for c in corr_list(spec) if c.get("kind") == "served_quality"), None)
    if quality and "served_quality" not in cdet:
        _, qdet, _ = _decide_one(spec, quality, units)
        if "served_quality" in qdet:
            cdet = dict(cdet, served_quality=qdet["served_quality"])
    res = {"correctness": cdet}
    if not cdone:
        return dict(res, verdict="INCOMPLETE_CORRECTNESS", polar=None, terminal=False, reason="correctness unit pending")
    if cv:
        r = (f"{cdet.get('kind')}: " + "; ".join(mismatch_text(m) for m in cdet.get("witness_mismatches", []))
             if cdet.get("witness_mismatches") else json.dumps({k: cdet.get(k) for k in ("failed", "nondet", "why", "error")
                                                                 if cdet.get(k)})[:600])
        return dict(res, verdict=cv, polar=polar(cv), terminal=True, reason=r)
    if spec["metric"]["name"] == "op_gbps":
        return decide_op(spec, units, res)
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
    floor_results = serving_floor_results(spec, units)
    keep = [a for a in live if (ci(log_ratios(spec, units, a))[1] or 0) > thr
            and (not spec.get("serving_floor") or floor_results[a]["pass"] is True)]
    if spec.get("serving_floor"):
        res["serving_floor"] = floor_results
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


def smoke_served_fix(decision):
    if decision["verdict"] == "FUTILITY_HARNESS_RESIDENCY":
        return "Verify GPU residency and adjust server.kfd_min_vram_gib to the measured footprint"
    if decision.get("witness_mismatches"):
        mismatch = decision["witness_mismatches"][0]
        return f"Check expect.{mismatch['arm']}.{mismatch['knob']}, expect_by_unit.served.{mismatch['arm']}.{mismatch['knob']}, knobs.{mismatch['knob']}.marker and server.argv"
    return "Check server.argv, smoke.n_predict and smoke.budget_s"


def decide_smoke_correctness(spec, units, identity_count=None):
    """Judge a reduced smoke correctness plan using the full-run correctness judge."""
    reduced = smoke_spec(spec, identity_count)
    if identity_count == 0:
        reduced["correctness"] = [c for c in corr_list(reduced) if c["kind"] != "identity"]
    # Identity candidates run once, while the reduced correctness judge compares
    # baseline pairs over the available prompt budget. Check every executed unit.
    mm = mismatches(correctness_units(units))
    if mm:
        kind = UNIT_TYPE.get(next(u["kind"] for u in units if u.get("unit_id") == mm[0]["unit"]), "unknown")
        return {"verdict": "FUTILITY_HARNESS_WITNESS", "polar": None, "terminal": True,
                "reason": "; ".join(mismatch_text(m) for m in mm[:6]),
                "fix": f"Check expect_by_unit.{kind}.{mm[0]['arm']}.{mm[0]['knob']}, knobs.{mm[0]['knob']}.marker and correctness[{kind}].argv",
                "witness_mismatches": mm}
    verdict, detail, _ = decide_correctness(reduced, units)
    if not verdict:
        return {"verdict": "SMOKE_PASS", "polar": "PASS", "terminal": True, "reason": "correctness units passed"}
    kind = detail.get("kind", "unknown")
    fix = {"FUTILITY_HARNESS_WITNESS": f"Check correctness[{kind}].argv and expect_by_unit.{kind} for the named arm and knob",
           "FUTILITY_HARNESS_NONDET": "Fix correctness[identity].argv or server.argv and baseline arm settings to make A/A deterministic",
           "FUTILITY_HARNESS_MISSING_OUTPUT": f"Fix correctness[{kind}].argv executable path and output flags"}.get(
               verdict, f"Check correctness[{kind}].argv and unit logs")
    if detail.get("witness_mismatches"):
        mismatch = detail["witness_mismatches"][0]
        fix = f"Check expect_by_unit.{kind}.{mismatch['arm']}.{mismatch['knob']}, knobs.{mismatch['knob']}.marker and correctness[{kind}].argv"
    return {"verdict": verdict, "polar": polar(verdict), "terminal": True,
            "reason": json.dumps(detail, sort_keys=True)[:1200], "fix": fix,
            "witness_mismatches": detail.get("witness_mismatches", [])}


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
    if not w.get("input"):
        # 2026-11-26: op rows (metric op_gbps, no served workload) have no workload input; the smoke died with
        # KeyError 'input' before running any op. A served row without input is still refused by validate_spec.
        return []
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
        self.linkage_witness = {}
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
        proof = (self.spec.get("op_unit") or {}).get("proof")
        if proof:
            try:
                store = proof["store"]
                with open(os.path.join(store, "BUILD-IDENTITY.json")) as f:
                    identity = json.load(f)
                if identity.get("source_sha") != proof["source_sha"]:
                    bad.append("op content proof: source_sha mismatch")
                if _sha_file(os.path.join(store, "bin", "libggml-hip.so")) != proof["library_sha256"]:
                    bad.append("op content proof: libggml-hip.so sha256 mismatch")
                check = subprocess.run(["/usr/bin/sha256sum", "--check", "--status", "SHA256SUMS"], cwd=store, timeout=900)
                if check.returncode:
                    bad.append("op content proof: SHA256SUMS verification failed")
            except (OSError, ValueError, KeyError, subprocess.TimeoutExpired) as e:
                bad.append(f"op content proof: {type(e).__name__}: {e}")
        for rel, want in sorted((self.spec.get("inputs") or {}).items()):
            p = os.path.join(self.d, rel)
            if not os.path.isfile(p):
                bad.append(f"input {rel} missing")
            elif want and _sha_file(p) != want:
                bad.append(f"input {rel} sha256 {_sha_file(p)[:12]} != pinned {str(want)[:12]}")
        self.content_proof_ok = bool(proof) and not any(x.startswith("op content proof:") for x in bad)
        return bad

    def verify_arm_stores(self):
        """Check pinned contents and loader resolution before any arm executes."""
        for arm, store in (self.spec.get("arm_stores") or {}).items():
            witness = {"store": store["store"], "ok": False, "files": {}, "linkage": {}}
            self.linkage_witness[arm] = witness
            try:
                root = os.path.realpath(store["store"])
                for rel, digest in store["sha256"].items():
                    path = os.path.join(root, rel)
                    if os.path.commonpath((root, os.path.realpath(path))) != root or _sha_file(path) != digest:
                        raise ValueError(f"digest or path mismatch: {rel}")
                    witness["files"][rel] = digest
                commands = [(self.spec["server"]["argv"], None)] + [
                    (c.get("argv") or self.spec["server"]["argv"], c.get("env")) for c in corr_list(self.spec)]
                commands += [(u["argv"], None) for u in self.spec.get("units", []) if u.get("argv")]
                for command, unit_env in commands:
                    binary = os.path.join(store["bin"], os.path.basename(command[0]))
                    self.require_exec_grant([binary])
                    env = self.proc_env(arm, binary, unit_env)
                    p = subprocess.run(["/usr/bin/ldd", binary], env=env, capture_output=True, text=True, timeout=60)
                    lines = [line.split() for line in p.stdout.splitlines() if line.strip().startswith(("libggml", "libllama", "libmtmd", "libwhisper"))]
                    if p.returncode or not any(x[0].startswith("libggml-base.so") for x in lines):
                        raise ValueError(f"ldd failed or no libggml-base: {binary}")
                    linked = {}
                    for fields in lines:
                        if len(fields) < 3 or fields[1] != "=>" or not os.path.isabs(fields[2]):
                            raise ValueError(f"unresolved linkage: {' '.join(fields)}")
                        resolved = os.path.realpath(fields[2])
                        if os.path.commonpath((root, resolved)) != root:
                            raise ValueError(f"linkage outside store: {resolved}")
                        if fields[0].startswith("libggml"):
                            pinned = {os.path.realpath(os.path.join(root, rel)) for rel in store["sha256"]}
                            if resolved not in pinned:
                                raise ValueError(f"linked ggml library is not digest-pinned: {resolved}")
                        linked[fields[0]] = resolved
                    witness["linkage"][binary] = linked
                witness["ok"] = True
            except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as e:
                witness["error"] = f"{type(e).__name__}: {e}"
        return all(w["ok"] for w in self.linkage_witness.values())

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

    def require_exec_grant(self, argv):
        """Guard spec executables before adding launcher wrappers or synthesizing child env."""
        # Keeper full runs export FILLER_ID; keeper smokes (dry runs) export FILLER_DRYRUN - the same pair
        # ak_row_harness.require_grant accepts. Missing FILLER_DRYRUN here refused every real smoke (2026-11-26).
        for env in (self.env, os.environ):
            if env.get("FILLER_ID") or env.get("FILLER_DRYRUN") or env.get("AK_GATE_ALLOW_EXEC") == "1":
                return
        executable = str(argv[0]) if argv else ""
        resolved = os.path.realpath(os.path.join(self.d, executable)) if os.sep in executable else ""
        if "fixtures" in resolved.split(os.sep) or "test-fixtures" in resolved.split(os.sep):
            return
        raise RuntimeError("INC-20261126-ungranted-mi210-replay: refusing to execute "
                           f"{executable!r} without a keeper grant (FILLER_ID); "
                           "use fixture executables or explicitly set AK_GATE_ALLOW_EXEC=1")

    def pin(self, argv):
        self.require_exec_grant(argv)
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
        store = (self.spec.get("arm_stores") or {}).get(arm)
        if store:
            e["LD_LIBRARY_PATH"] = store["lib"] + (":/opt/rocm/lib" if self.spec.get("lane") == "gpu" else "")
        return e

    def llama_argv(self, argv, arm, port=None, flags=True, extra=None, force_lv=False):
        a = self.subst(argv, port, extra)
        store = (self.spec.get("arm_stores") or {}).get(arm)
        if store and a:
            a[0] = os.path.join(store["bin"], os.path.basename(a[0]))
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
            vram_max, hip_from_store = 0, False
            try:
                while p.poll() is None:
                    if getattr(self, "monitor_library_root", None):
                        vram_max = max(vram_max, self.kfd_vram(p.pid))
                        try:
                            maps = [os.path.realpath(line.split()[-1]) for line in open(f"/proc/{p.pid}/maps") if "libggml-hip" in line]
                            root = os.path.realpath(self.monitor_library_root) + "/"
                            hip_from_store |= bool(maps) and all(path.startswith(root) for path in maps)
                        except OSError:
                            pass
                    if self.should_stop() or time.time() - t0 > timeout:
                        H.kill_tree(p)
                        return {"rc": None, "secs": round(time.time() - t0, 1),
                                "error": "stopped" if self.should_stop() else f"timeout {timeout} s"}
                    time.sleep(0.2)
            finally:
                if p in self.procs:
                    self.procs.remove(p)
        return {"rc": p.returncode, "secs": round(time.time() - t0, 1), "vram_max_b": vram_max, "hip_from_store": hip_from_store}

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

    def request(self, port, body, timeout, path="/completion"):
        import urllib.request
        req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=json.dumps(body).encode(),
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
        if kind == "c-sq":
            quality = corr_of(self.spec, kind)
            if arm == quality.get("noise_arm"):
                argv = quality_noise_argv(argv, quality.get("noise_argv_delta") or {})
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
                body = request_body(self.spec, pr, n_predict, cfg.get("sampler"), i + cfg.get("prompt_index", 0))
                promotion = kind == "c-sq" and cfg.get("promotion")
                if promotion:
                    body = {"model": "auto", "messages": [{"role": "user", "content": pr}], "max_tokens": 4096,
                            "temperature": 0.0, "seed": 42, "stream": False,
                            "chat_template_kwargs": {"enable_thinking": False}}
                    rec, response = self.request(port, body, request_timeout(), "/v1/chat/completions")
                    choices = response.get("choices")
                    if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0].get("message", {}).get("content"), str) or not choices[0]["message"]["content"] or choices[0].get("finish_reason") not in ("stop", "length"):
                        raise ValueError("invalid promotion chat response")
                    rec.update(content=choices[0]["message"]["content"], truncated=choices[0]["finish_reason"] == "length",
                               sampling={k: body[k] for k in ("seed", "temperature", "max_tokens")}
                               | {"enable_thinking": False, "endpoint": "/v1/chat/completions"})
                    return rec
                if kind == "c-sq":
                    body.update(temperature=0.0, top_k=1, n_predict=n_predict, n_probs=cfg["n_probs"], return_tokens=True, cache_prompt=False, ignore_eos=False)
                rec, response = self.request(port, body, request_timeout())
                if kind == "c-sq":
                    rec.update(content=response.get("content"), tokens=response.get("tokens"), completion_probabilities=response.get("completion_probabilities"))
                return rec
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

    # Correctness/smoke execution and judgment: bump UNIT_SEMANTICS_VERSION when
    # changing their behavior, including the helpers they call.
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
        if kind == "c-sq":
            try:
                promotion = c.get("input_kind") == "promotion_suites"
                items = (load_promotion_items if promotion else load_quality_items)(os.path.join(self.d, c["input"]))
                if c.get("_smoke") and promotion:
                    items = [next(x for x in items if x["suite"] == suite) for suite in ("mmlu_pro", "gpqa")]
                elif c.get("_smoke"):
                    items = [next(x for x in items if x["kind"] == kind_name) for kind_name in ("math", "code")
                             if any(x["kind"] == kind_name for x in items)]
                self.current_unit = {"sampler": {"temperature": 0.0, "top_k": 1}, "n_probs": c.get("n_probs", 5), "promotion": promotion}
                u = self.visit_fn(uid, arm, [x["prompt"] for x in items], 4096 if promotion else int(c.get("n_predict", 512)), 0,
                                  float(self.spec["server"].get("ready_timeout_s") or 900), kind=kind)
                if not u.get("error"):
                    req = u.get("req") or []
                    if len(req) != len(items):
                        raise ValueError("incomplete served quality responses")
                    for item, rec in zip(items, req):
                        # 2026-11-26: only `content` is needed for the accuracy gate; tokens / probabilities are optional
                        # diagnostics (speculative/MTP serving may omit or reshape them). Missing content is still an error.
                        if not isinstance(rec.get("content"), str):
                            raise ValueError("served quality response missing content; response keys: "
                                             + ",".join(sorted(k for k in rec if not k.startswith("_")))[:300])
                        if promotion:
                            if not rec["content"] or rec.get("error"):
                                raise ValueError("promotion request returned an error or empty response")
                            from answer_scoring import score_response
                            if not isinstance(rec.get("truncated"), bool):
                                raise ValueError("promotion response missing finish reason")
                            rec.update(item_id=item["id"], suite=item["suite"], correct=score_response(rec["content"], item["expected"], item))
                            continue
                        toks, probs = rec.get("tokens"), rec.get("completion_probabilities")
                        if not (isinstance(toks, list) and isinstance(probs, list) and len(toks) == len(probs)):
                            rec["diagnostics_unavailable"] = ("tokens/probabilities absent or misaligned: keys "
                                                              + ",".join(sorted(k for k in rec if not k.startswith("_")))[:300])
                        rec.update(item_id=item["id"], correct=score_quality(item, rec["content"], c.get("test_timeout_s", 5)))
                    u["correctness"] = {"served_quality": {"items": req}}
                return self.finish_correctness(u)
            except Exception as e:
                return {"unit_id": uid, "kind": kind, "arm": arm, "gate_unit": True, "error_class": "UNIT", "error": f"{type(e).__name__}: {e}"}
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
            argv = self.llama_argv(list(c["argv"]) + (["-o", str(ops)] if ops else []), arm, flags=False)
            if c.get("lv"):
                argv = ensure_lv(argv, self.lv, force=True)
        elif kind == "c-st":    # a declared A/A self-test binary, one fresh process per run
            argv = self.llama_argv(c["argv"], arm, flags=bool(c.get("apply_flags")), force_lv=c.get("lv", True))
        else:   # identity, cmd mode: every (arm, prompt) in its OWN process
            argv = self.llama_argv(c["argv"], arm, flags=bool(c.get("apply_flags")),
                                   extra={"{PROMPT_INDEX}": str(extra["prompt"])}, force_lv=c.get("lv", True))
        try:
            self.monitor_library_root = ((self.spec.get("arm_stores") or {}).get(arm) or {}).get("store", c.get("library_root")) if kind == "c-kld" and c.get("min_vram_gib") else None
            r = self.run_fn(self.pin(argv), self.proc_env(arm, argv[llama_index(argv) or 0], c.get("env")), log, to)
        except OSError as e:
            r = {"rc": None, "error": f"{type(e).__name__}: {e}"}
        finally:
            self.monitor_library_root = None
        u = {"unit_id": uid, "kind": kind, "arm": arm, "argv": argv, "log": os.path.relpath(log, self.out),
             "rc": r.get("rc"), "secs": r.get("secs"), **extra}
        if r.get("error"):
            u.update(error=r["error"], error_class="STOPPED" if r["error"] == "stopped" else ("MISSING_OUTPUT" if r["error"].startswith(("FileNotFoundError", "PermissionError")) else "TIMEOUT"))
        elif kind == "c-kld" and c.get("min_vram_gib"):
            u.update(vram_max_b=r.get("vram_max_b"), hip_from_store=r.get("hip_from_store"))
            if (r.get("vram_max_b") or 0) < c["min_vram_gib"] * (1 << 30) or not r.get("hip_from_store"):
                u.update(error="KLD residency or library mapping proof missing", error_class="RESIDENCY")
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
            u["nmse_lines"] = re.findall(r"(?im)^.*\bNMSE\s*=\s*[0-9.eE+-]+.*$", txt or "")
            u["required_cases"] = {rx: len({x["args"] for x in cases if not x.get("skipped") and re.search(rx, x["args"])}) for rx in (c.get("required_cases") or {})}
            u["pass"] = tbo_pass(c, u)
        elif u["kind"] == "c-kld":
            m = KLD_RX.findall(txt or "")
            s = SAME_TOP_RX.findall(txt or "")
            u.update(mean_kld=float(m[-1]) if m else None, same_top_p_pct=float(s[-1]) if s else None)
            if u.get("mode") == "base" and u.get("rc") not in (0, None):
                u.update(error=f"kld base run rc {u.get('rc')}", error_class="MISSING_OUTPUT")
            elif (self.spec.get("metric") or {}).get("name") == "op_gbps" and u.get("rc") != 0:
                u.update(error=f"kld run rc {u.get('rc')}", error_class="MISSING_OUTPUT")
            elif (self.spec.get("metric") or {}).get("name") == "op_gbps" and u.get("mode") == "base":
                base = os.path.join(self.out, "kld-base.bin")
                if not os.path.isfile(base) or os.path.getsize(base) == 0:
                    u.update(error="kld base output missing or empty", error_class="MISSING_OUTPUT")
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
                   "unit_semantics_version": UNIT_SEMANTICS_VERSION,
                   "server": server, "knobs": self.spec.get("knobs"), "arms": self.spec.get("arms"),
                   "arm_env": self.spec.get("arm_env"), "arm_stores": self.spec.get("arm_stores"), "expect": self.spec.get("expect"),
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
        elif kind == "c-sq":
            verdict = "RECORDED" if u.get("req") and all(type(r.get("correct")) is bool for r in u["req"]) else None
        elif kind == "c-id":
            verdict = "RECORDED" if u.get("output_sha") and u.get("accepted_sha") else None
        else:
            verdict = decide_smoke(self.spec, [u])["verdict"] if u.get("req") and u.get("metric") is not None else None
        if verdict:
            u.update(reuse_key=key, unit_verdict=verdict, unit_semantics_version=UNIT_SEMANTICS_VERSION)
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
                u = dict(u, reused_from=pid, unit_semantics_version=UNIT_SEMANTICS_VERSION)
                H.append_unit(u, self.out)
                self.log(f"UNIT-REUSED {uid} from {pid}")
                return u
        return None

    def write_op_progress(self, units):
        """Persist the first numbers and subsequent per-shape ratios before the terminal result."""
        op_units = [u for u in units if u.get("kind") == "op"]
        d = decide_op(self.spec, op_units, {})
        atomic_json(os.path.join(self.out, "OP-GBPS.json"), {
            "row": self.spec["row_id"], "metric": "op_gbps", "rule": self.spec.get("op_decide") or {"kind": "ci_lower"},
            "per_shape": d.get("per_shape", {}), "first_rep_gmean": d.get("first_rep_gmean"), "units": op_units})

    def run_op(self, uid, arm, shape, block):
        op = self.spec["op_unit"]
        prof = op.get("rocprof", "/mnt/raid0/llm/tools/rocprofiler-sdk-6.2.0-66/opt/rocm-6.2.0/bin/rocprofv3")
        log = os.path.join(self.logs, uid + ".log")
        odir = os.path.join(self.out, "prof", uid)
        argv = self.subst((op.get("arm_argv") or {}).get(arm, op["argv"])) + ["perf", "-b", op.get("backend", "ROCm0"), "-o", op["op"], "-p", shape["filter"]]
        cmd = [prof, "-M", "--output-format", "csv", "-d", odir, "-o", uid, "--kernel-trace", "--"] + self.pin(argv)
        u = {"unit_id": uid, "kind": "op", "arm": arm, "shape": shape["filter"], "block": block,
             "argv": argv, "log": os.path.relpath(log, self.out), "gate_unit": True}
        try:
            env = self.proc_env(arm, argv[0], op.get("env"))
            if arm in (op.get("arm_argv") or {}):
                env["LD_LIBRARY_PATH"] = os.path.dirname(os.path.realpath(argv[0])) + ":/opt/rocm/lib"
            sdk = os.path.dirname(os.path.dirname(prof))
            env["LD_LIBRARY_PATH"] = ":".join([env.get("LD_LIBRARY_PATH", ""), sdk + "/lib", sdk + "/lib/rocprofiler-sdk", "/mnt/raid0/llm/tools/rocm-profilers-6.2/opt/rocm-6.2.0/lib"])
            r = self.run_fn(cmd, env, log, float(op.get("timeout_s", 1800)))
            u.update(rc=r.get("rc"), secs=r.get("secs"))
            if r.get("error") == "stopped":
                return dict(u, error="stopped", error_class="STOPPED")
            if r.get("error") or r.get("rc") != 0:
                raise RuntimeError(r.get("error") or f"rocprofv3 exited {r.get('rc')}")
            u["metric"] = op_trace_metric(op, shape, arm, odir)
            u["witness"] = witness_for(self.spec, arm, read_log(log), None, u["log"], "op")
        except (OSError, ValueError, KeyError, TypeError, RuntimeError) as e:
            u.update(error=f"{type(e).__name__}: {e}", error_class="MISSING_OUTPUT")
        return u

    # ------------------------------------------------------------------ modes
    def smoke(self):
        """Visit every arm and run one reduced correctness plan within the smoke budget."""
        sm = dict({"arm": candidate_arms(self.spec)[0], "prompt_chars": 2000, "n_predict": 32, "budget_s": 300},
                  **(self.spec.get("smoke") or {}))
        t0 = time.time()
        self.smoke_deadline = t0 + float(sm["budget_s"])
        smoke_run_id = time.time_ns()
        try:
            bad = self.prepare()
            if bad:
                return H.end_smoke("FAIL", 3, "inputs: " + "; ".join(bad), self.out)
            if not self.verify_arm_stores():
                self.finish([], {"verdict": "FUTILITY_HARNESS_LINKAGE", "polar": None, "terminal": True, "reason": "arm linkage verification failed"})
                return H.end_smoke("FAIL", 3, "FUTILITY_HARNESS_LINKAGE: arm linkage verification failed", self.out)
            prompt = (workload_prompts(self.spec, self.d) or ["Hello"])[0][:int(sm["prompt_chars"])]
            units = []
            u0 = time.time()
            for arm in self.spec["arms"]:
                remaining = float(sm["budget_s"]) - (time.time() - t0)
                if remaining <= 0:
                    return H.end_smoke("FAIL", 3, "smoke budget exceeded; adjust smoke.budget_s", self.out)
                ready = min(float(self.spec["server"].get("ready_timeout_s") or 900), remaining)
                uid = f"smoke-{arm}"
                if self.spec["metric"]["name"] == "op_gbps":
                    u = self.run_op(uid, arm, self.spec["op_unit"]["shapes"][0], 1)
                    u["kind"] = "smoke"
                else:
                    u = self.finish_unit(self.visit_fn(uid, arm, [prompt], int(sm["n_predict"]), 1,
                                                       ready, kind="smoke"))
                H.append_unit(u, self.out)
                units.append(u)
                arm_load_s = {x["arm"]: x["load_s"] for x in units if x.get("load_s") is not None}
                H.write_smoke_measure(self.out_smoke, max((time.time() - u0) / len(units), 0.001),
                                      len(units), u0 - t0, unit_name="arm visit",
                                      extra={"gate": "ak_gate", "arm_load_s": arm_load_s})
                H.append_unit(dict(u, smoke=True, smoke_shape="full", smoke_run_id=smoke_run_id), self.out_smoke)
                d = decide_smoke(self.spec, units)
                if d["verdict"] != "SMOKE_PASS":
                    fix = smoke_served_fix(d)
                    return H.end_smoke("FAIL", 3, f"{d['verdict']}: {d['reason']}", self.out,
                                       extra={"verdict": d["verdict"], "fix": fix, "failclass": {"side": "harness"}})
            # Run the same correctness units and judge as the full run, against a reduced plan.
            original_spec = self.spec
            self.spec = smoke_spec(original_spec)
            correctness = []
            correctness_unit_s = {}
            identity = next((c for c in corr_list(self.spec) if c["kind"] == "identity"), None)
            total_prompts = int(identity.get("n_prompts") or len(identity_prompts(self.spec, self.d)) or 1) if identity else 0
            checked = 0
            try:
                plan = plan_correctness(self.spec)
                # The baseline pairs cover nondeterminism; each other declared
                # identity arm also gets one witnessed execution.
                original_identity = next((c for c in corr_list(original_spec) if c["kind"] == "identity"), None)
                if original_identity:
                    baseline = set(baseline_arms(self.spec)[:2])
                    extra_identity = [p for p in _plan_one(original_spec, original_identity)
                                      if p[2] not in baseline and p[3]["prompt"] == 0]
                    plan = [p for p in plan if p[1] != "c-id"] + extra_identity + [p for p in plan if p[1] == "c-id"]
                visit_s = max((time.time() - u0) / len(units), 0.001)
                generation_s = max((float(r.get("predicted_ms") or 0) / 1000
                                    for u in units for r in (u.get("req") or [])), default=0)
                ratio = max(1, identity["n_predict"] / int(sm["n_predict"])) if identity else 1
                pair_estimate = 2 * (visit_s + min(visit_s, generation_s) * (ratio - 1))
                for uid, kind, arm, extra in plan:
                    if kind == "c-id" and arm == baseline_arms(self.spec)[0]:
                        if len(baseline_arms(self.spec)) < 2:
                            break
                        if self.smoke_deadline - time.time() < pair_estimate:
                            break
                        pair_start = time.time()
                    remaining = self.smoke_deadline - time.time()
                    if remaining <= 0:
                        return H.end_smoke("FAIL", 3, "smoke budget exceeded; adjust smoke.budget_s", self.out)
                    c = corr_of(self.spec, kind)
                    c["timeout_s"] = min(float(c.get("timeout_s") or 3600), remaining)
                    self.spec["server"]["ready_timeout_s"] = min(float(self.spec["server"].get("ready_timeout_s") or 900), remaining)
                    unit_start = time.monotonic()
                    u = self.run_correctness_unit(uid, kind, arm, extra)
                    correctness_unit_s[uid] = max(time.monotonic() - unit_start, 0.001)
                    H.write_smoke_measure(self.out_smoke, visit_s, len(units), u0 - t0,
                                          unit_name="arm visit", extra={"gate": "ak_gate", "arm_load_s": arm_load_s,
                                                                        "correctness_unit_s": correctness_unit_s})
                    correctness.append(u)
                    if kind == "c-id" and arm == baseline_arms(self.spec)[1]:
                        checked += 1
                        pair_estimate = max(pair_estimate, time.time() - pair_start)
                    H.append_unit(dict(u, smoke=True, smoke_shape="full", smoke_run_id=smoke_run_id), self.out_smoke)
                coverage = f"{checked}/{total_prompts}"
                if identity:
                    H.append_unit({"kind": "smoke-coverage", "gate_unit": True, "smoke_shape": "full",
                                   "smoke_run_id": smoke_run_id, "nondet_prompts_checked": coverage}, self.out_smoke)
                decision = decide_smoke_correctness(original_spec, correctness, checked if identity else None)
                if decision["verdict"] != "SMOKE_PASS":
                    extra = {"verdict": decision["verdict"], "fix": decision["fix"], "nondet_prompts_checked": coverage}
                    if decision["verdict"].startswith("FUTILITY_HARNESS_"):
                        extra["failclass"] = {"side": "harness"}
                    return H.end_smoke("FAIL", 3, f"{decision['verdict']}: {decision['reason']}", self.out, extra=extra)
            finally:
                self.spec = original_spec
                self.current_unit = {}
            H.write_smoke_measure(self.out_smoke, visit_s, len(units), u0 - t0,
                                  unit_name="arm visit", extra={"gate": "ak_gate", "arm_load_s": arm_load_s,
                                                                "correctness_unit_s": correctness_unit_s})
            result_path = os.path.join(self.out, "RESULT.json")

            if time.time() - t0 > float(sm["budget_s"]):
                return H.end_smoke("FAIL", 3, f"smoke took {time.time() - t0:.0f} s > budget {sm['budget_s']} s "
                                              f"(shorten smoke.prompt_chars / n_predict)", self.out)
            return H.end_smoke("PASS", 0, f"{len(units)} arms: {d['reason']}; {time.time() - t0:.1f} s", self.out,
                               extra={"nondet_prompts_checked": coverage})
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
        if not self.verify_arm_stores():
            return self.finish([], {"verdict": "FUTILITY_HARNESS_LINKAGE", "polar": None, "terminal": True,
                                    "reason": "arm linkage verification failed"})
        units = load_units(self.out)
        done = {u["unit_id"] for u in units if u.get("gate_unit")}
        plan = plan_correctness(self.spec)
        first_number_done = False
        for index, (uid, kind, arm, extra) in enumerate(plan):
            if kind == "c-kld" and self.spec["metric"]["name"] == "op_gbps" and not first_number_done:
                first_number_done = True
                for i, shape in enumerate(self.spec["op_unit"]["shapes"]):
                    if not shape.get("futility", shape.get("gate", True)):
                        continue
                    for op_arm in block_order(self.spec, 1):
                        op_uid = f"op-b1-s{i}-{op_arm}"
                        if op_uid in done:
                            continue
                        if self.should_stop():
                            return 75
                        op_record = self.run_op(op_uid, op_arm, shape, 1)
                        if op_record.get("error_class") == "STOPPED":
                            return 75
                        H.append_unit(op_record, self.out)
                        units.append(op_record)
                        self.write_op_progress(units)
                        done.add(op_uid)
                        if op_record.get("error"):
                            return self.finish(units, {"verdict": "FUTILITY_HARNESS_" + op_record.get("error_class", "MISSING_OUTPUT"), "polar": None, "terminal": True, "reason": op_record["error"]})
                        mismatch = mismatches([op_record])
                        if mismatch:
                            return self.finish(units, {"verdict": "FUTILITY_HARNESS_WITNESS", "polar": None, "terminal": True, "reason": mismatch_text(mismatch[0])})
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
            if self.spec["metric"]["name"] == "op_gbps" and (index + 1 == len(plan) or plan[index + 1][1] != kind):
                c = corr_of(self.spec, kind)
                verdict, detail, complete = _decide_one(self.spec, c, units)
                if complete and verdict:
                    return self.finish(units, {"verdict": verdict, "polar": polar(verdict), "terminal": True,
                                               "reason": json.dumps(detail), "correctness": detail})
        quality = next((c for c in corr_list(self.spec) if c.get("kind") == "served_quality"), None)
        if quality and not any(u.get("kind") == "quality-summary" for u in units):
            _, detail, _ = _decide_one(self.spec, quality, units)
            if "served_quality" in detail:
                summary = {"unit_id": "quality-summary", "kind": "quality-summary", "correctness": {"served_quality": detail["served_quality"]}}
                H.append_unit(summary, self.out)
                units.append(summary)
        d = decide(self.spec, units)
        if d["terminal"]:
            return self.finish(units, d)
        srv = self.spec["server"]
        w = self.spec.get("workload") or {}
        prompts = workload_prompts(self.spec, self.d)
        kc = keep_cfg(self.spec)
        if self.spec["metric"]["name"] == "op_gbps":
            for b in range(1, self.spec["op_unit"]["reps"] + 1):
                for i, shape in enumerate(self.spec["op_unit"]["shapes"]):
                    for arm in block_order(self.spec, b):
                        uid = f"op-b{b}-s{i}-{arm}"
                        if uid in done:
                            continue
                        if self.should_stop():
                            return 75
                        u = self.run_op(uid, arm, shape, b)
                        if u.get("error_class") == "STOPPED":
                            return 75
                        H.append_unit(u, self.out)
                        units.append(u)
                        self.write_op_progress(units)
                        d = decide(self.spec, units)
                        if d["terminal"]:
                            return self.finish(units, d)
            return self.finish(units, decide(self.spec, units))
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
        d = map_verdict(self.spec, d)
        try:
            res = result_doc(self.spec, units, d)
        except Exception as e:
            d = decide_error(e, "result", "unknown")
            res = {"schema": RESULT_SCHEMA, "complete": True, "row": self.spec.get("row_id"), **d}
        if self.spec.get("arm_stores"):
            res["arm_linkage"] = self.linkage_witness
        if (self.spec.get("op_unit") or {}).get("proof"):
            res["content_proof"] = {"declaration": self.spec["op_unit"]["proof"], "verified": getattr(self, "content_proof_ok", False)}
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
    if spec.get("serving_floor"):
        res["serving_floor"] = d.get("serving_floor", serving_floor_results(spec, gate_units))
    if spec["metric"]["name"] == "op_gbps":
        op_units = [u for u in gate_units if u.get("kind") == "op"]
        shaped = {shape["filter"]: [u for u in op_units if u.get("shape") == shape["filter"]]
                  for shape in spec["op_unit"]["shapes"]}
        res["per_arm"] = {arm: {shape: {"n": len(values), "median_gbps": statistics.median(values) if values else None}
                                for shape, rows in shaped.items()
                                for values in [[u["metric"] for u in rows if u.get("arm") == arm and u.get("metric") is not None]]}
                          for arm in arm_list(spec)}
        res["blocks_scored"] = min((len(full_blocks(spec, [dict(u, kind="visit") for u in rows]))
                                    for rows in shaped.values()), default=0)
        res["n_op_units"] = len(op_units)
        res.update(op_decide=d.get("op_decide", spec.get("op_decide") or {"kind": "ci_lower"}), per_shape=d.get("per_shape", {}), first_rep_gmean=d.get("first_rep_gmean"))
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
    smoke_units = [u for u in load_units(os.path.join(row_dir, "out-smoke")) if u.get("gate_unit")]
    shaped = [u for u in smoke_units if u.get("smoke_shape") == "full" and isinstance(u.get("smoke_run_id"), int)]
    if shaped and not any(u.get("kind") in ("visit", "op") for u in units):
        latest = max(u["smoke_run_id"] for u in shaped)
        units = [u for u in shaped if u["smoke_run_id"] == latest]
        mode = "full-smoke"
    else:
        mode = "smoke" if units and all(u.get("kind") == "smoke" for u in units) else "units"
    if not units and not recorded:
        units = smoke_units
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
        witnessed = u["kind"] in ("visit", "smoke", "log") or \
            (u["kind"] in UNIT_KIND and c.get("witness", c.get("kind") != "tbo"))
        if not witnessed or (u["kind"] == "c-kld" and u.get("mode") == "base" and c.get("witness_base") is False):
            u.pop("witness", None)
        if witnessed and u.get("arm") not in (spec.get("arms") or {}):
            # a prior arm the new declaration does not declare cannot be judged: a mismatch, never "unwitnessed"
            u["witness"] = {"(arm)": {"expected": "a declared arm", "observed": "no-arm", "ok": False, "line": None,
                                      "lines_scanned": 0, "log": u.get("log"), "argv_lv": None, "log_lv": None,
                                      "lv_required": MIN_LV, "note": f"prior arm {u.get('arm')!r} is not declared"}}
        elif witnessed and not (u["kind"] == "c-kld" and u.get("mode") == "base" and c.get("witness_base") is False):
            u["witness"] = witness_for(spec, u["arm"], txt, u.get("argv") if u["kind"] != "c-tbo" else None, u.get("log"),
                                       UNIT_TYPE.get(u["kind"], "served"))
        if u.get("req") is not None:
            u["metric"] = metric_of(spec, u["req"])
        if u.get("kind") == "op" or (u.get("kind") == "smoke" and spec["metric"]["name"] == "op_gbps"):
            try:
                op = spec["op_unit"]
                shape = next(x for x in op["shapes"] if x["filter"] == u["shape"])
                u["metric"] = op_trace_metric(op, shape, u["arm"], os.path.join(out_dir, "prof", u["unit_id"]))
                u["witness"] = witness_for(spec, u["arm"], txt, None, u.get("log"), "op")
            except (OSError, ValueError, KeyError, TypeError, StopIteration) as e:
                u.update(error=str(e), error_class="MISSING_OUTPUT")
        if u["kind"] == "c-kld" and txt is not None:
            m = KLD_RX.findall(txt)
            u["mean_kld"] = float(m[-1]) if m else None
        if u["kind"] == "c-tbo" and txt is not None:
            cases = H.tbo_cases(txt)
            u.update(tbo_counts(cases))
            u["nmse_lines"] = re.findall(r"(?im)^.*\bNMSE\s*=\s*[0-9.eE+-]+.*$", txt or "")
            u["required_cases"] = {rx: len({x["args"] for x in cases if not x.get("skipped") and re.search(rx, x["args"])}) for rx in (c.get("required_cases") or {})}
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
    if mode == "full-smoke":
        if d["verdict"] == "SMOKE_PASS":
            visited = {u.get("arm") for u in units if u.get("kind") == "smoke"}
            missing = [a for a in spec.get("arms", {}) if a not in visited]
            if missing:
                d = {"verdict": "INCOMPLETE_SMOKE", "polar": None, "terminal": False,
                     "reason": f"missing smoke visits for arms {missing}"}
            else:
                coverage = next((u.get("nondet_prompts_checked") for u in units if u.get("kind") == "smoke-coverage"), None)
                count = int(coverage.split("/")[0]) if coverage else None
                d = decide_smoke_correctness(spec, units, count)
        else:
            d["fix"] = smoke_served_fix(d)
    if mode == "units" and not d["terminal"] and not [u for u in units if u.get("kind") in ("visit", "op")] and \
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
           "verdict": d["verdict"], "fix": d.get("fix"), "witness_mismatches": mm[:40],
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
    sp.pop("arm_stores", None)  # selftest uses synthetic visits and must never inspect real binaries
    if spec["metric"]["name"] == "op_gbps":
        # Exercise the runner and smoke with synthetic units; never invoke a profiler here.
        sp["op_unit"] = dict(sp["op_unit"])
        sp["op_unit"].pop("proof", None)
        rule = sp.get("op_decide") or {"kind": "ci_lower"}
        gain = max(2.0, 2 * float(rule.get("threshold", 1.0)), 2 * float(keep_cfg(sp)["threshold"]),
                   2 * float((rule.get("futility") or {}).get("first_rep_gmean_min", 1.0)))
        with tempfile.TemporaryDirectory() as t:
            def gate(path):
                g = Gate(sp, os.path.join(t, path), env={}, stream=stream)
                def fake(uid, arm, shape, block):
                    witness = {k: {"expected": expect_of(sp, arm, k, "op"),
                                   "observed": expect_of(sp, arm, k, "op"), "ok": True}
                               for k in sp["knobs"]}
                    return {"unit_id": uid, "kind": "op", "arm": arm, "shape": shape["filter"],
                            "block": block, "metric": gain if arm in candidate_arms(sp) else 1.0,
                            "witness": witness, "gate_unit": True}
                g.run_op = fake
                return g
            g = gate("full")
            assert g.run() == 0
            result = json.load(open(os.path.join(g.out, "RESULT.json")))
            assert result["native_verdict"].startswith("KEEP"), result
            g = gate("smoke")
            assert g.smoke() == 0
            assert os.path.isfile(os.path.join(g.out_smoke, H.SMOKE_MEASURE))
        print("selftest ok (synthetic op runner and smoke)", file=stream)
        return 0
    quiet = open(os.devnull, "w")
    verdicts = {}
    with tempfile.TemporaryDirectory() as t:
        def gate(name, speed):
            g = Gate(sp, os.path.join(t, name), env={"FILLER_PORTS": "1"}, stream=quiet)
            g.visit_fn = stub_visit(sp, g.out, speed)
            return g
        fast = max(1.10, float(keep_cfg(sp)["threshold"]) * 1.05,
                   float((sp.get("serving_floor") or {}).get("ratio", 1.0)) * 1.05)
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
    try:
        g = Gate(spec, row_dir, env=env)
    except SpecError as e:
        if env.get("FILLER_SMOKE") != "1" and env.get("FILLER_DRYRUN") != "1":
            raise
        reason = str(e)
        if "witness scope:" in reason:
            verdict = "FUTILITY_HARNESS_WITNESS"
        elif "argv[0]" in reason:
            verdict = "FUTILITY_HARNESS_MISSING_OUTPUT"
        else:
            verdict = "FUTILITY_HARNESS_DECLARATION"
        return H.end_smoke("FAIL", 3, f"{verdict}: {reason}", os.path.join(row_dir, "out"),
                           extra={"verdict": verdict, "fix": reason, "failclass": {"side": "harness"}})
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
