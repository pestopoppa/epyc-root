#!/usr/bin/env python3
"""Focused regression for the KVQ witness normalizer in the adjacent producer file."""
from __future__ import annotations

import ast
import copy
import re
import typing
import unittest
from pathlib import Path

SOURCE = Path(__file__).with_name("kv_quant_27b_v10_sweep.py")
TREE = ast.parse(SOURCE.read_text(encoding="utf-8"), filename=str(SOURCE))
WANTED = {"_binary_identity_for_witness", "identity_witness_matches"}
FUNCTIONS = [node for node in TREE.body if isinstance(node, ast.FunctionDef) and node.name in WANTED]
if {node.name for node in FUNCTIONS} != WANTED:
    raise RuntimeError("patched producer witness functions missing")
namespace = {"copy": copy, "re": re, "Any": typing.Any}
exec(compile(ast.Module(body=FUNCTIONS, type_ignores=[]), str(SOURCE), "exec"), namespace)
identity_witness_matches = namespace["identity_witness_matches"]


def witness(address: str = "0x00007f00abc00000") -> dict:
    return {
        "source": {"sha256": "source-a"},
        "binary": {
            "binary_sha256": "binary-a",
            "artifact": {"path": "/kernel/bin/llama-server", "sha256": "binary-a"},
            "linkage_receipt": {
                "verifier_id": "verify-ggml-v1",
                "verifier_artifact": {"path": "/tools/verify.sh", "sha256": "verifier-a"},
                "verifier_sha256": "verifier-a",
                "expected_tree": "/kernel/bin",
                "ld_library_path": "/kernel/bin:/rocm/lib",
                "capture": {"returncode": 0, "stdout": "PASS: linkage paths verified\n", "stderr": ""},
                "verdict": "pass",
                "inspected_libraries": [{
                    "soname": "libggml-hip.so.0", "path": "/kernel/bin/libggml-hip.so.0",
                    "resolved_path": "/kernel/bin/libggml-hip.so.0", "stable": True,
                    "sha256": "dso-a",
                }],
                "inspected_count": 1,
                "required_sonames_present": ["libggml-hip.so.0"],
                "required_sonames_satisfied": True,
                "ldd": {
                    "returncode": 0,
                    "stdout": f"\tlibggml-hip.so.0 => /kernel/bin/(0xPATH)/libggml-hip.so.0 ({address})\n",
                    "stderr": "",
                    "argv": ["ldd", "/kernel/bin/llama-server"],
                },
            },
        },
        "target_model": {"sha256": "model-a"},
        "harness": {"sha256": "harness-a"},
        "harness_snapshot": {"sha256": "harness-a"},
        "kernel_store": {"sha256": "store-a"},
    }


class LinkageWitnessASLRTests(unittest.TestCase):
    def test_aslr_only_address_change_matches(self):
        before = witness("0x00007f00abc00000")
        after = witness("0x00007e00def00000")
        self.assertEqual(identity_witness_matches(before, after), (True, "ok"))
        # Comparison must not mutate sealed native evidence.
        self.assertIn("0x00007f00abc00000", before["binary"]["linkage_receipt"]["ldd"]["stdout"])

    def test_library_digest_change_still_fails(self):
        before, after = witness(), witness("0x00007e00def00000")
        after["binary"]["linkage_receipt"]["inspected_libraries"][0]["sha256"] = "dso-changed"
        ok, reason = identity_witness_matches(before, after)
        self.assertFalse(ok)
        self.assertEqual(reason, "post-execution binary differs from pre-execution witness")

    def test_library_path_change_still_fails(self):
        before, after = witness(), witness("0x00007e00def00000")
        after["binary"]["linkage_receipt"]["ldd"]["stdout"] = (
            "\tlibggml-hip.so.0 => /other/libggml-hip.so.0 (0x00007e00def00000)\n"
        )
        ok, _ = identity_witness_matches(before, after)
        self.assertFalse(ok)

    def test_inspected_library_path_change_still_fails(self):
        before, after = witness(), witness("0x00007e00def00000")
        after["binary"]["linkage_receipt"]["inspected_libraries"][0]["resolved_path"] = "/other/libggml-hip.so.0"
        ok, _ = identity_witness_matches(before, after)
        self.assertFalse(ok)

    def test_verifier_identity_change_still_fails(self):
        before, after = witness(), witness("0x00007e00def00000")
        after["binary"]["linkage_receipt"]["verifier_sha256"] = "verifier-changed"
        ok, _ = identity_witness_matches(before, after)
        self.assertFalse(ok)

    def test_parenthesized_hex_in_path_is_not_normalized(self):
        before, after = witness("0x00007f00abc00000"), witness("0x00007e00def00000")
        before_path = before["binary"]["linkage_receipt"]["ldd"]["stdout"]
        after_path = after["binary"]["linkage_receipt"]["ldd"]["stdout"]
        after["binary"]["linkage_receipt"]["ldd"]["stdout"] = after_path.replace("(0xPATH)", "(0xOTHER)")
        self.assertNotEqual(before_path, after["binary"]["linkage_receipt"]["ldd"]["stdout"])
        ok, _ = identity_witness_matches(before, after)
        self.assertFalse(ok)

    def test_non_address_ldd_change_still_fails(self):
        before, after = witness(), witness("0x00007e00def00000")
        after["binary"]["linkage_receipt"]["ldd"]["stdout"] = (
            "\tlibggml-hip.so.0 => /kernel/bin/other.so (0x00007e00def00000)\n"
        )
        ok, _ = identity_witness_matches(before, after)
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main(verbosity=2)
