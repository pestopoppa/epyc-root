#!/usr/bin/env python3
"""keeper-hotfix 2026-11-05 (operator: "Harness first, then class fixes", step 1): one reproducer per defect in the
deployed fixes (keeper-friction-review-20261105.md P2.3 / P2.9-P2.13). Temp dirs only; nothing live is touched."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

_HERE = os.path.dirname(os.path.abspath(__file__))
_RF = os.path.join(os.path.dirname(_HERE), "rowflow")
sys.path.insert(0, _RF)
import publish_row as pr  # noqa: E402
import rowflow as rf  # noqa: E402
sys.path.insert(0, _HERE)
from test_rowflow_shape_evidence import Fx  # noqa: E402

ALL = set(rf.REGIONS) | set(rf.CORES) | set(rf.THREADS)
NOLOG = lambda *_: None  # noqa: E731


def iso(t):
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------- item 1 (D14): npd1 whole-host CPU serving admitted
class D14GpuShape(Fx):
    NPD1 = "--gpu-quiet exclusive --claim-cpus 0-95 --role bench"

    def npd1_launcher(self, rid):
        d = os.path.join(self.root, rid)
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, "job.py"), "w").write(
            'SMOKE = False\nTHREADS = "48" if not SMOKE else "4"\n'
            'argv = ["taskset", "-c", "0-95", "llama-server", "-t", THREADS]\n')
        return self.launcher(rid, cmd=f"/usr/bin/python3 -I {d}/job.py", cls="cpu+gpu", extra=self.NPD1)

    def test_npd1_step5_published_as_whole_host_cpu_serving(self):
        row = rf.publish(self.spec("npd1-step5", self.npd1_launcher("npd1-step5"), lane="gpu", regions="mi210_0,0-95"), self.flags)
        self.assertEqual(row["declared_threads"], 48)
        self.assertEqual(row["shape"], "quiet-host")

    def test_gpu_use_quiet_only_is_not_gpu_lane(self):
        o = {"class": "cpu+gpu", "gpu_quiet": "exclusive", "claim_cpus": "0-95"}
        self.assertEqual(rf.gpu_lane_overreach({"lane": "gpu", "gpu_use": "quiet-only"}, "mi210_0,0-95", o), set())
        self.assertTrue(rf.gpu_lane_overreach({"lane": "gpu"}, "mi210_0,0-95", o))

    def test_quiet_exclusive_with_sub_1gib_vram_is_not_gpu_lane(self):
        rf.atomic_json(rf.pass_path(rf.FLAGS, "kh-vram"), {"vram_used_max_bytes": 1 << 20})
        try:
            o = {"class": "cpu+gpu", "gpu_quiet": "exclusive", "claim_cpus": "0-95"}
            self.assertEqual(rf.gpu_lane_overreach({"id": "kh-vram", "lane": "gpu"}, "mi210_0,0-95", o), set())
        finally:
            shutil.rmtree(rf.dry_dir(rf.FLAGS, "kh-vram"), ignore_errors=True)

    def test_measured_threads_48_is_whole_host_evidence(self):
        self.assertTrue(rf.whole_host_evidence({"declared_threads": None, "measured_threads": 48}))
        self.assertFalse(rf.whole_host_evidence({"declared_threads": None}))

    def test_absent_declared_threads_is_unknown_not_zero(self):
        self.assertIsNone(rf.row_threads({"declared_threads": None}))
        # a quiet-host gpu-lane row published before the field existed is NOT a q3-coexist host
        self.assertFalse(rf.coexist_host({"shape": "quiet-host", "lane": "gpu", "declared_threads": None}))
        self.assertTrue(rf.coexist_host({"shape": "quiet-host", "lane": "gpu", "declared_threads": 8}))


# ---------------------------------------------------------------- item 2: supersede never stops a RUNNING predecessor
class SupersedeRunning(Fx):
    def test_running_predecessor_stop_not_touched_armed_one_is(self):
        rf.publish(self.spec("p-run", self.launcher("p-run"), regions="any-cpu-quarter"), self.flags)
        rf.publish(self.spec("p-arm", self.launcher("p-arm"), regions="any-cpu-quarter"), self.flags)
        open(os.path.join(self.flags, "grants", "p-run.grant"), "w").write("regions=0-23 holds=q0\n")
        self.assertEqual(rf.withdraw(self.flags, "p-run", "superseded-by:x", NOLOG), "PENDING")
        self.assertFalse(os.path.exists(os.path.join(self.root, "p-run", "p-run.STOP")))
        self.assertEqual(rf.withdraw(self.flags, "p-arm", "superseded-by:x", NOLOG), "WITHDRAWN")
        self.assertTrue(os.path.exists(os.path.join(self.root, "p-arm", "p-arm.STOP")))


# ---------------------------------------------------------------- item 3 (python side): /proc liveness, tree kill
class TreeKill(unittest.TestCase):
    def test_kill_tree_takes_setsid_grandchild(self):
        d = tempfile.mkdtemp()
        p = subprocess.Popen(["bash", "-c", f"setsid sleep 300 & echo $! > {d}/g; sleep 300"], start_new_session=True)
        for _ in range(50):
            if os.path.exists(f"{d}/g") and open(f"{d}/g").read().strip():
                break
            time.sleep(0.1)
        g = int(open(f"{d}/g").read())
        self.assertIn(g, rf.tree_pids(p.pid))
        self.assertEqual(rf.kill_tree(p.pid, grace=3), set())
        p.wait(timeout=5)
        self.assertFalse(rf.proc_alive(g))
        self.assertFalse(rf.proc_alive(p.pid), "a reaped/zombie pid is dead")


# ---------------------------------------------------------------- item 4 (D9 + 4th facet): dry-run deadline / reap
class DryrunReconcile(Fx):
    def setUp(self):
        super().setUp()
        self.rid = "dr1"
        rf.publish(self.spec(self.rid, self.launcher(self.rid), regions="any-cpu-quarter"), self.flags)
        self.dd = rf.dry_dir(self.flags, self.rid)
        os.makedirs(os.path.join(self.dd, "grants"), exist_ok=True)
        self.grant = os.path.join(self.dd, "grants", self.rid + ".grant")

    def running(self, pid, deadline, started=False):
        open(self.grant, "w").write(f"regions=0-3 start=2026-11-04T15:29Z end={iso(deadline)} holds=c0,c1,c2,c3\n")
        rf.atomic_json(rf.running_path(self.flags, self.rid), {"pid": pid, "pgid": pid, "regions": "0-3", "grant": self.grant,
                                                                "deadline": iso(deadline)})
        open(os.path.join(self.dd, "launcher.out"), "w").write("START regions=0-3\n" if started else "launcher up\n")

    def test_dead_pid_reaped_and_cpus_released(self):
        dead = subprocess.Popen(["true"]); dead.wait()
        self.running(dead.pid, datetime.now(timezone.utc) + timedelta(hours=1))
        self.assertIn("c0", rf.live_smoke_tokens(self.flags) | {"c0"})
        logs = []
        self.assertEqual(rf.reconcile_dryruns(self.flags, logs.append), [(self.rid, "reaped")])
        self.assertFalse(os.path.exists(rf.running_path(self.flags, self.rid)))
        self.assertFalse(os.path.exists(self.grant))
        busy, free, _ = rf.host_snapshot(self.flags, [], {})
        self.assertTrue({"c0", "c3", "q0"} <= free)

    def test_past_deadline_pre_start_kills_group_and_requeues_as_wait(self):
        p = subprocess.Popen(["bash", "-c", "setsid sleep 300 & sleep 300"], start_new_session=True)
        rf.atomic_json(rf.smoke_queued_path(self.flags, self.rid), {"id": self.rid})
        self.running(p.pid, datetime.now(timezone.utc) - timedelta(hours=1))
        kids = rf.tree_pids(p.pid)
        r = rf.reconcile_dryruns(self.flags, NOLOG)
        p.wait(timeout=10)
        self.assertEqual(r, [(self.rid, "WAIT")])
        self.assertFalse(any(rf.proc_alive(x) for x in kids))
        self.assertFalse(os.path.exists(rf.running_path(self.flags, self.rid)))
        self.assertEqual(rf.fail_paths(self.flags, self.rid), [])
        self.assertEqual((rf.load_json(rf.smoke_queued_path(self.flags, self.rid)) or {}).get("waits"), 1)

    def test_past_deadline_post_start_is_fail(self):
        p = subprocess.Popen(["sleep", "300"], start_new_session=True)
        self.running(p.pid, datetime.now(timezone.utc) - timedelta(hours=1), started=True)
        with mock.patch.object(rf.notify, "smoke_fail", lambda *a, **k: None):
            self.assertEqual(rf.reconcile_dryruns(self.flags, NOLOG), [(self.rid, "FAIL")])
        p.wait(timeout=10)
        self.assertEqual(len(rf.fail_paths(self.flags, self.rid)), 1)

    def test_legacy_running_json_without_deadline_or_grant_is_reaped_after_its_window(self):
        # kpf-rs1-impact-8952-20261104-r5: RUNNING.json (no deadline), grant gone, engine alive ~13 h
        p = subprocess.Popen(["sleep", "300"], start_new_session=True)
        rf.atomic_json(rf.running_path(self.flags, self.rid), {"pid": p.pid, "pgid": p.pid, "regions": "0-3",
                                                                "started": iso(datetime.now(timezone.utc) - timedelta(hours=13))})
        r = rf.reconcile_dryruns(self.flags, NOLOG)
        p.wait(timeout=10)
        self.assertEqual(r, [(self.rid, "deadline")])
        self.assertFalse(os.path.exists(rf.running_path(self.flags, self.rid)))

    def test_before_deadline_alive_untouched(self):
        p = subprocess.Popen(["sleep", "300"], start_new_session=True)
        try:
            self.running(p.pid, datetime.now(timezone.utc) + timedelta(hours=1))
            self.assertEqual(rf.reconcile_dryruns(self.flags, NOLOG), [])
            self.assertTrue(os.path.exists(rf.running_path(self.flags, self.rid)))
        finally:
            p.kill(); p.wait()

    def test_three_waits_then_fail_never_started(self):
        rf.atomic_json(rf.smoke_queued_path(self.flags, self.rid), {"id": self.rid})
        d = rf.rows(self.flags)[self.rid]
        with mock.patch.object(rf.notify, "smoke_fail", lambda *a, **k: None):
            v = [rf.smoke_wait_or_fail(self.flags, self.rid, d, "never reached START", NOLOG) for _ in range(3)]
        self.assertEqual(v, ["WAIT", "WAIT", "FAIL"])
        self.assertIn("never-started", rf.load_json(rf.fail_paths(self.flags, self.rid)[0])["reason"])
        self.assertFalse(os.path.exists(rf.smoke_queued_path(self.flags, self.rid)))

    def test_idle_why_names_partial_cpu_quarter(self):
        p = subprocess.Popen(["sleep", "300"])
        try:
            rf.atomic_json(rf.running_path(self.flags, self.rid), {"pid": p.pid, "regions": "0-3"})
            busy, free, holders = rf.host_snapshot(self.flags, [], {})
            why = rf.idle_partial_quarters(self.flags, free, busy, [], holders)
            self.assertIn("q0", why)
            self.assertIn(f"smoke {self.rid}", why["q0"])
            self.assertNotIn("q1", why)
        finally:
            p.kill(); p.wait()


class SmokeHoldsExactCores(unittest.TestCase):
    """coordinator (A) 2026-11-05: a 4-core smoke on q0 held `holds=q0` and idled six whole-quarter rows."""

    def test_dryrun_grant_holds_exact_tokens_not_quarter(self):
        h = rf.dryrun_grant_holds("4-7")
        self.assertEqual(h, {"c4", "c5", "c6", "c7", "t100", "t101", "t102", "t103"})
        self.assertNotIn("q0", h)
        self.assertEqual(rf.dryrun_grant_holds("0-23,96-111"), {"q0"})

    def test_four_core_smoke_leaves_20_q0_cores_grantable(self):
        flags = tempfile.mkdtemp()
        p = subprocess.Popen(["sleep", "300"])
        try:
            rf.atomic_json(rf.running_path(flags, "sm"), {"pid": p.pid, "regions": "4-7"})
            busy, free, _ = rf.host_snapshot(flags, [], {})
            q0free = {c for c in rf.qcores("q0") if c in free}
            self.assertEqual(len(q0free), 20)
            self.assertNotIn("q0", free, "a whole-q0 row waits for exactly those 4 cores")
            self.assertEqual(rf.expand({"q0"}) & busy - {"q0"}, {"c4", "c5", "c6", "c7", "t100", "t101", "t102", "t103"})
        finally:
            p.kill(); p.wait()
        busy, free, _ = rf.host_snapshot(flags, [], {})
        self.assertIn("q0", free, "the smoke's end returns the whole quarter")


# ---------------------------------------------------------------- item 5 (D10): sudo --preserve-env refused
class D10PreserveEnv(Fx):
    CJ6A = ("exec sudo -n --preserve-env=WS58_REGIONS,FILLER_CPUS,FILLER_SMOKE,FILLER_DRYRUN,FILLER_DRYRUN_DIR,"
            "FILLER_DRYRUN_RESULT_PATH setpriv --reuid=1000 ")

    def test_sudo_preserve_env_missing_names_refused(self):
        lp = self.launcher("pe1", pre=self.CJ6A + "true\n")
        with self.assertRaises(rf.Refused) as e:
            rf.publish(self.spec("pe1", lp, regions="any-cpu-quarter"), self.flags)
        self.assertIn("FILLER_DRYRUN_ONE_QUARTER", str(e.exception))

    def test_preserve_env_complete_admitted(self):
        lp = self.launcher("pe2", pre="exec sudo -n --preserve-env=" + ",".join(rf.DRYRUN_REQUIRED_ENV) + " true\n")
        row = rf.publish(self.spec("pe2", lp, regions="any-cpu-quarter"), self.flags)
        self.assertEqual(row["env_passthrough"], sorted(rf.DRYRUN_REQUIRED_ENV))


class D10EngineDerives(unittest.TestCase):
    def run_engine(self, env):
        d = tempfile.mkdtemp()
        stop = os.path.join(d, "STOP")
        r = subprocess.run(["bash", os.path.join(_RF, "filler_run15.sh"), "--id", "e1", "--class", "cpu", "--cmd", "true",
                            "--stop", stop, "--complete-cmd", "false", "--workdir", d],
                           env=dict(os.environ, FILLER_POLL="1", **env), capture_output=True, text=True, timeout=60)
        return d, r

    def test_dryrun_without_dryrun_dir_exits_64(self):
        _, r = self.run_engine({"FILLER_DRYRUN": "1"})
        self.assertEqual(r.returncode, 64, r.stderr)

    def test_dryrun_derives_grants_dir_from_dryrun_dir(self):
        flags = tempfile.mkdtemp()
        dr = os.path.join(flags, "dryrun", "e1")
        os.makedirs(os.path.join(dr, "grants"))
        open(os.path.join(dr, "stop"), "w").close()   # STOP while waiting: exits at once, after logging its grants dir
        env = {"FILLER_DRYRUN": "1", "FILLER_DRYRUN_DIR": dr, "FILLER_GRANTS_DIR": "/nonexistent-main-grants"}
        _, r = self.run_engine(env)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn(f"grants={dr}/grants", r.stdout)
        self.assertIn("stopped-while-waiting", open(os.path.join(dr, "ended")).read())


# ---------------------------------------------------------------- item 7: keeper smoke under a whole-host grant
class SmokeUnderWholeHost(unittest.TestCase):
    def setUp(self):
        self.flags = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.flags, "ready"))
        rf.atomic_json(rf.smoke_queued_path(self.flags, "s1"), {"id": "s1", "queued_at": "2026-11-05T12:00:00Z"})

    def test_whole_host_grant_waits_and_holds_no_token(self):
        logs = []
        with mock.patch.object(rf.subprocess, "Popen", side_effect=AssertionError("nothing is free")):
            self.assertEqual(rf.place_smokes(self.flags, {rf.GPU}, logs.append), [])
        self.assertTrue(any(l.startswith("SMOKE-WAIT s1") for l in logs))
        self.assertFalse(os.path.exists(rf.smoke_placed_path(self.flags, "s1")))
        self.assertEqual(rf.live_smoke_tokens(self.flags), set())
        self.assertEqual(rf.fail_paths(self.flags, "s1"), [])

    def test_harness_exception_is_wait_not_fail_and_releases(self):
        with mock.patch.object(pr, "run_smoke", side_effect=RuntimeError("boom")):
            v = pr.run_queued_smoke(self.flags, "s1", "0-3")
        self.assertEqual(v, "WAIT")
        self.assertEqual(rf.fail_paths(self.flags, "s1"), [])
        self.assertTrue(os.path.exists(rf.smoke_queued_path(self.flags, "s1")), "stays queued")
        self.assertFalse(os.path.exists(rf.smoke_placed_path(self.flags, "s1")), "no token held")


if __name__ == "__main__":
    unittest.main()
