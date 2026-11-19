#!/usr/bin/env python3
"""worktree_footprint.py - GiB and tree count of git worktrees per owner, for the flow scoreboard (LOOP-37).

A worker that never removes its landed trees should be visible BEFORE the disk floor. Owners: NI
(codex-ni*/ni0X lanes), refactor, codex3, other (a name rule, not a roster read: cheap and stable).

COST DISCIPLINE. The scoreboard ticks every 10 minutes; a recursive `du` over ~250 trees at that rate
would itself be the disk and CPU problem. So the tree COUNT comes from `git worktree list --porcelain`
(cheap, every tick) and SIZES come from a cache file: each call re-measures at most MAX_DU_PER_CALL
trees whose cached size is older than SIZE_TTL_S, stalest first, one `du` at a time under nice/ionice,
so a full census refreshes over several ticks and no tick walks more than a handful of trees. Trees not
yet measured are counted in `unsized` and never guessed. Read-only apart from the cache file.

    python3 worktree_footprint.py [--cache FILE] [--max-du N] [--json]
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import time

sys.path[:0] = [os.path.dirname(os.path.abspath(__file__))]   # bin/ when installed, scripts/coordination/ in the repo
import quiet_host  # noqa: E402  the ONE quiet-host check (2026-11-10 FAIL_FOREIGN_LOAD)

LLM = "/mnt/raid0/llm"
REPOS = [f"{LLM}/epyc-root", f"{LLM}/epyc-orchestrator", f"{LLM}/epyc-inference-research", f"{LLM}/llama.cpp"]
CACHE_DEFAULT = f"{LLM}/tmp/compute-flags/worktree-footprint-cache.json"
SIZE_TTL_S = 6 * 3600
MAX_DU_PER_CALL = 4
DU_TIMEOUT_S = 300
TOTAL_BUDGET_S = 30.0   # hard wall-clock budget per collect() call: the scoreboard tick must never stall on this
OWNERS = ("NI", "refactor", "codex3", "other")
_NI = re.compile(r"(^|[/-])(codex-ni|ni0\d)")
_REFACTOR = re.compile(r"(^|[/-])refactor")
_CODEX3 = re.compile(r"(^|[/-])codex3($|[-_0-9])")


def owner_of(path: str, branch: str = "") -> str:
    """Name rule on the tree's directory name, then its branch."""
    for text in (os.path.basename(path.rstrip("/")), branch):
        if _NI.search(text):
            return "NI"
        if _REFACTOR.search(text):
            return "refactor"
        if _CODEX3.search(text):
            return "codex3"
    return "other"


def list_trees(repos: list[str], remaining=None) -> list[dict]:
    out: list[dict] = []
    for repo in repos:
        left = 60.0 if remaining is None else min(60.0, remaining())
        if left <= 0:
            break                          # budget spent: report what we have
        try:
            cp = subprocess.run(["git", "worktree", "list", "--porcelain"], cwd=repo, capture_output=True,
                                text=True, timeout=left, env=dict(os.environ, GIT_OPTIONAL_LOCKS="0", LC_ALL="C"))
        except (OSError, subprocess.TimeoutExpired):
            continue
        if cp.returncode != 0:
            continue
        first, cur = True, None
        for line in cp.stdout.splitlines() + [""]:
            if not line:
                if cur is not None:
                    if not first:          # the main worktree is not a throwaway tree
                        out.append(cur)
                    first = False
                cur = None
                continue
            key, _, val = line.partition(" ")
            if key == "worktree":
                cur = {"path": val, "repo": repo, "branch": ""}
            elif cur is not None and key == "branch":
                cur["branch"] = val.removeprefix("refs/heads/")
    return out


def _du(path: str, timeout: float = DU_TIMEOUT_S) -> int | None:
    cmd = quiet_host.scan_prefix() + ["du", "-sx", "--block-size=1", path]
    try:
        cp = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return int(cp.stdout.split()[0]) if cp.stdout.split() else None
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None


