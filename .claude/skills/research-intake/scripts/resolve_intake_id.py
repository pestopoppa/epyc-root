#!/usr/bin/env python3
"""Resolve an intake id that no longer exists in the index.

    resolve_intake_id.py intake-797
    resolve_intake_id.py --audit          # every absorbed id, and where it is still referenced
    resolve_intake_id.py --write-map      # regenerate research/intake_merge_map.md
    resolve_intake_id.py --check-map      # fail if that file is stale (CI / validation)

WHY THIS EXISTS. Merging a duplicate away removes its id permanently, and renumbering to close the
gap is refused (schema § ID Sequencing) because a reused id would make old references resolve to
the WRONG entry rather than to nothing. That argument only holds if "nothing" is recoverable — a
reader who finds `intake-797` in a July progress log has to be able to learn where it went. The
survivor records what it absorbed in `merged_ids`; this indexes that the other way round, which is
the direction the question is actually asked in.

Deliberately NOT a rewriter. On 2026-08-10 the live references to absorbed ids were inspected and
several turned out to be things that must not be repointed: `handoffs/active/mi210-speed-campaign-
summary.md` cites intake-797 inside a correction recording that intake-797 was a *mis-stamped* id,
and `research/recommendations.yaml` uses "intake-779 through intake-797" as a range naming a
historical ingest batch. A bulk repoint would have corrupted both. Resolution is a lookup a reader
performs, not an edit a script applies.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[4]
INDEX = ROOT / "research" / "intake_index.yaml"
MAP = ROOT / "research" / "intake_merge_map.md"


def load() -> tuple[dict, dict]:
    entries = yaml.safe_load(INDEX.read_text()) or []
    live = {e["id"]: e for e in entries if isinstance(e.get("id"), str)}
    absorbed: dict[str, str] = {}
    for e in entries:
        for mid in e.get("merged_ids") or []:
            if isinstance(mid, str):
                absorbed[mid] = e["id"]
    return live, absorbed


def _why(survivor: dict, wanted: str) -> str:
    for note in survivor.get("merge_history") or []:
        if wanted in str(note):
            return str(note)
    return ""


def resolve(wanted: str) -> int:
    live, absorbed = load()
    if wanted in live:
        print(f"{wanted}: LIVE — {str(live[wanted].get('title'))[:90]}")
        return 0
    if wanted in absorbed:
        keeper = absorbed[wanted]
        print(f"{wanted}: MERGED into {keeper}")
        print(f"  {keeper}: {str(live[keeper].get('title'))[:90]}")
        note = _why(live[keeper], wanted)
        if note:
            print(f"  why: {note}")
        print("  NOTE: an older document citing this id may have meant the pre-merge record. "
              "Check the context before repointing it — some references name the id precisely "
              "because it was wrong.")
        return 0
    print(f"{wanted}: UNKNOWN — not in the index and not recorded as merged into anything.")
    print("  Either it never existed (a typo, or an id invented by a model) or it was removed "
          "without a merge record, which is itself a defect worth reporting.")
    return 1


def audit() -> int:
    live, absorbed = load()
    if not absorbed:
        print("no absorbed ids recorded")
        return 0
    out = subprocess.run(
        ["git", "grep", "-l", "-E", r"intake-[0-9]{1,4}", "--", "."],
        capture_output=True, text=True, cwd=ROOT,
    ).stdout.split()
    print(f"{len(absorbed)} absorbed id(s):")
    for gone, keeper in sorted(absorbed.items()):
        hits = []
        pattern = re.compile(rf"\b{re.escape(gone)}\b")
        for path in out:
            try:
                text = (ROOT / path).read_text(errors="ignore")
            except OSError:
                continue
            n = len(pattern.findall(text))
            if n:
                hits.append((n, path))
        total = sum(n for n, _ in hits)
        print(f"\n  {gone} -> {keeper}   ({total} reference(s) in {len(hits)} file(s))")
        for n, path in sorted(hits, reverse=True)[:8]:
            print(f"      {n:3}  {path}")
    print("\nReferences are NOT errors. Historical records naming a merged id are correct as "
          "written; this is a map, not a work list.")
    return 0


def render_map() -> str:
    """The persisted redirect table, generated from `merged_ids`.

    Generated rather than hand-kept: a redirect map that drifts is worse than none, because it
    answers confidently and wrongly. `merged_ids` on the survivors is the source of truth; this
    file is the same data indexed the way the question gets asked -- someone lands on a dead id
    from a progress log and needs to know where it went.
    """
    live, absorbed = load()
    lines = [
        "# Intake merge map — where a removed id went",
        "",
        "**Generated. Do not hand-edit** — run",
        "`.claude/skills/research-intake/scripts/resolve_intake_id.py --write-map`.",
        "Source of truth is the `merged_ids` field on each surviving entry.",
        "",
        "An intake id is never reused and never renumbered (schema § ID Sequencing), so a merged",
        "id resolves to nothing rather than to the wrong paper. This table is what makes that",
        "recoverable: land on a dead id in an old log, look it up here.",
        "",
        "**A reference to a removed id is not automatically wrong.** Historical records naming a",
        "merged id are correct as written, and some name it *because* it was a mis-stamp — the",
        "MI210 speed-campaign handoff cites intake-797 inside a correction saying intake-797 was",
        "the wrong id for KernelBench. Read the context before repointing anything.",
        "",
    ]
    if not absorbed:
        lines += ["*No entries have been merged.*", ""]
        return "\n".join(lines)

    lines += ["| Removed | Resolves to | Title | Merged |", "|---|---|---|---|"]
    for gone, keeper in sorted(absorbed.items(), key=lambda kv: int(kv[0].split("-")[1])):
        title = str(live[keeper].get("title") or "").replace("|", "\\|")[:70]
        note = _why(live[keeper], gone)
        when = ""
        m = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", note)
        if m:
            when = m.group(1)
        lines.append(f"| `{gone}` | [`{keeper}`](intake_index.yaml) | {title} | {when} |")
    lines.append("")
    return "\n".join(lines)


def write_map() -> int:
    MAP.write_text(render_map())
    print(f"wrote {MAP.relative_to(ROOT)}")
    return 0


def check_map() -> int:
    want = render_map()
    have = MAP.read_text() if MAP.exists() else ""
    if want == have:
        print(f"{MAP.relative_to(ROOT)}: current")
        return 0
    print(f"{MAP.relative_to(ROOT)}: STALE — regenerate with --write-map", file=sys.stderr)
    return 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("intake_id", nargs="?", help="e.g. intake-797")
    ap.add_argument("--audit", action="store_true",
                    help="list every absorbed id and where it is still referenced")
    ap.add_argument("--write-map", action="store_true",
                    help="regenerate research/intake_merge_map.md")
    ap.add_argument("--check-map", action="store_true",
                    help="exit non-zero if the map is stale")
    args = ap.parse_args()
    if args.write_map:
        return write_map()
    if args.check_map:
        return check_map()
    if args.audit:
        return audit()
    if not args.intake_id:
        ap.error("give an intake id, or --audit")
    return resolve(args.intake_id)


if __name__ == "__main__":
    raise SystemExit(main())
