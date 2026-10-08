#!/usr/bin/env python3
"""Verify exact candidate copies before running fake-only tests."""
import hashlib, json
from pathlib import Path
root=Path(__file__).resolve().parent
pins=json.loads((root/"source-pins.json").read_text())
for row in pins["files"]:
    path=root/row["path"]
    data=path.read_bytes()
    assert len(data)==row["bytes"], row["path"]+": byte count mismatch"
    assert hashlib.sha256(data).hexdigest()==row["sha256"], row["path"]+": SHA-256 mismatch"
print("verified", len(pins["files"]), "pinned candidate files")
