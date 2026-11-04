#!/usr/bin/env python3
"""Verify an original native-source manifest through explicit custody relocations.

This tool hashes bytes only. It never imports, sources, or executes any listed file.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any


HEX64 = re.compile(r"^[0-9a-f]{64}$")


class VerificationError(ValueError):
    pass


def _reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise VerificationError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_manifest(path: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            digest, original = raw.split("  ", 1)
        except ValueError as exc:
            raise VerificationError(f"manifest line {number}: expected '<sha256>  <path>'") from exc
        if not HEX64.fullmatch(digest):
            raise VerificationError(f"manifest line {number}: invalid SHA-256")
        if not original or original in entries:
            raise VerificationError(f"manifest line {number}: empty or duplicate original path: {original!r}")
        entries[original] = digest
    if not entries:
        raise VerificationError("manifest is empty")
    return entries


def load_map(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_json_keys)
    except (OSError, json.JSONDecodeError) as exc:
        raise VerificationError(f"cannot read relocation map: {exc}") from exc
    if not isinstance(data, dict) or set(data) != {"schema", "manifest_sha256", "relocations"}:
        raise VerificationError("map must contain exactly schema, manifest_sha256, relocations")
    if data["schema"] != "kpf18-native-relocations-v1":
        raise VerificationError("unsupported relocation map schema")
    if not isinstance(data["manifest_sha256"], str) or not HEX64.fullmatch(data["manifest_sha256"]):
        raise VerificationError("invalid manifest_sha256 in relocation map")
    if not isinstance(data["relocations"], list):
        raise VerificationError("relocations must be a list")
    seen_originals: set[str] = set()
    seen_targets: set[str] = set()
    for i, row in enumerate(data["relocations"]):
        if not isinstance(row, dict) or set(row) != {"original_path", "sha256", "relocated_path"}:
            raise VerificationError(f"relocation {i}: invalid fields")
        original, digest, target = row["original_path"], row["sha256"], row["relocated_path"]
        if not isinstance(original, str) or not original:
            raise VerificationError(f"relocation {i}: invalid original_path")
        if not isinstance(digest, str) or not HEX64.fullmatch(digest):
            raise VerificationError(f"relocation {i}: invalid sha256")
        if not isinstance(target, str) or not target:
            raise VerificationError(f"relocation {i}: invalid relocated_path")
        pure = PurePosixPath(target)
        if pure.is_absolute() or ".." in pure.parts or not pure.parts or pure.parts[0] != "relocated":
            raise VerificationError(f"relocation {i}: target must be a safe path below relocated/: {target}")
        if "\\" in target or pure.as_posix() != target:
            raise VerificationError(f"relocation {i}: target path is not canonical: {target}")
        if original in seen_originals:
            raise VerificationError(f"ambiguous duplicate mapping for original path: {original}")
        if target in seen_targets:
            raise VerificationError(f"ambiguous duplicate target mapping: {target}")
        seen_originals.add(original)
        seen_targets.add(target)
    return data


def verify(manifest: Path, relocation_map: Path) -> tuple[int, int]:
    manifest = manifest.resolve(strict=True)
    relocation_map = relocation_map.resolve(strict=True)
    entries = parse_manifest(manifest)
    data = load_map(relocation_map)
    manifest_digest = sha256(manifest)
    if data["manifest_sha256"] != manifest_digest:
        raise VerificationError("relocation map is bound to a different manifest digest")

    relocations = {row["original_path"]: row for row in data["relocations"]}
    unknown = sorted(set(relocations) - set(entries))
    if unknown:
        raise VerificationError(f"relocation references path absent from manifest: {unknown[0]}")
    for original, row in relocations.items():
        if row["sha256"] != entries[original]:
            raise VerificationError(f"relocation digest disagrees with manifest for {original}")

    custody_root = relocation_map.parent.resolve(strict=True)
    verified = 0
    relocated = 0
    resolved_targets: dict[Path, str] = {}
    for original, expected in entries.items():
        row = relocations.get(original)
        if row is None:
            source = Path(original)
            if not source.is_file():
                raise VerificationError(f"unmapped original source is missing: {original}")
        else:
            source = (custody_root / row["relocated_path"]).resolve(strict=False)
            try:
                source.relative_to(custody_root)
            except ValueError as exc:
                raise VerificationError(f"relocation escapes custody root: {row['relocated_path']}") from exc
            prior = resolved_targets.get(source)
            if prior is not None:
                raise VerificationError(
                    f"ambiguous aliased relocation targets for {prior} and {original}: {source}"
                )
            resolved_targets[source] = original
            if not source.is_file():
                raise VerificationError(f"relocated source is missing: {row['relocated_path']}")
            relocated += 1
        actual = sha256(source)
        if actual != expected:
            raise VerificationError(f"digest mismatch for {original}: expected {expected}, got {actual}")
        verified += 1
    return verified, relocated


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--map", dest="relocation_map", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        verified, relocated = verify(args.manifest, args.relocation_map)
    except (OSError, VerificationError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2
    print(f"PASS: verified {verified} manifest entries ({relocated} via explicit custody relocations); bytes only, no listed file executed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
