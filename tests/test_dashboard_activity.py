"""Tests for the hub's today's-activity counters (dashboard/server.py).

Pure-function tests over ``_parse_activity_log`` — no git or HTTP needed. Also
covers the kernel-contract and autopilot-outcome-contract freshness/reader logic.
Run: ``python3 -m unittest tests.test_dashboard_activity``
"""
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dashboard import server


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


_NOW = datetime.now(timezone.utc)


SAMPLE = """\
commit:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
diff --git a/handoffs/active/foo.md b/handoffs/active/foo.md
index 1111111..2222222 100644
--- a/handoffs/active/foo.md
+++ b/handoffs/active/foo.md
@@ -1,4 +1,5 @@
-- [ ] port the kernel
+- [x] port the kernel ✅ 2026-07-05
+- [ ] validate on MI210
 narrative line that mentions [x] inline but is not a task
+Status: converged — prose only, no checkbox here
commit:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
diff --git a/handoffs/active/foo.md b/handoffs/active/foo.md
--- a/handoffs/active/foo.md
+++ b/handoffs/active/foo.md
@@ -10,2 +10,3 @@
+  * [X] nested star task, capital X
diff --git a/handoffs/completed/bar.md b/handoffs/completed/bar.md
--- a/handoffs/completed/bar.md
+++ b/handoffs/completed/bar.md
@@ -1 +1,2 @@
+prose appended to a completed handoff
"""


class ParseActivityLogTest(unittest.TestCase):
    def test_counts_commits_files_and_boxes(self):
        act = server._parse_activity_log(SAMPLE)
        self.assertEqual(act["commits"], 2)
        # foo.md counted once across two commits; bar.md once.
        self.assertEqual(act["handoffs_touched"], 2)
        # +[x] flip and +[X] nested star task; the +++ header and prose lines don't count.
        self.assertEqual(act["boxes_checked"], 2)
        self.assertEqual(act["boxes_added"], 1)

    def test_empty_log_is_all_zero(self):
        self.assertEqual(server._parse_activity_log(""), server._ACT_EMPTY)

    def test_prose_only_day_shows_zero_boxes(self):
        text = (
            "commit:cccccccccccccccccccccccccccccccccccccccc\n"
            "diff --git a/handoffs/active/foo.md b/handoffs/active/foo.md\n"
            "+Update (2026-07-05): W8 paired diagnostics recorded.\n"
        )
        act = server._parse_activity_log(text)
        self.assertEqual(act["commits"], 1)
        self.assertEqual(act["handoffs_touched"], 1)
        self.assertEqual(act["boxes_checked"], 0)
        self.assertEqual(act["boxes_added"], 0)

    def test_activity_today_live_shape(self):
        """Smoke the real git path: keys present, values non-negative ints."""
        act = server._activity_today()
        self.assertEqual(set(act), set(server._ACT_EMPTY))
        for v in act.values():
            self.assertIsInstance(v, int)
            self.assertGreaterEqual(v, 0)


DAY_SAMPLE = """\
commit:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa|2026-07-29
diff --git a/handoffs/active/foo.md b/handoffs/active/foo.md
+++ b/handoffs/active/foo.md
-- [ ] port the kernel
+- [x] port the kernel
+- [ ] validate on MI210
+- [ ] write the report
commit:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb|2026-07-28
diff --git a/handoffs/active/foo.md b/handoffs/active/foo.md
+- [x] older close
diff --git a/handoffs/active/bar.md b/handoffs/active/bar.md
+- [x] another close
commit:cccccccccccccccccccccccccccccccccccccccc|2026-07-20
diff --git a/handoffs/active/baz.md b/handoffs/active/baz.md
+- [ ] filed long ago
"""


class ParseActivityLogByDayTest(unittest.TestCase):
    """Per-day bucketing must reproduce the same counting rules as the
    single-number fold — it is the SAME git source, only bucketed."""

    def setUp(self):
        self.rows = server._parse_activity_log_by_day(DAY_SAMPLE)
        self.by_date = {r["date"]: r for r in self.rows}

    def test_newest_day_first(self):
        self.assertEqual([r["date"] for r in self.rows],
                         ["2026-07-29", "2026-07-28", "2026-07-20"])

    def test_per_day_counters(self):
        d = self.by_date["2026-07-29"]
        self.assertEqual(d["commits"], 1)
        self.assertEqual(d["boxes_checked"], 1)
        self.assertEqual(d["boxes_added"], 2)
        self.assertEqual(d["_touched"], {"handoffs/active/foo.md"})
        d = self.by_date["2026-07-28"]
        self.assertEqual(d["boxes_checked"], 2)
        self.assertEqual(d["boxes_added"], 0)
        self.assertEqual(len(d["_touched"]), 2)

    def test_empty_log(self):
        self.assertEqual(server._parse_activity_log_by_day(""), [])

    def test_lines_before_first_commit_are_ignored(self):
        self.assertEqual(server._parse_activity_log_by_day("+- [x] orphan"), [])


