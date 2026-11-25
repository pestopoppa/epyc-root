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

    def test_argv_single_worker_only_for_q3(self):
        self.assertEqual(R.analyze_argv("q3")[-2:], ["--workers", "1"])
        self.assertNotIn("--workers", R.analyze_argv("host"))
        self.assertNotIn("taskset", R.analyze_argv("q3"))   # the engine claim pins; no bypass of it

    def test_env_pins_one_worker_only_for_q3(self):
        self.assertEqual(R.run_env("q3", {"GITNEXUS_WORKER_POOL_SIZE": "8"})["GITNEXUS_WORKER_POOL_SIZE"], "1")
        self.assertNotIn("GITNEXUS_WORKER_POOL_SIZE", R.run_env("host", {"GITNEXUS_WORKER_POOL_SIZE": "8"}))

    def test_guard_accepts_the_q3_argv_we_emit(self):
        g = importlib.util.spec_from_file_location("gg", SCRIPTS / "gitnexus-guard.py")
        G = importlib.util.module_from_spec(g)
        g.loader.exec_module(G)
        a = R.analyze_argv("q3")
        os.environ["GITNEXUS_WORKER_POOL_SIZE"] = "1"
        try:
            self.assertEqual(G.analyze_workers(a[a.index("--workers"):]), 1)
            self.assertIsNone(G.analyze_workers(R.analyze_argv("host")[2:]))   # bare = whole-host route
        finally:
            os.environ.pop("GITNEXUS_WORKER_POOL_SIZE")


class RegionChoice(unittest.TestCase):
    """The row offers both regions; the keeper's packer picks (idle -> host, busy -> q3 pocket)."""

    def specs(self, hist=(), **kw):
        with tempfile.TemporaryDirectory() as d:
            return {s["gnx_option"]: s for s in R.plan_rows("abc1234def", list(hist), rows_root=d, **kw)}

    def test_two_options_whole_host_and_q3_pocket(self):
        s = self.specs()
        self.assertEqual(set(s), {"host", "q3"})
        self.assertEqual((s["host"]["regions"], s["host"]["claim_cpus"]), ("0-95", "0-95"))
        self.assertEqual((s["q3"]["regions"], s["q3"]["claim_cpus"]), ("72-87", "72-75"))

    def test_never_books_mi210_host_threads(self):
        for sp in self.specs().values():
            for tok in (sp["regions"], sp["claim_cpus"]):
                if sp["gnx_option"] == "q3":
                    self.assertFalse(R.parse_cpus(tok) & set(range(88, 96)) | R.parse_cpus(tok) & set(range(184, 192)))

    def test_low_rank_resumable_and_distinct_ids(self):
        s = self.specs()
        self.assertEqual(s["host"]["priority_rank"], R.DEFAULT_RANK)
        self.assertTrue(s["q3"]["resumable"])
        self.assertNotEqual(s["host"]["id"], s["q3"]["id"])

    def test_launcher_claims_via_engine_and_is_a_noop_when_fresh(self):
        with tempfile.TemporaryDirectory() as d:
            sp = R.plan_rows("abc1234", [], rows_root=d)[1]
            R.write_row_files(sp)
            txt = Path(sp["launcher"]).read_text()
            self.assertIn("--claim-cpus 72-75", txt)
            self.assertIn("--complete-cmd", txt)
            self.assertIn("reindex.py fresh", txt)
            self.assertIn("--option q3", (Path(d) / sp["id"] / "job.sh").read_text())

    def test_copied_row_script_uses_repository_analyze_wrapper(self):
        with tempfile.TemporaryDirectory() as d:
            sp = R.plan_rows("abc1234", [], rows_root=d)[1]
            R.write_row_files(sp)
            copied = importlib.util.spec_from_file_location("row_reindex", Path(sp["workdir"]) / "reindex.py")
            row = importlib.util.module_from_spec(copied)
            copied.loader.exec_module(row)
            self.assertEqual(row.analyze_argv("q3"),
                             ["/bin/bash", str(row.REPO_ROOT / "scripts" / "gitnexus-analyze.sh"),
                              "--workers", "1"])
            self.assertEqual(row.analyze_argv("host")[1], row.analyze_argv("q3")[1])

    def test_gpu_grant_live_pocket_row_never_touches_gpu_threads(self):
        # a live GPU grant holds 88-95/184-191; the q3 option stays clear of them so it remains grantable beside it
        q3 = self.specs()["q3"]
        self.assertFalse(R.parse_cpus(q3["claim_cpus"]) & (set(range(88, 96)) | set(range(184, 192))))


