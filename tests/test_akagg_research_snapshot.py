"""akagg_research_snapshot: link-not-copy, verify, copy fallback. Temp dirs only."""
import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts", "system"))
import akagg_research_snapshot as ars  # noqa: E402
import scratch_release as sr  # noqa: E402


class T(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.t = self._td.name
        self.addCleanup(self._td.cleanup)
        self.src = os.path.join(self.t, "src")
        os.makedirs(os.path.join(self.src, "d"))
        for rel, data in (("d/a.py", b"a" * 5000), ("b.md", b"b\n")):
            open(os.path.join(self.src, rel), "wb").write(data)
        self.paths = ["owned-research/d/a.py", "owned-research/b.md"]
        self.store = os.path.join(self.t, "cas")
        self.sums = os.path.join(self.t, "SUMS")
        open(self.sums, "w").write("".join("%s  %s\n" % (sr.sha256(os.path.join(self.src, p[len("owned-research/"):])), p)
                                           for p in self.paths))

    def packet(self, name):
        d = os.path.join(self.t, name)
        os.makedirs(d)
        json.dump(self.paths, open(os.path.join(d, "RESEARCH-SNAPSHOT-PATHS.json"), "w"))
        return d

    def test_second_version_hardlinks_and_verifies(self):
        p1, p2 = self.packet("v1"), self.packet("v2")
        self.assertEqual(ars.materialise(p1, self.src, self.sums, self.store), 0)
        # v2 has no source at all: store-only link from the predecessor's sums
        self.assertEqual(ars.materialise(p2, None, self.sums, self.store), 0)
        a = os.stat(os.path.join(p1, "owned-research/d/a.py"))
        b = os.stat(os.path.join(p2, "owned-research/d/a.py"))
        self.assertEqual(a.st_ino, b.st_ino)
        self.assertGreaterEqual(a.st_nlink, 3)

    def test_fallback_copy_on_sha_mismatch_is_logged_and_fails_verify(self):
        p = self.packet("v3")
        open(os.path.join(self.src, "b.md"), "w").write("tampered\n")   # src no longer matches pinned sums
        log = os.path.join(self.t, "log")
        self.assertEqual(ars.materialise(p, self.src, self.sums, self.store, log), 1)
        self.assertIn("FALLBACK to copy", open(log).read())

    def test_fallback_copy_succeeds_when_link_fails(self):
        p = self.packet("v4")
        log = os.path.join(self.t, "log")
        orig = sr.link_snapshot
        sr.link_snapshot = lambda *a, **k: (_ for _ in ()).throw(OSError("boom"))
        try:
            self.assertEqual(ars.materialise(p, self.src, self.sums, self.store, log), 0)
        finally:
            sr.link_snapshot = orig
        self.assertIn("FALLBACK to copy", open(log).read())
        self.assertEqual(os.stat(os.path.join(p, "owned-research/b.md")).st_nlink, 1)

    def test_store_only_without_store_entry_fails(self):
        p = self.packet("v5")
        self.assertEqual(ars.materialise(p, None, self.sums, self.store), 1)


if __name__ == "__main__":
    unittest.main()
