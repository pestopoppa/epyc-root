#!/usr/bin/env python3
"""Fail-closed adapter for the existing authoritative tmux probe JSON.

Leaf observers may act on idleness only when the adapter itself completed
successfully and its JSON says the runtime decided, the runtime is idle, and
the final nudge guard is open. Everything else is unknown to this helper.
This file deliberately does not inspect pane text or infer state from markers.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Callable


ADAPTER = Path(__file__).with_name("tmux_adapter.py")


class _DuplicateProbeMember(ValueError):
    """Raised when a JSON object repeats a key and its value is ambiguous."""


def _object_without_duplicate_members(pairs: list[tuple[str, object]]) -> dict:
    payload: dict[str, object] = {}
    for key, value in pairs:
        if key in payload:
            raise _DuplicateProbeMember(f"duplicate JSON member: {key}")
        payload[key] = value
    return payload


def qualified_idle(
    agent: str,
    *,
    adapter: str | Path | None = None,
    timeout_s: float = 15.0,
    run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> tuple[bool, str]:
    """Return whether the existing probe positively qualifies this agent idle.

    The `run` parameter is the offline fixture seam. A nonzero exit, timeout,
    malformed or incomplete JSON, or any unqualified vocabulary fails closed.
    """
    adapter_path = Path(adapter or os.environ.get("EPYC_TMUX_ADAPTER") or ADAPTER)
    argv = [sys.executable, str(adapter_path), "probe", "--agent", agent, "--json"]
    try:
        proc = run(argv, capture_output=True, text=True, timeout=timeout_s)
    except subprocess.TimeoutExpired:
        return False, f"probe timed out after {timeout_s:g}s"
    except Exception as exc:  # noqa: BLE001 — an unusable probe is unknown
        return False, f"probe invocation failed: {type(exc).__name__}: {exc}"

    if proc.returncode != 0:
        return False, f"probe exited {proc.returncode}"
    try:
        payload = json.loads(proc.stdout, object_pairs_hook=_object_without_duplicate_members)
    except (TypeError, json.JSONDecodeError, _DuplicateProbeMember) as exc:
        return False, f"probe JSON is malformed or truncated: {exc}"
    if not isinstance(payload, dict):
        return False, "probe JSON is not an object"

    decided = payload.get("runtime_decided")
    state = payload.get("runtime_state")
    nudge_ok = payload.get("nudge_ok")
    if type(decided) is not bool or type(nudge_ok) is not bool:
        return False, "probe JSON is missing boolean runtime_decided/nudge_ok fields"
    if not isinstance(state, str):
        return False, "probe JSON is missing string runtime_state"
    if decided is True and state == "idle" and nudge_ok is True:
        return True, "authoritative probe qualifies idle"
    return False, (
        "probe did not qualify idle "
        f"(runtime_decided={decided!r}, runtime_state={state!r}, nudge_ok={nudge_ok!r})"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent", required=True)
    parser.add_argument("--adapter", help="adapter path override for offline fixtures")
    parser.add_argument("--timeout-s", type=float, default=15.0)
    args = parser.parse_args()
    idle, detail = qualified_idle(args.agent, adapter=args.adapter, timeout_s=args.timeout_s)
    print(detail, file=sys.stderr)
    return 0 if idle else 1


if __name__ == "__main__":
    raise SystemExit(main())