class ActivityRollupTest(unittest.TestCase):
    def setUp(self):
        self.rows = server._parse_activity_log_by_day(DAY_SAMPLE)

    def test_one_day_window_matches_today_only(self):
        r = server._activity_rollup(self.rows, 1, "2026-07-29")
        self.assertEqual(r["since"], "2026-07-29")
        self.assertEqual((r["boxes_checked"], r["boxes_added"]), (1, 2))

    def test_net_is_filed_minus_closed(self):
        r = server._activity_rollup(self.rows, 1, "2026-07-29")
        self.assertEqual(r["net"], 1)          # 2 filed − 1 closed: backlog grew
        r = server._activity_rollup(self.rows, 7, "2026-07-29")
        self.assertEqual((r["boxes_checked"], r["boxes_added"]), (3, 2))
        self.assertEqual(r["net"], -1)         # negative: backlog shrank

    def test_window_excludes_days_outside_it(self):
        r7 = server._activity_rollup(self.rows, 7, "2026-07-29")
        self.assertEqual(r7["commits"], 2)     # the 07-20 commit is out of range
        r14 = server._activity_rollup(self.rows, 14, "2026-07-29")
        self.assertEqual(r14["commits"], 3)
        self.assertEqual(r14["since"], "2026-07-16")

    def test_handoffs_touched_is_unioned_not_summed(self):
        # foo.md appears on both 07-29 and 07-28; bar.md only on 07-28.
        r = server._activity_rollup(self.rows, 7, "2026-07-29")
        self.assertEqual(r["handoffs_touched"], 2)

    def test_empty_rollup_is_zeroed(self):
        r = server._activity_rollup([], 7, "2026-07-29")
        self.assertEqual(
            (r["commits"], r["boxes_checked"], r["boxes_added"], r["net"]),
            (0, 0, 0, 0))


class ActivityWindowLiveTest(unittest.TestCase):
    """Smoke the real git path and lock the today-consistency invariant: the 1d
    roll-up is the SAME source as ``activity_today``, so their box counts agree."""

    def test_shape_and_rollups(self):
        w = server._activity_window()
        self.assertEqual(w["window_days"], server._ACT_WINDOW_DAYS)
        self.assertEqual(set(w["rollups"]),
                         {f"{n}d" for n in server._ACT_ROLLUPS})
        for r in w["rollups"].values():
            self.assertEqual(r["net"], r["boxes_added"] - r["boxes_checked"])
            for k in ("commits", "boxes_checked", "boxes_added", "handoffs_touched"):
                self.assertIsInstance(r[k], int)
                self.assertGreaterEqual(r[k], 0)

    def test_per_day_rows_have_no_internal_set(self):
        for row in server._activity_window()["per_day"]:
            self.assertNotIn("_touched", row)
            self.assertIsInstance(row["handoffs_touched"], int)
            self.assertEqual(row["net"], row["boxes_added"] - row["boxes_checked"])

    def test_one_day_rollup_agrees_with_activity_today(self):
        w = server._activity_window()
        today = server._activity_today()
        one = w["rollups"]["1d"]
        self.assertEqual(one["boxes_checked"], today["boxes_checked"])
        self.assertEqual(one["boxes_added"], today["boxes_added"])
        self.assertEqual(one["commits"], today["commits"])


class BoardPayloadFlowTest(unittest.TestCase):
    def test_board_exposes_both_ratios_and_flow(self):
        payload = server.board_payload(force=True)
        self.assertIn("activity_window", payload)
        self.assertIn("rollups", payload["activity_window"])
        # Both scopes must stay distinguishable — open scope vs all scope.
        bk = payload["backlog"]
        self.assertIn("pct_open_done", bk)
        self.assertIn("pct_all_done", bk)


