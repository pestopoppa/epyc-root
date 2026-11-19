#!/usr/bin/env python3
"""handoff_migrate.py — the MECHANICAL migration pass of the handoff standard (Rev 1 §6 step 2; operator decision 2,
2026-11-19: these moves land directly, each owning session gets a diff summary and may revert).

    python3 scripts/handoffs/handoff_migrate.py FILE.md [FILE.md ...] [--dry-run] [--json]

Safe transforms only, per file:
  move      every TOP-LEVEL open box block (box + own continuation + nested children) that sits inside a track but
            outside its `### Backlog` moves to the bottom of that track's `### Backlog` (created after the track's
            heading/gate lines when missing), relative order preserved. A file with no `## Track:` is one implicit
            track whose `### Backlog` goes right after the header. Each moved box gets `· section: <old heading>`
            so its context survives. Open boxes nested under a TICKED parent, and boxes under a non-track `##`
            section (History/Findings) of a tracked file, are NOT moved (reported as `left`).
  class     `· class: <c>` where task_lint classifies the box by its DELIVERABLE (basis `deliverable`), no tag yet.
  frozen    `· ❄ frozen until: <event>` for a legacy `❄ FROZEN … resume only once <event>` headline.
  roll-up   `· roll-up: children carry the work` on an open box with at least one open nested child box.
  inputs    `· inputs-missing: `p` …` for backticked paths task_lint finds dangling (field f).

INVARIANT: no box's first line changes (text_sha set of open boxes identical before/after; checked before writing).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import box_index as BI  # noqa: E402
import task_lint as TL  # noqa: E402
import task_lint_core as L1  # noqa: E402

CONT = "      "
_FROZEN_HEAD = re.compile(r"❄\s*FROZEN\b", re.I)
_FROZEN_EVENT = (re.compile(r"resume\s+only\s+(?:once|when|after)\s+(?P<ev>.+?)\s*(?:—|\*\*|[.;]|$)", re.I),
                 re.compile(r"FROZEN\s+behind\s+(?P<ev>[A-Za-z][\w.-]*\d[\w.-]*)", re.I))


def frozen_event(line):
    for rx in _FROZEN_EVENT:
        m = rx.search(line)
        if m:
            return m.group("ev").strip()
    return None
_H = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")


class MigrateError(Exception):
    pass


def open_shas(lines):
    fenced = L1.fenced_lines(lines)
    return sorted(BI.text_sha(l) for i, l in enumerate(lines)
                  if i not in fenced and (m := L1.CHECKBOX.match(l)) and m.group(2) not in "xX")


def first_lines(lines):
    fenced = L1.fenced_lines(lines)
    return sorted(l.strip() for i, l in enumerate(lines) if i not in fenced and L1.CHECKBOX.match(l))


def _own_end(lines, i):
    _, nums = L1.own_block(lines, i)
    return nums[-1] + 1


def _block_end(lines, i):
    txt, _ = L1.block(lines, i)
    return i + len(txt.split("\n"))


def _heading_before(lines, i):
    for j in range(i - 1, -1, -1):
        m = _H.match(lines[j])
        if m:
            return m.group(2)
    return None


def annotate(lines, stats):
    """Add class / frozen / roll-up / inputs-missing continuation lines. Returns new lines."""
    fenced = L1.fenced_lines(lines)
    inserts = {}                                  # insert index -> [lines]
    for i, l in enumerate(lines):
        if i in fenced:
            continue
        m = L1.CHECKBOX.match(l)
        if not m or m.group(2) in "xX":
            continue
        own, _ = L1.own_block(lines, i)
        full, ch = L1.block(lines, i)
        fields = TL.parse_fields(own)
        sc = TL.score2(full, ch)
        add = []
        ind = m.group(1) + CONT
        if not TL.CLASS_TAG.search(l) and "class" not in fields and sc["class_basis"] == "deliverable":
            add.append(f"{ind}· class: {sc['class']}"); stats["class"] += 1
        fm = _FROZEN_HEAD.search(l)
        if fm and "frozen until" not in fields:
            ev = frozen_event(l) or "the event named in the box (legacy ❄ FROZEN)"
            add.append(f"{ind}· ❄ frozen until: {ev}"); stats["frozen"] += 1
        kids = [x for x in full.split("\n")[1:] if (km := L1.CHECKBOX.match(x)) and km.group(2) == " "]
        if kids and "roll-up" not in fields and not TL.ROLLUP.search(l):
            add.append(f"{ind}· roll-up: children carry the work"); stats["rollup"] += 1
        dang = [p for p in (sc.get("dangling") or []) if p]
        if dang and "inputs-missing" not in fields:
            add.append(f"{ind}· inputs-missing: " + " ".join(f"`{p}`" for p in dang)); stats["inputs"] += 1
        if add:
            inserts[_own_end(lines, i)] = inserts.get(_own_end(lines, i), []) + add
    out = []
    for i, l in enumerate(lines):
        out.extend(inserts.get(i, []))
        out.append(l)
    out.extend(inserts.get(len(lines), []))
    return out


def _header_end(lines):
    j = 0
    while j < len(lines) and not lines[j].startswith("# "):
        j += 1
    j += 1
    while j < len(lines) and not lines[j].startswith("## "):
        j += 1
    return j


def move_to_backlog(lines, stats):
    """Move top-level open box blocks under their track's `### Backlog`. Returns new lines."""
    sec = BI.sections(lines)
    tracked = any(s[0] for s in sec)
    blocks = []                                   # (start, end, track key)
    i = 0
    while i < len(lines):
        m = L1.CHECKBOX.match(lines[i])
        if not m or sec[i][4]:
            i += 1
            continue
        if len(m.group(1)) > 0:
            if m.group(2) not in "xX" and not sec[i][1]:
                stats["left_nested"] += 1
            i += 1
            continue
        end = _block_end(lines, i)
        if m.group(2) in "xX" or sec[i][1]:
            # ticked, or already in a Backlog: count open children of a ticked parent that stay behind
            if m.group(2) in "xX":
                stats["left_nested"] += sum(1 for x in lines[i + 1:end]
                                            if (km := L1.CHECKBOX.match(x)) and km.group(2) == " " and not sec[i][1])
            i = end
            continue
        track = sec[i][0]
        if tracked and track is None:
            stats["left_section"] += 1
            i = end
            continue
        blocks.append((i, end, track if tracked else None))
        i = end
    if not blocks:
        return lines
    moved = {}
    for s, e, t in blocks:
        body = lines[s:e]
        while body and not body[-1].strip():
            body.pop()
        head = _heading_before(lines, s)
        if head:
            _, nums = L1.own_block(lines, s)
            k = nums[-1] - s + 1
            body = body[:k] + [CONT + f"· section: {head}"] + body[k:]
        moved.setdefault(t, []).append(body)
        stats["moved"] += 1
    drop = set()
    for s, e, _ in blocks:
        drop.update(range(s, e))
    kept = [l for j, l in enumerate(lines) if j not in drop]
    # insertion: existing Backlog end, or a new Backlog
    for t, bodies in moved.items():
        sec2 = BI.sections(kept)
        payload = [x for b in bodies for x in b]
        if t is None:
            bl = [j for j, s_ in enumerate(sec2) if s_[1] and s_[0] is None]
        else:
            bl = [j for j, s_ in enumerate(sec2) if s_[1] and s_[0] == t]
        if bl:
            last = bl[-1]
            while last > bl[0] and not kept[last].strip():
                last -= 1
            kept = kept[:last + 1] + payload + kept[last + 1:]
        else:
            if t is None:
                j = _header_end(kept)
            else:
                j = next(k for k, s_ in enumerate(sec2) if s_[0] == t) + 1
                while j < len(kept) and (re.match(r"^\s*<!--\s*(gate|frozen)", kept[j]) or kept[j].startswith("❄")
                                         or not kept[j].strip()):
                    j += 1
            kept = kept[:j] + ["### Backlog", ""] + payload + [""] + kept[j:]
            stats["backlogs_created"] += 1
    return kept


def migrate_text(text):
    eol = "\r\n" if "\r\n" in text else "\n"
    lines = text.replace("\r\n", "\n").split("\n")
    stats = dict(moved=0, left_nested=0, left_section=0, backlogs_created=0, **{"class": 0}, frozen=0, rollup=0, inputs=0)
    before_open, before_first = open_shas(lines), first_lines(lines)
    out = annotate(lines, stats)
    out = move_to_backlog(out, stats)
    if open_shas(out) != before_open or first_lines(out) != before_first:
        raise MigrateError("first-line invariant violated; refusing to write")
    return eol.join(out), stats


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("files", nargs="+")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    res = {}
    for f in a.files:
        p = Path(f)
        raw = p.read_bytes().decode("utf-8", errors="surrogateescape")
        new, stats = migrate_text(raw)
        res[f] = stats
        if not a.dry_run and new != raw:
            tmp = p.with_suffix(p.suffix + ".tmp")
            tmp.write_bytes(new.encode("utf-8", errors="surrogateescape"))
            os.replace(tmp, p)
    print(json.dumps(res, indent=1, sort_keys=True) if a.json else
          "\n".join(f"{f}: {s}" for f, s in res.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
