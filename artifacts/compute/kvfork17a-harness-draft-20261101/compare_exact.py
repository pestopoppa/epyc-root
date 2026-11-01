#!/usr/bin/env python3
"""Strict bitwise comparator for complete KPF-17a harness listings.

Usage: compare_exact.py <listing-a> <expected-a.json> <dump-a> <listing-b> <expected-b.json> <dump-b>
Expected unsupported rows must be explicitly declared by backend; unexpected
unsupported/missing/malformed cases and any output mismatch exit nonzero.
"""
from __future__ import annotations
import argparse
import json
import re
import struct
import sys
from pathlib import Path

CASE_RE = re.compile(r"^case\s+(\d+)\s+(.+)$")
FIELD_RE = re.compile(r"(?:^|\s)(hsk|hsv|nh|nr2|nb|hash)=([^\s]+)")
SHARED_RE = re.compile(r"(?:^|\s)shared=(\d+)(?:\s|$)")
NAN_RE = re.compile(r"(?:^|\s)nan=(\d+)(?:\s|$)")


def fail(msg: str) -> "NoReturn":
    print(f"FAIL: {msg}", file=sys.stderr)
    raise SystemExit(1)


def load_manifest(path: Path) -> tuple[int, set[int], set[int]]:
    try:
        obj = json.loads(path.read_text())
        count = int(obj["expected_cases"])
        supported = {int(x) for x in obj["expected_supported"]}
        unsupported = {int(x) for x in obj["expected_unsupported"]}
    except (OSError, ValueError, KeyError, TypeError) as e:
        fail(f"invalid expected-case manifest {path}: {e}")
    if count <= 0 or supported & unsupported or supported | unsupported != set(range(count)):
        fail(f"manifest must partition case ids 0..{count-1}: {path}")
    shared = set(range(count - 25, count))
    if not shared <= supported:
        fail(f"manifest declares shared-trunk case(s) unsupported: {sorted(shared - supported)}")
    return count, supported, unsupported


def load_listing(path: Path, manifest: Path) -> tuple[dict[int, str], set[int]]:
    count, expected_supported, expected_unsupported = load_manifest(manifest)
    if not path.is_file():
        fail(f"listing is missing: {path}")
    rows: dict[int, str] = {}
    unsupported: set[int] = set()
    all_lines = []
    for raw in path.read_text(errors="replace").splitlines():
        line = raw.strip()
        if line.startswith("case "):
            m = CASE_RE.match(line)
            if not m:
                fail(f"malformed case row in {path}: {line}")
            idx, body = int(m.group(1)), m.group(2)
            if idx in rows or idx in unsupported:
                fail(f"duplicate case {idx} in {path}")
            if body == "unsupported":
                unsupported.add(idx)
            else:
                nan = NAN_RE.search(line)
                if not nan or int(nan.group(1)) != 0:
                    fail(f"case {idx} has missing/nonzero nan count in {path}")
                rows[idx] = line
        elif line.startswith("ALL "):
            all_lines.append(line)
    if set(rows) != expected_supported:
        fail(f"supported cases in {path} differ from manifest: missing={sorted(expected_supported-set(rows))}, unexpected={sorted(set(rows)-expected_supported)}")
    if unsupported != expected_unsupported:
        fail(f"unsupported cases in {path} differ from manifest: missing={sorted(expected_unsupported-unsupported)}, unexpected={sorted(unsupported-expected_unsupported)}")
    if len(all_lines) != 1 or not re.fullmatch(r"ALL [0-9a-fA-F]{16}", all_lines[0]):
        fail(f"expected exactly one well-formed ALL summary in {path}, found {all_lines}")
    aggregate = 0x14650fb0739d0383
    for idx in sorted(expected_supported):
        fields = dict(FIELD_RE.findall(rows[idx]))
        try:
            h = int(fields["hash"], 16)
        except (KeyError, ValueError):
            fail(f"case {idx} has no valid output hash in {path}")
        aggregate = ((aggregate ^ h) * 0x100000001b3) & ((1 << 64) - 1)
    if all_lines[0].split()[1].lower() != f"{aggregate:016x}":
        fail(f"ALL summary does not match supported case hashes in {path}")
    shared_rows = [i for i, row in rows.items() if (m := SHARED_RE.search(row)) and int(m.group(1)) > 0]
    if len(shared_rows) != 25:
        fail(f"expected 25 shared-trunk output rows in {path}; found {len(shared_rows)}")
    return rows, expected_unsupported


def read_dump(directory: Path, idx: int, row: str) -> bytes:
    path = directory / f"out_{idx:02d}.bin"
    if not path.is_file():
        fail(f"missing output for case {idx}: {path}")
    data = path.read_bytes()
    fields = dict(FIELD_RE.findall(row))
    try:
        expected_floats = int(fields["hsv"]) * int(fields["nh"]) * int(fields["nr2"]) * int(fields["nb"])
    except (KeyError, ValueError):
        fail(f"case {idx} has malformed output-shape metadata: {row}")
    if len(data) != expected_floats * 4:
        fail(f"case {idx} output has {len(data)} bytes; expected {expected_floats * 4}: {path}")
    vals = struct.unpack(f"={expected_floats}f", data)
    if any(not (v == v and abs(v) != float("inf")) for v in vals):
        fail(f"non-finite output in case {idx}: {path}")
    return data


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("listing_a", type=Path)
    ap.add_argument("expected_a", type=Path)
    ap.add_argument("dump_a", type=Path)
    ap.add_argument("listing_b", type=Path)
    ap.add_argument("expected_b", type=Path)
    ap.add_argument("dump_b", type=Path)
    args = ap.parse_args()
    count_a, supported_a, _ = load_manifest(args.expected_a)
    count_b, supported_b, _ = load_manifest(args.expected_b)
    if (count_a, supported_a) != (count_b, supported_b):
        fail("comparison arms have different declared supported-case sets; compare like backend paths")
    a, _ = load_listing(args.listing_a, args.expected_a)
    b, _ = load_listing(args.listing_b, args.expected_b)
    if a != b:
        for idx in sorted(set(a) | set(b)):
            if a.get(idx) != b.get(idx):
                fail(f"case metadata differs at index {idx}: A={a.get(idx)!r} B={b.get(idx)!r}")
    for idx in sorted(supported_a):
        x = read_dump(args.dump_a, idx, a[idx])
        y = read_dump(args.dump_b, idx, b[idx])
        if len(x) != len(y):
            fail(f"case {idx} output lengths differ: A={len(x)} B={len(y)}")
        if x != y:
            fail(f"case {idx} is not bit-identical")
    print(f"PASS: all {len(supported_a)} declared supported cases are bit-identical; {count_a-len(supported_a)} declared unsupported cases were skipped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
