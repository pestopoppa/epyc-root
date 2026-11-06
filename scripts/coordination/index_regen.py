#!/usr/bin/env python3
"""The ONE deterministic writer of the generated handoff index files (operator ruling 3, 2026-11-02).

    python3 scripts/coordination/index_regen.py [--worktree <dir>] [--flags <dir>] [--min-interval 600] [--dry-run]

Handoff workers never regenerate `.index-state.json`, `.index-graph.json` or the master rollup (their wrap-up is the
light persist in churn/wrapup.py), so those files can never conflict between lanes. This script brings them up to
date on origin/main: at most once per --min-interval seconds (stamp under <flags>), it resets a dedicated worktree to
origin/main, runs `scripts/handoffs/index_state.py`, and when the generated files changed commits ONLY them under the
`wrapup` lease and pushes through serialized_push.py (one rebase-retry on rejection). The dispatcher pass starts it
detached (handoff_sessions.py `maybe_regen_index`). Once per BATCH (TOKEN-REGEN-ONCE-PER-BATCH, 2026-11-06): beyond the
interval it regenerates only when an input changed on origin/main since the last regen AND the batch has ended (no
non-generated commit for QUIET_S) or the last regen is older than MAX_AGE_S; `--force` (operator-cadence wrap-up)
bypasses the debounce. `index_state.py --check` is unchanged. Stdlib only.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time

ROOT = "/workspace"
WT_DEFAULT = "/mnt/raid0/llm/worktrees/index-regen"
FLAGS_DEFAULT = "/mnt/raid0/llm/tmp/compute-flags"
AGENT = "index-regen"
GENERATED = ("handoffs/active/.index-state.json", "handoffs/active/.index-graph.json",
             "handoffs/active/master-handoff-index.md")
TRAILERS = "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"


def log(msg: str) -> None:
    print(f"[index-regen] {msg}", flush=True)


def git(wt: str, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    r = subprocess.run(["git", "-C", wt, *args], capture_output=True, text=True, timeout=600)
    if check and r.returncode:
        raise RuntimeError(f"git {' '.join(args)}: {(r.stdout + r.stderr).strip()[-300:]}")
    return r


def stamp_path(flags: str) -> str:
    return os.path.join(flags, "handoff-sessions", "index-regen.stamp")


def due(flags: str, min_interval: float, now: float | None = None) -> bool:
    try:
        return (now or time.time()) - os.path.getmtime(stamp_path(flags)) >= min_interval
    except OSError:
        return True


def touch_stamp(flags: str) -> None:
    p = stamp_path(flags)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as fh:
        fh.write(f"{time.time():.0f}\n")


def ensure_worktree(wt: str, repo: str = ROOT) -> None:
    if not os.path.isdir(os.path.join(wt, ".git")) and not os.path.isfile(os.path.join(wt, ".git")):
        git(repo, "fetch", "-q", "origin")
        git(repo, "worktree", "add", "-q", "-B", AGENT, wt, "origin/main")
        git(wt, "branch", "-q", "--set-upstream-to=origin/main")


def sp(wt: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, os.path.join(wt, "scripts/coordination/serialized_push.py"), "--agent", AGENT,
                           "--repo", wt, *args], capture_output=True, text=True, timeout=900)


def regen(wt: str) -> list[str]:
    """Reset to origin/main, regenerate, return the generated paths that changed (staged)."""
    git(wt, "fetch", "-q", "origin")
    git(wt, "reset", "-q", "--hard", "origin/main")
    r = subprocess.run([sys.executable, os.path.join(wt, "scripts/handoffs/index_state.py")], cwd=wt,
                       capture_output=True, text=True, timeout=900)
    if r.returncode:
        raise RuntimeError(f"index_state.py rc={r.returncode}: {(r.stdout + r.stderr).strip()[-300:]}")
    changed = [g for g in GENERATED if git(wt, "status", "--porcelain", "--", g).stdout.strip()]
    if changed:
        git(wt, "add", "--", *changed)
    return changed


QUIET_S = 180        # batch end = origin/main has had no non-generated commit for this long
MAX_AGE_S = 3600     # ...or the last regen is older than this (bounds how stale the generated files can get)


def state_path(flags: str) -> str:
    return os.path.join(flags, "handoff-sessions", "index-regen.state.json")


def batch_verdict(changed_files, head_ts: float, last_ts: float, now: float, quiet_s: float = QUIET_S,
                  max_age_s: float = MAX_AGE_S) -> tuple[bool, str]:
    """Regenerate once per BATCH (TOKEN-REGEN-ONCE-PER-BATCH): (run?, why).
    `changed_files` = paths changed on origin/main since the last regen's base (None = never regenerated)."""
    if changed_files is None:
        return True, "first regen"
    inputs = [f for f in changed_files if f not in GENERATED]
    if not inputs:
        return False, "no input changed since the last regen (generated files only)"
    if now - last_ts >= max_age_s:
        return True, f"last regen older than {max_age_s:.0f} s"
    if now - head_ts < quiet_s:
        return False, f"batch still landing: newest commit {now - head_ts:.0f} s old < {quiet_s:.0f} s quiet"
    return True, f"batch ended: {len(inputs)} input file(s) changed, quiet {now - head_ts:.0f} s"


