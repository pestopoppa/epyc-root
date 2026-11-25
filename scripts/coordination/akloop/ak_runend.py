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
     BWS-*.md stubs in LOOP_STORE/inbox for measured, ownerless, open surfaces. Fail-soft: an error is shown as `inbox=error ...`
     AND recorded in CENSUS_STATE/inbox-state.json, which the hub reads (/api/bw_census `inbox`, the census panel).
  6. (/loop path gates) research `stage_bodies.coverage_report` (same snapshot, same registry extract) -> CENSUS_STATE/path-gates.json:
     per served path timing `cell`/`ungated`, quality `gated`/`quality-ungated`, op-perf `floored`/`grid-no-floor`/`no-lane`
     (only `floored` is gated; flow_status reads it). The file also records the registry commit used (`registry`).
  7. census/inbox/coverage read the serving registry from research-side env EPYC_ORCH_REGISTRY, which this hook points at a
     file extracted from orchestrator origin/main (`git show`), never the shared clone's uncommitted working tree.

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
ORCH_REPO = "/mnt/raid0/llm/epyc-orchestrator"
ORCH_REGISTRY_REL = "orchestration/model_registry.yaml"
ORCH_REGISTRY_CACHE = "/mnt/raid0/llm/tmp/akchain-orch-registry"
INBOX_STATE_FILE = "inbox-state.json"
PATH_GATES_FILE = "path-gates.json"
_PATH_GATES_PY = """
import json, sys
from autokernel.loop import census_coverage as cc, stage_bodies as sb
pol = json.load(open(sys.argv[1]))
reg = cc.load_registry()
if not reg:
    raise SystemExit("registry unreadable")
print(json.dumps(sb.coverage_report(reg, pol, {})))
"""
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
    """research scripts/ of `ref` (kernel_rnd is returned), extracted once per commit via fetch + git archive (read-only on the clone)."""
    remote, _, branch = ref.partition("/")
    subprocess.run(["git", "-C", repo, "fetch", "-q", remote, branch], capture_output=True)
    commit = subprocess.run(["git", "-C", repo, "rev-parse", f"{ref}^{{commit}}"], capture_output=True, text=True,
                            check=True).stdout.strip()
    root = os.path.join(cache, commit)
    kr = os.path.join(root, "scripts", "kernel_rnd")
    # all of research scripts/: stage_bodies.coverage_report (path-gates) imports scripts/lib and scripts/benchmark
    if not (os.path.isdir(os.path.join(kr, "autokernel", "lineage"))
            and os.path.isdir(os.path.join(root, "scripts", "benchmark"))):
        a = subprocess.run(["git", "-C", repo, "archive", commit, "scripts"],
                           capture_output=True, check=True)
        os.makedirs(root, exist_ok=True)
        tarfile.open(fileobj=io.BytesIO(a.stdout)).extractall(root)
    return kr


def registry_snapshot(repo: str = ORCH_REPO, ref: str = "origin/main", cache: str = ORCH_REGISTRY_CACHE,
                      run=subprocess.run) -> str | None:
    """Path of the serving registry as committed on orchestrator `ref`, extracted once per commit with `git show`
    (read-only on the clone; its uncommitted working tree is never read). None when it cannot be extracted -- the
    research side then falls back to its own default and reports that on the census coverage status."""
    try:
        remote, _, branch = ref.partition("/")
        run(["git", "-C", repo, "fetch", "-q", remote, branch], capture_output=True, timeout=120)
        commit = run(["git", "-C", repo, "rev-parse", f"{ref}^{{commit}}"], capture_output=True, text=True,
                     check=True).stdout.strip()
        dst = os.path.join(cache, commit, "model_registry.yaml")
        if not os.path.exists(dst):
            blob = run(["git", "-C", repo, "show", f"{commit}:{ORCH_REGISTRY_REL}"], capture_output=True,
                       check=True).stdout
            if not blob:
                return None
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            tmp = dst + f".tmp{os.getpid()}"
            with open(tmp, "wb") as f:
                f.write(blob)
            os.replace(tmp, dst)
        return dst
    except Exception:  # noqa: BLE001 -- fail-soft: a hook reports, it never blocks
        return None


REGISTRY_FAILED = "registry-snapshot-failed"


def registry_commit(path: str | None) -> str | None:
    """The orchestrator commit a snapshot path was extracted from (`<cache>/<commit>/model_registry.yaml`)."""
    return os.path.basename(os.path.dirname(path)) if path else None


