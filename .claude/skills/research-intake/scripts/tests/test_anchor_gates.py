"""ID-RI-ANCHOR-GATE and ID-RI-LANE-HEAD frozen controls, each with a predeclared verdict."""
import hashlib
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("validate_intake", HERE / "validate_intake.py")
v = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(v)
sys.path.insert(0, str(v.ROOT / "scripts" / "vidya"))
import machine_anchor as ma  # noqa: E402
from canonical import normalized_quote  # noqa: E402
from raw_anchor_store import store_raw_bytes  # noqa: E402

SOURCE = ("Introduction. " + "Filler sentence about nothing at all. " * 12 +
          "The ablation removes the critic and accuracy falls from 61.8 to 43.8 on FrontierCS. " +
          "Closing remarks follow here. " + "More filler text to pass the length floor. " * 5)
URL = "https://example.org/paper-a"


def sha(q):
    return hashlib.sha256(normalized_quote(q).encode()).hexdigest()


class AnchorGate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.art = store_raw_bytes(SOURCE.encode(), {
            "entry_url": URL, "requested_url": URL, "effective_url": URL,
            "retrieved_at_utc": "2026-11-07T00:00:00Z", "media_type": "text/plain",
            "extractor_id": ma.EXTRACTOR_ID, "extractor_sha256": ma._extractor_sha256(),
        }, root=Path(cls.tmp.name))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def entry(self, eid, quote, url=URL, qsha=None):
        return {"id": eid, "url": url, "ingested_date": "2026-11-08", "verification": "dive-verified",
                "claim_anchors": [{"claim_index": 0, "quote": quote, "quote_sha256": qsha or sha(quote),
                                   "source_revision": URL, "source_artifact": self.art}]}

    def run_anchors(self, entries):
        import os
        old = os.environ.get("EPYC_VIDYA_RAW_ANCHOR_ROOT")
        os.environ["EPYC_VIDYA_RAW_ANCHOR_ROOT"] = self.tmp.name
        try:
            return v.check_anchors(entries)
        finally:
            if old is None:
                os.environ.pop("EPYC_VIDYA_RAW_ANCHOR_ROOT")
            else:
                os.environ["EPYC_VIDYA_RAW_ANCHOR_ROOT"] = old

    VERBATIM = "accuracy falls from 61.8 to 43.8 on FrontierCS"

    def test_verbatim_verified_with_mark(self):
        f, errs = self.run_anchors([self.entry("intake-1", self.VERBATIM)])
        self.assertEqual(f[0]["verdict"], "verified")
        self.assertEqual(errs, [])
        self.assertEqual(f[0]["anchor_mark"]["found"], True)
        self.assertEqual(f[0]["anchor_mark"]["source_raw_sha256"], self.art["raw_sha256"])

    def test_fabricated_quote_flagged(self):
        q = "accuracy rises from 43.8 to 99.9 on FrontierCS"
        f, errs = self.run_anchors([self.entry("intake-2", q)])
        self.assertEqual(f[0]["verdict"], "quote_not_found")
        self.assertTrue(errs)
        self.assertFalse(f[0]["anchor_mark"]["found"])

    def test_whitespace_altered_quote_not_refound(self):
        q = "accuracy falls  from 61.8\nto 43.8 on FrontierCS"
        f, errs = self.run_anchors([self.entry("intake-3", q)])
        self.assertEqual(f[0]["verdict"], "quote_not_found")  # hash is normalised, re-find is exact
        self.assertTrue(errs)

    def test_same_quote_under_two_entries_flagged(self):
        f, errs = self.run_anchors([self.entry("intake-4", self.VERBATIM),
                                    self.entry("intake-5", self.VERBATIM, url="https://example.org/other")])
        self.assertEqual({x["verdict"] for x in f}, {"cross_pasted"})
        self.assertEqual(len(errs), 2)

    def test_wrong_hash_flagged(self):
        f, _ = self.run_anchors([self.entry("intake-6", self.VERBATIM, qsha="0" * 64)])
        self.assertEqual(f[0]["verdict"], "quote_sha_mismatch")

    def test_new_dive_verified_without_mark_fails_legacy_passes(self):
        base = {"id": "intake-9999", "arxiv_id": None, "url": "https://example.org/x", "source_type": "blog",
                "title": "T", "categories": ["agent_architecture"], "novelty": "low", "relevance": "low",
                "discovered_via": "test", "verdict": "not_applicable", "verification": "dive-verified",
                "read_depth": "FULL", "claim_anchors": [{"claim_index": 0, "quote": "q"}]}

        def errs(date, anchors=None):
            e = dict(base, ingested_date=date)
            if anchors is not None:
                e["claim_anchors"] = anchors
            return [x for x in v.validate_index([e], {"agent_architecture"}) if "anchor_mark" in x]
        self.assertTrue(errs("2026-11-08"))
        self.assertEqual(errs("2026-11-06"), [])
        self.assertEqual(errs("2026-11-08", [{"claim_index": 0, "quote": "q",
                                              "anchor_mark": {"found": True}}]), [])

    def test_forged_mark_rejected(self):
        e = self.entry("intake-7", "never in source at all")
        e["claim_anchors"][0]["anchor_mark"] = {"verifier": v.ANCHOR_VERIFIER_ID,
                                                "source_raw_sha256": self.art["raw_sha256"], "found": True}
        f, _ = self.run_anchors([e])
        self.assertTrue(v.check_anchor_marks([e], f))

    def test_source_absent_from_root_writes_no_mark(self):
        import os
        e = self.entry("intake-9", self.VERBATIM)
        old = os.environ.get("EPYC_VIDYA_RAW_ANCHOR_ROOT")
        with tempfile.TemporaryDirectory() as other:
            os.environ["EPYC_VIDYA_RAW_ANCHOR_ROOT"] = other
            try:
                f, _ = v.check_anchors([e])
            finally:
                if old is None:
                    os.environ.pop("EPYC_VIDYA_RAW_ANCHOR_ROOT")
                else:
                    os.environ["EPYC_VIDYA_RAW_ANCHOR_ROOT"] = old
        self.assertEqual(f[0]["verdict"], "source_unavailable")
        self.assertIsNone(f[0]["anchor_mark"])

    def test_write_marks_textual(self):
        f, _ = self.run_anchors([self.entry("intake-8", self.VERBATIM)])
        f[0]["quote_sha256"] = sha(self.VERBATIM)
        idx = Path(self.tmp.name) / "idx.yaml"
        idx.write_text(f"- id: intake-8\n  claim_anchors:\n  - quote_sha256: {sha(self.VERBATIM)}\n    quote: x\n")
        self.assertEqual(v.write_anchor_marks(idx, f), 1)
        import yaml
        got = yaml.safe_load(idx.read_text())[0]["claim_anchors"][0]
        self.assertTrue(got["anchor_mark"]["found"])


