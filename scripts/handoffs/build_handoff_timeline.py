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
from datetime import date, datetime, timezone
from pathlib import Path

STATES = ("active", "blocked", "completed", "archived")
_TERMINAL = ("completed", "archived")

_COMMIT_RE = re.compile(r"^\x00([0-9a-f]{7,40}) (.+)$")
_DIFF_RE = re.compile(r"^diff --git a/(.+) b/(.+)$")
_RENAME_FROM_RE = re.compile(r"^rename from (.+)$")
_RENAME_TO_RE = re.compile(r"^rename to (.+)$")
_ADDED_CHECKBOX_RE = re.compile(r"^\+\s*[-*]\s*\[([ xX])\]\s*(.*)$")
_ADDED_META_RE = re.compile(r"^\+\s*\*\*(Created|Updated|Date)\*\*:\s*(.*)$", re.I)
_PATH_RE = re.compile(r"^handoffs/(active|blocked|completed|archived)/(.+)\.md$")
_DATE_RE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
_CHECK_DATE_RE = re.compile(r"✅\s*(\d{4}-\d{2}-\d{2})")

_NON_HANDOFF_STEMS = {"BLOCKED", "README"}


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


def _run_git_log(repo: Path) -> str:
    cmd = [
        "git", "-C", str(repo), "log", "--reverse", "-M", "--no-color",
        "--format=%x00%H %aI", "-p", "--", "handoffs/",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True,
                          errors="replace", check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"git log failed: {proc.stderr.strip()[:400]}")
    return proc.stdout


def _head_sha(repo: Path) -> str | None:
    proc = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"],
                          capture_output=True, text=True, check=False)
    return (proc.stdout.strip() or None) if proc.returncode == 0 else None


class _Block:
    """One ``diff --git`` block within a commit."""

    __slots__ = ("old_path", "new_path", "is_new", "is_deleted", "rename_from",
                 "rename_to", "checkboxes", "created_date", "updated_date")

    def __init__(self, old_path: str, new_path: str) -> None:
        self.old_path = old_path
        self.new_path = new_path
        self.is_new = False
        self.is_deleted = False
        self.rename_from: str | None = None
        self.rename_to: str | None = None
        # each added checkbox line: (mark ' '|'x', task text, inline date)
        self.checkboxes: list[tuple[str, str, str | None]] = []
        self.created_date: str | None = None   # from +**Created** (new-file adds)
        self.updated_date: str | None = None   # from +**Updated**


def _parse_commits(log_text: str):
    """Return ``[(sha, iso_ts, [blocks]), ...]`` in chronological order."""
    sha = ts = None
    blocks: list[_Block] = []
    current: _Block | None = None
    results = []
    for line in log_text.splitlines():
        mcommit = _COMMIT_RE.match(line)
        if mcommit:
            if sha is not None:
                results.append((sha, ts, blocks))
            sha, ts = mcommit.group(1), mcommit.group(2)
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
        mac = _ADDED_CHECKBOX_RE.match(line)
        if mac:
            current.checkboxes.append(
                (mac.group(1), mac.group(2), _inline_task_date(mac.group(2))))
    if sha is not None:
        results.append((sha, ts, blocks))
    return results


def build_timeline(repo: Path) -> dict:
    commits = _parse_commits(_run_git_log(repo))

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
    opened_weekly: Counter = Counter()   # tasks entering the backlog per week
    created_weekly: Counter = Counter()
    completed_weekly: Counter = Counter()
    total_completions = 0
    total_opened = 0

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

        for blk in blocks:
            new_ss = _path_state_stem(blk.new_path)
            old_ss = _path_state_stem(blk.rename_from or blk.old_path)

            if blk.is_new and new_ss:
                state, stem = new_ss
                key = f"{state}/{stem}"
                created = blk.created_date or commit_day
                rec = records.setdefault(key, {"first_state": state})
                prev = rec.get("created")
                rec["created"] = min(prev, created) if prev else created
                rec.setdefault("terminal_date", None)
                rec.setdefault("terminal_state", None)
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
                if new_state in _TERMINAL:
                    _set_terminal(rec, commit_day, new_state)
                    if new_state == "completed" and old_state != "completed":
                        completed_weekly[commit_week] += 1
                else:  # moved back into active/blocked — reopen
                    rec["terminal_date"] = None
                    rec["terminal_state"] = None

            # Task flow: 'opened' = first appearance (any state, enters backlog);
            # 'completed' = first checked appearance. Both first-seen-once per handoff.
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
                rec = records.get(ikey) or {}
                obag = seen_opened.setdefault(ikey, set())
                cbag = seen_checked.setdefault(ikey, set())
                for mark, text, inline_date in blk.checkboxes:
                    tkey = _task_key(text)
                    if not tkey:
                        continue
                    if tkey not in obag:
                        obag.add(tkey)
                        # a task enters the backlog roughly when its handoff was created
                        opened_when = (rec.get("created")
                                       or (blk.created_date if blk.is_new else None)
                                       or commit_day)
                        opened_weekly[_iso_week(opened_when)] += 1
                        total_opened += 1
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
    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "last_sha": _head_sha(repo),
        "method": "git-log-p + in-file-date-seeding + file-activity",
        "series": series,
        "file_activity": file_activity,
        "tasks_weekly": [
            {"week": w, "tasks_completed": tasks_weekly.get(w, 0),
             "opened": opened_weekly.get(w, 0), "completed": tasks_weekly.get(w, 0)}
            for w in sorted(set(tasks_weekly) | set(opened_weekly))
        ],
        "handoffs_weekly": [
            {"week": w, "created": created_weekly.get(w, 0),
             "completed": completed_weekly.get(w, 0)}
            for w in sorted(set(created_weekly) | set(completed_weekly))
        ],
        "totals": {
            "active": final.get("active", 0),
            "completed": final.get("completed", 0),
            "archived": final.get("archived", 0),
            "tasks_completed": total_completions,
            "tasks_opened": total_opened,
            "commits_scanned": len(commits),
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
