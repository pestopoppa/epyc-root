#!/usr/bin/env python3
"""ak_runend.py -- AKPL-P3: what the owner watcher does on an ENDED event of an AutoKernel row, with zero LLM turns.

    ak_runend.py <row-id> [--flags DIR] [--dry-run]

  1. akloop chain rows (akc-*): `runend.py <id> --gate-eval --file` -- gate_eval drafts verdict.json and, when the
     verdict is policy-decided (every chain stage writes a polar token), files it from a pinned origin/main;
  2. every AK row: the P5 failure classifier over its RESULT.json (akloop/failclass.py); a harness failure is routed
     to the pipeline inbox (notify, owner pipeline-mgmt) instead of costing the AK owner a turn;
  3. a C-fold composite / fold row (c<N>-fold-*, c<N>-composite-*) that ended: the P4 lineage manager regenerates the
     keep ledger / fold list (`autokernel.lineage generate`, research origin/main extracted with `git archive` --
     never the research clone's tree). A chain fold-check KEEP already triggered it in-process (stage_bodies).
  4. every AK row with a RESULT.json: the DETERMINISTIC bandwidth census updater (research
     `autokernel/loop/census_update.py`, from the same origin/main snapshot) re-ranks the MI210 served-kernel census
     in CENSUS_STATE (census JSON seeded from the committed copy, generated table, journal lines, seed stubs).
     Idempotent per RESULT sha256; a session folds CENSUS_STATE back into the research repo (no shared-clone writes here).
  5. after step 4 (RSL-R2): research `autokernel/loop/census_inbox.py` (same snapshot; "-" while absent there) installs/removes
     BWS-*.md stubs in LOOP_STORE/inbox for measured, ownerless, open surfaces. Fail-soft: an error is shown as `inbox=error ...`.

Prints ONE line (`AK-RUNEND <id> filed=[...] class=<side>/<klass> lineage=<dir|->`). Exit 0 always: a watcher hook
reports, it never blocks the watcher. --dry-run prints what it would run and runs nothing.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import subprocess
import sys
import tarfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
RUNEND = os.path.join(REPO, ".claude", "skills", "row-owner-loop", "scripts", "runend.py")
FLAGS = "/mnt/raid0/llm/tmp/compute-flags"
RESEARCH_REPO = "/mnt/raid0/llm/epyc-inference-research"
RESEARCH_CACHE = "/mnt/raid0/llm/tmp/akchain-research"
LINEAGE_OUT = "/mnt/raid0/llm/tmp/akchain-lineage"
CENSUS_STATE = "/mnt/raid0/llm/tmp/ak-bw-census"
LOOP_STORE = "/mnt/raid0/llm/autokernel/loop-memory"  # the loop's store; its inbox/ is what the planner reads
COMPOSITE_RX = re.compile(r"^c\d+-(fold|composite)-")
sys.path.insert(0, HERE)


def manifest(flags: str, rid: str) -> dict:
    for sub in ("ready", os.path.join("ready", ".withdrawn")):
        p = os.path.join(flags, sub, rid + ".json")
        try:
            return json.load(open(p))
        except (OSError, ValueError):
            continue
    return {}


def classify(flags: str, rid: str, man: dict, *, route: bool, notify_mod=None) -> dict:
    import failclass as FC
    rp = str(man.get("result_path") or "")
    try:
        res = json.load(open(rp))
    except (OSError, ValueError):
        res = None
    lt = None
    for p in (os.path.join(flags, "dryrun", rid, "launcher.out"),):
        try:
            lt = open(p, errors="replace").read()[-20000:]
        except OSError:
            pass
    c = FC.classify_result(res, lt) if res is not None else FC.Classification(
        "harness", "result_contract", "result:missing", f"no RESULT at {rp or '(no result_path)'}", rid, "result")
    out = c.to_dict()
    if route and c.side == "harness":
        out["routed"] = bool(FC.route(c, flags, notify_mod=notify_mod, rid=rid))
    return out


def research_snapshot(repo: str = RESEARCH_REPO, ref: str = "origin/main", cache: str = RESEARCH_CACHE) -> str:
    """scripts/kernel_rnd of research `ref`, extracted once per commit via fetch + git archive (read-only on the clone)."""
    remote, _, branch = ref.partition("/")
    subprocess.run(["git", "-C", repo, "fetch", "-q", remote, branch], capture_output=True)
    commit = subprocess.run(["git", "-C", repo, "rev-parse", f"{ref}^{{commit}}"], capture_output=True, text=True,
                            check=True).stdout.strip()
    root = os.path.join(cache, commit)
    kr = os.path.join(root, "scripts", "kernel_rnd")
    if not os.path.isdir(os.path.join(kr, "autokernel", "lineage")):
        a = subprocess.run(["git", "-C", repo, "archive", commit, "scripts/kernel_rnd/autokernel"], capture_output=True,
                           check=True)
        os.makedirs(root, exist_ok=True)
        tarfile.open(fileobj=io.BytesIO(a.stdout)).extractall(root)
    return kr


def lineage_generate(rid: str, *, kernel_rnd: str | None = None, out_root: str = LINEAGE_OUT,
                     run=subprocess.run) -> str:
    kr = kernel_rnd or research_snapshot()
    out = os.path.join(out_root, f"{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}-composite-{rid}")
    os.makedirs(out, exist_ok=True)
    run([sys.executable, "-s", "-B", "-m", "autokernel.lineage", "generate", "--out", out], cwd=kr,
        capture_output=True, text=True, timeout=900)
    with open(os.path.join(out, "event.json"), "w") as f:
        json.dump({"kind": "composite", "row": rid}, f)
    return out


def census_update(rid: str, result_path: str, *, kernel_rnd: str | None = None, state: str = CENSUS_STATE,
                  run=subprocess.run, spec_path: str | None = None) -> str:
    """Deterministic census step (no LLM). Returns the updater's BW-CENSUS line."""
    if not result_path or not os.path.exists(result_path):
        return "-"
    kr = kernel_rnd or research_snapshot()
    os.makedirs(state, exist_ok=True)
    census = os.path.join(state, "mi210_bandwidth_census.json")
    seed = os.path.join(kr, "autokernel", "loop", "census", "mi210_bandwidth_census.json")
    if not os.path.exists(census):
        if os.path.exists(seed):
            with open(seed) as f, open(census, "w") as g:
                g.write(f.read())
    journal = os.path.join(state, "journal.md")
    if not os.path.exists(journal):
        open(journal, "w").write("# AK bandwidth census journal (deterministic; fold into loop/program.md)\n")
    r = run([sys.executable, "-s", "-B", "-m", "autokernel.loop.census_update", "--result", result_path, "--row", rid,
             "--census", census, "--program", journal, "--doc", os.path.join(state, "census-table.md"),
             "--seeds-out", os.path.join(state, "seed-stubs"),
             *(["--spec", spec_path] if spec_path and os.path.exists(spec_path) and "--spec" in open(
                 os.path.join(kr, "autokernel", "loop", "census_update.py")).read() else []),  # KEEP-stale target fallback
             *(["--merge-static-from", seed] if os.path.exists(seed) and "merge-static-from" in open(
                 os.path.join(kr, "autokernel", "loop", "census_update.py")).read() else [])],  # committed parity/time_only -> live, every run
            cwd=kr, capture_output=True, text=True, timeout=120)
    return ((r.stdout or "").strip().splitlines() or [f"rc={r.returncode} {(r.stderr or '')[-200:]}"])[-1][:300]