class KernelFreshnessTests(unittest.TestCase):
    """Regression lock: the kernel badge classifies DATA recency (max runs[].ts),
    never the export-file / ``generated_at`` proxy (the audited 'fresh forever'
    bug after a 1-row cron re-export)."""

    def test_uses_run_ts_not_generated_at(self):
        # runs[].ts is OLD but the export ``generated_at`` is NOW: a file-mtime /
        # export-recency classifier would read fresh; the fix must read stale.
        data = {"generated_at": _iso(_NOW),
                "runs": [{"ts": _iso(_NOW - timedelta(days=30))}]}
        fr = server._kernel_contract_freshness(data)
        self.assertEqual(fr["staleness_class"], "stale")
        self.assertEqual(fr["source"], "runs[].ts")

    def test_fresh_run_ts_is_fresh_even_if_generated_at_old(self):
        data = {"generated_at": _iso(_NOW - timedelta(days=30)),
                "runs": [{"ts": _iso(_NOW - timedelta(hours=1))}]}
        self.assertEqual(server._kernel_contract_freshness(data)["staleness_class"], "fresh")

    def test_max_of_multiple_run_ts(self):
        data = {"runs": [{"ts": _iso(_NOW - timedelta(days=30))},
                         {"ts": _iso(_NOW - timedelta(days=1))}]}
        fr = server._kernel_contract_freshness(data)
        self.assertEqual(fr["staleness_class"], "fresh")  # 1d < 3d warn

    def test_falls_back_to_generated_at_without_runs(self):
        data = {"generated_at": _iso(_NOW - timedelta(days=30)), "runs": []}
        fr = server._kernel_contract_freshness(data)
        self.assertEqual(fr["staleness_class"], "stale")
        self.assertEqual(fr["source"], "generated_at")

    def test_missing_when_no_timestamps(self):
        fr = server._kernel_contract_freshness({"runs": []})
        self.assertEqual(fr["staleness_class"], "missing")


class OutcomeContractFreshnessTests(unittest.TestCase):
    """The autopilot outcome contract classifies on the export ``generated_at``
    (data recency), never file mtime — mirrors the kernel fix."""

    def test_fresh_generated_at(self):
        fr = server._outcome_contract_freshness({"generated_at": _iso(_NOW - timedelta(minutes=5))})
        self.assertEqual(fr["staleness_class"], "fresh")
        self.assertEqual(fr["source"], "generated_at")

    def test_aging_then_stale(self):
        aging = server._outcome_contract_freshness({"generated_at": _iso(_NOW - timedelta(hours=12))})
        self.assertEqual(aging["staleness_class"], "aging")
        stale = server._outcome_contract_freshness({"generated_at": _iso(_NOW - timedelta(days=5))})
        self.assertEqual(stale["staleness_class"], "stale")

    def test_missing_without_timestamp(self):
        fr = server._outcome_contract_freshness({"outcome_progress": {"status": "ok"}})
        self.assertEqual(fr["staleness_class"], "missing")
        self.assertIsNone(fr["age_s"])

    def test_ignores_file_mtime(self):
        # A file written NOW but carrying an OLD generated_at must read stale.
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "outcome.json"
            p.write_text(json.dumps({"generated_at": _iso(_NOW - timedelta(days=5)),
                                     "outcome_progress": {"status": "ok"}}))
            orig = server.AUTOPILOT_OUTCOME_JSON
            try:
                server.AUTOPILOT_OUTCOME_JSON = p
                out = server.outcome_payload()
            finally:
                server.AUTOPILOT_OUTCOME_JSON = orig
        self.assertEqual(out["_freshness"]["staleness_class"], "stale")


class OutcomeContractReaderTests(unittest.TestCase):
    """``_read_outcome_contract`` / ``outcome_payload`` degrade honestly on every
    bad-artifact shape and normalize both the wrapper and bare contract forms."""

    def _with_contract(self, content):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "outcome.json"
            if content is not None:
                p.write_text(content)
            orig = server.AUTOPILOT_OUTCOME_JSON
            try:
                server.AUTOPILOT_OUTCOME_JSON = p
                return server.outcome_payload()
            finally:
                server.AUTOPILOT_OUTCOME_JSON = orig

    def test_missing_file_is_honest_degraded(self):
        out = self._with_contract(None)
        self.assertIn("error", out)
        self.assertEqual(out["outcome_progress"]["status"], "missing")
        self.assertEqual(out["_freshness"]["staleness_class"], "missing")
        self.assertIn("observation_notice", out)

    def test_corrupt_json(self):
        out = self._with_contract("{not json")
        self.assertIn("error", out)
        self.assertEqual(out["outcome_progress"]["status"], "missing")

    def test_non_dict_json(self):
        out = self._with_contract("[]")
        self.assertIn("error", out)
        self.assertEqual(out["outcome_progress"]["status"], "missing")

    def test_wrapper_form_passthrough(self):
        payload = {"generated_at": _iso(_NOW), "outcome_progress":
                   {"status": "attention", "latest_trial_id": 1200,
                    "trials_since_frontier": 172, "max_trials_since_frontier": 150,
                    "blockers": ["frontier admission stale: 172 > 150"]}}
        out = self._with_contract(json.dumps(payload))
        self.assertNotIn("error", out)
        self.assertEqual(out["outcome_progress"]["latest_trial_id"], 1200)
        self.assertEqual(out["outcome_progress"]["trials_since_frontier"], 172)
        self.assertIn("observation_notice", out)  # backfilled if absent

    def test_bare_outcome_progress_is_wrapped(self):
        bare = {"status": "ok", "latest_trial_id": 5, "rates": {}, "blockers": []}
        out = self._with_contract(json.dumps(bare))
        self.assertNotIn("error", out)
        self.assertEqual(out["outcome_progress"]["latest_trial_id"], 5)

    def test_object_without_outcome_progress_is_error(self):
        out = self._with_contract(json.dumps({"unrelated": True}))
        self.assertIn("error", out)
        self.assertEqual(out["outcome_progress"]["status"], "missing")


