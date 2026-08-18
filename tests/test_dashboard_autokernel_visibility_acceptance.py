"""Acceptance contract for an operator-legible AutoKernel live dashboard.

The live logs are evidence, not a status display.  A controller can hold its lock
for minutes without writing another event, and a controller that dies after critic
acceptance can leave a durable inflight build record with no completed iteration.
Neither case is allowed to render as an inert wall of timestamps or generic idle.

These tests intentionally specify the operator questions the surface must answer:

* what phase is active, for how long, and is it plausibly stalled;
* what the loop is waiting on;
* whether the GPU is expected now and whether its claim is actually held;
* which transitions led here;
* whether any durable checkpoint exists and whether it authorizes resume; and
* whether a stopped controller actually failed during source materialization,
  including a concrete recovery action.

Abandoned/retest detail remains available but collapsed by default.  The live
summary and transition timeline stay above that diagnostic history.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import fcntl
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

from dashboard import server


PAGE = Path(__file__).resolve().parents[1] / "dashboard/static/kernel.html"


def _iso(seconds_ago: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(seconds=seconds_ago)).isoformat(
    ).replace("+00:00", "Z")


def _event(event: str, *, seconds_ago: int, channel: str = "planner",
           model: str = "gpt-5.6-sol", provider: str = "codex",
           result: dict | None = None) -> dict:
    row = {
        "schema": server.AUTOKERNEL_DISCOVERY_EVENT_SCHEMA,
        "ts": _iso(seconds_ago),
        "channel": channel,
        "event": event,
        "campaign_id": "ak-discovery-visibility",
        "hypothesis_id": "akh-v2-q5-type-specific-dequant",
        "provider": provider,
        "model": model,
        "effort": "high",
    }
    if result is not None:
        row["result"] = result
    return row


class AutoKernelVisibilityContractTest(unittest.TestCase):
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
            "controller": {
                "state_root": str(self.state),
                "operations_root": str(self.operations),
            },
            "gpu": {"device_id": "mi210_0"},
        }
        (self.bundle / "config/deployment.json").write_text(json.dumps(config))
        (self.state / "controller.run.lock").touch()
        server.AUTOKERNEL_DEPLOYMENTS_ROOT = root

    def tearDown(self) -> None:
        server.AUTOKERNEL_DEPLOYMENTS_ROOT = self._old_root
        self.temp.cleanup()

    def _write_events(self, rows: list[dict]) -> None:
        encoded = "".join(json.dumps(row) + "\n" for row in rows)
        (self.operations / "live/autokernel.jsonl").write_text(encoded)
        planner = [row for row in rows if row.get("channel") == "planner"]
        (self.operations / "live/planner.jsonl").write_text(
            "".join(json.dumps(row) + "\n" for row in planner))

    def _active_payload(self) -> dict:
        with (self.state / "controller.run.lock").open("r") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return server.discovery_live_payload()

    def test_active_precheckpoint_planner_answers_the_operator_questions(self) -> None:
        self._write_events([_event("planner_started", seconds_ago=95)])

        payload = self._active_payload()
        activity = payload["activity"]

        self.assertEqual(activity["status"], "running")
        self.assertEqual(activity["phase"]["id"], "planner")
        self.assertTrue(activity["phase"]["label"])
        self.assertGreaterEqual(activity["phase"]["elapsed_s"], 90)
        self.assertIn(activity["stall"]["state"],
                      {"healthy", "slow", "stalled"})
        self.assertGreater(activity["stall"]["threshold_s"], 0)
        self.assertTrue(activity["stall"]["detail"])
        self.assertIn("planner", activity["waiting_on"].lower())
        self.assertFalse(activity["gpu"]["expected_now"])
        self.assertFalse(activity["gpu"]["claim_held"])
        self.assertTrue(activity["gpu"]["detail"])
        self.assertFalse(activity["checkpoint"]["available"])
        self.assertIn("no", activity["checkpoint"]["detail"].lower())
        self.assertIn("checkpoint", activity["checkpoint"]["detail"].lower())

        transitions = activity["transitions"]
        self.assertGreaterEqual(len(transitions), 1)
        self.assertEqual(transitions[-1]["event"], "planner_started")
        self.assertEqual(transitions[-1]["phase"], "planner")
        self.assertTrue(transitions[-1]["label"])
        self.assertEqual(
            [row["ts"] for row in transitions],
            sorted(row["ts"] for row in transitions),
            "the transition timeline must be chronological")

    def test_planner_uses_its_sealed_actor_budget_before_stall_warning(self) -> None:
        self._write_events([_event("planner_started", seconds_ago=600)])

        activity = self._active_payload()["activity"]

        self.assertEqual(activity["status"], "running")
        self.assertEqual(activity["phase"]["id"], "planner")
        self.assertEqual(activity["stall"]["state"], "healthy")
        self.assertEqual(activity["stall"]["threshold_s"], 900.0)

    def test_gpu_expected_and_claimed_are_two_independent_facts(self) -> None:
        self._write_events([
            _event("planner_started", seconds_ago=180),
            _event("planner_completed", seconds_ago=150, result={"returncode": 0}),
            _event("critic_started", seconds_ago=145, channel="autokernel",
                   model="claude-fable-5", provider="claude"),
            _event("critic_completed", seconds_ago=120, channel="autokernel",
                   model="claude-fable-5", provider="claude",
                   result={"decision": "accept", "returncode": 0}),
        ])
        (self.state / "state.json").write_text(json.dumps({
            "updated_at": _iso(5),
            "next": 1,
            "complete": False,
            "terminal_reason": None,
            "pending": None,
            "iterations": [],
            "inflight": {
                "phase": "measurement",
                "lease": {
                    "phase": "measurement",
                    "device_id": "mi210_0",
                    # This is the controller's native durable field, not a
                    # dashboard-only fixture shape.
                    "device_claim_probe_open": {
                        "state": "held",
                        "released_at": None,
                        "device_id": "mi210_0",
                    },
                },
            },
        }))

        activity = self._active_payload()["activity"]
        self.assertTrue(activity["gpu"]["expected_now"])
        self.assertTrue(activity["gpu"]["claim_held"])
        self.assertIn("mi210", activity["gpu"]["detail"].lower())

    def test_held_identity_bound_build_transaction_is_the_active_stage(self) -> None:
        manifest_sha = "b" * 64
        proposal_sha = "c" * 64
        build_key = "d" * 64
        state = {
            "updated_at": _iso(5), "next": 1, "complete": False,
            "iterations": [],
            "inflight": {
                "candidate": {"source_manifest_sha256": manifest_sha,
                              "manifest": {"candidate_id": "akc-candidate-1"},
                              "hypothesis_id": "akh-v2-q5-type-specific-dequant"},
                "row": {"proposal_sha256": proposal_sha,
                        "hypothesis_id": "akh-v2-q5-type-specific-dequant"},
                "lease": {"admitted": True,
                          "device_claim_probe_released": {"released_at": _iso(6)}},
            },
        }
        (self.state / "state.json").write_text(json.dumps(state))
        entry = self.operations / "build-cache/entries" / build_key
        locks = self.operations / "build-cache/locks"
        entry.mkdir(parents=True)
        locks.mkdir(parents=True)
        (entry / "intent.json").write_text(json.dumps({
            "schema": "epyc.autokernel.gpu_source_build_intent.v1",
            "build_key": build_key,
            "build_contract": {
                "build_key": build_key,
                "patch_bundle_sha256": manifest_sha,
                "proposal_sha256": proposal_sha,
                "deployment_config_sha256": "a" * 64,
            },
        }))
        build_lock = locks / f"build-{build_key}.lock"
        build_lock.touch()
        logs = entry / "logs"
        logs.mkdir()
        (logs / "akc-candidate-1.log.build-sandbox.json").write_text("{}")
        with build_lock.open("r+") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            activity = self._active_payload()["activity"]

        self.assertEqual(activity["status"], "running")
        self.assertEqual(activity["phase"]["id"], "build")
        self.assertEqual(activity["phase"]["label"], "Compiling candidate arm 2 of 2")
        self.assertEqual(activity["waiting_on"], "candidate build completion")
        self.assertFalse(activity["gpu"]["expected_now"])
        pipeline = {row["id"]: row for row in activity["pipeline"]}
        self.assertEqual(pipeline["source_materialization"]["state"], "complete")
        self.assertEqual(pipeline["build"]["state"], "running")
        self.assertEqual(activity["transitions"][-1]["event"],
                         "build_transaction_observed")
        self.assertEqual(activity["transitions"][-1]["label"],
                         "candidate arm active")

    def test_terminal_source_materialization_failure_is_not_idle_or_resumable(self) -> None:
        self._write_events([
            _event("planner_started", seconds_ago=240),
            _event("planner_completed", seconds_ago=180, result={"returncode": 0}),
            _event("critic_started", seconds_ago=175, channel="autokernel",
                   model="claude-fable-5", provider="claude"),
            _event("critic_completed", seconds_ago=120, channel="autokernel",
                   model="claude-fable-5", provider="claude",
                   result={"decision": "accept", "returncode": 0}),
        ])
        (self.state / "state.json").write_text(json.dumps({
            "updated_at": _iso(90),
            "next": 1,
            "complete": False,
            "terminal_reason": None,
            "pending": None,
            "iterations": [],
            "inflight": {
                "lease": {"phase": "prebuild_probe", "device_id": "mi210_0"},
                "operation_key": "operation-source-materialization",
                "exception": {
                    "type": "SourceCandidateError",
                    "message": "candidate diff derives an undeclared file-scope symbol",
                },
            },
        }))
        journal = self.state / "journal"
        journal.mkdir()
        (journal / "events.jsonl").write_text("".join([
            json.dumps({
                "campaign_id": None,
                "event_id": "akj-000000000001-pre-screen",
                "journal_schema": "epyc.autokernel.journal_entry.v1",
                "kind": "STOP_STATE",
                "payload": {"controller_state_sha256": "b" * 64,
                            "state": "discovery_pre_screen_intent"},
                "record_id": None,
                "seq": 1,
                "written_at": _iso(91),
            }) + "\n",
            json.dumps({
                "campaign_id": None,
                "event_id": "akj-000000000002-ambiguous",
                "journal_schema": "epyc.autokernel.journal_entry.v1",
                "kind": "STOP_STATE",
                "payload": {"controller_state_sha256": "c" * 64,
                            "state": "discovery_screen_ambiguous"},
                "record_id": None,
                "seq": 2,
                "written_at": _iso(90),
            }) + "\n",
        ]))

        payload = server.discovery_live_payload()  # lock is not held
        activity = payload["activity"]

        self.assertFalse(payload["active"])
        self.assertEqual(activity["status"], "failed")
        self.assertEqual(activity["phase"]["id"], "source_materialization")
        self.assertTrue(activity["failure"]["detected"])
        self.assertEqual(activity["failure"]["stage"], "source_materialization")
        self.assertIn("SourceCandidateError", activity["failure"]["detail"])
        self.assertTrue(activity["failure"]["recovery"])
        self.assertFalse(activity["failure"]["source_proof_created"])
        self.assertFalse(activity["failure"]["runner_started"])
        self.assertFalse(activity["failure"]["gpu_screen_started"])
        self.assertNotEqual(activity["waiting_on"].lower(), "nothing")
        self.assertTrue(activity["checkpoint"]["available"])
        self.assertEqual(activity["checkpoint"]["kind"], "STOP_STATE")
        self.assertEqual(activity["checkpoint"]["state"],
                         "discovery_screen_ambiguous")
        self.assertFalse(activity["resume"]["possible"])
        self.assertEqual(activity["resume"]["recoverability"], "ambiguous")
        self.assertTrue(activity["resume"]["detail"])
        self.assertFalse(activity["gpu"]["expected_now"])
        self.assertFalse(activity["gpu"]["claim_held"])

    def test_abandoned_and_retest_history_is_summarized_separately(self) -> None:
        self._write_events([_event("planner_started", seconds_ago=20)])
        (self.state / "state.json").write_text(json.dumps({
            "updated_at": _iso(5),
            "next": 4,
            "complete": False,
            "terminal_reason": None,
            "pending": None,
            "inflight": None,
            "iterations": [
                {"turn": 1, "hypothesis_id": "akh-old-a", "status": "abandoned"},
                {"turn": 2, "hypothesis_id": "akh-old-b", "status": "abandoned"},
                {"turn": 3, "hypothesis_id": "akh-retest", "status": "retest"},
            ],
        }))

        history = self._active_payload()["activity"]["history"]
        self.assertEqual(history["abandoned_count"], 2)
        self.assertEqual(history["retest_count"], 1)
        self.assertIn("2", history["summary"])
        self.assertIn("abandoned", history["summary"].lower())
        self.assertIn("retest", history["summary"].lower())
        self.assertEqual(len(history["rows"]), 3)


@unittest.skipIf(shutil.which("node") is None, "node unavailable")
class AutoKernelVisibilityRenderingTest(unittest.TestCase):
    def _render_live(self, payload: dict) -> dict:
        html = PAGE.read_text(encoding="utf-8")
        blocks = re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", html, re.S)
        self.assertEqual(len(blocks), 1)
        source = blocks[0]
        # The page's final line starts polling.  Acceptance calls renderLive
        # directly; no HTTP server or timer is part of this unit boundary.
        source = source.replace(
            "load(); setInterval(load, 60000); loadLive(); setInterval(loadLive, 2000);",
            "")
        harness = r'''
const fs = require("fs");
const input = JSON.parse(fs.readFileSync(0, "utf8"));
const elements = new Map();
for (const id of input.ids) elements.set(id, {
  id, textContent: "", innerHTML: "", className: "", style: {}
});
global.document = {
  querySelector: selector => selector.startsWith("#")
    ? (elements.get(selector.slice(1)) || null) : null,
  createElementNS: () => ({setAttribute(){}, appendChild(){}, textContent:""})
};
global.window = {};
global.console = {error(){}, log(){}};
const payload = input.payload;
eval(input.source + "\nrenderLive(payload);");
const out = {};
for (const [id, node] of elements) out[id] = {
  textContent: node.textContent, innerHTML: node.innerHTML,
  className: node.className
};
process.stdout.write(JSON.stringify(out));
'''
        ids = re.findall(r'\bid="([^"]+)"', html)
        proc = subprocess.run(
            [shutil.which("node"), "-e", harness],
            input=json.dumps({"source": source, "payload": payload, "ids": ids}),
            capture_output=True, text=True, timeout=30)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads(proc.stdout)

    def test_live_summary_timeline_and_history_are_visible(self) -> None:
        html = PAGE.read_text(encoding="utf-8")
        details = re.search(r"<details\b([^>]*)\bid=\"ak-live-history\"([^>]*)>",
                            html, re.I)
        self.assertIsNotNone(details, "abandoned/retest history needs a details disclosure")
        self.assertNotRegex("".join(details.groups()), r"\bopen\b",
                            "abandoned/retest history must be collapsed by default")
        progression = re.search(
            r"<details\b([^>]*)\bid=\\?['\"]ak-progression-abandoned\\?['\"]([^>]*)>",
            html, re.I)
        self.assertIsNotNone(
            progression,
            "the large progression abandoned/retest wall needs its own disclosure")
        self.assertNotRegex("".join(progression.groups()), r"\bopen\b",
                            "progression abandoned/retest rows must be collapsed")

        payload = {
            "active": True,
            "observed_at": _iso(0),
            "deployment": "campaign-a",
            "autokernel_log": [],
            "planner_log": [],
            "telemetry_note": "allowlisted lifecycle facts only",
            "_freshness": {"staleness_class": "fresh"},
            "activity": {
                "status": "running",
                "phase": {"id": "planner", "label": "Planning",
                          "started_at": _iso(95), "elapsed_s": 95},
                "stall": {"state": "healthy", "threshold_s": 900,
                          "detail": "within the planner response budget"},
                "waiting_on": "planner model response",
                "gpu": {"expected_now": False, "claim_held": False,
                        "detail": "GPU is not expected during planning"},
                "checkpoint": {"available": False,
                               "detail": "No completed durable checkpoint yet"},
                "failure": {"detected": False, "stage": None,
                            "detail": "", "recovery": ""},
                "transitions": [
                    {"ts": _iso(95), "event": "planner_started",
                     "phase": "planner", "label": "Planner started"},
                ],
                "history": {"abandoned_count": 2, "retest_count": 1,
                            "summary": "2 abandoned · 1 retest",
                            "rows": [
                                {"turn": 1, "hypothesis_id": "akh-old-a",
                                 "status": "abandoned"},
                                {"turn": 2, "hypothesis_id": "akh-old-b",
                                 "status": "abandoned"},
                                {"turn": 3, "hypothesis_id": "akh-retest",
                                 "status": "retest"},
                            ]},
            },
        }
        nodes = self._render_live(payload)
        summary = nodes["ak-live-summary"]["textContent"] + nodes[
            "ak-live-summary"]["innerHTML"]
        timeline = nodes["ak-live-timeline"]["textContent"] + nodes[
            "ak-live-timeline"]["innerHTML"]
        history_summary = nodes["ak-live-history-summary"]["textContent"]
        history_rows = nodes["ak-live-history-rows"]["textContent"] + nodes[
            "ak-live-history-rows"]["innerHTML"]

        for token in ("Planning", "healthy", "planner model response", "GPU",
                      "not expected", "No completed durable checkpoint"):
            self.assertIn(token.lower(), summary.lower())
        self.assertRegex(summary, r"(?i)(95\s*s|1\s*m(?:in)?\s*35)",
                         "phase elapsed time is not visibly rendered")
        self.assertIn("Planner started", timeline)
        self.assertIn("2 abandoned", history_summary)
        self.assertIn("1 retest", history_summary)
        self.assertIn("akh-old-a", history_rows)
        self.assertIn("akh-retest", history_rows)

    def test_source_materialization_failure_renders_stop_and_recovery(self) -> None:
        payload = {
            "active": False,
            "observed_at": _iso(0),
            "deployment": "campaign-a",
            "autokernel_log": [],
            "planner_log": [],
            "telemetry_note": "allowlisted lifecycle facts only",
            "_freshness": {"staleness_class": "aging"},
            "activity": {
                "status": "failed",
                "phase": {"id": "source_materialization",
                          "label": "Source materialization failed",
                          "started_at": _iso(120), "elapsed_s": 120},
                "stall": {"state": "stopped", "threshold_s": 900,
                          "detail": "controller lock is no longer held"},
                "waiting_on": "operator recovery decision",
                "gpu": {"expected_now": False, "claim_held": False,
                        "detail": "GPU screening was not reached"},
                "checkpoint": {"available": True, "kind": "STOP_STATE",
                               "state": "discovery_screen_ambiguous",
                               "detail": "Durable ambiguous screen stop"},
                "resume": {"possible": False, "recoverability": "ambiguous",
                           "detail": "Cannot resume this inflight materialization"},
                "failure": {"detected": True,
                            "stage": "source_materialization",
                            "detail": "SourceCandidateError: undeclared symbol",
                            "recovery": "Repair source declaration and start a new attempt",
                            "source_proof_created": False,
                            "runner_started": False,
                            "gpu_screen_started": False},
                "transitions": [],
                "history": {"abandoned_count": 0, "retest_count": 0,
                            "summary": "No abandoned or retest rows", "rows": []},
            },
        }
        nodes = self._render_live(payload)
        summary = nodes["ak-live-summary"]["textContent"] + nodes[
            "ak-live-summary"]["innerHTML"]
        for token in ("failed", "Source materialization failed",
                      "SourceCandidateError", "discovery_screen_ambiguous",
                      "Cannot resume", "GPU screening was not reached",
                      "Repair source declaration"):
            self.assertIn(token.lower(), summary.lower())


if __name__ == "__main__":
    unittest.main()
