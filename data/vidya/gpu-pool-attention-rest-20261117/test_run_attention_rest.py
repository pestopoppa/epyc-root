"""Two-operation capture controls using a fake native child and synthetic custody."""
import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_attention_rest as runner

PARAMETERS = {
    "SOFT_MAX": "type=f32,ne=[16,16,1,1]",
    "FLASH_ATTN_EXT": "hsk=64,hsv=64,nh=4,nr23=[1,1],kv=113,nb=1,mask=1,type_K=f16,type_V=f16,",
}


class AttentionRestTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pins, cls.linkage = runner.preflight()

    def setUp(self):
        tmp = tempfile.TemporaryDirectory(dir=runner.HERE)
        self.addCleanup(tmp.cleanup)
        self.out = Path(tmp.name) / "native"
        self.receipt = self.out / "belief.json"
        self.ops = []
        self.now = time.time()
        self.grant = (self.out.parent / "STOP", self.now + 30, self.out.parent / "fixture.grant", {
            "regions": runner.REGIONS,
            "start": datetime.fromtimestamp(self.now - 5, timezone.utc).isoformat(),
            "end": datetime.fromtimestamp(self.now + 30, timezone.utc).isoformat(),
        })

    def fake_run(self, out, op, params, expected, stop, deadline, expected_maps):
        self.assertTrue((out / "request.json").is_file())
        request = json.loads((out / "request.json").read_text())
        self.assertEqual(request["selected_ops"], ["SOFT_MAX", "FLASH_ATTN_EXT"])
        self.assertFalse(self.receipt.exists())
        for preceding in self.ops:
            self.assertTrue((out / f"{preceding}.terminal.json").is_file())
        self.ops.append(op)
        pid = 100 + len(self.ops)
        start = time.time()
        argv = runner.argv_for(op, params)
        log = out / f"{op}.log"
        log.write_text("ARGV " + json.dumps(argv) + "\nBackend 1/1: ROCm0\n  Device description: fixture\n"
                       + "".join(f"  {op}({PARAMETERS[op]},case={i}): OK\n" for i in range(expected)))
        end = time.time()
        return {
            "op": op, "argv": argv, "seed": runner.SEED, "generated_expected": expected,
            "status": "native_exit_recorded", "pid": pid, "rc": 0,
            "started_epoch": start, "ended_epoch": end, "log": str(log), "log_sha256": runner.sha(log),
            "observed": expected, "passed": expected, "unsupported": 0, "failed": [],
            "residency_samples": [
                {"time": when, "pid": pid, "task_masks": {str(pid): "184-191"},
                 "complete": True, "kfd": True, "vram_bytes": {"vram_0": 67_108_865},
                 "maps": copy.deepcopy(expected_maps)}
                for when in (start, end)
            ],
        }

    def execute(self, *, smoke=False, worker=None):
        # No native process or host grant. The fake replaces only the native process boundary.
        with patch.object(runner, "run_native", side_effect=worker or self.fake_run), patch.object(runner, "guard"):
            return runner.execute(self.out, self.grant, self.pins, self.linkage, smoke=smoke)

    def reseal(self, alter, *, update_terminal=False):
        record = json.loads(self.receipt.read_text())
        alter(record)
        if update_terminal:
            for run in record["native"]["runs"]:
                (self.out / f'{run["op"]}.terminal.json').write_text(json.dumps(run))
        record["sha256"] = runner.capture.digest({key: value for key, value in record.items() if key != "sha256"})
        self.receipt.write_text(json.dumps(record))

    def test_accepts_two_ordered_native_tuples_through_shared_grade(self):
        result = self.execute()
        from claim_tuple import grade
        claims = runner.capture.read_capture(self.receipt)
        self.assertEqual(self.ops, ["SOFT_MAX", "FLASH_ATTN_EXT"])
        self.assertEqual([claim.value for claim in claims], [207, 528])
        for op, claim in zip(self.ops, claims, strict=True):
            self.assertEqual(grade(claim)[:2], ("Judged", "T0"))
            self.assertEqual(claim.applicability, {"op": op, "run_id": runner.ROW, "scope_basis": "native"})
        self.assertEqual((result["projected"], result["refused"], result["passed"]), (2, 0, 735))

    def test_refuses_missing_or_duplicate_op_even_if_resealed(self):
        for change in (lambda runs: runs[:1], lambda runs: [runs[0], runs[0]]):
            with self.subTest(change=change):
                if not self.receipt.exists():
                    self.execute()
                original = self.receipt.read_text()
                self.reseal(lambda record: record["native"].update(runs=change(record["native"]["runs"])))
                with self.assertRaisesRegex(ValueError, "exact ordered operator coverage"):
                    runner.check_capture(self.out, self.pins, smoke=False)
                self.receipt.write_text(original)

    def test_refuses_altered_second_log(self):
        self.execute()
        log = self.out / "FLASH_ATTN_EXT.log"
        log.write_text(log.read_text().replace("case=1", "case=changed", 1))
        with self.assertRaisesRegex(runner.capture.ProjectionError, "raw log changed"):
            runner.check_capture(self.out, self.pins, smoke=False)

    def test_refuses_resealed_overlapping_process_windows(self):
        self.execute()

        def overlap(record):
            first, second = record["native"]["runs"]
            second["started_epoch"] = first["ended_epoch"] - 0.001

        self.reseal(overlap, update_terminal=True)
        with self.assertRaisesRegex(ValueError, "process window overlaps"):
            runner.check_capture(self.out, self.pins, smoke=False)

    def test_refuses_second_run_samples_with_wrong_pid(self):
        self.execute()
        self.reseal(lambda record: record["native"]["runs"][1]["residency_samples"][0].update(pid=100),
                    update_terminal=True)
        with self.assertRaisesRegex(ValueError, "sample window"):
            runner.check_capture(self.out, self.pins, smoke=False)

    def test_refuses_second_run_selection_drift_at_write(self):
        def drift(*args):
            run = self.fake_run(*args)
            if run["op"] == "FLASH_ATTN_EXT":
                log = Path(run["log"])
                log.write_text(log.read_text().replace("mask=1,type_K=f16", "mask=1,type_K=q8_0", 1))
                run["log_sha256"] = runner.sha(log)
            return run

        with self.assertRaisesRegex(ValueError, "native FLASH_ATTN_EXT case outside the original selection"):
            self.execute(worker=drift)
        self.assertTrue((self.out / "SOFT_MAX.terminal.json").is_file())
        self.assertTrue((self.out / "FLASH_ATTN_EXT.terminal.json").is_file())
        self.assertFalse(self.receipt.exists())

    def test_preserves_first_terminal_failure_and_does_not_start_second(self):
        def fail(*args):
            run = self.fake_run(*args)
            run["rc"] = 9
            return run

        with self.assertRaisesRegex(ValueError, "expected native pass partition absent"):
            self.execute(worker=fail)
        self.assertEqual(self.ops, ["SOFT_MAX"])
        self.assertEqual(json.loads((self.out / "SOFT_MAX.terminal.json").read_text())["rc"], 9)
        self.assertFalse(self.receipt.exists())

    def test_refuses_resealed_second_denominator_drift(self):
        self.execute()
        self.reseal(lambda record: record["native"]["runs"][1].update(generated_expected=527), update_terminal=True)
        with self.assertRaisesRegex(ValueError, "native seed, denominator or status changed"):
            runner.check_capture(self.out, self.pins, smoke=False)

    def test_refuses_changed_prospective_request(self):
        self.execute()
        (self.out / "request.json").write_text("{}")
        with self.assertRaisesRegex(ValueError, "prospectively written request"):
            runner.check_capture(self.out, self.pins, smoke=False)

    def test_refuses_smoke_in_direct_checker_and_registered_reader(self):
        self.execute(smoke=True)
        with self.assertRaisesRegex(ValueError, "wrong capture purpose"):
            runner.check_capture(self.out, self.pins, smoke=False)
        with self.assertRaisesRegex(runner.capture.ProjectionError, "grant.smoke"):
            runner.capture.emit(self.receipt, as_of=runner.capture.now())


if __name__ == "__main__":
    unittest.main()
