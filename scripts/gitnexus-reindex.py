#!/usr/bin/python3
"""GitNexus re-index on the q3 non-GPU pocket, plus the staleness trigger.

Operator 2026-11-20: re-indexing must never take q0-q2, even while the MI210 is busy.
q3 = cores 72-95 (+ SMT siblings 168-191); 88-95 / 184-191 are the MI210 host threads and are never used.
The candidate pocket is therefore cores 72-87 (siblings 168-183).

Claim path (never a bypass): `region-lock run --cpu-list <pocket>` takes LOCK_SH GLOBAL.q3 + build.q3 and
LOCK_EX on each cpu_core.N.lock, pins the child with taskset and sets
ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT=1 for it. The child is `gitnexus-analyze.sh --workers 1`, whose
guard route `admit_subquarter_q3` (docs/reference/gitnexus-compute-claims.md) verifies that claim twice.
The refusal "cross-role global region locks are not enabled" only appears when analyze is run OUTSIDE a
region-lock; it is not an operator setting.

Subcommands
  run      [--cpus 72-75]            claim the pocket and analyze (foreground)
  check                              print the trigger decision, change nothing
  trigger  [--batch-id ID] [--min-interval-h N]
                                     if `gitnexus status` says stale, not run in the last N hours, not already
                                     requested for this batch and nothing running: start `run` detached.
Exit: trigger/check 0 always except usage (64); run returns the analyze/region-lock status.
"""
import argparse
import fcntl
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).absolute().parent
REPO_ROOT = Path(os.environ.get("GITNEXUS_REINDEX_REPO", "/workspace"))
REGION_LOCK = os.environ.get("GITNEXUS_REGION_LOCK", "/workspace/repos/epyc-orchestrator/scripts/region-lock")
STATE_DIR = Path(os.environ.get("GITNEXUS_REINDEX_STATE_DIR", "/mnt/raid0/llm/tmp/gitnexus-reindex"))
POCKET_CORES = range(72, 88)          # q3 cores that do not own the MI210 (siblings +96)
DEFAULT_CPUS = "72-75"                # 4 cores; `--workers 1` needs two threads
DEFAULT_INTERVAL_H = 6.0
REFUSAL_RETRY_S = 900                 # an admission refusal (64/75) does not burn the full interval
REFUSED_RC = {64, 75}


class Usage(Exception):
    pass


def parse_cpus(text):
    cpus = set()
    for tok in text.split(","):
        a, sep, b = tok.strip().partition("-")
        if not a.isdigit() or (sep and not b.isdigit()):
            raise Usage(f"malformed cpu list {text!r}")
        lo, hi = int(a), int(b) if sep else int(a)
        if hi < lo:
            raise Usage(f"malformed cpu list {text!r}")
        cpus.update(range(lo, hi + 1))
    return cpus


def validate_pocket(text):
    """Every cpu must be a q3 non-GPU core (72-87) or its SMT sibling (168-183)."""
    cpus = parse_cpus(text)
    allowed = set(POCKET_CORES) | {c + 96 for c in POCKET_CORES}
    bad = sorted(cpus - allowed)
    if bad or not cpus:
        raise Usage(f"cpus {bad or text} outside the q3 non-GPU pocket 72-87/168-183 "
                    "(88-95/184-191 are MI210 host threads)")
    return text


def run_argv(cpus=DEFAULT_CPUS, timeout_s=600):
    validate_pocket(cpus)
    return [REGION_LOCK, "run", "--cpu-list", cpus, "--role", "build", "--tag", "gitnexus-reindex-q3",
            "--timeout-s", str(timeout_s), "--",
            "/bin/bash", str(HERE / "gitnexus-analyze.sh"), "--workers", "1"]


def run_env(base=None):
    env = dict(base if base is not None else os.environ)
    env["GITNEXUS_WORKER_POOL_SIZE"] = "1"
    env["ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT"] = "1"
    return env


# ---------------------------------------------------------------- state
def _state_path():
    return STATE_DIR / "state.json"


def load_state():
    try:
        return json.loads(_state_path().read_text())
    except (OSError, ValueError):
        return {}


def update_state(**kw):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with open(STATE_DIR / "state.lock", "a+") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        st = load_state()
        st.update(kw)
        tmp = _state_path().with_suffix(".tmp")
        tmp.write_text(json.dumps(st, sort_keys=True))
        os.replace(tmp, _state_path())
        return st