def git(root, *a):
    return subprocess.run(["git", "-C", str(root), *a], capture_output=True, text=True, check=True).stdout.strip()


class LaneHead(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        r = cls.root = Path(cls.tmp.name)
        git(r, "init", "-q")
        git(r, "config", "user.email", "t@t")
        git(r, "config", "user.name", "t")
        (r / "changed.md").write_text("alpha line\nthe pinned fact lives here\n")
        (r / "moved.md").write_text("beta line\nmoved fact is here\n")
        (r / "same.md").write_text("gamma line\nstable fact is here\n")
        git(r, "add", "-A")
        git(r, "commit", "-qm", "c1")
        cls.sha7 = git(r, "rev-parse", "--short=7", "HEAD")
        (r / "changed.md").write_text("alpha line\nthe pinned fact lives here\nappended later\n")
        git(r, "mv", "moved.md", "renamed.md")
        git(r, "add", "-A")
        git(r, "commit", "-qm", "c2")
        git(r, "update-ref", "refs/remotes/origin/main", "HEAD")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def verdict(self, path, quote, sha7=None):
        e = {"id": "intake-1", "claim_anchors": [{"locator": f"{path}:L2 @ {sha7 or self.sha7}", "quote": quote}]}
        out = v.check_lane_anchors([e], root=self.root)
        self.assertEqual(len(out), 1)
        return out[0]["verdict"]

    def test_stale_anchor_at_changed_file(self):
        self.assertEqual(self.verdict("changed.md", "the pinned fact lives here"), "stale_epoch")

    def test_moved_path(self):
        self.assertEqual(self.verdict("moved.md", "moved fact is here"), "stale_epoch")

    def test_unchanged_path_not_stale(self):
        self.assertEqual(self.verdict("same.md", "stable fact is here"), "ok")

    def test_fabricated_quote_at_sha(self):
        self.assertEqual(self.verdict("same.md", "never written"), "quote_not_at_sha")

    def test_elided_quote_ok(self):
        self.assertEqual(self.verdict("same.md", "gamma line ... stable fact"), "ok")

    def test_foreign_sha_skipped(self):
        e = {"id": "i", "claim_anchors": [{"locator": "a/b.py:L1 @ deadbee", "quote": "x"}]}
        self.assertEqual(v.check_lane_anchors([e], root=self.root), [])

    def test_preflight(self):
        spec = importlib.util.spec_from_file_location("dive_preflight", HERE / "dive_preflight.py")
        pf = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(pf)
        ok, reason, _ = pf.preflight(self.root)
        self.assertEqual((ok, reason), (False, "shared_clone_not_lane_worktree"))


if __name__ == "__main__":
    unittest.main()
