#!/usr/bin/env python3
"""Retention for /mnt/raid0/llm/claude-backups (LOOP-21 ai-sessions, LOOP-22 opencode snapshots).

The nightly host job (backup-claude-sessions.sh, daniele's crontab 04:00) calls this
tool in place of its inline ``ls | tail | rm`` rotation. The production rule is:
**no unlink without a verified copy on the mounted Micron mirror**.

    backup_retention.py ai-sessions --dir D --keep N [--expect PATH]
        Verify the exact NEWEST archive is a complete gzip+tar stream (read the gzip
        stream to EOF, CRC/length trailer included) and that it is the archive the
        caller just wrote. Only then verify every victim exists on --require-mirror
        with the same size and SHA-256. If anything fails, delete nothing.

    backup_retention.py opencode --dir D --prefix P --source DB [--keep N]
        Skip (exit 10, no new file) when sha256(DB) equals the hash recorded for the
        newest snapshot; retention still runs on any extras. Otherwise compress the
        source to a temp name, verify it, rename atomically, record the source hash,
        then prune with the same mirror gate. The source must be a stable,
        self-contained SQLite DB (the hourly read-only copies under
        /mnt/raid0/llm/opencode-db are the production source), never a live WAL DB.

Exit codes:
    0   success
    10  opencode source unchanged; snapshot skipped (retention may still have run)
    2   usage/config/precondition failure; nothing deleted
    3   new artifact failed verification; nothing deleted
    4   mirror verification failed; nothing deleted
    5   deletion failed partway

Deletion is os.unlink on explicit regular files matched by a strict timestamped
name. There is no recursion and no symlink following.
"""
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import hashlib
import os
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
import time
from pathlib import Path

EXIT_OK = 0
EXIT_USAGE = 2
EXIT_UNVERIFIED = 3
EXIT_MIRROR = 4
EXIT_DELETE = 5
EXIT_SKIPPED = 10
OPENCODE_KEEP_DEFAULT = 3

AI_RE = re.compile(r"^ai-sessions-(\d{8})-(\d{6})\.tar\.gz$")


class MirrorPreconditionError(Exception):
    """The mirror is missing, unmounted, or on the same device."""


class MirrorVerifyError(Exception):
    """The mirror copy exists but does not match the victim."""


def utc_ts() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for blk in iter(lambda: f.read(1 << 22), b""):
            h.update(blk)
    return h.hexdigest()


def _stamp_key(name: str) -> dt.datetime | None:
    m = re.search(r"(\d{8})-(\d{6})", name)
    if not m:
        return None
    try:
        return dt.datetime.strptime(m.group(1) + m.group(2), "%Y%m%d%H%M%S")
    except ValueError:
        return None


def path_sort_key(p: Path):
    """Sort by embedded timestamp, not raw name; fall back to mtime."""
    stamp = _stamp_key(p.name)
    try:
        mtime = p.stat().st_mtime
    except OSError:
        mtime = 0
    return (stamp or dt.datetime.fromtimestamp(mtime), p.name)


def log_line(message: str, log_file: str | None = None) -> None:
    print(message)
    if log_file:
        lp = Path(log_file)
        lp.parent.mkdir(parents=True, exist_ok=True)
        with lp.open("a") as f:
            f.write(message + "\n")


def verify_tarball(p: Path) -> bool:
    """Complete gzip stream (CRC + length trailer reached) and a readable tar chain."""
    try:
        if p.stat().st_size == 0:
            return False
        # gzip.open().read() to EOF is what checks the CRC/length trailer. Iterating
        # tarfile alone can stop at the end-of-archive marker before the trailer.
        with gzip.open(p, "rb") as gz:
            while gz.read(1 << 22):
                pass
        n = 0
        with tarfile.open(p, "r|gz") as tf:
            for _ in tf:
                n += 1
        return n > 0
    except (OSError, EOFError, tarfile.TarError, gzip.BadGzipFile, ValueError):
        return False


