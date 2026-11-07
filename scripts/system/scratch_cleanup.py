#!/usr/bin/env python3
"""scratch_cleanup.py — the wrap-up / `/log` scratch-cleanup step, per handoff.

THE CONVENTION (operator, 2026-10-04). Every handoff declares where its scratch lives, in one
header line next to **Status** / **Created**:

    **Scratch**: /mnt/raid0/llm/tmp/<scratch-id>/ · worktrees: /mnt/raid0/llm/worktrees/<scratch-id>-*

(or `**Scratch**: none` for work that creates no scratch). Every scratch dir, build dir, comparison
checkout and subagent worktree for that work lives under those roots, and a subagent brief names
the root it may write to. Cleanup is then a listing of the roots, not an act of memory:

    python3 scripts/system/scratch_cleanup.py plan  --handoff handoffs/active/<h>.md   # read-only
    python3 scripts/system/scratch_cleanup.py apply --handoff handoffs/active/<h>.md
    python3 scripts/system/scratch_cleanup.py plan  --root /mnt/raid0/llm/tmp/<id> \
        --worktree-glob '/mnt/raid0/llm/worktrees/<id>-*'                            # ad hoc

WHAT IS REMOVED. Each top-level entry under a declared dir, and each path a worktree glob matches:
  * a registered git worktree -> only through worktree_gate.py (clean, landed in origin/main, no
    process cwd/argv/environ names it, no live launch file names it, no ignored evidence, not
    locked/keep-marked) and only by `git worktree remove` (never --force, never prune/gc);
  * plain scratch (a dir or file that is not a worktree) -> moved to the trash with
    scripts/safety/guarded_rm.sh (trash-first rule, OPERATING_CONSTRAINTS.md "Destructive
    operations"), unless it is KEEP-marked, a visible process uses it (cwd, argv or environment),
    a live launch/state file OUTSIDE the declared roots names it, it holds an evidence-shaped file
    (VERDICT*.json, *receipt*, attestations — archive those first), or it still contains a
    worktree the gate refused.
  KEEP markers: `.epyc-keep` / `.epyc-load-bearing` / `KEEP` / `LOAD-BEARING` inside a dir, or a
  sibling `<name>.epyc-keep` file next to a plain file; for a worktree prefer
  `git -C <repo> worktree lock --reason "load-bearing: <who>" <path>`. A marker should say WHY. A
  marked declared root is one `KEEP-MARKED` entry; its descendants, marker file and any candidate
  ancestor containing it are preserved, while unrelated siblings retain their own classifications.
  An emptied declared dir is removed last (rmdir only).

References from INSIDE the declared roots do not keep a sibling: the whole root is being cleaned,
and a script there that is actually running is caught by the process probe instead. That is the
point of declaring roots — the 2026-10-04 incident (a DS41 launcher under tmp/ exported
EPYC_ROOT_REPO=<worktree>, the worktree was removed, the campaign crashed) is a reference from
OUTSIDE the worktree's root, which is still a hard keep.

Exit codes: 0 nothing refused; 1 at least one entry kept for a reason (listed); 2 usage error,
including a handoff with no or an invalid **Scratch** declaration.
Orphan sweep (`sweep --min-age-days 3 [--dry-run]`): see the ORPHAN SWEEP block below.
Tests: tests/test_scratch_cleanup.py
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import worktree_gate as wg  # noqa: E402
import scratch_lease  # noqa: E402

REPO_ROOT = HERE.parent.parent
GUARDED_RM = REPO_ROOT / "scripts" / "safety" / "guarded_rm.sh"
ALLOWED_PARENTS = ("/mnt/raid0/llm/tmp/", "/mnt/raid0/llm/worktrees/")
SCRATCH_RE = re.compile(r"^\*\*Scratch\*\*:\s*(.*)$", re.M)
PATH_RE = re.compile(r"/[^\s`;,·()\[\]|]+")
MIN_STEM = 3
EVIDENCE_WALK_CAP = 200_000


@dataclass
class Decl:
    none: bool = False
    dirs: list[str] = field(default_factory=list)
    worktree_globs: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def parse_scratch(text: str) -> Decl | None:
    """The **Scratch** declaration of a handoff body, or None when it has none."""
    m = SCRATCH_RE.search(text)
    if not m:
        return None
    value = m.group(1).strip()
    d = Decl()
    if value.strip("`").lower().startswith("none"):
        d.none = True
        return d
    for tok in PATH_RE.findall(value):
        tok = tok.rstrip(".")
        (d.worktree_globs if any(c in tok for c in "*?[") else d.dirs).append(tok.rstrip("/"))
    d.errors = validate(d)
    return d


# OPERATOR DIRECTIVE 2026-10-04 (hard rule): Claude/codex backup logs and session transcripts are NEVER
# touched by this project (they serve a more senior root-filesystem project). Defense in depth on top of
# ALLOWED_PARENTS: any path under these prefixes is refused outright, whatever a handoff declares.
# Extended 2026-10-04 to every third-party agent harness's state (operator: "what about opencode and any
# other 3rd party harness really?").
NEVER_TOUCH = ("/home/node/.codex", "/home/node/.claude", "/home/node/.local/share/claude",
               "/home/node/.local/share/opencode", "/home/node/.config/opencode", "/home/node/.hermes",
               "/mnt/raid0/llm/hermes-agent", "/mnt/raid0/llm/claude-backups", "/mnt/raid0/llm/cloud-llm-vault",
               "/mnt/raid0/llm/tmp/ds41-c95/codex-home", "/mnt/raid0/llm/tmp/ds41-c95/hermes")


def _never_touch(path: str) -> bool:
    rp = os.path.realpath(path)
    return any(rp == n or rp.startswith(n + "/") for n in NEVER_TOUCH)


def validate(d: Decl) -> list[str]:
    errs = []
    if not d.none and not d.dirs and not d.worktree_globs:
        errs.append("declares no path (write `**Scratch**: none` if the work creates no scratch)")
    for p in d.dirs + d.worktree_globs:
        parent = next((a for a in ALLOWED_PARENTS if (p + "/").startswith(a)), None)
        if parent is None:
            errs.append(f"{p}: scratch must live under {' or '.join(ALLOWED_PARENTS)}")
            continue
        stem = re.split(r"[*?\[]", p[len(parent):], maxsplit=1)[0]
        if len(stem) < MIN_STEM:
            errs.append(f"{p}: too broad — needs a task-specific name of >= {MIN_STEM} chars under {parent}")
    return errs


@dataclass
class Entry:
    path: str
    kind: str                     # worktree | dir | file
    verdict: str = ""             # REMOVE | KEEP-<reason>
    reason: str = ""
    result: str = ""


def _keep_marker(path: str) -> str | None:
    # A live sibling marker is part of its payload's custody, not disposable scratch.
    # Strip exactly one suffix; marker-of-marker chains are not a keep convention.
    suffix = ".epyc-keep"
    if os.path.isfile(path) and path.endswith(suffix):
        target = path[:-len(suffix)]
        if not target.endswith(suffix) and os.path.exists(target):
            return path
    if os.path.isdir(path) and not os.path.islink(path):
        for m in wg.KEEP_MARKERS:
            mp = os.path.join(path, m)
            if os.path.exists(mp):
                # scratch-lease Phase 1: an expired lease releases the marker; no lease = legacy keep
                return mp if scratch_lease.marker_blocks(path) else None
    side = path.rstrip("/") + ".epyc-keep"
    return side if os.path.exists(side) and scratch_lease.marker_blocks(path) else None


DEEP_MARKER_WALK_CAP = 200_000


def _deep_marker(path: str) -> str | None:
    """A KEEP marker at ANY depth inside a plain dir keeps the whole dir (operator 2026-11-07:
    "a KEEP at any level is never removed"). Returns the marker path, or the string
    "WALK-CAP" when the walk hit its cap (fail closed: the caller keeps the dir), else None.
    Top-level markers are handled by _keep_marker (lease-aware); a deeper marker is lease-aware
    for the directory that holds it."""
    if not os.path.isdir(path) or os.path.islink(path):
        return None
    seen = 0
    for dirpath, dirnames, filenames in os.walk(path):
        dirnames[:] = [d for d in dirnames if not os.path.islink(os.path.join(dirpath, d))]
        for name in list(dirnames) + filenames:
            seen += 1
            if seen > DEEP_MARKER_WALK_CAP:
                return "WALK-CAP"
            if name in wg.KEEP_MARKERS:
                if scratch_lease.marker_blocks(dirpath):
                    return os.path.join(dirpath, name)
            elif name.endswith(".epyc-keep") and name != ".epyc-keep":
                target = os.path.join(dirpath, name[:-len(".epyc-keep")])
                if os.path.exists(target) and scratch_lease.marker_blocks(target):
                    return os.path.join(dirpath, name)
    return None


def _evidence(path: str) -> tuple[list[str], bool]:
    if not os.path.isdir(path) or os.path.islink(path):
        return ([path] if wg.EVIDENCE_RE.search(os.path.basename(path)) else []), True
    hits, seen = [], 0
    for dirpath, dirnames, filenames in os.walk(path):
        dirnames[:] = [d for d in dirnames if d not in wg.EVIDENCE_SKIP_DIRS and not d.startswith("build")]
        for fn in filenames:
            seen += 1
            if seen > EVIDENCE_WALK_CAP:
                return hits, False
            if wg.EVIDENCE_RE.search(fn):
                hits.append(os.path.join(dirpath, fn))
    return hits, True


def _outside(src: str, roots: list[str]) -> bool:
    return not any(src == r or src.startswith(r.rstrip("/") + "/") for r in roots)


def _under(src: str, path: str) -> bool:
    p = path.rstrip("/")
    return src == p or src.startswith(p + "/")


def _declared_keep_roots(dirs: list[str]) -> list[tuple[str, str, str, str]]:
    """Declared directory roots and their marker paths, all resolved for safe containment checks."""
    roots = []
    for d in dirs:
        marker = _keep_marker(d) if os.path.isdir(d) else None
        if marker:
            roots.append((os.path.realpath(d), os.path.realpath(marker), marker, d))
    return roots


def _declared_keep_reason(path: str, roots: list[tuple[str, str, str, str]]) -> str | None:
    """A declared marked root protects itself, descendants, its marker, and removal ancestors."""
    real = os.path.realpath(path)
    for root, marker_real, marker, _ in roots:
        if real == marker_real or _under(real, root) or _under(root, real):
            return marker
    return None


def _registered_worktrees(repos: list[str]) -> dict[str, wg.Worktree]:
    out = {}
    for repo in repos:
        if not os.path.isdir(repo):
            continue
        try:
            for wt in wg.list_worktrees(repo):
                out[os.path.realpath(wt.path)] = wt
        except (RuntimeError, subprocess.TimeoutExpired):
            continue
    return out


def build_plan(decl: Decl, *, repos: list[str] | None = None, probe: wg.Probe | None = None,
               base: str = wg.DEFAULT_BASE) -> list[Entry]:
    """Classify every entry under the declared roots.

    References are resolved as "named by anything that SURVIVES": a source outside the declared
    roots always keeps its target; a source inside the roots keeps its target only if the entry
    holding that source is itself kept (busy, marked, referenced...), computed to a fixpoint. So
    a running watchdog keeps the launcher it calls, which keeps the worktree the launcher exports,
    while a dead script that is being removed with its siblings keeps nothing.
    """
    import time as _t
    probe = probe if probe is not None else wg.gather_probe()
    wts = _registered_worktrees(repos if repos is not None else wg.DEFAULT_REPOS)
    roots = list(decl.dirs) + [os.path.dirname(g) + "/" + os.path.basename(g).split("*")[0]
                               for g in decl.worktree_globs]
    # the gate sees only OUTSIDE references; in-root ones are resolved by the fixpoint below
    outside_probe = wg.Probe(cwds=probe.cwds, proc_refs=probe.proc_refs, complete=probe.complete,
                             refs={k: [s for s in v if _outside(s, roots)] for k, v in probe.refs.items()})
    marked_roots = _declared_keep_roots(decl.dirs)
    marked_root_paths = {root for root, _, _, _ in marked_roots}
    cands: list[str] = [path for root, _, _, path in marked_roots
                        if not any(root != parent and _under(root, parent)
                                   for parent in marked_root_paths)]
    for g in decl.worktree_globs:
        for p in sorted(glob.glob(g)):
            real = os.path.realpath(p)
            if any(_under(real, root) or real == marker_real
                   for root, marker_real, _, _ in marked_roots):
                continue
            cands.append(p)
    for d in decl.dirs:
        if not os.path.isdir(d):
            continue
        real = os.path.realpath(d)
        if any(_under(real, marked_root) for marked_root in marked_root_paths):
            continue                   # a marked declared root coalesces overlapping roots/globs
        if real in wts or os.path.exists(os.path.join(d, ".git")):
            cands.append(d)          # a checkout is ONE entry — never enumerate (trash) its files
        else:
            cands += sorted(os.path.join(d, c) for c in os.listdir(d))
    entries: list[Entry] = []
    seen: set[str] = set()
    for p in cands:
        real = os.path.realpath(p)
        if real in seen:
            continue
        seen.add(real)
        if real in wts:
            e = Entry(p, "worktree")
        else:
            e = Entry(p, "dir" if os.path.isdir(p) and not os.path.islink(p) else "file")
        marker = _declared_keep_reason(p, marked_roots)
        if marker:
            e.verdict, e.reason = "KEEP-MARKED", marker
            entries.append(e)
            continue
        if real in wts:
            wt = wts[real]
            wg.classify(wt, base=base, min_idle_days=0.0, probe=outside_probe,
                        canonical_roots=["/workspace", f"{wg.LLM}/epyc-root"], now=_t.time())
            e.verdict, e.reason = ("REMOVE", wt.reasons[0]) if wt.verdict == wg.REMOVABLE else \
                (f"KEEP-{wt.verdict}", "; ".join(wt.reasons))
            entries.append(e)
            continue
        gitp = os.path.join(p, ".git")
        if os.path.isfile(gitp):
            e.verdict, e.reason = "KEEP-UNVERIFIABLE", "a worktree of a repo outside the known set"
            entries.append(e)
            continue
        if os.path.isdir(gitp):                      # a standalone clone: keep unless nothing unpushed
            st = subprocess.run(["git", "-C", p, "status", "--porcelain"], capture_output=True, text=True)
            lo = subprocess.run(["git", "-C", p, "log", "--branches", "--not", "--remotes", "--oneline"],
                                capture_output=True, text=True)
            if st.returncode or lo.returncode or st.stdout.strip() or lo.stdout.strip():
                e.verdict, e.reason = "KEEP-UNLANDED-CLONE", "standalone clone with local changes or unpushed commits"
                entries.append(e)
                continue
        nested = [w for w in wts if w.startswith(real + "/")]
        marker = _keep_marker(p) or _deep_marker(p)
        busy = outside_probe.busy(p)
        ref = outside_probe.referenced(p)
        if marker == "WALK-CAP":
            e.verdict, e.reason = "KEEP-UNVERIFIABLE", "marker walk hit its cap"
        elif marker:
            e.verdict, e.reason = "KEEP-MARKED", marker
        elif busy:
            e.verdict, e.reason = "KEEP-BUSY", busy
        elif ref:
            e.verdict, e.reason = "KEEP-REFERENCED", ref
        else:
            ev, complete = _evidence(p)
            if ev:
                e.verdict, e.reason = "KEEP-EVIDENCE", f"archive first: {', '.join(ev[:3])}"
            elif not complete:
                e.verdict, e.reason = "KEEP-UNVERIFIABLE", "evidence walk hit its cap"
            elif nested:
                e.verdict, e.reason = "REMOVE-AFTER-WORKTREES", f"contains worktree(s) {', '.join(nested[:3])}"
            else:
                e.verdict, e.reason = "REMOVE", "plain scratch"
        entries.append(e)

    changed = True
    while changed:                                   # in-root references from SURVIVING entries
        changed = False
        kept = [x.path for x in entries if x.verdict.startswith("KEEP")]
        for e in entries:
            if e.verdict.startswith("KEEP"):
                continue
            real = os.path.realpath(e.path)
            for key in {e.path.rstrip("/"), real.rstrip("/")}:
                srcs = [s for s in probe.refs.get(key, []) if not _under(s, key)]
                holder = next((k for s in srcs for k in kept if _under(s, k)), None)
                if holder:
                    e.verdict, e.reason = "KEEP-REFERENCED", f"named from kept {holder}"
                    changed = True
                    break
    return entries


def apply_plan(entries: list[Entry], decl: Decl, *, base: str = wg.DEFAULT_BASE,
               guarded_rm: Path = GUARDED_RM, fetch: bool = True) -> list[Entry]:
    """Execute a plan, rechecking declared-root markers before applying it.

    Every removal is also re-checked against a FRESH probe (a process may have started since the
    plan); references from entries that are themselves being removed are dropped from that probe,
    since they go away in the same pass. The marker check protects the plan/apply boundary; it is
    not an atomic guarantee against a marker created after that check.
    """
    marked_roots = _declared_keep_roots(decl.dirs)
    for e in entries:
        marker = _declared_keep_reason(e.path, marked_roots)
        if marker:
            e.verdict, e.reason, e.result = "KEEP-MARKED", marker, "kept (declared root is marked)"
    fresh = wg.gather_probe()
    dying = [e.path for e in entries if e.verdict.startswith("REMOVE")]
    probe = wg.Probe(cwds=fresh.cwds, proc_refs=fresh.proc_refs, complete=fresh.complete,
                     ref_files_scanned=fresh.ref_files_scanned,
                     refs={k: [s for s in v if not any(_under(s, d) for d in dying)]
                           for k, v in fresh.refs.items()})
    for e in entries:                                         # worktrees first
        if e.kind != "worktree":
            continue
        if e.verdict != "REMOVE":
            e.result = "kept"
            continue
        ok, msg = wg.remove_one(e.path, base=base, min_idle_days=0.0, fetch=fetch, probe=probe)
        e.result = msg
        if not ok:
            e.verdict = "KEEP-GATE-REFUSED"
    for e in entries:                       # worktrees nested in a plain scratch dir (tmp/<id>/research)
        if e.verdict != "REMOVE-AFTER-WORKTREES":
            continue
        real = os.path.realpath(e.path)
        for repo_wt in list(_registered_worktrees(wg.DEFAULT_REPOS)):
            if repo_wt.startswith(real + "/"):
                ok, msg = wg.remove_one(repo_wt, base=base, min_idle_days=0.0, fetch=fetch, probe=probe)
                if not ok:
                    e.verdict, e.reason, e.result = "KEEP-NESTED-WORKTREE", msg, "kept"
                    break
        else:
            e.verdict = "REMOVE"
    for e in entries:                                         # then plain scratch, trash-first
        if _never_touch(e.path):
            e.result = "REFUSED: NEVER_TOUCH (operator 2026-10-04: claude/codex logs are off-limits)"
            continue
        if e.kind == "worktree":
            continue
        if e.verdict != "REMOVE":
            e.result = e.result or "kept"
            continue
        busy = probe.busy(e.path)
        if busy:
            e.verdict, e.reason, e.result = "KEEP-BUSY", busy, "kept (busy at apply time)"
            continue
        marker = _keep_marker(e.path) or _deep_marker(e.path)   # a marker written since the plan
        if marker:
            e.verdict, e.reason, e.result = "KEEP-MARKED", marker, "kept (marker present at apply time)"
            continue
        if not guarded_rm.exists():
            e.result = f"REFUSED: {guarded_rm} missing (trash-first rule; never rm -rf scratch)"
            e.verdict = "KEEP-NO-TRASH"
            continue
        cp = subprocess.run(["bash", str(guarded_rm), e.path], capture_output=True, text=True,
                            timeout=1800)
        e.result = "trashed" if cp.returncode == 0 else f"guarded_rm failed: {(cp.stderr or cp.stdout).strip()[:200]}"
        if cp.returncode != 0:
            e.verdict = "KEEP-RM-FAILED"
    for d in decl.dirs:                                       # an emptied declared dir goes last
        try:
            if os.path.isdir(d) and not os.listdir(d):
                os.rmdir(d)
        except OSError:
            pass
    return entries


# ---------------------------------------------------------------------------------------------------
# ORPHAN SWEEP (operator approval 2026-11-04: close the scratch-reaper gaps). The per-handoff `apply`
# above only fires when a dispatcher session reaches done, so scratch from non-dispatcher writers
# (codex-ni-*, codex3-*, refactor-*, one-off dated dirs), from sessions that never finish, and from
# before the ws58 2026-11-02 wiring was never reaped. `sweep` looks at every TOP-LEVEL entry of
# /mnt/raid0/llm/tmp and admits it as a candidate only if ALL of these hold:
#   (a) nothing inside it (files or dirs, lstat mtime) is newer than --min-age-days;
#   (b) no process has its cwd, an open fd, or an argv/environ reference under it;
#   (c) it is not named by a live dispatcher session (status not done/retired: cwd, scratch_root(s),
#       tmp/<slug>), a FILLERS.md row whose status is not terminal, a ready/*.json, a non-ended
#       grant, a booking, or a live launch file (worktree_gate's reference probe);
#   (d) it is not protected: PROTECTED_TOP names, NEVER_TOUCH, or anything containing a keep marker
#       (worktree_gate.KEEP_MARKERS, `*.epyc-keep`, or an upper-case KEEP / RETAIN / LEAN token).
# Survivors are then handed to the SAME build_plan/apply_plan as `apply` (evidence keep, worktree gate,
# fixpoint references, guarded_rm trash-first) — there is no second deletion primitive here.
# (e) FREE-SPACE RULE: a sweep only deletes when free space on the filesystem is below
#     --apply-below-free-gib (default 500 GiB, i.e. 350 GiB above the 150 GiB disk-bin floor). Above it
#     the sweep degrades to a dry run: the leak is still visible in the log, but nothing that might yet
#     be wanted is trashed while the disk is comfortable. Note the trash is on the same filesystem, so
#     the bytes return only after scripts/safety/trash-sweep.sh runs.
# Every candidate verdict is logged as one line:
#     SCRATCH-REAP[-DRYRUN] path=<p> bytes=<n> reason=<why> result=<what happened>
# ---------------------------------------------------------------------------------------------------
SWEEP_BASE = "/mnt/raid0/llm/tmp"
FLAGS_DIR = "/mnt/raid0/llm/tmp/compute-flags"
SWEEP_LOG_NAME = "scratch-reap.log"
PROTECTED_TOP = ("compute-flags", "autokernel-cross-workload-keep-gate", ".trash")
MARKER_TOKEN_RE = re.compile(r"(^|[._-])(KEEP|RETAIN|LEAN)([._-]|$)")
TERMINAL_ROW = {"COMPLETE", "COMPLETED", "CANCELLED", "CANCELED", "DONE", "FAILED", "WITHDRAWN",
                "RETIRED", "SUPERSEDED", "ABANDONED"}
TERMINAL_SESSION = {"done", "retired"}
SWEEP_WALK_CAP = 500_000
DEFAULT_APPLY_BELOW_FREE_GIB = 500.0


@dataclass
class SweepItem:
    path: str
    bytes: int = 0
    verdict: str = ""             # CANDIDATE | KEEP-<why> | REAP | KEEP-<plan verdict>
    reason: str = ""
    result: str = ""


def _is_marker(name: str) -> bool:
    return name in wg.KEEP_MARKERS or name.endswith(".epyc-keep") or bool(MARKER_TOKEN_RE.search(name))


def _age_scan(path: str, cutoff: float) -> tuple[str | None, int]:
    """(why-kept or None, bytes). Walks once: stops at the first entry newer than cutoff or marker."""
    total = 0
    try:
        st = os.lstat(path)
    except OSError as exc:
        return f"UNREADABLE {exc}", 0
    if st.st_mtime > cutoff:
        return "RECENT top-level mtime", 0
    if _is_marker(os.path.basename(path)):
        return f"MARKED {path}", 0
    if not os.path.isdir(path) or os.path.islink(path):
        return None, st.st_blocks * 512
    seen = 0
    for dp, dn, fn in os.walk(path):
        for n in dn + fn:
            seen += 1
            if seen > SWEEP_WALK_CAP:
                return "UNVERIFIABLE walk cap hit", total
            p = os.path.join(dp, n)
            if _is_marker(n):
                return f"MARKED {p}", total
            try:
                s = os.lstat(p)
            except OSError:
                continue
            if s.st_mtime > cutoff:
                return f"RECENT {p}", total
            total += s.st_blocks * 512
    return None, total


def _open_fd_paths(proc_root: str = "/proc") -> list[str]:
    """Realpaths of every open fd target visible to us (the gap worktree_gate's probe leaves: fds)."""
    out = []
    try:
        pids = [p for p in os.listdir(proc_root) if p.isdigit()]
    except OSError:
        return out
    for pid in pids:
        fd_dir = f"{proc_root}/{pid}/fd"
        try:
            fds = os.listdir(fd_dir)
        except OSError:
            continue
        for fd in fds:
            try:
                t = os.readlink(f"{fd_dir}/{fd}")
            except OSError:
                continue
            if t.startswith("/"):
                out.append(t.removesuffix(" (deleted)"))
    return out


def _paths_in(text: str) -> list[str]:
    return [m.group(0).rstrip("/.") for m in wg.PATH_TOKEN_RE.finditer(text)]


def _live_row_text(fillers: str) -> str:
    """Text of every FILLERS.md table row whose status cell is not terminal (READY/ARMED/RUNNING/...)."""
    try:
        lines = Path(fillers).read_text(errors="replace").splitlines()
    except OSError:
        return ""
    out, status_idx = [], None
    for ln in lines:
        if not ln.startswith("|"):
            continue
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        low = [c.lower() for c in cells]
        if "status" in low and status_idx is None:
            status_idx = low.index("status")
            continue
        if set(ln.replace("|", "").strip()) <= set("-: "):
            continue
        st = cells[status_idx].upper() if status_idx is not None and status_idx < len(cells) else ""
        if st and st.split()[0].strip("*`") in TERMINAL_ROW:
            continue
        out.append(ln)
    return "\n".join(out)


def live_references(flags: str = FLAGS_DIR, base: str = SWEEP_BASE) -> dict[str, str]:
    """{top-level name under base: source} named by live rows, ready files, grants, bookings, sessions."""
    texts: list[tuple[str, str]] = [("FILLERS.md live row", _live_row_text(os.path.join(flags, "FILLERS.md")))]
    for p in sorted(glob.glob(os.path.join(flags, "ready", "*.json"))):
        try:
            texts.append((p, Path(p).read_text(errors="replace")))
        except OSError:
            continue
    gdir = os.path.join(flags, "grants")
    for p in sorted(glob.glob(os.path.join(gdir, "*.grant"))):
        stem = p[:-len(".grant")]
        if glob.glob(glob.escape(stem) + ".ended*") or glob.glob(glob.escape(stem) + ".complete*"):
            continue
        try:
            texts.append((p, Path(p).read_text(errors="replace") + "\n" + p))
        except OSError:
            continue
    for p in sorted(glob.glob(os.path.join(flags, "bookings", "*"))):
        if os.path.isfile(p):
            try:
                texts.append((p, Path(p).read_text(errors="replace")))
            except OSError:
                continue
    try:
        reg = json.loads(Path(os.path.join(flags, "handoff-sessions.json")).read_text())
    except (OSError, ValueError):
        reg = {}
    for slug, e in (reg.get("sessions") or {}).items():
        if str(e.get("status") or "").lower() in TERMINAL_SESSION:
            continue
        names = [e.get("cwd"), e.get("scratch_root"), *(e.get("scratch_roots") or []), os.path.join(base, slug)]
        texts.append((f"session {slug}", "\n".join(n for n in names if n)))
    out: dict[str, str] = {}
    pref = base.rstrip("/") + "/"
    for src, text in texts:
        for p in _paths_in(text):
            if p.startswith(pref):
                out.setdefault(p[len(pref):].split("/", 1)[0], src)
    return out


def free_gib(path: str) -> float:
    try:
        st = os.statvfs(path)
        return st.f_bavail * st.f_frsize / 2**30
    except OSError:
        return float("inf")


def sweep(base: str = SWEEP_BASE, *, min_age_days: float = 3.0, dry_run: bool = True,
          flags: str = FLAGS_DIR, apply_below_free_gib: float = DEFAULT_APPLY_BELOW_FREE_GIB,
          probe: wg.Probe | None = None, fd_paths: list[str] | None = None,
          refs: dict[str, str] | None = None, guarded_rm: Path = GUARDED_RM, fetch: bool = True,
          now: float | None = None, log_path: str | None = None, free=free_gib) -> tuple[list[SweepItem], bool]:
    """Age-based orphan sweep over the top level of `base`. Returns (items, dry_run_effective)."""
    import time as _t
    now = _t.time() if now is None else now
    cutoff = now - min_age_days * 86400
    eff_dry = dry_run or free(base) >= apply_below_free_gib
    probe = probe if probe is not None else wg.gather_probe()
    fd_paths = fd_paths if fd_paths is not None else _open_fd_paths()
    refs = refs if refs is not None else live_references(flags, base)
    items: list[SweepItem] = []
    try:
        names = sorted(os.listdir(base))
    except OSError:
        names = []
    for name in names:
        p = os.path.join(base, name)
        it = SweepItem(p)
        items.append(it)
        real = os.path.realpath(p)
        if name in PROTECTED_TOP or _never_touch(p) or real == os.path.realpath(flags):
            it.verdict, it.reason = "KEEP-PROTECTED", "protected top-level name"
            continue
        if name in refs:
            it.verdict, it.reason = "KEEP-LIVE-REF", f"named by {refs[name]}"
            continue
        why, it.bytes = _age_scan(p, cutoff)
        if why:
            it.verdict, it.reason = f"KEEP-{why.split()[0]}", why
            continue
        fd = next((f for f in fd_paths if _under(f, real) or _under(f, p)), None)
        busy = probe.busy(p) or (f"open fd {fd}" if fd else None)
        if busy:
            it.verdict, it.reason = "KEEP-BUSY", busy
            continue
        ref = probe.referenced(p)
        if ref:
            it.verdict, it.reason = "KEEP-REFERENCED", ref
            continue
        it.verdict, it.reason = "CANDIDATE", f"orphan: nothing newer than {min_age_days:g}d, no live reference"
    cands = [it for it in items if it.verdict == "CANDIDATE"]
    dirs = [it.path for it in cands if os.path.isdir(it.path) and not os.path.islink(it.path)]
    decl = Decl(dirs=dirs)
    entries = build_plan(decl, probe=probe) if dirs else []
    for it in cands:
        if it.path not in dirs:            # a top-level plain file / symlink: one entry, same guards
            entries.append(Entry(it.path, "file", "REMOVE", "plain scratch"))
    if not eff_dry and entries:
        entries = apply_plan(entries, decl, guarded_rm=guarded_rm, fetch=fetch)
    by_root: dict[str, list[Entry]] = {}
    for e in entries:
        root = next((it.path for it in cands if _under(e.path, it.path)), e.path)
        by_root.setdefault(root, []).append(e)
    for it in cands:
        es = by_root.get(it.path, [])
        kept = [e for e in es if e.verdict.startswith("KEEP")]
        if kept:
            it.verdict = kept[0].verdict
            it.reason = f"{kept[0].path}: {kept[0].reason}"
            it.result = f"{len(es) - len(kept)} of {len(es)} children " + ("would be trashed" if eff_dry else "trashed")
        else:
            it.verdict = "REAP"
            it.result = "would trash (dry run)" if eff_dry else \
                ("trashed" if not os.path.exists(it.path) else "; ".join(sorted({e.result for e in es}))[:200])
    tag = "SCRATCH-REAP-DRYRUN" if eff_dry else "SCRATCH-REAP"
    lines = [f"{tag} path={it.path} bytes={it.bytes} reason={it.reason!r} result={it.result!r}"
             for it in cands]
    reap = [it for it in cands if it.verdict == "REAP"]
    lines.append(f"{tag} SUMMARY base={base} entries={len(items)} candidates={len(cands)} reap={len(reap)} "
                 f"bytes={sum(it.bytes for it in reap)} min_age_days={min_age_days:g} "
                 f"free_gib={free(base):.0f} apply_below_free_gib={apply_below_free_gib:g}")
    if log_path:
        try:
            stamp = _t.strftime("%Y-%m-%dT%H:%M:%SZ", _t.gmtime(now))
            with open(log_path, "a") as f:
                f.writelines(f"{stamp} {ln}\n" for ln in lines)
        except OSError:
            pass
    return items, eff_dry


def _sweep_main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="age-based orphan sweep of /mnt/raid0/llm/tmp (see ORPHAN SWEEP)")
    ap.add_argument("cmd", choices=["sweep"])
    ap.add_argument("--base", default=SWEEP_BASE)
    ap.add_argument("--flags", default=FLAGS_DIR)
    ap.add_argument("--min-age-days", type=float, default=3.0)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--apply-below-free-gib", type=float, default=DEFAULT_APPLY_BELOW_FREE_GIB)
    ap.add_argument("--log", default=None, help=f"append SCRATCH-REAP lines here (conventional: <flags>/{SWEEP_LOG_NAME})")
    ap.add_argument("--no-fetch", action="store_true")
    ap.add_argument("--all", action="store_true", help="also print kept entries")
    a = ap.parse_args(argv)
    items, eff_dry = sweep(a.base, min_age_days=a.min_age_days, dry_run=a.dry_run, flags=a.flags,
                           apply_below_free_gib=a.apply_below_free_gib, log_path=a.log, fetch=not a.no_fetch)
    tag = "SCRATCH-REAP-DRYRUN" if eff_dry else "SCRATCH-REAP"
    for it in sorted(items, key=lambda i: -i.bytes):
        if a.all or it.verdict == "REAP" or it.result:
            print(f"{tag} {it.verdict:<18} bytes={it.bytes:<14} {it.path}  ({it.reason}) {it.result}")
    reap = [it for it in items if it.verdict == "REAP"]
    from collections import Counter
    print(f"\n{len(items)} entries; would-{'reap' if eff_dry else 'reaped'} {len(reap)} "
          f"({sum(i.bytes for i in reap) / 2**30:.1f} GiB); verdicts "
          + ", ".join(f"{k}={v}" for k, v in Counter(i.verdict for i in items).most_common()))
    return 0


