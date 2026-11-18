"""Offline custody and scope controls for the C5 historical packet."""
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import re
import tempfile
import time
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("producer", HERE / "run_elementwise.py")
producer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(producer)


class PacketTests(unittest.TestCase):
    def test_exact_historical_scope_and_pins(self):
        pins = producer.pinned_inputs()
        plan = producer.read_case_plan()
        full = producer.selection(plan, pins, smoke=False)
        smoke = producer.selection(plan, pins, smoke=True)
        self.assertEqual(full["seeds"], list(range(2026102600, 2026102632)))
        self.assertEqual(smoke["seeds"], [2026102603])
        self.assertEqual([(item["seed"], item["op"]) for item in full["invocations"]],
                         [(seed, op) for seed in full["seeds"] for op in ["NORM", "SUM", "SUM_ROWS"]])
        self.assertEqual(sum(item["generated_expected"] for item in full["invocations"]), 640)
        self.assertEqual(len(full["invocations"]), 96)
        self.assertEqual(sum(item["generated_expected"] for item in smoke["invocations"]), 20)
        self.assertEqual(len(smoke["invocations"]), 3)
        self.assertEqual(sum(full["target_cases_per_seed"].values()) * len(full["seeds"]), 544)
        for item in full["invocations"]:
            selector = item["argv"][item["argv"].index("-p") + 1]
            for case in plan[item["op"]]:
                self.assertIsNotNone(re.fullmatch(selector, case))
                self.assertIsNone(re.fullmatch(selector, case + "_changed"))

    def test_parser_preserves_target_statuses_and_checks_exit(self):
        plan = producer.read_case_plan()
        selection = producer.selection(plan, producer.pinned_inputs(), smoke=True)
        invocation = selection["invocations"][0]
        cases = plan["NORM"]
        names = list(cases)
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            path = out / "NORM-2026102603.log"
            failed = f"  NORM({names[2]}): compare failed FAIL"
            raw = "\n".join([
                "ARGV " + json.dumps(invocation["argv"]),
                "Backend 1/1: ROCm0",
                "  Device description: AMD Instinct MI210",
                f"  NORM({names[0]}): OK",
                f"  NORM({names[1]}): not supported [ROCm0]",
                failed,
                f"  NORM({names[-1]}): OK",
                "  2/3 tests passed",
                "  Backend ROCm0: FAIL",
            ]) + "\n"
            path.write_text(raw)
            run = {**invocation, "log": str(path), "log_sha256": producer.sha(path),
                   "status": "native_exit_recorded", "rc": 1, "observed": 4, "passed": 2,
                   "unsupported": 1, "failed": [failed]}
            with patch.object(producer, "qualified", return_value={1, 2}):
                result = producer.check_run(out, run, invocation, {}, cases)
                self.assertEqual(result["target_outcomes"],
                                 {names[0]: "OK", names[1]: "not supported [ROCm0]", names[2]: "compare failed FAIL"})
                self.assertTrue(result["control_pass"])
                self.assertEqual(len(result["missing"]), 7)
                self.assertEqual(result["backend_status"], "FAIL")
                with self.assertRaisesRegex(ValueError, "disagrees with native process exit"):
                    producer.check_run(out, {**run, "rc": 0}, invocation, {}, cases)
                path.write_text(raw.replace("AMD Instinct MI210", "wrong device"))
                with self.assertRaisesRegex(ValueError, "backend terminal identity"):
                    producer.check_run(out, {**run, "log_sha256": producer.sha(path)}, invocation, {}, cases)

    def test_sealed_smoke_cannot_complete_official_row(self):
        pins = producer.pinned_inputs()
        plan = producer.read_case_plan()
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            dry_base = base / "smoke"
            dry_base.mkdir()
            smoke_root = dry_base / "historical544-123"
            smoke_root.mkdir()
            native_root = base / "native"
            native_root.mkdir()
            out = native_root / ("attempt-" + "a" * 32)
            now = time.time()
            def stamp(epoch):
                return datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat()
            grant_path = dry_base / "grants" / (producer.ROW + ".grant")
            grant = {"regions": producer.REGIONS, "start": stamp(now - 10), "end": stamp(now + 200)}

            def fixture(out, invocation, stop, deadline, maps):
                started = time.time()
                op = invocation["op"]
                path = out / (producer.invocation_stem(invocation) + ".log")
                cases = plan[op]
                lines = ["ARGV " + json.dumps(invocation["argv"]),
                         "Backend 1/1: ROCm0", "  Device description: AMD Instinct MI210"]
                lines.extend(f"  {op}({case}): " + ("OK" if role == "PASS" else "not supported [ROCm0]")
                             for case, role in cases.items())
                lines.append("  Backend ROCm0: OK")
                path.write_text("\n".join(lines) + "\n")
                ended = time.time()
                return {**invocation, "log": str(path), "log_sha256": producer.sha(path),
                        "status": "native_exit_recorded", "rc": 0, "observed": len(cases), "passed": 1,
                        "unsupported": len(cases) - 1, "failed": [], "started_epoch": started,
                        "ended_epoch": ended, "pid": 100, "birth_ticks": 100,
                        "residency_samples": [
                            {"time": epoch, "pid": 100, "birth_ticks": 100, "task_masks": {"100": "184-191"},
                             "complete": True, "kfd": True, "vram_bytes": {"vram": 1}, "maps": maps}
                            for epoch in (started, ended)
                        ]}

            with patch.object(producer, "run_native", side_effect=fixture):
                result = producer.execute(out, (dry_base / "stop", now + 100, grant_path, grant),
                                          pins, "fixture linkage", smoke=True)
            self.assertTrue(result["coverage_complete"])
            self.assertEqual((result["projected"], result["observed"], result["target_expected"]), (3, 20, 17))
            self.assertEqual(result["control_counts"], {"expected": 3, "passed": 3})
            with self.assertRaisesRegex(ValueError, "requires grant.smoke"):
                producer.capture.emit(out / "belief.json", as_of=producer.capture.now())
            with self.assertRaisesRegex(ValueError, "prospective selection changed"):
                producer.check_capture(out, pins, smoke=False)

            (native_root / "RESULT.json").write_text(json.dumps(result))
            with patch.object(producer, "HERE", base), patch.object(producer, "pinned_inputs", return_value=pins):
                with self.assertRaisesRegex(ValueError, "prospective selection changed"):
                    producer.main(["complete"])

            (smoke_root / "controls.log").write_text("fixture controls")
            controls = {"status": "PASS", "test_sha256": pins[producer.CONTROLS],
                        "log_sha256": producer.sha(smoke_root / "controls.log")}
            (smoke_root / "controls.json").write_text(json.dumps(controls))
            (smoke_root / "SMOKE.json").write_text(json.dumps({"native": result, "controls": controls}))
            env = {"FILLER_DRYRUN": "1", "FILLER_DRYRUN_DIR": str(dry_base), "FILLER_SMOKE_T0": "123"}
            with patch.dict(os.environ, env), patch.object(producer, "check_capture", return_value=result):
                self.assertEqual(producer.main(["smoke"]), 0)
                self.assertEqual(producer.main(["complete"]), 0)
                result["coverage_complete"] = False
                self.assertEqual(producer.main(["smoke"]), 1)
                self.assertEqual(producer.main(["complete"]), 1)


if __name__ == "__main__":
    unittest.main()
