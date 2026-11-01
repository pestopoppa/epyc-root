#!/usr/bin/env python3
"""keeper_qual_memo.py - durable memo of the keeper's last qualification refusal per READY row.

Why (ws58 2026-11-01, GPU-idle incident): keeper v8 ran ONE real qualification per tick, took the first
`would-qualify` row in priority order and ended the tick whatever the outcome. A row that the qualifier refuses
before any native attempt (no FILLERS.md registry row, bad fixture, ...) therefore monopolised the slot every
tick and starved every lower-ranked row - the only runnable GPU row never got qualified. Keeper v9 writes a memo
on every refusal and skips the row while it is UNCHANGED; backlog_gen.py reads the same memo as the row's
blocking task (independent of the keeper-log window).

A memo binds the refusal to the exact inputs the qualifier saw:
    manifest sha256, ready/<id>.row.md sha256, and the FILLERS.md row(s) for the id (the registry row is what
    `row_binding` reads; the NI rows failed for lack of one). Any change invalidates the memo and the keeper
    retries at its next tick. Nothing here is a qualification; it only decides WHEN to retry one.

    keeper_qual_memo.py held  <manifest> [--flags DIR]   exit 0 = memo current (skip), 1 = retry, 2 = bad input
    keeper_qual_memo.py write <manifest> <reason> [--flags DIR]
    keeper_qual_memo.py show  <manifest> [--flags DIR]    prints the memo JSON or {}

Memo path: <flags>/ws58-keeper-state/qual-refused/<id>.json
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import sys

FLAGS_DEFAULT = "/mnt/raid0/llm/tmp/compute-flags"
MEMO_DIR = "ws58-keeper-state/qual-refused"


def _sha_file(path: str) -> str:
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except OSError:
        return "absent"


def _sha_fillers_rows(flags: str, rid: str) -> str:
    """sha256 of every FILLERS.md line that is this id's registry row (the lines row_binding reads)."""
    h = hashlib.sha256()
    n = 0
    try:
        with open(os.path.join(flags, "FILLERS.md"), errors="replace") as f:
            for line in f:
                if line.startswith("| " + rid + " |") or line.startswith("|" + rid + "|"):
                    h.update(line.encode()); n += 1
    except OSError:
        return "absent"
    return f"{n}:{h.hexdigest()}"


def row_id(manifest: str) -> str:
    try:
        d = json.load(open(manifest))
        if isinstance(d, dict) and isinstance(d.get("id"), str) and d["id"]:
            return d["id"]
    except (OSError, ValueError):
        pass
    return os.path.basename(manifest)[:-5] if manifest.endswith(".json") else os.path.basename(manifest)


def fingerprint(manifest: str, flags: str) -> dict:
    rid = row_id(manifest)
    row_md = os.path.join(flags, "ready", rid + ".row.md")
    return {"id": rid, "manifest_sha256": _sha_file(manifest), "row_sha256": _sha_file(row_md),
            "fillers_rows_sha256": _sha_fillers_rows(flags, rid)}


def memo_path(flags: str, rid: str) -> str:
    return os.path.join(flags, MEMO_DIR, rid + ".json")


def read_memo(flags: str, rid: str) -> dict | None:
    try:
        d = json.load(open(memo_path(flags, rid)))
        return d if isinstance(d, dict) else None
    except (OSError, ValueError):
        return None


def is_current(memo: dict | None, fp: dict) -> bool:
    if not memo:
        return False
    return all(memo.get(k) == fp[k] for k in ("id", "manifest_sha256", "row_sha256", "fillers_rows_sha256"))


def current_memo(manifest: str, flags: str = FLAGS_DEFAULT) -> dict | None:
    """The memo if it still describes the row as it is on disk now, else None (library entry point)."""
    fp = fingerprint(manifest, flags)
    m = read_memo(flags, fp["id"])
    return m if is_current(m, fp) else None


def write(manifest: str, reason: str, flags: str = FLAGS_DEFAULT, keeper: str = "") -> dict:
    fp = fingerprint(manifest, flags)
    prior = read_memo(flags, fp["id"]) or {}
    memo = dict(fp, reason=reason[:600], at=_dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                keeper=keeper or os.environ.get("WS58_KEEPER_VERSION", ""),
                refusals=int(prior.get("refusals") or 0) + 1 if is_current(prior, fp) else 1)
    p = memo_path(flags, fp["id"])
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp." + str(os.getpid())
    with open(tmp, "w") as f:
        json.dump(memo, f, sort_keys=True, indent=1); f.write("\n")
    os.replace(tmp, p)
    return memo


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=("held", "write", "show"))
    ap.add_argument("manifest")
    ap.add_argument("reason", nargs="?", default="")
    ap.add_argument("--flags", default=FLAGS_DEFAULT)
    a = ap.parse_args(argv)
    if not os.path.isfile(a.manifest):
        print("REFUSED: manifest missing", file=sys.stderr); return 2
    if a.command == "write":
        if not a.reason.strip():
            print("REFUSED: reason required", file=sys.stderr); return 2
        m = write(a.manifest, a.reason, a.flags)
        print(json.dumps({"memo": memo_path(a.flags, m["id"]), "refusals": m["refusals"]})); return 0
    m = current_memo(a.manifest, a.flags)
    if a.command == "show":
        print(json.dumps(m or {}, sort_keys=True)); return 0
    if m:
        print(f"held\t{m['id']}: refused {m.get('refusals', 1)}x since {m.get('at')}; unchanged: {m.get('reason', '')[:200]}")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
