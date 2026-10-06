"""Read-depth gate (2026-10-06): dive-verified needs read_depth FULL|PARTIAL + anchors, forward-only."""
import copy
import importlib.util
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location(
    "validate_intake", Path(__file__).resolve().parents[1] / "validate_intake.py")
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)

BASE = {
    "id": "intake-9999", "arxiv_id": None, "url": "https://example.org/x", "source_type": "blog",
    "title": "T", "categories": ["agent_architecture"], "novelty": "low", "relevance": "low",
    "discovered_via": "test", "verdict": "not_applicable", "ingested_date": "2026-09-01",
    "verification": "dive-verified",
}
CATS = {"agent_architecture"}


def errs(**kw):
    e = copy.deepcopy(BASE)
    e.update(kw)
    return [x for x in validator.validate_index([e], CATS) if "read_depth" in x or "claim_anchors" in x]


class ReadDepthGate(unittest.TestCase):
    def test_new_entry_without_anchors_fails(self):
        self.assertTrue(errs(ingested_date="2026-10-07", read_depth="FULL"))

    def test_new_entry_without_read_depth_fails(self):
        self.assertTrue(errs(ingested_date="2026-10-07", claim_anchors=[{"claim_index": 1}]))

    def test_digest_fails(self):
        self.assertTrue(errs(read_depth="DIGEST", claim_anchors=[{"claim_index": 1}]))

    def test_legacy_without_anchors_passes(self):
        self.assertEqual(errs(), [])


if __name__ == "__main__":
    unittest.main()
