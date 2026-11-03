"""2026-11-03 session review item 1: run_direct.sh - one deterministic, idempotent command that claims exactly what a row
needs under a finite region-lock timeout, runs the row's job with the engine's FILLER_* contract, holds the row from
the keeper (DIRECT.json), writes grants/<id>.ended on exit and prints a measured utilisation proof."""
import argparse
import io
import os
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "rowflow"))
import hostutil  # noqa: E402
import rowflow as rf  # noqa: E402
import run_direct as rd  # noqa: E402

UTIL = {"q0": 96.0, "q1": 95.0, "q2": 0.0, "q3": 0.0, "claim": 96.0, "gpu": {"busy": 0, "vram_pct": 1.0, "vram_gib": 0.5, "card": "c"}}


def args(**kw):
    base = dict(regions=None, gpu_quiet=None, timeout_s=5, window_s=None, wait_s=0, no_wait=False)
    base.update(kw)
    return argparse.Namespace(**base)


class Pure(unittest.TestCase):
    def test_successor_id_is_a_suffix_rule(self):
        self.assertEqual(rd.successor_id("inf22-m4-q38-recipe-r3-20261103"), "inf22-m4-q38-recipe-r3-20261103-r2")
        self.assertEqual(rd.successor_id("yarn-e1-mem-r5"), "yarn-e1-mem-r6")
        self.assertEqual(rd.successor_id("brf-exp04"), "brf-exp04-r2")

    def test_parse_regions_mirrors_the_engine(self):
        self.assertEqual(rd.parse_regions("0-95", "cpu"), ("0-95", 96, False))
        self.assertEqual(rd.parse_regions("q1", "cpu"), ("24-47,120-135", 24, False))
        self.assertEqual(rd.parse_regions("q0,q2", "cpu")[0], "0-23,96-111,48-71,144-159")
        self.assertEqual(rd.parse_regions("mi210_0,88-91", "gpu"), ("88-91", 4, True))
        self.assertEqual(rd.parse_regions("mi210_0", "gpu"), ("184-191", 8, True))
        self.assertEqual(rd.parse_regions("mi210_0,0-95", "cpu+gpu"), ("0-95", 96, True))
        self.assertIsNone(rd.parse_regions("mi210_0,0-23", "cpu"))     # a cpu row never names the gpu
        self.assertIsNone(rd.parse_regions("0-23", "gpu"))             # a gpu row must name it
        self.assertIsNone(rd.parse_regions("0-300", "cpu"))


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.flags = self.tmp.name
        for d in ("ready", "grants", "dryrun"):
            os.makedirs(os.path.join(self.flags, d))
        # a stand-in region-lock: records its argv, then runs the command after `--`; `--cpu-list 95` = lane busy (75)
        self.rl = os.path.join(self.flags, "region-lock")
        with open(self.rl, "w") as f:
            f.write("#!/bin/bash\nprintf '%s\\n' \"$*\" > \"$(dirname \"$0\")/rl.argv\"\n"
                    "case \" $* \" in *' --cpu-list 95 '*) echo 'waiting: held by pid 1 role=bench tag=other' >&2; exit 75;; esac\n"
                    "while [ \"$1\" != -- ]; do shift; done; shift; exec \"$@\"\n")
        os.chmod(self.rl, 0o755)
        self.saved_rl = rf.RL
        rf.RL = self.rl
        self.lines = []

    def tearDown(self):
        rf.RL = self.saved_rl
        self.tmp.cleanup()

    def row(self, rid, cmd="echo hello; sleep 1", cls="cpu", regions="q1"):
        stop = os.path.join(self.flags, rid + ".STOP")
        lp = os.path.join(self.flags, rid + ".launch.sh")
        with open(lp, "w") as f:
            f.write("#!/bin/bash\n"
                    f"exec bash /x/filler_run15.sh --id {rid} --class {cls} --cmd '{cmd}' --min-window 600 --stop {stop} "
                    f"--complete-cmd true --workdir {self.flags}\n")
        d = {"schema": rf.SCHEMA, "id": rid, "owner": "t", "lane": "cpu", "priority_rank": 10, "shape": "quarter",
             "regions": regions, "window_s": 3600, "estimate_s": 600, "gib": 0, "launcher": {"path": lp},
             "stop_file": stop, "result_path": os.path.join(self.flags, rid + ".json"), "ports": []}
        rf.atomic_json(rf.ready_path(self.flags, rid), d)
        rf.atomic_json(rf.pass_path(self.flags, rid), {"id": rid, "passed_at": rf.now_iso(), "launcher_sha256": rf.sha256(lp)})
        return d

    def launch(self, rid, d, **kw):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = rd.launch(self.flags, rid, d, args(**kw), sleep=lambda s: time.sleep(min(s, 0.2)), measure=lambda *a, **k: UTIL)
        return rc, buf.getvalue()

    def wait_ended(self, rid, t=15):
        p = os.path.join(self.flags, "grants", rid + ".ended")
        for _ in range(t * 10):
            if os.path.exists(p):
                return open(p).read()
            time.sleep(0.1)
        return None


