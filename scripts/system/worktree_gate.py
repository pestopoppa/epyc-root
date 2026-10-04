#!/usr/bin/env python3
"""worktree_gate.py — the removal gate for throwaway git worktrees.

WHY. The disk audit of 2026-10-03 (/mnt/raid0/llm/tmp/disk-audit-20261003/) found ~26 new
worktrees a day and almost none removed: 265 in ten days, 215 of them landed, clean and idle for
more than 7 days, 233 GiB. Every workflow that creates a worktree (subagent lanes, promotion
checkouts, acceptance trees, build trees) prescribed `git worktree add` and nothing prescribed the
removal, so removal depended on memory. This file is the removal half, in one place, with the
checks that make removal safe:

    python3 scripts/system/worktree_gate.py check  <path>...   # read-only verdict
    python3 scripts/system/worktree_gate.py remove <path>...   # remove iff the verdict is REMOVABLE
    python3 scripts/system/worktree_gate.py report [--json] [--out FILE] [--sizes] [--min-idle-days 7]
    python3 scripts/system/worktree_gate.py remove --from-report FILE --confirm TOKEN

A worktree is REMOVABLE only when ALL of these hold:
  * it is a registered LINKED worktree of a known repo (never a main clone, never a view);
  * it is not protected: not locked, not a roster lane (worktrees/mains/*), not a worker-pool lane
    (worktrees/pool/*), not a read-only view, not a canonical root;
  * it is CLEAN: `git status --porcelain` (untracked included) prints nothing;
  * it is LANDED: `git cherry <base> HEAD` has no `+` line (patch-id equivalence, so a squash or a
    rebase that kept the patch counts as landed, and a merge commit is not mistaken for content);
  * it is not declared load-bearing. The PREFERRED declaration is git's own lock, which dirties
    nothing and which `git worktree remove` itself honours:
        git -C <repo> worktree lock --reason "load-bearing: <who uses it>" <path>
    Also honoured: a marker file `.epyc-keep`/`.epyc-load-bearing`/`KEEP`/`LOAD-BEARING` at the
    tree's top level (note: an untracked marker makes the tree dirty, and some loops refuse a dirty
    tree), or `epyc-keep` inside the worktree's git admin dir (`git rev-parse --git-dir`);
  * no process visible to us has its cwd inside it, or names it in its argv or ENVIRONMENT
    (`/proc/*/environ`: a launcher that exports `EPYC_ROOT_REPO=<tree>` holds no cwd there);
  * no live launch/state file names it: shell scripts under /mnt/raid0/llm/tmp modified in the
    last 30 days, AutoKernel campaign inputs and top-level state files, the launch manifest, the
    bus roster, the observer registry, the latest crontab backup (REFERENCE_SOURCES below);
  * its ignored files hold no evidence-shaped file (VERDICT*.json, *receipt*.json(l), attestations,
    ratifications, SHA256SUMS) — those are archived first, never deleted with a tree;
  * it has been idle for at least --min-idle-days (default 0 for an explicit `remove <path>`: you
    are removing your own tree at your own boundary; 7 for `report` and `--from-report`).

Removal is `git -C <owning repo> worktree remove <path>` — never `--force`, never
`git worktree prune`, never `git gc` (this repo is reachable at two path depths and prune deletes
live registrations; WORKTREE_MIGRATION.md "NEVER git worktree prune"). The branch ref is left in
place: refs are cheap, and a branch is the last pointer to anything the checks misjudged.

`report` is read-only (no fetch). `remove` fetches the base first (--no-fetch to skip), so the
landed check sees the promotion that just happened. `--from-report` acts only on the REMOVABLE rows
of a report the operator reviewed, and only with the token that report printed — a list nobody
looked at is never removed in bulk. Every row is re-checked immediately before its removal.

Exit codes: 0 every requested path removed / check verdict REMOVABLE / report written;
            1 at least one path refused (verdict printed); 2 usage error.

Origin of the reference checks (2026-10-04): the approved cleanup removed
`worktrees/root-main-epyc-root-repo` — landed, clean, idle >7 d, it passed every git check — but
DS41's launch scripts in /mnt/raid0/llm/tmp/ds41-scope-20260926/*.sh exported
`EPYC_ROOT_REPO` to it, and the next batch's claim failed until it was restored. Git state says
whether a tree's CONTENT is safe to drop; only a reference scan says whether its PATH is in use.

Tests: tests/test_worktree_gate.py (temp repos only).
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

SCHEMA = "epyc.worktree_gate.report.v1"
LLM = "/mnt/raid0/llm"
DEFAULT_REPOS = [
    f"{LLM}/epyc-root",
    f"{LLM}/epyc-orchestrator",
    f"{LLM}/epyc-inference-research",
    f"{LLM}/llama.cpp",
]
DEFAULT_BASE = "origin/main"
PROTECTED_PARENT_DIRS = ("worktrees/mains", "worktrees/pool")
VIEW_MARKER = ".epyc-view-readonly"
# Same narrow pattern as autokernel_disk_sweep.EVIDENCE_RE (kept in sync by a test).
EVIDENCE_RE = re.compile(
    r"(?i)(^verdict[^/]*\.json$|^SHA256SUMS$|receipt[^/]*\.jsonl?$|(^|[._-])sealed([._-]|$)|"
    r"attestation[^/]*\.json$|^ratif[^/]*\.json$)"
)
EVIDENCE_SKIP_DIRS = {
    "node_modules", "__pycache__", ".pytest_cache", ".ruff_cache", ".gitnexus", "CMakeFiles",
    ".mypy_cache", ".venv", "venv", ".git",
}
EVIDENCE_WALK_CAP = 200_000
KEEP_MARKERS = (".epyc-keep", ".epyc-load-bearing", "KEEP", "LOAD-BEARING")
# Live reference sources: (glob root, filename suffixes or None=any, maxdepth, max age days or None).
REFERENCE_SOURCES = [
    (f"{LLM}/tmp", (".sh", ".env", ".bash"), 4, 30),
    (f"{LLM}/autokernel/campaigns/*/inputs", None, 4, None),
    (f"{LLM}/autokernel/campaigns/*", (".json", ".yaml", ".yml", ".sh", ".env", ".toml"), 1, None),
    (f"{LLM}/autokernel", (".json", ".yaml", ".yml", ".sh", ".env"), 1, None),
]
REFERENCE_FILES = [
    f"{LLM}/epyc-orchestrator/orchestration/launch_manifest.yaml",
    f"{LLM}/epyc-root/coordination/session-bus/config.yaml",
    f"{LLM}/epyc-root/scripts/coordination/observer_registry.json",
]
REFERENCE_GLOB_FILES = [f"{LLM}/epyc-root/logs/crontab.bak-*"]
REFERENCE_MAX_FILE_BYTES = 2 * 2**20

REMOVABLE = "REMOVABLE"
VERDICTS = (
    "MISSING",        # registered but the directory is gone (never pruned here; reported)
    "PROTECTED",      # locked / roster lane / pool lane / view / canonical root
    "BUSY",           # a visible process has its cwd inside, or names it in argv/environ
    "REFERENCED",     # a live launch/state file names its path
    "DIRTY",          # modified or untracked files
    "UNLANDED",       # git cherry shows patches not in base
    "EVIDENCE",       # ignored evidence-shaped files present
    "UNVERIFIABLE",   # a check could not run (git error, walk cap hit, unknown repo)
    "RECENT",         # idle less than --min-idle-days
    REMOVABLE,
)


def _git(args: list[str], cwd: str, timeout: int = 60) -> subprocess.CompletedProcess:
    env = dict(os.environ, GIT_OPTIONAL_LOCKS="0", LC_ALL="C")
    return subprocess.run(["git", *args], cwd=cwd, env=env, capture_output=True, text=True,
                          timeout=timeout)


@dataclass
class Worktree:
    path: str
    repo: str
    head: str = ""
    branch: str = ""
    locked: bool = False
    verdict: str = "UNVERIFIABLE"
    reasons: list[str] = field(default_factory=list)
    unlanded: int | None = None
    idle_days: float | None = None
    size_bytes: int | None = None


def list_worktrees(repo: str) -> list[Worktree]:
    """Linked worktrees of `repo` (the main worktree is skipped)."""
    cp = _git(["worktree", "list", "--porcelain"], cwd=repo)
    if cp.returncode != 0:
        raise RuntimeError(f"git worktree list failed in {repo}: {cp.stderr.strip()}")
    out: list[Worktree] = []
    cur: Worktree | None = None
    first = True
    for line in cp.stdout.splitlines() + [""]:
        if not line:
            if cur is not None:
                if not first:
                    out.append(cur)
                first = False
            cur = None
            continue
        key, _, val = line.partition(" ")
        if key == "worktree":
            cur = Worktree(path=val, repo=repo)
        elif cur is None:
            continue
        elif key == "HEAD":
            cur.head = val
        elif key == "branch":
            cur.branch = val.removeprefix("refs/heads/")
        elif key == "locked":
            cur.locked = True
    return out


def _ancestry(proc_root: str = "/proc") -> set[str]:
    """This process and its ancestors: the caller asking to remove a tree may be standing in it."""
    out: set[str] = set()
    pid = str(os.getpid())
    while pid and pid not in out and pid != "0":
        out.add(pid)
        try:
            stat = Path(f"{proc_root}/{pid}/stat").read_text()
            pid = stat.rsplit(")", 1)[1].split()[1]
        except (OSError, IndexError):
            break
    return out


PATH_TOKEN_RE = re.compile(r"(?:/mnt/raid0/llm|/workspace|/tmp)/[^\s:;,=\"'()\[\]{}<>|&`$\x00]+")


@dataclass
class Probe:
    """Every PATH a live process or a live launch/state file names, gathered once (read-only).

    Indexed inverted: each referenced path and its ancestors map to the sources that name them, so
    asking "is this tree named anywhere?" is one dict lookup instead of a regex per tree per file.
    """
    cwds: dict[str, str] = field(default_factory=dict)            # realpath cwd -> pid
    refs: dict[str, list[str]] = field(default_factory=dict)      # path prefix -> sources
    proc_refs: dict[str, list[str]] = field(default_factory=dict)  # same, from argv/environ
    ref_files_scanned: int = 0
    complete: bool = True

    @staticmethod
    def _index(index: dict[str, list[str]], text: str, source: str) -> None:
        for m in PATH_TOKEN_RE.finditer(text):
            path = m.group(0).rstrip("/.")
            parts = path.split("/")
            for i in range(len(parts), 3, -1):          # the path and its ancestors, >= /a/b/c
                pref = "/".join(parts[:i])
                srcs = index.setdefault(pref, [])
                if source in srcs:
                    break                                 # ancestors already indexed for source
                if len(srcs) < 8:
                    srcs.append(source)

    def add_text(self, text: str, source: str, proc: bool = False) -> None:
        self._index(self.proc_refs if proc else self.refs, text, source)

    @staticmethod
    def _lookup(index: dict[str, list[str]], wt_path: str) -> str | None:
        real = os.path.realpath(wt_path)
        for key in {wt_path.rstrip("/"), real.rstrip("/")}:
            for src in index.get(key, []):
                # a file INSIDE the tree naming the tree goes away with it; it is not a user
                if src.startswith(key + "/") or src.startswith(real + "/"):
                    continue
                return src
        return None

    def busy(self, wt_path: str) -> str | None:
        real = os.path.realpath(wt_path)
        for c, pid in self.cwds.items():
            if c == real or c.startswith(real + "/"):
                return f"pid {pid} has cwd {c}"
        src = self._lookup(self.proc_refs, wt_path)
        return f"{src} names it in argv/environ" if src else None

    def referenced(self, wt_path: str) -> str | None:
        src = self._lookup(self.refs, wt_path)
        return f"named by {src}" if src else None


def _iter_reference_files(sources=None, files=None, glob_files=None):
    import glob as _glob
    now = time.time()
    for root_glob, suffixes, maxdepth, max_age_days in (sources if sources is not None else REFERENCE_SOURCES):
        for root in _glob.glob(root_glob):
            if not os.path.isdir(root):
                continue
            base = root.rstrip("/").count("/")
            for dirpath, dirnames, filenames in os.walk(root):
                if dirpath.count("/") - base >= maxdepth - 1:
                    dirnames[:] = []
                dirnames[:] = [d for d in dirnames if d not in EVIDENCE_SKIP_DIRS]
                for fn in filenames:
                    if suffixes and not fn.endswith(suffixes):
                        continue
                    p = os.path.join(dirpath, fn)
                    try:
                        st = os.stat(p)
                    except OSError:
                        continue
                    if st.st_size > REFERENCE_MAX_FILE_BYTES:
                        continue
                    if max_age_days is not None and now - st.st_mtime > max_age_days * 86400:
                        continue
                    yield p
    for p in (files if files is not None else REFERENCE_FILES):
        if os.path.isfile(p):
            yield p
    for g in (glob_files if glob_files is not None else REFERENCE_GLOB_FILES):
        hits = sorted(_glob.glob(g), key=lambda x: os.path.getmtime(x) if os.path.exists(x) else 0)
        if hits:
            yield hits[-1]


def gather_probe(proc_root: str = "/proc", *, sources=None, files=None, glob_files=None) -> Probe:
    pr = Probe()
    try:
        pids = [p for p in os.listdir(proc_root) if p.isdigit()]
    except OSError:
        pr.complete = False
        pids = []
    skip = _ancestry(proc_root)
    for pid in pids:
        if pid in skip:
            continue
        try:
            pr.cwds[os.path.realpath(os.readlink(f"{proc_root}/{pid}/cwd"))] = pid
        except FileNotFoundError:
            continue
        except OSError:
            pr.complete = False
        chunks = []
        for leaf in ("cmdline", "environ"):
            try:
                chunks.append(Path(f"{proc_root}/{pid}/{leaf}").read_bytes().decode(errors="replace"))
            except FileNotFoundError:
                break
            except OSError:
                pr.complete = False
        if chunks:
            pr.add_text("\x00".join(chunks), f"pid {pid}", proc=True)
    for p in _iter_reference_files(sources, files, glob_files):
        try:
            pr.add_text(Path(p).read_text(errors="replace"), p)
            pr.ref_files_scanned += 1
        except OSError:
            continue
    return pr


def _gitdir(wt_path: str) -> Path | None:
    try:
        txt = (Path(wt_path) / ".git").read_text().strip()
    except OSError:
        return None
    if not txt.startswith("gitdir:"):
        return None
    gd = Path(txt.split(":", 1)[1].strip())
    return gd if gd.is_absolute() else (Path(wt_path) / gd).resolve()


def _idle_days(wt: Worktree, now: float) -> float | None:
    """Days since the newest of: the tree dir, its HEAD reflog, its index (cheap — no tree walk)."""
    cands = [Path(wt.path)]
    gitfile = Path(wt.path) / ".git"
    try:
        txt = gitfile.read_text().strip()
        if txt.startswith("gitdir:"):
            gd = Path(txt.split(":", 1)[1].strip())
            if not gd.is_absolute():
                gd = (Path(wt.path) / gd).resolve()
            cands += [gd / "HEAD", gd / "index", gd / "logs" / "HEAD"]
    except OSError:
        pass
    mt = []
    for c in cands:
        try:
            mt.append(c.stat().st_mtime)
        except OSError:
            continue
    if not mt:
        return None
    return round((now - max(mt)) / 86400.0, 2)


def _evidence_in_ignored(path: str) -> tuple[list[str], bool]:
    """(evidence-shaped ignored files, walk completed?)"""
    cp = _git(["ls-files", "--others", "--ignored", "--exclude-standard", "--directory"], cwd=path,
              timeout=120)
    if cp.returncode != 0:
        return [], False
    hits: list[str] = []
    seen = 0
    for rel in cp.stdout.splitlines():
        rel = rel.rstrip("/")
        top = os.path.join(path, rel)
        if os.path.basename(rel) in EVIDENCE_SKIP_DIRS:
            continue
        if os.path.isfile(top) or os.path.islink(top):
            seen += 1
            if EVIDENCE_RE.search(os.path.basename(rel)):
                hits.append(rel)
            continue
        for dirpath, dirnames, filenames in os.walk(top):
            dirnames[:] = [d for d in dirnames if d not in EVIDENCE_SKIP_DIRS
                           and not d.startswith("build")]
            for fn in filenames:
                seen += 1
                if seen > EVIDENCE_WALK_CAP:
                    return hits, False
                if EVIDENCE_RE.search(fn):
                    hits.append(os.path.relpath(os.path.join(dirpath, fn), path))
    return hits, True


def _protected_reason(wt: Worktree, canonical_roots: list[str]) -> str | None:
    if wt.locked:
        return "locked worktree"
    real = os.path.realpath(wt.path)
    parent_dir = os.path.dirname(real.rstrip("/"))
    for parent in PROTECTED_PARENT_DIRS:
        if parent_dir.endswith("/" + parent):
            return f"roster/pool lane under {parent}/"
    if os.path.exists(os.path.join(wt.path, VIEW_MARKER)):
        return "read-only view"
    for m in KEEP_MARKERS:
        if os.path.exists(os.path.join(wt.path, m)):
            return f"keep marker {m}"
    gd = _gitdir(wt.path)
    if gd is not None and (gd / "epyc-keep").exists():
        return f"keep marker {gd / 'epyc-keep'}"
    for r in canonical_roots:
        if real == os.path.realpath(r):
            return "canonical root"
    return None


def _du_bytes(path: str) -> int | None:
    try:
        cp = subprocess.run(["du", "-sx", "--block-size=1", path], capture_output=True, text=True,
                            timeout=1800)
        return int(cp.stdout.split()[0]) if cp.stdout else None
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None


def classify(wt: Worktree, *, base: str, min_idle_days: float, probe: Probe,
             canonical_roots: list[str], now: float, sizes: bool = False) -> Worktree:
    wt.reasons = []
    if not os.path.isdir(wt.path):
        wt.verdict, wt.reasons = "MISSING", ["directory does not exist (registration only)"]
        return wt
    wt.idle_days = _idle_days(wt, now)
    if sizes:
        wt.size_bytes = _du_bytes(wt.path)
    pr = _protected_reason(wt, canonical_roots)
    if pr:
        wt.verdict, wt.reasons = "PROTECTED", [pr]
        return wt
    busy = probe.busy(wt.path)
    if busy:
        wt.verdict, wt.reasons = "BUSY", [busy]
        return wt
    ref = probe.referenced(wt.path)
    if ref:
        wt.verdict, wt.reasons = "REFERENCED", [ref]
        return wt
    try:
        st = _git(["status", "--porcelain", "--untracked-files=normal"], cwd=wt.path, timeout=300)
        if st.returncode != 0:
            wt.verdict, wt.reasons = "UNVERIFIABLE", [f"git status failed: {st.stderr.strip()[:200]}"]
            return wt
        if st.stdout.strip():
            n = len(st.stdout.splitlines())
            wt.verdict, wt.reasons = "DIRTY", [f"{n} modified/untracked path(s)"]
            return wt
        ch = _git(["cherry", base, "HEAD"], cwd=wt.path, timeout=300)
        if ch.returncode != 0:
            wt.verdict, wt.reasons = "UNVERIFIABLE", [f"git cherry {base} failed: {ch.stderr.strip()[:200]}"]
            return wt
        plus = [ln for ln in ch.stdout.splitlines() if ln.startswith("+")]
        wt.unlanded = len(plus)
        if plus:
            wt.verdict, wt.reasons = "UNLANDED", [f"{len(plus)} patch(es) not in {base}"]
            return wt
        ev, complete = _evidence_in_ignored(wt.path)
        if ev:
            wt.verdict, wt.reasons = "EVIDENCE", [f"ignored evidence file(s): {', '.join(ev[:5])}"]
            return wt
        if not complete:
            wt.verdict, wt.reasons = "UNVERIFIABLE", ["ignored-file evidence walk incomplete (cap or git error)"]
            return wt
    except subprocess.TimeoutExpired as exc:
        wt.verdict, wt.reasons = "UNVERIFIABLE", [f"timeout: {exc.cmd}"]
        return wt
    if wt.idle_days is None or wt.idle_days < min_idle_days:
        wt.verdict, wt.reasons = "RECENT", [f"idle {wt.idle_days} d < {min_idle_days} d"]
        return wt
    wt.verdict, wt.reasons = REMOVABLE, [f"clean, landed in {base}, idle {wt.idle_days} d"]
    return wt


def _owning_repo(path: str) -> str | None:
    cp = _git(["rev-parse", "--path-format=absolute", "--git-common-dir"], cwd=path)
    if cp.returncode != 0:
        return None
    common = Path(cp.stdout.strip())
    return str(common.parent) if common.name == ".git" else None


def _find(path: str) -> Worktree | None:
    repo = _owning_repo(path) if os.path.isdir(path) else None
    if repo is None:
        return None
    real = os.path.realpath(path)
    for wt in list_worktrees(repo):
        if os.path.realpath(wt.path) == real:
            return wt
    return None


def report_token(rows: list[dict]) -> str:
    payload = "\n".join(sorted(r["path"] for r in rows if r["verdict"] == REMOVABLE))
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def build_report(repos: list[str], *, base: str, min_idle_days: float, sizes: bool,
                 proc_root: str = "/proc", canonical_roots: list[str] | None = None,
                 probe: Probe | None = None, should_continue=None) -> dict:
    """`should_continue()` is called before each worktree; it may raise to abort the scan."""
    now = time.time()
    probe = probe if probe is not None else gather_probe(proc_root)
    complete = probe.complete
    canon = canonical_roots if canonical_roots is not None else ["/workspace", f"{LLM}/epyc-root"]
    rows: list[dict] = []
    errors: list[str] = []
    seen: set[str] = set()
    for repo in repos:
        if not os.path.isdir(repo):
            errors.append(f"repo not found: {repo}")
            continue
        try:
            wts = list_worktrees(repo)
        except (RuntimeError, subprocess.TimeoutExpired) as exc:
            errors.append(str(exc))
            continue
        for wt in wts:
            key = os.path.realpath(wt.path)
            if key in seen:
                continue
            seen.add(key)
            if should_continue is not None:
                should_continue()
            classify(wt, base=base, min_idle_days=min_idle_days, probe=probe,
                     canonical_roots=canon, now=now, sizes=sizes)
            d = asdict(wt)
            d["repo"] = os.path.basename(repo.rstrip("/"))
            rows.append(d)
    by_verdict: dict[str, dict] = {}
    for r in rows:
        b = by_verdict.setdefault(r["verdict"], {"count": 0, "size_bytes": 0})
        b["count"] += 1
        b["size_bytes"] += r["size_bytes"] or 0
    total = sum(r["size_bytes"] or 0 for r in rows)
    return {
        "schema": SCHEMA,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "base": base,
        "min_idle_days": min_idle_days,
        "sizes_measured": sizes,
        "proc_probe": "complete" if complete else "partial",
        "reference_files_scanned": probe.ref_files_scanned,
        "repos": repos,
        "errors": errors,
        "totals": {"count": len(rows), "size_bytes": total if sizes else None,
                   "by_verdict": by_verdict},
        "removable_token": report_token(rows),
        "worktrees": sorted(rows, key=lambda r: (r["verdict"] != REMOVABLE, -(r["size_bytes"] or 0))),
    }


def remove_one(path: str, *, base: str, min_idle_days: float, fetch: bool,
               probe: Probe | None = None) -> tuple[bool, str]:
    wt = _find(path)
    if wt is None:
        return False, f"REFUSED {path}: not a registered linked worktree of a git repo"
    if fetch:
        remote = base.split("/", 1)[0] if "/" in base else "origin"
        _git(["fetch", "--quiet", remote], cwd=wt.repo, timeout=300)
    classify(wt, base=base, min_idle_days=min_idle_days, probe=probe or gather_probe(),
             canonical_roots=["/workspace", f"{LLM}/epyc-root"], now=time.time())
    if wt.verdict != REMOVABLE:
        return False, f"REFUSED {path}: {wt.verdict} — {'; '.join(wt.reasons)}"
    cp = _git(["worktree", "remove", wt.path], cwd=wt.repo, timeout=1800)   # never --force
    if cp.returncode != 0:
        return False, f"REFUSED {path}: git worktree remove failed: {cp.stderr.strip()[:300]}"
    return True, f"REMOVED {path} (branch {wt.branch or '(detached)'} kept; {wt.reasons[0]})"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", default=DEFAULT_BASE, help="ref a branch must have landed in")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check", help="read-only verdict for each path")
    c.add_argument("paths", nargs="+")
    c.add_argument("--min-idle-days", type=float, default=0.0)
    r = sub.add_parser("remove", help="remove each path iff REMOVABLE")
    r.add_argument("paths", nargs="*")
    r.add_argument("--min-idle-days", type=float, default=None)
    r.add_argument("--no-fetch", action="store_true")
    r.add_argument("--from-report", help="act on the REMOVABLE rows of this report")
    r.add_argument("--confirm", help="the removable_token printed by that report")
    p = sub.add_parser("report", help="read-only inventory of every linked worktree")
    p.add_argument("--repo", action="append", dest="repos", help="repeatable; default: the 4 repos")
    p.add_argument("--min-idle-days", type=float, default=7.0)
    p.add_argument("--sizes", action="store_true", help="du each tree (slow; nightly only)")
    p.add_argument("--json", action="store_true")
    p.add_argument("--out", help="also write the JSON report here (atomic)")
    a = ap.parse_args(argv)

    if a.cmd == "check":
        rc = 0
        probe = gather_probe()
        for path in a.paths:
            wt = _find(path)
            if wt is None:
                print(f"{path}\tUNVERIFIABLE\tnot a registered linked worktree")
                rc = 1
                continue
            classify(wt, base=a.base, min_idle_days=a.min_idle_days, probe=probe,
                     canonical_roots=["/workspace", f"{LLM}/epyc-root"], now=time.time())
            print(f"{path}\t{wt.verdict}\t{'; '.join(wt.reasons)}")
            rc |= 0 if wt.verdict == REMOVABLE else 1
        return rc

    if a.cmd == "remove":
        paths = list(a.paths)
        min_idle = a.min_idle_days
        if a.from_report:
            rep = json.loads(Path(a.from_report).read_text())
            rows = rep.get("worktrees", [])
            if not a.confirm or a.confirm != report_token(rows):
                print(f"REFUSED: --confirm must equal the report's removable_token "
                      f"({report_token(rows)}) — review the report first", file=sys.stderr)
                return 2
            paths += [r["path"] for r in rows if r["verdict"] == REMOVABLE]
            if min_idle is None:
                min_idle = float(rep.get("min_idle_days", 7.0))
        if not paths:
            ap.error("remove needs <path>... or --from-report")
        rc = 0
        for path in paths:
            ok, msg = remove_one(path, base=a.base, min_idle_days=min_idle or 0.0,
                                 fetch=not a.no_fetch)
            print(msg)
            rc |= 0 if ok else 1
        return rc

    rep = build_report(a.repos or DEFAULT_REPOS, base=a.base, min_idle_days=a.min_idle_days,
                       sizes=a.sizes)
    text = json.dumps(rep, indent=2)
    if a.out:
        out = Path(a.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        tmp = out.with_suffix(out.suffix + f".{os.getpid()}.tmp")
        tmp.write_text(text + "\n")
        os.replace(tmp, out)
    if a.json:
        print(text)
    else:
        bv = rep["totals"]["by_verdict"]
        for v in VERDICTS:
            if v in bv:
                sz = bv[v]["size_bytes"] / 2**30 if rep["sizes_measured"] else float("nan")
                print(f"{v:<13} {bv[v]['count']:>5}  {sz:8.1f} GiB")
        print(f"removable_token={rep['removable_token']}  (pass to `remove --from-report ... --confirm`)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
