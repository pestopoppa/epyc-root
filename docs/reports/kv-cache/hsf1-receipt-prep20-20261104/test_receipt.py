"""Offline lifecycle coverage for the exact hsf1-next15 receipt source."""
from __future__ import annotations

import importlib.util
import hashlib
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPT_PATH = Path(__file__).with_name("receipt.py")
spec = importlib.util.spec_from_file_location("hsf1_receipt", RECEIPT_PATH)
receipt = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(receipt)

T0 = datetime(2026, 11, 4, 12, 0, tzinfo=timezone.utc)
DIGEST = "a" * 64


def make(**overrides):
    fields = dict(
        role="gpu-main", model_id="model-27b", device_id="mi210-0",
        started_at=T0, load_model_at=T0 + timedelta(seconds=2),
        loaded_at=T0 + timedelta(seconds=20), healthy_at=T0 + timedelta(seconds=22),
        first_token_at=T0 + timedelta(seconds=25),
        argv=["llama-server", "-m", "/models/model.gguf", "--header", "Authorization: Bearer secret"],
        server_sha256=DIGEST, kernel_store_sha256="b" * 64, gguf_sha256="c" * 64,
        fincore_resident_bytes=990, fincore_file_bytes=1000,
        outcome="healthy_first_token", error_class=None,
    )
    fields.update(overrides)
    return receipt.build_receipt(**fields)


class ReceiptLifecycleTests(unittest.TestCase):
    def test_success_has_durations_custody_and_redacted_argv(self):
        got = make()
        self.assertEqual(got["durations_s"]["start_to_first_token"], 25)
        self.assertEqual(got["cache_class"], "hot")
        self.assertIsNone(got["argv"])
        self.assertTrue(got["argv_redacted"])
        self.assertEqual(got["argv_sha256"], hashlib.sha256(
            json.dumps(["llama-server", "-m", "/models/model.gguf", "--header",
                        "Authorization: Bearer secret"], ensure_ascii=False,
                       separators=(",", ":")).encode()).hexdigest())
        self.assertNotIn("Authorization: Bearer secret", json.dumps(got))
        self.assertFalse(got["argv_digest_contract"]["keyed"])
        self.assertIn("guessing low-entropy", got["argv_digest_contract"]["limitation"])
        self.assertEqual(got["custody_sha256"]["gguf"], "c" * 64)

    def test_outcomes_and_unknown_cache_are_explicit(self):
        got = make(outcome="healthy_no_first_token", first_token_at=None,
                   fincore_resident_bytes=None, fincore_file_bytes=None)
        self.assertEqual(got["outcome"], "healthy_no_first_token")
        self.assertEqual(got["cache_class"], "unknown")
        failed = make(outcome="spawn_failed", error_class="OSError", load_model_at=None,
                      loaded_at=None, healthy_at=None, first_token_at=None)
        self.assertEqual(failed["timestamps_utc"]["model_loaded"], None)

    def test_invalid_timestamp_order_and_incomplete_failure_refuse(self):
        with self.assertRaisesRegex(ValueError, "non-monotone"):
            make(healthy_at=T0 - timedelta(seconds=1))
        with self.assertRaisesRegex(ValueError, "requires error_class"):
            make(outcome="health_failed", healthy_at=None, first_token_at=None)

    def test_effective_argv_digest_changes_with_secret_but_secret_is_never_stored(self):
        a = make(argv=["server", "--header", "Authorization: Bearer alpha"])
        b = make(argv=["server", "--header", "Authorization: Bearer beta"])
        self.assertNotEqual(a["argv_sha256"], b["argv_sha256"])
        self.assertNotIn("Bearer alpha", json.dumps(a))
        self.assertNotIn("Bearer beta", json.dumps(b))

    def test_writer_is_atomic_and_never_overwrites(self):
        with tempfile.TemporaryDirectory(prefix=".test-receipts-", dir=ROOT) as directory:
            path = receipt.write_receipt(Path(directory), make())
            self.assertTrue(path.is_file())
            with self.assertRaises(FileExistsError):
                receipt.write_receipt(Path(directory), make())


if __name__ == "__main__":
    unittest.main(verbosity=2)
