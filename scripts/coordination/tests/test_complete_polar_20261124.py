"""AK bug 2026-11-24: complete:true + polar with a descriptive verdict (CEILING_OPEN) ended rc=75 and was auto-requeued."""
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "rowflow"))
sys.path.insert(0, os.path.join(HERE, "..", "churn"))
import rowflow as rf  # noqa: E402
import filing  # noqa: E402
import smoke_verdict as sv  # noqa: E402

RID = "ak-i8gemm-pc-sol-gpu-20261124"
# key shape copied from /mnt/raid0/llm/tmp/ak-i8gemm-pc-sol-gpu-20261124/out/RESULT.json
I8GEMM = {"at": "2026-11-24T17:59:29Z", "complete": True, "futility_line": 0.03,
          "ms_per_verify_ceiling_at_n8": 1.925296172306543, "polar": "PASS",
          "proof": {"linkage_rc0": True, "ok": True, "sha256sums_ok": True, "sol_string": True, "source_sha_ok": True},
          "row": RID, "saving_by_n": {"1": 0.057, "16": 0.102, "4": 0.054, "8": 0.076}, "smoke": False,
          "task": "autokernel-loop.md:AK-ASM-I8GEMM-PERCHANNEL-GEMV", "verdict": "CEILING_OPEN"}


class Keeper(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.f = self.tmp.name
        self.G = os.path.join(self.f, "grants")
        os.makedirs(self.G)
        os.makedirs(os.path.join(self.f, "ready"))
        self.scratch = os.path.join(self.f, "scratch")
        os.makedirs(os.path.join(self.scratch, "out"))
        self.logs = []

    def tearDown(self):
        self.tmp.cleanup()

    def setup_row(self, result):
        with open(os.path.join(self.scratch, "out", "RESULT.json"), "w") as fh:
            json.dump(result, fh)
        d = {"id": RID, "owner": "autokernel", "resumable": True, "scratch_root": self.scratch,
             "stop_file": os.path.join(self.f, RID + ".STOP")}
        with open(rf.ready_path(self.f, RID), "w") as fh:
            json.dump(d, fh)
        with open(os.path.join(self.G, RID + ".ended"), "w") as fh:
            fh.write("rc=75 time=2026-11-24T17:59:34Z reason=partial-native-incomplete\n")

    def tick(self):
        return rf.autorequeue(self.f, log=self.logs.append, emit=lambda *a, **k: None)

    def test_ceiling_open_polar_not_requeued(self):
        self.setup_row(I8GEMM)
        self.assertFalse(filing.capcut_pending(self.f, RID))
        self.assertFalse(rf.autorequeue_pending(self.f, RID))
        self.assertEqual(self.tick(), [])
        self.assertTrue(os.path.exists(os.path.join(self.G, RID + ".ended")))
        self.assertTrue(any(l.startswith("NO-REQUEUE-COMPLETE " + RID) for l in self.logs))

    def test_incomplete_still_requeued(self):
        self.setup_row(dict(I8GEMM, complete=False))
        self.assertEqual(self.tick(), [RID])

    def test_no_polar_still_requeued(self):
        r = dict(I8GEMM); r.pop("polar")
        self.setup_row(r)
        self.assertEqual(self.tick(), [RID])

    def test_is_decided(self):
        self.assertTrue(sv.is_decided(I8GEMM))
        self.assertTrue(sv.is_decided({"complete": True, "polar": "FAIL", "verdict": "NO_ABORT_AT_16385"}))
        self.assertFalse(sv.is_decided({"complete": True, "verdict": "CEILING_OPEN"}))


import subprocess  # noqa: E402
import mk_ak_row  # noqa: E402
import complete_check as cc  # noqa: E402

OLD_CHECK = """import json, sys
r = json.load(open("x"))
v = str(r.get("verdict") or "")
polar = str(r.get("polar") or "").upper() in ("PASS", "FAIL")
sys.exit(0 if r.get("complete") is True and polar and v.startswith(("PASS", "KEEP", "DROP", "FAIL", "FUTILITY")) else 1)
"""
JOB = """
def decide(m):
    if m > 1:
        return "CEILING_OPEN"
    if m < 0:
        return {"verdict": "NO_ABORT_AT_16385"}
    return "PASS"
"""


class Generator(unittest.TestCase):
    def run_check(self, result):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "out"))
            with open(os.path.join(d, "out", "RESULT.json"), "w") as fh:
                json.dump(result, fh)
            p = os.path.join(d, "check_complete.py")
            with open(p, "w") as fh:
                fh.write(mk_ak_row.CHECK_T.format(dir=d))
            return subprocess.run([sys.executable, "-I", p]).returncode

    def test_template_accepts_ceiling_open_with_polar(self):
        self.assertEqual(self.run_check(I8GEMM), 0)

    def test_template_rejects_incomplete_or_no_polar_or_smoke(self):
        self.assertEqual(self.run_check(dict(I8GEMM, complete=False)), 1)
        r = dict(I8GEMM); r.pop("polar")
        self.assertEqual(self.run_check(r), 1)
        self.assertEqual(self.run_check(dict(I8GEMM, smoke=True)), 1)

    def test_template_passes_own_preflight(self):
        self.assertEqual(cc.excluded(mk_ak_row.CHECK_T.format(dir="/x"), JOB), [])


class Preflight(unittest.TestCase):
    def test_old_regex_flags_descriptive_verdicts(self):
        self.assertEqual(cc.excluded(OLD_CHECK, JOB), ["CEILING_OPEN", "NO_ABORT_AT_16385"])

    def test_warnings_from_spec(self):
        with tempfile.TemporaryDirectory() as d:
            cp = os.path.join(d, "check_complete.py")
            open(cp, "w").write(OLD_CHECK)
            open(os.path.join(d, "job.py"), "w").write(JOB)
            w = cc.warnings({"launcher": {"argv": ["--complete-cmd", f"/usr/bin/python3 -I {cp}"]}})
            self.assertEqual(len(w), 1)
            self.assertIn(cc.CODE, w[0])
            self.assertIn("CEILING_OPEN", w[0])


if __name__ == "__main__":
    unittest.main()
