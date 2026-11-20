#!/usr/bin/env python3
"""`rowflow.py release`: owner-only early release of an idle grant (whole or shrink-to-regions); never kills a running
job (a zombie pid is dead); build grants covered; a grant with a .ended receipt is no phantom hold (AK build-dtree-gdnr-ak2)."""
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest

_TESTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_TESTS), "rowflow"))
import rowflow as rf  # noqa: E402

LINE = "regions=q2 start=2026-11-20T21:44Z end=2026-11-20T23:14Z holds=q2 cpus=48-71,144-159\n"
LINE2 = "regions=q1,q2 start=2026-11-20T21:44Z end=2026-11-20T23:14Z holds=q1,q2\n"


class Release(unittest.TestCase):
    def setUp(self):
        self.f = tempfile.mkdtemp(prefix="rel-")
        self.G = os.path.join(self.f, "grants")
        os.makedirs(self.G)
        os.makedirs(os.path.join(self.f, "ready"))
        self.log = []

    def put(self, name, text):
        with open(os.path.join(self.G, name), "w") as fh:
            fh.write(text)

    def rel(self, rid, by="akagg", **kw):
        return rf.release_grant(self.f, rid, by, kw.pop("reason", "idle"), log=self.log.append, **kw)

    def build(self, rid="build-x-20261120T211712Z", line=LINE, owner="akagg"):
        self.put(rid + ".grant", line)
        self.put(rid + ".build.json", json.dumps({"id": rid, "owner": owner, "kind": "build", "quarters": ["q2"], "cpus": "48-71"}))
        return rid

    def test_build_release_frees_q2(self):
        rid = self.build()
        self.assertEqual(self.rel(rid), "RELEASED")
        self.assertTrue(os.path.exists(os.path.join(self.G, rid + ".ended")))
        self.assertTrue(os.path.exists(os.path.join(self.G, rid + ".grant.released-early")))
        self.assertFalse(os.path.exists(os.path.join(self.G, rid + ".grant")))
        _, free, _ = rf.host_snapshot(self.f, rf.open_grants(self.f), {})
        self.assertIn("q2", free)
        self.assertTrue(any(l.startswith("GRANT-RELEASED") for l in self.log))

    def test_non_owner_refused(self):
        rid = self.build()
        with self.assertRaises(rf.Refused) as e:
            self.rel(rid, by="someone-else")
        self.assertIn("only the row owner", str(e.exception))
        self.assertTrue(os.path.exists(os.path.join(self.G, rid + ".grant")))

    def test_ended_grant_is_not_a_phantom_hold(self):
        # AK hand-release state: .ended written, .grant still present (or .build.json left behind)
        rid = self.build()
        self.put(rid + ".ended", "rc=0 time=2026-11-20T21:45:13Z reason=build-done-early (owner released)\n")
        self.assertEqual(rf.open_grants(self.f), [])
        _, free, holders = rf.host_snapshot(self.f, rf.open_grants(self.f), {})
        self.assertIn("q2", free)
        self.assertNotIn("q2", holders)
        # and the renamed state with only .build.json + .ended left
        os.replace(os.path.join(self.G, rid + ".grant"), os.path.join(self.G, rid + ".grant.released-early"))
        self.assertEqual(rf.open_grants(self.f), [])
        with self.assertRaises(rf.Refused):
            self.rel(rid)   # already ended

    def row(self, rid, owner="akagg", started=True, pid=None):
        with open(rf.ready_path(self.f, rid), "w") as fh:
            json.dump({"id": rid, "owner": owner}, fh)
        self.put(rid + ".grant", LINE2)
        if pid is not None:
            os.makedirs(rf.dry_dir(self.f, rid), exist_ok=True)
            with open(rf.armed_path(self.f, rid), "w") as fh:
                json.dump({"pid": pid}, fh)
        if started:
            os.makedirs(rf.dry_dir(self.f, rid), exist_ok=True)
            with open(os.path.join(rf.dry_dir(self.f, rid), "poller.out"), "w") as fh:
                fh.write("START regions=q1,q2\n")
            os.utime(os.path.join(self.G, rid + ".grant"), (time.time() - 60, time.time() - 60))

    def test_running_job_refused_never_killed(self):
        p = subprocess.Popen(["sleep", "30"])
        try:
            self.row("r-run", pid=p.pid)
            with self.assertRaises(rf.Refused) as e:
                self.rel("r-run")
            self.assertIn("running", str(e.exception))
            self.assertIsNone(p.poll())   # untouched
            self.assertTrue(os.path.exists(os.path.join(self.G, "r-run.grant")))
        finally:
            p.kill(); p.wait()

    def test_zombie_pid_counts_as_dead(self):
        p = subprocess.Popen(["true"])
        for _ in range(100):   # exited but not reaped = zombie
            if rf._proc_stat(p.pid) is None:
                break
            time.sleep(0.05)
        try:
            self.row("r-zomb", pid=p.pid)
            self.assertEqual(self.rel("r-zomb"), "RELEASED")
        finally:
            p.wait()

    def test_shrink_to_remaining_regions(self):
        self.row("r-shrink", started=False)
        self.assertEqual(self.rel("r-shrink", regions="q2"), "SHRUNK")
        g = {x["id"]: x for x in rf.open_grants(self.f)}["r-shrink"]
        self.assertEqual(g["holds"] & set(rf.QUARTERS), {"q1"})
        self.assertFalse(os.path.exists(os.path.join(self.G, "r-shrink.ended")))
        with self.assertRaises(rf.Refused):
            self.rel("r-shrink", regions="q3")   # not held

    def test_shrink_build_updates_build_json(self):
        rid = self.build(line=LINE2)
        self.assertEqual(self.rel(rid, regions="q1"), "SHRUNK")
        self.assertEqual(json.load(open(os.path.join(self.G, rid + ".build.json")))["quarters"], ["q2"])

    def test_cli(self):
        rid = self.build()
        r = subprocess.run([sys.executable, os.path.join(os.path.dirname(_TESTS), "rowflow", "rowflow.py"), "--flags", self.f,
                            "release", rid, "--by", "akagg", "--reason", "leftover"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("RELEASED", r.stdout)


if __name__ == "__main__":
    unittest.main()
