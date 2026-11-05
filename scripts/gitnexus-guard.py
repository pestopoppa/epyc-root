#!/usr/bin/python3
"""Fail-closed proof that GitNexus is inside a live region-lock owner tree."""
import json
import math
import os
import stat
import sys
import time

LOCK_ROOT = "/mnt/raid0/llm/tmp"
QUADRANTS = ("q0", "q1", "q2", "q3")
DENIED = 64
EXPECTED_ROOT = None

class Refusal(Exception):
    pass

def deny(message):
    raise Refusal(message)

def proc_stat(pid):
    with open(f"/proc/{pid}/stat", "r", encoding="ascii") as f:
        raw = f.read()
    end = raw.rfind(")")
    if end < 0:
        deny("malformed proc stat")
    fields = raw[end + 2:].split()  # starts at field 3
    if len(fields) < 20:
        deny("short proc stat")
    ppid = int(fields[1])
    starttime = int(fields[19])  # field 22
    with open(f"/proc/{pid}/status", "r", encoding="ascii") as f:
        status = f.read()
    uid_line = next((line for line in status.splitlines() if line.startswith("Uid:")), None)
    if uid_line is None:
        deny("missing process uid")
    uid = int(uid_line.split()[1])
    return ppid, starttime, uid

def ancestors():
    result = {}
    pid = os.getpid()
    seen = set()
    while pid > 1 and pid not in seen:
        seen.add(pid)
        ppid, start, uid = proc_stat(pid)
        result[pid] = (start, uid)
        if ppid == pid:
            break
        pid = ppid
    return result

def proc_lock_owners():
    owners = {}
    with open("/proc/locks", "r", encoding="ascii") as f:
        for line in f:
            fields = line.split()
            if not fields or "->" in fields:
                continue  # a waiter is not an owner
            if len(fields) < 8 or fields[1:4] != ["FLOCK", "ADVISORY", "WRITE"]:
                continue
            if not fields[4].isdigit():
                continue
            major, minor, inode = fields[5].split(":")
            key = (int(major, 16), int(minor, 16), int(inode, 10))
            owners.setdefault(key, set()).add(int(fields[4]))
    return owners

def safe_root():
    for name in ("ORCHESTRATOR_TMP_DIR", "ORCHESTRATOR_PATHS_TMP_DIR", "TMP_DIR"):
        value = os.environ.get(name)
        if value and value != LOCK_ROOT:
            deny(f"noncanonical {name}")
    root_fd, root_stat = open_fixed_root()
    os.close(root_fd)
    return (root_stat.st_dev, root_stat.st_ino)

def open_fixed_root():
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open("/", flags)
    try:
        for part in LOCK_ROOT.strip("/").split("/"):
            child = os.open(part, flags, dir_fd=fd)
            os.close(fd)
            fd = child
        return fd, os.fstat(fd)
    except BaseException:
        os.close(fd)
        raise

def open_identity(path):
    if os.path.dirname(path) != LOCK_ROOT:
        deny("lock path escaped fixed root")
    root_fd, root_stat = open_fixed_root()
    try:
        if EXPECTED_ROOT is None or (root_stat.st_dev, root_stat.st_ino) != EXPECTED_ROOT:
            deny("fixed lock-root identity changed")
        name = os.path.basename(path)
        before = os.stat(name, dir_fd=root_fd, follow_symlinks=False)
        if stat.S_ISLNK(before.st_mode) or not stat.S_ISREG(before.st_mode):
            deny("lock path is not a regular nonsymlink")
        fd = os.open(name, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=root_fd)
        try:
            opened = os.fstat(fd)
            if not stat.S_ISREG(opened.st_mode):
                deny("opened lock is not regular")
            if opened.st_nlink != 1:
                deny("opened lock is not single-link")
            if (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino):
                deny("lock path changed during open")
            if opened.st_uid != os.getuid():
                deny("lock file uid differs")
            data = os.read(fd, 65537)
            if len(data) > 65536:
                deny("oversized lock payload")
            after = os.stat(name, dir_fd=root_fd, follow_symlinks=False)
            final = os.fstat(fd)
            if not stat.S_ISREG(final.st_mode) or final.st_uid != os.getuid() or final.st_nlink != 1:
                deny("lock type or owner changed during read")
            if (after.st_dev, after.st_ino) != (final.st_dev, final.st_ino):
                deny("lock path changed during read")
            check_fd, check_stat = open_fixed_root()
            os.close(check_fd)
            if (check_stat.st_dev, check_stat.st_ino) != EXPECTED_ROOT:
                deny("fixed lock-root path changed during admission")
            return (final.st_dev, final.st_ino), data
        finally:
            os.close(fd)
    finally:
        os.close(root_fd)

