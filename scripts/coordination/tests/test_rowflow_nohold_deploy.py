"""No-hold deploys (operator 2026-11-07 "Approve + deploy"): a global HOLD-ADMISSIONS set for a keeper deploy idled q2, q3
and the GPU for hours, and a renamed HOLD_ADMISSIONS.lifted-symlink still matched the keeper's HOLD_* glob.

1. arm_one snapshots the engine set into <flags>/dryrun/<id>/engine/; the live engine re-execs that copy, so a running
   row executes only its snapshot and a deploy may swap bin/rowflow/ under its open grant.
2. deploy_guard refuses only for LEGACY grants (pollers that still read the live path).
3. The hold check takes exact HOLD_<NAME> files only; *.lifted* / *.disabled* / dangling links never hold."""
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
RF_DIR = os.path.join(HERE, "..", "rowflow")
sys.path.insert(0, RF_DIR)
import rowflow as rf  # noqa: E402

ENGINE_FILES = ("filler_run15.sh", "filler_lib.sh", "notify.py", "diskpause.py")


def _iso(t):
    return dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ps_alive(pid):
    r = subprocess.run(["ps", "-o", "stat=", "-p", str(pid)], capture_output=True, text=True)
    return r.returncode == 0 and r.stdout.strip() and not r.stdout.strip().startswith("Z")


