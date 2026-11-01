#!/usr/bin/env python3
"""Verify the candidate's detached runtime source seal before producer or consumer work."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "CANDIDATE-MANIFEST.json"
SOURCE_LIST = ROOT / "SOURCE-CODE.sha256"

def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()

def verify_source_seal(root: Path = ROOT) -> tuple[bool, str]:
    root = Path(root)
    manifest_path = root / "CANDIDATE-MANIFEST.json"
    source_list = root / "SOURCE-CODE.sha256"
    try:
        manifest_bytes = manifest_path.read_bytes()
        manifest = json.loads(manifest_bytes)
        entries_bytes = source_list.read_bytes()
    except (OSError, json.JSONDecodeError) as exc:
        return False, f"source manifest unavailable: {exc}"
    expected = manifest.get("source_code_manifest_sha256")
    if not isinstance(expected, str) or sha(source_list) != expected:
        return False, "SOURCE-CODE.sha256 digest does not match candidate manifest"
    for line_no, line in enumerate(entries_bytes.decode("utf-8").splitlines(), 1):
        if not line:
            continue
        digest, sep, name = line.partition("  ")
        if not sep or len(digest) != 64 or not name:
            return False, f"malformed source seal entry at line {line_no}"
        path = Path(name)
        if not path.is_absolute():
            path = root / path
        if path.is_symlink() or not path.is_file():
            return False, f"source path missing or symlinked: {name}"
        if sha(path) != digest:
            return False, f"source digest mismatch: {name}"
    return True, sha(manifest_path)

if __name__ == "__main__":
    ok, detail = verify_source_seal()
    print(detail)
    raise SystemExit(0 if ok else 1)
