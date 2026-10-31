#!/usr/bin/env python3
"""PreToolUse hook (matcher ``Agent|Task``): audit main-thread subagent dispatches.

FM-8 (handoffs/active/fleet-fanout-measurement.md). WARN MODE ONLY: this hook
always exits 0. It never blocks a dispatch, including on malformed input or an
internal error. Enforce mode is a later, separate operator decision.

Acts only on the MAIN thread: a hook payload carrying ``agent_id`` fires inside a
subagent and is skipped without logging.

Findings (each is a warning, never a denial):
  no_model_non_project_type  no ``model`` and ``subagent_type`` is not a project
                             type (``.claude/agents/<name>.md`` with ``model:``
                             frontmatter); the dispatch silently inherits the
                             main thread's (most expensive) model.
  fork_cheaper_model         a ``fork`` was given a cheaper ``model``; a fork runs
                             on its parent's model, so the override is ignored.
                             A fork with no ``model`` is correct and not flagged.

Every handled dispatch appends one JSONL line to ``logs/agent_dispatch_audit.jsonl``
(override: ``AGENT_DISPATCH_AUDIT_LOG``) carrying this file's sha256 as ``hook_sha``.
The prompt text is never logged.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import sys
from pathlib import Path

MODE = "warn"
HOOK_PATH = Path(__file__).resolve()
CHEAPER_MODEL_MARKERS = ("haiku", "sonnet")
DISPATCH_TOOLS = ("Agent", "Task")


def hook_sha() -> str:
    try:
        return hashlib.sha256(HOOK_PATH.read_bytes()).hexdigest()
    except OSError:
        return "unreadable"


def project_dir() -> Path:
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    return Path(env) if env else HOOK_PATH.parents[2]


def audit_log_path() -> Path:
    env = os.environ.get("AGENT_DISPATCH_AUDIT_LOG")
    return Path(env) if env else project_dir() / "logs" / "agent_dispatch_audit.jsonl"


def frontmatter(path: Path) -> dict:
    """Minimal ``key: value`` frontmatter reader (no YAML dependency)."""
    out: dict = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return out
    if not lines or lines[0].strip() != "---":
        return out
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" in line and not line.startswith((" ", "\t", "#")):
            key, _, value = line.partition(":")
            out[key.strip()] = value.strip().strip("'\"")
    return out


def project_types() -> dict:
    """Map project subagent name -> declared model (only types that declare one)."""
    types: dict = {}
    agents_dir = project_dir() / ".claude" / "agents"
    try:
        files = sorted(agents_dir.glob("*.md"))
    except OSError:
        return types
    for path in files:
        meta = frontmatter(path)
        if meta.get("model"):
            types[meta.get("name") or path.stem] = meta["model"]
    return types


def classify(tool_input: dict, types: dict) -> list:
    """Return the list of warning codes for one main-thread dispatch."""
    subagent_type = tool_input.get("subagent_type")
    model = tool_input.get("model")
    is_fork = isinstance(subagent_type, str) and subagent_type.lower() == "fork"
    findings = []
    if is_fork:
        if isinstance(model, str) and any(m in model.lower() for m in CHEAPER_MODEL_MARKERS):
            findings.append("fork_cheaper_model")
    elif not model and not (isinstance(subagent_type, str) and subagent_type in types):
        findings.append("no_model_non_project_type")
    return findings


NOTES = {
    "no_model_non_project_type": (
        "dispatch has no `model` and is not a project type "
        "(explorer/runner/clerk): it will inherit the main thread's model. "
        "Pass `model` or use a project type."
    ),
    "fork_cheaper_model": (
        "a `fork` runs on its parent's model; the cheaper `model` you passed is "
        "ignored. Use a typed subagent to get a cheaper tier."
    ),
}


def append_audit(record: dict) -> None:
    path = audit_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")


def base_record(verdict: str, findings: list) -> dict:
    return {
        "ts": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hook": "check_agent_dispatch",
        "hook_sha": hook_sha(),
        "mode": MODE,
        "verdict": verdict,
        "findings": findings,
    }


def handle(raw: str) -> None:
    try:
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError("payload is not an object")
        tool_input = payload.get("tool_input")
        if not isinstance(tool_input, dict):
            raise ValueError("tool_input missing or not an object")
    except (ValueError, TypeError) as exc:
        record = base_record("malformed", ["malformed_input"])
        record["error"] = str(exc)[:200]
        record["input_bytes"] = len(raw.encode("utf-8", "replace"))
        append_audit(record)
        sys.stderr.write(f"[check_agent_dispatch] WARN malformed hook input allowed: {exc}\n")
        return

    if payload.get("agent_id"):
        return  # inside a subagent: main thread only

    tool_name = payload.get("tool_name")
    if tool_name is not None and tool_name not in DISPATCH_TOOLS:
        return  # mis-registered matcher: not a dispatch

    findings = classify(tool_input, project_types())
    record = base_record("warn" if findings else "ok", findings)
    record.update(
        tool_name=tool_name,
        subagent_type=tool_input.get("subagent_type"),
        model=tool_input.get("model"),
        session_id=payload.get("session_id"),
    )
    append_audit(record)
    for code in findings:
        sys.stderr.write(f"[check_agent_dispatch] WARN {code}: {NOTES[code]}\n")


def main() -> int:
    try:
        handle(sys.stdin.read())
    except Exception as exc:  # warn mode must never block a dispatch
        try:
            sys.stderr.write(f"[check_agent_dispatch] internal error allowed: {exc!r}\n")
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
