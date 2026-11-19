"""SCRATCH-LEASE-P2: allocate API. Temp dirs only; never touches /mnt/raid0/llm/tmp or the real lease dir."""
import os
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SYS = os.path.join(ROOT, "scripts", "system")
sys.path.insert(0, SYS)
import scratch_lease as sl  # noqa: E402


class Allocate(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.root = os.path.join(self.td.name, "tmp")
        self.ldir = os.path.join(self.td.name, "leases")
        os.makedirs(self.root)

    def tearDown(self):
        self.td.cleanup()

    def alloc(self, name="job1", **kw):
        kw.setdefault("owner", "workspace-99")
        kw.setdefault("ttl_days", 3)
        return sl.allocate(name, root=self.root, ldir=self.ldir, **kw)

    def test_creates_dir_marker_and_lease_with_owner_and_ttl(self):
        now = time.time()
        le = self.alloc(now=now, row="ROW-1", budget_gib=2.5)
        t = os.path.join(os.path.realpath(self.root), "job1")
        self.assertTrue(os.path.isdir(t))
        self.assertEqual(sl.find_markers(t), [os.path.join(t, ".epyc-keep")])
        d = sl.read_lease(t, self.ldir)
        self.assertEqual(d, le)
        self.assertEqual(d["owner"], "workspace-99")
        self.assertEqual(d["handoff_or_row"], "ROW-1")
        self.assertEqual(sl._epoch(d["expires"]) - sl._epoch(d["created"]), 3 * 86400)
        self.assertEqual(sl.parse_owner(open(os.path.join(t, ".epyc-keep")).read()), "workspace-99")

    def test_blocks_until_expiry_then_releases(self):
        now = time.time()
        self.alloc(now=now)
        t = os.path.join(os.path.realpath(self.root), "job1")
        self.assertTrue(sl.marker_blocks(t, now + 86400, self.ldir))
        self.assertFalse(sl.marker_blocks(t, now + 4 * 86400, self.ldir))

    def test_refuses_missing_owner_bad_ttl_bad_name_existing_target_missing_root(self):
        for kw in ({"owner": ""}, {"owner": "  "}, {"owner": "unknown"}, {"ttl_days": 0}, {"ttl_days": -1},
                   {"ttl_days": sl.MAX_TTL_DAYS + 1}, {"ttl_days": True}):
            with self.assertRaises(sl.LeaseError, msg=str(kw)):
                self.alloc(**kw)
        for bad in ("", "a/b", "../x", ".hidden", "KEEP", "x.epyc-keep", "sp ace"):
            with self.assertRaises(sl.LeaseError, msg=bad):
                self.alloc(name=bad)
        self.assertEqual(os.listdir(self.root), [])
        self.alloc()
        with self.assertRaises(sl.LeaseError):
            self.alloc()
        with self.assertRaises(sl.LeaseError):
            sl.allocate("x", owner="o", ttl_days=1, root=os.path.join(self.td.name, "nope"), ldir=self.ldir)

    def test_refuses_pre_existing_unleased_dir_without_touching_it(self):
        pre = os.path.join(self.root, "legacy")
        os.mkdir(pre)
        with self.assertRaises(sl.LeaseError):
            self.alloc("legacy")
        self.assertEqual(os.listdir(pre), [])

    def test_lease_write_failure_leaves_no_half_state(self):
        blocker = os.path.join(self.td.name, "leases")
        open(blocker, "w").close()           # lease dir path is a FILE -> makedirs fails
        with self.assertRaises(OSError):
            self.alloc()
        self.assertEqual(os.listdir(self.root), [])

    def test_cli_allocate_prints_path_and_refuses_without_owner(self):
        env = dict(os.environ, SCRATCH_LEASE_DIR=self.ldir)
        cli = [sys.executable, os.path.join(SYS, "scratch_lease.py"), "allocate", "clijob", "--root", self.root]
        r = subprocess.run(cli + ["--owner", "ws99", "--ttl-days", "2"], capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), os.path.join(os.path.realpath(self.root), "clijob"))
        r = subprocess.run(cli + ["--owner", "unknown", "--ttl-days", "2"], capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 2)
        self.assertIn("REFUSED", r.stderr)
        r = subprocess.run(cli, capture_output=True, text=True, env=env)   # no --owner / --ttl-days: argparse error
        self.assertNotEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
