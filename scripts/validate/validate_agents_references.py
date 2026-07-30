#!/usr/bin/env python3
"""Validate local markdown references in agent governance files.

Scope (extended 2026-07-30, audit D2/D13 follow-up):
- every role/shared file under agents/ (not just the fixed governance set)
- docs/guides/agent-workflows/*.md
- anchor-bearing links (path.md#anchor): the file must exist AND the anchor must
  match a heading in it (GitHub-style slug), so a deleted section is caught.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

FIXED_FILES = [
    ROOT / "agents" / "README.md",
    ROOT / "agents" / "AGENT_INSTRUCTIONS.md",
    ROOT / "docs" / "guides" / "agent-workflows" / "INDEX.md",
    ROOT / "docs" / "reference" / "agent-config" / "CLAUDE_MD_MATRIX.md",
    ROOT / ".claude" / "commands" / "agent-files.md",
    ROOT / ".claude" / "commands" / "agent-governance.md",
]


def scan_files() -> list[Path]:
    files = list(FIXED_FILES)
    files += sorted((ROOT / "agents").glob("*.md"))
    files += sorted((ROOT / "agents" / "shared").glob("*.md"))
    files += sorted((ROOT / "docs" / "guides" / "agent-workflows").glob("*.md"))
    seen: set[Path] = set()
    out: list[Path] = []
    for f in files:
        if f not in seen:
            seen.add(f)
            out.append(f)
    return out


CODE_REF = re.compile(r"`([^`]+\.md)`")
MD_LINK = re.compile(r"\[[^\]]+\]\(([^)#]+\.md)\)")
ANCHOR_LINK = re.compile(r"\[[^\]]+\]\(([^)#]+\.md)#([^)]+)\)")
HEADING = re.compile(r"^#{1,6}\s+(.*)$", re.MULTILINE)


def slugify(heading: str) -> str:
    # GitHub-style: lowercase, drop punctuation, EACH space becomes a hyphen
    # (so "A & B" -> "a--b" — do not collapse runs).
    s = re.sub(r"[*`_]", "", heading.strip().lower())
    s = re.sub(r"[^a-z0-9 -]", "", s)
    return s.replace(" ", "-")


def resolve(ref: str, src: Path) -> Path:
    if ref.startswith("http://") or ref.startswith("https://"):
        return Path("/dev/null")
    cleaned = ref.split(":", 1)[0]
    if "*" in cleaned or "<" in cleaned or ">" in cleaned:
        return Path("/dev/null")
    if cleaned.startswith("/"):
        return Path(cleaned)
    local_target = (src.parent / cleaned).resolve()
    if local_target.exists():
        return local_target
    return (ROOT / cleaned).resolve()


def main() -> int:
    missing: list[str] = []
    for path in scan_files():
        if not path.exists():
            missing.append(f"missing file: {path.relative_to(ROOT)}")
            continue
        text = path.read_text(encoding="utf-8")
        refs = set(CODE_REF.findall(text)) | set(MD_LINK.findall(text))
        for ref in sorted(refs):
            if ref == "SKILL.md":
                continue
            target = resolve(ref, path)
            if str(target) == "/dev/null":
                continue
            if not target.exists():
                missing.append(f"{path.relative_to(ROOT)} -> {ref}")
        for ref, anchor in sorted(set(ANCHOR_LINK.findall(text))):
            target = resolve(ref, path)
            if str(target) == "/dev/null":
                continue
            if not target.exists():
                missing.append(f"{path.relative_to(ROOT)} -> {ref}#{anchor}")
                continue
            slugs = {slugify(h) for h in HEADING.findall(target.read_text(encoding="utf-8"))}
            if anchor not in slugs:
                missing.append(
                    f"{path.relative_to(ROOT)} -> {ref}#{anchor} (anchor not found)"
                )

    if missing:
        print("agent reference validation failed")
        for item in missing:
            print("-", item)
        return 1

    print("agent reference validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
