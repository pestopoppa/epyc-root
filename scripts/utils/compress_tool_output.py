#!/usr/bin/env python3
"""Native tool output compression for context efficiency.

Reduces token consumption from verbose tool outputs (pytest, git, builds)
by 60-90% before they enter the LLM context window. Each command type
gets a specialized handler that preserves actionable information (errors,
failures, summaries) while stripping redundant success output.

Integration points:
  1. Claude Code PostToolUse hook (scripts/hooks/compress_bash_output.sh)
  2. Orchestrator REPL pipeline (helpers.py, before _spill_if_truncated)

Usage as CLI:
  echo "$output" | python compress_tool_output.py --command "pytest tests/"
"""
from __future__ import annotations

import re
from collections import Counter
from pathlib import PurePosixPath
from typing import Callable

# Minimum output length to trigger compression. Short outputs are returned as-is.
MIN_COMPRESS_CHARS = 500


def compress_tool_output(text: str, command: str) -> str:
    """Main entry point. Dispatches to per-command compressors.

    Returns compressed text, or original text unchanged if no handler
    matches or input is below the compression threshold.
    """
    if not text or len(text) < MIN_COMPRESS_CHARS:
        return text

    cmd = command.strip()
    for matcher, handler in _HANDLERS:
        if matcher(cmd):
            result = handler(text, cmd)
            # Only use compressed result if it's actually shorter
            if len(result) < len(text):
                return result
            return text
    return text


# ---------------------------------------------------------------------------
# Pytest
# ---------------------------------------------------------------------------

def _compress_pytest(text: str, command: str) -> str:
    """Failure focus: strip passing test lines, keep failures + summary."""
    lines = text.splitlines()

    summary_lines: list[str] = []
    failure_lines: list[str] = []
    in_failure_section = False
    in_summary_section = False

    for line in lines:
        if re.match(r"^={3,}\s*(FAILURES|ERRORS)\s*={3,}$", line):
            in_failure_section = True
            in_summary_section = False
            failure_lines.append(line)
            continue
        if re.match(r"^={3,}\s*short test summary info\s*={3,}$", line):
            in_failure_section = False
            in_summary_section = True
            summary_lines.append(line)
            continue
        if re.match(r"^={3,}\s*warnings summary\s*={3,}$", line):
            in_failure_section = False
            in_summary_section = False
            continue
        # Final result line (e.g., "=== 5 passed, 2 failed in 3.21s ===")
        if re.match(r"^={3,}\s*\d+\s+(passed|failed|error)", line):
            in_failure_section = False
            in_summary_section = False
            summary_lines.append(line)
            continue

        if in_failure_section:
            failure_lines.append(line)
        elif in_summary_section:
            summary_lines.append(line)

    # If no failures found, just return the final summary line
    if not failure_lines and not summary_lines:
        for line in reversed(lines):
            if re.match(r"^={3,}\s*\d+\s+(passed|failed|error)", line):
                return f"[compressed pytest output — {len(lines)} lines]\n{line}"
        return text

    parts: list[str] = []
    parts.append(f"[compressed pytest output — {len(lines)} lines original]")
    if failure_lines:
        parts.append("\n".join(failure_lines))
    if summary_lines:
        parts.append("\n".join(summary_lines))

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Cargo test
# ---------------------------------------------------------------------------

def _compress_cargo_test(text: str, command: str) -> str:
    """Failure focus for Rust test output."""
    lines = text.splitlines()

    failure_lines: list[str] = []
    summary_lines: list[str] = []
    in_failures = False

    for line in lines:
        if line.strip() == "failures:":
            in_failures = True
            failure_lines.append(line)
            continue
        if in_failures and line.startswith("test result:"):
            in_failures = False
            summary_lines.append(line)
            continue
        if line.startswith("test result:"):
            summary_lines.append(line)
            continue
        if in_failures:
            failure_lines.append(line)

    if not failure_lines and not summary_lines:
        for line in reversed(lines):
            if line.startswith("test result:"):
                return f"[compressed cargo test — {len(lines)} lines]\n{line}"
        return text

    parts = [f"[compressed cargo test — {len(lines)} lines original]"]
    if failure_lines:
        parts.append("\n".join(failure_lines))
    if summary_lines:
        parts.append("\n".join(summary_lines))
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# git status
# ---------------------------------------------------------------------------

