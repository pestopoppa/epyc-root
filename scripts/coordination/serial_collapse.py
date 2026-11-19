#!/usr/bin/env python3
"""Serial-collapse detector (FM-8, handoffs/active/coordination-and-churn-pipeline.md).

"This main is working serially" as an observable condition. Offline, zero-token,
read-only over Claude Code JSONL transcripts; it never blocks anything.

Definitions (fixed here so the number cannot drift):
  task boundary   a main-thread (``isSidechain`` false) ``type: user`` record that
                  carries a new instruction: ``origin.kind`` in {human, peer} when the
                  record has an origin; otherwise non-meta text that is not a
                  tool_result, task-notification, system-reminder, ``<bash-*>`` echo
                  or compaction continuation. Subagent completion notifications are
                  NOT boundaries (they would split one task into many and inflate
                  the flag). Each boundary opens one task segment.
  task segment    the main-thread records from one boundary to the next.
  completed task  a segment whose main thread issued >= ``--min-tools`` tool calls
                  (default 5): a one-line answer is not work that could fan out.
  fan-out width   number of ``Agent``/``Task`` tool_use blocks in the segment.
  serial collapse a run of >= ``--run`` (default 3) consecutive completed tasks
                  each with fan-out width 0. Segments that are not completed tasks
                  neither extend nor break a run.

Output: one JSON object per session (schema ``serial_collapse.v1``) with the
per-segment widths, the longest zero-width run and ``flag``. Malformed lines are
counted, never fatal.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCHEMA = "serial_collapse.v1"
DISPATCH_TOOLS = {"Agent", "Task"}


def _blocks(msg) -> list:
    content = msg.get("content") if isinstance(msg, dict) else None
    if isinstance(content, list):
        return [b for b in content if isinstance(b, dict)]
    return []


BOUNDARY_ORIGINS = {"human", "peer"}
NON_BOUNDARY_PREFIXES = ("<task-notification", "<system-reminder", "<bash-", "<local-command",
                         "This session is being continued")


def _text(msg: dict) -> str:
    content = msg.get("content")
    if isinstance(content, str):
        return content
    for b in _blocks(msg):
        if b.get("type") == "text":
            return str(b.get("text") or "")
    return ""


def is_boundary(rec: dict) -> bool:
    if rec.get("type") != "user" or rec.get("isSidechain"):
        return False
    msg = rec.get("message")
    if not isinstance(msg, dict):
        return False
    origin = rec.get("origin")
    if isinstance(origin, dict) and origin.get("kind"):
        return origin["kind"] in BOUNDARY_ORIGINS
    if rec.get("isMeta"):
        return False
    text = _text(msg).lstrip()
    return bool(text) and not text.startswith(NON_BOUNDARY_PREFIXES)


def analyze(path: Path, min_tools: int = 5, run: int = 3) -> dict:
    segments: list = []
    cur = None
    malformed = 0
    session_id = None
    try:
        fh = path.open(encoding="utf-8", errors="replace")
    except OSError as exc:
        return {"schema": SCHEMA, "path": str(path), "error": str(exc)}
    with fh:
        for line in fh:
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                malformed += 1
                continue
            if not isinstance(rec, dict):
                malformed += 1
                continue
            session_id = session_id or rec.get("sessionId")
            if is_boundary(rec):
                cur = {"tools": 0, "width": 0}
                segments.append(cur)
                continue
            if cur is None or rec.get("type") != "assistant" or rec.get("isSidechain"):
                continue
            for b in _blocks(rec.get("message")):
                if b.get("type") == "tool_use":
                    cur["tools"] += 1
                    if b.get("name") in DISPATCH_TOOLS:
                        cur["width"] += 1
    widths, longest, streak = [], 0, 0
    for seg in segments:
        if seg["tools"] < min_tools:
            continue
        widths.append(seg["width"])
        streak = streak + 1 if seg["width"] == 0 else 0
        longest = max(longest, streak)
    return {
        "schema": SCHEMA,
        "path": str(path),
        "session_id": session_id,
        "boundaries": len(segments),
        "completed_tasks": len(widths),
        "widths": widths,
        "longest_zero_run": longest,
        "flag": longest >= run,
        "malformed_lines": malformed,
        "params": {"min_tools": min_tools, "run": run},
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--files", nargs="+", type=Path)
    src.add_argument("--root", type=Path, help="directory of top-level session *.jsonl")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--min-tools", type=int, default=5)
    ap.add_argument("--run", type=int, default=3)
    ap.add_argument("--flagged-only", action="store_true")
    args = ap.parse_args(argv)
    files = args.files or sorted(args.root.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    if args.limit:
        files = files[: args.limit]
    for f in files:
        rep = analyze(f, args.min_tools, args.run)
        if args.flagged_only and not rep.get("flag"):
            continue
        sys.stdout.write(json.dumps(rep, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
