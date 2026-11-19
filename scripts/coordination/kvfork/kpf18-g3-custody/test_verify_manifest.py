import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("verify_manifest", Path(__file__).with_name("verify_manifest.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class VerifyManifestTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.a = self.root / "a"
        self.b = self.root / "b"
        self.a.write_bytes(b"alpha")
        self.b.write_bytes(b"beta")
        self.manifest = self.root / "manifest.sha256"
        self.write_manifest([self.a, self.b])

    def write_manifest(self, paths):
        self.manifest.write_text("".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p}\n" for p in paths))
        self.pin = hashlib.sha256(self.manifest.read_bytes()).hexdigest()

    def test_exact_inventory_and_bytes_pass(self):
        self.assertEqual(module.verify(self.manifest, [str(self.a), str(self.b)], self.pin), 2)

    def test_empty_inventory_refused(self):
        self.write_manifest([])
        with self.assertRaisesRegex(ValueError, "empty expected inventory"):
            module.verify(self.manifest, [], self.pin)

    def test_missing_or_extra_path_refused(self):
        with self.assertRaisesRegex(ValueError, "coverage mismatch"):
            module.verify(self.manifest, [str(self.a)], self.pin)
        with self.assertRaisesRegex(ValueError, "coverage mismatch"):
            module.verify(self.manifest, [str(self.a), str(self.b), str(self.root / "c")], self.pin)

    def test_manifest_digest_and_file_tampering_refused(self):
        with self.assertRaisesRegex(ValueError, "manifest digest mismatch"):
            module.verify(self.manifest, [str(self.a), str(self.b)], "0" * 64)
        self.b.write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError, "file digest mismatch"):
            module.verify(self.manifest, [str(self.a), str(self.b)], self.pin)

    def test_duplicate_expected_and_manifest_paths_refused(self):
        with self.assertRaisesRegex(ValueError, "duplicate expected"):
            module.verify(self.manifest, [str(self.a), str(self.a)], self.pin)
        self.write_manifest([self.a, self.a])
        with self.assertRaisesRegex(ValueError, "duplicate manifest path"):
            module.verify(self.manifest, [str(self.a)], self.pin)


if __name__ == "__main__":
    unittest.main()
