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


OPS = {"add": op_add, "split": op_split, "refine": op_refine, "gate": op_gate, "freeze": op_freeze,
       "propose": op_propose, "reject": op_reject}


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
    p = sub.add_parser("split"); common(p); p.add_argument("--child", action="append", required=True)
    p = sub.add_parser("refine"); common(p); fields(p, need_class=False); p.add_argument("--new-id", required=True)
    p = sub.add_parser("gate"); common(p)
    p.add_argument("--add"); p.add_argument("--remove"); p.add_argument("--none", action="store_true")
    p = sub.add_parser("propose"); common(p); fields(p)
    p.add_argument("--proposed-by", required=True); p.add_argument("--stop-rule")
    p = sub.add_parser("reject"); common(p)
    p.add_argument("--by", required=True); p.add_argument("--reason", required=True); p.add_argument("--date")
    p = sub.add_parser("freeze"); common(p)
    p.add_argument("--track"); p.add_argument("--whole-file", action="store_true"); p.add_argument("--until", required=True)
    return ap


def main(argv=None):
    a = parser().parse_args(argv)
    path = Path(a.file)
    try:
        print(apply(path, a.op, a, dry_run=a.dry_run) or "(no change)")
    except BoxError as e:
        print(f"handoff_box: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
