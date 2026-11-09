#!/usr/bin/env python3
"""Reconstruct a handoff progress timeline from git history + in-file dates.

Emits ``data/handoff_timeline.json`` for the dashboard hub's
``/api/handoff_timeline`` endpoint. Two derived views:

* **task-level throughput** — checkbox completions per ISO week (the headline
  chart), and
* **handoff lifecycle** — cumulative active/completed/archived counts over time
  plus created/completed-per-week.

Historical seeding (why this is not just ``git log``)
-----------------------------------------------------
This repo's ``handoffs/`` git history begins at the 2026-02-25 monorepo split,
which bulk-imported ~72 archived + ~10 completed handoffs and hundreds of
already-``[x]`` tasks in **one commit**. Trusting commit dates would pile all of
that onto 2026-W09 (a false spike) and truncate the timeline at the split.

So we prefer **self-reported dates** over the git-commit date, per event:

* a task completion is dated by the ``✅ YYYY-MM-DD`` (or any ISO date) on the
  checkbox line; else, for a bulk-imported file, by the file's ``**Updated**`` /
  ``**Created**``; else by the commit that first shows it checked;
* a handoff's creation is dated by its ``**Created**`` field (else git first-seen);
* a bulk-imported completed/archived handoff's terminal date is its
  ``**Updated**`` / ``**Created**`` (else the import commit).

The cumulative ``series`` is then rebuilt from each handoff's
(created → terminal) interval, so it extends back to true project origin
(Jan 2026) rather than starting flat at the import.

Design: one ``git log -M -p --reverse`` pass over ``handoffs/`` (~1s over full
history); full rebuild every run (the post-commit hook runs it detached). Task
identity follows renames; a task completes once, at its first checked appearance.

The same pass also emits ``file_activity`` — the last commit day (``YYYY-MM-DD``)
that touched each handoff, keyed by ``state/stem`` — which the board uses as a
recency signal. Note: ``git log -p`` shows no diff for merge commits (no ``-m``),
so a handoff last touched only by a merge is dated by its prior non-merge commit;
in practice such handoffs are also flagged git-dirty on pull and covered there.

The same pass also emits ``next_action_repoints`` — every commit in which an index row's
``Next action`` cell changed, with the PREVIOUS text and a ``reason`` (RTG-46, adapted from
Prove2Me's mandatory re-link reason, intake-1299#record). Before this, re-pointing a row
overwrote the cell with no trace, so why the previous target was abandoned was lost and the
next session could re-walk a rejected path at full price. The reason lives HERE, in the
sidecar, and never in the row (status and history never go in a row —
``docs/guides/agent-workflows/handoff-index-authoring.md``). Its source, in order:

* a ``Repoint-Reason: <ROW-ID>: <why>`` line in the commit message (row-specific);
* else the commit subject (``reason_source: "commit_subject"`` — commit-level, weaker).

A row that moves between index files with an unchanged ``Next action`` is a re-home, not a
re-point, and is not reported; a row removed without a replacement is a deletion, likewise.

Run: ``python3 scripts/handoffs/build_handoff_timeline.py``  (``--repo`` to override)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from difflib import SequenceMatcher
from pathlib import Path

STATES = ("active", "blocked", "completed", "archived")
_TERMINAL = ("completed", "archived")

# ``\x00<sha> <author-iso>[\x1f<Repoint-Reason trailers>\x1f<D9-ack trailers>]`` (_LOG_FORMAT).
# The trailer fields are optional so a bare ``\x00<sha> <ts>`` header still parses.
_COMMIT_RE = re.compile(r"^\x00([0-9a-f]{7,40}) ([^\x1f]+?)(?:\x1f([^\x1f]*)\x1f(.*))?$")
_LOG_FORMAT = ("--format=%x00%H %aI"
               "%x1f%(trailers:key=Repoint-Reason,valueonly=true,separator=%x3B)"
               "%x1f%(trailers:key=D9-ack,valueonly=true,separator=%x3B)")
_DIFF_RE = re.compile(r"^diff --git a/(.+) b/(.+)$")
_RENAME_FROM_RE = re.compile(r"^rename from (.+)$")
_RENAME_TO_RE = re.compile(r"^rename to (.+)$")
_ROLLUP_RE = re.compile(r"\[roll-up\]", re.I)
# ONE box grammar: identical to dashboard/handoff_parser.BOX_MARKER and to the graph's
# backlog_row_check._boxes (bullet OR numbered item, one space, the box). Copied, not
# imported, because this script runs without the dashboard package on its path; a test
# pins the two strings equal.
_BOX_MARKER = r"(?:[-*+]|\d+[.)]) \[([ xX])\]"
_ADDED_CHECKBOX_RE = re.compile(rf"^\+[ \t]*{_BOX_MARKER}[ \t]*(.*)$")
_REMOVED_CHECKBOX_RE = re.compile(rf"^-[ \t]*{_BOX_MARKER}[ \t]*(.*)$")
# An added ``> **Folded into …`` banner: the block is a fold stub, not a completed handoff.
_FOLDED_BANNER_ADD_RE = re.compile(r"^\+>\s*\*\*Folded into\b", re.I)
_ADDED_META_RE = re.compile(r"^\+\s*\*\*(Created|Updated|Date)\*\*:\s*(.*)$", re.I)
_PATH_RE = re.compile(r"^handoffs/(active|blocked|completed|archived)/(.+)\.md$")
_DATE_RE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
_CHECK_DATE_RE = re.compile(r"✅\s*(\d{4}-\d{2}-\d{2})")

_NON_HANDOFF_STEMS = {"BLOCKED", "README"}
# Routers (the master index, CURRENT-CAMPAIGN and every ``*-index`` file, current or retired)
# list handoffs rather than being one. They keep their ``file_activity`` (the board dates their
# cards) but are excluded from the handoff lifecycle, the task flow and the open-box stock, so
# the charts count the same handoff set as the graph and the backlog panel.
_ROUTER_STEMS = {"CURRENT-CAMPAIGN"}


def _is_router(stem: str) -> bool:
    return stem in _ROUTER_STEMS or stem.endswith("-index")


def _commit_flags(repoint: str | None, ack: str | None) -> dict:
    """``{"fold", "refactor"}`` from a commit's trailers, as ``server._is_fold_commit``.

    ``fold``: a ``Repoint-Reason:`` trailer -- a readiness-neutral migration: boxes it moves
    are moves, and beyond in-place ticks nothing it adds counts as filed. ``refactor``: a
    ``D9-ack:`` trailer naming the backlog refactor -- only turns on moved-box pairing.
    """
    return {"fold": bool((repoint or "").strip()),
            "refactor": "backlog refactor" in (ack or "").lower()}

# Index-row lines in a diff: `-| INF-06 | … |` / `+| INF-06 | … |`. Same id shape and
# unescaped-pipe split as index_state.py's thin-row parser.
_ROW_LINE_RE = re.compile(r"^([+-])(\|\s*([A-Z]{3}-\d+)\s*\|.*)$")
_CELL_SPLIT_RE = re.compile(r"(?<!\\)\|")
_REPOINT_TRAILER_RE = re.compile(r"^\s*Repoint-Reason:\s*([A-Z]{3}-\d+)\s*[:—–-]\s*(.+?)\s*$")


def _repo_root() -> Path:
    # scripts/handoffs/build_handoff_timeline.py -> parents[2] == repo root
    return Path(__file__).resolve().parents[2]


def _iso_date(value: str | None) -> str | None:
    """First valid ISO ``YYYY-MM-DD`` in ``value`` (values carry trailing prose)."""
    if not value:
        return None
    m = _DATE_RE.search(value)
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3))).isoformat()
    except ValueError:
        return None


def _inline_task_date(line_text: str) -> str | None:
    """Completion date carried on a checkbox line: prefer the ``✅ <date>`` one."""
    m = _CHECK_DATE_RE.search(line_text)
    if m:
        return _iso_date(m.group(1))
    return _iso_date(line_text)


def _task_key(text: str) -> str:
    """Stable-ish identity for a checkbox task line.

    Strip emphasis, cut at the first ``✅``/em-dash decoration, collapse
    whitespace, lowercase, truncate. Colons are preserved so ``S1: foo`` stays
    distinct from ``S2: foo``. A flip in this repo appends ``✅ <date> — notes``,
    so full-text pairing would fail — the prefix is the stable part.
    """
    t = re.sub(r"[*_`]+", "", text)
    t = re.split(r"✅|—|–|\bDONE\b", t, maxsplit=1)[0]
    t = re.sub(r"\s+", " ", t).strip().lower()
    return t[:60]


def _path_state_stem(path: str) -> tuple[str, str] | None:
    m = _PATH_RE.match(path)
    if not m:
        return None
    state, stem = m.group(1), m.group(2)
    if stem in _NON_HANDOFF_STEMS or "/" in stem:  # index files / nested dirs
        return None
    return state, stem


def _iso_week(day: str) -> str:
    y, w, _ = date.fromisoformat(day).isocalendar()
    return f"{y}-W{w:02d}"


def _run_git_log(repo: Path, first_parent: bool = False, no_merges: bool = False) -> str:
    # first_parent: follow the main line only, and show merges as a diff against
    # their first parent. Plain ``git log -p`` prints NO diff for merge commits, so a
    # box change that landed via a merge is invisible and a replayed stock drifts
    # from the real tree (measured: 39 boxes / 26 files on 2026-10-24).
    cmd = [
        "git", "-C", str(repo), "log", "--reverse", "-M", "--no-color",
        *(["--first-parent"] if first_parent else []),
        *(["--no-merges"] if no_merges else []),
        _LOG_FORMAT, "-p", "--", "handoffs/",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True,
                          errors="replace", check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"git log failed: {proc.stderr.strip()[:400]}")
    return proc.stdout


def _run_git_messages(repo: Path) -> dict[str, str]:
    """``sha -> full commit message`` for every commit touching ``handoffs/``."""
    cmd = ["git", "-C", str(repo), "log", "--no-color", "--format=%x00%H%x1f%B",
           "--", "handoffs/"]
    proc = subprocess.run(cmd, capture_output=True, text=True,
                          errors="replace", check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"git log (messages) failed: {proc.stderr.strip()[:400]}")
    out = {}
    for chunk in proc.stdout.split("\x00"):
        if "\x1f" in chunk:
            sha, msg = chunk.split("\x1f", 1)
            out[sha.strip()] = msg.strip()
    return out


def repoints_for_commit(sha: str, day: str, blocks, message: str) -> list[dict]:
    """Re-pointed rows in one commit: same id removed and re-added with a different
    ``Next action``. Pairing is commit-wide so a row moved between indices still pairs."""
    removed: dict[str, tuple[str, str]] = {}
    added: dict[str, tuple[str, str]] = {}
    for blk in blocks:
        name = Path(blk.new_path).name
        for rid, act in blk.rows_removed.items():
            removed[rid] = (act, Path(blk.old_path).name)
        for rid, act in blk.rows_added.items():
            added[rid] = (act, name)
    if not removed or not added:
        return []
    trailers = {}
    for line in (message or "").splitlines():
        m = _REPOINT_TRAILER_RE.match(line)
        if m:
            trailers[m.group(1)] = m.group(2)
    subject = (message or "").splitlines()[0].strip() if message else ""
    events = []
    for rid in sorted(set(removed) & set(added)):
        (old, _), (new, index) = removed[rid], added[rid]
        if " ".join(old.split()) == " ".join(new.split()):
            continue
        reason, source = ((trailers[rid], "trailer") if rid in trailers
                          else (subject or None, "commit_subject" if subject else None))
        events.append({"id": rid, "date": day, "commit": sha[:12], "index": index,
                       "from": old, "to": new, "reason": reason,
                       "reason_source": source})
    return events


def _head_sha(repo: Path) -> str | None:
    proc = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"],
                          capture_output=True, text=True, check=False)
    return (proc.stdout.strip() or None) if proc.returncode == 0 else None


class _Block:
    """One ``diff --git`` block within a commit."""

    __slots__ = ("old_path", "new_path", "is_new", "is_deleted", "rename_from",
                 "rename_to", "checkboxes", "removed_checkboxes", "folded_banner",
                 "created_date", "updated_date", "rows_removed", "rows_added")

    def __init__(self, old_path: str, new_path: str) -> None:
        self.old_path = old_path
        self.new_path = new_path
        self.is_new = False
        self.is_deleted = False
        self.rename_from: str | None = None
        self.rename_to: str | None = None
        # each added checkbox line: (mark ' '|'x', task text, inline date)
        self.checkboxes: list[tuple[str, str, str | None]] = []
        # each removed checkbox line: (mark, task text) -- pairs fold moves across files
        self.removed_checkboxes: list[tuple[str, str]] = []
        self.folded_banner = False             # block adds a ``> **Folded into`` banner
        self.created_date: str | None = None   # from +**Created** (new-file adds)
        self.updated_date: str | None = None   # from +**Updated**
        # index rows (index files only): row id -> Next action cell
        self.rows_removed: dict[str, str] = {}
        self.rows_added: dict[str, str] = {}


def _is_index_path(path: str) -> bool:
    return path.startswith("handoffs/") and path.endswith("index.md")


def _row_next_action(row: str) -> str | None:
    """``Next action`` cell of a 5-column thin row, else None (malformed/legacy rows)."""
    cells = [c.strip() for c in _CELL_SPLIT_RE.split(row.strip())]
    if cells and cells[0] == "":
        cells = cells[1:-1]
    return cells[3] if len(cells) == 5 else None


def _parse_commits(log_text: str, flags: dict | None = None):
    """Return ``[(sha, iso_ts, [blocks]), ...]`` in chronological order.

    ``flags`` (optional) is filled with ``{sha: {"fold", "refactor"}}`` from the header's
    trailer fields (see ``_commit_flags``)."""
    sha = ts = None
    blocks: list[_Block] = []
    current: _Block | None = None
    results = []
    for line in log_text.splitlines():
        mcommit = _COMMIT_RE.match(line)
        if mcommit:
            if sha is not None:
                results.append((sha, ts, blocks))
            sha, ts = mcommit.group(1), mcommit.group(2).strip()
            if flags is not None:
                flags[sha] = _commit_flags(mcommit.group(3), mcommit.group(4))
            blocks = []
            current = None
            continue
        mdiff = _DIFF_RE.match(line)
        if mdiff:
            current = _Block(mdiff.group(1), mdiff.group(2))
            blocks.append(current)
            continue
        if current is None:
            continue
        if line.startswith("new file mode"):
            current.is_new = True
        elif line.startswith("deleted file mode"):
            current.is_deleted = True
            continue
        mrf = _RENAME_FROM_RE.match(line)
        if mrf:
            current.rename_from = mrf.group(1)
            continue
        mrt = _RENAME_TO_RE.match(line)
        if mrt:
            current.rename_to = mrt.group(1)
            continue
        mmeta = _ADDED_META_RE.match(line)
        if mmeta:
            field, val = mmeta.group(1).lower(), _iso_date(mmeta.group(2))
            if val:
                if field in ("created", "date") and not current.created_date:
                    current.created_date = val
                elif field == "updated" and not current.updated_date:
                    current.updated_date = val
            continue
        mrow = _ROW_LINE_RE.match(line)
        if mrow and _is_index_path(current.new_path):
            action = _row_next_action(mrow.group(2))
            if action is not None:
                side = current.rows_added if mrow.group(1) == "+" else current.rows_removed
                side[mrow.group(3)] = action
            continue
        mac = _ADDED_CHECKBOX_RE.match(line)
        if mac:
            current.checkboxes.append(
                (mac.group(1), mac.group(2), _inline_task_date(mac.group(2))))
            continue
        mrc = _REMOVED_CHECKBOX_RE.match(line)
        if mrc:
            current.removed_checkboxes.append((mrc.group(1), mrc.group(2)))
            continue
        if _FOLDED_BANNER_ADD_RE.match(line):
            current.folded_banner = True
    if sha is not None:
        results.append((sha, ts, blocks))
    return results


# --------------------------------------------------------------------------
# Daily open-box flow (operator-approved refinement, 2026-10-24)
#
# ``tasks_weekly`` counts every added ``- [ ]`` line as newly filed and never sees
# removals, so rewording an open box looked like a new filing and the backlog
# could not fall. ``daily_flow`` replays the SAME ``git log -p`` text but tracks the
# per-file open-box STOCK, and pairs removed lines with added lines per commit.
# One row per calendar day, zero-filled, ending today (counts are boxes):
#   open_stock            open ``[ ]`` boxes in handoffs/active+blocked at end of day
#   ticked                removed open box matched to an added ``[x]`` (same text or
#                         similarity >= _SIM)
#   new_open              added open box with NO removed open partner (really new)
#   reworded              added open box paired with a removed open box (net zero)
#   born_ticked           added ``[x]`` with no removed partner (filed already done)
#   removed_open          open boxes deleted unmatched (line removed, or the whole
#                         handoff deleted from active/blocked)
#   closed_by_completion  open boxes still open in a handoff the day it moved from
#                         active/blocked to completed/ or archived/
#   handoffs_completed / handoffs_archived   handoffs moved to that state that day
# Pairing is commit-wide and one-to-one.
# --------------------------------------------------------------------------
_SIM = 0.75
_PAIR_LIMIT = 40000          # skip O(n*m) similarity on bulk-rewrite commits
_LIVE = ("active", "blocked")
_ANY_CHECKBOX_RE = re.compile(rf"^([+-])[ \t]*{_BOX_MARKER}[ \t]*(.*)$")
_FLOW_FIELDS = ("ticked", "new_open", "reworded", "born_ticked", "removed_open",
                "closed_by_completion", "handoffs_completed", "handoffs_archived",
                "moved", "handoffs_folded", "reworded_done", "declined", "reopened",
                "fold_added", "fold_removed", "fold_moved", "commits")
# A box ticked with a declined/won't-fix marker left the backlog without being done.
_DECLINED_RE = re.compile(r"\bdeclined\b|\bwon'?t[- ]?fix\b|\bwontfix\b", re.I)


def _norm_text(text: str) -> str:
    t = re.sub(r"[*_`]+", "", text)
    t = re.split(r"✅|—|–|\bDONE\b", t, maxsplit=1)[0]
    return re.sub(r"\s+", " ", t).strip().lower()[:200]


def _similar(a: str, b: str) -> bool:
    if a == b:
        return True
    if not a or not b:
        return False
    sm = SequenceMatcher(None, a, b, autojunk=False)
    return (sm.real_quick_ratio() >= _SIM and sm.quick_ratio() >= _SIM
            and sm.ratio() >= _SIM)


def _pair_commit(removed: list, added: list, flow: Counter) -> None:
    """Classify one commit's removed/added boxes, consumed one-to-one: exact-text pairs
    first, then similarity pairs. Removed entries are ``[is_open, text]``, added entries
    ``[is_open, text, declined]``. Open -> ``[x]`` is a tick (a ``declined`` one is not a
    closure), ``[x]`` -> open a reopen, open -> open and ``[x]`` -> ``[x]`` are edits and
    count as neither."""
    r_used = [False] * len(removed)
    a_done = [False] * len(added)
    # An open box is the likelier origin of any added line, so it pairs before a done one.
    order = sorted(range(len(removed)), key=lambda ri: not removed[ri][0])
    for exact in (True, False):
        if not exact and len(removed) * len(added) > _PAIR_LIMIT:
            break
        for ai, entry in enumerate(added):
            a_open, txt = entry[0], entry[1]
            if a_done[ai]:
                continue
            for ri in order:
                r_open, r_txt = removed[ri]
                if r_used[ri]:
                    continue
                if (r_txt == txt) if exact else _similar(r_txt, txt):
                    r_used[ri] = a_done[ai] = True
                    if not r_open:
                        flow["reopened" if a_open else "reworded_done"] += 1
                    elif a_open:
                        flow["reworded"] += 1
                    else:
                        flow["declined" if entry[2:3] == [True] else "ticked"] += 1
                    break
    for ai, entry in enumerate(added):
        if not a_done[ai]:
            flow["new_open" if entry[0] else "born_ticked"] += 1
    flow["removed_open"] += sum(1 for ri, (r_open, _t) in enumerate(removed)
                                if r_open and not r_used[ri])


def _pair_moves(removed: list, added: list, flow: Counter | None = None) -> tuple[list, list, int]:
    """A box removed in one file and added in ANOTHER with the same normalised text is the
    same box in a new place, in EVERY commit. Same state = MOVED (neither filed nor closed).
    A state change carried by the move still counts: open -> ``[x]`` is a tick (or a decline)
    and ``[x]`` -> open a reopen, recorded in ``flow`` when given.
    Removed entries are ``[is_open, text, path]``, added ``[is_open, text, path[, declined]]``;
    returns the unpaired rest and the same-state move count."""
    pool: dict[str, list[int]] = {}
    for ri, (_o, txt, _p) in enumerate(removed):
        pool.setdefault(txt, []).append(ri)
    used: set[int] = set()
    rest_added, moved = [], 0
    for entry in added:
        a_open, txt, path = entry[0], entry[1], entry[2]
        hit = next((ri for ri in pool.get(txt, ()) if ri not in used and removed[ri][2] != path),
                   None)
        if hit is None:
            rest_added.append(entry)
            continue
        used.add(hit)
        r_open = removed[hit][0]
        if r_open == a_open:
            moved += 1
        elif flow is not None:
            if r_open:
                flow["declined" if entry[3:4] == [True] else "ticked"] += 1
            else:
                flow["reopened"] += 1
    rest_removed = [r for ri, r in enumerate(removed) if ri not in used]
    return rest_removed, rest_added, moved


def _replay(log_text: str, *, monotonic: bool = False) -> tuple[dict, dict, dict]:
    """One pass over ``git log -M -p`` text. Returns ``(flows, stock_eod, meta)`` by day.

    ``monotonic``: a replay of the first-parent line dates a commit no earlier than the one
    before it, because a rebased commit's author date can precede what already landed and
    must not rewrite an earlier end-of-day stock.
    """
    counts: dict[str, int] = {}      # state/stem -> open boxes (every state tracked,
    state_of: dict[str, str] = {}    # so a move back into active restores its stock)
    days: dict[str, Counter] = {}
    stock_eod: dict[str, int] = {}
    meta: dict[str, dict] = {}
    st: dict = {"day": None, "sha": None, "blocks": [], "cur": None, "hunk": False,
                "seen": False, "fold": False, "refactor": False}
    last_day: list = [None]

    def ss(path: str):
        r = _path_state_stem(path)
        return None if r is None or _is_router(r[1]) else r

    def flush() -> None:
        day = st["day"]
        if not st["seen"] or day is None:
            return
        flow = days.setdefault(day, Counter())
        info = meta.setdefault(day, {"touched": set(), "folds": []})
        fold = st["fold"]
        removed: list = []
        added: list = []
        handoff_touched = False
        for b in st["blocks"]:
            new_ss = ss(b["new"])
            old_ss = ss(b["rename_from"] or b["old"])
            if new_ss is None and old_ss is None:
                continue
            handoff_touched = True
            if not fold:
                info["touched"].add(b["new"])
            okey = f"{old_ss[0]}/{old_ss[1]}" if old_ss else None
            nkey = f"{new_ss[0]}/{new_ss[1]}" if new_ss else None
            if b["deleted"]:
                if okey is not None:
                    if old_ss[0] in _LIVE:      # its boxes may have moved into another file
                        removed.extend([is_open, _norm_text(txt), okey]
                                       for sign, is_open, txt in b["boxes"] if sign == "-")
                    counts.pop(okey, None)
                    state_of.pop(okey, None)
                continue
            if nkey is None:
                continue
            live_touch = new_ss[0] in _LIVE or bool(old_ss and old_ss[0] in _LIVE)
            before = counts.get(okey, 0) if okey else 0
            if okey and okey != nkey:
                counts[nkey] = counts.pop(okey, 0)
                state_of.pop(okey, None)
            counts.setdefault(nkey, 0)
            state_of[nkey] = new_ss[0]
            d_open = 0
            for sign, is_open, txt in b["boxes"]:
                if is_open:
                    d_open += 1 if sign == "+" else -1
                if live_touch:
                    if sign == "+":
                        added.append([is_open, _norm_text(txt), nkey,
                                      bool(_DECLINED_RE.search(txt))])
                    else:
                        removed.append([is_open, _norm_text(txt), nkey])
            counts[nkey] = max(0, counts[nkey] + d_open)
            if old_ss and old_ss[0] in _LIVE and new_ss[0] in _TERMINAL:
                if b["folded"]:
                    flow["handoffs_folded"] += 1
                    flow["fold_removed"] += counts[nkey]
                else:
                    flow["closed_by_completion"] += counts[nkey]
                    flow["handoffs_completed" if new_ss[0] == "completed"
                         else "handoffs_archived"] += 1
            elif old_ss and old_ss[0] in _TERMINAL and new_ss[0] in _LIVE:
                flow["reopened"] += before
        removed, added, moved = _pair_moves(removed, added, flow)
        flow["moved"] += moved
        if handoff_touched and not fold:
            flow["commits"] += 1
        if fold or moved:
            if handoff_touched:
                info["folds"].append((st["sha"] or "")[:12])
        if fold or st["refactor"]:
            flow["fold_moved"] += moved
        if fold:
            # Readiness-neutral migration: only an in-place open -> [x] flip is a closure.
            # What else it adds or drops is NOT filing or removal, but it does move the
            # stock, so it is recorded separately for the reconciliation.
            for entry in added:
                a_open, txt, path = entry[0], entry[1], entry[2]
                if a_open:
                    flow["fold_added"] += 1
                    continue
                hit = next((r for r in removed if r[0] and r[2] == path
                            and (r[1] == txt or _similar(r[1], txt))), None)
                if hit is not None:
                    removed.remove(hit)
                    flow["declined" if entry[3] else "ticked"] += 1
            flow["fold_removed"] += sum(1 for r in removed if r[0])
        else:
            _pair_commit([r[:2] for r in removed], [[a[0], a[1], a[3]] for a in added], flow)
        stock_eod[day] = sum(n for k, n in counts.items() if state_of.get(k) in _LIVE)

    for line in log_text.splitlines():
        mc = _COMMIT_RE.match(line)
        if mc:
            flush()
            try:
                day = datetime.fromisoformat(mc.group(2).strip()).date().isoformat()
            except ValueError:
                day = None
            if monotonic and day is not None:
                if last_day[0] is not None and day < last_day[0]:
                    day = last_day[0]
                last_day[0] = day
            st.update(day=day, sha=mc.group(1), blocks=[], cur=None, hunk=False, seen=True,
                      **_commit_flags(mc.group(3), mc.group(4)))
            continue
        md = _DIFF_RE.match(line)
        if md:
            st["cur"] = {"old": md.group(1), "new": md.group(2), "deleted": False,
                         "rename_from": None, "boxes": [], "folded": False}
            st["blocks"].append(st["cur"])
            st["hunk"] = False
            continue
        cur = st["cur"]
        if cur is None:
            continue
        if line.startswith("@@"):
            st["hunk"] = True
            continue
        if not st["hunk"]:
            if line.startswith("deleted file mode"):
                cur["deleted"] = True
            else:
                mrf = _RENAME_FROM_RE.match(line)
                if mrf:
                    cur["rename_from"] = mrf.group(1)
            continue
        mb = _ANY_CHECKBOX_RE.match(line)
        if mb:
            if not _ROLLUP_RE.search(mb.group(3)):   # roll-up parents are never tasks
                cur["boxes"].append((mb.group(1), mb.group(2) == " ", mb.group(3)))
        elif _FOLDED_BANNER_ADD_RE.match(line):
            cur["folded"] = True
    flush()
    return days, stock_eod, meta


def build_daily_flow(log_text: str, today: str | None = None,
                     flow_log: str | None = None) -> list[dict]:
    """Daily open-box stock + flows; THE counter (the hub's flow panel reads this output).

    ``log_text`` (``--first-parent``) replays end-of-day stock on the main line. ``flow_log``
    (``--no-merges``) supplies the flows, so each commit counts on its own date with its own
    trailers rather than lumping a merged lane onto the merge day. Without ``flow_log`` the
    flows come from ``log_text``.

    Every commit pairs boxes across files (a move is never a filing). A fold commit
    (``Repoint-Reason:``) is readiness-neutral: beyond moves only an in-place open -> ``[x]``
    flip counts; what else it adds or drops lands in ``fold_added`` / ``fold_removed``.

    Each row also carries the derived totals the panel shows, defined once here:
    ``closed`` = ticked + closed_by_completion; ``filed`` = new_open + reopened;
    ``removed`` = removed_open + declined; ``net`` = filed - closed - removed.
    """
    stock_days, stock_eod, stock_meta = _replay(log_text, monotonic=True)
    if flow_log is None:
        days, meta = stock_days, stock_meta
    else:
        days, _unused, meta = _replay(flow_log)
    if not stock_eod and not days:
        return []
    today = today or datetime.now(timezone.utc).date().isoformat()
    seen = set(stock_eod) | set(days)
    d = date.fromisoformat(min(seen))
    end = date.fromisoformat(max(max(seen), today))
    out: list[dict] = []
    carry = 0
    while d <= end:
        ds = d.isoformat()
        carry = stock_eod.get(ds, carry)
        c = days.get(ds, Counter())
        row: dict = {"date": ds, "open_stock": carry, **{f: c.get(f, 0) for f in _FLOW_FIELDS}}
        row["closed"] = row["ticked"] + row["closed_by_completion"]
        row["filed"] = row["new_open"] + row["reopened"]
        row["removed"] = row["removed_open"] + row["declined"]
        row["net"] = row["filed"] - row["closed"] - row["removed"]
        info = meta.get(ds) or {}
        row["touched"] = sorted(info.get("touched", ()))
        row["fold_commits"] = list(info.get("folds", ()))
        out.append(row)
        d += timedelta(days=1)
    return out


def refactor_markers(daily: list[dict]) -> list[dict]:
    """One marker per day on which fold commits MOVED boxes (``fold_moved > 0``), for the
    stock and flow charts (a day of plain re-points that moved nothing is not marked)."""
    return [{"date": r["date"], "moved": r.get("fold_moved", 0),
             "label": "backlog refactor fold: boxes moved, not closed or filed"}
            for r in daily if r.get("fold_moved", 0) > 0]


def _fill_weeks(rows: list[dict], zero: dict) -> list[dict]:
    """Continuous ISO weeks first..current with explicit zeros (empty weeks used to
    be skipped, so the chart never plotted a zero-completion week)."""
    if not rows:
        return rows
    by = {r["week"]: r for r in rows}

    def monday(wk: str) -> date:
        y, w = wk.split("-W")
        return date.fromisocalendar(int(y), int(w), 1)

    cur, last = monday(min(by)), max(monday(max(by)), datetime.now(timezone.utc).date())
    out = []
    while cur <= last:
        y, w, _ = cur.isocalendar()
        wk = f"{y}-W{w:02d}"
        out.append(by.get(wk) or {"week": wk, **zero})
        cur += timedelta(days=7)
    return out


def build_timeline(repo: Path) -> dict:
    commit_flags: dict[str, dict] = {}
    commits = _parse_commits(_run_git_log(repo), commit_flags)
    messages: dict[str, str] | None = None   # fetched lazily, only if a re-point exists
    repoints: list[dict] = []

    # Per-handoff lifecycle, keyed by the full ``state/stem`` path (migrated on
    # rename) so two distinct handoffs that share a basename across state dirs
    # (e.g. active/foo.md and completed/foo.md) do not collide into one record
    # and one task-dedup bag.
    records: dict[str, dict] = {}
    seen_checked: dict[str, set] = {}   # task keys first seen CHECKED (completed)
    seen_opened: dict[str, set] = {}    # task keys first seen at all (entered backlog)
    created_seen: set = set()
    # Last commit day (YYYY-MM-DD) that touched each handoff, keyed by state/stem.
    # Migrated on rename, dropped on delete. Feeds the board's recency signal so a
    # card re-sorts/re-dates on edits even when its file carries no ``Updated:`` field.
    file_activity: dict[str, str] = {}
    tasks_weekly: Counter = Counter()    # task completions per week
    opened_weekly: Counter = Counter()   # legacy created-date task intake estimate
    newly_filed_weekly: Counter = Counter()  # first observed checkbox additions
    created_weekly: Counter = Counter()
    completed_weekly: Counter = Counter()
    commits_weekly: Counter = Counter()      # handoff commits per week (any change)
    box_events_weekly: Counter = Counter()   # checkbox lines added/removed per week
    total_completions = 0
    total_opened = 0
    total_newly_filed = 0
    total_moved = 0

    def _set_terminal(rec: dict, term_date: str, term_state: str) -> None:
        # A handoff cannot terminate before it was created.
        created = rec.get("created")
        if created and term_date < created:
            term_date = created
        rec["terminal_date"] = term_date
        rec["terminal_state"] = term_state

    for sha, ts, blocks in commits:
        try:
            commit_day = datetime.fromisoformat(ts).date().isoformat()
        except ValueError:
            continue
        commit_week = _iso_week(commit_day)
        commits_weekly[commit_week] += 1
        box_events_weekly[commit_week] += sum(len(b.checkboxes) + len(b.removed_checkboxes)
                                              for b in blocks)
        cflags = commit_flags.get(sha) or {}
        fold_commit = bool(cflags.get("fold"))
        # FOLD-AWARE first-seen (2026-11-03). In a fold (Repoint-Reason) or backlog-refactor
        # (D9-ack) commit, a box removed from one handoff and added to another is a MOVE: the
        # target inherits it as already seen, so it is neither "newly filed" nor completed a
        # second time. Before this, the per-file first-seen bags counted every moved box
        # again -- 2026-W45 read 6616 newly filed.
        moved_pool: dict[str, list] = {}
        if fold_commit or cflags.get("refactor"):
            for blk in blocks:
                rss = _path_state_stem(blk.rename_from or blk.old_path)
                if rss is None or _is_router(rss[1]):
                    continue
                rkey = f"{rss[0]}/{rss[1]}"
                for mark, text in blk.removed_checkboxes:
                    tk = _task_key(text)
                    if tk and not _ROLLUP_RE.search(text):
                        moved_pool.setdefault(tk, []).append(rkey)

        if any(b.rows_removed for b in blocks) and any(b.rows_added for b in blocks):
            if messages is None:
                messages = _run_git_messages(repo)
            repoints.extend(repoints_for_commit(sha, commit_day, blocks,
                                                messages.get(sha, "")))

        for blk in blocks:
            new_ss = _path_state_stem(blk.new_path)
            old_ss = _path_state_stem(blk.rename_from or blk.old_path)
            router = bool((new_ss and _is_router(new_ss[1])) or (old_ss and _is_router(old_ss[1])))

            if router:
                pass        # routers are not handoffs: no lifecycle record (activity below)
            elif blk.is_new and new_ss and new_ss[0] in _TERMINAL and blk.folded_banner:
                # A fold stub written straight into completed/ (git saw delete + add): the
                # source's active record was terminated by the delete; the stub is neither a
                # new handoff nor a completion.
                pass
            elif blk.is_new and new_ss:
                state, stem = new_ss
                key = f"{state}/{stem}"
                created = blk.created_date or commit_day
                rec = records.setdefault(key, {"first_state": state})
                prev = rec.get("created")
                rec["created"] = min(prev, created) if prev else created
                rec.setdefault("terminal_date", None)
                rec.setdefault("terminal_state", None)
                if state not in _TERMINAL and rec.get("terminal_state"):
                    # RE-ADD REOPENS. `setdefault` above cannot do this: it is a
                    # no-op when the key already exists, so a record terminated by
                    # an earlier delete stayed terminal forever even though the
                    # path exists again. A file that is present is not deleted.
                    #
                    # Measured 2026-08-10: commit 24b06884 (2026-07-29) removed all
                    # 442 handoffs and 2053b758 restored them minutes later ("fix:
                    # restore full tree after malformed isolated index"). The series
                    # took the delete and never took the restore, so `active` fell
                    # 263 -> 6 and stayed there — the plot showed the repository
                    # losing its entire backlog on a day nothing was completed.
                    #
                    # The rename branch below already reopens on a move back into
                    # active/blocked; this is the same rule for the add path.
                    # Note keys are state-qualified (`active/x` vs `completed/x`),
                    # so a genuine active->completed move cannot be reopened here.
                    rec["terminal_date"] = None
                    rec["terminal_state"] = None
                if key not in created_seen:
                    created_seen.add(key)
                    created_weekly[_iso_week(rec["created"])] += 1
                if state in _TERMINAL:
                    term = blk.updated_date or blk.created_date or commit_day
                    _set_terminal(rec, term, state)
                    if state == "completed":
                        completed_weekly[_iso_week(rec["terminal_date"])] += 1
            elif blk.is_deleted and old_ss:
                # Terminate (do not erase) so the live interval up to the delete
                # is preserved in the series. 'deleted' is not counted after.
                rec = records.get(f"{old_ss[0]}/{old_ss[1]}")
                if rec is not None:
                    _set_terminal(rec, commit_day, "deleted")
            elif (blk.rename_to or blk.old_path != blk.new_path) and new_ss and old_ss:
                old_state, new_state = old_ss[0], new_ss[0]
                old_key = f"{old_ss[0]}/{old_ss[1]}"
                new_key = f"{new_ss[0]}/{new_ss[1]}"
                rec = records.pop(old_key, {"first_state": old_state})
                records[new_key] = rec
                if old_key != new_key:
                    seen_checked[new_key] = seen_checked.pop(
                        old_key, seen_checked.get(new_key, set()))
                    seen_opened[new_key] = seen_opened.pop(
                        old_key, seen_opened.get(new_key, set()))
                rec.setdefault("created", commit_day)
                if new_state in _TERMINAL and blk.folded_banner and old_state not in _TERMINAL:
                    # Folded into another handoff (``> **Folded into`` stub): its work moved,
                    # it did not finish. Like a delete, it leaves the series uncounted.
                    _set_terminal(rec, commit_day, "folded")
                elif new_state in _TERMINAL:
                    _set_terminal(rec, commit_day, new_state)
                    if new_state == "completed" and old_state != "completed":
                        completed_weekly[commit_week] += 1
                else:  # moved back into active/blocked — reopen
                    rec["terminal_date"] = None
                    rec["terminal_state"] = None

            # Task flow: legacy 'opened' attributes first appearance to the handoff
            # Created date; 'newly_filed' uses the first observed patch commit.
            # 'completed' is first checked appearance. All are first-seen-once.
            ident = new_ss or old_ss
            if ident is not None:
                ikey = f"{ident[0]}/{ident[1]}"
                # Last-touched bookkeeping. This runs for EVERY block (including
                # plain content edits, which hit none of the is_new/delete/rename
                # branches above), so it is the correct home for the activity map.
                if blk.is_deleted:
                    file_activity.pop(ikey, None)
                else:
                    # On rename the record already migrated to the new key above;
                    # drop the stale old key here. ``commit_day`` (this rename/edit
                    # commit) dominates any carried value, so max() suffices.
                    if old_ss and (blk.rename_to or blk.old_path != blk.new_path):
                        old_key = f"{old_ss[0]}/{old_ss[1]}"
                        if old_key != ikey:
                            file_activity.pop(old_key, None)
                    file_activity[ikey] = max(file_activity.get(ikey, ""), commit_day)
                if router:
                    continue   # no task flow for routers
                rec = records.get(ikey) or {}
                obag = seen_opened.setdefault(ikey, set())
                cbag = seen_checked.setdefault(ikey, set())
                removed_here = {_task_key(t): m for m, t in blk.removed_checkboxes}
                for mark, text, inline_date in blk.checkboxes:
                    tkey = _task_key(text)
                    if not tkey or _ROLLUP_RE.search(text):
                        continue   # roll-up parents never count (children carry the work)
                    src = moved_pool.get(tkey)
                    hit = next((k for k in src if k != ikey), None) if src else None
                    if hit is not None:
                        src.remove(hit)            # moved in from another handoff
                        if tkey not in obag:
                            total_moved += 1
                        obag.add(tkey)
                        if mark in ("x", "X"):
                            cbag.add(tkey)
                        continue
                    if fold_commit:
                        # Readiness-neutral migration: nothing it adds is a filing; only an
                        # in-place open -> [x] flip is a completion (server._count_commit).
                        flip = mark in ("x", "X") and removed_here.get(tkey) == " "
                        if not flip:
                            obag.add(tkey)
                            if mark in ("x", "X"):
                                cbag.add(tkey)
                            continue
                    if tkey not in obag:
                        obag.add(tkey)
                        # a task enters the backlog roughly when its handoff was created
                        opened_when = (rec.get("created")
                                       or (blk.created_date if blk.is_new else None)
                                       or commit_day)
                        opened_weekly[_iso_week(opened_when)] += 1
                        total_opened += 1
                        newly_filed_weekly[commit_week] += 1
                        total_newly_filed += 1
                    if mark in ("x", "X") and tkey not in cbag:
                        cbag.add(tkey)
                        when = inline_date
                        if not when and blk.is_new:
                            when = blk.updated_date or blk.created_date
                        when = when or commit_day
                        tasks_weekly[_iso_week(when)] += 1
                        total_completions += 1

    series = _build_series(records)
    final = series[-1] if series else {s: 0 for s in STATES}
    daily_flow = build_daily_flow(_run_git_log(repo, first_parent=True),
                                  flow_log=_run_git_log(repo, no_merges=True))

    def _week_row(w: str) -> dict:
        ev = box_events_weekly.get(w, 0)
        return {"week": w, "tasks_completed": tasks_weekly.get(w, 0),
                "opened": opened_weekly.get(w, 0),
                "newly_filed": newly_filed_weekly.get(w, 0),
                "completed": tasks_weekly.get(w, 0),
                "commits": commits_weekly.get(w, 0), "box_events": ev,
                # no_data: git shows NO checkbox change that week (no handoff commit at all,
                # or only box-free edits) -- not the same thing as a week that measured zero.
                # (A backdated completion landing in such a week still counts as data.)
                "no_data": ev == 0 and not tasks_weekly.get(w) and not newly_filed_weekly.get(w)}
    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "last_sha": _head_sha(repo),
        "method": "git-log-p + in-file-date-seeding + file-activity",
        "series": series,
        "file_activity": file_activity,
        "next_action_repoints": repoints,
        "daily_flow": daily_flow,
        "refactor_markers": refactor_markers(daily_flow),
        "tasks_weekly": _fill_weeks([
            _week_row(w)
            for w in sorted(set(tasks_weekly) | set(opened_weekly) | set(newly_filed_weekly)
                            | set(commits_weekly))
        ], {"tasks_completed": 0, "opened": 0, "newly_filed": 0, "completed": 0,
            "commits": 0, "box_events": 0, "no_data": True}),
        "handoffs_weekly": _fill_weeks([
            {"week": w, "created": created_weekly.get(w, 0),
             "completed": completed_weekly.get(w, 0)}
            for w in sorted(set(created_weekly) | set(completed_weekly))
        ], {"created": 0, "completed": 0}),
        "totals": {
            "active": final.get("active", 0),
            "completed": final.get("completed", 0),
            "archived": final.get("archived", 0),
            "tasks_completed": total_completions,
            "tasks_opened": total_opened,
            "tasks_newly_filed": total_newly_filed,
            # Boxes first seen in a handoff via a fold/refactor MOVE (not counted as filed).
            "tasks_moved": total_moved,
            "commits_scanned": len(commits),
            "next_action_repoints": len(repoints),
            "repoints_with_trailer_reason": sum(
                1 for e in repoints if e["reason_source"] == "trailer"),
            "earliest": series[0]["date"] if series else None,
        },
    }


def _build_series(records: dict[str, dict]) -> list[dict]:
    """Cumulative active/completed/archived over time from lifecycle intervals.

    A handoff counts as *active* from its ``created`` date until its
    ``terminal_date``, then as its ``terminal_state`` thereafter. Emitted at each
    distinct event date; consecutive identical snapshots are collapsed.
    """
    events = set()
    for rec in records.values():
        if rec.get("created"):
            events.add(rec["created"])
        if rec.get("terminal_date"):
            events.add(rec["terminal_date"])
    if not events:
        return []

    series: list[dict] = []
    prev_key = None
    for day in sorted(events):
        counts = {"active": 0, "completed": 0, "archived": 0}
        for rec in records.values():
            created = rec.get("created")
            if not created or created > day:
                continue
            term = rec.get("terminal_date")
            tstate = rec.get("terminal_state")
            if term and day >= term:
                # Reached a terminal state: count completed/archived; a 'deleted'
                # handoff contributes nothing after its deletion.
                if tstate in ("completed", "archived"):
                    counts[tstate] += 1
            else:
                counts["active"] += 1
        key = (counts["active"], counts["completed"], counts["archived"])
        if key != prev_key:
            series.append({"date": day, "blocked": 0, **counts})
            prev_key = key
    return series


def write_atomic(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".tmp.{os.getpid()}")
    tmp.write_text(json.dumps(data, indent=1), encoding="utf-8")
    os.replace(tmp, path)


def main() -> int:
    ap = argparse.ArgumentParser(description="Build the handoff progress timeline")
    ap.add_argument("--repo", type=Path, default=_repo_root())
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--print", action="store_true", help="print summary to stderr")
    args = ap.parse_args()

    repo = args.repo.resolve()
    out = args.out or (repo / "data" / "handoff_timeline.json")
    try:
        data = build_timeline(repo)
    except Exception as exc:  # keep the hook quiet on failure
        print(f"[handoff-timeline] build failed: {exc}", file=sys.stderr)
        return 1
    write_atomic(out, data)
    if args.print:
        t = data["totals"]
        print(
            f"[handoff-timeline] {out} — commits={t['commits_scanned']} "
            f"earliest={t['earliest']} tasks_completed={t['tasks_completed']} "
            f"active={t['active']} completed={t['completed']} archived={t['archived']}",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
