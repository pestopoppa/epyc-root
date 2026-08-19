from __future__ import annotations

from datetime import datetime, timedelta, timezone
import fcntl
import json
from pathlib import Path
import tempfile
import unittest

from dashboard import server


class AutoKernelLiveDashboardTest(unittest.TestCase):
    def setUp(self) -> None:
        self._old_root = server.AUTOKERNEL_DEPLOYMENTS_ROOT
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name) / "deployments"
        self.bundle = root / "campaign-a"
        self.state = self.bundle / "state"
        self.operations = self.bundle / "operations"
        (self.bundle / "config").mkdir(parents=True)
        self.state.mkdir()
        (self.operations / "live").mkdir(parents=True)
        config = {
            "config_sha256": "a" * 64,
            "controller": {"state_root": str(self.state),
                           "operations_root": str(self.operations)},
        }
        (self.bundle / "config/deployment.json").write_text(json.dumps(config))
        (self.state / "controller.run.lock").touch()
        server.AUTOKERNEL_DEPLOYMENTS_ROOT = root

    def tearDown(self) -> None:
        server.AUTOKERNEL_DEPLOYMENTS_ROOT = self._old_root
        self.temp.cleanup()

    def test_active_precheckpoint_planner_is_visible(self) -> None:
        with (self.state / "controller.run.lock").open("r") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            payload = server.discovery_live_payload()
            self.assertTrue(payload["active"])
            self.assertIn("first durable checkpoint", payload["status_message"])
            self.assertEqual(payload["_freshness"]["reporting"], "observed")
            self.assertEqual(payload["_freshness"]["staleness_class"], "fresh")

    def test_active_planner_uses_its_stage_budget_in_health_envelope(self) -> None:
        """v14: a healthy bounded planner call is not silent at 329 seconds."""
        started_at = (datetime.now(timezone.utc) - timedelta(seconds=329))
        event = {
            "schema": server.AUTOKERNEL_DISCOVERY_EVENT_SCHEMA,
            "ts": started_at.isoformat().replace("+00:00", "Z"),
            "channel": "planner", "event": "planner_started",
            "campaign_id": "ak-discovery-" + "a" * 16,
            "hypothesis_id": "akh-v2-q5-type-specific-dequant",
            "provider": "codex", "model": "gpt-5.6-sol", "effort": "high",
        }
        (self.operations / "live/planner.jsonl").write_text(
            json.dumps(event) + "\n")

        with (self.state / "controller.run.lock").open("r") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            payload = server.discovery_live_payload()

        self.assertEqual(payload["activity"]["phase"]["id"], "planner")
        self.assertEqual(payload["activity"]["stall"]["state"], "healthy")
        self.assertEqual(payload["activity"]["stall"]["threshold_s"], 900.0)
        freshness = payload["_freshness"]
        self.assertEqual(freshness["reporting"], "observed")
        self.assertEqual(freshness["staleness_class"], "fresh")
        self.assertEqual(freshness["watchdog"]["state"], "ok")
        self.assertEqual(freshness["thresholds"], {
            "warn_s": 900.0, "stale_s": 900.0, "silent_after_s": 900.0})

    def test_only_allowlisted_producer_events_reach_log(self) -> None:
        valid = {
            "schema": server.AUTOKERNEL_DISCOVERY_EVENT_SCHEMA,
            "ts": "2026-08-14T16:00:00Z", "channel": "planner",
            "event": "planner_started", "campaign_id": "ak-discovery-x",
            "hypothesis_id": "akh-x", "provider": "codex",
            "model": "gpt-5.6-sol", "effort": "high",
        }
        rogue = {**valid, "prompt": "secret text"}
        path = self.operations / "live/planner.jsonl"
        path.write_text(json.dumps(valid) + "\n" + json.dumps(rogue) + "\n")
        payload = server.discovery_live_payload()
        self.assertEqual(len(payload["planner_log"]), 1)
        self.assertNotIn("secret text", json.dumps(payload))
        self.assertNotIn("prompt", payload["planner_log"][0])

    def test_v16_planner_terminal_failure_is_not_projected_as_idle(self) -> None:
        """Exact v16 seam: a typed planning failure must remain visible."""
        campaign_id = "ak-discovery-" + "a" * 16
        started_at = "2026-08-19T04:42:39.059499Z"
        failed_at = "2026-08-19T04:48:25.206346Z"
        hypothesis_id = "akh-v2-q5-type-specific-dequant"
        event = {
            "schema": server.AUTOKERNEL_DISCOVERY_EVENT_SCHEMA,
            "ts": started_at, "channel": "planner",
            "event": "planner_started", "campaign_id": campaign_id,
            "hypothesis_id": hypothesis_id, "provider": "codex",
            "model": "gpt-5.6-sol", "effort": "high",
        }
        (self.operations / "live/autokernel.jsonl").write_text(
            json.dumps(event) + "\n")
        (self.operations / "live/planner.jsonl").write_text(
            json.dumps(event) + "\n")
        planning = {
            "turn": 1, "phase": "actor_entering",
            "portfolio_binding": {"hypothesis_id": hypothesis_id},
            "context": {"authoring_assignment": {
                "campaign_id": campaign_id,
            }},
            "failure": {
                "type": "TelemetryError",
                "message": "telemetry result contains a non-allowlisted field",
            },
        }
        (self.state / "state.json").write_text(json.dumps({
            "updated_at": "2026-08-19T04:48:25.203592Z",
            "next": 1, "complete": False, "iterations": [],
            "planning": planning,
        }))
        journal = self.state / "journal"
        journal.mkdir()
        (journal / "events.jsonl").write_text(json.dumps({
            "journal_schema": "epyc.autokernel.journal_entry.v1",
            "event_id": "akj-000000000003-29f8feef6dc9",
            "kind": "STOP_STATE", "seq": 3, "written_at": failed_at,
            "payload": {
                "state": "discovery_planner_terminal_failure",
                "controller_state_sha256": "c" * 64,
            },
        }) + "\n")

        payload = server.discovery_live_payload()
        activity = payload["activity"]

        self.assertFalse(payload["active"])
        self.assertEqual(activity["status"], "failed")
        self.assertEqual(activity["phase"]["id"], "planner_validation")
        self.assertEqual(activity["hypothesis_id"], hypothesis_id)
        self.assertEqual(activity["turn"], 1)
        self.assertTrue(activity["failure"]["detected"])
        self.assertEqual(activity["failure"]["stage"], "planner_validation")
        self.assertIn("non-allowlisted field", activity["failure"]["detail"])
        self.assertIn("fresh sealed deployment", activity["failure"]["recovery"])
        self.assertFalse(activity["gpu"]["expected_now"])
        self.assertFalse(activity["gpu"]["claim_held"])
        pipeline = {row["id"]: row["state"] for row in activity["pipeline"]}
        self.assertEqual(pipeline["planner"], "complete")
        self.assertEqual(pipeline["planner_validation"], "failed")
        self.assertEqual(pipeline["critic"], "not_reached")
        self.assertIn("FAILED", payload["status_message"])
        self.assertEqual(payload["autokernel_log"][0]["event"], "planner_started")
        self.assertEqual(payload["planner_log"][0]["event"], "planner_started")

    def test_path_escape_in_deployment_is_not_read(self) -> None:
        config_path = self.bundle / "config/deployment.json"
        config = json.loads(config_path.read_text())
        config["controller"]["operations_root"] = "/etc"
        config_path.write_text(json.dumps(config))
        payload = server.discovery_live_payload()
        self.assertFalse(payload["available"])
        self.assertEqual(payload["autokernel_log"], [])

    def test_active_campaign_outranks_newer_terminal_progress(self) -> None:
        terminal = self.bundle.parent / "campaign-terminal"
        terminal_state = terminal / "state"
        terminal_operations = terminal / "operations"
        (terminal / "config").mkdir(parents=True)
        terminal_state.mkdir()
        (terminal_operations / "live").mkdir(parents=True)
        (terminal_state / "controller.run.lock").touch()
        (terminal / "config/deployment.json").write_text(json.dumps({
            "config_sha256": "b" * 64,
            "controller": {
                "state_root": str(terminal_state),
                "operations_root": str(terminal_operations),
            },
        }))
        (terminal_state / "state.json").write_text(json.dumps({
            "updated_at": "2099-01-01T00:00:00Z",
            "complete": False,
            "iterations": [],
            "inflight": {
                "exception": {"type": "RuntimeError", "message": "terminal"},
            },
        }))

        with (self.state / "controller.run.lock").open("r") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            payload = server.discovery_live_payload()

        self.assertTrue(payload["active"])
        self.assertEqual(payload["deployment"], "campaign-a")


if __name__ == "__main__":
    unittest.main()
