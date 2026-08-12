#!/usr/bin/env python3
"""Guard the pattern-kill guard (mainD, 2026-08-12, INC-20260812).

The load-bearing tests are the NEGATIVE ones: this hook must not block the bus
message reporting a pkill incident, the CLAUDE.md rule forbidding it, or its own
source. A guard that forbids its own documentation is a failure this repo has
already paid for once (C21, pytest_worker_scan).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HOOKS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HOOKS))
from process_pattern_kill_scan import pattern_kill_verdict  # noqa: E402

BLOCKED = [
    ("pkill -f llama-server", "kill-pattern"),
    ("pkill llama-server", "kill-pattern"),
    ("pkill -9 -f 'task-output'", "kill-pattern"),
    ("/usr/bin/pkill -f waiter", "kill-pattern"),
    ("sleep 1 && pkill -f my-waiter", "kill-pattern"),
    ("timeout 5 pgrep -f llama", "grep-pattern"),
    # The canonical dangerous pipeline. Verdict is grep-pattern, not kill-pattern —
    # there is no `pkill` here — and it BLOCKS either way, which is the property that
    # matters. Kept because selection is the dangerous step: `xargs kill` is only as
    # safe as the pids handed to it.
    ("pgrep -f sd-server | xargs kill", "grep-pattern"),
]

ALLOWED = [
    # The reason this file exists: mentions are DATA, not invocations.
    """echo "never pkill -f on a name pattern" """,
    """python3 bus.py append --json '{"rule":"do not pkill -f <name>"}'""",
    "grep -n 'pkill' CLAUDE.md",
    "cat <<'EOF'\npkill -f llama-server\nEOF",
    # Legitimate, pid-scoped, or unrelated.
    "kill 12345",
    "kill -9 $PID",
    "pgrep -P 4242",
    "ps -o pid,lstart,args -p 4242",
    "python3 -m pytest tests/ -q",
]


def test_name_pattern_invocations_are_refused() -> None:
    for cmd, expect in BLOCKED:
        assert pattern_kill_verdict(cmd) == expect, f"{cmd!r} -> {pattern_kill_verdict(cmd)!r}"


def test_mentions_and_pid_scoped_forms_are_allowed() -> None:
    for cmd in ALLOWED:
        assert pattern_kill_verdict(cmd) == "clean", f"{cmd!r} -> {pattern_kill_verdict(cmd)!r}"


def test_the_guard_does_not_forbid_its_own_documentation() -> None:
    """Every file that DESCRIBES the rule must pass the guard that enforces it."""
    for name in ("check_process_pattern_kill.sh", "process_pattern_kill_scan.py"):
        body = (HOOKS / name).read_text(encoding="utf-8")
        assert pattern_kill_verdict(f"cat <<'EOF'\n{body}\nEOF") == "clean", name


def test_the_hook_blocks_end_to_end_and_names_the_alternative() -> None:
    """Exercise the shell hook itself, not only the scanner."""
    import json
    payload = json.dumps({"tool_input": {"command": "pkill -f llama-server"}})
    r = subprocess.run(["bash", str(HOOKS / "check_process_pattern_kill.sh")],
                       input=payload, capture_output=True, text=True)
    assert r.returncode == 2, r.stdout + r.stderr
    assert "TaskStop" in r.stderr and "captured yourself" in r.stderr

    ok = json.dumps({"tool_input": {"command": "kill 12345"}})
    r2 = subprocess.run(["bash", str(HOOKS / "check_process_pattern_kill.sh")],
                        input=ok, capture_output=True, text=True)
    assert r2.returncode == 0, r2.stdout + r2.stderr


# --- Two defects found in this guard within an hour of shipping it -------------

def test_a_comment_documenting_the_rule_is_not_an_invocation() -> None:
    """C47: the coordinator's bus message documenting INC-20260812 was BLOCKED.

    It carried the banned command in an unquoted `#` comment. strip_quoted covers
    quoted mentions; comments were the gap. A guard that cannot distinguish
    executing a command from discussing one blocks writing about the incident it
    exists for.
    """
    for c in ["# never run pkill -f llama-server on this host",
              "ls -la   # reminder: pkill -f is forbidden",
              "echo hi  # pgrep -f autopilot is banned"]:
        assert pattern_kill_verdict(c) == "clean", c


def test_a_comment_does_not_hide_a_real_invocation_on_the_same_line() -> None:
    """Mutation: stripping comments must not become a way to smuggle one past."""
    assert pattern_kill_verdict("pkill -f llama-server  # cleanup") == "kill-pattern"
    assert pattern_kill_verdict("if [ $# -gt 0 ]; then pkill -f x; fi") == "kill-pattern"


def test_the_scanner_refuses_rather_than_saying_clean_for_input_it_never_read() -> None:
    """mainA's HIGH: `scan.py <file>` ignored argv, read empty stdin, printed `clean`.

    A false ALL-CLEAR from a tool whose only job is to refuse. They reported
    "scanner says clean" twice off it, about a file that genuinely trips.
    """
    scan = str(HOOKS / "process_pattern_kill_scan.py")
    empty = subprocess.run([sys.executable, scan], input="", capture_output=True, text=True)
    assert empty.returncode == 2, empty.stdout
    assert "clean" not in empty.stdout
    assert "refusing" in empty.stderr


def test_a_path_argument_actually_scans_that_path() -> None:
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False) as fh:
        fh.write("#!/bin/bash\npkill -9 -f llama-server\n")
        name = fh.name
    scan = str(HOOKS / "process_pattern_kill_scan.py")
    r = subprocess.run([sys.executable, scan, name], input="", capture_output=True, text=True)
    assert r.returncode == 0 and r.stdout.startswith("kill-pattern"), (r.stdout, r.stderr)


def test_narrowed_to_pkill_only_pgrep_passes_the_hook() -> None:
    """Operator decision 2026-08-12 (C46 aftermath): pgrep SELECTS, it does not
    kill. The scanner still classifies it (grep-pattern) but the hook allows it —
    read-only sensing (coordinator bringup, inference_load_check) must not be
    blocked. This test pins the narrowing so it cannot be silently re-widened
    (or un-narrowed) without the change announcing itself.
    """
    import json
    payload = json.dumps({"tool_input": {"command": "pgrep -af llama-server"}})
    r = subprocess.run(["bash", str(HOOKS / "check_process_pattern_kill.sh")],
                       input=payload, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
