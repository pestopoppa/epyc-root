import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from evidence import EvidenceError, verify_bundle

class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        def git(*args):
            return subprocess.run(["git", "-C", str(self.repo), *args], check=True,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout
        self.git = git
        git("init", "-q")
        git("config", "user.email", "test@example.invalid")
        git("config", "user.name", "test")
        (self.repo / "file").write_text("old\n")
        git("add", "file")
        git("commit", "-qm", "parent")
        self.parent = git("rev-parse", "HEAD").decode().strip()
        (self.repo / "file").write_text("new\n")
        git("commit", "-qam", "candidate")
        self.candidate = git("rev-parse", "HEAD").decode().strip()
        self.files = {}
        for role in ("census", "footprint", "source_patch", "anchor_profile", "candidate_profile"):
            self.put(role, role.encode())
        self.put("source_patch", git("-c", "core.abbrev=10", "diff", "--binary", self.parent, self.candidate))
        self.put("normalized", json.dumps({"footprint": {"sha256": self.files["footprint"]["sha256"]},
            "t1": {"anchor_profile_sha256": self.files["anchor_profile"]["sha256"],
                   "candidate_profile_sha256": self.files["candidate_profile"]["sha256"]}}).encode())
        self.seal()

    def put(self, role, data):
        (self.root / role).write_bytes(data)
        self.files[role] = {"path": role, "sha256": hashlib.sha256(data).hexdigest()}

    def seal(self):
        raw = json.dumps({"schema": "epyc.inf75.evidence_binding.v1", "parent": self.parent,
                          "candidate": self.candidate, "files": self.files}).encode()
        self.path = self.root / "manifest.json"
        self.path.write_bytes(raw)
        self.digest = hashlib.sha256(raw).hexdigest()

    def verify(self, **kwargs):
        return verify_bundle(self.path, expected_manifest_sha256=kwargs.get("digest", self.digest),
                             expected_parent=kwargs.get("parent", self.parent),
                             expected_candidate=self.candidate, source_repo=self.repo)

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

    def test_sealed_patch_from_wrong_source_is_refused(self):
        self.put("source_patch", b"wrong but correctly hashed")
        self.seal()
        with self.assertRaises(EvidenceError): self.verify()


if __name__ == "__main__":
    unittest.main()
