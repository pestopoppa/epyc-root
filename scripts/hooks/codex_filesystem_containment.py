#!/usr/bin/env python3
"""Codex PreToolUse hook — bridges codex's hook JSON to the ONE shared scanner
(scripts/hooks/filesystem_containment_scan.py), same rules as every other
harness surface (INC-20260823-filesystem-containment-gap: the guard was built
in two surfaces with duplicated hand-written rules; codex was uncovered).

WIRED in ~/.codex/config.toml:

    [[hooks.PreToolUse]]
    command = "python3 /workspace/scripts/hooks/codex_filesystem_containment.py"
    timeout_sec = 10
    status_message = "filesystem containment"

CODEX WIRE FORMAT (verified against the local codex 0.147.0 binary's embedded
JSON schemas, 2026-08-23 — not guessed):

  Input on stdin (pre-tool-use.command.input):
    {"hook_event_name": "PreToolUse", "tool_name": "shell",
     "tool_input": {"command": "..."}, "cwd": "...",
     "permission_mode": "...", "session_id": "...", "model": "...",
     "tool_use_id": "...", "transcript_path": null, "turn_id": "..."}

  Blocking: exit 2 with a blocking reason on stderr (the binary enforces
  "PreToolUse hook exited with code 2 but did not write a blocking reason to
  stderr"); an allow decision is exit 0. This hook only ever emits those two.

SCOPE: any tool_input carrying a shell ``command`` is scanned with the full
scanner (CLASS A + CLASS B, cwd-aware); any tool_input carrying a ``file_path``
is checked with ``--check-path`` semantics. codex's apply_patch payloads are
NOT shell commands and are not scanned — that is a stated residual gap (the
sandbox layer is codex's own; this host runs sandbox_mode =
"danger-full-access", so the gap note in the containment guide stands).

EPYC_FS_ACK is read from the scanner's environment — the codex process
environment, which an agent's shell export cannot reach — so the one-off
operator override is strictly operator-set, same as every other surface.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import filesystem_containment_scan as fs  # noqa: E402 — the ONE truth


def main() -> int:
    data = sys.stdin.read()
    if not data.strip():
        return 0  # not a hook payload — nothing to scan
    try:
        payload = json.loads(data)
    except json.JSONDecodeError:
        return 0  # not the documented codex envelope; do not brick the session
    if not isinstance(payload, dict):
        return 0
    if payload.get("hook_event_name") not in (None, "PreToolUse"):
        return 0
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return 0
    cwd = payload.get("cwd") if isinstance(payload.get("cwd"), str) else None

    command = tool_input.get("command")
    if isinstance(command, str) and command.strip():
        verdict = fs.scan_command(command, cwd=cwd)
        if verdict.get("verdict") == "allowed":
            return 0
        print(verdict.get("detail", "refused by the filesystem-containment scanner"),
              file=sys.stderr)
        return 2

    file_path = tool_input.get("file_path")
    if isinstance(file_path, str) and file_path.strip():
        verdict = fs.check_path(file_path, cwd=cwd)
        if verdict.get("verdict") == "allowed":
            return 0
        print(verdict.get("detail", "refused by the filesystem-containment scanner"),
              file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
