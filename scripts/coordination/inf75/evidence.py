#!/usr/bin/env python3
"""Check byte custody of a sealed P1c evidence bundle.

This module does not establish that a capture is complete, that its normalized
record was derived from its raw evidence, or that any object was loaded. A
successful result must not be used to set the screen's ``verified`` flags.
The caller must obtain the manifest digest and source commits from an
independent, trusted authority, rather than from the bundle itself.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

_HEX256 = re.compile(r"[0-9a-f]{64}\Z")
_COMMIT = re.compile(r"[0-9a-f]{40}\Z")
_ROLES = frozenset({"normalized", "census", "footprint", "source_patch",
                    "anchor_profile", "candidate_profile"})
_LIMIT = 256 * 1024 * 1024


class EvidenceError(ValueError):
    """Missing, malformed, unbound or changed evidence."""


def _read(path: Path, limit: int = _LIMIT) -> bytes:
    if not path.is_file() or path.stat().st_size > limit:
        raise EvidenceError(f"not a regular-sized file: {path}")
    with path.open("rb") as f:
        result = f.read(limit + 1)
    if len(result) > limit:
        raise EvidenceError(f"file too large: {path}")
    return result


def _json(data: bytes) -> dict:
    try:
        value = json.loads(data)
    except (ValueError, UnicodeError) as e:
        raise EvidenceError("invalid JSON") from e
    if not isinstance(value, dict):
        raise EvidenceError("expected JSON object")
    return value


def verify_bundle(manifest_path: Path, *, expected_manifest_sha256: str,
                  expected_parent: str, expected_candidate: str) -> dict:
    """Return a byte-custody receipt, never an execution or classification claim."""
    if not isinstance(expected_manifest_sha256, str) or not _HEX256.fullmatch(expected_manifest_sha256):
        raise EvidenceError("trusted manifest digest required")
    if any(not isinstance(c, str) or not _COMMIT.fullmatch(c)
           for c in (expected_parent, expected_candidate)):
        raise EvidenceError("full trusted source commits required")
    try:
        manifest_path = Path(manifest_path).resolve(strict=True)
    except OSError as e:
        raise EvidenceError("manifest unavailable") from e
    raw = _read(manifest_path, 1024 * 1024)
    if hashlib.sha256(raw).hexdigest() != expected_manifest_sha256:
        raise EvidenceError("manifest digest mismatch")
    m = _json(raw)
    if (m.get("schema") != "epyc.inf75.evidence_binding.v1"
            or m.get("parent") != expected_parent or m.get("candidate") != expected_candidate):
        raise EvidenceError("schema or source binding mismatch")
    files = m.get("files")
    if not isinstance(files, dict) or set(files) != _ROLES:
        raise EvidenceError("complete fixed evidence role set required")
    root = manifest_path.parent
    contents, digests = {}, {}
    for role in sorted(_ROLES):
        item = files[role]
        if not isinstance(item, dict) or set(item) != {"path", "sha256"}:
            raise EvidenceError(f"invalid {role} entry")
        name, digest = item["path"], item["sha256"]
        if (not isinstance(name, str) or not name or Path(name).is_absolute()
                or not isinstance(digest, str) or not _HEX256.fullmatch(digest)):
            raise EvidenceError(f"invalid {role} path or digest")
        try:
            target = (root / name).resolve(strict=True)
        except OSError as e:
            raise EvidenceError(f"{role} unavailable") from e
        if not target.is_relative_to(root):
            raise EvidenceError(f"{role} escapes evidence bundle")
        blob = _read(target)
        if hashlib.sha256(blob).hexdigest() != digest:
            raise EvidenceError(f"{role} digest mismatch")
        contents[role], digests[role] = blob, digest
    record = _json(contents["normalized"])
    try:
        if (record["footprint"]["sha256"] != digests["footprint"]
                or record["t1"]["anchor_profile_sha256"] != digests["anchor_profile"]
                or record["t1"]["candidate_profile_sha256"] != digests["candidate_profile"]):
            raise EvidenceError("normalized evidence references differ from sealed files")
    except (KeyError, TypeError) as e:
        raise EvidenceError("normalized evidence lacks required references") from e
    return {"schema": "epyc.inf75.byte_custody_receipt.v1", "status": "BYTE_BINDING_ONLY",
            "manifest_sha256": expected_manifest_sha256, "parent": expected_parent,
            "candidate": expected_candidate, "digests": digests}
