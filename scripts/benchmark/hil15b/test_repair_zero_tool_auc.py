"""Offline regressions. Set HIL15B_UNIT_SOURCE to the original packet's unit.py."""
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from repair_zero_tool_auc import NEW, OLD, ORIGINAL_SHA256, repair, repaired_source


class RefusalTests(unittest.TestCase):
    def test_unknown_source_is_never_modified(self):
        with tempfile.TemporaryDirectory() as tmp:
            packet = Path(tmp)
            unit = packet / "unit.py"
            pins = packet / "source.sha256"
            unit.write_bytes(b"unknown source\n")
            pins.write_text("unchanged\n")
            with self.assertRaisesRegex(ValueError, "approved original"):
                repair(packet)
            self.assertEqual(unit.read_bytes(), b"unknown source\n")
            self.assertEqual(pins.read_text(), "unchanged\n")


class NativeValidatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source_path = os.environ.get("HIL15B_UNIT_SOURCE")
        if not source_path:
            raise unittest.SkipTest("set HIL15B_UNIT_SOURCE for native validator regressions")
        cls.original = Path(source_path).read_bytes()
        # The pinned packet may already have this repair applied. Recover the
        # original assertion in memory; repaired_source still verifies its hash.
        if NEW.encode() in cls.original:
            cls.original = cls.original.replace(NEW.encode(), OLD.encode(), 1)
        cls.fixed = repaired_source(cls.original)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.unit = self.root / "unit.py"
        self.unit.write_bytes(self.fixed)
        self.attempt = self.root / "unit-17"
        self.manifests = []
        flags = ["ORCHESTRATOR_" + name for name in (
            "OBSERVED_DEPENDENCY_LOGGING", "STEP_EVENT_LOGGING", "REPLAY_RECORDING")]
        for i, population in enumerate((0, 0, 1)):
            d = self.attempt / f"driver-{i}"
            d.mkdir(parents=True)
            expected = f"filter-17-p{i}-r0"
            auc = {"status": "insufficient", "n_runs": population, "n_tasks": population}
            manifest = {
                "mock": False, "verdict": "OK", "flags": flags,
                "runs": [{"run_id": expected, "pass": True}],
                "join": {"task_runs": 1, "step_bearing_runs": 1,
                         "joined_outcome": 1, "join_ok": True},
                "replay_verify": {expected: {"rc": 0}}, "l2_scan": {"rc": 0},
                "auc_table": auc,
            }
            (d / "auc_table.json").write_text(json.dumps(auc))
            (d / "l2_report.json").write_text(json.dumps({"n": {
                "traces": 1, "unknown_outcome": 0, "passed": 1, "failed": 0}}))
            with sqlite3.connect(d / "events.sqlite") as conn:
                conn.execute("create table event (id integer, category text, session_id text, detail_json text)")
                seed = {"env": {f: "1" for f in flags}, "features": {
                    f.lower().removeprefix("orchestrator_"): True for f in flags}}
                conn.execute("insert into event values (1, 'model_turn', ?, ?)",
                             (expected, json.dumps({"seed": seed})))
            self.manifests.append(manifest)

    def run_validator(self):
        for i, manifest in enumerate(self.manifests):
            (self.attempt / f"driver-{i}" / "manifest.json").write_text(json.dumps(manifest))
        return subprocess.run([sys.executable, "-I", "-B", str(self.unit), "validate",
                               str(self.attempt), "17"], capture_output=True, text=True)

    def test_original_rejects_zero_tools_and_repair_accepts(self):
        self.unit.write_bytes(self.original)
        self.assertNotEqual(self.run_validator().returncode, 0)
        self.unit.write_bytes(self.fixed)
        result = self.run_validator()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "complete unit 17")

    def test_dependency_bearing_slots_still_pass(self):
        for i, manifest in enumerate(self.manifests):
            manifest["auc_table"].update(n_runs=1, n_tasks=1)
            (self.attempt / f"driver-{i}" / "auc_table.json").write_text(json.dumps(manifest["auc_table"]))
        self.assertEqual(self.run_validator().returncode, 0)

    def test_malformed_populations_rejected(self):
        for runs, tasks in [(0, 1), (1, 0), (2, 2), (-1, -1), (False, False), (1.0, 1.0)]:
            with self.subTest(runs=runs, tasks=tasks):
                auc = self.manifests[0]["auc_table"]
                auc.update(n_runs=runs, n_tasks=tasks)
                (self.attempt / "driver-0" / "auc_table.json").write_text(json.dumps(auc))
                self.assertNotEqual(self.run_validator().returncode, 0)

    def test_manifest_table_disagreement_rejected(self):
        self.manifests[0]["auc_table"] = {"status": "insufficient", "n_runs": 1, "n_tasks": 1}
        self.assertNotEqual(self.run_validator().returncode, 0)

    def test_non_auc_validity_guards_remain(self):
        original = json.dumps(self.manifests)
        for guard in ("mock", "replay", "l2", "join", "flags"):
            with self.subTest(guard=guard):
                self.manifests = json.loads(original)
                m = self.manifests[0]
                if guard == "mock":
                    m["mock"] = True
                elif guard == "replay":
                    m["replay_verify"]["filter-17-p0-r0"]["rc"] = 1
                elif guard == "l2":
                    m["l2_scan"]["rc"] = 1
                elif guard == "join":
                    m["join"]["joined_outcome"] = 0
                else:
                    m["flags"] = []
                self.assertNotEqual(self.run_validator().returncode, 0)

    def test_repair_updates_only_validator_pin(self):
        self.unit.write_bytes(self.original)
        pins = self.root / "source.sha256"
        other = "a" * 64 + "  /retained/driver.py\n"
        pins.write_text(f"{ORIGINAL_SHA256}  {self.unit}\n" + other)
        digest = repair(self.root)
        self.assertEqual(self.unit.read_bytes(), self.fixed)
        self.assertEqual(digest, hashlib.sha256(self.fixed).hexdigest())
        self.assertEqual(pins.read_text(), f"{digest}  {self.unit}\n" + other)

    def test_pin_mismatch_refuses_before_writes(self):
        self.unit.write_bytes(self.original)
        (self.root / "source.sha256").write_text("wrong pin\n")
        with self.assertRaisesRegex(ValueError, "exact original"):
            repair(self.root)
        self.assertEqual(self.unit.read_bytes(), self.original)
        self.assertEqual((self.root / "source.sha256").read_text(), "wrong pin\n")


if __name__ == "__main__":
    unittest.main()
