#!/usr/bin/env python3
"""check_html_artifact_index.py — keep docs/reference/html-artifacts-index.md honest.

Owning doc:  docs/reference/html-artifacts-index.md (the catalog)
Companion:   docs/guides/agent-workflows/html-artifacts-runbook.md (how to add/update an entry)

Mirrors scripts/handoffs/index_state.py --check: a coverage gate, not a generator. The index is
short-lived and hand-edited (5 rows as of 2026-08-23), so there is nothing here to regenerate —
just a diff between what's on disk and what the index claims, in both directions:

    on disk, no index row   -> the exact "agents can't find our HTML artifacts" failure this
                                index exists to prevent
    index row, no file      -> a stale row pointing at something moved or deleted

Usage:
    python3 scripts/docs/check_html_artifact_index.py            # print the diff, exit 0
    python3 scripts/docs/check_html_artifact_index.py --check    # exit 1 if the diff is non-empty

Run --check before committing any change that adds, moves, or removes an HTML artifact (the
runbook's mandatory registration step).
"""

import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
INDEX_PATH = REPO_ROOT / "docs" / "reference" / "html-artifacts-index.md"

# Directory components pruned during the walk. Prefixes are repo-root-relative POSIX paths;
# names are pruned wherever they occur (so ".git" also catches nested worktree metadata).
EXCLUDED_PREFIXES = ("dashboard/static", "tmp", "worktrees")
EXCLUDED_NAMES = {".git", "node_modules", "__pycache__"}

LINK_TARGET_RE = re.compile(r"\]\(([^)]+\.html)\)")


def scan_html_files(repo_root: Path) -> set[str]:
    found = set()
    for dirpath, dirnames, filenames in os.walk(repo_root):
        rel_dir = Path(dirpath).relative_to(repo_root).as_posix()
        rel_dir = "" if rel_dir == "." else rel_dir

        dirnames[:] = [
            d
            for d in dirnames
            if d not in EXCLUDED_NAMES
            and not _is_excluded(f"{rel_dir}/{d}" if rel_dir else d)
        ]

        if _is_excluded(rel_dir):
            continue

        for name in filenames:
            if name.endswith(".html"):
                rel_path = f"{rel_dir}/{name}" if rel_dir else name
                found.add(rel_path)
    return found


def _is_excluded(rel_posix_path: str) -> bool:
    return any(
        rel_posix_path == prefix or rel_posix_path.startswith(prefix + "/")
        for prefix in EXCLUDED_PREFIXES
    )


def parse_index_paths(index_path: Path) -> set[str]:
    text = index_path.read_text()
    index_dir = index_path.parent
    resolved = set()
    for target in LINK_TARGET_RE.findall(text):
        abs_target = (index_dir / target).resolve()
        try:
            rel = abs_target.relative_to(REPO_ROOT.resolve())
        except ValueError:
            continue  # link escapes the repo — not our problem to resolve
        resolved.add(rel.as_posix())
    return resolved


def main() -> int:
    check_mode = "--check" in sys.argv[1:]

    if not INDEX_PATH.exists():
        print(f"FAIL: index not found at {INDEX_PATH.relative_to(REPO_ROOT)}")
        return 1

    on_disk = scan_html_files(REPO_ROOT)
    indexed = parse_index_paths(INDEX_PATH)

    unindexed = sorted(on_disk - indexed)
    stale = sorted(indexed - on_disk)

    if not unindexed and not stale:
        print(f"OK: {len(indexed)} HTML artifact(s), index matches disk.")
        return 0

    if unindexed:
        print(f"ON DISK, NO INDEX ROW ({len(unindexed)}):")
        for path in unindexed:
            print(f"  {path}")
    if stale:
        print(f"INDEX ROW, NO FILE ON DISK ({len(stale)}):")
        for path in stale:
            print(f"  {path}")

    if check_mode:
        return 1
    print("\n(run with --check to make this a non-zero-exit gate)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