def _compress_git_status(text: str, command: str) -> str:
    """Stats extraction: count by status category, list files if few."""
    lines = text.splitlines()

    porcelain_re = re.compile(r"^([ MADRCU?!]{2})\s+(.+)$")
    categories: dict[str, list[str]] = {}

    current_section = ""
    for line in lines:
        # Porcelain format
        m = porcelain_re.match(line)
        if m:
            status, path = m.group(1), m.group(2)
            xy = status.strip()
            if "?" in xy:
                cat = "untracked"
            elif "D" in xy:
                cat = "deleted"
            elif "A" in xy:
                cat = "added"
            elif "R" in xy:
                cat = "renamed"
            else:
                cat = "modified"
            categories.setdefault(cat, []).append(path)
            continue

        # Human-readable section headers
        if "Changes to be committed:" in line:
            current_section = "staged"
        elif "Changes not staged for commit:" in line:
            current_section = "unstaged"
        elif "Untracked files:" in line:
            current_section = "untracked"
        elif line.startswith("\t") and current_section:
            entry = line.strip()
            if current_section == "untracked":
                categories.setdefault("untracked", []).append(entry)
            else:
                m2 = re.match(r"([\w\s]+):\s+(.+)", entry)
                if m2:
                    action = m2.group(1).strip()
                    path = m2.group(2).strip()
                    categories.setdefault(action, []).append(path)

    if not categories:
        return text

    parts = ["git status:"]
    for cat, files in sorted(categories.items()):
        if len(files) <= 8:
            file_list = ", ".join(files)
            parts.append(f"  {len(files)} {cat}: {file_list}")
        else:
            parts.append(f"  {len(files)} {cat}")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# git diff
# ---------------------------------------------------------------------------

def _compress_git_diff(text: str, command: str) -> str:
    """Smart truncation: keep file headers + hunk headers + changed lines."""
    lines = text.splitlines()

    kept: list[str] = []
    files_seen = 0
    total_additions = 0
    total_deletions = 0

    for line in lines:
        if line.startswith("diff --git"):
            files_seen += 1
            kept.append(line)
            continue
        if line.startswith("index ") or line.startswith("---") or line.startswith("+++"):
            continue
        if line.startswith("@@"):
            kept.append(line)
            continue
        if line.startswith("+"):
            total_additions += 1
            kept.append(line)
            continue
        if line.startswith("-"):
            total_deletions += 1
            kept.append(line)
            continue

    result = "\n".join(kept)

    max_chars = 4000
    if len(result) > max_chars:
        result = result[:max_chars]
        result += f"\n[... truncated — {files_seen} files, +{total_additions}/-{total_deletions} lines total]"
    else:
        result = f"[git diff: {files_seen} files, +{total_additions}/-{total_deletions}]\n{result}"

    return result


# ---------------------------------------------------------------------------
# git log
# ---------------------------------------------------------------------------

def _compress_git_log(text: str, command: str) -> str:
    """Compact: hash + subject only."""
    lines = text.splitlines()

    # If already using a compact format (oneline/short), likely already compressed
    # Check if lines look like verbose format (has "commit <hash>" + "Author:" pattern)
    has_verbose_markers = any(l.startswith("Author:") or l.startswith("Date:") for l in lines[:20])
    if not has_verbose_markers:
        return text

    commits: list[str] = []
    current_hash = ""
    current_subject = ""

    for line in lines:
        m = re.match(r"^commit\s+([0-9a-f]{7,40})", line)
        if m:
            if current_hash and current_subject:
                commits.append(f"{current_hash[:8]} {current_subject}")
            current_hash = m.group(1)
            current_subject = ""
            continue
        if line.startswith("Author:") or line.startswith("Date:") or line.startswith("Merge:"):
            continue
        stripped = line.strip()
        if stripped and not current_subject:
            current_subject = stripped

    if current_hash and current_subject:
        commits.append(f"{current_hash[:8]} {current_subject}")

    if not commits:
        return text

    return f"[git log: {len(commits)} commits]\n" + "\n".join(commits)


# ---------------------------------------------------------------------------
# ls / tree
# ---------------------------------------------------------------------------

