#!/usr/bin/env python3
"""akagg_research_snapshot.py - materialise a packet's `owned-research/` pinned snapshot WITHOUT a 2 GB copy.

WHY. akxall8-floor-vN (autokernel aggregate lane) packets each carried a full copy of the research repo
(owned-research/, ~2 GB) although only the files listed in RESEARCH-SNAPSHOT-PATHS.json (pinned by
RESEARCH-SHA256SUMS) are read. On 2026-11-04 republishing v9..v36 after each disk-floor kill wrote 29 x 2 GB.
This helper hardlinks the pinned files from the content-addressed store used by scratch_release.py
(`link_snapshot`, same code as `scratch_release.py snapshot-link`), then VERIFIES every file against the sums.
If linking or verification fails it falls back to a plain copy from --src (logged loudly), then verifies again.

Usage (run after the patch is applied to --src, before seal_packet.py, or after it with --sums for verification):
  akagg_research_snapshot.py --packet DIR --src SRC_DIR [--sums RESEARCH-SHA256SUMS] [--store CAS] [--log FILE]
  akagg_research_snapshot.py --packet DIR --sums PREDECESSOR/RESEARCH-SHA256SUMS      # store-only, no --src needed
`--src` holds the pinned files at the paths listed in RESEARCH-SNAPSHOT-PATHS.json with the leading
`owned-research/` removed. Dest is DIR/owned-research. Exit 0 = verified; 1 = could not materialise/verify.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scratch_release as sr  # noqa: E402

PREFIX = "owned-research/"


def _log(msg: str, logfile: str | None) -> None:
    line = "%s akagg_research_snapshot: %s" % (time.strftime("%FT%TZ", time.gmtime()), msg)
    print(line, file=sys.stderr)
    if logfile:
        with open(logfile, "a") as f:
            f.write(line + "\n")


def parse_sums(path: str) -> dict[str, str]:
    """{path as written: sha256} from a RESEARCH-SHA256SUMS file."""
    out = {}
    with open(path) as f:
        for line in f:
            if line.strip():
                h, _, p = line.rstrip("\n").partition("  ")
                out[p] = h
    return out


def verify(packet: str, paths: list[str], sums: dict[str, str]) -> list[str]:
    """Return a list of problems (empty = every path present, regular, unmodified and no extras pinned)."""
    bad = []
    if set(paths) != set(sums):
        bad.append("path set differs from sums (%d vs %d)" % (len(paths), len(sums)))
    for p in paths:
        fp = os.path.join(packet, p)
        if os.path.islink(fp) or not os.path.isfile(fp):
            bad.append("missing/not regular: " + p)
        elif p in sums and sr.sha256(fp) != sums[p]:
            bad.append("sha mismatch: " + p)
    return bad


def link_from_store(packet: str, paths: list[str], sums: dict[str, str], store: str) -> dict:
    res = {"linked": 0, "copied": 0}
    for p in paths:
        rel = p[len(PREFIX):] if p.startswith(PREFIX) else p
        if not sr.valid_rel(rel) or p not in sums:
            raise ValueError("bad or unpinned path %r" % p)
        cas = os.path.join(store, sums[p][:2], sums[p])
        if not os.path.isfile(cas):
            raise FileNotFoundError("store has no %s for %s" % (sums[p][:12], p))
        dp = os.path.join(packet, p)
        os.makedirs(os.path.dirname(dp), exist_ok=True)
        try:
            os.link(cas, dp)
            res["linked"] += 1
        except FileExistsError:
            pass
        except OSError:
            shutil.copyfile(cas, dp)
            res["copied"] += 1
    return res


def copy_fallback(packet: str, src: str, paths: list[str]) -> int:
    n = 0
    for p in paths:
        rel = p[len(PREFIX):] if p.startswith(PREFIX) else p
        if not sr.valid_rel(rel):
            raise ValueError("bad path %r" % p)
        dp = os.path.join(packet, p)
        os.makedirs(os.path.dirname(dp), exist_ok=True)
        if os.path.lexists(dp):
            os.unlink(dp)           # never write through a hardlink into the shared store
        shutil.copyfile(os.path.join(src, rel), dp)
        n += 1
    return n


def materialise(packet: str, src: str | None, sums_file: str | None, store: str, logfile: str | None = None) -> int:
    with open(os.path.join(packet, "RESEARCH-SNAPSHOT-PATHS.json")) as f:
        paths = json.load(f)
    if not paths:
        _log("empty RESEARCH-SNAPSHOT-PATHS.json", logfile)
        return 1
    sums_file = sums_file or os.path.join(packet, "RESEARCH-SHA256SUMS")
    sums = parse_sums(sums_file) if os.path.isfile(sums_file) else None
    if sums is None and not src:
        _log("no sums file and no --src: nothing to link from", logfile)
        return 1
    try:
        if src:
            r = sr.link_snapshot(src, os.path.join(packet, PREFIX.rstrip("/")), paths, store, prefix=PREFIX)
            if sums is None:
                sums = {s.split("  ", 1)[1]: s.split("  ", 1)[0] for s in r["sums"]}
        else:
            r = link_from_store(packet, paths, sums, store)
        _log("snapshot-link ok: %s" % {k: v for k, v in r.items() if k != "sums"}, logfile)
        bad = verify(packet, paths, sums)
        if not bad:
            return 0
        raise RuntimeError("verification failed: %s" % "; ".join(bad[:5]))
    except Exception as e:  # noqa: BLE001 - any failure falls back to a verified plain copy
        _log("FALLBACK to copy (snapshot-link failed: %s)" % e, logfile)
    if not src:
        _log("cannot fall back to copy: no --src", logfile)
        return 1
    n = copy_fallback(packet, src, paths)
    if sums is None:
        _log("copied %d files but no sums to verify against" % n, logfile)
        return 1
    bad = verify(packet, paths, sums)
    _log("copy fallback wrote %d files; verification %s" % (n, "OK" if not bad else "FAILED: " + "; ".join(bad[:5])), logfile)
    return 1 if bad else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--packet", required=True)
    ap.add_argument("--src")
    ap.add_argument("--sums", help="RESEARCH-SHA256SUMS to verify against (default PACKET/RESEARCH-SHA256SUMS if present)")
    ap.add_argument("--store", default=sr.DEFAULT_STORE)
    ap.add_argument("--log")
    a = ap.parse_args(argv)
    return materialise(a.packet, a.src, a.sums, a.store, a.log)


if __name__ == "__main__":
    sys.exit(main())
