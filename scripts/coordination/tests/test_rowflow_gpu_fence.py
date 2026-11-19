"""GPU FENCE (operator 2026-11-05 "fix it"): a grant without the GPU token must not open the MI210.

Origin: codex3-cs8-stt5-validation-baseline-r3/r4 (lane cpu) ran baseline_job.py, which runs the HIP whisper-cli every
~7 s; it opened KFD and wrecked the exclusive kvu16g2-ab twice. Launcher-argv inference cannot see a Python job that
spawns a HIP binary, so the engine fences the whole process tree and the keeper samples KFD as the safety net.

Scenario (deploy-gating, tests/test_rowflow*.py): a CPU row's job spawns a binary that opens /dev/kfd ->
  1. under the engine fence the open is refused (EACCES) and HIP device visibility is hidden;
  2. a GPU-token row runs unchanged (no fence env, no preload);
  3. if the fence is bypassed (the KFD pid shows up in the CPU grant's tree) the keeper logs GPU-FENCE-BREACH, alerts
     and marks the row contaminated; a GPU-token grant's KFD pid is never a breach.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone

_RF = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "rowflow")
sys.path.insert(0, _RF)
import rowflow  # noqa: E402

KFD_OPEN_C = r"""
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
int main(int c, char **v){ int fd = open("/dev/kfd", O_RDWR); FILE *o = fopen(v[1], "w");
  fprintf(o, "fd=%d errno=%d\n", fd, fd < 0 ? errno : 0); fclose(o); return 0; }