def dev_inode(identity):
    dev, ino = identity
    return (os.major(dev), os.minor(dev), ino)

def valid_payload(data, owner, expected_region, regions=QUADRANTS):
    try:
        p = json.loads(data.decode("utf-8"))
    except Exception:
        deny("invalid build lock payload")
    if not isinstance(p, dict):
        deny("invalid build lock payload object")
    if (type(p.get("schema_version")) is not int or
        type(p.get("pid")) is not int):
        deny("build lock attribution field types mismatch")
    started = p.get("started_at")
    if (p.get("schema_version") != 1 or p.get("pid") != owner or
        p.get("role") != "build" or p.get("region") != expected_region or
        p.get("regions") != list(regions) or
        not isinstance(p.get("request_tag"), str) or not p["request_tag"].strip() or
        isinstance(started, bool) or not isinstance(started, (int, float)) or
        not math.isfinite(started) or started <= 0 or started > time.time() + 60):
        deny("build lock attribution mismatch")

def analyze_workers(args):
    """Return 1 only for one unambiguous `--workers 1`; otherwise None.

    Operator decision 2026-11-05 ("Change the rule: 1 quarter"): a pinned
    single-worker analyze may run on ONE CPU quarter. Anything absent,
    repeated, malformed or not exactly 1 keeps the four-quarter rule.
    """
    values = []
    i = 0
    while i < len(args):
        item = args[i]
        if item == "--":
            return None  # positional tail is ambiguous: fail closed
        if item == "--workers":
            if i + 1 >= len(args):
                return None
            values.append(args[i + 1])
            i += 2
            continue
        if item.startswith("--workers="):
            values.append(item.split("=", 1)[1])
        elif item.startswith("--worker"):
            return None  # unknown spelling (e.g. --workers-max) is ambiguous
        i += 1
    if len(values) != 1 or values[0] != "1":
        return None
    if os.environ.get("GITNEXUS_WORKER_POOL_SIZE", "1") != "1":
        return None  # environment channel disagrees with the pinned CLI
    return 1

def admit(analyze_args=None):
    if analyze_args is not None and analyze_workers(analyze_args) == 1:
        try:
            return admit_one_quarter()
        except Refusal as quarter_refusal:
            # A full four-quarter claim also covers a single worker.
            try:
                return admit_whole_host()
            except Refusal:
                raise quarter_refusal
    return admit_whole_host()

def admit_one_quarter():
    """Single-worker analyze: GLOBAL+build write flocks on one same quarter."""
    global EXPECTED_ROOT
    EXPECTED_ROOT = safe_root()
    if os.environ.get("ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT", "").strip().lower() not in {"1", "true", "yes", "on"}:
        deny("cross-role global region locks are not enabled")
    anc = ancestors()
    current_uid = os.getuid()
    kernel = proc_lock_owners()
    held = {}
    for q in QUADRANTS:
        pair = []
        for role in ("GLOBAL", "build"):
            path = os.path.join(LOCK_ROOT, f"cpu_region.{role}.{q}.lock")
            ident, payload = open_identity(path)
            candidates = kernel.get(dev_inode(ident), set()).intersection(anc)
            if len(candidates) > 1:
                deny(f"{role}/{q} has ambiguous ancestor write flocks")
            pair.append((role, path, ident, next(iter(candidates)) if candidates else None, payload))
        owners = [entry[3] for entry in pair]
        if owners[0] is None and owners[1] is None:
            continue
        if owners[0] is None or owners[1] is None:
            deny(f"{q} needs both GLOBAL and build write flocks on the same quarter")
        held[q] = pair
    if len(held) != 1:
        deny("single-worker admission needs exactly one GLOBAL/build quarter pair")
    q, pair = next(iter(held.items()))
    owner_set = {entry[3] for entry in pair}
    if len(owner_set) != 1:
        deny("quarter locks do not share one ancestor owner")
    owner = next(iter(owner_set))
    if owner == os.getpid():
        deny("guard itself cannot be the claim owner")
    if anc[owner][1] != current_uid:
        deny("claim owner uid differs")
    if pair[0][2] == pair[1][2]:
        deny("CPU claims do not have two distinct inode identities")
    valid_payload(pair[1][4], owner, q, (q,))
    ppid_start_uid = proc_stat(owner)
    anc2 = ancestors()
    if owner not in anc2 or ppid_start_uid[1] != anc[owner][0] or anc2[owner] != anc[owner] or ppid_start_uid[2] != current_uid:
        deny("claim owner changed")
    kernel2 = proc_lock_owners()
    for role, path, prior, _owner, _payload in pair:
        now, payload = open_identity(path)
        if now != prior:
            deny("lock identity changed during admission")
        if owner not in kernel2.get(dev_inode(now), set()):
            deny("write flock disappeared during admission")
        if role == "build":
            valid_payload(payload, owner, q, (q,))
    return owner

