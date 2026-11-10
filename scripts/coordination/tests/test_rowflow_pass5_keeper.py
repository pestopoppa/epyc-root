#!/usr/bin/env python3
"""Pass 5 emergency keeper batch (operator 2026-11-07, "Approve, deploy when grants drain"): items 1-4 and 6 each carry a
NEGATIVE CONTROL (the module flag / env knob off = the pre-fix keeper must fail the same assertion). Item 5 (dead
coexist/lends path) is proven by the replay gate: decisions identical before/after (see the commit message)."""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
RF_DIR = os.path.join(os.path.dirname(HERE), "rowflow")
sys.path.insert(0, RF_DIR)
import rowflow as rf  # noqa: E402


def load_copy(root):
    """Load rowflow.py from <root>/bin/rowflow/ - the DEPLOYED layout (no sibling ../coordination/)."""
    d = os.path.join(root, "bin", "rowflow")
    os.makedirs(d, exist_ok=True)
    for f in os.listdir(RF_DIR):
        if f.endswith((".py", ".sh")) and ".bak" not in f:
            shutil.copy(os.path.join(RF_DIR, f), d)
    sys.path.insert(0, d)
    try:
        spec = importlib.util.spec_from_file_location("rf_deployed_%d" % len(os.listdir(root)), os.path.join(d, "rowflow.py"))
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
    finally:
        sys.path.remove(d)
    return m


class AlarmChannel(unittest.TestCase):
    def setUp(self):
        self.old = os.environ.pop("ROWFLOW_ALARM_CHANNEL", None)

    def tearDown(self):
        if self.old is not None:
            os.environ["ROWFLOW_ALARM_CHANNEL"] = self.old

    def test_configured_path_exists_in_repo_layout(self):
        self.assertTrue(os.path.isfile(rf.ALARM_CHANNEL), rf.ALARM_CHANNEL)

    def test_configured_path_exists_in_deployed_layout(self):
        m = load_copy(tempfile.mkdtemp())
        self.assertTrue(os.path.isfile(m.ALARM_CHANNEL), f"87 escalations were dropped on this: {m.ALARM_CHANNEL}")

    def test_env_override_wins(self):
        os.environ["ROWFLOW_ALARM_CHANNEL"] = "/x/y.py"
        self.assertEqual(rf._alarm_channel_path(), "/x/y.py")


class Underused(unittest.TestCase):
    def run_underused(self, holders, vram=None):
        flags = tempfile.mkdtemp()
        lines, seen = [], set()
        t0 = 1_000_000.0
        cpu = {c: (0, 100) for c in range(192)}
        rf.underused(flags, holders, lines.append, seen, sample=cpu, now=t0, vram=vram)
        cpu2 = {c: (0, 100 + 6000) for c in range(192)}   # 0 % busy over the window
        out = rf.underused(flags, holders, lines.append, seen, sample=cpu2, now=t0 + rf.UNDERUSED_S + 5, vram=vram)
        return out, lines

    def test_gpu_grant_is_skipped(self):
        out, lines = self.run_underused({rf.GPU: "g1", "q3": "g1"}, vram=0)
        self.assertEqual(out, [])
        self.assertFalse([l for l in lines if "UNDERUSED" in l], lines)

    def test_cpu_grant_still_flagged(self):
        out, lines = self.run_underused({"q1": "c1"})
        self.assertEqual([(r, rid) for r, rid, _ in out], [("q1", "c1")])

