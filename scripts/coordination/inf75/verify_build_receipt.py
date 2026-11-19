#!/usr/bin/env python3
"""Verify bytes in a P1c build receipt; this does not prove runtime linkage.

Only an independently reviewed, admitted build may produce a usable receipt.
This checker cannot establish that a build used the stated commit or flags; it
detects missing, substituted, or modified receipt members after their capture.
"""
from __future__ import annotations

import argparse
import hashlib
import re
from pathlib import Path, PurePosixPath

COMMITS = {
    "ef81196d5bdd4190b46dff4ae7eecc333a46c8ce",
    "2516c9807b8a92d472c8e75a0a1ce8558d2e34a7",
}
REQUIRED = {
    "source-commit.txt", "compiler-sha256.txt", "cc-version.txt",
    "cxx-version.txt", "cmake-version.txt", "build/CMakeCache.txt",
    "build/compile_commands.json", "configure.log", "build.log",
    "build/bin/llama-server",
}
LINE = re.compile(r"([0-9a-f]{64})  ([^\n]+)")


def verify(root: Path, receipt: Path, commit: str) -> None:
    if commit not in COMMITS:
        raise ValueError("unknown source commit")
    root = root.resolve(strict=True)
    members: set[str] = set()
    for line in receipt.read_text(encoding="utf-8").splitlines():
        match = LINE.fullmatch(line)
        if not match:
            raise ValueError("malformed receipt line")
        digest, name = match.groups()
        rel = PurePosixPath(name)
        if rel.is_absolute() or any(p in ("", ".", "..") for p in name.split("/")) or name in members:
            raise ValueError("unsafe or duplicate member")
        path = root.joinpath(*rel.parts)
        if not path.is_file() or path.resolve(strict=True) != path:
            raise ValueError("missing or symlinked member")
        h = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                h.update(block)
        if h.hexdigest() != digest:
            raise ValueError("member digest mismatch")
        members.add(name)
    if not REQUIRED <= members:
        raise ValueError("required receipt members absent")
    if not any(n.startswith("build/") and n.endswith(".gcno") for n in members):
        raise ValueError("coverage notes absent")
    if not any(n.startswith("build/bin/") and "ggml" in PurePosixPath(n).name
               and ".so" in PurePosixPath(n).name for n in members):
        raise ValueError("ggml shared library absent")
    if (root / "source-commit.txt").read_text(encoding="utf-8").strip() != commit:
        raise ValueError("source commit mismatch")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("receipt", type=Path)
    parser.add_argument("commit")
    args = parser.parse_args()
    try:
        verify(args.root, args.receipt, args.commit)
    except (OSError, ValueError, UnicodeError) as exc:
        parser.exit(1, f"REFUSED: {exc}\n")


if __name__ == "__main__":
    main()
