#!/usr/bin/env python3
"""Detect versioned WORK being changed in the shared clone instead of a lane worktree.

THE TWO PLANES (design note: ``scripts/coordination/WORKTREE_MIGRATION.md``)
---------------------------------------------------------------------------

**Canonical runtime plane — the shared clone, one instance, never forked.**
The session bus (``coordination/session-bus/``), its token files, and
``logs/`` are *state*, not *work*: they describe what agents are doing right
now, and there can only ever be one live copy of "right now". ``session_bus.py``
deliberately resolves its bus root to the literal canonical checkout regardless
of which worktree's copy of the module answers the call, precisely so that five
worktrees do not become five independently-mutating buses. Writing these files
in the shared clone is **CORRECT**, and this guard must never flag it. A guard
that nagged about bus writes would be teaching agents to break the bus.

**Versioned work plane — one worktree per agent, on ``lane/<agent>``.**
Code, docs, handoffs, progress entries, tests: an agent's own work-in-progress,
which wants git's normal machinery (diff, log, blame, revert) rather than a
single always-current snapshot. Doing *this* in the shared clone is the hazard
this guard exists to surface, because five sessions sharing one index is the
direct mechanism behind pathspec commits sweeping other sessions' hunks and
staged files riding into parallel commits.

The split is exactly "does this file want to be ONE current answer, or a
HISTORY of changes an agent is making".

POSTURE: REPORT, DO NOT ENFORCE
-------------------------------

Default behaviour is advisory and exits 0 even when it finds violations. This
is deliberate. A guard that hard-fails by default on day one is a guard that
the first person it inconveniences disables permanently, which trades a small
amount of noise for a total loss of coverage. ``--strict`` opts in to a
non-zero exit and is intended for a reviewed, deliberate rollout.

The one thing that is NOT advisory is not knowing where we are. If the guard
cannot determine whether it is running in the shared clone or a linked
worktree, it fails CLOSED and LOUD (exit 4) with an error that names the
underlying cause, in both modes. A location guard that guesses is worse than
no location guard: it produces confident output about the wrong plane.

WHY LOCATION DETECTION IS NOT A PATH PREFIX COMPARISON
------------------------------------------------------

Three separate traps make ``str(path).startswith(canonical_root)`` wrong here,
and a fourth makes ``realpath`` wrong as a fix:

1. The shared clone is reachable under **two different absolute paths that are
   the same directory** (a bind mount, e.g. ``/workspace`` and
   ``/mnt/raid0/llm/epyc-root`` share ``st_dev``/``st_ino``). Neither is a
   symlink to the other, so ``realpath`` does **not** unify them. Comparing
   against one spelling silently misclassifies every path given in the other.
2. ``repos/<name>`` inside the clone is a **symlink to a different repository**
   entirely. ``realpath``-ing such a path moves it *out* of the clone, so
   resolving first destroys the very information needed to say "this belongs to
   another repo, not my jurisdiction".
3. Linked worktrees and the shared clone report the **same**
   ``--git-common-dir``. Common-dir alone cannot tell them apart.
4. Paths that no longer exist (deletions, renames) cannot be ``stat``-ed at
   all, so identity checks must degrade to the nearest existing ancestor.

So: location comes from ``git rev-parse`` (git's own answer, no path guessing),
and the shared clone is identified structurally as *the main worktree* — the
one whose ``--git-dir`` IS its ``--git-common-dir``. Path-to-repo mapping tries
the literal path first (preserving trap 2), then the resolved path, then an
inode-identity ancestor walk (defeating trap 1 and trap 4).

EXIT CODES
----------
    0  clean, or violations found in advisory (default) mode
    3  work-plane paths changed in the shared clone, and ``--strict`` was given
    4  could not determine location, or git itself failed (fail-closed)
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable, Sequence

# --------------------------------------------------------------------------
# Planes
# --------------------------------------------------------------------------

RUNTIME = "runtime"          # live coordination state; correct in the shared clone
WORK = "work"                # versioned work-in-progress; belongs in a lane worktree
UNKNOWN = "unknown"          # cannot classify confidently -- reported, never flagged
OUT_OF_SCOPE = "out-of-scope"  # a different repository reached through repos/
OUT_OF_TREE = "out-of-tree"  # not inside the working tree being inspected

#: Only ``WORK`` is ever a violation. ``UNKNOWN`` is deliberately NOT flagged:
#: a wrong work-classification blocks correct work, which costs more than the
#: hazard it would have caught, and an unflagged-but-reported path is still
#: visible to a human. Ambiguity is surfaced, not resolved by guessing.
FLAGGABLE = (WORK,)


# --------------------------------------------------------------------------
# Classification rules
# --------------------------------------------------------------------------

#: Live coordination state. Correct in the shared clone; never flagged anywhere.
RUNTIME_PREFIXES: tuple[str, ...] = (
    "coordination/session-bus/",  # inbox, outbox, cursors, heartbeats, queue, ledgers, tokens
    "logs/",                      # agent_audit.log, daemon logs, pidfiles, canvases
    "tmp/",                       # scratch; .gitignored except .gitkeep
    "tokens/",                    # defensive: token-queue.md under an alternate top-level spelling
)

#: Generated or session-scoped files whose plane is genuinely arguable. They are
#: derived state of the versioned plane (regenerated, not hand-written), which
#: makes them look runtime, but they are committed alongside the work that
#: produced them, which makes them look versioned. Reported as UNKNOWN so a human
#: decides rather than the guard guessing in either direction.
AMBIGUOUS_EXACT: frozenset[str] = frozenset(
    {
        "handoffs/active/.index-state.json",
        "handoffs/active/.index-graph.json",
        ".research-session.json",
        ".current_session",
    }
)

#: Everything under ``coordination/`` that is NOT the session bus. The design note
#: defines the runtime plane as the bus "and any other live coordination sidecar"
#: -- deliberately open-ended, so this subtree cannot be closed confidently. It
#: mixes plain docs (BLOCKED_TASKS.md) with live ledgers (inference-batch/
#: ledger.jsonl). Reported as UNKNOWN rather than split on a guess.
AMBIGUOUS_PREFIXES: tuple[str, ...] = ("coordination/",)

#: Child repositories reached through symlinks. Changes there are versioned in a
#: DIFFERENT repository with its own branch and index, so this guard has no
#: jurisdiction over them and must not flag them.
OUT_OF_SCOPE_PREFIXES: tuple[str, ...] = ("repos/",)

#: Versioned work-in-progress: the plane that belongs in a lane worktree.
WORK_PREFIXES: tuple[str, ...] = (
    ".claude/",
    ".devc/",
    ".devcontainer/",
    ".github/",
    ".research/",
    ".vidya/",
    "agents/",
    "artifacts/",
    "bug-reports/",
    "dashboard/",
    "data/",
    "docs/",
    "handoffs/",
    "measurement/",
    "progress/",
    "research/",
    "scripts/",
    "site_src/",
    "tests/",
    "wiki/",
)

#: Top-level files with these suffixes are docs/config -- versioned work.
WORK_TOPLEVEL_SUFFIXES: frozenset[str] = frozenset(
    {".md", ".yml", ".yaml", ".ini", ".txt", ".toml", ".cfg", ".json"}
)

#: Top-level extensionless files that are versioned work.
WORK_TOPLEVEL_NAMES: frozenset[str] = frozenset({"LICENSE", ".gitignore", ".shellcheckrc"})

#: Git's own metadata is never anyone's work.
IGNORED_PREFIXES: tuple[str, ...] = (".git/",)


def classify(rel: str) -> tuple[str, str]:
    """Classify one repo-relative POSIX path into a plane.

    Returns ``(plane, rule)`` where ``rule`` names the matching rule, so a
    surprising verdict can be traced to the line that produced it instead of
    being taken on faith.

    Rule order is load-bearing: the specific ambiguous entries are tested before
    the broad prefixes that would otherwise swallow them (``handoffs/active/
    .index-state.json`` would be caught by ``handoffs/``), and the runtime
    allowlist is tested before the ambiguous ``coordination/`` prefix that
    contains it.
    """
    # Normalise separators and strip a leading "./" -- but NOT with lstrip("./"),
    # which strips a character SET and would turn ".claude/x" into "claude/x",
    # silently demoting a work-plane dotfile tree to unmatched.
    rel = rel.replace(os.sep, "/")
    while rel.startswith("./"):
        rel = rel[2:]
    while rel.startswith("/"):
        rel = rel[1:]

    if not rel or rel == ".":
        return UNKNOWN, "empty-path"

    for prefix in IGNORED_PREFIXES:
        if rel == prefix.rstrip("/") or rel.startswith(prefix):
            return UNKNOWN, "git-metadata"

    # Specific before general.
    if rel in AMBIGUOUS_EXACT:
        return UNKNOWN, "ambiguous-generated-state"

    for prefix in OUT_OF_SCOPE_PREFIXES:
        if rel == prefix.rstrip("/") or rel.startswith(prefix):
            return OUT_OF_SCOPE, f"child-repo:{prefix}"

    for prefix in RUNTIME_PREFIXES:
        if rel == prefix.rstrip("/") or rel.startswith(prefix):
            return RUNTIME, f"runtime-prefix:{prefix}"

    for prefix in AMBIGUOUS_PREFIXES:
        if rel == prefix.rstrip("/") or rel.startswith(prefix):
            return UNKNOWN, f"ambiguous-prefix:{prefix}"

    for prefix in WORK_PREFIXES:
        if rel == prefix.rstrip("/") or rel.startswith(prefix):
            return WORK, f"work-prefix:{prefix}"

    if "/" not in rel.rstrip("/"):
        name = rel.rstrip("/")
        if name in WORK_TOPLEVEL_NAMES:
            return WORK, "work-toplevel-name"
        if Path(name).suffix in WORK_TOPLEVEL_SUFFIXES:
            return WORK, "work-toplevel-suffix"

    return UNKNOWN, "unmatched"


# --------------------------------------------------------------------------
# Errors -- specific causes, never a generic swallow
# --------------------------------------------------------------------------


class LaneWorktreeError(RuntimeError):
    """Base: the guard could not establish ground truth. Always fail closed."""


class GitInvocationError(LaneWorktreeError):
    """git could not be executed at all (missing binary, permissions)."""


class NotAGitWorkingTree(LaneWorktreeError):
    """The starting directory is not inside a git working tree."""


class UnrecognizedGitLayout(LaneWorktreeError):
    """git answered, but the answer matches neither a main nor a linked worktree."""


# --------------------------------------------------------------------------
# Location detection
# --------------------------------------------------------------------------

SHARED_CLONE = "shared-clone"
LINKED_WORKTREE = "linked-worktree"


@dataclass(frozen=True)
class Location:
    """Where the guard is running, as reported by git itself."""

    toplevel: Path
    git_dir: Path
    common_dir: Path
    kind: str          # SHARED_CLONE | LINKED_WORKTREE
    branch: str        # "HEAD" when detached
    lane: str | None   # agent name when the branch is lane/<agent>, else None

    @property
    def is_shared_clone(self) -> bool:
        return self.kind == SHARED_CLONE


def _run_git(args: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise GitInvocationError(
            f"git executable not found on PATH; cannot determine worktree identity "
            f"(cwd={cwd})"
        ) from exc
    except OSError as exc:
        raise GitInvocationError(
            f"could not execute git in {cwd}: {exc.__class__.__name__}: {exc}"
        ) from exc


def _dir_identity(path: Path) -> tuple[int, int] | None:
    """``(st_dev, st_ino)`` for an existing path, else ``None``.

    Identity rather than string comparison because the shared clone is reachable
    under two distinct absolute paths that are the same directory (a bind mount),
    which no amount of ``realpath`` will unify.
    """
    try:
        st = path.stat()
    except (OSError, ValueError):
        return None
    return (st.st_dev, st.st_ino)


def _same_dir(a: Path, b: Path) -> bool:
    ida, idb = _dir_identity(a), _dir_identity(b)
    if ida is not None and idb is not None:
        return ida == idb
    # Fall back to path comparison only when a stat was impossible.
    try:
        return os.path.normpath(str(a)) == os.path.normpath(str(b))
    except (OSError, ValueError):
        return False


def _is_ancestor(ancestor: Path, descendant: Path) -> bool:
    try:
        descendant.relative_to(ancestor)
        return True
    except ValueError:
        return False


def detect_location(start: Path | str | None = None) -> Location:
    """Determine whether ``start`` sits in the shared clone or a linked worktree.

    Raises a specific :class:`LaneWorktreeError` subclass -- never returns a
    guess -- when ground truth cannot be established.
    """
    cwd = Path(start) if start is not None else Path.cwd()
    if not cwd.is_dir():
        raise NotAGitWorkingTree(
            f"starting path is not an existing directory: {cwd}"
        )

    proc = _run_git(
        ["rev-parse", "--path-format=absolute", "--git-dir", "--git-common-dir", "--show-toplevel"],
        cwd=cwd,
    )
    if proc.returncode != 0:
        stderr = proc.stderr.strip() or "(git produced no stderr)"
        raise NotAGitWorkingTree(
            f"git rev-parse failed in {cwd} (exit {proc.returncode}): {stderr}"
        )

    lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
    if len(lines) != 3:
        raise UnrecognizedGitLayout(
            f"expected 3 paths from git rev-parse (--git-dir, --git-common-dir, "
            f"--show-toplevel) in {cwd}, got {len(lines)}: {lines!r}. A bare "
            f"repository has no working tree and cannot host either plane."
        )

    git_dir, common_dir, toplevel = (Path(ln) for ln in lines)

    if _same_dir(git_dir, common_dir):
        kind = SHARED_CLONE
    elif _is_ancestor(common_dir / "worktrees", git_dir):
        kind = LINKED_WORKTREE
    else:
        raise UnrecognizedGitLayout(
            f"git-dir {git_dir} is neither identical to git-common-dir {common_dir} "
            f"(which would make this the shared clone's main worktree) nor located "
            f"under {common_dir / 'worktrees'} (which would make it a linked "
            f"worktree). Refusing to guess which plane applies."
        )

    branch_proc = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd)
    branch = branch_proc.stdout.strip() if branch_proc.returncode == 0 else "HEAD"
    lane = branch[len("lane/") :] if branch.startswith("lane/") else None

    return Location(
        toplevel=toplevel,
        git_dir=git_dir,
        common_dir=common_dir,
        kind=kind,
        branch=branch,
        lane=lane,
    )


# --------------------------------------------------------------------------
# Path -> repo-relative mapping
# --------------------------------------------------------------------------


def _resolve_lenient(path: Path) -> Path:
    try:
        return path.resolve()
    except (OSError, RuntimeError):
        return Path(os.path.normpath(str(path)))


def _identity_relative(path: Path, root: Path) -> str | None:
    """Map ``path`` under ``root`` by walking up to an inode-identical ancestor.

    Handles both the bind-mount duality (two absolute spellings of one directory)
    and non-existent paths (deletions, rename sources), which cannot be stat-ed
    and so must degrade to their nearest existing ancestor.
    """
    root_id = _dir_identity(root)
    if root_id is None:
        return None

    parts: list[str] = []
    cur = _resolve_lenient(path)
    seen = 0
    while seen < 256:
        seen += 1
        cur_id = _dir_identity(cur)
        if cur_id is not None and cur_id == root_id:
            return "/".join(reversed(parts))
        parent = cur.parent
        if parent == cur:
            return None
        parts.append(cur.name)
        cur = parent
    return None


def repo_relative(path: Path, root: Path) -> str | None:
    """Return ``path`` as a POSIX repo-relative string, or ``None`` if outside.

    Order matters. The literal comparison runs FIRST so that a path inside
    ``repos/<name>`` -- a symlink to a different repository -- is still seen as
    ``repos/...`` and can be reported as out-of-scope. Resolving first would
    relocate it outside the clone and lose that distinction.
    """
    # 1. Literal containment: preserves symlinked subtrees as given.
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        pass

    # 2. Resolved containment: handles a symlinked path to a real in-tree file.
    try:
        return _resolve_lenient(path).relative_to(_resolve_lenient(root)).as_posix()
    except ValueError:
        pass

    # 3. Inode identity: handles bind-mounted alternate spellings of the root.
    return _identity_relative(path, root)


# --------------------------------------------------------------------------
# Findings and report
# --------------------------------------------------------------------------


@dataclass
class Finding:
    given: str
    rel: str | None
    plane: str
    rule: str

    @property
    def flaggable(self) -> bool:
        return self.plane in FLAGGABLE


@dataclass
class Report:
    location: Location
    findings: list[Finding] = field(default_factory=list)

    @property
    def examined(self) -> int:
        """Number of candidate paths actually inspected.

        Exposed so callers can refuse to conclude "nothing flagged" from a run
        that examined nothing -- a check that passes because its input was empty
        is a vacuous pass, not a green light.
        """
        return len(self.findings)

    @property
    def violations(self) -> list[Finding]:
        """Work-plane paths being changed inside the shared clone.

        Empty by construction anywhere else: in a linked worktree, work-plane
        changes are exactly what is supposed to be happening.
        """
        if not self.location.is_shared_clone:
            return []
        return [f for f in self.findings if f.flaggable]

    def counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for f in self.findings:
            out[f.plane] = out.get(f.plane, 0) + 1
        return out

    def to_dict(self) -> dict:
        loc = asdict(self.location)
        loc = {k: (str(v) if isinstance(v, Path) else v) for k, v in loc.items()}
        return {
            "location": loc,
            "examined": self.examined,
            "counts": self.counts(),
            "findings": [asdict(f) for f in self.findings],
            "violations": [asdict(f) for f in self.violations],
        }


# --------------------------------------------------------------------------
# Candidate collection
# --------------------------------------------------------------------------


def status_paths(location: Location, include_untracked: bool = True) -> list[Path]:
    """Candidate paths from ``git status`` in the located working tree."""
    args = ["status", "--porcelain=v1", "-z"]
    args.append("--untracked-files=normal" if include_untracked else "--untracked-files=no")
    proc = _run_git(args, cwd=location.toplevel)
    if proc.returncode != 0:
        stderr = proc.stderr.strip() or "(git produced no stderr)"
        raise LaneWorktreeError(
            f"git status failed in {location.toplevel} (exit {proc.returncode}): {stderr}"
        )

    fields = proc.stdout.split("\0")
    rels: list[str] = []
    i = 0
    while i < len(fields):
        record = fields[i]
        i += 1
        if not record or len(record) < 4:
            continue
        xy, rel = record[:2], record[3:]
        rels.append(rel)
        # Renames/copies carry their ORIGIN path in the following NUL field.
        if "R" in xy or "C" in xy:
            if i < len(fields) and fields[i]:
                rels.append(fields[i])
            i += 1

    seen: set[str] = set()
    out: list[Path] = []
    for rel in rels:
        if rel in seen:
            continue
        seen.add(rel)
        out.append(location.toplevel / rel)
    return out


def _as_absolute(raw: str, cwd: Path) -> Path:
    p = Path(raw)
    return p if p.is_absolute() else (cwd / p)


def build_report(
    location: Location,
    raw_paths: Iterable[str] | None,
    cwd: Path,
    include_untracked: bool = True,
) -> Report:
    """Classify ``raw_paths`` (or the working tree's git status) against ``location``."""
    if raw_paths is None:
        candidates = status_paths(location, include_untracked=include_untracked)
        given = [str(p) for p in candidates]
    else:
        given = [r for r in raw_paths if r.strip()]
        candidates = [_as_absolute(r, cwd) for r in given]

    report = Report(location=location)
    for raw, path in zip(given, candidates):
        rel = repo_relative(path, location.toplevel)
        if rel is None:
            report.findings.append(Finding(raw, None, OUT_OF_TREE, "outside-working-tree"))
            continue
        plane, rule = classify(rel)
        report.findings.append(Finding(raw, rel, plane, rule))
    return report


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

EXIT_OK = 0
EXIT_VIOLATIONS = 3
EXIT_LOCATION = 4

_ADVICE = """
  Work-plane changes belong in a lane worktree, not the shared clone.
  Five sessions sharing one index is how pathspec commits sweep other
  sessions' hunks and staged files ride into parallel commits.

    lane worktree: /mnt/raid0/llm/worktrees/mains/<agent>  (branch lane/<agent>)
    design note:   scripts/coordination/WORKTREE_MIGRATION.md

  Runtime state (session bus, logs) is CORRECT here and is not listed above.
"""


def _render(report: Report, verbose: bool) -> str:
    loc = report.location
    lines: list[str] = []
    where = "SHARED CLONE" if loc.is_shared_clone else "lane worktree" if loc.lane else "linked worktree"
    lines.append(f"location : {where}  ({loc.toplevel})")
    lines.append(f"branch   : {loc.branch}" + (f"   lane={loc.lane}" if loc.lane else ""))
    lines.append(f"examined : {report.examined} path(s)  {report.counts()}")

    if verbose:
        for f in report.findings:
            lines.append(f"  [{f.plane:<12}] {f.rel or f.given}   ({f.rule})")

    violations = report.violations
    if violations:
        lines.append("")
        lines.append(f"WORK-PLANE CHANGES IN THE SHARED CLONE: {len(violations)}")
        for f in violations:
            lines.append(f"  - {f.rel}   ({f.rule})")
        lines.append(_ADVICE.rstrip())
    elif loc.is_shared_clone:
        lines.append("OK: no work-plane changes in the shared clone.")
    else:
        lines.append("OK: work-plane changes here are expected (not the shared clone).")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="check_lane_worktree.py",
        description=(
            "Report versioned WORK being changed in the shared clone instead of a "
            "lane worktree. Runtime coordination state (session bus, logs) is "
            "correct in the shared clone and is never flagged."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "exit codes: 0 ok (or advisory) | 3 violations under --strict | "
            "4 location undeterminable (fail-closed)"
        ),
    )
    parser.add_argument("paths", nargs="*", help="candidate paths; default is git status")
    parser.add_argument("--stdin", action="store_true", help="read newline-separated paths from stdin")
    parser.add_argument("--root", default=None, help="working tree to inspect (default: cwd)")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="exit %d when work-plane paths are changed in the shared clone" % EXIT_VIOLATIONS,
    )
    parser.add_argument("--json", action="store_true", help="emit the full report as JSON")
    parser.add_argument("--verbose", action="store_true", help="list every examined path")
    parser.add_argument("--no-untracked", action="store_true", help="ignore untracked files")
    args = parser.parse_args(argv)

    cwd = Path(args.root) if args.root else Path.cwd()

    try:
        location = detect_location(cwd)
    except LaneWorktreeError as exc:
        print(
            f"check_lane_worktree: FAILED CLOSED: {exc.__class__.__name__}: {exc}",
            file=sys.stderr,
        )
        return EXIT_LOCATION

    raw: list[str] | None
    if args.stdin:
        raw = [ln.strip() for ln in sys.stdin.read().splitlines() if ln.strip()]
        raw.extend(args.paths)
    elif args.paths:
        raw = list(args.paths)
    else:
        raw = None

    try:
        report = build_report(location, raw, cwd, include_untracked=not args.no_untracked)
    except LaneWorktreeError as exc:
        print(
            f"check_lane_worktree: FAILED CLOSED: {exc.__class__.__name__}: {exc}",
            file=sys.stderr,
        )
        return EXIT_LOCATION

    if args.json:
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    else:
        print(_render(report, verbose=args.verbose))

    if report.violations and args.strict:
        return EXIT_VIOLATIONS
    return EXIT_OK


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
