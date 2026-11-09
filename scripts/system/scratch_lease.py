#!/usr/bin/env python3
"""scratch_lease.py — owner + TTL for KEEP markers under /mnt/raid0/llm/tmp (scratch-lease Phase 1).

WHY. A KEEP marker (`KEEP`, `.epyc-keep`, `.epyc-load-bearing`, `LOAD-BEARING`, or a sibling
`<dir>.epyc-keep`) had no owner and no expiry, and every reaper honoured it forever: on 2026-11-04
451 dirs / 166.6 GiB were KEEP-marked, 201 with the same blanket text from workspace-58 on 10-25
(operator-directed scratch-leak structural fix, 2026-11-04).

STORAGE (one place, not sidecars). Leases live in ONE directory, default
`/mnt/raid0/llm/tmp/.scratch-leases/` (override: env SCRATCH_LEASE_DIR), one JSON file per
target, named `<sha256(realpath(target))[:24]>.json`. A single dir was chosen over sidecars
because a sidecar written inside a target bumps its idle clock and dirties a worktree, and a
dot-prefixed dir under tmp is already skipped by the keeper's idle rule.

SCHEMA (epyc.scratch_lease.v1):
    {schema, owner, target, handoff_or_row, created, expires, budget_gib, reason}
    created/expires are ISO-8601 UTC (`YYYY-MM-DDTHH:MM:SSZ`).

SEMANTICS (marker_blocks): a KEEP marker WITHOUT a lease blocks reaping (legacy behaviour, so
nothing changes until `backfill --apply`); a marker with an UNEXPIRED lease blocks; a marker with
an EXPIRED lease no longer blocks — the item then faces every other guard as unmarked scratch.
An unreadable or malformed lease fails CLOSED (blocks).

CLI:
    scratch_lease.py backfill --dry-run|--apply [--ttl-days 14] [--root /mnt/raid0/llm/tmp]
    scratch_lease.py report [--root ...] [--json]
    scratch_lease.py show <dir>
    scratch_lease.py allocate <name> --owner OWNER --ttl-days N [--row ROW] [--budget-gib G] [--reason TXT] [--root ...]
allocate (Phase 2) is THE way to create scratch: it makes <root>/<name>, writes the KEEP marker and the
lease (owner + expiry) in one step, so nothing is ever born unowned. Owner and TTL are mandatory.
backfill is idempotent: a target that already has a lease is never rewritten.
Tests: tests/test_scratch_lease.py, tests/test_scratch_lease_allocate.py (temp dirs only).
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
import time

SCHEMA = "epyc.scratch_lease.v1"
TMP_ROOT = "/mnt/raid0/llm/tmp"
DEFAULT_LEASE_DIR = os.path.join(TMP_ROOT, ".scratch-leases")
KEEP_MARKERS = (".epyc-keep", ".epyc-load-bearing", "KEEP", "LOAD-BEARING")  # == worktree_gate.KEEP_MARKERS
FIELDS = ("owner", "target", "handoff_or_row", "created", "expires", "budget_gib", "reason")
ISO = "%Y-%m-%dT%H:%M:%SZ"


def lease_dir() -> str:
    return os.environ.get("SCRATCH_LEASE_DIR") or DEFAULT_LEASE_DIR


def lease_path(target: str, ldir: str | None = None) -> str:
    key = hashlib.sha256(os.path.realpath(target.rstrip("/") or "/").encode()).hexdigest()[:24]
    return os.path.join(ldir or lease_dir(), key + ".json")


def _iso(t: float) -> str:
    return dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime(ISO)


def _epoch(s) -> float | None:
    try:
        return dt.datetime.strptime(str(s), ISO).replace(tzinfo=dt.timezone.utc).timestamp()
    except ValueError:
        return None


def find_markers(target: str) -> list[str]:
    t = target.rstrip("/")
    found = [os.path.join(t, m) for m in KEEP_MARKERS if os.path.exists(os.path.join(t, m))] \
        if os.path.isdir(t) and not os.path.islink(t) else []
    if os.path.exists(t + ".epyc-keep"):
        found.append(t + ".epyc-keep")
    return found


class LeaseError(ValueError):
    pass


def read_lease(target: str, ldir: str | None = None) -> dict | None:
    """None when no lease exists; raises LeaseError when one exists but is unreadable/malformed."""
    p = lease_path(target, ldir)
    if not os.path.lexists(p):
        return None
    try:
        with open(p) as f:
            d = json.load(f)
    except (OSError, ValueError) as e:
        raise LeaseError(f"{p}: {e!r}") from e
    if not isinstance(d, dict) or any(k not in d for k in FIELDS) or _epoch(d.get("expires")) is None:
        raise LeaseError(f"{p}: malformed lease")
    if os.path.realpath(str(d["target"])) != os.path.realpath(target.rstrip("/")):
        raise LeaseError(f"{p}: lease target {d['target']!r} != {target!r}")
    return d


def is_retained(target: str, now: float | None = None, ldir: str | None = None) -> bool:
    """True only if a lease exists and is unexpired (a malformed lease counts as retained)."""
    now = time.time() if now is None else now
    try:
        d = read_lease(target, ldir)
    except LeaseError:
        return True
    return d is not None and _epoch(d["expires"]) > now


def marker_blocks(target: str, now: float | None = None, ldir: str | None = None) -> bool:
    """Does this target's KEEP marker still block reaping? Legacy (no lease) => True."""
    try:
        if read_lease(target, ldir) is None:
            return True
    except LeaseError:
        return True
    return is_retained(target, now, ldir)


