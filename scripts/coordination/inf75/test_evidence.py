import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from evidence import EvidenceError, verify_bundle

P, C = "a" * 40, "b" * 40


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.files = {}
        for role in ("census", "footprint", "source_patch", "anchor_profile", "candidate_profile"):
            self.put(role, role.encode())
        self.put("normalized", json.dumps({"footprint": {"sha256": self.files["footprint"]["sha256"]},
            "t1": {"anchor_profile_sha256": self.files["anchor_profile"]["sha256"],
                   "candidate_profile_sha256": self.files["candidate_profile"]["sha256"]}}).encode())
        self.seal()

    def put(self, role, data):
        (self.root / role).write_bytes(data)
        self.files[role] = {"path": role, "sha256": hashlib.sha256(data).hexdigest()}

    def seal(self):
        raw = json.dumps({"schema": "epyc.inf75.evidence_binding.v1", "parent": P,
                          "candidate": C, "files": self.files}).encode()
        self.path = self.root / "manifest.json"
        self.path.write_bytes(raw)
        self.digest = hashlib.sha256(raw).hexdigest()

    def verify(self, **kwargs):
        return verify_bundle(self.path, expected_manifest_sha256=kwargs.get("digest", self.digest),
                             expected_parent=kwargs.get("parent", P), expected_candidate=C)

    def test_bound_bundle_is_byte_custody_only(self):
        receipt = self.verify()
        self.assertEqual(receipt["status"], "BYTE_BINDING_ONLY")
        self.assertNotIn("verified", receipt)

    def test_mismatch_is_refused(self):
        with self.assertRaises(EvidenceError): self.verify(parent="c" * 40)
        with self.assertRaises(EvidenceError): self.verify(digest="d" * 64)
        (self.root / "footprint").write_text("tampered")
        with self.assertRaises(EvidenceError): self.verify()

    def test_unbound_normalization_and_path_escape_are_refused(self):
        self.put("normalized", b'{"footprint":{"sha256":"wrong"},"t1":{}}')
        self.seal()
        with self.assertRaises(EvidenceError): self.verify()
        self.files["census"]["path"] = "../outside"
        self.seal()
        with self.assertRaises((EvidenceError, FileNotFoundError)): self.verify()


if __name__ == "__main__":
    unittest.main()
