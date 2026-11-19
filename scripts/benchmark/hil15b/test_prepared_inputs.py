import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from prepared_inputs import file_identity, model_pin, runtime_pin


class PreparedInputsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.model = self.root / "model.gguf"
        self.model.write_bytes(b"fixture weights")
        self.sha = hashlib.sha256(self.model.read_bytes()).hexdigest()
        self.receipt = self.root / "prepared-model.json"
        self.record = {"schema": "hil15-prepared-model/v1", "path": str(self.model.resolve()),
                       "sha256": self.sha, "identity": list(file_identity(self.model))}
        self.receipt.write_text(json.dumps(self.record))

    def test_content_verified_input_is_reused_without_reading_weights(self):
        from unittest.mock import patch
        with patch.object(Path, "read_bytes", side_effect=AssertionError("weight read")):
            self.assertEqual(model_pin(self.model, self.sha, self.receipt), file_identity(self.model))

    def test_changed_model_is_refused(self):
        self.model.write_bytes(b"replacement weights")
        with self.assertRaisesRegex(ValueError, "differs"):
            model_pin(self.model, self.sha, self.receipt)

    def test_wrong_hash_path_schema_and_identity_are_refused(self):
        for key, value in [("sha256", "0" * 64), ("path", "/other/model.gguf"),
                           ("schema", "unverified"), ("identity", [0, 0, 0, 0, 0])]:
            with self.subTest(key=key):
                altered = dict(self.record, **{key: value})
                self.receipt.write_text(json.dumps(altered))
                with self.assertRaises(ValueError):
                    model_pin(self.model, self.sha, self.receipt)

    def test_runtime_requires_metadata(self):
        self.receipt.write_text(json.dumps({"schema": "hil15-python-runtime/v1"}))
        with self.assertRaises(ValueError):
            runtime_pin(self.receipt)


if __name__ == "__main__":
    unittest.main()
