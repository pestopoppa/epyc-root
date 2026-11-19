"""No-native-execution controls for the prepared model-free MUL_MAT packet."""
import copy
from importlib.util import module_from_spec, spec_from_file_location
import json
import os
from pathlib import Path
import tempfile
import unittest

DEPLOY = Path(os.environ.get(
    "GPU_POOL_PACKET", "/mnt/raid0/llm/tmp/vidya-belief-substrate/gpu-pool"
))
SPEC = spec_from_file_location("run_matmul", DEPLOY / "run_matmul.py")
runner = module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


class MatmulCaptureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pins, cls.linkage = runner.preflight()

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.out = Path(temporary.name)
        self.log = self.out / (runner.OP + ".log")
        self.log.write_text(
            "ARGV " + json.dumps(runner.ARGV) + "\nBackend 1/1: ROCm0\n  Device description: fixture\n"
            + "".join(f"  MUL_MAT(type_a={runner.TYPES[i % len(runner.TYPES)]},case={i}): OK\n"
                      for i in range(runner.EXPECTED))
        )
        self.maps = {str(path): runner.file_identity(path)
                     for path in sorted({runner.BIN, *runner.DSOS, runner.SHIM})}
        self.request = runner.capture.begin("matmul", runner.ROW, runner.identity(self.pins), [runner.OP],
                                            producer=runner.__file__)
        self.linkage_log = self.out / "linkage.log"
        self.linkage_log.write_text(self.linkage)
        run = {
            "op": runner.OP, "argv": runner.ARGV, "seed": runner.SEED, "log": str(self.log),
            "log_sha256": runner.sha(self.log), "rc": 0, "observed": 201, "passed": 201,
            "unsupported": 0, "failed": [], "pid": 100,
            "started_epoch": 1794900000.0, "ended_epoch": 1794900002.0,
            "residency_samples": [
                {"time": 1794900000.1 + i, "pid": 100, "task_masks": {"100": "184-191"},
                 "kfd": True, "vram_bytes": {"vram_0": 67_108_865}, "maps": copy.deepcopy(self.maps)}
                for i in range(2)
            ],
        }
        self.native = {
            **runner.identity(self.pins), "schema": runner.capture.NATIVE, "row_id": runner.ROW,
            "model_free": True, "invocation_token": self.request["invocation_token"], "runs": [run],
            "expected_maps": copy.deepcopy(self.maps), "environment": runner.ENV,
            "grant": {"smoke": False, "record": {"regions": runner.REGIONS,
                      "start": "2026-11-17T07:19:59+00:00", "end": "2026-11-18T00:00:00+00:00"}},
            "preflight": {"linkage_log_sha256": runner.sha(self.linkage_log)}, "owned_pid_reaped": True,
        }
        self.receipt = self.out / "belief.json"

    def accept(self):
        runner.capture.write_capture(self.receipt, self.request, self.native)
        return runner.check_capture(self.out, self.pins, smoke=False)

    def test_accepts_exact_custody(self):
        accepted = self.accept()
        self.assertEqual((accepted["projected"], accepted["refused"], accepted["resident_samples"]), (1, 0, 2))

    def test_refuses_old_raw_history_and_smoke_as_live(self):
        self.assertEqual(runner.capture.project(self.native), [])
        self.native["grant"]["smoke"] = True
        with self.assertRaisesRegex(ValueError, "wrong capture purpose"):
            self.accept()

    def test_refuses_out_of_window_samples(self):
        self.native["runs"][0]["residency_samples"][0]["time"] = 1794900003.0
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
        with self.assertRaisesRegex(ValueError, "linkage log changed"):
            self.accept()

    def test_refuses_changed_native_log(self):
        self.accept()
        self.log.write_text(self.log.read_text().replace("case=1", "case=changed"))
        with self.assertRaisesRegex(runner.capture.ProjectionError, "raw log changed"):
            runner.check_capture(self.out, self.pins, smoke=False)


if __name__ == "__main__":
    unittest.main()
