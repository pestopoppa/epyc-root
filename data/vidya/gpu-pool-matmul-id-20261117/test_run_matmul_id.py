"""CPU-only producer custody controls with a fake child and synthetic residency."""
from collections import Counter
from datetime import datetime, timezone
from importlib.util import module_from_spec, spec_from_file_location
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch

DEPLOY = Path(os.environ.get(
    "GPU_POOL_PACKET", "/mnt/raid0/llm/tmp/vidya-belief-substrate/matmul-id-ready"
))
HISTORY = Path(os.environ.get(
    "GPU_POOL_HISTORY", str(DEPLOY / "controls")
))
SPEC = spec_from_file_location("run_matmul_id", DEPLOY / "run_matmul_id.py")
runner = module_from_spec(SPEC)
SPEC.loader.exec_module(runner)
REAL_POPEN = subprocess.Popen


def utc(epoch):
    return datetime.fromtimestamp(epoch, timezone.utc).isoformat()


class MatmulIdCaptureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pins, cls.linkage = runner.preflight()
        raw = re.sub(r"\x1b\[[0-9;]*m", "", (HISTORY / "MUL_MAT_ID.log").read_text())
        cls.cases = [match[1] for line in raw.splitlines()
                     if (match := re.fullmatch(r"  MUL_MAT_ID\((.*)\): OK", line))]

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(dir=os.environ.get("GPU_POOL_CONTROL_TMP", str(DEPLOY)))
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.out = self.root / "native"
        self.stop = self.root / "STOP"
        self.pidfile = self.root / "pids"
        self.fake_log = self.root / "fixture.log"
        self.children = []
        self.cases = self.cases.copy()

    def execute(self, *, smoke=False, alter_sample=None):
        self.fake_log.write_text(
            "Backend 1/2: ROCm0\n  Device description: AMD Instinct MI210\n"
            + "".join(f"  MUL_MAT_ID({case}): OK\n" for case in self.cases)
        )
        now = time.time()
        grant = self.stop, now + 20, self.root / "fixture.grant", {
            "regions": runner.REGIONS, "start": utc(now - 1), "end": utc(now + 30),
        }

        def fake_popen(argv, *, stdout, stderr, env):
            self.assertEqual(argv, runner.ARGV)
            self.assertEqual(env["FILLER_ID"], runner.ROW)
            request = json.loads((self.out / "request.json").read_text())
            self.assertEqual(request["selected_ops"], [runner.OP])
            self.assertEqual(request["row_id"], runner.ROW)
            self.assertEqual(request["identity"], runner.identity(self.pins))
            child = REAL_POPEN(
                ["/usr/bin/python3", "-BI", "-c",
                 "from pathlib import Path; import sys, time; "
                 "print(Path(sys.argv[1]).read_text(), end='', flush=True); time.sleep(0.17)",
                 str(self.fake_log)],
                stdout=stdout, stderr=stderr, env={"LC_ALL": "C"},
            )
            self.children.append(child)
            return child

        def fake_sample(pid, maps):
            self.assertEqual(pid, self.children[-1].pid)
            birth = runner.process_birth(Path(f"/proc/{pid}"))
            if birth is None:
                return None
            sample = {"time": time.time(), "pid": pid, "birth_ticks": birth, "complete": True,
                      "task_masks": {str(pid): "184-191"},
                      "kfd": True, "vram_bytes": {"vram_0": 67_108_865}, "maps": dict(maps)}
            if alter_sample is not None:
                alter_sample(sample)
            return sample

        with patch.dict(os.environ, {"FILLER_PIDFILE": str(self.pidfile)}), \
                patch.object(runner.subprocess, "Popen", side_effect=fake_popen), \
                patch.object(runner, "sample", side_effect=fake_sample):
            return runner.execute(self.out, grant, self.pins, self.linkage, smoke=smoke)

    def assert_reaped(self):
        child, = self.children
        self.assertIsNotNone(child.returncode)
        self.assertFalse(Path(f"/proc/{child.pid}").exists())
        self.assertEqual(self.pidfile.read_text(), f"{child.pid}\n")

    def assert_refusal(self, reason, **kwargs):
        with self.assertRaisesRegex(ValueError, reason):
            self.execute(**kwargs)
        self.assert_reaped()
        self.assertTrue((self.out / "request.json").is_file())
        self.assertFalse((self.out / "belief.json").exists())
        self.assertFalse((self.out / "RESULT.json").exists())

    def test_exact_historical_argv_and_artifact_identity(self):
        source = json.loads((HISTORY / "results.json").read_text())
        original, = [run for run in source["runs"] if run["op"] == runner.OP]
        self.assertEqual(runner.ARGV[1:], original["argv"][1:])
        self.assertEqual(runner.EXPECTED, original["generated_expected"])
        self.assertEqual(runner.sha(HISTORY / "MUL_MAT_ID.log"),
                         "7dc833ceedbad2d2e552e6becb5ea9943bb889167dd22c2e4e848c6559c303e5")
        self.assertEqual(Counter(Counter(self.cases).values()), {1: 366, 2: 2})
        self.assertTrue(all(re.fullmatch(runner.PARAMS, case) for case in self.cases))
        identity = runner.identity(self.pins)
        self.assertEqual(identity["source"]["removed_worktree_dirty_state"], "UNKNOWN")
        self.assertEqual({arm["sha256"] for arm in identity["artifacts"]},
                         {arm["sha256"] for arm in source["artifacts"]})
        self.assertEqual({key: value for key, value in identity["shim"].items() if key != "path"},
                         {key: value for key, value in source["shim"].items() if key != "path"})
        self.assertEqual(runner.capture.project(source), [])

    def test_one_prospective_invocation_and_strict_rederivation(self):
        result = self.execute()
        self.assert_reaped()
        self.assertEqual((result["observed"], result["passed"], result["unsupported"], result["failed"],
                          result["projected"], result["refused"]), (370, 370, 0, 0, 1, 0))
        self.assertGreaterEqual(result["resident_samples"], 2)
        self.assertEqual(result, runner.check_capture(self.out, self.pins, smoke=False))
        source, claim, evidence = runner.capture.emit(result["capture"], as_of=runner.capture.now())
        self.assertEqual([frame["frame_type"] for frame in (source, claim, evidence)], [
            "epyc.vidya/frame/source_observed/v1",
            "epyc.vidya/frame/claim_proposed/v1",
            "epyc.vidya/frame/evidence_supports_claim/v1",
        ])
        self.assertEqual(claim["assertion"]["source_id"], source["assertion"]["source_id"])
        self.assertEqual(evidence["assertion"]["claim_id"], claim["assertion"]["claim_id"])
        with self.assertRaises(FileExistsError):
            self.execute()
        self.assert_reaped()

    def test_refuses_coherent_wrong_denominator(self):
        self.cases.pop()
        self.assert_refusal("expected native pass partition")

    def test_refuses_substituted_case_with_unchanged_denominator(self):
        self.cases[1] = self.cases[0]
        self.assert_refusal("exact native case multiset differs")

    def test_refuses_wrong_pid(self):
        self.assert_refusal("sample window", alter_sample=lambda sample: sample.update(pid=sample["pid"] + 1))

    def test_refuses_reused_pid(self):
        self.assert_refusal("process identity", alter_sample=lambda sample: sample.update(
            birth_ticks=sample["birth_ticks"] + 1))

    def test_refuses_incomplete_task_samples(self):
        self.assert_refusal("fewer than two", alter_sample=lambda sample: sample.update(complete=False))

    def test_refuses_outside_process_window(self):
        self.assert_refusal("sample window", alter_sample=lambda sample: sample.update(time=time.time() + 30))

    def test_refuses_escaped_affinity(self):
        self.assert_refusal("affinity", alter_sample=lambda sample: sample["task_masks"].update(other="0"))

    def test_refuses_wrong_mapped_inode(self):
        def change_inode(sample):
            major, minor, inode = sample["maps"][str(runner.HIP)]
            sample["maps"][str(runner.HIP)] = [major, minor, inode + 1]

        self.assert_refusal("map", alter_sample=change_inode)

    def test_refuses_absent_kfd_and_zero_vram(self):
        self.assert_refusal("fewer than two", alter_sample=lambda sample: sample.update(kfd=False, vram_bytes={"vram_0": 0}))

    def test_stop_reaps_without_sealing(self):
        self.assert_refusal("STOP", alter_sample=lambda sample: self.stop.touch())

    def test_smoke_is_not_native_ingestion(self):
        result = self.execute(smoke=True)
        self.assert_reaped()
        with self.assertRaisesRegex(ValueError, "wrong capture purpose"):
            runner.check_capture(self.out, self.pins, smoke=False)
        with self.assertRaisesRegex(runner.capture.ProjectionError, "grant.smoke"):
            runner.capture.emit(result["capture"], as_of=runner.capture.now())

    def test_refuses_changed_raw_log(self):
        self.execute()
        log = self.out / "MUL_MAT_ID.log"
        log.write_text(log.read_text() + "changed\n")
        with self.assertRaisesRegex(runner.capture.ProjectionError, "raw log changed"):
            runner.check_capture(self.out, self.pins, smoke=False)

    def test_refuses_changed_persisted_request(self):
        self.execute()
        request = self.out / "request.json"
        data = json.loads(request.read_text())
        data["invocation_token"] = "0" * 32
        request.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, "prepared prospective request"):
            runner.check_capture(self.out, self.pins, smoke=False)


if __name__ == "__main__":
    unittest.main()
