#!/usr/bin/env python3
"""toolroot - which code a churn tool runs, and where it reads config (F5, AK audit B5/C5, D9 2026-11-20).

Every churn tool (publish_row, file_result, session_bus, queue_status) calls banner(__file__) at startup:
  (a) prints `tool-commit <sha>` to stderr: bin/rowflow/DEPLOYED.json `sha` for an installed copy (compute-flags/bin/...),
      else `git rev-parse HEAD` of the file's own tree;
  (b) resolve(rel) returns a config path (roster config.yaml, holds.yaml, templates) from the hub view first
      (/mnt/raid0/llm/views/epyc-root-main, tracks origin/main), else the file's own checkout;
  (c) when the file runs from a checkout > STALE_COMMITS behind origin/main (one `git rev-list --count`, 2 s timeout,
      cached per hour) prints `WARN: checkout N commits behind origin/main; tools/config read from <hub>`.
No behaviour change otherwise; nothing here ever raises into the caller.
"""
import json
import os
import subprocess
import sys
import time

HUB = os.environ.get("TOOLROOT_HUB", "/mnt/raid0/llm/views/epyc-root-main")
STALE_COMMITS = 50
GIT_TIMEOUT_S = 2
CACHE_TTL_S = 3600
CACHE_DIR = os.environ.get("TOOLROOT_CACHE", "/mnt/raid0/llm/" + "tmp/toolroot-cache")


def _git(cwd, *args):
    try:
        r = subprocess.run(["git", "-C", cwd, *args], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                           stdin=subprocess.DEVNULL, timeout=GIT_TIMEOUT_S)
        return r.stdout.decode().strip() if r.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def deployed_json(path):
    """bin/rowflow/DEPLOYED.json for a file installed under compute-flags/bin/<x>/, else None."""
    d = os.path.dirname(os.path.abspath(path))
    for cand in (os.path.join(d, "DEPLOYED.json"), os.path.join(d, "..", "rowflow", "DEPLOYED.json"),
                 os.path.join(d, "rowflow", "DEPLOYED.json")):
        if os.path.isfile(cand):
            return os.path.normpath(cand)
    return None


def tool_commit(path):
    """(sha, source) of the code `path` belongs to."""
    dj = deployed_json(path)
    if dj:
        try:
            d = json.load(open(dj))
            if d.get("sha"):
                return str(d["sha"]), dj
        except (OSError, ValueError):
            pass
    sha = _git(os.path.dirname(os.path.abspath(path)), "rev-parse", "HEAD")
    return (sha or "unknown"), "git"


def checkout_root(path):
    return _git(os.path.dirname(os.path.abspath(path)), "rev-parse", "--show-toplevel")


def behind(root):
    """Commits HEAD of `root` is behind origin/main; cached per hour per root (None = unknown)."""
    key = os.path.join(CACHE_DIR, root.strip("/").replace("/", "_") + ".json")
    try:
        c = json.load(open(key))
        if time.time() - float(c["at"]) < CACHE_TTL_S:
            return c["n"]
    except (OSError, ValueError, KeyError, TypeError):
        pass
    counts = []
    out = _git(root, "rev-list", "--count", "HEAD..origin/main")
    if out and out.isdigit():
        counts.append(int(out))
    # review S3: a never-fetched clone's origin/main is as stale as its HEAD; the hub view's HEAD is fetched by the view
    hub_head = _git(HUB, "rev-parse", "HEAD") if os.path.isdir(HUB) else None
    if hub_head:
        out = _git(root, "rev-list", "--count", f"HEAD..{hub_head}")
        if out and out.isdigit():
            counts.append(int(out))
        elif _git(root, "merge-base", "--is-ancestor", hub_head, "HEAD") is None:
            counts.append(STALE_COMMITS + 1)   # the checkout does not even hold the hub's HEAD: older than any count
    n = max(counts) if counts else None
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        tmp = f"{key}.{os.getpid()}.tmp"
        json.dump({"at": time.time(), "n": n}, open(tmp, "w"))
        os.replace(tmp, key)
    except OSError:
        pass
    return n


def resolve(rel, path=None):
    """A repo-relative config path: the hub view's copy first, else the caller's own checkout's."""
    hub = os.path.join(HUB, rel)
    if os.path.exists(hub):
        return hub
    root = checkout_root(path) if path else None
    return os.path.join(root, rel) if root else hub


def banner(path, out=None):
    """Print tool-commit (and the stale-checkout WARN) to stderr. Returns the lines printed; never raises."""
    out = out or sys.stderr
    lines = []
    try:
        sha, src = tool_commit(path)
        lines.append(f"tool-commit {sha[:12]} ({os.path.basename(path)}, {'deployed' if src != 'git' else 'checkout'})")
        if src == "git":
            root = checkout_root(path)
            if root and os.path.realpath(root) != os.path.realpath(HUB):
                n = behind(root)
                if n is not None and n > STALE_COMMITS:
                    lines.append(f"WARN: checkout {n} commits behind origin/main; tools/config read from {HUB}")
        for ln in lines:
            print(ln, file=out)
    except Exception:  # noqa: BLE001 - a banner never breaks the tool
        pass
    return lines
