#!/usr/bin/env python3
"""handoff_compact.py — fold old ticked boxes into one-line `### Done` summaries (handoff standard §3 / Stage C C4).

    python3 scripts/handoffs/handoff_compact.py <file.md>... --audit <closure_audit.json> [--days 30] [--dry-run]

A TOP-LEVEL ticked box (`- [x]`, no open descendant) whose tick date (`✅ YYYY-MM-DD`) is older than --days leaves its
place; one summary line `- [x] **<ID>** ✅ <date> <verdict>` lands under its track's `### Done` (created when missing).
`## History` never holds boxes, so the full block is written verbatim to `handoffs/archived/<slug>-history-<date>.md`
and History gets one pointer line.

SAFETY. Refuses to fold a box that `closure_audit.py` flagged (class a/b: a code reference that does not exist on
main): the audit JSON (`closure_audit.py --only <file> --json OUT`) is REQUIRED (`--no-audit` only with
`--dry-run`). Open boxes, roll-ups with open children and fenced examples are never touched. The ticked first line is
kept as the summary's first line minus the body (its id and tick suffix), so `flip_checkbox.parse_tick` still reads it.
Compaction runs only in the operator-invoked `/wrap-up` sweep (CLAUDE.md cadence), never per task.
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "coordination"))
import box_index as BI  # noqa: E402
import task_lint_core as L1  # noqa: E402
from flip_checkbox import parse_tick  # noqa: E402

_DATE = re.compile(r"✅\s*(\d{4}-\d{2}-\d{2})")


def flagged_texts(audit: dict, name: str) -> list[str]:
    return [" ".join(str(b.get("text", "")).split())[:100] for b in audit.get("flagged") or []
            if Path(str(b.get("handoff", ""))).name == name]


def compact(text: str, name: str, days: int, audit: dict | None, today: str | None = None):
    """(new text, archived blocks text, stats)."""
    now = datetime.date.fromisoformat(today) if today else datetime.date.today()
    lines = text.split("\n")
    sec = BI.sections(lines)
    flagged = flagged_texts(audit or {}, name)
    stats = {"folded": 0, "refused_audit": 0, "kept_recent": 0}
    folds = []                                # (start, end, track, summary)
    i = 0
    while i < len(lines):
        m = L1.CHECKBOX.match(lines[i])
        if not m or sec[i][4] or len(m.group(1)) != 0 or m.group(2) not in "xX":
            i += 1
            continue
        txt, _ = L1.block(lines, i)
        end = i + len(txt.split("\n"))
        if any(L1.CHECKBOX.match(l) and L1.CHECKBOX.match(l).group(2) == " " for l in lines[i + 1:end]):
            i = end
            continue                          # an open descendant: not foldable
        d = _DATE.findall(lines[i])
        if not d or (now - datetime.date.fromisoformat(d[-1])).days <= days:
            stats["kept_recent"] += 1
            i = end
            continue
        first = " ".join(lines[i].split())[:100]
        if any(f and (f[:60] in first or first[6:66] in f) for f in flagged):
            stats["refused_audit"] += 1
            i = end
            continue
        t = parse_tick(lines[i]) or {}
        bid = L1.head_id(lines[i]) or "—"
        summary = f"- [x] **{bid}** ✅ {t.get('date') or d[-1]} " + (
            f"[belief: {t['belief']}] " if t.get("belief") and not str(t["belief"]).startswith("no-belief") else "") + (
            " ".join(str(t.get("verdict") or "").split())[:160])
        folds.append((i, end, sec[i][0], summary.rstrip()))
        stats["folded"] += 1
        i = end
    if not folds:
        return text, "", stats
    archived = []
    drop = set()
    by_track: dict = {}
    for s, e, track, summ in folds:
        archived.extend(lines[s:e])
        drop.update(range(s, e))
        by_track.setdefault(track, []).append(summ)
    out = [l for k, l in enumerate(lines) if k not in drop]
    for track, summ in by_track.items():
        sec2 = BI.sections(out)
        t_lines = [k for k, x in enumerate(sec2) if x[0] == track] if track else list(range(len(out)))
        done = next((k for k in t_lines if re.match(r"^###\s+Done\b", out[k])), None)
        if done is None:
            end_t = (max(t_lines) + 1) if t_lines else len(out)
            out[end_t:end_t] = ["", "### Done", ""] + summ + [""]
        else:
            out[done + 1:done + 1] = [""] + summ
    return "\n".join(out), "\n".join(archived) + "\n", stats


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("files", nargs="+")
    ap.add_argument("--audit")
    ap.add_argument("--no-audit", action="store_true")
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    if not a.audit and not (a.no_audit and a.dry_run):
        print("handoff_compact: --audit <closure_audit.json> is required (run closure_audit.py --only <file> --json OUT)"
              "; --no-audit only with --dry-run", file=sys.stderr)
        return 2
    audit = json.load(open(a.audit)) if a.audit else {}
    today = datetime.date.today().isoformat()
    report = {}
    for f in a.files:
        p = Path(f)
        before = p.read_text(encoding="utf-8")
        new, arch, st = compact(before, p.name, a.days, audit, today)
        st.update(lines_before=before.count("\n"), lines_after=new.count("\n"))
        report[p.name] = st
        if a.dry_run or new == before:
            continue
        ap_ = REPO_ROOT / "handoffs" / "archived" / f"{p.stem}-history-{today}.md"
        ap_.parent.mkdir(parents=True, exist_ok=True)
        with open(ap_, "a", encoding="utf-8") as fh:
            fh.write(f"# {p.stem} — compacted ticked boxes ({today}, handoff_compact.py)\n\n{arch}\n")
        hist = f"- {today} compacted {st['folded']} ticked box(es) older than {a.days} d -> " \
               f"[{ap_.name}](../archived/{ap_.name}) (handoff_compact.py)"
        new = new.replace("\n## History\n", f"\n## History\n\n{hist}\n", 1) if "\n## History\n" in new \
            else new.rstrip("\n") + f"\n\n## History\n\n{hist}\n"
        p.write_text(new, encoding="utf-8")
    print(json.dumps(report, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
