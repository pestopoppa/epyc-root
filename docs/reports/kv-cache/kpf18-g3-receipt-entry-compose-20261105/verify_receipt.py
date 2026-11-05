#!/usr/bin/env python3
"""Verify a preload model identity receipt without reading model contents.

This checks receipt provenance, manifest identity fields, and current filesystem
stat tuples. It deliberately does not hash model files or invoke a model runtime.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

EXPECTED_RECEIPT_SHA256 = "4a44cf4a80377a9ea03b19ae8a0e73b0777a61ed9392025678b6a4f39db41052"
ROLES = ("target", "drafter")
STAT_FIELDS = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
DRAFT_SHAPE = {
    "general.architecture": "dflash",
    "dflash.block_count": 5,
    "dflash.attention.sliding_window": 2048,
    "dflash.attention.sliding_window_pattern": [True, True, True, True, True],
}


class VerificationError(Exception):
    pass


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise VerificationError(f"cannot read valid JSON {path}: {exc}") from exc


def stat_identity(path: str) -> list[int]:
    try:
        st = os.stat(path)
    except OSError as exc:
        raise VerificationError(f"model path is unavailable: {path}: {exc}") from exc
    return [int(getattr(st, field)) for field in STAT_FIELDS]


def verify(receipt_path: Path, manifest_path: Path,
           expected_digest: str = EXPECTED_RECEIPT_SHA256) -> dict[str, Any]:
    try:
        receipt_bytes = receipt_path.read_bytes()
    except OSError as exc:
        raise VerificationError(f"cannot read receipt {receipt_path}: {exc}") from exc
    receipt_digest = hashlib.sha256(receipt_bytes).hexdigest()
    if receipt_digest != expected_digest:
        raise VerificationError(
            f"receipt digest mismatch: expected {expected_digest}, got {receipt_digest}"
        )
    try:
        receipt = json.loads(receipt_bytes)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise VerificationError(f"receipt is not valid JSON: {exc}") from exc
    manifest = load_json(manifest_path)
    if not isinstance(receipt, dict) or not isinstance(manifest, dict):
        raise VerificationError("receipt and original model manifest must be JSON objects")

    checked: list[dict[str, Any]] = []
    for role in ROLES:
        entry = receipt.get(role)
        original = manifest.get(role)
        if not isinstance(entry, dict) or not isinstance(original, dict):
            raise VerificationError(f"missing {role} entry in receipt or manifest")
        metadata = entry.get("metadata")
        if not isinstance(metadata, dict) or not metadata:
            raise VerificationError(f"{role} receipt metadata is missing or empty")
        if role == "drafter":
            for key, expected in DRAFT_SHAPE.items():
                if key not in metadata:
                    raise VerificationError(f"drafter required metadata field is missing: {key}")
                if key == "dflash.attention.sliding_window_pattern":
                    actual_pattern = metadata[key]
                    if (not isinstance(actual_pattern, list)
                            or len(actual_pattern) != 5
                            or any(type(value) is not bool for value in actual_pattern)):
                        raise VerificationError(
                            "drafter metadata dflash.attention.sliding_window_pattern "
                            "must be a five-element list of booleans"
                        )
                if metadata[key] != expected:
                    raise VerificationError(
                        f"drafter metadata {key} mismatch: expected {expected!r}, got {metadata[key]!r}"
                    )
        if "tensor_count" not in entry or type(entry["tensor_count"]) is not int:
            raise VerificationError(f"{role} receipt tensor_count is missing or invalid")
        for key in ("path", "sha256"):
            if not isinstance(entry.get(key), str) or not entry[key]:
                raise VerificationError(f"{role} receipt {key} is missing")
            if original.get(key) != entry[key]:
                raise VerificationError(f"{role} {key} differs from ORIGINAL-MODELS.json")
        recorded_stat = entry.get("stat_identity")
        if (not isinstance(recorded_stat, list) or len(recorded_stat) != len(STAT_FIELDS)
                or any(type(value) is not int for value in recorded_stat)):
            raise VerificationError(f"{role} stat_identity is missing or malformed")
        current_stat = stat_identity(entry["path"])
        if current_stat != recorded_stat:
            raise VerificationError(
                f"{role} stat tuple drift: recorded {recorded_stat}, current {current_stat}"
            )
        checked.append({"role": role, "path": entry["path"],
                        "sha256": entry["sha256"], "stat_identity": current_stat,
                        "metadata": metadata,
                        "tensor_count": entry["tensor_count"]})
    return {"ok": True, "receipt_sha256": receipt_digest, "models": checked,
            "verified_metadata": {model["role"]: model["metadata"] for model in checked},
            "drafter_shape": {"architecture": "dflash", "layers": 5,
                              "sliding_window": 2048,
                              "sliding_window_all_layers": True},
            "content_hash_performed": False,
            "scope": "receipt/manifest fields and current stat tuples only"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        # Runtime entry is pinned to the retained receipt; callers cannot override it.
        result = verify(args.receipt, args.manifest, EXPECTED_RECEIPT_SHA256)
    except VerificationError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
