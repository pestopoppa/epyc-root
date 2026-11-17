"""No-native-execution controls for the prepared model-free ROPE packet."""
import copy
from datetime import datetime, timezone
from importlib.util import module_from_spec, spec_from_file_location
import json
import os
from pathlib import Path
import tempfile
import time
import unittest

DEPLOY = Path(os.environ.get(
    "GPU_POOL_PACKET", "/mnt/raid0/llm/tmp/vidya-belief-substrate/attention-ready"
))
SPEC = spec_from_file_location("run_attention", DEPLOY / "run_attention.py")
runner = module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


class AttentionCaptureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pins, cls.linkage = runner.preflight()

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(dir=DEPLOY)
        self.addCleanup(temporary.cleanup)
        self.out = Path(temporary.name)
        self.log = self.out / (runner.OP + ".log")
        self.now = time.time()
        self.log.write_text(
            "ARGV " + json.dumps(runner.ARGV) + "\nBackend 1/1: ROCm0\n  Device description: fixture\n"
            + "".join(f"  ROPE(type=f32,ne_a=[128,32,2,1],case={i}): OK\n"
                      for i in range(runner.EXPECTED))
        )
        self.maps = {str(path): runner.file_identity(path)
                     for path in sorted({runner.BIN, *runner.DSOS, runner.SHIM})}
        self.request = runner.capture.begin("attention", runner.ROW, runner.identity(self.pins), [runner.OP],
                                            producer=runner.__file__)
        self.request["started_utc"] = datetime.fromtimestamp(self.now - 10, timezone.utc).isoformat()
        runner.output_json(self.out / "request.json", self.request)
        self.linkage_log = self.out / "linkage.log"
        self.linkage_log.write_text(self.linkage)
        run = {
            "op": runner.OP, "argv": runner.ARGV, "seed": runner.SEED, "log": str(self.log),
            "log_sha256": runner.sha(self.log), "rc": 0, "observed": runner.EXPECTED, "passed": runner.EXPECTED,
            "generated_expected": runner.EXPECTED, "status": "native_exit_recorded",
            "unsupported": 0, "failed": [], "pid": 100,
            "started_epoch": self.now - 4, "ended_epoch": self.now - 1,
            "residency_samples": [
                {"time": self.now - 3 + i, "pid": 100, "task_masks": {"100": "184-191"},
                 "kfd": True, "complete": True, "vram_bytes": {"vram_0": 67_108_865}, "maps": copy.deepcopy(self.maps)}
                for i in range(2)
            ],
        }
        self.native = {
            **runner.identity(self.pins), "schema": runner.capture.NATIVE, "row_id": runner.ROW,
            "model_free": True, "seed": runner.SEED, "invocation_token": self.request["invocation_token"], "runs": [run],
            "expected_maps": copy.deepcopy(self.maps), "environment": runner.ENV,
            "grant": {"smoke": False, "record": {"regions": runner.REGIONS,
                      "start": datetime.fromtimestamp(self.now - 30, timezone.utc).isoformat(),
                      "end": datetime.fromtimestamp(self.now + 30, timezone.utc).isoformat()}},
            "preflight": {"linkage_log_sha256": runner.sha(self.linkage_log),
                          "shim_threads": 2, "graphs_disabled": True}, "owned_pid_reaped": True,
        }
        self.receipt = self.out / "belief.json"

    def accept(self):
        runner.capture.write_capture(self.receipt, self.request, self.native)
        return runner.check_capture(self.out, self.pins, smoke=False)

    def test_accepts_exact_custody(self):
        accepted = self.accept()
        claim, = runner.capture.read_capture(self.receipt)
        from claim_tuple import grade
        self.assertEqual(grade(claim)[:2], ("Judged", "T0"))
        self.assertEqual(claim.applicability, {"op": "ROPE", "run_id": runner.ROW, "scope_basis": "native"})
        self.assertEqual((accepted["projected"], accepted["refused"], accepted["resident_samples"]), (1, 0, 2))

    def test_refuses_old_raw_history_and_smoke_as_live(self):
        self.assertEqual(runner.capture.project(self.native), [])
        self.native["grant"]["smoke"] = True
        with self.assertRaisesRegex(ValueError, "wrong capture purpose"):
            self.accept()

    def test_refuses_out_of_window_samples(self):
        self.native["runs"][0]["residency_samples"][0]["time"] = self.now
        with self.assertRaisesRegex(ValueError, "sample window"):
            self.accept()

    def test_refuses_cpu_escape(self):
        self.native["runs"][0]["residency_samples"][0]["task_masks"]["100"] = "0-191"
        with self.assertRaisesRegex(ValueError, "affinity"):
            self.accept()

    def test_refuses_wrong_mapped_inode(self):
        self.native["runs"][0]["residency_samples"][0]["maps"][str(runner.HIP)][2] += 1
        with self.assertRaisesRegex(ValueError, "map"):
            self.accept()

    def test_refuses_duplicate_sample_times(self):
        first, second = self.native["runs"][0]["residency_samples"]
        second["time"] = first["time"]
        with self.assertRaisesRegex(ValueError, "fewer than two"):
            self.accept()

    def test_refuses_changed_linkage_log(self):
        self.linkage_log.write_text("changed\n")
        with self.assertRaisesRegex(ValueError, "preflight custody changed"):
            self.accept()

    def test_refuses_resealed_outside_original_rope_selection(self):
        self.log.write_text(self.log.read_text().replace("type=f32", "type=q8_0", 1))
        self.native["runs"][0]["log_sha256"] = runner.sha(self.log)
        with self.assertRaisesRegex(ValueError, "outside the original selection"):
            self.accept()

    def test_refuses_changed_source_request(self):
        (self.out / "request.json").write_text("{}")
        with self.assertRaisesRegex(ValueError, "prospectively written request"):
            self.accept()

    def test_refuses_resealed_wrong_native_seed(self):
        self.native["seed"] = 20261026
        with self.assertRaisesRegex(ValueError, "native seed, denominator or status changed"):
            self.accept()

    def test_refuses_partial_samples(self):
        self.native["runs"][0]["residency_samples"][0]["complete"] = False
        with self.assertRaisesRegex(ValueError, "fewer than two"):
            self.accept()

    def test_refuses_changed_native_log(self):
        self.accept()
        self.log.write_text(self.log.read_text().replace("case=1", "case=changed"))
        with self.assertRaisesRegex(runner.capture.ProjectionError, "raw log changed"):
            runner.check_capture(self.out, self.pins, smoke=False)


if __name__ == "__main__":
    unittest.main()
