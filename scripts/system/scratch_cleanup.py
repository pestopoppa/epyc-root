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
  `git -C <repo> worktree lock --reason "load-bearing: <who>" <path>`. A marker should say WHY.
  An emptied declared dir is removed last (rmdir only).

References from INSIDE the declared roots do not keep a sibling: the whole root is being cleaned,
and a script there that is actually running is caught by the process probe instead. That is the
point of declaring roots — the 2026-10-04 incident (a DS41 launcher under tmp/ exported
EPYC_ROOT_REPO=<worktree>, the worktree was removed, the campaign crashed) is a reference from
OUTSIDE the worktree's root, which is still a hard keep.

Exit codes: 0 nothing refused; 1 at least one entry kept for a reason (listed); 2 usage error,
including a handoff with no or an invalid **Scratch** declaration.
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
    if os.path.isdir(path) and not os.path.islink(path):
        for m in wg.KEEP_MARKERS:
            mp = os.path.join(path, m)
            if os.path.exists(mp):
                return mp
    side = path.rstrip("/") + ".epyc-keep"
    return side if os.path.exists(side) else None


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
    cands: list[str] = []
    for g in decl.worktree_globs:
        cands += sorted(glob.glob(g))
    for d in decl.dirs:
        if not os.path.isdir(d):
            continue
        if os.path.realpath(d) in wts or os.path.exists(os.path.join(d, ".git")):
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
            wt = wts[real]
            wg.classify(wt, base=base, min_idle_days=0.0, probe=outside_probe,
                        canonical_roots=["/workspace", f"{wg.LLM}/epyc-root"], now=_t.time())
            e = Entry(p, "worktree")
            e.verdict, e.reason = ("REMOVE", wt.reasons[0]) if wt.verdict == wg.REMOVABLE else \
                (f"KEEP-{wt.verdict}", "; ".join(wt.reasons))
            entries.append(e)
            continue
        e = Entry(p, "dir" if os.path.isdir(p) and not os.path.islink(p) else "file")
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
        marker = _keep_marker(p)
        busy = outside_probe.busy(p)
        ref = outside_probe.referenced(p)
        if marker:
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
    """Execute a plan. Every removal is re-checked against a FRESH probe first (a process may have
    started since the plan); references from entries that are themselves being removed are
    dropped from that probe, since they go away in the same pass."""
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
    ap = argparse.ArgumentParser(description="per-handoff scratch cleanup (see module docstring)")
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
