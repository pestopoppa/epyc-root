#!/usr/bin/env python3
"""pending_operator_cmds.py -- the operator command accumulator (operator-steering report 2026-11-21, item 6).

Sessions append the sudo / ratify / host commands only the operator can run, each with a reason. The operator
gets ONE copy-paste line (or a short script) instead of commands scattered over many reports.

    pending_operator_cmds.py add --cmd '<command>' --reason '<why>' [--session <id>] [--kind sudo|ratify|host|other]
    pending_operator_cmds.py list [--json]
    pending_operator_cmds.py clear (--id <id> | --session <id> | --all)
    pending_operator_cmds.py combined [--script]

Storage: one JSON file per entry under $EPYC_OPERATOR_CMDS_DIR (default
/mnt/raid0/llm/tmp/compute-flags/operator-cmds/). One file per entry, written with O_EXCL, so concurrent sessions
never race on a shared file. `clear` moves entries into done/ (never deletes). Identical commands are de-duplicated
(the second `add` returns the existing id). Zero compute, stdlib only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import sys
from datetime import datetime, timezone

DEFAULT_DIR = "/mnt/raid0/llm/tmp/compute-flags/operator-cmds"
SCHEMA = "epyc.operator_cmd.v1"
KINDS = ("sudo", "ratify", "host", "other")


def store_dir(d: str | None = None) -> str:
    return d or os.environ.get("EPYC_OPERATOR_CMDS_DIR") or DEFAULT_DIR


def _cid(cmd: str) -> str:
    return hashlib.sha256(" ".join(cmd.split()).encode()).hexdigest()[:12]


def add(cmd: str, reason: str, session: str = "?", kind: str = "other", d: str | None = None) -> tuple[str, bool]:
    """Returns (id, created). An identical pending command is not added twice."""
    cmd = cmd.strip()
    if not cmd or "\n" in cmd:
        raise ValueError("cmd must be one non-empty line")
    if not reason.strip():
        raise ValueError("reason is required")
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {KINDS}")
    d = store_dir(d)
    os.makedirs(d, exist_ok=True)
    cid = _cid(cmd)
    p = os.path.join(d, cid + ".json")
    doc = {"schema": SCHEMA, "id": cid, "cmd": cmd, "reason": reason.strip(), "session": session, "kind": kind,
           "added_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    try:
        fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError:
        return cid, False
    with os.fdopen(fd, "w") as fh:
        json.dump(doc, fh, indent=1)
        fh.write("\n")
    return cid, True


def entries(d: str | None = None) -> list[dict]:
    d = store_dir(d)
    out = []
    if not os.path.isdir(d):
        return out
    for n in sorted(os.listdir(d)):
        if not n.endswith(".json"):
            continue
        try:
            e = json.load(open(os.path.join(d, n)))
        except (OSError, ValueError):
            out.append({"id": n[:-5], "cmd": None, "reason": f"UNREADABLE entry {n}", "bad": True})
            continue
        if isinstance(e, dict) and e.get("cmd"):
            out.append(e)
    # ratify before sudo before host: a ratify usually unblocks the rest
    order = {k: i for i, k in enumerate(("ratify", "sudo", "host", "other"))}
    return sorted(out, key=lambda e: (order.get(e.get("kind"), 9), e.get("added_at") or "", e["id"]))


def clear(d: str | None = None, cid: str | None = None, session: str | None = None, everything: bool = False) -> int:
    d = store_dir(d)
    done = os.path.join(d, "done")
    n = 0
    for e in entries(d):
        if e.get("bad"):
            continue
        if everything or (cid and e["id"] == cid) or (session and e.get("session") == session):
            os.makedirs(done, exist_ok=True)
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            os.replace(os.path.join(d, e["id"] + ".json"), os.path.join(done, f"{e['id']}.{stamp}.json"))
            n += 1
    return n


def combined(d: str | None = None, script: bool = False) -> str:
    es = [e for e in entries(d) if not e.get("bad")]
    if not es:
        return ""
    if script or len(es) > 4:
        lines = ["#!/bin/bash", "# pending operator commands -- run top to bottom; stops on the first failure",
                 "set -euo pipefail"]
        for e in es:
            lines.append(f"# [{e['id']}] {e.get('kind')} from {e.get('session')}: {e.get('reason')}")
            lines.append(e["cmd"])
        lines.append(f"python3 {shlex.quote(os.path.abspath(__file__))} clear --all")
        return "\n".join(lines)
    return " && ".join(f"( {e['cmd']} )" for e in es) + \
        f" && python3 {shlex.quote(os.path.abspath(__file__))} clear --all"


def render_md(d: str | None = None) -> str:
    es = entries(d)
    if not es:
        return "none pending"
    out = [f"- `{e['id']}` {e.get('kind')} ({e.get('session')}): {e.get('reason')}" for e in es]
    c = combined(d)
    if c:
        out += ["", "Run:" if "\n" not in c else "Run as a script:", "```", c, "```"]
    return "\n".join(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dir")
    sp = ap.add_subparsers(dest="op", required=True)
    a = sp.add_parser("add")
    a.add_argument("--cmd", required=True)
    a.add_argument("--reason", required=True)
    a.add_argument("--session", default=os.environ.get("AGENT_ID", "?"))
    a.add_argument("--kind", default="other", choices=KINDS)
    ls = sp.add_parser("list")
    ls.add_argument("--json", action="store_true")
    c = sp.add_parser("clear")
    g = c.add_mutually_exclusive_group(required=True)
    g.add_argument("--id")
    g.add_argument("--session")
    g.add_argument("--all", action="store_true")
    cb = sp.add_parser("combined")
    cb.add_argument("--script", action="store_true")
    x = ap.parse_args(argv)
    if x.op == "add":
        try:
            cid, new = add(x.cmd, x.reason, x.session, x.kind, x.dir)
        except ValueError as e:
            print(f"REFUSED: {e}", file=sys.stderr)
            return 2
        print(f"{'added' if new else 'already pending'} {cid}")
    elif x.op == "list":
        es = entries(x.dir)
        if x.json:
            json.dump(es, sys.stdout, indent=1)
            print()
        else:
            print(render_md(x.dir))
    elif x.op == "clear":
        print(f"cleared {clear(x.dir, x.id, x.session, x.all)}")
    else:
        out = combined(x.dir, x.script)
        print(out if out else "# no pending operator commands")
    return 0


if __name__ == "__main__":
    sys.exit(main())
