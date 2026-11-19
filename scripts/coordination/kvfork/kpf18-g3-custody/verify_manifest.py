#!/usr/bin/env python3
"""Verify a pinned custody manifest has exact path coverage and matching bytes."""
import hashlib
import json
from pathlib import Path
import re
import sys

from rebind_manifest import LINE, read_regular


def verify(manifest: Path, expected_paths: list[str], expected_sha256: str) -> int:
    """Return entry count, refusing digest, coverage, syntax, or file mismatches."""
    if not re.fullmatch(r"[0-9a-f]{64}", expected_sha256):
        raise ValueError("expected manifest digest must be lowercase SHA-256")
    raw = read_regular(manifest)
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError("manifest digest mismatch")
    if not isinstance(expected_paths, list) or not all(isinstance(p, str) for p in expected_paths):
        raise ValueError("expected paths must be a string list")
    if not expected_paths:
        raise ValueError("empty expected inventory")
    if len(set(expected_paths)) != len(expected_paths):
        raise ValueError("duplicate expected path")
    entries = {}
    for line in raw.decode("utf-8").splitlines():
        match = LINE.fullmatch(line)
        if not match:
            raise ValueError("malformed manifest line")
        digest, path = match.groups()
        if path in entries:
            raise ValueError(f"duplicate manifest path: {path}")
        entries[path] = digest
    if set(entries) != set(expected_paths):
        missing = sorted(set(expected_paths) - set(entries))
        extra = sorted(set(entries) - set(expected_paths))
        raise ValueError(f"path coverage mismatch (missing={missing}, extra={extra})")
    for path, digest in entries.items():
        if hashlib.sha256(read_regular(path)).hexdigest() != digest:
            raise ValueError(f"file digest mismatch: {path}")
    return len(entries)


if __name__ == "__main__":
    if len(sys.argv) != 4:
        raise SystemExit("usage: verify_manifest.py manifest expected-paths.json expected-manifest-sha256")
    try:
        paths = json.loads(read_regular(sys.argv[2]))
        count = verify(Path(sys.argv[1]), paths, sys.argv[3])
    except (OSError, UnicodeError, ValueError, TypeError) as exc:
        raise SystemExit(f"REFUSED: {exc}")
    print(f"PASS: {count} pinned custody entries")
