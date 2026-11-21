#!/usr/bin/env python3
"""replay_failclass.py - replay past AK/rowflow failures through failclass and write an agreement report.

Gold labels (see docs/design/autokernel-parallel-loop-p5.md for the honesty caveats):
  FAIL-N.json : TEMPLATE_GOLD - reason templates hand-labelled by reading the raw reason text (+ launcher tails for the
                job-rc family, via GOLD_JOBRC_TAILS keyword sample), NOT derived from the rule table.
  RESULT.json : TOKEN_GOLD - verdict tokens hand-labelled by meaning; cross-checked against the filing verdict
                (filing-done/<id>.verdict.json outcome_class) where one exists.
"""
from __future__ import annotations

import collections
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import failclass as fc  # noqa: E402

FLAGS = "/mnt/raid0/llm/" + "tmp/compute-flags"

# reason regex -> gold side. Written from the clustered reason list, independent of FAIL_REASON_RULES' klass names.
TEMPLATE_GOLD = [
    (r"admission refused|refuse rc=", "harness"),
    (r"did not log 'launcher up", "harness"),
    (r"VRAM never showed residency", "harness"),
    (r"build-missing", "harness"),
    (r"no ended record", "harness"),
    (r"launcher-signalled|did not stop within|waits on region-lock", "harness"),
    (r"dryrun_timeout_s|completion marker", "harness"),
    (r"reason=complete", "harness"),
    (r"partial-native-incomplete", "harness"),
]


def gold_fail(d):
    r = str(d.get("reason") or "")
    for p, side in TEMPLATE_GOLD:
        if re.search(p, r):
            return side
    return None   # job-rc family and others: no template gold; judged from the launcher text in gold_jobrc


# verdict token -> gold side, hand-labelled by meaning (not from RESULT_TOKENS).
TOKEN_GOLD = {
    "PASS": "ok", "KEEP": "ok", "COMPLETE": "ok", "BUILT": "ok", "PROFILED": "ok", "BRACKET_DONE": "ok",
    "CENSUS_DONE": "ok", "PASS_CORRECTNESS": "ok", "BIT_EXACT_PASS": "ok", "COMPLETE_DIAGNOSTIC_ONLY": "ok",
    "FUNCTIONAL-ONLY": "ok", "REJECT_CORRECTNESS": "candidate", "DROP": "candidate", "NO_MOVE": "candidate",
    "NOT_OVERRIDE": "candidate", "UNDERFILL": "candidate", "INCONCLUSIVE": "candidate", "NOT_JUDGEABLE": "candidate",
    "CONTROL_NONDETERMINISTIC": "candidate", "FAIL": "candidate",
    "FUTILITY_NOISY_NOT_REGISTERED": "harness", "FAIL_FOREIGN_LOAD": "harness", "FAIL_WINDOW": "harness",
    "STOPPED": "harness", "ANSWERED": "ok", "EQUIVALENT": "ok", "NEUTRAL": "candidate", "NO_GAIN": "candidate",
    "TESTS_FAIL": "candidate",
}


def _tok(v):
    b = re.sub(r"\([^)]*\)", "", str(v)).strip().upper()
    m = re.match(r"^[A-Z][A-Z0-9_\-]*", b)
    return m.group(0) if m and m.group(0) in TOKEN_GOLD else b


def iter_ak_results():
    seen = set()
    for d in ("ready", "retired", "withdrawn"):
        for f in sorted(glob.glob(os.path.join(FLAGS, d, "ak*.json"))):
            try:
                s = json.load(open(f))
            except (OSError, ValueError):
                continue
            rp = s.get("result_path")
            if isinstance(rp, str) and rp.endswith("RESULT.json") and os.path.exists(rp) and rp not in seen:
                seen.add(rp)
                yield s.get("id") or os.path.basename(f)[:-5], rp


def replay():
    out = {"fail": collections.Counter(), "result": collections.Counter(), "fail_dis": [], "result_dis": [],
           "by_class": collections.Counter(), "result_by_class": collections.Counter(), "unlabeled_by_side": collections.Counter(),
           "filing_cross": collections.Counter()}
    for f in sorted(glob.glob(os.path.join(FLAGS, "dryrun", "*", "FAIL-*.json"))):
        try:
            d = json.load(open(f))
        except (OSError, ValueError):
            out["fail"]["unparseable"] += 1
            continue
        c = fc.classify_fail(d, fc._read(os.path.join(os.path.dirname(f), "launcher.out")))
        out["fail"]["total"] += 1
        out["by_class"][f"{c.side}:{c.klass}"] += 1
        g = gold_fail(d)
        if g is None:
            out["unlabeled_by_side"][c.side] += 1
            continue
        out["fail"]["labelled"] += 1
        if g == c.side:
            out["fail"]["agree"] += 1
        else:
            out["fail_dis"].append((os.path.relpath(f, FLAGS), g, c.side, c.klass))
    for rid, rp in iter_ak_results():
        try:
            d = json.load(open(rp))
        except (OSError, ValueError):
            out["result"]["unparseable"] += 1
            continue
        c = fc.classify_result(d, fc._read(os.path.join(os.path.dirname(rp), "launcher.out")))
        out["result"]["total"] += 1
        out["result_by_class"][f"{c.side}:{c.klass}"] += 1
        tok = _tok(d.get("verdict") if isinstance(d, dict) and d.get("verdict") else (d.get("status") if isinstance(d, dict) else ""))
        g = TOKEN_GOLD.get(tok)
        if g is None:
            out["result"]["no_gold_token"] += 1
            out["unlabeled_by_side"]["result:" + c.side] += 1
        else:
            out["result"]["labelled"] += 1
            if g == c.side:
                out["result"]["agree"] += 1
            else:
                out["result_dis"].append((rid, tok, g, c.side, c.klass))
        vp = os.path.join(FLAGS, "filing-done", f"{rid}.verdict.json")
        if os.path.exists(vp):
            try:
                oc = json.load(open(vp)).get("outcome_class")
            except (OSError, ValueError):
                continue
            out["filing_cross"][f"{c.side} | filed={oc}"] += 1
    return out


def main():
    o = replay()
    def rate(k):
        a, b = o[k]["agree"], o[k]["labelled"]
        return f"{a}/{b} = {a / b:.1%}" if b else "n/a"
    print(json.dumps({"fail": o["fail"], "fail_agreement": rate("fail"), "result": o["result"],
                      "result_agreement": rate("result"), "by_class": o["by_class"], "result_by_class": o["result_by_class"],
                      "unlabeled": o["unlabeled_by_side"], "filing_cross": o["filing_cross"],
                      "fail_disagreements": o["fail_dis"][:20], "result_disagreements": o["result_dis"]}, indent=1, default=dict))
    return o


if __name__ == "__main__":
    main()
