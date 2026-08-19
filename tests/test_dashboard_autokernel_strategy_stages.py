from __future__ import annotations

from datetime import datetime, timedelta, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from dashboard import server


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sealed(body: dict) -> dict:
    key = "result_sha256" if body["schema"] in {
        "epyc.autokernel.gpu_candidate_only_screen.v2",
        "epyc.autokernel.exact_attribution_outcome.v1",
    } else "receipt_sha256"
    value = dict(body)
    value[key] = hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return value


class AutoKernelStrategyStageApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.old_root = server.AUTOKERNEL_DEPLOYMENTS_ROOT
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name) / "deployments"
        self.bundle = root / "campaign-stage-fixture"
        self.state_root = self.bundle / "state"
        self.operations = self.bundle / "operations"
        (self.bundle / "config").mkdir(parents=True)
        self.state_root.mkdir()
        (self.operations / "live").mkdir(parents=True)
        (self.state_root / "controller.run.lock").touch()
        (self.bundle / "config/deployment.json").write_text(json.dumps({
            "config_sha256": "a" * 64,
            "controller": {"state_root": str(self.state_root),
                           "operations_root": str(self.operations)},
        }))
        self.operation_key = "8" * 64
        self.manifest_sha = "b" * 64
        self.operation = self.operations / self.operation_key
        self.operation.mkdir()
        (self.operation / "intent.json").write_text(json.dumps({
            "schema": "epyc.autokernel.gpu_source_operation.v1",
            "operation_key": self.operation_key,
            "manifest_sha256": self.manifest_sha,
        }))
        (self.operation / "evidence-policy.json").write_text(json.dumps({
            "schema": "epyc.autokernel.gpu_source_execution_policy.v2",
            "manifest_sha256": self.manifest_sha,
            "attribution_arm_order": ["candidate", "anchor"],
            "attribution_arm_order_seed_sha256": "c" * 64,
        }))
        self.proposal_sha = "e" * 64
        build_key = "d" * 64
        entry = self.operations / "build-cache/entries" / build_key
        entry.mkdir(parents=True)
        contract = {
            "build_key": build_key,
            "patch_bundle_sha256": self.manifest_sha,
            "proposal_sha256": self.proposal_sha,
            "deployment_config_sha256": "a" * 64,
        }
        intent_path = entry / "intent.json"
        intent_path.write_text(json.dumps({
            "schema": "epyc.autokernel.gpu_source_build_intent.v1",
            "build_key": build_key, "build_contract": contract,
        }))
        materialization_path = entry / "materialization.json"
        materialization_path.write_text(json.dumps(_sealed({
            "schema": "epyc.autokernel.gpu_source_materialization.v1",
            "authority": "nonpromotable_candidate_only_discovery",
            "operation_key": build_key, "build_key": build_key,
            "build_contract": contract, "manifest_sha256": self.manifest_sha,
            "promotion_claim": False,
        })) + "\n")
        (entry / "terminal.json").write_text(json.dumps(_sealed({
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
        })) + "\n")
        self._write_state(repetition=1)
        server.AUTOKERNEL_DEPLOYMENTS_ROOT = root

    def tearDown(self) -> None:
        server.AUTOKERNEL_DEPLOYMENTS_ROOT = self.old_root
        self.temp.cleanup()

    def _write_state(self, *, repetition: int) -> None:
        (self.state_root / "state.json").write_text(json.dumps({
            "updated_at": _now(), "next": repetition, "complete": False,
            "iterations": [],
            "inflight": {
                "operation_key": self.operation_key,
                "candidate": {"source_manifest_sha256": self.manifest_sha,
                              "hypothesis_id": "akh-stage-fixture"},
                "row": {"hypothesis_id": "akh-stage-fixture",
                        "proposal_sha256": self.proposal_sha},
                "lease": {"admitted": True, "device_id": "mi210_0",
                          "repetition": repetition},
            },
        }))

    def _receipt(self, relative: str, schema: str, **fields: object) -> None:
        path = self.operation / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        base = {
            "schema": schema,
            "authority": "nonpromotable_candidate_only_discovery",
            "promotion_claim": False,
            "manifest_sha256": self.manifest_sha,
            "ended_at": _now(),
            **({"non_promotable": True, "hip_residency_proved": True}
               if schema == "epyc.autokernel.gpu_candidate_only_screen.v2"
               else {}),
            **fields,
        }
        path.write_text(json.dumps(_sealed(base), sort_keys=True) + "\n")

    def _active(self) -> dict:
        with (self.state_root / "controller.run.lock").open("r") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return server.discovery_live_payload()

    def test_receipts_advance_every_exact_postbuild_stage_once(self) -> None:
        expected = [
            "correctness", "candidate_attribution", "anchor_attribution",
            "measurement_graphs_off_screen",
            "target_runtime_graphs_on_screen", "decision",
        ]
        payload = self._active()
        self.assertEqual(payload["activity"]["stage_contract"]["first_incomplete_stage"],
                         expected[0])

        self._receipt("proof/correctness/receipt.json",
                      "epyc.autokernel.targeted_correctness_receipt.v3",
                      status="complete", result="PASS")
        self.assertEqual(self._active()["activity"]["phase"]["id"], expected[1])

        self._receipt("proof/attribution-candidate/receipt.json",
                      "epyc.autokernel.gpu_kernel_attribution.v2",
                      status="complete", result="PASS")
        self.assertEqual(self._active()["activity"]["phase"]["id"], expected[2])

        self._receipt("proof/attribution-anchor/receipt.json",
                      "epyc.autokernel.gpu_kernel_attribution.v2",
                      status="complete", result="PASS")
        self._receipt("proof/attribution-pair.json",
                      "epyc.autokernel.gpu_kernel_attribution_pair.v1",
                      attribution_arm_order=["candidate", "anchor"],
                      attribution_arm_order_seed_sha256="c" * 64,
                      exact_duration_comparison={
                          "direction": "improved",
                          "relative_improvement_fraction": 0.01})
        self._receipt("proof/proof-bundle.json",
                      "epyc.autokernel.gpu_source_evidence_bundle.v1")
        after_attribution = self._active()["activity"]
        self.assertEqual(after_attribution["phase"]["id"], expected[3])
        self.assertEqual(after_attribution["stage_contract"]["arm_order"],
                         ["candidate", "anchor"])
        self.assertEqual(after_attribution["stage_contract"]
                         ["exact_attribution_direction"], "improved")

        self._receipt("runner/s1/measurement-graphs-off/result.json",
                      "epyc.autokernel.gpu_candidate_only_screen.v2",
                      status="complete", state="decided", ok=True,
                      runtime_graphs="off",
                      arm_order_schedule=["candidate", "anchor"])
        self.assertEqual(self._active()["activity"]["phase"]["id"], expected[4])

        self._receipt("runner/s1/target-runtime-graphs-on/result.json",
                      "epyc.autokernel.gpu_candidate_only_screen.v2",
                      status="complete", state="decided", ok=True,
                      median_relative=0.025, runtime_graphs="on",
                      arm_order_schedule=["candidate", "anchor"])
        decided = self._active()["activity"]
        self.assertEqual(decided["phase"]["id"], expected[5])
        self.assertIsNone(decided["stage_contract"]["replication"])
        self.assertEqual(decided["stage_contract"]
                         ["target_runtime_effect_fraction"], 0.025)
        self.assertEqual(decided["stage_contract"]["dual_decision_state"],
                         "exact_and_graphs_on_complete")
        pipeline = {row["id"]: row["state"] for row in decided["pipeline"]}
        for stage in ("correctness", "correctness_validation",
                      "candidate_attribution", "anchor_attribution",
                      "measurement_graphs_off_screen",
                      "target_runtime_graphs_on_screen", "benchmark"):
            self.assertEqual(pipeline[stage], "complete", stage)

    def test_live_source_claim_starts_correctness_clock_at_claim_acquisition(self) -> None:
        """v11: a held correctness claim must not inherit pre-screen time."""
        acquired_at = _now()
        holder_pid = os.getpid()
        holder_start_ticks = int((Path("/proc") / str(holder_pid) / "stat")
                                 .read_text().split()[21])
        claims = self.operations / "claims"
        claims.mkdir()
        receipt = {
            "schema": "epyc.autokernel.device_claim_receipt.v1",
            "claim_id": "akd-1a2840d5bfe6433e",
            "campaign_id": "ak-discovery-" + "a" * 16,
            "device_id": "mi210_0",
            "purpose": "AutoKernel GPU source proof and throughput",
            "holder_pid": holder_pid,
            "holder_start_ticks": holder_start_ticks,
            "acquired_at": acquired_at,
            "released_at": None,
        }
        (claims / "device.jsonl").write_text(json.dumps({
            "schema": "epyc.autokernel.device_claim_journal.v1",
            "kind": "claim_acquired", "created_at": acquired_at,
            "detail": {"receipt": receipt},
        }) + "\n")

        activity = self._active()["activity"]

        self.assertEqual(activity["phase"]["id"], "correctness")
        self.assertEqual(activity["phase"]["started_at"], acquired_at)
        self.assertLess(activity["phase"]["elapsed_s"], 5)
        self.assertTrue(activity["correctness"]["execution_started"])
        self.assertFalse(activity["correctness"]["execution_completed"])
        self.assertEqual(activity["correctness"]["started_at"], acquired_at)
        self.assertTrue(activity["gpu"]["claim_held"])
        self.assertTrue(activity["gpu"]["expected_now"])
        self.assertEqual(activity["stall"]["state"], "healthy")
        pipeline = {row["id"]: row for row in activity["pipeline"]}
        self.assertEqual(pipeline["correctness"]["state"], "running")
        self.assertEqual(activity["transitions"][-1]["event"],
                         "correctness_execution_started")

    def test_live_correctness_claim_uses_governed_1800_second_budget(self) -> None:
        acquired_at = (datetime.now(timezone.utc) - timedelta(seconds=600)
                       ).isoformat().replace("+00:00", "Z")
        holder_pid = os.getpid()
        holder_start_ticks = int((Path("/proc") / str(holder_pid) / "stat")
                                 .read_text().split()[21])
        claims = self.operations / "claims"
        claims.mkdir()
        receipt = {
            "schema": "epyc.autokernel.device_claim_receipt.v1",
            "claim_id": "akd-correctness-budget",
            "campaign_id": "ak-discovery-" + "a" * 16,
            "device_id": "mi210_0",
            "purpose": "AutoKernel GPU source proof and throughput",
            "holder_pid": holder_pid,
            "holder_start_ticks": holder_start_ticks,
            "acquired_at": acquired_at,
            "released_at": None,
        }
        (claims / "device.jsonl").write_text(json.dumps({
            "schema": "epyc.autokernel.device_claim_journal.v1",
            "kind": "claim_acquired", "created_at": acquired_at,
            "detail": {"receipt": receipt},
        }) + "\n")

        activity = self._active()["activity"]

        self.assertEqual(activity["phase"]["id"], "correctness")
        self.assertGreater(activity["phase"]["elapsed_s"], 590)
        self.assertEqual(activity["stall"]["state"], "healthy")
        self.assertEqual(activity["stall"]["threshold_s"], 1800.0)

    def test_v11_runtime_identity_failure_is_candidate_attribution_terminal(self) -> None:
        started_at = "2026-08-18T22:55:06.002345+00:00"
        ended_at = "2026-08-18T22:56:01.130533Z"
        build_completed = datetime.fromisoformat(
            "2026-08-18T22:55:04.585924+00:00").timestamp()
        terminal = self.operations / "build-cache/entries" / ("d" * 64) / "terminal.json"
        os.utime(terminal, (build_completed, build_completed))
        state = json.loads((self.state_root / "state.json").read_text())
        state["updated_at"] = "2026-08-18T22:56:02.752711Z"
        state["inflight"]["exception"] = {
            "type": "EvidenceProducerError",
            "message": ("rocprof/candidate execution failed: runtime maps must "
                        "prove exactly one owned KFD process for the sealed arm"),
        }
        (self.state_root / "state.json").write_text(json.dumps(state))
        self._receipt(
            "proof/correctness/receipt.json",
            "epyc.autokernel.targeted_correctness_receipt.v3",
            status="complete", result="PASS", overall="OK",
            passed_cases=1139, expected_cases=1139, ended_at=ended_at,
            device_claim_open={
                "schema": "epyc.autokernel.device_claim_receipt.v1",
                "campaign_id": "ak-discovery-" + "a" * 16,
                "claim_id": "akd-1a2840d5bfe6433e",
                "device_id": "mi210_0", "acquired_at": started_at,
            })
        attribution = self.operation / "proof/attribution-candidate"
        attribution.mkdir()
        (attribution / "stdout.txt").write_text("")
        (attribution / "stderr.txt").write_text(
            "runtime maps must prove exactly one owned KFD process\n")
        (attribution / "timestamps.csv").write_text(
            "start_ns,end_ns\n1,2\n")

        activity = server.discovery_live_payload()["activity"]

        self.assertEqual(activity["status"], "failed")
        self.assertEqual(activity["phase"]["id"], "candidate_attribution")
        self.assertEqual(activity["phase"]["label"],
                         "Candidate attribution failed during runtime identity binding")
        self.assertEqual(activity["failure"]["stage"], "candidate_attribution")
        self.assertIn("exactly one owned KFD process",
                      activity["failure"]["detail"])
        pipeline = {row["id"]: row["state"] for row in activity["pipeline"]}
        for stage in ("source_materialization", "build", "evidence_binding",
                      "correctness", "correctness_validation"):
            self.assertEqual(pipeline[stage], "complete", stage)
        self.assertEqual(pipeline["candidate_attribution"], "failed")
        for stage in ("anchor_attribution", "dispatch_proof", "profile",
                      "measurement_graphs_off_screen",
                      "target_runtime_graphs_on_screen", "decision"):
            self.assertEqual(pipeline[stage], "not_reached", stage)
        self.assertTrue(activity["correctness"]["execution_completed"])
        self.assertTrue(activity["correctness"]["validation_passed"])
        self.assertEqual(activity["correctness"]["summary"],
                         "1139/1139 tests passed")
        self.assertEqual(activity["correctness"]["started_at"], started_at)
        self.assertEqual(activity["correctness"]["completed_at"], ended_at)
        self.assertEqual(activity["transitions"][-1]["event"],
                         "candidate_attribution_failed")

    def test_v13_released_terminal_does_not_expect_gpu_now(self) -> None:
        acquired_at = "2026-08-18T23:52:50.625980+00:00"
        released_at = "2026-08-18T23:53:46.922940+00:00"
        state = json.loads((self.state_root / "state.json").read_text())
        state["updated_at"] = "2026-08-18T23:53:47.267355Z"
        state["inflight"]["exception"] = {
            "type": "EvidenceProducerError",
            "message": ("runtime maps did not prove the sealed arm during "
                        "child execution"),
        }
        (self.state_root / "state.json").write_text(json.dumps(state))
        self._receipt(
            "proof/correctness/receipt.json",
            "epyc.autokernel.targeted_correctness_receipt.v3",
            status="complete", result="PASS", overall="OK",
            passed_cases=1139, expected_cases=1139,
            ended_at="2026-08-18T23:53:45.559262Z",
            device_claim_open={
                "schema": "epyc.autokernel.device_claim_receipt.v1",
                "campaign_id": "ak-discovery-" + "a" * 16,
                "claim_id": "akd-a27c5e21725a4e37",
                "device_id": "mi210_0", "acquired_at": acquired_at,
            })
        attribution = self.operation / "proof/attribution-candidate"
        attribution.mkdir()
        for name in ("stdout.txt", "stderr.txt", "timestamps.csv"):
            (attribution / name).write_text("\n")
        claims = self.operations / "claims"
        claims.mkdir()
        receipt = {
            "schema": "epyc.autokernel.device_claim_receipt.v1",
            "campaign_id": "ak-discovery-" + "a" * 16,
            "claim_id": "akd-a27c5e21725a4e37", "device_id": "mi210_0",
            "purpose": "AutoKernel GPU source proof and throughput",
            "holder_pid": 2096922, "holder_start_ticks": 48012147,
            "acquired_at": acquired_at, "released_at": released_at,
        }
        (claims / "device.jsonl").write_text(json.dumps({
            "schema": "epyc.autokernel.device_claim_journal.v1",
            "kind": "claim_released", "created_at": released_at,
            "detail": {"receipt": receipt},
        }) + "\n")

        activity = server.discovery_live_payload()["activity"]

        self.assertEqual(activity["status"], "failed")
        self.assertEqual(activity["phase"]["id"], "candidate_attribution")
        self.assertEqual(activity["failure"]["stage"], "candidate_attribution")
        self.assertFalse(activity["gpu"]["expected_now"])
        self.assertFalse(activity["gpu"]["claim_held"])
        self.assertTrue(activity["gpu"]["claim_released"])
        self.assertTrue(activity["gpu"]["screen_started"])
        self.assertTrue(activity["correctness"]["execution_completed"])

    @mock.patch("dashboard.server.time.time", return_value=datetime.fromisoformat(
        "2026-08-19T01:55:00+00:00").timestamp())
    def test_v14_new_planner_turn_outranks_prior_authoring_refusal(
            self, _time: mock.Mock) -> None:
        receipt_path = self.state_root / "stage-outcomes/source-apply.json"
        receipt_path.parent.mkdir()
        receipt = _sealed({
            "schema": "epyc.autokernel.gpu_source_build_terminal.v1",
            "state": "failed", "failure_stage": "source_apply",
            "build_key": "f" * 64, "promotion_claim": False,
        })
        raw = (json.dumps(receipt, sort_keys=True, separators=(",", ":"))
               + "\n").encode()
        receipt_path.write_bytes(raw)
        refused_at = datetime.fromisoformat(
            "2026-08-19T01:45:16.613149+00:00").timestamp()
        os.utime(receipt_path, (refused_at, refused_at))
        (self.state_root / "state.json").write_text(json.dumps({
            "updated_at": "2026-08-19T01:45:16.621284Z",
            "next": 2, "complete": False,
            "iterations": [{
                "turn": 1,
                "hypothesis_id": "akh-v2-q5-type-specific-dequant",
                "status": "authoring_refused", "stage": "source_apply",
                "stage_receipt_path": str(receipt_path),
                "stage_receipt_sha256": hashlib.sha256(raw).hexdigest(),
                "scientific_budget_spent": False,
                "reason": "committed diff derives undeclared file-scope symbols",
            }],
            "planning": {"turn": 2, "provider_attempt": 1},
            "pending": None, "inflight": None,
        }))
        campaign = "ak-discovery-" + "a" * 16
        events = [
            ("planner", "planner_started", "2026-08-19T01:36:33.711555Z"),
            ("planner", "planner_completed", "2026-08-19T01:43:53.515551Z"),
            ("autokernel", "critic_started", "2026-08-19T01:43:53.927490Z"),
            ("autokernel", "critic_completed", "2026-08-19T01:45:13.425467Z"),
            ("planner", "planner_started", "2026-08-19T01:45:16.797464Z"),
        ]
        rows = [{
            "schema": server.AUTOKERNEL_DISCOVERY_EVENT_SCHEMA,
            "ts": ts, "channel": channel, "event": event,
            "campaign_id": campaign,
            "hypothesis_id": "akh-v2-q5-type-specific-dequant",
            "provider": "claude" if channel == "autokernel" else "codex",
            "model": "claude-fable-5" if channel == "autokernel" else "gpt-5.6-sol",
            "effort": "high",
        } for channel, event, ts in events]
        (self.operations / "live/autokernel.jsonl").write_text(
            "".join(json.dumps(row) + "\n" for row in rows))
        (self.operations / "live/planner.jsonl").write_text(
            "".join(json.dumps(row) + "\n" for row in rows
                    if row["channel"] == "planner"))
        journal = self.state_root / "journal"
        journal.mkdir()
        checkpoints = [
            (6, "discovery_authoring_refused",
             "2026-08-19T01:45:16.613149Z"),
            (8, "discovery_planner_entering",
             "2026-08-19T01:45:16.621284Z"),
        ]
        (journal / "events.jsonl").write_text("".join(json.dumps({
            "journal_schema": "epyc.autokernel.journal_entry.v1",
            "kind": "STOP_STATE", "seq": seq, "written_at": written_at,
            "payload": {"state": checkpoint_state,
                        "controller_state_sha256": "c" * 64},
        }) + "\n" for seq, checkpoint_state, written_at in checkpoints))

        activity = self._active()["activity"]

        self.assertEqual(activity["status"], "running")
        self.assertEqual(activity["turn"], 2)
        self.assertEqual(activity["phase"]["id"], "planner")
        self.assertEqual(activity["phase"]["label"], "Planner model call")
        self.assertEqual(activity["phase"]["started_at"],
                         "2026-08-19T01:45:16.797464Z")
        self.assertFalse(activity["refusal"]["detected"])
        pipeline = {row["id"]: row for row in activity["pipeline"]}
        self.assertEqual(pipeline["planner"]["state"], "running")
        self.assertNotIn("completed_at", pipeline["planner"])
        for stage in ("planner_validation", "critic", "authorization",
                      "source_materialization", "next_hypothesis"):
            self.assertEqual(pipeline[stage]["state"], "not_reached", stage)
        refusal_transition = next(
            row for row in activity["transitions"]
            if row["event"] == "discovery_authoring_refused")
        self.assertEqual(refusal_transition["ts"],
                         "2026-08-19T01:45:16.613149Z")
        self.assertEqual(activity["transitions"][-1]["event"], "planner_started")

        # Exact next live boundary: turn 2 planner has completed and the
        # controller has durably checkpointed/started its critic.  The prior
        # turn refusal must remain history, not retake the headline.
        state = json.loads((self.state_root / "state.json").read_text())
        state["planning"] = None
        state["pending"] = {
            "phase": "critic_pending", "turn": 2,
            "candidate": {"hypothesis_id": "akh-v2-q5-type-specific-dequant"},
            "row": {"hypothesis_id": "akh-v2-q5-type-specific-dequant"},
        }
        state["updated_at"] = "2026-08-19T01:52:10.921284Z"
        (self.state_root / "state.json").write_text(json.dumps(state))
        critic_started = {
            "schema": server.AUTOKERNEL_DISCOVERY_EVENT_SCHEMA,
            "ts": "2026-08-19T01:52:10.931000Z",
            "channel": "autokernel", "event": "critic_started",
            "campaign_id": campaign,
            "hypothesis_id": "akh-v2-q5-type-specific-dequant",
            "provider": "claude", "model": "claude-fable-5",
            "effort": "high",
        }
        with (self.operations / "live/autokernel.jsonl").open("a") as handle:
            handle.write(json.dumps(critic_started) + "\n")

        activity = self._active()["activity"]

        self.assertEqual(activity["status"], "running")
        self.assertEqual(activity["turn"], 2)
        self.assertEqual(activity["phase"]["id"], "critic")
        self.assertEqual(activity["phase"]["started_at"],
                         "2026-08-19T01:52:10.931000Z")
        self.assertFalse(activity["refusal"]["detected"])
        pipeline = {row["id"]: row for row in activity["pipeline"]}
        self.assertEqual(pipeline["planner"]["state"], "complete")
        self.assertEqual(pipeline["planner_validation"]["state"], "complete")
        self.assertEqual(pipeline["critic"]["state"], "running")
        for stage in ("authorization", "source_materialization", "build",
                      "correctness", "next_hypothesis"):
            self.assertEqual(pipeline[stage]["state"], "not_reached", stage)
        self.assertEqual(activity["transitions"][-1]["event"], "critic_started")

        build_key = "a" * 64
        current_manifest_sha = "1" * 64
        current_proposal_sha = "2" * 64
        build_entry = self.operations / "build-cache/entries" / build_key
        build_entry.mkdir(parents=True)
        (build_entry / "intent.json").write_text(json.dumps({
            "schema": "epyc.autokernel.gpu_source_build_intent.v1",
            "build_key": build_key,
            "build_contract": {
                "build_key": build_key,
                "patch_bundle_sha256": current_manifest_sha,
                "proposal_sha256": current_proposal_sha,
                "deployment_config_sha256": "a" * 64,
            },
        }))
        lock_path = self.operations / f"build-cache/locks/build-{build_key}.lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock_path.touch()
        state["pending"] = None
        state["inflight"] = {
            "operation_key": self.operation_key,
            "candidate": {
                "source_manifest_sha256": current_manifest_sha,
                "hypothesis_id": "akh-v2-q5-type-specific-dequant",
                "manifest": {"candidate_id": "akc-discovery-2"},
            },
            "row": {
                "turn": 2,
                "hypothesis_id": "akh-v2-q5-type-specific-dequant",
                "proposal_sha256": current_proposal_sha,
            },
            "lease": {"admitted": True, "device_id": "mi210_0",
                      "repetition": 1},
        }
        state["updated_at"] = "2026-08-19T01:54:13.140134Z"
        (self.state_root / "state.json").write_text(json.dumps(state))
        critic_completed = dict(critic_started)
        critic_completed.update({
            "ts": "2026-08-19T01:54:12.709191Z",
            "event": "critic_completed", "result": {"decision": "accept"},
        })
        with (self.operations / "live/autokernel.jsonl").open("a") as handle:
            handle.write(json.dumps(critic_completed) + "\n")
        with lock_path.open() as build_lock:
            fcntl.flock(build_lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            activity = self._active()["activity"]

        self.assertEqual(activity["status"], "running")
        self.assertEqual(activity["turn"], 2)
        self.assertEqual(activity["phase"]["id"], "build")
        self.assertFalse(activity["refusal"]["detected"])
        pipeline = {row["id"]: row for row in activity["pipeline"]}
        self.assertEqual(pipeline["source_materialization"]["state"], "running")
        self.assertEqual(pipeline["build"]["state"], "running")
        self.assertEqual(pipeline["next_hypothesis"]["state"], "not_reached")
        self.assertEqual(activity["transitions"][-1]["event"],
                         "build_transaction_observed")

    def test_stopped_operation_names_first_incomplete_resume_stage(self) -> None:
        self._receipt("proof/correctness/receipt.json",
                      "epyc.autokernel.targeted_correctness_receipt.v3",
                      status="complete", result="PASS")
        activity = server.discovery_live_payload()["activity"]
        self.assertEqual(activity["status"], "stopped")
        self.assertEqual(activity["phase"]["id"], "candidate_attribution")
        self.assertTrue(activity["resume"]["possible"])
        self.assertEqual(activity["stage_contract"]["first_incomplete_stage"],
                         "candidate_attribution")
        self.assertIn("Resume at candidate_attribution", activity["resume"]["detail"])

    def test_graphs_on_result_cannot_masquerade_as_graphs_off_stage(self) -> None:
        self._receipt("proof/correctness/receipt.json",
                      "epyc.autokernel.targeted_correctness_receipt.v3",
                      status="complete", result="PASS")
        self._receipt("proof/attribution-candidate/receipt.json",
                      "epyc.autokernel.gpu_kernel_attribution.v2",
                      status="complete", result="PASS")
        self._receipt("proof/attribution-anchor/receipt.json",
                      "epyc.autokernel.gpu_kernel_attribution.v2",
                      status="complete", result="PASS")
        self._receipt("proof/attribution-pair.json",
                      "epyc.autokernel.gpu_kernel_attribution_pair.v1")
        self._receipt("proof/proof-bundle.json",
                      "epyc.autokernel.gpu_source_evidence_bundle.v1")
        self._receipt("runner/s1/measurement-graphs-off/result.json",
                      "epyc.autokernel.gpu_candidate_only_screen.v2",
                      status="complete", state="decided", ok=True,
                      runtime_graphs="on")
        activity = self._active()["activity"]
        self.assertEqual(activity["phase"]["id"],
                         "measurement_graphs_off_screen")
        self.assertEqual(activity["stage_contract"]["first_incomplete_stage"],
                         "measurement_graphs_off_screen")

    def test_minimal_adapter_valid_runner_receipt_advances_resume_stage(self) -> None:
        self._receipt("proof/correctness/receipt.json",
                      "epyc.autokernel.targeted_correctness_receipt.v3",
                      status="complete", result="PASS")
        self._receipt("proof/attribution-candidate/receipt.json",
                      "epyc.autokernel.gpu_kernel_attribution.v2",
                      status="complete", result="PASS")
        self._receipt("proof/attribution-anchor/receipt.json",
                      "epyc.autokernel.gpu_kernel_attribution.v2",
                      status="complete", result="PASS")
        self._receipt("proof/attribution-pair.json",
                      "epyc.autokernel.gpu_kernel_attribution_pair.v1")
        self._receipt("proof/proof-bundle.json",
                      "epyc.autokernel.gpu_source_evidence_bundle.v1")
        path = self.operation / "runner/s1/measurement-graphs-off/result.json"
        path.parent.mkdir(parents=True)
        body = {
            "schema": "epyc.autokernel.gpu_candidate_only_screen.v2",
            "non_promotable": True, "promotion_claim": False,
            "hip_residency_proved": True, "runtime_graphs": "off",
        }
        body["result_sha256"] = hashlib.sha256(json.dumps(
            body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        path.write_text(json.dumps(body, sort_keys=True) + "\n")
        activity = self._active()["activity"]
        self.assertEqual(activity["phase"]["id"],
                         "target_runtime_graphs_on_screen")

    def test_nonpositive_exact_attribution_short_circuits_both_runtime_screens(self) -> None:
        self._receipt("proof/correctness/receipt.json",
                      "epyc.autokernel.targeted_correctness_receipt.v3",
                      status="complete", result="PASS")
        self._receipt("proof/attribution-candidate/receipt.json",
                      "epyc.autokernel.gpu_kernel_attribution.v2",
                      status="complete", result="PASS")
        self._receipt("proof/attribution-anchor/receipt.json",
                      "epyc.autokernel.gpu_kernel_attribution.v2",
                      status="complete", result="PASS")
        self._receipt("proof/attribution-pair.json",
                      "epyc.autokernel.gpu_kernel_attribution_pair.v1",
                      exact_duration_comparison={
                          "direction": "neutral",
                          "relative_improvement_fraction": 0.0})
        self._receipt("proof/proof-bundle.json",
                      "epyc.autokernel.gpu_source_evidence_bundle.v1")
        self._receipt("runner/s1/exact-attribution-outcome.json",
                      "epyc.autokernel.exact_attribution_outcome.v1",
                      status="complete", classification="screened_out",
                      exact_attribution_effect_fraction=0.0,
                      target_runtime_executed=False,
                      target_runtime_reason="nonpositive_exact_duration")
        activity = self._active()["activity"]
        self.assertEqual(activity["phase"]["id"], "decision")
        contract = activity["stage_contract"]
        self.assertFalse(contract["target_runtime_executed"])
        self.assertEqual(contract["target_runtime_reason"],
                         "nonpositive_exact_duration")
        self.assertEqual(contract["dual_decision_state"],
                         "measured_nonpositive_exact_short_circuit")
        pipeline = {row["id"]: row for row in activity["pipeline"]}
        self.assertEqual(pipeline["measurement_graphs_off_screen"]["state"],
                         "skipped")
        self.assertEqual(pipeline["target_runtime_graphs_on_screen"]["state"],
                         "skipped")

    def test_replication_two_is_explicit_and_counterbalanced_order_is_preserved(self) -> None:
        self._write_state(repetition=2)
        state_path = self.state_root / "state.json"
        state = json.loads(state_path.read_text())
        state["inflight"]["confirmation"] = True
        state_path.write_text(json.dumps(state))
        self._receipt("proof/correctness/receipt.json",
                      "epyc.autokernel.targeted_correctness_receipt.v3",
                      status="complete", result="PASS")
        self._receipt("proof/attribution-candidate/receipt.json",
                      "epyc.autokernel.gpu_kernel_attribution.v2",
                      status="complete", result="PASS")
        self._receipt("proof/attribution-anchor/receipt.json",
                      "epyc.autokernel.gpu_kernel_attribution.v2",
                      status="complete", result="PASS")
        self._receipt("proof/attribution-pair.json",
                      "epyc.autokernel.gpu_kernel_attribution_pair.v1",
                      attribution_arm_order=["anchor", "candidate"],
                      attribution_arm_order_seed_sha256="d" * 64,
                      exact_duration_comparison={
                          "direction": "regressed",
                          "relative_improvement_fraction": -0.01})
        self._receipt("proof/proof-bundle.json",
                      "epyc.autokernel.gpu_source_evidence_bundle.v1")
        contract = self._active()["activity"]["stage_contract"]
        self.assertEqual(contract["replication"], "S2")
        self.assertEqual(contract["arm_order"], ["anchor", "candidate"])

    def test_anchor_first_partial_receipt_resumes_at_candidate_attribution(self) -> None:
        (self.operation / "evidence-policy.json").write_text(json.dumps({
            "schema": "epyc.autokernel.gpu_source_execution_policy.v2",
            "manifest_sha256": self.manifest_sha,
            "attribution_arm_order": ["anchor", "candidate"],
            "attribution_arm_order_seed_sha256": "d" * 64,
        }))
        self._receipt("proof/correctness/receipt.json",
                      "epyc.autokernel.targeted_correctness_receipt.v3",
                      status="complete", result="PASS")
        self._receipt("proof/attribution-anchor/receipt.json",
                      "epyc.autokernel.gpu_kernel_attribution.v2",
                      status="complete", result="PASS")
        activity = server.discovery_live_payload()["activity"]
        self.assertEqual(activity["phase"]["id"], "candidate_attribution")
        self.assertEqual(activity["stage_contract"]["first_incomplete_stage"],
                         "candidate_attribution")
        self.assertEqual(activity["stage_contract"]["arm_order"],
                         ["anchor", "candidate"])
        pipeline = {row["id"]: row["state"] for row in activity["pipeline"]}
        self.assertEqual(pipeline["anchor_attribution"], "complete")
        self.assertEqual(pipeline["candidate_attribution"], "interrupted")

    def test_s1_decision_exposes_automatic_s2_replication_checkpoint(self) -> None:
        (self.state_root / "state.json").write_text(json.dumps({
            "updated_at": _now(), "next": 2, "complete": False,
            "iterations": [{
                "turn": 1, "hypothesis_id": "akh-stage-fixture",
                "status": "candidate", "result_sha256": "f" * 64,
            }],
            "pending": {
                "phase": "critic_complete", "confirmation": True,
                "candidate": {"hypothesis_id": "akh-stage-fixture"},
                "row": {"hypothesis_id": "akh-stage-fixture",
                        "status": "replication_pending",
                        "replication_of": "f" * 64},
            },
        }))
        activity = server.discovery_live_payload()["activity"]
        self.assertEqual(activity["stage_contract"]["replication"], "S2")
        pipeline = {row["id"]: row["state"] for row in activity["pipeline"]}
        self.assertEqual(pipeline["replication_s1"], "complete")
        self.assertEqual(pipeline["replication_s2"], "waiting")

    def test_s1_runs_only_after_a_persisted_inflight_decision(self) -> None:
        state_path = self.state_root / "state.json"
        state = json.loads(state_path.read_text())
        state["inflight"]["result"] = {"result_sha256": "f" * 64}
        state_path.write_text(json.dumps(state))
        activity = self._active()["activity"]
        self.assertEqual(activity["stage_contract"]["replication"], "S1")
        pipeline = {row["id"]: row["state"] for row in activity["pipeline"]}
        self.assertEqual(pipeline["replication_s1"], "running")
        self.assertEqual(pipeline["replication_s2"], "not_reached")

    def test_screened_checkpoint_resumes_into_automatic_next_hypothesis(self) -> None:
        (self.state_root / "state.json").write_text(json.dumps({
            "updated_at": _now(), "next": 2, "complete": False,
            "iterations": [{"turn": 1, "hypothesis_id": "akh-stage-fixture",
                            "status": "screened_out", "effect_fraction": -0.01}],
        }))
        journal = self.state_root / "journal"
        journal.mkdir()
        (journal / "events.jsonl").write_text(json.dumps({
            "journal_schema": "epyc.autokernel.journal_entry.v1",
            "kind": "STOP_STATE", "seq": 7, "written_at": _now(),
            "payload": {"state": "discovery_screened",
                        "controller_state_sha256": "e" * 64},
        }) + "\n")
        stopped = server.discovery_live_payload()["activity"]
        self.assertEqual(stopped["phase"]["id"], "next_hypothesis")
        self.assertEqual(stopped["status"], "stopped")
        self.assertTrue(stopped["resume"]["possible"])
        self.assertIn("next hypothesis", stopped["resume"]["detail"])
        with (self.state_root / "controller.run.lock").open("r") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            running = server.discovery_live_payload()["activity"]
        self.assertEqual(running["phase"]["id"], "next_hypothesis")
        self.assertEqual(running["status"], "running")
        self.assertTrue(any(row["event"] == "next_hypothesis_transition"
                            for row in running["transitions"]))

    def test_final_iteration_keeps_dual_decision_and_replication_visible(self) -> None:
        (self.state_root / "state.json").write_text(json.dumps({
            "updated_at": _now(), "next": 3, "complete": False,
            "iterations": [{
                "turn": 2, "hypothesis_id": "akh-stage-fixture",
                "status": "candidate", "result_sha256": "f" * 64,
                "replication_of": "e" * 64, "repetition": 2,
                "exact_attribution_effect_fraction": 0.015,
                "target_runtime_effect_fraction": 0.009,
                "target_runtime_executed": True,
                "target_runtime_reason": None,
            }],
        }))
        activity = server.discovery_live_payload()["activity"]
        contract = activity["stage_contract"]
        self.assertEqual(contract["replication"], "S2")
        self.assertEqual(contract["exact_attribution_direction"], "improved")
        self.assertEqual(contract["exact_attribution_effect_fraction"], 0.015)
        self.assertEqual(contract["target_runtime_effect_fraction"], 0.009)
        self.assertEqual(contract["dual_decision_state"],
                         "exact_and_graphs_on_complete")
        pipeline = {row["id"]: row["state"] for row in activity["pipeline"]}
        self.assertEqual(pipeline["replication_s1"], "complete")
        self.assertEqual(pipeline["replication_s2"], "complete")

    def test_typed_refusal_follows_declared_receipt_without_guessing_filename(self) -> None:
        receipt_path = self.state_root / "governed-refusals/arbitrary-name.json"
        receipt_path.parent.mkdir()
        receipt = {
            "schema": "epyc.autokernel.governed_stage_refusal.fixture.v1",
            "refusal_type": "CompileRefusal", "stage": "build",
            "disposition": "authoring_refused",
            "scientific_budget_spent": False,
        }
        raw = (json.dumps(receipt, sort_keys=True) + "\n").encode()
        receipt_path.write_bytes(raw)
        refusal = {
            **receipt, "receipt_path": str(receipt_path),
            "receipt_sha256": hashlib.sha256(raw).hexdigest(),
            "reason": "compiler rejected authored source",
        }
        (self.state_root / "state.json").write_text(json.dumps({
            "updated_at": _now(), "next": 2, "complete": False,
            "iterations": [{"turn": 1, "hypothesis_id": "akh-stage-fixture",
                            "status": "screen_refused", "refusal": refusal}],
        }))
        projected = server.discovery_live_payload()["activity"]["refusal"]
        self.assertTrue(projected["detected"])
        self.assertEqual(projected["type"], "authoring_refused")
        self.assertEqual(projected["class"], "CompileRefusal")
        self.assertEqual(projected["stage"], "build")
        self.assertFalse(projected["scientific_budget_spent"])

        receipt_path.write_text("{}\n")
        rejected = server.discovery_live_payload()["activity"]["refusal"]
        self.assertEqual(rejected["class"], None)

    def test_planner_and_critic_provider_interruptions_are_restartable(self) -> None:
        (self.state_root / "state.json").write_text(json.dumps({
            "updated_at": _now(), "next": 2, "complete": False,
            "planner_provider_attempt": 1,
            "planning": {"phase": "intent", "provider_attempt": 1},
            "iterations": [{"turn": 1, "hypothesis_id": "akh-retry",
                            "status": "planner_transient",
                            "reason": "provider unavailable"}],
        }))
        planner = server.discovery_live_payload()["activity"]
        self.assertEqual(planner["phase"]["id"], "planner")
        self.assertTrue(planner["provider_retry"]["detected"])
        self.assertTrue(planner["provider_retry"]["same_hypothesis"])
        self.assertEqual(planner["provider_retry"]["provider_attempt"], 1)
        self.assertTrue(planner["resume"]["possible"])

        (self.state_root / "state.json").write_text(json.dumps({
            "updated_at": _now(), "next": 1, "complete": False,
            "iterations": [],
            "pending": {"phase": "critic_pending",
                        "candidate": {"hypothesis_id": "akh-retry"},
                        "row": {"hypothesis_id": "akh-retry"}},
        }))
        event = {
            "schema": server.AUTOKERNEL_DISCOVERY_EVENT_SCHEMA,
            "ts": _now(), "channel": "autokernel", "event": "critic_failed",
            "campaign_id": "campaign-stage-fixture",
            "hypothesis_id": "akh-retry", "provider": "claude",
            "model": "claude-fable-5", "effort": "high",
        }
        (self.operations / "live/autokernel.jsonl").write_text(
            json.dumps(event) + "\n")
        critic = server.discovery_live_payload()["activity"]
        self.assertEqual(critic["phase"]["id"], "critic")
        self.assertTrue(critic["provider_retry"]["detected"])
        self.assertFalse(critic["provider_retry"]["planner_rerun"])
        self.assertTrue(critic["resume"]["possible"])

    def test_controller_stage_receipt_aliases_project_canonical_refusal(self) -> None:
        receipt_path = self.state_root / "stage-outcomes/compile.json"
        receipt_path.parent.mkdir()
        receipt = {
            "schema": "epyc.autokernel.gpu_source_build_terminal.v1",
            "state": "failed", "failure_stage": "compile",
            "build_key": "f" * 64, "promotion_claim": False,
        }
        receipt["receipt_sha256"] = hashlib.sha256(json.dumps(
            receipt, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False).encode()).hexdigest()
        raw = (json.dumps(receipt, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False) + "\n").encode()
        receipt_path.write_bytes(raw)
        (self.state_root / "state.json").write_text(json.dumps({
            "updated_at": _now(), "next": 2, "complete": False,
            "iterations": [{
                "turn": 1, "hypothesis_id": "akh-refused",
                "status": "authoring_refused", "stage": "compile",
                "stage_receipt_path": str(receipt_path),
                "stage_receipt_sha256": hashlib.sha256(raw).hexdigest(),
                "scientific_budget_spent": False,
            }],
        }))
        activity = server.discovery_live_payload()["activity"]
        self.assertEqual(activity["phase"]["id"], "next_hypothesis")
        self.assertEqual(activity["refusal"]["type"], "authoring_refused")
        self.assertEqual(activity["refusal"]["class"], "CompileRefusal")
        self.assertFalse(activity["refusal"]["scientific_budget_spent"])

    def test_exact_producer_refusal_receipts_project_all_governed_stages(self) -> None:
        fixtures = (
            ("source_apply", "authoring_refused", "SourceApplyRefusal",
             "epyc.autokernel.gpu_source_build_terminal.v1", True),
            ("compile", "authoring_refused", "CompileRefusal",
             "epyc.autokernel.gpu_source_build_terminal.v1", True),
            ("correctness", "correctness_falsified", "CorrectnessRefusal",
             "epyc.autokernel.targeted_correctness_refusal.v1", False),
            ("dispatch_attribution", "attribution_route_falsified",
             "DispatchAttributionRefusal",
             "epyc.autokernel.gpu_kernel_attribution_refusal.v1", False),
            ("dispatch_attribution", "attribution_route_falsified",
             "DispatchAttributionRefusal",
             "epyc.autokernel.gpu_kernel_attribution_pair_refusal.v1", False),
        )
        for index, (stage, disposition, refusal_class, schema,
                    native_binding) in enumerate(fixtures, 1):
            with self.subTest(stage=stage):
                receipt_path = self.state_root / f"stage-outcomes/{stage}.json"
                receipt_path.parent.mkdir(exist_ok=True)
                receipt = {
                    "schema": schema, "promotion_claim": False,
                    "state": "failed" if native_binding else "refused",
                }
                if native_binding:
                    receipt["failure_stage"] = stage
                    receipt["receipt_sha256"] = hashlib.sha256(json.dumps(
                        receipt, sort_keys=True, separators=(",", ":"),
                        ensure_ascii=False, allow_nan=False).encode()).hexdigest()
                raw = (json.dumps(
                    receipt, sort_keys=True, separators=(",", ":"),
                    ensure_ascii=False, allow_nan=False) + "\n").encode()
                receipt_path.write_bytes(raw)
                bound_sha = hashlib.sha256(raw).hexdigest()
                (self.state_root / "state.json").write_text(json.dumps({
                    "updated_at": _now(), "next": index + 1, "complete": False,
                    "iterations": [{
                        "turn": index, "hypothesis_id": f"akh-{stage}",
                        "status": disposition, "stage": stage,
                        "stage_receipt_path": str(receipt_path),
                        "stage_receipt_sha256": bound_sha,
                        "scientific_budget_spent": False,
                    }],
                }))
                activity = server.discovery_live_payload()["activity"]
                self.assertEqual(activity["phase"]["id"], "next_hypothesis")
                self.assertEqual(activity["refusal"]["type"], disposition)
                self.assertEqual(activity["refusal"]["class"], refusal_class)
                self.assertEqual(activity["refusal"]["stage"], stage)
                self.assertFalse(
                    activity["refusal"]["scientific_budget_spent"])


if __name__ == "__main__":
    unittest.main()
