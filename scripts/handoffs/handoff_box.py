#!/usr/bin/env python3
"""handoff_box.py — write handoff boxes in the standard grammar (handoff standard Rev 1 §2.2 / §3, Stage A).

  add    --file F --track T --id ID --class C --text "..." --done-when "..." [--gate A,B] [--inputs P ...]
         [--tier T] [--owner O] [--needs-owner] [--after ID|end]
         Appends the box under the track's `### Backlog` (created right after the track heading/gate marker if absent).
  split  --file F ID --child "ID2::text::done when" [--child ...]
         Marks ID a roll-up via a `· roll-up:` continuation line and nests the children under it.
  refine --file F ID --new-id ID2 --text "..." --done-when "..." [same optional fields as add]
         Writes a NEW box ID2 after ID carrying `· previous_task_text:` + `· supersedes:`; ID gets `· ❄ frozen until:`.
  gate   --file F ID [--add A,B] [--remove A] [--none]      edits the box's `· gate:` line
  freeze --file F (ID | --track T | --whole-file) --until EVENT
  add ... --brief --where W [W ...] --approach TEXT [--acceptance CMD] [--non-goal NG ...] [--brief-author A]
         also writes the box's brief sidecar `handoffs/active/briefs/<ID>.md` (epyc.brief.v1, task-brief layer) in the
         same run and compiles it; --acceptance defaults to the --done-when text. Every new box should carry one.
  needs-brief --file F ID [--reason R] [--clear]
         tags the box NEEDS-BRIEF (a `· NEEDS-BRIEF:` continuation line) so box_index/select.py skip it until briefed.
  brief accept|reject ID [--by owner] [--root R]
         accept (clears the self-brief `review: backfill` flag, re-grounds) or reject a brief; refuses an orphaned
         brief (box_text_sha mismatch).

  assign-id FILE LINE [--id X] [--base origin/main]
         give an ID-less box (or one whose extracted "ID" is a title word, e.g. "Sub-quarter", "1") a bold head ID,
         minted with the handoff's prefix convention against IDs on --base + the working tree; records
         {op: assign-id, box_id, text_sha (old), new_text_sha, from, to, at} in handoffs/active/.moves.jsonl so text_sha
         identity is followed. Idempotent: a box that already has a real ID is left alone. The ONE sanctioned
         first-line edit (bulk use notifies owners, as for the Stage B bulk moves).

INVARIANT: the FIRST LINE of an existing box is never changed (task text is the identity; spec §2.2). Every op edits
continuation lines or inserts new lines only, and verifies this before writing. `--dry-run` prints the diff.
"""
from __future__ import annotations

import argparse
import collections
import difflib
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import box_index as BI  # noqa: E402
import task_lint as TL  # noqa: E402
import task_lint_core as L1  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
ID_SCAN_DIRS = ("handoffs/active", "handoffs/blocked", "handoffs/completed", "handoffs/archived")
CONT_INDENT = "      "          # continuation indent relative to the box's own indent
CHILD_INDENT = "  "             # nesting indent for split children
_ID_OK = re.compile(r"^[A-Za-z][A-Za-z0-9._-]*$")


class BoxError(Exception):
    pass


def render(box_id, cls, text, done_when=None, gate=None, inputs=(), tier=None, owner=None, needs_owner=False,
           extra=(), indent=""):
    if not _ID_OK.match(box_id):
        raise BoxError(f"bad ID {box_id!r}")
    if cls not in TL.CLASSES:
        raise BoxError(f"class must be one of {TL.CLASSES}")
    text = " ".join(text.split())
    if not text:
        raise BoxError("empty task text")
    if cls in TL.DONE_WHEN_REQUIRED and not done_when and not needs_owner:
        raise BoxError(f"[{cls}] box needs --done-when (or --needs-owner for a draft)")
    head = f"{indent}- [ ] **{box_id}** [{cls}] {text}" + (" NEEDS-OWNER" if needs_owner else "")
    c = indent + CONT_INDENT
    out = [head]
    if done_when:
        out.append(f"{c}· done when: {' '.join(done_when.split())}")
    g = f"· gate: {', '.join(gate) if gate else 'none'}"
    if inputs:
        g += "        · inputs: " + " ".join(f"`{p}`" for p in inputs)
    out.append(c + g)
    opt = [f"· tier: {tier}" if tier else "", f"· owner: {owner}" if owner else ""]
    if any(opt):
        out.append(c + "   ".join(x for x in opt if x))
    out += [c + e for e in extra]
    return out


