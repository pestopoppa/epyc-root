#!/usr/bin/env python3
"""Generate site_src/stories/recent-results.md from progress/ entries.

Walks the last 90 days of progress/YYYY-MM/YYYY-MM-DD*.md files, extracts
each one's H1 title and first non-heading paragraph, and writes a curated
"Recent results" page with links back to the GitHub source.

The progress directory itself isn't published to the site (operationally
noisy), but the *summaries* are valuable as a chronology of what's landed
recently. This script bridges the two.

Run after scripts/docs/build-site-src.sh and before mkdocs build.
"""
from __future__ import annotations

import os
import re
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SITE_SRC = ROOT / "site_src"
PROGRESS = ROOT / "progress"
OUT = SITE_SRC / "stories" / "recent-results.md"

GH_ROOT = "https://github.com/pestopoppa/epyc-root/blob/main"
WINDOW_DAYS = 90


def first_paragraph(text: str) -> str:
    """Return the first non-heading, non-empty paragraph, collapsed to one line."""
    in_fence = False
    lines: list[str] = []
    for raw in text.splitlines()[1:]:  # skip H1
        stripped = raw.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if stripped.startswith("#"):
            if lines:
                break
            continue
        if not stripped:
            if lines:
                break
            continue
        if stripped.startswith(("|", "-", "*", "1.", "2.", ">")):
            if lines:
                break
            continue
        lines.append(stripped)
        if len(" ".join(lines)) > 300:
            break
    return re.sub(r"\s+", " ", " ".join(lines))[:280]


def extract_h1(text: str) -> str:
    for line in text.splitlines():
        m = re.match(r"^#\s+(.+)", line)
        if m:
            return m.group(1).strip()
    return ""


def collect_entries() -> list[dict]:
    cutoff = date.today() - timedelta(days=WINDOW_DAYS)
    entries: list[dict] = []
    if not PROGRESS.exists():
        return entries
    for month_dir in sorted(PROGRESS.glob("[0-9][0-9][0-9][0-9]-[0-9][0-9]"), reverse=True):
        for path in sorted(month_dir.glob("*.md"), reverse=True):
            stem = path.stem
            m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", stem)
            if not m:
                continue
            y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
            try:
                entry_date = date(y, mo, d)
            except ValueError:
                continue
            if entry_date < cutoff:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            title = extract_h1(text)
            synopsis = first_paragraph(text)
            gh_path = path.relative_to(ROOT).as_posix()
            entries.append({
                "date": entry_date,
                "stem": stem,
                "title": title,
                "synopsis": synopsis,
                "gh_url": f"{GH_ROOT}/{gh_path}",
            })
    entries.sort(key=lambda e: (e["date"], e["stem"]), reverse=True)
    return entries


def write_page(entries: list[dict]) -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Recent results",
        "",
        f"Auto-generated chronology of the last {WINDOW_DAYS} days of progress entries. ",
        "Each row links to the full session log on GitHub (the `progress/` directory itself isn't published to the site).",
        "",
        "For the curated narrative version of what's landed, see [Stories](index.md). For active work, see [What we're investigating now](investigating-now.md).",
        "",
        "| Date | Session | Synopsis |",
        "|---|---|---|",
    ]
    for e in entries:
        date_str = e["date"].isoformat()
        # Strip leading date prefix from the H1 title so it doesn't repeat
        title = re.sub(r"^\d{4}-\d{2}-\d{2}\s*[—-]\s*", "", e["title"]).strip()
        if not title:
            title = e["stem"]
        synopsis = e["synopsis"].replace("|", "\\|")
        lines.append(f"| {date_str} | [{title}]({e['gh_url']}) | {synopsis} |")
    lines.append("")
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Recent results: wrote {len(entries)} entries to {OUT.relative_to(ROOT)}")


def main() -> int:
    entries = collect_entries()
    write_page(entries)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