def _load_state(flags: str) -> dict:
    try:
        import json
        return json.load(open(state_path(flags)))
    except (OSError, ValueError):
        return {}


def _save_state(flags: str, sha: str) -> None:
    import json
    os.makedirs(os.path.dirname(state_path(flags)), exist_ok=True)
    with open(state_path(flags), "w") as fh:
        json.dump({"sha": sha, "ts": time.time()}, fh)


def should_run(wt: str, flags: str, now: float | None = None, force: bool = False) -> tuple[bool, str]:
    if force:
        return True, "forced"
    st = _load_state(flags)
    git(wt, "fetch", "-q", "origin")
    head = git(wt, "rev-parse", "origin/main").stdout.strip()
    changed = None
    if st.get("sha"):
        d = git(wt, "diff", "--name-only", f"{st['sha']}..{head}", check=False)
        changed = d.stdout.split() if d.returncode == 0 else None
    ts = float(git(wt, "log", "-1", "--format=%ct", "origin/main").stdout.strip() or 0)
    return batch_verdict(changed, ts, float(st.get("ts") or 0), now or time.time())


def run(wt: str, flags: str, dry_run: bool, force: bool = False) -> int:
    ensure_worktree(wt)
    ok, why = should_run(wt, flags, force=force)
    if not ok:
        log(f"skip: {why}")
        return 0
    log(f"regen: {why}")
    changed = regen(wt)
    if not changed:
        log("generated files current on origin/main")
        if not dry_run:
            _save_state(flags, git(wt, "rev-parse", "origin/main").stdout.strip())
        return 0
    if dry_run:
        log(f"DRY-RUN would commit {changed}")
        git(wt, "reset", "-q", "--hard", "origin/main")
        return 0
    token = os.path.join(flags, "handoff-sessions", "index-regen.token")
    a = sp(wt, "--acquire", "--lock-name", "wrapup", "--token-file", token)
    if a.returncode:
        log(f"wrapup lease busy, skipping this pass: {(a.stdout + a.stderr).strip()[-200:]}")
        return 0
    try:
        for attempt in (1, 2):
            if attempt == 2:
                changed = regen(wt)
                if not changed:
                    return 0
            git(wt, "commit", "-q", "-m", "Regenerate handoff index files (index_regen.py)\n\n" + TRAILERS, "--", *changed)
            p = sp(wt, "--fetch", "--push")
            if p.returncode == 0:
                log(f"pushed {git(wt, 'rev-parse', 'HEAD').stdout.strip()[:12]} {changed}")
                _save_state(flags, git(wt, "rev-parse", "HEAD").stdout.strip())
                return 0
            log(f"push rc={p.returncode}, regenerating on fresh origin/main: {(p.stdout + p.stderr).strip()[-200:]}")
        return 1
    finally:
        sp(wt, "--release", "--lock-name", "wrapup", "--token-file", token)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--worktree", default=WT_DEFAULT)
    ap.add_argument("--flags", default=FLAGS_DEFAULT)
    ap.add_argument("--min-interval", type=float, default=600)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true", help="skip the once-per-batch debounce and the interval stamp (operator wrap-up)")
    a = ap.parse_args(argv)
    if not a.force and not due(a.flags, a.min_interval):
        return 0
    touch_stamp(a.flags)
    try:
        return run(a.worktree, a.flags, a.dry_run, a.force)
    except Exception as exc:  # noqa: BLE001
        log(f"FAIL {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
