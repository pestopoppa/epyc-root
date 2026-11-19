#!/usr/bin/env python3
"""worktree_reaper.py — zero-token TTL reaper for AGENT worktrees (run periodically by the disk janitor).

Walks every registered LINKED worktree of every repo in worktree_gate.DEFAULT_REPOS whose realpath
is under one of --roots, classifies it with worktree_gate.classify, and:

    REMOVABLE / RECENT, idle >= --ttl-clean-days  -> REMOVE  (worktree_gate.remove_one; never --force)
    DIRTY / UNLANDED,   idle >= --ttl-dirty-days  -> SALVAGE (worktree_salvage.retire: bundle +
                                                              salvage branch, guarded_rm, deregister)
    BUSY / REFERENCED / EVIDENCE / UNVERIFIABLE / PROTECTED / MISSING -> KEEP (reason logged;
                                                              MISSING is reported, never pruned)
    below the TTL                                 -> KEEP-RECENT
    <root>/mains/, <root>/pool/, locked, KEEP-marked, canonical roots -> SKIP (never acted on)

Each repo is fetched ONCE per pass (`git fetch --quiet origin`); a failed fetch skips that whole repo
this pass (fail closed). Dry-run unless --apply. At most --max actions per pass. Deletion happens
ONLY through worktree_gate.remove_one and worktree_salvage.retire — this file deletes nothing itself.
Exit 0 on a completed pass (per-tree errors are logged), 2 on usage error.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import worktree_gate as wg  # noqa: E402
import worktree_salvage as ws  # noqa: E402

DEFAULT_ROOTS = [f"{wg.LLM}/worktrees", "/workspace/.worktrees"]
SKIP_SUBDIRS = ("mains", "pool")
KEEP_VERDICTS = {"BUSY", "REFERENCED", "EVIDENCE", "UNVERIFIABLE", "PROTECTED", "MISSING"}
FETCH_TIMEOUT = 300


def _canonical_roots() -> list[str]:
    return ["/workspace", f"{wg.LLM}/epyc-root"]


def _under(path: str, root: str) -> bool:
    r = os.path.realpath(root).rstrip("/")
    return path == r or path.startswith(r + "/")


def _skip_reason(wt: wg.Worktree, real: str, root: str) -> str | None:
    rr = os.path.realpath(root).rstrip("/")
    for sub in SKIP_SUBDIRS:
        if _under(real, os.path.join(rr, sub)):
            return f"under {sub}/ (roster/pool lane)"
    if wt.locked:
        return "locked worktree"
    if os.path.isdir(wt.path):
        km = ws._keep_marker(wt.path)
        if km:
            return f"KEEP marker {km}"
    canon = {os.path.realpath(c) for c in _canonical_roots()} | {os.path.realpath(r) for r in wg.DEFAULT_REPOS}
    if real in canon:
        return "canonical root"
    if os.path.isdir(wt.path):
        pr = wg._protected_reason(wt, _canonical_roots())
        if pr:
            return pr
    return None


def _fetch(repo: str) -> str | None:
    try:
        cp = wg._git(["fetch", "--quiet", "origin"], cwd=repo, timeout=FETCH_TIMEOUT)
    except (subprocess.TimeoutExpired, OSError) as exc:
        return f"fetch failed: {exc}"[:200]
    if cp.returncode != 0:
        return f"fetch failed rc={cp.returncode}: {cp.stderr.strip()[:200]}"
    return None


def _q(s: object) -> str:
    return str(s).replace("'", '"').replace("\n", " ")[:400]


DEFAULT_BASE_FOR = {f"{wg.LLM}/llama.cpp": "origin/master"}   # its remote main branch is master


def reap(*, roots: list[str], ttl_clean: float, ttl_dirty: float, salvage_dir: str, apply: bool,
         max_actions: int, base: str, repos: list[str] | None = None, probe: wg.Probe | None = None,
         now: float | None = None, trash_root: str | None = None, guarded_rm: str | None = None,
         emit=print, base_for: dict[str, str] | None = None) -> dict:
    tag = "WT-REAP" if apply else "WT-REAP-DRYRUN"
    base_for = dict(DEFAULT_BASE_FOR if base_for is None else base_for)
    now = time.time() if now is None else now
    repos = list(wg.DEFAULT_REPOS if repos is None else repos)
    probe = probe if probe is not None else wg.gather_probe()
    rows: list[dict] = []
    counts = {"trees": 0, "remove": 0, "salvage": 0, "kept": 0, "errors": 0}
    actions = 0

    def line(path, verdict, idle, action, reason, result):
        rows.append(dict(path=path, verdict=verdict, idle_d=idle, action=action, reason=reason, result=result))
        emit(f"{tag} path={path} verdict={verdict} idle_d={idle} action={action} "
             f"reason='{_q(reason)}' result='{_q(result)}'")

    for repo in repos:
        if not os.path.isdir(repo):
            continue
        try:
            wts = wg.list_worktrees(repo)
        except (RuntimeError, subprocess.TimeoutExpired, OSError) as exc:
            counts["errors"] += 1
            emit(f"{tag} repo={repo} action=REFUSED reason='{_q(exc)}'")
            continue
        mine = []
        for wt in wts:
            real = os.path.realpath(wt.path)
            root = next((r for r in roots if _under(real, r)), None)
            if root is not None:
                mine.append((wt, real, root))
        if not mine:
            continue
        ferr = _fetch(repo)
        rbase = base_for.get(os.path.realpath(repo), base_for.get(repo, base))   # llama.cpp lands on origin/master
        for wt, real, root in mine:
            counts["trees"] += 1
            if ferr:
                counts["kept"] += 1
                line(wt.path, "-", "-", "SKIP", f"repo {repo} {ferr}", "untouched (fail closed)")
                continue
            sr = _skip_reason(wt, real, root)
            if sr:
                counts["kept"] += 1
                line(wt.path, "-", "-", "SKIP", sr, "untouched")
                continue
            try:
                wg.classify(wt, base=rbase, min_idle_days=0, probe=probe,
                            canonical_roots=_canonical_roots(), now=now)
            except Exception as exc:  # noqa: BLE001 — per-tree error, keep going
                counts["errors"] += 1
                line(wt.path, "ERROR", "-", "KEEP-ERROR", f"classify raised: {exc}", "untouched")
                continue
            v, idle = wt.verdict, wt.idle_days
            reason = "; ".join(wt.reasons)
            if v in KEEP_VERDICTS:
                counts["kept"] += 1
                line(wt.path, v, idle, f"KEEP-{v}", reason, "untouched" + (" (registration reported, not pruned)" if v == "MISSING" else ""))
                continue
            if v in (wg.REMOVABLE, "RECENT"):
                ttl, act = ttl_clean, "REMOVE"
            elif v in ("DIRTY", "UNLANDED"):
                ttl, act = ttl_dirty, "SALVAGE"
            else:
                counts["kept"] += 1
                line(wt.path, v, idle, f"KEEP-{v}", reason, "untouched (unknown verdict)")
                continue
            if idle is None or idle < ttl:
                counts["kept"] += 1
                line(wt.path, v, idle, "KEEP-RECENT", f"idle {idle} d < ttl {ttl} d", "untouched")
                continue
            if actions >= max_actions:
                counts["kept"] += 1
                line(wt.path, v, idle, "KEEP-BUDGET", f"--max {max_actions} reached", "untouched")
                continue
            actions += 1
            if act == "REMOVE":
                if not apply:
                    counts["remove"] += 1
                    line(wt.path, v, idle, "REMOVE", reason, "dry-run: would git worktree remove")
                    continue
                try:
                    ok, msg = wg.remove_one(wt.path, base=rbase, min_idle_days=ttl_clean, fetch=False, probe=probe)
                except Exception as exc:  # noqa: BLE001
                    ok, msg = False, f"remove_one raised: {exc}"
                if ok:
                    counts["remove"] += 1
                    line(wt.path, v, idle, "REMOVE", reason, msg)
                else:
                    counts["errors"] += 1
                    line(wt.path, v, idle, "REFUSED", reason, msg)
                continue
            kw = dict(apply=apply, salvage_dir=salvage_dir, probe=probe, base=rbase)
            if trash_root:
                kw["trash_root"] = trash_root
            if guarded_rm:
                kw["guarded_rm"] = guarded_rm
            try:
                r = ws.retire(wt.path, **kw)
            except Exception as exc:  # noqa: BLE001
                r = {"refused": None, "error": f"retire raised: {exc}"}
            if r.get("refused"):
                counts["errors"] += 1
                line(wt.path, v, idle, "REFUSED", reason, r["refused"])
            elif r.get("error"):
                counts["errors"] += 1
                line(wt.path, v, idle, "REFUSED", reason, f"error: {r['error']}")
            else:
                counts["salvage"] += 1
                if apply:
                    sv = r.get("salvage") or {}
                    res = (f"{r.get('action')} bundle={sv.get('bundle')} branch={sv.get('salvage_branch')} "
                           f"deregistered={r.get('deregistered')}")
                else:
                    res = f"dry-run: would {r.get('action')} (dirty={r.get('dirty')} unlanded={r.get('unlanded')})"
                line(wt.path, v, idle, "SALVAGE", reason, res)
    emit(f"{tag} SUMMARY roots={','.join(roots)} trees={counts['trees']} remove={counts['remove']} "
         f"salvage={counts['salvage']} kept={counts['kept']} errors={counts['errors']}")
    return {"apply": apply, "counts": counts, "rows": rows}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="TTL reaper for agent worktrees (dry-run unless --apply)")
    ap.add_argument("--roots", nargs="+", default=DEFAULT_ROOTS)
    ap.add_argument("--ttl-clean-days", type=float, default=3.0)
    ap.add_argument("--ttl-dirty-days", type=float, default=7.0)
    ap.add_argument("--salvage-dir", default=ws.DEFAULT_SALVAGE_DIR)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--max", type=int, default=20)
    ap.add_argument("--log")
    ap.add_argument("--base", default=wg.DEFAULT_BASE)
    ap.add_argument("--base-for", action="append", default=[], metavar="REPO=BASE",
                    help="per-repo landed base (default: /mnt/raid0/llm/llama.cpp=origin/master)")
    ap.add_argument("--json", action="store_true", help="also print the JSON result at the end")
    try:
        a = ap.parse_args(argv)
    except SystemExit as exc:
        return 0 if exc.code == 0 else 2
    if a.max < 0 or a.ttl_clean_days < 0 or a.ttl_dirty_days < 0:
        print("worktree_reaper: --max/--ttl-* must be >= 0", file=sys.stderr)
        return 2
    logf = None
    if a.log:
        os.makedirs(os.path.dirname(os.path.abspath(a.log)), exist_ok=True)
        logf = open(a.log, "a")

    def emit(s: str) -> None:
        print(s, flush=True)
        if logf:
            logf.write(f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} {s}\n")
            logf.flush()

    try:
        res = reap(roots=a.roots, ttl_clean=a.ttl_clean_days, ttl_dirty=a.ttl_dirty_days,
                   salvage_dir=a.salvage_dir, apply=a.apply, max_actions=a.max, base=a.base, emit=emit,
                   base_for=dict(DEFAULT_BASE_FOR, **dict(x.split("=", 1) for x in a.base_for if "=" in x)))
    finally:
        if logf:
            logf.close()
    if a.json:
        print(json.dumps(res, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
