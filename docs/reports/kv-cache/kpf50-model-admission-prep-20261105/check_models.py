#!/usr/bin/env python3
"""Read the small sealed receipt, then stat models; never open model weights."""
import hashlib
import json
from pathlib import Path
import stat
import sys

D = Path(__file__).resolve().parent
EXPECTED_PATHS = (
    "/mnt/raid0/llm/models/Qwen3.8-27B-Q8_0.gguf",
    "/mnt/raid0/llm/models/Qwen3.8-27B-DFlash2-Q8_0.gguf",
)
FIELDS = ("path", "device", "inode", "size", "mtime_ns")

def main():
    if len(sys.argv) != 1:
        raise ValueError("no overrides permitted")
    seals = json.loads((D / "seals.json").read_text())
    if set(seals) != {"check_models.py", "models.stat.json"}:
        raise ValueError("unexpected seal set")
    for name, expected in seals.items():
        if hashlib.sha256((D / name).read_bytes()).hexdigest() != expected:
            raise ValueError("admission input seal changed: " + name)
    receipt = json.loads((D / "models.stat.json").read_text())
    if receipt.get("schema") != "kpf50.model-stat-admission.v1":
        raise ValueError("unknown receipt schema")
    records = receipt["models"]
    if len(records) != 2:
        raise ValueError("expected exactly two models")
    for rec, expected_path in zip(records, EXPECTED_PATHS):
        if set(rec) != set(FIELDS) or rec["path"] != expected_path:
            raise ValueError("unexpected model identity fields or path")
        if any(type(rec[k]) is not int or rec[k] < 0 for k in FIELDS[1:]):
            raise ValueError("invalid model stat fields")
        p = Path(expected_path)
        if p.resolve(strict=True) != p:
            raise ValueError("model symlink substitution")
        s = p.stat()
        if not stat.S_ISREG(s.st_mode):
            raise ValueError("model is not regular")
        actual = dict(path=expected_path, device=s.st_dev, inode=s.st_ino,
                      size=s.st_size, mtime_ns=s.st_mtime_ns)
        if actual != rec:
            raise ValueError("model metadata drift: " + expected_path)
    print("PASS: sealed model metadata matched; no model contents opened")

if __name__ == "__main__":
    main()
