#!/usr/bin/env python3
"""Validate CLAUDE.md governance matrix artifacts.

Strengthened 2026-07-30 (audit D11): besides checking the required governed rows, the
validator now DISCOVERS agent-policy files (CLAUDE.md / AGENTS.md at the root and in
repos/*/) and fails when a discovered file is not accounted for in the JSON matrix
(governed, child_repo_governed, upstream_unmanaged, related, or an excluded-class prefix).
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MATRIX_MD = ROOT / "docs/reference/agent-config/CLAUDE_MD_MATRIX.md"
MATRIX_JSON = ROOT / "docs/reference/agent-config/claude_md_matrix.json"

REQUIRED_GOVERNED = {
    "CLAUDE.md",
}

ACCOUNT_SECTIONS = (
    "governed",
    "child_repo_governed",
    "upstream_unmanaged",
    "related",
)


def discover() -> list[str]:
    found: list[str] = []
    for name in ("CLAUDE.md", "AGENTS.md"):
        if (ROOT / name).exists():
            found.append(name)
    repos = ROOT / "repos"
    if repos.is_dir():
        for repo in sorted(repos.iterdir()):
            if ".bak-" in repo.name or not repo.is_dir():
                continue
            for name in ("CLAUDE.md", "AGENTS.md"):
                if (repo / name).exists():
                    found.append(f"repos/{repo.name}/{name}")
    return found


def main() -> int:
    if not MATRIX_MD.exists():
        print("missing", MATRIX_MD.relative_to(ROOT))
        return 1
    if not MATRIX_JSON.exists():
        print("missing", MATRIX_JSON.relative_to(ROOT))
        return 1

    text = MATRIX_MD.read_text(encoding="utf-8")
    for p in REQUIRED_GOVERNED:
        if p not in text:
            print("missing from md matrix:", p)
            return 1

    data = json.loads(MATRIX_JSON.read_text(encoding="utf-8"))
    governed = {entry.get("path") for entry in data.get("governed", [])}
    missing = sorted(REQUIRED_GOVERNED - governed)
    if missing:
        print("missing from json matrix:", ", ".join(missing))
        return 1

    accounted = {
        entry.get("path")
        for section in ACCOUNT_SECTIONS
        for entry in data.get(section, [])
    }
    prefixes = [c.get("prefix", "") for c in data.get("excluded_classes", [])]
    unaccounted = [
        path
        for path in discover()
        if path not in accounted and not any(path.startswith(p) for p in prefixes if p)
    ]
    if unaccounted:
        print("agent-policy files not accounted for in the matrix:")
        for p in unaccounted:
            print("-", p)
        return 1

    md_missing = [p for p in accounted if p and p not in text]
    if md_missing:
        print("json rows absent from md matrix:", ", ".join(sorted(md_missing)))
        return 1

    print("claude md matrix validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
