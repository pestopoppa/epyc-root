#!/usr/bin/env python3
"""safe_download.py — run any download command so it cannot leave partial files behind.

WHY. The 2026-10-03 disk audit found 9.2 GB of `*.incomplete` stubs from aborted HF downloads,
a 35.9 GB `.part2` chunk kept after its join, and stray multi-GB GGUFs in /tmp. Every download
on this host is an ad-hoc `hf download` / `huggingface-cli` / `curl` / `wget` / `aria2c`, and
none of them cleans up after an abort. This wrapper is the one place that does:

    python3 scripts/utils/safe_download.py --dest /mnt/raid0/llm/models/<org>/<repo> -- \
        hf download <org>/<repo> --include '*Q4_K_M*' --local-dir /mnt/raid0/llm/models/<org>/<repo>

    python3 scripts/utils/safe_download.py --check /mnt/raid0/llm/models      # list leftovers

What it does around the command:
  * refuses a --dest under /tmp or /var/tmp (large artifacts belong on /mnt/raid0; pass
    --allow-tmp for a deliberate small download), and defaults HF_HOME / TMPDIR to the project
    locations (OPERATING_CONSTRAINTS.md "Filesystem and Storage") when they are unset or /tmp;
  * forwards SIGINT/SIGTERM to the command, so an interrupted run still reaches the cleanup;
  * afterwards finds partial files (`*.part`, `*.incomplete`, `*.aria2`, `*.crdownload`) under
    --dest that THIS run created or modified (mtime >= start) and that no process holds open, then:
      - command succeeded  -> deletes them (a finished download has no use for its stubs);
      - command failed     -> deletes them, unless --keep-partial (keep to resume; they are
                              then still logged, and the daily hygiene scan reports them after 24 h);
  * appends one JSONL record per run that found any partial to the ledger
    (default /mnt/raid0/llm/epyc-root/logs/hygiene/partial_downloads.jsonl).
It never touches a partial file it did not create in this run (mtime before the start) — those
belong to a concurrent or earlier download; `--check` lists them.

Exit code: the command's own exit code (130 on SIGINT); 2 usage/refusal; `--check`: 0 none, 3 found.
Tests: tests/test_safe_download.py
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

PARTIAL_SUFFIXES = (".part", ".incomplete", ".aria2", ".crdownload")
TMP_ROOTS = ("/tmp", "/var/tmp")
DEFAULT_LEDGER = os.environ.get(
    "SAFE_DOWNLOAD_LEDGER", "/mnt/raid0/llm/epyc-root/logs/hygiene/partial_downloads.jsonl")
PROJECT_ENV = {"HF_HOME": "/mnt/raid0/llm/cache/huggingface", "TMPDIR": "/mnt/raid0/llm/tmp"}


def is_partial(name: str) -> bool:
    return name.endswith(PARTIAL_SUFFIXES)


def find_partials(dest: str) -> list[str]:
    out = []
    for dirpath, _dirnames, filenames in os.walk(dest):      # hidden dirs (.cache/huggingface) too
        out += [os.path.join(dirpath, f) for f in filenames if is_partial(f)]
    return out


def open_paths(proc_root: str = "/proc") -> set[str]:
    held: set[str] = set()
    try:
        pids = [p for p in os.listdir(proc_root) if p.isdigit()]
    except OSError:
        return held
    for pid in pids:
        try:
            fds = os.listdir(f"{proc_root}/{pid}/fd")
        except OSError:
            continue
        for fd in fds:
            try:
                held.add(os.readlink(f"{proc_root}/{pid}/fd/{fd}"))
            except OSError:
                continue
    return held


def under_tmp(path: str) -> bool:
    real = os.path.realpath(path)
    return any(real == r or real.startswith(r + "/") for r in TMP_ROOTS)


def ledger_write(ledger: str, rec: dict) -> None:
    try:
        Path(ledger).parent.mkdir(parents=True, exist_ok=True)
        with open(ledger, "a") as fh:
            fh.write(json.dumps(rec) + "\n")
    except OSError as exc:
        print(f"safe_download: could not write ledger {ledger}: {exc}", file=sys.stderr)


def cleanup(dest: str, start: float, rc: int, keep: bool, ledger: str, argv: list[str]) -> list[dict]:
    held = open_paths()
    rows = []
    for p in find_partials(dest):
        try:
            st = os.lstat(p)
        except OSError:
            continue
        if st.st_mtime < start - 1:          # not ours: an earlier or concurrent download's file
            continue
        row = {"path": p, "bytes": st.st_size}
        if p in held:
            row["action"] = "kept-held-open"
        elif keep and rc != 0:
            row["action"] = "kept-for-resume"
        else:
            try:
                os.unlink(p)
                row["action"] = "deleted"
            except OSError as exc:
                row["action"] = f"delete-failed: {exc}"
        rows.append(row)
    if rows:
        ledger_write(ledger, {"at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                              "dest": dest, "rc": rc, "argv": argv, "partials": rows})
        for r in rows:
            print(f"safe_download: {r['action']}: {r['path']} ({r['bytes']} B)", file=sys.stderr)
    return rows


def main(argv: list[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    cmd: list[str] = []
    if "--" in raw:
        i = raw.index("--")
        raw, cmd = raw[:i], raw[i + 1:]
    ap = argparse.ArgumentParser(description="run a download command without leaving partial files")
    ap.add_argument("--dest", help="directory the command downloads into")
    ap.add_argument("--check", metavar="DIR", help="list partial files under DIR and exit")
    ap.add_argument("--keep-partial", action="store_true", help="on failure keep this run's partials to resume")
    ap.add_argument("--allow-tmp", action="store_true", help="permit a --dest under /tmp")
    ap.add_argument("--ledger", default=DEFAULT_LEDGER)
    a = ap.parse_args(raw)

    if a.check:
        held = open_paths()
        found = find_partials(a.check)
        now = time.time()
        for p in found:
            try:
                st = os.lstat(p)
            except OSError:
                continue
            tag = "held-open" if p in held else f"age {(now - st.st_mtime) / 3600:.1f} h"
            print(f"{st.st_size}\t{tag}\t{p}")
        return 3 if found else 0

    if not a.dest or not cmd:
        ap.error("need --dest DIR -- <download command...> (or --check DIR)")
    if under_tmp(a.dest) and not a.allow_tmp:
        print(f"REFUSED: --dest {a.dest} is under /tmp; large artifacts go under /mnt/raid0 "
              "(pass --allow-tmp for a deliberate small download)", file=sys.stderr)
        return 2
    os.makedirs(a.dest, exist_ok=True)
    env = dict(os.environ)
    for k, v in PROJECT_ENV.items():
        if not env.get(k) or under_tmp(env[k]):
            env[k] = v
    start = time.time()
    proc = subprocess.Popen(cmd, env=env)
    got: list[int] = []

    def forward(signum, _frame):
        got.append(signum)
        try:
            proc.send_signal(signum)
        except ProcessLookupError:
            pass

    old = {s: signal.signal(s, forward) for s in (signal.SIGINT, signal.SIGTERM)}
    try:
        rc = proc.wait()
    finally:
        for s, h in old.items():
            signal.signal(s, h)
    if got and rc >= 0:
        rc = 128 + got[0] if rc == 0 else rc
    elif rc < 0:
        rc = 128 - rc
    cleanup(a.dest, start, rc, a.keep_partial, a.ledger, cmd)
    return rc


if __name__ == "__main__":
    sys.exit(main())