def all_ids(root: Path) -> set[str]:
    ids = set()
    for d in ID_SCAN_DIRS:
        for p in sorted((root / d).glob("*.md")) if (root / d).exists() else []:
            for line in p.read_text(encoding="utf-8", errors="replace").split("\n"):
                m = L1.head_id(line)
                if m:
                    ids.add(m)
    return ids


def find_box(lines, box_id):
    fenced = L1.fenced_lines(lines)
    hits = [i for i, l in enumerate(lines) if i not in fenced and L1.head_id(l) == box_id]
    if len(hits) != 1:
        raise BoxError(f"box **{box_id}** found {len(hits)} times (need exactly 1)")
    return hits[0]


def block_end(lines, i):
    """Index after the box's block (its continuation + nested lines)."""
    txt, _ = L1.block(lines, i)
    return i + len(txt.split("\n"))


def own_end(lines, i):
    """Index after the box's OWN continuation lines (before any nested child box)."""
    j, ind = i + 1, len(lines[i]) - len(lines[i].lstrip())
    while j < len(lines) and lines[j].strip() and not L1.CHECKBOX.match(lines[j]) \
            and len(lines[j]) - len(lines[j].lstrip()) > ind and not lines[j].lstrip().startswith("#"):
        j += 1
    return j


def cont_prefix(lines, i):
    return lines[i][:len(lines[i]) - len(lines[i].lstrip())] + CONT_INDENT


def _top_ancestor(lines, i):
    """The top-level box whose block contains line i (i itself when it is top-level)."""
    ind = len(lines[i]) - len(lines[i].lstrip())
    j = i
    while ind > 0 and j > 0:
        j -= 1
        m = L1.CHECKBOX.match(lines[j])
        if m and len(m.group(1)) < ind:
            i, ind = j, len(m.group(1))
        elif not lines[j].strip() or lines[j].lstrip().startswith("#"):
            break
    return i


def _header_end(lines):
    """Index right after the title + `**Key**:` front-matter block (implicit-track insert point)."""
    j = 0
    while j < len(lines) and not lines[j].startswith("# "):
        j += 1
    j += 1
    while j < len(lines) and not lines[j].startswith("## "):
        j += 1
    return j


def backlog_insert_point(lines, track, after=None):
    """(lines, insert index) — creates `### Backlog` under the track when missing. A file with NO `## Track:`
    is one implicit track (review S3): `--track` is then ignored and its `### Backlog` sits after the header."""
    sec = BI.sections(lines)
    tracked = any(x[0] for x in sec)
    if not tracked:
        t_lines = [i for i, x in enumerate(sec) if x[0] is None and not x[4]]
        head = None
    else:
        t_lines = [i for i, x in enumerate(sec) if x[0] == track]
        if not t_lines:
            raise BoxError(f"no `## Track: {track}` section")
        head = t_lines[0]
    if after and after != "end":
        i = find_box(lines, after)
        if tracked and sec[i][0] != track:
            raise BoxError(f"--after {after} is not in track {track}")
        top = _top_ancestor(lines, i)      # review S4: a new box is top-level, so it goes after the WHOLE parent block
        return lines, block_end(lines, top)
    bl = [i for i in t_lines if sec[i][1]]
    if not bl:
        if head is None:
            j = _header_end(lines)
            lines = lines[:j] + ["### Backlog", ""] + lines[j:]
            return lines, j + 1
        j = head + 1
        while j < len(lines) and (BI._FENCE.match(lines[j]) is None) and \
                (re.match(r"^\s*<!--\s*(gate|frozen)", lines[j]) or lines[j].startswith("❄") or not lines[j].strip()):
            j += 1
        lines = lines[:j] + ["### Backlog", ""] + lines[j:]
        return lines, j + 1
    last = bl[-1]
    while last > bl[0] and not lines[last].strip():
        last -= 1
    return lines, last + 1


