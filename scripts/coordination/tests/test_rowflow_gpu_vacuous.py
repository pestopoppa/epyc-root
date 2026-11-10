"""GPU-FENCE-VACUOUS (operator 2026-11-05): a fenced GPU test must never pass silently.

Under the GPU fence (grants without the GPU token: ROCR/HIP hidden + /dev/kfd shim) `test-backend-ops test -b ROCm0`
finds no ROCm backend, prints "Backend 1/1: CPU / Skipping", "1/1 backends passed", OK and exits rc0 - it tested
nothing. Defence in depth, deploy-gating (tests/test_rowflow*.py):
  1. publish refuses a row whose launcher/job files run GPU-only work without declaring the GPU token (the job.py the
     launcher runs is scanned, not only the argv); token rows and HIP *builds* are not refused;
  2. if such a row slips through, the engine scans the fenced job's output for test-backend-ops' own markers, logs
     `GPU-FENCE-VACUOUS <id>`, and ends the run rc=78 reason=gpu-fence-vacuous (not 0, not 75) with a record;
  3. a GPU-token row running the same fake test is unchanged, and a fenced row whose CPU test really ran is not flagged.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from datetime import datetime, timedelta, timezone

_TESTS = os.path.dirname(os.path.abspath(__file__))
_RF = os.path.join(os.path.dirname(_TESTS), "rowflow")
sys.path.insert(0, _RF)
sys.path.insert(0, _TESTS)
import rowflow as rf  # noqa: E402
from test_rowflow import Fixture, write  # noqa: E402

# test-backend-ops console output under the fence (tests/test-backend-ops.cpp console printer, -b ROCm0, no ROCm device)
SKIPPED = ("Testing 1 devices\n\nBackend 1/1: CPU\n  Skipping\n1/1 backends passed\n\033[1;32mOK\033[0m\n")
CPU_RAN = ("Testing 1 devices\n\nBackend 1/1: CPU\n  Device description: AMD EPYC\n\n  ADD(type=f32): \033[1;32mOK\033[0m\n"
           "  12/12 tests passed\n  Backend CPU: \033[1;32mOK\033[0m\n1/1 backends passed\n\033[1;32mOK\033[0m\n")
ZERO_CASES = ("Testing 1 devices\n\nBackend 1/1: ROCm0\n\n  0/0 tests passed\n  Backend ROCm0: \033[1;32mOK\033[0m\n"
              "1/1 backends passed\n\033[1;32mOK\033[0m\n")
# 2026-11-10 race-tsan-v10-r2: a per-cell cap killed test-backend-ops mid-run, before "  Backend X: OK|FAIL" printed
TRUNC_CPU = ("Testing 1 devices\n\nBackend 1/1: CPU\n  Device description: AMD EPYC\n\n"
             "  FLASH_ATTN_EXT(hsk=40,hsv=40,nh=4): \033[1;32mOK\033[0m\n  FLASH_ATTN_EXT(hsk=64,hsv=64,nh=4")
TRUNC_GPU = ("Testing 2 devices\n\nBackend 1/2: ROCm0\n  Device description: AMD Instinct MI210\n\n"
             "  MUL_MAT(type_a=f16,type_b=f32,m=16): \033[1;32mOK\033[0m\n  MUL_MAT(type_a=q4_0")
NEVER_STARTED = "Testing 1 devices\n\nBackend 1/1: CPU\n  Device description: AMD EPYC\n\n"
FAKE_RL = "#!/bin/bash\nwhile [ $# -gt 0 ] && [ \"$1\" != -- ]; do shift; done; shift\n\"$@\"\n"


def iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


class PublishGate(unittest.TestCase):
    def setUp(self):
        self.fx = Fixture()

    def tearDown(self):
        self.fx.cleanup()

    def gpu_job(self, rid, line):
        d = self.fx.job(rid)
        write(os.path.join(d, "job.py"), f"import subprocess\n# runs the backend test\n{line}\n")
        write(os.path.join(d, "job.sh"), f'#!/bin/bash\nD={d}\npython3 "$D/job.py"\nexit 0\n', 0o755)
        return d

    def test_fenced_gpu_test_row_is_refused_at_publish(self):
        d = self.gpu_job("t-vac-pub", 'subprocess.run(["/x/build-hip/bin/test-backend-ops", "test", "-b", "ROCm0"])')
        with self.assertRaises(rf.Refused) as cm:
            rf.publish(self.fx.spec("t-vac-pub", d), self.fx.flags)
        self.assertIn("GPU-FENCE", str(cm.exception))
        self.assertIn("job.py", str(cm.exception), "the evidence names the job file, not only the argv")

    def test_ngl_in_job_is_refused(self):
        d = self.gpu_job("t-vac-ngl", 'subprocess.run(["llama-cli", "-m", "m.gguf", "-ngl", "99"])')
        with self.assertRaises(rf.Refused):
            rf.publish(self.fx.spec("t-vac-ngl", d), self.fx.flags)

    def test_cpu_rows_and_hip_builds_are_not_refused(self):
        for rid, line in (("t-vac-cpu", 'subprocess.run(["test-backend-ops", "test", "-b", "CPU", "-ngl", "0"])'),
                          ("t-vac-bld", 'subprocess.run(["cmake", "-B", "build-hip", "-DGGML_HIP=ON"])')):
            d = self.gpu_job(rid, line)
            rf.publish(self.fx.spec(rid, d), self.fx.flags)   # no Refused

    def test_override_admits_conditional_gpu_branch(self):
        d = self.gpu_job("t-vac-ovr", "argv = ['-ngl', '99', '--device', 'ROCm0'] if KIND == 'gpu' else ['-ngl', '0']")
        with self.assertRaises(rf.Refused):
            rf.publish(self.fx.spec("t-vac-ovr", d), self.fx.flags)
        row = rf.publish(self.fx.spec("t-vac-ovr", d, gpu_fence_override="owner t 2026-11-05: KIND=cpu here"), self.fx.flags)
        self.assertIn("KIND=cpu", row["gpu_fence_override"])

    def test_token_row_declares(self):
        d = self.gpu_job("t-vac-tok", 'subprocess.run(["test-backend-ops", "test", "-b", "ROCm0"])')
        row = {"launcher": {"path": os.path.join(d, "launch.sh")}, "regions": "mi210_0,184-191", "lane": "gpu"}
        self.assertTrue(rf.gpu_declared(row))
        rf.check_gpu_declared(row, rf._opts(row))   # no Refused
        self.assertTrue(rf.gpu_work_evidence(row), "evidence still found; the token makes it legal")


class EngineVacuous(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="gpu-vac-")
        self.bin = os.path.join(self.d, "bin")
        os.makedirs(self.bin)
        shutil.copy(os.path.join(_RF, "filler_run15.sh"), self.bin)
        shutil.copy(os.path.join(_RF, "filler_lib.sh"), self.bin)
        self.rl = os.path.join(self.bin, "region-lock")
        write(self.rl, FAKE_RL, 0o755)
        self.grants = os.path.join(self.d, "grants")
        os.makedirs(self.grants)
        self.proc = None

    def tearDown(self):
        if self.proc and self.proc.poll() is None:
            self.proc.kill()
            self.proc.wait()
        shutil.rmtree(self.d, ignore_errors=True)

    def run_row(self, rid, cls, regions, holds, output):
        fake = os.path.join(self.d, rid + "-test-backend-ops")
        out = os.path.join(self.d, rid + ".txt")
        write(out, output)
        write(fake, f"#!/bin/bash\ncat {out}\nexit 0\n", 0o755)
        now = datetime.now(timezone.utc)
        write(os.path.join(self.grants, rid + ".grant"),
              f"regions={regions} start={iso(now - timedelta(seconds=5))} end={iso(now + timedelta(seconds=900))} holds={holds}\n")
        env = dict(os.environ, FILLER_RL=self.rl, FILLER_FLAGS_DIR=self.d, FILLER_GRANTS_DIR=self.grants,
                   FILLER_STATE_DIR=os.path.join(self.d, "state"), FILLER_POLL="1", FILLER_DISK_FLOOR_GIB="0",
                   FILLER_GPU_LOCK=os.path.join(self.d, "gpu.lock"))
        env.pop("LD_PRELOAD", None)
        wd = os.path.join(self.d, "wd-" + rid)
        os.makedirs(wd)
        argv = ["bash", os.path.join(self.bin, "filler_run15.sh"), "--id", rid, "--class", cls,
                "--cmd", f"{fake} test -b ROCm0", "--min-window", "60", "--stop", os.path.join(self.d, "STOP"),
                "--complete-cmd", "false", "--workdir", wd]
        log = open(os.path.join(self.d, rid + ".out"), "w")
        self.proc = subprocess.Popen(argv, env=env, stdout=log, stderr=subprocess.STDOUT)
        ended = os.path.join(self.grants, rid + ".ended")
        end = time.time() + 60
        while time.time() < end and not os.path.exists(ended):
            time.sleep(0.2)
        self.proc.wait(timeout=30)
        self.assertTrue(os.path.exists(ended), open(os.path.join(self.d, rid + ".out")).read())
        return open(ended).read().splitlines()[0], open(os.path.join(self.d, rid + ".out")).read()

    def test_fenced_skip_fails_distinct_rc(self):
        first, out = self.run_row("cpu-gpu-test", "cpu", "q0", "q0", SKIPPED)
        self.assertIn("rc=78 ", first + " ")
        self.assertIn("reason=gpu-fence-vacuous", first)
        self.assertIn("GPU-FENCE-VACUOUS cpu-gpu-test", out)
        rec = os.path.join(self.d, "state", "cpu-gpu-test.gpu-fence-vacuous.json")
        self.assertIn("0 backends", open(rec).read())

    def test_fenced_zero_cases_fails(self):
        first, _ = self.run_row("cpu-zero", "cpu", "q0", "q0", ZERO_CASES)
        self.assertIn("reason=gpu-fence-vacuous", first)

    def test_fenced_real_cpu_test_not_flagged(self):
        first, out = self.run_row("cpu-real", "cpu", "q0", "q0", CPU_RAN)
        self.assertNotIn("gpu-fence-vacuous", first)
        self.assertNotIn("GPU-FENCE-VACUOUS", out)

    def test_fenced_truncated_cpu_log_not_vacuous(self):
        first, out = self.run_row("cpu-trunc", "cpu", "q0", "q0", TRUNC_CPU)
        self.assertNotIn("gpu-fence-vacuous", first)
        self.assertNotIn("GPU-FENCE-VACUOUS", out)

    def test_fenced_never_started_is_vacuous(self):
        first, _ = self.run_row("cpu-nostart", "cpu", "q0", "q0", NEVER_STARTED)
        self.assertIn("reason=gpu-fence-vacuous", first)

    def scan(self, text):
        f = os.path.join(self.d, "scan.log")
        write(f, text)
        src = open(os.path.join(_RF, "filler_run15.sh")).read()
        fn = src[src.index("gpu_vacuous_scan() {"):src.index("gpu_vacuous_check() {")]
        return subprocess.run(["bash", "-c", fn + '\ngpu_vacuous_scan "$1"', "_", f], capture_output=True, text=True)

    def test_scan_truncated_gpu_cases_not_vacuous(self):
        self.assertNotEqual(self.scan(TRUNC_GPU).returncode, 0)
        self.assertNotEqual(self.scan(TRUNC_CPU).returncode, 0)
        r = self.scan(NEVER_STARTED)
        self.assertEqual(r.returncode, 0)
        self.assertIn("0 backends", r.stdout)
        self.assertEqual(self.scan(SKIPPED).returncode, 0)

    def test_token_row_unchanged(self):
        first, out = self.run_row("gpu-tok", "gpu", "mi210_0,184-191", "gpu-quiet,t184", SKIPPED)
        self.assertNotIn("gpu-fence-vacuous", first)
        self.assertNotIn("GPU-FENCE-VACUOUS", out)
        self.assertIn("rc=75", first)   # unchanged pre-fix behaviour: rc0 without COMPLETE -> partial


if __name__ == "__main__":
    unittest.main()