def _registry_resolve(registry: str | None, *, live: bool = True) -> dict:
    """Which registry the research child will read, and why. status: `snapshot` (origin/main extract), `explicit`
    (caller-supplied path), `registry-snapshot-failed` (live, extract failed), `inherit` (not live: a test's injected run).
    A failed extract is a NAMED state, never a silent fallback to the shared working tree (final-gate N9)."""
    if registry is not None:
        return {"status": "explicit", "path": registry, "commit": registry_commit(registry)}
    if not live:
        return {"status": "inherit", "path": None, "commit": None}
    snap = registry_snapshot()
    if snap:
        return {"status": "snapshot", "path": snap, "commit": registry_commit(snap)}
    return {"status": REGISTRY_FAILED, "path": None, "commit": None}


def _env_for(reg: dict) -> dict | None:
    """Child env for a resolved registry. On a failed extract the child gets EPYC_ORCH_REGISTRY at a path that cannot exist, so the
    research side reports registry-unreadable instead of silently reading the shared working tree; None = plain inherit (not live)."""
    if reg["path"]:
        return {**os.environ, "EPYC_ORCH_REGISTRY": reg["path"]}
    if reg["status"] == REGISTRY_FAILED:  # point at a path that cannot exist: research reports registry-unreadable
        return {**os.environ, "EPYC_ORCH_REGISTRY": "/nonexistent/" + REGISTRY_FAILED + "/model_registry.yaml"}
    return None


def _registry_env(registry: str | None, *, live: bool = True) -> dict | None:
    """Child env with EPYC_ORCH_REGISTRY set to the origin/main extract; no variable on a failed extract; None = inherit
    (a test's injected `run` never touches the orchestrator clone unless `registry` is given)."""
    return _env_for(_registry_resolve(registry, live=live))


def _flag_registry_failure(line: str, reg: dict) -> str:
    """Census/inbox status line with the failed-extract state appended (the BW-CENSUS / `-` prefix stays intact)."""
    return f"{line} [{REGISTRY_FAILED}]" if reg["status"] == REGISTRY_FAILED else line


def path_gates(*, kernel_rnd: str | None = None, state: str = CENSUS_STATE, registry: str | None = None,
               run=subprocess.run, now: float | None = None) -> str:
    """Write CENSUS_STATE/path-gates.json from research coverage_report (read-only on every input). Returns a one-token
    summary; a failure is RECORDED in the file (`error`) so /loop reads "unknown", never a stale all-gated report."""
    kr = kernel_rnd or research_snapshot()
    pol = os.path.join(kr, "autokernel", "loop", "graph_kld_policy.json")
    rec: dict = {"schema": "epyc.ak.path_gates.v1", "at": now if now is not None else time.time()}
    reg = _registry_resolve(registry, live=run is subprocess.run)
    rec["registry"] = {k: reg[k] for k in ("status", "commit", "path")}
    try:
        if not os.path.exists(os.path.join(kr, "autokernel", "loop", "stage_bodies.py")):
            raise RuntimeError("snapshot has no stage_bodies.py")
        r = run([sys.executable, "-s", "-B", "-c", _PATH_GATES_PY, pol], cwd=kr, capture_output=True, text=True,
                timeout=120, env=_env_for(reg))
        if r.returncode != 0:
            raise RuntimeError(f"rc={r.returncode} {(r.stderr or '').strip().splitlines()[-1:] or ''}")
        rec["report"] = json.loads((r.stdout or "").strip().splitlines()[-1])
    except Exception as e:  # noqa: BLE001 -- fail-soft, but recorded where the hub reads it
        rec["error"] = f"{type(e).__name__}: {e}"[:300]
    os.makedirs(state, exist_ok=True)
    p = os.path.join(state, PATH_GATES_FILE)
    tmp = p + f".tmp{os.getpid()}"
    with open(tmp, "w") as f:
        json.dump(rec, f, indent=1, sort_keys=True)
    os.replace(tmp, p)
    if "error" in rec:
        return f"error {rec['error']}"[:200]
    return _flag_registry_failure(f"paths={len(rec['report'])}", reg)


def inbox_status(line: str) -> str:
    """ok | absent | error, from the census_inbox line (`-` = module absent from the snapshot)."""
    t = str(line or "").strip()
    if t == "-":
        return "absent"
    if t.startswith("error") or t.startswith("rc=") or not t:
        return "error"
    return "ok"