def set_field(lines, i, key, value):
    """Replace the box's own `· key:` value, or append a new continuation line. Returns new lines."""
    end = own_end(lines, i)
    rx = re.compile(r"·\s*(?:❄\s*)?" + re.escape(key) + r"\s*:\s*[^·]*")
    pre = "❄ " if key == "frozen until" else ""
    for j in range(i + 1, end):
        if rx.search(lines[j]):
            lines[j] = rx.sub(f"· {pre}{key}: {value}" + ("        " if "·" in rx.sub("", lines[j]).strip() else ""),
                              lines[j], count=1).rstrip()
            return lines
    return lines[:end] + [f"{cont_prefix(lines, i)}· {pre}{key}: {value}"] + lines[end:]


def guard_first_lines(before, after):
    old = collections.Counter(l for l in before if L1.CHECKBOX.match(l))
    new = collections.Counter(l for l in after if L1.CHECKBOX.match(l))
    lost = old - new
    if lost:
        raise BoxError(f"refusing: would change an existing box first line: {next(iter(lost))!r}")


def op_add(lines, a, root):
    if a.id in all_ids(root):
        raise BoxError(f"ID {a.id} already exists (IDs are never reused)")
    new = render(a.id, a.cls, a.text, a.done_when, split(a.gate), a.inputs or (), a.tier, a.owner, a.needs_owner)
    lines, at = backlog_insert_point(list(lines), a.track, a.after)
    return lines[:at] + new + lines[at:]


def op_split(lines, a, root):
    i = find_box(lines, a.box)
    existing = all_ids(root)
    kids = []
    ind = lines[i][:len(lines[i]) - len(lines[i].lstrip())] + CHILD_INDENT
    for spec in a.child:
        parts = spec.split("::")
        if len(parts) != 3:
            raise BoxError(f"--child must be ID::text::done when, got {spec!r}")
        cid, text, dw = parts
        if cid in existing:
            raise BoxError(f"child ID {cid} already exists")
        cls = TL.dispatch_result(L1.block(lines, i)[0])["class"]
        kids += render(cid, cls if cls in TL.DONE_WHEN_REQUIRED else "non-inference", text, dw, indent=ind)
    lines = list(lines)
    if "roll-up" not in TL.parse_fields(L1.block(lines, i)[0]):
        lines = set_field(lines, i, "roll-up", "non-dispatchable — children carry the work")
    return lines[:block_end(lines, i)] + kids + lines[block_end(lines, i):]


def op_refine(lines, a, root):
    i = find_box(lines, a.box)
    if a.new_id in all_ids(root):
        raise BoxError(f"ID {a.new_id} already exists")
    m = L1.CHECKBOX.match(lines[i])
    prev = " ".join(m.group(3).split())
    ind = lines[i][:len(lines[i]) - len(lines[i].lstrip())]
    new = render(a.new_id, a.cls or TL.dispatch_result(L1.block(lines, i)[0])["class"], a.text, a.done_when,
                 split(a.gate), a.inputs or (), a.tier, a.owner, a.needs_owner,
                 extra=[f"· supersedes: {a.box}", f"· previous_task_text: {prev}"], indent=ind)
    lines = set_field(list(lines), i, "frozen until", f"{a.new_id} (superseded by {a.new_id})")
    e = block_end(lines, i)
    return lines[:e] + new + lines[e:]