"""
FAKE_RL = """#!/bin/bash
while [ $# -gt 0 ] && [ "$1" != -- ]; do shift; done; shift
"$@"
"""
GCC = shutil.which("gcc")


def iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


@unittest.skipUnless(GCC, "gcc needed to build the KFD-opening fake job and the fence shim")
class EngineFence(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="gpu-fence-")
        self.bin = os.path.join(self.d, "bin")
        os.makedirs(self.bin)
        shutil.copy(os.path.join(_RF, "filler_run15.sh"), self.bin)
        self.rl = os.path.join(self.bin, "region-lock")
        open(self.rl, "w").write(FAKE_RL)
        os.chmod(self.rl, 0o755)
        self.grants = os.path.join(self.d, "grants")
        os.makedirs(self.grants)
        self.opener = os.path.join(self.d, "kfdopen")
        subprocess.run([GCC, "-x", "c", "-o", self.opener, "-"], input=KFD_OPEN_C, text=True, check=True)
        self.proc = None

    def tearDown(self):
        if self.proc and self.proc.poll() is None:
            self.proc.kill()
            self.proc.wait()
        shutil.rmtree(self.d, ignore_errors=True)

    def run_row(self, rid, cls, regions, holds, extra=()):
        now = datetime.now(timezone.utc)
        with open(os.path.join(self.grants, rid + ".grant"), "w") as f:
            f.write(f"regions={regions} start={iso(now - timedelta(seconds=5))} end={iso(now + timedelta(seconds=900))}"
                    f" holds={holds}\n")
        res = os.path.join(self.d, rid + ".res")
        envf = os.path.join(self.d, rid + ".env")
        job = (f"{self.opener} {res}; env | grep -E '^(LD_PRELOAD|ROCR_VISIBLE_DEVICES|HIP_VISIBLE_DEVICES|"
               f"FILLER_GPU_FENCE|GPU_DEVICE_ORDINAL|CUDA_VISIBLE_DEVICES)=' > {envf}; true")
        env = dict(os.environ, FILLER_RL=self.rl, FILLER_FLAGS_DIR=self.d, FILLER_GRANTS_DIR=self.grants,
                   FILLER_STATE_DIR=os.path.join(self.d, "state"), FILLER_POLL="1", FILLER_DISK_FLOOR_GIB="0",
                   FILLER_GPU_LOCK=os.path.join(self.d, "gpu.lock"))
        env.pop("LD_PRELOAD", None)
        argv = ["bash", os.path.join(self.bin, "filler_run15.sh"), "--id", rid, "--class", cls, "--cmd", job,
                "--min-window", "60", "--stop", os.path.join(self.d, "STOP"), "--complete-cmd", "false",
                "--workdir", self.d, *extra]
        log = open(os.path.join(self.d, rid + ".out"), "w")
        self.proc = subprocess.Popen(argv, env=env, stdout=log, stderr=subprocess.STDOUT)
        end = time.time() + 60
        while time.time() < end and not os.path.exists(os.path.join(self.grants, rid + ".ended")):
            time.sleep(0.2)
        if self.proc.poll() is None:
            self.proc.kill()
            self.proc.wait()
        out = open(os.path.join(self.d, rid + ".out")).read()
        self.assertTrue(os.path.exists(res), f"job never ran:\n{out}")
        envs = dict(l.split("=", 1) for l in open(envf).read().splitlines())
        return open(res).read().strip(), envs, out

    def test_cpu_row_is_fenced(self):
        res, envs, out = self.run_row("cpu-row-spawns-hip", "cpu", "q0", "q0")
        self.assertEqual(res, "fd=-1 errno=13", f"CPU row opened /dev/kfd under the fence:\n{out}")
        self.assertEqual(envs.get("FILLER_GPU_FENCE"), "1")
        self.assertEqual(envs.get("ROCR_VISIBLE_DEVICES"), "")
        self.assertEqual(envs.get("HIP_VISIBLE_DEVICES"), "-1")
        self.assertIn("gpu_fence-", envs.get("LD_PRELOAD", ""))
        self.assertIn("GPU-FENCE on", out)

    def test_gpu_token_row_unchanged(self):
        res, envs, out = self.run_row("gpu-row", "gpu", "mi210_0,184-191", "gpu-quiet,t184")
        self.assertNotIn("errno=13", res)
        self.assertEqual(envs.get("FILLER_GPU_FENCE"), "0")
        for k in ("LD_PRELOAD", "ROCR_VISIBLE_DEVICES", "HIP_VISIBLE_DEVICES"):
            self.assertNotIn(k, envs)

    def test_cpu_row_holding_gpu_quiet_unchanged(self):
        res, envs, _ = self.run_row("cpu-quiet-row", "cpu", "0-95", "q0,q1,q2,q3,gpu-quiet",
                                    extra=("--gpu-quiet", "exclusive", "--claim-cpus", "0-95"))
        self.assertNotIn("errno=13", res)
        self.assertEqual(envs.get("FILLER_GPU_FENCE"), "0")


class KeeperBreach(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="gpu-fence-keeper-")
        self.alerts = []
        self._ra, self._tp = rowflow.route_alert, rowflow.tree_pids
        rowflow.route_alert = lambda kind, msg, ev, log=print: self.alerts.append((kind, ev)) or True
        rowflow.tree_pids = lambda pg: {100: {100, 101, 102}, 200: {200, 201}}.get(pg, set())

    def tearDown(self):
        rowflow.route_alert, rowflow.tree_pids = self._ra, self._tp
        shutil.rmtree(self.d, ignore_errors=True)

    def test_bypassed_fence_is_detected_and_contaminates(self):
        grants = [{"id": "cpu-row", "holds": {"q0"}, "pid": 100},
                  {"id": "gpu-row", "holds": {rowflow.GPU, "t184"}, "pid": 200}]
        occ = {"pids": {102: 0, 201: 5 << 30, 999: 0}, "vram_used": 5 << 30}
        lines, seen = [], set()
        hits = rowflow.gpu_fence_breach(self.d, grants, lines.append, seen, occ=occ)
        self.assertEqual(hits, [("cpu-row", 102)])
        self.assertIn("GPU-FENCE-BREACH cpu-row 102", lines)
        self.assertFalse(any("gpu-row" in l for l in lines), "a GPU-token grant's KFD pid is not a breach")
        self.assertTrue(os.path.exists(os.path.join(rowflow.dry_dir(self.d, "cpu-row"), "CONTAMINATED.json")))
        self.assertEqual([a[0] for a in self.alerts], ["gpu-fence-breach"])
        rowflow.gpu_fence_breach(self.d, grants, lines.append, seen, occ=occ)
        self.assertEqual(len(self.alerts), 1, "alert once per row, log every tick")
        self.assertEqual(sum("GPU-FENCE-BREACH" in l for l in lines), 2)

    def test_fenced_row_without_kfd_is_clean(self):
        grants = [{"id": "cpu-row", "holds": {"q0"}, "pid": 100}]
        lines = []
        self.assertEqual(rowflow.gpu_fence_breach(self.d, grants, lines.append, set(), occ={"pids": {999: 0}}), [])
        self.assertEqual(lines, [])


if __name__ == "__main__":
    unittest.main()
