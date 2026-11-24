"""KEEPER-REAP-OOB (operator D9, 2026-11-18): the keeper's reap is pinned off the MI210 host threads, runs out of band
under a non-blocking lock (at most one pass), and the keeper's own housekeeping pids are excluded from the busy measure."""
import os
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
RF_DIR = os.path.normpath(os.path.join(HERE, "..", "rowflow"))
KEEPER = os.path.join(RF_DIR, "ws58-calendar-keeper-v13.sh")
sys.path.insert(0, RF_DIR)
import hostutil  # noqa: E402

GPU_HOST = set(range(88, 96)) | set(range(184, 192))

# taskset stub: records its argv; a pinned python3 (the reap heredoc) is replaced by a sleep, anything else is exec'd.
STUB = """#!/bin/bash
echo "$*" >> "$STUB_LOG"
[ "$1" = -c ] && shift 2
if [ "$1" = python3 ]; then cat > /dev/null; sleep "${STUB_SLEEP:-0}"; echo "REAP-PASS-SUMMARY live: stub"; exit 0; fi
exec "$@"
"""


class Base(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        bindir = os.path.join(self.root, "bin"); os.makedirs(bindir)
        ts = os.path.join(bindir, "taskset"); open(ts, "w").write(STUB); os.chmod(ts, 0o755)
        self.state = os.path.join(self.root, "state") + "/"
        self.log = os.path.join(self.root, "keeper.log")
        self.stub_log = os.path.join(self.root, "taskset.log")
        self.env = dict(os.environ, PATH=bindir + ":" + os.environ["PATH"], WS58_KEEPER_STATE=self.state,
                        WS58_KEEPER_LOG=self.log, STUB_LOG=self.stub_log, STUB_SLEEP="0")

    def lines(self, path):
        try:
            return open(path).read().splitlines()
        except OSError:
            return []

    def wait_for(self, pred, timeout=20):
        end = time.time() + timeout
        while time.time() < end:
            if pred():
                return True
            time.sleep(0.1)
        return False


class HousekeepingPinned(Base):
    def test_constant_excludes_gpu_host_threads(self):
        text = open(KEEPER).read()
        val = text.split("KEEPER_HOUSEKEEPING_CPUS=", 1)[1].split()[0]
        cpus = set(hostutil.parse_cpus(val))
        self.assertEqual(val, "0-87,96-183")
        self.assertFalse(cpus & GPU_HOST)
        self.assertEqual(cpus | GPU_HOST, set(range(192)))

    def test_reap_python_runs_under_housekeeping_taskset(self):
        r = subprocess.run(["bash", KEEPER, "--reap-job"], env=self.env, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        calls = self.lines(self.stub_log)
        self.assertIn("-c 84-87 python3 -I -", calls)   # REAP-LIGHT: light pocket only, never quarter cores 0-71
        # no python3 heredoc in the keeper escapes the wrapper
        text = open(KEEPER).read()
        for l in text.splitlines():
            if "python3 -I -" in l and "<<" in l:
                self.assertIn("hk_heavy python3", l, l)

    def test_reap_now_launcher_is_pinned_and_detached(self):
        self.env["STUB_SLEEP"] = "3"
        t0 = time.time()
        r = subprocess.run(["bash", KEEPER, "--reap-now"], env=self.env, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertLess(time.time() - t0, 2.5, "--reap-now must not wait for the pass")
        self.assertTrue(self.wait_for(lambda: any("REAP-END" in l for l in self.lines(self.log))), self.lines(self.log))
        calls = self.lines(self.stub_log)
        self.assertTrue(any(c.startswith("-c 84-87 bash ") and c.endswith(" --reap-job") for c in calls), calls)

    def test_reap_runs_niced_idle_io_in_light_pocket(self):
        text = open(KEEPER).read()
        val = text.split("KEEPER_REAP_CPUS=", 1)[1].split()[0]
        cpus = set(hostutil.parse_cpus(val))
        self.assertTrue(cpus <= set(range(84, 88)), val)   # never quarter cores 0-71, never the GPU host threads
        self.assertIn('hk_heavy() { nice -n 19 ionice -c3 taskset -c "$KEEPER_REAP_CPUS" "$@"; }', text)
        launch = [l for l in text.splitlines() if "setsid -f" in l and "--reap-job" in l]
        self.assertEqual(len(launch), 1, launch)
        self.assertIn('nice -n 19 ionice -c3 taskset -c "$KEEPER_REAP_CPUS" bash', launch[0])


class ReapOutOfBand(Base):
    def test_at_most_one_pass(self):
        self.env["STUB_SLEEP"] = "3"
        a = subprocess.Popen(["bash", KEEPER, "--reap-job"], env=self.env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            self.assertTrue(self.wait_for(lambda: any("REAP-START" in l for l in self.lines(self.log))))
            pid = open(os.path.join(self.state, "housekeeping", "reap.pid")).read().strip()
            self.assertEqual(pid, str(a.pid))
            r = subprocess.run(["bash", KEEPER, "--reap-job"], env=self.env, capture_output=True, text=True, timeout=30)
            self.assertEqual(r.returncode, 0)
            skip = [l for l in self.lines(self.log) if "REAP-SKIP" in l]
            self.assertEqual(len(skip), 1, self.lines(self.log))
            self.assertIn("already running pid=%d" % a.pid, skip[0])
            self.assertRegex(skip[0], r"for \d+s")
        finally:
            a.wait(timeout=30)
        log = self.lines(self.log)
        self.assertEqual(sum("REAP-START" in l for l in log), 1, log)
        end = [l for l in log if "REAP-END" in l]
        self.assertEqual(len(end), 1, log)
        self.assertRegex(end[0], r"duration=\d+s")
        self.assertGreaterEqual(int(end[0].split("duration=")[1].rstrip("s")), 2)
        # pidfile emptied: names no pid afterwards; the lock is free again
        self.assertEqual(open(os.path.join(self.state, "housekeeping", "reap.pid")).read().strip(), "")
        self.env["STUB_SLEEP"] = "0"
        subprocess.run(["bash", KEEPER, "--reap-job"], env=self.env, timeout=30)
        self.assertEqual(sum("REAP-START" in l for l in self.lines(self.log)), 2)


def _fake_proc(root, procs):
    """procs: {pid: (ppid, utime, stime, cpu)} -> a fake /proc tree with stat files."""
    for pid, (ppid, ut, st, cpu) in procs.items():
        d = os.path.join(root, str(pid)); os.makedirs(d, exist_ok=True)
        f = ["S", str(ppid)] + ["0"] * 9 + [str(ut), str(st)] + ["0"] * 23 + [str(cpu), "0", "0"]
        open(os.path.join(d, "stat"), "w").write("%d (x y) %s\n" % (pid, " ".join(f)))


class BusyMeasureExclusion(unittest.TestCase):
    def test_pidfile_and_descendants_only(self):
        root = tempfile.mkdtemp(); proc = os.path.join(root, "proc"); hk = os.path.join(root, "hk"); os.makedirs(hk)
        # 100 = reap job, 101 its python, 102 python's git child; 200 = an unrelated job (same name pattern irrelevant)
        _fake_proc(proc, {100: (1, 0, 0, 5), 101: (100, 0, 0, 184), 102: (101, 0, 0, 88), 200: (1, 0, 0, 185)})
        open(os.path.join(hk, "reap.pid"), "w").write("100\n")
        open(os.path.join(hk, "empty.pid"), "w").write("")
        self.assertEqual(hostutil.housekeeping_pids(hk, proc), {100, 101, 102})
        os.remove(os.path.join(hk, "reap.pid"))
        self.assertEqual(hostutil.housekeeping_pids(hk, proc), set())

    def test_subtract_excluded_jiffies(self):
        s0 = {184: (1000, 5000), 185: (1000, 5000), 88: (0, 5000)}
        s1 = {184: (1100, 5100), 185: (1100, 5100), 88: (100, 5100)}   # 184, 185, 88 all 100 % busy in the window
        x0 = {101: (500, 184), 102: (10, 88)}
        x1 = {101: (600, 184), 102: (110, 88)}   # the reap python burnt all of 184; its child all of 88
        adj = hostutil.subtract_pids(s0, s1, x0, x1)
        self.assertEqual(hostutil.busy_pct(s0, adj, [184]), 0.0)
        self.assertEqual(hostutil.busy_pct(s0, adj, [88]), 0.0)
        self.assertEqual(hostutil.busy_pct(s0, adj, [185]), 100.0)   # real work stays busy
        # never below the window start, a pid born mid-window counts from 0
        adj = hostutil.subtract_pids(s0, s1, {}, {300: (10 ** 6, 185)})
        self.assertEqual(adj[185], (1000, 5100))

    def test_measure_excludes_pidfile_tree(self):
        with tempfile.TemporaryDirectory() as root:
            proc = os.path.join(root, "proc")
            hk = os.path.join(root, "hk")
            os.makedirs(hk)
            census = hostutil.housekeeping_pids

            def measure(named):
                _fake_proc(proc, {100: (1, 0, 0, 0), 101: (100, 0, 0, 0)})
                if named:
                    with open(os.path.join(hk, "reap.pid"), "w") as f:
                        f.write("100\n")

                def advance(_):
                    _fake_proc(proc, {100: (1, 40, 0, 0), 101: (100, 60, 0, 0)})

                with mock.patch.object(hostutil, "housekeeping_pids", side_effect=lambda path: census(path, proc)), \
                     mock.patch.object(hostutil, "pid_jiffies", side_effect=lambda pids: pid_jiffies(pids, proc)), \
                     mock.patch.object(hostutil, "cpu_sample", side_effect=[{0: (1000, 5000)}, {0: (1100, 5100)}]), \
                     mock.patch.object(hostutil, "gpu_sample", return_value=None):
                    return hostutil.measure(1.0, {"c0": [0]}, sleep=advance, pid_dir=hk)["c0"]

            pid_jiffies = hostutil.pid_jiffies
            self.assertEqual(measure(False), 100.0)
            self.assertEqual(measure(True), 0.0)


if __name__ == "__main__":
    unittest.main()
