#!/usr/bin/env python3
"""Fake-file-only tests for receipt-backed PRELOAD_MODELS integration."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import preload_integration as integration
from verify_receipt import stat_identity, VerificationError


class PreloadIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.target = self.root / "fake-target.gguf"
        self.drafter = self.root / "fake-drafter.gguf"
        self.target.write_bytes(b"not a model: fake target")
        self.drafter.write_bytes(b"not a model: fake drafter")
        self.receipt = {
            "target": self.entry(self.target, "a" * 64, {
                "general.architecture": "qwen35", "qwen35.block_count": 65}),
            "drafter": self.entry(self.drafter, "b" * 64, {
                "general.architecture": "dflash", "dflash.block_count": 5,
                "dflash.attention.sliding_window": 2048,
                "dflash.attention.sliding_window_pattern": [True] * 5}),
        }
        self.manifest = {role: {"path": entry["path"], "sha256": entry["sha256"]}
                         for role, entry in self.receipt.items()}
        self.receipt_path = self.root / "receipt.json"
        self.manifest_path = self.root / "original.json"
        self.write_inputs()

    def tearDown(self):
        self.tmp.cleanup()

    @staticmethod
    def entry(path, digest, metadata):
        return {"path": str(path), "sha256": digest, "stat_identity": stat_identity(str(path)),
                "tensor_count": 2, "metadata": metadata}

    def write_inputs(self):
        self.receipt_path.write_text(json.dumps(self.receipt), encoding="utf-8")
        self.manifest_path.write_text(json.dumps(self.manifest), encoding="utf-8")

    def digest(self):
        return hashlib.sha256(self.receipt_path.read_bytes()).hexdigest()

    def load(self):
        # Test-only patch of the pinned constant; production API offers no override.
        with patch.object(integration, "EXPECTED_RECEIPT_SHA256", self.digest()):
            return integration.load_preload_models(self.receipt_path, self.manifest_path)

    def test_builds_existing_preload_entries_and_shape(self):
        models = self.load()
        self.assertEqual(set(models), {"target", "drafter", "draft_cache_shape"})
        self.assertEqual(set(models["target"]),
                         {"path", "sha256", "tensor_count", "metadata", "stat_identity"})
        shape = models["draft_cache_shape"]
        self.assertEqual(shape["draft_base_layers"], 0)
        self.assertEqual(shape["draft_swa_layers"], 5)
        self.assertEqual(shape["metadata"], self.receipt["drafter"]["metadata"])
        integration.unchanged_models(models)

    def test_repeated_stat_check_rejects_drift(self):
        models = self.load()
        with self.drafter.open("ab") as stream:
            stream.write(b"changed")
        with self.assertRaisesRegex(VerificationError, "stat identity changed"):
            integration.unchanged_models(models)

    def test_entry_construction_fails_if_stat_drifted_before_preload(self):
        with self.target.open("ab") as stream:
            stream.write(b"changed")
        with self.assertRaisesRegex(VerificationError, "stat tuple drift"):
            self.load()


if __name__ == "__main__":
    unittest.main()
