#!/usr/bin/env python3
"""Offline fixtures for the KPF-17a exact comparator."""
import json
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
COMPARATOR = HERE / "compare_exact.py"
FNV_OFFSET = 0x14650fb0739d0383
FNV_PRIME = 0x100000001b3
MASK64 = (1 << 64) - 1


def fnv(data: bytes) -> int:
    value = FNV_OFFSET
    for byte in data:
        value = ((value ^ byte) * FNV_PRIME) & MASK64
    return value


def fixture(root: Path, *, wrong_shared_ids: bool = False, wrong_case_hash: bool = False):
    count = 111
    manifest = root / "expected.json"
    manifest.write_text(json.dumps({
        "expected_cases": count,
        "expected_supported": list(range(count)),
        "expected_unsupported": [],
    }))
    dumps = [root / "dump-a", root / "dump-b"]
    for directory in dumps:
        directory.mkdir()
        for idx in range(count):
            (directory / f"out_{idx:02d}.bin").write_bytes(struct.pack("=f", float(idx + 1)))

    lines = []
    aggregate = FNV_OFFSET
    for idx in range(count):
        data = (dumps[0] / f"out_{idx:02d}.bin").read_bytes()
        h = fnv(data)
        if wrong_case_hash and idx == 0:
            h ^= 1
        aggregate = ((aggregate ^ h) * FNV_PRIME) & MASK64
        has_shared = idx >= count - 25
        if wrong_shared_ids:
            has_shared = idx >= count - 24 or idx == count - 26
        shared = 1 if has_shared else 0
        # Match the harness's real listing grammar: hs=hsk/hsv.
        lines.append(
            f"case {idx:2d} hs=1/1 nh=1 nr2=1 kv=1 nb=1 nseq=1 run=1 "
            f"free=0 shared={shared} type=f16 bias=0 cap=0 hash={h:016x} nan=0"
        )
    lines.append(f"ALL {aggregate:016x}")
    listing = root / "listing.txt"
    listing.write_text("\n".join(lines) + "\n")
    return listing, manifest, dumps


class CompareExactFixtures(unittest.TestCase):
    def invoke(self, args):
        return subprocess.run([sys.executable, str(COMPARATOR), *map(str, args)], capture_output=True, text=True)

    def test_actual_listing_grammar_and_matching_dumps_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            listing, manifest, dumps = fixture(Path(tmp))
            result = self.invoke([listing, manifest, dumps[0], listing, manifest, dumps[1]])
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("111 declared supported cases", result.stdout)

    def test_wrong_shared_case_ids_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            listing, manifest, dumps = fixture(Path(tmp), wrong_shared_ids=True)
            result = self.invoke([listing, manifest, dumps[0], listing, manifest, dumps[1]])
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("shared-trunk rows", result.stderr)

    def test_listing_hash_must_match_dump_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            listing, manifest, dumps = fixture(Path(tmp), wrong_case_hash=True)
            result = self.invoke([listing, manifest, dumps[0], listing, manifest, dumps[1]])
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("output hash does not match listing", result.stderr)


if __name__ == "__main__":
    unittest.main()
