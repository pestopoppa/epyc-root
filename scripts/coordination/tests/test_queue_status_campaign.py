"""queue_status.campaign_status reads the AK loop's campaign-status payloads, read-only, fail visible."""
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", ".claude", "skills", "inference-backlog-scheduling", "scripts"))
import queue_status as qs  # noqa: E402


def put(flags, name, text):
    d = os.path.join(flags, "campaign-status")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, name), "w") as f:
        f.write(text if isinstance(text, str) else json.dumps(text))


GOOD = {"schema": qs.CAMPAIGN_STATUS_SCHEMA, "row_id": "r1", "as_of": 1000,
        "rows": ["r1: running 1h00m, ETA 0h30m, heartbeat 0h01m ago"],
        "idle_bins": [{"bin": "gpu", "idle_s": 1200, "reason": "no ready row", "backlog_rows": ["x"]}],
        "escalations": [{"id": "e", "decision": "Accept +0.2% PPL?", "text": ""}],
        "decision_package": {"decided_by": "operator", "items": [{"topic": "t"}]}}


class T(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.f = self.td.name

    def test_absent_dir_is_empty(self):
        self.assertEqual(qs.campaign_status(self.f, 2000), {"campaigns": [], "bad": []})

    def test_reads_fresh_and_stale_and_bad(self):
        put(self.f, "r1.json", GOOD)
        put(self.f, "old.json", {**GOOD, "row_id": "old", "as_of": 1000 - 10 * 3600})
        put(self.f, "junk.json", "{not json")
        put(self.f, "other.json", {"schema": "x"})
        r = qs.campaign_status(self.f, 2000)
        by = {c["row_id"]: c for c in r["campaigns"]}
        self.assertFalse(by["r1"]["stale"])
        self.assertTrue(by["old"]["stale"])
        self.assertEqual(sorted(b["file"] for b in r["bad"]), ["junk.json", "other.json"])
        self.assertEqual(by["r1"]["escalations"][0]["decision"], "Accept +0.2% PPL?")

    def test_missing_as_of_is_stale(self):
        put(self.f, "r1.json", {k: v for k, v in GOOD.items() if k != "as_of"})
        self.assertTrue(qs.campaign_status(self.f, 2000)["campaigns"][0]["stale"])

    def test_read_only_and_json_and_text_surface(self):
        put(self.f, "r1.json", GOOD)
        before = sorted(os.listdir(os.path.join(self.f, "campaign-status")))
        for argv in (["--flags", self.f], ["--flags", self.f, "--json"]):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                self.assertEqual(qs.main(argv), 0)
            out = buf.getvalue()
            self.assertIn("r1", out)
            self.assertIn("Accept +0.2% PPL?", out)
        self.assertEqual(sorted(os.listdir(os.path.join(self.f, "campaign-status"))), before)


if __name__ == "__main__":
    unittest.main()
