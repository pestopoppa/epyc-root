#!/usr/bin/env python3
"""replay_allocator.py - run a rowflow.py candidate through the replay harness (see replay_lib.py for the design).

    replay_allocator.py run   --rowflow DIR --trace T.jsonl[.gz] --out D        # one replay (sandboxed worker)
    replay_allocator.py gate  --rowflow DIR [--trace T ...] [--json OUT]        # scenarios + traces + invariants; rc 1 on failure
    replay_allocator.py versions --repo R --commits A,B,... [--trace T ...]     # gate each git commit's rowflow/

The DAY trace (fixtures/2026-11-05.trace.jsonl.gz) is replayed for invariants and the idle-hours metric; the
scenario fixtures are the deploy-blocking incident classes. Every replay runs in its own python process (the candidate
module, its patched os.kill and fake clock never leak), with a scratch dir under $REPLAY_SCRATCH (default
/mnt/raid0/llm/tmp/rowflow-replay)."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import replay_lib as RL  # noqa: E402
import scenarios as SC  # noqa: E402

DAY_TRACE = os.path.join(HERE, "fixtures", "2026-11-05.trace.jsonl.gz")
SCRATCH = os.environ.get("REPLAY_SCRATCH", "/mnt/raid0/llm/tmp/rowflow-replay")
# day-trace invariants that BLOCK a deploy (the rest of the day trace is reported, not gating: a reconstructed
# trace is coarse - see record_trace.py)
DAY_BLOCKING = ("INV-NO-CRASH", "INV-STOP", "INV-REGRANT", "INV-1THREAD")


def worker(rowflow, trace, out, timeout=1800):
    r = subprocess.run([sys.executable, os.path.abspath(__file__), "run", "--rowflow", rowflow, "--trace", trace, "--out", out],
                       capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        return None, (r.stderr or r.stdout)[-2000:]
    with open(os.path.join(out, "decisions.jsonl")) as f:
        return [json.loads(l) for l in f], None


def gate(rowflow, traces=(), work=None, quiet=False):
    """-> report dict; report['pass'] False blocks a deploy."""
    work = work or tempfile.mkdtemp(prefix="gate-", dir=_scratch())
    rep = {"rowflow": rowflow, "scenarios": {}, "traces": {}, "pass": True}
    built = SC.build_all(os.path.join(work, "scenario-traces"))
    for name, (tpath, check) in built.items():
        dec, err = worker(rowflow, tpath, os.path.join(work, "sc", name))
        if dec is None:
            rep["scenarios"][name] = {"pass": False, "violations": [f"replay worker failed: {err[-300:]}"]}
            rep["pass"] = False
            continue
        _, ticks = RL.read_trace(tpath)
        inv = RL.check_invariants(ticks, dec)
        viol = list(check(dec))
        for k in SC.SUBJECT.get(name, []) + ["INV-NO-CRASH", "INV-STOP", "INV-1THREAD", "INV-EVIDENCE"]:
            viol += [f"{k}: {x}" for x in inv.get(k, [])]
        viol = sorted(set(viol))
        rep["scenarios"][name] = {"pass": not viol, "violations": viol}
        rep["pass"] &= not viol
    for tpath in traces:
        dec, err = worker(rowflow, tpath, os.path.join(work, "trace", os.path.basename(tpath)))
        if dec is None:
            rep["traces"][tpath] = {"pass": False, "error": err[-500:]}
            rep["pass"] = False
            continue
        _, ticks = RL.read_trace(tpath)
        inv = RL.check_invariants(ticks, dec)
        blocking = {k: v for k, v in inv.items() if v and k in DAY_BLOCKING}
        rep["traces"][tpath] = {"pass": not blocking, "invariants": {k: len(v) for k, v in inv.items()},
                                "examples": {k: v[:3] for k, v in inv.items() if v}, "metrics": RL.idle_metrics(dec)}
        rep["pass"] &= not blocking
    if not quiet:
        print_report(rep)
    return rep


def print_report(rep):
    print(f"replay gate: {rep['rowflow']}")
    for n, s in rep["scenarios"].items():
        print(f"  {'PASS' if s['pass'] else 'FAIL'}  {n}")
        for v in s["violations"][:4]:
            print(f"          - {v[:200]}")
    for t, s in rep["traces"].items():
        print(f"  {'PASS' if s['pass'] else 'FAIL'}  trace {os.path.basename(t)} {s.get('metrics', s.get('error', ''))}")
        for k, n in (s.get("invariants") or {}).items():
            if n:
                print(f"          {k}: {n}  e.g. {s['examples'][k][0][:160]}")
    print("GATE " + ("PASS" if rep["pass"] else "FAIL"))


def _scratch():
    os.makedirs(SCRATCH, exist_ok=True)
    return SCRATCH


def main(argv=None):
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    r = sp.add_parser("run"); r.add_argument("--rowflow", required=True); r.add_argument("--trace", required=True)
    r.add_argument("--out", required=True); r.add_argument("--max-ticks", type=int)
    g = sp.add_parser("gate"); g.add_argument("--rowflow", required=True); g.add_argument("--trace", action="append", default=None)
    g.add_argument("--no-day", action="store_true"); g.add_argument("--json")
    v = sp.add_parser("versions"); v.add_argument("--repo", required=True); v.add_argument("--commits", required=True)
    v.add_argument("--trace", action="append", default=None); v.add_argument("--no-day", action="store_true"); v.add_argument("--json")
    a = ap.parse_args(argv)
    if a.cmd == "run":
        RL.run_replay(os.path.abspath(a.rowflow), a.trace, a.out, a.max_ticks)
        return 0
    traces = a.trace if a.trace else ([] if a.no_day or not os.path.exists(DAY_TRACE) else [DAY_TRACE])
    if a.cmd == "gate":
        rep = gate(os.path.abspath(a.rowflow), traces)
        if a.json:
            json.dump(rep, open(a.json, "w"), indent=1)
        return 0 if rep["pass"] else 1
    reps = {}
    for sha in a.commits.split(","):
        d = tempfile.mkdtemp(prefix=f"v-{sha[:9]}-", dir=_scratch())
        RL.checkout_commit(a.repo, sha, os.path.join(d, "rowflow"))
        print(f"\n=== {sha}")
        reps[sha] = gate(os.path.join(d, "rowflow"), traces, work=os.path.join(d, "work"))
    names = list(next(iter(reps.values()))["scenarios"])
    print("\n| check | " + " | ".join(s[:9] for s in reps) + " |")
    print("|---|" + "---|" * len(reps))
    for n in names:
        print(f"| {n} | " + " | ".join("pass" if reps[s]["scenarios"][n]["pass"] else "FAIL" for s in reps) + " |")
    for t in traces:
        print(f"| day {os.path.basename(t)} | " + " | ".join("pass" if reps[s]["traces"][t]["pass"] else "FAIL" for s in reps) + " |")
        print(f"| idle q-h / gpu-h | " + " | ".join(
            f"{reps[s]['traces'][t].get('metrics', {}).get('idle_quarter_hours')}/{reps[s]['traces'][t].get('metrics', {}).get('idle_gpu_hours')}" for s in reps) + " |")
    if a.json:
        json.dump(reps, open(a.json, "w"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