def op_gate(lines, a, root):
    i = find_box(lines, a.box)
    cur = TL.split_refs(TL.parse_fields(L1.block(lines, i)[0]).get("gate", ""))
    if a.none:
        cur = []
    cur = [g for g in cur if g not in split(a.remove)] + [g for g in split(a.add) if g not in cur]
    for g in cur:
        if not TL.GATE_REF.match(g):
            raise BoxError(f"gate ref {g!r} is not an ID")
    return set_field(list(lines), i, "gate", ", ".join(cur) if cur else "none")


def op_freeze(lines, a, root):
    lines = list(lines)
    if a.box:
        return set_field(lines, find_box(lines, a.box), "frozen until", a.until)
    if a.track:
        sec = BI.sections(lines)
        t = [i for i, x in enumerate(sec) if x[0] == a.track]
        if not t:
            raise BoxError(f"no `## Track: {a.track}` section")
        j = t[0] + 1
        while j < len(lines) and re.match(r"^\s*<!--\s*gate", lines[j]):
            j += 1
        return lines[:j] + [f"❄ frozen until: {a.until}"] + lines[j:]
    if a.whole_file:
        for j, l in enumerate(lines[:60]):
            m = re.match(r"^(\*\*Status\*\*:\s*)(.*)$", l)
            if m:
                lines[j] = f"{m.group(1)}FROZEN — ❄ frozen until: {a.until} (was: {m.group(2)})"
                return lines
        raise BoxError("no `**Status**:` line in the first 60 lines")
    raise BoxError("freeze needs ID, --track or --whole-file")


def op_needs_brief(lines, a, root):
    """Tag the box NEEDS-BRIEF on a `· NEEDS-BRIEF: <date> <reason>` continuation line (the first line is the identity
    and never changes). box_index reads `needs_brief` from it and select.py skips the box until its owner briefs it
    (`brief accept` or `--clear` removes the tag). Idempotent: a second tag replaces the line."""
    lines = list(lines)
    i = find_box(lines, a.box)
    if L1.CHECKBOX.match(lines[i]).group(2) in "xX":
        raise BoxError(f"{a.box} is ticked; nothing to tag")
    if a.clear:
        end = own_end(lines, i)
        return [l for k, l in enumerate(lines) if not (i < k < end and re.match(r"^\s*·\s*NEEDS-BRIEF\s*:", l))]
    date = a.date or __import__("datetime").date.today().isoformat()
    why = " ".join((a.reason or "two failed self-briefs").replace("·", "-").split())[:200]
    return set_field(lines, i, "NEEDS-BRIEF", f"{date} {why}")


def split(v):
    return [x for x in re.split(r"[,\s]+", v or "") if x]


def op_propose(lines, a, root):
    """C1 (decision 6): a NEEDS-OWNER proposal child `**<ID>.p<n>** [<class>] <text> NEEDS-OWNER` nested after the
    parent's own block, with `· done when:` / `· stop rule:`, `· proposed-by: <who> <ts>` and `· parent: <ID>`. The
    parent is NEVER edited. No `gate:` (an accepted child must not be blocked by its own open parent)."""
    i = find_box(lines, a.box)
    if L1.CHECKBOX.match(lines[i]).group(2) in "xX":
        raise BoxError(f"{a.box} is ticked; proposals go under open boxes")
    ids = all_ids(root)
    n = 1
    while f"{a.box}.p{n}" in ids or any(f"**{a.box}.p{n}**" in l for l in lines):
        n += 1
    cid = f"{a.box}.p{n}"
    indent = lines[i][:len(lines[i]) - len(lines[i].lstrip())]
    extra = []
    if a.stop_rule:
        extra.append(f"· stop rule: {' '.join(a.stop_rule.split())}")
    extra.append(f"· proposed-by: {' '.join(a.proposed_by.split())}        · parent: {a.box}")
    new = render(cid, a.cls, a.text, a.done_when, None, a.inputs or (), a.tier, a.owner, True, extra, indent + "  ")
    new = [l for l in new if l.strip() != "· gate: none"]
    end = block_end(lines, i)
    return lines[:end] + new + lines[end:]


