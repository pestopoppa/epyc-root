"""KT-3: the read-only claim browser over the vidya ledger.

Fixture frames are copied in SHAPE from the canonical ledger (claim_proposed,
evidence_supports_claim with an applicability build_sha on the source,
retraction of an evidence frame). An absent ledger is ABSENT — no counts.
"""
import json
import os
import tempfile
import unittest
from pathlib import Path

from dashboard import knowledge, server


def _frame(seq, ftype, assertion, created="2026-10-24T09:14:57Z", fid=None):
    return {"frame": {"assertion": assertion, "frame_id": fid or f"sha256:{seq:064x}",
                      "frame_type": f"epyc.vidya/frame/{ftype}/v1",
                      "provenance": {"method": "vidya.adapters.test/v1"},
                      "pubinfo": {"actor": "vidya.adapters.test/v1", "authority_scope": "measurement",
                                  "created_at": created}, "signatures": []},
            "frame_hash": "sha256:x", "prev_hash": "sha256:y", "seq": seq}


FRAMES = [
    _frame(0, "source_observed", {"source_id": "src_a", "source_kind": "np-ctx-kvu-measurement",
                                  "locator": "/mnt/raid0/llm/tmp/x/results.jsonl", "revision_observed": "2026-10-24",
                                  "title": "run a", "applicability": {"build_sha": "ffc1bac82"}}),
    _frame(1, "claim_proposed", {"claim_id": "clm_a", "display_text": "prefill = 115.8 tok/s", "source_id": "src_a"}),
    _frame(2, "evidence_supports_claim", {"claim_id": "clm_a", "evidence_id": "evd_a", "source_id": "src_a",
                                          "grade": {"Q": "Judged", "T": "Located"}, "metric": "prefill_tps_median",
                                          "value": "115.8", "unit": "tok/s"}, fid="sha256:evd"),
    _frame(3, "claim_proposed", {"claim_id": "clm_b", "display_text": "no evidence yet", "source_id": "src_missing"},
           created="2026-10-25T00:00:00Z"),
    _frame(4, "retraction", {"retracts": "sha256:evd", "reason": "read-depth correction"}),
]


class KnowledgeBrowserTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ledger = Path(self.tmp.name) / "ledger.jsonl"
        self.ledger.write_text("".join(json.dumps(f) + "\n" for f in FRAMES) + "not json\n")
        self._old = os.environ.get("VIDYA_LEDGER")
        os.environ["VIDYA_LEDGER"] = str(self.ledger)

    def tearDown(self):
        if self._old is None:
            os.environ.pop("VIDYA_LEDGER", None)
        else:
            os.environ["VIDYA_LEDGER"] = self._old
        self.tmp.cleanup()

    def test_index_and_summary(self):
        data = server.knowledge_payload()
        self.assertEqual(data["n_claims"], 2)
        self.assertEqual(data["claims"][0]["id"], "clm_b")  # newest first
        a = next(c for c in data["claims"] if c["id"] == "clm_a")
        self.assertEqual((a["s"], a["o"], a["r"], a["q"], a["k"]), (1, 0, 1, "Judged", "np-ctx-kvu-measurement"))
        self.assertIn("1 malformed", data["_freshness"]["detail"])

    def test_chain_claim_evidence_run_commit(self):
        status, d = server.knowledge_claim_payload("clm_a")
        self.assertEqual(status, 200)
        self.assertEqual(d["evidence"][0]["assertion"]["evidence_id"], "evd_a")
        self.assertEqual(d["run"]["assertion"]["source_kind"], "np-ctx-kvu-measurement")
        self.assertEqual(d["commits"], [{"field": "applicability.build_sha", "value": "ffc1bac82"}])
        self.assertEqual(d["retractions"][0]["reason"], "read-depth correction")

    def test_no_commit_is_not_invented(self):
        status, d = server.knowledge_claim_payload("clm_b")
        self.assertEqual(status, 200)
        self.assertEqual((d["commits"], d["run"], d["evidence"]), ([], None, []))

    def test_unknown_claim_is_404(self):
        self.assertEqual(server.knowledge_claim_payload("clm_nope")[0], 404)

    def test_absent_ledger_renders_absent_without_counts(self):
        os.environ["VIDYA_LEDGER"] = str(Path(self.tmp.name) / "missing.jsonl")
        data = server.knowledge_payload()
        self.assertIsNone(data["claims"])
        self.assertIsNone(data["counts"])
        self.assertEqual(data["_freshness"]["reporting"], "absent")
        self.assertEqual(server.knowledge_claim_payload("clm_a")[0], 404)

    def test_read_only(self):
        before = self.ledger.read_bytes()
        server.knowledge_payload(); server.knowledge_claim_payload("clm_a")
        self.assertEqual(self.ledger.read_bytes(), before)
        self.assertFalse(hasattr(knowledge, "write"))


if __name__ == "__main__":
    unittest.main()