class HoldNames(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.f = self.t.name

    def tearDown(self):
        self.t.cleanup()

    def touch(self, name, text="owner=x\n"):
        with open(os.path.join(self.f, name), "w") as fh:
            fh.write(text)

    def test_renamed_and_disabled_holds_never_match(self):
        self.touch("HOLD-ADMISSIONS.lifted-20261107-operator")
        os.symlink("HOLD-ADMISSIONS", os.path.join(self.f, "HOLD_ADMISSIONS.lifted-symlink"))   # the 2026-11-07 incident
        self.touch("HOLD_KEEPER.disabled")
        self.touch("HOLD_X.bak")
        os.symlink("does-not-exist", os.path.join(self.f, "HOLD_DANGLING"))
        self.assertEqual(rf.operator_holds(self.f), [])

    def test_lifted_symlink_matched_the_old_glob(self):
        """negative control: the pre-fix check (glob HOLD_*) holds the whole keeper on the renamed link."""
        import glob
        self.touch("HOLD-ADMISSIONS")
        os.symlink("HOLD-ADMISSIONS", os.path.join(self.f, "HOLD_ADMISSIONS.lifted-symlink"))
        self.assertTrue(glob.glob(os.path.join(self.f, "HOLD_*")))
        self.assertEqual(rf.operator_holds(self.f), [])

    def test_exact_operator_hold_still_stops(self):
        self.touch("HOLD_EMERGENCY")
        self.assertEqual(rf.operator_holds(self.f), ["HOLD_EMERGENCY"])

    def test_allocate_and_gpu_batch_use_the_exact_check(self):
        import inspect
        for fn in (rf.allocate, rf.gpu_batch):
            src = inspect.getsource(fn)
            self.assertIn("operator_holds(flags)", src)
            self.assertNotIn('"HOLD_*"', src)


class DeployGuard(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.flags = os.path.join(self.t.name, "flags")
        os.makedirs(os.path.join(self.flags, "grants"))
        self.live = os.path.join(self.flags, "bin", "rowflow")
        os.makedirs(self.live)
        for n in ENGINE_FILES:
            shutil.copy(os.path.join(RF_DIR, n), os.path.join(self.live, n))
        self.engine = os.path.join(self.live, "filler_run15.sh")
        self.procs = []

    def tearDown(self):
        for p in self.procs:   # only the pids this test started
            if p.poll() is None:
                p.terminate()
                try:
                    p.wait(10)
                except subprocess.TimeoutExpired:
                    p.kill(); p.wait(5)
        self.t.cleanup()

    def grant(self, rid, start=None, end=None, regions="0-1"):
        now = time.time()
        with open(os.path.join(self.flags, "grants", rid + ".grant"), "w") as f:
            f.write(f"regions={regions} start={_iso(start or now - 5)} end={_iso(end or now + 3600)} holds=c0,c1\n")

    def armed(self, rid, pid, snap=None):
        os.makedirs(rf.dry_dir(self.flags, rid), exist_ok=True)
        with open(rf.armed_path(self.flags, rid), "w") as f:
            json.dump({"id": rid, "pid": pid, "engine_snapshot": snap}, f)

    def test_snapshot_launched_grant_does_not_block(self):
        snap, rec = rf.snapshot_engine(self.flags, "row-a", self.engine)
        self.assertEqual(sorted(rec["files"]), sorted(ENGINE_FILES))
        self.grant("row-a"); self.armed("row-a", 999999999, snap)   # poller gone: the snapshot record decides
        ok, line = rf.deploy_guard(self.flags, ["filler_run15.sh", "rowflow.py"])
        self.assertTrue(ok, line)
        self.assertEqual(rf.legacy_open_grants(self.flags), [])

    def test_legacy_grant_blocks_unless_allowed(self):
        self.grant("row-legacy"); self.armed("row-legacy", 999999999, None)
        ok, line = rf.deploy_guard(self.flags, ["filler_run15.sh"])
        self.assertFalse(ok); self.assertIn("LEGACY", line)
        self.assertTrue(rf.deploy_guard(self.flags, ["filler_run15.sh"], allow_open=True)[0])
        self.assertTrue(rf.deploy_guard(self.flags, ["rowflow.py", "publish_row.py"])[0])   # keeper-only files never block

    def test_cli_exit_codes(self):
        self.grant("row-legacy"); self.armed("row-legacy", 999999999, None)
        cmd = [sys.executable, "-I", os.path.join(RF_DIR, "rowflow.py"), "--flags", self.flags, "deploy-guard", "--changed", "notify.py"]
        self.assertEqual(subprocess.run(cmd, capture_output=True).returncode, 75)
        self.assertEqual(subprocess.run(cmd + ["--allow-open-grants"], capture_output=True).returncode, 0)

    def test_deploy_with_open_snapshot_grant_proceeds_and_running_row_is_unaffected(self):
        """A real filler_run15.sh poller armed with a snapshot; the deploy guard passes; the live engine set is then
        replaced by a broken one (what a deploy does) and the grant still runs to completion on the snapshot."""
        rid = "nohold-e2e"
        wd = os.path.join(self.t.name, "job"); os.makedirs(wd)
        stub_rl = os.path.join(self.t.name, "region-lock")
        with open(stub_rl, "w") as f:   # stands in for region-lock: run the command after `--`
            f.write('#!/bin/bash\nwhile [ "$#" -gt 0 ] && [ "$1" != -- ]; do shift; done; shift; exec "$@"\n')
        os.chmod(stub_rl, 0o755)
        bus = os.path.join(self.t.name, "bus.py")
        with open(bus, "w") as f:
            f.write("import sys\n")
        snap, _ = rf.snapshot_engine(self.flags, rid, self.engine)
        env = dict(os.environ, FILLER_ENGINE_SNAPSHOT=snap, FILLER_FLAGS_DIR=self.flags,
                   FILLER_GRANTS_DIR=os.path.join(self.flags, "grants"), FILLER_STATE_DIR=os.path.join(self.t.name, "state"),
                   FILLER_FENCE_DIR=os.path.join(self.t.name, "fence"), FILLER_POLL="1", FILLER_RL=stub_rl,
                   FILLER_GPU_LOCK=os.path.join(self.t.name, "gpu.lock"), ROWFLOW_SESSION_BUS=bus,
                   ROWFLOW_BUS_ROOT=os.path.join(self.t.name, "busroot"), ROWFLOW_FLAGS=self.flags)
        for k in ("FILLER_DRYRUN", "FILLER_DRYRUN_DIR", "FILLER_ENGINE_HOME", "LOOP_METRICS_LEDGER"):
            env.pop(k, None)
        job = 'echo "lib=$FILLER_LIB" > out.txt; touch done'
        out = open(os.path.join(self.t.name, "poller.out"), "w")
        p = subprocess.Popen(["bash", self.engine, "--id", rid, "--class", "cpu", "--min-window", "300", "--cmd", job,
                              "--complete-cmd", "test -f done", "--stop", os.path.join(wd, "STOP"), "--workdir", wd],
                             env=env, stdout=out, stderr=subprocess.STDOUT, start_new_session=True)
        self.procs.append(p)
        deadline = time.time() + 30
        while time.time() < deadline and "launcher up pid=" not in open(out.name).read():
            time.sleep(0.2)
        self.assertIn("launcher up pid=", open(out.name).read())
        with open(f"/proc/{p.pid}/cmdline", "rb") as f:
            argv = f.read().split(b"\0")
        self.assertIn(os.path.join(snap, "filler_run15.sh").encode(), argv, "the poller must exec its own snapshot")
        self.armed(rid, p.pid, snap)
        self.grant(rid)
        # the deploy: guard passes (snapshot-launched grant), then the live engine set is swapped for a broken one
        ok, line = rf.deploy_guard(self.flags, list(ENGINE_FILES))
        self.assertTrue(ok, line)
        self.assertEqual(rf.legacy_open_grants(self.flags), [])
        for n in ENGINE_FILES:
            tmp = os.path.join(self.live, n + ".part")
            with open(tmp, "w") as f:
                f.write("#!/bin/bash\necho LIVE-ENGINE-READ >&2; exit 99\n" if n.endswith(".sh") else "raise SystemExit(99)\n")
            os.replace(tmp, os.path.join(self.live, n))
        rc = p.wait(90)
        log = open(out.name).read()
        self.assertEqual(rc, 0, log[-2000:])
        self.assertNotIn("LIVE-ENGINE-READ", log)
        self.assertIn("ALL DONE", log)
        self.assertEqual(open(os.path.join(wd, "out.txt")).read().strip(), f"lib={os.path.join(snap, 'filler_lib.sh')}")
        self.assertIn("reason=complete", open(os.path.join(self.flags, "grants", rid + ".ended")).read())


if __name__ == "__main__":
    unittest.main()
