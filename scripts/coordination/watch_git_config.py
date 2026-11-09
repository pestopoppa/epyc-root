#!/usr/bin/env python3
"""watch_git_config.py - record when core.bare flips to true in a watched .git/config. WRITES ONLY ITS LOG.

Never modifies any git config and never runs git (a git child would land in its own process list).

HONEST LIMITS. The process list is BEST-EFFORT: it is the git processes running when the change was NOTICED (inotifywait
if installed, else a 1 s poll), so the writer may already have exited, and any listed process may be innocent. It does not
identify the writer. True writer identity needs auditd (a path watch on these files); a watcher in user space cannot give it.

Each event is one JSON line: ts, file, content, git_processes [{pid, argv, cwd}]. A file already true at start logs one
event with event="already-true-at-start". Git replaces config by rename, so inotify watches the parent directories.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import time

FILES = ("/workspace/.git/config", "/mnt/raid0/llm/epyc-orchestrator/.git/config",
         "/mnt/raid0/llm/epyc-inference-research/.git/config")
LOG = "/mnt/raid0/llm/tmp/git-config-watch/events.log"
POLL_S = 1.0
MAX_CONTENT = 65536
TRUE_VALUES = ("true", "yes", "on", "1")


def is_bare(text):
    """core.bare per git's rules, last value wins; a bare key with no '=' means true."""
    section, val = None, None
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].split(";", 1)[0].strip()
        if line.startswith("["):
            section = line[1:].split("]", 1)[0].strip().lower()
            continue
        if section == "core":
            k, sep, v = line.partition("=")
            if k.strip().lower() == "bare":
                val = v.strip().lower() in TRUE_VALUES if sep else True
    return bool(val)


def read(path):
    try:
        with open(path, errors="replace") as f:
            return f.read(MAX_CONTENT)
    except OSError:
        return None


def git_processes(proc="/proc"):
    out = []
    for pid in os.listdir(proc):
        if not pid.isdigit():
            continue
        try:
            with open(f"{proc}/{pid}/cmdline", "rb") as f:
                argv = [a.decode(errors="replace") for a in f.read().split(b"\0") if a]
        except OSError:
            continue
        if not argv or not os.path.basename(argv[0]).split("-", 1)[0] == "git":
            continue
        try:
            cwd = os.readlink(f"{proc}/{pid}/cwd")
        except OSError:
            cwd = None
        out.append({"pid": int(pid), "argv": argv, "cwd": cwd})
    return out


def log_event(log, path, content, event):
    rec = {"ts": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "event": event, "file": path, "content": content,
           "git_processes": git_processes()}
    try:
        os.makedirs(os.path.dirname(log), exist_ok=True)
        with open(log, "a") as f:
            f.write(json.dumps(rec) + "\n")
    except OSError as e:   # a full disk must not stop the watch
        print(f"watch_git_config: cannot write {log}: {e}", file=sys.stderr)


def scan(files, state, log, first=False):
    """One pass: state maps path -> last bare value. Logs each false/absent -> true transition."""
    for p in files:
        text = read(p)
        if text is None:   # a replace in progress or an absent repo: keep the last state, so a rename never re-fires
            continue
        now, was = is_bare(text), state.get(p, False)
        if now and not was:
            log_event(log, p, text, "already-true-at-start" if first else "became-true")
        state[p] = now


def wait_change(files, inotify):
    """Block up to POLL_S; inotify only ends the wait sooner, the content scan decides."""
    if inotify:
        dirs = sorted({os.path.dirname(p) for p in files if os.path.isdir(os.path.dirname(p))})
        if dirs:
            subprocess.run([inotify, "-qq", "-t", "1", "-e", "close_write,moved_to,create", *dirs],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            return
    time.sleep(POLL_S)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--file", action="append", help="watch this config instead of the defaults (repeatable)")
    ap.add_argument("--log", default=LOG)
    ap.add_argument("--max-passes", type=int, default=0, help="stop after N passes (tests); 0 = forever")
    a = ap.parse_args(argv)
    files, state, inotify = a.file or list(FILES), {}, shutil.which("inotifywait")
    scan(files, state, a.log, first=True)
    n = 0
    while not a.max_passes or n < a.max_passes:
        wait_change(files, inotify)
        scan(files, state, a.log)
        n += 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
