"""q3-pocket re-index launcher and staleness trigger: pocket validation, region-lock argv, trigger decisions."""
import importlib.util
import os
import tempfile
import time
import unittest
from argparse import Namespace
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
spec = importlib.util.spec_from_file_location("gitnexus_reindex", SCRIPTS / "gitnexus-reindex.py")
R = importlib.util.module_from_spec(spec)
spec.loader.exec_module(R)

STALE = "Indexed commit: 97268ec\nCurrent commit: a3a613e\nStatus: ⚠️ stale (re-run gitnexus analyze)\n"
FRESH = "Indexed commit: a3a613e\nCurrent commit: a3a613e\nStatus: ✅ up-to-date\n"
NOW = 1_000_000.0


class Pocket(unittest.TestCase):
    def test_accepts_non_gpu_q3(self):
        for ok in ("72-75", "72-87", "168-183", "72-73,168-169"):
            self.assertEqual(R.validate_pocket(ok), ok)

    def test_refuses_gpu_threads_and_other_quarters(self):
        for bad in ("88-95", "184-191", "72-88", "0-3", "71", "96", "72-", "x", "75-72"):
            with self.assertRaises(R.Usage, msg=bad):
                R.validate_pocket(bad)

    def test_argv_goes_through_region_lock_single_worker(self):
        a = R.run_argv("72-75", 30)
        self.assertEqual(a[0], R.REGION_LOCK)
        self.assertEqual(a[1:3], ["run", "--cpu-list"])
        self.assertIn("--workers", a)
        self.assertEqual(a[a.index("--workers") + 1], "1")
        self.assertTrue(a[a.index("--") + 2].endswith("gitnexus-analyze.sh"))
        self.assertNotIn("taskset", a)   # region-lock pins; no bypass of the claim

    def test_env_pins_one_worker(self):
        e = R.run_env({"GITNEXUS_WORKER_POOL_SIZE": "8"})
        self.assertEqual(e["GITNEXUS_WORKER_POOL_SIZE"], "1")

    def test_guard_accepts_the_argv_we_emit(self):
        g = importlib.util.spec_from_file_location("gg", SCRIPTS / "gitnexus-guard.py")
        G = importlib.util.module_from_spec(g)
        g.loader.exec_module(G)
        a = R.run_argv()
        os.environ["GITNEXUS_WORKER_POOL_SIZE"] = "1"
        try:
            self.assertEqual(G.analyze_workers(a[a.index("--workers") - 0:]), 1)
        finally:
            os.environ.pop("GITNEXUS_WORKER_POOL_SIZE")


class Decide(unittest.TestCase):
    def test_status_parsing(self):
        self.assertTrue(R.is_stale(STALE))
        self.assertFalse(R.is_stale(FRESH))
        self.assertIsNone(R.is_stale("garbage"))
        self.assertEqual(R.current_commit(STALE), "a3a613e")

    def test_fresh_and_unreadable_skip(self):
        self.assertEqual(R.decide(FRESH, {}, NOW)[0], "skip")
        self.assertEqual(R.decide("", {}, NOW)[0], "skip")

    def test_stale_runs_when_idle(self):
        self.assertEqual(R.decide(STALE, {}, NOW), ("run", "stale"))

    def test_interval(self):
        st = {"started_at": NOW - 3600, "rc": 0, "finished_at": NOW - 3000}
        self.assertEqual(R.decide(STALE, st, NOW, min_interval_h=6)[0], "skip")
        self.assertEqual(R.decide(STALE, st, NOW + 6 * 3600, min_interval_h=6)[0], "run")

    def test_refusal_retries_sooner(self):
        st = {"started_at": NOW - 1000, "rc": 64, "finished_at": NOW - 990}
        self.assertEqual(R.decide(STALE, st, NOW, min_interval_h=6)[0], "run")

    def test_batch_dedup(self):
        st = {"last_batch": "b1", "started_at": NOW - 10 ** 6}
        self.assertEqual(R.decide(STALE, st, NOW, batch_id="b1")[0], "skip")
        self.assertEqual(R.decide(STALE, st, NOW, batch_id="b2")[0], "run")

    def test_running_pid_blocks(self):
        st = {"pid": os.getpid(), "pid_start": R.proc_start(os.getpid())}
        self.assertEqual(R.decide(STALE, st, NOW)[0], "skip")
        st["pid_start"] += 1   # pid reuse is not liveness
        self.assertEqual(R.decide(STALE, st, NOW)[0], "run")


class Trigger(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        R.STATE_DIR = Path(self.tmp.name)
        self.spawned = []
        self.args = Namespace(cpus="72-75", timeout_s=600, batch_id="b1", min_interval_h=6)

    def tearDown(self):
        self.tmp.cleanup()

    def test_once_per_batch(self):
        for _ in range(3):   # three "workers" of one dispatch batch
            R.cmd_trigger(self.args, STALE, spawn=lambda a: self.spawned.append(a))
        self.assertEqual(len(self.spawned), 1)
        self.assertEqual(R.load_state()["last_batch"], "b1")

    def test_fresh_spawns_nothing(self):
        R.cmd_trigger(self.args, FRESH, spawn=lambda a: self.spawned.append(a))
        self.assertEqual(self.spawned, [])

    def test_bad_pocket_never_spawns(self):
        self.args.cpus = "88-95"
        with self.assertRaises(R.Usage):
            R.cmd_trigger(self.args, STALE, spawn=lambda a: self.spawned.append(a))
        self.assertEqual(self.spawned, [])


if __name__ == "__main__":
    unittest.main()
