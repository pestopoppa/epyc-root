#!/usr/bin/env python3
"""LOOP-50: the tick/deletion science gate, BLOCKING in scripts/hooks/pre-commit.extras.

Operator sign-off 2026-11-02 (decision tool, BRF-T5-2 fold-3 revision, LOOP-50 "A sign off
(blocking)"). Spec and backtest: docs/reports/tick-science-audit-20261031.md. Tick contract:
agents/shared/SESSION_LIFECYCLE.md -> "Two axioms" ("A result tick names its belief").

What it reads: exactly the commit being made. In pre-commit, git has already set
GIT_INDEX_FILE to the index being recorded (a pathspec commit's temporary index, a private
index, or a lane worktree's own index), so `git diff --cached HEAD -- handoffs/` is this
commit's own handoff change and never another session's uncommitted work.

What it refuses, each with the file, the line and the tag that line needs:

  T1  a NEW tick without a belief tag. A new tick is an added `[x]` line whose task is not
      already `[x]` in a removed line of the same commit: a `[ ]` -> `[x]` flip, or a task
      born ticked. Required on the checkbox line: `[belief: clm_<id>]`, `[belief: cc]`, or
      `[no-belief: <reason>]`.
  T2  a malformed belief tag on a new tick (`[belief: <anything else>]`, empty reason).
  T3  a declined task rendered as `[x]` (a decline is never a tick).
  T4  a new tick whose own completion text says unknown completion / INCONCLUSIVE / NOT MET /
      no verdict. Only the text after a `✅ YYYY-MM-DD` marker is read when the marker exists,
      because task titles often name the failure states they guard against.
  T5  a new `[belief: cc]` tick with neither a commit SHA nor a repository path on its line.
  T6  a new `[belief:]` tick whose cited run's latest receipt (host-local, under
      /mnt/raid0/llm/tmp/compute-flags) is FAILED / INCONCLUSIVE / INCOMPLETE / PARTIAL /
      rc!=0, unless the line carries `[receipt-ack: <id> <CLASS> — reason]`.
  D1  a removed open `[ ]` task that this commit neither re-adds as a checkbox (any file:
      folds and moves) nor replaces with a line naming it and carrying `[moved: <path>]` or
      `[declined: <who> <YYYY-MM-DD> <reason>]`.

What it never refuses: a fold or move. Folds move boxes verbatim, so an added `[x]` whose
task was `[x]` in a removed line is a move, not a tick, whatever tags it carries; and a
removed `[ ]` re-added anywhere in the commit is restored. Editing an existing `[x]` line
(adding evidence, adding the tag itself) is not a new tick either.

Merges: a line already present in ANY merge parent was judged when it was committed there,
so only violations that are new against every parent are reported.

Modes:
  (default)          the staged commit (pre-commit).
  --range A..B       replay one committed range (audits).
  --commit SHA       replay one commit exactly as the hook would have judged it.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_RECEIPTS = Path("/mnt/raid0/llm/tmp/compute-flags")
SCOPE = "handoffs/"

TICK = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+\[([ xX])\]\s*(.*)$")
TAG_ANY = re.compile(r"\[(no-belief|belief):\s*([^\]]*)\]", re.I)
TAG_BELIEF_OK = re.compile(r"^(?:cc|clm_[A-Za-z0-9_.:-]+(?:\s*,\s*clm_[A-Za-z0-9_.:-]+)*)$")
UNKNOWN = re.compile(
    r"\b(?:unknown\s+completion|completion\s+unknown|INCONCLUSIVE|NOT\s+MET|no\s+verdict|verdict\s+unknown)\b",
    re.I)
ACK = re.compile(r"\[receipt-ack:\s*[^\s\]]+\s+[A-Z][A-Z0-9_-]*\s+[—-]+\s*[^\]]+\]", re.I)
MOVED = re.compile(r"\[moved:\s*[^\]\s][^\]]*\]", re.I)
DECLINED = re.compile(r"\[declined:\s*[^\]]*20\d{2}-\d{2}-\d{2}[^\]]*\]", re.I)
SHA = re.compile(r"(?<![0-9A-Za-z])(?=[0-9a-f]*\d)(?=[0-9a-f]*[a-f])[0-9a-f]{7,64}(?![0-9A-Za-z])")
GIT_PATH = re.compile(r"(?:[\w.-]+/)+[\w.-]+\.\w+|(?:[\w.-]+/){2,}")
ID_TOKEN = re.compile(r"\b[A-Z][A-Z0-9]*(?:-[A-Z0-9][A-Z0-9.]*)+\b")
DONE_MARK = re.compile(r"✅\s*20\d{2}-\d{2}-\d{2}(?:\s*[—:-]+\s*)?")

TAG_HINT = ("[belief: clm_<id>] or [belief: cc] for a result tick, "
            "or [no-belief: <reason>] (e.g. not-a-result, tooling-repair, build/landing)")
DEL_HINT = "[moved: <path>] or [declined: <who> <YYYY-MM-DD> <reason>]"


@dataclass
class Diff:
    added: list[tuple[str, int, str]] = field(default_factory=list)    # (path, new line no, text)
    removed: list[tuple[str, int, str]] = field(default_factory=list)  # (path, old line no, text)


def git(repo: Path, *args: str) -> str:
    p = subprocess.run(["git", *args], cwd=repo, text=True, stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, errors="replace")
    if p.returncode:
        raise RuntimeError(p.stderr.strip() or f"git {' '.join(args)} failed")
    return p.stdout


def parse_diff(text: str) -> Diff:
    d = Diff()
    old_path = new_path = ""
    in_header = False
    old_no = new_no = 0
    for line in text.splitlines():
        if line.startswith("diff --git "):
            in_header, old_path, new_path = True, "", ""
            continue
        if in_header:
            if line.startswith("--- "):
                old_path = line[6:] if line.startswith("--- a/") else ""
            elif line.startswith("+++ "):
                new_path = line[6:] if line.startswith("+++ b/") else ""
            elif line.startswith("@@"):
                in_header = False
            else:
                continue
        if line.startswith("@@"):
            m = re.match(r"@@ -(\d+)(?:,\d+)? \+(\d+)", line)
            if m:
                old_no, new_no = int(m.group(1)), int(m.group(2))
        elif in_header:
            continue
        elif line.startswith("+"):
            d.added.append((new_path, new_no, line[1:]))
            new_no += 1
        elif line.startswith("-"):
            d.removed.append((old_path, old_no, line[1:]))
            old_no += 1
        elif line.startswith(" "):
            old_no += 1
            new_no += 1
    return d


def _strip_markup(body: str) -> str:
    body = re.sub(r"\[[^\]]*\]", " ", body)
    body = DONE_MARK.sub(" ", body)
    return re.sub(r"\W+", " ", body.lower()).strip()


LEAD_CODE = re.compile(r"^\W*([A-Z][A-Za-z0-9]*(?:[-_.][A-Za-z0-9]+)*)")


def identity(body: str) -> tuple[str, str]:
    """(leading task ID, normalized text) of a checkbox body.

    The ID is the first token of the line when it is code-shaped (LOOP-50, KVU-16h, G11,
    VB-TICK-CONTRACT); otherwise the first hyphenated upper-case ID in the opening words.
    """
    lead = ""
    m = LEAD_CODE.match(body)
    if m and re.search(r"\d", m.group(1)) or (m and "-" in m.group(1) and m.group(1).split("-")[0].isupper()):
        lead = m.group(1)
    else:
        m2 = ID_TOKEN.search(body[:120])
        lead = m2.group(0) if m2 else ""
    return lead, _strip_markup(body)


def same_task(a: tuple[str, str], b: tuple[str, str]) -> bool:
    """Same task when the normalized texts share an opening.

    Leading IDs alone are not enough: siblings such as "R18-A admission successor" and
    "R18-A successor repair" share one, and matching on it would let a deletion of one
    hide behind a flip of the other.

    A flip usually appends text (a date, a verdict) after the title, so equality of the
    first 40 characters is too strict; a shared opening of 32+ characters (or the whole
    of a shorter line, when that is at least 12) identifies the same task.
    """
    x, y = a[1], b[1]
    if not x or not y:
        return False
    n = 0
    for cx, cy in zip(x, y):
        if cx != cy:
            break
        n += 1
    return n >= 32 or (n == min(len(x), len(y)) and n >= 12)


def completion_evidence(body: str) -> str:
    m = None
    for m in DONE_MARK.finditer(body):
        pass
    return body[m.end():] if m else body


def receipt_files(root: Path) -> list[Path]:
    if not root.is_dir():
        return []
    out = []
    for dirpath, _dirs, files in os.walk(root):
        for f in files:
            if f.endswith((".FILED", ".FINAL", ".COMPLETE")):
                out.append(Path(dirpath) / f)
    return out


def cited_receipts(line: str, files: list[Path]) -> list[Path]:
    low = line.lower()
    hits = []
    for p in files:
        stem = p.name.rsplit(".", 1)[0].lower()
        # Short stems ("r1", "smoke") would match prose; a run id is long and specific.
        if len(stem) >= 12 and re.search(r"(?<![\w-])" + re.escape(stem) + r"(?![\w-])", low):
            hits.append(p)
    return hits


def receipt_state(paths: list[Path]) -> tuple[str, str]:
    def order(p: Path):
        try:
            return p.stat().st_mtime_ns
        except OSError:
            return 0
    latest = max(paths, key=order)
    run_id = latest.name.rsplit(".", 1)[0]
    if latest.name.endswith((".FINAL", ".COMPLETE")):
        return "COMPLETE", run_id
    try:
        text = latest.read_text(errors="replace")
    except OSError:
        return "UNREADABLE", run_id
    first = text.splitlines()[0] if text.splitlines() else ""
    m = re.search(r"\b(FAILED(?:-RUN)?|INCONCLUSIVE|INCOMPLETE|PARTIAL)\b|\brc\s*=\s*([1-9]\d*)", first, re.I)
    if m:
        return (m.group(1) or f"rc={m.group(2)}").upper(), run_id
    return "COMPLETE", run_id


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" \t"))


LIST_MARK = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s")


def item_text(lines: list[str] | None, lineno: int, first: str) -> tuple[str, str, int]:
    """(core, full, last line) of the item whose checkbox line is `first` at `lineno`.

    Handoff items wrap: the `✅ <date> [belief: ...]` close often sits on a continuation
    line, and dated notes go in nested sub-bullets. A line belongs to the item when it is
    indented deeper than the checkbox, is not blank, and is not itself a checkbox (that is
    its own item). CORE is the checkbox line plus its wrapped text (no nested bullets): the
    completion claim itself. FULL adds the nested non-checkbox sub-bullets.
    """
    if not lines or lineno < 1 or lineno > len(lines) or lines[lineno - 1] != first:
        return first, first, lineno
    base = _indent(first)
    core, full, last, in_sub = [first], [first], lineno, False
    for i in range(lineno, len(lines)):
        nxt = lines[i]
        if not nxt.strip() or _indent(nxt) <= base or TICK.match(nxt):
            break
        if LIST_MARK.match(nxt):
            in_sub = True
        if not in_sub:
            core.append(nxt.strip())
        full.append(nxt.strip())
        last = i + 1
    return " ".join(core), " ".join(full), last


def check(diff: Diff, receipts_root: Path | None, reader=None) -> list[tuple[str, str]]:
    """Return [(key, message)]. The key is stable across merge parents (path + line text).

    `reader(path)` returns the new file's lines so a wrapped item is read whole."""
    # Pair every removed checkbox with at most one added checkbox, ONE-TO-ONE, so one
    # added box can never account for two removed ones. Pass 1 pairs by shared opening
    # text (moves and flips keep the title); pass 2 pairs the rest by leading task ID
    # (an open task whose wording was edited in place).
    rem = [(i, path, no, text, TICK.match(text)) for i, (path, no, text) in enumerate(diff.removed)]
    rem = [(i, path, no, text, t.group(1).lower(), identity(t.group(2))) for i, path, no, text, t in rem if t]
    add = [(j, path, no, text, TICK.match(text)) for j, (path, no, text) in enumerate(diff.added)]
    add = [(j, path, no, text, t.group(1).lower(), identity(t.group(2))) for j, path, no, text, t in add if t]
    pair_of_removed: dict[int, tuple] = {}
    pair_of_added: dict[int, tuple] = {}
    for rule in ("text", "lead"):
        for r in rem:
            if r[0] in pair_of_removed:
                continue
            for a in add:
                if a[0] in pair_of_added:
                    continue
                ok = same_task(r[5], a[5]) if rule == "text" else (r[5][0] and r[5][0] == a[5][0])
                if ok:
                    pair_of_removed[r[0]] = a
                    pair_of_added[a[0]] = r
                    break
    removed_open = [(path, no, text) for i, path, no, text, state, _id in rem
                    if state == " " and i not in pair_of_removed]
    added_any: list[tuple[str, int, str]] = list(diff.added)
    already_ticked = {a[0] for a in add if a[0] in pair_of_added and pair_of_added[a[0]][4] == "x"}
    added_index = {(path, no, text): j for j, path, no, text, _s, _i in add}

    receipt_cache: list[Path] | None = None
    errors: list[tuple[str, str]] = []
    for path, no, text in diff.added:
        t = TICK.match(text)
        if not t or t.group(1).lower() != "x":
            continue
        if added_index.get((path, no, text)) in already_ticked:
            continue                       # a fold/move or an edit of an existing tick
        core, whole, last = item_text(reader(path) if reader else None, no, text)
        body = TICK.match(whole).group(2)
        core_body = TICK.match(core).group(2)
        where = f"{path}:{no}" + (f" (item through line {last})" if last != no else "")
        key = f"{path}\0{text.strip()}"
        tags = TAG_ANY.findall(body)
        if DECLINED.search(body):
            errors.append((key, f"{where}: a declined task is never [x]; write it as a non-checkbox "
                                f"line carrying [declined: <who> <YYYY-MM-DD> <reason>]"))
        if not tags:
            errors.append((key, f"{where}: new [x] tick has no belief tag; add {TAG_HINT} "
                                f"to line {last}, after its ✅ date"))
        for kind, value in tags:
            value = value.strip()
            if kind.lower() == "belief" and not TAG_BELIEF_OK.match(value):
                errors.append((key, f"{where}: malformed tag [belief: {value}]; use [belief: clm_<id>], "
                                    f"[belief: cc] or [no-belief: <reason>]"))
            if kind.lower() == "no-belief" and not value:
                errors.append((key, f"{where}: [no-belief:] needs a reason, e.g. [no-belief: not-a-result]"))
        if UNKNOWN.search(completion_evidence(core_body)):
            errors.append((key, f"{where}: tick text states unknown/inconclusive completion; leave the box "
                                f"[ ] and add a checkpoint child task (SESSION_LIFECYCLE.md -> Two axioms)"))
        beliefs = [v.strip() for k, v in tags if k.lower() == "belief"]
        if "cc" in beliefs and not (SHA.search(body) or GIT_PATH.search(body)):
            errors.append((key, f"{where}: [belief: cc] tick needs a commit SHA or a repository path "
                                f"on this line (the committed conclusion's evidence)"))
        if beliefs and receipts_root is not None:
            if receipt_cache is None:
                receipt_cache = receipt_files(receipts_root)
            hits = cited_receipts(body, receipt_cache)
            if hits:
                state, run_id = receipt_state(hits)
                if state != "COMPLETE" and not ACK.search(body):
                    errors.append((key, f"{where}: cited run {run_id} has receipt {state}; reopen the box or "
                                        f"add [receipt-ack: {run_id} {state} — <reason>] to this line"))

    for path, no, text in removed_open:
        t = TICK.match(text)
        ident = identity(t.group(2))
        marked = False
        for p2, _n, new in added_any:
            if (MOVED.search(new) or DECLINED.search(new)) and same_task(ident, identity(re.sub(r"^\s*(?:[-*+]|\d+[.)])?\s*(?:\[[ xX]\]\s*)?", "", new))):
                marked = True
                break
            # A retirement banner: one non-checkbox `[moved: <path>]` line added to the
            # same file accounts for every open task that file drops in this commit.
            if p2 == path and MOVED.search(new) and not TICK.match(new):
                marked = True
                break
        if not marked:
            key = f"{path}\0-{text.strip()}"
            short = text.strip()[:90]
            errors.append((key, f"{path}:{no} (old line): open task removed without being re-added; "
                                f"put {DEL_HINT} on a line naming it: {short}"))
    return errors


