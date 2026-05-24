#!/usr/bin/env python3
"""README freshness + discoverability check for owned repos.

Lightweight wrap-up helper. Flags any owned-repo README that:
  - has not been modified in >=THRESHOLD_DAYS days (commit-date, not mtime), OR
  - does not link to both `wiki/` AND `research/` (the two knowledge-base
    entry points a GitHub visitor needs to find compiled findings).

Exit 0 always. Prints a human-readable warning block to stdout when any
README fails one or more checks; prints nothing when all pass. Designed
to be inlined into the /wrap-up flow — the operator sees the warning
verbatim in the wrap-up output and decides whether to act.

Owned repos checked:
  - /mnt/raid0/llm/epyc-root            (this repo)
  - /mnt/raid0/llm/epyc-orchestrator
  - /mnt/raid0/llm/epyc-inference-research

External clones (llama.cpp fork, hermes-agent upstream, etc.) are NOT
checked — their READMEs are upstream artifacts.
"""

from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

THRESHOLD_DAYS = 60

OWNED_REPOS = [
    Path("/mnt/raid0/llm/epyc-root"),
    Path("/mnt/raid0/llm/epyc-orchestrator"),
    Path("/mnt/raid0/llm/epyc-inference-research"),
]

REQUIRED_LINKS = ("wiki/", "research/")


def last_commit_age_days(repo: Path, file_rel: str = "README.md") -> int | None:
    """Days since README was last touched by a commit. None if no git or no commit."""
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%ct", "--", file_rel],
            cwd=repo, capture_output=True, text=True, timeout=5,
        )
        if out.returncode != 0 or not out.stdout.strip():
            return None
        ts = int(out.stdout.strip())
        return (datetime.now(timezone.utc) - datetime.fromtimestamp(ts, tz=timezone.utc)).days
    except (subprocess.TimeoutExpired, ValueError, FileNotFoundError):
        return None


def missing_required_links(readme: Path) -> list[str]:
    """Returns the subset of REQUIRED_LINKS not present in the README body."""
    try:
        body = readme.read_text(errors="replace")
    except OSError:
        return list(REQUIRED_LINKS)
    return [link for link in REQUIRED_LINKS if link not in body]


def main() -> int:
    findings: list[tuple[Path, list[str]]] = []
    for repo in OWNED_REPOS:
        readme = repo / "README.md"
        if not readme.exists():
            findings.append((repo, [f"README.md missing entirely at {readme}"]))
            continue
        issues: list[str] = []
        age = last_commit_age_days(repo)
        if age is None:
            issues.append("could not determine last-commit age (no git history?)")
        elif age >= THRESHOLD_DAYS:
            issues.append(f"last commit was {age} days ago (>={THRESHOLD_DAYS}-day threshold)")
        missing = missing_required_links(readme)
        if missing:
            issues.append(
                f"missing knowledge-base links: {', '.join(missing)} "
                "(GitHub visitors cannot find wiki/research from this README)"
            )
        if issues:
            findings.append((repo, issues))

    if not findings:
        return 0

    print("## README freshness warnings")
    print()
    print(
        f"`check_readme_freshness.py` flagged {len(findings)} of "
        f"{len(OWNED_REPOS)} owned READMEs. Rewrites are tracked in the "
        "`handoffs/active/readme-refresh.md` handoff."
    )
    print()
    for repo, issues in findings:
        print(f"- **{repo.name}** (`{repo / 'README.md'}`)")
        for issue in issues:
            print(f"  - {issue}")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