def write_lease(lease: dict, ldir: str | None = None) -> str:
    ldir = ldir or lease_dir()
    os.makedirs(ldir, exist_ok=True)
    p = lease_path(lease["target"], ldir)
    tmp = p + ".part.%d" % os.getpid()
    with open(tmp, "w") as f:
        json.dump(lease, f, indent=1, sort_keys=True)
    os.replace(tmp, p)
    return p


_OWNER_RES = (
    re.compile(r"(?i)\bmarked by ([A-Za-z][\w.-]*[\w])"),
    re.compile(r"(?i)\bowner[:=]\s*([A-Za-z][\w.-]*[\w])"),
    re.compile(r"(?i)\bowned by ([A-Za-z][\w.-]*[\w])"),
    re.compile(r"\b(workspace-\d+|ws\d+|main[A-D]|codex\d*)\b"),
)


def parse_owner(marker_text: str, target: str = "") -> str:
    for rx in _OWNER_RES:
        m = rx.search(marker_text or "")
        if m:
            return m.group(1)
    m = re.match(r"(codex\d*)-", os.path.basename(target.rstrip("/")))
    return m.group(1) if m else "unknown"


def _du(p: str) -> int:
    t = 0
    for dp, dn, fn in os.walk(p):
        for f in fn:
            try:
                t += os.lstat(os.path.join(dp, f)).st_size
            except OSError:
                pass
    return t


def scan(root: str) -> list[tuple[str, list[str]]]:
    """(target, markers) for every top-level entry of root carrying a KEEP marker."""
    out = []
    for e in sorted(os.scandir(root), key=lambda e: e.name):
        if e.name.startswith(".") or e.name.endswith(".epyc-keep"):
            continue
        if not e.is_dir(follow_symlinks=False) and not os.path.exists(e.path + ".epyc-keep"):
            continue
        ms = find_markers(e.path)
        if ms:
            out.append((e.path, ms))
    return out


def backfill(root: str, *, apply: bool, ttl_days: float, now: float | None = None,
             ldir: str | None = None, sizes: bool = True) -> dict:
    now = time.time() if now is None else now
    res = {"created": [], "existing": [], "errors": []}
    for target, ms in scan(root):
        try:
            if read_lease(target, ldir) is not None:
                res["existing"].append(target)
                continue
        except LeaseError as e:
            res["errors"].append(str(e))
            continue
        text = ""
        for m in ms:
            try:
                with open(m, errors="replace") as f:
                    text += f.read(4096) + "\n"
            except OSError:
                pass
        lease = {
            "schema": SCHEMA, "owner": parse_owner(text, target), "target": os.path.realpath(target),
            "handoff_or_row": None, "created": _iso(now), "expires": _iso(now + ttl_days * 86400),
            "budget_gib": round(_du(target) / 2**30, 3) if sizes else None,
            "reason": "backfill from KEEP marker %s: %s" % (
                os.path.basename(ms[0]), " ".join(text.split())[:300]),
        }
        if apply:
            write_lease(lease, ldir)
        res["created"].append(lease)
    return res


def report(root: str, *, now: float | None = None, ldir: str | None = None) -> dict:
    """Per owner: count / GiB / earliest expiry, over marked targets (unleased => owner '(no lease)')."""
    now = time.time() if now is None else now
    owners: dict[str, dict] = {}
    for target, _ in scan(root):
        try:
            d = read_lease(target, ldir)
        except LeaseError:
            d = {"owner": "(malformed lease)", "expires": None, "budget_gib": None}
        owner = d["owner"] if d else "(no lease)"
        o = owners.setdefault(owner, {"count": 0, "gib": 0.0, "earliest_expiry": None, "expired": 0})
        o["count"] += 1
        g = d.get("budget_gib") if d else None
        o["gib"] += float(g) if g is not None else _du(target) / 2**30
        exp = d.get("expires") if d else None
        if exp and (o["earliest_expiry"] is None or exp < o["earliest_expiry"]):
            o["earliest_expiry"] = exp
        if exp and (_epoch(exp) or 0) <= now:
            o["expired"] += 1
    for o in owners.values():
        o["gib"] = round(o["gib"], 2)
    return owners


