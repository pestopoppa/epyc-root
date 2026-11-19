#!/usr/bin/env python3
"""Synthetic model-free tests for verify_receipt.py."""
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("verify_receipt.py")
spec = importlib.util.spec_from_file_location("verify_receipt", MODULE_PATH)
vr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vr)


class ReceiptTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.target = self.root / "synthetic-target.gguf"
        self.drafter = self.root / "synthetic-drafter.gguf"
        self.target.write_bytes(b"synthetic placeholder, not a model")
        self.drafter.write_bytes(b"synthetic placeholder, not a model")
        self.receipt_path = self.root / "receipt.json"
        self.manifest_path = self.root / "original.json"
        self.receipt = {
            "target": self.entry(self.target, "a" * 64, {"general.architecture": "test"}),
            "drafter": self.entry(self.drafter, "b" * 64, {
                "general.architecture": "dflash", "dflash.block_count": 5,
                "dflash.attention.sliding_window": 2048,
                "dflash.attention.sliding_window_pattern": [True] * 5}),
        }
        self.manifest = {role: {"path": e["path"], "sha256": e["sha256"]}
                         for role, e in self.receipt.items()}
        self.write_inputs()

    def tearDown(self):
        self.tmp.cleanup()

    @staticmethod
    def entry(path, digest, metadata):
        return {"path": str(path), "sha256": digest,
                "stat_identity": vr.stat_identity(str(path)), "metadata": metadata,
                "tensor_count": 1}

    def write_inputs(self):
        self.receipt_path.write_text(json.dumps(self.receipt), encoding="utf-8")
        self.manifest_path.write_text(json.dumps(self.manifest), encoding="utf-8")

    def expected(self):
        return hashlib.sha256(self.receipt_path.read_bytes()).hexdigest()

    def test_accepts_receipt_manifest_and_matching_stats(self):
        result = vr.verify(self.receipt_path, self.manifest_path, self.expected())
        self.assertTrue(result["ok"])
        self.assertFalse(result["content_hash_performed"])
        self.assertEqual(result["drafter_shape"]["layers"], 5)
        self.assertEqual(result["drafter_shape"]["sliding_window"], 2048)
        self.assertEqual(result["verified_metadata"]["drafter"], self.receipt["drafter"]["metadata"])

    def assert_drafter_metadata_rejected(self, key, value=None, missing=False,
                                         expected_error=None):
        metadata = self.receipt["drafter"]["metadata"]
        if missing:
            del metadata[key]
            expected = "required metadata field is missing"
        else:
            metadata[key] = value
            expected = f"metadata {key} mismatch"
        self.write_inputs()
        with self.assertRaisesRegex(vr.VerificationError, expected_error or expected):
            vr.verify(self.receipt_path, self.manifest_path, self.expected())

    def test_rejects_wrong_drafter_architecture(self):
        self.assert_drafter_metadata_rejected("general.architecture", "qwen35")

    def test_rejects_missing_drafter_architecture(self):
        self.assert_drafter_metadata_rejected("general.architecture", missing=True)

    def test_rejects_wrong_drafter_sliding_window(self):
        self.assert_drafter_metadata_rejected("dflash.attention.sliding_window", 1024)

    def test_rejects_missing_drafter_sliding_window(self):
        self.assert_drafter_metadata_rejected("dflash.attention.sliding_window", missing=True)

    def test_rejects_wrong_drafter_layer_pattern(self):
        self.assert_drafter_metadata_rejected(
            "dflash.attention.sliding_window_pattern", [True] * 4,
            expected_error="five-element list of booleans")

    def test_rejects_integer_equivalents_in_drafter_layer_pattern(self):
        self.assert_drafter_metadata_rejected(
            "dflash.attention.sliding_window_pattern", [1] * 5,
            expected_error="five-element list of booleans")

    def test_rejects_boolean_in_stat_identity(self):
        self.receipt["target"]["stat_identity"][0] = True
        self.write_inputs()
        with self.assertRaisesRegex(vr.VerificationError, "stat_identity is missing or malformed"):
            vr.verify(self.receipt_path, self.manifest_path, self.expected())

    def test_rejects_boolean_tensor_count(self):
        self.receipt["target"]["tensor_count"] = True
        self.write_inputs()
        with self.assertRaisesRegex(vr.VerificationError, "tensor_count is missing or invalid"):
            vr.verify(self.receipt_path, self.manifest_path, self.expected())

    def test_rejects_missing_drafter_layer_pattern(self):
        self.assert_drafter_metadata_rejected("dflash.attention.sliding_window_pattern", missing=True)

    def test_rejects_stat_drift(self):
        with self.target.open("ab") as stream:
            stream.write(b"changed")
        with self.assertRaisesRegex(vr.VerificationError, "stat tuple drift"):
            vr.verify(self.receipt_path, self.manifest_path, self.expected())

    def test_rejects_missing_metadata(self):
        del self.receipt["drafter"]["metadata"]
        self.write_inputs()
        with self.assertRaisesRegex(vr.VerificationError, "metadata is missing"):
            vr.verify(self.receipt_path, self.manifest_path, self.expected())

    def test_rejects_receipt_digest_mismatch(self):
        with self.assertRaisesRegex(vr.VerificationError, "receipt digest mismatch"):
            vr.verify(self.receipt_path, self.manifest_path, "0" * 64)

    def test_rejects_manifest_original_sha_mismatch(self):
        self.manifest["target"]["sha256"] = "f" * 64
        self.write_inputs()
        with self.assertRaisesRegex(vr.VerificationError, "sha256 differs"):
            vr.verify(self.receipt_path, self.manifest_path, self.expected())


if __name__ == "__main__":
    unittest.main()