def _decl_from_args(a) -> Decl:
    if a.handoff:
        text = Path(a.handoff).read_text(encoding="utf-8")
        d = parse_scratch(text)
        if d is None:
            raise SystemExit(f"REFUSED: {a.handoff} declares no **Scratch** field — add one "
                             "(docs/guides/agent-workflows/handoff-index-authoring.md § Scratch roots)")
    else:
        d = Decl(dirs=[r.rstrip("/") for r in a.root or []], worktree_globs=a.worktree_glob or [])
        d.errors = validate(d)
    if d.errors:
        raise SystemExit("REFUSED: invalid scratch declaration:\n  " + "\n  ".join(d.errors))
    return d


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["sweep"]:
        return _sweep_main(argv)
    ap =argparse.ArgumentParser(description="per-handoff scratch cleanup (see module docstring)")
    ap.add_argument("cmd", choices=["plan", "apply", "roots"])
    ap.add_argument("--handoff", help="handoff whose **Scratch** field names the roots")
    ap.add_argument("--root", action="append", help="ad hoc scratch dir (repeatable)")
    ap.add_argument("--worktree-glob", action="append", help="ad hoc worktree glob (repeatable)")
    ap.add_argument("--base", default=wg.DEFAULT_BASE)
    ap.add_argument("--no-fetch", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    if not a.handoff and not a.root and not a.worktree_glob:
        ap.error("need --handoff, or --root/--worktree-glob")
    try:
        decl = _decl_from_args(a)
    except SystemExit as exc:
        print(exc, file=sys.stderr)
        return 2
    if a.cmd == "roots":
        print(json.dumps(asdict(decl), indent=2))
        return 0
    if decl.none:
        print("scratch: none declared — nothing to clean")
        return 0
    entries = build_plan(decl, base=a.base)
    if a.cmd == "apply":
        entries = apply_plan(entries, decl, base=a.base, fetch=not a.no_fetch)
    if a.json:
        print(json.dumps([asdict(e) for e in entries], indent=2))
    else:
        for e in entries:
            tail = f"  -> {e.result}" if e.result else ""
            print(f"{e.verdict:<24} {e.kind:<8} {e.path}  ({e.reason}){tail}")
        kept = [e for e in entries if e.verdict.startswith("KEEP")]
        print(f"\n{len(entries)} entr{'y' if len(entries) == 1 else 'ies'} under "
              f"{', '.join(decl.dirs + decl.worktree_globs)}; {len(kept)} kept")
    return 1 if any(e.verdict.startswith("KEEP") for e in entries) else 0


if __name__ == "__main__":
    sys.exit(main())