def op_reject(lines, a, root):
    """C1: decline a proposal child -- its block leaves the backlog and lands under `## History` as a plain line
    `- **<ID>** <text> [declined: <who> <date> <reason>]` (the belief-capture D1 form; History never holds boxes)."""
    i = find_box(lines, a.box)
    own_txt, _ = L1.own_block(lines, i)
    if "NEEDS-OWNER" not in own_txt or "proposed-by" not in own_txt:
        raise BoxError(f"{a.box} is not a pending proposal (needs NEEDS-OWNER + proposed-by)")
    end = own_end(lines, i)
    body = L1.CHECKBOX.match(lines[i]).group(3).replace("NEEDS-OWNER", "").strip()
    date = a.date or __import__("datetime").date.today().isoformat()
    note = f"- {body} [declined: {a.by} {date} {' '.join(a.reason.split())}]"
    rest = lines[:i] + lines[end:]
    hist = next((k for k, l in enumerate(rest) if re.match(r"^##\s+History\b", l)), None)
    if hist is None:
        while rest and not rest[-1].strip():
            rest.pop()
        return rest + ["", "## History", "", note, ""]
    return rest[:hist + 1] + ["", note] + rest[hist + 1:]


def split_file(path: Path, track: str, to_slug: str, root: Path = REPO_ROOT, dry_run=False, today=None) -> dict:
    """C4 (standard §2.3, > 6,000 lines or > 3 tracks): move a whole `## Track: <track>` section into a NEW handoff
    `handoffs/active/<to_slug>.md` (rendered by new_handoff.render, `**Parent**` pointing back), leave a pointer track
    in the source, and append one `.moves.jsonl` line per moved box (box_id, text_sha, from, to, at) so rowflow readers
    repoint rows by text_sha (handoff_ref.resolve). Zero first-line changes across both files (checked)."""
    import datetime
    import json
    import new_handoff as NH
    today = today or datetime.date.today().isoformat()
    lines = path.read_text(encoding="utf-8").split("\n")
    start = next((i for i, l in enumerate(lines) if re.match(r"^##\s+Track:\s*" + re.escape(track) + r"\s*$", l)), None)
    if start is None:
        raise BoxError(f"no `## Track: {track}` in {path.name}")
    end = next((i for i in range(start + 1, len(lines)) if re.match(r"^#{1,2}\s", lines[i])), len(lines))
    dest = root / "handoffs" / "active" / f"{to_slug}.md"
    if dest.exists():
        raise BoxError(f"{dest} exists")
    row = next((re.sub(r"^\*\*Row\*\*:\s*", "", l).strip() for l in lines[:60] if l.startswith("**Row**:")), "XXX-0")
    dom = next((re.sub(r"^\*\*Domain\*\*:\s*", "", l).strip() for l in lines[:60] if l.startswith("**Domain**:")), "")
    head = NH.render(to_slug, row if re.fullmatch(r"[A-Z]{3}-\d+", row) else "XXX-0", dom or "unassigned", track=track,
                     today=today, status=f"ACTIVE — split from {path.name} ({today}); the owning session assigns its row")
    head = head.split("\n## Track:", 1)[0].rstrip("\n") + f"\n**Parent**: [{path.name}]({path.name})\n\n"
    moved = lines[start:end]
    new_src = lines[:start] + [lines[start], "", f"Moved to [{to_slug}.md]({to_slug}.md) on {today} "
                                                 f"(handoff_box.py split-file).", ""] + lines[end:]
    before = [l for l in lines if L1.CHECKBOX.match(l)]
    after = [l for l in new_src + moved if L1.CHECKBOX.match(l)]
    if sorted(before) != sorted(after):
        raise BoxError("refusing: split would change a box first line")
    moves = [{"box_id": L1.head_id(l), "text_sha": BI.text_sha(l), "from": path.name, "to": f"{to_slug}.md", "at": today}
             for l in moved if L1.CHECKBOX.match(l)]
    if not dry_run:
        dest.write_text(head + "\n".join(moved).rstrip("\n") + "\n\n## Findings\n\n## History\n\n"
                        f"- {today} split from {path.name} (handoff_box.py split-file)\n", encoding="utf-8")
        path.write_text("\n".join(new_src), encoding="utf-8")
        with open(root / "handoffs" / "active" / ".moves.jsonl", "a", encoding="utf-8") as fh:
            for m in moves:
                fh.write(json.dumps(m, sort_keys=True) + "\n")
    return {"moved_boxes": len(moves), "to": str(dest), "lines_moved": len(moved)}


