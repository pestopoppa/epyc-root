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

SEC-ART-1 provenance (handoffs/active/model-artifact-integrity.md). With `--hf-repo ORG/REPO [--revision REF]`
the wrapper, BEFORE the command runs, resolves REF (default `main`) to a 40-hex commit sha through the HF API
and, for `hf|huggingface-cli download ...` commands, appends `--revision <sha>` so the bytes fetched are the
bytes pinned (no ref-moves-mid-download race). After a successful run it reads the tree at that sha
(`?recursive=1&expand=1`) and appends one record to the PROVENANCE ledger
(default <epyc-root>/data/provenance/model_downloads.jsonl, override --provenance-ledger / SAFE_DOWNLOAD_PROVENANCE_LEDGER):
the resolved commit and, for every tree file present under --dest, its path, size, LFS sha256 (the oid; null for
non-LFS files, which carry the git blob oid instead) and whether the local size matches. Nothing is hashed locally.
The ledger is a TRACKED path, not logs/: provenance evidence must resolve in git history (a deleted or rewritten
line shows in a diff) and survive log rotation/hygiene sweeps; records are ~1 KB per download. Append-only by
convention (open mode "a"); commit it with the registry change that cites it. If the ref cannot be resolved the
run is REFUSED (exit 2) unless --no-resolve.

Exit code: the command's own exit code (130 on SIGINT); 2 usage/refusal; `--check`: 0 none, 3 found.
Tests: tests/test_safe_download.py
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import signal
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

PARTIAL_SUFFIXES = (".part", ".incomplete", ".aria2", ".crdownload")
TMP_ROOTS = ("/tmp", "/var/tmp")
DEFAULT_LEDGER = os.environ.get(
    "SAFE_DOWNLOAD_LEDGER", "/mnt/raid0/llm/epyc-root/logs/hygiene/partial_downloads.jsonl")
DEFAULT_PROVENANCE_LEDGER = os.environ.get(
    "SAFE_DOWNLOAD_PROVENANCE_LEDGER", "/mnt/raid0/llm/epyc-root/data/provenance/model_downloads.jsonl")
LEDGER_SCHEMA = "model-download-ledger/1"
HF_ENDPOINT = "https://huggingface.co"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
HF_REPO_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*/[A-Za-z0-9][A-Za-z0-9._-]*$")
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


def hf_get_json(url: str):
    """GET a HF API URL as JSON (HF_TOKEN honoured). Tests replace this function."""
    req = urllib.request.Request(url, headers={"User-Agent": "epyc-safe-download/1"})
    if os.environ.get("HF_TOKEN"):
        req.add_header("Authorization", f"Bearer {os.environ['HF_TOKEN']}")
    with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310 - fixed https host
        return json.load(resp)


def resolve_revision(repo: str, ref: str) -> str:
    """Resolve a branch/tag/sha to the 40-hex commit sha (a sha still round-trips the API, proving it exists)."""
    info = hf_get_json(f"{HF_ENDPOINT}/api/models/{repo}/revision/{urllib.parse.quote(ref, safe='')}")
    sha = info.get("sha", "")
    if not SHA40.match(sha):
        raise ValueError(f"HF returned no 40-hex commit sha for {repo}@{ref}: {sha!r}")
    return sha


def inject_revision(cmd: list[str], sha: str) -> list[str]:
    """Pin `hf download` / `huggingface-cli download` to the resolved sha; other commands are left alone."""
    is_hf = (len(cmd) >= 2 and os.path.basename(cmd[0]) in ("hf", "huggingface-cli") and cmd[1] == "download")
    if not is_hf:
        return cmd
    out, i = [], 0
    while i < len(cmd):                       # replace any caller --revision with the resolved sha
        if cmd[i] == "--revision":
            i += 2
            continue
        if cmd[i].startswith("--revision="):
            i += 1
            continue
        out.append(cmd[i])
        i += 1
    return out + ["--revision", sha]


def provenance_record(repo: str, requested: str, sha: str, dest: str, rc: int, argv: list[str]) -> dict:
    """Ledger record: per-file LFS sha256 for tree files present under dest. Reads the tree API; hashes nothing."""
    tree = hf_get_json(f"{HF_ENDPOINT}/api/models/{repo}/tree/{sha}?recursive=1&expand=1")
    files = []
    for e in tree:
        if e.get("type") != "file":
            continue
        local = os.path.join(dest, e["path"])
        if not os.path.isfile(local):
            continue
        lfs = e.get("lfs") or {}
        size = os.path.getsize(local)
        files.append({"path": e["path"], "size": size,
                      "sha256": lfs.get("oid"), "git_oid": e.get("oid"), "lfs": bool(lfs),
                      "size_matches_upstream": size == (lfs.get("size") if lfs else e.get("size"))})
    return {"schema": LEDGER_SCHEMA, "at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "hf_repo": repo, "requested_revision": requested, "hf_revision": sha,
            "dest": dest, "rc": rc, "argv": argv, "files": files}


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
    ap.add_argument("--hf-repo", help="ORG/REPO being downloaded: pin the revision and record the SEC-ART-1 ledger")
    ap.add_argument("--revision", default="main", help="branch/tag/sha for --hf-repo (resolved to a commit sha)")
    ap.add_argument("--no-resolve", action="store_true", help="with --hf-repo: proceed if the ref cannot be resolved (no ledger)")
    ap.add_argument("--provenance-ledger", default=DEFAULT_PROVENANCE_LEDGER)
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
    sha = None
    if a.hf_repo:
        if not HF_REPO_RE.match(a.hf_repo):
            print(f"REFUSED: --hf-repo {a.hf_repo!r} is not ORG/REPO", file=sys.stderr)
            return 2
        try:
            sha = resolve_revision(a.hf_repo, a.revision)
        except Exception as exc:  # noqa: BLE001 - any resolution failure is a refusal
            if not a.no_resolve:
                print(f"REFUSED: cannot resolve {a.hf_repo}@{a.revision} to a commit sha ({exc}); "
                      "pass --no-resolve to download unpinned (nothing is recorded)", file=sys.stderr)
                return 2
            print(f"safe_download: WARNING unpinned download, ledger skipped ({exc})", file=sys.stderr)
        else:
            cmd = inject_revision(cmd, sha)
            print(f"safe_download: pinned {a.hf_repo}@{a.revision} -> {sha}", file=sys.stderr)
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
    if sha and rc == 0:
        try:
            ledger_write(a.provenance_ledger, provenance_record(a.hf_repo, a.revision, sha, a.dest, rc, cmd))
        except Exception as exc:  # noqa: BLE001 - the download succeeded; say loudly the record did not
            print(f"safe_download: ERROR provenance ledger NOT written: {exc}", file=sys.stderr)
            return rc or 4
    return rc


if __name__ == "__main__":
    sys.exit(main())