def write_inbox_state(state: str, rid: str, line: str, *, now: float | None = None) -> str:
    """Record the inbox step's outcome where the hub can see it: CENSUS_STATE/inbox-state.json (atomic replace)."""
    os.makedirs(state, exist_ok=True)
    rec = {"schema": "epyc.ak.census_inbox_state.v1", "at": now if now is not None else time.time(),
           "row": rid, "status": inbox_status(line), "detail": str(line)[:300]}
    p = os.path.join(state, INBOX_STATE_FILE)
    tmp = p + f".tmp{os.getpid()}"
    with open(tmp, "w") as f:
        json.dump(rec, f, indent=1, sort_keys=True)
    os.replace(tmp, p)
    return p


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
                  run=subprocess.run, spec_path: str | None = None, registry: str | None = None) -> str:
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
    reg = _registry_resolve(registry, live=run is subprocess.run)
    r = run([sys.executable, "-s", "-B", "-m", "autokernel.loop.census_update", "--result", result_path, "--row", rid,
             "--census", census, "--program", journal, "--doc", os.path.join(state, "census-table.md"),
             "--seeds-out", os.path.join(state, "seed-stubs"),
             *(["--spec", spec_path] if spec_path and os.path.exists(spec_path) and "--spec" in open(
                 os.path.join(kr, "autokernel", "loop", "census_update.py")).read() else []),  # KEEP-stale target fallback
             *(["--merge-static-from", seed] if os.path.exists(seed) and "merge-static-from" in open(
                 os.path.join(kr, "autokernel", "loop", "census_update.py")).read() else [])],  # committed parity/time_only -> live, every run
            cwd=kr, capture_output=True, text=True, timeout=120, env=_env_for(reg))
    last = ((r.stdout or "").strip().splitlines() or [f"rc={r.returncode} {(r.stderr or '')[-200:]}"])[-1][:300]
    return _flag_registry_failure(last, reg)


def census_inbox(rid: str, *, kernel_rnd: str | None = None, state: str = CENSUS_STATE, store: str = LOOP_STORE,
                 run=subprocess.run, registry: str | None = None) -> str:
    """RSL-R2: sync BWS-*.md stubs in the loop inbox from the live census (research `loop/census_inbox.py`, same snapshot).
    The snapshot is a git archive of research origin/main, so the module is absent until RSL-R2 lands there: "-"."""
    kr = kernel_rnd or research_snapshot()
    if not os.path.exists(os.path.join(kr, "autokernel", "loop", "census_inbox.py")):
        return "-"
    reg = _registry_resolve(registry, live=run is subprocess.run)
    r = run([sys.executable, "-s", "-B", "-m", "autokernel.loop.census_inbox", "--census",
             os.path.join(state, "mi210_bandwidth_census.json"), "--store", store], cwd=kr, capture_output=True,
            text=True, timeout=120, env=_env_for(reg))
    last = ((r.stdout or "").strip().splitlines() or [f"rc={r.returncode} {(r.stderr or '')[-200:]}"])[-1][:300]
    # a nonzero exit is never reported as the success line it may have printed before failing (it was discarded before)
    return _flag_registry_failure(last, reg) if r.returncode == 0 else f"error rc={r.returncode} {last}"[:300]


def handle(rid: str, flags: str = FLAGS, *, dry_run: bool = False, runend_run=subprocess.run,
           lineage=lineage_generate, notify_mod=None, census=census_update, inbox=None, state: str | None = None,
           gates=None) -> dict:
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
            if state is not None or census is census_update:  # an injected census never touches the live state dir
                try:
                    write_inbox_state(state or CENSUS_STATE, rid, rep["inbox"])
                except Exception as e:  # noqa: BLE001
                    rep["inbox"] = f"{rep['inbox']} (inbox-state write failed: {type(e).__name__}: {e})"
        live = state is not None or census is census_update
        gates = gates or (path_gates if census is census_update else None)
        if gates and live:   # fail-soft; refreshed at every AK run end so /loop's per-path gate status tracks the registry
            try:
                rep["gates"] = gates(state=state or CENSUS_STATE) if gates is path_gates else gates(rid)
            except Exception as e:  # noqa: BLE001
                rep["gates"] = f"error {type(e).__name__}: {e}"
    return rep


def line(rep: dict) -> str:
    c = rep.get("class") or {}
    return (f"AK-RUNEND {rep['row']} filed=[{rep.get('filed', '-')}] class={c.get('side')}/{c.get('klass')}"
            f"{' routed' if c.get('routed') else ''} lineage={rep.get('lineage', '-')} census={rep.get('census', '-')}"
            f"{' inbox=' + str(rep['inbox']) if 'inbox' in rep else ''}"
            f"{' gates=' + str(rep['gates']) if 'gates' in rep else ''}")


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