def base_ids(root: Path, base: str | None) -> set[str]:
    """Head IDs in handoffs/ at `base` (e.g. origin/main) -- minting checks the shared branch, not only this tree."""
    import subprocess
    if not base:
        return set()
    r = subprocess.run(["git", "-C", str(root), "grep", "-h", "-I", "-e", r"\[", base, "--", "handoffs/"],
                       capture_output=True, text=True, timeout=120)
    return {i for i in (L1.head_id(l) for l in r.stdout.split("\n")) if i}


def id_prefix(lines: list[str], path: Path) -> str:
    """The handoff's ID convention: the most common `<PREFIX>-` of its real IDs, else the file stem's initials."""
    c = collections.Counter()
    for l in lines:
        i = L1.head_id(l)
        if i and not L1.suspect_id(i):
            m = re.match(r"^(.*?)[-_.]?\d+[A-Za-z]?$", i)
            if m and m.group(1):
                c[m.group(1)] += 1
    if c:
        return c.most_common(1)[0][0]
    return "".join(w[0] for w in path.stem.split("-") if w).upper() or "BOX"


def assign_id(path: Path, line: int, new_id: str | None = None, root: Path = REPO_ROOT, base: str | None = "origin/main",
              dry_run=False, today=None) -> dict:
    import datetime
    import json
    today = today or datetime.date.today().isoformat()
    raw = path.read_text(encoding="utf-8")
    lines = raw.split("\n")
    i = line - 1
    if not (0 <= i < len(lines)) or not L1.CHECKBOX.match(lines[i]):
        raise BoxError(f"{path.name}:{line} is not a checkbox line")
    cur = L1.head_id(lines[i])
    if cur and not L1.suspect_id(cur):
        return {"id": cur, "changed": False, "line": line}
    taken = all_ids(root) | base_ids(root, base)
    if new_id:
        if not _ID_OK.match(new_id) or L1.suspect_id(new_id):
            raise BoxError(f"--id {new_id!r} is not an ID (UPPER-CASE prefix + a digit)")
        if new_id in taken:
            raise BoxError(f"ID {new_id} already exists")
    else:
        pre = id_prefix(lines, path)
        sep = "" if pre.endswith(("-", "_", ".")) else "-"
        n = 1 + max([int(m.group(1)) for t in taken for m in [re.match(re.escape(pre) + r"[-_.]?(\d+)$", t)] if m] or [0])
        new_id = f"{pre}{sep}{n}"
    m = L1.HEAD_PREFIX.match(lines[i])
    old = lines[i]
    lines[i] = old[:m.end()] + f"**{new_id}** " + old[m.end():]
    if L1.head_id(lines[i]) != new_id:
        raise BoxError(f"inserted ID does not parse back as the head ID: {lines[i][:80]!r}")
    rec = {"op": "assign-id", "box_id": new_id, "text_sha": BI.text_sha(old), "new_text_sha": BI.text_sha(lines[i]),
           "from": path.name, "to": path.name, "at": today, "line": line, "old_head": cur}
    if not dry_run:
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text("\n".join(lines), encoding="utf-8")
        os.replace(tmp, path)
        mv = root / "handoffs" / "active" / ".moves.jsonl"
        mv.parent.mkdir(parents=True, exist_ok=True)
        with open(mv, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, sort_keys=True) + "\n")
    return {"id": new_id, "changed": True, "line": line, "move": rec}