def pid_alive(pid, start=None):
    """Liveness by /proc (kill -0 is blind to reuse): pid exists, not a zombie, same start time."""
    try:
        raw = Path(f"/proc/{pid}/stat").read_text()
    except OSError:
        return False
    fields = raw[raw.rfind(")") + 2:].split()
    if fields[0] == "Z":
        return False
    return start is None or int(fields[19]) == start


def proc_start(pid):
    raw = Path(f"/proc/{pid}/stat").read_text()
    return int(raw[raw.rfind(")") + 2:].split()[19])


# ---------------------------------------------------------------- decision
def status_text():
    p = subprocess.run(["gitnexus", "status"], cwd=REPO_ROOT, text=True, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, timeout=120)
    return p.stdout


def is_stale(text):
    """True stale, False up-to-date, None unreadable (never trigger on an unreadable status)."""
    m = re.search(r"^Status:\s*(.*)$", text, re.M)
    if not m:
        return None
    line = m.group(1).lower()
    if "stale" in line:
        return True
    if "up-to-date" in line:
        return False
    return None


def current_commit(text):
    m = re.search(r"^Current commit:\s*([0-9a-f]{7,40})", text, re.M)
    return m.group(1) if m else None


def decide(text, state, now, batch_id=None, min_interval_h=DEFAULT_INTERVAL_H):
    """Return (action, reason); action is 'run' or 'skip'."""
    stale = is_stale(text)
    if stale is None:
        return "skip", "status unreadable"
    if not stale:
        return "skip", "fresh"
    pid = state.get("pid")
    if pid and pid_alive(pid, state.get("pid_start")) and not state.get("finished_at"):
        return "skip", f"running pid {pid}"
    if batch_id and state.get("last_batch") == batch_id:
        return "skip", f"already requested for batch {batch_id}"
    started = state.get("started_at")
    if started:
        wait = REFUSAL_RETRY_S if state.get("rc") in REFUSED_RC else min_interval_h * 3600
        if now - started < wait:
            return "skip", f"last attempt {int(now - started)}s ago, min {int(wait)}s"
    return "run", "stale"


# ---------------------------------------------------------------- commands
def cmd_run(args):
    argv = run_argv(args.cpus, args.timeout_s)
    update_state(pid=os.getpid(), pid_start=proc_start(os.getpid()), finished_at=None)
    rc = subprocess.call(argv, cwd=REPO_ROOT, env=run_env())
    update_state(rc=rc, finished_at=time.time())
    return rc


def cmd_check(args, text=None):
    text = status_text() if text is None else text
    action, reason = decide(text, load_state(), time.time(), args.batch_id, args.min_interval_h)
    print(json.dumps({"action": action, "reason": reason, "commit": current_commit(text)}))
    return action, reason


def cmd_trigger(args, text=None, spawn=None):
    text = status_text() if text is None else text
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with open(STATE_DIR / "trigger.lock", "a+") as lk:   # serialize triggers: one decision at a time
        fcntl.flock(lk, fcntl.LOCK_EX)
        action, reason = decide(text, load_state(), time.time(), args.batch_id, args.min_interval_h)
        if action == "run":
            validate_pocket(args.cpus)
            update_state(started_at=time.time(), last_batch=args.batch_id, rc=None, finished_at=None,
                         pid=None, requested_commit=current_commit(text))
            (spawn or _spawn)(args)
        print(json.dumps({"action": action, "reason": reason}))
    return 0


def _spawn(args):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    log = open(STATE_DIR / "last-run.log", "ab")
    subprocess.Popen([sys.executable, "-I", str(HERE / "gitnexus-reindex.py"), "run", "--cpus", args.cpus,
                      "--timeout-s", str(args.timeout_s)],
                     cwd=REPO_ROOT, stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=("run", "check", "trigger"))
    ap.add_argument("--cpus", default=DEFAULT_CPUS)
    ap.add_argument("--timeout-s", type=float, default=600)
    ap.add_argument("--batch-id")
    ap.add_argument("--min-interval-h", type=float, default=DEFAULT_INTERVAL_H)
    args = ap.parse_args(argv)
    try:
        validate_pocket(args.cpus)
        if args.cmd == "run":
            return cmd_run(args)
        if args.cmd == "check":
            cmd_check(args)
            return 0
        return cmd_trigger(args)
    except Usage as exc:
        print(f"gitnexus-reindex: {exc}", file=sys.stderr)
        return 64


if __name__ == "__main__":
    raise SystemExit(main())
