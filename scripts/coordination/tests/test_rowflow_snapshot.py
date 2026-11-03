#!/usr/bin/env python3
"""Rows are independent of lanes: a spec whose launcher (or engine / job file) lives under a lane worktree or /workspace
is SNAPSHOTTED into the row's scratch_root at publish time, the row points into the snapshot, and editing the worktree
afterwards changes nothing the keeper sees. Everything runs in a temp dir with a temp git repo standing in for a lane."""
import json
import os
import shutil
import subprocess
import sys
import textwrap
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "rowflow"))
import rowflow as rf  # noqa: E402
from test_rowflow import Fixture, write, _RF  # noqa: E402


def git(wt, *args):
    return subprocess.run(["git", "-C", wt] + list(args), capture_output=True, text=True, check=True,
                          env=dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@x", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@x")).stdout.strip()


class SnapshotFixture(Fixture):
    """Fixture + a 'lane' git repo under <root>/lanes/wt that SNAPSHOT_ROOTS points at."""

    def __init__(self):
        super().__init__()
        self.lanes = os.path.join(self.root, "lanes")
        self.wt = os.path.join(self.lanes, "wt")
        os.makedirs(self.wt)
        git(self.wt, "init", "-q", "-b", "main")
        rf.SNAPSHOT_ROOTS = [self.lanes + "/"]
        # an engine copy INSIDE the lane (the host has rows pointing at worktrees/mains/<h>/scripts/coordination/rowflow/)
        self.lane_engine_dir = os.path.join(self.wt, "tools", "rowflow")
        os.makedirs(self.lane_engine_dir)
        for f in ("filler_run15.sh", "filler_lib.sh"):
            shutil.copy(os.path.join(_RF, f), os.path.join(self.lane_engine_dir, f))

    def lane_job(self, rid, engine=None, body=None):
        """A job dir INSIDE the lane repo: jobs/<rid>/{launch.sh,job.sh}, committed. The job writes to $D/out."""
        d = os.path.join(self.wt, "jobs", rid)
        os.makedirs(d, exist_ok=True)
        body = body or 'mkdir -p "$D/out"; for i in 1 2 3 4 5 6 7 8 9 10; do [ -e "$FILLER_STOPFILE" ] && exit 75; echo "{\\"item\\": $i, \\"src\\": \\"snapshot\\"}" >> "$D/out/results.jsonl"; sleep 2; done; exit 0'
        write(os.path.join(d, "job.sh"), f'#!/bin/bash\nD={d}\n{body}\n', 0o755)
        write(os.path.join(d, "launch.sh"), textwrap.dedent(f"""\
            #!/bin/bash
            set -euo pipefail
            D={d}
            ENGINE={engine or self.engine}
            exec bash "$ENGINE" --id {rid} --class cpu --min-window 300 --stop "$D/STOP" \\
              --complete-cmd "test -e $D/out/COMPLETE" --workdir "$D" --cmd "bash '$D/job.sh'"
            """), 0o755)
        git(self.wt, "add", "-A")
        git(self.wt, "commit", "-q", "-m", f"job {rid}")
        return d


class SnapshotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fx = SnapshotFixture()

    @classmethod
    def tearDownClass(cls):
        cls.fx.cleanup()
        rf.SNAPSHOT_ROOTS = rf._default_snapshot_roots()

    def test_01_worktree_launcher_is_snapshotted_and_immune_to_lane_edits(self):
        fx = self.fx
        rid = "t-snap-20261101"
        d = fx.lane_job(rid)
        head = git(fx.wt, "rev-parse", "HEAD")
        row = rf.publish(fx.spec(rid, d), fx.flags)
        snap = row["snapshot"]
        scratch = os.path.join(fx.root, rid)
        self.assertEqual(row["scratch_root"], scratch)
        self.assertEqual(snap["snapshot_dir"], os.path.join(scratch, "snapshot"))
        self.assertEqual(snap["source_path"], os.path.join(d, "launch.sh"))
        self.assertEqual(snap["source_commit"], head)
        self.assertEqual(snap["method"], "git-archive")
        self.assertFalse(snap["dirty"])
        # the row points INTO the snapshot and its sha is the snapshot file's sha
        lp = row["launcher"]["path"]
        self.assertTrue(lp.startswith(snap["snapshot_dir"] + "/"), lp)
        self.assertEqual(lp, snap["launcher"])
        self.assertEqual(row["launcher"]["sha256"], rf.sha256(lp))
        self.assertEqual(snap["sha256"][os.path.relpath(lp, snap["snapshot_dir"])], row["launcher"]["sha256"])
        self.assertIn("launcher/job.sh", snap["sha256"])
        # paths were rewritten: the snapshot launcher names no lane path, and result/stop/workdir moved with it
        text = open(lp).read()
        self.assertNotIn(fx.wt, text)
        self.assertIn(snap["snapshot_dir"], text)
        self.assertTrue(row["result_path"].startswith(snap["snapshot_dir"] + "/"), row["result_path"])
        self.assertTrue(row["stop_file"].startswith(snap["snapshot_dir"] + "/"))
        self.assertEqual(row["workdir"], os.path.join(snap["snapshot_dir"], "launcher"))
        self.assertTrue(os.path.isdir(os.path.dirname(row["result_path"])), "result dir pre-created inside the snapshot")
        # snapshot files are read-only; the source is untouched
        self.assertFalse(os.stat(lp).st_mode & 0o222)
        self.assertIn(fx.wt, open(os.path.join(d, "launch.sh")).read())
        self.assertEqual(git(fx.wt, "status", "--porcelain"), "")
        self.assertEqual(rf.status(fx.flags, rid)["state"], "needs-dryrun")
        # a passing dry run keyed on the snapshot sha stays grantable when the lane launcher is edited (no `stale`)
        rf.atomic_json(rf.pass_path(fx.flags, rid), {"id": rid, "passed_at": rf.now_iso(), "launcher_sha256": row["launcher"]["sha256"], "units": 1,
                                                     "result_path": row["result_path"]})
        self.assertEqual(rf.status(fx.flags, rid)["state"], "grantable")
        with open(os.path.join(d, "launch.sh"), "a") as f:
            f.write("# lane edited after publish\n")
        os.remove(os.path.join(d, "job.sh"))
        self.assertEqual(rf.status(fx.flags, rid)["state"], "grantable")
        self.assertEqual(rf.status(fx.flags, rid)["state"], "grantable")  # grantable == admitted by the allocator
        # ... and removing the lane altogether (session done) changes nothing either
        shutil.move(fx.wt, fx.wt + ".gone")
        try:
            self.assertEqual(rf.status(fx.flags, rid)["state"], "grantable")
        finally:
            shutil.move(fx.wt + ".gone", fx.wt)
        git(fx.wt, "checkout", "-q", "--", ".")

    def test_02_dirty_worktree_falls_back_to_copy(self):
        fx = self.fx
        rid = "t-snap-dirty-20261101"
        d = fx.lane_job(rid)
        with open(os.path.join(d, "job.sh"), "a") as f:
            f.write("# uncommitted\n")
        row = rf.publish(fx.spec(rid, d), fx.flags)
        snap = row["snapshot"]
        self.assertTrue(snap["dirty"])
        self.assertIsNone(snap["source_commit"])
        self.assertEqual(snap["method"], "copy")
        self.assertIn("uncommitted", snap["dirty_reason"])
        self.assertIn("# uncommitted", open(os.path.join(snap["snapshot_dir"], "launcher", "job.sh")).read())
        self.assertFalse(os.stat(os.path.join(snap["snapshot_dir"], "launcher", "job.sh")).st_mode & 0o222)
        git(fx.wt, "checkout", "-q", "--", ".")
        # re-publishing replaces the previous (read-only) snapshot
        row2 = rf.publish(fx.spec(rid, d), fx.flags)
        self.assertEqual(row2["snapshot"]["method"], "git-archive")
        self.assertNotIn("# uncommitted", open(os.path.join(row2["snapshot"]["snapshot_dir"], "launcher", "job.sh")).read())

    def test_03_tmp_launcher_is_untouched(self):
        fx = self.fx
        rid = "t-snap-plain-20261101"
        d = fx.job(rid)
        row = rf.publish(fx.spec(rid, d), fx.flags)
        self.assertNotIn("snapshot", row)
        self.assertEqual(row["launcher"]["path"], os.path.join(d, "launch.sh"))
        self.assertEqual(row["scratch_root"], d)
        self.assertFalse(os.path.exists(os.path.join(d, "snapshot")))
        # the explicit knob snapshots a stable launcher too, into a scratch_root of its own
        rid2 = "t-snap-forced-20261101"
        d2 = fx.job(rid2)
        row2 = rf.publish(fx.spec(rid2, d2, snapshot=True, scratch_root=os.path.join(fx.root, rid2 + "-scratch")), fx.flags)
        self.assertEqual(row2["snapshot"]["method"], "copy")
        self.assertTrue(row2["launcher"]["path"].startswith(os.path.join(fx.root, rid2 + "-scratch", "snapshot") + "/"))
        # snapshot: true with the launcher inside its own scratch_root is a refusal (the snapshot would nest)
        with self.assertRaises(rf.Refused):
            rf.publish(fx.spec(rid2, d2, snapshot=True), fx.flags)

    def test_04_dryrun_executes_the_snapshot_not_the_lane(self):
        """Launcher AND engine inside the lane: the dry run runs the snapshot copies; breaking the lane copies afterwards
        cannot break the run."""
        fx = self.fx
        rid = "t-snap-run-20261101"
        d = fx.lane_job(rid, engine=os.path.join(fx.lane_engine_dir, "filler_run15.sh"))
        row = rf.publish(fx.spec(rid, d, dryrun_timeout_s=60), fx.flags)
        snap = row["snapshot"]
        self.assertTrue(row["engine"]["path"].startswith(os.path.join(snap["snapshot_dir"], "ext") + "/"), row["engine"]["path"])
        self.assertTrue(os.path.isfile(os.path.join(os.path.dirname(row["engine"]["path"]), "filler_lib.sh")))
        self.assertEqual(len(snap["units"]), 2)
        # sabotage the lane after publishing: launcher, job and engine all broken
        for f in ("launch.sh", "job.sh"):
            write(os.path.join(d, f), "#!/bin/bash\nexit 1\n", 0o755)
        write(os.path.join(fx.lane_engine_dir, "filler_run15.sh"), "#!/bin/bash\nexit 1\n", 0o755)
        try:
            v, msg = rf.dryrun_run(fx.flags, rid, "0-23")
        finally:
            git(fx.wt, "checkout", "-q", "--", ".")
        self.assertEqual(v, "PASS", msg + "\n" + "\n".join(rf.tail(os.path.join(rf.dry_dir(fx.flags, rid), "launcher.out"), 40)))
        self.assertIn('"src": "snapshot"', open(row["result_path"]).read())
        self.assertEqual(rf.status(fx.flags, rid)["state"], "grantable")


if __name__ == "__main__":
    unittest.main(verbosity=2)


def test_underused_skips_gpu_quiet_of_whole_host_row(tmp_path):
    import importlib.util, os
    spec = importlib.util.spec_from_file_location("rf_uu", os.path.join(os.path.dirname(__file__), "..", "rowflow", "rowflow.py"))
    rf = importlib.util.module_from_spec(spec); spec.loader.exec_module(rf)
    holders = {"gpu-quiet": "r", "q0": "r"}
    busy = {c: (0, 0) for c in range(192)}
    for t in (0, 700):
        busy = {c: (t * 100 if c < 24 else 0, t * 100) for c in range(192)}
        out = rf.underused(str(tmp_path), holders, lambda m: None, set(), sample=busy, now=1000 + t, vram=0)
    assert all(r != "gpu-quiet" for r, _, _ in out)