OPS = {"add": op_add, "split": op_split, "refine": op_refine, "gate": op_gate, "freeze": op_freeze,
       "propose": op_propose, "reject": op_reject, "needs-brief": op_needs_brief}


def apply(path: Path, op: str, a, root: Path = REPO_ROOT, dry_run=False) -> str:
    raw = path.read_bytes().decode("utf-8", errors="surrogateescape")   # stray bytes round-trip unchanged (S4)
    eol = "\r\n" if "\r\n" in raw else "\n"                            # CRLF files stay CRLF (S4)
    before = raw.replace("\r\n", "\n").split("\n")
    after = OPS[op](before, a, root)
    if op == "reject":     # the declined proposal's first line leaves on purpose; every OTHER first line must stay
        drop = next(l for l in before if L1.CHECKBOX.match(l) and L1.head_id(l) == a.box)
        guard_first_lines([l for l in before if l != drop], after)
    else:
        guard_first_lines(before, after)
    diff = "\n".join(difflib.unified_diff(before, after, str(path), str(path), lineterm="", n=1))
    if not dry_run:
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_bytes(eol.join(after).encode("utf-8", errors="surrogateescape"))
        os.replace(tmp, path)
    return diff


def parser():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="op", required=True)

    def common(p, box=True):
        p.add_argument("--file", required=True)
        p.add_argument("--dry-run", action="store_true")
        if box:
            p.add_argument("box", nargs="?" if p.prog.endswith("freeze") else None)

    def fields(p, need_class=True):
        p.add_argument("--class", dest="cls", required=need_class, choices=TL.CLASSES)
        p.add_argument("--text", required=True)
        p.add_argument("--done-when")
        p.add_argument("--gate")
        p.add_argument("--inputs", nargs="*")
        p.add_argument("--tier", choices=TL.TIERS)
        p.add_argument("--owner")
        p.add_argument("--needs-owner", action="store_true")

    p = sub.add_parser("add"); common(p, box=False); fields(p)
    p.add_argument("--track", required=True); p.add_argument("--id", required=True); p.add_argument("--after")
    p.add_argument("--brief", action="store_true", help="also write the brief sidecar (task-brief layer)")
    p.add_argument("--where", nargs="+"); p.add_argument("--approach"); p.add_argument("--acceptance")
    p.add_argument("--non-goal", action="append", default=[])
    p.add_argument("--brief-author", default="owner")
    p.add_argument("--new-test", action="append", default=[])
    p = sub.add_parser("brief"); p.add_argument("action", choices=("accept", "reject")); p.add_argument("box")
    p.add_argument("--by", default="owner"); p.add_argument("--root", default=str(REPO_ROOT))
    p = sub.add_parser("split"); common(p); p.add_argument("--child", action="append", required=True)
    p = sub.add_parser("refine"); common(p); fields(p, need_class=False); p.add_argument("--new-id", required=True)
    p = sub.add_parser("gate"); common(p)
    p.add_argument("--add"); p.add_argument("--remove"); p.add_argument("--none", action="store_true")
    p = sub.add_parser("propose"); common(p); fields(p)
    p.add_argument("--proposed-by", required=True); p.add_argument("--stop-rule")
    p = sub.add_parser("reject"); common(p)
    p.add_argument("--by", required=True); p.add_argument("--reason", required=True); p.add_argument("--date")
    p = sub.add_parser("needs-brief"); common(p)
    p.add_argument("--reason"); p.add_argument("--date"); p.add_argument("--clear", action="store_true")
    p.add_argument("--root", default=str(REPO_ROOT))
    p = sub.add_parser("split-file"); common(p, box=False)
    p.add_argument("--track", required=True); p.add_argument("--to", required=True)
    p = sub.add_parser("assign-id"); p.add_argument("file"); p.add_argument("line", type=int)
    p.add_argument("--id"); p.add_argument("--base", default="origin/main"); p.add_argument("--dry-run", action="store_true")
    p = sub.add_parser("freeze"); common(p)
    p.add_argument("--track"); p.add_argument("--whole-file", action="store_true"); p.add_argument("--until", required=True)
    return ap


