import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from verify_native_sources import VerificationError, verify


class RelocationVerifierTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.manifest = self.root / "NATIVE-SOURCES.sha256"
        self.map_path = self.root / "native_relocations.json"
        self.relocated = self.root / "relocated" / "sample.bin"
        self.relocated.parent.mkdir(parents=True)
        self.relocated.write_bytes(b"historical exact bytes\x00\xff")
        self.live = self.root / "live.bin"
        self.live.write_bytes(b"current exact bytes")
        self.mapped_digest = hashlib.sha256(self.relocated.read_bytes()).hexdigest()
        self.live_digest = hashlib.sha256(self.live.read_bytes()).hexdigest()
        self.original_mapped = str(self.root / "old-location.bin")
        self.original_live = str(self.live)
        self.write_manifest()
        self.write_map([self.row(self.original_mapped, self.mapped_digest, "relocated/sample.bin")])

    def tearDown(self):
        self.temp.cleanup()

    def write_manifest(self, rows=None):
        rows = rows or [(self.mapped_digest, self.original_mapped), (self.live_digest, self.original_live)]
        self.manifest.write_text("".join(f"{digest}  {path}\n" for digest, path in rows))

    def row(self, original, digest, target):
        return {"original_path": original, "sha256": digest, "relocated_path": target}

    def write_map(self, rows):
        data = {
            "schema": "kpf18-native-relocations-v1",
            "manifest_sha256": hashlib.sha256(self.manifest.read_bytes()).hexdigest(),
            "relocations": rows,
        }
        self.map_path.write_text(json.dumps(data))

    def test_valid_relocation_and_unmapped_live_entry(self):
        self.assertEqual(verify(self.manifest, self.map_path), (2, 1))

    def test_tampered_relocated_bytes_fail(self):
        self.relocated.write_bytes(b"tampered")
        with self.assertRaisesRegex(VerificationError, "digest mismatch"):
            verify(self.manifest, self.map_path)

    def test_missing_relocated_bytes_fail(self):
        self.relocated.unlink()
        with self.assertRaisesRegex(VerificationError, "relocated source is missing"):
            verify(self.manifest, self.map_path)

    def test_duplicate_original_mapping_fails_closed(self):
        row = self.row(self.original_mapped, self.mapped_digest, "relocated/sample.bin")
        self.write_map([row, dict(row)])
        with self.assertRaisesRegex(VerificationError, "ambiguous duplicate mapping"):
            verify(self.manifest, self.map_path)

    def test_duplicate_target_mapping_fails_closed(self):
        self.write_map([
            self.row(self.original_mapped, self.mapped_digest, "relocated/sample.bin"),
            self.row(self.original_live, self.live_digest, "relocated/sample.bin"),
        ])
        with self.assertRaisesRegex(VerificationError, "ambiguous duplicate target"):
            verify(self.manifest, self.map_path)

    def test_unknown_original_mapping_fails_closed(self):
        self.write_map([self.row("not-in-manifest", self.mapped_digest, "relocated/sample.bin")])
        with self.assertRaisesRegex(VerificationError, "absent from manifest"):
            verify(self.manifest, self.map_path)

    def test_unmapped_missing_live_file_fails(self):
        self.live.unlink()
        with self.assertRaisesRegex(VerificationError, "unmapped original source is missing"):
            verify(self.manifest, self.map_path)

    def test_manifest_mutation_breaks_binding(self):
        self.manifest.write_text(self.manifest.read_text() + "0" * 64 + "  another.bin\n")
        with self.assertRaisesRegex(VerificationError, "different manifest digest"):
            verify(self.manifest, self.map_path)

    def test_target_traversal_fails_closed(self):
        self.write_map([self.row(self.original_mapped, self.mapped_digest, "relocated/../live.bin")])
        with self.assertRaisesRegex(VerificationError, "safe path"):
            verify(self.manifest, self.map_path)

    def test_noncanonical_dot_alias_fails_closed(self):
        self.write_map([self.row(self.original_mapped, self.mapped_digest, "relocated/./sample.bin")])
        with self.assertRaisesRegex(VerificationError, "not canonical"):
            verify(self.manifest, self.map_path)

    def test_symlink_aliases_to_same_target_fail_closed(self):
        alias = self.root / "relocated" / "alias.bin"
        alias.symlink_to(self.relocated)
        self.write_map([
            self.row(self.original_mapped, self.mapped_digest, "relocated/sample.bin"),
            self.row(self.original_live, self.live_digest, "relocated/alias.bin"),
        ])
        with self.assertRaisesRegex(VerificationError, "ambiguous aliased relocation targets"):
            verify(self.manifest, self.map_path)

    def test_symlink_escape_fails_closed(self):
        external_dir = tempfile.TemporaryDirectory()
        self.addCleanup(external_dir.cleanup)
        outside = Path(external_dir.name) / "outside.bin"
        outside.write_bytes(self.relocated.read_bytes())
        escape = self.root / "relocated" / "escape.bin"
        escape.symlink_to(outside)
        self.write_map([self.row(self.original_mapped, self.mapped_digest, "relocated/escape.bin")])
        with self.assertRaisesRegex(VerificationError, "escapes custody root"):
            verify(self.manifest, self.map_path)


if __name__ == "__main__":
    unittest.main()
