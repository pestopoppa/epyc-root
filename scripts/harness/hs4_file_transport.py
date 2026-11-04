"""Transport plumbing for HS-4 file trials; live execution is currently refused.

The isolation verifier is intentionally not implemented here. It must be
replaced by the scoring owner with an actual agent-and-grader boundary proof;
the prepared workspace, a certificate supplied by a caller, or a synthetic
test is not such a proof. Both transports fail closed before any I/O until then.
"""
from __future__ import annotations

import json
import os
import signal
import subprocess
import time
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from scripts.harness.hs4_file_adapters import opencode_session, repl_response


def _require_live_isolation() -> None:
    raise RuntimeError("live agent/grader isolation is not implemented or verified")


def _identity(pid: int) -> tuple[str, int, int] | None:
    try:
        fields = Path(f"/proc/{pid}/stat").read_text().rsplit(") ", 1)[1].split()
        return fields[0], int(fields[1]), int(fields[19])
    except (OSError, ValueError, IndexError):
        return None


def _children(root: int, captured: dict[int, int]) -> None:
    """Capture descendants by parent PID and birth time, never by name."""
    nodes: dict[int, tuple[str, int, int]] = {}
    for entry in Path("/proc").iterdir():
        if entry.name.isdecimal():
            pid = int(entry.name)
            record = _identity(pid)
            if record:
                nodes[pid] = record
    frontier = [root]
    while frontier:
        parent = frontier.pop()
        for pid, (_, ppid, birth) in nodes.items():
            if ppid == parent and pid not in captured:
                captured[pid] = birth
                frontier.append(pid)


def _signal_owned(pid: int, birth: int, sig: int) -> None:
    current = _identity(pid)
    if current is not None and current[2] == birth and current[0] != "Z":
        try:
            os.kill(pid, sig)
        except ProcessLookupError:
            pass


def _terminate_owned_tree(pid: int, birth: int | None) -> dict[str, Any]:
    """Stop, capture and drain the observed descendants of this exact child.

    A process that escaped before capture cannot be proven absent by a /proc
    ancestry scan. Report only captured identities; a stronger containment
    mechanism remains required before enabling live runs.
    """
    if birth is None:
        return {"captured": [], "remaining": None, "scope": "identity unavailable"}
    captured = {pid: birth}
    _signal_owned(pid, birth, signal.SIGSTOP)
    for _ in range(4):
        before = len(captured)
        for parent, start in list(captured.items()):
            record = _identity(parent)
            if record is not None and record[2] == start:
                _children(parent, captured)
        for child, start in captured.items():
            _signal_owned(child, start, signal.SIGSTOP)
        if len(captured) == before:
            break
    for child, start in reversed(list(captured.items())):
        _signal_owned(child, start, signal.SIGTERM)
        _signal_owned(child, start, signal.SIGCONT)
    deadline = time.monotonic() + 1
    while time.monotonic() < deadline:
        if all((record := _identity(child)) is None or record[0] == "Z" or record[2] != start
               for child, start in captured.items()):
            break
        time.sleep(0.02)
    for child, start in reversed(list(captured.items())):
        _signal_owned(child, start, signal.SIGKILL)
    deadline = time.monotonic() + 1
    while time.monotonic() < deadline:
        remaining = [child for child, start in captured.items()
                     if (record := _identity(child)) is not None and record[0] != "Z" and record[2] == start]
        if not remaining:
            break
        time.sleep(0.02)
    return {"captured": [{"pid": child, "start_ticks": start} for child, start in captured.items()],
            "remaining": remaining, "scope": "captured descendants; escaped processes unknown"}


def run_repl(url: str, body: dict[str, Any], *, timeout_s: float) -> dict[str, Any]:
    """POST an exact prepared request after the isolation gate is implemented."""
    _require_live_isolation()
    if not url.startswith(("http://", "https://")) or timeout_s <= 0:
        raise ValueError("explicit HTTP endpoint and positive timeout required")
    request_body = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    request = Request(url.rstrip("/") + "/chat", data=request_body,
                      headers={"Content-Type": "application/json"}, method="POST")
    result: dict[str, Any] = {"request_body": request_body.decode(), "response_body": None,
                              "http_status": None, "observation": None, "error": None}
    try:
        with urlopen(request, timeout=timeout_s) as response:
            raw = response.read()
            result["http_status"] = response.status
        result["response_body"] = raw.decode()
        result["observation"] = repl_response(json.loads(raw))
    except (OSError, UnicodeError, ValueError) as exc:
        result["error"] = type(exc).__name__
    return result


def _process(argv: list[str], *, cwd: Path, env: dict[str, str], stdin: str,
             timeout_s: float) -> dict[str, Any]:
    proc = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, start_new_session=True)
    identity = _identity(proc.pid)
    start_ticks = identity[2] if identity else None
    try:
        stdout, stderr = proc.communicate(stdin, timeout=timeout_s)
    except subprocess.TimeoutExpired:
        drain = _terminate_owned_tree(proc.pid, start_ticks)
        try:
            stdout, stderr = proc.communicate(timeout=2)
        except subprocess.TimeoutExpired:
            # Escaped or unidentifiable pipe holder: preserve an explicit failure.
            return {"pid": proc.pid, "start_ticks": start_ticks, "returncode": proc.returncode,
                    "stdout": None, "stderr": None, "timed_out": True, "drain": drain,
                    "error": "pipe_holders_not_drained"}
        return {"pid": proc.pid, "start_ticks": start_ticks, "returncode": proc.returncode,
                "stdout": stdout, "stderr": stderr, "timed_out": True, "drain": drain}
    return {"pid": proc.pid, "start_ticks": start_ticks, "returncode": proc.returncode,
            "stdout": stdout, "stderr": stderr, "timed_out": False}


def run_opencode(binary: Path, workspace: Path, config: Path, prompt: str,
                 *, timeout_s: float, env: dict[str, str]) -> dict[str, Any]:
    """Run and export one OpenCode session after the isolation gate is implemented."""
    _require_live_isolation()
    if (not binary.is_absolute() or not workspace.is_dir() or not config.is_file()
            or not prompt or timeout_s <= 0):
        raise ValueError("absolute binary, workspace, config, prompt and timeout required")
    child_env = dict(env)
    child_env["OPENCODE_CONFIG"] = str(config.resolve())
    # Transport inherits only explicitly supplied environment, never the host's by default.
    run = _process([os.fspath(binary), "run", "--format", "json", "--title", "hs4-file-trial"],
                   cwd=workspace, env=child_env, stdin=prompt, timeout_s=timeout_s)
    result: dict[str, Any] = {"run": run, "export": None, "observation": None, "error": None}
    if run["timed_out"] or run["returncode"] != 0:
        return result
    try:
        events = [json.loads(line) for line in run["stdout"].splitlines() if line.strip()]
        ids = {event.get("sessionID") for event in events if event.get("sessionID")}
        if len(ids) != 1:
            raise ValueError("missing or ambiguous OpenCode session identity")
        session_id = ids.pop()
    except (ValueError, AttributeError, TypeError):
        result["error"] = "malformed_or_ambiguous_event_stream"
        return result
    exported = _process([os.fspath(binary), "export", session_id], cwd=workspace,
                        env=child_env, stdin="", timeout_s=timeout_s)
    result["export"] = exported
    if not exported["timed_out"] and exported["returncode"] == 0:
        try:
            result["observation"] = opencode_session(json.loads(exported["stdout"]), events)
        except (ValueError, TypeError):
            result["error"] = "malformed_session_export"
    return result