def _brief_mod():
    p = str(REPO_ROOT / "scripts" / "coordination")
    if p not in sys.path:
        sys.path.insert(0, p)
    from taskflow import brief  # noqa: PLC0415
    return brief


def root_of(path: Path) -> Path:
    """The repo root a handoff file lives in (`<root>/handoffs/<dir>/<file>.md`), else REPO_ROOT."""
    rp = path.resolve()
    return rp.parents[2] if len(rp.parents) > 2 and rp.parents[1].name == "handoffs" else REPO_ROOT


def op_brief(a) -> int:
    B = _brief_mod()
    root = Path(a.root)
    r = B.compile_brief(a.box, root, use_cache=False)
    if r["state"] == "none":
        print(f"handoff_box: no brief for {a.box}", file=sys.stderr)
        return 1
    if r["state"] == "orphaned" and a.action == "accept":
        print(f"handoff_box: refusing to accept an orphaned brief: {'; '.join(r['stale_list'])}", file=sys.stderr)
        return 1
    print(B.set_accepted(a.box, "rejected" if a.action == "reject" else a.by, root))
    if a.action == "accept" and r.get("box"):       # the owner briefed it: the NEEDS-BRIEF tag has done its job
        f = root / r["box"]["file"]
        if f.exists() and "NEEDS-BRIEF" in f.read_text(encoding="utf-8", errors="replace"):
            ns = argparse.Namespace(box=a.box, clear=True, reason=None, date=None)
            apply(f, "needs-brief", ns, root)
    return 0


def add_brief(a, path: Path) -> int:
    if not (a.where and a.approach):
        print("handoff_box: --brief needs --where and --approach", file=sys.stderr)
        return 1
    B = _brief_mod()
    root = root_of(path)
    acc = a.acceptance or (a.done_when or "").strip().strip("`")
    try:
        B.write_brief(a.id, a.where, a.approach, acc, a.non_goal, a.tier or "local", a.brief_author, root=root,
                      new_tests=a.new_test)
    except ValueError as e:
        print(f"handoff_box: brief not written: {e}", file=sys.stderr)
        return 1
    r = B.compile_brief(a.id, root)
    print(f"brief {a.id}: {r['state']}" + "".join(f"\n  STALE {x}" for x in r["stale_list"]))
    return 0 if r["state"] in ("fresh", "drift") else 1


def main(argv=None):
    a = parser().parse_args(argv)
    if a.op == "brief":
        return op_brief(a)
    path = Path(a.file)
    if a.op == "assign-id":
        try:
            print(__import__("json").dumps(assign_id(path, a.line, a.id, root_of(path), a.base or None, a.dry_run)))
        except BoxError as e:
            print(f"handoff_box: {e}", file=sys.stderr)
            return 1
        return 0
    if a.op == "split-file":
        try:
            print(split_file(path, a.track, a.to, dry_run=a.dry_run))
        except BoxError as e:
            print(f"handoff_box: {e}", file=sys.stderr)
            return 1
        return 0
    if a.op == "add" and a.brief and not (a.where and a.approach):
        print("handoff_box: --brief needs --where and --approach", file=sys.stderr)
        return 1
    try:
        print(apply(path, a.op, a, dry_run=a.dry_run) or "(no change)")
    except BoxError as e:
        print(f"handoff_box: {e}", file=sys.stderr)
        return 1
    if a.op == "add" and a.brief and not a.dry_run:
        return add_brief(a, path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