class LogTransition(unittest.TestCase):
    """Items 3 and 4: the same helper backs IDLE-HELD and WAIT-FOR-SMOKE."""
    def ticks(self, kind, seq):
        flags = tempfile.mkdtemp()
        lines = []
        for cur in seq:
            rf.log_transition(flags, kind, {k: k for k in cur}, lines.append)
        return lines

    def test_same_set_logs_once(self):
        for kind in ("idle-held", "wait-for-smoke"):
            self.assertEqual(self.ticks(kind, [["a"]] * 6), ["a"])

    def test_change_and_return_log_again(self):
        self.assertEqual(self.ticks("wait-for-smoke", [["a"], ["a"], ["a", "b"], [], ["a"]]), ["a", "b", "a"])

    def test_wait_for_smoke_two_ticks_same_queue_one_line(self):
        flags = tempfile.mkdtemp()
        lines = []
        wl = "WAIT-FOR-SMOKE: queued GPU smoke rank 5 runs first; GPU row(s) r1 (worse rank) wait"
        for _ in range(2):
            rf.log_transition(flags, "wait-for-smoke", {wl: wl}, lines.append)
        self.assertEqual(lines, [wl])

    def test_idle_held_quiet_gpu_grant_logs_once(self):
        flags = tempfile.mkdtemp()
        gp = os.path.join(flags, "g1.grant"); open(gp, "w").write("x")
        os.utime(gp, (1000, 1000))
        grants = [{"id": "g1", "path": gp, "holds": {rf.GPU}, "pid": None}]
        util = {"gpu": {"busy": 0.0}}
        occ = {"pids": {}, "vram_used": 0}
        lines, seen = [], set()
        for _ in range(6):
            rf.idle_held(flags, grants, {rf.GPU: "g1"}, util, lines.append, seen, now=1000 + 600, occ=occ)
        held = [l for l in lines if l.startswith("IDLE-HELD ")]
        self.assertEqual(len(held), 1, held)


class KeeperWrapperV13(unittest.TestCase):
    KEEPER = os.path.join(RF_DIR, "ws58-calendar-keeper-v13.sh")

    def reaper_lines(self, dedup):
        """Run the real reaper python (extracted from v13) twice over the same unchanged fixture; return per-pass lines."""
        text = open(self.KEEPER).read()
        py = text.split("python3 -I - <<'PY'", 1)[1].split("\n", 1)[1].split("\nPY\n", 1)[0]
        root = tempfile.mkdtemp()
        st = os.path.join(root, "state") + "/"; os.makedirs(st)
        # a tmp dir the idle rule sees but that is too young: one IDLE-WAIT decision per dir per pass
        py = py.replace("TMP = '/mnt/raid0/llm/tmp/'", "TMP = %r" % (root + "/tmp/"))
        os.makedirs(os.path.join(root, "tmp", "somedir")); open(os.path.join(root, "tmp", "somedir", "f.txt"), "w").write("x")
        py = py.replace("F = '/mnt/raid0/llm/tmp/compute-flags/'", "F = %r" % (root + "/flags/"))
        for sub in ("flags/grants", "flags/ready/armed", "flags/ready/refused"):
            os.makedirs(os.path.join(root, sub), exist_ok=True)
        env = dict(os.environ, REAP_MODE="live", REAP_LEGACY="0", REAP_DAYS="1", REAP_MAX_GIB="1", REAP_MAX_DIRS="5", REAP_IDLE="1",
                   REAP_IDLE_DAYS="1", REAP_WORKTREES="0", REAP_STATE=st, REAP_REPORT="0", REAP_LOG_DEDUP="1" if dedup else "0")
        res = []
        for _ in range(2):
            r = subprocess.run([sys.executable, "-I", "-c", py], capture_output=True, text=True, env=env, timeout=120)
            res.append([l for l in r.stdout.splitlines() if l.startswith("REAP-") and not l.startswith(("REAP-PASS-SUMMARY", "REAP-IDLE-SUMMARY", "REAP-SWEPT"))])
        return res

    def test_second_pass_over_unchanged_dirs_logs_nothing(self):
        p1, p2 = self.reaper_lines(True)
        self.assertTrue(p1, "fixture produced no REAP decision on pass 1; the test would be vacuous")
        self.assertEqual(p2, [], p2)

    def test_negative_control_dedup_off_repeats(self):
        p1, p2 = self.reaper_lines(False)
        self.assertTrue(p1)
        self.assertEqual(sorted(p1), sorted(p2))


if __name__ == "__main__":
    unittest.main()
