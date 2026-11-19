"""Offline tests for the HSF-1 receipt design; no launch or model access."""
import base64
import hashlib
import importlib.util
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

SOURCE = Path(__file__).with_name("receipt.py")
spec = importlib.util.spec_from_file_location("hsf1_receipt_design", SOURCE)
receipt = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(receipt)

T0 = datetime(2026, 11, 4, 12, 0, tzinfo=timezone.utc)
ARGV = ["llama-server", "--header", "Authorization: Bearer alpha", "--label", "customer secret"]
PLAINTEXT = json.dumps(ARGV, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
CIPHERTEXT = b"test-only opaque envelope"
DIGEST = "a" * 64


def encrypt(data):
    assert data == PLAINTEXT
    return "test-key-v1", CIPHERTEXT


def make(**overrides):
    fields = dict(role="gpu-main", model_id="model-27b", device_id="mi210-0",
        started_at=T0, load_model_at=T0 + timedelta(seconds=2),
        loaded_at=T0 + timedelta(seconds=20), healthy_at=T0 + timedelta(seconds=22),
        first_token_at=T0 + timedelta(seconds=25), argv=ARGV, encrypt_argv=encrypt,
        server_sha256=DIGEST, kernel_store_sha256="b" * 64, gguf_sha256="c" * 64,
        fincore_resident_bytes=990, fincore_file_bytes=1000,
        outcome="healthy_first_token", error_class=None)
    fields.update(overrides)
    return receipt.build_receipt(**fields)


class EffectiveArgvCaptureTests(unittest.TestCase):
    def test_complete_argv_is_passed_to_encryptor_and_only_envelope_is_recorded(self):
        got = make()
        capture = got["effective_argv_capture"]
        self.assertEqual(capture["key_id"], "test-key-v1")
        self.assertEqual(base64.b64decode(capture["ciphertext_b64"]), CIPHERTEXT)
        self.assertEqual(capture["ciphertext_sha256"], hashlib.sha256(CIPHERTEXT).hexdigest())
        serialized = json.dumps(got)
        for secret in ("alpha", "customer secret", "Authorization"):
            self.assertNotIn(secret, serialized)
        self.assertNotIn("argv_sha256", got)

    def test_rejects_invalid_envelope_metadata(self):
        with self.assertRaisesRegex(ValueError, "key id and ciphertext"):
            make(encrypt_argv=lambda _: ("", b"cipher"))
        with self.assertRaisesRegex(ValueError, "key id and ciphertext"):
            make(encrypt_argv=lambda _: ("key", b""))

    def test_atomic_writer_syncs_file_and_parent_directory_and_never_overwrites(self):
        with tempfile.TemporaryDirectory() as tmp:
            real_fsync = __import__("os").fsync
            calls = []
            def record_fsync(fd):
                calls.append(fd)
                return real_fsync(fd)
            with patch.object(receipt.os, "fsync", side_effect=record_fsync):
                path = receipt.write_receipt(Path(tmp), make())
            self.assertEqual(len(calls), 2)
            self.assertTrue(path.is_file())
            self.assertEqual(json.loads(path.read_text())["effective_argv_capture"]["key_id"], "test-key-v1")
            with self.assertRaises(FileExistsError):
                receipt.write_receipt(Path(tmp), make())


if __name__ == "__main__":
    unittest.main(verbosity=2)
