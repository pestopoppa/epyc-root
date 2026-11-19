#!/usr/bin/env python3
"""Scan a Bash command for an INFERENCE LAUNCH and decide whether a region claim covers it.

REG-ENF-2 (handoffs/active/coordination-and-churn-pipeline.md): tool-use authorization
moves from prose ("hold a region claim before you run inference") to a tool-boundary
hook, mirroring the destructive-command PreToolUse hooks. Companion hook:
`check_inference_launch_claim.sh`.

WHAT COUNTS AS A LAUNCH. An unquoted command word (after env assignments and runner
prefixes such as `timeout`, `nohup`, `numactl`, `taskset`, `sudo`, `env`) whose basename is
an inference binary: llama-server, llama-bench, llama-cli, llama-completion, ... and the
whisper speech binaries. SCOPED TO INVOCATIONS, NOT TEXT: this uses the shared
`shell_scan.lex()`, so `grep llama-server notes.md`, `echo "run llama-bench"`, heredoc
bodies and comments are data and never match. `--version` / `--help` / `--list-devices`
style invocations do not run inference and are not launches.

WHAT COUNTS AS A CLAIM. Region claims are the orchestrator's CPU-region / GPU locks
(`epyc-orchestrator/scripts/region-lock`, state in `$EPYC_REGION_LOCK_DIR` =
/mnt/raid0/llm/tmp, registry `cpu_region.occupancy.json`). A launch is COVERED when:
  1. it is itself wrapped by `region-lock run ... -- <binary>` (the wrapper acquires the
     claim for the child's lifetime, so the wrapped form IS the claim); or
  2. the session proves ownership of a LIVE occupancy entry: its `pid` is an ancestor of
     this hook process, or `EPYC_REGION_CLAIM_TOKEN` equals its `token`, or
     `EPYC_REGION_CLAIM_TAG` equals its `request_tag`. A dead pid is not live.
A live claim held by somebody ELSE does not cover this session; that is the point.

POSTURE (stated here because the box requires it in the acceptance):
  * Non-launch command              -> FAIL-OPEN  (allow). A guard that blocks ordinary
                                       commands stalls parallel sessions for reasons they
                                       cannot see.
  * Detected launch, covered        -> allow.
  * Detected launch, no claim       -> DENY.
  * Detected launch, claim state UNREADABLE (corrupt JSON, wrong schema, permission
    error)                          -> FAIL-CLOSED (deny). Unreadable is not "no one holds
                                       a claim" nor "I hold one"; a missed launch on a
                                       shared host costs another session's measurement,
                                       a false block costs one rephrase or a wrap.
  * Scanner crash                   -> the shell hook denies only if a coarse regex still
                                       sees an inference binary at a command position;
                                       otherwise allow.
  * Operator override: EPYC_ALLOW_UNCLAIMED_LAUNCH=1 (set in the hook's env, not
    something an agent should reach for).
KNOWN LIMIT: launches hidden inside scripts (`bash run_bench.sh`) are not visible at the
tool boundary; those scripts are expected to take the claim themselves via region-lock.

CLI: reads the command on stdin, prints one verdict:
  clean | wrapped | launch:covered | launch:uncovered | launch:unreadable
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from shell_scan import lex  # noqa: E402

LOCK_DIR_DEFAULT = "/mnt/raid0/llm/tmp"
OCCUPANCY_NAME = "cpu_region.occupancy.json"

_BINARY = re.compile(
    r"^(?:llama-(?:server|bench|cli|completion|speculative|batched-bench|batched|"
    r"perplexity|parallel|embedding|mtmd-cli|simple|lookup|eval-callback)"
    r"|whisper-(?:cli|server|bench)|main)$"
)
# `main` is deliberately NOT launch-matched unless path-qualified into a llama tree; see below.
_AMBIGUOUS = {"main"}
_RUNNERS = {
    "timeout", "nohup", "numactl", "taskset", "sudo", "setsid", "stdbuf", "env", "nice",
    "ionice", "time", "exec", "command", "chrt", "flock", "systemd-run", "unbuffer",
    "region-lock", "region_lock_cli",
}
_WRAPPERS = {"region-lock", "region_lock_cli"}
_INFO_FLAGS = {"--version", "-v", "--help", "-h", "--list-devices", "--cache-list", "--license"}
_ENV_ASSIGN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")


def _tokens(seg: str) -> list[str]:
    toks = seg.split()
    while toks and _ENV_ASSIGN.match(toks[0]):
        toks.pop(0)
    return toks


def _base(tok: str) -> str:
    return tok.rsplit("/", 1)[-1]


def _is_bin(name: str) -> bool:
    return bool(_BINARY.match(name)) and name not in _AMBIGUOUS


def launch_kind(command: str) -> str:
    """'clean', 'wrapped' (inside region-lock) or 'launch' (bare launch)."""
    for seg in lex(command):
        toks = _tokens(seg)
        if not toks:
            continue
        first = _base(toks[0])
        if _is_bin(first):
            idx, wrapped = 0, False
        elif first in _RUNNERS:
            wrapped = first in _WRAPPERS
            idx = next(
                (i for i, t in enumerate(toks[1:], 1)
                 if _is_bin(_base(t))),
                -1,
            )
            if idx < 0:
                continue
            wrapped = wrapped or any(_base(t) in _WRAPPERS for t in toks[:idx])
        else:
            continue
        if any(t in _INFO_FLAGS for t in toks[idx + 1:]):
            continue
        return "wrapped" if wrapped else "launch"
    return "clean"


def _ancestors(pid: int | None = None) -> set[int]:
    out: set[int] = set()
    pid = pid or os.getpid()
    for _ in range(64):
        try:
            stat = Path(f"/proc/{pid}/stat").read_text()
            ppid = int(stat.rsplit(")", 1)[1].split()[1])
        except (OSError, ValueError, IndexError):
            break
        if ppid <= 1 or ppid in out:
            break
        out.add(ppid)
        pid = ppid
    return out


def _alive(pid: int) -> bool:
    return Path(f"/proc/{pid}").exists()


def claim_state(lock_dir: str | None = None, env: dict | None = None,
                ancestors: set[int] | None = None) -> str:
    """'covered' | 'uncovered' | 'unreadable'."""
    env = os.environ if env is None else env
    d = Path(lock_dir or env.get("EPYC_REGION_LOCK_DIR") or LOCK_DIR_DEFAULT)
    path = d / OCCUPANCY_NAME
    try:
        data = json.loads(path.read_text())
        entries = data["entries"]
        if not isinstance(entries, list):
            return "unreadable"
    except FileNotFoundError:
        return "uncovered"            # no registry written yet == nobody holds a claim
    except (OSError, ValueError, KeyError, TypeError):
        return "unreadable"
    anc = _ancestors() if ancestors is None else ancestors
    token, tag = env.get("EPYC_REGION_CLAIM_TOKEN"), env.get("EPYC_REGION_CLAIM_TAG")
    for e in entries:
        if not isinstance(e, dict):
            return "unreadable"
        pid = e.get("pid")
        if not isinstance(pid, int) or not _alive(pid):
            continue
        if pid in anc or (token and e.get("token") == token) or (tag and e.get("request_tag") == tag):
            return "covered"
    return "uncovered"


def verdict(command: str, lock_dir: str | None = None, env: dict | None = None,
            ancestors: set[int] | None = None) -> str:
    kind = launch_kind(command)
    if kind == "clean":
        return "clean"
    if kind == "wrapped":
        return "wrapped"
    return "launch:" + claim_state(lock_dir, env, ancestors)


def main() -> int:
    print(verdict(sys.stdin.read()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
