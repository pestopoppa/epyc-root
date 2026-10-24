#!/usr/bin/env python3
"""Write a self-hashed GitNexus index-freshness receipt (VB-GNX-REINDEX-1 write side).

A re-index job calls this AFTER ``scripts/gitnexus-analyze.sh`` returns 0, so impact checks can cite index
freshness by sha instead of by a pasted ``gitnexus status`` line:

    /usr/bin/python3 -I scripts/gitnexus-index-receipt.py --repo /mnt/raid0/llm/epyc-orchestrator \\
        --out <job>/out/index_receipt.json [--job-result <job>/RESULT.json]

The receipt is DEPENDENCY EVIDENCE about tool state (the index is fresh at a commit), not a measurement: it
registers no ClaimTuple and emits no ``evidence_supports_claim`` (scripts/vidya/adapters/README.md, GitNexus
re-index row). Every field is READ, never inferred:

* repo / branch / indexed commit / indexedAt / node, edge, file, community, process and embedding counts come
  from the index's own ``.gitnexus/meta.json`` (its sha256 is recorded too);
* HEAD and ``origin/main`` are ``git rev-parse`` at read time -- no fetch is done, so ``origin_main`` is the
  local remote-tracking ref as of ``read_at`` and says so;
* ``gitnexus_version`` is ``gitnexus --version``; absent when the CLI is not on PATH (recorded as null).

``content_sha256`` is sha256 over the canonical JSON (sorted keys, compact separators) of every other field.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "epyc.gitnexus.index_receipt.v1"


def _canon(obj: object) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


def _git(repo: Path, *args: str) -> str | None:
    try:
        out = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() or None


def _gitnexus_version() -> str | None:
    try:
        out = subprocess.run(["gitnexus", "--version"], capture_output=True, text=True, check=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip().splitlines()[-1] if out.stdout.strip() else None


def build(repo: Path, *, job_result: Path | None = None, read_at: str | None = None) -> dict:
    meta_path = repo / ".gitnexus" / "meta.json"
    raw = meta_path.read_bytes()
    meta = json.loads(raw)
    stats = meta.get("stats") if isinstance(meta.get("stats"), dict) else {}
    head = _git(repo, "rev-parse", "HEAD")
    body = {
        "schema": SCHEMA,
        "read_at": read_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "repo": str(repo),
        "index_repo_path": meta.get("repoPath"),
        "index_branch": meta.get("branch"),
        "indexed_commit": meta.get("lastCommit"),
        "indexed_at": meta.get("indexedAt"),
        "index_schema_version": meta.get("schemaVersion"),
        "stats": {k: stats.get(k) for k in ("files", "nodes", "edges", "communities", "processes", "embeddings")},
        "meta_json_sha256": hashlib.sha256(raw).hexdigest(),
        "git_branch": _git(repo, "branch", "--show-current"),
        "git_head": head,
        "origin_main": _git(repo, "rev-parse", "--verify", "-q", "refs/remotes/origin/main"),
        "origin_main_basis": "local remote-tracking ref at read_at; no fetch was performed",
        "fresh_at_head": bool(head) and head == meta.get("lastCommit"),
        "gitnexus_version": _gitnexus_version(),
        "job_result": None,
    }
    if job_result is not None:
        jr = job_result.read_bytes()
        body["job_result"] = {"path": str(job_result), "sha256": hashlib.sha256(jr).hexdigest()}
    body["content_sha256"] = hashlib.sha256(_canon(body)).hexdigest()
    return body


def verify(receipt: dict) -> bool:
    body = {k: v for k, v in receipt.items() if k != "content_sha256"}
    return receipt.get("schema") == SCHEMA and hashlib.sha256(_canon(body)).hexdigest() == receipt.get("content_sha256")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--job-result", type=Path)
    a = ap.parse_args(argv)
    receipt = build(a.repo.resolve(), job_result=a.job_result)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=a.out.parent, prefix=".receipt-")
    with os.fdopen(fd, "w") as fh:
        json.dump(receipt, fh, indent=1, sort_keys=True)
        fh.write("\n")
    os.replace(tmp, a.out)
    print(json.dumps({"out": str(a.out), "content_sha256": receipt["content_sha256"],
                      "indexed_commit": receipt["indexed_commit"], "fresh_at_head": receipt["fresh_at_head"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
