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
import hashlib
import json
import os
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
           result: dict | None = None,
           campaign_id: str = "ak-discovery-visibility") -> dict:
    row = {
        "schema": server.AUTOKERNEL_DISCOVERY_EVENT_SCHEMA,
        "ts": _iso(seconds_ago),
        "channel": channel,
        "event": event,
        "campaign_id": campaign_id,
        "hypothesis_id": "akh-v2-q5-type-specific-dequant",
        "provider": provider,
        "model": model,
        "effort": "high",
    }
    if result is not None:
        row["result"] = result
    return row


def _seal(body: dict) -> dict:
    sealed = dict(body)
    sealed["receipt_sha256"] = hashlib.sha256(json.dumps(
        sealed, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")).hexdigest()
    return sealed


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

    def _complete_build(self, entry: Path, *, build_key: str,
                        manifest_sha: str, contract: dict) -> None:
        materialization = _seal({
            "schema": "epyc.autokernel.gpu_source_materialization.v1",
            "authority": "nonpromotable_candidate_only_discovery",
            "operation_key": build_key,
            "build_key": build_key,
            "build_contract": contract,
            "manifest_sha256": manifest_sha,
            "promotion_claim": False,
        })
        materialization_path = entry / "materialization.json"
        materialization_path.write_text(json.dumps(materialization) + "\n")
        intent_path = entry / "intent.json"
        terminal = _seal({
            "schema": "epyc.autokernel.gpu_source_build_terminal.v1",
            "build_key": build_key,
            "intent_file_sha256": hashlib.sha256(
                intent_path.read_bytes()).hexdigest(),
            "state": "complete",
            "build": {
                "build_key": build_key,
                "materialization_receipt": str(materialization_path),
                "materialization_sha256": hashlib.sha256(
                    materialization_path.read_bytes()).hexdigest(),
            },
            "promotion_claim": False,
        })
        (entry / "terminal.json").write_text(json.dumps(terminal) + "\n")

    def _write_v10_correctness_parser_terminal(self) -> None:
        """Reproduce the durable v10 boundary, without inventing telemetry."""
        manifest_sha = "b" * 64
        proposal_sha = "c" * 64
        operation_key = "8" * 64
        build_key = "d" * 64
        acquired_at = _iso(60)
        released_at = _iso(5)
        (self.state / "state.json").write_text(json.dumps({
            "updated_at": _iso(2), "next": 1, "complete": False,
            "iterations": [],
            "inflight": {
                "operation_key": operation_key,
                "candidate": {
                    "source_manifest_sha256": manifest_sha,
                    "hypothesis_id": "akh-v2-q5-type-specific-dequant",
                },
                "row": {
                    "proposal_sha256": proposal_sha,
                    "hypothesis_id": "akh-v2-q5-type-specific-dequant",
                },
                "lease": {"admitted": True, "device_id": "mi210_0"},
                "exception": {
                    "type": "EvidenceProducerError",
                    "message": "correctness stdout must contain exactly one summary",
                },
            },
        }))
        entry = self.operations / "build-cache/entries" / build_key
        entry.mkdir(parents=True)
        contract = {
            "build_key": build_key,
            "patch_bundle_sha256": manifest_sha,
            "proposal_sha256": proposal_sha,
            "deployment_config_sha256": "a" * 64,
        }
        (entry / "intent.json").write_text(json.dumps({
            "schema": "epyc.autokernel.gpu_source_build_intent.v1",
            "build_key": build_key,
            "build_contract": contract,
        }))
        self._complete_build(entry, build_key=build_key,
                             manifest_sha=manifest_sha, contract=contract)
        build_completed = datetime.fromisoformat(
            acquired_at.replace("Z", "+00:00")).timestamp() - 1
        os.utime(entry / "terminal.json", (build_completed, build_completed))
        operation = self.operations / operation_key
        (operation / "proof/correctness").mkdir(parents=True)
        (operation / "intent.json").write_text(json.dumps({
            "schema": "epyc.autokernel.gpu_source_operation.v1",
            "operation_key": operation_key,
            "manifest_sha256": manifest_sha,
        }))
        (operation / "evidence-policy.json").write_text(json.dumps({
            "schema": "epyc.autokernel.gpu_source_execution_policy.v1",
            "manifest_sha256": manifest_sha,
        }))
        (operation / "proof/correctness/stdout.txt").write_text(
            "Testing 2 devices\n  1139/1139 tests passed\n"
            "  Backend ROCm0: OK\nBackend 2/2: CPU\n  Skipping\n"
            "2/2 backends passed\nOK\n")
        (operation / "proof/correctness/stderr.txt").write_text(
            "ggml_cuda_init: found 1 ROCm devices\n")
        (operation / "reservation-release.json").write_text(json.dumps({
            "schema": "epyc.autokernel.gpu_source_reservation_release.v1",
            "operation_key": operation_key,
            "device_claim_released": {
                "schema": "epyc.autokernel.device_claim_receipt.v1",
                "claim_id": "akd-v10-correctness",
                "device_id": "mi210_0",
                "purpose": "AutoKernel GPU source proof and throughput",
                "acquired_at": acquired_at,
                "released_at": released_at,
            },
        }))

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

    def test_v11_planner_event_supplies_hypothesis_before_pending_checkpoint(self) -> None:
        expected_campaign = "ak-discovery-" + "a" * 16
        self._write_events([_event(
            "planner_started", seconds_ago=4,
            campaign_id=expected_campaign)])

        activity = self._active_payload()["activity"]

        self.assertEqual(activity["status"], "running")
        self.assertEqual(activity["phase"]["id"], "planner")
        self.assertEqual(activity["hypothesis_id"],
                         "akh-v2-q5-type-specific-dequant")

        self._write_events([
            _event("planner_started", seconds_ago=4,
                   campaign_id=expected_campaign),
            _event("planner_started", seconds_ago=3,
                   campaign_id="ak-discovery-wrong"),
        ])
        self.assertEqual(self._active_payload()["activity"]["hypothesis_id"],
                         "akh-v2-q5-type-specific-dequant")

        self._write_events([
            _event("planner_started", seconds_ago=4,
                   campaign_id=expected_campaign),
            _event("planner_completed", seconds_ago=3,
                   campaign_id=expected_campaign),
        ])
        self.assertIsNone(self._active_payload()["activity"]["hypothesis_id"])

    def test_planner_uses_its_sealed_actor_budget_before_stall_warning(self) -> None:
        self._write_events([_event("planner_started", seconds_ago=600)])

        activity = self._active_payload()["activity"]

        self.assertEqual(activity["status"], "running")
        self.assertEqual(activity["phase"]["id"], "planner")
        self.assertEqual(activity["stall"]["state"], "healthy")
        self.assertEqual(activity["stall"]["threshold_s"], 900.0)

    def test_v7_exit_after_planner_completion_is_validation_failure(self) -> None:
        """Two actor events are not a launch-idle state after the lock exits."""
        self._write_events([
            _event("planner_started", seconds_ago=90),
            _event("planner_completed", seconds_ago=30,
                   result={"returncode": 0}),
        ])

        payload = server.discovery_live_payload()
        activity = payload["activity"]

        self.assertFalse(payload["active"])
        self.assertEqual(activity["status"], "failed")
        self.assertEqual(activity["phase"]["id"], "planner_validation")
        self.assertIsNone(activity["hypothesis_id"])
        self.assertFalse(activity["checkpoint"]["available"])
        self.assertTrue(activity["failure"]["detected"])
        self.assertEqual(activity["failure"]["stage"], "planner_validation")
        self.assertIn("did not persist", activity["failure"]["detail"])
        self.assertIn("exact planner-validation exception",
                      activity["failure"]["detail"])
        self.assertFalse(activity["resume"]["possible"])
        self.assertIn("fresh sealed deployment", activity["resume"]["detail"])
        self.assertFalse(activity["gpu"]["expected_now"])
        self.assertFalse(activity["gpu"]["claim_held"])
        self.assertIn("not reached", activity["gpu"]["detail"])
        pipeline = {row["id"]: row for row in activity["pipeline"]}
        self.assertEqual(pipeline["planner"]["state"], "complete")
        self.assertEqual(pipeline["planner_validation"]["state"], "failed")
        self.assertEqual(pipeline["critic"]["state"], "not_reached")
        self.assertEqual(activity["transitions"][-1]["event"],
                         "planner_validation_interrupted")

    def test_explicit_planner_validation_terminal_events_are_consumed(self) -> None:
        for event in ("planner_validation_failed", "planner_validation_refused"):
            with self.subTest(event=event):
                self._write_events([
                    _event("planner_started", seconds_ago=90),
                    _event("planner_completed", seconds_ago=30,
                           result={"returncode": 0}),
                    _event(event, seconds_ago=29, channel="autokernel",
                           model="local-validator", provider="controller"),
                ])

                activity = server.discovery_live_payload()["activity"]

                self.assertEqual(activity["status"], "failed")
                self.assertEqual(activity["phase"]["id"], "planner_validation")
                self.assertTrue(activity["failure"]["detected"])
                self.assertIn("producer lifecycle event",
                              activity["failure"]["detail"])
                pipeline = {row["id"]: row for row in activity["pipeline"]}
                self.assertEqual(pipeline["planner"]["state"], "complete")
                self.assertEqual(pipeline["planner_validation"]["state"], "failed")

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

    def test_v8_critic_pending_actor_outranks_resource_admission(self) -> None:
        self._write_events([
            _event("planner_started", seconds_ago=180),
            _event("planner_completed", seconds_ago=60,
                   result={"returncode": 0}),
            _event("critic_started", seconds_ago=30, channel="autokernel",
                   model="claude-fable-5", provider="claude"),
        ])
        (self.state / "state.json").write_text(json.dumps({
            "updated_at": _iso(31),
            "next": 1,
            "complete": False,
            "terminal_reason": None,
            "inflight": None,
            "iterations": [],
            "pending": {
                "phase": "critic_pending",
                "candidate": {
                    "hypothesis_id": "akh-v2-q5-type-specific-dequant",
                },
                "row": {
                    "hypothesis_id": "akh-v2-q5-type-specific-dequant",
                },
            },
        }))
        journal = self.state / "journal"
        journal.mkdir()
        (journal / "events.jsonl").write_text(json.dumps({
            "campaign_id": "ak-discovery-v8",
            "event_id": "akj-000000000003-planner-checkpointed",
            "journal_schema": "epyc.autokernel.journal_entry.v1",
            "kind": "STOP_STATE",
            "payload": {
                "controller_state_sha256": "c" * 64,
                "state": "discovery_planner_checkpointed",
            },
            "record_id": None,
            "seq": 3,
            "written_at": _iso(31),
        }) + "\n")

        payload = self._active_payload()
        activity = payload["activity"]

        self.assertTrue(payload["active"])
        self.assertEqual(activity["status"], "running")
        self.assertEqual(activity["phase"]["id"], "critic")
        self.assertEqual(activity["phase"]["label"], "Critic review")
        self.assertEqual(activity["waiting_on"], "critic review completion")
        self.assertEqual(activity["hypothesis_id"],
                         "akh-v2-q5-type-specific-dequant")
        self.assertFalse(activity["gpu"]["expected_now"])
        pipeline = {row["id"]: row for row in activity["pipeline"]}
        self.assertEqual(pipeline["planner"]["state"], "complete")
        self.assertEqual(pipeline["planner_validation"]["state"], "complete")
        self.assertEqual(pipeline["critic"]["state"], "running")
        self.assertEqual(pipeline["authorization"]["state"], "not_reached")
        self.assertEqual(pipeline["resource_admission"]["state"], "not_reached")
        self.assertTrue(activity["checkpoint"]["available"])
        self.assertEqual(activity["checkpoint"]["seq"], 3)

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
        self.assertEqual(pipeline["source_materialization"]["state"], "running")
        self.assertEqual(pipeline["build"]["state"], "running")
        self.assertEqual(activity["transitions"][-1]["event"],
                         "build_transaction_observed")
        self.assertEqual(activity["transitions"][-1]["label"],
                         "candidate arm active")

    def test_v11_pre_screen_intent_keeps_active_anchor_build_fail_closed(self) -> None:
        """Exact v11 boundary: declared proof plan cannot invent correctness."""
        manifest_sha = "6bb3454fac66b311f126311837b85cad11af609d62c349a5eafb1b5674525569"
        proposal_sha = "c02c48262a7634cf023ec454547517925f8d1df6c5158ee90a28eb85414e869a"
        operation_key = "3818df9f05218f6b2583c7d8d4f1436d849e874e19ea47841b9d7055ce2df307"
        build_key = "d21841b48fca9adbd410d8f4cadcf91f41087567088197bc85bf88ce633d70f5"
        (self.state / "state.json").write_text(json.dumps({
            "updated_at": _iso(3), "next": 1, "complete": False,
            "pending": None, "planning": None, "iterations": [],
            "inflight": {
                "phase": "prebuild_probe", "operation_key": operation_key,
                "candidate": {
                    "source_manifest_sha256": manifest_sha,
                    "hypothesis_id": "akh-v2-q5-type-specific-dequant",
                    "manifest": {"candidate_id": "akc-discovery-1",
                                 "campaign_id": "ak-discovery-8e4eee8d36dc7e9e"},
                },
                "row": {"proposal_sha256": proposal_sha,
                        "hypothesis_id": "akh-v2-q5-type-specific-dequant"},
                "lease": {"admitted": True, "phase": "prebuild_probe",
                          "repetition": 1,
                          "device_claim_probe_released": {"released_at": _iso(4)}},
                "confirmation": False,
            },
        }))
        operation = self.operations / operation_key
        operation.mkdir()
        (operation / "intent.json").write_text(json.dumps({
            "schema": "epyc.autokernel.gpu_source_operation.v1",
            "operation_key": operation_key,
            "manifest_sha256": manifest_sha,
        }))
        # The v11 incident had no evidence-policy or any correctness receipt.
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
        logs = entry / "logs"
        logs.mkdir()
        (logs / "akc-anchor.log.build-sandbox.json").write_text("{}")
        build_lock = locks / f"build-{build_key}.lock"
        build_lock.touch()
        with build_lock.open("r+") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            activity = self._active_payload()["activity"]

        self.assertEqual(activity["status"], "running")
        self.assertEqual(activity["phase"]["id"], "build")
        self.assertEqual(activity["phase"]["label"],
                         "Compiling anchor arm 1 of 2")
        self.assertFalse(activity["correctness"]["execution_started"])
        self.assertFalse(activity["gpu"]["expected_now"])
        pipeline = {row["id"]: row for row in activity["pipeline"]}
        self.assertEqual(pipeline["resource_admission"]["state"], "complete")
        self.assertEqual(pipeline["source_materialization"]["state"], "running")
        self.assertEqual(pipeline["build"]["state"], "running")
        for stage in ("evidence_binding", "correctness",
                      "correctness_validation", "candidate_attribution"):
            self.assertEqual(pipeline[stage]["state"], "not_reached", stage)
        self.assertEqual(activity["stage_contract"]["first_incomplete_stage"],
                         "build")

    def test_completed_build_then_factory_error_is_evidence_binding_failure(self) -> None:
        manifest_sha = "b" * 64
        proposal_sha = "c" * 64
        build_key = "d" * 64
        (self.state / "state.json").write_text(json.dumps({
            "updated_at": _iso(2), "next": 1, "complete": False,
            "iterations": [],
            "inflight": {
                "candidate": {"source_manifest_sha256": manifest_sha},
                "row": {"proposal_sha256": proposal_sha},
                "lease": {"admitted": True},
                "exception": {
                    "type": "DeploymentFactoryError",
                    "message": "candidate manifest canonical carrier hash mismatch",
                },
            },
        }))
        entry = self.operations / "build-cache/entries" / build_key
        entry.mkdir(parents=True)
        contract = {
            "build_key": build_key,
            "patch_bundle_sha256": manifest_sha,
            "proposal_sha256": proposal_sha,
            "deployment_config_sha256": "a" * 64,
        }
        (entry / "intent.json").write_text(json.dumps({
            "schema": "epyc.autokernel.gpu_source_build_intent.v1",
            "build_key": build_key,
            "build_contract": contract,
        }))
        self._complete_build(entry, build_key=build_key,
                             manifest_sha=manifest_sha, contract=contract)

        activity = server.discovery_live_payload()["activity"]

        self.assertEqual(activity["status"], "failed")
        self.assertEqual(activity["phase"]["id"], "evidence_binding")
        self.assertIn("after completed build", activity["phase"]["label"])
        self.assertEqual(activity["failure"]["stage"], "evidence_binding")
        pipeline = {row["id"]: row for row in activity["pipeline"]}
        self.assertEqual(pipeline["source_materialization"]["state"], "complete")
        self.assertEqual(pipeline["build"]["state"], "complete")
        self.assertEqual(pipeline["evidence_binding"]["state"], "failed")
        self.assertEqual(activity["transitions"][-1]["event"],
                         "build_transaction_complete")

    def test_v10_correctness_parser_failure_preserves_completed_gpu_execution(self) -> None:
        self._write_v10_correctness_parser_terminal()

        activity = server.discovery_live_payload()["activity"]

        self.assertEqual(activity["status"], "failed")
        self.assertEqual(activity["phase"]["id"], "correctness_validation")
        self.assertEqual(activity["phase"]["label"],
                         "Correctness result parsing failed after GPU proof")
        self.assertEqual(activity["failure"]["stage"], "correctness_validation")
        self.assertTrue(activity["failure"]["gpu_screen_started"])
        self.assertTrue(activity["failure"]["correctness_execution_completed"])
        self.assertFalse(activity["gpu"]["expected_now"])
        self.assertFalse(activity["gpu"]["claim_held"])
        self.assertTrue(activity["gpu"]["screen_started"])
        self.assertTrue(activity["gpu"]["claim_released"])
        self.assertIn("1139/1139 tests passed", activity["gpu"]["detail"])
        self.assertEqual(activity["correctness"]["summary"],
                         "1139/1139 tests passed")
        self.assertTrue(activity["correctness"]["execution_completed"])
        self.assertFalse(activity["correctness"]["validation_passed"])
        self.assertGreaterEqual(activity["correctness"]["elapsed_s"], 54)
        self.assertLessEqual(activity["correctness"]["elapsed_s"], 56)
        pipeline = {row["id"]: row for row in activity["pipeline"]}
        for stage in ("source_materialization", "build", "evidence_binding",
                      "correctness"):
            self.assertEqual(pipeline[stage]["state"], "complete", stage)
        self.assertEqual(pipeline["correctness_validation"]["state"], "failed")
        for stage in ("dispatch_proof", "profile", "benchmark", "decision"):
            self.assertEqual(pipeline[stage]["state"], "not_reached", stage)
        for stage in ("replication_s1", "replication_s2"):
            self.assertEqual(pipeline[stage]["state"], "not_reached", stage)
        self.assertIsNone(activity["stage_contract"]["replication"])
        self.assertEqual(activity["transitions"][-2]["event"],
                         "correctness_execution_complete")
        self.assertEqual(activity["transitions"][-1]["event"],
                         "correctness_validation_failed")

    def test_correctness_observation_rejects_a_symlinked_release_receipt(self) -> None:
        self._write_v10_correctness_parser_terminal()
        operation = self.operations / ("8" * 64)
        release = operation / "reservation-release.json"
        outside = Path(self.temp.name) / "outside-release.json"
        outside.write_bytes(release.read_bytes())
        release.unlink()
        release.symlink_to(outside)

        activity = server.discovery_live_payload()["activity"]

        self.assertFalse(activity["gpu"]["screen_started"])
        self.assertFalse(activity["correctness"]["execution_started"])
        self.assertNotEqual(activity["phase"]["id"], "correctness_validation")

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

    def test_newer_sealed_bundle_does_not_mask_failed_launched_campaign(self) -> None:
        """A config mtime is availability, never a replacement for run truth."""
        (self.state / "state.json").write_text(json.dumps({
            "updated_at": _iso(5),
            "next": 1,
            "complete": False,
            "terminal_reason": None,
            "pending": None,
            "iterations": [],
            "inflight": {
                "phase": "screen",
                "exception": {
                    "type": "DeploymentFactoryError",
                    "message": "candidate manifest canonical carrier hash mismatch",
                },
            },
        }))
        next_bundle = self.bundle.parent / "campaign-v6"
        next_state = next_bundle / "state"
        next_operations = next_bundle / "operations"
        (next_bundle / "config").mkdir(parents=True)
        next_state.mkdir()
        (next_operations / "live").mkdir(parents=True)
        (next_state / "controller.run.lock").touch()
        next_config = next_bundle / "config/deployment.json"
        next_config.write_text(json.dumps({
            "config_sha256": "b" * 64,
            "controller": {
                "state_root": str(next_state),
                "operations_root": str(next_operations),
            },
        }))
        newer = datetime.now(timezone.utc).timestamp() + 60
        os.utime(next_config, (newer, newer))

        payload = server.discovery_live_payload()

        self.assertEqual(payload["deployment"], "campaign-a")
        self.assertEqual(payload["activity"]["status"], "failed")
        self.assertIn("canonical carrier hash mismatch",
                      payload["activity"]["failure"]["detail"])
        sealed = payload["newest_unlaunched_deployment"]
        self.assertTrue(sealed["available"])
        self.assertEqual(sealed["deployment"], "campaign-v6")
        self.assertEqual(sealed["launch_state"], "not_launched")

    def test_active_v7_supersedes_older_unlaunched_v6(self) -> None:
        base_stamp = (self.bundle / "config/deployment.json").stat().st_mtime

        def add_bundle(name: str, stamp: float) -> tuple[Path, Path]:
            bundle = self.bundle.parent / name
            state = bundle / "state"
            operations = bundle / "operations"
            (bundle / "config").mkdir(parents=True)
            state.mkdir()
            (operations / "live").mkdir(parents=True)
            (state / "controller.run.lock").touch()
            config_path = bundle / "config/deployment.json"
            config_path.write_text(json.dumps({
                "config_sha256": ("6" if name.endswith("v6") else "7") * 64,
                "controller": {
                    "state_root": str(state),
                    "operations_root": str(operations),
                },
            }))
            os.utime(config_path, (stamp, stamp))
            return state, operations

        add_bundle("campaign-v6", base_stamp + 10)
        v7_state, _ = add_bundle("campaign-v7", base_stamp + 20)

        with (v7_state / "controller.run.lock").open("r") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            payload = server.discovery_live_payload()

        self.assertTrue(payload["active"])
        self.assertEqual(payload["deployment"], "campaign-v7")
        self.assertEqual(payload["activity"]["status"], "running")
        self.assertFalse(payload["newest_unlaunched_deployment"]["available"])


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
  id, textContent: "", innerHTML: "", className: "", style: {},
  scrollTop: 0, scrollHeight: 100
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
  className: node.className, scrollTop: node.scrollTop,
  scrollHeight: node.scrollHeight
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
        for detail_id in ("ak-live-details", "ak-live-full-details",
                          "planner-live-full-details"):
            disclosure = re.search(
                rf"<details\b([^>]*)\bid=\"{detail_id}\"([^>]*)>", html, re.I)
            self.assertIsNotNone(disclosure, f"missing {detail_id} disclosure")
            self.assertNotRegex("".join(disclosure.groups()), r"\bopen\b",
                                f"{detail_id} must be collapsed by default")
        live_panel = re.search(
            r'<section class="panel" id="autokernel-live-panel">(.*?)</section>',
            html, re.S)
        self.assertIsNotNone(live_panel)
        self.assertLess(live_panel.group(1).index('id="ak-live-log"'),
                        live_panel.group(1).index('id="ak-live-full-details"'),
                        "compact AutoKernel tail must remain outside its disclosure")
        actor_panel = re.search(
            r'<section class="panel" id="planner-live-panel">(.*?)</section>',
            html, re.S)
        self.assertIsNotNone(actor_panel)
        self.assertLess(actor_panel.group(1).index('id="planner-live-log"'),
                        actor_panel.group(1).index('id="planner-live-full-details"'),
                        "compact actor tail must remain outside its disclosure")

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
        detail_meta = nodes["ak-live-detail-meta"]["innerHTML"]
        last_transition = nodes["ak-live-last-transition"]["innerHTML"]
        timeline = nodes["ak-live-timeline"]["textContent"] + nodes[
            "ak-live-timeline"]["innerHTML"]
        history_summary = nodes["ak-live-history-summary"]["textContent"]
        history_rows = nodes["ak-live-history-rows"]["textContent"] + nodes[
            "ak-live-history-rows"]["innerHTML"]

        for token in ("Planning", "GPU", "not expected"):
            self.assertIn(token.lower(), summary.lower())
        for token in ("healthy", "planner model response",
                      "No completed durable checkpoint"):
            self.assertIn(token.lower(), detail_meta.lower())
        self.assertRegex(summary, r"(?i)(95\s*s|1\s*m(?:in)?\s*35)",
                         "phase elapsed time is not visibly rendered")
        self.assertIn("Planner started", timeline)
        self.assertIn("Planner started", last_transition)
        self.assertIn("2 abandoned", history_summary)
        self.assertIn("1 retest", history_summary)
        self.assertIn("akh-old-a", history_rows)
        self.assertIn("akh-retest", history_rows)

    def test_live_pulse_tail_stays_visible_but_full_stream_and_detail_collapse(self) -> None:
        events = [
            {"ts": f"2026-08-18T19:5{i}:00Z", "channel": "planner",
             "event": f"producer_event_{i}", "hypothesis_id": "akh-q5",
             "model": "gpt-5.6-sol"}
            for i in range(8)
        ]
        events[-1] = {
            "ts": "2026-08-18T19:58:00Z", "channel": "autokernel",
            "event": "critic_completed", "hypothesis_id": "akh-q5",
            "model": "claude-fable-5", "result": {"decision": "accept"},
        }
        payload = {
            "active": True, "deployment": "campaign-pulse",
            "dashboard_observed_at": "2026-08-18T20:00:00Z",
            "status_message": "STALLED — critic",
            "autokernel_log": events, "planner_log": events[:-1],
            "_freshness": {"staleness_class": "aging"},
            "activity": {
                "status": "stalled", "last_progress_at": "2026-08-18T19:58:00Z",
                "progress_age_s": 120,
                "phase": {"id": "critic", "label": "Critic review",
                          "elapsed_s": 240},
                "hypothesis_id": "akh-q5", "turn": 1,
                "waiting_on": "hidden critic method detail",
                "gpu": {"expected_now": False, "claim_held": False,
                        "detail": "GPU not expected during critic"},
                "correctness": {"execution_started": False},
                "checkpoint": {"available": True,
                               "state": "hidden-checkpoint-state"},
                "stall": {"state": "stalled", "detail": "hidden stall prose"},
                "failure": {"detected": False},
                "resume": {"required": False, "possible": True},
                "pipeline": [{"id": "critic", "label": "hidden pipeline row",
                              "state": "running"}],
                "transitions": [
                    {"ts": "2026-08-18T19:58:00Z", "phase": "critic",
                     "event": "critic_completed", "label": "last visible transition"},
                ],
                "history": {"summary": "1 abandoned · 0 retest",
                            "rows": [{"turn": 0, "hypothesis_id": "hidden-history-row",
                                      "status": "abandoned"}]},
            },
        }
        nodes = self._render_live(payload)
        summary = nodes["ak-live-summary"]["innerHTML"]
        last = nodes["ak-live-last-transition"]["innerHTML"]
        detail = nodes["ak-live-detail-meta"]["innerHTML"]
        compact = nodes["ak-live-log"]["textContent"]
        actor = nodes["planner-live-log"]["textContent"]
        full = nodes["ak-live-log-full"]["textContent"]

        for token in ("STALLED", "Critic review", "4 min", "akh-q5",
                      "Turn", "GPU", "no claim"):
            self.assertIn(token.lower(), summary.lower())
        self.assertIn("last visible transition", last)
        for hidden in ("hidden critic method detail", "hidden-checkpoint-state",
                       "hidden stall prose"):
            self.assertNotIn(hidden, summary)
            self.assertIn(hidden, detail)
        self.assertIn("producer last 2026-08-18T19:58:00Z · age 2 min", compact)
        self.assertIn("dashboard poll 2026-08-18T20:00:00Z (not producer progress)",
                      compact)
        self.assertNotIn("producer_event_0", compact)
        self.assertIn("producer_event_2", compact)
        self.assertIn("producer_event_0", full)
        self.assertIn("critic_completed", actor)
        for node_id in ("ak-live-log", "planner-live-log", "ak-live-log-full",
                        "planner-live-log-full"):
            self.assertEqual(nodes[node_id]["scrollTop"],
                             nodes[node_id]["scrollHeight"], node_id)

    def test_planner_validation_interruption_is_visible_in_hero_and_pipeline(self) -> None:
        payload = {
            "active": False,
            "observed_at": _iso(0),
            "deployment": "campaign-v7",
            "autokernel_log": [],
            "planner_log": [],
            "_freshness": {"staleness_class": "fresh"},
            "activity": {
                "status": "failed",
                "phase": {"id": "planner_validation",
                          "label": "Controller stopped during planner validation",
                          "elapsed_s": 30},
                "stall": {"state": "failed",
                          "detail": "planner validation interrupted"},
                "waiting_on": "fresh sealed deployment after controller repair",
                "hypothesis_id": None,
                "turn": None,
                "gpu": {"expected_now": False, "claim_held": False,
                        "detail": "GPU screening was not reached"},
                "checkpoint": {"available": False,
                               "detail": "no durable controller checkpoint"},
                "resume": {"required": True, "possible": False,
                           "detail": "Cannot resume; repair the controller and launch a fresh sealed deployment"},
                "failure": {
                    "detected": True, "stage": "planner_validation",
                    "detail": "Controller stopped after the planner actor completed; the producer did not persist the exact planner-validation exception.",
                    "recovery": "Do not resume this attempt; repair the controller and launch a fresh sealed deployment.",
                },
                "pipeline": [
                    {"id": "planner", "label": "Planner", "state": "complete"},
                    {"id": "planner_validation",
                     "label": "Validate planner output", "state": "failed"},
                    {"id": "critic", "label": "Critic review",
                     "state": "not_reached"},
                ],
                "transitions": [],
                "history": {"abandoned_count": 0, "retest_count": 0,
                            "summary": "0 abandoned · 0 retest", "rows": []},
            },
        }

        nodes = self._render_live(payload)
        summary = nodes["ak-live-summary"]["innerHTML"]
        pipeline = nodes["ak-live-pipeline"]["innerHTML"]

        for token in ("failed", "planner validation", "did not persist",
                      "fresh sealed deployment", "GPU screening was not reached"):
            self.assertIn(token.lower(), summary.lower())
        self.assertIn("Planner", pipeline)
        self.assertIn("complete", pipeline)
        self.assertIn("Validate planner output", pipeline)
        self.assertIn("failed", pipeline)
        self.assertIn("Critic review", pipeline)
        self.assertIn("not_reached", pipeline)

    def test_active_critic_pending_is_visible_in_hero_and_pipeline(self) -> None:
        payload = {
            "active": True,
            "observed_at": _iso(0),
            "deployment": "campaign-v8",
            "autokernel_log": [],
            "planner_log": [],
            "_freshness": {"staleness_class": "fresh"},
            "activity": {
                "status": "running",
                "phase": {"id": "critic", "label": "Critic review",
                          "elapsed_s": 30},
                "stall": {"state": "healthy",
                          "detail": "durable lifecycle is advancing"},
                "waiting_on": "critic review completion",
                "hypothesis_id": "akh-v2-q5-type-specific-dequant",
                "turn": 1,
                "gpu": {"expected_now": False, "claim_held": False,
                        "detail": "no identity-bound GPU claim is evidenced"},
                "checkpoint": {"available": True, "kind": "STOP_STATE",
                               "state": "discovery_planner_checkpointed",
                               "seq": 3},
                "resume": {"required": False, "possible": True},
                "failure": {"detected": False},
                "pipeline": [
                    {"id": "planner", "label": "Planner", "state": "complete"},
                    {"id": "planner_validation",
                     "label": "Validate planner output", "state": "complete"},
                    {"id": "critic", "label": "Critic review", "state": "running"},
                    {"id": "authorization", "label": "Governance authorization",
                     "state": "not_reached"},
                    {"id": "resource_admission", "label": "Resource admission",
                     "state": "not_reached"},
                ],
                "transitions": [],
                "history": {"abandoned_count": 0, "retest_count": 0,
                            "summary": "0 abandoned · 0 retest", "rows": []},
            },
        }

        nodes = self._render_live(payload)
        summary = nodes["ak-live-summary"]["innerHTML"]
        pipeline = nodes["ak-live-pipeline"]["innerHTML"]
        detail_meta = nodes["ak-live-detail-meta"]["innerHTML"]

        for token in ("running", "campaign-v8", "Critic review",
                      "akh-v2-q5-type-specific-dequant", "not expected now"):
            self.assertIn(token.lower(), summary.lower())
        for token in ("critic review completion", "discovery_planner_checkpointed"):
            self.assertIn(token.lower(), detail_meta.lower())
        self.assertIn("Critic review", pipeline)
        self.assertIn("running", pipeline)
        self.assertIn("Resource admission", pipeline)
        self.assertIn("not_reached", pipeline)

    def test_v10_correctness_parser_terminal_is_visible_in_hero_and_pipeline(self) -> None:
        payload = {
            "active": False,
            "deployment": "gpu-discovery-quant-ladder-occupancy-v10",
            "activity": {
                "status": "failed",
                "phase": {"id": "correctness_validation",
                          "label": "Correctness result parsing failed after GPU proof",
                          "elapsed_s": 2},
                "waiting_on": "fresh candidate attempt after controller repair",
                "gpu": {"expected_now": False, "claim_held": False,
                        "screen_started": True, "claim_released": True,
                        "detail": ("GPU correctness ran for 55.4s; "
                                   "1139/1139 tests passed; claim released")},
                "correctness": {"execution_started": True,
                                "execution_completed": True,
                                "validation_passed": False,
                                "summary": "1139/1139 tests passed",
                                "elapsed_s": 55.4},
                "checkpoint": {"available": True,
                               "state": "discovery_screen_ambiguous"},
                "stall": {"state": "failed",
                          "detail": ("EvidenceProducerError: correctness stdout "
                                     "must contain exactly one summary")},
                "resume": {"required": True, "possible": False,
                           "detail": "Cannot resume this ambiguous inflight operation"},
                "failure": {"detected": True,
                            "stage": "correctness_validation",
                            "detail": ("EvidenceProducerError: correctness stdout "
                                       "must contain exactly one summary"),
                            "recovery": "Launch a fresh sealed deployment after repair"},
                "pipeline": [
                    {"id": "source_materialization",
                     "label": "Source validation / materialization", "state": "complete"},
                    {"id": "build", "label": "Compile anchor and candidate",
                     "state": "complete"},
                    {"id": "evidence_binding", "label": "Bind build to proof plan",
                     "state": "complete"},
                    {"id": "correctness", "label": "Correctness proof",
                     "state": "complete"},
                    {"id": "correctness_validation",
                     "label": "Validate correctness result", "state": "failed"},
                    {"id": "dispatch_proof", "label": "Dispatch attribution",
                     "state": "not_reached"},
                    {"id": "profile", "label": "Kernel profile",
                     "state": "not_reached"},
                    {"id": "benchmark", "label": "Whole-model benchmark",
                     "state": "not_reached"},
                ],
                "transitions": [],
                "history": {"summary": "0 abandoned · 0 retest", "rows": []},
            },
            "autokernel_log": [], "planner_log": [],
            "_freshness": {"staleness_class": "fresh"},
        }

        nodes = self._render_live(payload)
        summary = nodes["ak-live-summary"]["innerHTML"]
        pipeline = nodes["ak-live-pipeline"]["innerHTML"]

        for token in (
                "FAILED", "Correctness result parsing failed after GPU proof",
                "EvidenceProducerError", "correctness stdout must contain exactly one summary",
                "GPU correctness", "execution complete", "1139/1139 tests passed",
                "claim released", "not expected now"):
            self.assertIn(token.lower(), summary.lower(), token)
        for token in (
                "Source validation / materialization", "Compile anchor and candidate",
                "Bind build to proof plan", "Correctness proof", "complete",
                "Validate correctness result", "failed", "Dispatch attribution",
                "Kernel profile", "Whole-model benchmark", "not_reached"):
            self.assertIn(token.lower(), pipeline.lower(), token)

    def test_failed_campaign_and_newer_unlaunched_bundle_render_separately(self) -> None:
        payload = {
            "active": False,
            "observed_at": _iso(0),
            "deployment": "campaign-v5",
            "newest_unlaunched_deployment": {
                "available": True,
                "deployment": "campaign-v6",
                "launch_state": "not_launched",
            },
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
        detail_meta = nodes["ak-live-detail-meta"]["innerHTML"]
        for token in ("failed", "Source materialization failed",
                      "SourceCandidateError",
                      "Cannot resume", "GPU screening was not reached",
                      "Repair source declaration", "campaign-v5"):
            self.assertIn(token.lower(), summary.lower())
        for token in ("discovery_screen_ambiguous",
                      "Available next deployment", "campaign-v6",
                      "sealed, not launched"):
            self.assertIn(token.lower(), detail_meta.lower())

    def test_every_cross_strategy_stage_has_a_compact_dom_headline(self) -> None:
        stages = (
            "correctness", "correctness_validation", "candidate_attribution",
            "anchor_attribution", "measurement_graphs_off_screen",
            "target_runtime_graphs_on_screen", "decision", "replication_s1",
            "replication_s2", "next_hypothesis",
        )
        for index, stage in enumerate(stages, 1):
            with self.subTest(stage=stage):
                payload = {
                    "active": True, "deployment": "campaign-stage-dom",
                    "dashboard_observed_at": _iso(0),
                    "autokernel_log": [{
                        "ts": _iso(1), "channel": "autokernel",
                        "event": stage + "_started", "hypothesis_id": "akh-stage",
                        "result": {"stage": stage,
                                   "first_incomplete_stage": stage,
                                   "replication": "S2",
                                   "arm_order_schedule": ["anchor", "candidate"]},
                    }],
                    "planner_log": [],
                    "_freshness": {"staleness_class": "fresh"},
                    "activity": {
                        "status": "running", "last_progress_at": _iso(1),
                        "progress_age_s": 1,
                        "phase": {"id": stage,
                                  "label": stage.replace("_", " "),
                                  "elapsed_s": index},
                        "hypothesis_id": "akh-stage", "turn": 2,
                        "waiting_on": stage + " completion",
                        "gpu": {"expected_now": stage in {
                            "correctness", "candidate_attribution",
                            "anchor_attribution", "measurement_graphs_off_screen",
                            "target_runtime_graphs_on_screen"},
                            "claim_held": True,
                            "detail": "MI210 source-proof claim is held"},
                        "correctness": {"execution_started": stage != "correctness"},
                        "checkpoint": {"available": True,
                                       "state": "resume-stage-fixture"},
                        "resume": {"required": False, "possible": True,
                                   "disposition": "resume_first_incomplete_stage"},
                        "stall": {"state": "healthy", "detail": "advancing"},
                        "failure": {"detected": False},
                        "refusal": {"detected": False},
                        "stage_contract": {
                            "current_stage": stage,
                            "first_incomplete_stage": stage,
                            "resume_policy": "execute_once_from_first_incomplete",
                            "replication": "S2",
                            "arm_order": ["anchor", "candidate"],
                            "arm_order_seed_sha256": "a" * 64,
                        },
                        "pipeline": [{"id": stage,
                                      "label": stage.replace("_", " "),
                                      "state": "running"}],
                        "transitions": [{"ts": _iso(1), "phase": stage,
                                         "label": stage + " started"}],
                        "history": {"summary": "0 abandoned · 0 retest",
                                    "rows": []},
                    },
                }
                nodes = self._render_live(payload)
                hero = nodes["ak-live-summary"]["innerHTML"]
                pulse = nodes["ak-live-log"]["textContent"]
                self.assertIn(stage.replace("_", " "), hero)
                for token in ("First incomplete", "S2", "anchor → candidate",
                              "claim held"):
                    self.assertIn(token.lower(), hero.lower(), token)
                self.assertIn("stage=" + stage, pulse)

    def test_typed_refusal_and_restart_checkpoint_are_headline_visible(self) -> None:
        for refusal in ("authoring_refused", "critic_refused", "compile_refused",
                        "correctness_falsified", "attribution_route_falsified"):
            with self.subTest(refusal=refusal):
                payload = {
                    "active": False, "deployment": "campaign-refusal",
                    "autokernel_log": [], "planner_log": [],
                    "_freshness": {"staleness_class": "fresh"},
                    "activity": {
                        "status": "stopped",
                        "phase": {"id": "candidate_attribution",
                                  "label": "Controller stopped", "elapsed_s": 2},
                        "gpu": {"expected_now": True, "claim_held": False,
                                "claim_released": True,
                                "detail": "source-proof claim released"},
                        "stage_contract": {
                            "first_incomplete_stage": "candidate_attribution",
                            "resume_policy": "execute_once_from_first_incomplete",
                        },
                        "refusal": {"detected": True, "type": refusal,
                                    "detail": "typed fixture"},
                        "resume": {"required": True, "possible": True,
                                   "detail": "Resume at candidate_attribution"},
                        "failure": {"detected": False},
                        "correctness": {"execution_started": True,
                                        "execution_completed": True,
                                        "summary": "1/1 tests passed"},
                        "checkpoint": {"available": True,
                                       "state": "candidate_attribution_complete"},
                        "stall": {"state": "healthy", "detail": "stopped"},
                        "waiting_on": "resume",
                        "pipeline": [], "transitions": [],
                        "history": {"summary": "0 abandoned · 0 retest",
                                    "rows": []},
                    },
                }
                hero = self._render_live(payload)["ak-live-summary"]["innerHTML"]
                for token in (refusal, "candidate_attribution", "claim released",
                              "Resume at candidate_attribution"):
                    self.assertIn(token.lower(), hero.lower(), token)

    def test_only_pulse_and_headline_surfaces_are_open_by_default(self) -> None:
        html = PAGE.read_text(encoding="utf-8")
        progression = re.search(
            r'<details\b([^>]*)\bid="progression-panel"([^>]*)>', html, re.I)
        self.assertIsNotNone(progression)
        self.assertNotRegex("".join(progression.groups()), r"\bopen\b")
        self.assertLess(html.index('id="autokernel-live-panel"'),
                        html.index('id="progression-panel"'))
        self.assertLess(html.index('id="planner-live-panel"'),
                        html.index('id="progression-panel"'))
        for log_id in ("ak-live-log", "planner-live-log"):
            self.assertRegex(html, rf'<pre class="live-log" id="{log_id}">',
                             log_id)

    def test_provider_retry_checkpoint_is_visible_without_looking_terminal(self) -> None:
        payload = {
            "active": False, "deployment": "campaign-provider-retry",
            "autokernel_log": [], "planner_log": [],
            "_freshness": {"staleness_class": "fresh"},
            "activity": {
                "status": "stopped",
                "phase": {"id": "critic",
                          "label": "Critic provider interrupted", "elapsed_s": 3},
                "gpu": {"expected_now": False, "claim_held": False,
                        "detail": "GPU not expected"},
                "stage_contract": {"first_incomplete_stage": "critic",
                                   "resume_policy": "resume_critic_provider_retry"},
                "refusal": {"detected": False},
                "provider_retry": {"detected": True, "actor": "critic",
                                   "same_hypothesis": False,
                                   "planner_rerun": False,
                                   "detail": "critic_pending is durable"},
                "resume": {"required": True, "possible": True,
                           "detail": "retry only the critic"},
                "failure": {"detected": False},
                "correctness": {"execution_started": False},
                "checkpoint": {"available": True, "state": "critic_pending"},
                "stall": {"state": "healthy", "detail": "checkpointed"},
                "waiting_on": "controller restart", "pipeline": [],
                "transitions": [],
                "history": {"summary": "0 abandoned · 0 retest", "rows": []},
            },
        }
        hero = self._render_live(payload)["ak-live-summary"]["innerHTML"]
        for token in ("Provider retry", "critic", "checkpoint preserved",
                      "planner will not rerun", "retry only the critic"):
            self.assertIn(token.lower(), hero.lower(), token)
        self.assertNotIn("Typed refusal", hero)

    def test_nonpositive_exact_measurement_explains_graphs_on_short_circuit(self) -> None:
        payload = {
            "active": True, "deployment": "campaign-short-circuit",
            "autokernel_log": [], "planner_log": [],
            "_freshness": {"staleness_class": "fresh"},
            "activity": {
                "status": "running",
                "phase": {"id": "decision", "label": "Classify result",
                          "elapsed_s": 1},
                "gpu": {"expected_now": False, "claim_held": False,
                        "claim_released": True, "detail": "claim released"},
                "stage_contract": {
                    "first_incomplete_stage": "decision",
                    "exact_attribution_direction": "neutral",
                    "exact_attribution_effect_fraction": 0.0,
                    "target_runtime_executed": False,
                    "target_runtime_reason": "nonpositive_exact_duration",
                    "dual_decision_state": "measured_nonpositive_exact_short_circuit",
                },
                "refusal": {"detected": False},
                "provider_retry": {"detected": False},
                "resume": {"required": False, "possible": True},
                "failure": {"detected": False},
                "correctness": {"execution_started": True,
                                "execution_completed": True,
                                "summary": "1/1 tests passed"},
                "checkpoint": {"available": True, "state": "exact_measured"},
                "stall": {"state": "healthy", "detail": "advancing"},
                "waiting_on": "classification",
                "pipeline": [
                    {"id": "measurement_graphs_off_screen",
                     "label": "Graphs-off measurement screen", "state": "skipped",
                     "detail": "exact attribution was nonpositive"},
                    {"id": "target_runtime_graphs_on_screen",
                     "label": "Graphs-on target-runtime screen", "state": "skipped",
                     "detail": "short-circuited by exact attribution"},
                ],
                "transitions": [],
                "history": {"summary": "0 abandoned · 0 retest", "rows": []},
            },
        }
        nodes = self._render_live(payload)
        hero = nodes["ak-live-summary"]["innerHTML"]
        pipeline = nodes["ak-live-pipeline"]["innerHTML"]
        for token in ("Exact attribution", "neutral", "Graphs-on runtime",
                      "skipped", "nonpositive_exact_duration",
                      "measured_nonpositive_exact_short_circuit"):
            self.assertIn(token.lower(), hero.lower(), token)
        for token in ("Graphs-off measurement screen", "Graphs-on target-runtime screen",
                      "short-circuited by exact attribution"):
            self.assertIn(token.lower(), pipeline.lower(), token)


if __name__ == "__main__":
    unittest.main()