def _load(cache: str) -> dict:
    try:
        with open(cache) as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _save(cache: str, data: dict) -> None:
    try:
        os.makedirs(os.path.dirname(cache), exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(cache), prefix=".wtfp.")
        with os.fdopen(fd, "w") as f:
            json.dump(data, f)
        os.replace(tmp, cache)
    except OSError:
        pass


def collect(repos: list[str] | None = None, cache: str = CACHE_DEFAULT, *, now: float | None = None,
            max_du: int = MAX_DU_PER_CALL, ttl_s: float = SIZE_TTL_S, du=_du, lister=list_trees,
            budget_s: float = TOTAL_BUDGET_S, clock=time.monotonic) -> dict:
    """{owner: {trees, bytes, sized}} plus `_meta`; measures at most `max_du` stale trees, and never
    spends more than `budget_s` seconds in total (listing + du): a spent budget skips the remaining
    work and says so in `_meta.budget_exhausted`."""
    now = time.time() if now is None else now
    t0 = clock()
    remaining = lambda: budget_s - (clock() - t0)  # noqa: E731
    trees = lister(repos or REPOS, remaining) if lister is list_trees else lister(repos or REPOS)
    sizes = {p: v for p, v in _load(cache).get("sizes", {}).items() if isinstance(v, dict)}
    live = {t["path"] for t in trees}
    sizes = {p: v for p, v in sizes.items() if p in live and os.path.isdir(p)}   # removed trees leave the cache
    stale = sorted((t["path"] for t in trees if os.path.isdir(t["path"])
                    and now - float(sizes.get(t["path"], {}).get("at", 0)) >= ttl_s),
                   key=lambda p: float(sizes.get(p, {}).get("at", 0)))
    measured = 0
    exhausted = remaining() <= 0
    if du is _du and quiet_host.defer("worktree_footprint", log=lambda m: print(m, file=sys.stderr)):
        stale_todo = []                                # quiet-host grant live: counts only, no du this tick
    else:
        stale_todo = stale[:max(0, max_du)]
    for p in stale_todo:
        left = remaining()
        if left <= 0:
            exhausted = True
            break
        b = _du(p, timeout=min(DU_TIMEOUT_S, left)) if du is _du else du(p)
        if b is not None:
            sizes[p] = {"bytes": b, "at": now}
            measured += 1
    _save(cache, {"sizes": sizes})
    res = {o: {"trees": 0, "bytes": 0, "sized": 0} for o in OWNERS}
    for t in trees:
        r = res[owner_of(t["path"], t["branch"])]
        r["trees"] += 1
        if t["path"] in sizes:
            r["bytes"] += int(sizes[t["path"]]["bytes"])
            r["sized"] += 1
    res["_meta"] = {"measured_now": measured, "stale_remaining": max(0, len(stale) - measured),
                   "budget_exhausted": exhausted or remaining() <= 0}
    return res


def render_lines(res: dict) -> list[str]:
    L = ["**Worktree footprint per owner** (git worktree count; GiB from a rotating size cache, a few trees per tick, "
         "never a full recursive du): "]
    parts = []
    for o in OWNERS:
        r = res[o]
        gib = f"{r['bytes'] / 2**30:.1f} GiB" + ("" if r["sized"] == r["trees"] else f" ({r['sized']}/{r['trees']} sized)")
        parts.append(f"{o} **{r['trees']}** trees, {gib}")
    m = res.get("_meta", {})
    L[0] += "; ".join(parts) + f". Size refresh pending for {m.get('stale_remaining', 0)} trees."
    return L


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cache", default=CACHE_DEFAULT)
    ap.add_argument("--max-du", type=int, default=MAX_DU_PER_CALL)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    res = collect(cache=a.cache, max_du=a.max_du)
    print(json.dumps(res, indent=2) if a.json else "\n".join(render_lines(res)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
