"""Prompt scratch release (operator-directed 2026-11-04). Temp dirs only: nothing here touches the real tmp tree,
compute-flags, or runs a reaper."""
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts", "system"))
sys.path.insert(0, os.path.join(ROOT, "scripts", "coordination", "rowflow"))
import scratch_release as sr  # noqa: E402
import rowflow as rf  # noqa: E402

KEEPER = os.path.join(ROOT, "scripts", "coordination", "rowflow", "ws58-calendar-keeper-v13.sh")


def git(cwd, *a):
    subprocess.run(["git", "-C", cwd, "-c", "user.email=t@t", "-c", "user.name=t"] + list(a), check=True,
                   capture_output=True)


def h(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


class Base(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.t = self.td.name

    def tearDown(self):
        self.td.cleanup()


class GitWorktreeInput(Base):
    def setUp(self):
        super().setUp()
        self.repo = os.path.join(self.t, "repo")
        os.makedirs(os.path.join(self.repo, "pkg"))
        git(self.t, "init", "-q", "-b", "main", self.repo)
        open(os.path.join(self.repo, "pkg", "a.py"), "w").write("x = 1\n")
        open(os.path.join(self.repo, "big.bin"), "w").write("B" * 1000)
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-qm", "c1")
        self.sroot = os.path.join(self.t, "job-v3")
        os.makedirs(self.sroot)
        self.wt = os.path.join(self.sroot, "owned-research")
        git(self.repo, "worktree", "add", "-q", "--detach", self.wt, "HEAD")
        os.makedirs(os.path.join(self.sroot, "runs"))
        open(os.path.join(self.sroot, "runs", "out.json"), "w").write("{}")

    def pin(self):
        p = os.path.join(self.wt, "pkg", "a.py")
        open(os.path.join(self.sroot, "RESEARCH-SHA256SUMS"), "w").write("%s  owned-research/pkg/a.py\n" % h(p))

    def test_derive_finds_only_the_worktree(self):
        self.assertEqual([d["path"] for d in sr.derive_inputs(self.sroot)], ["owned-research"])

    def test_clean_worktree_verifies_and_frees_directly(self):
        d = sr.derive_inputs(self.sroot)[0]
        ok, why = sr.verify_input(self.sroot, d)
        self.assertTrue(ok, why)
        sr.free_input(self.sroot, d)
        self.assertFalse(os.path.exists(self.wt))
        self.assertTrue(os.path.isfile(os.path.join(self.sroot, "runs", "out.json")))   # outputs untouched
        out = subprocess.run(["git", "-C", self.repo, "worktree", "list"], capture_output=True, text=True).stdout
        self.assertNotIn("owned-research", out)

    def test_pinned_modification_verifies(self):
        open(os.path.join(self.wt, "pkg", "a.py"), "a").write("y = 2\n")
        self.pin()
        ok, why = sr.verify_input(self.sroot, sr.derive_inputs(self.sroot)[0])
        self.assertTrue(ok, why)

    def test_unpinned_modification_fails(self):
        self.pin()
        open(os.path.join(self.wt, "pkg", "a.py"), "a").write("y = 2\n")
        ok, why = sr.verify_input(self.sroot, sr.derive_inputs(self.sroot)[0])
        self.assertFalse(ok)
        self.assertIn("not pinned", why)

    def test_untracked_file_fails(self):
        open(os.path.join(self.wt, "result.json"), "w").write("{}")
        ok, why = sr.verify_input(self.sroot, sr.derive_inputs(self.sroot)[0])
        self.assertFalse(ok)
        self.assertIn("uncommitted", why)

    def test_local_commit_not_on_any_ref_fails(self):
        open(os.path.join(self.wt, "pkg", "a.py"), "a").write("z\n")
        git(self.wt, "commit", "-qam", "local")
        ok, why = sr.verify_input(self.sroot, sr.derive_inputs(self.sroot)[0])
        self.assertFalse(ok)
        self.assertIn("no ref", why)


class ShaManifestInput(Base):
    def test_verify_against_source(self):
        src = os.path.join(self.t, "src")
        sroot = os.path.join(self.t, "job")
        os.makedirs(src)
        os.makedirs(os.path.join(sroot, "snap"))
        for n in ("a", "b"):
            open(os.path.join(src, n), "w").write(n)
            open(os.path.join(sroot, "snap", n), "w").write(n)
        open(os.path.join(sroot, "SNAP-SHA256SUMS"), "w").write(
            "".join("%s  snap/%s\n" % (h(os.path.join(src, n)), n) for n in ("a", "b")))
        d = {"path": "snap", "kind": "sha-manifest", "manifest": "SNAP-SHA256SUMS", "source": src}
        self.assertTrue(sr.verify_input(sroot, d)[0])
        open(os.path.join(src, "b"), "w").write("changed")
        self.assertFalse(sr.verify_input(sroot, d)[0])
        open(os.path.join(src, "b"), "w").write("b")
        open(os.path.join(sroot, "snap", "extra"), "w").write("job output")
        self.assertFalse(sr.verify_input(sroot, d)[0])
        os.unlink(os.path.join(sroot, "snap", "extra"))
        sr.free_input(sroot, d)
        self.assertFalse(os.path.exists(os.path.join(sroot, "snap")))

    def test_bad_paths_refused(self):
        for p in ("/abs", "../up", "a/../b", "", None):
            self.assertFalse(sr.verify_input(self.t, {"path": p, "kind": "sha-manifest"})[0])


class Release(Base):
    def setUp(self):
        super().setUp()
        self.flags = self.t
        os.makedirs(os.path.join(self.t, "grants"))
        os.makedirs(os.path.join(self.t, "dryrun"))

    def test_versions(self):
        self.assertEqual(sr.version_of("akxall8-c5-declared-floor-v9-20261104"), ("akxall8-c5-declared-floor", "v", 9))
        self.assertEqual(sr.version_of("foo-r12"), ("foo", "r", 12))
        self.assertIsNone(sr.version_of("plain-row"))
        ids = {"x-v9-20261104", "x-v10-20261104", "x-v37-20261104", "y-v40"}
        self.assertEqual(sr.superseded_by("x-v9-20261104", ids), "x-v37-20261104")
        self.assertIsNone(sr.superseded_by("x-v37-20261104", ids))
        self.assertIsNone(sr.superseded_by("x-r1", {"x-v5"}))   # -r and -v lineages are distinct
        self.assertTrue(sr.all_superseded({"x-v9-20261104", "x-v10-20261104"}, ids))
        self.assertFalse(sr.all_superseded({"x-v37-20261104"}, ids))

    def test_row_released(self):
        g = os.path.join(self.t, "grants")
        self.assertFalse(sr.row_released(self.flags, "a-v1", {"a-v1"})[0])
        open(os.path.join(g, "a-v1.ended"), "w").write("rc=1\n")   # any rc
        self.assertTrue(sr.row_released(self.flags, "a-v1", {"a-v1"})[0])
        os.makedirs(os.path.join(self.t, "dryrun", "b-v1"))
        open(os.path.join(self.t, "dryrun", "b-v1", "ended"), "w").write("rc=0 reason=smoke\n")
        self.assertFalse(sr.row_released(self.flags, "b-v1", {"b-v1"})[0])
        open(os.path.join(self.t, "dryrun", "b-v1", "ended"), "w").write("rc=0 time=x reason=complete\n")
        self.assertFalse(sr.row_released(self.flags, "b-v1", {"b-v1"})[0])   # smoke end never releases
        self.assertTrue(sr.row_released(self.flags, "c-v1", {"c-v1", "c-v2"})[0])   # superseded
        open(os.path.join(g, "c-v1.grant"), "w").write("regions=0-23\n")            # ...but never under an open grant
        self.assertFalse(sr.row_released(self.flags, "c-v1", {"c-v1", "c-v2"})[0])

    def test_declared_inputs_win_over_derived(self):
        row = {"scratch_root": self.t, "scratch_inputs": [{"path": "snap", "kind": "sha-manifest"}, {"path": "../x", "kind": "sha-manifest"}]}
        self.assertEqual(sr.row_inputs(row), [{"path": "snap", "kind": "sha-manifest", "derived": False}])


class Dedup(Base):
    def test_link_snapshot_shares_bytes_across_versions(self):
        src = os.path.join(self.t, "src")
        os.makedirs(os.path.join(src, "d"))
        open(os.path.join(src, "d", "img.png"), "wb").write(os.urandom(4096))
        open(os.path.join(src, "f.py"), "w").write("print(1)\n")
        store = os.path.join(self.t, "cas")
        paths = ["owned-research/d/img.png", "owned-research/f.py"]
        r1 = sr.link_snapshot(src, os.path.join(self.t, "v1", "owned-research"), paths, store, prefix="owned-research/")
        r2 = sr.link_snapshot(src, os.path.join(self.t, "v2", "owned-research"), paths, store, prefix="owned-research/")
        self.assertEqual((r1["stored"], r2["stored"], r2["linked"]), (2, 0, 2))
        a = os.stat(os.path.join(self.t, "v1", "owned-research", "d", "img.png"))
        b = os.stat(os.path.join(self.t, "v2", "owned-research", "d", "img.png"))
        self.assertEqual(a.st_ino, b.st_ino)
        self.assertEqual(a.st_mode & 0o777, 0o444)
        self.assertTrue(r1["sums"][0].endswith("  owned-research/d/img.png"))
        with self.assertRaises(ValueError):
            sr.link_snapshot(src, self.t, ["../etc/passwd"], store)


class Budget(Base):
    def test_budget_refusal(self):
        self.assertIsNone(sr.budget_refusal(400, 100, 50))
        self.assertIn("floor", sr.budget_refusal(300, 100, 60))

    def test_rowflow_disk_budget_refusal(self):
        os.makedirs(os.path.join(self.t, "grants"))
        for rid in ("live-a", "done-b"):
            open(os.path.join(self.t, "grants", rid + ".grant"), "w").write("regions=0-23 holds=q0\n")
        open(os.path.join(self.t, "grants", "done-b.ended"), "w").write("rc=0\n")
        rows = {"live-a": {"budget_gib": 100}, "done-b": {"budget_gib": 500}, "new": {"budget_gib": 60}}
        self.assertIsNone(rf.disk_budget_refusal(self.t, "new", rows, free_gib=320))
        self.assertIn("< 150 GiB floor", rf.disk_budget_refusal(self.t, "new", rows, free_gib=300))
        self.assertIsNone(rf.disk_budget_refusal(self.t, "new", {}, free_gib=200))   # legacy rows budget 0
        self.assertIsNone(rf.disk_budget_refusal(self.t, "new", rows, free_gib=None) if rf.disk_free_gib() is None else None)


class DiskFloorPredecessor(Base):
    def test_disk_floor_predecessor(self):
        os.makedirs(os.path.join(self.t, "grants"))
        os.makedirs(os.path.join(self.t, "ready"))
        open(os.path.join(self.t, "grants", "fam-v8-20261104.ended"), "w").write("rc=0 reason=complete\n")
        self.assertIsNone(rf.disk_floor_predecessor(self.t, "fam-v9-20261104"))
        open(os.path.join(self.t, "grants", "fam-v9-20261104.ended"), "w").write("rc=75 time=x reason=disk-floor\n")
        json.dump({"scratch_root": "/s/fam-v9"}, open(os.path.join(self.t, "ready", "fam-v9-20261104.json"), "w"))
        self.assertEqual(rf.disk_floor_predecessor(self.t, "fam-v10-20261104"), ("fam-v9-20261104", "/s/fam-v9"))
        self.assertIsNone(rf.disk_floor_predecessor(self.t, "other-v10"))
        self.assertIsNone(rf.disk_floor_predecessor(self.t, "fam-v9-20261104"))


class KeeperWiring(unittest.TestCase):
    def test_keeper_inline_python_compiles_and_wires_release(self):
        s = open(KEEPER).read()
        m = re.search(r"<<'PY'[^\n]*\n(.*?)\nPY\n", s, re.S)
        compile(m.group(1), "keeper-step6", "exec")
        self.assertIn("release_inputs(root, ids, tag)", m.group(1))
        self.assertIn("SREL.free_input", m.group(1))
        self.assertIn("and not sup: out('HOLD'", m.group(1))
        self.assertEqual(subprocess.run(["bash", "-n", KEEPER]).returncode, 0)


if __name__ == "__main__":
    unittest.main()
