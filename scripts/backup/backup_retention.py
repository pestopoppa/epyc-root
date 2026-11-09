#!/usr/bin/env python3
"""Retention for /mnt/raid0/llm/claude-backups (LOOP-21 ai-sessions, LOOP-22 opencode snapshots).

The nightly host job (backup-claude-sessions.sh, host crontab 04:00, root) lives outside this repo; it calls
this tool in place of its inline ``ls | tail | rm`` rotation (install step: scripts/backup/README-retention.txt).

    backup_retention.py ai-sessions --dir D [--keep 1]
        Verify the NEWEST ai-sessions-*.tar.gz is a complete gzip+tar stream (read to EOF, CRC checked,
        non-empty). Only if it verifies are older tarballs deleted. If it does not verify, nothing is
        deleted (the previous tarball is the one that survives) and the exit code is 3. Never deletes the
        last remaining file; --keep < 1 is refused.

    backup_retention.py opencode --dir D --prefix opencode-epyc --source DB [--keep 3]
        Skip (exit 10, nothing written) when sha256(DB) equals the hash recorded for the newest snapshot.
        Otherwise compress DB to a temp name, verify it, rename atomically to <prefix>-<stamp>.db.zst,
        record the source hash in <prefix>.last.sha256, then keep the newest --keep snapshots. A failed
        compress or verify removes only the temp file and leaves every existing snapshot alone (exit 3).

Deletion is os.unlink on explicit single files matched by an exact glob; no recursion.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import os
import subprocess
import sys
import tarfile
import time
from pathlib import Path

EXIT_UNVERIFIED = 3
EXIT_SKIPPED = 10
OPENCODE_KEEP_DEFAULT = 3


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for blk in iter(lambda: f.read(1 << 22), b""):
            h.update(blk)
    return h.hexdigest()


def verify_tarball(p: Path) -> bool:
    """Complete gzip stream (CRC + length trailer reached) and a readable tar header chain."""
    try:
        if p.stat().st_size == 0:
            return False
        n = 0
        with tarfile.open(p, "r|gz") as tf:
            for _ in tf:
                n += 1
        # a truncated gzip raises EOFError inside the iteration; tar members are required
        return n > 0
    except (OSError, EOFError, tarfile.TarError, gzip.BadGzipFile, ValueError):
        return False


def _unlink_all(paths: list[Path]) -> list[str]:
    gone = []
    for p in paths:
        os.unlink(p)
        gone.append(p.name)
    return gone


def prune_ai_sessions(d: Path, keep: int = 1) -> tuple[int, str]:
    if keep < 1:
        return 2, "refused: --keep must be >= 1 (never leave zero)"
    tbs = sorted(d.glob("ai-sessions-*.tar.gz"))
    if not tbs:
        return EXIT_UNVERIFIED, "no ai-sessions tarball present; nothing deleted"
    newest = tbs[-1]
    if not verify_tarball(newest):
        return EXIT_UNVERIFIED, f"newest {newest.name} failed verification; nothing deleted"
    victims = tbs[:-keep] if len(tbs) > keep else []
    gone = _unlink_all(victims)
    return 0, f"verified {newest.name}; kept {min(keep, len(tbs))}, removed {len(gone)}: {' '.join(gone)}"


def _run(cmd: str, src: Path, out: Path) -> bool:
    r = subprocess.run(cmd.format(src=str(src), out=str(out)), shell=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return r.returncode == 0


def opencode_snapshot(d: Path, prefix: str, source: Path, keep: int = OPENCODE_KEEP_DEFAULT,
                      compress_cmd: str = "zstd -q -T0 -3 -f -o {out} {src}",
                      verify_cmd: str = "zstd -q -t {out}", stamp: str | None = None) -> tuple[int, str]:
    if keep < 1:
        return 2, "refused: --keep must be >= 1"
    sidecar = d / f"{prefix}.last.sha256"
    snaps = sorted(d.glob(f"{prefix}-2*.db.zst"))
    digest = sha256_file(source)
    if snaps and sidecar.exists() and sidecar.read_text().strip() == digest:
        return EXIT_SKIPPED, f"source unchanged (sha256 {digest[:12]}); skipped, newest is {snaps[-1].name}"
    stamp = stamp or time.strftime("%Y%m%d-%H%M%S", time.gmtime())
    final = d / f"{prefix}-{stamp}.db.zst"
    tmp = d / f".{prefix}-{stamp}.db.zst.tmp"
    ok = _run(compress_cmd, source, tmp) and tmp.exists() and tmp.stat().st_size > 0 and _run(verify_cmd, source, tmp)
    if not ok:
        if tmp.exists():
            os.unlink(tmp)
        return EXIT_UNVERIFIED, "snapshot failed to write/verify; existing snapshots untouched"
    os.replace(tmp, final)
    sidecar.write_text(digest + "\n")
    snaps = sorted(d.glob(f"{prefix}-2*.db.zst"))
    gone = _unlink_all(snaps[:-keep]) if len(snaps) > keep else []
    return 0, f"wrote {final.name}; kept {min(keep, len(snaps))}, removed {len(gone)}: {' '.join(gone)}"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("ai-sessions"); a.add_argument("--dir", required=True); a.add_argument("--keep", type=int, default=1)
    o = sub.add_parser("opencode"); o.add_argument("--dir", required=True); o.add_argument("--prefix", required=True)
    o.add_argument("--source", required=True); o.add_argument("--keep", type=int, default=OPENCODE_KEEP_DEFAULT)
    o.add_argument("--compress-cmd", default="zstd -q -T0 -3 -f -o {out} {src}")
    o.add_argument("--verify-cmd", default="zstd -q -t {out}")
    n = ap.parse_args(argv)
    if n.cmd == "ai-sessions":
        rc, msg = prune_ai_sessions(Path(n.dir), n.keep)
    else:
        rc, msg = opencode_snapshot(Path(n.dir), n.prefix, Path(n.source), n.keep, n.compress_cmd, n.verify_cmd)
    print(msg)
    return rc


if __name__ == "__main__":
    sys.exit(main())