def _diff(repo: Path, base: str, target: str | None) -> Diff:
    args = ["diff", "--no-ext-diff", "--no-color", "--no-renames", "--unified=0"]
    if target is None:
        args += ["--cached", base]
    else:
        args += [base, target]
    return parse_diff(git(repo, *args, "--", SCOPE))


def make_reader(repo: Path, target: str | None):
    cache: dict[str, list[str] | None] = {}

    def read(path: str) -> list[str] | None:
        if path not in cache:
            spec = f":{path}" if target is None else f"{target}:{path}"
            try:
                cache[path] = git(repo, "show", spec).splitlines()
            except RuntimeError:
                cache[path] = None
        return cache[path]
    return read


def judge(repo: Path, parents: list[str], target: str | None, receipts: Path | None) -> list[str]:
    """Violations new against EVERY parent (one parent for an ordinary commit)."""
    reader = make_reader(repo, target)
    per_parent = [dict(check(_diff(repo, p, target), receipts, reader)) for p in parents]
    keys = set(per_parent[0])
    for other in per_parent[1:]:
        keys &= set(other)
    seen, out = set(), []
    for key, msg in check(_diff(repo, parents[0], target), receipts, reader):
        if key in keys and msg not in seen:
            seen.add(msg)
            out.append(msg)
    return out


EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"


def staged_parents(repo: Path) -> list[str]:
    try:
        head = git(repo, "rev-parse", "-q", "--verify", "HEAD").strip()
    except RuntimeError:
        return [EMPTY_TREE]
    parents = [head]
    try:
        mh = git(repo, "rev-parse", "--git-path", "MERGE_HEAD").strip()
        mp = Path(mh) if os.path.isabs(mh) else repo / mh
        if mp.is_file():
            parents += [l.strip() for l in mp.read_text().splitlines() if l.strip()]
    except (RuntimeError, OSError):
        pass
    return parents


def commit_parents(repo: Path, sha: str) -> list[str]:
    parts = git(repo, "rev-list", "--parents", "-n", "1", sha).split()
    return parts[1:] or [EMPTY_TREE]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", type=Path, default=None)
    ap.add_argument("--range", dest="commit_range", help="replay committed changes in A..B as one diff")
    ap.add_argument("--commit", help="replay one commit exactly as the hook judged it")
    ap.add_argument("--receipts", type=Path, default=DEFAULT_RECEIPTS)
    ap.add_argument("--no-receipts", action="store_true", help="skip the host-local receipt rule (T6)")
    ap.add_argument("--report", action="store_true", help="print a one-line summary")
    args = ap.parse_args()
    try:
        repo = args.repo or Path(git(Path.cwd(), "rev-parse", "--show-toplevel").strip())
        receipts = None if args.no_receipts else args.receipts
        if args.commit:
            errors = judge(repo, commit_parents(repo, args.commit), args.commit, receipts)
        elif args.commit_range:
            base, _, tip = args.commit_range.partition("..")
            errors = judge(repo, [base], tip or "HEAD", receipts)
        else:
            errors = judge(repo, staged_parents(repo), None, receipts)
    except (OSError, RuntimeError) as exc:
        print(f"belief-capture: cannot verify: {exc}", file=sys.stderr)
        return 2
    for e in errors:
        print(f"belief-capture: {e}", file=sys.stderr)
    if errors:
        print("belief-capture: BLOCKED (LOOP-50, operator 2026-11-02). Folds that move boxes verbatim pass; "
              "see scripts/handoffs/belief_capture_check.py for the rules.", file=sys.stderr)
    if args.report:
        print(f"belief-capture: {'blocked' if errors else 'clear'}; violations={len(errors)}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
