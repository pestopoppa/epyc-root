#!/usr/bin/env python3
"""kernel_store_gc.py — evict stale build dirs from the kernel store (<store>/builds/).

Dry-run unless --apply. Zero-token; meant for the periodic disk janitor. Fail-closed: any
check that cannot be completed keeps the build (KEEP-UNVERIFIABLE). The ONLY deletion path is
scripts/safety/guarded_rm.sh (trash-first move); this file never deletes anything itself.

Keep rules (first match wins): KEEP-PRODUCTION, KEEP-MARKED, KEEP-LINEAGE, KEEP-REFERENCED,
KEEP-BUSY, KEEP-RECENT. Everything else is REAP (at most --max per pass).
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
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import worktree_gate as wg  # noqa: E402

REPO = os.path.dirname(os.path.dirname(HERE))
GUARDED_RM = os.path.join(REPO, "scripts", "safety", "guarded_rm.sh")
DEFAULT_STORE = "/mnt/raid0/llm/kernels"
DEFAULT_SUFFIXES = ["-c7r", "-c7", "-champion"]
LINEAGE_COMMITS = ["ffc1bac82", "0db32c06e",   # production v10, v9 rollback anchor
                   "b30737922", "2c1b5182e"]  # production-speech-v1 (whisper STT, qwentts TTS)
DEFAULT_REFS = [
    "/workspace/handoffs/active/*.md",
    "/workspace/docs/reference/kernel-manifests/*.md",
    "/mnt/raid0/llm/tmp/compute-flags/ready/**/*.json",
    "/mnt/raid0/llm/tmp/compute-flags/armed/*.json",
    "/mnt/raid0/llm/tmp/compute-flags/FILLERS.md",
    "/mnt/raid0/llm/tmp/compute-flags/backlog*.json",
    "/mnt/raid0/llm/autokernel/loop-memory/champion*.json",
    "/mnt/raid0/llm/autokernel/*.json",
]
DEFAULT_COMMIT_REFS = [
    "/workspace/handoffs/active/kernel-champion-and-promotion.md",
    "/workspace/handoffs/active/autokernel-loop.md",
]
REF_CAP = 4 * 1024 * 1024
WALK_CAP = 200_000
HEX_RE = re.compile(r"(?:^|-)([0-9a-f]{9})(?:-|$)")
TOKEN_SPLIT = re.compile(r"[^A-Za-z0-9._-]+")


def _under(path: str, root: str) -> bool:
    return path == root or path.startswith(root + "/")


def protected_targets(store: str) -> set[str]:
    """Realpaths of every symlink target under production/archive/candidates."""
    out: set[str] = set()
    for sub in ("production", "archive", "candidates"):
        top = os.path.join(store, sub)
        for dp, dns, fns in os.walk(top, followlinks=False):
            for n in dns + fns:
                p = os.path.join(dp, n)
                if os.path.islink(p):
                    out.add(os.path.realpath(p))
    return out


def read_refs(globs: list[str]) -> tuple[set[str], list[str]]:
    """Token set over all reference files; second value lists unreadable files."""
    tokens: set[str] = set()
    bad: list[str] = []
    for g in globs:
        for f in glob.glob(g, recursive=True):
            if not os.path.isfile(f):
                continue
            try:
                with open(f, "rb") as fh:
                    text = fh.read(REF_CAP).decode("utf-8", "replace")
            except OSError:
                bad.append(f)
                continue
            tokens.update(t.strip("._-") for t in TOKEN_SPLIT.split(text))
            tokens.update(TOKEN_SPLIT.split(text))
    return tokens, bad


def read_commit_text(files: list[str]) -> tuple[str, list[str]]:
    buf, bad = [], []
    for f in files:
        if not os.path.exists(f):
            continue
        try:
            with open(f, "rb") as fh:
                buf.append(fh.read(REF_CAP).decode("utf-8", "replace"))
        except OSError:
            bad.append(f)
    return "\n".join(buf), bad


def proc_open_paths(proc_root: str = "/proc") -> tuple[set[str], bool]:
    """Paths from /proc/*/fd and /proc/*/maps. Returns (paths, complete)."""
    paths: set[str] = set()
    try:
        pids = [p for p in os.listdir(proc_root) if p.isdigit()]
    except OSError:
        return paths, False
    seen_any = False
    for pid in pids:
        fd_dir = f"{proc_root}/{pid}/fd"
        try:
            for fd in os.listdir(fd_dir):
                try:
                    paths.add(os.readlink(f"{fd_dir}/{fd}"))
                    seen_any = True
                except OSError:
                    pass
        except OSError:
            pass
        try:
            with open(f"{proc_root}/{pid}/maps", "r", errors="replace") as fh:
                for line in fh:
                    parts = line.split(None, 5)
                    if len(parts) == 6 and parts[5].startswith("/"):
                        paths.add(parts[5].strip().removesuffix(" (deleted)"))
                        seen_any = True
        except OSError:
            pass
    return paths, (seen_any or not pids)


def newest_mtime(path: str) -> tuple[float, int, bool]:
    """(newest lstat mtime, bytes, complete) over the tree, capped at WALK_CAP entries."""
    newest, total, n = os.lstat(path).st_mtime, 0, 0
    stack = [path]
    while stack:
        d = stack.pop()
        try:
            it = os.scandir(d)
        except OSError:
            return newest, total, False
        with it:
            for e in it:
                n += 1
                if n > WALK_CAP:
                    return newest, total, False
                try:
                    st = e.stat(follow_symlinks=False)
                except OSError:
                    return newest, total, False
                newest = max(newest, st.st_mtime)
                if e.is_dir(follow_symlinks=False):
                    stack.append(e.path)
                else:
                    total += st.st_size
    return newest, total, True


def classify(name, path, *, targets, suffixes, ref_tokens, refs_bad, commit_text, probe,
             open_paths, open_ok, min_age_s, now):
    real = os.path.realpath(path)
    for t in targets:
        if _under(t, real):
            return "KEEP-PRODUCTION", f"symlink target {t}"
    for m in wg.KEEP_MARKERS:
        if os.path.exists(os.path.join(path, m)):
            return "KEEP-MARKED", f"marker {m}"
    for s in suffixes:
        if name.endswith(s):
            return "KEEP-LINEAGE", f"suffix {s}"
    for c in LINEAGE_COMMITS:
        if c in name:
            return "KEEP-LINEAGE", f"lineage commit {c}"
    if refs_bad:
        return "KEEP-UNVERIFIABLE", f"unreadable reference file {refs_bad[0]}"
    if name in ref_tokens:
        return "KEEP-REFERENCED", "name appears in a reference file"
    m = HEX_RE.search(name)
    if m and m.group(1) in commit_text:
        return "KEEP-REFERENCED", f"commit {m.group(1)} named in champion handoff"
    # Same visibility rule as worktree_gate.remove_one / scratch_cleanup / the keeper's reaper: processes we can
    # see count; other uids' unreadable /proc entries (always present on this shared host) do not fail the pass.
    # Only a BLIND walk (no /proc, nothing readable at all) fails closed.
    if probe is None or not open_ok:
        return "KEEP-UNVERIFIABLE", "process walk blind"
    hit = probe.busy(path)
    if hit:
        return "KEEP-BUSY", hit
    for p in open_paths:
        if _under(p, real) or _under(p, path):
            return "KEEP-BUSY", f"open fd/map {p}"
    newest, _, ok = newest_mtime(path)
    if not ok:
        return "KEEP-UNVERIFIABLE", "mtime walk incomplete or capped"
    age_d = (now - newest) / 86400
    if now - newest < min_age_s:
        return "KEEP-RECENT", f"newest mtime {age_d:.1f}d old"
    return "REAP", f"newest mtime {age_d:.1f}d old, unreferenced"


def main(argv=None, *, probe_fn=None, proc_fn=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--store", default=DEFAULT_STORE)
    ap.add_argument("--min-age-days", type=float, default=7)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--max", type=int, default=10)
    ap.add_argument("--log")
    ap.add_argument("--refs-glob", nargs="+", action="extend")
    ap.add_argument("--commit-refs", nargs="+", action="extend")
    ap.add_argument("--protect-suffix", nargs="+", action="extend")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    tag = "KERNEL-GC" if a.apply else "KERNEL-GC-DRYRUN"
    builds_dir = os.path.join(a.store, "builds")
    targets = protected_targets(a.store)
    suffixes = DEFAULT_SUFFIXES + (a.protect_suffix or [])
    ref_tokens, refs_bad = read_refs(a.refs_glob or DEFAULT_REFS)
    commit_text, cbad = read_commit_text(a.commit_refs or DEFAULT_COMMIT_REFS)
    refs_bad += cbad
    try:
        probe = (probe_fn or wg.gather_probe)()
    except Exception:
        probe = None
    open_paths, open_ok = (proc_fn or proc_open_paths)()
    now = time.time()

    lines, records = [], []
    keep = reap = bytes_reap = 0
    names = sorted(n for n in os.listdir(builds_dir)
                   if os.path.isdir(os.path.join(builds_dir, n))
                   and not os.path.islink(os.path.join(builds_dir, n)))
    for name in names:
        path = os.path.join(builds_dir, name)
        verdict, reason = classify(
            name, path, targets=targets, suffixes=suffixes, ref_tokens=ref_tokens,
            refs_bad=refs_bad, commit_text=commit_text, probe=probe, open_paths=open_paths,
            open_ok=open_ok, min_age_s=a.min_age_days * 86400, now=now)
        _, size, _ = newest_mtime(path)
        result = "kept"
        if verdict == "REAP":
            if reap >= a.max:
                verdict, reason, result = "KEEP-MAXCAP", f"--max {a.max} reached", "kept"
            elif a.apply:
                r = subprocess.run(["bash", GUARDED_RM, path], capture_output=True, text=True)
                result = "trashed" if r.returncode == 0 else f"failed rc={r.returncode}"
                if r.returncode == 0:
                    reap += 1
                    bytes_reap += size
            else:
                result = "would-trash"
                reap += 1
                bytes_reap += size
        if verdict != "REAP":
            keep += 1
        records.append(dict(build=name, bytes=size, verdict=verdict, reason=reason, result=result))
        lines.append(f"{tag} build={name} bytes={size} verdict={verdict} "
                     f"reason={reason!r} result={result!r}")
    free_gib = shutil.disk_usage(builds_dir).free / 2**30
    summary = (f"{tag} SUMMARY builds={len(names)} keep={keep} reap={reap} "
               f"bytes_reap={bytes_reap} free_gib={free_gib:.1f}")
    lines.append(summary)
    if a.json:
        print(json.dumps({"builds": records, "summary": summary}, indent=1))
    else:
        print("\n".join(lines))
    if a.log:
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        with open(a.log, "a") as fh:
            fh.writelines(f"{stamp} {ln}\n" for ln in lines)
    return 0


if __name__ == "__main__":
    sys.exit(main())
