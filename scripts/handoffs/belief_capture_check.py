#!/usr/bin/env python3
"""Block handoff ticks that hide failed/unknown evidence or delete open work.

Receipts are host-local under /mnt/raid0/llm/tmp/compute-flags; --range permits
replaying a historical commit range on a host that has those receipts.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

DEFAULT_RECEIPTS = Path("/mnt/raid0/llm/tmp/compute-flags")
TICK = re.compile(r"^\s*[-*+]\s+\[([ xX])\]\s*(.*)$")
BELIEF = re.compile(r"\[belief:\s*([^\]]+)\]", re.I)
UNKNOWN = re.compile(r"\b(?:unknown\s+completion|completion\s+unknown|INCONCLUSIVE|NOT\s+MET|no\s+verdict|verdict\s+unknown)\b", re.I)
ACK = re.compile(r"\[receipt-ack:\s*[^\s\]]+\s+[A-Z][A-Z0-9_-]*\s+[—-]\s*[^\]]+\]", re.I)
MOVED = re.compile(r"\[moved:\s*[^\]]+\]", re.I)
DECLINED = re.compile(r"\[declined:\s*[^\]]*(?:/|\s)20\d{2}-\d{2}-\d{2}\s+[^\]]+\]", re.I)
SHA = re.compile(r"\b(?:sha(?:-?256)?[:= ]*)?[0-9a-f]{40,64}\b", re.I)
GIT_PATH = re.compile(r"(?:^|\s)(?:`)?(?:[\w.-]+/)+[\w./-]+(?:`)?")
BAD_RECEIPT = re.compile(r"\b(FAILED|INCONCLUSIVE|INCOMPLETE|PARTIAL|rc\s*=\s*[1-9]\d*)\b", re.I)
GOOD_RECEIPT = re.compile(r"\b(FINAL|COMPLETE)\b", re.I)


def git(repo: Path, *args: str) -> str:
    p = subprocess.run(["git", *args], cwd=repo, text=True, stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE)
    if p.returncode:
        raise RuntimeError(p.stderr.strip() or f"git {' '.join(args)} failed")
    return p.stdout


def parse_diff(text: str) -> tuple[dict[str, list[tuple[int, str]]], dict[str, list[str]]]:
    """Return added lines with new line numbers and removed source lines per file."""
    added: dict[str, list[tuple[int, str]]] = {}
    removed: dict[str, list[str]] = {}
    path = ""
    new_line = 0
    for line in text.splitlines():
        if line.startswith("+++ b/"):
            path = line[6:]
        elif line.startswith("@@"):
            m = re.search(r"\+(\d+)(?:,(\d+))?", line)
            if m:
                new_line = int(m.group(1))
        elif line.startswith("+") and not line.startswith("+++"):
            added.setdefault(path, []).append((new_line, line[1:]))
            new_line += 1
        elif line.startswith("-") and not line.startswith("---"):
            # The first dash is the diff marker; the remainder retains the
            # original markdown list marker (for example "-- [ ] ...").
            removed.setdefault(path, []).append(line[1:])
        elif not line.startswith("\\"):
            new_line += 1
    return added, removed


def normalized_task(text: str) -> str:
    m = TICK.match(text)
    body = m.group(2) if m else text
    body = re.sub(r"\[[^]]+\]", " ", body)
    return re.sub(r"\W+", " ", body.lower()).strip()


def receipt_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return [p for p in root.rglob("*") if p.is_file() and p.name.endswith((".FILED", ".FINAL", ".COMPLETE"))]


def cited_receipts(line: str, files: list[Path]) -> list[Path]:
    low = line.lower()
    return [p for p in files if p.stem.lower() in low or p.stem.lower().replace("-", "_") in low]


def names_run(line: str) -> bool:
    return bool(re.search(r"\b(?:run|receipt)\s*(?:[:#=]\s*)?[A-Za-z0-9][\w.-]+", line, re.I))


def completion_evidence(body: str) -> str:
    """Exclude task-specification wording from checks of the completion claim.

    Backlog titles often name the failure states a guard must reject. When a
    tick has the canonical dated completion marker, only the text after that
    marker asserts what was completed; scanning the title creates false
    positives for tasks such as LOOP-50 itself.
    """
    marker = re.search(r"✅\s*20\d{2}-\d{2}-\d{2}(?:\s*[—:-]\s*)?", body)
    return body[marker.end():] if marker else body


def receipt_state(paths: list[Path]) -> tuple[str | None, str | None]:
    if not paths:
        return None, None
    def order(p: Path):
        try:
            return p.stat().st_mtime_ns
        except OSError:
            return 0
    latest = max(paths, key=order)
    try:
        text = latest.read_text(errors="replace")
    except OSError:
        return "UNREADABLE", latest.stem
    terminal_line = text.splitlines()[0] if text.splitlines() else ""
    if latest.name.endswith((".FINAL", ".COMPLETE")) or GOOD_RECEIPT.search(terminal_line):
        return "COMPLETE", latest.stem
    m = re.search(r"\b(FAILED(?:-RUN)?|INCONCLUSIVE|INCOMPLETE|PARTIAL)\b|\brc\s*=\s*([1-9]\d*)", text, re.I)
    if m:
        return (m.group(1) or f"rc={m.group(2)}").upper(), latest.stem
    return "UNKNOWN", latest.stem


def check(repo: Path, diff: str, receipt_root: Path) -> list[str]:
    added, removed = parse_diff(diff)
    files = receipt_files(receipt_root)
    errors: list[str] = []
    for path, lines in added.items():
        for number, source in lines:
            tick = TICK.match(source)
            if not tick or tick.group(1).lower() != "x":
                continue
            body = tick.group(2)
            label = f"{path}:{number}"
            if DECLINED.search(body):
                errors.append(f"{label}: a declined task cannot be ticked [x]")
            if UNKNOWN.search(completion_evidence(body)):
                errors.append(f"{label}: tick line states unknown/inconclusive completion")
            belief = BELIEF.search(body)
            if belief:
                if not SHA.search(body) or not GIT_PATH.search(body):
                    errors.append(f"{label}: [belief:] tick needs a SHA and a repository path on its own line")
                matches = cited_receipts(body, files)
                if matches:
                    state, run_id = receipt_state(matches)
                    if state != "COMPLETE" and not ACK.search(body):
                        errors.append(f"{label}: receipt {run_id} is {state}; add [receipt-ack: <id> <CLASS> — reason] to acknowledge")
                elif names_run(body):
                    errors.append(f"{label}: [belief:] tick cites a run but no matching .FILED receipt exists")
            elif not DECLINED.search(body):
                # Result ticks can be explicitly classified as non-results.
                if re.search(r"\[no-belief:\s*[^]]+\]", body, re.I):
                    continue
    for path, old_lines in removed.items():
        new_lines = [line for _, line in added.get(path, [])]
        for old in old_lines:
            tick = TICK.match(old)
            if not tick or tick.group(1) != " ":
                continue
            key = normalized_task(old)
            old_ids = set(re.findall(r"\b[A-Z]{2,5}-\d{1,4}(?:-[A-Z0-9.]+)*\b", old))
            restored = any((key and key[:40] in normalized_task(new)) or
                           bool(old_ids & set(re.findall(r"\b[A-Z]{2,5}-\d{1,4}(?:-[A-Z0-9.]+)*\b", new))) for new in new_lines)
            # Cross-file move is evidenced by marker on the destination line.
            has_override = any(MOVED.search(line) or DECLINED.search(line) for line in new_lines)
            if not restored and not has_override:
                errors.append(f"{path}: removed open task without re-add, [moved: <path>], or [declined: <who/YYYY-MM-DD> reason]: {old.strip()[:100]}")
    return errors


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", type=Path, default=Path.cwd())
    ap.add_argument("--range", dest="commit_range", help="replay committed changes in A..B")
    ap.add_argument("--include-worktree", action="store_true", help="also inspect unstaged worktree changes with --range")
    ap.add_argument("--receipts", type=Path, default=DEFAULT_RECEIPTS)
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()
    repo = args.repo.resolve()
    try:
        if args.commit_range:
            diff = git(repo, "diff", "--no-ext-diff", "--unified=0", args.commit_range, "--", "handoffs/")
            if args.include_worktree:
                diff += git(repo, "diff", "--no-ext-diff", "--unified=0", "HEAD", "--", "handoffs/")
        else:
            diff = git(repo, "diff", "--cached", "--no-ext-diff", "--unified=0", "--", "handoffs/")
        errors = check(repo, diff, args.receipts)
    except (OSError, RuntimeError) as exc:
        print(f"belief-capture: cannot verify: {exc}", file=sys.stderr)
        return 2
    if args.report:
        print(f"belief-capture: {'blocked' if errors else 'clear'}; violations={len(errors)}")
    for error in errors:
        print(f"belief-capture: {error}", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