def admit_whole_host():
    global EXPECTED_ROOT
    EXPECTED_ROOT = safe_root()
    if os.environ.get("ORCHESTRATOR_CROSS_ROLE_DISJOINT_PLACEMENT", "").strip().lower() not in {"1", "true", "yes", "on"}:
        deny("cross-role global region locks are not enabled")
    anc = ancestors()
    current_uid = os.getuid()
    kernel = proc_lock_owners()
    identities = []
    for role in ("GLOBAL", "build"):
        for q in QUADRANTS:
            path = os.path.join(LOCK_ROOT, f"cpu_region.{role}.{q}.lock")
            ident, payload = open_identity(path)
            maj, min_, ino = dev_inode(ident)
            owners = kernel.get((maj, min_, ino), set())
            candidates = owners.intersection(anc)
            if len(candidates) != 1:
                deny(f"{role}/{q} lacks one granted ancestor write flock")
            owner = next(iter(candidates))
            start, uid = anc[owner]
            if uid != current_uid:
                deny("claim owner uid differs")
            if role == "build":
                valid_payload(payload, owner, q)
            identities.append((path, ident, owner, start))
    if len({entry[1] for entry in identities}) != 8:
        deny("CPU claims do not have eight distinct inode identities")
    owner_set = {entry[2] for entry in identities}
    if len(owner_set) != 1:
        deny("locks do not share one ancestor owner")
    owner = next(iter(owner_set))
    if owner == os.getpid():
        deny("guard itself cannot be the claim owner")
    # Re-open/re-read every pathname and revalidate process identity and kernel grants.
    ppid_start_uid = proc_stat(owner)
    anc2 = ancestors()
    if owner not in anc2 or ppid_start_uid[1] != anc[owner][0] or anc2[owner] != anc[owner] or ppid_start_uid[2] != current_uid:
        deny("claim owner changed")
    kernel2 = proc_lock_owners()
    for path, prior, expected_owner, start in identities:
        now, payload = open_identity(path)
        if now != prior:
            deny("lock identity changed during admission")
        maj, min_, ino = dev_inode(now)
        if expected_owner not in kernel2.get((maj, min_, ino), set()):
            deny("write flock disappeared during admission")
        if "cpu_region.build." in path:
            q = path.rsplit(".", 2)[-2]
            valid_payload(payload, owner, q)
    return owner

def main():
    try:
        argv = sys.argv[1:]
        if len(argv) < 2 or argv[0] != "--repo" or argv[1] not in {"root", "app"}:
            deny("usage: gitnexus-guard.py --repo root|app [-- analyze arguments]")
        if len(argv) == 2:
            admit()
        elif argv[2] == "--":
            admit(argv[3:])
        else:
            deny("usage: gitnexus-guard.py --repo root|app [-- analyze arguments]")
        return 0
    except Exception as exc:
        print(f"gitnexus guard: denied: {exc}", file=sys.stderr)
        return DENIED

if __name__ == "__main__":
    raise SystemExit(main())
