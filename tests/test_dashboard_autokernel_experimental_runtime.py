from __future__ import annotations

from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest

from dashboard import server


STAGES = (
    "experimental_build", "cpu_gpu_regression", "matched_np1",
    "concurrency_grid", "greedy_parity", "decision",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sealed(body: dict) -> dict:
    value = dict(body)
    value["receipt_sha256"] = hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False).encode("utf-8")).hexdigest()
    return value


class ExperimentalRuntimeDashboardApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.old_root = server.AUTOKERNEL_DEPLOYMENTS_ROOT
        self.temp = tempfile.TemporaryDirectory()
        deployments = Path(self.temp.name) / "deployments"
        self.bundle = deployments / "dflash2-runtime-fixture"
        self.state_root = self.bundle / "state"
        self.operations_root = self.bundle / "operations"
        self.runtime_root = self.bundle / "experimental-runtime"
        (self.bundle / "config").mkdir(parents=True)
        (self.operations_root / "live").mkdir(parents=True)
        self.runtime_root.mkdir()
        self.state_root.mkdir()
        (self.state_root / "controller.run.lock").touch()
        self.config_sha = "a" * 64
        self.campaign_id = "ak-discovery-" + self.config_sha[:16]
        self.candidate_id = "dflash2-qwen38-27b"
        config = {
            "config_sha256": self.config_sha,
            "campaign_kind": "experimental_runtime",
            "controller": {
                "state_root": str(self.state_root),
                "operations_root": str(self.operations_root),
            },
            "experimental_runtime": {
                "schema": "epyc.autokernel.experimental_runtime_dashboard.v1",
                "candidate_id": self.candidate_id,
                "runtime_root": str(self.runtime_root),
                "stage_order": list(STAGES),
                "stage_budgets_s": {
                    "experimental_build": 3600,
                    "cpu_gpu_regression": 3600,
                    "matched_np1": 7200,
                    "concurrency_grid": 14400,
                    "greedy_parity": 7200,
                    "decision": 900,
                },
            },
        }
        (self.bundle / "config/deployment.json").write_text(json.dumps(config))
        self._state("experimental_build", "none")
        self.predecessor = None
        server.AUTOKERNEL_DEPLOYMENTS_ROOT = deployments

    def tearDown(self) -> None:
        server.AUTOKERNEL_DEPLOYMENTS_ROOT = self.old_root
        self.temp.cleanup()

    def _state(self, stage: str | None, step: str | None) -> None:
        (self.state_root / "state.json").write_text(json.dumps({
            "updated_at": _now(), "next": 1, "complete": stage is None,
            "iterations": [],
            "experimental_runtime": {
                "candidate_id": self.candidate_id,
                "active_stage": stage, "active_step": step,
                "stage_started_at": _now(),
            },
        }))

    def _result(self, stage: str) -> dict:
        return {
            "experimental_build": {
                "hip_binary_sha256": "1" * 64,
                "cpu_binary_sha256": "2" * 64,
                "dflash2_gguf_sha256": "3" * 64,
                "mmq_path_check": "pass",
            },
            "cpu_gpu_regression": {"cpu_pass": True, "gpu_pass": True},
            "matched_np1": {
                "plain_decode_tps": 27.78, "mtp_decode_tps": 55.46,
                "dflash2_decode_tps": 59.12,
                "dflash2_acceptance": 0.61, "comparator_tps": 55.46,
            },
            "concurrency_grid": {
                "np_values": [2, 4, 8], "mtp_np8_tps": 157.3,
                "dflash2_np8_tps": 161.4,
            },
            "greedy_parity": {
                "exact_token_parity": True, "compared_tokens": 4096},
            "decision": {
                "decision": "runtime_candidate_selected",
                "reason_code": "beats_mtp_and_parity_passed",
            },
        }[stage]

    def _receipt(self, stage: str) -> str:
        started_at = _now()
        body = {
            "schema": "epyc.autokernel.experimental_runtime_stage_receipt.v1",
            "campaign_kind": "experimental_runtime",
            "campaign_id": self.campaign_id,
            "candidate_id": self.candidate_id,
            "stage": stage, "status": "complete",
            "started_at": started_at, "ended_at": _now(),
            "predecessor_receipt_file_sha256": self.predecessor,
            "evidence_sha256": hashlib.sha256(stage.encode()).hexdigest(),
            "result": self._result(stage),
        }
        path = self.runtime_root / "stages" / stage / "receipt.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(_sealed(body), sort_keys=True) + "\n")
        os.chmod(path, 0o600)
        self.predecessor = hashlib.sha256(path.read_bytes()).hexdigest()
        return self.predecessor

    def _active(self) -> dict:
        with (self.state_root / "controller.run.lock").open("r") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return server.discovery_live_payload()

    def _claim(self) -> None:
        holder_pid = os.getpid()
        holder_start_ticks = int((Path("/proc") / str(holder_pid) / "stat")
                                 .read_text().split()[21])
        claims = self.operations_root / "claims"
        claims.mkdir()
        acquired_at = _now()
        receipt = {
            "schema": "epyc.autokernel.device_claim_receipt.v1",
            "claim_id": "akd-dflash2-runtime",
            "campaign_id": self.campaign_id,
            "device_id": "mi210_0",
            "purpose": "AutoKernel experimental runtime validation and measurement",
            "holder_pid": holder_pid,
            "holder_start_ticks": holder_start_ticks,
            "acquired_at": acquired_at, "released_at": None,
        }
        (claims / "device.jsonl").write_text(json.dumps({
            "schema": "epyc.autokernel.device_claim_journal.v1",
            "kind": "claim_acquired", "created_at": acquired_at,
            "detail": {"receipt": receipt},
        }) + "\n")

    def test_six_receipts_advance_exact_runtime_stages_and_headlines(self) -> None:
        initial = self._active()
        self.assertEqual(initial["campaign_kind"], "experimental_runtime")
        activity = initial["activity"]
        self.assertEqual(activity["phase"]["id"], "experimental_build")
        self.assertEqual(activity["stage_contract"]["first_incomplete_stage"],
                         "experimental_build")
        self.assertFalse(activity["gpu"]["expected_now"])
        self.assertTrue(activity["runtime_campaign"]
                        ["excluded_from_kernel_frontier"])
        self.assertNotIn("champion", json.dumps(initial).lower())
        self.assertEqual([row["id"] for row in activity["pipeline"]],
                         list(STAGES))

        steps = {
            "experimental_build": ("cpu_gpu_regression", "cpu"),
            "cpu_gpu_regression": ("matched_np1", "gpu"),
            "matched_np1": ("concurrency_grid", "gpu"),
            "concurrency_grid": ("greedy_parity", "gpu"),
            "greedy_parity": ("decision", "none"),
            "decision": (None, None),
        }
        for completed, (next_stage, step) in steps.items():
            self._receipt(completed)
            self._state(next_stage, step)
            payload = self._active()
            activity = payload["activity"]
            if next_stage is None:
                self.assertEqual(activity["status"], "complete")
                self.assertIsNone(activity["stage_contract"]
                                  ["first_incomplete_stage"])
            else:
                self.assertEqual(activity["phase"]["id"], next_stage)
                self.assertEqual(activity["stage_contract"]
                                 ["first_incomplete_stage"], next_stage)

        runtime = activity["runtime_campaign"]
        self.assertEqual(runtime["matched_np1"]["dflash2_decode_tps"], 59.12)
        self.assertEqual(runtime["concurrency_grid"]["dflash2_np8_tps"], 161.4)
        self.assertTrue(runtime["greedy_parity"]["exact_token_parity"])
        self.assertEqual(runtime["decision"], "runtime_candidate_selected")
        self.assertNotIn("hypothesis", json.dumps(runtime).lower())

    def test_gpu_posture_and_stopped_resume_use_exact_runtime_boundary(self) -> None:
        self._receipt("experimental_build")
        self._receipt("cpu_gpu_regression")
        self._state("matched_np1", "gpu")
        self._claim()

        active = self._active()["activity"]
        self.assertEqual(active["phase"]["id"], "matched_np1")
        self.assertTrue(active["gpu"]["expected_now"])
        self.assertTrue(active["gpu"]["claim_held"])
        self.assertEqual(active["stall"]["threshold_s"], 7200)

        stopped = server.discovery_live_payload()["activity"]
        self.assertEqual(stopped["status"], "stopped")
        self.assertEqual(stopped["stage_contract"]["first_incomplete_stage"],
                         "matched_np1")
        self.assertEqual(stopped["stage_contract"]["resume_policy"],
                         "execute_once_from_first_incomplete")
        self.assertTrue(stopped["resume"]["required"])
        pipeline = {row["id"]: row["state"] for row in stopped["pipeline"]}
        self.assertEqual(pipeline["experimental_build"], "complete")
        self.assertEqual(pipeline["cpu_gpu_regression"], "complete")
        self.assertEqual(pipeline["matched_np1"], "waiting")
        self.assertEqual(pipeline["concurrency_grid"], "not_reached")
        self.assertFalse(stopped["gpu"]["expected_now"])

    def test_stage_order_or_receipt_identity_drift_fails_closed(self) -> None:
        self._state("matched_np1", "gpu")
        drift = self._active()["activity"]
        self.assertEqual(drift["status"], "failed")
        self.assertEqual(drift["phase"]["id"], "experimental_build")
        self.assertTrue(drift["failure"]["detected"])
        self.assertIn("first incomplete", drift["failure"]["detail"])

        self._state("experimental_build", "none")
        self._receipt("experimental_build")
        path = self.runtime_root / "stages/experimental_build/receipt.json"
        receipt = json.loads(path.read_text())
        receipt["candidate_id"] = "attacker-runtime"
        path.write_text(json.dumps(receipt) + "\n")
        os.chmod(path, 0o600)
        refused = self._active()["activity"]
        self.assertEqual(refused["status"], "failed")
        self.assertEqual(refused["phase"]["id"], "experimental_build")
        self.assertEqual(refused["stage_contract"]["first_incomplete_stage"],
                         "experimental_build")
        self.assertEqual(refused["pipeline"][0]["state"], "failed")


if __name__ == "__main__":
    unittest.main()
