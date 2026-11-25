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
    "schema": "x", "floor_gbps": 1000, "target_gbps": 1200, "ceiling_gbps": 1638,
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

    def test_lanes_sort_served_then_candidate_then_not_served(self):
        doc = {"records": {
            "ns": {"model": "27b", "kernel_class": "vk_dense_q8wv", "gbps": 400.0, "recoverable_ms_per_round": 9.0, "lane": "not_served"},
            "ca": {"model": "a3b", "kernel_class": "router", "gbps": 18.0, "recoverable_ms_per_round": 5.0, "lane": "candidate"},
            "sv": {"model": "27b", "kernel_class": "ffn", "gbps": 1100.0, "recoverable_ms_per_round": 1.0}}}
        mi = bw_census.shape_rows(doc)["mi210"]
        self.assertEqual([(r["id"], r["lane"]) for r in mi], [("sv", "served"), ("ca", "candidate"), ("ns", "not_served")])

    def test_both_tables_render_sorted(self):
        now = time.time()
        self._write(now - 60)
        d = S.bw_census_payload(self.census, self.grants, now=now)
        self.assertTrue(d["present"])
        mi = d["tables"]["mi210"]
        self.assertEqual([r["id"] for r in mi], ["g2", "g1"])  # recoverable ms desc
        self.assertEqual(mi[1]["gap_gbps"], -100.0)
        self.assertEqual(mi[1]["ceiling_gbps"], 1638)
        self.assertAlmostEqual(mi[1]["frac_of_ceiling"], 900 / 1638, places=4)
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
        for needle in ('id="bwc-sec"', "/api/bw_census", "MI210", "CPU", 'id="bwc-surfaces"', "bwcSurfaces", "saving ms/step"):
            self.assertIn(needle, page)

    def test_parity_table_and_batch_block(self):
        doc = {**FIXTURE, "parity": {
            "note": "n", "refs": {
                "m": {"pct": 88, "status": "measured", "cite": "c1", "basis": "b"},
                "r": {"pct": 85, "cite": "c2", "basis": "b"}},
            "batch_dependence": {"note": "bn", "source": "src",
                                 "rows": [{"kernel": "k", "pct": "85-89", "batch": ">=8"}]},
            "ops": [
                {"op": "a", "ref": "m", "ours_gbps": 819.2, "roofline_gbps": 1638.4, "share_of_step": 0.1,
                 "served": True, "covered_by": "", "refresh_c21": True, "path": "p"},
                {"op": "b", "ref": "r", "ours_pct": 35, "share_of_step": 0.5, "served": True,
                 "covered_by": "box", "refresh_c21": False, "path": "p"},
                {"op": "c", "ref": "m", "ours_pct": 99, "share_of_step": 0.9, "served": False, "path": "p"}]}}
        self.census.write_text(json.dumps(doc))
        d = S.bw_census_payload(self.census, self.grants)
        rows = d["parity"]["rows"]
        self.assertEqual([r["op"] for r in rows], ["b", "a", "c"])  # served first, score desc
        b, a, c = rows
        self.assertEqual((b["gap_pp"], b["score"], b["ref_status"]), (50.0, 25.0, "recalled, not re-verified"))
        self.assertEqual((a["ours_pct"], a["gap_pp"], a["score"], a["ref_status"]), (50.0, 38.0, 3.8, "measured"))
        self.assertEqual(a["ref_cite"], "c1")
        self.assertTrue(a["refresh_c21"])
        self.assertEqual(c["gap_pp"], 0.0)
        self.assertEqual(d["parity"]["batch_dependence"]["rows"][0]["pct"], "85-89")
        self.census.write_text(json.dumps(FIXTURE))   # no parity section -> null, panel still fine
        self.assertIsNone(S.bw_census_payload(self.census, self.grants)["parity"])

    def test_null_ref_pct_has_no_gap_or_score(self):
        doc = {**FIXTURE, "parity": {"note": "n", "refs": {"n": {"pct": None, "status": "no-published-measurement",
                                                                 "cite": "c", "bracket_pct": {"x": 80}}},
                                     "ops": [{"op": "a", "ref": "n", "ours_pct": 35, "share_of_step": 0.5,
                                              "served": True, "path": "p"}]}}
        self.census.write_text(json.dumps(doc))
        r = S.bw_census_payload(self.census, self.grants)["parity"]["rows"][0]
        self.assertEqual((r["ref_pct"], r["gap_pp"], r["score"], r["ref_bracket_pct"]), (None, None, None, {"x": 80}))
        page = (REPO / "dashboard/static/loop.html").read_text()
        self.assertIn("no published measurement", page)

    def test_parity_dom_on_page(self):
        page = (REPO / "dashboard/static/loop.html").read_text()
        for needle in ('id="bwc-batch"', "bwcBatch", "ref_status", "<b>none</b>", "unmeasured", "bwcRuns",
                       "ABSENT", "STALE", "target_pct", "quarter-24t", "full-host"):
            self.assertIn(needle, page)
        for gone in ('id="bwc-mi210"', 'id="bwc-cpu"', 'id="bwc-parity"'):  # the three old tables are replaced
            self.assertNotIn(gone, page)

    def test_surfaces_pass_through_ranked_with_runs(self):
        doc = {**FIXTURE, "target_pct": 88.0, "surface_groups": [{"op": "g", "unreconciled": True}], "surfaces": [
            {"path": "p", "op": "small", "device": "mi210", "saving_ms_per_step": 0.5, "ours_pct": 60.0,
             "ours_measured": True, "census_rows": ["g1"], "covered_by": None, "status": "open", "gap_pp": None},
            {"path": "p", "op": "unmeasured", "device": "mi210", "saving_ms_per_step": None, "ours_pct": None,
             "ours_measured": False, "census_rows": [], "covered_by": "box", "status": "needs_measurement"},
            {"path": "q", "op": "big", "device": "cpu-quarter-24t", "saving_ms_per_step": 7.5, "ours_pct": 15.0,
             "ours_measured": True, "census_rows": ["c1", "missing"], "covered_by": "", "status": "bogus"}]}
        doc["records"] = {k: dict(v, op="x") for k, v in FIXTURE["records"].items()}
        self.census.write_text(json.dumps(doc))
        d = S.bw_census_payload(self.census, self.grants)
        self.assertEqual(d["target_pct"], 88.0)
        self.assertTrue(d["surface_groups"][0]["unreconciled"])
        s = d["surfaces"]
        self.assertEqual([x["op"] for x in s], ["big", "small", "unmeasured"])  # saving desc, null last
        self.assertEqual(s[0]["status"], "open")       # unknown status is never drawn as covered/ok
        self.assertEqual([r["id"] for r in s[0]["runs"]], ["c1"])  # dangling id dropped
        self.assertEqual(s[0]["runs"][0]["pct_ceiling"], 50.0)
        self.assertEqual(s[1]["runs"][0]["source_row"], "ak-r1")
        self.assertEqual(s[1]["covered_by"], "")
        self.assertIsNone(s[1]["gap_pp"])               # null gap stays null
        self.assertEqual(d["tables"]["mi210"][0]["op"], "x")
        self.census.write_text(json.dumps(FIXTURE))      # pre-surfaces census still renders
        self.assertEqual(S.bw_census_payload(self.census, self.grants)["surfaces"], [])

    def test_stale_surface_marker_passes_through_and_renders(self):
        doc = {**FIXTURE, "surfaces": [
            {"path": "p", "op": "tail", "saving_ms_per_step": None, "census_rows": [], "status": "needs_measurement",
             "stale": True, "stale_since": "2026-11-24T10:00:00Z", "stale_row": "ak-x"},
            {"path": "p", "op": "fresh", "saving_ms_per_step": 1.0, "census_rows": [], "status": "open", "stale": "yes"}]}
        self.census.write_text(json.dumps(doc))
        s = {x["op"]: x for x in S.bw_census_payload(self.census, self.grants)["surfaces"]}
        self.assertEqual((s["tail"]["stale"], s["tail"]["stale_row"]), (True, "ak-x"))
        self.assertFalse(s["fresh"]["stale"])  # only a literal true is drawn as stale
        page = (REPO / "dashboard/static/loop.html").read_text()
        self.assertIn("r.stale?", page)
        self.assertIn("bwc-stale", page)

    def test_coverage_and_family_rank_pass_through(self):
        doc = {**FIXTURE, "coverage": {"status": "ok", "paths": {
            "a3b|mi210": {"status": "planned", "path": "a3b-mtp-mi210", "n": [1, 2], "uncovered_ops": ["x", "y"]},
            "27b|mi210": {"status": "live", "path": "27b-df2-mi210", "n": [1], "uncovered_ops": []}},
            "mismatch": [{"op": "o", "path": "ghost"}], "unmapped": []},
            "family_rank": [{"family": "b", "kind": "family", "score": None, "members": []},
                            {"family": "a", "kind": "family", "score": 1.5, "n_unpriced": 0, "members": [{"path": "p"}]},
                            {"family": "serving-knob:k", "kind": "knob", "score": None, "members": []}]}
        self.census.write_text(json.dumps(doc))
        d = S.bw_census_payload(self.census, self.grants)
        cov = d["coverage"]
        self.assertEqual([(p["path"], p["uncovered_count"], p["planned"]) for p in cov["paths"]],
                         [("27b-df2-mi210", 0, False), ("a3b-mtp-mi210", 2, True)])
        self.assertEqual((cov["uncovered_total"], len(cov["mismatch"])), (2, 1))
        fr = d["family_rank"]
        self.assertEqual([r["family"] for r in fr], ["a", "b", "serving-knob:k"])  # priced first, unpriced last
        self.assertEqual([r["status"] for r in fr], ["priced", "unpriced", "unpriced"])
        self.assertIsNone(fr[1]["score"])  # a null is never filled
        self.census.write_text(json.dumps({**FIXTURE, "coverage": {"status": "registry-unreadable"}}))
        d = S.bw_census_payload(self.census, self.grants)
        self.assertEqual((d["coverage"]["status"], d["coverage"]["paths"], d["family_rank"]), ("registry-unreadable", [], []))
        self.census.write_text(json.dumps(FIXTURE))  # a census that predates both keys
        d = S.bw_census_payload(self.census, self.grants)
        self.assertEqual((d["coverage"], d["family_rank"]), (None, []))
        page = (REPO / "dashboard/static/loop.html").read_text()
        for needle in ('id="bwc-coverage"', 'id="bwc-family"', "bwcCoverage", "bwcFamily", "uncovered_count", "planned, not yet served",
                       "Family rank", "Coverage unknown"):
            self.assertIn(needle, page)

    def test_coverage_status_defaults_to_unknown_never_ok(self):
        self.census.write_text(json.dumps({**FIXTURE, "coverage": {"paths": {}}}))   # producer wrote no status
        self.assertEqual(S.bw_census_payload(self.census, self.grants)["coverage"]["status"], "unknown")

    def test_inbox_state_is_read_from_the_hook_state_file(self):
        self.census.write_text(json.dumps(FIXTURE))
        inbox = self.census.parent / "inbox-state.json"
        d = S.bw_census_payload(self.census, self.grants)
        self.assertEqual(d["inbox"]["status"], "unknown")             # no record yet is never "ok"
        inbox.write_text(json.dumps({"at": 5.0, "row": "ak-x-20261124", "status": "error",
                                     "detail": "error rc=2 boom"}))
        i = S.bw_census_payload(self.census, self.grants)["inbox"]
        self.assertEqual((i["status"], i["row"], i["detail"]), ("error", "ak-x-20261124", "error rc=2 boom"))
        inbox.write_text(json.dumps({"status": "fine-ish"}))          # an unknown vocabulary value is not passed as ok
        self.assertEqual(S.bw_census_payload(self.census, self.grants)["inbox"]["status"], "unknown")
        inbox.write_text("{nope")
        self.assertEqual(S.bw_census_payload(self.census, self.grants)["inbox"]["status"], "unreadable")
        page = (REPO / "dashboard/static/loop.html").read_text()
        for needle in ("bwcInbox", "Census inbox step"):
            self.assertIn(needle, page)

    def test_event_stale_reason_names_the_event_not_the_mtime(self):
        now = time.time()
        self._write(now - 3600)
        self._ended("akx-late-row", now - 60)                        # akx-* rows count (defect 1 routes them to the hook)
        env = S.bw_census_payload(self.census, self.grants, now=now)["_freshness"]
        self.assertTrue(env["event_stale"])
        status, why = panels.panel_verdict(env)
        self.assertEqual(status, panels.STATUS_DEGRADED)
        self.assertIn("akx-late-row", why)
        self.assertIn("did not run at their row end", why)

    def test_trend(self):
        self.assertEqual(bw_census.trend(None), "")
        self.assertTrue(bw_census.trend([["a", 2], ["b", 1]]).endswith("↓"))


if __name__ == "__main__":
    unittest.main()