def _mirror_check(victim: Path, mirror_dir: Path | None, require_mount: str | None,
                  allow_same_device: bool = False) -> str:
    if require_mount:
        if not os.path.ismount(require_mount):
            raise MirrorPreconditionError(f"required mount {require_mount} is not a mountpoint")
    if mirror_dir is None:
        raise MirrorPreconditionError("no mirror directory supplied")
    mirror_dir = Path(mirror_dir)
    if not mirror_dir.is_dir():
        raise MirrorPreconditionError(f"mirror directory missing: {mirror_dir}")
    if not allow_same_device and os.stat(mirror_dir).st_dev == os.stat(victim.parent).st_dev:
        raise MirrorPreconditionError("mirror is on the same device as --dir")
    mirror = mirror_dir / victim.name
    if not mirror.is_file():
        raise MirrorVerifyError(f"missing mirror copy: {mirror}")
    if mirror.stat().st_size != victim.stat().st_size:
        raise MirrorVerifyError(
            f"size mismatch for {victim.name}: raid={victim.stat().st_size} mirror={mirror.stat().st_size}"
        )
    vh = sha256_file(victim)
    mh = sha256_file(mirror)
    if vh != mh:
        raise MirrorVerifyError(f"sha256 mismatch for {victim.name}: raid={vh} mirror={mh}")
    return vh


def _prune(victims: list[Path], mirror_dir: Path | None, require_mount: str | None,
           dry_run: bool, log_file: str | None, allow_unmirrored: bool = False,
           allow_same_device: bool = False) -> tuple[int, str]:
    if not victims:
        return EXIT_OK, "nothing to prune"
    if mirror_dir is None and not allow_unmirrored:
        return EXIT_USAGE, "refusing to delete without --require-mirror"

    verified: list[tuple[Path, str]] = []
    if mirror_dir is not None:
        try:
            for victim in victims:
                verified.append((victim, _mirror_check(victim, mirror_dir, require_mount, allow_same_device)))
        except MirrorPreconditionError as e:
            return EXIT_USAGE, f"mirror precondition failed; nothing deleted: {e}"
        except MirrorVerifyError as e:
            return EXIT_MIRROR, f"mirror verification failed; nothing deleted: {e}"

    if dry_run:
        for victim, digest in verified:
            log_line(f"{utc_ts()} WOULD_DELETE {victim.name} {victim.stat().st_size} {digest} "
                     f"mirror={mirror_dir} verified=1", log_file)
        return EXIT_OK, f"dry-run: would delete {len(victims)} file(s)"

    gone = 0
    for victim, digest in verified or [(v, "") for v in victims]:
        try:
            log_line(f"{utc_ts()} DELETE {victim.name} {victim.stat().st_size} {digest} "
                     f"mirror={mirror_dir} verified={1 if mirror_dir else 0}", log_file)
            os.unlink(victim)
            gone += 1
        except OSError as e:
            return EXIT_DELETE, f"deleted {gone}/{len(victims)}; failed on {victim.name}: {e}"
    return EXIT_OK, f"removed {gone} file(s)"


def prune_ai_sessions(d: Path, keep: int = 1, expect: Path | None = None,
                      require_mirror: Path | None = None, require_mount: str | None = None,
                      dry_run: bool = False, log_file: str | None = None,
                      allow_unmirrored: bool = False,
                      allow_same_device: bool = False) -> tuple[int, str]:
    d = Path(d)
    if not d.is_dir():
        return EXIT_USAGE, f"backup directory missing: {d}"
    if keep < 1:
        return EXIT_USAGE, "refused: --keep must be >= 1 (never leave zero)"

    tbs = sorted(
        (p for p in d.glob("ai-sessions-*.tar.gz") if AI_RE.match(p.name)),
        key=path_sort_key,
    )
    if not tbs:
        return EXIT_UNVERIFIED, "no ai-sessions tarball present; nothing deleted"

    newest = tbs[-1]
    if expect is not None:
        expect = Path(expect)
        if newest.resolve() != expect.resolve():
            return EXIT_UNVERIFIED, f"newest {newest.name} is not expected {expect.name}; nothing deleted"

    if not verify_tarball(newest):
        return EXIT_UNVERIFIED, f"newest {newest.name} failed verification; nothing deleted"

    victims = tbs[:-keep] if len(tbs) > keep else []
    if victims and not dry_run and expect is None and not allow_unmirrored:
        return EXIT_USAGE, "refusing to prune without --expect"
    rc, msg = _prune(victims, require_mirror, require_mount, dry_run, log_file,
                     allow_unmirrored, allow_same_device)
    if rc != EXIT_OK:
        return rc, msg
    return EXIT_OK, f"verified {newest.name}; kept {min(keep, len(tbs))}; {msg}"