def census_inbox(rid: str, *, kernel_rnd: str | None = None, state: str = CENSUS_STATE, store: str = LOOP_STORE,
                 run=subprocess.run) -> str:
    """RSL-R2: sync BWS-*.md stubs in the loop inbox from the live census (research `loop/census_inbox.py`, same snapshot).
    The snapshot is a git archive of research origin/main, so the module is absent until RSL-R2 lands there: "-"."""
    kr = kernel_rnd or research_snapshot()
    if not os.path.exists(os.path.join(kr, "autokernel", "loop", "census_inbox.py")):
        return "-"
    r = run([sys.executable, "-s", "-B", "-m", "autokernel.loop.census_inbox", "--census",
             os.path.join(state, "mi210_bandwidth_census.json"), "--store", store], cwd=kr, capture_output=True,
            text=True, timeout=120)
    return ((r.stdout or "").strip().splitlines() or [f"rc={r.returncode} {(r.stderr or '')[-200:]}"])[-1][:300]


def handle(rid: str, flags: str = FLAGS, *, dry_run: bool = False, runend_run=subprocess.run,
           lineage=lineage_generate, notify_mod=None, census=census_update, inbox=None) -> dict:
    man = manifest(flags, rid)
    rep: dict = {"row": rid}
    if rid.startswith("akc-"):
        argv = [sys.executable, RUNEND, rid, "--gate-eval", "--file"]
        if dry_run:
            rep["filed"] = "dry-run: " + " ".join(argv[1:])
        else:
            r = runend_run(argv, capture_output=True, text=True, timeout=900)
            rep["filed"] = ((r.stdout or "").strip().splitlines() or [f"rc={r.returncode}"])[-1][:160]
    try:
        rep["class"] = classify(flags, rid, man, route=not dry_run, notify_mod=notify_mod)
    except Exception as e:  # noqa: BLE001
        rep["class"] = {"side": "unknown", "klass": "classifier_error", "error": f"{type(e).__name__}: {e}"}
    if COMPOSITE_RX.match(rid):
        if dry_run:
            rep["lineage"] = "dry-run: autokernel.lineage generate"
        else:
            try:
                rep["lineage"] = lineage(rid)
            except Exception as e:  # noqa: BLE001
                rep["lineage"] = f"error {type(e).__name__}: {e}"
    rp = str(man.get("result_path") or "")
    if dry_run:
        rep["census"] = f"dry-run: census_update --result {rp or '-'}"
    else:
        try:
            sp = next((p for p in (os.path.join(flags, "ready", rid + ".json"),
                                   os.path.join(flags, "ready", ".withdrawn", rid + ".json")) if os.path.exists(p)), None)
            rep["census"] = census(rid, rp, spec_path=sp) if census is census_update else census(rid, rp)
        except Exception as e:  # noqa: BLE001
            rep["census"] = f"error {type(e).__name__}: {e}"
        inbox = inbox or (census_inbox if census is census_update else None)  # an injected census never touches the live store
        if inbox and str(rep["census"]).startswith("BW-CENSUS"):
            try:
                rep["inbox"] = inbox(rid)
            except Exception as e:  # noqa: BLE001 -- fail-soft: an inbox error is logged on the AK-RUNEND line, never fails the run-end
                rep["inbox"] = f"error {type(e).__name__}: {e}"
    return rep


def line(rep: dict) -> str:
    c = rep.get("class") or {}
    return (f"AK-RUNEND {rep['row']} filed=[{rep.get('filed', '-')}] class={c.get('side')}/{c.get('klass')}"
            f"{' routed' if c.get('routed') else ''} lineage={rep.get('lineage', '-')} census={rep.get('census', '-')}"
            f"{' inbox=' + str(rep['inbox']) if 'inbox' in rep else ''}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("row")
    ap.add_argument("--flags", default=FLAGS)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    rep = handle(a.row, a.flags, dry_run=a.dry_run)
    print(json.dumps(rep, indent=1) if a.json else line(rep))
    return 0


if __name__ == "__main__":
    sys.exit(main())