def _compress_ls(text: str, command: str) -> str:
    """Aggregate by extension, show counts."""
    lines = text.splitlines()

    entries: list[str] = []
    dirs = 0

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("total "):
            continue

        parts = stripped.split()
        if not parts:
            continue

        name = parts[-1]
        if stripped.startswith("d") and len(parts) >= 9:
            dirs += 1
            continue
        if name.endswith("/"):
            dirs += 1
            continue

        entries.append(name)

    if not entries and dirs == 0:
        return text

    ext_counts: Counter[str] = Counter()
    for name in entries:
        p = PurePosixPath(name)
        ext = p.suffix if p.suffix else "(no ext)"
        ext_counts[ext] += 1

    file_count = len(entries)
    top_exts = ext_counts.most_common(6)
    ext_summary = ", ".join(f"{count} {ext}" for ext, count in top_exts)
    if len(ext_counts) > 6:
        other = file_count - sum(c for _, c in top_exts)
        ext_summary += f", {other} other"

    result = f"[ls: {file_count} files ({ext_summary})"
    if dirs:
        result += f", {dirs} dirs"
    result += "]"
    return result


# ---------------------------------------------------------------------------
# Build output (cargo build, tsc, make, gcc, etc.)
# ---------------------------------------------------------------------------

def _compress_build_output(text: str, command: str) -> str:
    """Error focus: strip successful compilation, keep errors + context."""
    lines = text.splitlines()

    error_lines: list[str] = []
    warning_lines: list[str] = []
    summary_lines: list[str] = []
    error_count = 0
    warning_count = 0

    error_re = re.compile(r"(error\[|error:|Error:|ERROR:|FAILED)", re.IGNORECASE)
    warning_re = re.compile(r"(warning\[|warning:|Warning:|WARN:)", re.IGNORECASE)

    context_before: list[str] = []

    for i, line in enumerate(lines):
        if error_re.search(line):
            error_count += 1
            # Add context line only if it's meaningful (not a generic compilation line)
            if context_before and not re.match(r"^\s*(Compiling|Building|Linking)", context_before[-1]):
                error_lines.append(context_before[-1])
            error_lines.append(line)
            if i + 1 < len(lines):
                error_lines.append(lines[i + 1])
        elif warning_re.search(line):
            warning_count += 1
            warning_lines.append(line)
        elif re.match(r"^(Finished|Built|Compiling|Build succeeded|Build failed)", line):
            summary_lines.append(line)

        context_before = context_before[-1:] + [line]

    if error_count == 0 and warning_count == 0 and not summary_lines:
        return text

    parts = [f"[build output: {error_count} errors, {warning_count} warnings — {len(lines)} lines original]"]
    if error_lines:
        # Deduplicate preserving order
        seen: set[str] = set()
        deduped: list[str] = []
        for l in error_lines:
            if l not in seen:
                seen.add(l)
                deduped.append(l)
        parts.append("\n".join(deduped))
    if warning_lines and len("\n".join(warning_lines)) < 1000:
        parts.append("\n".join(warning_lines))
    elif warning_lines:
        parts.append(f"[{warning_count} warnings suppressed]")
    if summary_lines:
        parts.append("\n".join(summary_lines))
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

_HANDLERS: list[tuple[Callable[[str], bool], Callable[[str, str], str]]] = [
    (lambda cmd: "pytest" in cmd or "python -m pytest" in cmd, _compress_pytest),
    (lambda cmd: "cargo test" in cmd, _compress_cargo_test),
    (lambda cmd: cmd.startswith("git status") or ("git -c" in cmd and "status" in cmd), _compress_git_status),
    (lambda cmd: cmd.startswith("git diff") or ("git " in cmd and " diff" in cmd), _compress_git_diff),
    (lambda cmd: cmd.startswith("git log"), _compress_git_log),
    (lambda cmd: cmd.split("|")[0].strip().startswith("ls ") or cmd.strip() == "ls", _compress_ls),
    (lambda cmd: any(kw in cmd for kw in ("cargo build", "make ", "tsc", "gcc ", "g++ ", "cmake --build")), _compress_build_output),
]


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Compress tool output for context efficiency")
    parser.add_argument("--command", required=True, help="The command that produced the output")
    args = parser.parse_args()

    text = sys.stdin.read()
    print(compress_tool_output(text, args.command))