def _opencode_re(prefix: str) -> re.Pattern[str]:
    return re.compile(r"^" + re.escape(prefix) + r"-(\d{8})-(\d{6})\.db\.zst$")


def _sqlite_quick_check(source: Path) -> tuple[bool, str]:
    sqlite3 = shutil.which("sqlite3")
    if not sqlite3:
        return False, "sqlite3 not found"
    r = subprocess.run(
        [sqlite3, "-readonly", str(source), "pragma quick_check"],
        capture_output=True, text=True,
    )
    out = (r.stdout or "").strip()
    if r.returncode != 0 or out != "ok":
        return False, out or (r.stderr or "").strip() or f"sqlite3 exit {r.returncode}"
    return True, "ok"


def opencode_snapshot(d: Path, prefix: str, source: Path, keep: int = OPENCODE_KEEP_DEFAULT,
                      compress_cmd: str = "zstd -q -T0 -3 -f -o {out} {src}",
                      verify_cmd: str = "zstd -q -t {out}",
                      stamp: str | None = None,
                      require_mirror: Path | None = None,
                      require_mount: str | None = None,
                      max_source_age: int | None = None,
                      integrity_check: str = "quick_check",
                      dry_run: bool = False, log_file: str | None = None,
                      allow_unmirrored: bool = False,
                      allow_same_device: bool = False,
                      allow_stale: bool = False) -> tuple[int, str]:
    d = Path(d)
    source = Path(source)
    if not d.is_dir():
        return EXIT_USAGE, f"backup directory missing: {d}"
    if keep < 1:
        return EXIT_USAGE, "refused: --keep must be >= 1"
    if not re.fullmatch(r"[A-Za-z0-9._-]+", prefix):
        return EXIT_USAGE, f"bad --prefix: {prefix!r}"
    if not source.is_file():
        return EXIT_USAGE, f"source missing: {source}"

    if max_source_age is not None and not allow_stale:
        age = time.time() - source.stat().st_mtime
        if age > max_source_age:
            return EXIT_USAGE, f"source is stale ({age:.0f}s > {max_source_age}s): {source}"

    for suffix in ("-wal", "-shm"):
        side = Path(str(source) + suffix)
        if side.exists() and side.stat().st_size > 0:
            return EXIT_USAGE, f"source has a non-empty {suffix} sibling; refusing: {side}"

    if integrity_check != "off":
        ok, detail = _sqlite_quick_check(source)
        if not ok:
            return EXIT_UNVERIFIED, f"source quick_check failed ({detail}); existing snapshots untouched"

    snap_re = _opencode_re(prefix)
    snaps = sorted(
        (p for p in d.glob(f"{prefix}-*.db.zst") if snap_re.match(p.name)),
        key=path_sort_key,
    )
    sidecar = d / f"{prefix}.last.sha256"
    digest = sha256_file(source)
    unchanged = bool(snaps and sidecar.exists() and sidecar.read_text().strip() == digest)

    if dry_run:
        if unchanged:
            rc = EXIT_SKIPPED
            msg = f"source unchanged (sha256 {digest[:12]}); would skip, newest is {snaps[-1].name}"
            projected = snaps
        else:
            rc = EXIT_OK
            new_stamp = stamp or time.strftime("%Y%m%d-%H%M%S", time.localtime())
            msg = f"would write {prefix}-{new_stamp}.db.zst"
            # Project the new snapshot so the dry-run shows the same victim the real run would prune.
            projected = snaps + [d / f"{prefix}-{new_stamp}.db.zst"]
        victims = projected[:-keep] if len(projected) > keep else []
        prc, pmsg = _prune(victims, require_mirror, require_mount, True, log_file,
                           allow_unmirrored, allow_same_device)
        if prc != EXIT_OK:
            return prc, pmsg
        return rc, f"{msg}; {pmsg}"

    if unchanged:
        victims = snaps[:-keep] if len(snaps) > keep else []
        prc, pmsg = _prune(victims, require_mirror, require_mount, False, log_file,
                           allow_unmirrored, allow_same_device)
        if prc != EXIT_OK:
            return prc, pmsg
        return EXIT_SKIPPED, f"source unchanged (sha256 {digest[:12]}); skipped, newest is {snaps[-1].name}; {pmsg}"

    new_stamp = stamp or time.strftime("%Y%m%d-%H%M%S", time.localtime())
    final = d / f"{prefix}-{new_stamp}.db.zst"
    tmp = d / f".{prefix}-{new_stamp}.db.zst.tmp"
    ok = _run(compress_cmd, source, tmp) and tmp.exists() and tmp.stat().st_size > 0 and _run(verify_cmd, source, tmp)
    if not ok:
        if tmp.exists():
            os.unlink(tmp)
        return EXIT_UNVERIFIED, "snapshot failed to write/verify; existing snapshots untouched"
    os.replace(tmp, final)
    sidecar.write_text(digest + "\n")

    snaps = sorted(
        (p for p in d.glob(f"{prefix}-*.db.zst") if snap_re.match(p.name)),
        key=path_sort_key,
    )
    victims = snaps[:-keep] if len(snaps) > keep else []
    prc, pmsg = _prune(victims, require_mirror, require_mount, False, log_file,
                       allow_unmirrored, allow_same_device)
    if prc != EXIT_OK:
        return prc, f"wrote {final.name}; {pmsg}"
    return EXIT_OK, f"wrote {final.name}; kept {min(keep, len(snaps))}; {pmsg}"


