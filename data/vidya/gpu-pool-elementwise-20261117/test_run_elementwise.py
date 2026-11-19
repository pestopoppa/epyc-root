"""Elementwise packet controls using a fake native child and synthetic custody."""
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
import run_elementwise as runner

class ElementwiseTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pins, cls.linkage = runner.preflight()
        cls.case_plan = runner.read_case_plan()

    def setUp(self):
        tmp = tempfile.TemporaryDirectory(dir=runner.HERE)
        self.addCleanup(tmp.cleanup)
        self.out = Path(tmp.name) / "native"
        self.receipt = self.out / "belief.json"
        self.ops = []
        self.now = time.time()
        self.grant = (self.out.parent / "STOP", self.now + 30, runner.FLAGS / "grants" / (runner.ROW + ".grant"), {
            "regions": runner.REGIONS,
            "start": datetime.fromtimestamp(self.now - 5, timezone.utc).isoformat(),
            "end": datetime.fromtimestamp(self.now + 150, timezone.utc).isoformat(),
        })

    def fake_run(self, out, op, params, expected, stop, deadline, expected_maps):
        self.assertTrue((out / "request.json").is_file())
        request = json.loads((out / "request.json").read_text())
        self.assertEqual(request["selected_ops"], runner.OPS)
        self.assertFalse(self.receipt.exists())
        for preceding in self.ops:
            self.assertTrue((out / f"{preceding}.terminal.json").is_file())
        self.ops.append(op)
        pid = 100 + len(self.ops)
        start = time.time()
        argv = runner.argv_for(op, params)
        log = out / f"{op}.log"
        cases = self.case_plan[op]
        passed = sum(status == "PASS" for status in cases.values())
        messages = {"PASS": "OK", "UNSUPPORTED": "not supported [ROCm0] "}
        log.write_text("ARGV " + json.dumps(argv) + "\nBackend 1/2: ROCm0\n  Device description: AMD Instinct MI210\n"
                       + "".join(f"  {op}({params}): {messages[status]}\n" for params, status in cases.items())
                       + f"  {passed}/{passed} tests passed\n  Backend ROCm0: OK\nBackend 2/2: CPU\n  Skipping\n")
        end = time.time()
        return {
            "op": op, "argv": argv, "seed": runner.SEED, "generated_expected": expected,
            "status": "native_exit_recorded", "pid": pid, "birth_ticks": pid * 10, "rc": 0,
            "started_epoch": start, "ended_epoch": end, "log": str(log), "log_sha256": runner.sha(log),
            "observed": expected, "passed": passed, "unsupported": expected - passed, "failed": [],
            "residency_samples": [
                {"time": when, "pid": pid, "birth_ticks": pid * 10, "task_masks": {str(pid): "184-191"},
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

    def test_accepts_seven_ordered_native_tuples_through_shared_grade(self):
        result = self.execute()
        from claim_tuple import grade
        claims = runner.capture.read_capture(self.receipt)
        self.assertEqual(self.ops, ["ADD", "MUL", "SCALE", "NORM", "RMS_NORM", "SUM", "SUM_ROWS"])
        self.assertEqual([claim.value for claim in claims], [16, 16, 4, 20, 21, 7, 4])
        self.assertEqual([claim.extra["native_run"]["unsupported"] for claim in claims], [0, 0, 0, 10, 0, 1, 6])
        for op, claim in zip(self.ops, claims, strict=True):
            self.assertEqual(grade(claim)[:2], ("Judged", "T0"))
            self.assertEqual(claim.applicability, {"op": op, "run_id": runner.ROW, "scope_basis": "native"})
        self.assertEqual((result["projected"], result["refused"], result["observed"], result["passed"],
                          result["unsupported"], result["failed"]), (7, 0, 105, 88, 17, 0))

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

    def test_refuses_altered_last_log(self):
        self.execute()
        log = self.out / "SUM_ROWS.log"
        log.write_text(log.read_text().replace("slice=1", "slice=2", 1))
        with self.assertRaisesRegex(runner.capture.ProjectionError, "raw log changed"):
            runner.check_capture(self.out, self.pins, smoke=False)

    def test_refuses_resealed_overlapping_process_windows(self):
        self.execute()

        def overlap(record):
            first, second = record["native"]["runs"][:2]
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

    def test_refuses_same_pid_with_wrong_birth_ticks(self):
        self.execute()
        self.reseal(lambda record: record["native"]["runs"][1]["residency_samples"][0].update(birth_ticks=12345),
                    update_terminal=True)
        with self.assertRaisesRegex(ValueError, "sample window"):
            runner.check_capture(self.out, self.pins, smoke=False)

    def test_refuses_second_run_selection_drift_at_write(self):
        def drift(*args):
            run = self.fake_run(*args)
            if run["op"] == "MUL":
                log = Path(run["log"])
                log.write_text(log.read_text().replace("ne=[10,5,4,3]", "ne=[10,5,4,9]", 1))
                run["log_sha256"] = runner.sha(log)
            return run

        with self.assertRaisesRegex(ValueError, "native MUL case outside the original selection"):
            self.execute(worker=drift)
        self.assertTrue((self.out / "ADD.terminal.json").is_file())
        self.assertTrue((self.out / "MUL.terminal.json").is_file())
        self.assertFalse(self.receipt.exists())

    def test_preserves_first_terminal_failure_and_does_not_start_second(self):
        def fail(*args):
            run = self.fake_run(*args)
            run["rc"] = 9
            return run

        with self.assertRaisesRegex(ValueError, "expected native pass/unsupported partition absent"):
            self.execute(worker=fail)
        self.assertEqual(self.ops, ["ADD"])
        self.assertEqual(json.loads((self.out / "ADD.terminal.json").read_text())["rc"], 9)
        self.assertFalse(self.receipt.exists())

    def test_refuses_resealed_second_denominator_drift(self):
        self.execute()
        self.reseal(lambda record: record["native"]["runs"][1].update(generated_expected=17), update_terminal=True)
        with self.assertRaisesRegex(ValueError, "native seed, denominator or status changed"):
            runner.check_capture(self.out, self.pins, smoke=False)

    def test_refuses_resealed_unsupported_to_pass(self):
        self.execute()

        def relabel(record):
            run = record["native"]["runs"][3]
            log = Path(run["log"])
            log.write_text(log.read_text().replace("not supported [ROCm0] ", "OK", 1).replace("20/20", "21/21"))
            run.update(log_sha256=runner.sha(log), passed=21, unsupported=9)

        self.reseal(relabel, update_terminal=True)
        self.assertEqual(len(runner.capture.read_capture(self.receipt)), 7)
        with self.assertRaisesRegex(ValueError, "expected native pass/unsupported partition absent"):
            runner.check_capture(self.out, self.pins, smoke=False)

    def test_refuses_resealed_support_swap_with_unchanged_counts(self):
        self.execute()

        def swap(record):
            run = record["native"]["runs"][3]
            log = Path(run["log"])
            log.write_text(log.read_text().replace("noncontig_rows=0): OK", "noncontig_rows=0): not supported [ROCm0] ", 1)
                           .replace("noncontig_rows=1): not supported [ROCm0] ", "noncontig_rows=1): OK", 1))
            run["log_sha256"] = runner.sha(log)

        self.reseal(swap, update_terminal=True)
        with self.assertRaisesRegex(ValueError, "case identity or support disposition changed"):
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
