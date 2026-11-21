#!/usr/bin/env python3
"""build_ttl.py - TTL reaper for /mnt/raid0/llm/kernels/builds (deterministic, no LLM). Dry run unless --apply.

    build_ttl.py [--store DIR] [--ttl-days 7] [--apply] [--max N] [--flags DIR] [--json]

A build older than --ttl-days (newest mtime anywhere in the tree) is trashed via scripts/safety/guarded_rm.sh unless
ANY of these keeps it (first match reported):
  production/archive/candidate symlink targets (kernels/production, the v9 archive anchors) - kernel_store_gc.protected_targets
  KEEP marker; the lineage commits v10 ffc1bac82 / v9 0db32c06e / speech b30737922 / 2c1b5182e
  the CURRENT CHAMPION: build whose sha is the tip of the newest llama.cpp `ak/champion/*` branch
  the NEWEST build per lineage head (P4 ledger convention: backend + tag family, tag with -rN/-vN stripped)
  OPEN GRANT / ROW SPEC: any grants/*.grant without .ended, ready/armed/parked/held/dryrun spec or FILLERS row that names it
  PENDING: pending_refs.referenced_by_pending (handoff boxes, hold files, launchers, unfiled rows) - operator 2026-11-21
  referenced by a handoff/manifest/champion file, busy (open fd/map/cwd), unverifiable
Reuses kernel_store_gc.classify for the generic rules; this file adds champion, lineage-head, grant and pending keeps.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.append(os.path.join(REPO, "scripts", "system"))   # AFTER safety/: both dirs hold a worktree_reaper.py
import pending_refs  # noqa: E402
import kernel_store_gc as ksg  # noqa: E402
import worktree_gate as wg  # noqa: E402

GUARDED_RM = os.path.join(HERE, "guarded_rm.sh")
DEFAULT_STORE = "/mnt/raid0/llm/kernels"
LLAMA_TREE = "/mnt/raid0/llm/llama.cpp"
NAME_RE = re.compile(r"^(?P<be>[a-z]+)-(?P<date>\d{8})-(?P<sha>[0-9a-f]{9})(?:-(?P<tag>.+))?$")


def lineage_key(name):
    m = NAME_RE.match(name)
    if not m:
        return None
    tag = m.group("tag") or ""
    c = re.match(r"c\d+", tag)   # champion fold family: c8fold1 / c8h16 / c8lcattn all belong to lineage head c8
    tag = c.group(0) if c else re.sub(r"[-_](?:r|v)\d+$", "", tag)
    return (m.group("be"), tag)


def lineage_heads(builds):
    """{build name: lineage key} for the newest build (by name date, then mtime) of each (backend, tag family)."""
    best = {}
    for n, mt in builds:
        k = lineage_key(n)
        if k is None:
            continue
        rank = (NAME_RE.match(n).group("date"), mt)
        if k not in best or rank > best[k][0]:
            best[k] = (rank, n)
    return {v[1]: k for k, v in best.items()}


def champion_shas(tree=LLAMA_TREE):
    """9-char tip sha of the newest `ak/champion/*` branch (empty set when it cannot be read)."""
    try:
        r = subprocess.run(["git", "-C", tree, "for-each-ref", "--sort=-committerdate", "--count=1",
                            "--format=%(objectname:short=9)", "refs/heads/ak/champion/"],
                           capture_output=True, text=True, timeout=60)
        return {r.stdout.strip()} if r.returncode == 0 and r.stdout.strip() else set()
    except (OSError, subprocess.TimeoutExpired):
        return set()


def grant_refs(flags):
    """-> text of every OPEN grant file and FILLERS row (names a build => open work uses it)."""
    txt = []
    for g in glob.glob(os.path.join(flags, "grants", "*.grant")):
        if not os.path.exists(g[:-6] + ".ended"):
            try:
                txt.append(open(g, errors="replace").read(1 << 20))
            except OSError:
                pass
    return "\n".join(txt)


def plan(store, *, ttl_days=7.0, flags=pending_refs.DEFAULT_FLAGS, now=None, champions=None, pending=None,
         probe=None, open_paths=None, open_ok=True, refs=None, commit_refs=None):
    now = time.time() if now is None else now
    builds_dir = os.path.join(store, "builds")
    targets = ksg.protected_targets(store)
    # references are judged by pending_refs (open/held/parked work only, ticked history ignored); kernel_store_gc's own
    # reference tokens count every historical mention and so keep nearly everything - pass refs=/commit_refs= to re-enable
    ref_tokens, refs_bad = ksg.read_refs(refs if refs is not None else [])
    commit_text, cbad = ksg.read_commit_text(commit_refs if commit_refs is not None else [])
    refs_bad += cbad
    champs = champion_shas() if champions is None else champions
    names = sorted(n for n in os.listdir(builds_dir)
                   if os.path.isdir(os.path.join(builds_dir, n)) and not os.path.islink(os.path.join(builds_dir, n)))
    mts = [(n, os.lstat(os.path.join(builds_dir, n)).st_mtime) for n in names]
    heads = lineage_heads(mts)
    grants = grant_refs(flags)
    pending = pending_refs.PendingIndex(flags=flags) if pending is None else pending
    recs = []
    for name in names:
        path = os.path.join(builds_dir, name)
        m = NAME_RE.match(name)
        v, why = None, None
        if m and m.group("sha") in champs:
            v, why = "KEEP-CHAMPION", f"tip of newest ak/champion branch {m.group('sha')}"
        elif name in heads:
            v, why = "KEEP-LINEAGE-HEAD", f"newest build of lineage {heads[name]}"
        elif name in grants:
            v, why = "KEEP-OPEN-GRANT", "named by an open grant"
        else:
            pr = pending.check(path)
            if pr:
                v, why = "KEEP-PENDING", pr
        if v is None:
            v, why = ksg.classify(name, path, targets=targets, suffixes=ksg.DEFAULT_SUFFIXES, ref_tokens=ref_tokens,
                                  refs_bad=refs_bad, commit_text=commit_text, probe=probe, open_paths=open_paths or set(),
                                  open_ok=open_ok, min_age_s=ttl_days * 86400, now=now)
        newest, size, _ = ksg.newest_mtime(path)
        recs.append({"build": name, "path": path, "bytes": size, "verdict": v, "reason": why, "result": "kept"})
    return recs


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--store", default=DEFAULT_STORE)
    ap.add_argument("--ttl-days", type=float, default=7.0)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--max", type=int)
    ap.add_argument("--flags", default=pending_refs.DEFAULT_FLAGS)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    try:
        probe = wg.gather_probe()
    except Exception:  # noqa: BLE001
        probe = None
    open_paths, open_ok = ksg.proc_open_paths()
    recs = plan(a.store, ttl_days=a.ttl_days, flags=a.flags, probe=probe, open_paths=open_paths, open_ok=open_ok)
    n = freed = 0
    tag = "BUILDTTL" if a.apply else "BUILDTTL-DRYRUN"
    for r in recs:
        if r["verdict"] != "REAP":
            continue
        if a.max is not None and n >= a.max:
            r["verdict"], r["reason"] = "KEEP-MAXCAP", f"--max {a.max}"
            continue
        if a.apply:
            p = subprocess.run(["bash", GUARDED_RM, r["path"]], capture_output=True, text=True)
            r["result"] = "trashed" if p.returncode == 0 else f"FAILED rc={p.returncode}"
            if p.returncode == 0:
                n += 1
                freed += r["bytes"]
        else:
            r["result"] = "would-trash"
            n += 1
            freed += r["bytes"]
    summ = f"{tag} SUMMARY builds={len(recs)} reap={n} bytes={freed} free_gib={shutil.disk_usage(a.store).free / 2**30:.1f}"
    if a.json:
        print(json.dumps({"records": recs, "summary": summ}, indent=1))
    else:
        for r in recs:
            print(f"{tag} {r['verdict']} {r['build']} bytes={r['bytes']} :: {r['reason']} -> {r['result']}")
        print(summ)
    return 0


if __name__ == "__main__":
    sys.exit(main())
