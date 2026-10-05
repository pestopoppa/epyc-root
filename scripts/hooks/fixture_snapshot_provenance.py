#!/usr/bin/env python3
"""Recognize reviewed public fixture/policy blobs in complete staged native custody.

This is a PII false-positive check, not measurement authority. Unknown/changed or
unbound contents always fall back to the ordinary scanner. All input bytes come
from the Git index, never from the worktree or a captured executable.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tempfile


# Exact public test-fixture identities, reviewed at both immutable app revisions.
# https://github.com/pestopoppa/epyc-orchestrator/blob/def18591f813070a20906f9d228ddd9dd0da9fd3/tests/unit/test_credential_redaction.py
# https://github.com/pestopoppa/epyc-orchestrator/blob/def18591f813070a20906f9d228ddd9dd0da9fd3/tests/unit/test_knowledge_tools.py
# These synthetic test inputs are NOT vendor-published credential placeholders.
FIXTURES = {
    "tests/unit/test_credential_redaction.py":
        "531a7bcd5239c80f1bd57df66c5214abfc12b0807d2e6260652597d1a743a382",
    "tests/unit/test_knowledge_tools.py":
        "44a331b41ea80f92a2915cc6040fd6ee4f51da0bd5acb0a7daa388e24418bfcc",
    # Original public policy source at the exact tested ROOT revision. Its
    # illustrative account-shaped comments are not vendor placeholders.
    # https://github.com/pestopoppa/epyc-root/blob/4cc17080c6209e5d7f2a744807c9cf87ae0bf70f/scripts/hooks/pii_precommit.sh
    "scripts/hooks/pii_precommit.sh":
        "5cafb5e16ed0e14d51b4e151bc2748709018f45d68db650c9d8ce34764d26c88",
}
SOURCE_REVISIONS = {
    "def18591f813070a20906f9d228ddd9dd0da9fd3",
    "4244e72b2aa8aae9a92f684fcd5090a852223888",
}
# Revision namespaces are independent: app identities never authorize ROOT
# policy snapshots, and ROOT identities never authorize app test fixtures.
SOURCE_BINDINGS = {
    "tests/unit/test_credential_redaction.py": ("orchestrator", SOURCE_REVISIONS),
    "tests/unit/test_knowledge_tools.py": ("orchestrator", SOURCE_REVISIONS),
    "scripts/hooks/pii_precommit.sh":
        ("root_source", {"4cc17080c6209e5d7f2a744807c9cf87ae0bf70f"}),
}
REGULAR_MODES = {"100644", "100755"}


def index_entries(repo: Path) -> dict[str, tuple[str, str]]:
    result = subprocess.run(
        ["git", "-C", str(repo), "ls-files", "--stage", "-z"],
        check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    entries = {}
    for entry in result.stdout.split(b"\0"):
        if not entry:
            continue
        metadata, raw_path = entry.split(b"\t", 1)
        mode, oid, stage = metadata.decode("ascii").split()
        if stage != "0":
            raise ValueError("unmerged index cannot establish fixture custody")
        path = raw_path.decode("utf-8", "surrogateescape")
        entries[path] = (mode, oid)
    return entries


class IndexBlobs:
    """One batch Git object reader for the entire hook invocation."""

    def __init__(self, repo: Path, entries: dict[str, tuple[str, str]]):
        self.entries = entries
        self.cache: dict[str, bytes] = {}
        self.process = subprocess.Popen(
            ["git", "-C", str(repo), "cat-file", "--batch"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        )

    def read(self, path: str) -> bytes:
        mode, oid = self.entries[path]
        if mode not in REGULAR_MODES:
            raise ValueError("native custody must contain indexed regular blobs")
        if oid not in self.cache:
            self.process.stdin.write(oid.encode("ascii") + b"\n")
            self.process.stdin.flush()
            header = self.process.stdout.readline().decode("ascii").split()
            if len(header) != 3 or header[:2] != [oid, "blob"]:
                raise ValueError("indexed object is not a regular blob")
            size = int(header[2])
            data = self.process.stdout.read(size)
            if len(data) != size or self.process.stdout.read(1) != b"\n":
                raise ValueError("incomplete indexed object")
            self.cache[oid] = data
        return self.cache[oid]

    def close(self):
        self.process.stdin.close()
        self.process.stdout.close()
        self.process.wait()


def native_container(path: str) -> PurePosixPath | None:
    parts = path.split("/")
    if (len(parts) < 5 or parts[:2] != ["artifacts", "ni05"]
            or any(part in {"", ".", ".."} for part in parts)
            or not re.fullmatch(r"native-[A-Za-z0-9-]+", parts[-2])
            or not re.fullmatch(r"read-[0-9]+[.]bin", parts[-1])):
        return None
    return PurePosixPath(path).parent


def reader():
    path = Path(__file__).resolve().parents[2] / "scripts/ci/native_conformance.py"
    spec = importlib.util.spec_from_file_location("ni31_native_reader", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.read_receipt


def verified_phase(container: PurePosixPath, blobs: IndexBlobs, read_receipt):
    record = json.loads(blobs.read(str(container / "receipt.json")))
    pins = [record["request"], record["log"]]
    pins.extend(item["artifact"] for item in record["readset"])
    if record["junit"] is not None:
        pins.append(record["junit"])
    pins.extend(item["artifact"] for item in record.get("generated_outputs", []))
    names = ["receipt.json"]
    for pin in pins:
        name = pin["name"]
        if not isinstance(name, str) or PurePosixPath(name).name != name or name in {"", ".", ".."}:
            raise ValueError("nonlocal indexed custody member")
        names.append(name)
    if len(names) != len(set(names)):
        raise ValueError("duplicate native custody member")
    with tempfile.TemporaryDirectory(prefix="ni31-staged-custody-") as temp:
        destination = Path(temp)
        for name in names:
            with (destination / name).open("xb") as output:
                output.write(blobs.read(str(container / name)))
        verified, _ = read_receipt(destination / "receipt.json")
    return verified


def exemptions(repo: Path) -> list[str]:
    entries = index_entries(repo)
    changed = subprocess.run(
        ["git", "-C", str(repo), "diff", "--cached", "--name-only", "-z", "--diff-filter=ACM"],
        check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    ).stdout
    candidates = [(path.decode("utf-8", "surrogateescape"),
                   native_container(path.decode("utf-8", "surrogateescape")))
                  for path in changed.split(b"\0") if path]
    candidates = [(path, parent) for path, parent in candidates if parent is not None]
    if not candidates:
        return []
    read_receipt = reader()
    blobs = IndexBlobs(repo, entries)
    phases = {}
    allowed = []
    try:
        for path, parent in candidates:
            try:
                content_hash = hashlib.sha256(blobs.read(path)).hexdigest()
                if content_hash not in FIXTURES.values():
                    continue
                if parent not in phases:
                    try:
                        phases[parent] = verified_phase(parent, blobs, read_receipt)
                    except (KeyError, ValueError, TypeError, AttributeError, OSError):
                        phases[parent] = None
                record = phases[parent]
                if record is None:
                    continue
                cwd = PurePosixPath(record["cwd"])
                if not cwd.is_absolute() or ".." in cwd.parts:
                    continue
                source = [relative for relative, sha in FIXTURES.items() if sha == content_hash][0]
                repository, revisions = SOURCE_BINDINGS[source]
                if record["repositories"].get(repository) not in revisions:
                    continue
                expected_name = str(cwd / source)
                bound = [item for item in record["readset"]
                         if item.get("role") == "declared_read"
                         and item.get("name") == expected_name
                         and item.get("artifact") == {"name": PurePosixPath(path).name,
                                                      "sha256": content_hash}]
                if len(bound) == 1:
                    allowed.append(path)
            except (KeyError, ValueError, TypeError, AttributeError, OSError):
                continue
    finally:
        blobs.close()
    return allowed


def main() -> int:
    try:
        allowed = exemptions(Path(sys.argv[1]).resolve())
    except (IndexError, KeyError, ValueError, TypeError, AttributeError, OSError, subprocess.SubprocessError):
        return 1
    # Emit only after validation, with NUL framing for exact Git paths.
    for path in allowed:
        sys.stdout.buffer.write(path.encode("utf-8", "surrogateescape") + b"\0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
