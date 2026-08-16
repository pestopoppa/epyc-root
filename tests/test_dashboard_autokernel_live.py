from __future__ import annotations

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

    def test_path_escape_in_deployment_is_not_read(self) -> None:
        config_path = self.bundle / "config/deployment.json"
        config = json.loads(config_path.read_text())
        config["controller"]["operations_root"] = "/etc"
        config_path.write_text(json.dumps(config))
        payload = server.discovery_live_payload()
        self.assertFalse(payload["available"])
        self.assertEqual(payload["autokernel_log"], [])


if __name__ == "__main__":
    unittest.main()