class Launch(Fixture):
    def test_starts_holds_the_row_measures_and_ends(self):
        rid = "row-direct"
        d = self.row(rid)
        rc, out = self.launch(rid, d)
        self.assertEqual(rc, 0, out)
        L = out.splitlines()
        self.assertEqual(L[0], f"id:      {rid}")
        self.assertIn("cpus=24-47,120-135 gpu-quiet=none", L[1])
        self.assertTrue(L[2].startswith("util:    q0=96%"), L[2])
        self.assertIn("claim=96%", L[2])
        self.assertEqual(len(L), 6)
        argv = open(os.path.join(self.flags, "rl.argv")).read()
        self.assertIn(f"run --cpu-list 24-47,120-135 --role bench --timeout-s 5 --tag filler-{rid} --", argv)
        self.assertNotIn("--gpu-quiet", argv)
        st = rf.status(self.flags, rid, util=UTIL)
        self.assertEqual(st["state"], "running")
        self.assertTrue(st["direct"])
        self.assertIn("session_id", rf.load_json(rd.direct_path(self.flags, rid)))   # the question-discipline hook reads it
        self.assertEqual(st["held"], ["q1"])
        self.assertEqual(st["util"], {"q1": 95.0})
        # idempotent: a second launch does not start a second job
        rc2, out2 = self.launch(rid, d)
        self.assertEqual(rc2, 0)
        self.assertTrue(out2.startswith("ALREADY RUNNING"), out2)
        ended = self.wait_ended(rid)
        self.assertIsNotNone(ended)
        self.assertTrue(ended.startswith("rc=0 "), ended)
        self.assertIn("reason=direct-run", ended)
        self.assertEqual(rf.status(self.flags, rid)["state"], "done")
        log = open(os.path.join(rf.dry_dir(self.flags, rid), "direct.out")).read()
        self.assertIn("hello", log)
        self.assertIn("exit rc=0", log)

    def test_job_env_is_the_engine_contract(self):
        rid = "row-env"
        d = self.row(rid, cmd="env | grep ^FILLER_ | sort")
        rc, _ = self.launch(rid, d)
        self.assertEqual(rc, 0)
        self.wait_ended(rid)
        env = dict(l.rstrip("\n").split("=", 1) for l in open(os.path.join(rf.dry_dir(self.flags, rid), "direct.out")) if l.startswith("FILLER_"))
        self.assertEqual(env["FILLER_ID"], rid)
        self.assertEqual(env["FILLER_CPUS"], "24-47,120-135")
        self.assertEqual(env["FILLER_THREADS"], "24")
        self.assertEqual(env["FILLER_NEEDGPU"], "0")
        self.assertEqual(env["FILLER_STOPFILE"].strip(), d["stop_file"])
        self.assertEqual(int(env["FILLER_DEADLINE"]), int(env["FILLER_END"]) - 90)
        self.assertEqual(env["FILLER_DIRECT"].strip(), "1")

    def test_gpu_row_defaults_to_shared_and_a_caller_can_opt_out(self):
        rid = "row-gpu"
        d = self.row(rid, cls="gpu", regions="mi210_0,88-91")
        rc, _ = self.launch(rid, d, no_wait=True)
        self.assertEqual(rc, 0)
        self.wait_ended(rid)
        self.assertIn("--cpu-list 88-91 --role bench --timeout-s 5 --tag filler-row-gpu --gpu-quiet shared --", open(os.path.join(self.flags, "rl.argv")).read())
        rec = rd.build(self.flags, rid, d, d["regions"], "none", 60, 5)
        self.assertNotIn("--gpu-quiet", rec["argv"])
        self.assertEqual(rec["env"]["FILLER_NEEDGPU"], "1")

    def test_lane_busy_is_one_line_and_leaves_the_row_grantable(self):
        rid = "row-busy"
        d = self.row(rid, regions="95")
        rc, out = self.launch(rid, d)
        self.assertEqual(rc, 75)
        self.assertTrue(out.startswith("REFUSED: lane busy:"), out)
        self.assertIn("fix: run_direct.sh row-busy --regions", out)
        for _ in range(50):
            if (rf.load_json(rd.direct_path(self.flags, rid)) or {}).get("result") == "lock-timeout":
                break
            time.sleep(0.1)
        self.assertFalse(os.path.exists(os.path.join(self.flags, "grants", rid + ".ended")))
        self.assertEqual(rf.status(self.flags, rid)["state"], "grantable")

    def test_refusals_name_the_cause_and_the_fix(self):
        rid = "row-ref"
        d = self.row(rid)
        open(d["stop_file"], "w").close()
        rc, out = self.launch(rid, d)
        self.assertEqual((rc, out.strip()), (2, f"REFUSED: STOP file present ({d['stop_file']}); fix: rm {d['stop_file']}"))
        os.remove(d["stop_file"])
        open(os.path.join(self.flags, "grants", rid + ".grant"), "w").write("regions=q1 start=x end=y holds=q1\n")
        rc, out = self.launch(rid, d)
        self.assertEqual(rc, 2)
        self.assertIn("the keeper already granted", out)
        os.remove(os.path.join(self.flags, "grants", rid + ".grant"))
        open(os.path.join(self.flags, "grants", rid + ".ended"), "w").write("rc=0\n")
        rc, out = self.launch(rid, d)
        self.assertEqual(rc, 2)
        self.assertIn(f"fix: publish it under the successor id {rid}-r2", out)
        d2 = self.row("row-badreg", regions="mi210_0,0-23")   # cpu row naming the gpu
        rc, out = self.launch("row-badreg", d2)
        self.assertEqual(rc, 2)
        self.assertIn("regions 'mi210_0,0-23' unusable for class cpu", out)

    def test_stop_and_status_subcommands(self):
        rid = "row-stop"
        d = self.row(rid, cmd="sleep 3")
        rc, _ = self.launch(rid, d, no_wait=True)
        self.assertEqual(rc, 0)
        saved = rf.measure_util
        rf.measure_util = lambda *a, **k: UTIL
        try:
            buf = io.StringIO()
            with redirect_stdout(buf):
                self.assertEqual(rd.main(["status", rid, "--flags", self.flags]), 0)
            self.assertIn("state:   running - direct run pid", buf.getvalue())
            buf = io.StringIO()
            with redirect_stdout(buf):
                self.assertEqual(rd.main(["stop", rid, "--flags", self.flags]), 0)
            self.assertTrue(buf.getvalue().startswith(f"STOP written: {d['stop_file']}"), buf.getvalue())
            self.assertTrue(os.path.exists(d["stop_file"]))
        finally:
            rf.measure_util = saved
        self.wait_ended(rid)

    def test_unknown_row_is_refused_with_the_publish_command(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.assertEqual(rd.main(["nope", "--flags", self.flags]), 2)
        self.assertIn("REFUSED: nope is not a published row", buf.getvalue())
        self.assertIn("fix: python3", buf.getvalue())

    def test_wrapper_is_executable_and_pins_isolated_mode(self):
        sh = os.path.join(os.path.dirname(rd.__file__), "run_direct.sh")
        self.assertTrue(os.stat(sh).st_mode & stat.S_IXUSR)
        self.assertIn("python3 -I", open(sh).read())
        self.assertEqual(subprocess.run(["bash", "-n", sh]).returncode, 0)


if __name__ == "__main__":
    unittest.main()