def _run(cmd: str, src: Path, out: Path) -> bool:
    r = subprocess.run(cmd.format(src=str(src), out=str(out)), shell=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return r.returncode == 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("ai-sessions")
    a.add_argument("--dir", required=True)
    a.add_argument("--keep", type=int, default=1)
    a.add_argument("--expect")
    a.add_argument("--require-mirror")
    a.add_argument("--require-mount")
    a.add_argument("--dry-run", action="store_true")
    a.add_argument("--log")

    o = sub.add_parser("opencode")
    o.add_argument("--dir", required=True)
    o.add_argument("--prefix", required=True)
    o.add_argument("--source", required=True)
    o.add_argument("--keep", type=int, default=OPENCODE_KEEP_DEFAULT)
    o.add_argument("--require-mirror")
    o.add_argument("--require-mount")
    o.add_argument("--max-source-age", type=int)
    o.add_argument("--integrity-check", choices=("quick_check", "off"), default="quick_check")
    o.add_argument("--zstd")
    o.add_argument("--dry-run", action="store_true")
    o.add_argument("--log")

    n = ap.parse_args(argv)
    mirror = Path(n.require_mirror) if n.require_mirror else None
    if n.cmd == "ai-sessions":
        rc, msg = prune_ai_sessions(
            Path(n.dir), n.keep, Path(n.expect) if n.expect else None,
            mirror, n.require_mount, n.dry_run, n.log,
        )
    else:
        compress = "zstd -q -T0 -3 -f -o {out} {src}"
        verify = "zstd -q -t {out}"
        if n.zstd:
            z = shlex.quote(n.zstd)
            compress = f"{z} -q -T0 -3 -f -o {{out}} {{src}}"
            verify = f"{z} -q -t {{out}}"
        rc, msg = opencode_snapshot(
            Path(n.dir), n.prefix, Path(n.source), n.keep,
            compress_cmd=compress, verify_cmd=verify,
            require_mirror=mirror, require_mount=n.require_mount,
            max_source_age=n.max_source_age, integrity_check=n.integrity_check,
            dry_run=n.dry_run, log_file=n.log,
        )
    log_line(msg, n.log)
    return rc


if __name__ == "__main__":
    sys.exit(main())