class Estimates(unittest.TestCase):
    def test_seeds_floor_at_rowflow_minimum(self):
        self.assertEqual(R.estimate_s("host", []), R.MIN_ESTIMATE_S)
        self.assertGreaterEqual(R.estimate_s("q3", []), R.MIN_ESTIMATE_S)

    def test_measured_median_plus_margin(self):
        h = [{"option": "host", "rc": 0, "wall_s": w} for w in (1000, 2000, 3000)]
        self.assertEqual(R.estimate_s("host", h), 2500)           # median 2000 * 1.25
        self.assertEqual(R.estimate_s("q3", h), R.estimate_s("q3", []))   # other option unaffected

    def test_failed_runs_do_not_count(self):
        h = [{"option": "q3", "rc": 64, "wall_s": 9999}, {"option": "q3", "rc": 0, "wall_s": 4000}]
        self.assertEqual(R.estimate_s("q3", h), 5000)

    def test_longer_pocket_estimate_follows_history(self):
        h = [{"option": "host", "rc": 0, "wall_s": 1700}, {"option": "q3", "rc": 0, "wall_s": 2100}]
        self.assertLess(R.estimate_s("host", h), R.estimate_s("q3", h))


class RunRecord(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        R.STATE_DIR = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_state_and_history_carry_wall_workers_region_nodes(self):
        out = "indexed 87,754 nodes, 134,727 edges\n"
        rec = R.run_record("q3", "72-87", 0, 123.456, 1000.0, out, "row1", env={"FILLER_THREADS": "4"})
        R.record_run(rec, str(Path(self.tmp.name) / "out" / "results.jsonl"))
        st = R.load_state()["last_run"]
        self.assertEqual((st["wall_s"], st["workers"], st["region"], st["nodes"], st["threads"]),
                         (123.5, 1, "72-87", 87754, 4))
        self.assertEqual(R.load_history()[-1]["option"], "q3")
        self.assertIn("unit_id", (Path(self.tmp.name) / "out" / "results.jsonl").read_text())

    def test_history_feeds_estimate(self):
        R.record_run(R.run_record("host", "0-95", 0, 2000, 1.0, "", "r"))
        self.assertEqual(R.estimate_s("host"), 2500)


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
        self.published = []
        self.args = Namespace(cpus="72-75", batch_id="b1", min_interval_h=6, handoff_task="x.md:T", rank=900, dry_run=False)

    def tearDown(self):
        self.tmp.cleanup()

    def pub(self, sp):
        self.published.append(sp["id"])
        return 0, "ok"

    def test_once_per_batch_publishes_both_rows(self):
        for _ in range(3):   # three "workers" of one dispatch batch
            R.cmd_trigger(self.args, STALE, publisher=self.pub)
        self.assertEqual(len(self.published), 2)
        self.assertEqual(R.load_state()["last_batch"], "b1")

    def test_fresh_publishes_nothing(self):
        R.cmd_trigger(self.args, FRESH, publisher=self.pub)
        self.assertEqual(self.published, [])

    def test_bad_pocket_never_publishes(self):
        self.args.cpus = "88-95"
        with self.assertRaises(R.Usage):
            R.cmd_trigger(self.args, STALE, publisher=self.pub)
        self.assertEqual(self.published, [])

    def test_dry_run_publishes_nothing(self):
        self.args.dry_run = True
        R.cmd_trigger(self.args, STALE, publisher=self.pub)
        self.assertEqual(self.published, [])


if __name__ == "__main__":
    unittest.main()
