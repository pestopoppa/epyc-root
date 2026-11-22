"""Bandwidth census panel on /loop: tables, absence, event-based staleness."""
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from dashboard import bw_census, panels  # noqa: E402
from dashboard import server as S  # noqa: E402

FIXTURE = {
    "schema": "x", "floor_gbps": 1000, "target_gbps": 1200, "ceiling_gbps": 1500,
    "cpu": {"flag_frac": 0.75, "target_frac": 0.8,
            "ceiling_gbps": {"half-48t": 259.8}, "ceiling_source": {}},
    "records": {
        "g1": {"model": "27b", "kernel_class": "attn_q", "shape": "a", "n": 1, "gbps": 900.0,
               "recoverable_ms_per_round": 0.5, "status": "open_surface", "seed": "S1",
               "source_row": "ak-r1", "measured_at": "2026-11-22T00:00:00Z",
               "history": [["r0", 800], ["r1", 900]]},
        "g2": {"model": "27b", "kernel_class": "ffn", "gbps": 1100.0,
               "recoverable_ms_per_round": 2.0, "status": "ok", "share_of_round": None},
        "c1": {"device": "cpu", "config": "half-48t", "model": "35b", "kernel_class": "mm",
               "gbps": 130.0, "recoverable_ms_per_round": 1.0, "status": "stale",
               "frac_of_ceiling": 0.5, "ceiling_gbps": 259.8},
    },
    "seeds": {}, "seed_stubs": [], "applied": [{"row": "ak-r1", "sha256": "0"}],
}


class CensusTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        d = Path(self.tmp.name)
        self.census = d / "census.json"
        self.grants = d / "grants"
        self.grants.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self, mtime):
        self.census.write_text(json.dumps(FIXTURE))
        os.utime(self.census, (mtime, mtime))

    def _ended(self, name, mtime):
        p = self.grants / f"{name}.ended"
        p.write_text("")
        os.utime(p, (mtime, mtime))

    def test_both_tables_render_sorted(self):
        now = time.time()
        self._write(now - 60)
        d = S.bw_census_payload(self.census, self.grants, now=now)
        self.assertTrue(d["present"])
        mi = d["tables"]["mi210"]
        self.assertEqual([r["id"] for r in mi], ["g2", "g1"])  # recoverable ms desc
        self.assertEqual(mi[1]["gap_gbps"], -100.0)
        self.assertEqual(mi[1]["ceiling_gbps"], 1500)
        self.assertAlmostEqual(mi[1]["frac_of_ceiling"], 0.6)
        self.assertTrue(mi[1]["trend"].endswith("↑"))
        self.assertIsNone(mi[0]["share_of_round"])
        cpu = d["tables"]["cpu"]
        self.assertEqual(len(cpu), 1)
        self.assertEqual(cpu[0]["ceiling_gbps"], 259.8)
        self.assertEqual(d["_freshness"]["staleness_class"], "fresh")
        self.assertEqual(panels.panel_verdict(d["_freshness"])[0], "ok")

    def test_absent_file_reads_absent(self):
        d = S.bw_census_payload(self.census, self.grants)
        self.assertFalse(d["present"])
        env = d["_freshness"]
        self.assertEqual(env["reporting"], "absent")
        self.assertIn("absence_means", env)
        self.assertEqual(panels.panel_verdict(env)[0], "absent")

    def test_event_staleness_ak_rows_only(self):
        now = time.time()
        self._write(now - 600)
        self._ended("ak-old-row", now - 900)       # before census: ignored
        self._ended("q38-other-row", now - 60)     # not AK: ignored
        d = S.bw_census_payload(self.census, self.grants, now=now)
        self.assertFalse(d["event_stale"])
        self.assertEqual(d["_freshness"]["staleness_class"], "fresh")
        self._ended("akc-new-row", now - 30)       # AK row after census
        d = S.bw_census_payload(self.census, self.grants, now=now)
        self.assertTrue(d["event_stale"])
        self.assertEqual(d["ak_rows_ended_after_census"][0]["row"], "akc-new-row")
        env = d["_freshness"]
        self.assertEqual(env["staleness_class"], "stale")
        self.assertEqual(panels.panel_verdict(env)[0], "degraded")

    def test_registered_and_on_loop_page(self):
        self.assertEqual(panels.source("bw_census").route, "/api/bw_census")
        self.assertIn("/api/bw_census", S.API_ROUTES)
        self.assertIn("/api/bw_census/health", S.PANEL_HEALTH_ROUTES)
        self.assertFalse(any(panels.registry_gaps(S).values()))
        page = (REPO / "dashboard/static/loop.html").read_text()
        for needle in ('id="bwc-sec"', "/api/bw_census", "MI210", "Zen 5 EPYC 9655"):
            self.assertIn(needle, page)

    def test_trend(self):
        self.assertEqual(bw_census.trend(None), "")
        self.assertTrue(bw_census.trend([["a", 2], ["b", 1]]).endswith("↓"))


if __name__ == "__main__":
    unittest.main()
