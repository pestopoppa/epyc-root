#!/usr/bin/env python3
"""new_handoff.py — create a handoff in the standard anatomy (handoff standard §2.1, Stage C C4).

    python3 scripts/handoffs/new_handoff.py <slug> --row <ID> --domain <domain> [--title T] [--track NAME]
                                             [--owner S] [--scratch PATH] [--priority HIGH|MEDIUM|LOW] [--dry-run]

Writes handoffs/active/<slug>.md with the fixed header keys (`**Status**`, `**Row**`, `**Domain**`, `**Created**`,
`**Owner**`, `**Scratch**`, `**Priority**`, `**Holds**`), `## Dispatch contract`, one `## Track:` with an empty
`### Backlog` and `### Done`, `## Findings` and `## History`, so `handoff_box.py add` has a home for its boxes. Refuses
an existing file. The index row is generated from the `**Row**`/`**Domain**` header (C6); until the hand-row drop
the owning session also adds the hand row (ruling (b)).
"""
from __future__ import annotations

import argparse
import datetime
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def render(slug, row, domain, title=None, track=None, owner=None, scratch=None, priority="MEDIUM", today=None,
           status="ACTIVE — created; first boxes pending") -> str:
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", slug):
        raise ValueError(f"slug {slug!r}: lowercase letters, digits and dashes only")
    if not re.fullmatch(r"[A-Z]{3}-\d+", row or ""):
        raise ValueError(f"--row {row!r}: an index row id like RTG-58")
    today = today or datetime.date.today().isoformat()
    title = title or slug.replace("-", " ").title()
    track = track or slug
    return (f"# {title}\n\n"
            f"**Status**: {status}\n"
            f"**Row**: {row}\n"
            f"**Domain**: {domain}\n"
            f"**Created**: {today}\n"
            f"**Owner**: {owner or 'none'}\n"
            f"**Scratch**: {scratch or f'/mnt/raid0/llm/tmp/{slug}/'}\n"
            f"**Priority**: {priority}\n"
            f"**Holds**: none\n\n"
            f"## Dispatch contract\n\n"
            f"- Boxes follow the box grammar (`docs/guides/agent-workflows/handoff-index-authoring.md` → *Box grammar*);\n"
            f"  add them with `scripts/handoffs/handoff_box.py add`, tick them with `churn/wrapup.py`.\n\n"
            f"## Track: {track}\n\n<!-- gate: none -->\n\n### Backlog\n\n### Done\n\n"
            f"## Findings\n\n## History\n\n- {today} created (new_handoff.py)\n")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("slug")
    ap.add_argument("--row", required=True)
    ap.add_argument("--domain", required=True)
    ap.add_argument("--title")
    ap.add_argument("--track")
    ap.add_argument("--owner")
    ap.add_argument("--scratch")
    ap.add_argument("--priority", default="MEDIUM", choices=("HIGH", "MEDIUM", "LOW"))
    ap.add_argument("--root", default=str(REPO_ROOT))
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    p = Path(a.root) / "handoffs" / "active" / f"{a.slug}.md"
    if p.exists():
        print(f"new_handoff: {p} exists; refusing", file=sys.stderr)
        return 1
    try:
        text = render(a.slug, a.row, a.domain, a.title, a.track, a.owner, a.scratch, a.priority)
    except ValueError as e:
        print(f"new_handoff: {e}", file=sys.stderr)
        return 2
    if a.dry_run:
        print(text)
        return 0
    p.write_text(text, encoding="utf-8")
    print(f"wrote {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
