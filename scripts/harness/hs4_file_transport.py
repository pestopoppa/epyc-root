"""Transport plumbing for HS-4 file trials; live execution is currently refused.

The isolation verifier is intentionally not implemented here. It must be
replaced by the scoring owner with an actual agent-and-grader boundary proof;
the prepared workspace, a certificate supplied by a caller, or a synthetic
test is not such a proof. Both transports fail closed before any I/O until then.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from scripts.harness.hs4_file_adapters import opencode_session, repl_response


def _require_live_isolation() -> None:
    raise RuntimeError("live agent/grader isolation is not implemented or verified")


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
    try:
        # PID and start ticks identify this exact child, not just an executable name.
        tail = Path(f"/proc/{proc.pid}/stat").read_text().rsplit(") ", 1)[1].split()
        start_ticks = int(tail[19])
    except (OSError, IndexError, ValueError):
        start_ticks = None
    try:
        stdout, stderr = proc.communicate(stdin, timeout=timeout_s)
    except subprocess.TimeoutExpired:
        proc.kill()  # Only the child PID captured above; descendant cleanup is not claimed.
        stdout, stderr = proc.communicate()
        return {"pid": proc.pid, "start_ticks": start_ticks, "returncode": proc.returncode,
                "stdout": stdout, "stderr": stderr, "timed_out": True}
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