MAX_TTL_DAYS = 60.0
_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def allocate(name: str, *, owner: str, ttl_days: float, root: str = TMP_ROOT, row: str | None = None,
             budget_gib: float | None = None, reason: str = "", now: float | None = None,
             ldir: str | None = None) -> dict:
    """Create scratch dir <root>/<name> WITH owner+TTL at creation (SCRATCH-LEASE-P2).

    Writes the dir (exclusive mkdir: never adopts an existing path), a KEEP marker naming the owner, and the
    lease. Refuses: missing/placeholder owner, ttl not in (0, MAX_TTL_DAYS], name that is not one plain path
    component (reapers only scan top-level entries of the root), an existing target, a missing root. If the lease
    cannot be written the new dir is removed, so there is no marker-without-lease half state. Returns the lease.
    """
    if not owner or not owner.strip() or owner.strip().lower() in ("unknown", "none", "?"):
        raise LeaseError("owner is required (a real session id, e.g. workspace-58)")
    if not isinstance(ttl_days, (int, float)) or isinstance(ttl_days, bool) or not 0 < ttl_days <= MAX_TTL_DAYS:
        raise LeaseError(f"ttl_days must be in (0, {MAX_TTL_DAYS:g}]; renew by allocating a new lease, not an unbounded one")
    if not _NAME_RE.fullmatch(name or "") or name.endswith(".epyc-keep") or name in KEEP_MARKERS:
        raise LeaseError(f"bad scratch name {name!r}: one plain path component, no slashes or leading dot")
    if not os.path.isdir(root):
        raise LeaseError(f"scratch root {root!r} does not exist")
    now = time.time() if now is None else now
    target = os.path.join(os.path.realpath(root), name)
    try:
        os.mkdir(target)
    except FileExistsError:
        raise LeaseError(f"{target} already exists; allocate never adopts an existing path") from None
    lease = {
        "schema": SCHEMA, "owner": owner.strip(), "target": target, "handoff_or_row": row,
        "created": _iso(now), "expires": _iso(now + ttl_days * 86400),
        "budget_gib": budget_gib, "reason": reason or "allocate",
    }
    try:
        with open(os.path.join(target, ".epyc-keep"), "w") as f:
            f.write("KEEP: owner=%s allocated %s expires %s%s\n" % (
                lease["owner"], lease["created"], lease["expires"], f" row={row}" if row else ""))
        write_lease(lease, ldir)
    except BaseException:
        import shutil
        shutil.rmtree(target, ignore_errors=True)
        raise
    return lease


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("backfill")
    g = b.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--apply", action="store_true")
    b.add_argument("--ttl-days", type=float, default=14.0)
    b.add_argument("--root", default=TMP_ROOT)
    b.add_argument("--json", action="store_true")
    r = sub.add_parser("report")
    r.add_argument("--root", default=TMP_ROOT)
    r.add_argument("--json", action="store_true")
    s = sub.add_parser("show")
    s.add_argument("target")
    al = sub.add_parser("allocate")
    al.add_argument("name")
    al.add_argument("--owner", required=True)
    al.add_argument("--ttl-days", type=float, required=True)
    al.add_argument("--row")
    al.add_argument("--budget-gib", type=float)
    al.add_argument("--reason", default="")
    al.add_argument("--root", default=TMP_ROOT)
    a = ap.parse_args(argv)
    if a.cmd == "allocate":
        try:
            le = allocate(a.name, owner=a.owner, ttl_days=a.ttl_days, root=a.root, row=a.row,
                          budget_gib=a.budget_gib, reason=a.reason)
        except LeaseError as e:
            print(f"REFUSED {e}", file=sys.stderr)
            return 2
        print(le["target"])
        return 0
    if a.cmd == "show":
        try:
            d = read_lease(a.target)
        except LeaseError as e:
            print(f"MALFORMED {e}")
            return 1
        print(json.dumps(d, indent=1) if d else "no lease (legacy marker semantics: retained)")
        print("marker_blocks=%s" % marker_blocks(a.target))
        return 0
    if a.cmd == "backfill":
        res = backfill(a.root, apply=a.apply, ttl_days=a.ttl_days)
        if a.json:
            print(json.dumps(res, indent=1))
        else:
            verb = "CREATED" if a.apply else "WOULD-CREATE"
            for le in res["created"]:
                print(f"{verb}\t{le['owner']}\t{le['budget_gib']}GiB\t{le['expires']}\t{le['target']}")
            for t in res["existing"]:
                print(f"EXISTING\t{t}")
            for e in res["errors"]:
                print(f"ERROR\t{e}")
            tot = sum(le["budget_gib"] or 0 for le in res["created"])
            print(f"SUMMARY\t{verb.lower()}={len(res['created'])} ({tot:.1f} GiB) "
                  f"existing={len(res['existing'])} errors={len(res['errors'])} lease_dir={lease_dir()}")
        return 1 if res["errors"] else 0
    owners = report(a.root)
    if a.json:
        print(json.dumps(owners, indent=1))
    else:
        print("owner\tcount\tGiB\texpired\tearliest_expiry")
        for k, o in sorted(owners.items(), key=lambda kv: -kv[1]["gib"]):
            print(f"{k}\t{o['count']}\t{o['gib']}\t{o['expired']}\t{o['earliest_expiry']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