class HealthPayloadTests(unittest.TestCase):
    """AK6 AMENDMENT (2026-08-03).

    This class used to assert that an outcome export 10 days stale left
    ``/api/health`` at ``ok``, on the reasoning that "a paused loop reads stale
    by design". That reasoning is right about a paused loop and wrong about a
    dead one, and the hub could not tell them apart — which is the trial-1302
    outage in one assertion: an autopilot that last said ``status: ok`` ten days
    ago, and a green dashboard.

    The rule now: an UNDECLARED silence past the panel's ``silent_after_s``
    budget degrades the fold even on a non-gating panel, and a DECLARED pause
    does not. Staleness and absence are still governed by ``gates_health``, so
    everything this class was protecting except the undeclared case is intact.
    """

    def _health_with(self, outcome_doc):
        with tempfile.TemporaryDirectory() as d:
            oc = Path(d) / "outcome.json"
            oc.write_text(json.dumps(outcome_doc))
            kn = Path(d) / "kernel.json"
            kn.write_text(json.dumps({"generated_at": _iso(_NOW),
                                      "runs": [{"ts": _iso(_NOW)}]}))
            orig_oc = server.AUTOPILOT_OUTCOME_JSON
            orig_kn = server.KERNEL_DASHBOARD_JSON
            orig_tl = server.TIMELINE_PATH
            try:
                server.AUTOPILOT_OUTCOME_JSON = oc
                server.KERNEL_DASHBOARD_JSON = kn
                server.TIMELINE_PATH = Path(d) / "missing_timeline.json"
                return server.health_payload()
            finally:
                server.AUTOPILOT_OUTCOME_JSON = orig_oc
                server.KERNEL_DASHBOARD_JSON = orig_kn
                server.TIMELINE_PATH = orig_tl

    def test_an_undeclared_ten_day_outcome_silence_degrades_health(self):
        h = self._health_with({"generated_at": _iso(_NOW - timedelta(days=10)),
                               "outcome_progress": {"status": "ok"}})
        self.assertEqual(h["outcome"]["staleness_class"], "stale")
        self.assertEqual(h["kernel"]["staleness_class"], "fresh")
        self.assertEqual(h["outcome"]["watchdog"]["state"], "stopped_reporting")
        self.assertEqual(h["status"], "degraded")
        self.assertEqual(h["status_set_by"]["panel"], "outcome")

    def test_a_declared_pause_at_the_same_age_stays_ok(self):
        """COMPLIANT-PATH CONTROL: the Phase-0 stop-loss case this class was
        originally written to protect. A paused loop still exports, and only the
        loop can tell a pause from a crash — so it declares it."""
        h = self._health_with({"generated_at": _iso(_NOW - timedelta(days=10)),
                               "outcome_progress": {"status": "paused"}})
        self.assertEqual(h["outcome"]["staleness_class"], "stale")
        self.assertEqual(h["outcome"]["watchdog"]["state"], "idle")
        self.assertEqual(h["status"], "ok")

    def test_a_stale_outcome_still_does_not_gate_on_staleness_alone(self):
        """COMPLIANT-PATH CONTROL: ``gates_health=False`` still means what it
        said. Inside the 6 h silence budget the panel is ``aging`` with no alarm,
        and the fold stays green."""
        h = self._health_with({"generated_at": _iso(_NOW - timedelta(hours=5)),
                               "outcome_progress": {"status": "ok"}})
        self.assertEqual(h["outcome"]["watchdog"]["state"], "ok")
        self.assertEqual(h["status"], "ok")


if __name__ == "__main__":
    unittest.main()
