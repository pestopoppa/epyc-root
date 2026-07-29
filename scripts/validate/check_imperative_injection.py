#!/usr/bin/env python3
"""Warn on instruction-injection shaped text in new research/handoff diffs.

The check is intentionally warn-mode by default. It targets newly added diff
lines in handoffs/ and research/ so existing historical material is not
retrofit-policed.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


WATCHED_PREFIXES = ("handoffs/", "research/")
QUARANTINE_HEADER_RE = re.compile(r"SOURCE-QUARANTINE:", re.IGNORECASE)
FENCE_RE = re.compile(r"^\s*```")
INTAKE_CONTEXT_RE = re.compile(
    r"(Research Intake Update|Recommended Actions|via research intake|intake-\d+)",
    re.IGNORECASE,
)
SOURCE_DIRECTIVE_RE = re.compile(
    r"\b("
    r"ignore\s+(?:all\s+)?(?:previous|above)\s+instructions|"
    r"disregard\s+(?:previous|above)\s+instructions|"
    r"follow\s+these\s+instructions|"
    r"system\s+prompt|developer\s+message|assistant\s+must|you\s+must|"
    r"do\s+not\s+tell|"
    r"exfiltrat\w*|leak\s+(?:the\s+)?(?:secret|credential|token)|"
    r"run\s+(?:rm|curl|wget|bash|sh|python|sudo)\b|"
    r"execute\s+(?:this|the|a)\s+(?:command|script)|"
    r"delete\s+(?:the\s+)?(?:repo|repository|files?|handoffs?)"
    r")\b",
    re.IGNORECASE,
)
ACTION_BULLET_RE = re.compile(
    r"^\s*(?:[-*]|\d+[.)])\s+"
    r"(?:Implement|Run|Execute|Install|Delete|Disable|Enable|Add|Create|"
    r"Modify|Patch|Update|Use|Follow|Obey|Ignore)\b",
    re.IGNORECASE,
)
ATTRIBUTION_RE = re.compile(
    r"\b(operator|human|review|candidate|proposal|proposed|requires approval|"
    r"approval required|do not execute|not an instruction|triage)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class WarningRecord:
    path: str
    line: int | None
    kind: str
    text: str


def _run_git_diff(cached: bool) -> str:
    cmd = ["git", "diff", "--unified=0"]
    if cached:
        cmd.append("--cached")
    cmd.extend(["--", *WATCHED_PREFIXES])
    proc = subprocess.run(cmd, check=False, text=True, capture_output=True)
    if proc.returncode not in (0, 1):
        raise RuntimeError(proc.stderr.strip() or "git diff failed")
    return proc.stdout


def _is_watched_path(path: str | None) -> bool:
    if not path:
        return False
    path = path.removeprefix("a/").removeprefix("b/")
    return path.startswith(WATCHED_PREFIXES)


def scan_diff(diff_text: str) -> list[WarningRecord]:
    warnings: list[WarningRecord] = []
    current_path: str | None = None
    new_line: int | None = None
    in_quarantine = False
    quarantine_fence_open = False
    intake_context_remaining = 0

    for raw in diff_text.splitlines():
        if raw.startswith("+++ "):
            marker = raw[4:].strip()
            current_path = marker.removeprefix("b/")
            new_line = None
            in_quarantine = False
            quarantine_fence_open = False
            intake_context_remaining = 0
            continue

        if raw.startswith("@@ "):
            match = re.search(r"\+(\d+)(?:,(\d+))?", raw)
            new_line = int(match.group(1)) - 1 if match else None
            in_quarantine = False
            quarantine_fence_open = False
            intake_context_remaining = 0
            continue

        if raw.startswith("--- ") or raw.startswith("diff ") or raw.startswith("index "):
            continue

        if raw.startswith("+") and not raw.startswith("+++ "):
            if new_line is not None:
                new_line += 1
            line = raw[1:]
            if not _is_watched_path(current_path):
                continue

            if QUARANTINE_HEADER_RE.search(line):
                in_quarantine = True
                quarantine_fence_open = False
                intake_context_remaining = max(intake_context_remaining, 8)

            if in_quarantine and FENCE_RE.match(line):
                quarantine_fence_open = not quarantine_fence_open
                if not quarantine_fence_open:
                    in_quarantine = False

            if in_quarantine and SOURCE_DIRECTIVE_RE.search(line):
                warnings.append(
                    WarningRecord(
                        current_path or "<unknown>",
                        new_line,
                        "quarantined-directive",
                        line.strip(),
                    )
                )

            if INTAKE_CONTEXT_RE.search(line):
                intake_context_remaining = 12

            if (
                intake_context_remaining > 0
                and ACTION_BULLET_RE.search(line)
                and not ATTRIBUTION_RE.search(line)
            ):
                warnings.append(
                    WarningRecord(
                        current_path or "<unknown>",
                        new_line,
                        "unattributed-intake-action",
                        line.strip(),
                    )
                )

            if intake_context_remaining > 0:
                intake_context_remaining -= 1
            continue

        if raw.startswith(" ") and new_line is not None:
            new_line += 1

    return warnings


def format_warnings(warnings: list[WarningRecord]) -> str:
    lines = [
        "[check_imperative_injection] warning: possible intake instruction-injection surface",
    ]
    for warning in warnings:
        loc = f"{warning.path}:{warning.line}" if warning.line else warning.path
        lines.append(f"  - {loc}: [{warning.kind}] {warning.text[:160]}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cached", action="store_true", help="scan staged diff")
    parser.add_argument("--warn-only", action="store_true", help="always exit 0")
    parser.add_argument("--strict", action="store_true", help="exit 1 when warnings are found")
    parser.add_argument("--diff-file", type=Path, help="read unified diff from this file")
    parser.add_argument("--stdin", action="store_true", help="read unified diff from stdin")
    args = parser.parse_args(argv)

    if args.diff_file:
        diff_text = args.diff_file.read_text(encoding="utf-8")
    elif args.stdin:
        diff_text = sys.stdin.read()
    else:
        diff_text = _run_git_diff(cached=args.cached)

    warnings = scan_diff(diff_text)
    if warnings:
        print(format_warnings(warnings), file=sys.stderr)
        if args.strict:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
