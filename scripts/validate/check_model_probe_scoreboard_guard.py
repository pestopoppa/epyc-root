#!/usr/bin/env python3
"""Require model-probe evidence to update the root scoreboard.

The research registry and active handoffs are useful context, but they are not
the glanceable source of model-probe status. This guard catches the repeated
failure mode where an agent adds fresh probe metrics or artifact paths to those
files without also updating docs/reference/model-probe-scoreboard.md.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT_REPO = Path("/mnt/raid0/llm/epyc-root")
RESEARCH_REPO = Path("/mnt/raid0/llm/epyc-inference-research")
SCOREBOARD_PATH = "docs/reference/model-probe-scoreboard.md"

RESEARCH_WATCHED_PATHS = (
    "orchestration/model_registry.yaml",
    "docs/reference/models",
)
ROOT_WATCHED_PATHS = (
    "handoffs/active",
    "progress",
)

STOP_LIST_RE = re.compile(
    r"\b("
    r"bonsai|q1_0|ternary|q2_g64|q2_0|nemotron[-_ ]?nano|"
    r"nemotron[-_ ]?diffusion|diffusion[-_ ]?14b|qwen3[-_ ]?vl|"
    r"supergemma|paddleocr"
    r")\b",
    re.IGNORECASE,
)
PROBE_EVIDENCE_RE = re.compile(
    r"("
    r"\bt/s\b|\bpp\d+\b|\btg\d+\b|llama[_-]?bench|summary\.json|"
    r"metrics_summary\.json|/data/|data/|throughput|decode|prompt t/s|"
    r"fixture|passed?\s+\d+/\d+|failed?\s+\d+/\d+"
    r")",
    re.IGNORECASE,
)
STEERING_RE = re.compile(
    r"\b("
    r"do not|stop|stopped|reopen only|blocked|quality[- ]blocked|"
    r"loader[- ]blocked|redirect|no speed rerun|not role[- ]ready"
    r")\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Finding:
    repo: str
    path: str
    line: int | None
    text: str
    reason: str


def _run_git(repo: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=False,
        text=True,
        capture_output=True,
    )


def _git_diff(repo: Path, mode: str, paths: tuple[str, ...]) -> str:
    args = ["diff", "--unified=0"]
    if mode == "staged":
        args.append("--cached")
    args.extend(["--", *paths])
    proc = _run_git(repo, args)
    if proc.returncode not in (0, 1):
        raise RuntimeError(proc.stderr.strip() or f"git diff failed in {repo}")
    return proc.stdout


def _git_changed_paths(repo: Path, mode: str) -> set[str]:
    args = ["diff", "--name-only", "-z"]
    if mode == "staged":
        args.append("--cached")
    proc = _run_git(repo, args)
    if proc.returncode not in (0, 1):
        raise RuntimeError(proc.stderr.strip() or f"git diff --name-only failed in {repo}")
    return {path for path in proc.stdout.split("\0") if path}


def scoreboard_changed(root_repo: Path, mode: str) -> bool:
    return SCOREBOARD_PATH in _git_changed_paths(root_repo, mode)


def _parse_unified_added_lines(diff_text: str) -> list[tuple[str, int | None, str]]:
    rows: list[tuple[str, int | None, str]] = []
    current_path: str | None = None
    new_line: int | None = None
    hunk_re = re.compile(r"@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")
    for raw in diff_text.splitlines():
        if raw.startswith("+++ b/"):
            current_path = raw.removeprefix("+++ b/")
            continue
        if raw.startswith("@@ "):
            match = hunk_re.match(raw)
            new_line = int(match.group(1)) if match else None
            continue
        if raw.startswith("+") and not raw.startswith("+++"):
            rows.append((current_path or "?", new_line, raw[1:]))
            if new_line is not None:
                new_line += 1
            continue
        if raw.startswith("-") and not raw.startswith("---"):
            continue
        if new_line is not None:
            new_line += 1
    return rows


def _line_is_probe_evidence(path: str, text: str) -> tuple[bool, str]:
    if not PROBE_EVIDENCE_RE.search(text):
        return (False, "")
    if path == SCOREBOARD_PATH:
        return (False, "")

    in_registry_or_model_docs = path == "orchestration/model_registry.yaml" or path.startswith(
        "docs/reference/models/"
    )
    in_root_handoff_or_progress = path.startswith("handoffs/active/") or path.startswith("progress/")

    if in_registry_or_model_docs:
        return (True, "model-probe evidence added outside scoreboard")

    if in_root_handoff_or_progress and STOP_LIST_RE.search(text) and not STEERING_RE.search(text):
        return (True, "stop-listed model evidence added outside scoreboard")

    return (False, "")


def scan_diff(repo_name: str, diff_text: str, *, scoreboard_is_changed: bool) -> list[Finding]:
    if scoreboard_is_changed:
        return []

    findings: list[Finding] = []
    for path, line, text in _parse_unified_added_lines(diff_text):
        is_probe, reason = _line_is_probe_evidence(path, text)
        if is_probe:
            findings.append(Finding(repo_name, path, line, text.strip(), reason))
    return findings


def check_repos(root_repo: Path, research_repo: Path, mode: str) -> list[Finding]:
    sb_changed = scoreboard_changed(root_repo, mode)
    findings: list[Finding] = []
    findings.extend(
        scan_diff(
            "epyc-inference-research",
            _git_diff(research_repo, mode, RESEARCH_WATCHED_PATHS),
            scoreboard_is_changed=sb_changed,
        )
    )
    findings.extend(
        scan_diff(
            "epyc-root",
            _git_diff(root_repo, mode, ROOT_WATCHED_PATHS),
            scoreboard_is_changed=sb_changed,
        )
    )
    return findings


def _format_findings(findings: list[Finding]) -> str:
    lines = [
        "[check_model_probe_scoreboard_guard] model-probe evidence needs scoreboard update",
        "",
        f"Required companion: {SCOREBOARD_PATH}",
        "",
    ]
    for finding in findings:
        loc = f"{finding.repo}:{finding.path}"
        if finding.line is not None:
            loc += f":{finding.line}"
        lines.extend(
            [
                f"- {loc}",
                f"  reason: {finding.reason}",
                f"  added: {finding.text[:220]}",
            ]
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root-repo", type=Path, default=ROOT_REPO)
    parser.add_argument("--research-repo", type=Path, default=RESEARCH_REPO)
    parser.add_argument(
        "--mode",
        choices=("staged", "worktree"),
        default="staged",
        help="Inspect staged changes by default; use worktree for local audits.",
    )
    args = parser.parse_args(argv)

    try:
        findings = check_repos(args.root_repo.resolve(), args.research_repo.resolve(), args.mode)
    except RuntimeError as exc:
        print(f"[check_model_probe_scoreboard_guard] {exc}", file=sys.stderr)
        return 2

    if findings:
        print(_format_findings(findings), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
