"""Tests for the hub's today's-activity counters (dashboard/server.py).

Flow counting itself is covered in tests/test_dashboard_flow_counter.py. Also
covers the kernel-contract and autopilot-outcome-contract freshness/reader logic.
Run: ``python3 -m unittest tests.test_dashboard_activity``
"""
import json
import tempfile
import unittest
from unittest import mock
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dashboard import panels, server, kernel_contract as legacy


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


_NOW = datetime.now(timezone.utc)


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
        fr = legacy._kernel_contract_freshness(data)
        self.assertEqual(fr["staleness_class"], "stale")
        self.assertEqual(fr["source"], "runs[].ts")

    def test_fresh_run_ts_is_fresh_even_if_generated_at_old(self):
        data = {"generated_at": _iso(_NOW - timedelta(days=30)),
                "runs": [{"ts": _iso(_NOW - timedelta(hours=1))}]}
        self.assertEqual(legacy._kernel_contract_freshness(data)["staleness_class"], "fresh")

    def test_max_of_multiple_run_ts(self):
        data = {"runs": [{"ts": _iso(_NOW - timedelta(days=30))},
                         {"ts": _iso(_NOW - timedelta(days=1))}]}
        fr = legacy._kernel_contract_freshness(data)
        self.assertEqual(fr["staleness_class"], "fresh")  # 1d < 3d warn

    def test_falls_back_to_generated_at_without_runs(self):
        data = {"generated_at": _iso(_NOW - timedelta(days=30)), "runs": []}
        fr = legacy._kernel_contract_freshness(data)
        self.assertEqual(fr["staleness_class"], "stale")
        self.assertEqual(fr["source"], "generated_at")

    def test_missing_when_no_timestamps(self):
        fr = legacy._kernel_contract_freshness({"runs": []})
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
            orig_kn = legacy.KERNEL_DASHBOARD_JSON
            orig_tl = server.TIMELINE_PATH
            try:
                server.AUTOPILOT_OUTCOME_JSON = oc
                legacy.KERNEL_DASHBOARD_JSON = kn
                server.TIMELINE_PATH = Path(d) / "missing_timeline.json"
                # This fixture exercises the outcome fold.  The unified-loop
                # panel reads a separate, host-global store; letting that real
                # snapshot into this temp-root test makes an unrelated stale
                # campaign set the result before ``outcome`` is evaluated.
                with mock.patch(
                        "dashboard.server.loop_status.snapshot",
                        return_value=({}, panels.Observation(
                            False, detail="no loop report in outcome fixture"))):
                    return server.health_payload()
            finally:
                server.AUTOPILOT_OUTCOME_JSON = orig_oc
                legacy.KERNEL_DASHBOARD_JSON = orig_kn
                server.TIMELINE_PATH = orig_tl

    def test_an_undeclared_ten_day_outcome_silence_degrades_health(self):
        h = self._health_with({"generated_at": _iso(_NOW - timedelta(days=10)),
                               "outcome_progress": {"status": "ok"}})
        self.assertEqual(h["outcome"]["staleness_class"], "stale")
        self.assertNotIn("kernel", h)
        self.assertNotIn("kernel", h["panels"])
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
