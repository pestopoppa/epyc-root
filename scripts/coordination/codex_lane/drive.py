#!/usr/bin/env python3
"""Interim Codex lane driver (PM-CODEX-LANE-VERDICT). INTERIM: see
/mnt/raid0/llm/tmp/codex-lanes-20261123/README-INTERIM.md. Port target: PM-CODEX-DISPATCH-DETERMINISTIC.

Replaces drive.sh / drive2.sh. Codex `exec` is one-shot, so after every exit the driver resumes the same
thread until lane_verdict() says stop. The verdict is judged from ARTIFACTS, never from the lane's own
`LANE-STATUS:` line alone:

  DONE      every box the report claims (`<box> <repo> <branch> <sha>` lines after the status line) has a
            commit that exists in that repo (`git cat-file -e`) and is on that branch (`git log`); with
            --push the commit must also be reachable from origin/main.
  BLOCKED   the lane wrote `LANE-STATUS: BLOCKED ...` AND named a file, command or error.
  STALLED   3 consecutive resume rounds with no new commit on any lane branch -> stop and alert.
  CONTINUE  anything else (resume the thread).

Modes: default `--no-interference` (drive2: no claims, no tests, no push); `--push` (drive.sh behaviour).
Per-round wall time goes to <lane>-drive.log.

usage: drive.py <lane> [--max N] [--dir D] [--repo name=path ...] [--watch name:branch ...] [--push]
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_DIR = "/mnt/raid0/llm/tmp/codex-lanes-20261123"
STALL_ROUNDS = 3
MODEL = "gpt-6.1-terra"
DEFAULT_REPOS = {
    "epyc-root": "/workspace",
    "epyc-orchestrator": "/mnt/raid0/llm/epyc-orchestrator",
    "epyc-inference-research": "/mnt/raid0/llm/epyc-inference-research",
    "epyc-web": "/mnt/raid0/llm/epyc-web",
}

_STATUS_RE = re.compile(r"^LANE-STATUS:\s*(DONE|BLOCKED)\b\s*(.*)$")
_BOX_RE = re.compile(r"^\s*[-*]?\s*`?([A-Z][A-Z0-9_.-]+)`?\s+(\S+)\s+(\S+)\s+([0-9a-f]{7,40})\b")
# a concrete blocker names a path, a command in backticks, or an error token
_CONCRETE_RE = re.compile(
    r"(/[\w.@-]+(?:/[\w.@-]+)+|\b[\w.-]+\.(?:py|sh|md|json|yaml|yml|toml|txt|log)\b|`[^`]+`"
    r"|\b\w*(?:Error|Exception)\b|\berror\b|\bexit (?:code|status)\s*\d+|\bE\d{3,}\b|\bfatal:)",
    re.IGNORECASE)

CONT_COMMON = ("Continue the same task from where you stopped. You are not finished. If you have a question, choose "
               "the simplest reasonable answer, write it in the commit message, and proceed. Design for the current "
               "code path. When every assigned box is committed, make the FIRST line of the report file "
               "`LANE-STATUS: DONE` followed by one line per box: `<box id> <repo> <branch> <sha>`; the driver "
               "verifies every line against git, so a line without a real commit is not done. Only if a concrete "
               "external blocker remains (name it: file, command, error), make it `LANE-STATUS: BLOCKED <blocker>`. "
               "Otherwise keep working.")
CONT_NI = ("Rules for this lane: take NO rowflow claim, run NO pytest and no other workload; run only static checks "
           "(python3 -m py_compile, ruff check --select F if available, or an AST undefined-name scan); commit each "
           "box to its own branch and do NOT push. ")
CONT_PUSH = ("Rules: a refused light claim is never a stop condition - commit your code first, then retry the claim "
             "every 60 s inside one shell loop and run the tests when granted; origin/main moving is normal - fetch, "
             "rebase, re-check, continue. Push every box (PUSH VERIFIED); the sha you report must be reachable from "
             "origin/main. ")


def _git(repo: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True)


def parse_report(report: str | os.PathLike | None) -> tuple[str | None, str, list[tuple[str, str, str, str]]]:
    """(status, detail, boxes). status is DONE, BLOCKED or None. Accepts a path or the report text."""
    text = ""
    if isinstance(report, os.PathLike) or (isinstance(report, str) and report and "\n" not in report
                                            and Path(report).is_file()):
        p = Path(report)
        text = p.read_text(errors="replace") if p.is_file() else ""
    elif isinstance(report, str):
        text = report
    lines = text.splitlines()
    if not lines:
        return None, "", []
    m = _STATUS_RE.match(lines[0].strip())
    if not m:
        return None, "", []
    boxes = [b.groups() for b in (_BOX_RE.match(ln) for ln in lines[1:]) if b]
    return m.group(1), m.group(2).strip(), boxes


def commit_check(repo: str, branch: str, sha: str, push: bool) -> str | None:
    """None if ok, else the reason the claim fails."""
    if not repo or not Path(repo).exists():
        return f"repo path missing: {repo}"
    if _git(repo, "cat-file", "-e", f"{sha}^{{commit}}").returncode != 0:
        return f"commit {sha} not in {repo}"
    ref = branch
    if _git(repo, "rev-parse", "--verify", "-q", f"refs/heads/{branch}").returncode != 0:
        if _git(repo, "rev-parse", "--verify", "-q", f"refs/remotes/origin/{branch}").returncode != 0:
            return f"branch {branch} not in {repo}"
        ref = f"origin/{branch}"
    full = _git(repo, "rev-parse", f"{sha}^{{commit}}").stdout.strip()
    on_branch = _git(repo, "log", "--format=%H", ref).stdout.split()
    if full not in on_branch:
        return f"commit {sha} not on {branch}"
    if push and _git(repo, "merge-base", "--is-ancestor", full, "origin/main").returncode != 0:
        return f"commit {sha} not reachable from origin/main"
    return None


def lane_verdict(report, repos: dict[str, str], *, push: bool = False, stall_rounds: int = 0) -> str:
    """DONE | BLOCKED <reason> | STALLED | CONTINUE. `stall_rounds` = consecutive resume rounds with no new
    commit on any lane branch (the driver counts it)."""
    status, detail, boxes = parse_report(report)
    if status == "DONE" and boxes:
        if all(commit_check(repos.get(r, r), br, sha, push) is None for _, r, br, sha in boxes):
            return "DONE"
    if status == "BLOCKED" and _CONCRETE_RE.search(detail or ""):
        return f"BLOCKED {detail}"
    if stall_rounds >= STALL_ROUNDS:
        return "STALLED"
    return "CONTINUE"


def explain(report, repos, push=False) -> list[str]:
    _, _, boxes = parse_report(report)
    return [f"{b} {r} {br} {sha}: {commit_check(repos.get(r, r), br, sha, push) or 'ok'}" for b, r, br, sha in boxes]


def branch_heads(repos: dict[str, str], watch: list[tuple[str, str]], report) -> dict[str, str]:
    """Head sha of every lane branch: the --watch list plus every branch the report names."""
    pairs = set(watch) | {(r, br) for _, r, br, _ in parse_report(report)[2]}
    out = {}
    for r, br in sorted(pairs):
        cp = _git(repos.get(r, r), "rev-parse", "-q", "--verify", f"refs/heads/{br}")
        out[f"{r}:{br}"] = cp.stdout.strip() if cp.returncode == 0 else ""
    return out


def _log(logf: Path, msg: str) -> None:
    with logf.open("a") as f:
        f.write(f"{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')} {msg}\n")


def drive(lane: str, d: Path, repos: dict[str, str], watch: list[tuple[str, str]], max_rounds: int,
          push: bool, codex: str = "codex") -> int:
    report, logf = d / f"{lane}-REPORT.md", d / f"{lane}-drive.log"
    jsonl, err = d / f"{lane}.jsonl", d / f"{lane}.err"
    env = dict(os.environ, HIP_VISIBLE_DEVICES="-1")
    pre = [] if os.environ.get("CODEX_LANE_NO_NICE") else ["nice", "-n", "19", "ionice", "-c3"]
    mode = "push" if push else "no-interference"

    def run(cmd, stdin_text):
        t0 = time.monotonic()
        with jsonl.open("a") as o, err.open("a") as e:
            rc = subprocess.run(pre + cmd, input=stdin_text, stdout=o, stderr=e, text=True, env=env).returncode
        return rc, time.monotonic() - t0

    if not jsonl.exists() or jsonl.stat().st_size == 0:
        _log(logf, f"start mode={mode}")
        rc, wall = run([codex, "exec", "--json", "--skip-git-repo-check", "-m", MODEL, "-c",
                        "model_reasoning_effort=high", "-C", "/mnt/raid0/llm", "-"],
                       (d / f"{lane}.prompt").read_text())
        _log(logf, f"round 0 rc={rc} wall={wall:.1f}s")
    m = re.search(r'"thread_id":"([^"]*)"', jsonl.read_text(errors="replace") if jsonl.exists() else "")
    if not m:
        _log(logf, "no thread id")
        return 2
    tid = m.group(1)
    cont = (CONT_PUSH if push else CONT_NI) + CONT_COMMON
    heads = branch_heads(repos, watch, report)
    stall = 0
    for rnd in range(1, max_rounds + 1):
        v = lane_verdict(report, repos, push=push, stall_rounds=stall)
        if v != "CONTINUE":
            break
        status, _, _ = parse_report(report)
        if status:
            _log(logf, f"lane says {status} but artifacts disagree: " + "; ".join(explain(report, repos, push)))
        _log(logf, f"resume round {rnd} thread {tid}")
        rc, wall = run([codex, "exec", "resume", "--json", "--skip-git-repo-check", "-c",
                        "model_reasoning_effort=high", tid, "-"], cont + "\n")
        new = branch_heads(repos, watch, report)
        moved = any(v and heads.get(k) != v for k, v in new.items())
        stall = 0 if moved else stall + 1
        heads = new
        _log(logf, f"round {rnd} rc={rc} wall={wall:.1f}s new_commit={moved} stall={stall}")
    else:
        v = lane_verdict(report, repos, push=push, stall_rounds=stall)
        if v == "CONTINUE":
            _log(logf, f"max rounds ({max_rounds}) reached without verdict")
            return 3
    _log(logf, f"VERDICT {v}")
    if v == "STALLED":
        print(f"ALERT lane {lane} STALLED: {STALL_ROUNDS} rounds with no new commit", file=sys.stderr)
        return 4
    return 0 if v == "DONE" else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("lane")
    ap.add_argument("--max", type=int, default=8)
    ap.add_argument("--dir", default=DEFAULT_DIR)
    ap.add_argument("--repo", action="append", default=[], help="name=path (adds to the defaults)")
    ap.add_argument("--watch", action="append", default=[], help="repo:branch lane branch to watch for stalls")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--push", action="store_true", help="drive.sh mode: lane claims, tests and pushes")
    g.add_argument("--no-interference", action="store_true", help="default: no claims, no tests, no push")
    ap.add_argument("--codex", default=os.environ.get("CODEX_BIN", "codex"))
    a = ap.parse_args(argv)
    repos = dict(DEFAULT_REPOS)
    repos.update(dict(x.split("=", 1) for x in a.repo))
    watch = [tuple(x.split(":", 1)) for x in a.watch]
    return drive(a.lane, Path(a.dir), repos, watch, a.max, a.push, a.codex)


if __name__ == "__main__":
    sys.exit(main())
