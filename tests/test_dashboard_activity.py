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
    def test_stale_outcome_does_not_gate_health(self):
        # A stale outcome export must NOT flip stack health to degraded (a paused
        # loop reads stale by design); the block is still surfaced for visibility.
        # Control all three inputs so only the outcome staleness is under test:
        # timeline -> missing (not degraded), kernel -> fresh, outcome -> stale.
        with tempfile.TemporaryDirectory() as d:
            oc = Path(d) / "outcome.json"
            oc.write_text(json.dumps({"generated_at": _iso(_NOW - timedelta(days=10)),
                                      "outcome_progress": {"status": "ok"}}))
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
                h = server.health_payload()
            finally:
                server.AUTOPILOT_OUTCOME_JSON = orig_oc
                server.KERNEL_DASHBOARD_JSON = orig_kn
                server.TIMELINE_PATH = orig_tl
        self.assertIn("outcome", h)
        self.assertEqual(h["outcome"]["staleness_class"], "stale")
        self.assertEqual(h["kernel"]["staleness_class"], "fresh")
        # outcome is intentionally excluded from the degraded gate -> still ok.
        self.assertEqual(h["status"], "ok")


if __name__ == "__main__":
    unittest.main()
